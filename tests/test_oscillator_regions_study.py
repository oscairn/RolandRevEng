import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble
from oscillator_regions_study import anchor_packets


class AnchorTests(unittest.TestCase):
    def test_literal_position_and_width_need_both_to_agree(self):
        stream = assemble([[0x0903, 0x0410, 0x3000]])
        row = anchor_packets(stream, [dict(relative=4, width=2)])[0]
        self.assertEqual(len(row['layout_matches']), 1)
        self.assertEqual(row['value'], 1.0)
        for anchor in [dict(relative=4, width=4), dict(relative=5, width=2),
                       dict(relative=0, width=2), dict(relative=2, width=2),
                       dict(relative=-1, width=2), dict(relative=4, width=1)]:
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                anchor_packets(stream, [anchor])

    def test_named_anchor_does_not_establish_unknown_header_semantics(self):
        stream = assemble([[0x0a03, 0xff75, 0x3000]])
        row = anchor_packets(stream, [dict(name='authored test anchor', relative=4, width=2)])[0]
        self.assertIn('layout_error', row)
        self.assertNotIn('layout_matches', row)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                     'Capstone or local artifacts not prepared')
class CorpusTests(unittest.TestCase):
    def test_all_six_anchors_are_located_but_opcode_layouts_remain_unsupported(self):
        from oscillator_regions_study import study
        result = study()
        self.assertEqual((result['base'], result['length'], result['source']), (0x20, 0x35b6, 0x610a5614))
        self.assertEqual([(row['packet_offset'], row['header']) for row in result['anchors']],
                         [(0, 0xbd4b), (0x5e, 0xa50c), (0x2a, 0x5c07),
                          (0x7e, 0x4d0d), (0x5e, 0xa50c), (0x7e, 0x4d0d)])
        self.assertTrue(all('layout_error' in row for row in result['anchors']))


if __name__ == '__main__':
    unittest.main()
