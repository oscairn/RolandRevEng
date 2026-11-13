#!/usr/bin/env python3
"""Bound where a wire byte-1 = 0xEF word could be consumed in bmc0 CORE1.

Static, read-only file analysis of the pinned bmc0 MI078 C1A v1.08 CORE1
payload: no device access, no execution, no capture. It extends run 5
(docs/core1-ef-route-study.md) with the two receiving edges that study left
open: the first router's route-0 fallthrough helper 0x01126d2e and the
byte-stream command parser reached from the ASGN router's non-kind-zero high
nibbles at 0x0110d962. It pins every byte-1 dispatch on that chain and shows
which byte-1 values it consumes (0xEF among them) and which it ignores.

This checks run 5's open questions: the helper "not traced this run" and the
parser entry "reachability unresolved". See docs/core1-ef-319-consumers-study.md
and docs/core1-ef-route-study.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

CORE1_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# (address, hex bytes, mnemonic, operand) anchors of the run-6 receiving edges.
# Byte semantics: parser words are (byte0 low nibble) (byte1) (bytes 2..3),
# so wire byte 1 sits at word bits 15:8; the helpers read it at [r0,#1].
ANCHORS = (
    # First router route 0 fallthrough: call the remote-state helper.
    (0x0111ea80, 'ebf791fd', 'bl', '#0x110a5a6'),
    (0x0111ea84, '6846', 'mov', 'r0, sp'),
    (0x0111ea86, '08f052f9', 'bl', '#0x1126d2e'),
    # Remote-state helper 0x01126d2e: byte0 high nibble must be 2, then byte 1
    # selects among 0x80..0x85 (TBB), 0x8e, 0x8f, 0xbc, 0xbd, 0xbe. 0xEF ignored.
    (0x01126d2e, '10b5', 'push', '{r4, lr}'),
    (0x01126d30, '0178', 'ldrb', 'r1, [r0]'),
    (0x01126d32, '0222', 'movs', 'r2, #2'),
    (0x01126d34, 'b2eb111f', 'cmp.w', 'r2, r1, lsr #4'),
    (0x01126d38, '6cd1', 'bne', '#0x1126e14'),
    (0x01126d3a, '4378', 'ldrb', 'r3, [r0, #1]'),
    (0x01126d40, '8e2b', 'cmp', 'r3, #0x8e'),
    (0x01126d4a, 'a3f18003', 'sub.w', 'r3, r3, #0x80'),
    (0x01126d4e, '052b', 'cmp', 'r3, #5'),
    (0x01126d50, '63d2', 'bhs', '#0x1126e1a'),
    (0x01126d52, 'dfe803f0', 'tbb', '[pc, r3]'),
    # TBB table at 0x1126d54: entries for byte1 0x80..0x85.
    (0x01126d54, '03f05b5d2a1c', '.byte', 'helper tbb byte1 0x80..0x85'),
    (0x01126d5c, '8f2b', 'cmp', 'r3, #0x8f'),
    (0x01126d64, 'bc2b', 'cmp', 'r3, #0xbc'),
    (0x01126d68, 'bd2b', 'cmp', 'r3, #0xbd'),
    (0x01126d6c, 'be2b', 'cmp', 'r3, #0xbe'),
    (0x01126d70, '53e0', 'b', '#0x1126e1a'),
    # Helper tail: return code 8.
    (0x01126e1a, 'bde81040', 'pop.w', '{r4, lr}'),
    (0x01126e1e, '0820', 'movs', 'r0, #8'),
    (0x01126e20, 'dbf74eb9', 'b.w', '#0x11020c0'),
    # ASGN router second call site: non-kind-zero byte-0 high nibbles reach the
    # parser; the direct b.w at 0x0110d962's branch census missed this call.
    (0x0110a6b4, '0b28', 'cmp', 'r0, #0xb'),
    (0x0110a6b6, '10a8', 'add', 'r0, sp, #0x40'),
    (0x0110a6b8, '1ad0', 'beq', '#0x110a6f0'),
    (0x0110a6ba, '03f052f9', 'bl', '#0x110d962'),
    (0x0110a6be, '6078', 'ldrb', 'r0, [r4, #1]'),
    # Parser entry 0x0110d962: byte0 low nibble selects, 0xf rejects.
    (0x0110d962, '2de9f84f', 'push.w', '{r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}'),
    (0x0110d966, '0178', 'ldrb', 'r1, [r0]'),
    (0x0110d968, '01f00f07', 'and', 'r7, r1, #0xf'),
    (0x0110d96c, '0f2f', 'cmp', 'r7, #0xf'),
    (0x0110d96e, '80f0a284', 'bhs.w', '#0x110e2b6'),
    (0x0110d972, 'dfe807f0', 'tbb', '[pc, r7]'),
    # Parser TBB table at 0x110d974 (after the tbb halfword).
    (0x0110d974, '07f0f4f38ef4f2f1f0ef0829eeb5f4',
     '.byte', 'parser tbb low nibble 0..14'),
    # Nibble 10 (values 0x00..0x7f): byte1 dispatch chain, byte1 at bits 15:8.
    (0x0110d984, 'e200', 'lsls', 'r2, r4, #3'),
    (0x0110d986, '4278', 'ldrb', 'r2, [r0, #1]'),
    (0x0110d988, '0909', 'lsrs', 'r1, r1, #4'),
    (0x0110d98a, '02f00f05', 'and', 'r5, r2, #0xf'),
    # Nibble 11 (0x80..0x8f): another byte1 chain.
    (0x0110d9c8, '4278', 'ldrb', 'r2, [r0, #1]'),
    (0x0110d9ca, '0909', 'lsrs', 'r1, r1, #4'),
    (0x0110d9cc, '02f00f04', 'and', 'r4, r2, #0xf'),
    # Second-level dispatcher at 0x110dd22: the byte1 compare chain.
    (0x0110dd22, '4178', 'ldrb', 'r1, [r0, #1]'),
    (0x0110dd24, 'a529', 'cmp', 'r1, #0xa5'),
    (0x0110dd26, '77d0', 'beq', '#0x110de18'),
    (0x0110dd28, '23dc', 'bgt', '#0x110dd72'),
    (0x0110dd2a, '9929', 'cmp', 'r1, #0x99'),
    (0x0110dd30, '15dc', 'bgt', '#0x110dd5e'),
    (0x0110dd32, '8029', 'cmp', 'r1, #0x80'),
    (0x0110dd34, '53d0', 'beq', '#0x110ddde'),
    (0x0110dd36, '09dc', 'bgt', '#0x110dd4c'),
    (0x0110dd38, '7629', 'cmp', 'r1, #0x76'),
    (0x0110dd3e, '7729', 'cmp', 'r1, #0x77'),
    (0x0110dd44, '7c29', 'cmp', 'r1, #0x7c'),
    (0x0110dd48, '00f0b5ba', 'b.w', '#0x110e2b6'),
    (0x0110dd4c, '8829', 'cmp', 'r1, #0x88'),
    (0x0110dd50, '8c29', 'cmp', 'r1, #0x8c'),
    (0x0110dd54, '8d29', 'cmp', 'r1, #0x8d'),
    (0x0110dd5e, '9d39', 'subs', 'r1, #0x9d'),
    (0x0110dd60, '0829', 'cmp', 'r1, #8'),
    (0x0110dd66, 'dfe801f0', 'tbb', '[pc, r1]'),
    # The b3..bb sub-chain.
    (0x0110dd72, 'b329', 'cmp', 'r1, #0xb3'),
    (0x0110dd78, 'a1f1a601', 'sub.w', 'r1, r1, #0xa6'),
    (0x0110dd7c, '0d29', 'cmp', 'r1, #0xd'),
    (0x0110dd82, 'dfe801f0', 'tbb', '[pc, r1]'),
    (0x0110dd94, 'b729', 'cmp', 'r1, #0xb7'),
    (0x0110dd9a, 'b429', 'cmp', 'r1, #0xb4'),
    (0x0110dd9e, 'b529', 'cmp', 'r1, #0xb5'),
    (0x0110dda2, 'b629', 'cmp', 'r1, #0xb6'),
    (0x0110dda6, '00f086ba', 'b.w', '#0x110e2b6'),
    (0x0110ddaa, 'ee29', 'cmp', 'r1, #0xee'),
    (0x0110ddac, '00f01682', 'beq.w', '#0x110e1dc'),
    # The 0xEF handler and the chain's terminal reject.
    (0x0110ddb0, 'ef29', 'cmp', 'r1, #0xef'),
    (0x0110ddb2, '00f01e82', 'beq.w', '#0x110e1f2'),
    (0x0110ddb6, '00f07eba', 'b.w', '#0x110e2b6'),
    # The 0xEF body: flag test and guarded 16-iteration hook walk.
    (0x0110e1f2, '4088', 'ldrh', 'r0, [r0, #2]'),
    (0x0110e1f4, '10f4004f', 'tst.w', 'r0, #0x8000'),
    (0x0110e1f8, '5dd0', 'beq', '#0x110e2b6'),
    (0x0110e1fa, '00f0f9fb', 'bl', '#0x110e9f0'),
    (0x0110e1fe, '807a', 'ldrb', 'r0, [r0, #0xa]'),
    (0x0110e200, '0028', 'cmp', 'r0, #0'),
    (0x0110e204, '0025', 'movs', 'r5, #0'),
    (0x0110e206, '6e4e', 'ldr', 'r6, [pc, #0x1b8]'),
    (0x0110e208, '2ad0', 'beq', '#0x110e260'),
    (0x0110e20a, '01f08af9', 'bl', '#0x110f522'),
    (0x0110e20e, '6c4e', 'ldr', 'r6, [pc, #0x1b0]'),
    (0x0110e210, '0025', 'movs', 'r5, #0'),
    (0x0110e214, 'c5eb4510', 'rsb', 'r0, r5, r5, lsl #5'),
    (0x0110e218, '00eb8000', 'add.w', 'r0, r0, r0, lsl #2'),
    (0x0110e21c, '06eb8009', 'add.w', 'sb, r6, r0, lsl #2'),
    (0x0110e220, '56f82000', 'ldr.w', 'r0, [r6, r0, lsl #2]'),
    (0x0110e224, '0169', 'ldr', 'r1, [r0, #0x10]'),
    (0x0110e226, '4846', 'mov', 'r0, sb'),
    (0x0110e228, '8847', 'blx', 'r1'),
    (0x0110e24a, '4846', 'mov', 'r0, sb'),
    (0x0110e24c, 'f6f7f2fd', 'bl', '#0x1104e34'),
    (0x0110e29e, '102d', 'cmp', 'r5, #0x10'),
    # Parser common exit: state store and return.
    (0x0110e2b6, '4748', 'ldr', 'r0, [pc, #0x11c]'),
    (0x0110e2b8, '0770', 'strb', 'r7, [r0]'),
    (0x0110e2ba, 'bde8f88f', 'pop.w', '{r3, r4, r5, r6, r7, r8, sb, sl, fp, pc}'),
    # The 0xEE body for contrast: single destination handler.
    (0x0110e1dc, '8078', 'ldrb', 'r0, [r0, #2]'),
    (0x0110e1de, '00f03f04', 'and', 'r4, r0, #0x3f'),
    (0x0110e1e2, '00f003fc', 'bl', '#0x110e9ec'),
    (0x0110e1e6, '90f90a10', 'ldrsb.w', 'r1, [r0, #0xa]'),
    (0x0110e1ec, 'fff7d2f9', 'bl', '#0x110d594'),
)

# Values the parser chain consumes at byte 1 of a (low nibble 0..2/10/11) word.
PARSER_BYTE1 = (0x76, 0x77, 0x7c, 0x80, 0x88, 0x8c, 0x8d, 0x99,
                0xa5, 0xa6, 0xac, 0xad, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7,
                0xbc, 0xbd, 0xbe, 0xee, 0xef)
# Values the remote-state helper consumes at byte 1 of a (high nibble 2) word.
HELPER_BYTE1 = (0x80, 0x81, 0x82, 0x83, 0x84, 0x85,
                0x8e, 0x8f, 0xbc, 0xbd, 0xbe)


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


def check_tbb_bytes(core):
    """Decode the three dispatch tables this study depends on.

    Takes the TBB instruction addresses; each table base is (insn+4) & ~3.
    """
    def tbb(insn, count):
        base = (insn + 4) & ~3
        offset = core.offset(base)
        return [(base + 2 * core.data[offset + i]) & 0xffffffff
                for i in range(count)]
    return dict(
        helper=tbb(0x01126d52, 6),
        parser=tbb(0x0110d972, 15),
        parser_low1=tbb(0x0110dd66, 8),
        parser_low2=tbb(0x0110dd82, 14))


def report(path):
    core = core1(path)
    anchors = check_anchors(core)
    return dict(payload_sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_match=all(row['match'] for row in anchors),
                anchors=anchors,
                tbb_targets=check_tbb_bytes(core),
                helper_byte1=[f'0x{v:02x}' for v in HELPER_BYTE1],
                parser_byte1=[f'0x{v:02x}' for v in PARSER_BYTE1])


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