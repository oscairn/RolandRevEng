import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from five_e09_inventory import SHAPES, command_count, payload_bytes, resource_words, scan_segments, shape_of
from bmc_dsp import literal, swap_words

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_QSPI = all((CORPUS / f).exists() for f in
               ('zen_arm64', 'b0c1a.bin', 'b1c1a.bin',
                'crossmodel/jupiter-x/MI077_C1A_up.bin',
                'crossmodel/mc101/RPG69_C1A_up.bin',
                'crossmodel/sh-4d/DD013_C1A_up.bin'))


class ShapeTests(unittest.TestCase):
    WORDS = [0x5e09, 0x1e50, 0x5d52, 0x4014, 0x0fe6, 0x3c00, 0xa400, 0x000d, 0x013f,
             0x0001]  # trailing compact NOP keeps the synthetic stream word-padded

    def test_known_shapes_fail_closed_on_unknown_controls(self):
        self.assertIsNotNone(shape_of(self.WORDS))
        words = list(self.WORDS)
        words[3] = 0x4015
        self.assertIsNone(shape_of(words))
        words = list(self.WORDS)
        words[4] = 0x0fe7  # odd transfer address
        self.assertIsNone(shape_of(words))
        words = list(self.WORDS)
        words[1] = 0x1e51
        self.assertIsNone(shape_of(words))

    def test_scan_frames_padded_stream_and_pins_length(self):
        # A trailing compact NOP word (the stock stream padding) must not change the
        # decoded 5e09 record; the record pins the packet's own 9-word length.
        for extra in ([], [0x0001]):
            words = list(self.WORDS) + extra
            segment = (0x4020, 2 * len(words), 0x100, 0)
            records, counts = scan_segments(self.stored(words), [segment])
            self.assertEqual(counts['framed_segments'], 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['length'], 9)
            self.assertEqual(records[0]['controls'], ['1e50', '5d52', '4014', '0fe6'])
            self.assertEqual([off for off, _ in records[0]['resources']], [4, 6])

    def test_gain_bias_literals_are_pinned(self):
        payload = bytes.fromhex('3c00a400000d013f')
        self.assertEqual(literal(payload[0:2]), 1.75)
        self.assertEqual(literal(payload[2:4]), -0.25)

    def test_resource_offsets_must_be_even_and_inside_payload(self):
        shape = SHAPES[(0x1e50, 0x5d52, 0x4014, 0x0fe6)]
        words = list(self.WORDS)
        self.assertEqual([off for off, _ in resource_words(b'', 0x28c, words, shape)], [4, 6])
        words[8] = 0x013e  # constant tail is fine; resource words are raw values
        self.assertEqual([value for _, value in resource_words(b'', 0x28c, words, shape)],
                         [0x000d, 0x013e])
        words[7] = 0x013d
        self.assertEqual([value for _, value in resource_words(b'', 0x28c, words, shape)],
                         [0x013d, 0x013e])
        # Changed gain or bias literals must raise.
        words[5] = 0x3c01
        self.assertRaises(ValueError, list, resource_words(b'', 0x28c, words, shape))
        words[5] = 0x3c00
        words[6] = 0xa500
        self.assertRaises(ValueError, list, resource_words(b'', 0x28c, words, shape))

    def test_scan_framing_and_shape_fail_closed(self):
        segment = (0x4020, 2 * len(self.WORDS), 2 * len(self.WORDS), 0)
        words = list(self.WORDS)
        words[3] = 0x4015  # unknown control shape
        with self.assertRaises(ValueError):
            scan_segments(self.stored(words), [segment])
        words[3] = 0x4014
        records, counts = scan_segments(self.stored(words), [segment])
        self.assertEqual(counts['framed_segments'], 1)
        self.assertEqual(len(records), 1)
        self.assertEqual([off for off, _ in records[0]['resources']], [4, 6])

    @staticmethod
    def stored(words):
        # scan_segments takes the stored LE32 form; pad odd word counts like stock data.
        logical = b''.join(word.to_bytes(2, 'big') for word in words)
        if len(logical) % 4:
            logical += b'\x00\x00'
        return swap_words(logical)


