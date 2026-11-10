"""Offline address-reference candidates for known firmware images; never emits key bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PROVIDERS = {0x012023b0: 'documented ROM table base', 0x012034a8: 'documented slot B5',
             0x012034c0: 'documented slot B6', 0x01203f64: 'documented setup export',
             0x01203f68: 'documented buffer export', 0x01202604: 'documented setup body',
             0x01202605: 'documented setup Thumb pointer',
             0x0120283a: 'documented buffer body', 0x0120283b: 'documented buffer Thumb pointer',
             0x01202c94: 'documented flash decrypt body',
             0x01202c95: 'documented flash decrypt Thumb pointer'}
BUILDS = {
    '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154': 'fantom',
    'c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd': 'fantom',
    '6de1e182e531d672ef9bcc0aabf853dd724f59e70dfd9c9aa34c28a393d62a21': 'qspi',
    '9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b': 'qspi',
    '57466624effa7b78ea6f775487d78a35dbf141d2ec4a979338266b77bdcccadf': 'qspi',
    '718abc6885cb3c0a45ba0da7a50d1abb0b775f5d48dbeaac1f71025511749558': 'sub',
    'f9ab7a9e845907afe0cdad7d336961cc1467bc37d91a80f173a2d5491c798fca': 'sub',
}


def category(value):
    if 0x01200000 <= value < 0x01210000:
        return 'ROM-address range candidate'
    if 0x40020000 <= value <= 0x40020424 or value == 0x42408400:
        return 'ESC2 cipher-address range candidate; peripheral identity unproved'
    return None


def regions(path):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    kind = BUILDS.get(digest)
    if kind is None:
        raise ValueError('Unsupported artifact digest')
    if kind == 'fantom':
        from core1 import Core1
        core = Core1(path)
        return digest, [('itcm', 0x01100000, core.data[:core.eram_offset]),
                        ('eram', 0x61000000, core.data[core.eram_offset:])]
    if kind == 'qspi':
        from qspi_c1 import parse_c1
        manifest, view = parse_c1(data)
        return digest, [(r['name'], r['runtime_base'],
                         view[r['analysis_offset']:r['analysis_offset'] + r['size']])
                        for r in manifest['regions']]
    # SUB images have a four-byte prefix followed by an ARM vector table.
    sp, reset = struct.unpack_from('<II', data, 4)
    if not 0x20000000 <= sp < 0x20100000 or not 0x08000000 <= reset < 0x08010000 or not reset & 1:
        raise ValueError('Unexpected SUB vector anchors')
    return digest, [('sub', 0x08000000, data[4:])]


def scan_region(data, base):
    """Halfword candidates include data and second halves of real instructions."""
    import capstone
    from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    words, refs = [], []
    for off in range(0, len(data) - 3, 4):
        value = struct.unpack_from('<I', data, off)[0]
        if category(value):
            words.append(dict(address=base + off, value=value))
    for off in range(0, len(data) - 1, 2):
        first = struct.unpack_from('<H', data, off)[0]
        ldr = first & 0xf800 == 0x4800 or first in (0xf8df, 0xf85f)
        branch = first & 0xf800 in (0xe000, 0xf000)
        mov = first & 0xfbe0 == 0xf040
        movw = first & 0xfbf0 == 0xf240
        if not (ldr or branch or mov or movw):
            continue
        ins = next(md.disasm(data[off:off + 4], base + off, count=1), None)
        if ins is None:
            continue
        value, pool = None, None
        if ldr and ins.mnemonic in ('ldr', 'ldr.w') and len(ins.operands) == 2:
            op = ins.operands[1]
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                pool = ((ins.address + 4) & ~3) + op.mem.disp
                if base <= pool and pool + 4 <= base + len(data):
                    value = struct.unpack_from('<I', data, pool - base)[0]
        elif ins.mnemonic in ('b', 'b.w', 'bl') and ins.operands[0].type == ARM_OP_IMM:
            value = ins.operands[0].imm
        elif ins.mnemonic in ('mov', 'mov.w', 'movs', 'movs.w') and ins.operands[1].type == ARM_OP_IMM:
            value = ins.operands[1].imm
        elif ins.mnemonic == 'movw':
            pair = list(md.disasm(data[off:off + 8], base + off))
            if (len(pair) == 2 and pair[1].mnemonic == 'movt'
                    and pair[0].operands[0].reg == pair[1].operands[0].reg):
                value = pair[0].operands[1].imm | (pair[1].operands[1].imm << 16)
        if value is None or category(value) is None:
            continue
        row = dict(address=ins.address, mnemonic=ins.mnemonic, operands=ins.op_str,
                   value=value, pool=pool, category=category(value))
        if ins.mnemonic in ('b', 'b.w', 'bl') and off >= 2:
            prev = next(md.disasm(data[off - 2:off + 2], ins.address - 2, count=1), None)
            if prev is not None and prev.size == 4:
                row['overlapping_previous_decode'] = dict(address=prev.address,
                                                          mnemonic=prev.mnemonic, operands=prev.op_str)
        refs.append(row)
    return dict(base=base, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                address_words=words, exact_provider_words=[w for w in words if w['value'] in PROVIDERS],
                instruction_candidates=refs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    args = parser.parse_args()
    try:
        digest, inputs = regions(args.artifact)
        result = dict(artifact_sha256=digest, regions=[dict(name=name, **scan_region(data, base))
                                                     for name, base, data in inputs],
                      limits=['Candidates do not prove code reachability, ROM identity or key material.',
                              'Covers aligned words, PC literals, immediate B/BL/MOV and contiguous MOVW/MOVT only.',
                              'No ROM dump, decryption, device access or execution is performed.'])
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
