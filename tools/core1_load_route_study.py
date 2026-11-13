#!/usr/bin/env python3
"""Census the bmc0 CORE1 program-load route and its readback users, pinned image.

The loader map (docs/BMC DSP packet and loader map.md, section 6) lists the
driver routines — StackWriteDspProg (0x112f582), WriteLiteralRaw (0x112f528),
WriteLiteralFloat (0x112ff4e), ReadLiteralRaw (0x112f6e8), GetDspProgAdrs
(0x112f92a), WriteDspProgAllImpl (0x1131c4e) — and the manager vtable slots at
address point 0x6117647c (bytes 0x18/0x1c/0x20 upload programs; bytes 0x64/0x6c
write coefficients, 0x70/0x74 read them back). What no note binds is who CALLS
those entries: the load path's users, the readback users, and the exclusion
flag's scope. This tool answers that by:

1. byte-pinning the recovered bodies (assertion signature strings, flag byte
   0x2008480c handling, even-address checks, port command encoding, aperture
   table 0x113a954) so the census runs against the same functions the notes
   name;
2. scanning the whole image (ITCM 0x01100000.. and ERAM 0x61000000..) for
   direct BL/B.W callers of each routine, MOVW/MOVT/BX veneers, and aligned
   word-pointer references;
3. decoding the manager vtable quad region 0x61176490..0x611764f0 and scanning
   for strict virtual-call sites (ldr rX,[rY,#disp]; blx rX) at offsets
   0x18/0x1c/0x20 (program upload slots) and 0x64..0x74 (coefficient write/
   read slots);
4. byte-pinning the boot program walk at 0x61001186: GetDspProgAdrs through
   veneer 0x61076a82, upload through vtable byte 0x18, then a halfword
   readback-compare loop over the written segment.

Static, read-only file analysis. No firmware execution, no device access,
no key/ciphertext material.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

STACK_WRITE_DSP_PROG = 0x0112f583       # Thumb pointers used in BL encodings
WRITE_LITERAL_RAW = 0x0112f529
WRITE_LITERAL_FLOAT = 0x0112ff4f
READ_LITERAL_RAW = 0x0112f6e9
GET_DSP_PROG_ADRS = 0x0112f92b
WRITE_DSP_PROG_ALL_IMPL = 0x1131c4f
WRITE_DRAM_IO_PROG = 0x1131cf5
SEGMENTED_WRITER = 0x1131e71
UNIQUE_SEGMENTED_WRITER = 0x113214f
STACK_FILL_NOP = 0x112fbbb
DSP_LISTED_MEMCPY = 0x112f291
DMA_COMPLETION = 0x112f6a5
ACTIVE_DMA_DRAIN = 0x112f509
SET_EXE_MODE = 0x1130b6d
GET_EXE_MODE = 0x1130be7

MGR_VTABLE_ADDR_POINT = 0x6117647c
MGR_VTABLE_QUADS_START = 0x61176490
MGR_VTABLE_QUADS_END = 0x611764f0

UPLOAD_SLOTS = (0x18, 0x1c, 0x20)
COEF_SLOTS = (0x64, 0x68, 0x6c, 0x70, 0x74)

# (address, hex bytes) — byte-exact anchors. Strings below name each anchor.
ANCHORS = (
    # StackWriteDspProg 0x112f582: dsp<7, even dst/count, flag byte 0x200847f0.
    (0x0112f582, '2de9f84f'),
    (0x0112f58e, '0728'),
    (0x0112f5a4, '10f0010f'),
    (0x0112f5b8, '9b4d'),
    (0x0112f5ba, '2878'),
    (0x0112f5bc, '0228'),
    # WriteLiteralRaw 0x112f528: width-2..4 check, ubfx 19-bit address.
    (0x0112f528, '78b4'),
    (0x0112f540, '941e'),
    (0x0112f542, '032c'),
    (0x0112f554, 'c1f31201'),
    # WriteLiteralFloat 0x112ff4e: same width check.
    (0x0112ff4e, '82b0'),
    (0x0112ff64, '931e'),
    (0x0112ff66, '032b'),
    (0x0112ff7a, 'c1f31201'),
    # ReadLiteralRaw 0x112f6e8: width check, command store, busy-wait loop.
    (0x0112f6e8, '10b5'),
    (0x0112f6fe, 'a2f1020c'),
    (0x0112f702, 'bcf1030f'),
    (0x0112f718, '4c4c'),
    (0x0112f71a, 'c1f31201'),
    (0x0112f71e, '41ea0271'),
    (0x0112f726, 'ccf80010'),
    (0x0112f72a, '4249'),
    (0x0112f72c, 'd1f808c0'),
    (0x0112f730, '1cf0004f'),
    (0x0112f734, 'fad1'),
    # GetDspProgAdrs 0x112f92a: even-address check, aperture add.
    (0x0112f92a, '10b5'),
    (0x0112f942, '11f0010f'),
    (0x0112f95a, 'c94a'),
    (0x0112f95c, '52f82000'),
    (0x0112f960, '0844'),
    # WriteDspProgAllImpl 0x1131c4e: list type 0, DSP equality, flag byte.
    (0x01131c4e, '2de9f047'),
    (0x01131c54, '8068'),
    (0x01131c5c, '0728'),
    (0x01131c6e, '6978'),
    (0x01131c70, '8842'),
    (0x01131c82, '2878'),
    (0x01131c94, '494f'),
    (0x01131c96, '3878'),
    (0x01131ca4, '0120'),
    (0x01131ca6, '3870'),
    # Manager program-write wrappers 0x1135098..0x11350c8 (vtable 0x18/0x1c/0x20).
    (0x01135098, '0122'),
    (0x0113509a, 'fcf7d8bd'),
    (0x011350a8, '0122'),
    (0x011350aa, 'fcf723be'),
    (0x011350b4, '0022'),
    (0x011350b6, 'fcf7cabd'),
    # Boot program walk: veneer call, walk prologue, tail pointer tables.
    (0x61001190, 'd8f80010'),
    (0x61001194, '75f075fc'),
    (0x61001198, 'd8f80410'),
    (0x6100119c, 'd8f80c30'),
    (0x61001270, 'b078'),
    (0x61001272, '6d1c'),
    (0x61001274, 'a842'),
    (0x61001276, '86dc'),
    (0x61001278, '641c'),
    (0x6100127a, '062c'),
    (0x6100127c, '7ff672af'),
    # Readback-compare loop interior (halfword compare, word compare).
    (0x610011ae, 'b3f80080'),
    (0x610011b2, 'b0f800c0'),
    (0x610011be, 'c445'),
    (0x610011c0, '15d1'),
    # Manager vtable quads (bytes 0x14..0x70 of the address point region).
    (0x61176490, 'fd1b1301'),
    (0x61176494, '99501301'),
    (0x61176498, 'a9501301'),
    (0x6117649c, 'b5501301'),
    (0x611764e0, 'e7271301'),
    (0x611764ec, 'bf2a1301'),
    # Boot verify routine's log strings (DSP%c VerifyProg / ...DrProg / NG(%d)).
    (0x610014f4, '44535025632056657269667950726f672829203d2000'),
    (0x6100150f, '204e47282564290a00'),
    (0x61001518, '445350256320566572696679447250726f672829203d2000'),
    # SetExeMode veneer cell and its five boot callers.
    (0x61076aaa, '40f66d3c'),
    (0x610016d8, '75f0e7f9'),
    (0x6100170c, '75f0cdb9'),
    # GetDspProgAdrs veneer cell.
    (0x61076a82, '4ff62b1c'),
)

UPLOAD_SLOT_TARGETS = {0x18: 0x01135099, 0x1c: 0x011350a9, 0x20: 0x011350b5}
COEF_SLOT_TARGETS = {0x64: 0x011327e7, 0x68: 0x11328e3, 0x6c: 0x11329cf,
                     0x70: 0x1132abf, 0x74: 0x1132b89}
EXPECTED_UPLOAD_SITES_18 = [0x01102220, 0x011027c8, 0x0110ddd8, 0x0110e43a,
                            0x01131306, 0x61001118, 0x61013afa, 0x6101ef8c,
                            0x61026a64, 0x6103056c, 0x61030578, 0x61034980,
                            0x61034cf6]
EXPECTED_UPLOAD_SITES_1C = [0x01102250, 0x011027fc, 0x01131336, 0x61001156,
                            0x61026652, 0x61030584, 0x61030594, 0x6103bede,
                            0x6103bee8]
EXPECTED_UPLOAD_SITES_20 = [0x01102280, 0x01129a04, 0x01131366, 0x6101efb0,
                            0x61030594, 0x610836f8]
EXPECTED_BOOT_WALK_SITES = [0x610016d8, 0x610016e4, 0x610016f0,
                            0x610016fc, 0x6100170c]


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    for address, hex_bytes in ANCHORS:
        expected = bytes.fromhex(hex_bytes)
        try:
            actual = core.data[core.offset(address):core.offset(address) + len(expected)]
        except ValueError:
            problems.append((hex(address), 'not backed by image'))
            continue
        if actual != expected:
            problems.append((hex(address), f'expected {hex_bytes}, got {actual.hex()}'))
    return len(ANCHORS), problems


def bl_callers(core, target):
    """Absolute addresses of direct BL/B.W encodings to a Thumb target."""
    from core1_xrefs import branch_candidates
    rows = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        rows += [r['address'] for r in branch_candidates(data, base, target)]
    return sorted(set(rows))


def veneer_callers(core, target):
    """MOVW/MOVT/BX veneer cells targeting a Thumb pointer."""
    from core1_xrefs import veneer_candidates
    rows = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        # branch_candidates disasms at base+offset, so r['address'] is already absolute.
        rows += [r['address'] for r in veneer_candidates(data, base, target)]
    return sorted(set(rows))


def word_pointer_refs(core, target):
    """Aligned image words equal to the value (raw pointers, thumb or not)."""
    from core1_rtti import word_refs
    return sorted({core.address(offset) for offset in word_refs(core.data, target)})


def virtual_slot_sites(core, disp):
    """Strict pairs: ldr rX,[rY,#disp] within 12 prior halfword instructions,
    then blx rX, over both image regions. Returns (site, vtable_offset)."""
    import capstone
    from capstone.arm import ARM_OP_MEM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    regs = {getattr(capstone.arm, name): name[9:].lower() for name in
            ('ARM_REG_R0', 'ARM_REG_R1', 'ARM_REG_R2', 'ARM_REG_R3', 'ARM_REG_R4',
             'ARM_REG_R5', 'ARM_REG_R6', 'ARM_REG_R7', 'ARM_REG_R8', 'ARM_REG_R9',
             'ARM_REG_R10', 'ARM_REG_R11', 'ARM_REG_R12')}
    sites = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        for offset in range(0, len(data) - 3, 2):
            ins = next(md.disasm(data[offset:offset + 4], base + offset, count=1), None)
            if ins is None or ins.mnemonic != 'blx':
                continue
            ops = ins.operands
            if len(ops) != 1 or ops[0].type != ARM_OP_REG or ops[0].reg not in regs:
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
                prior = next(md.disasm(data[start:start + 2], 0, count=1), None)
                if prior and prior.mnemonic == 'ldr' and len(prior.operands) == 2:
                    mem = prior.operands[1]
                    if (mem.type == ARM_OP_MEM and mem.mem.base != capstone.arm.ARM_REG_PC
                            and regs.get(mem.mem.base) == reg and mem.mem.disp == disp
                            and regs.get(prior.operands[0].reg) == reg):
                        sites.append(ins.address)
                        break
                back += 2
    return sorted(set(sites))


def vtable_quads(core):
    return {hex(address): core.u32(address)
            for address in range(MGR_VTABLE_QUADS_START, MGR_VTABLE_QUADS_END, 4)}


def census(core):
    targets = {
        'StackWriteDspProg': STACK_WRITE_DSP_PROG,
        'StackFillDspProgNop': STACK_FILL_NOP,
        'DSP_listed_memcpy': DSP_LISTED_MEMCPY,
        'DMA_completion_helper': DMA_COMPLETION,
        'Active_DMA_drain': ACTIVE_DMA_DRAIN,
        'WriteLiteralRaw': WRITE_LITERAL_RAW,
        'WriteLiteralFloat': WRITE_LITERAL_FLOAT,
        'ReadLiteralRaw': READ_LITERAL_RAW,
        'GetDspProgAdrs': GET_DSP_PROG_ADRS,
        'WriteDspProgAllImpl': WRITE_DSP_PROG_ALL_IMPL,
        'WriteDramIOProg': WRITE_DRAM_IO_PROG,
        'Segmented_writer': SEGMENTED_WRITER,
        'Unique_segmented_writer': UNIQUE_SEGMENTED_WRITER,
        'SetExeMode': SET_EXE_MODE,
        'GetExeMode': GET_EXE_MODE,
    }
    callers = {}
    for name, target in targets.items():
        callers[name] = dict(target=target, direct_bl=bl_callers(core, target),
                             veneers=veneer_callers(core, target),
                             word_pointers=word_pointer_refs(core, target))
    # veneer pool cell -> caller mapping for the two veneer-reached drivers
    for name in ('GetDspProgAdrs', 'SetExeMode'):
        for cell in callers[name]['veneers']:
            callers.setdefault(f'veneer_cell_{hex(cell)}', dict(
                target=cell | 1, direct_bl=bl_callers(core, cell | 1)))
    upload_sites = {disp: virtual_slot_sites(core, disp) for disp in UPLOAD_SLOTS}
    coef_sites = {disp: virtual_slot_sites(core, disp) for disp in COEF_SLOTS}
    return callers, upload_sites, coef_sites, vtable_quads(core)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, nargs='?',
                        default=Path(__import__('os').environ.get('BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin')
    parser.add_argument('--json', action='store_true', help='Emit the JSON report')
    args = parser.parse_args()
    core = load_image(args.image)
    count, problems = check_anchors(core)
    callers, upload_sites, coef_sites, quads = census(core)
    ok = (not problems
          and upload_sites[0x18] == EXPECTED_UPLOAD_SITES_18
          and upload_sites[0x1c] == EXPECTED_UPLOAD_SITES_1C
          and upload_sites[0x20] == EXPECTED_UPLOAD_SITES_20
          and quads.get(hex(MGR_VTABLE_QUADS_START)) == 0x01131bfd)
    report = dict(anchors_checked=count, anchor_problems=problems,
                  upload_slot_call_sites={hex(k): [hex(a) for a in v]
                                          for k, v in upload_sites.items()},
                  coef_slot_call_sites={hex(k): [hex(a) for a in v]
                                        for k, v in coef_sites.items()},
                  vtable_quads={k: hex(v) for k, v in sorted(quads.items())},
                  callers=callers, ok=ok,
                  payload_sha256=hashlib.sha256(core.data).hexdigest())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()