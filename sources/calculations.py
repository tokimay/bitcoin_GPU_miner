
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

import hashlib

from sources.logging import log, LogTypes


def header_hash(header: str) -> str:
    solution_hash = hashlib.sha256(
        hashlib.sha256(bytearray.fromhex(header)).digest()
    ).digest()[::-1].hex()
    return solution_hash

def re_order(hash_string: str) -> str:
    return bytearray.fromhex(hash_string)[::-1].hex()

def difficulty_to_target(difficulty: float) -> str:
    target = ''
    try:
        base_difficulty = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        target = hex(int(base_difficulty / difficulty))[2:].zfill(64)
    except Exception as er:
        log(LogTypes.ERROR, f"difficulty_to_target", er)
    finally:
        return target

def bits_to_target(bits: str) -> str:
    try:
        bits = int(bits, 16)
        bits_bytes = bits.to_bytes(4, 'big')
        exponent = bits_bytes[0]
        coefficient = int.from_bytes(b'\x00' + bits_bytes[1:], 'big')
        target = coefficient * 256 ** (exponent - 3)
        return hex(target)[2:].zfill(64)
    except Exception as er:
        log(LogTypes.ERROR, f"bits_to_target", er)

def re_order_block_hash(block_hash: str) -> str:
    result = ''
    for i in range(0, len(block_hash), 8):
        result += re_order(block_hash[i:i + 8])
    return result