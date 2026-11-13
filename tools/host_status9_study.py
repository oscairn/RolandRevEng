#!/usr/bin/env python3
"""Locate the pinned mi078 consumer of the measured kind-9/selector-9 status frames.

Static, read-only file analysis of the pinned Fantom-0 v1.08 `mi078` ELF plus
re-framing of the saved unit captures. No device access, no execution.

The 2026-11-12 unit captures show long kind-9 frames from 0xE1 to 0x60 with
selector byte 9 and a 112-byte payload about ten times a second; their contents
were not decoded. This tool verifies that capture shape and pins the static
input-worker dispatch that consumes it: kind 9 with byte 3 = 9 stores the
payload through 0x6c3070 into a gated two-slot 112-byte ring at 0x40a9760,
and readers gated on byte 0x40a9758 consume selected halfwords from it.
See docs/host-status9-study.md.
"""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

HOST_SHA256 = '90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
INPUT_WORKER, PAYLOAD_GETTER, RING_STORE = 0xbe1a50, 0xbe3688, 0x6c3070
GATE_ENABLE, GATE_DISABLE = 0x6c27d8, 0x6c27e8
GATE_READER, SLOT_READER = 0x6c27fc, 0x6c2a50


def text_rows(path):
    """Disassemble the pinned ELF's .text; fail closed on any other build."""
    from elftools.elf.elffile import ELFFile
    import capstone
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != HOST_SHA256:
        raise ValueError('Expected pinned Fantom-0 v1.08 mi078 ELF')
    elf = ELFFile(io.BytesIO(data))
    text = elf.get_section_by_name('.text')
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    return list(md.disasm(text.data(), text['sh_addr']))


def at(rows, address):
    row = {ins.address: ins for ins in rows}.get(address)
    if row is None:
        raise ValueError(f'No instruction at {address:#x}')
    return f'{row.mnemonic} {row.op_str}'.strip()


def ring_writers(rows):
    """Every direct call of the gate enable/disable and the ring store."""
    wanted = {RING_STORE, GATE_ENABLE, GATE_DISABLE}
    found = {}
    for ins in rows:
        if ins.mnemonic == 'bl':
            try:
                target = int(ins.op_str.lstrip('#'), 0)
            except ValueError:
                continue
            if target in wanted:
                found.setdefault(target, []).append(ins.address)
    return found


def static_anchors(path):
    """Verified instruction anchors of the selector-9 path; raises on mismatch."""
    rows = text_rows(path)
    expect = {
        0xbe1ae4: 'ldrb w0, [sp, #0x73]',       # kind 9: selector = byte 3
        0xbe1ae8: 'cmp w0, #0xa',
        0xbe1af4: 'cmp w0, #0xd',
        0xbe1b18: 'cmp w0, #9',                 # selector 9 branch target 0xbe1b20
        0xbe1b20: 'add x0, sp, #0x70',
        0xbe1b24: f'bl #{PAYLOAD_GETTER:#x}',
        0xbe1b34: f'bl #{RING_STORE:#x}',
        0x6c3074: 'add x2, x2, #0x758',        # ring gate/cursor base 0x40a9758
        0x6c3084: 'ldr w0, [x2, #4]',           # cursor
        0x6c308c: 'sub w3, w3, w0',             # new cursor = 1 - old
        0x6c3090: 'str w3, [x2, #4]',           # toggle store
        0x6c30d4: 'ret',
        0x6c27dc: 'mov w1, #1',
        0x6c27e0: 'strb w1, [x0, #0x758]',      # gate enable
        0x6c27ec: 'strb wzr, [x0, #0x758]',     # gate disable
        0x6c2800: 'mov w0, #-0x3c',             # reader: closed-gate result -60
        0x6c2804: 'ldrb w2, [x2, #0x758]',      # reader gate load
        0x6c2a8c: 'ldrsh w0, [x1, #0x5c]',      # slot halfword reader at +0x54
    }
    anchors = {address: at(rows, address) for address in expect}
    mismatches = {a: (want, anchors[a]) for a, want in expect.items()
                  if anchors[a] != want}
    if mismatches:
        raise ValueError(f'Anchor mismatch: {mismatches!r}')
    # The ring store copies exactly 112 bytes: seven ldp/stp pairs of 16.
    store = [ins for ins in rows
             if 0x6c3070 <= ins.address <= 0x6c30d4
             and ins.mnemonic in ('ldp', 'stp')]
    if sum(1 for ins in store if ins.mnemonic == 'ldp') != 7 \
            or sum(1 for ins in store if ins.mnemonic == 'stp') != 7:
        raise ValueError(f'Ring store copy width changed: {store!r}')
    callers = ring_writers(rows)
    return dict(anchors=anchors, callers={f'{k:#x}': [hex(a) for a in v]
                                         for k, v in callers.items()})


def capture_census(capture_dir):
    """Re-frame saved captures; return the kind-9 census per file."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from bmc_ipc import frames
    report = {}
    for path in sorted(Path(capture_dir).glob('*.bin')):
        rows = list(frames(path.read_bytes()))
        kind9 = [r for r in rows if r['kind'] == 9]
        shapes = {(r['byte1'], r['destination'], r['selector']) for r in kind9}
        payloads = [bytes.fromhex(r['payload']) for r in kind9]
        varying = sorted({i for i in range(112) if len({p[i] for p in payloads}) > 1})
        report[path.name] = dict(
            frames=len(rows), kind9=len(kind9), shapes=sorted(shapes),
            payload_lengths=sorted({len(p) for p in payloads}),
            varying_payload_offsets=varying)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host', type=Path, help='Pinned mi078 ELF path')
    parser.add_argument('--captures', type=Path, default=None,
                        help='Directory of saved .bin unit captures')
    args = parser.parse_args()
    report = dict(static=static_anchors(args.host))
    if args.captures:
        report['captures'] = capture_census(args.captures)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()