@unittest.skipUnless(HAS_QSPI, 'Pinned cross-image corpus required')
class CorpusTests(unittest.TestCase):
    def test_cross_image_inventory_and_gass_invariants(self):
        from five_e09_inventory import study
        report = study()
        self.assertEqual(report['totals']['five_e_packets'], 117)
        self.assertEqual(report['totals']['shape_1e50'], 28)
        self.assertEqual(report['totals']['shape_2c80'], 56)
        self.assertEqual(report['totals']['shape_0cc8'], 28)
        self.assertEqual(report['totals']['shape_4050'], 5)
        self.assertEqual(report['totals']['distinct_gass_resource_pairs'], 26)
        self.assertEqual(report['zen_arm64']['counts']['five_e_packets'], 8)
        self.assertEqual(report['b0c1a.bin']['counts']['five_e_packets'], 17)
        self.assertEqual(report['b1c1a.bin']['counts']['five_e_packets'], 1)
        self.assertEqual(report['MI077_C1A_up.bin']['counts']['five_e_packets'], 45)
        self.assertEqual(report['RPG69_C1A_up.bin']['counts']['five_e_packets'], 1)
        self.assertEqual(report['DD013_C1A_up.bin']['counts']['five_e_packets'], 45)
        # The negative-bias study's unknown group: 28 GASS-type 5d52 uses, all with
        # gain 1.75, bias -.25 and exactly the offsets 4/6 as variable words.
        for name in ('zen_arm64', 'b0c1a.bin', 'MI077_C1A_up.bin', 'DD013_C1A_up.bin'):
            self.assertEqual(report[name]['gass_5d52_packets'],
                             report[name]['counts']['shape_1e50'])
        self.assertFalse(report['totals'].get('opcode_admission'))

    def test_unframeable_segments_are_counted_not_fatal(self):
        from five_e09_inventory import study
        report = study()
        # The inventories contain segments the strict subset parser rejects; the scan
        # counts them and still fully covers every 5e09 packet with a known shape.
        self.assertGreaterEqual(report['totals']['unframeable_segments'], 135)
        for name, rep in report.items():
            if name in ('totals',):
                continue
            self.assertNotIn('unknown 5e09 control shape', str(rep))

    def test_b0c1a_gass_context_resource_pairs_vary_per_placement(self):
        from five_e09_inventory import study
        report = study()['b0c1a.bin']
        rows = [row for row in report['five_e_packets'] if row['controls'][1] == '5d52']
        self.assertEqual(len(rows), 4)
        self.assertEqual({row['offset'] for row in rows}, {0x28c})
        bases = sorted(row['base'] for row in rows)
        self.assertEqual(bases, [0x4020, 0x8040, 0x9040, 0xa040])
        pairs = {tuple(row['resources']) for row in rows}
        self.assertEqual(len(pairs), 4)
        # Same segment length family: every GASS-type source sits in a 0x5f0 stream.
        self.assertTrue(all(row['length'] == 9 for row in rows))
        # Pinned run-10 facts: the four GASS sources advance by exactly 0x5f0 and
        # the shared dsp6 diagnostic payload is constant with minimum offset 0x1324.
        srcs = sorted(row['source'] for row in rows)
        self.assertEqual([srcs[i + 1] - srcs[i] for i in range(3)], [0x5f0] * 3)
        diags = [row for row in report['five_e_packets']
                 if row['controls'] == ['4050', '1052', '0094', '0fe6']]
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0]['payload'], '0004d000002de000')
        full = study()
        diag_rows = [row for name in full if name != 'totals'
                     for row in full[name]['five_e_packets']
                     if row['controls'] == ['4050', '1052', '0094', '0fe6']]
        self.assertEqual(len(diag_rows), 5)
        self.assertEqual({row['payload'] for row in diag_rows},
                         {'0004d000002de000'})
        self.assertGreaterEqual(min(row['offset'] for row in diag_rows), 0x1324)
        # A GASS-type b0c1a anchor packet is pinned byte-exactly.
        first = next(row for row in rows if row['base'] == 0x4020)
        self.assertEqual(first['payload'], '3c00a400000d013f')

    def test_anchor_addresses_match_the_note(self):
        from five_e09_inventory import study
        report = study()
        # Zen anchor: list 0xa41220, segment base 0x4020, length 0x5ec, source
        # 0x817988, packet offset 0x288 (the note's hexdump anchors).
        zen = [row for row in report['zen_arm64']['five_e_packets']
               if row['controls'] == ['1e50', '5d52', '4014', '0fe6']]
        self.assertEqual([(row['base'], row['source'], row['offset'], row['payload'])
                          for row in zen],
                         [(0x4020, 0x817988, 0x288, '3c00a40000030040'),
                          (0x8000, 0x817f74, 0x288, '3c00a400000301d0')])
        # JUPITER-X first GASS placement (the note's second hexdump).
        jx = [row for row in report['MI077_C1A_up.bin']['five_e_packets']
              if row['controls'] == ['1e50', '5d52', '4014', '0fe6']]
        self.assertIn((0x2020, 0x17621c, 0x28c, '3c00a4000003003f'),
                      [(row['base'], row['source'], row['offset'], row['payload'])
                       for row in jx])
        # SBF325/STTMDLY desktop anchors named in the note.
        sbf = [row for row in report['zen_arm64']['five_e_packets']
               if row['controls'] == ['2c80', 'edf4', '4010', '0fe2']]
        self.assertEqual({(row['base'], row['source']) for row in sbf},
                         {(0x4020, 0x7ecaf0), (0x8000, 0x7ecf60)})
        stt = [row for row in report['zen_arm64']['five_e_packets']
               if row['controls'] == ['0cc8', '5074', '4010', '8fe2']]
        self.assertEqual({(row['base'], row['source']) for row in stt},
                         {(0x4020, 0x7c0cec), (0x8000, 0x7c0fa0)})


if __name__ == '__main__':
    unittest.main()