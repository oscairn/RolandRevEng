import importlib.util
import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_prefix_single_writer import (WRITER_CHECKS, code_references, mentions,
                                       writer_shape)


def native_fixture(records, count=None):
    """Synthetic LP64 image: record table at 128, pointed to by the descriptor."""
    data = bytearray(4096)
    struct.pack_into('<Q', data, 16, 128)
    for index, (absolute, relative, width) in enumerate(records):
        struct.pack_into('<3I', data, 128+12*index, absolute, relative, width)
    data[24] = len(records) if count is None else count
    return bytes(data)


class MentionsTests(unittest.TestCase):
    def test_count1_records_parse_and_filter_by_fields(self):
        data = native_fixture([(0x4037, 0x17, 3), (0x4034, 0x14, 3)], count=1)
        rows = mentions(data, 8, lambda a: a, lambda o: o, {0x17})
        self.assertEqual([(r['symbol'], r['count']) for r in rows], [(0, 1)])
        # Only the counted record is declared; the second packed record is padding.
        self.assertEqual([rec['relative_byte'] for rec in rows[0]['records']], [0x17])
        self.assertEqual(mentions(data, 8, lambda a: a, lambda o: o, {0x27}), [])

    def test_count2_requires_every_record_width_to_qualify(self):
        data = native_fixture([(0x4037, 0x17, 3), (0x4034, 0x14, 3)])
        self.assertEqual([r['count'] for r in mentions(data, 8, lambda a: a, lambda o: o,
                                                       {0x17})], [2])
        data = native_fixture([(0x4037, 0x17, 3), (0x4034, 0x14, 0)])
        self.assertEqual(mentions(data, 8, lambda a: a, lambda o: o, {0x17}), [])

    def test_bad_width_and_unmapped_table_are_rejected(self):
        data = native_fixture([(0x4037, 0x17, 5)])
        self.assertEqual(mentions(data, 8, lambda a: a, lambda o: o, {0x17}), [])
        data = bytearray(256)
        struct.pack_into('<Q', data, 16, 3)  # table not 4-aligned
        data[24] = 1
        struct.pack_into('<3I', data, 128, 0x4037, 0x17, 3)
        self.assertEqual(mentions(data, 8, lambda a: a, lambda o: o, {0x17}), [])

    def test_count_byte_below_min_is_skipped(self):
        data = native_fixture([(0x4037, 0x17, 3)], count=0)
        self.assertEqual(mentions(data, 8, lambda a: a, lambda o: o, {0x17}), [])
        data = native_fixture([(0x4037, 0x17, 3), (0, 0, 2)], count=2)
        self.assertEqual([r['count'] for r in mentions(data, 8, lambda a: a, lambda o: o,
                                                       {0x17})], [2])
        self.assertEqual([r['count'] for r in mentions(data, 8, lambda a: a, lambda o: o,
                                                       {0x17}, min_count=2)], [2])
        self.assertEqual([r['count'] for r in mentions(data, 8, lambda a: a, lambda o: o,
                                                       {0x17}, min_count=3)], [])


class CodeReferenceTests(unittest.TestCase):
    def test_adrp_add_reference_is_resolved_and_branches_bound_the_window(self):
        # adrp x1, page(0x1000); add x1, x1, #0xf00; ret — original synthetic form.
        function_bytes = struct.pack('<3I', 0x90000001, 0x913c0021, 0xd65f03c0)
        data = native_fixture([]) + function_bytes
        start = len(native_fixture([]))  # The method window begins after the fixture.
        starts = [0, start, len(data)]
        self.assertEqual(code_references(data, 0x1f00, starts, limit=64, reach=4),
                         [start+4])
        self.assertEqual(code_references(data, 0x1f01, starts, limit=64, reach=4), [])
        # A branch between adrp and add must end the resolution window.
        branched = native_fixture([]) + struct.pack('<4I', 0x90000001, 0x14000001,
                                                    0x913c0021, 0xd65f03c0)
        self.assertEqual(code_references(branched, 0x1f00, [0, start, len(branched)],
                                         limit=64, reach=8), [])


