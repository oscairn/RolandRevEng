import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble, encode_literal, swap_words
from line_mix_variation import LINE_MIX, scan, study


class MixVariationTests(unittest.TestCase):
    def test_literal_values_and_following_packet_are_independent(self):
        prefix = assemble([LINE_MIX + (0, 0, 0)])[:6]
        prefix += encode_literal(0.25, 3) + encode_literal(-0.75, 3)
        stream = prefix + assemble([[1]])
        stored = swap_words(stream.ljust(16, b'\0'))
        result = scan(stored, [(0x1000, (0x20, len(stream), 16, 0))])
        self.assertEqual(result['counts'], dict(framed_segments=1, framed_packets=2))
        match, = result['matches']
        self.assertEqual(match['literals'], [dict(field=6, width=3, value=0.25),
                                             dict(field=9, width=3, value=-0.75)])
        self.assertEqual(match['following'], dict(offset=12, header=1, controls=[], literals=[]))
        different_extension = prefix[:5] + b'\x00' + prefix[6:]
        self.assertEqual(scan(swap_words(different_extension),
                              [(1, (0x20, 12, 12, 0))])['matches'], [])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
JUPITER = CORPUS/'crossmodel/jupiter-x/MI077_C1A_up.bin'


@unittest.skipUnless(importlib.util.find_spec('capstone') and JUPITER.exists()
                     and (CORPUS/'zen_arm64').exists() and (CORPUS/'zenology_inventory.json').exists(),
                     'Recorded JUPITER-X and ZENOLOGY artifacts required')
class CorpusTests(unittest.TestCase):
    def test_jupiter_asymmetric_occurrences(self):
        reports = study([], [JUPITER])
        self.assertEqual(len(reports['zenology']['matches']), 4)
        hits = reports[JUPITER.name]['matches']
        self.assertEqual(len(hits), 24)
        unequal = [hit for hit in hits if len({item['value'] for item in hit['literals']}) > 1]
        self.assertEqual([(hit['descriptor'], hit['base'], hit['offset'],
                           hit['original_source']['container_offset']) for hit in unequal],
                         [(0x61218324, 0x2020, 0xca, 0x2545d0),
                          (0x61218324, 0x7020, 0xca, 0x255c78)])
        for hit in unequal:
            self.assertEqual([item['value'] for item in hit['literals']], [1, 0])
            self.assertEqual(hit['following']['controls'], [0x5824, 0xcfe2])
            self.assertEqual([item['value'] for item in hit['following']['literals']], [0, 1])
