#!/usr/bin/env python3
"""Bind the CORE1 per-DSP flag register path (CBmcDspDrv::SetDspFlag family).

Pins the driver, its two manager wrappers, the global mask helpers, the veneer
and boot constants, and the 0x4110X318 port table; models the packed control
words; and censuses direct/veneer/word callers of every entry point.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# --- Anchors: (address, expected hex bytes) ---------------------------------

ANCHORS = (
    # Driver CBmcDspDrv::SetDspFlag(int dsp, unsigned char flag,
    #                               eDSP_EVENT_REF_TYPE event) at 0x112f4ba.
    (0x112f4ba, '70b5' '1446' '0d46' '0646' '0728'),
    (0x112f4c4, '06db'),                                # dsp>=7 -> assertion
    (0x112f4c6, 'bde87040' 'dba2' 'd021' 'db48'),       # pop + assertion call
    (0x112f4ce, 'db48'),                                # literal at 0x112f83c
    (0x112f4d4, '35f07f00' '04d0'),                     # flag>0x7f check (bics)
    (0x112f4e4, '092c' '06d3'),                         # event>=9 bound
    (0x112f4f6, 'd249' '05f07f00' '40ea0470' '51f82610' '0860' '70bd'),
    # Global OR-set helper 0x112f4a6 and reader 0x112f4b4.
    (0x112f4a6, 'e049' 'ca68' '1043' 'c860' 'e149' '4860' '7047'),
    (0x112f4b4, 'dc48' 'c068' '7047'),
    # Manager wrappers: CBmcDspMgr::SetDspFlag(unsigned char, bool) and
    # CBmcDspMgr::SetDspFlagBit(unsigned char, bool, bool).
    (0x1131bc6, '8368' 'd3f800c0' 'bcf1070f' '04db'),
    (0x1131bdc, '31f07f0c' '04d0'),                     # flag>0x7f assertion gate
    (0x1131bec, '0173' '002a' '14bf' '0222' '0822' '1868' 'fdf75fbc'),
    (0x1131bfc, '30b4' 'd0f808c0' 'dcf80040' '072c' '05db'),
    (0x1131c26, '0124' '04fa01f1' '002a' '027b' '14bf' '1143' '22ea0101'
                '0173' '002b' '14bf' '0222' '0822' 'c9b2' 'dcf80000' '30bc'
                'fdf736bc'),
    (0x1131c16, '0729' '05d3'),   # SetDspFlagBit bit<7 bound
    # Manager vtable word for the global-set thunk (byte 0x8).
    (0x61176484, struct.pack('<I', 0x1131bbd).hex()),
    # Manager vtable slots (address point 0x6117647c).
    (0x6117647c, struct.pack('<8I', 0x1135095, 0x1135189, 0x1131bbd,
                             0x1131bc3, 0x1131bc7, 0x1131bfd, 0x1135099,
                             0x11350a9).hex()),
    # Thunks to the global helpers.
    (0x1131bbe, 'fdf772bc'),        # b.w 0x112f4a6 (global OR-set, r0 = r1)
    (0x1131bc2, 'fdf777bc'),        # b.w 0x112f4b4 (global reader)
    # Veneer cell to the global setter and the boot routine's call with 0x45c5.
    (0x61076aa0, '4ff2a74c' 'c0f2121c' '6047'),
    (0x610016be, '44f2c550' '75f0edf9'),
    # The five boot SetExeMode call sites (run 11) — their immediate tuples.
    (0x610016d0, '0022' '0323' '0221' '1046' '75f0e7f9'),
    (0x610016dc, '0022' '0323' '1146' '0120' '75f0e1f9'),
    (0x610016e8, '0221' '0323' '0022' '0846' '75f0dbf9'),
    (0x610016f4, '0323' '0022' '1146' '1846' '75f0d5f9'),
    (0x61001700, '0323' '0022' '0221' 'bde81040' '0620' '75f0cdb9'),
    # Debug/verify helper family call sites (r0 = event<<28 single bits).
    (0x6102d704, '4ff08060' '49f0caf9'),
    (0x6102d75e, '4ff00070' '49f09df9'),
    (0x6102d89c, '4ff08070' '49f0fef8'),
    # Literal pools backing the helpers.
    (0x112f828, struct.pack('<I', 0x200847f0).hex()),
    (0x112f834, struct.pack('<I', 0x41100000).hex()),
    (0x112f83c, struct.pack('<I', 0x610b8cfc).hex()),
    (0x1131dac, struct.pack('<I', 0x610b99e5).hex()),
    (0x1131db0, struct.pack('<I', 0x610b9a16).hex()),
    (0x1130c24, struct.pack('<I', 0x113a9ec).hex()),
    (0x112f840, struct.pack('<I', 0x113a9d0).hex()),
    # SetExeMode's argument-bound check (bfc ip,#1,#0xf) and packing.
    (0x1130b9c, '6ff34f0c' 'bcf1000f' '0dd0'),
    # Assertion signature strings.
    (0x610b8cfc, b'void CBmcDspDrv::SetDspFlag(int, unsigned char, '
                 b'eDSP_EVENT_REF_TYPE)\x00'.hex()),
    (0x610b99e5, b'void CBmcDspMgr::SetDspFlag(unsigned char, bool)\x00'.hex()),
    (0x610b9a16, b'void CBmcDspMgr::SetDspFlagBit(unsigned char, bool, '
                 b'bool)\x00'.hex()),
)

DRIVER = 0x112f4bb
GLOBAL_SET = 0x112f4a7
GLOBAL_READ = 0x112f4b5
MGR_SET = 0x1131bc7
MGR_SET_BIT = 0x1131bfd
VENEER_GLOBAL_SET = 0x61076aa1
FLAG_PORT_TABLE = 0x113a9d0
EXEC_PORT_TABLE = 0x113a9ec
DMA_STATE = 0x200847f0
GLOBAL_PORT = 0x41100004

# Port table: 0x4110{4..9}318 for dsp 0..5, entry 6 = MDSP 0x41102318
# (stride 0x1000 per DSP, the "X" digit of run 13's 0x4110X318 form).
EXPECTED_FLAG_PORTS = tuple([0x41104318 + dsp * 0x1000 for dsp in range(6)]
                             + [0x41102318])

EXPECTED_CALLERS = {
    'driver': {'bl': [0x1131bf8, 0x1131c4a], 'veneers': [], 'words': []},
    'global_set': {'bl': [0x1131bbe], 'veneers': [0x61076aa0], 'words': []},
    'global_read': {'bl': [0x1131bc2], 'veneers': [], 'words': []},
    'veneer_global_set': {'bl': [0x610016c2, 0x6102d708, 0x6102d762,
                                 0x6102d8a0]},
    'mgr_set': {'bl': [], 'veneers': [], 'words': [0x6117648c]},
    'mgr_set_bit': {'bl': [], 'veneers': [], 'words': [0x61176490]},
}

# Pure model of the driver's packed control word (verified against 0x1130bd4
# for SetExeMode and 0x112f4fc..0x112f504 for SetDspFlag).

def pack_exe_mode(dsp, mode, argument, event):
    """CBmcDspDrv::SetExeMode packing (driver 0x1130b6c), bounds from the body:
    dsp<7, mode<3, event<9; DSP5 and (DSP4, mode 2) hit assertion 0x5ce
    unconditionally; otherwise assertion 0x5cf requires argument & 0xfffe == 0;
    packed word = event<<28 | mode<<24 | argument."""
    if not 0 <= dsp < 7:
        raise ValueError('dsp bound')
    if not 0 <= mode < 3:
        raise ValueError('mode bound')
    if not 0 <= event < 9:
        raise ValueError('event bound')
    if dsp == 5 or (dsp == 4 and mode == 2):
        raise ValueError('assertion 0x5ce: DSP5 and DSP4-mode-2 unsupported')
    if (argument & ~1) != 0:
        raise ValueError('assertion 0x5cf: argument must be 0 or 1 '
                         '(bfc #1,#0xf leaves bit 0 only)')
    return (event << 28) | (mode << 24) | argument


def pack_flag(dsp, flag, event):
    """SetDspFlag packing: event<<28 | (flag & 0x7f)."""
    if not 0 <= dsp < 7:
        raise ValueError('dsp bound')
    if not 0 <= flag < 0x80:
        raise ValueError('flag bound')
    if not 0 <= event < 9:
        raise ValueError('event bound')
    return (event << 28) | (flag & 0x7f)


def flag_bit_byte(byte, bit, set_):
    """SetDspFlagBit shadow-byte update: 1<<bit OR'd or BIC'd."""
    if not 0 <= bit < 7:
        raise ValueError('bit bound (cmp r1,#7; blo)')
    mask = 1 << bit
    return (byte | mask) if set_ else (byte & ~mask & 0xff)


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    for address, hex_bytes in ANCHORS:
        expected = bytes.fromhex(hex_bytes)
        try:
            actual = core.data[core.offset(address):
                               core.offset(address) + len(expected)]
        except ValueError:
            problems.append((hex(address), 'not backed by image'))
            continue
        if actual != expected:
            problems.append((hex(address),
                             f'expected {hex_bytes}, got {actual.hex()}'))
    return len(ANCHORS), problems


def bl_callers(core, target):
    from core1_xrefs import branch_candidates
    rows = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        rows += [r['address'] for r in branch_candidates(data, base, target)]
    return sorted(set(rows))


def veneer_callers(core, target):
    from core1_xrefs import veneer_candidates
    rows = []
    for data, base in ((core.data[:core.eram_offset], 0x01100000),
                       (core.data[core.eram_offset:], 0x61000000)):
        rows += [r['address'] for r in veneer_candidates(data, base, target)]
    return sorted(set(rows))


def word_pointer_refs(core, target):
    from core1_rtti import word_refs
    return sorted({core.address(off) for off in word_refs(core.data, target)})


def initial_flag_word(core):
    """Initial value of the DMA-state word at 0x200847f0+0xc from the scatter
    record's compressed initial data."""
    from core1_wait_study import expand_initial_data
    for record in core.scatter():
        if record['destination'] <= DMA_STATE < record['destination'] + record['length']:
            break
    else:
        raise ValueError('no scatter record covers 0x200847f0')
    initial, _ = expand_initial_data(
        core.data[core.offset(record['source']):
                  core.offset(record['source']) + 0x1f44],
        record['length'])
    off = DMA_STATE + 0xc - record['destination']
    return struct.unpack_from('<I', initial, off)[0]


