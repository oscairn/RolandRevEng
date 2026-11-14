#!/usr/bin/env python3
"""Census the bmc0 CORE1 stock program reservations (per-DSP list slots).

Run 13's DRAM-IO decode (tools/core1_dramio_apertures_study.py) pinned five
boot-verify upload objects at 0x61085dc4/0x61085dcc/0x61085dd4/0x61085ddc/
0x61085de4 — eight bytes apart — and run 13's log queued the A2 question:
which per-DSP program slots exist, who owns each, and which are unused in the
stock image. This tool answers it by:

1. byte-pinning the boot verify routine's phase-1 (program) and phase-2
   (DRAM-IO) dispatches: TBB table bytes, the per-DSP object literal pools,
   the manager-cell IT-block dispatch (vtable bytes 0x18/0x1c), the walk
   bounds (cmp r4,#6 / bls — seven slots, DSP0..DSP5 plus MDSP) and the
   count-byte load (ldrb r0,[r6,#2]) that gates the record walk;
2. decoding the five reservation entries: header word
   (count << 16) | (dsp << 8) | phase, list pointer, and 16-byte records
   (word0 aperture offset, word1 length, word2 length repeat, word3 source);
3. checking that no further entry follows (zero words 0x61085dec..0x61085e33)
   and that the manager cells 0x20084b8c/ba0/bb4 are zero in both scatter
   records, i.e. runtime-constructed;
4. decoding the program-aperture table (7 words at 0x0113a954) and computing
   the stock occupancy ranges (aperture base + record offset/length);
5. scanning the whole image for any other word of the reservation-header form
   (count in bits 16..23, dsp in bits 8..15, phase bit 0) followed by a
   plausible list pointer, so a second table cannot hide.

Static, read-only file analysis. No firmware execution, no device access, no
key/ciphertext material.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

# Boot verify routine 0x610010d0 (run 11/12): phase-1 head and dispatch.
PHASE1_TBB_INSN = 0x610010e2
PHASE1_TBB_BYTES = (0x610010e6, '041a061a1a1a0800')
PHASE1_OBJECTS = {0: 0x61085dc4, 2: 0x61085dd4, 6: 0x61085de4}
PHASE1_SKIP = 0x6100111a
WALK_BOUND = (0x6100111c, '062cded9')          # cmp r4,#6 ; bls dispatch head
MANAGER_CELLS = {0: 0x20084b8c, 2: 0x20084ba0, 6: 0x20084bb4}
PHASE1_UPLOAD_VTABLE_BYTE = 0x18
PHASE2_UPLOAD_VTABLE_BYTE = 0x1c
COUNT_LOAD = (0x6100117e, 'b0780025002878dd')  # ldrb r0,[r6,#2] ; ble gate
RECORD_WALK_HEAD = (0x61001186, '706810eb051870d0')
GET_PROG_ADRS_VENEER_BL = (0x61001194, '75f075fc')  # -> 0x61076a82 veneer
PHASE1_LOOP_TAIL = (0x61001278, '641c062c')    # adds r4,#1 ; cmp r4,#6
PHASE2_LOOP_TAIL = (0x61001390, '641c052c')    # adds r4,#1 ; cmp r4,#5
PHASE2_TBB_BYTES = (0x6100112c, '02160400')
PHASE2_OBJECTS = {0: 0x61085dcc, 2: 0x61085ddc}
PHASE2_MDSP_SRAM = 0x20084bb4
PHASE2_SKIP = 0x61001158

OBJECT_POOLS = (0x610014d4, 0x610014d8, 0x610014dc,
                0x610014e0, 0x610014e4, 0x610014e8,
                0x610014ec, 0x610014f0)
OBJECT_POOL_VALUES = {
    0x610014d4: 0x61085dc4, 0x610014d8: 0x61085dd4, 0x610014dc: 0x61085de4,
    0x610014e0: 0x20084b8c, 0x610014e4: 0x20084ba0, 0x610014e8: 0x20084bb4,
    0x610014ec: 0x61085dcc, 0x610014f0: 0x61085ddc,
}

ENTRY_ADDRESSES = (0x61085dc4, 0x61085dcc, 0x61085dd4, 0x61085ddc, 0x61085de4)
ENTRY_AFTER = 0x61085dec          # first word after the last (MDSP) entry
ZERO_TAIL_WORDS = 18              # 0x61085dec..0x61085e33 inclusive

# Program-aperture table GetDspProgAdrs loads (run 13: 0x0113a954).
PROGRAM_APERTURE_TABLE = 0x0113a954
PROGRAM_APERTURE_WORDS = tuple([0x41480000 + dsp * 0x100000 for dsp in range(6)]
                               + [0x41260000])

# Manager-cell constructor 0x6100177c (writes vtable address point and fields).
CTOR = (0x6100177c, '70b5294c2b4d00222560284922612848a16060602046')
CTOR_POOLS = {0x61001824: 0x20084b8c, 0x61001830: 0x6117647c,
              0x61001828: 0x61085dec, 0x6100183c: 0x61085e34,
              0x61001840: 0x61085e7c, 0x6100182c: 0x2009be2c}
CTOR_STRIDES = ((0x610017a0, '1434'), (0x610017c0, '1434'))
MANAGER_VTABLE_ADDRESS_POINT = 0x6117647c

# Expected stock entries: (address, count, dsp, phase, list, records).
EXPECTED_ENTRIES = (
    dict(address=0x61085dc4, count=1, dsp=0, phase=0, list=0x61085db4,
         records=(dict(word0=0, length=0x13e4, length_repeat=0x13e4,
                       word3=0x610849d0),)),
    dict(address=0x61085dcc, count=1, dsp=0, phase=1, list=0x61085ed4,
         records=(dict(word0=0, length=16, length_repeat=16,
                       word3=0x61085ec4),)),
    dict(address=0x61085dd4, count=1, dsp=2, phase=0, list=0x61086bcc,
         records=(dict(word0=0, length=0xce6, length_repeat=0xce6,
                       word3=0x61085ee4),)),
    dict(address=0x61085ddc, count=1, dsp=2, phase=1, list=0x61086bec,
         records=(dict(word0=0, length=16, length_repeat=16,
                       word3=0x61086bdc),)),
    dict(address=0x61085de4, count=1, dsp=6, phase=0, list=0x61093554,
         records=(dict(word0=0, length=0xc956, length_repeat=0xc956,
                       word3=0x61086bfc),)),
)


def load_image(path):
    from core1 import Core1
    return Core1(path)


def pack_header(count, dsp, phase):
    if not 1 <= count <= 0xFF or not 0 <= dsp <= 0xFF or phase not in (0, 1):
        raise ValueError('Reservation header field out of range')
    return (count << 16) | (dsp << 8) | phase


def unpack_header(word):
    return dict(count=(word >> 16) & 0xFF, dsp=(word >> 8) & 0xFF,
                phase=word & 1, high_byte=(word >> 24) & 0xFF)


def check_anchors(core):
    problems = []
    checks = [PHASE1_TBB_BYTES, WALK_BOUND, COUNT_LOAD, RECORD_WALK_HEAD,
              GET_PROG_ADRS_VENEER_BL, PHASE1_LOOP_TAIL, PHASE2_LOOP_TAIL,
              PHASE2_TBB_BYTES, CTOR] + list(CTOR_STRIDES)
    checks += [(address, struct.pack('<I', value).hex())
               for address, value in OBJECT_POOL_VALUES.items()]
    checks += [(address, struct.pack('<I', core.u32(address)).hex())
               for address in ENTRY_ADDRESSES]
    for address, hex_bytes in checks:
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
    return len(checks), problems


def decode_entries(core):
    rows = []
    for expected in EXPECTED_ENTRIES:
        address = expected['address']
        header = core.u32(address)
        fields = unpack_header(header)
        list_pointer = core.u32(address + 4)
        records = []
        for index in range(fields['count']):
            record = list_pointer + 16 * index
            records.append(dict(word0=core.u32(record),
                                length=core.u32(record + 4),
                                length_repeat=core.u32(record + 8),
                                word3=core.u32(record + 0xc)))
        rows.append(dict(address=hex(address), header=hex(header), **fields,
                         list=hex(list_pointer), records=records))
    return rows


def entries_match_expectations(rows):
    for row, expected in zip(rows, EXPECTED_ENTRIES):
        if (row['address'] != hex(expected['address'])
                or row['count'] != expected['count']
                or row['dsp'] != expected['dsp']
                or row['phase'] != expected['phase']
                or row['list'] != hex(expected['list'])
                or len(row['records']) != len(expected['records'])):
            return False
        for got, want in zip(row['records'], expected['records']):
            if any(got[key] != want[key] for key in want):
                return False
    return True


def tbb_targets(core, insn, count):
    """TBB targets: unaligned base insn+4, byte entries scaled by two."""
    base = insn + 4
    offset = core.offset(base)
    return [base + 2 * core.data[offset + i] for i in range(count)]


def word_refs(core, value):
    """Image words equal to `value`."""
    import core1_rtti
    return sorted({core.address(offset)
                   for offset in core1_rtti.word_refs(core.data, value)})


def object_reference_census(core):
    return {hex(address): [hex(a) for a in word_refs(core, address)]
            for address in ENTRY_ADDRESSES}


def header_form_scan(core):
    """Whole-image scan for reservation-header words followed by a plausible
    list pointer (ERAM data or SRAM), so a second table cannot hide."""
    data = core.data
    rows = []
    for dsp in range(7):
        for phase in range(2):
            word = pack_header(1, dsp, phase)
            needle = struct.pack('<I', word)
            offset = 0
            while True:
                index = data.find(needle, offset)
                if index < 0:
                    break
                nxt = struct.unpack_from('<I', data, index + 4)[0]
                if (0x61000000 <= nxt < 0x61180000
                        or 0x20080000 <= nxt < 0x200A0000):
                    rows.append(dict(header=hex(word), address=hex(
                        core.address(index)), list=hex(nxt)))
                offset = index + 1
    return rows


def scatter_word(core, address):
    """Value of an SRAM word in the stock image, via the scatter records."""
    for record in core.scatter():
        if record['destination'] <= address < record['destination'] + record['length']:
            offset = core.offset(record['source']
                                 + (address - record['destination']))
            return struct.unpack_from('<I', core.data, offset)[0]
    raise ValueError(f'SRAM address not covered by scatter: {address:#x}')


def manager_cells_in_image(core):
    return {hex(cell): hex(scatter_word(core, cell))
            for cell in MANAGER_CELLS.values()}


def occupancy(rows):
    """Stock occupancy: per entry, aperture base + record word0/length.
    Phase 0 (program lists) uses the GetDspProgAdrs table at 0x0113a954;
    phase 1 (DRAM-IO) uses the bank-0 aperture base 0x41440000+dsp*0x100000
    (run 13's closed form)."""
    program = {dsp: PROGRAM_APERTURE_WORDS[dsp] for dsp in range(7)}
    dramio = {dsp: 0x41440000 + dsp * 0x100000 for dsp in range(6)}
    ranges = []
    for row in rows:
        for record in row['records']:
            if row['phase'] == 0:
                start = program[row['dsp']] + record['word0']
            else:
                start = dramio[row['dsp']] + record['word0']
            ranges.append(dict(dsp=row['dsp'], phase=row['phase'],
                               start=hex(start), end=hex(start + record['length']),
                               length=record['length']))
    return ranges


def ctor_fields(core):
    """What the manager-cell constructor writes (pools and stores)."""
    return {hex(pool): hex(value) for pool, value in CTOR_POOLS.items()}


def report(image_path):
    core = load_image(image_path)
    anchors_checked, anchor_problems = check_anchors(core)
    phase1 = tbb_targets(core, PHASE1_TBB_INSN, 8)
    rows = decode_entries(core)
    zero_tail = [core.u32(ENTRY_AFTER + 4 * i) for i in range(ZERO_TAIL_WORDS)]
    program_apertures = [core.u32(PROGRAM_APERTURE_TABLE + 4 * i)
                         for i in range(len(PROGRAM_APERTURE_WORDS))]
    refs = object_reference_census(core)
    header_form_hits = header_form_scan(core)
    expected_refs = {hex(0x61085dc4): ['0x610014d4'],
                     hex(0x61085dcc): ['0x610014ec'],
                     hex(0x61085dd4): ['0x610014d8'],
                     hex(0x61085ddc): ['0x610014f0'],
                     hex(0x61085de4): ['0x610014dc']}
    boot_entries_present = all(
        any(hit['address'] == hex(entry['address'])
            and hit['list'] == hex(entry['list'])
            for hit in header_form_hits)
        for entry in EXPECTED_ENTRIES)
    ok = (not anchor_problems
          and entries_match_expectations(rows)
          and not any(zero_tail)
          and phase1[0] == 0x610010ee and phase1[2] == 0x610010f2
          and phase1[6] == 0x610010f6
          and phase1[1] == PHASE1_SKIP and phase1[3] == PHASE1_SKIP
          and phase1[4] == PHASE1_SKIP and phase1[5] == PHASE1_SKIP
          and phase1[7] == 0x610010e6
          and program_apertures == list(PROGRAM_APERTURE_WORDS)
          and all(int(value, 16) == 0
                  for value in manager_cells_in_image(core).values())
          and refs == expected_refs
          and boot_entries_present)
    return dict(ok=ok,
                sha256=hashlib.sha256(core.data).hexdigest(),
                anchors_checked=anchors_checked,
                anchor_problems=anchor_problems,
                phase1_tbb_targets=[hex(t) for t in phase1],
                entries=rows,
                entries_match_expectations=entries_match_expectations(rows),
                zero_tail_after_mdsp_entry=[hex(w) for w in zero_tail],
                program_aperture_table=[hex(w) for w in program_apertures],
                program_aperture_matches_closed_form=(
                    program_apertures == list(PROGRAM_APERTURE_WORDS)),
                object_references=refs,
                header_form_hits_elsewhere=header_form_hits,
                manager_cells_in_image=manager_cells_in_image(core),
                manager_ctor_pools=ctor_fields(core),
                stock_occupancy=occupancy(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', default='local/b0c1a.bin',
                        type=Path)
    parser.add_argument('--json', action='store_true',
                        help='print the JSON report only')
    args = parser.parse_args()
    result = report(args.image)
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()