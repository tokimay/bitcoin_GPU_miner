
# This file is part of https://github.com/tokimay/bitcoin_GPU_miner
# Copyright (C) 2016 https://github.com/tokimay
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# This software is licensed under GPLv3. If you use or modify this project,
# you must include a reference to the original repository: https://github.com/tokimay/bitcoin_GPU_miner

import asyncio
import threading
from datetime import datetime
import json
import hashlib
import binascii
import numpy as np
import pycuda.driver as cuda
import pycuda.autoinit
from pycuda.autoinit import device
from pycuda.compiler import SourceModule
from sources.calculations import difficulty_to_target, re_order_block_hash, re_order, bits_to_target, header_hash
from sources.logging import LogTypes, log, FStyle

class Miner:
    def __init__(self, user: str, password: str, server: str = 'localhost', port: int = 3333):
        self._username = user
        self._password = password
        self._server_ip = server
        self._server_port = port
        self._server_reader = None
        self._server_writer = None
        self._extra_nonce_1 = '0'
        self._extra_nonce_2_size = 0
        self._target = '0000000000000000000000000000000000000000000000000000000000000000'
        self._job_id = ''
        self._prev_hash_reorder = ''
        self._coinbase1 = ''
        self._coinbase2 = ''
        self._merkle_branch = []
        self._version_reorder = ''
        self._nbits_reorder = ''
        self._ntime_reorder = ''
        self._share_id = 666
        self._total_accepted_shares = 0
        self._total_rejected_shares = 0
        self._threads = 0
        self._blocks = 0
        self._loop_counter = 0
        self._is_new_job = False
        self._is_job_on_gpu = False

    async def __send_message(self, method: str, params: list, _id: int) -> bool:
        try:
            response_message_bytes = (json.dumps(
                {"id": _id,
                 "method": method,
                 "params": params }
            ).replace('\n', '')) + '\n'
            response_message_bytes = response_message_bytes.encode('UTF-8')
            self._server_writer.write(response_message_bytes)
            await self._server_writer.drain()
            return True
        except Exception as er:
            log(LogTypes.ERROR, f"_send_message", er)
            return False

    def run_miner(self):
        try:
            _self_loop = asyncio.get_event_loop()
        except RuntimeError:
            _self_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_self_loop)

        # connect to server
        _connect_task = _self_loop.create_task(self._connect(), name='Connect')
        _self_loop.run_until_complete(_connect_task)

        # subscribe on server
        _subscribe_task = _self_loop.create_task(self._subscribe(), name='Subscribe')
        _self_loop.run_until_complete(_subscribe_task)

        # _authorize on server
        # _authorize_task = _self_loop.create_task(self._authorize(), name='Authorize')
        # _is_authorized = _self_loop.run_until_complete(_authorize_task)

        asyncio.ensure_future(self._listener(), loop=_self_loop)

        _calculate_loop = asyncio.new_event_loop()
        _calculate_thread = threading.Thread(target=self._background_loop, args=(_calculate_loop,), daemon=True)
        _calculate_thread.start()
        _calculate_task = asyncio.run_coroutine_threadsafe(self._calculate(_calculate_loop), _calculate_loop)
        _self_loop.run_forever()

    @staticmethod
    def _background_loop(_loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    async def _connect(self):
        _is_connect = False
        while not _is_connect:
            await asyncio.sleep(1)
            try:
                log(LogTypes.WARNING, f"connecting...")
                self._server_reader, self._server_writer = await asyncio.open_connection(self._server_ip, self._server_port)
                if isinstance(self._server_writer, asyncio.streams.StreamWriter) and isinstance(
                        self._server_reader, asyncio.streams.StreamReader):
                    _is_connect =  True
                else: _is_connect = False
            except Exception as er:
                log(LogTypes.ERROR, f"_connect", er)
                _is_connect = False

    async def _subscribe(self):
        _is_subscribe = False
        while not _is_subscribe:
            await asyncio.sleep(1)
            try:
                log(LogTypes.WARNING, f"Waiting to subscribe...")
                await self.__send_message(method="mining.subscribe", params=[], _id=1)
                request_body = await self._server_reader.readline()
                if isinstance(request_body, bytes):
                    message_body = None
                    try:
                        message_body = json.loads(request_body.decode())
                        if message_body:
                            self._difficulty = message_body['result'][0][0][1]
                            self._extra_nonce_1 = message_body['result'][1]
                            self._extra_nonce_2_size = message_body['result'][2]
                            log(LogTypes.TEXT,
                                       f"Miner subscribed on {self._server_writer.get_extra_info('peername')}")
                            _is_subscribe = True
                    except Exception as er:
                        log(LogTypes.WARNING, f"Unexpected subscribe message {er}", message_body)
            except Exception as er:
                log(LogTypes.WARNING, f"_subscribe", er)

    async def _authorize(self):
        _is_authorized = False
        while not _is_authorized:
            await asyncio.sleep(1)
            try:
                log(LogTypes.WARNING, f"Waiting for authorization...")
                await self.__send_message(method="mining.authorize", params=[self._username, self._password], _id=2)
                request_body = await self._server_reader.readline()
                if isinstance(request_body, bytes):
                    message_body = None
                    try:
                        message_body = json.loads(request_body.decode())
                        if message_body:
                            if isinstance(message_body['result'], bool):
                                log(LogTypes.TEXT,
                                           f"Miner authorized on {self._server_writer.get_extra_info('peername')}")
                                _is_authorized = True
                    except Exception as er:
                        log(LogTypes.WARNING, f"Unexpected authorize message {er}", message_body)
            except Exception as er:
                log(LogTypes.WARNING, f"_authorize", er)

    async def _listener(self):
        while True:
            try:
                request_body = await asyncio.wait_for(self._server_reader.readline(),timeout=60)
                if isinstance(request_body, bytes):
                    message_body = json.loads(request_body.decode())
                    if message_body:
                        await self.__message_parser(message_body)
            except asyncio.TimeoutError:
                pass
            except Exception as er:
                log(LogTypes.WARNING, f"_listener", er)
                await asyncio.sleep(3)

    async def _calculate(self, _loop):
        _kernel = None
        _mod = None
        _device = None
        _contex = None
        try:
            cuda.init()
            _device = cuda.Device(0)
            _contex = _device.make_context()
            # CUDA kernel
            # compile kernel
            _mod = SourceModule(open("sources/miner_CUDA_kernel.cu").read())
            _kernel = _mod.get_function("mine_kernel")
            log(LogTypes.SUCCEED, f"CUDA compiled successfully")
            _SM_count = cuda.Device(0).get_attribute(cuda.device_attribute.MULTIPROCESSOR_COUNT)
            _block_per_SM = 32
            self._threads = 256
            #self._blocks = min(65535, (0xFFFFFFFF // self._threads)) + 1
            self._blocks = min(65535, _SM_count * _block_per_SM)
        except Exception as er:
            log(LogTypes.ERROR, f"_calculate cuda", er)
            await asyncio.sleep(1)

        _prefix_coinbase_gpu_memory = None
        _suffix_coinbase_gpu_memory = None
        _merkle_branch_gpu_memory = None
        _extranonce2_temp_gpu_memory = None

        _start_time = datetime.now()
        _start_mine = datetime.now()
        _start_app = datetime.now()
        while True:
            if self._is_new_job:
                try:
                    if not self._is_job_on_gpu:
                        self._loop_counter = 0
                        log(LogTypes.WARNING, f"Allocating  new  job  on GPU",
                                   f"{_device.name()}")

                        # set result_nonce to 0xFFFFFF
                        cuda.memcpy_htod(int(_mod.get_global("result_nonce")[0]),
                                         np.array([0xFFFFFFFF], dtype=np.uint32))

                        # set target
                        cuda.memcpy_htod(int(_mod.get_global("target")[0]),
                                         np.frombuffer(bytearray.fromhex(self._target), dtype=np.uint8))

                        # set nbits
                        cuda.memcpy_htod(int(_mod.get_global("nbits")[0]),
                                         np.frombuffer(bytearray.fromhex(self._nbits_reorder), dtype=np.uint8))

                        # set ntime
                        cuda.memcpy_htod(int(_mod.get_global("ntime")[0]),
                                         np.frombuffer(bytearray.fromhex(self._ntime_reorder), dtype=np.uint8))

                        # set version
                        cuda.memcpy_htod(int(_mod.get_global("version")[0]),
                                         np.frombuffer(bytearray.fromhex(self._version_reorder), dtype=np.uint8))

                        # set previous_block_hash
                        cuda.memcpy_htod(int(_mod.get_global("previous_block_hash")[0]),
                                         np.frombuffer(bytearray.fromhex(self._prev_hash_reorder), dtype=np.uint8))

                        # build prefix_coinbase = coinbase1 + extra nonce1
                        _prefix_coinbase = (bytearray.fromhex(self._coinbase1 + self._extra_nonce_1))
                        _prefix_coinbase_array = np.frombuffer(_prefix_coinbase, dtype=np.uint8)
                        # allocate prefix_coinbase array size on GPU memory
                        _prefix_coinbase_gpu_memory = cuda.mem_alloc(_prefix_coinbase_array.nbytes)
                        # set prefix_coinbase array on GPU memory
                        cuda.memcpy_htod(_prefix_coinbase_gpu_memory, _prefix_coinbase_array)
                        # set len_prefix_coinbase
                        cuda.memcpy_htod(int(_mod.get_global("len_prefix_coinbase")[0]),
                                         np.uint16(len(_prefix_coinbase_array)))

                        # build suffix_coinbase = coinbase2
                        _suffix_coinbase = (bytearray.fromhex(self._coinbase2))
                        _suffix_coinbase_array = np.frombuffer(_suffix_coinbase, dtype=np.uint8)
                        # allocate suffix_coinbase array size on GPU memory
                        _suffix_coinbase_gpu_memory = cuda.mem_alloc(_suffix_coinbase_array.nbytes)
                        # set suffix_coinbase array on GPU memory
                        cuda.memcpy_htod(_suffix_coinbase_gpu_memory, _suffix_coinbase_array)
                        # set len_suffix_coinbase
                        cuda.memcpy_htod(int(_mod.get_global("len_suffix_coinbase")[0]),
                                         np.uint16(len(_suffix_coinbase_array)))

                        # merkle_branch to bytearray
                        _merkle_branch = bytearray()
                        for trx_id in self._merkle_branch:
                            _merkle_branch = _merkle_branch + (bytearray.fromhex(trx_id))
                        _merkle_branch_array = np.frombuffer(_merkle_branch, dtype=np.uint8)
                        # allocate merkle_branch array size on GPU memory
                        _merkle_branch_gpu_memory = cuda.mem_alloc(_merkle_branch_array.nbytes)
                        # set merkle_branch array on GPU memory
                        cuda.memcpy_htod(_merkle_branch_gpu_memory, _merkle_branch_array)
                        # set merkle_branch_depth
                        cuda.memcpy_htod(int(_mod.get_global("merkle_branch_depth")[0]),
                                         np.uint16(len(_merkle_branch_array)))

                        # build temp extranonce2 to calculate size an allocate memory on GPU
                        _extranonce2_temp = '00' * self._extra_nonce_2_size
                        _extranonce2_temp_array = (bytearray.fromhex(_extranonce2_temp))
                        _extranonce2_temp_array_array = np.frombuffer(_extranonce2_temp_array, dtype=np.uint8)
                        # allocate extranonce2 array size on GPU memory
                        _extranonce2_temp_gpu_memory = cuda.mem_alloc(_extranonce2_temp_array_array.nbytes)
                        # set extranonce2 array on GPU memory
                        cuda.memcpy_htod(_extranonce2_temp_gpu_memory, _extranonce2_temp_array_array)
                        # set len_extranonce2
                        cuda.memcpy_htod(int(_mod.get_global("len_extranonce2")[0]),
                                         np.uint16(self._extra_nonce_2_size))

                        log(LogTypes.SUCCEED, f"Job successfully sent to GPU",
                                   f"{_device.name()}")
                        self._is_job_on_gpu = True
                        log(LogTypes.SPECIAL, f"Mining started")

                    # reset nonce
                    # set result_nonce to 0xFFFFFF
                    cuda.memcpy_htod(int(_mod.get_global("result_nonce")[0]),
                                     np.array([0xFFFFFFFF], dtype=np.uint32))

                    # run  kernel
                    _kernel(_prefix_coinbase_gpu_memory,
                            _suffix_coinbase_gpu_memory,
                            _merkle_branch_gpu_memory,
                            _extranonce2_temp_gpu_memory,
                            block=(self._threads, 1, 1), grid=(self._blocks, 1))

                    # get results
                    _nonce = np.array([0xFFFFFFFF], dtype=np.uint32)
                    cuda.memcpy_dtoh(_nonce, int(_mod.get_global("result_nonce")[0]))

                    if _nonce[0] != 0xFFFFFFFF:
                        _nonce = (hex(_nonce[0].item())[2:]).zfill(8)

                        # get extra nonce
                        _extranonce2_result = np.zeros(self._extra_nonce_2_size, dtype=np.uint8)
                        cuda.memcpy_dtoh(_extranonce2_result, _extranonce2_temp_gpu_memory)

                        _extra_nonce = ''
                        for h in _extranonce2_result.tolist():
                            _extra_nonce = _extra_nonce + hex(h)[2:].zfill(2)

                        _submit_task_result = False
                        while not _submit_task_result:
                            _submit_task = _loop.create_task(self.__send_message(
                                method="mining.submit",
                                params=[self._username,
                                        self._job_id,
                                        _extra_nonce,
                                        (re_order(self._ntime_reorder)).zfill(8),
                                        (re_order(_nonce)).zfill(8)],
                                _id=666), name='Submit')
                            await _submit_task
                            _submit_task_result = _submit_task.result()
                            if not _submit_task_result:
                                await asyncio.sleep(1)

                        log(LogTypes.TEXT, f"Nonce       = '{_nonce}'")
                        log(LogTypes.TEXT, f"ExtraNonce2 = '{_extra_nonce}'")

                        # create coin base
                        _coinbase = self._coinbase1 + self._extra_nonce_1 + _extra_nonce + self._coinbase2
                        _coinbase_id = hashlib.sha256(
                            hashlib.sha256(binascii.unhexlify(_coinbase)).digest()).hexdigest()

                        # calculate merkle root
                        _merkle_root = _coinbase_id
                        for branch in self._merkle_branch:
                            _merkle_root = hashlib.sha256(
                                hashlib.sha256(
                                    binascii.unhexlify(_merkle_root) + binascii.unhexlify(branch)).digest()).hexdigest()

                        _pre_header = f"{self._version_reorder}{self._prev_hash_reorder}{_merkle_root}{self._ntime_reorder}{self._nbits_reorder}"
                        __header_hash = header_hash(_pre_header + _nonce)
                        log(LogTypes.TEXT, f"Header hash = '{__header_hash}'")
                        log(LogTypes.TEXT, f"Finding time= '{datetime.now() - _start_mine}'")
                        _start_mine = datetime.now()

                    self._loop_counter += 1
                    _loop_time = datetime.now()
                    log(LogTypes.TEXT,
                               f"{FStyle.BOLD}kernel loop {FStyle.NORMAL}{FStyle.BLUE}{'{0:2d} '.format(self._loop_counter)}{FStyle.NORMAL}:"
                               f"for job {FStyle.UNDERLINE}{self._job_id}{FStyle.NORMAL}",
                               f"loop time: {_loop_time - _start_time} total time: {_loop_time - _start_mine}")
                    log(LogTypes.TEXT, f"target", f"{self._target}")
                    _start_time = _loop_time
                except Exception as er:
                    log(LogTypes.ERROR, f"_calculate", er)
                    await asyncio.sleep(1)
            else:
                log(LogTypes.WARNING, f"Job calculations have no new job")
                await asyncio.sleep(3)



    async def __message_parser(self, message: dict) -> bool:
        try:
            if 'method' in message:
                if message['method'] == 'mining.set_difficulty':
                    _difficulty = message['params']
                    self._target = difficulty_to_target(_difficulty[0])
                    log(LogTypes.SPECIAL, f"New difficulty received",f"{_difficulty}")
                    log(LogTypes.TEXT, f"Target is set to", f"{self._target}")
                    if self._is_job_on_gpu:
                        self._is_new_job = True
                    self._is_job_on_gpu = False
                    return True

                elif message['method'] == 'mining.notify':
                    log(LogTypes.SPECIAL, f"New job received", f"{message['params'][0]}")
                    if  message["params"][8]:
                        self._is_new_job = message["params"][8]
                        self._is_job_on_gpu = False
                        self._job_id = message["params"][0]
                        # reorder
                        self._prev_hash_reorder = re_order_block_hash(block_hash=message["params"][1])
                        self._coinbase1 = message["params"][2]
                        self._coinbase2 = message["params"][3]
                        self._merkle_branch = message["params"][4]
                        # reorder
                        self._version_reorder = re_order(message["params"][5])
                        # reorder
                        self._nbits_reorder = (re_order(message["params"][6])).zfill(8)
                        # reorder
                        self._ntime_reorder = (re_order(message["params"][7])).zfill(8)

                        # check if new target is easier or harder
                        if (int(bits_to_target(message["params"][6]), 16)) > (int(self._target, 16)):
                            self._target = bits_to_target(message["params"][6])
                            log(LogTypes.TEXT, f"Job target is",f"{self._target}")
                        else:
                            log(LogTypes.TEXT, f"Default target will use")
                    else:
                        log(LogTypes.TEXT, "There is a duplicate job. Nothing to do.")
                    return True

            elif message['id'] == self._share_id:
                if message['result']:
                    self._total_accepted_shares = self._total_accepted_shares + 1
                    log(LogTypes.SUCCEED,
                               f"Share accepted!"
                               f"{FStyle.NORMAL}({FStyle.GREEN}{self._total_accepted_shares}{FStyle.NORMAL}/{FStyle.RED}{self._total_rejected_shares}{FStyle.NORMAL})")
                    self._is_new_job = True
                else:
                    self._total_rejected_shares = self._total_rejected_shares + 1
                    log(LogTypes.ERROR,
                               f"Share, reject by reason {message['error'][1]}"
                               f"{FStyle.NORMAL}({FStyle.GREEN}{self._total_accepted_shares}{FStyle.NORMAL}/{FStyle.RED}{self._total_rejected_shares}{FStyle.NORMAL})")
                return True
            log(LogTypes.TEXT, f"Server message received", f"{message}")
            log(LogTypes.TEXT, f"Parsing this message is not possible for now.")
        except Exception as er:
            log(LogTypes.ERROR, f"_message_parser result: {message} ", er)