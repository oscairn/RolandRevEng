import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from weighted_mix_study import compare, reference_shape, study, weighted_sum


class WeightedMixTests(unittest.TestCase):
    def test_reference_normalization_keeps_source_and_control_bits(self):
        expected = (0x4800, 0x1000)
        self.assertEqual(reference_shape(0x4812, 0x1500), expected)
        self.assertEqual(reference_shape(0x4822, 0x1940), expected)
        for control, extension in ((0x5822, 0x1940), (0x4822, 0x2940), (0x4822, 0x1941)):
            self.assertNotEqual(reference_shape(control, extension), expected)
        with self.assertRaises(ValueError):
            reference_shape(0x4802, 0x1940)

    def test_comparison_rejects_swapped_coefficients(self):
        a, b = [('signal', ('input', i)) for i in range(2)]
        c, d = [('signal', ('literal', i)) for i in range(2)]
        expected = weighted_sum(a, b, c, d)
        self.assertEqual(len(compare(expected, expected, {})), 2)
        with self.assertRaises(ValueError):
            compare(weighted_sum(a, b, d, c), expected, {})


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')),
    'Recorded ZENOLOGY image and indexes required')
class WeightedMixCorpusTests(unittest.TestCase):
    def test_weighted_mix_and_following_stores(self):
        report = study()
        self.assertEqual([(r['packet'], r['destination_port'], r['native_store'])
                          for r in report['SIM_MFX_TRECHO']],
                         [(0x1d6, 4, 0xd018), (0x1e8, 5, 0xd02c)])
        self.assertEqual([[f['value'] for f in stage['literals']]
                          for stage in report['SIM_MFX_BITCRUSH']],
                         [[0.75, 0.25], [0.5, 0.5], [0.25, 0.75]])
        self.assertEqual(report['SIM_REV_BINHALL']['native_result'], 0x1a3c10)
        self.assertEqual(report['SIM_REV_BRHL']['destination_port'], 2)
        self.assertEqual(report['SIM_MFX_UPLIFT_EXCITER']['destination_port'], 3)
        self.assertFalse(report['line_candidate']['admitted'])
