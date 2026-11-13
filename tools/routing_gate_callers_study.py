#!/usr/bin/env python3
"""Census the callers of CSimDspMgr::WriteDspCoefFloat (0xfba10), pinned image.

Run 9 (docs/routing-gate-writers-study.md) proved that the two routing gate
floats (struct+0x628 enable, +0x678 bypass) are initialized once by the per-core
initializers as keyed records, and that CSimDspMgr::WriteDspCoefFloat (0xfba10)
can rewrite those records at runtime through the routing object's record-lookup
vtable slot. This tool answers run 9's open question — does the stock
application ever call that write path, and with which keys — by:

1. byte-checking the write/lookup ABI anchors: the 0xfba10 prologue (x0=manager,
   x1=symbol, d0=value; gate byte symbol+0x18; blr [vtable+0x10] with
   (routing, symbol); str d8,[x0] into the returned record+8), both routing
   lookup helpers (0x41334: 0xce x 16-byte key scan over [routing+0x38], wanted
   key u32[[symbol+0x10]+4, returns record+8; 0x41380: 0x1ba x 8-byte key scan
   over [routing+0x38]+0xce0, returns record+4), the DSP4 routing vtable quads
   at 0x9cfd78..0x9cfd98 and the DSP5 quads at 0xa52e98..0xa52eb8, and the four
   gate-record initializer stores;
2. scanning the whole image for direct BLs targeting 0xfba10/0xfba11, aligned
   quads equal to either address, and adrp+add pairs computing either address;
3. finding the virtual call sites that reach 0xfba10 through the manager
   vtable: strict (LDR xS,[xR] from a loaded manager pointer, LDR xT,[xS,#0xc8],
   BLR xT) pattern scan at every 4-byte offset, then attributing each site to
   the manager global 0x9c8480 (adrp x, 0x9c8000; ldr x, [x, #0x480] within
   40 instructions) to name the stock callers.

Static, read-only file analysis. No firmware or plugin execution, no device
access, no key/ciphertext material.
"""
import argparse
import hashlib
import json
from pathlib import Path

SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
WRITE_DSP_COEF_FLOAT = 0xfba10
WRITE_DSP_COEF_FLOAT_THUMB = 0xfba11