class WriterShapeTests(unittest.TestCase):
    def test_check_table_covers_both_descriptor_writes_and_tail(self):
        checked = {index for index, _, _ in WRITER_CHECKS}
        self.assertEqual(min(checked), 12)
        self.assertEqual(max(checked), 41)
        self.assertIn(30, checked)  # fmov d0, d8 before first blr
        self.assertIn(37, checked)  # fmov d0, d8 before terminal br
        self.assertIn(41, checked)  # br x2 terminates

    def test_writer_shape_rejects_shifted_constant_and_pins_real_shape(self):
        if not importlib.util.find_spec('capstone'):
            self.skipTest('Capstone required')
        corpus = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
        if not (corpus/'zen_arm64').exists():
            self.skipTest('Recorded native image required')
        image = (corpus/'zen_arm64').read_bytes()
        shape = writer_shape(image)
        self.assertEqual(shape['method'], 0x1d1ac8)
        self.assertEqual(shape['divisor'], 32000.0)
        self.assertEqual(shape['scale_int32'], 44100)
        self.assertEqual([w['relative_byte'] for w in shape['writes']], [0x17, 0x27])
        self.assertTrue(shape['same_d8_both_writes'])
        # Corrupting the int32 44100 scale word must fail closed.
        from line_prefix_single_writer import WRITER_SCALE as S
        shifted = image[:S]+b'\x00'*4+image[S+4:]
        with self.assertRaises(ValueError):
            writer_shape(shifted)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'zen_arm64').exists(),
                     'Recorded native image required')
class CorpusTests(unittest.TestCase):
    def test_single_writer_inventory_and_references(self):
        from line_prefix_single_writer import study
        result = study((CORPUS/'zen_arm64').read_bytes())
        self.assertEqual([row['symbol'] for row in result['mentioning']],
                         [0x9d4e30, 0x9ff988, 0xa1f7b0, 0xa1f7d0, 0xa2e778, 0xa3f560,
                          0xa3f580, 0xa519f0, 0xa51e08, 0xa51e28, 0xa52c30, 0xa54ee8,
                          0xa70a28])
        self.assertEqual(result['count2_pair_groups'], [])
        writers = result['relative17_27_writers']
        self.assertEqual(writers['single_writer_for_17_and_27_pair'], 0x1d1ac8)
        self.assertEqual(writers['methods'][0x29a9c8], [0x29a9dc, 0x29a9fc, 0x29aa58])
        self.assertEqual(result['references']['0xa1f7b0'], ['0x1d1b3c'])
        self.assertEqual(result['references']['0xa1f7d0'], ['0x1d1b58'])
        self.assertTrue(any('ownership' in limit for limit in result['limits']))
        self.assertTrue(any('Count-1 records' in limit for limit in result['limits']))

    @unittest.skipUnless(all((CORPUS/name).exists() for name in
                             ('zen_arm64', 'crossmodel/jupiter-x/MI077_C1A_up.bin')),
                         'Recorded native and JUPITER-X artifacts required')
    def test_jupiter_asymmetric_fields_are_count1(self):
        import hashlib
        from qspi_c1 import read_c1
        from line_prefix_single_writer import study, JUPITER_SHA256
        container = CORPUS/'crossmodel/jupiter-x/MI077_C1A_up.bin'
        self.assertEqual(hashlib.sha256(container.read_bytes()).hexdigest(), JUPITER_SHA256)
        manifest, view = read_c1(str(container))
        result = study((CORPUS/'zen_arm64').read_bytes(), (view, manifest))
        jupiter = result['jupiter_x']
        self.assertEqual(len(jupiter['field_mentions']), 8)
        self.assertTrue(all(row['count'] == 1 for row in jupiter['field_mentions']))
        self.assertFalse(jupiter['count2_group_containing_d0_d3'])
        self.assertEqual(jupiter['asymmetric_instance_sites'], [0x61218334, 0x61218364])
        self.assertEqual(jupiter['literal_values'], [1.0, 0.0])


if __name__ == '__main__':
    unittest.main()