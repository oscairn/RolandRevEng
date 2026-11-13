#!/usr/bin/env python3
"""Check the writers of the routing gate floats at routing+0x38+0x678/+0x628.

Static, read-only analysis of the pinned ZENOLOGY arm64 image. Run 8
(docs/routing-2016-owner-study.md) proved that CSimDSP4Routing::VSubProc
(0x413d0) gates its per-pass effect dispatch on two floats in the 0x1b40
working structure at [x8+0x678] (zero forces bypass) and [x8+0x628] (nonzero
enables). This tool closes that run's open question "which coefficient symbols
feed the gate floats": the initializer 0x42e14 (called at 0x41248 straight
after the 0x1b40 allocation) writes each gate float exactly once as the value
slot of a 0x50-stride record (32-bit record key at value_offset-8), and the
routing vtable's record-lookup slot (slot 5 = 0x41380, 8-byte key scan over
[x0+0x38]+0xce0, 0x1ba entries) plus CSimDspMgr::WriteDspCoefFloat (0xfba10,
entering through slot 4 = 0x41334) give the manager the path to rewrite those
same records at runtime.

Anchor classes pinned here:
- constructor tail writes 0x620/0x628/0x670/0x678 in the 0x42e14 initializer;
- the two hard-coded record-lookup helpers in the routing vtable: slot 4 =
  0x41334 (16-byte entry scan, 0xce entries over [x0+0x38], returning
  entry+8) and slot 5 = 0x41380 (8-byte key scan, 0x1ba entries over
  [x0+0x38]+0xce0) — the manager-side interface to the same structure;
- CSimDspMgr::WriteDspCoefFloat (0xfba10) reaches the same floats via
  CSimDSP4Routing vtable slot 4 = 0x41334;
- the full DSP4 chain: ctor 0x410e8 (allocates 0x1b40, calls 0x42e14, copies
  three pointers at +0x1b10/+0x1b20/+0x1b28 into routing+0x40/0x50/0x58 and
  the manager pointer into routing+0x28), core init 0x16bc68, wrapper
  0x165fd8, VProcSync 0x1662a0 -> CSimDSP4_Core::VProcSync 0x16c2e4 ->
  routing vtable slot 4 = 0x413d0;
- CSimDSP5Routing::VSubProc (0x34c244) as the control analog: DSP5 ctor
  0x34bf7c allocates 0x46c8 bytes, the initializer 0x34d690 writes the value
  slots +0x628 and +0x678 inside 0x50-byte tail records (keys 0x4fce and
  0x4d02), and per pass it reads the two CoefSym values directly through the
  manager (0x34c2b8 ldr x10,[x9,#0x3300] -> ldr s0,[x10,#0x28] for +0x628's
  record, #0x8d8 for +0x678's) with no hard-coded gate.

No execution, no device access, no key or ciphertext material.
"""
import argparse
import hashlib
import json
from pathlib import Path

SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'

