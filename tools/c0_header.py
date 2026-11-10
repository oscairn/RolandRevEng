"""Read CORE0 update metadata; no decryption, patching or device access."""
import argparse
import json
from pathlib import Path
import struct


def header(data):
    if len(data) < 96 or data[:9] != b'App1_Main':
        raise ValueError('Expected a 96-byte App1_Main header')
    source, length, destination, reserved, checksum, control, pad1, pad2 = struct.unpack_from('<8I', data, 64)
    if not length or length % 8 or 96 + length > len(data):
        raise ValueError('Invalid or truncated encrypted payload length')
    return dict(payload_offset=96, payload_length=length, flash_source=source,
                load_destination=destination, checksum=checksum, crypto_control=control,
                enabled=control & 255, mode=(control >> 16) & 255, key_index=control >> 24)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    print(json.dumps(header(args.file.read_bytes()), indent=2))
