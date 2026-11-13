import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import command_count, packets, swap_words
from four_b_five_c_crosscheck import (TRAP_CODE, TRAP_SLOT, calibration, is_fe_window,
                                      scan_segments, study, vocab_crosscheck)
from header_family_crosscheck import ranked_choices
from header_study import layout


def stored(words):
    """Stored LE32 form of a logical big-endian halfword stream, word padded."""
    stream = b''.join(word.to_bytes(2, 'big') for word in words)
    if len(stream) % 4:
        stream += b'\0\0'
    return b''.join(word[::-1] for word in (stream[i:i + 4] for i in range(0, len(stream), 4)))


def segment(words):
    return (0x4020, len(words) * 2, len(words) * 2, 0)


class InvariantTests(unittest.TestCase):
    RULE = ranked_choices()

    def test_fitted_predictions_are_positional(self):
        self.assertEqual(self.RULE[0x4b], (0, 1, 2, 4))
        self.assertEqual(self.RULE[0x5c], (1, 1, 2, 4))
        self.assertEqual(self.RULE[0x5a], (1, 1, 2, 2))
        self.assertEqual(self.RULE[TRAP_CODE], (1, 2, 2, 4))

    def test_anchor_packet_keeps_window_control_in_transfer_slot(self):
        # The admitted 4709 anchor: two fe-window controls in the two transfer slots.
        words = [0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0]
        counts, _ = scan_segments(stored(words), [segment(words)], self.RULE)
        self.assertEqual(counts['decoded_packets'], 1)
        self.assertEqual(counts['rejected_packets'], 0)

    def test_anchor_with_window_control_in_short_slot_fails(self):
        # Move 7fe6 into slot 0 (predicted long): C1 must raise.
        words = [0x4709, 0x7fe6, 0x454b, 0x3fe4, 0x044b, 0, 4, 0, 0]
        with self.assertRaises(ValueError):
            scan_segments(stored(words), [segment(words)], self.RULE)

    def test_anchor_with_too_many_window_controls_fails(self):
        # A 58xx anchor predicts one transfer slot; two window controls breach C1.
        words = [0x5809, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0, 0]
        with self.assertRaises(ValueError):
            scan_segments(stored(words), [segment(words)], self.RULE)

    def test_four_b_five_c_window_control_must_sit_in_slot3(self):
        # The real GASSDLY 4b09 shape 1822 5c87 8e0a b9b3 has no window control;
        # swap slot 3's control for a window word: C2 requires it in slot 3 (ok),
        # while the same word in slot 2 must raise.
        ok = [0x4b09, 0x1822, 0x5c87, 0x8e0a, 0x5fe2, 0, 4, 0, 0]
        counts, _ = scan_segments(stored(ok), [segment(ok)], self.RULE)
        self.assertEqual(counts['code4b_fe3_packets'], 1)
        bad = [0x4b09, 0x1822, 0x5fe2, 0x8e0a, 0xb9b3, 0, 4, 0, 0]
        with self.assertRaises(ValueError):
            scan_segments(stored(bad), [segment(bad)], self.RULE)

    def test_five_a_window_control_raises(self):
        # 5a predicts no transfer slot; any window control breaches C3.
        words = [0x5a09, 0x0422, 0x4525, 0x1c90, 0x5fe2, 0, 4, 0, 0]
        with self.assertRaises(ValueError):
            scan_segments(stored(words), [segment(words)], self.RULE)

    def test_trap_6209_window_in_slot0_is_counted_not_fatal(self):
        words = [0x6209, 0x6fe4, 0x9450, 0xded4, 0x8fe2, 0, 0x13, 0x369f, 0xbe00]
        counts, _ = scan_segments(stored(words), [segment(words)], self.RULE)
        self.assertEqual(counts['code62_packets'], 1)
        self.assertEqual(counts['code62_slot0_fe'], 1)

    def test_count1_window_calibration_fails_closed(self):
        words = [0x0902, 0x3fe4, 0x0001]  # 09 (short) with a window control
        counts, vocab = scan_segments(stored(words), [segment(words)], self.RULE)
        self.assertEqual(counts['count1_09_fe_window'], 1)
        # calibration() pins classes 08..0b to zero window occurrences; 09 now has
        # one, so it must raise.
        with self.assertRaises(ValueError):
            calibration(vocab)
        words = [0x0c02, 0x8fe0, 0x0001]  # 0c (transfer) with a window control
        counts, vocab = scan_segments(stored(words), [segment(words)], self.RULE)
        result = calibration(vocab)
        self.assertEqual(result['0c']['fe_window_occurrences'], 1)

    def test_truncated_packet_is_counted_not_decoded(self):
        # count 4 but one control word: packets() raises, scan_segments counts the
        # framing failure and never decodes the segment.
        words = [0x4709, 0x044b]
        counts, _ = scan_segments(stored(words), [segment(words)], self.RULE)
        self.assertEqual(counts['unframeable_segments'], 1)
        self.assertNotIn('decoded_packets', counts)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_QSPI = all((CORPUS / name).exists() for name in
               ('zen_arm64', 'b0c1a.bin', 'b1c1a.bin',
                'crossmodel/jupiter-x/MI077_C1A_up.bin',
                'crossmodel/mc101/RPG69_C1A_up.bin',
                'crossmodel/sh-4d/DD013_C1A_up.bin'))


