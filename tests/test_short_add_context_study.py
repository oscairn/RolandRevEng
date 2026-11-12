import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble
from short_add_context_study import candidates


class ClassificationTests(unittest.TestCase):
    def test_same_word_short_and_misc_have_different_operand_admission(self):
        short = assemble([[0x0903, 0x5d50, 0x2340]])
        misc = assemble([[0x3108, 0x4d74, 0x5d50, 0x7fe2, 0, 0xc004, 0, 0]])
        a, b = candidates(short+misc)
        self.assertEqual((a['control'], b['control']), (0x5d50, 0x5d50))
        self.assertEqual((a['family'], b['family']), (1, 2))
        self.assertEqual(a['operand'], dict(role='literal', field=4, width=2, value=0.203125))
        self.assertIsNone(b['operand'])
        self.assertFalse(a['semantic_admission'])

    def test_long_form_and_unknown_header_do_not_become_short_operands(self):
        long = assemble([[0x0804, 0x1d4c, 0x2481, 0x4200]])
        unknown = assemble([[0xb409, 0x5d72, 0, 0, 0, 0, 0, 0, 0]])
        a, b = candidates(long+unknown)
        self.assertEqual(a['family'], 0)
        self.assertIsNone(a['operand'])
        self.assertIsNone(b['family'])
        self.assertIsNone(b['operand'])
        with self.assertRaises(ValueError):
            candidates(b'\x09\x03\x5d\x50')


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                     for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')),
                     'Capstone and pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_actual_scope_and_transient_constructor_literal_binding(self):
        from short_add_context_study import report
        result = report()
        self.assertEqual((result['short_candidates'], result['short_classes']), (15, 9))
        self.assertEqual(result['family_counts'].get('0'), 23)
        self.assertEqual(result['family_counts'].get('2'), 1)
        binding = result['transient_literal_binding']
        self.assertEqual((binding['field'], binding['width']), (0x104, 4))
        self.assertEqual(binding['stored_value'], -0.0004233471117913723)
        self.assertLess(abs(binding['stored_value']-binding['full_native_default']), 2**-32)
        self.assertEqual(binding['native_clamp_limit'].hex(), '-0x1.ba18a998fffa0p+2')
        self.assertEqual(len(result['native_addition_candidates']), 4)
        self.assertEqual([row['native_add_candidates'] for row in result['native_addition_candidates']],
                         [[0x29750], [0x14a630, 0x14a680], [0x324f88, 0x324fe8], [0x2fa1b4, 0x2fa200]])
        self.assertTrue(all(not row['source_port_binding_verified']
                            for row in result['native_addition_candidates']))
        self.assertFalse(result['isolated_short_add_verified'])


if __name__ == '__main__':
    unittest.main()
