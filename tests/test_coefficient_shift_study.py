import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from coefficient_shift_study import fantom_report, native_report, native_selected_gain, native_shift4_coefficient
from line_shaping_study import EPSILON, quantize_native_reference


class NumericTests(unittest.TestCase):
    def test_native_shift4_and_unity_gate(self):
        self.assertEqual(native_shift4_coefficient(0.03125), 0.5)
        self.assertEqual(native_shift4_coefficient(-0.015625), -0.25)
        self.assertEqual(native_shift4_coefficient(2 ** -33), 0)
        self.assertEqual(native_shift4_coefficient(2 ** 27), -(2 ** 31))
        self.assertEqual(native_selected_gain(0.03125, 0), 0.5)
        self.assertEqual(native_selected_gain(0.03125, EPSILON), 1)
        self.assertEqual(native_selected_gain(0.03125, -EPSILON), 1)
        self.assertEqual(quantize_native_reference(0.03125, shift_bits=2)['quantized'], 0.125)
        with self.assertRaises(ValueError):
            quantize_native_reference(1, shift_bits=3)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None


class CorpusTests(unittest.TestCase):
    @unittest.skipUnless(HAS_CAPSTONE and all((CORPUS/name).exists()
                         for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')), 'Native corpus required')
    def test_native_conversions_and_distinct_port_observations(self):
        report = native_report()
        self.assertFalse(report['strict_dsp_admission'])
        base = report['VSOD']
        self.assertEqual((base['packets']['load_port'], base['packets']['store_port']), (7, 7))
        self.assertEqual((base['store']['pc'], base['store']['relative']), (0x273984, 0x28))
        for effect, pc, register in (('VSODDSAW', 0x179268, 'd3'), ('VSODDSTW', 0x28143c, 'd4')):
            entry = report[effect]
            self.assertEqual(entry['packets']['load_port'], 3)
            self.assertEqual(entry['packets']['coefficient_slot'], 1)
            self.assertEqual(entry['select'], pc)
            self.assertEqual(entry['quantizer']['floating_output'], register)
        self.assertEqual(report['FORMANT']['quantizer']['shift_bits'], 2)
        self.assertEqual(report['FORMANT']['coefficient_slot'], 2)
        self.assertEqual((report['GASSPH']['shift_bits'], report['GASSPH']['store_port']), (2, 7))
        self.assertEqual(report['GASSPH']['native_store'], 0x14a730)
        self.assertEqual(report['VMCP']['quantizer']['shift_bits'], 4)

    @unittest.skipUnless(HAS_CAPSTONE and (CORPUS/'b0c1a.bin').exists(), 'Recorded Fantom image required')
    def test_fantom_contexts_relocate_coefficient_and_store_addresses(self):
        from core1 import Core1

        report = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual({name: len(rows) for name, rows in report.items()},
                         {'VSOD': 5, 'VSODDSAW': 4, 'VSODDSTW': 4})
        for name, rows in report.items():
            self.assertEqual([row['coefficient_slot'] for row in rows[:4]], [401, 501, 521, 541])
            self.assertTrue(all(row['control'] == (0xfdd4 if name == 'VSOD' else 0xbcd4) for row in rows))
        self.assertEqual([row['data_store'] for row in report['VSOD']], [257, 801, 951, 1101, 193])
