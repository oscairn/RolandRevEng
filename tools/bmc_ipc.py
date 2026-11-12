"""Inspect recorded mi078 BMC IPC frames offline; never opens or writes a device."""
import argparse
import json
from pathlib import Path
import struct


def frames(data):
    """Decode the bounded wire layout recovered from mi078's serializer/parser."""
    offset = 0
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError(f'Truncated 12-byte prefix at {offset:#x}')
        prefix = data[offset:offset + 12]
        kind, variable = prefix[0] >> 1, bool(prefix[0] & 1)
        if kind > 9:
            raise ValueError(f'Unsupported message kind {kind} at {offset:#x}')
        if variable:
            if len(data) - offset < 16:
                raise ValueError(f'Truncated payload length at {offset:#x}')
            length = struct.unpack_from('<I', data, offset + 12)[0]
            end = offset + 16 + length
            if end > len(data):
                raise ValueError(f'Truncated variable payload at {offset:#x}')
            payload = data[offset + 16:end]
        else:
            length = prefix[11]
            if length > 7:
                raise ValueError(f'Unsupported inline payload length {length} at {offset:#x}')
            end = offset + 12
            payload = prefix[4:4 + length]
        row = dict(offset=offset, size=end - offset, kind=kind, variable=variable,
                   prefix=prefix.hex(), payload=payload.hex(),
                   byte1=prefix[1], destination=prefix[2], selector=prefix[3])
        if kind == 3 and len(payload) == 4:
            row['word_le'] = int.from_bytes(payload, 'little')
        if kind == 7:
            metadata = prefix[8:12] if variable else payload[:4]
            if len(metadata) != 4:
                raise ValueError(f'Truncated kind-7 metadata at {offset:#x}')
            row['block'] = dict(u16=int.from_bytes(metadata[:2], 'little'),
                                byte2=metadata[2], byte3=metadata[3],
                                data=(payload if variable else payload[4:]).hex())
        yield row
        offset = end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='Existing binary capture file')
    args = parser.parse_args()
    try:
        rows = list(frames(args.capture.read_bytes()))
    except ValueError as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
