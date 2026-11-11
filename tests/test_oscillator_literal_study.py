import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                     for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')),
                     'Recorded native corpus required')
class LiteralContextTests(unittest.TestCase):
    def test_owned_literals_reach_two_independent_native_stores(self):
        from oscillator_literal_study import report

        result = report()
        self.assertEqual([(row['control'], row['literal']['field'], row['observed_store_port'])
                          for row in result['copies']], [(0x3074, 0xe, 3), (0x7078, 0x12, 7)])
        self.assertEqual([row['native_store']['pc'] for row in result['copies']], [0x45600, 0x45614])
        self.assertEqual([row['literal']['field'] for row in result['other_contexts']], [0xca, 0x182])
        self.assertFalse(result['isolated_opcode_admission'])
