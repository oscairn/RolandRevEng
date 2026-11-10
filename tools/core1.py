"""Read-only CORE1 mapping, scatter records and annotated Thumb disassembly."""
import argparse
from pathlib import Path
import struct

import capstone


class Core1:
    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.header = 0 if 0x20080000 <= int.from_bytes(raw[:4], 'little') < 0x20100000 else 32
        self.data = raw[self.header:]
        if len(self.data) < 16 or int.from_bytes(self.data[4:8], 'little') >> 16 != 0x110:
            raise ValueError('Expected a Fantom-0 CORE1 image or its header-stripped payload')
        # ARMCC __main / __scatterload, checked against its reset-entry pointer.
        marker = bytes.fromhex('0aa090e8000c82448344')
        hits, pos = [], 0
        while (pos := self.data.find(marker, pos)) >= 0:
            hits.append(pos)
            pos += len(marker)
        if len(hits) != 1:
            raise ValueError(f'Expected one ARMCC scatter bootstrap, got {len(hits)}')
        self.eram_offset = hits[0] - 8
        self.md = capstone.Cs(capstone.CS_ARCH_ARM,
                             capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
        self.md.detail = True

    def offset(self, address):
        if 0x1100000 <= address < 0x1100000 + self.eram_offset:
            return address - 0x1100000
        if 0x61000000 <= address < 0x61000000 + len(self.data) - self.eram_offset:
            return address - 0x61000000 + self.eram_offset
        raise ValueError(f'Address not backed by image: {address:#x}')

    def address(self, offset):
        if not 0 <= offset < len(self.data):
            raise ValueError(f'Offset outside payload: {offset:#x}')
        return offset + 0x1100000 if offset < self.eram_offset else offset - self.eram_offset + 0x61000000

    def u32(self, address):
        return struct.unpack_from('<I', self.data, self.offset(address))[0]

    def scatter(self):
        origin = 0x61000034
        start, end = (origin + value for value in
                      struct.unpack_from('<ii', self.data, self.eram_offset + 0x34))
        if end < start or (end - start) % 16 or end - start > 4096:
            raise ValueError('Invalid scatter table bounds')
        records = []
        for address in range(start, end, 16):
            source, destination, length, handler = struct.unpack_from('<4I', self.data, self.offset(address))
            records.append(dict(table_address=address, source=source, destination=destination,
                                length=length, handler=handler))
        return records

    def disasm(self, address, size):
        offset = self.offset(address)
        for ins in self.md.disasm(self.data[offset:offset + size], address):
            note = ''
            if ins.mnemonic == 'ldr' and len(ins.operands) == 2:
                op = ins.operands[1]
                if op.type == capstone.arm.ARM_OP_MEM and op.mem.base == capstone.arm.ARM_REG_PC:
                    pool = ((ins.address + 4) & ~3) + op.mem.disp
                    try:
                        value = self.u32(pool)
                        note = f' ; [{pool:#x}] = {value:#x}'
                        string_offset = self.offset(value)
                        text = self.data[string_offset:string_offset + 160].split(b'\0', 1)[0]
                        if text and all(32 <= byte < 127 for byte in text):
                            note += ' ' + text.decode('ascii')
                    except ValueError:
                        pass
            yield f'{ins.address:08x}  {ins.bytes.hex():10s} {ins.mnemonic:9s} {ins.op_str}{note}'

    def assertion_refs(self, fragment):
        """ITCM PC-relative literal loads of a matching assertion string pointer."""
        needle = fragment.encode('ascii')
        pos = self.data.find(needle)
        if pos < 0:
            return []
        start = self.data.rfind(b'\0', 0, pos) + 1
        pointer = self.address(start)
        pools = {i for i in range(0, len(self.data) - 3, 4)
                 if struct.unpack_from('<I', self.data, i)[0] == pointer}
        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
        md.detail, md.skipdata = True, True
        refs = []
        for ins in md.disasm(self.data[:self.eram_offset], 0x1100000):
            if ins.mnemonic == 'ldr' and len(ins.operands) == 2:
                op = ins.operands[1]
                if op.type == capstone.arm.ARM_OP_MEM and op.mem.base == capstone.arm.ARM_REG_PC:
                    pool = ((ins.address + 4) & ~3) + op.mem.disp - 0x1100000
                    if pool in pools:
                        refs.append(ins.address)
        return refs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--address', type=lambda s: int(s, 0))
    parser.add_argument('--size', type=lambda s: int(s, 0), default=256)
    parser.add_argument('--find', help='Find ITCM literal references to an assertion string')
    args = parser.parse_args()
    core = Core1(args.file)
    if args.find is not None:
        print('\n'.join(hex(address) for address in core.assertion_refs(args.find)))
    elif args.address is not None:
        print('\n'.join(core.disasm(args.address, args.size)))
    else:
        print(f'Container header {core.header:#x}; ERAM starts at payload {core.eram_offset:#x}')
        for record in core.scatter():
            print(' '.join(f'{key}={value:#x}' for key, value in record.items()))


if __name__ == '__main__':
    main()