# (address, hex bytes, mnemonic, operand) — byte-exact anchors of the write
# path and of the four gate records run 9 pinned.
ANCHORS = (
    # WriteDspCoefFloat 0xfba10: (x0=manager, x1=symbol, d0=value).
    (0x00fba10, 'e923be6d', 'stp', 'd9, d8, [sp, #-0x20]!'),
    (0x00fba1c, '28604039', 'ldrb', 'w8, [x1, #0x18]'),
    (0x00fba20, 'a8020034', 'cbz', 'w8, #0xfba74'),
    (0x00fba54, '001440f9', 'ldr', 'x0, [x0, #0x28]'),
    (0x00fba58, '400100b4', 'cbz', 'x0, #0xfba80'),
    (0x00fba5c, '0840601e', 'fmov', 'd8, d0'),
    (0x00fba60, '080040f9', 'ldr', 'x8, [x0]'),
    (0x00fba64, '080940f9', 'ldr', 'x8, [x8, #0x10]'),
    (0x00fba68, '00013fd6', 'blr', 'x8'),
    (0x00fba6c, '400000b4', 'cbz', 'x0, #0xfba74'),
    (0x00fba70, '080000fd', 'str', 'd8, [x0]'),
    (0x00fba74, 'fd7b41a9', 'ldp', 'x29, x30, [sp, #0x10]'),
    (0x00fba7c, 'c0035fd6', 'ret', ''),
    # DSP4 routing lookup at vtable byte 0x10 (0x41334): 0xce x 16-byte scan.
    (0x041334, '28604039', 'ldrb', 'w8, [x1, #0x18]'),
    (0x041340, '091c40f9', 'ldr', 'x9, [x0, #0x38]'),
    (0x041344, '2a0840f9', 'ldr', 'x10, [x1, #0x10]'),
    (0x041348, '4a0540b9', 'ldr', 'w10, [x10, #4]'),
    (0x041350, '6c0140b9', 'ldr', 'w12, [x11]'),
    (0x041354, '9f010a6b', 'cmp', 'w12, w10'),
    (0x041360, '6b410091', 'add', 'x11, x11, #0x10'),
    (0x041364, '1f3903f1', 'cmp', 'x8, #0xce'),
    (0x041374, '2851288b', 'add', 'x8, x9, w8, uxtw #4'),
    (0x041378, '00210091', 'add', 'x0, x8, #8'),
    (0x04137c, 'c0035fd6', 'ret', ''),
    # DSP4 routing lookup at vtable byte 0x18 (0x41380): 0x1ba x 8-byte scan.
    (0x041380, '28404079', 'ldrh', 'w8, [x1, #0x20]'),
    (0x041390, '29813391', 'add', 'x9, x9, #0xce0'),
    (0x041394, '2a0c40f9', 'ldr', 'x10, [x1, #0x18]'),
    (0x041398, '4a0540b9', 'ldr', 'w10, [x10, #4]'),
    (0x0413b4, '1fe906f1', 'cmp', 'x8, #0x1ba'),
    (0x0413c4, '284d288b', 'add', 'x8, x9, w8, uxtw #3'),
    (0x0413c8, '00110091', 'add', 'x0, x8, #4'),
    (0x0413cc, 'c0035fd6', 'ret', ''),
    # DSP4 routing vtable quads 0x9cfd78..0x9cfd98 (slot bytes 0..0x20).
    (0x09cfd78, 'c412040000000000', '.quad', 'vtable byte 0x00 = 0x412c4'),
    (0x09cfd80, 'fc12040000000000', '.quad', 'vtable byte 0x08 = 0x412fc'),
    (0x09cfd88, '3413040000000000', '.quad', 'vtable byte 0x10 = 0x41334'),
    (0x09cfd90, '8013040000000000', '.quad', 'vtable byte 0x18 = 0x41380'),
    (0x09cfd98, 'd013040000000000', '.quad', 'vtable byte 0x20 = 0x413d0'),
    # DSP4 routing ctor stores the vtable pointer at 0x41224..0x4122c.
    (0x041224, '684c00d0', 'adrp', 'x8, #0x9cf000'),
    (0x041228, '08e13591', 'add', 'x8, x8, #0xd78'),
    (0x04122c, '680200f9', 'str', 'x8, [x19]'),
    # DSP5 routing ctor stores its own vtable pointer 0xa52e98.
    (0x34c0b8, '283800d0', 'adrp', 'x8, #0xa52000'),
    (0x34c0bc, '08613a91', 'add', 'x8, x8, #0xe98'),
    (0x34c0c0, '680200f9', 'str', 'x8, [x19]'),
    # DSP5 routing lookup at its vtable byte 0x10 (0x34c1a8): 0xa9 entries.
    (0x34c1a8, '28604039', 'ldrb', 'w8, [x1, #0x18]'),
    (0x34c1b4, '091c40f9', 'ldr', 'x9, [x0, #0x38]'),
    (0x34c1b8, '2a0840f9', 'ldr', 'x10, [x1, #0x10]'),
    (0x34c1bc, '4a0540b9', 'ldr', 'w10, [x10, #4]'),
    (0x34c1d8, '1fa502f1', 'cmp', 'x8, #0xa9'),
    (0x34c1e8, '2851288b', 'add', 'x8, x9, w8, uxtw #4'),
    (0x34c1ec, '00210091', 'add', 'x0, x8, #8'),
    # DSP5 routing lookup at its vtable byte 0x18 (0x34c1f4): 0x4bb entries.
    (0x34c1f4, '28404079', 'ldrh', 'w8, [x1, #0x20]'),
    (0x34c204, '29412a91', 'add', 'x9, x9, #0xa90'),
    (0x34c208, '2a0c40f9', 'ldr', 'x10, [x1, #0x18]'),
    (0x34c228, '1fed12f1', 'cmp', 'x8, #0x4bb'),
    (0x34c238, '284d288b', 'add', 'x8, x9, w8, uxtw #3'),
    (0x34c23c, '00110091', 'add', 'x0, x8, #4'),
    # The four gate record writes (run 9 anchors), re-pinned here.
    (0x0432b0, '1f2006b9', 'str', 'wzr, [x0, #0x620]'),
    (0x0432b8, '091403f9', 'str', 'x9, [x0, #0x628]'),
    (0x0432fc, '8af88052', 'mov', 'w10, #0x7c4'),
    (0x043300, '0a7006b9', 'str', 'w10, [x0, #0x670]'),
    (0x043304, '1f3c03f9', 'str', 'xzr, [x0, #0x678]'),
    (0x034db94, 'c9f98952', 'mov', 'w9, #0x4fce'),
    (0x034db98, '092006b9', 'str', 'w9, [x0, #0x620]'),
    (0x034db9c, '081403f9', 'str', 'x8, [x0, #0x628]'),
    (0x034dbd0, '49a08952', 'mov', 'w9, #0x4d02'),
    (0x034dbd4, '097006b9', 'str', 'w9, [x0, #0x670]'),
    (0x034dbd8, '083c03f9', 'str', 'x8, [x0, #0x678]'),
    # Parameter-apply function 0x354184: manager-global prologue and the five
    # virtual call sites through vtable byte 0xc8 (the census's expectation).
    (0x3541a4, 'a8330090', 'adrp', 'x8, #0x9c8000'),
    (0x3541a8, '084142f9', 'ldr', 'x8, [x8, #0x480]'),
    (0x3541ac, '080140f9', 'ldr', 'x8, [x8]'),
    (0x354394, '602240a9', 'ldp', 'x0, x8, [x19]'),
    (0x354398, '010940f9', 'ldr', 'x1, [x8, #0x10]'),
    (0x35439c, 'e00740fd', 'ldr', 'd0, [sp, #8]'),
    (0x3543a0, '080040f9', 'ldr', 'x8, [x0]'),
    (0x3543a4, '086540f9', 'ldr', 'x8, [x8, #0xc8]'),
    (0x3543a8, '00013fd6', 'blr', 'x8'),
)