# (address, hex bytes, mnemonic, operand) — every anchor is byte-exact.
ANCHORS = (
    # Initializer 0x42e14 tail: gate floats written once, at struct offsets.
    (0x0432b0, '1f2006b9', 'str', 'wzr, [x0, #0x620]'),
    (0x0432b4, '09fee7d2', 'mov', 'x9, #0x3ff0000000000000'),
    (0x0432b8, '091403f9', 'str', 'x9, [x0, #0x628]'),
    (0x0432fc, '8af88052', 'mov', 'w10, #0x7c4'),
    (0x043300, '0a7006b9', 'str', 'w10, [x0, #0x670]'),
    (0x043304, '1f3c03f9', 'str', 'xzr, [x0, #0x678]'),
    (0x0442e8, 'c0035fd6', 'ret', ''),
    # Routing ctor 0x410e8: allocate 0x1b40, call 0x42e14, store at +0x38.
    (0x041234, '00688352', 'mov', 'w0, #0x1b40'),
    (0x041238, 'f75c1a94', 'bl', '#0x6d8614'),
    (0x041248, 'f3060094', 'bl', '#0x42e14'),
    (0x04124c, '601e00f9', 'str', 'x0, [x19, #0x38]'),
    # Manager pointer routing+0x28 (pairs x21=mgr, x20=global at +0x28).
    (0x041220, 'b31600f9', 'str', 'x19, [x21, #0x28]'),
    (0x041230, '75d202a9', 'stp', 'x21, x20, [x19, #0x28]'),
    # Routing vtable slots 2/3: hard-coded record searchers (no keys).
    (0x041334, '28604039', 'ldrb', 'w8, [x1, #0x18]'),
    (0x041340, '091c40f9', 'ldr', 'x9, [x0, #0x38]'),
    (0x04134c, 'eb0309aa', 'mov', 'x11, x9'),
    (0x041350, '6c0140b9', 'ldr', 'w12, [x11]'),
    (0x041374, '2851288b', 'add', 'x8, x9, w8, uxtw #4'),
    (0x041378, '00210091', 'add', 'x0, x8, #8'),
    (0x041380, '28404079', 'ldrh', 'w8, [x1, #0x20]'),
    (0x041390, '29813391', 'add', 'x9, x9, #0xce0'),
    (0x0413c4, '284d288b', 'add', 'x8, x9, w8, uxtw #3'),
    (0x0413c8, '00110091', 'add', 'x0, x8, #4'),
    # CSimDspMgr::WriteDspCoefFloat: mgr->0x28 vtable slot 1 -> 0x41334.
    (0x00fba54, '001440f9', 'ldr', 'x0, [x0, #0x28]'),
    (0x00fba60, '080040f9', 'ldr', 'x8, [x0]'),
    (0x00fba64, '080940f9', 'ldr', 'x8, [x8, #0x10]'),
    (0x00fba6c, '400000b4', 'cbz', 'x0, #0xfba74'),
    (0x00fba70, '080000fd', 'str', 'd8, [x0]'),
    # Routing vtable: slot 1 = destructor 0x412fc, slot 4 = 0x41334,
    # slot 5 = 0x41380 (byte offsets 8/0x20/0x28 from 0x9cfd68).
    (0x09cfd70, 'a0fd9c0000000000', '.quad', 'routing vtable slot 1'),
    (0x09cfd88, '3413040000000000', '.quad', 'routing vtable slot 4 = 0x41334'),
    (0x09cfd90, '8013040000000000', '.quad', 'routing vtable slot 5 = 0x41380'),
    # VProcSync -> core VProcSync -> routing vtable slot 4 (byte +0x20).
    (0x1662b4, '0c180094', 'bl', '#0x16c2e4'),
    (0x16c350, '601a41f9', 'ldr', 'x0, [x19, #0x230]'),
    (0x16c354, '080040f9', 'ldr', 'x8, [x0]'),
    (0x16c358, '081140f9', 'ldr', 'x8, [x8, #0x20]'),
    (0x16c364, '00013fd6', 'blr', 'x8'),
    # Core init 0x16bc68 and wrapper 0x165fd8 chain (run 8).
    (0x16bca8, '00148052', 'mov', 'w0, #0xa0'),
    (0x16bcb8, '012140f9', 'ldr', 'x1, [x8, #0x40]'),
    (0x16bcc0, '7255fb97', 'bl', '#0x41288'),
    (0x16bcc4, '741a01f9', 'str', 'x20, [x19, #0x230]'),
    (0x165ff4, '1d170094', 'bl', '#0x16bc68'),
    (0x165ff8, '600e40f9', 'ldr', 'x0, [x19, #0x18]'),
    (0x165ffc, '89b00494', 'bl', '#0x292220'),
    (0x16614c, 'e32e0994', 'bl', '#0x3b1cd8'),
    # DSP4 VSubProc head: global at 0x9c8000+0x480 -> deref; coefficient
    # records at struct+0xc78 (fmadd gain) and +0x978 (fnmsub).
    (0x041404, '284c00f0', 'adrp', 'x8, #0x9c8000'),
    (0x041408, '084142f9', 'ldr', 'x8, [x8, #0x480]'),
    (0x04140c, '080140f9', 'ldr', 'x8, [x8]'),
    (0x041414, '080440f9', 'ldr', 'x8, [x0, #8]'),
    (0x04144c, '013d46fd', 'ldr', 'd1, [x8, #0xc78]'),
    (0x041448, '081c40f9', 'ldr', 'x8, [x0, #0x38]'),
    # DSP5 ctor 0x34bf7c: allocate 0x46c8, call initializer 0x34d690,
    # store at routing+0x38; manager pair at +0x28; vtable 0xa520e98.
    (0x34c0b4, 'b31600f9', 'str', 'x19, [x21, #0x28]'),
    (0x34c0b8, '283800d0', 'adrp', 'x8, #0xa52000'),
    (0x34c0bc, '08613a91', 'add', 'x8, x8, #0xe98'),
    (0x34c0c0, '680200f9', 'str', 'x8, [x19]'),
    (0x34c0c4, '75d202a9', 'stp', 'x21, x20, [x19, #0x28]'),
    (0x34c0c8, '00d98852', 'mov', 'w0, #0x46c8'),
    (0x34c0cc, '52310e94', 'bl', '#0x6d8614'),
    (0x34c0dc, '6d050094', 'bl', '#0x34d690'),
    (0x34c0e0, '601e00f9', 'str', 'x0, [x19, #0x38]'),
    # CSimDSP5_Core::Init 0x292220 (run 8) reaches ctor 0x34c0f8.
    (0x292270, '012540f9', 'ldr', 'x1, [x8, #0x48]'),
    (0x292278, 'a0e70294', 'bl', '#0x34c0f8'),
    (0x29227c, '741a01f9', 'str', 'x20, [x19, #0x230]'),
    # DSP5 initializer tail records: key 0x4fce at +0x620 pairs with value
    # slot +0x628; key 0x4d02 at +0x670 pairs with value slot +0x678
    # (0x50-byte record stride: key at +0, 64-bit value at +8).
    (0x034db94, 'c9f98952', 'mov', 'w9, #0x4fce'),
    (0x034db98, '092006b9', 'str', 'w9, [x0, #0x620]'),
    (0x034db9c, '081403f9', 'str', 'x8, [x0, #0x628]'),
    (0x034dbd0, '49a08952', 'mov', 'w9, #0x4d02'),
    (0x034dbd4, '097006b9', 'str', 'w9, [x0, #0x670]'),
    (0x034dbd8, '083c03f9', 'str', 'x8, [x0, #0x678]'),
    # DSP5 VSubProc head: global 0x9c8000+0x480 -> deref -> str [sp,#0x58];
    # reads the two gate CoefSym records directly through the manager.
    (0x034c26c, 'e8330090', 'adrp', 'x8, #0x9c8000'),
    (0x034c270, '084142f9', 'ldr', 'x8, [x8, #0x480]'),
    (0x034c274, '080140f9', 'ldr', 'x8, [x8]'),
    (0x034c278, 'e82f00f9', 'str', 'x8, [sp, #0x58]'),
    (0x034c27c, 'f40300aa', 'mov', 'x20, x0'),
    (0x034c2b4, '090040fd', 'ldr', 'd9, [x0]'),
    (0x034c2b8, '2a8159f9', 'ldr', 'x10, [x9, #0x3300]'),
    (0x034c2bc, '402940bd', 'ldr', 's0, [x10, #0x28]'),
    (0x034c2c0, '00c0221e', 'fcvt', 'd0, s0'),
    (0x034c2c4, '216d44fd', 'ldr', 'd1, [x9, #0x8d8]'),
    # DSP5 per-effect dispatch: routing+0x28 -> +8 -> +0x60 -> +0x28 -> vtable
    # byte 0x20 (slot 4).
    (0x034c890, '681640f9', 'ldr', 'x8, [x19, #0x28]'),
    (0x034c894, '080540f9', 'ldr', 'x8, [x8, #8]'),
    (0x034c898, '083140f9', 'ldr', 'x8, [x8, #0x60]'),
    (0x034c89c, '001540f9', 'ldr', 'x0, [x8, #0x28]'),
    (0x034c8a0, '080040f9', 'ldr', 'x8, [x0]'),
    (0x034c8a4, '081140f9', 'ldr', 'x8, [x8, #0x20]'),
    (0x034c8b0, '00013fd6', 'blr', 'x8'),
    # DSP5 in-loop gate: [x21] +0x638 scaled/compared per sub-block.
    (0x034cd24, '010d40fd', 'ldr', 'd1, [x8, #0x18]'),
    (0x034cd28, 'a90240f9', 'ldr', 'x9, [x21]'),
    (0x034cd2c, '221d43fd', 'ldr', 'd2, [x9, #0x638]'),
    (0x034cd38, '6820601e', 'fcmp', 'd3, #0.0'),
    (0x034cd44, '2820601e', 'fcmp', 'd1, #0.0'),
    # DSP4 slot stores and gate/dispatch (run 8 re-pinned here).
    (0x041c14, '033d43fd', 'ldr', 'd3, [x8, #0x678]'),
    (0x041c18, '6820601e', 'fcmp', 'd3, #0.0'),
    (0x041c20, '031543fd', 'ldr', 'd3, [x8, #0x628]'),
    (0x041c28, 'e8079f1a', 'cset', 'w8, ne'),
    (0x041c30, '08008052', 'mov', 'w8, #0'),
    (0x041cac, 'a8010036', 'tbz', 'w8, #0, #0x41ce0'),
    (0x041cb8, '681640f9', 'ldr', 'x8, [x19, #0x28]'),
    (0x041cbc, '080540f9', 'ldr', 'x8, [x8, #8]'),
    (0x041cc0, '082940f9', 'ldr', 'x8, [x8, #0x50]'),
    (0x041cc4, '001540f9', 'ldr', 'x0, [x8, #0x28]'),
    (0x041cd8, '00013fd6', 'blr', 'x8'),
    (0x0a76210, '0c483e00', '.quad', 'FZ vtable slot 4 = 0x3e480c'),
)

