import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_prefix_study import descriptor, report


class DescriptorTests(unittest.TestCase):
    def test_adjacent_records_are_not_a_group_without_count(self):
        data = bytearray(128)
        struct.pack_into('<Q', data, 16, 64)
        data[24] = 1
        struct.pack_into('<6I', data, 64, 0x4034, 0x14, 3, 0x4037, 0x17, 3)
        self.assertEqual([r['relative_byte'] for r in descriptor(data, 0)['records']], [0x14])
        data[24] = 2
        self.assertEqual([r['relative_byte'] for r in descriptor(data, 0)['records']], [0x14, 0x17])
        with self.assertRaises(ValueError):
            descriptor(data[:80], 0)
        data[24] = 17
        with self.assertRaises(ValueError):
            descriptor(data, 0)
        data[24] = 1
        struct.pack_into('<I', data, 72, 0x103)
        with self.assertRaises(ValueError):
            descriptor(data, 0)  # Unproved nonzero segment encoding is not silently accepted.


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'zen_arm64').exists(),
                     'Recorded native image required')
class CorpusTests(unittest.TestCase):
    def test_declared_line_groups_leave_prefix_unowned(self):
        result = report((CORPUS/'zen_arm64').read_bytes())
        self.assertEqual([g['count'] for g in result['groups']], [4, 4, 1])
        self.assertEqual([g['native_representative_double_field'] for g in result['groups']], [8, 0x18, 0x28])
        self.assertEqual(result['prefix_representatives'], {0x14: 0x58, 0x17: None, 0x24: 0x78, 0x27: None})
        self.assertFalse(result['prefix_grouping_proven'])
        self.assertFalse(result['new_interpreter_admission'])

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Recorded CORE1 image required')
    def test_firmware_walks_counted_records(self):
        from core1 import Core1
        result = report((CORPUS/'zen_arm64').read_bytes(), Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(result['firmware']['record_stride'], 12)
        self.assertTrue(result['firmware']['same_saved_float_per_record'])
        self.assertFalse(result['old_value_store_semantics_proven'])


if __name__ == '__main__':
    unittest.main()