def census(core):
    rows = {
        'driver': dict(target=DRIVER, bl=bl_callers(core, DRIVER),
                       veneers=veneer_callers(core, DRIVER),
                       words=word_pointer_refs(core, DRIVER)),
        'global_set': dict(target=GLOBAL_SET, bl=bl_callers(core, GLOBAL_SET),
                           veneers=veneer_callers(core, GLOBAL_SET),
                           words=word_pointer_refs(core, GLOBAL_SET)),
        'global_read': dict(target=GLOBAL_READ, bl=bl_callers(core, GLOBAL_READ),
                            veneers=veneer_callers(core, GLOBAL_READ),
                            words=word_pointer_refs(core, GLOBAL_READ)),
        'mgr_set': dict(target=MGR_SET, bl=bl_callers(core, MGR_SET),
                        veneers=veneer_callers(core, MGR_SET),
                        words=word_pointer_refs(core, MGR_SET)),
        'mgr_set_bit': dict(target=MGR_SET_BIT, bl=bl_callers(core, MGR_SET_BIT),
                            veneers=veneer_callers(core, MGR_SET_BIT),
                            words=word_pointer_refs(core, MGR_SET_BIT)),
        'veneer_global_set': dict(target=VENEER_GLOBAL_SET,
                                  bl=bl_callers(core, VENEER_GLOBAL_SET)),
    }
    problems = []
    for name, expected in EXPECTED_CALLERS.items():
        got = {k: rows[name][k] for k in expected}
        if got != expected:
            problems.append((name, {k: ([hex(x) for x in got[k]],
                                        [hex(x) for x in expected[k]])
                                    for k in expected if got[k] != expected[k]}))
    return rows, problems


