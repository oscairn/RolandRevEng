import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_prefix_study import descriptor, literal_calls, report


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


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone required')
class NativeCallTests(unittest.TestCase):
    def test_branch_or_return_cannot_bridge_to_a_later_call(self):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
        md.detail = True
        # LDR vtable/slot; ADRP+ADD x1; BLR x8. These are original synthetic instructions.
        prefix, call = [0xf9400008, 0xf9406508, 0x90000001, 0x91008021], 0xd63f0100
        def decode(words):
            return list(md.disasm(struct.pack('<'+'I'*len(words), *words), 0x1000))
        self.assertEqual(literal_calls(decode(prefix+[call])),
                         [dict(slot_load=0x1004, call=0x1010, symbol=0x1020)])
        for control in [0x14000001, 0x94000001, 0xb4000020, 0xb5000020,
                        0x36000020, 0x37000020, 0x54000020, 0xd65f03c0]:
            with self.subTest(control=hex(control)), self.assertRaises(ValueError):
                literal_calls(decode(prefix+[control, call]))


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
