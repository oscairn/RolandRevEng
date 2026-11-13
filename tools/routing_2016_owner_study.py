#!/usr/bin/env python3
"""Check the native routing context that owns the `2016..2019` writes.

Static, read-only analysis of the pinned ZENOLOGY arm64 image
(local/zen_arm64): no execution, no device access. It pins the owner of the
MFX routing writes that the kernel study attributed to
`CSimDSP4Routing::VSubProc` (0x000413d0, exported), and the chain that calls
it per rendered DSP:

  CEfctPrm::EfctLoadFixedAlg (0x165fd8) calls CSimDSP4_Core::Init (0x16bc68)
  and CSimDSP5_Core::Init (0x292220); each Init allocates its routing object
  (CSimDSP4Routing via 0x41288, CSimDSP5Routing via 0x34c0f8) with
  (CFspDspMgr*, SGlobalObj*) and stores it at core+0x230. Each render pass
  reaches VSubProc virtually through that pointer. Inside VSubProc the four
  routing slots (absolute indices 0x16..0x19 = program operands 2016..2019)
  are written unconditionally; the effect's virtual call at slot 4
  (0x41cd8/0x34c8b0) is gated on two coefficient-backed condition floats.

Anchors are (address, hex bytes, mnemonic, operand) tuples checked byte-exact
against the pinned image. Pure checks (slot arithmetic, condition-decoder
model) run without the corpus; pinned-image checks need BMC_CORPUS_DIR (or
local/) plus capstone. See docs/routing-2016-owner-study.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'

# CSimDSP4Routing::VSubProc 0x413d0: output/input slot stores and dispatch.
ANCHORS = (
    # this->0x38 is the coefficient object; condition floats at 0x678/0x628.
    (0x041448, '081c40f9', 'ldr', 'x8, [x0, #0x38]'),
    (0x041c14, '033d43fd', 'ldr', 'd3, [x8, #0x678]'),
    (0x041c18, '6820601e', 'fcmp', 'd3, #0.0'),
    (0x041c20, '031543fd', 'ldr', 'd3, [x8, #0x628]'),
    (0x041c28, 'e8079f1a', 'cset', 'w8, ne'),
    (0x041c30, '08008052', 'mov', 'w8, #0'),
    # Fallback/main outputs (0x41c40/0x41c50 at absolute 0xf0/0x100) and the
    # four routing slots 0x16..0x19, written unconditionally every call.
    (0x041c54, '0c038052', 'mov', 'w12, #0x18'),
    (0x041c64, '810100fd', 'str', 'd1, [x12]'),
    (0x041c68, '2d038052', 'mov', 'w13, #0x19'),
    (0x041c78, 'a00100fd', 'str', 'd0, [x13]'),
    (0x041c84, 'ce028052', 'mov', 'w14, #0x16'),
    (0x041c94, 'c10100fd', 'str', 'd1, [x14]'),
    (0x041c98, 'ef028052', 'mov', 'w15, #0x17'),
    (0x041ca4, '4f4d2f8b', 'add', 'x15, x10, w15, uxtw #3'),
    (0x041ca8, 'e00100fd', 'str', 'd0, [x15]'),
    # Slot scaling by the 0x48-stride live coefficient record at +0x28.
    (0x041bf4, '0c614df9', 'ldr', 'x12, [x8, #0x1ac0]'),
    (0x041bf8, '842940bd', 'ldr', 's4, [x12, #0x28]'),
    (0x041bfc, '84c0221e', 'fcvt', 'd4, s4'),
    (0x041c7c, '2108621e', 'fmul', 'd1, d1, d2'),
    (0x041c80, '0008621e', 'fmul', 'd0, d0, d2'),
    # Effect dispatch is gated: tbz on the decoded condition word.
    (0x041cac, 'a8010036', 'tbz', 'w8, #0, #0x41ce0'),
    (0x041cb8, '681640f9', 'ldr', 'x8, [x19, #0x28]'),
    (0x041cbc, '080540f9', 'ldr', 'x8, [x8, #8]'),
    (0x041cc0, '082940f9', 'ldr', 'x8, [x8, #0x50]'),
    (0x041cc4, '001540f9', 'ldr', 'x0, [x8, #0x28]'),
    (0x041cc8, '080040f9', 'ldr', 'x8, [x0]'),
    (0x041ccc, '081140f9', 'ldr', 'x8, [x8, #0x20]'),
    (0x041cd8, '00013fd6', 'blr', 'x8'),
    # Post-dispatch read of the output slot 0x18.
    (0x041da8, '0b038052', 'mov', 'w11, #0x18'),
    # Routing ctor 0x410e8: vtable, (mgr, global) pair at +0x28, big struct.
    (0x041104, '684c00d0', 'adrp', 'x8, #0x9cf000'),
    (0x041110, '080400a9', 'stp', 'x8, x1, [x0]'),
    (0x041220, 'b31600f9', 'str', 'x19, [x21, #0x28]'),
    (0x041234, '00688352', 'mov', 'w0, #0x1b40'),
    (0x041238, 'f75c1a94', 'bl', '#0x6d8614'),
    (0x041248, 'f3060094', 'bl', '#0x42e14'),
    (0x04124c, '601e00f9', 'str', 'x0, [x19, #0x38]'),
    # CSimDSP4_Core::Init 0x16bc68: allocate 0xa0, call routing ctor, store
    # at core+0x230.
    (0x16bca8, '00148052', 'mov', 'w0, #0xa0'),
    (0x16bcb4, '680640f9', 'ldr', 'x8, [x19, #8]'),
    (0x16bcb8, '012140f9', 'ldr', 'x1, [x8, #0x40]'),
    (0x16bcbc, '621241f9', 'ldr', 'x2, [x19, #0x220]'),
    (0x16bcc0, '7255fb97', 'bl', '#0x41288'),
    (0x16bcc4, '741a01f9', 'str', 'x20, [x19, #0x230]'),
    # CEfctPrm::EfctLoadFixedAlg 0x165fd8: call both core Inits; the per-effect
    # SIM_MFX_COMP::Init at 0x3b1cd8 runs at the loop tail.
    (0x165ff0, '000840f9', 'ldr', 'x0, [x0, #0x10]'),
    (0x165ff4, '1d170094', 'bl', '#0x16bc68'),
    (0x165ff8, '600e40f9', 'ldr', 'x0, [x19, #0x18]'),
    (0x165ffc, '89b00494', 'bl', '#0x292220'),
    (0x166148, 'e00314aa', 'mov', 'x0, x20'),
    (0x16614c, 'e32e0994', 'bl', '#0x3b1cd8'),
    # CSimDSP5_Core::Init 0x292220: same allocation/store shape.
    (0x292264, 'ec181194', 'bl', '#0x6d8614'),
    (0x292278, 'a0e70294', 'bl', '#0x34c0f8'),
    (0x29227c, '741a01f9', 'str', 'x20, [x19, #0x230]'),
    # CSimDSP5Routing::VSubProc 0x34c244: DSP5's analog uses absolute slots
    # 0x462..0x465 with zeroed fallback outputs 0x464/0x465 and the same
    # vtable-slot-4 dispatch.
    (0x34c76c, '4b8c8052', 'mov', 'w11, #0x462'),
    (0x34c778, '2b4d2b8b', 'add', 'x11, x9, w11, uxtw #3'),
    (0x34c77c, '610100fd', 'str', 'd1, [x11]'),
    (0x34c794, '8d8c8052', 'mov', 'w13, #0x464'),
    (0x34c7a4, 'bf0100f9', 'str', 'xzr, [x13]'),
    (0x34c7a8, 'ae8c8052', 'mov', 'w14, #0x465'),
    (0x34c888, 'ebb303a9', 'stp', 'x11, x12, [sp, #0x38]'),
    (0x34c8a8, 'e1e30091', 'add', 'x1, sp, #0x38'),
    (0x34c8b0, '00013fd6', 'blr', 'x8'),
    # FZ effect vtable: VSubProc 0x3e480c sits at vtable slot 4 (byte 0xa76210,
    # vtable start 0xa761f0), matching the +0x20 slot dispatch.
    (0x0a761f0, '844f3e00', '.quad', 'FZ vtable slot 0 = 0x3e4f84'),
    (0x0a76210, '0c483e00', '.quad', 'FZ vtable slot 4 = 0x3e480c'),
)

# The condition decoder at 0x41c14..c30:
#   if [x8+0x678] == 0.0 -> w8 = 0 (bypass)
#   else w8 = ([x8+0x628] != 0.0)
# Effect dispatch runs only when both condition floats are nonzero.
CONDITION_ADDRS = (0x678, 0x628)


def load_image(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ValueError(f'Expected pinned zen_arm64 {SHA256}, got {digest}')
    return data


def check_anchors(data):
    """Every anchor must decode byte-exact at its address."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    rows, problems = [], []
    for address, hexbytes, mnemonic, operand in ANCHORS:
        raw = bytes.fromhex(hexbytes)
        chunk = data[address:address + len(raw)]
        if chunk != raw:
            problems.append(f'{address:#x}: expected {hexbytes}, got {chunk.hex()}')
            continue
        try:
            if mnemonic == '.quad':
                value = int.from_bytes(raw, 'little')
                if not value:
                    problems.append(f'{address:#x}: .quad must be nonzero')
            else:
                ins = next(md.disasm(raw, address))
                if ins.mnemonic != mnemonic or ins.op_str != operand:
                    problems.append(f'{address:#x}: decoded {ins.mnemonic} {ins.op_str}')
        except StopIteration:
            problems.append(f'{address:#x}: undecodable')
        rows.append((address, hexbytes, mnemonic, operand))
    return rows, problems


