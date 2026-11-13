import json
import os
import struct
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from host_ef_study import (ROUTE, capture_census, frames, static_report,
                           text_rows)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HOST = CORPUS / 'mi078'
CAPTURES = CORPUS / 'fantom-unit-2026-11-12' / 'link-and-panel-captures'
HAS_HOST = HOST.exists() and all(find_spec(m) for m in ('capstone', 'elftools'))
HAS_CAPTURES = CAPTURES.exists()

# Reply handlers checking a copied message's source byte against 0xE1:
# the kind-9 selector-6 callback 00be9fa0 and the selector 0d/0e callbacks
# 00c0f5d0/00c0fe18 (host-core1-bridge-followup.md service table).
STACK_SOURCE_E1 = (0xbe9fdc, 0xc0f610, 0xc0fe58)


@unittest.skipUnless(
    HAS_HOST, 'Pinned mi078 host corpus and ELF/Capstone readers required')
class SettingsSendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = static_report(HOST)

    def test_route_dispatch_is_unchanged_from_run1_census(self):
        # 391 direct calls to 00be4270, 46 with immediate route 0xEF.
        self.assertEqual(self.report['route_calls_total'], 391)
        self.assertEqual(self.report['ef_route_calls'], 46)

    def test_every_ef_route_sits_in_a_kind_constructing_function(self):
        # Each 0xEF site's enclosing function constructs kind 7 (parameter
        # block), kind 8 (companion) or kind 9 (service envelope).
        for entry, info in self.report['ef_functions'].items():
            self.assertTrue(info['constructor_kinds'], entry)
            self.assertTrue(
                set(info['constructor_kinds'])
                <= {'kind7', 'kind7-wrapper', 'kind8',
                    'kind9', 'kind9-wrapper'}, entry)

    def test_exactly_two_functions_pair_kind7_with_kind8_to_ef(self):
        # The measured kind-7/kind-8 companion pairing (388 pairs in the
        # slider trace) needs senders building both; exactly the level/system
        # parameter functions at 0xc01ec0 and 0xc02010 do.
        paired = sorted(entry for entry, info in
                        self.report['ef_functions'].items()
                        if {'kind7-wrapper', 'kind8'}
                        <= set(info['constructor_kinds']))
        self.assertEqual(paired, ['0xc01ec0', '0xc02010'])

    def test_reply_source_compares_are_e1_e2_only_no_ef(self):
        # Recovered reply handlers check a copied message's source byte
        # against 0xE1 (three stack-copy sites) and the version client against
        # 0xE1/0xE2. No recovered compare uses 0xEF on a frame byte at all.
        self.assertEqual(self.report['compares']['0xe1'],
                         ['0xb899d8', '0xbe9fdc', '0xc0f610', '0xc0fe58',
                          '0xcf9cbc', '0xcf9d48', '0xcfa1ac', '0xcfa1c8'])
        self.assertEqual(self.report['compares']['0xe2'],
                         ['0xb44b90', '0xb45210', '0xcf9cc4', '0xcf9d54',
                          '0xcfa1b8', '0xcfa1d4'])
        self.assertEqual(self.report['compares']['0xef'],
                         ['0xb894b8', '0xbf1f44', '0xc345e4', '0xce8264',
                          '0xd6bfec', '0xe88eb0', '0xeaa884', '0xef5dec'])
        # The three stack-copy source checks load [sp, #0x29] before cmp.
        for site in STACK_SOURCE_E1:
            self.assertIn('ldrb w0, [sp, #0x29]',
                          ' '.join(self.report['compare_contexts'][f'{site:#x}']))
        # No 0xEF compare sits in the input worker's dispatch range.
        for site in self.report['compares']['0xef']:
            self.assertFalse(0xbe1a50 <= int(site, 16) < 0xbe1e50, site)


@unittest.skipUnless(
    HOST.exists() and HAS_CAPTURES and find_spec('capstone'),
    'Pinned mi078 and saved unit captures required')
class CaptureCrossCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = capture_census(CAPTURES)

    def test_every_written_frame_parses_and_carries_byte1_zero(self):
        # Measured: all writes carry source byte 1 = 0x00 (run 1, all traces).
        self.assertEqual(set(self.census), {'slider.trace.raw',
                                            'rest.trace.raw',
                                            'local.trace.raw',
                                            'local2.trace.raw'})
        for name, row in self.census.items():
            self.assertEqual(row['write_byte1_values'], [0], name)

    def test_slider_settings_traffic_shape(self):
        # Measured on the unit: 388 kind-7 selector-0x0E blocks to 0xEF, each
        # immediately followed by a kind-8 companion; reads only kind-9 status
        # sourced 0xE1. Nothing sourced 0xEF or 0xE2 was ever read back.
        slider = self.census['slider.trace.raw']
        self.assertEqual(slider['ef_shapes'],
                         {"(7, 14, 5)": 388, "(8, 0, 7)": 388})
        self.assertEqual(slider['kind7_followed_by_kind8'], 388)
        self.assertEqual(slider['read_byte1_values'], [225])
        self.assertEqual(slider['read_shapes'], {"(9, 225, 96, 9, 112)": 9})

    def test_local_switch_settings_shape(self):
        # Measured: Local Switch toggling sends 37 kind-7 selector-1 blocks
        # (system parameter 0xCF) with the same kind-8 companion shape.
        local2 = self.census['local2.trace.raw']
        self.assertEqual(local2['ef_shapes'],
                         {"(7, 1, 5)": 37, "(8, 0, 7)": 37})
        self.assertEqual(local2['kind7_followed_by_kind8'], 37)
        # No capture ever read a frame sourced 0xEF (or 0xE2).
        for name, row in self.census.items():
            self.assertNotIn(239, row['read_byte1_values'], name)
            self.assertNotIn(226, row['read_byte1_values'], name)


class FrameParserTests(unittest.TestCase):
    def test_short_and_long_frame_layout(self):
        # The measured settings pair, byte for byte from the slider trace:
        # kind-7 selector-0x0E block and its kind-8 companion, both short
        # 12-byte frames (the companion's byte 0 is 0x10: kind 8, inline 7).
        short7 = bytes([14, 0, 0xef, 0x0e, 0, 0, 0, 7, 0x54, 0, 0x0a, 5])
        short8 = bytes([16, 0, 0xef, 0, 0x0e, 0, 0, 0, 0, 0, 0x77, 7])
        rows = list(frames(short7 + short8))
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0]['kind'], rows[0]['destination'],
                          rows[0]['selector'], rows[0]['variable']),
                         (7, 0xef, 0x0e, False))
        self.assertEqual(rows[0]['payload'], '0000000754')
        self.assertEqual((rows[1]['kind'], rows[1]['byte1'],
                          rows[1]['destination']), (8, 0, 0xef))
        self.assertEqual(rows[1]['payload'], '0e000000000077')
        # A long frame still parses: kind 9 with a 112-byte payload, the
        # measured status envelope shape (16-byte header + payload).
        long9 = (bytes([19, 0xe1, 0x60, 9, 0, 0, 0, 0, 0x10, 0x16, 0x2d, 0])
                 + struct.pack('<I', 112) + b'\0' * 112)
        rows = list(frames(long9))
        self.assertEqual((rows[0]['kind'], rows[0]['byte1'],
                          rows[0]['destination'], rows[0]['selector'],
                          rows[0]['payload_length']), (9, 0xe1, 0x60, 9, 112))


if __name__ == '__main__':
    unittest.main()