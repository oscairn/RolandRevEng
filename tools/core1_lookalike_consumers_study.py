#!/usr/bin/env python3
"""Trace the CORE1 runtime consumers of the DSP1/3/4/5 program-reservation lookalikes.

Run 15 (tools/core1_reservations_study.py) left the same-shape (header, list) run
at 0x610a1ee8..0x610a1f74 as an untraced second table. This tool bounds who
consumes it: two ERAM functions drive its 16 entries through the same manager
upload wrappers the boot route uses (vtable bytes 0x18/0x1c at address point
0x6117647c), reached from the diagnostic dispatcher 0x1126a6c via veneers, behind
CFspDspTest::TestEram 0x6103f4b2.

Steps:
1. byte-pinning the entry pairs, the consumer loads, the upload-wrapper bodies,
   the manager vtable address point and the chain of veneers/branches;
2. decoding all 16 entries (header (count<<16)|(dsp<<8)|phase, list pointer,
   16-byte records);
3. mapping record word0 aperture offsets onto the GetDspProgAdrs program table
   and the run-13 DRAM-IO closed form;
4. checking the consumer call chains end to end (branch scan, committed
   veneer scanner, aligned word-pointer scan) and the zero word at 0x2009bbf8.

Static, read-only file analysis. No firmware execution, no device access,
no key/ciphertext material.
"""
import argparse
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# --- Anchors: (address, expected bytes) -------------------------------------

# Table-2 entries (the run-15 lookalikes), 8 bytes each: (header, list).
TABLE2_FIRST = 0x610a1ef8
TABLE2_LAST = 0x610a1f70
# First entry bytes: header 0x00030100 list 0x610a52e8.
TABLE2_HEAD = (TABLE2_FIRST, '003101' + '00' * 0)  # placeholder, set below
TABLE2_HEAD_BYTES = (TABLE2_FIRST, struct.pack('<II', 0x00030100, 0x610a52e8).hex())
TABLE2_DSP1345_TAIL = (0x610a1f58, struct.pack(
    '<IIII', 0x00010100, 0x610b3d4c, 0x00010300, 0x610b3e24).hex())
TABLE2_END = (0x610a1f78, struct.pack(
    '<II', 0x610b37a0, 0x610b37bc).hex())

# Table-1 entries the first consumer drives (DSP1..DSP5 phase-0 seeds + stubs).
TABLE1_HEAD = (0x610a1ef8 - 0, None)  # table 1 shares the run; see decode step.
TABLE1_P0_POOL = (0x610293d0, '6549')        # ldr r1,[pc,#0x194] -> 0x610a1ef8
TABLE1_P0_LOADS = (
    (0x610293d0, '6549'),   # ldr r1 = 0x610a1ef8 (dsp1 p0)
    (0x610293da, '6449'),   # ldr r1 = 0x610a1f08 (dsp3 p0)
    (0x610293e4, '6249'),   # ldr r1 = 0x610a1f18 (dsp4 p0)
    (0x610293ee, '6149'),   # ldr r1 = 0x610a1f28 (dsp5 p0)
)
TABLE1_VTABLE_LOADS = tuple(
    (address, '8a69') for address in (0x610293ce, 0x610293d8, 0x610293e2,
                                      0x610293ec))  # ldr r2,[r1,#0x18]
TABLE1_CALLER_FN = (0x610293b2, '2de9f04f')  # push.w {r4-r8,sl,fp,lr}

# Second consumer: DSP1/3/4/5 phase-0/1 uploads (tables 2 tail) + stub pair.
TABLE2_LOADS = (
    (0x6102a612, '6549'),   # ldr r1 = 0x610a1f38 (dsp1 p0 stubs)
    (0x6102a61c, '6349'),   # ldr r1 = 0x610a1f40 (dsp3 p0 stubs)
    (0x6102a626, '6249'),   # ldr r1 = 0x610a1f48 (dsp4 p0 stubs)
    (0x6102a630, '6049'),   # ldr r1 = 0x610a1f50 (dsp5 p0 stubs)
    (0x6102a63a, '5f49'),   # ldr r1 = 0x610a1f00 (dsp1 p1)
    (0x6102a644, '5d49'),   # ldr r1 = 0x610a1f10 (dsp3 p1)
    (0x6102a64e, '5c49'),   # ldr r1 = 0x610a1f20 (dsp4 p1)
    (0x6102a658, '5a49'),   # ldr r1 = 0x610a1f30 (dsp5 p1)
    (0x6102a3cc, 'e049'),   # ldr r1 = 0x610a1f58 (dsp1 p0 alt)
    (0x6102a3d6, 'df49'),   # ldr r1 = 0x610a1f60 (dsp3 p0 alt)
    (0x6102a3e0, 'dd49'),   # ldr r1 = 0x610a1f68 (dsp4 p0 alt)
    (0x6102a3ea, 'dc49'),   # ldr r1 = 0x610a1f70 (dsp5 p0 alt)
)
TABLE2_TAILCALL = (0x6102a662, 'fef7a6be')   # b.w 0x610293b2 (table-1 consumer)
TABLE2_SEEDCALL = (0x6102a478, 'fef79bff')   # bl 0x610293b2
TABLE2_CTOR_ENTER = (0x6102a48c, 'd0e6')     # b 0x6102a230

