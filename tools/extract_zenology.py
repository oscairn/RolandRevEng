"""Rebuild effect pair metadata from local ZENOLOGY arm64 code and exports.

Use lib.BASE/zen_arm64 and exports_dem.txt. No plugin code is executed.
Constructor and indirect-call readers are deliberately bounded heuristics.
"""
import hashlib
import json
import re
import struct

import lib
import parse
from coeftab import coeftab


def program_lists():
    """Candidate LP64 lists: type u32, DSP u8, count u8, padding, pointer u64."""
    data, result = lib.Z, {}
    for offset in range(0, len(data) - 16, 8):
        kind, packed, pointer = struct.unpack_from('<IIQ', data, offset)
        dsp, count = packed & 255, packed >> 8
        if kind not in (0, 1) or dsp > 6 or not 1 <= count <= 16:
            continue
        if pointer % 8 or not 0 < pointer <= len(data) - 24 * count:
            continue
        segments = []
        for index in range(count):
            base, length, capacity, pad, source = struct.unpack_from('<IIIIQ', data, pointer + 24 * index)
            if pad or length % 2 or not 0 <= length <= capacity <= 0x10000 or not capacity:
                break
            if source % 4 or not 0 < source <= len(data) - ((length + 3) & ~3):
                break
            segments.append([base, length, capacity, source])
        if len(segments) == count:
            result[offset] = [offset, kind, packed, segments]
    return result


def init_lists(address, candidates):
    start, end = lib.func(address)
    registers, result = {}, []
    for ins in lib.md().disasm(lib.Z[start:end], start):
        if ins.mnemonic == 'adrp':
            register, immediate = ins.op_str.split(', ')
            registers[register] = int(immediate.lstrip('#'), 0)
        elif ins.mnemonic == 'add' and ins.op_str.count(',') == 2:
            dest, source, immediate = ins.op_str.split(', ')
            if source in registers and immediate.startswith('#'):
                registers[dest] = registers[source] + int(immediate[1:], 0)
        elif ins.mnemonic in ('bl', 'blr'):
            pointer = registers.get('x1')
            if pointer in candidates:
                result.append(candidates[pointer])
            for index in range(18):
                registers.pop(f'x{index}', None)
    return result


def main():
    exports = lib.load_exports()
    candidates = program_lists()
    drivers, labels = {}, {}
    for name, address in exports.items():
        if re.fullmatch(r'vtable for CFsp(?:Mfx|Cho|Rev)\w+', name):
            cls = name.removeprefix('vtable for ')
            init = struct.unpack_from('<Q', lib.Z, address + 0x20)[0]
            try:
                lists = init_lists(init, candidates)
            except ValueError:
                continue
            drivers[cls.upper()] = (cls, lists)
            for item in lists:
                labels.setdefault(str(item[0]), []).append(cls)
    pairs = {}
    for name, address in exports.items():
        match = re.fullmatch(r'(SIM_(MFX|CHO|REV)_(\w+))::Init\(\)', name)
        if not match:
            continue
        cls, kind, suffix = match.groups()
        ctor = parse.ctor_addr(cls)
        if ctor is None:
            continue
        start, end = lib.func(ctor)
        coefficients = coeftab(lib.Z, start, end)
        fsp, lists = drivers.get(('CFsp' + kind + suffix).upper(), (None, []))
        pairs[cls] = [coefficients, fsp, lists or None]
    (lib.BASE / 'pairs.json').write_text(json.dumps(pairs, indent=2) + '\n')
    inventory = dict(sha256=hashlib.sha256(lib.Z).hexdigest(), lists=list(candidates.values()),
                     labels=labels, driver_classes=len(drivers))
    (lib.BASE / 'zenology_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(f'{len(pairs)} SIM classes, {sum(bool(v[2]) for v in pairs.values())} paired; '
          f'{len(candidates)} candidate lists')


if __name__ == '__main__':
    main()