@unittest.skipUnless(HAS_QSPI, 'Pinned cross-image corpus required')
class CorpusTests(unittest.TestCase):
    @staticmethod
    def load():
        return json.loads((ROOT / 'local/four-b-five-c-run11.json').read_text()) \
            if (ROOT / 'local/four-b-five-c-run11.json').exists() else study()

    def test_pinned_totals(self):
        totals = self.load()['totals']
        self.assertEqual(totals['count4_fitted'], 38441)
        self.assertEqual(totals['decoded_packets'], 27138)
        self.assertEqual(totals['unsupported_packets'], 11303)
        self.assertEqual(totals['packets_4b5c'], 2257)
        self.assertEqual(totals['fe3_packets'], 1520)
        self.assertEqual(totals['no_fe_packets'], 737)
        self.assertEqual(totals['fe3_packets'] + totals['no_fe_packets'],
                         totals['packets_4b5c'])
        self.assertEqual(totals['code5a_packets'], 276)
        self.assertEqual(totals['code62_packets'], 306)
        self.assertEqual(totals['code62_slot0_fe'], 28)

    def test_pinned_calibration(self):
        cal = self.load()['totals']['calibration']
        self.assertEqual([cal[code]['fe_window_occurrences'] for code in
                          ('08', '09', '0a', '0b')], [0, 0, 0, 0])
        self.assertEqual(cal['0c']['fe_window_occurrences'], 7579)
        self.assertEqual(cal['0c']['fe_window_distinct'], 16)
        self.assertEqual(cal['0c']['occurrences'], 10967)

    def test_pinned_vocab_crosscheck(self):
        vocab = self.load()['totals']['vocab_crosscheck']
        self.assertEqual(vocab['long8_distinct'], 194)
        self.assertEqual(vocab['short9_distinct'], 269)
        self.assertEqual(vocab['overlap'], 6)
        self.assertEqual(vocab['4b_slot0']['distinct'], 28)
        self.assertEqual(vocab['4b_slot0']['short9_inside'], 0)
        self.assertEqual(vocab['5c_slot01']['short9_inside'], 22)
        self.assertEqual(vocab['5c_slot01']['long8_inside'], 5)

    def test_per_image_counts(self):
        result = self.load()
        for name, count4 in (('zen_arm64', 2266), ('b0c1a.bin', 5204), ('b1c1a.bin', 1253),
                             ('MI077_C1A_up.bin', 14923), ('RPG69_C1A_up.bin', 2116),
                             ('DD013_C1A_up.bin', 12679)):
            self.assertEqual(result[name]['count4_fitted'], count4, name)
        self.assertEqual(result['zen_arm64']['packets_4b5c'], 152)
        self.assertEqual(result['b0c1a.bin']['packets_4b5c'], 316)
        self.assertEqual(result['b1c1a.bin']['packets_4b5c'], 61)
        self.assertEqual(result['MI077_C1A_up.bin']['packets_4b5c'], 801)
        self.assertEqual(result['RPG69_C1A_up.bin']['packets_4b5c'], 117)
        self.assertEqual(result['DD013_C1A_up.bin']['packets_4b5c'], 810)


if __name__ == '__main__':
    unittest.main()