# The reservation entry initializer 0x6102a230 and its phase-1 (0x1c) selector.
TABLE2_CTOR = (0x6102a230, '70b50126')       # push {r4-r6,lr}; movs r6,#1
TABLE2_CTOR_VT = (0x6102a242, 'ca69')        # ldr r2,[r1,#0x1c]
TABLE2_CTOR_POOL1 = (0x6102a244, '3549')     # ldr r1 = 0x610a1f00
TABLE2_CTOR_POOL2 = (0x6102a24e, '3449')     # ldr r1 = 0x610a1f10
TABLE2_CTOR_POOL3 = (0x6102a258, '3249')     # ldr r1 = 0x610a1f20
TABLE2_CTOR_POOL4 = (0x6102a262, '3149')     # ldr r1 = 0x610a1f30

# Table-1 consumer head (0x610293b2) and its 0x3a00 wait + upload calls.
TABLE1_HEAD_ANCHOR = (0x610293b2, '2de9f04f')
TABLE1_WAIT_LOAD = (0x610293c4, '4ff46851')  # mov.w r1,#0x3a00
TABLE1_WAIT_VT = (0x610293c2, '8a68')        # ldr r2,[r1,#8]

# Diagnostic dispatcher 0x1126a6c -> TestEram chain.
DISPATCH_HEAD = (0x1126a6c, 'f8b5')          # push {r3,r4,r5,r6,r7,lr}
DISPATCH_TESTERAM = (0x1126bba, '0ef05ff8')  # bl 0x1134c7c (veneer)
DISPATCH_LOGGER = (0x1126d1e, '0df0e4bf')    # b.w 0x1134cea (veneer)
VENEER_TESTERAM = (0x1134c7c, '4ff2b34cc6f2031c6047')  # -> 0x6103f4b3
VENEER_LOGGER = (0x1134cea, '4af2096c')      # movw ip,#0xa609 ; movt ip,#0x6102

# CFspDspTest::TestEram and its qctest caller.
TESTERAM_HEAD = (0x6103f4b2, '2de9f041')     # push.w {r4-r8,lr}
TESTERAM_CALLER_BL = (0x6108104e, 'bef730fa')  # bl 0x6103f4b2
QCTEST_WORDREF = 0x6117b0f0                  # pointer-table slot holding 0x61080fe1
QCTEST_FN = 0x61080fe1

# Manager upload wrappers (run 11) and the vtable address point.
MANAGER_VTABLE_AP = 0x6117647c
MANAGER_VTABLE_WORDS = {0x18: 0x1135099, 0x1c: 0x11350a9}
UPLOAD_WRAPPER_18 = (0x1135098, '0122')      # movs r2,#1 ; b.w 0x1131c4e
UPLOAD_WRAPPER_1C = (0x11350a8, '0122')      # movs r2,#1 ; b.w 0x1131cf4

# Aperture tables (runs 13/15).
PROGRAM_APERTURE_TABLE = 0x0113a954
PROGRAM_APERTURE_WORDS = tuple([0x41480000 + dsp * 0x100000 for dsp in range(6)]
                               + [0x41260000])
DRAMIO_BANK0 = {dsp: 0x41440000 + dsp * 0x100000 for dsp in range(6)}