def condition_word(value_678, value_628):
    """The two-float gate decoded from 0x41c14..c30."""
    if value_678 == 0.0:
        return 0
    return 1 if value_628 != 0.0 else 0


def check_condition_model():
    cases = (
        ((0.0, 0.0), 0), ((0.0, 1.0), 0),
        ((1.0, 0.0), 0), ((1.0, 1.0), 1), ((-2.5, 1e-30), 1),
    )
    problems = [(values, condition_word(*values), want)
                for values, want in cases if condition_word(*values) != want]
    return problems


def vtable_slot(byte_address, vtable_start):
    """VSubProc slot index within its vtable."""
    if byte_address < vtable_start or (byte_address - vtable_start) % 8:
        raise ValueError(f'{byte_address:#x} not in vtable {vtable_start:#x}')
    return (byte_address - vtable_start) // 8


def check_slots():
    problems = []
    if vtable_slot(0xa76210, 0xa761f0) != 4:
        problems.append('FZ vtable slot must be 4 (dispatch uses +0x20)')
    if 4 * 8 != 0x20:
        problems.append('slot*8 must equal the dispatch offset 0x20')
    return problems


def report(path):
    data = load_image(path)
    rows, anchor_problems = check_anchors(data)
    result = {
        'image': str(path), 'sha256': SHA256,
        'anchors_checked': len(rows), 'anchor_problems': anchor_problems,
        'condition_problems': check_condition_model(),
        'slot_problems': check_slots(),
        'owner': 'CSimDSP4Routing::VSubProc 0x413d0 (+ CSimDSP5Routing 0x34c244)',
        'caller_chain': 'CEfctPrm::EfctLoadFixedAlg 0x165fd8 -> Core Init 0x16bc68/0x292220 -> core+0x230 routing -> virtual vtable slot 4',
    }
    result['ok'] = not (anchor_problems or result['condition_problems']
                        or result['slot_problems'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', default=None,
                        help='pinned zen_arm64 path (default: local/zen_arm64)')
    parser.add_argument('--json', action='store_true', help='machine output')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    import os
    base = Path(os.environ.get('BMC_CORPUS_DIR', root / 'local'))
    path = Path(args.image) if args.image else base / 'zen_arm64'
    result = report(path)
    print(json.dumps(result, indent=2 if args.json else None, sort_keys=True))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()