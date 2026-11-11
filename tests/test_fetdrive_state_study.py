import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class StateTests(unittest.TestCase):
    def test_history_aliases_across_every_origin_and_owned_filter_pairs(self):
        from fetdrive_state_study import report
        from line_state_study import native_ring_index

        checked = report()
        self.assertEqual([(row['store']['address'], row['previous']['address'])
                          for row in checked['history']],
                         [(7, 8), (9, 10), (15, 16), (17, 18), (11, 12), (13, 14), (19, 20), (21, 22)])
        for pair in checked['history']:
            for origin in range(2048):
                self.assertEqual(native_ring_index(pair['store']['address'], 0, (origin-1)&0x7ff),
                                 native_ring_index(pair['previous']['address'], 0, origin))
        self.assertEqual([[item['field'] for item in row['literals']]
                          for row in checked['filter_coefficients']],
                         [[0xb8, 0x14e], [0xc2, 0x158], [0xc5, 0x15b]])
        self.assertFalse(checked['hardware_cadence_verified'])
        self.assertFalse(checked['isolated_opcode_admission'])