# The seed lists of table 1 (16-byte records: word0, len, len, source).
TABLE1_RECORDS = {
    0x610a1ef8: [(0x20, 0x27a, 0x1000, 0x610a505c),
                 (0x1020, 0x6, 0x5000, 0x610a52d8),
                 (0x6020, 0x6, 0x5000, 0x610a52e0)],
    0x610a1f08: [(0x20, 0x186, 0x1000, 0x610a53e4)],
    0x610a1f18: [(0x20, 0x35b6, 0x4000, 0x610a5614),
                 (0x4020, 0x6, 0x1000, 0x610a8bcc),
                 (0x5020, 0x6, 0x1000, 0x610a8bd4),
                 (0x6020, 0x6, 0x400, 0x610a8bdc),
                 (0x6420, 0x6, 0x1000, 0x610a8be4)],
    0x610a1f28: [(0x20, 0x356e, 0x8000, 0x610ad6f0),
                 (0x8040, 0x6, 0x1000, 0x610b0c60),
                 (0x9040, 0x6, 0x1000, 0x610b0c68),
                 (0xa040, 0x6, 0x1000, 0x610b0c70),
                 (0xb040, 0x6, 0x1000, 0x610b0c78),
                 (0xc040, 0x6, 0x1000, 0x610b0c80),
                 (0xd040, 0x6, 0x400, 0x610b0c88),
                 (0xd440, 0x6, 0x400, 0x610b0c90),
                 (0xd840, 0x6, 0x1000, 0x610b0c98),
                 (0xe840, 0x6, 0x1400, 0x610b0ca0),
                 (0xfc40, 0x6, 0x2c0, 0x610b0ca8)],
}
TABLE2_RECORDS = {
    0x610a1f00: [(0x0, 0x0, 0x80, 0x610a5318),
                 (0x80, 0x8, 0x528, 0x610a5320),
                 (0x5a8, 0x10, 0x10, 0x610a5328),
                 (0x2400, 0x8, 0x800, 0x610a5338),
                 (0x2c00, 0x10, 0x400, 0x610a5340)],
    0x610a1f10: [(0x0, 0x0, 0x0, 0x610a557c),
                 (0x0, 0x8, 0x800, 0x610a5584),
                 (0x800, 0x10, 0x10, 0x610a558c),
                 (0x2400, 0x8, 0x800, 0x610a559c),
                 (0x2c00, 0x10, 0x400, 0x610a55a4)],
    0x610a1f20: [(0x0, 0x0, 0x0, 0x610a8c3c),
                 (0x0, 0x8, 0x900, 0x610a8c44),
                 (0x900, 0x10, 0x10, 0x610a8c4c),
                 (0x2400, 0x8, 0x800, 0x610a8c5c),
                 (0x2c00, 0x10, 0x400, 0x610a8c64)],
    0x610a1f30: [(0x0, 0x0, 0x0, 0x610b0d60),
                 (0x0, 0x8, 0x13a0, 0x610b0d68),
                 (0x13a0, 0x10, 0x10, 0x610b0d70),
                 (0x2400, 0x8, 0x800, 0x610b0d80),
                 (0x2c00, 0x10, 0x400, 0x610b0d88)],
    0x610a1f38: [(0x0, 0x12, 0x20, 0x610b3b74),
                 (0x20, 0x0, 0x0, 0x610b3b88)],
    0x610a1f40: [(0x0, 0x12, 0x20, 0x610b3bb8),
                 (0x20, 0x0, 0x0, 0x610b3bcc)],
    0x610a1f48: [(0x0, 0x12, 0x20, 0x610b3bfc),
                 (0x20, 0x0, 0x0, 0x610b3c10)],
    0x610a1f50: [(0x0, 0x12, 0x20, 0x610b3c40),
                 (0x20, 0x0, 0x0, 0x610b3c54)],
    0x610a1f58: [(0x20, 0xc6, 0xc6, 0x610b3c84)],
    0x610a1f60: [(0x20, 0xc6, 0xc6, 0x610b3d5c)],
    0x610a1f68: [(0x20, 0xc6, 0xc6, 0x610b3e34)],
    0x610a1f70: [(0x20, 0xc6, 0xc6, 0x610b3f0c)],
}