# The gate floats, their initializing records, and per-core shapes. Both
# cores use 0x50-byte records in the initializer tail: 32-bit record key at
# +0, 64-bit value at +8. The VSubProc gates read the value slots directly
# (absolute offsets 0x628/0x678 of the big struct).
GATE_DEFAULTS = {
    'DSP4': {'struct_size': 0x1b40, 'enable_offset': 0x628, 'bypass_offset': 0x678,
             'initializer': 0x42e14,
             'enable_key': 0x0000, 'bypass_key': 0x07c4,
             'enable_default': 1.0, 'bypass_default': 0.0,
             'record_stride': 0x50, 'enable_write': 0x432b8,
             'bypass_write': 0x43304},
    'DSP5': {'struct_size': 0x46c8, 'enable_offset': 0x628, 'bypass_offset': 0x678,
             'initializer': 0x34d690,
             'enable_key': 0x4fce, 'bypass_key': 0x4d02,
             'enable_default': 1.0, 'bypass_default': 0.0,
             'record_stride': 0x50, 'enable_write': 0x34db9c,
             'bypass_write': 0x34dbd8},
}


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


def scan_struct_writers(data, start, length, offsets):
    """Find str x/w/d/q, [xN, #off] with plain offsets inside [start, start+length).

    Returns {offset: [address, ...]} for the requested byte offsets. Only
    unscaled-unsigned-offset stores are modeled; the checked initializers use
    them exclusively for the gate offsets, which is what the anchors pin.
    """
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    hits = {off: [] for off in offsets}
    code = data[start:start + length]
    for ins in md.disasm(code, start):
        if ins.mnemonic != 'str':
            continue
        # op_str like 'd1, [x12]' / 'x9, [x0, #0x628]' — plain offsets only.
        mem = ins.op_str[ins.op_str.index('[') + 1 : ins.op_str.index(']')]
        pieces = [p.strip() for p in mem.split(',')]
        if len(pieces) != 2 or not pieces[1].startswith('#'):
            continue
        try:
            off = int(pieces[1].lstrip('#'), 0)
        except ValueError:
            continue
        if off in hits:
            hits[off].append(ins.address)
    return hits


