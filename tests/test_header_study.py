import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from header_study import UnsupportedLayout, families, layout, reference


class ReferenceTests(unittest.TestCase):
    def test_register_and_literal_byte_offsets(self):
        self.assertEqual(reference(3, 0), dict(role='register', index=3))
        self.assertEqual(reference(0x24, 8), dict(role='literal', offset=4, width=3))
        self.assertEqual(reference(0x36, 10), dict(role='literal', offset=6, width=4))
        for code, size in [(64, 0), (-1, 2), (0x24, 6), (0, -1)]:
            with self.subTest(code=code, size=size), self.assertRaises(ValueError):
                reference(code, size)

    def test_long_operation_three_coefficient_references(self):
        # Synthetic operands at byte offsets 2, 5 and 8 in a 12-byte payload.
        decoded = layout([0x0808, 0x0422, 0x1968, 0, 0, 0, 0, 0])
        fields = [(f['offset'], f['width']) for f in decoded['fields'] if f['role'] == 'literal']
        self.assertEqual(fields, [(6, 3), (9, 3), (12, 3)])
        self.assertEqual(decoded['padding'], 1)

    def test_dual_short_literal_packing_and_aliases(self):
        decoded = layout([0x1506, 0x0420, 0x4523, 0, 0, 0])
        self.assertEqual([(f['offset'], f['width']) for f in decoded['fields']], [(6, 3), (9, 3)])
        aliased = layout([0x1505, 0x0420, 0x4520, 0, 0])
        self.assertEqual([f['offset'] for f in aliased['fields']], [6, 6])

    def test_transfer_and_direct_register_forms(self):
        self.assertEqual(layout([0x0c03, 0x8fe0, 0])['fields'][0]['offset'], 4)
        self.assertEqual(layout([0x0c02, 0x0a80])['fields'], [])
        self.assertEqual(families(0x1503), (1, 1))
        self.assertEqual(families(0x3e07), (4, 4, 4))

    def test_two_long_extensions_precede_transfer_addresses(self):
        decoded = layout([0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0])
        self.assertEqual(decoded['families'], [0, 0, 4, 4])
        self.assertEqual([(f['role'], f['offset']) for f in decoded['fields']],
                         [('extension', 10), ('extension', 12), ('address', 14), ('address', 16)])

    def test_unsupported_forms_do_not_gain_guessed_operands(self):
        for words in ([0x0902, 0x4091], [0x0a02, 0xff70], [0x2e05, 0x0403, 0x4503, 0x3fe0, 0]):
            with self.subTest(words=words), self.assertRaises(UnsupportedLayout):
                layout(words)
        with self.assertRaises(ValueError):
            layout([0x0903, 0x0412, 0])


@unittest.skipUnless((ROOT / 'local/zenology_inventory.json').exists() and importlib.util.find_spec('capstone'),
                     'local artifacts and Capstone are required')
class CorpusReferenceTests(unittest.TestCase):
    def test_bounded_layout_and_independent_symbol_positions(self):
        from header_study import study
        results = study()
        for name in ('zenology', 'b0c1a.bin', 'b1c1a.bin', 'independent_symbols'):
            self.assertEqual(results[name]['failures'], [], name)
        self.assertEqual(results['zenology']['counts']['decoded'], 3047)
        self.assertEqual(results['b0c1a.bin']['counts']['decoded'], 13739)
        self.assertEqual(results['b1c1a.bin']['counts']['decoded'], 4392)
        self.assertEqual(results['independent_symbols']['counts']['matching_anchors'], 387)


if __name__ == '__main__':
    unittest.main()
