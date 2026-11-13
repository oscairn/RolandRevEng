"""Checks for the CORE1 load-route and readback census study.

tools/core1_load_route_study.py answers which stock code actually calls the
recovered bmc0 CORE1 program-load route (StackWriteDspProg 0x112f582 and its
manager vtable upload slots 0x18/0x1c/0x20) and which code reads program or
DRAM-IO state back (ReadLiteralRaw 0x112f6e8; the boot verify routine at
0x610010d0 comparing program and DRAM-IO apertures against stored bytes).
Pure checks run without the corpus; the pinned-image checks need
BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import core1_load_route_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'b0c1a.bin'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ModelTests(unittest.TestCase):
    def test_upload_slot_targets_are_the_manager_wrappers(self):
        self.assertEqual(study.UPLOAD_SLOT_TARGETS,
                         {0x18: 0x01135099, 0x1c: 0x011350a9, 0x20: 0x011350b5})
        self.assertEqual(study.COEF_SLOT_TARGETS[0x70], 0x01132abf)
        self.assertEqual(study.COEF_SLOT_TARGETS[0x74], 0x1132b89)

    def test_expected_upload_sites_are_sorted(self):
        for expected in (study.EXPECTED_UPLOAD_SITES_18,
                         study.EXPECTED_UPLOAD_SITES_1C,
                         study.EXPECTED_UPLOAD_SITES_20):
            self.assertEqual(expected, sorted(expected))
            self.assertEqual(len(expected), len(set(expected)))
        # The boot verify routine's program and DRAM-IO phase calls.
        self.assertIn(0x61001118, study.EXPECTED_UPLOAD_SITES_18)
        self.assertIn(0x61001156, study.EXPECTED_UPLOAD_SITES_1C)
        self.assertIn(0x6101efb0, study.EXPECTED_UPLOAD_SITES_20)
        # One function at 0x6103050c calls both upload slots back to back
        # (0x61030584 through byte 0x1c, 0x61030594 through byte 0x20).
        self.assertEqual(set(study.EXPECTED_UPLOAD_SITES_1C)
                         & set(study.EXPECTED_UPLOAD_SITES_20),
                         {0x61030594})
        self.assertEqual(set(study.EXPECTED_UPLOAD_SITES_18)
                         & (set(study.EXPECTED_UPLOAD_SITES_1C)
                            | set(study.EXPECTED_UPLOAD_SITES_20)),
                         set())

    def test_anchor_list_covers_flag_byte_and_ports(self):
        addresses = {address for address, _ in study.ANCHORS}
        # The shared exclusion flag byte load and the literal-port command
        # encodings must be pinned, since the census reads them.
        self.assertIn(0x01131c96, addresses)   # WriteDspProgAllImpl ldrb [0x2008480c]
        self.assertIn(0x0112f726, addresses)   # ReadLiteralRaw command store
        self.assertIn(0x0112f554, addresses)   # WriteLiteralRaw ubfx 19-bit addr
        self.assertIn(0x0112f5a4, addresses)   # StackWriteDspProg even check
        # The boot verify strings and both veneer cells.
        self.assertIn(0x610014f4, addresses)
        self.assertIn(0x61001518, addresses)
        self.assertIn(0x61076a82, addresses)
        self.assertIn(0x61076aaa, addresses)


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned b0c1a.bin image and capstone required')
        cls.core = study.load_image(IMAGE)

    def test_anchors_are_byte_exact(self):
        _, problems = study.check_anchors(self.core)
        self.assertEqual(problems, [])

    def test_payload_sha_matches_pinned_image(self):
        import hashlib
        digest = hashlib.sha256(self.core.data).hexdigest()
        self.assertEqual(digest, study.SHA256)

    def test_upload_slots_reach_exactly_the_expected_sites(self):
        sites = {disp: study.virtual_slot_sites(self.core, disp)
                 for disp in study.UPLOAD_SLOTS}
        self.assertEqual(sites[0x18], study.EXPECTED_UPLOAD_SITES_18)
        self.assertEqual(sites[0x1c], study.EXPECTED_UPLOAD_SITES_1C)
        self.assertEqual(sites[0x20], study.EXPECTED_UPLOAD_SITES_20)

    def test_vtable_quads_name_the_wrappers(self):
        quads = study.vtable_quads(self.core)
        self.assertEqual(quads[hex(0x61176490)], 0x01131bfd)
        self.assertEqual(quads[hex(0x61176494)], 0x01135099)
        self.assertEqual(quads[hex(0x61176498)], 0x011350a9)
        self.assertEqual(quads[hex(0x6117649c)], 0x011350b5)
        self.assertEqual(quads[hex(0x611764e0)], 0x011327e7)
        self.assertEqual(quads[hex(0x611764ec)], 0x01132abf)

    def test_direct_caller_counts(self):
        callers, _, _, _ = study.census(self.core)
        self.assertEqual(callers['StackWriteDspProg']['direct_bl'],
                         [0x01131cd4, 0x01131f6c, 0x01132240])
        self.assertEqual(callers['StackFillDspProgNop']['direct_bl'], [0x011324c2])
        self.assertEqual(callers['GetDspProgAdrs']['direct_bl'], [])
        self.assertEqual(len(callers['WriteLiteralRaw']['direct_bl']), 9)
        self.assertEqual(len(callers['ReadLiteralRaw']['direct_bl']), 5)
        self.assertEqual(callers['GetExeMode']['direct_bl'], [])
        self.assertEqual(callers['GetExeMode']['veneers'], [])
        self.assertEqual(callers['GetExeMode']['word_pointers'], [])

    def test_veneer_cells_resolve_to_boot_routines(self):
        callers, _, _, _ = study.census(self.core)
        get_cell = callers['GetDspProgAdrs']['veneers']
        set_cell = callers['SetExeMode']['veneers']
        self.assertEqual(get_cell, [0x61076a82])
        self.assertEqual(set_cell, [0x61076aaa])
        self.assertEqual(callers[f'veneer_cell_{hex(get_cell[0])}']['direct_bl'],
                         [0x61001194])
        self.assertEqual(callers[f'veneer_cell_{hex(set_cell[0])}']['direct_bl'],
                         study.EXPECTED_BOOT_WALK_SITES)

    def test_report_is_ok(self):
        callers, upload_sites, coef_sites, quads = study.census(self.core)
        self.assertEqual(study.check_anchors(self.core)[1], [])
        self.assertEqual(upload_sites[0x18], study.EXPECTED_UPLOAD_SITES_18)
        self.assertEqual(upload_sites[0x1c], study.EXPECTED_UPLOAD_SITES_1C)
        self.assertEqual(upload_sites[0x20], study.EXPECTED_UPLOAD_SITES_20)
        self.assertEqual(quads[hex(0x61176490)], 0x01131bfd)


if __name__ == '__main__':
    unittest.main()