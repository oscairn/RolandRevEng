"""Copy an arm64 slice and demangled exports from a user-supplied Mach-O.

Requires Apple's dyld_info and c++filt. Does not load or execute the plugin.
"""
import argparse
from pathlib import Path
import re
import struct
import subprocess


def arm64_slice(data):
    if data[:4] == bytes.fromhex('cafebabe'):
        for index in range(struct.unpack_from('>I', data, 4)[0]):
            cpu, subtype, offset, size, align = struct.unpack_from('>5I', data, 8 + 20 * index)
            if cpu == 0x100000c:
                if offset + size > len(data):
                    raise ValueError('Truncated universal Mach-O')
                data = data[offset:offset + size]
                break
        else:
            raise ValueError('No arm64 slice')
    if data[:4] != bytes.fromhex('cffaedfe') or struct.unpack_from('<I', data, 4)[0] != 0x100000c:
        raise ValueError('Expected a little-endian arm64 Mach-O or FAT32 container')
    # The constructor readers use VA == file offset in these three segments.
    offset = 32
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        cmd, size = struct.unpack_from('<II', data, offset)
        if cmd == 25:
            name, address, vm_size, file_offset, file_size = struct.unpack_from('<16sQQQQ', data, offset + 8)
            if name.rstrip(b'\0') in (b'__TEXT', b'__DATA_CONST', b'__DATA') and address != file_offset:
                raise ValueError('Unsupported Mach-O segment mapping')
        if size < 8 or offset + size > len(data):
            raise ValueError('Invalid Mach-O load command')
        offset += size
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    thin = args.out / 'zen_arm64'
    thin.write_bytes(arm64_slice(args.binary.read_bytes()))
    exports = subprocess.run(['xcrun', 'dyld_info', '-exports', str(thin)],
                             capture_output=True, text=True, check=True).stdout
    entries = re.findall(r'^\s*(0x[0-9A-Fa-f]+)\s+(\S+)', exports, re.M)
    # Mach-O's extra leading underscore must be removed before Itanium demangling.
    names = [name[1:] if name.startswith('__Z') else name for _, name in entries]
    demangled = subprocess.run(['c++filt', '-n'], input='\n'.join(names) + '\n',
                               capture_output=True, text=True, check=True).stdout.splitlines()
    if len(demangled) != len(entries):
        raise ValueError('Demangler output does not match export count')
    (args.out / 'exports_dem.txt').write_text(''.join(
        f'{address}\t{name}\n' for (address, _), name in zip(entries, demangled)))
    print(f'{len(entries)} exports; prepared {thin}')


if __name__ == '__main__':
    main()
