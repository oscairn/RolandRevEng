import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble, packets
from label_target_study import resolve
from mute_mode_study import resolve_entry, scan_first_packet


class MuteTests(unittest.TestCase):
    def test_all_four_masked_words_replace_both_low_bits_and_only_first_match(self):
        for original in range(0xff70, 0xff74):
            for muted in (False, True):
                stream = assemble([[0x1e03, original, 0xff71]])
                before = stream[:]
                result = scan_first_packet(stream, muted)
                self.assertEqual((result['word_index'], result['byte_offset']), (1, 2))
                self.assertEqual(result['original_word'], original)
                self.assertEqual(result['replacement_word'], 0xff70+muted)
                self.assertEqual(result['scanned_halfwords'], 1)
                self.assertEqual(result['role'], 'control')
                self.assertFalse(result['execution_ready'])
                self.assertEqual(stream, before)

    def test_matching_payload_is_selected_without_any_control_family_check(self):
        stream = assemble([[0x1e05, 0x0fe0, 0x1fe2, 0xff72, 0xff73]])
        result = scan_first_packet(stream, True)
        self.assertEqual(result['role'], 'payload')
        self.assertEqual(result['byte_offset'], 6)
        self.assertEqual(result['replacement_word'], 0xff71)
        # A model which limits the scan to command_count(header) would miss this write.
        self.assertEqual(result['scanned_halfwords'], 3)

    def test_return_and_ff75_do_not_supply_the_required_gate(self):
        for stream in (assemble([[0x0b02, 0x00f8]]), assemble([[0x0a02, 0xff75]]),
                       assemble([[0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]), b'\0\1'):
            result = scan_first_packet(stream, False)
            self.assertTrue(result['firmware_search_assert'])
            self.assertIsNone(result['word_index'])
        # Generic packet framing calls 001f compact, but the firmware loop would read 30 words.
        self.assertEqual(packets(b'\0\x1f'), [(0, [31])])
        self.assertRaisesRegex(ValueError, 'scan extent', scan_first_packet, b'\0\x1f', False)

    def test_bounds_types_and_extra_packets_are_rejected_offline(self):
        packet = assemble([[0x0a02, 0xff71]])
        for stream in (b'', packet[:-1], packet[:-2], packet+packet, bytearray(packet), None):
            self.assertRaises(ValueError, scan_first_packet, stream, False)
        for muted in (0, 1, None, 'true'):
            self.assertRaises(ValueError, scan_first_packet, packet, muted)

    def test_entry_resolution_does_not_invent_label_writer_capacity_or_parity_checks(self):
        raw = struct.pack('<HHBB', 0x4020, 0x20, 0, 1)
        reservations = [dict(base=0xfffffff0, capacity=2)]
        self.assertEqual(resolve_entry(raw, reservations), 0x10)
        self.assertRaises(ValueError, resolve, raw, reservations)
        self.assertEqual(resolve_entry(raw, None), 0x4020)
        self.assertEqual(resolve_entry(struct.pack('<HHBB', 1, 3, 0, 1), [dict(base=0)]), 3)
        self.assertRaises(ValueError, resolve_entry, raw, [])
        self.assertRaises(ValueError, resolve_entry, raw, [dict(base=True)])
        self.assertRaises(ValueError, resolve_entry, raw, [dict(base=0)]*128)
        self.assertRaises(ValueError, resolve_entry, raw[:-1], None)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS, 'Pinned Fantom CORE1 and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_real_method_and_five_actual_fetdrive_first_packets(self):
        from core1 import Core1
        from mute_mode_study import report
        core = Core1(CORPUS/'b0c1a.bin')
        result = report(core)
        self.assertEqual([row['entry'] for row in result['fetdrive_placements']],
                         [0x4020, 0x8040, 0x9040, 0xa040, 0x3020])
        self.assertTrue(all(row['replacement_word'] == 0xff70 for row in result['fetdrive_placements']))
        self.assertTrue(all(row['byte_offset'] == 2 for row in result['fetdrive_placements']))
        self.assertFalse(result['label_capacity_checked'])
        self.assertFalse(result['packet_family_checked'])
        self.assertFalse(result['hardware_mute_effect_verified'])
        self.assertFalse(result['execution_ready'])
        core.data += b'changed'
        self.assertRaisesRegex(ValueError, 'pinned Fantom', report, core)

    def test_changed_resolver_or_search_instruction_is_rejected(self):
        from core1 import Core1
        from mute_mode_study import report
        from dramio_owner_study import expect
        core = Core1(CORPUS/'b0c1a.bin')
        def changed(core, address, mnemonic, operands):
            return expect(core, address, mnemonic, '#wrong' if address == 0x1133be4 else operands)
        with patch('dramio_owner_study.expect', side_effect=changed):
            self.assertRaises(ValueError, report, core)


if __name__ == '__main__':
    unittest.main()
