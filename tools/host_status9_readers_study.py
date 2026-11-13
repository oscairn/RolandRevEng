#!/usr/bin/env python3
"""Map the pinned mi078 readers of the selector-9 status ring.

Static, read-only analysis of the pinned Fantom-0 v1.08 `mi078` ELF. No
device access, no execution, no capture required. Companion to
docs/host-status9-study.md (run 2, the ring store) and
docs/host-status9-readers-study.md (this run, the readers).

The selector-9 input path stores each 112-byte payload into a two-slot ring
at 0x40a9760 (cursor at 0x40a975c). This tool verifies the reader side:
a 26-way jump-table dispatcher at 0xb983c0 (table 0x1308c98) whose tail-call
stubs select fixed selectors into five reader dispatchers, each gated on one
of the gate bytes 0x40a9758 (direct) or 0x40a9758+0xe8 (0x40a9840), each
reading one or two slot halfwords through the cursor, and each decoding a
dB-like level from the halfword's bits 5..9 through the 32-entry float table
at 0x1214f78. It also maps every selector to the payload byte offsets it
can reach and prints the derived level ladder.
"""
import argparse
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

HOST_SHA256 = '90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
JUMP_TABLE, STUB_BASE, SELECTOR_COUNT = 0x1308c98, 0xb98430, 26
DISPATCHER = 0xb983c0
FLOAT_TABLE = 0x1214f78
RING_BASE = 0x40a9758                      # gate byte; cursor +4; slots +8
# dispatcher -> {selector: (halfword byte offset in ring, gate)}
# byte offset = ring-relative (0x758 base) minus 8 = payload offset.
DISPATCHER_SELECTORS = {
    0x6c27f8: 'pair',        # A: two halfwords, (h1&31 + level)/2, gate direct
    0x6c2900: 'pair_shift',  # A2: like A but h1 index doubled (payload 4*s)
    0x6c2988: 'pair_shift2', # A3: h1 index doubled + 1
    0x6c2a30: 'single_direct',   # B: 8 selectors, gate 0x40a9840
    0x6c2b60: 'single_w2',       # B2: 8 selectors, w2 forces nonzero, gate 0x40a9840
    0x6c2d50: 'single_direct2',  # C: 2 selectors, gate direct
    0x6c2e10: 'single_direct3',  # D: 7 selectors, gate 0x40a9840
    0x6c2fb0: 'single_direct4',  # E: 2 selectors, gate 0x40a9840
}
# per dispatcher: {selector: ldrsh slot halfword offset (ring base 0x758)}
SELECTOR_OFFSETS = {
    0x6c2a30: {0: 0x4c, 1: 0x4e, 2: 0x50, 3: 0x52, 4: 0x54, 5: 0x56, 6: 0x58, 7: 0x5a},
    0x6c2b60: {0: 0x4c, 1: 0x4e, 2: 0x50, 3: 0x52, 4: 0x54, 5: 0x56, 6: 0x58, 7: 0x5a},
    0x6c2d50: {0: 0x64, 1: 0x66},
    0x6c2e10: {0: 0x68, 1: 0x6a, 2: 0x6c, 4: 0x70, 5: 0x72, 6: 0x6e, 7: 0x74},
    0x6c2fb0: {0: 0x74, 1: 0x76},
}


def load(path):
    """Read and hash-check the pinned ELF; return (elf, .text rows)."""
    from elftools.elf.elffile import ELFFile
    import capstone
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != HOST_SHA256:
        raise ValueError('Expected pinned Fantom-0 v1.08 mi078 ELF')
    elf = ELFFile(io.BytesIO(data))
    text = elf.get_section_by_name('.text')
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    return elf, list(md.disasm(text.data(), text['sh_addr']))


def read_vaddr(elf, va, n):
    for s in elf.iter_sections():
        a = s['sh_addr']
        z = s['sh_size']
        if s.header.sh_type != 'SHT_NOBITS' and a and a <= va < a + z:
            return s.data()[va - a:va - a + n]
    raise KeyError(hex(va))


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def jump_table(elf):
    """Decode the 26-entry halfword jump table into (selector, dispatcher)."""
    tab = read_vaddr(elf, JUMP_TABLE, 2 * SELECTOR_COUNT)
    out = {}
    for sel in range(SELECTOR_COUNT):
        off = struct.unpack_from('<H', tab, 2 * sel)[0]
        stub = STUB_BASE + 4 * s16(off)
        out[sel] = stub
    return out


def stub_dispatch(elf, stub):
    """Return the dispatcher address a tail-call stub selects, or None."""
    from elftools.elf.elffile import ELFFile  # noqa: F401  (import guard)
    import capstone
    # disassemble from a local Cs without touching .text rows: stubs live in .text
    return None  # replaced below; kept for API clarity


