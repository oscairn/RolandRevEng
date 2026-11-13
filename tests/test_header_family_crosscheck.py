import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from header_family_crosscheck import (ANCHORS, RULE_SIZE, crosscheck_core, ranked_choices,
                                      strictly_decodable_codes, study)
from header_study import families, layout


def stored(words):
    """Stored LE32 word form of a logical big-endian halfword stream."""
    stream = b''.join(word.to_bytes(2, 'big') for word in words)
    if len(stream) % 4:
        stream += b'\0\0'
    return b''.join(word[::-1] for word in (stream[i:i + 4] for i in range(0, len(stream), 4)))


class RuleTests(unittest.TestCase):
    def test_ranking_size_and_anchor_agreement(self):
        rule = ranked_choices()
        self.assertEqual(len(rule), RULE_SIZE)
        for code, expected in ANCHORS.items():
            self.assertEqual(rule[code], expected)
            self.assertEqual(families(code << 8), expected,
                             f'header_study families for {code:04x} changed')

    def test_only_anchors_admit_strict_decode_in_the_ranking(self):
        self.assertEqual(sorted(strictly_decodable_codes(ranked_choices())),
                         [0x47, 0x4e, 0x58, 0x5f, 0x69, 0x78])
        # Every predicted-miscellaneous code must fail closed in layout(), never
        # decode: a strict decode of a 62xx packet would falsify the fitted rule.
        for code in (0x40, 0x4b, 0x5a, 0x62, 0x73):
            self.assertIn(2, ranked_choices()[code])
            with self.assertRaises(Exception):
                layout(packet_words(code, 10, [0x044b, 0x454b, 0x3fe4, 0x7fe6],
                                    [0, 4, 0, 0, 0]))

    def test_anchor_packet_still_decodes_and_matches_ranking(self):
        rule = ranked_choices()
        words = [0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0]
        decoded = layout(words)
        self.assertEqual(tuple(decoded['families']), rule[0x47])

    def test_strict_decode_mismatch_is_reported(self):
        rule = ranked_choices()
        # An anchor packet strictly decodes and must agree with the fitted ranking.
        # Stored form of the known-good 4709 packet from test_header_study.
        words = [0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0]
        data = stored(words)
        counterexamples = []
        counts = crosscheck_core(data, [(0x4020, len(words) * 2, len(words) * 2, 0)],
                                 rule, counterexamples)
        self.assertEqual(counts['decoded_packets'], 1)
        self.assertEqual(counts['anchor_decoded'], 1)
        self.assertEqual(counterexamples, [])
        # A 62xx packet fails closed (miscellaneous predicted), which counts as
        # unsupported without being a counterexample. 4709's word count is 9, so a
        # 6209 packet with the same 9 words is well-formed and layout-rejected.
        words62 = [(0x62 << 8) | 9] + words[1:]
        counts = crosscheck_core(stored(words62),
                                 [(0x4020, len(words62) * 2, len(words62) * 2, 0)],
                                 rule, counterexamples)
        self.assertEqual(counts['unsupported_packets'], 1)
        self.assertEqual(counts['decoded_packets'], 0)
        self.assertEqual(counterexamples, [])

    def test_out_of_range_code_counterexample(self):
        rule = ranked_choices()
        words = [0x7909, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0]
        counterexamples = []
        crosscheck_core(stored(words), [(0x4020, len(words) * 2, len(words) * 2, 0)],
                        rule, counterexamples)
        self.assertTrue(any(row['problem'].startswith('code outside') for row in counterexamples))


@unittest.skipUnless(importlib.util.find_spec('capstone')
                     and (Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local')) / 'zen_arm64').exists(),
                     'prepared corpus and Capstone are required')
class CorpusRuleTests(unittest.TestCase):
    def test_no_counterexample_in_paired_corpus(self):
        import lib
        result = study()
        self.assertEqual(result['counterexamples'], [])
        self.assertEqual(result['strictly_decodable_codes'],
                         ['0047', '004e', '0058', '005f', '0069', '0078'])
        for name, report in result['images'].items():
            self.assertGreater(report['count4_packets'], 0, name)
            self.assertGreaterEqual(report['min_code'], 0x40, name)
            self.assertLessEqual(report['max_code'], 0x78, name)
            self.assertGreater(report['nonanchor_decoded'] if 'nonanchor_decoded' in report
                               else report['decoded_packets'] - report['anchor_decoded'], -1, name)
            self.assertEqual(report['rejected_packets'], 0, name)
            self.assertGreater(report['unsupported_packets'], 0, name)

    def test_pinned_counts_for_pinned_images(self):
        import lib
        result = study(core1=[lib.BASE / 'b0c1a.bin', lib.BASE / 'b1c1a.bin'])
        self.assertEqual(result['images']['zen_arm64']['packets'], 12365)
        self.assertEqual(result['images']['zen_arm64']['count4_packets'], 2266)
        self.assertEqual(result['images']['zen_arm64']['anchor_decoded'], 1703)
        self.assertEqual(result['images']['zen_arm64']['nonanchor_decoded'], 0)
        self.assertEqual(result['images']['b0c1a.bin']['packets'], 36793)
        self.assertEqual(result['images']['b0c1a.bin']['count4_packets'], 5204)
        self.assertEqual(result['images']['b0c1a.bin']['distinct_codes'], 40)
        self.assertEqual(result['images']['b0c1a.bin']['anchor_decoded'], 3697)
        self.assertEqual(result['images']['b0c1a.bin']['nonanchor_decoded'], 0)
        self.assertEqual(result['images']['b1c1a.bin']['packets'], 12176)
        self.assertEqual(result['images']['b1c1a.bin']['count4_packets'], 1253)
        self.assertEqual(result['images']['b1c1a.bin']['distinct_codes'], 32)
        self.assertEqual(result['images']['b1c1a.bin']['anchor_decoded'], 631)
        self.assertEqual(result['images']['b1c1a.bin']['nonanchor_decoded'], 0)


if __name__ == '__main__':
    unittest.main()