def report(image_path):
    core = load_image(image_path)
    count, problems = check_anchors(core)
    ports = tuple(core.u32(FLAG_PORT_TABLE + 4 * i) for i in range(7))
    if ports != EXPECTED_FLAG_PORTS:
        problems.append(('flag_port_table',
                         [hex(p) for p in ports], [hex(p) for p in EXPECTED_FLAG_PORTS]))
    exec_ports = tuple(core.u32(EXEC_PORT_TABLE + 4 * i) for i in range(7))
    expected_exec = tuple([0x41104310 + dsp * 0x1000 for dsp in range(6)]
                          + [0x41102310])
    if exec_ports != expected_exec:
        problems.append(('exec_port_table', [hex(p) for p in exec_ports]))
    callers, caller_problems = census(core)
    problems += caller_problems
    initial = initial_flag_word(core)
    if initial != 0:
        problems.append(('initial_flag_word_0x200847fc', hex(initial)))
    ok = not problems
    return dict(ok=ok, anchors_checked=count, anchor_problems=problems,
                flag_ports={hex(0x41104318 + d * 0x100000) if d < 6 else
                            '0x41102318': hex(p)
                            for d, p in enumerate(ports)},
                callers={name: {k: ([hex(x) for x in v] if isinstance(v, list)
                                    else hex(v))
                                for k, v in row.items()}
                         for name, row in callers.items()},
                initial_dma_state_plus_c=hex(initial),
                model_checks=dict(
                    pack_flag_event2_flag2=hex(pack_flag(0, 2, 2)),
                    pack_flag_event8_flag8=hex(pack_flag(0, 8, 8)),
                    pack_exe_mode_dsp0_mode2=hex(pack_exe_mode(0, 2, 0, 3)),
                    flag_bit_or_bit1=flag_bit_byte(0, 1, True),
                    flag_bit_bic_bit3=flag_bit_byte(0xff, 3, False)),
                payload_sha256=hashlib.sha256(core.data).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, nargs='?',
                        default=Path(__import__('os').environ.get(
                            'BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = report(args.image)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()