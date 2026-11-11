import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble, encode_literal
from line_mix_probe import decode_fantom_mix, jupiter_report, predict_fantom_mix, predict_jupiter_mix
from line_shaping_study import dsp_quantizer_windows


def pool(*values):
    return b''.join(encode_literal(value, 3) for value in values)


class MixProbeTests(unittest.TestCase):
    def test_fantom_uses_four_independent_literal_values(self):
        shared = assemble([[0x0806, 0x4822, 0x1940, 0, 0, 0]])[:6] + pool(0.25, -0.5)
        stereo = assemble([[0x1008, 0x2424, 0x3467, 4, 4, 0, 0, 0]])[:10] + pool(0.5, 0.25)
        stores = assemble([[0x3e07, 0xafe0, 0xbfe2, 0x5fe4, 1, 2, 0xc009]])
        spec = decode_fantom_mix(shared + stereo + stores)
        self.assertEqual(spec, dict(literal_values=[0.25, -0.5, 0.5, 0.25],
                                    targets=[1, 2], coefficient_slot=9))
        self.assertEqual(predict_fantom_mix(2, -3, spec['literal_values']), (3, 1.25))
        with self.assertRaises(ValueError):
            decode_fantom_mix(shared + stereo[:-2] + stores)

    def test_jupiter_store_uses_entering_b(self):
        loads = assemble([[0x1e05, 0x0fe0, 0x1fe2, 0x2001, 0x2002]])
        mix = assemble([[0x0806, 0x4822, 0x1940, 0, 0, 0]])[:6] + pool(1, 0)
        store = assemble([[0x1408, 0x5824, 0xcfe2, 0x19c0, 0x2003, 0, 0, 0]])
        result = predict_jupiter_mix(loads + mix + store, 0.25, -0.125)
        self.assertEqual((result['store_address'], result['predicted_store']), (0x2003, 0.25))
        with self.assertRaises(ValueError):
            predict_jupiter_mix(loads + mix + store[:-2], 0.25, -0.125)

    def test_quantizer_windows_keep_exceptional_slots_separate(self):
        words = ((0, [0x3105, 0x2485, 0xfe10, 0xb9b2, 0]), (0xa, [0x0a02, 0xac99]),
                 (0xe, [0x1a03, 0xaed2, 0x1e10]), (0x14, [0x0903, 0x2490, 0x32d0]),
                 (0x1a, [0x0a02, 0xaeda]))
        rows = [(base+offset, packet) for base in (0x48, 0x8a) for offset, packet in words]
        left, right = dsp_quantizer_windows(rows)
        self.assertEqual(left[0]['operations'], [(0x2485, 1), (0xfe10, 2), (0xb9b2, 4)])
        self.assertEqual(right[1]['operations'], [(0xac99, 2)])
        with self.assertRaises(ValueError):
            dsp_quantizer_windows(rows[:-1])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
JUPITER = CORPUS/'crossmodel/jupiter-x/MI077_C1A_up.bin'


@unittest.skipUnless(JUPITER.exists(), 'Recorded JUPITER-X firmware required')
class JupiterCorpusTests(unittest.TestCase):
    def test_both_jupiter_banks_predict_first_input(self):
        report = jupiter_report(JUPITER, 0.25, -0.125)
        self.assertFalse(report['hardware_execution_verified'])
        self.assertEqual([(row['input_addresses'], row['store_address'], row['predicted_store'])
                          for row in report['banks']], [([0x2008, 0x2009], 0x200e, 0.25),
                                                       ([0x2078, 0x2079], 0x207e, 0.25)])
