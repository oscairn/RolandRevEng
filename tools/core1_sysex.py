"""Inspect one saved CORE1 SysEx record; no command generation or device access.

Only the exact internal-word wrapper and debug read reply are supported. Recognition
does not establish forwarding from mi078, device reachability, or safe MMIO access.
"""
import argparse
import json
from pathlib import Path


def inspect(data):
    if len(data) < 2 or data[0] != 0xf0 or data[-1] != 0xf7:
        raise ValueError('Expected one complete SysEx record')
    if any(byte >= 128 for byte in data[1:-1]):
        raise ValueError('Non-seven-bit SysEx body')
    if data[:3] == bytes.fromhex('f04160'):
        if len(data) != 9:
            raise ValueError('Internal-word wrapper must be exactly 9 bytes')
        high = data[3]
        if high > 15:
            raise ValueError('Unsupported high-bit group')
        word_bytes = bytes(data[4 + i] | ((high >> (3 - i)) & 1) << 7
                           for i in range(4))
        word = int.from_bytes(word_bytes, 'little')
        return dict(form='internal_word', word_le=word,
                    word_bytes=word_bytes.hex(), word_high_nibble=word_bytes[0] >> 4,
                    word_byte1=word_bytes[1], word_upper16=word >> 16)
    if data[:5] == bytes.fromhex('f041104e13'):
        encoded = data[9:-2]
        if not encoded or len(encoded) % 8 or len(encoded) > 128:
            raise ValueError('Read reply needs 1..16 complete nibble-encoded words')
        if data[5] >= 16 or any(byte >= 16 for byte in encoded):
            raise ValueError('Unsupported address or non-nibble word data')
        if sum(data[5:-1]) & 127:
            raise ValueError('Invalid read-reply checksum')
        offset = 0
        for byte in data[5:9]:
            offset = offset << 7 | byte
        if offset & 3:
            raise ValueError('Read-reply offset must be four-byte aligned')
        words = []
        for start in range(0, len(encoded), 8):
            word = 0
            for nibble in encoded[start:start + 8]:
                word = word << 4 | nibble
            words.append(word)
        return dict(form='debug_mmio_read_reply', offset=offset,
                    address=0x41100000 + offset, byte_count=4 * len(words),
                    words=words)
    raise ValueError('Unsupported SysEx form; no guessed command decoding')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path, help='Existing file containing one raw SysEx record')
    args = parser.parse_args()
    try:
        result = inspect(args.record.read_bytes())
    except ValueError as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
