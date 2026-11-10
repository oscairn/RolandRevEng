import importlib.util
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dramio_clear_study import firmware_report, native_clear_geometry, ramclr_records


class RecordTests(unittest.TestCase):
    def test_two_little_endian_words_and_field_boundaries(self):
        data = b''.join(struct.pack('<II', 0x80000000 | (0x123456+i), 0xabc00000) for i in range(23))
        rows = ramclr_records(data)
        self.assertEqual(rows[0], dict(offset=0, address_field=0x123456,
                                     control_bits=0x80000000, companion_high12=0xabc))
        self.assertEqual(rows[-1]['offset'], 0xb0)
        self.assertEqual(rows[-1]['address_field'], 0x12346c)
        for invalid in (data[:-1], data+b'\0'*8,
                        struct.pack('<I', 0x80800000)+data[4:],
                        data[:4]+struct.pack('<I', 1)+data[8:]):
            with self.assertRaises(ValueError):
                ramclr_records(invalid)

    def test_native_start_is_excluded_and_zero_length_is_not_empty(self):
        self.assertEqual(native_clear_geometry(9, 1, 0, 0x7ff)['stores'], 0)
        one = native_clear_geometry(9, 2, 0, 0x7ff)
        self.assertEqual((one['first_store'], one['last_store'], one['occupied_half_open_spans']),
                         (10, 10, [[10, 11]]))
        zero = native_clear_geometry(9, 0, 0, 0x7ff)
        self.assertEqual((zero['stores'], zero['first_store'], zero['last_store']), (2047, 8, 10))
        self.assertEqual(zero['occupied_half_open_spans'], [[10, 2048], [0, 9]])
        self.assertEqual(native_clear_geometry(0, 0, 1, 0x3fffff)['stores'], 0x3fffff)

    def test_geometry_matches_literal_native_loop_for_wrap_and_length_cases(self):
        for base, length, origin in ((2, 0, 7), (2, 1, 7), (2, 2, 7),
                                     (2047, 5, 0), (0xffffffff, 2049, 4)):
            current = (base+length-1-origin) & 0x7ff
            stop = (base-origin) & 0x7ff
            stores = []
            while current != stop:
                stores.append(current)
                current = (current-1) & 0x7ff
            result = native_clear_geometry(base, length, origin, 0x7ff)
            occupied = [i for lo, hi in result['occupied_half_open_spans'] for i in range(lo, hi)]
            self.assertEqual(set(occupied), set(stores))
            self.assertEqual(result['stores'], len(stores))
            self.assertNotIn(result['excluded_start'], occupied)
        for values in ((-1, 1, 0, 0x7ff), (0, 1 << 32, 0, 0x7ff),
                       (0, 2, 0, 0xff), (0, 1.5, 0, 0x7ff)):
            with self.assertRaises(ValueError):
                native_clear_geometry(*values)

    def test_unknown_firmware_rejected_before_mapping(self):
        with self.assertRaisesRegex(ValueError, 'Unknown firmware'):
            firmware_report(SimpleNamespace(data=b'unknown'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS / name).exists() for name in ('b0c1a.bin', 'zen_arm64')),
                     'Capstone and local firmware/native artifacts required')
class CorpusTests(unittest.TestCase):
    def test_four_owned_hardware_record_sets_and_separate_native_paths(self):
        from dramio_clear_study import study
        result = study()
        rows = result['firmware']['segments']
        self.assertEqual([r['list_index'] for r in rows], [0, 1, 2, 3])
        self.assertEqual([r['dsp'] for r in rows], [4, 5, 5, 5])
        self.assertEqual([r['enum11']['base'] for r in rows], [0x420000, 0x520000, 0x543000, 0x566000])
        self.assertEqual([r['enum2']['base'] for r in rows], [0xa, 0, 0x22, 0x44])
        self.assertTrue(all(len(r['records']) == 23 for r in rows))
        self.assertFalse(result['firmware']['exact_history_clear_proven'])
        self.assertEqual([r['mask'] for r in result['native']['loops']], [0x3fffff, 0x7ff, 0x7ff])
        self.assertEqual(result['native']['wait_return'], 1)
        self.assertTrue(result['native']['sample_body_returns_immediately'])


if __name__ == '__main__':
    unittest.main()