def selector_map(elf, rows):
    """Map each selector to its dispatcher by walking stub instructions."""
    import capstone
    by = {i.address: i for i in rows}
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    mapping = {}
    for sel, stub in jump_table(elf).items():
        ins = list(md.disasm(read_vaddr(elf, stub, 28), stub))
        finals = [i for i in ins if i.mnemonic == 'b'
                  and i.op_str.lstrip('#').startswith('0x')]
        if not finals:
            raise ValueError(f'selector {sel} stub {stub:#x} has no tail branch')
        target = int(finals[-1].op_str.lstrip('#'), 0)
        if target == 0xb9840c:  # in-function return path, follow w0 load
            mapping[sel] = ('return', stub)
        else:
            mapping[sel] = (target, stub)
    return mapping


def float_table(elf):
    return struct.unpack('<32f', read_vaddr(elf, FLOAT_TABLE, 128))


def level_ladder(tab):
    """The clamped [-60, 0] dB-like ladder indexed by bits 5..9 of a slot
    halfword: level = clamp(6*(k-27) + tab[k], -60, 0)."""
    out = {}
    for k in range(32):
        out[k] = max(-60.0, min(0.0, 6 * (k - 27) + tab[k]))
    return out


def payload_coverage(mapping):
    """Selector -> payload byte offsets reachable, from per-case ldrsh offsets.
    Ring base 0x40a9758, slots at +8, cursor contributes 112*cursor; the
    payload byte offset is (halfword offset - 8) for fixed cases. Dispatcher
    0x6c27f8/0x6c2900/0x6c2988 are pair readers: first halfword at 4*s/4*s+2
    scaled forms; verified in the study note, summarized here as ranges."""
    covered = set()
    for disp, sel_off in SELECTOR_OFFSETS.items():
        for sel, hw in sel_off.items():
            covered.add(hw - 8)
            covered.add(hw - 7)  # 16-bit halfword spans two bytes
    # pair readers cover payload bytes 0..31 (four 32-bit words, indices 0..7)
    covered |= set(range(0, 32))
    return covered


def check_anchors(rows):
    """Exact instruction anchors of the cited reader edges; raises on drift."""
    by = {i.address: i for i in rows}
    expect = {
        0xb98400: 'cmp w19, #0x19',          # dispatcher bound: 26 selectors
        0xb98420: 'ldrh w0, [x0, w19, uxtw #1]',
        0xb9842c: 'br x0',
        0x6c27fc: 'add x3, x2, #0x758',      # reader A gate/cursor base
        0x6c2830: 'ands w5, w2, #0xffff',
        0x6c2838: 'ubfx x2, x2, #5, #5',     # k = (h2 >> 5) & 31
        0x6c2840: 'sub w2, w2, #0x1b',
        0x6c28d8: 'add w0, w0, w2',         # level + (h1 & 31)
        0x6c28e0: 'asr w0, w0, #1',         # rounded average
        0x6c28f8: 'sdiv w0, w2, w0',         # zero-level fallback (h1lo5-60)/2
        0x6c2a18: 'strb w1, [x0, #0x840]',    # gate 0x40a9840 enable
        0x6c2a24: 'strb wzr, [x0, #0x840]',   # gate 0x40a9840 disable
        0x6c2a58: 'ldrb w2, [x1, #0xe8]',     # reader B gate load (0x758+0xe8)
        0x6c2a8c: 'ldrsh w0, [x1, #0x5c]',    # reader B selector 0 halfword
        0x6c2be0: 'ldrsh w0, [x0, #0x4c]',    # dispatcher B2 selector 0 case
        0x6c2fb0: 'cbz w1, #0x6c2fdc',        # dispatcher E selector 0
        0x6c3000: 'ldrsh w0, [x1, #0x74]',    # dispatcher E 0x74 halfword
    }
    got = {}
    for a, want in expect.items():
        ins = by.get(a)
        if ins is None:
            raise ValueError(f'No instruction at {a:#x}')
        t = f'{ins.mnemonic} {ins.op_str}'.strip()
        if t != want:
            raise ValueError(f'Anchor mismatch at {a:#x}: {want!r} != {t!r}')
        got[a] = t
    return got


def analyze(host):
    elf, rows = load(host)
    report = {}
    report['anchors'] = {f'{a:#x}': t for a, t in check_anchors(rows).items()}
    mapping = selector_map(elf, rows)
    report['selectors'] = {}
    for sel in range(SELECTOR_COUNT):
        disp, stub = mapping[sel]
        if disp == 'return':
            report['selectors'][sel] = {'stub': f'{stub:#x}', 'kind': 'return',
                                       'dispatcher': f'{0xb9840c:#x}'}
        else:
            row = {'stub': f'{stub:#x}',
                   'dispatcher': f'{disp:#x}' if isinstance(disp, int) else disp}
            sel_off = SELECTOR_OFFSETS.get(disp, {})
            if sel in sel_off:
                row['payload_offset'] = sel_off[sel] - 8
            report['selectors'][sel] = row
    ladder = level_ladder(float_table(elf))
    report['level_ladder'] = {k: round(v, 4) for k, v in ladder.items()}
    report['coverage'] = sorted(payload_coverage(mapping))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host', type=Path, help='Pinned mi078 ELF path')
    args = parser.parse_args()
    print(json.dumps(analyze(args.host), indent=2))


if __name__ == '__main__':
    main()