# Expected entry fields for the 16-entry run (address -> (header, list)).
EXPECTED_TABLE2 = {
    0x610a1ef8: (0x00030100, 0x610a52e8),
    0x610a1f00: (0x00050101, 0x610a5350),
    0x610a1f08: (0x00010300, 0x610a556c),
    0x610a1f10: (0x00050301, 0x610a55b4),
    0x610a1f18: (0x00050400, 0x610a8bec),
    0x610a1f20: (0x00050401, 0x610a8c74),
    0x610a1f28: (0x000b0500, 0x610b0cb0),
    0x610a1f30: (0x00050501, 0x610b0d98),
    0x610a1f38: (0x00020100, 0x610b3b8c),
    0x610a1f40: (0x00020300, 0x610b3bd0),
    0x610a1f48: (0x00020400, 0x610b3c14),
    0x610a1f50: (0x00020500, 0x610b3c58),
    0x610a1f58: (0x00010100, 0x610b3d4c),
    0x610a1f60: (0x00010300, 0x610b3e24),
    0x610a1f68: (0x00010400, 0x610b3efc),
    0x610a1f70: (0x00010500, 0x610b3fd4),
}


ANCHORS = (
    TABLE2_HEAD_BYTES, TABLE2_DSP1345_TAIL, TABLE2_END,
    TABLE1_P0_LOADS[0], TABLE1_P0_LOADS[1], TABLE1_P0_LOADS[2], TABLE1_P0_LOADS[3],
    TABLE1_VTABLE_LOADS[0], TABLE1_VTABLE_LOADS[1],
    TABLE1_VTABLE_LOADS[2], TABLE1_VTABLE_LOADS[3],
    TABLE1_CALLER_FN,
    TABLE2_LOADS[0], TABLE2_LOADS[1], TABLE2_LOADS[2], TABLE2_LOADS[3],
    TABLE2_LOADS[4], TABLE2_LOADS[5], TABLE2_LOADS[6], TABLE2_LOADS[7],
    TABLE2_LOADS[8], TABLE2_LOADS[9], TABLE2_LOADS[10], TABLE2_LOADS[11],
    TABLE2_TAILCALL, TABLE2_SEEDCALL, TABLE2_CTOR_ENTER,
    TABLE2_CTOR, TABLE2_CTOR_VT, TABLE2_CTOR_POOL1, TABLE2_CTOR_POOL2,
    TABLE2_CTOR_POOL3, TABLE2_CTOR_POOL4,
    TABLE1_HEAD_ANCHOR, TABLE1_WAIT_LOAD, TABLE1_WAIT_VT,
    DISPATCH_HEAD, DISPATCH_TESTERAM, DISPATCH_LOGGER,
    VENEER_TESTERAM, VENEER_LOGGER,
    TESTERAM_HEAD, TESTERAM_CALLER_BL,
    UPLOAD_WRAPPER_18, UPLOAD_WRAPPER_1C,
)


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    checks = 0
    for address, expected in ANCHORS:
        got = core.data[core.offset(address):core.offset(address) + len(expected) // 2]
        checks += 1
        if got.hex() != expected:
            problems.append(f'anchor {address:#x}: got {got.hex()}')
    if core.u32(MANAGER_VTABLE_AP + 0x18) != MANAGER_VTABLE_WORDS[0x18]:
        problems.append('manager vtable +0x18 mismatch')
    if core.u32(MANAGER_VTABLE_AP + 0x1c) != MANAGER_VTABLE_WORDS[0x1c]:
        problems.append('manager vtable +0x1c mismatch')
    checks += 2
    if tuple(core.u32(PROGRAM_APERTURE_TABLE + 4 * i) for i in range(7)) \
            != PROGRAM_APERTURE_WORDS:
        problems.append('program aperture table mismatch')
    checks += 1
    return checks, problems


def unpack_header(word):
    return dict(count=(word >> 16) & 0xFF, dsp=(word >> 8) & 0xFF,
                phase=word & 1, high_byte=(word >> 24) & 0xFF)


def decode_table2(core):
    rows = []
    for address, (header, lst) in sorted(EXPECTED_TABLE2.items()):
        fields = unpack_header(header)
        records = [tuple(core.u32(lst + 16 * i + 4 * k) for k in range(4))
                   for i in range(fields['count'])]
        rows.append(dict(address=hex(address), header=hex(header),
                         list=hex(lst), **fields, records=records))
    return rows


def table2_matches(rows):
    for row in rows:
        address = int(row['address'], 16)
        header, lst = EXPECTED_TABLE2[address]
        expected = TABLE2_RECORDS.get(address)
        if expected is not None and list(row['records']) != expected:
            return False
    return True


def table1_matches(core):
    for entry, records in TABLE1_RECORDS.items():
        header = core.u32(entry)
        fields = unpack_header(header)
        if fields['count'] != len(records):
            return False
        lst = core.u32(entry + 4)
        got = [tuple(core.u32(lst + 16 * i + 4 * k) for k in range(4))
               for i in range(len(records))]
        if got != records:
            return False
    return True


def decode_table1(core):
    rows = []
    for address in sorted(TABLE1_RECORDS):
        header = core.u32(address)
        lst = core.u32(address + 4)
        fields = unpack_header(header)
        records = [tuple(core.u32(lst + 16 * i + 4 * k) for k in range(4))
                   for i in range(fields['count'])]
        rows.append(dict(address=hex(address), header=hex(header),
                         list=hex(lst), **fields, records=records))
    return rows


def apertures(rows):
    """Map each record's word0 offset to program (phase 0) or DRAM-IO bank 0
    (phase 1) aperture base for its DSP."""
    out = []
    for row in rows:
        dsp = row['dsp']
        base = (DRAMIO_BANK0[dsp] if row['phase'] else
                PROGRAM_APERTURE_WORDS[dsp])
        ranges = []
        for rec in row['records']:
            word0, length = rec[0], rec[1]
            ranges.append(dict(start=hex(base + word0), length=length))
        out.append(dict(entry=row['address'], dsp=dsp, phase=row['phase'],
                        base=hex(base), ranges=ranges))
    return out


def bl_branch_veneer_scan(core):
    """Capstone-driven scan of every 2-aligned branch plus the committed veneer
    scanner and aligned word-pointer scan, for the whole call chain."""
    import capstone
    from core1_xrefs import veneer_candidates
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB
                     | capstone.CS_MODE_MCLASS)
    targets = {0x1126a6d, 0x11269bb, 0x1126cec, 0x1134c7c, 0x1134cea,
               0x6103f4b2, 0x61080fe1, 0x610293b2, 0x6102a230, 0x6102a608,
               0x1135099, 0x11350a9}
    found = {t: dict(branches=[], veneers=[], words=[]) for t in targets}
    data = core.data
    for off in range(0, len(data) - 4, 2):
        try:
            ins = next(md.disasm(data[off:off + 4], core.address(off)))
        except Exception:
            continue
        if ins.mnemonic in ('b', 'bl', 'blx', 'b.w', 'bl.w') \
                and ins.op_str.startswith('#'):
            try:
                t = int(ins.op_str[1:], 0)
            except ValueError:
                continue
            if t in found:
                found[t]['branches'].append([hex(ins.address), ins.mnemonic])
    for t in targets:
        for region, base in ((core.data[:core.eram_offset], 0x01100000),
                             (core.data[core.eram_offset:], 0x61000000)):
            found[t]['veneers'] += [r['address'] for r in
                                    veneer_candidates(region, base, t)]
        needle = struct.pack('<I', t)
        pos = 0
        while True:
            i = data.find(needle, pos)
            if i < 0:
                break
            found[t]['words'].append(hex(core.address(i)))
            pos = i + 1
    return {hex(t): {k: v if k != 'veneers' else [hex(x) for x in v]
                     for k, v in row.items()} for t, row in found.items()}


