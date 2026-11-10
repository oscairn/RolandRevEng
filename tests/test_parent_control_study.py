import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble
from parent_control_study import controls, native_list, report


class ReferenceTests(unittest.TestCase):
    def test_shifted_indices_are_not_distinct_fixed_operands(self):
        stream = assemble([[0xa84e, 0x1852, 0x00a6, 0x00a8, 0x0823, 0x9fea, 0xdfec,
                            0x5500, 0x2800, 0x2800, 0x28bb, 0x5800, 0x2462, 0x2463]])
        rows = controls(stream, 0x20, {0xb000})['indexed_00a_candidates']
        self.assertEqual([(r['pool_byte_offset'], r['pool_value'], r['candidate_entry_byte']) for r in rows],
                         [(6, 0x28bb, None), (8, 0x5800, 0xb000)])
        self.assertEqual(controls(assemble([[0x0b04, 0x1710, 0x00a0, 0x00f8]]), 0, set()),
                         dict(indexed_00a_candidates=[], return_00f8_candidates=[]))
        with self.assertRaisesRegex(ValueError, 'outside'):
            controls(assemble([[0x0b02, 0x00ae]]), 0, set())

    def test_selected_native_list_bounds_and_count(self):
        data = bytearray(1024)
        struct.pack_into('<IIQ', data, 0, 0, (24 << 8) | 4, 0x20)
        for i in range(24):
            struct.pack_into('<IIIIQ', data, 0x20+24*i, i*8, 6, 8, 0, 0x300)
        self.assertEqual(len(native_list(data, 0)['segments']), 24)
        for offset, fmt, value in [(4, '<I', (33 << 8) | 4), (8, '<Q', 0x3f8),
                                    (0x28, '<I', 4), (0x2c, '<I', 1), (0x30, '<Q', 1020)]:
            changed = data.copy()
            struct.pack_into(fmt, changed, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                native_list(changed, 0)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS / f).exists() for f in ('b0c1a.bin', 'zen_arm64')),
                     'Capstone and recorded corpus required')
class CorpusTests(unittest.TestCase):
    def test_nested_fifth_entry_native_index_variants_and_stubs(self):
        from core1 import Core1
        result = report(Core1(CORPUS / 'b0c1a.bin'), (CORPUS / 'zen_arm64').read_bytes())
        organ = result['firmware'][1]['indexed_00a_candidates']
        self.assertIn((0x10c8, 0x3020), [(r['packet_address'], r['candidate_entry_byte']) for r in organ])
        native4, native5 = result['desktop']
        self.assertEqual(native4['segment_count'], 24)
        self.assertEqual([(r['packet_address'], r['control'], r['candidate_entry_byte'])
                         for r in native5['indexed_00a_candidates'] if r['candidate_entry_byte'] is not None],
                         [(0x3f02, 0x00a2, 0x8000), (0x43f8, 0x00a8, 0xb000),
                          (0x44b6, 0x00a8, 0x9000), (0x49ce, 0x00a0, 0xcc00)])
        for parent in (native4, native5):
            for stub in parent['six_byte_stubs']:
                self.assertEqual(stub['return_00f8_candidates'],
                                 [dict(packet_address=stub['base'], operation=0)])
        self.assertEqual(native4['return_00f8_candidates'], [])


if __name__ == '__main__':
    unittest.main()
