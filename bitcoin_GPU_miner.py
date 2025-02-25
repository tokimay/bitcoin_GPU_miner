
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

import os
import argparse
import sys as _sys
from sources.logging import FStyle
from sources.miner import Miner


class MinerArgumentParser(argparse.ArgumentParser):

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout

        message = (f"Bitcoin stratum Nvidia GPU miner\nOptions:\n"
                  f"{FStyle.YELLOW}option key             option description           valid values\n{FStyle.NORMAL}"
                  f"-a, --algo             mining algorithm             {FStyle.GREEN} SHA-256D {FStyle.NORMAL}\n"
                  f"-u, --user             worker user name             {FStyle.GREEN} usually your bitcoin address {FStyle.NORMAL}\n"
                  f"-p, --password         worker mining password       {FStyle.GREEN} 'x' or any password {FStyle.NORMAL}\n"
                  f"-o, --ulr              mining server address        {FStyle.GREEN} server:port {FStyle.NORMAL}\n"
                  f"-h, --help             print this message           \n"
                  f"\nExample: {FStyle.YELLOW}bitcoin_GPU_miner.py -u {FStyle.BLUE}BITCOIN_ADDRESS {FStyle.YELLOW}-p {FStyle.BLUE}PASSWORD {FStyle.YELLOW}-o {FStyle.BLUE}SERVER{FStyle.YELLOW}:{FStyle.BLUE}PORT{FStyle.NORMAL}"
                  f"\n")
        file.write(message+"\n")

if __name__ == '__main__':
    _server_address = ''
    _server_port = ''
    _user_name = ''
    _password = ''

    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # setWorking directory an scrypt location
    parser = MinerArgumentParser(description='Bitcoin stratum Nvidia GPU miner')
    parser.add_argument('-a', '--algo', help='SHA-256D (bitcoin hash algorithm)', required=False)
    parser.add_argument('-u', '--user', help='user name (bitcoin address)', required=False)
    parser.add_argument('-p', '--password', help='mining password', required=False)
    parser.add_argument('-o', '--url',help='server url (server:port)', required=False)

    try:
        args = vars(parser.parse_args())
        if args['algo']:
            if args['algo'] == 'SHA-256D':
                pass
            else:
                print(f"\nUnavailable algorithm{FStyle.RED} '{args['algo']}' {FStyle.NORMAL}")
        if args['user']:
            _user_name = args['user']
        if args['password']:
            _password = args['password']
        if args['url']:
            try:
                _s = args['url'].rsplit('//', 1)[1]
            except Exception as er:
                _s = args['url']
            _server_port = _s.rsplit(':', 1)[1]
            _server_port = int(_server_port)
            _server_address = _s.rsplit(':', 1)[0]

        print(f"\n{FStyle.CYAN}Bitcoin stratum Nvidia GPU miner{FStyle.NORMAL}\n"
              f"user name: {FStyle.BLUE}{_user_name}{FStyle.NORMAL}\n"
              f"password : {FStyle.BLUE}{_password}{FStyle.NORMAL}\n"
              f"server address : {FStyle.BLUE}{_server_address}{FStyle.NORMAL}\n"
              f"server port    : {FStyle.BLUE}{_server_port}{FStyle.NORMAL}\n"
              f"\n")
        if _server_address and _server_port and _user_name and _password:
            stratumMiner = Miner(user=_user_name, password=_password,
                                 server=_server_address, port=_server_port)
            stratumMiner.run_miner()
        else:
            print(f"\n{FStyle.RED}Low arguments{FStyle.NORMAL}\n")
            parser.print_help()
    except Exception as er:
        print(f"\n{FStyle.RED}Low arguments{FStyle.NORMAL}\n{er}")
        parser.print_help()
