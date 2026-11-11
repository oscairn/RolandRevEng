import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from limit_control_study import fantom_report, native_report, vmcp_detector_reference


class DetectorTests(unittest.TestCase):
    def test_scale_and_bias_are_on_opposite_sides_of_the_clamp(self):
        self.assertEqual(vmcp_detector_reference(2, 3, scale=0.5, bias=-0.125), 0.875)
        self.assertEqual(vmcp_detector_reference(-2, 3, scale=0.5, bias=-0.125), -1.125)
        self.assertEqual(vmcp_detector_reference(0.5, 1, scale=0.5, bias=-0.125), 0.125)
        self.assertEqual(vmcp_detector_reference(2, 3, scale=0, bias=-0.125), -0.125)
        with self.assertRaises(ValueError):
            vmcp_detector_reference(1, 1, scale=float('nan'), bias=0)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Recorded native corpus required')
class CorpusTests(unittest.TestCase):
    def test_limit_and_fixed_point_windows_have_distinct_store_anchors(self):
        report = native_report()
        self.assertFalse(report['strict_dsp_admission'])
        vmcp = report['vmcp']
        self.assertEqual([binding['pc'] for binding in vmcp['detector_bindings']],
                         [0x39da78, 0x39da90, 0x39dac8])
        self.assertEqual([row['shift_bits'] for row in vmcp['quantizers']], [2, 4])
        self.assertEqual(vmcp['before_shift']['pc'], 0x39dba8)
        self.assertEqual([binding['pc'] for binding in vmcp['after_gain']], [0x39dc30, 0x39dc44])
        self.assertEqual(report['ring']['after']['pc'], 0x277e00)
        self.assertEqual(report['ring']['store_operand'], 0x11e)
        self.assertEqual(report['gate']['native_store'], 0x313fa8)
        self.assertEqual(report['gate']['dsp_store_operand'], 0xba)
        self.assertEqual(report['gate']['destination_port_after_bundle'], 0)
        self.assertFalse(report['gate']['isolated_writeback_verified'])

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Recorded Fantom image required')
    def test_fantom_relocations_and_threshold_table(self):
        from core1 import Core1

        report = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(report['threshold'], native_report()['threshold'])
        self.assertEqual(report['threshold']['field'], 0x4a)
        self.assertEqual([(row['base'], row['detector']) for row in report['placements']],
                         [(0x4020, 0x100), (0x8040, 0x320), (0x9040, 0x3b6), (0xa040, 0x44c)])
        for row in report['placements']:
            self.assertEqual(row['scale'], 0)
            self.assertEqual(row['state'], row['detector'] + 4)