def scatter_word(core, address):
    for record in core.scatter():
        if record['destination'] <= address < record['destination'] + record['length']:
            off = core.offset(record['source']) + (address - record['destination'])
            return struct.unpack_from('<I', core.data, off)[0]
    raise ValueError(f'SRAM address not covered by scatter: {address:#x}')


def report(image_path):
    core = load_image(image_path)
    checks, problems = check_anchors(core)
    rows2 = decode_table2(core)
    rows1 = decode_table1(core)
    import hashlib
    ok = (not problems and table2_matches(rows2) and table1_matches(core))
    return dict(ok=ok, sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_checked=checks, anchor_problems=problems,
                table2_entries=rows2, table2_matches=table2_matches(rows2),
                table1_entries=rows1, table1_matches=table1_matches(core),
                table2_apertures=apertures(rows2),
                table1_apertures=apertures(rows1),
                call_chains=bl_branch_veneer_scan(core),
                efct_context_word_0x2009bbf8=hex(scatter_word(core, 0x2009bbf8)),
                manager_cells={hex(c): hex(scatter_word(core, c))
                               for c in (0x20084b8c, 0x20084ba0, 0x20084bb4)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, help='b0c1a.bin (header-stripped)')
    parser.add_argument('--json', action='store_true',
                        help='print the full JSON report')
    args = parser.parse_args()
    result = report(args.image)
    import json
    print(json.dumps(result, indent=1, default=str))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()