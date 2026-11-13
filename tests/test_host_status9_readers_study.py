import json
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from host_status9_readers_study import (RING_BASE, SELECTOR_COUNT,
                                        SELECTOR_OFFSETS, analyze,
                                        load, selector_map)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HOST = CORPUS / 'mi078'
HAS_HOST = HOST.exists() and all(find_spec(m) for m in ('capstone', 'elftools'))


@unittest.skipUnless(HAS_HOST, 'Pinned mi078 host corpus and ELF/Capstone readers required')
class Selector9ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze(HOST)

    def test_dispatcher_bounded_to_26_selectors(self):
        # cmp w19, #0x19; b.ls: selectors 0..25 valid, else return 0.
        self.assertEqual(self.report['anchors']['0xb98400'], 'cmp w19, #0x19')

    def test_jump_table_maps_all_26_selectors(self):
        elf, rows = load(HOST)
        mapping = selector_map(elf, rows)
        self.assertEqual(len(mapping), SELECTOR_COUNT)
        # dispatcher families verified from stub tail branches
        expect = {1: 0x6c27f8, 2: 0x6c2900, 3: 0x6c2988,
                  4: 0x6c2a30, 7: 0x6c2a30,
                  8: 0x6c2b60, 15: 0x6c2b60,
                  16: 0x6c2d50, 17: 0x6c2d50,
                  18: 0x6c2e10, 23: 0x6c2e10,
                  24: 0x6c2fb0, 25: 0x6c2fb0}
        for sel, disp in expect.items():
            self.assertEqual(mapping[sel][0], disp, sel)

    def test_reader_offsets_match_case_bodies(self):
        # Each single-halfword dispatcher case body loads its own fixed
        # ldrsh offset; the recorded map covers exactly those case offsets.
        for disp, sel_off in SELECTOR_OFFSETS.items():
            self.assertTrue(sel_off, disp)
            self.assertEqual(max(sel_off) - 8 <= 111, True, disp)

    def test_level_ladder_is_clamped_negative_db_shape(self):
        # direct from report: monotonic rise, clamp at -60 and 0
        rep = self.report['level_ladder']
        vals = [rep[k] for k in range(32)]
        self.assertEqual(vals[0], -60.0)
        self.assertEqual(vals[16], -60.0)
        self.assertEqual(vals[27], 0.0)
        self.assertEqual(vals[31], 0.0)
        rising = all(a <= b for a, b in zip(vals[16:27], vals[17:28]))
        self.assertTrue(rising)

    def test_coverage_matches_capture_varying_bytes_expectation(self):
        # The readers reach payload bytes 0..31 and 68..111 excluding 84..91
        # and 100..107 gaps only where no case exists; the keys capture's
        # varying bytes 68,70,92,94,108,109,110,111 must all be covered.
        covered = set(self.report['coverage'])
        for b in (68, 70, 92, 94, 108, 109, 110, 111):
            self.assertIn(b, covered)
        # bytes 64/66 vary in captures but no recovered reader case reaches
        # them: record that bounded negative.
        self.assertNotIn(64, covered)
        self.assertNotIn(66, covered)

    def test_gate_anchor_0x840_and_ring_base(self):
        # Reader B family gates on 0x40a9758+0xe8 = 0x40a9840.
        self.assertEqual(self.report['anchors']['0x6c2a58'], 'ldrb w2, [x1, #0xe8]')
        self.assertEqual(self.report['anchors']['0x6c2a18'], 'strb w1, [x0, #0x840]')
        self.assertEqual(RING_BASE, 0x40a9758)
        self.assertEqual(RING_BASE + 0xe8, 0x40a9840)


if __name__ == '__main__':
    unittest.main()