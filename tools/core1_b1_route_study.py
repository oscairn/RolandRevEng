#!/usr/bin/env python3
"""Check whether bmc1 CORE1 mirrors the bmc0 receive route and its byte-1 handling.

Static, read-only file analysis of the pinned bmc1 MI078 C1A v1.08 CORE1
payload (local/b1c1a.bin): no device access, no execution, no capture. It pins
the bmc1 analogs of the bmc0 receive path recovered in runs 5 and 6
(docs/core1-ef-route-study.md, docs/core1-ef-319-consumers-study.md): the
ASGN-analog task 0x110a9e2, the CUMDWRx dispatcher 0x110b7da, the
remote-state helper 0x112a1ce and the byte-stream command parser 0x110f70c,
and checks which wire byte-1 values (0xE1, 0xE2, 0xEF) each consumes or
ignores. It also census-compares 8-bit `cmp rN, #imm` counts with bmc0's
committed scanner results.

This closes the runs-5/6 open question "whether bmc1 mirrors the route". See
docs/core1-b1-route-study.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

B1_SHA256 = 'c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd'
B0_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# (address, hex bytes, mnemonic, operand) anchors of the bmc1 receive path.
ANCHORS = (
    # ASGN-analog task 0x110a9e2: prologue, nibble switch, parser call,
    # kind-zero byte-1 compare, CUMDWRx call, IRQ-clear epilogue.
    (0x0110a9e2, '30b5', 'push', '{r4, r5, lr}'),
    (0x0110aa2a, '9df84000', 'ldrb.w', 'r0, [sp, #0x40]'),
    (0x0110aa2e, '0009', 'lsrs', 'r0, r0, #4'),
    (0x0110aa30, '10d0', 'beq', '#0x110aa54'),
    (0x0110aa32, '0328', 'cmp', 'r0, #3'),
    (0x0110aa34, '09d0', 'beq', '#0x110aa4a'),
    (0x0110aa36, '0728', 'cmp', 'r0, #7'),
    (0x0110aa38, '19d0', 'beq', '#0x110aa6e'),
    (0x0110aa3a, '0b28', 'cmp', 'r0, #0xb'),
    (0x0110aa3c, '10a8', 'add', 'r0, sp, #0x40'),
    (0x0110aa3e, '1ad0', 'beq', '#0x110aa76'),
    (0x0110aa40, '04f064fe', 'bl', '#0x110f70c'),
    (0x0110aa54, '9df84100', 'ldrb.w', 'r0, [sp, #0x41]'),
    (0x0110aa58, '0728', 'cmp', 'r0, #7'),
    (0x0110aa60, '00f0bbfe', 'bl', '#0x110b7da'),
    # CUMDWRx 0x110b7da: same 8-bit command extraction, bmc1 adds command 0x53.
    (0x0110b7da, '10b5', 'push', '{r4, lr}'),
    (0x0110b7dc, 'c1f30722', 'ubfx', 'r2, r1, #8, #8'),
    (0x0110b7e2, '582a', 'cmp', 'r2, #0x58'),
    (0x0110b7e8, '512a', 'cmp', 'r2, #0x51'),
    (0x0110b7ec, '522a', 'cmp', 'r2, #0x52'),
    (0x0110b7f0, '532a', 'cmp', 'r2, #0x53'),
    (0x0110b7f4, '542a', 'cmp', 'r2, #0x54'),
    (0x0110b802, '702a', 'cmp', 'r2, #0x70'),
    (0x0110b806, '742a', 'cmp', 'r2, #0x74'),
    (0x0110b80a, '752a', 'cmp', 'r2, #0x75'),
    (0x0110b80e, '7b2a', 'cmp', 'r2, #0x7b'),
    (0x0110b812, '10bd', 'pop', '{r4, pc}'),
    # Remote-state helper 0x112a1ce: byte-0 high nibble must be 2; byte-1
    # consumed set is 0x80..0x88 (TBB), 0x89, 0x8a, 0x8e, 0x8f, 0x9f;
    # shared tail returns 8.
    (0x0112a1ce, '10b5', 'push', '{r4, lr}'),
    (0x0112a1d0, '0178', 'ldrb', 'r1, [r0]'),
    (0x0112a1d2, '0222', 'movs', 'r2, #2'),
    (0x0112a1d4, 'b2eb111f', 'cmp.w', 'r2, r1, lsr #4'),
    (0x0112a1d8, '1fd1', 'bne', '#0x112a21a'),
    (0x0112a1da, '4378', 'ldrb', 'r3, [r0, #1]'),
    (0x0112a1e0, '892b', 'cmp', 'r3, #0x89'),
    (0x0112a1e6, 'a3f1800c', 'sub.w', 'ip, r3, #0x80'),
    (0x0112a1ec, 'bcf1090f', 'cmp.w', 'ip, #9'),
    (0x0112a1f0, '15d2', 'bhs', '#0x112a21e'),
    (0x0112a1f2, 'dfe80cf0', 'tbb', '[pc, ip]'),
    (0x0112a1f6, 'efeecfbf9ded14aedf', '.byte', 'helper tbb byte1 0x80..0x88'),
    (0x0112a200, '9f2b', 'cmp', 'r3, #0x9f'),
    (0x0112a20a, '8a2b', 'cmp', 'r3, #0x8a'),
    (0x0112a20e, '8e2b', 'cmp', 'r3, #0x8e'),
    (0x0112a216, '8f2b', 'cmp', 'r3, #0x8f'),
    (0x0112a46c, 'bde81040', 'pop.w', '{r4, lr}'),
    (0x0112a470, '0820', 'movs', 'r0, #8'),
    (0x0112a472, 'd6f7b3be', 'b.w', '#0x11011dc'),
    # Parser 0x110f70c: low-nibble TBB with 15 entries, 15 rejects.
    (0x0110f70c, '2de9f04f', 'push.w', '{r4, r5, r6, r7, r8, sb, sl, fp, lr}'),
    (0x0110f716, '0178', 'ldrb', 'r1, [r0]'),
    (0x0110f718, '01f00f09', 'and', 'sb, r1, #0xf'),
    (0x0110f71c, 'b9f10f0f', 'cmp.w', 'sb, #0xf'),
    (0x0110f720, '80f08585', 'bhs.w', '#0x111022e'),
    (0x0110f724, 'dfe809f0', 'tbb', '[pc, sb]'),
    (0x0110f728, 'f8f7a3f8f6f5f4f30835f2c7f8f9f0', '.byte', 'parser tbb low nibble 0..14'),
    # Parser shared byte-1 chain tail: 0xEE and 0xEF both consumed.
    (0x0110fb88, 'ee29', 'cmp', 'r1, #0xee'),
    (0x0110fb8a, '00f0e982', 'beq.w', '#0x1110160'),
    (0x0110fb8e, 'ef29', 'cmp', 'r1, #0xef'),
    (0x0110fb90, '00f0f182', 'beq.w', '#0x1110176'),
    (0x0110fb94, '00f04bbb', 'b.w', '#0x111022e'),
    # The 0xEF body 0x1110176: payload bit 15, singleton getter 0x1110cfc
    # (returns 0x61402164), flag byte +8, optional cleanup 0x11118a4,
    # then the 16-entry pointer-table walk at 0x20084d28.
    (0x01110176, '4088', 'ldrh', 'r0, [r0, #2]'),
    (0x01110178, '10f4004f', 'tst.w', 'r0, #0x8000'),
    (0x0111017c, '57d0', 'beq', '#0x111022e'),
    (0x0111017e, '00f0bdfd', 'bl', '#0x1110cfc'),
    (0x01110182, '007a', 'ldrb', 'r0, [r0, #8]'),
    (0x01110184, '0028', 'cmp', 'r0, #0'),
    (0x0111018e, '01f089fb', 'bl', '#0x11118a4'),
    (0x01110192, '904f', 'ldr', 'r7, [pc, #0x240]'),
    (0x01110196, 'ab20', 'movs', 'r5, #0xab'),
    (0x011101d6, '102d', 'cmp', 'r5, #0x10'),
    (0x011101da, '28e0', 'b', '#0x111022e'),
    # Singleton getter and its object literal.
    (0x01110cfc, 'f748', 'ldr', 'r0, [pc, #0x3dc]'),
    (0x01110cfe, '7047', 'bx', 'lr'),
    # The 0xEE body 0x1110160 for contrast: single destination, getter 0x1110cf8.
    (0x01110160, '8078', 'ldrb', 'r0, [r0, #2]'),
    (0x01110162, '00f03f04', 'and', 'r4, r0, #0x3f'),
    (0x01110166, '00f0c7fd', 'bl', '#0x1110cf8'),
    (0x01110170, 'fff7f8f8', 'bl', '#0x110f364'),
)

# Byte-1 values the parser chain consumes (decoded from the cmp/TBB skeleton).
PARSER_BYTE1 = (0x76, 0x77, 0x7c, 0x80, 0x88, 0x8c, 0x8d, 0x99,
                0xa5, 0xa6, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xee, 0xef)
# Byte-1 values the remote-state helper consumes.
HELPER_BYTE1 = (0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88,
                0x89, 0x8a, 0x8e, 0x8f, 0x9f)
# Commands the CUMDWRx dispatcher consumes.
CUMDWRX_COMMANDS = (0x51, 0x52, 0x53, 0x54, 0x58, 0x70, 0x74, 0x75, 0x7b)
# Wire byte-1 candidates for the census.
CANDIDATES = (0x02, 0x07, 0x60, 0x61, 0x62, 0x63, 0x64, 0x75,
              0xe0, 0xe1, 0xe2, 0xef)
# Committed bmc0 scanner results (tools/core1_ef_route_study.py on b0c1a.bin),
# for the cross-image comparison table.
B0_CENSUS = {0x02: 736, 0x07: 788, 0x60: 84, 0x61: 20, 0x62: 62, 0x63: 46,
             0x64: 191, 0x75: 11, 0xe0: 1077, 0xe1: 4, 0xe2: 1506, 0xef: 16}


def core1(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    rows = []
    for address, bytehex, mnemonic, operands in ANCHORS:
        offset = core.offset(address)
        size = len(bytehex) // 2
        actual = core.data[offset:offset + size].hex()
        rows.append(dict(address=f'{address:#010x}', expect=bytehex, actual=actual,
                         match=actual == bytehex))
    return rows


def census_immediates(core):
    """Same scanner as tools/core1_ef_route_study.py: 16-bit-aligned Thumb
    format-3 `cmp rN, #imm8` candidates, excluding 32-bit-instruction interiors.
    Literal-pool data can still match; candidates, not proven instructions."""
    counts, sites = {}, []
    regions = ((core.data[:core.eram_offset], 0x01100000),
               (core.data[core.eram_offset:], 0x61000000))
    for data, base in regions:
        for offset in range(0, len(data) - 1, 2):
            half = int.from_bytes(data[offset:offset + 2], 'little')
            if (half & 0xf000) != 0x2000 or ((half >> 11) & 3) != 1:
                continue
            if offset >= 2:
                previous = int.from_bytes(data[offset - 2:offset], 'little')
                if (previous & 0xf800) in (0xe800, 0xf000, 0xf800):
                    continue
            imm = half & 0xff
            counts[imm] = counts.get(imm, 0) + 1
            if imm in CANDIDATES:
                register = (half >> 8) & 7
                sites.append(dict(address=f'{base + offset:#010x}',
                                  imm=f'0x{imm:02x}',
                                  instruction=f'cmp r{register}, #{imm:#x}'))
    return counts, sites


def check_value_sets():
    """The derived consumption sets are internally consistent with the anchors."""
    problems = []
    if 0xef not in PARSER_BYTE1 or 0xe1 in PARSER_BYTE1 or 0xe2 in PARSER_BYTE1:
        problems.append('parser set must consume 0xEF, not 0xE1/0xE2')
    if 0xe1 in HELPER_BYTE1 or 0xef in HELPER_BYTE1:
        problems.append('helper set must not consume 0xE1/0xEF')
    if 0xe1 in CUMDWRX_COMMANDS or 0xef in CUMDWRX_COMMANDS:
        problems.append('CUMDWRx set must not consume 0xE1/0xEF')
    if 0x53 not in CUMDWRX_COMMANDS:
        problems.append('bmc1 adds command 0x53')
    return problems


def report(b1_path, b0_path=None):
    core = core1(b1_path)
    anchors = check_anchors(core)
    counts, sites = census_immediates(core)
    b0_counts = {}
    if b0_path is not None:
        b0_core = core1(b0_path)
        b0_counts, _ = census_immediates(b0_core)
    return dict(payload_sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_match=all(row['match'] for row in anchors),
                anchors=anchors,
                value_set_problems=check_value_sets(),
                cmp_immediates={f'0x{k:02x}': v for k, v in sorted(counts.items())},
                b0_cmp_immediates={f'0x{k:02x}': b0_counts.get(k, 0)
                                   for k in sorted(CANDIDATES)},
                candidate_sites=sites)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--b0', type=Path, default=None,
                        help='Optional bmc0 payload for the census comparison')
    args = parser.parse_args()
    result = report(args.image, args.b0)
    if result['payload_sha256'] != B1_SHA256:
        parser.exit(1, f'Unexpected bmc1 payload digest {result["payload_sha256"]}\n')
    if not result['anchors_match']:
        parser.exit(1, 'Anchor mismatch\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()