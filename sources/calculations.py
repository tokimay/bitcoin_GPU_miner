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