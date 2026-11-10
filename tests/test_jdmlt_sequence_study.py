import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from jdmlt_sequence_study import sequence_word, study


class SelectorTests(unittest.TestCase):
    def test_selector_order_gate_substitution_and_clamping(self):
        self.assertEqual([sequence_word(i, 0) for i in range(6)],
                         [0x201, 0x021, 0x210, 0x120, 0x012, 0x102])
        self.assertEqual([sequence_word(i, 3) for i in range(6)],
                         [0x301, 0x031, 0x310, 0x130, 0x013, 0x103])
        self.assertEqual(sequence_word(-1, -1), 0x201)
        self.assertEqual(sequence_word(6, 7), 0x103)
        with self.assertRaises(ValueError):
            sequence_word(True, 0)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')),
                     'Prepared native pairing metadata required')
class CorpusTests(unittest.TestCase):
    def test_selector_links_callees_and_return_adjacent_stores(self):
        report = study()
        self.assertEqual(report['default_word'], 0x210)
        self.assertEqual(report['candidate_target'], 0x8784)
        self.assertEqual(report['local_indexed_00a'], [])
        self.assertEqual([row['packet_address'] for row in report['parent_references']], [0x3f02])
        self.assertEqual([row['following_00f8'] for row in report['anchors']], [0x208, 0x332, 0x564, 0x76e])
        self.assertEqual([(row['native_store'], row['dsp_packet'], row['dsp_control'])
                          for row in report['stores']],
                         [(0x131e34, 0x210, 0x9fe4), (0x132234, 0x332, 0xbfe0)])


if __name__ == '__main__':
    unittest.main()
