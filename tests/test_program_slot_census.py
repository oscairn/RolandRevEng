"""Fail-closed checks for the CORE1 render program-slot census; no device IO."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from program_slot_census import (B1C1A_RESERVATION_RECORDS,
                                 B1C1A_RESERVATION_TABLE, IMAGES,
                                 KNOWN_B0C1A_RESERVATIONS, STUB_PROGRAM,
                                 STUB_RECORD, classify_segment, frame_lists,
                                 stub_record_census, study)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_CORPUS = (CORPUS / 'b0c1a.bin').exists() and (CORPUS / 'b1c1a.bin').exists()


class Stub:
    """Minimal Core1 stand-in with the low/ERAM address split and u32."""

    def __init__(self, data, eram_offset=0x40):
        self.data = bytes(data)
        self.eram_offset = eram_offset

    def address(self, offset):
        if offset < self.eram_offset:
            return 0x01100000 + offset
        return 0x61000000 + offset - self.eram_offset

    def offset(self, address):
        if 0x01100000 <= address < 0x01100000 + self.eram_offset:
            return address - 0x01100000
        if 0x61000000 <= address < 0x61000000 + len(self.data) - self.eram_offset:
            return address - 0x61000000 + self.eram_offset
        raise ValueError(f'Address not backed by image: {address:#x}')

    def u32(self, address):
        import struct
        return struct.unpack_from('<I', self.data, self.offset(address))[0]


class SyntheticTests(unittest.TestCase):
    def test_stub_record_bytes_are_the_pinned_eight(self):
        # Stored record: word f800020b then high half 0001; the six-byte program
        # is its logical stream. Both constants disassembled from real segments.
        self.assertEqual(STUB_RECORD, bytes.fromhex('f800020b00000100'))
        self.assertEqual(STUB_PROGRAM, bytes.fromhex('0b0200f80001'))
        # The stored record's first six bytes, read in storage order, are NOT
        # the logical program: word-swap gives the program bytes.
        from bmc_dsp import swap_words
        self.assertEqual(STUB_PROGRAM, swap_words(STUB_RECORD)[:6])

    def test_classify_segment_shapes(self):
        stub = Stub(STUB_RECORD + b'\0' * 16)
        self.assertEqual(classify_segment(STUB_RECORD, 6), 'stub')
        # Anything else that decodes strictly counts as packet content; a
        # non-decodable odd stream is data. The exact bytes here are real
        # packet bytes dumped from b0c1a segment 0 of list 0x610a1f18.
        packet_bytes = bytes.fromhex('c0f8020c')
        self.assertEqual(classify_segment(packet_bytes, 4), 'packet')
        # A two-byte non-decodable stream: classify needs the padded stored
        # bytes, so pass four stored bytes for a two-byte length.
        self.assertEqual(classify_segment(bytes.fromhex('05000000'), 2), 'data')
        # Stored bytes shorter than the padded length: fail closed.
        with self.assertRaises(ValueError):
            classify_segment(b'\0\0', 4)

    def test_frame_lists_rejects_bad_segment_geometry(self):
        # list header {kind=0, dsp=4, count=1, pad=0, pointer} + one segment
        # {base, length, capacity, source}; source must hold the bytes.
        import struct
        base = 0x40
        header = bytearray(struct.pack('<BBBBI', 0, 4, 1, 0, 0))  # pointer patched below
        segment = bytearray(struct.pack('<4I', 0x4020, 6, 0x1000, 0))  # source patched below
        table_offset = base + len(header) + 16
        record_offset = table_offset + len(segment)
        # Identity ERAM mapping (eram_offset 0): address = 0x61000000 + offset.
        struct.pack_into('<I', header, 4, 0x61000000 + table_offset)
        struct.pack_into('<I', segment, 12, 0x61000000 + record_offset)
        data = bytearray(b'\0' * base + header + b'\0' * 16 + segment + STUB_RECORD)
        stub = Stub(bytes(data), eram_offset=0)
        lists = frame_lists(stub)
        self.assertEqual(len(lists), 1)
        seg_offset = table_offset
        # Break the capacity bound: capacity 0 -> segment skipped, list unframed.
        struct.pack_into('<I', data, seg_offset + 8, 0)
        self.assertEqual(frame_lists(Stub(bytes(data))), [])
        # Odd length: rejected by the length%2 predicate.
        struct.pack_into('<I', data, seg_offset + 4, 5)
        self.assertEqual(frame_lists(Stub(bytes(data))), [])

    def test_stub_record_census_fails_closed_on_shape_changes(self):
        import struct
        stub_only = [4, '0x4020', ['0x1000']]
        # words: {base, 6, capacity, source} then the pinned record at the source.
        # Stub maps offsets < 0x40 to the low region: record at offset 0x10
        # (address 0x01100010), record pointer at offset 0x20.
        words = (struct.pack('<4I', 0x4020, 6, 0x1000, 0x01100010)
                 + STUB_RECORD)
        stub = Stub(words)
        report = stub_record_census(stub, [stub_only])
        self.assertEqual(report[0]['base'], '0x4020')
        self.assertEqual(report[0]['capacity'], '0x1000')
        self.assertEqual(int(report[0]['record'], 16), 0x01100000)
        self.assertEqual(int(report[0]['source'], 16), 0x01100010)
        # Remove the record: must raise.
        stub = Stub(struct.pack('<4I', 0x4020, 6, 0x1000, 0x01100010))
        with self.assertRaises(ValueError):
            stub_record_census(stub, [stub_only])
        # Record present but wrong source bytes: must raise.
        stub = Stub(struct.pack('<4I', 0x4020, 6, 0x1000, 0x01100010)
                    + b'\0' * 8)
        with self.assertRaises(ValueError):
            stub_record_census(stub, [stub_only])
        # Duplicate record: must raise.
        stub = Stub(words * 2)
        with self.assertRaises(ValueError):
            stub_record_census(stub, [stub_only])
        # Multiple capacities pinned on one slot: must raise.
        with self.assertRaises(ValueError):
            stub_record_census(stub, [[4, '0x4020', ['0x1000', '0x700']]])

    def test_reservation_pins_match_the_kernel_abi_table(self):
        # docs/kernel-audio-abi-study.md pins the five FETDRIVE/LINEDRIVE
        # reservations (dsp, base, capacity): 4020/1000, 8040/1000, 9040/1000,
        # a040/1000 on dsps 4,5,5,5 and 3020/1800 on dsp 1.
        self.assertEqual(KNOWN_B0C1A_RESERVATIONS,
                         ((4, 0x4020, 0x1000), (5, 0x8040, 0x1000),
                          (5, 0x9040, 0x1000), (5, 0xa040, 0x1000),
                          (1, 0x3020, 0x1800)))
        self.assertEqual(B1C1A_RESERVATION_RECORDS, 20)


@unittest.skipUnless(HAS_CORPUS, 'Pinned Fantom CORE1 payloads required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.cores = {name: Core1(str(CORPUS / f'{name}.bin')) for name in IMAGES}

    def test_payload_hashes_match_the_pins(self):
        for name, digest in IMAGES.items():
            self.assertEqual(hashlib.sha256(self.cores[name].data).hexdigest(),
                             digest, msg=name)

    def test_b0c1a_census_matches_the_pinned_report(self):
        result = study(self.cores['b0c1a'], 'b0c1a')
        self.assertEqual(result['lists'], 103)
        self.assertEqual(result['slots'], 32)
        self.assertEqual(result['classification']['counts'],
                         dict(stub=16, packet=361, data=0))
        self.assertEqual(result['classification']['data_segments'], [])
        self.assertEqual([row[1] for row in result['stub_only']],
                         ['0x4020', '0x5020', '0x6020', '0x6420',
                          '0xe840', '0xfc40'])
        self.assertEqual(result['descriptor_crosscheck'],
                         [dict(dsp=4, base='0x4020', capacity='0x1000',
                               stub_segments=1, packet_segments=76),
                          dict(dsp=5, base='0x8040', capacity='0x1000',
                               stub_segments=1, packet_segments=76),
                          dict(dsp=5, base='0x9040', capacity='0x1000',
                               stub_segments=1, packet_segments=76),
                          dict(dsp=5, base='0xa040', capacity='0x1000',
                               stub_segments=1, packet_segments=76),
                          dict(dsp=1, base='0x3020', capacity='0x1800',
                               stub_segments=0, packet_segments=12)])

    def test_b1c1a_census_matches_the_pinned_report(self):
        result = study(self.cores['b1c1a'], 'b1c1a')
        self.assertEqual(result['lists'], 104)
        self.assertEqual(result['slots'], 51)
        self.assertEqual(result['classification']['counts'],
                         dict(stub=26, packet=1606, data=1))
        self.assertEqual(result['classification']['data_segments'],
                         [dict(list_offset=941364, dsp=4, base='0x1bda',
                               length=64)])
        self.assertEqual(len(result['stub_only']), 19)
        # The pinned 20-row reservation table at 0x610a4f20 holds 20 distinct
        # {base, 0x700} pairs, all of which are real-content slots in the census.
        table = result['b1c1a_reservation_table']
        self.assertEqual(len(table), 20)
        self.assertEqual(len(set(table)), 20)
        self.assertEqual(sorted({capacity for _, capacity in table}), [0x700])

    def test_every_stub_only_slot_has_exactly_one_record(self):
        for name in IMAGES:
            result = study(self.cores[name], name)
            self.assertEqual(len(result['stub_records']),
                             len(result['stub_only']), msg=name)
            for row in result['stub_records']:
                self.assertEqual(set(row),
                                 {'base', 'capacity', 'record', 'source'})
                int(row['record'], 16)
                int(row['source'], 16)

    def test_b0c1a_stub_records_are_pinned_addresses(self):
        result = study(self.cores['b0c1a'], 'b0c1a')
        self.assertEqual([row['record'] for row in result['stub_records']],
                         ['0x610a8bfc', '0x610a8c0c', '0x610a8c1c',
                          '0x610a8c2c', '0x610b0d40', '0x610b0d50'])
        # Every record's source holds the pinned boot-stub record bytes.
        core = self.cores['b0c1a']
        for row in result['stub_records']:
            offset = core.offset(int(row['source'], 16))
            self.assertEqual(core.data[offset:offset + 8], STUB_RECORD)

    def test_b1c1a_stub_records_are_pinned_addresses(self):
        result = study(self.cores['b1c1a'], 'b1c1a')
        records = [row['record'] for row in result['stub_records']]
        # 16 consecutive dsp-4 records at 0x610a9000 (stride 16), then the
        # three stragglers; all pinned this run against image bytes.
        self.assertEqual(records[:2], ['0x610a9000', '0x610a9010'])
        self.assertEqual(records[-3:], ['0x610a9100', '0x610afcec',
                                        '0x610afcfc'])
        self.assertEqual(len([a for a in records
                              if int(a, 16) < 0x610afc00]), 17)
        core = self.cores['b1c1a']
        for row in result['stub_records']:
            offset = core.offset(int(row['source'], 16))
            self.assertEqual(core.data[offset:offset + 8], STUB_RECORD)

    def test_b1c1a_reservation_table_sits_beside_the_stub_records(self):
        # The table words at 0x610a4f20 must literally be the pinned rows.
        core = self.cores['b1c1a']
        import struct
        from program_slot_census import b1c1a_reservation_table
        rows = b1c1a_reservation_table(core)
        offset = core.offset(B1C1A_RESERVATION_TABLE)
        raw = list(struct.iter_unpack(
            '<II', core.data[offset:offset + 8 * B1C1A_RESERVATION_RECORDS]))
        self.assertEqual(rows, raw)
        self.assertEqual(rows[0], (0x4020, 0x700))

    def test_stub_only_slots_never_carry_real_content(self):
        from program_slot_census import STUB_RECORD
        for name in IMAGES:
            core = self.cores[name]
            result = study(core, name)
            stub_bases = {(int(base, 16), tuple(int(c, 16) for c in caps))
                          for _dsp, base, caps in result['stub_only']}
            self.assertTrue(stub_bases, msg=name)

    def test_report_fails_closed_on_a_duplicate_stub_record(self):
        import struct
        name = 'b0c1a'
        # Overwrite the second stub-only segment record's base word 0x5020 with
        # 0x4020 (verified one-bit change, 0x5020 ^ 0x4020 = 0x1000) at
        # 0x610a8c0c: slot 0x4020 then has two stub segment records and the
        # record census must raise instead of silently passing.
        data = bytearray(self.cores[name].data)
        offset = self.cores[name].offset(0x610a8c0c)
        self.assertEqual(int.from_bytes(data[offset:offset + 4], 'little'),
                         0x5020)
        struct.pack_into('<I', data, offset, 0x4020)
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as handle:
            handle.write(bytes(data))
        try:
            from core1 import Core1
            mutated = Core1(handle.name)
            with self.assertRaises(ValueError):
                study(mutated, name)
        finally:
            os.unlink(handle.name)


if __name__ == '__main__':
    unittest.main()