# The four gate record keys run 9 decoded (record keys at struct offsets
# 0x620/0x670 with 64-bit value slots 0x628/0x678).
GATE_KEYS = {
    0x0000: 'DSP4 enable (+0x628)',
    0x07c4: 'DSP4 bypass (+0x678)',
    0x4fce: 'DSP5 enable (+0x628)',
    0x4d02: 'DSP5 bypass (+0x678)',
}

# The five strict virtual-call sites that load the manager global 0x9c8480
# nearby: all inside the parameter-apply function at 0x354184.
EXPECTED_CALL_SITES = [0x354388, 0x3543a0, 0x3543b8, 0x3543d0, 0x3543e8]


def load_image(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ValueError(f'Expected pinned zen_arm64 {SHA256}, got {digest}')
    return data


def check_anchors(data):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    rows, problems = [], []
    for address, hexbytes, mnemonic, operand in ANCHORS:
        raw = bytes.fromhex(hexbytes)
        chunk = data[address:address + len(raw)]
        if chunk != raw:
            problems.append(f'{address:#x}: expected {hexbytes}, got {chunk.hex()}')
            continue
        if mnemonic == '.quad':
            if not int.from_bytes(raw, 'little'):
                problems.append(f'{address:#x}: .quad must be nonzero')
        else:
            ins = next(md.disasm(raw, address), None)
            if ins is None or ins.mnemonic != mnemonic or ins.op_str != operand:
                got = 'undecodable' if ins is None else f'{ins.mnemonic} {ins.op_str}'
                problems.append(f'{address:#x}: decoded {got}')
        rows.append((address, hexbytes, mnemonic, operand))
    return rows, problems


def bl_callers(data, target):
    """Every 4-byte-aligned BL whose encoded target is exactly `target`."""
    hits = []
    for offset in range(0, len(data) - 3, 4):
        word = int.from_bytes(data[offset:offset + 4], 'little')
        if word >> 26 != 0x25:  # BL: 100101 imm26
            continue
        imm = word & 0x3ffffff
        if imm >= 1 << 25:
            imm -= 1 << 26
        if offset + imm * 4 == target:
            hits.append(offset)
    return hits


def aligned_quads(data, *targets):
    return [offset for offset in range(0, len(data) - 7, 8)
            if int.from_bytes(data[offset:offset + 8], 'little') in targets]


def adrp_add_candidates(data, *targets):
    """adrp+add pairs computing exactly one of `targets` (static candidates)."""
    import capstone
    from capstone.arm64_const import ARM64_OP_IMM, ARM64_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    hits = []
    for offset in range(0, len(data) - 7, 4):
        ins = next(md.disasm(data[offset:offset + 8], offset, count=2), None)
        if ins is None or ins.mnemonic != 'adrp':
            continue
        ins2 = next(md.disasm(data[offset + 4:offset + 8], offset + 4, count=1), None)
        if ins2 is None or ins2.mnemonic != 'add':
            continue
        ops = ins2.operands
        if (len(ops) == 3 and ops[0].type == ARM64_OP_REG
                and ops[1].type == ARM64_OP_REG and ops[2].type == ARM64_OP_IMM
                and ins.operands[0].reg == ops[1].reg
                and ins.operands[1].imm + ops[2].imm in targets):
            hits.append(offset)
    return hits


def virtual_call_sites(data, slot_offset):
    """Strict pattern: LDR xS,[xR] (manager pointer load) within the previous
    four instructions, LDR xT,[xS,#slot_offset] at `off`, BLR xT immediately
    after. Returns the list of LDR xS addresses."""
    imm12 = slot_offset >> 3
    hits = []
    for offset in range(0, len(data) - 11, 4):
        w2 = int.from_bytes(data[offset:offset + 4], 'little')
        if (w2 >> 22) != 0b1111100101 or ((w2 >> 10) & 0xfff) != imm12:
            continue
        w3 = int.from_bytes(data[offset + 4:offset + 8], 'little')
        if w3 != 0xd63f0000 | ((w2 & 0x1f) << 5):
            continue
        source = (w2 >> 5) & 0x1f
        for back in range(1, 5):
            w1 = int.from_bytes(data[offset - 4 * back:offset - 4 * back + 4], 'little')
            if ((w1 >> 22) == 0b1111100101 and ((w1 >> 10) & 0xfff) == 0
                    and (w1 & 0x1f) == source):
                hits.append(offset - 4 * back)
                break
    return hits


def manager_global_call_sites(data, strict_sites, lookback=40):
    """Which strict virtual-call sites load the manager global 0x9c8480
    (adrp x, 0x9c8000 then ldr x, [x, #0x480]) within `lookback` instructions
    before the call."""
    manager_sites = []
    for site in strict_sites:
        window_start = max(0, site - lookback * 4)
        found = False
        for offset in range(window_start, site, 4):
            word = int.from_bytes(data[offset:offset + 4], 'little')
            if word >> 24 != 0x90:
                continue
            reg = word & 0x1f
            immlo = (word >> 29) & 3
            immhi = (word >> 5) & 0x7ffff
            imm = (immhi << 2) | immlo
            if imm >= 1 << 20:
                imm -= 1 << 21
            if (offset + imm * 4096) & ~0xfff != 0x9c8000:
                continue
            for step in range(1, lookback):
                other = offset + 4 * step
                if other >= site:
                    break
                w2 = int.from_bytes(data[other:other + 4], 'little')
                if ((w2 >> 22) == 0b1111100101 and ((w2 >> 5) & 0x1f) == reg
                        and ((w2 >> 10) & 0xfff) == 0x480 >> 3):
                    found = True
                    break
            if found:
                break
        if found:
            manager_sites.append(site)
    return manager_sites


def report(path):
    data = load_image(path)
    rows, anchor_problems = check_anchors(data)
    direct_bl = bl_callers(data, WRITE_DSP_COEF_FLOAT)
    direct_bl_thumb = bl_callers(data, WRITE_DSP_COEF_FLOAT_THUMB)
    quads = aligned_quads(data, WRITE_DSP_COEF_FLOAT, WRITE_DSP_COEF_FLOAT_THUMB)
    adrp_add = adrp_add_candidates(data, WRITE_DSP_COEF_FLOAT,
                                   WRITE_DSP_COEF_FLOAT_THUMB)
    strict = virtual_call_sites(data, 0xc8)
    manager_sites = manager_global_call_sites(data, strict)
    manager_quad = [q for q in quads
                    if data[q + 4:q + 8] == b'\x00\x00\x00\x00']
    result = dict(
        image=str(path), sha256=SHA256,
        write_dsp_coef_float=hex(WRITE_DSP_COEF_FLOAT),
        anchors_checked=len(rows), anchor_problems=anchor_problems,
        direct_bl_callers=len(direct_bl) + len(direct_bl_thumb),
        direct_bl_sites=[hex(a) for a in direct_bl + direct_bl_thumb],
        aligned_pointer_quads=[hex(a) for a in quads],
        adrp_add_candidates=[hex(a) for a in adrp_add],
        virtual_call_sites_slot_c8=len(strict),
        virtual_call_site_sample=[hex(a) for a in strict[:12]],
        manager_global_call_sites=[hex(a) for a in manager_sites],
        manager_caller_function=hex(0x354184),
        manager_pointer_table_quad=hex(manager_quad[0]) if manager_quad else None,
        gate_keys=GATE_KEYS,
        gate_key_writers=dict(
            DSP4_enable_store=hex(0x0432b8), DSP4_enable_key_store=hex(0x0432b0),
            DSP4_bypass_key_store=hex(0x043300), DSP4_bypass_store=hex(0x043304),
            DSP5_enable_key_store=hex(0x034db94), DSP5_enable_store=hex(0x034db9c),
            DSP5_bypass_key_store=hex(0x034dbd0), DSP5_bypass_store=hex(0x034dbd8)),
        abi=('WriteDspCoefFloat(x0=manager, x1=symbol, d0=value): checks byte '
             'symbol+0x18 nonzero, calls manager vtable slot at byte 0x10 '
             '(DSP4 0x41334, 0xce x 16-byte key scan over [routing+0x38]) with '
             '(routing, symbol), wanted key u32[[symbol+0x10]+4, returns '
             'record+8, then str d8,[x0]. The manager vtable (ctor 0x41288 '
             'stores quads 0x9cfd78..0x9cfd98: slot bytes 0x0/0x8/0x10/0x18/'
             '0x20 = 0x412c4/0x412fc/0x41334/0x41380/0x413d0) is reached from '
             'the manager global 0x9c8480 (adrp+ldr x8,[x8,#0x480]; ldr x8,[x8] '
             'at 0x41404 and 0x34c26c). 0xfba10 has no direct BL callers; it is '
             'referenced only as a function pointer (aligned quad at 0x9e54d0, '
             'one of a consecutive manager-function-pointer table at 0x9e53f8..), '
             'so all runtime callers enter through the manager vtable slot '
             'reached at vtable byte 0xc8 (strict virtual-call census).'),
        method_note=('caller census is structural: virtual-call sites prove '
                     'reachability of the write path, not execution order, '
                     'task context or runtime values; symbol keys are not '
                     'statically recoverable at the virtual call sites'),
    )
    ok = (not anchor_problems and manager_quad and not direct_bl
          and manager_sites == EXPECTED_CALL_SITES)
    result['ok'] = ok
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
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