"""Generate the a_bogus signature used by Douyin's public detail endpoint.

Adapted from the upstream DouyinParser plugin's August 2026 share-page update.
"""

import math
import random
import struct
import time

_S4 = "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe"
_S3 = "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"
_WINDOW_ENV = "1536|747|1536|834|0|30|0|0|1536|834|1536|864|1525|747|24|24|Win32"
_AID = 6383
_PAGE_ID = 6241

_fixed_ts = None


def set_fixed_ts(ts):
    global _fixed_ts
    _fixed_ts = ts


def _now_ms():
    return _fixed_ts if _fixed_ts is not None else int(time.time() * 1000)


def rc4_encrypt(plaintext, key):
    if isinstance(key, str):
        key = key.encode("latin-1")
    if isinstance(plaintext, str):
        plaintext = [ord(c) for c in plaintext]
    elif isinstance(plaintext, (bytes, bytearray)):
        plaintext = list(plaintext)

    state = list(range(256))
    position = 0
    for index in range(256):
        position = (position + state[index] + key[index % len(key)]) & 0xFF
        state[index], state[position] = state[position], state[index]

    output = []
    index = position = 0
    for value in plaintext:
        index = (index + 1) & 0xFF
        position = (position + state[index]) & 0xFF
        state[index], state[position] = state[position], state[index]
        output.append(chr(state[(state[index] + state[position]) & 0xFF] ^ value))
    return "".join(output)


def _rotl(value, bits):
    bits %= 32
    return ((value << bits) | (value >> (32 - bits))) & 0xFFFFFFFF


def _sm3_compress(registers, chunk):
    words = [0] * 132
    for index in range(16):
        words[index] = (
            (chunk[4 * index] << 24)
            | (chunk[4 * index + 1] << 16)
            | (chunk[4 * index + 2] << 8)
            | chunk[4 * index + 3]
        ) & 0xFFFFFFFF

    for index in range(16, 68):
        value = words[index - 16] ^ words[index - 9] ^ _rotl(words[index - 3], 15)
        value = (value ^ _rotl(value, 15) ^ _rotl(value, 23)) & 0xFFFFFFFF
        words[index] = (value ^ _rotl(words[index - 13], 7) ^ words[index - 6]) & 0xFFFFFFFF
    for index in range(64):
        words[index + 68] = (words[index] ^ words[index + 4]) & 0xFFFFFFFF

    result = registers[:]
    for index in range(64):
        constant = 0x79CC4519 if index < 16 else 0x7A879D8A
        ss1 = _rotl((_rotl(result[0], 12) + result[4] + _rotl(constant, index)) & 0xFFFFFFFF, 7)
        ss2 = (ss1 ^ _rotl(result[0], 12)) & 0xFFFFFFFF
        if index < 16:
            ff = (result[0] ^ result[1] ^ result[2]) & 0xFFFFFFFF
            gg = (result[4] ^ result[5] ^ result[6]) & 0xFFFFFFFF
        else:
            ff = (result[0] & result[1] | result[0] & result[2] | result[1] & result[2]) & 0xFFFFFFFF
            gg = (result[4] & result[5] | ~result[4] & result[6]) & 0xFFFFFFFF

        tt1 = (ff + result[3] + ss2 + words[index + 68]) & 0xFFFFFFFF
        tt2 = (gg + result[7] + ss1 + words[index]) & 0xFFFFFFFF
        result[3] = result[2]
        result[2] = _rotl(result[1], 9)
        result[1] = result[0]
        result[0] = tt1
        result[7] = result[6]
        result[6] = _rotl(result[5], 19)
        result[5] = result[4]
        result[4] = (tt2 ^ _rotl(tt2, 9) ^ _rotl(tt2, 17)) & 0xFFFFFFFF
    return [(left ^ right) & 0xFFFFFFFF for left, right in zip(registers, result)]


