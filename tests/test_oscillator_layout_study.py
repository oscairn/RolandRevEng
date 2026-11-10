import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from header_study import layout, UnsupportedLayout
from oscillator_layout_study import candidates, CONTEXTS


def authored_packet(header, pool):
    return [header, *CONTEXTS[header][0], *pool]


class CandidateTests(unittest.TestCase):
    def test_extension_can_alias_an_address_so_sine_frequency_is_not_an_arity_proof(self):
        words = authored_packet(0xbd4b, [0x000c, 0x000d, 0, 0])
        report = candidates(words)
        self.assertEqual([row['arithmetic_families'] for row in report['candidates']], [[0], [1]])
        for row in report['candidates']:
            literal = [f for f in row['fields'] if f['role'] == 'literal']
            self.assertEqual([(f['operation'], f['slot'], f['offset'], f['width']) for f in literal],
                             [(0, 0, 0x12, 4)])
        extended = report['candidates'][0]['fields']
        extension = next(f for f in extended if f['role'] == 'extension')
        address = next(f for f in extended if f['role'] == 'address')
        self.assertEqual(extension['offset'], address['offset'])
        self.assertFalse(report['fully_decoded'])
        self.assertEqual(len(report['opaque_operations']), 3)

    def test_two_short_operations_and_long_dual_level_operation_are_constrained(self):
        rate = candidates(authored_packet(0x5c07, [0, 0]))
        self.assertEqual([row['arithmetic_families'] for row in rate['candidates']], [[1, 1]])
        self.assertEqual(rate['candidates'][0]['padding'], 1)
        levels = candidates(authored_packet(0xa50c, [0x6a40, 0, 0, 0, 0, 0]))
        self.assertEqual([row['arithmetic_families'] for row in levels['candidates']], [[0]])
        literals = [f for f in levels['candidates'][0]['fields'] if f['role'] == 'literal']
        self.assertEqual([(f['slot'], f['offset'], f['width']) for f in literals], [(0, 0x12, 3), (1, 0x15, 3)])

    def test_shared_extension_does_not_identify_which_arithmetic_operation_owns_it(self):
        report = candidates(authored_packet(0x4d0d, [0x2037, 0x0013, 0, 0, 0, 0, 0, 0]))
        self.assertEqual([row['arithmetic_families'] for row in report['candidates']], [[0, 1], [1, 0]])
        dc_owners = []
        for row in report['candidates']:
            dc = [f for f in row['fields'] if f['role'] == 'literal' and f['offset'] == 0x11 and f['width'] == 4]
            self.assertEqual(len(dc), 1)
            dc_owners.append(dc[0]['operation'])
            self.assertEqual(row['padding'], 1)
        self.assertEqual(dc_owners, [0, 1])
        self.assertTrue(any('overlaps' in row['error'] for row in report['rejected']))

    def test_unobserved_controls_headers_and_truncation_fail_closed(self):
        words = authored_packet(0xa50c, [0x6a40, 0, 0, 0, 0, 0])
        changed = words.copy()
        changed[2] ^= 1
        for invalid in ([], [0x0902, 0x0401], changed):
            with self.subTest(invalid=invalid), self.assertRaises(UnsupportedLayout):
                candidates(invalid)
        with self.assertRaises(ValueError):
            candidates(words[:-1])
        for header, pool in [(0xbd4b, [0, 0, 0, 0]), (0x5c07, [0, 0]),
                             (0xa50c, [0x6a40, 0, 0, 0, 0, 0]),
                             (0x4d0d, [0x2037, 0x0013, 0, 0, 0, 0, 0, 0])]:
            with self.subTest(header=header), self.assertRaises(UnsupportedLayout):
                layout(authored_packet(header, pool))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                     'Capstone or local artifacts not prepared')
class CorpusTests(unittest.TestCase):
    def test_owner_proven_records_match_all_surviving_candidates(self):
        from oscillator_layout_study import study
        result = study()
        expected = {0xbd4b: [[0], [1]], 0x5c07: [[1, 1]], 0xa50c: [[0]], 0x4d0d: [[0, 1], [1, 0]]}
        self.assertEqual(len(result['packets']), 4)
        self.assertFalse(result['fully_decoded'])
        seen = set()
        for packet in result['packets']:
            self.assertEqual([row['arithmetic_families'] for row in packet['candidates']], expected[packet['header']])
            for anchor in packet['anchors']:
                seen.add(anchor['name'])
                self.assertEqual(len(anchor['matches']), len(packet['candidates']))
                self.assertTrue(all(match['fields'] for match in anchor['matches']))
        self.assertEqual(seen, {'SineFreq', 'SineLev', 'ImpulseRate', 'ImpulseLev', 'WhiteLev', 'DCLev'})


if __name__ == '__main__':
    unittest.main()