def report(path):
    data = load_image(path)
    rows, anchor_problems = check_anchors(data)
    # The initializer ranges: DSP4 0x42e14..0x4439c, DSP5 0x34d690..0x351808.
    dsp4_writers = scan_struct_writers(data, 0x42e14, 0x4439c - 0x42e14,
                                        (0x628, 0x678))
    dsp5_writers = scan_struct_writers(data, 0x34d690, 0x351808 - 0x34d690,
                                        (0x628, 0x678))
    result = {
        'image': str(path), 'sha256': SHA256,
        'anchors_checked': len(rows), 'anchor_problems': anchor_problems,
        'gates': {
            'DSP4': {
                **GATE_DEFAULTS['DSP4'],
                'initializer_single_writes': {
                    hex(off): [hex(a) for a in addrs]
                    for off, addrs in dsp4_writers.items()},
            },
            'DSP5': {
                **GATE_DEFAULTS['DSP5'],
                'initializer_single_writes': {
                    hex(off): [hex(a) for a in addrs]
                    for off, addrs in dsp5_writers.items()},
            },
        },
        'owner': 'CSimDSP4Routing::VSubProc 0x413d0 (+ CSimDSP5Routing 0x34c244)',
        'writer_chain': ('initializer 0x42e14 (DSP4, key 0x0000/0x07c4) and '
                         'initializer 0x34d690 (DSP5, record keys 0x4fce/0x4d02) '
                         'write +0x628=1.0 and +0x678=0.0 once each; '
                         'CSimDspMgr::WriteDspCoefFloat 0xfba10 reaches the same '
                         'floats through routing vtable slot 4 = 0x41334 (DSP4)'),
    }
    ok = not anchor_problems
    result.setdefault('writer_problems', [])
    for core, gate, writers in (('DSP4', GATE_DEFAULTS['DSP4'], dsp4_writers),
                                ('DSP5', GATE_DEFAULTS['DSP5'], dsp5_writers)):
        expected = {'enable': gate['enable_offset'], 'bypass': gate['bypass_offset']}
        for name, off in expected.items():
            addrs = writers[off]
            # Exactly one write in each initializer, at the pinned address.
            if addrs != [gate[f'{name}_write']]:
                ok = False
                result['writer_problems'].append(
                    f'{core} initializer: {name} ({off:#x}) written at '
                    f'{[hex(a) for a in addrs]}, expected '
                    f'{gate[f"{name}_write"]:#x}')
    result['ok'] = ok
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='machine output')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    import os
    base = Path(os.environ.get('BMC_CORPUS_DIR', root / 'local'))
    path = base / 'zen_arm64'
    result = report(path)
    print(json.dumps(result, indent=2 if args.json else None, sort_keys=True))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()