def sm3_sum(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    data = bytearray(data)
    registers = [
        1937774191,
        1226093241,
        388252375,
        3666478592,
        2842636476,
        372324522,
        3817729613,
        2969243214,
    ]
    size = len(data)
    data.append(0x80)
    while len(data) % 64 != 56:
        data.append(0)
    data += struct.pack(">Q", size * 8)
    for index in range(0, len(data), 64):
        registers = _sm3_compress(registers, data[index : index + 64])

    output = bytearray()
    for value in registers:
        output += struct.pack(">I", value)
    return bytes(output)


def result_encrypt(value, table):
    output = []
    total = math.ceil(len(value) / 3 * 4)
    for index in range(total):
        offset = (index // 4) * 3
        first = ord(value[offset]) if offset < len(value) else 0
        second = ord(value[offset + 1]) if offset + 1 < len(value) else 0
        third = ord(value[offset + 2]) if offset + 2 < len(value) else 0
        packed = (first << 16) | (second << 8) | third
        position = index % 4
        if position == 0:
            output.append(table[(packed >> 18) & 63])
        elif position == 1:
            output.append(table[(packed >> 12) & 63])
        elif position == 2:
            output.append(table[(packed >> 6) & 63])
        else:
            output.append(table[packed & 63])
    return "".join(output)


def _generate_random_bytes(value, option):
    value = int(value)
    return [
        (value & 255 & 170) | (option[0] & 85),
        (value & 255 & 85) | (option[0] & 170),
        (value >> 8 & 255 & 170) | (option[1] & 85),
        (value >> 8 & 255 & 85) | (option[1] & 170),
    ]


def _generate_rc4_payload(url_search_params, user_agent, window_env):
    start_time = _now_ms()
    url_hash = sm3_sum(sm3_sum(url_search_params + "cus"))
    cus_hash = sm3_sum(sm3_sum("cus"))
    user_agent_hash = sm3_sum(result_encrypt(rc4_encrypt(user_agent, "\x00\x01\x0e"), _S3))
    end_time = _now_ms()

    values = {}
    values[8] = 3
    values[10] = end_time
    values[16] = start_time
    values[18] = 44
    args = [0, 1, 14]

    values[20] = (values[16] >> 24) & 255
    values[21] = (values[16] >> 16) & 255
    values[22] = (values[16] >> 8) & 255
    values[23] = values[16] & 255
    values[24] = (values[16] // (256**4)) & 0xFFFFFFFF
    values[25] = (values[16] // (256**5)) & 0xFFFFFFFF

    values[26] = (args[0] >> 24) & 255
    values[27] = (args[0] >> 16) & 255
    values[28] = (args[0] >> 8) & 255
    values[29] = args[0] & 255
    values[30] = (args[1] // 256) & 255
    values[31] = args[1] % 256
    values[32] = (args[1] >> 24) & 255
    values[33] = (args[1] >> 16) & 255
    values[34] = (args[2] >> 24) & 255
    values[35] = (args[2] >> 16) & 255
    values[36] = (args[2] >> 8) & 255
    values[37] = args[2] & 255

    values[38] = url_hash[21]
    values[39] = url_hash[22]
    values[40] = cus_hash[21]
    values[41] = cus_hash[22]
    values[42] = user_agent_hash[23]
    values[43] = user_agent_hash[24]

    values[44] = (values[10] >> 24) & 255
    values[45] = (values[10] >> 16) & 255
    values[46] = (values[10] >> 8) & 255
    values[47] = values[10] & 255
    values[48] = values[8]
    values[49] = (values[10] // (256**4)) & 0xFFFFFFFF
    values[50] = (values[10] // (256**5)) & 0xFFFFFFFF

    values[51] = _PAGE_ID
    values[52] = (_PAGE_ID >> 24) & 255
    values[53] = (_PAGE_ID >> 16) & 255
    values[54] = (_PAGE_ID >> 8) & 255
    values[55] = _PAGE_ID & 255
    values[56] = _AID
    values[57] = _AID & 255
    values[58] = (_AID >> 8) & 255
    values[59] = (_AID >> 16) & 255
    values[60] = (_AID >> 24) & 255

    window_values = [ord(char) for char in window_env]
    values[64] = len(window_values)
    values[65] = values[64] & 255
    values[66] = (values[64] >> 8) & 255
    values[69] = 0
    values[70] = 0
    values[71] = 0

    checksum_indexes = [
        18, 20, 26, 30, 38, 40, 42, 21, 27, 31, 35, 39, 41, 43, 22, 28, 32, 36,
        23, 29, 33, 37, 44, 45, 46, 47, 48, 49, 50, 24, 25, 52, 53, 54, 55, 57,
        58, 59, 60, 65, 66, 70, 71,
    ]
    checksum = 0
    for index in checksum_indexes:
        checksum ^= values[index]
    values[72] = checksum

    payload_indexes = [
        18, 20, 52, 26, 30, 34, 58, 38, 40, 53, 42, 21, 27, 54, 55, 31, 35, 57,
        39, 41, 43, 22, 28, 32, 60, 36, 23, 29, 33, 37, 44, 45, 59, 46, 47, 48,
        49, 50, 24, 25, 65, 66, 70, 71,
    ]
    payload = [values[index] for index in payload_indexes] + window_values + [values[72]]
    return rc4_encrypt(payload, b"y")


def _generate_random_string(first, second, third):
    values = []
    values += _generate_random_bytes(first, [3, 45])
    values += _generate_random_bytes(second, [1, 0])
    values += _generate_random_bytes(third, [1, 5])
    return "".join(chr(value) for value in values)


def generate_a_bogus(url_search_params, user_agent):
    value = _generate_random_string(
        random.random() * 10000,
        random.random() * 10000,
        random.random() * 10000,
    )
    value += _generate_rc4_payload(url_search_params, user_agent, _WINDOW_ENV)
    return result_encrypt(value, _S4) + "="
