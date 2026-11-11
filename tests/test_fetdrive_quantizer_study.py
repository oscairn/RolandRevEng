import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from fetdrive_quantizer_study import fantom_report, native_report, native_shaped_store


class ShapedStoreTests(unittest.TestCase):
    def test_quantization_and_clip_precede_affine_square(self):
        params = dict(drive=1, scale=1, post_gain=0.5)
        small = native_shaped_store(2 ** -33, **params)
        self.assertEqual(small['quantized'], 0)
        self.assertAlmostEqual(small['stored'], 0.0555577778, places=14)
        positive, negative = [native_shaped_store(value, **params) for value in (1, -1)]
        self.assertEqual((positive['quantized'], positive['clipped']), (512, 1))
        self.assertEqual((negative['quantized'], negative['clipped']), (-512, -1))
        self.assertAlmostEqual(positive['stored'], 0.22222444445, places=14)
        self.assertAlmostEqual(negative['stored'], 5e-11, places=20)

    def test_invalid_values_are_rejected(self):
        for args in ((float('nan'), 1, 1, 1), (0.1, 1e40, 1, 1), (1, 1, 1, float('inf'))):
            with self.subTest(args=args), self.assertRaises(ValueError):
                native_shaped_store(args[0], drive=args[1], scale=args[2], post_gain=args[3])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None


class CorpusTests(unittest.TestCase):
    @unittest.skipUnless(HAS_CAPSTONE and all((CORPUS/name).exists()
                         for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')), 'Native corpus required')
    def test_native_cutpoints_and_defaults(self):
        report = native_report()
        self.assertEqual([(channel['data_bindings'][0]['pc'], channel['data_bindings'][1]['pc'])
                          for channel in report['quantizers']], [(0x2f7e6c, 0x2f7ee4), (0x2f7fd8, 0x2f8018)])
        self.assertEqual(report['native_defaults']['post_gain'], 1)
        self.assertEqual(report['desktop_packets']['coefficient_slot'], 1)
        self.assertEqual(report['gain_comparison']['sample_load_ports'], [0, 4])
        self.assertEqual(report['gain_comparison']['store_ports'], [1, 5])
        self.assertEqual(report['gain_comparison']['native_stores'], [0x1d6580, 0x1d6594])
        self.assertEqual(report['quantizer_input_port_candidate'], 1)
        self.assertFalse(report['isolated_writeback_verified'])
        setup = report['post_gain_setup']
        self.assertEqual((setup['numerator'], setup['initial_divisor']), (44100, 44100))
        self.assertEqual([r['relative_byte'] for r in setup['group']['records']], [0x62, 0xf8])

    @unittest.skipUnless(HAS_CAPSTONE and (CORPUS/'b0c1a.bin').exists(), 'Recorded Fantom image required')
    def test_all_stock_placements_keep_firmware_specific_literals(self):
        from core1 import Core1

        reports = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([row['base'] for row in reports], [0x4020, 0x8040, 0x9040, 0xa040, 0x3020])
        for row in reports:
            self.assertEqual(row['targets'], [source+2 for source in row['sources']])
            self.assertEqual(row['scale'], 1/256)
            self.assertEqual(row['post_gain'], [0.9187498092651367] * 2)
            self.assertLess(abs(row['post_gain'][0] - 44100/48000), 2 ** -20)
            self.assertEqual(row['affine_literals'], [[0.333251953125] * 2] * 2)
