import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from transfer_study import constructor_memory, native_accesses, records_from_memory

HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None


def disasm(hex_bytes):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    return list(md.disasm(bytes.fromhex(hex_bytes), 0))


class RecordTests(unittest.TestCase):
    def test_missing_constructor_bytes_are_not_invented(self):
        memory = {0x20 + index: byte for index, byte in enumerate(bytes.fromhex('1000000003000000'))}
        self.assertEqual(records_from_memory(memory, 0x20, 1), [(16, 3)])
        del memory[0x27]
        with self.assertRaises(ValueError):
            records_from_memory(memory, 0x20, 1)


@unittest.skipUnless(HAS_CAPSTONE, 'Capstone not installed')
class ProvenanceTests(unittest.TestCase):
    # All instruction fixtures below were assembled from study-owned synthetic
    # snippets. They do not contain extracted Roland code or data.
    def test_constructor_stops_at_first_return(self):
        code = disasm('080082d20001c03d0008803dc0035fd61f2000b9')
        data = bytes(0x1000) + bytes(range(16))
        self.assertEqual(constructor_memory(code, data), {0x20 + i: i for i in range(16)})

    def test_scalar_width_and_unknown_vector_overwrite(self):
        data = bytes(0x1000) + bytes(range(16))
        scalar = disasm('080082d2090140b9092000b9c0035fd6')
        self.assertEqual(constructor_memory(scalar, data), {0x20 + i: i for i in range(4)})
        unknown_overwrite = disasm('080082d20001c03d0008803d001c206e0008803dc0035fd6')
        self.assertEqual(constructor_memory(unknown_overwrite, data), {})

    def test_native_pointer_and_mask_provenance(self):
        code = disasm('081440f9094140b90a2040b929010a0b0b0440f96b0d40f96b1540f9'
                      '6b0d40f9605969fc094940b929290012605929fcc0035fd6')
        result = native_accesses(code, {0x40: {}, 0x48: {}}, {})
        first, second = result['accesses']
        self.assertEqual((first['fields'], first['mask']), ([0x40], None))
        self.assertEqual((second['fields'], second['mask']), ([0x48], 0x7ff))
        self.assertEqual(first['path'], ['wrapper', 8, 0x18, 0x28, 0x18])

    def test_clobbered_object_and_pair_width(self):
        clobbered = disasm('081440f9080108ca094140b9405869fcc0035fd6')
        self.assertEqual(native_accesses(clobbered, {0x40: {}}, {})['accesses'], [])
        pair = disasm('081440f90929482940586afcc0035fd6')
        result = native_accesses(pair, {0x40: {}, 0x44: {}, 0x48: {}}, {})
        self.assertEqual(result['accesses'][0]['fields'], [0x44])


@unittest.skipUnless(HAS_CAPSTONE and all((ROOT / 'local' / name).exists() for name in
                                        ('pairs.json', 'zen_arm64', 'exports_dem.txt')), 'local corpus not prepared')
class LocalTransferTests(unittest.TestCase):
    def test_three_resolved_spaces_have_distinct_native_paths(self):
        from transfer_study import collect
        result = collect()
        self.assertEqual(result['totals']['classes'], 73)
        expected = {
            0: (['wrapper', 8, 0x18, 0x10, 0x18], 0x7ff),
            2: (['wrapper', 8, 0x18, 0x18, 0x18], 0x7ff),
            4: (['wrapper', 8, 0x18, 0x28, 0x18], None),
        }
        for space in result['spaces']:
            self.assertEqual((space['path'], space['mask']), expected[space['tag']])
        for cls in result['classes']:
            for tag in expected:
                offsets = {a['program_index'] - a['table_value'] for a in cls['accesses'] if a.get('tag') == tag}
                self.assertLessEqual(len(offsets), 1, (cls['cls'], tag))


if __name__ == '__main__':
    unittest.main()
