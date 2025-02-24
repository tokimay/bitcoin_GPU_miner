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