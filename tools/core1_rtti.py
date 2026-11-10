"""Trace a plain CORE1 RTTI name to candidate vtables, without executing firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def word_refs(data, value):
    return [offset for offset in range(0, len(data) - 3, 4)
            if struct.unpack_from('<I', data, offset)[0] == value]


def trace(core, encoded_name):
    needle = encoded_name.encode('ascii') + b'\0'
    name_offset = core.data.find(needle)
    if name_offset < 0 or core.data.find(needle, name_offset + 1) >= 0:
        raise ValueError('Expected one exact RTTI name in the supplied image')
    result = []
    for reference in word_refs(core.data, core.address(name_offset)):
        if reference < 4:
            continue
        typeinfo = core.address(reference - 4)
        for pointer in word_refs(core.data, typeinfo):
            if pointer < 4 or core.data[pointer - 4:pointer] != b'\0' * 4:
                continue
            callbacks = []
            for offset in range(pointer + 4, min(pointer + 4 + 32 * 4, len(core.data) - 3), 4):
                value = struct.unpack_from('<I', core.data, offset)[0]
                if not value & 1:
                    break
                try:
                    core.offset(value & ~1)
                except ValueError:
                    break
                callbacks.append(value)
            if callbacks:
                result.append(dict(typeinfo=typeinfo, vtable=core.address(pointer - 4),
                                   thumb_callback_candidates=callbacks))
    return dict(encoded_name=encoded_name, name_address=core.address(name_offset),
                candidates=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('encoded_name', help='Exact firmware RTTI name, e.g. 13CUMDWRxSysCmd')
    args = parser.parse_args()
    from core1 import Core1
    core = Core1(args.image)
    result = trace(core, args.encoded_name)
    result['payload_sha256'] = hashlib.sha256(core.data).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
