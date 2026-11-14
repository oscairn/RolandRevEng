"""Tests for the CBmcDspMgr virtual-call site attribution study.

Pure tests (parser/model checks) always run. The pinned-image class needs
BMC_CORPUS_DIR pointing at the prepared b0c1a.bin.
"""
import os
import struct
import unittest
from pathlib import Path

from core1_mgr_vtable_sites_study import (ANCHORS, EXPECTED_SITES,
                                          MGR_CELLS, MGR_NAME, MGR_VTABLE_ADDR_POINT,
                                          corrected_virtual_slot_sites,
                                          load_image, report)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin'
PINNED_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


class CorrectedScanModel(unittest.TestCase):
    """Model checks over a synthetic code buffer, no image required."""

    def _scan(self, code, disp):
        import capstone
        from core1 import Core1
        core = load_image.__wrapped__ if False else None  # unused; scan needs core
        # Build a minimal fake core: corrected_virtual_slot_sites uses core.data
        # and core.eram_offset only.
        class Fake:
            pass
        fake = Fake()
        fake.data = code
        fake.eram_offset = len(code)
        return corrected_virtual_slot_sites(fake, disp)

    def test_stale_load_not_counted(self):
        # ldr r1,[r0,#0x14]; ldr r1,[r0,#0x10]; blx r1  -> counts only #0x10.
        code = bytes.fromhex('4a68' '0969' '8847')
        sites = self._scan(code, 0x14)
        self.assertEqual(sites, [])
        sites = self._scan(code, 0x10)
        self.assertEqual([s & 0xffff for s in sites], [4])

    def test_data_processing_between_loads_stops_scan(self):
        # ldr r1,[r0,#0x14]; movs r1,#1; blx r1 -> the ldr is stale, no match.
        code = bytes.fromhex('4a68' '0121' '8847')
        self.assertEqual(self._scan(code, 0x14), [])
        self.assertEqual(self._scan(code, 0x10), [])

    def test_immediate_match(self):
        # ldr r1,[r0,#0x14]; blx r1 counts.
        code = bytes.fromhex('4a68' '8847')
        self.assertEqual([s & 0xffff for s in self._scan(code, 0x14)], [0])


class PinnedImageAttribution(unittest.TestCase):
    """Requires BMC_CORPUS_DIR with the pinned b0c1a.bin."""

    def setUp(self):
        if not CORPUS.exists():
            self.skipTest(f'pinned image not present at {CORPUS}')

    def test_report_ok(self):
        result = report(CORPUS)
        self.assertTrue(result['ok'], result['anchor_problems'])
        self.assertEqual(result['anchors_checked'], len(ANCHORS))
        self.assertEqual(result['payload_sha256'], PINNED_SHA256)

    def test_flag_wrapper_sites_present(self):
        result = report(CORPUS)
        # Byte 0x10/0x14 sites include the boot-adjacent ITCM handlers and the
        # ERAM lifecycle sites; the manager-internal helpers never appear
        # (0x1131bc7/0x1131bfd are reached only through the vtable words).
        sites10 = [int(s, 16) for s in result['corrected_sites']['0x10']]
        sites14 = [int(s, 16) for s in result['corrected_sites']['0x14']]
        for expected in (0x11021c0, 0x1102760, 0x61030578, 0x61083d1e):
            self.assertIn(expected, sites10)
        for expected in (0x11021f0, 0x1102794, 0x61030560, 0x61034cb8):
            self.assertIn(expected, sites14)
        # The stale-match members removed versus runs 11/17 must be absent.
        self.assertNotIn(0x61030584, sites10)   # 0x61030584 blx is #0x1c
        self.assertNotIn(0x6103056c, sites14)   # 0x6103056c blx is #0x18
        self.assertNotIn(0x61030594, sites14)   # 0x61030594 blx is #0x20
        self.assertNotIn(0x110e06a, sites14)    # 0x110e06a blx is #0x10
        self.assertNotIn(0x1128fae, sites10)    # 0x1128fae blx is #0x04
        self.assertNotIn(0x1128fe8, sites10)    # 0x1128fe8 blx is #0x04
        self.assertNotIn(0x1128ff2, sites10)    # 0x1128ff2 blx is #0x00
        self.assertNotIn(0x1128fae, sites10)
        # Upload byte lists shrink accordingly.
        self.assertNotIn(0x61030578,
                         [int(s, 16) for s in result['corrected_sites']['0x18']])
        self.assertNotIn(0x6103bee8,
                         [int(s, 16) for s in result['corrected_sites']['0x1c']])
        self.assertNotIn(0x61030584,
                         [int(s, 16) for s in result['corrected_sites']['0x20']])

    def test_manager_cells_limited_references(self):
        result = report(CORPUS)
        refs = result['manager_cell_word_refs']
        self.assertEqual(refs['0x20084b8c'],
                         ['0x610014e0', '0x61001824'])
        self.assertEqual(refs['0x20084ba0'], ['0x610014e4'])
        self.assertEqual(refs['0x20084bb4'], ['0x610014e8'])


if __name__ == '__main__':
    unittest.main()