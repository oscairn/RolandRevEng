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

    def test_mixed_long_short_and_transfer_reference_packing(self):
        paired = layout([0x1107, 0x0422, 0x4525, 0, 0, 0, 0])
        self.assertEqual(paired['families'], [0, 1])
        self.assertEqual([(f['role'], f['offset'], f['width']) for f in paired['fields']],
                         [('extension', 6, 2), ('literal', 8, 3), ('literal', 11, 3)])
        mixed = layout([0x2509, 0x0422, 0x4525, 0x3fe8, 0, 0, 0, 0, 0])
        self.assertEqual(mixed['families'], [0, 1, 4])
        self.assertEqual([(f['role'], f['offset']) for f in mixed['fields']],
                         [('extension', 8), ('literal', 10), ('literal', 13), ('address', 16)])
        four = layout([0x4e0b, 0x0422, 0x4525, 0x3fe8, 0x7fea, 0, 0, 0, 0, 0, 0])
        self.assertEqual(four['families'], [0, 1, 4, 4])
        self.assertEqual([(f['role'], f['offset']) for f in four['fields']],
                         [('extension', 10), ('literal', 12), ('literal', 15),
                          ('address', 18), ('address', 20)])

    def test_extended_count_adds_transfer_slots(self):
        five = layout([0x8f0b, 0x044b, 0x454b, 0x2fe4, 0x3fe6, 0x7fe8, 0, 4, 0, 0, 0])
        self.assertEqual(five['families'], [0, 0, 4, 4, 4])
        eight = layout([0x8fd1, 0x044b, 0x454b, 0x1fe4, 0x2fe6, 0x3fe8,
                        0x4fea, 0x5fec, 0x6fee, 0, 4, 0, 0, 0, 0, 0, 0])
        self.assertEqual(eight['families'], [0, 0, 4, 4, 4, 4, 4, 4])
        self.assertEqual([f['offset'] for f in eight['fields']], [18, 20, 22, 24, 26, 28, 30, 32])
        self.assertEqual(families(0x9c4d), (0, 1, 4, 4, 4, 4))
        self.assertEqual(families(0xab50), (0, 4, 4, 4, 4, 4))
        self.assertEqual(families(0xc74e), (1, 4, 4, 4, 4, 4))
        with self.assertRaises(UnsupportedLayout):
            families(0x9c8d)

    def test_unsupported_forms_do_not_gain_guessed_operands(self):
        for words in ([0x0902, 0x4091], [0x0a02, 0xff70],
                      [0x1108, 0x0432, 0x20a0, 0, 0, 0, 0, 0],
                      [0x1108, 0x0432, 0x30a0, 0, 0, 0, 0, 0],
                      [0x1108, 0x0432, 0x20a4, 0, 0, 0, 0, 0],
                      [0x1108, 0x0432, 0x20a5, 0, 0, 0, 0, 0],
                      [0x1108, 0x0432, 0x30a2, 0, 0, 0, 0, 0]):
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
        for name in ('zenology', 'b0c1a.bin', 'b1c1a.bin'):
            self.assertEqual(results[name]['failures'], [], name)
        self.assertEqual(results['zenology']['counts']['decoded'], 8970)
        self.assertEqual(results['b0c1a.bin']['counts']['decoded'], 25864)
        self.assertEqual(results['b1c1a.bin']['counts']['decoded'], 6876)
        self.assertEqual(results['independent_symbols']['counts']['matching_anchors'], 2233)
        self.assertEqual(results['independent_symbols']['failures'], [dict(
            cls='SIM_MFX_GASSPH', offset=0x29e, symbol_offset=0x2a8,
            candidate_width=4, candidate_symbol_offsets=[0x827cac], predicted_widths=[3])])


if __name__ == '__main__':
    unittest.main()
