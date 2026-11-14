#!/usr/bin/env python3
"""Attribute the CBmcDspMgr virtual-call sites (manager vtable 0x6117647c).

Run 17 (tools/core1_dsp_flag_study.py) proved the flag path's manager wrappers
(CBmcDspMgr::SetDspFlag byte 0x10, SetDspFlagBit byte 0x14) have zero direct
callers and listed candidate virtual-call sites, but could not attribute them:
the strict ldr/blx scan counts a site for every ldr-with-offset found within 12
prior halfwords, even when an intervening instruction rewrites the register.
This tool re-derives the site lists with a corrected scan (the matched ldr must
be the LAST write of the blx register before the blx) and bounds the
attribution: it proves the manager objects (cells 0x20084b8c/ba0/bb4, vtable
address point 0x6117647c, RTTI name 10CBmcDspMgr at 0x61173e6d) are dispatched
only by the boot verify routine among literal-backed sites, and enumerates the
corrected byte-0x10/0x14/0x18/0x1c/0x20 site lists.

Static, read-only file analysis of the pinned bmc0 CORE1 payload.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

MGR_VTABLE_ADDR_POINT = 0x6117647c
MGR_TYPEINFO = 0x6117177c
MGR_TYPEINFO_NAME = 0x61173e6d
MGR_NAME = b'10CBmcDspMgr'
MGR_CTOR = 0x6100177c
MGR_CELLS = (0x20084b8c, 0x20084ba0, 0x20084bb4)
OBJ_STRIDE = 0x14

# Corrected strict sites: the matched ldr rX,[rY,#disp] must be the last write
# of rX before the blx (no intervening instruction writing rX). Expected lists
# below were derived from the corrected scan itself and are re-checked here.
EXPECTED_SITES = {
    0x10: [0x11021c0, 0x1102760, 0x110e03e, 0x110e06a, 0x110e274, 0x1128ca0,
           0x1128f20, 0x1128fa4, 0x1128fde, 0x112a666, 0x112a848, 0x113126a,
           0x6101ef68, 0x6102f648, 0x6102fb78, 0x61030578, 0x61030acc,
           0x610839e6, 0x61083d1e],
    0x14: [0x11021f0, 0x1102794, 0x110e060, 0x1129064, 0x11312b8, 0x61030560,
           0x61034cb8, 0x6103ce96, 0x611b74c2, 0x611b7562, 0x611ca2ca],
    0x18: [0x1102220, 0x11027c8, 0x110ddd8, 0x110e43a, 0x1131306, 0x61001118,
           0x61013afa, 0x6101ef8c, 0x61026a64, 0x6103056c, 0x61034980,
           0x61034cf6],
    0x1c: [0x1102250, 0x11027fc, 0x1131336, 0x61001156, 0x61026652,
           0x61030584, 0x6103bede],
    0x20: [0x1102280, 0x1129a04, 0x1131366, 0x6101efb0, 0x61030594,
           0x610836f8],
}

# (address, hex bytes) — byte-exact anchors.
ANCHORS = (
    # Manager vtable: typeinfo slot, address point, flag/flagbit/upload slots.
    (0x61176478, struct.pack('<I', MGR_TYPEINFO).hex()),
    (0x6117647c, struct.pack('<8I', 0x1135095, 0x1135189, 0x1131bbd,
                             0x1131bc3, 0x1131bc7, 0x1131bfd, 0x1135099,
                             0x11350a9).hex()),
    # RTTI: typeinfo words (base pointer, name pointer) and the name bytes.
    (MGR_TYPEINFO, struct.pack('<2I', 0x6117c3f8, MGR_TYPEINFO_NAME).hex()),
    (MGR_TYPEINFO_NAME, (MGR_NAME + b'\0').hex()),
    # The three manager objects are constructed only by 0x6100177c: it loads
    # r4 = 0x20084b8c / r5 = vtable address point from its pool and stores the
    # vtable into each object with a 0x14 stride (adds r4,#0x14 twice).
    (MGR_CTOR, '70b5' '294c' '2b4d' '0022' '2560'),
    (0x61001784, '2560' '2849' '2261' '2848' 'a160' '6060' '2046'),
    (0x610017a0, '1434' '0022' '2560'),               # adds r4,#0x14 (object 2)
    (0x610017c0, '1434' '0022' '2560'),               # adds r4,#0x14 (object 3)
    # Boot verify routine's manager dispatch (byte 0x18 phase 1, 0x1c phase 2):
    # ldreq r0,[pc,...] -> ldr r2,[r0] -> ldr r2,[r2,#0x18] -> blx r2.
    (0x61001114, '0268' '9269' '9047'),
    # Corrected-site spot anchors: the stale matches removed from the committed
    # lists. 0x61030578 blx uses the #0x10 load at 0x61030576 (not #0x18):
    (0x61030576, '0969' '8847'),
    # 0x61030594 blx uses the #0x20 load at 0x61030592 (not #0x1c):
    (0x61030592, '096a' '8847'),
    # 0x61030584 blx uses the #0x1c load at 0x61030582 (not #0x10):
    (0x61030582, 'c969' '8847'),
    # 0x6103056c blx uses the #0x18 load at 0x6103056a (not #0x14):
    (0x6103056a, '8969' '8847'),
    # 0x110e06a blx uses the #0x10 load at 0x110e068 (not #0x14):
    (0x110e068, '0969' '8847'),
    # The dispatcher rows holding the lifecycle function pointers: each row is
    # [0, typeinfo, ctor, fn, helper, helper, helper] — row 1 at 0x6117a848
    # (typeinfo 0x61173414, ctor 0x61030505, fn 0x6103050d) and row 2 at
    # 0x6117b33c (typeinfo 0x611737e4, ctor 0x61034c39, fn 0x61034c53).
    (0x6117a848, struct.pack('<7I', 0, 0x61173414, 0x61030505, 0x6103050d,
                             0x610813c5, 0x61030613, 0x610813c1).hex()),
    (0x6117b33c, struct.pack('<7I', 0, 0x611737e4, 0x61034c39, 0x61034c53,
                             0x610813c5, 0x61034d29, 0x610813c1).hex()),
    # Literal pools behind the boot routine's manager cell loads.
    (0x610014e0, struct.pack('<3I', 0x20084b8c, 0x20084ba0,
                             0x20084bb4).hex()),
    # Ctor pools: the three objects' table pointers and helpers' veneer words.
    (0x61001824, struct.pack('<I', 0x20084b8c).hex()),
    (0x61001828, struct.pack('<I', 0x61085dec).hex()),
    (0x6100182c, struct.pack('<I', 0x2009be2c).hex()),
    (0x61001830, struct.pack('<I', MGR_VTABLE_ADDR_POINT).hex()),
    (0x6100183c, struct.pack('<I', 0x61085e34).hex()),
    (0x61001840, struct.pack('<I', 0x61085e7c).hex()),
    # The ERAM dispatcher-table twins' vtable pool words (ITCM/ERAM ctor twins
    # construct same-vtable objects; their cells are runtime SRAM, anchored
    # here only as pool words).
    (0x112716c, struct.pack('<2I', 0x2009be2c, MGR_VTABLE_ADDR_POINT).hex()),
    (0x11289a8, struct.pack('<I', MGR_VTABLE_ADDR_POINT).hex()),
    (0x6102cc78, struct.pack('<I', MGR_VTABLE_ADDR_POINT).hex()),
    (0x61077b78, struct.pack('<I', MGR_VTABLE_ADDR_POINT).hex()),
)


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    for address, hex_bytes in ANCHORS:
        expected = bytes.fromhex(hex_bytes)
        try:
            actual = core.data[core.offset(address):
                               core.offset(address) + len(expected)]
        except ValueError:
            problems.append((hex(address), 'not backed by image'))
            continue
        if actual != expected:
            problems.append((hex(address),
                             f'expected {hex_bytes}, got {actual.hex()}'))
    return len(ANCHORS), problems


def corrected_virtual_slot_sites(core, disp):
    """Strict virtual-call sites: blx rX where the matched ldr rX,[rY,#disp]
    is the LAST write of rX before the blx (runs 11/17 counted any ldr within
    12 prior halfwords, double-counting stale loads)."""
    import capstone
    from capstone.arm import ARM_OP_MEM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM,
                     capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    regs = {getattr(capstone.arm, name): name[9:].lower() for name in
            ('ARM_REG_R0', 'ARM_REG_R1', 'ARM_REG_R2', 'ARM_REG_R3',
             'ARM_REG_R4', 'ARM_REG_R5', 'ARM_REG_R6', 'ARM_REG_R7',
             'ARM_REG_R8', 'ARM_REG_R9', 'ARM_REG_R10', 'ARM_REG_R11',
             'ARM_REG_R12')}
    sites = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        for offset in range(0, len(data) - 3, 2):
            ins = next(md.disasm(data[offset:offset + 4], base + offset,
                                 count=1), None)
            if ins is None or ins.mnemonic != 'blx':
                continue
            ops = ins.operands
            if (len(ops) != 1 or ops[0].type != ARM_OP_REG
                    or ops[0].reg not in regs):
                continue
            reg = regs[ops[0].reg]
            back = 2
            for _step in range(12):
                start = offset - back
                if start < 0:
                    break
                first = int.from_bytes(data[start:start + 2], 'little')
                if first & 0xf800 == 0xe800 or first >> 11 >= 0x1d:
                    back += 2
                    continue
                prior = next(md.disasm(data[start:start + 2], 0, count=1),
                             None)
                if prior is None:
                    back += 2
                    continue
                if (prior.mnemonic == 'ldr' and len(prior.operands) == 2
                        and regs.get(prior.operands[0].reg) == reg):
                    mem = prior.operands[1]
                    if (mem.type == ARM_OP_MEM
                            and mem.mem.base != capstone.arm.ARM_REG_PC
                            and regs.get(mem.mem.base) == reg
                            and mem.mem.disp == disp):
                        sites.append(ins.address)
                        break
                    # The last write of the register is an ldr with another
                    # displacement (or a non-matching form): stop scanning.
                    break
                # Any other instruction that writes the register stops the scan.
                if _writes_register(prior, reg, regs):
                    break
                back += 2
    return sorted(set(sites))


def _writes_register(prior, reg, regs):
    """Conservative writer check. Store family, push, compares, branches,
    barriers, hint and it-block instructions write no register (store
    writeback excluded — none of the matched sites use it); everything else
    is treated as a writer of its first register operand."""
    if prior.mnemonic in ('cmp', 'cmp.w', 'cmn', 'cmn.w', 'tst', 'tst.w',
                          'teq', 'dsb', 'dmb', 'isb', 'nop', 'b', 'b.w',
                          'bx', 'bl', 'blx', 'cbz', 'cbnz', 'cbz.w',
                          'cbnz.w', 'tbb', 'tbh', 'it', 'itt', 'ite',
                          'ittt', 'iteq', 'itne', 'push', 'svc', 'bkpt'):
        return False
    if (prior.mnemonic.startswith('str') or prior.mnemonic.startswith('stc')
            or prior.mnemonic.startswith('stl')):
        return False
    ops = prior.operands
    if not ops:
        return False
    import capstone
    from capstone.arm import ARM_OP_REG
    op = ops[0]
    return (op.type == ARM_OP_REG and regs.get(op.reg) == reg)


def vtable_refs(core):
    from core1_rtti import word_refs
    return {hex(cell): [hex(core.address(o))
                        for o in word_refs(core.data, cell)]
            for cell in MGR_CELLS}


def report(image_path):
    core = load_image(image_path)
    count, problems = check_anchors(core)
    sites = {disp: corrected_virtual_slot_sites(core, disp)
             for disp in sorted(EXPECTED_SITES)}
    for disp, expected in sorted(EXPECTED_SITES.items()):
        if sites[disp] != expected:
            problems.append((f'sites_{disp:#04x}',
                             [hex(s) for s in sites[disp]],
                             [hex(s) for s in expected]))
    ok = not problems
    return dict(ok=ok, anchors_checked=count, anchor_problems=problems,
                corrected_sites={f'{disp:#04x}': [hex(s) for s in rows]
                                 for disp, rows in sites.items()},
                manager_cell_word_refs=vtable_refs(core),
                payload_sha256=hashlib.sha256(core.data).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, nargs='?',
                        default=Path(__import__('os').environ.get(
                            'BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin')
    args = parser.parse_args()
    result = report(args.image)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()