#!/usr/bin/env python3
"""Check the bmc0 CORE1 receive path for handlers of wire byte 1, especially 0xEF.

Static, read-only file analysis of the pinned bmc0 MI078 C1A v1.08 CORE1
payload: no device access, no execution, no capture. It pins the instruction
anchors of the two recovered ring routers (RXDT callback 0111ea24, ASGN
callback 0110a65c) and the CUMDWRx system-command dispatcher (0110bacc), and
census-compares every 8-bit `cmp rN, #imm` in the image against the wire byte-1
values the host actually sends (0xE1, 0xEF, 0x75, 0x60/0x61/0x62/0x63/0x64,
0x02) plus 0xE2.

This checks the run-4 open question: nothing on the recovered CORE1 receive
route tests a frame's byte 1 against 0xEF (docs/host-ef-settings-study.md), so
which service answers 0xEF remains the missing peer edge. See
docs/core1-ef-route-study.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

CORE1_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# (address, hex bytes, mnemonic, operand) anchors of the recovered receive path.
ANCHORS = (
    # IRQ6 handler tail: first router is 0111ea24; drain epilogue re-enables IRQ6.
    (0x0111ea24, '2de9f041', 'push.w', '{r4, r5, r6, r7, r8, lr}'),
    (0x0111ea44, '9df80000', 'ldrb.w', 'r0, [sp]'),
    (0x0111ea4a, '1028', 'cmp', 'r0, #0x10'),
    # TBB dispatch table bytes at 0x111ea54 (16 route bytes).
    (0x0111ea54, '0847b3b386b3b3b98686bdb3868686f6', '.byte', 'tbb routes 0..15'),
    # Route 0 (kind zero) reads byte 1 and compares 0x07/0xc0/0xc1/0xfe.
    (0x0111ea64, '9df80100', 'ldrb.w', 'r0, [sp, #1]'),
    (0x0111ea68, '0728', 'cmp', 'r0, #7'),
    (0x0111ea72, 'c028', 'cmp', 'r0, #0xc0'),
    (0x0111ea76, 'c128', 'cmp', 'r0, #0xc1'),
    (0x0111ea7a, 'fe28', 'cmp', 'r0, #0xfe'),
    (0x0111ea80, 'ebf791fd', 'bl', '#0x110a5a6'),
    # Route 1 (high nibble 1) forwards the word to both SysEx receiver objects.
    (0x0111eae2, '9b48', 'ldr', 'r0, [pc, #0x26c]'),
    (0x0111eaf2, '00f00f00', 'and', 'r0, r0, #0xf'),
    (0x0111eaf6, '0f28', 'cmp', 'r0, #0xf'),
    (0x0111eafc, 'ebf753fd', 'bl', '#0x110a5a6'),
    (0x0111eb04, '00f002fb', 'bl', '#0x111f10c'),
    # ASGN router (0110a65c) kind zero: byte 1 == 7 special, else CUMDWRx.
    (0x0110a65c, '30b5', 'push', '{r4, r5, lr}'),
    (0x0110a6ce, '9df84100', 'ldrb.w', 'r0, [sp, #0x41]'),
    (0x0110a6d2, '0728', 'cmp', 'r0, #7'),
    (0x0110a6da, '01f0f7f9', 'bl', '#0x110bacc'),
    # CUMDWRx dispatcher: command = (word >> 8) & 0xff, eight commands only.
    (0x0110bacc, '10b5', 'push', '{r4, lr}'),
    (0x0110bace, 'c1f30722', 'ubfx', 'r2, r1, #8, #8'),
    (0x0110bad4, '702a', 'cmp', 'r2, #0x70'),
    (0x0110bada, '512a', 'cmp', 'r2, #0x51'),
    (0x0110bade, '522a', 'cmp', 'r2, #0x52'),
    (0x0110bae2, '542a', 'cmp', 'r2, #0x54'),
    (0x0110bae6, '582a', 'cmp', 'r2, #0x58'),
    (0x0110baf8, '742a', 'cmp', 'r2, #0x74'),
    (0x0110bafc, '752a', 'cmp', 'r2, #0x75'),
    (0x0110bb00, '7b2a', 'cmp', 'r2, #0x7b'),
    (0x0110bb04, '10bd', 'pop', '{r4, pc}'),
    # The byte-1 compare of the debug/service command chain in ITCM (context).
    (0x0110045e, 'ef29', 'cmp', 'r1, #0xef'),
    (0x0110048c, '0020', 'movs', 'r0, #0'),
)

# 8-bit cmp immediates in the whole image equal to wire byte-1 candidates.
CANDIDATES = (0x02, 0x07, 0x60, 0x61, 0x62, 0x63, 0x64, 0x75,
              0xe0, 0xe1, 0xe2, 0xef)


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
    """Candidates: 16-bit-aligned Thumb format-3 `cmp rN, #imm8` in both regions.

    Excludes halfwords that are the second half of a 32-bit instruction (the
    preceding halfword is an e8xx..ffff prefix). Does not otherwise prove that
    each remaining halfword is a decoded standalone instruction: literal-pool
    data can still match, so results are candidates, verified only where the
    study disassembled the surrounding function.
    """
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


def report(path):
    core = core1(path)
    anchors = check_anchors(core)
    counts, sites = census_immediates(core)
    return dict(payload_sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_match=all(row['match'] for row in anchors),
                anchors=anchors,
                cmp_immediates={f'0x{k:02x}': v
                                for k, v in sorted(counts.items())},
                candidate_sites=sites)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    result = report(args.image)
    if result['payload_sha256'] != CORE1_SHA256:
        parser.exit(1, f'Unexpected payload digest {result["payload_sha256"]}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()