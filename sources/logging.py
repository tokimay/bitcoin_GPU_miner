
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

from datetime import datetime

class FStyle:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    NORMAL = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class LogTypes:
    ERROR = FStyle.RED
    WARNING = FStyle.YELLOW
    INFO = FStyle.PINK
    SUCCEED = FStyle.GREEN
    IMPORTANT = FStyle.BOLD
    TEXT = FStyle.NORMAL
    SPECIAL = FStyle.CYAN

def log(log_type: str, server_message: str, error_message: Exception or str = ''):
    if error_message:
        server_message = str(server_message) + ': '
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {log_type}{server_message}"
          f"{FStyle.PINK}{error_message}{FStyle.NORMAL}")