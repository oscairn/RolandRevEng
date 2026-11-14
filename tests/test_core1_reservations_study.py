"""Checks for the CORE1 program-reservation census study.

tools/core1_reservations_study.py answers the A2 question queued by run 13:
which per-DSP program slots exist on bmc0 CORE1, who owns each, and which are
unused in the stock image. It byte-pins the boot verify routine's phase-1 /
phase-2 dispatches, decodes the five reservation entries (header
(count<<16)|(dsp<<8)|phase, list pointer, 16-byte records), checks the zero
tail after the MDSP entry, the program-aperture table, the manager cells
(zero in both scatter records), the constructor pools, and scans the whole
image for other header-form words. Pure checks run without the corpus; the
pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import core1_reservations_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'b0c1a.bin'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ModelTests(unittest.TestCase):
    def test_header_pack_round_trip(self):
        self.assertEqual(study.pack_header(1, 0, 0), 0x00010000)
        self.assertEqual(study.pack_header(1, 0, 1), 0x00010001)
        self.assertEqual(study.pack_header(1, 2, 0), 0x00010200)
        self.assertEqual(study.pack_header(1, 2, 1), 0x00010201)
        self.assertEqual(study.pack_header(1, 6, 0), 0x00010600)
        fields = study.unpack_header(0x00010201)
        self.assertEqual((fields['count'], fields['dsp'], fields['phase']),
                         (1, 2, 1))

    def test_header_pack_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            study.pack_header(0, 0, 0)
        with self.assertRaises(ValueError):
            study.pack_header(1, 7, 2)

    def test_expected_entries_cover_five_slots(self):
        self.assertEqual(len(study.EXPECTED_ENTRIES), 5)
        covered = {(e['dsp'], e['phase']) for e in study.EXPECTED_ENTRIES}
        self.assertEqual(covered, {(0, 0), (0, 1), (2, 0), (2, 1), (6, 0)})

    def test_program_aperture_closed_form(self):
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[0], 0x41480000)
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[5], 0x41980000)
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[6], 0x41260000)
        self.assertEqual(len(study.PROGRAM_APERTURE_WORDS), 7)


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned b0c1a.bin image and capstone required')
        cls.core = study.load_image(IMAGE)
        cls.report = study.report(IMAGE)

    def test_payload_sha_matches_pinned_image(self):
        import hashlib
        self.assertEqual(hashlib.sha256(self.core.data).hexdigest(),
                         study.SHA256)

    def test_anchors_are_byte_exact(self):
        self.assertEqual(self.report['anchor_problems'], [])
        self.assertGreater(self.report['anchors_checked'], 0)

    def test_phase1_tbb_dispatches_only_dsp0_2_mdsp(self):
        targets = [int(t, 16) for t in self.report['phase1_tbb_targets']]
        self.assertEqual(targets[0], 0x610010ee)
        self.assertEqual(targets[2], 0x610010f2)
        self.assertEqual(targets[6], 0x610010f6)
        for index in (1, 3, 4, 5):
            self.assertEqual(targets[index], study.PHASE1_SKIP)
        self.assertEqual(targets[7], 0x610010e6)

    def test_stock_entries_match_pinned_values(self):
        self.assertTrue(self.report['entries_match_expectations'])
        self.assertTrue(self.report['ok'])
        by_key = {(e['dsp'], e['phase']): e for e in self.report['entries']}
        self.assertEqual(int(by_key[(0, 0)]['list'], 16), 0x61085db4)
        lengths = {(e['dsp'], e['phase']):
                   e['records'][0]['length'] for e in self.report['entries']}
        self.assertEqual(lengths[(0, 0)], 0x13e4)
        self.assertEqual(lengths[(2, 0)], 0xce6)
        self.assertEqual(lengths[(6, 0)], 0xc956)
        self.assertEqual(lengths[(0, 1)], 16)
        self.assertEqual(lengths[(2, 1)], 16)

    def test_no_sixth_entry_after_mdsp(self):
        self.assertTrue(all(int(w, 16) == 0
                            for w in self.report['zero_tail_after_mdsp_entry']))

    def test_program_aperture_table_matches_closed_form(self):
        self.assertTrue(self.report['program_aperture_matches_closed_form'])
        self.assertEqual(self.report['program_aperture_table'][0], '0x41480000')
        self.assertEqual(self.report['program_aperture_table'][6], '0x41260000')

    def test_stock_occupancy_ranges(self):
        ranges = {(r['dsp'], r['phase']): (int(r['start'], 16), int(r['end'], 16))
                  for r in self.report['stock_occupancy']}
        self.assertEqual(ranges[(0, 0)], (0x41480000, 0x41480000 + 0x13e4))
        self.assertEqual(ranges[(2, 0)], (0x41680000, 0x41680000 + 0xce6))
        self.assertEqual(ranges[(6, 0)], (0x41260000, 0x41260000 + 0xc956))
        self.assertEqual(ranges[(0, 1)], (0x41440000, 0x41440010))
        self.assertEqual(ranges[(2, 1)], (0x41640000, 0x41640010))

    def test_objects_referenced_only_by_verify_pools(self):
        self.assertEqual(
            self.report['object_references'],
            {'0x61085dc4': ['0x610014d4'], '0x61085dcc': ['0x610014ec'],
             '0x61085dd4': ['0x610014d8'], '0x61085ddc': ['0x610014f0'],
             '0x61085de4': ['0x610014dc']})

    def test_manager_cells_zero_in_image(self):
        self.assertEqual(set(self.report['manager_cells_in_image'].values()),
                         {'0x0'})

    def test_manager_ctor_pools(self):
        self.assertEqual(self.report['manager_ctor_pools']['0x61001824'],
                         '0x20084b8c')
        self.assertEqual(self.report['manager_ctor_pools']['0x61001830'],
                         hex(study.MANAGER_VTABLE_ADDRESS_POINT))
        self.assertEqual(self.report['manager_ctor_pools']['0x61001828'],
                         '0x61085dec')

    def test_header_form_scan_includes_boot_entries(self):
        hits = self.report['header_form_hits_elsewhere']
        for entry in study.EXPECTED_ENTRIES:
            match = any(hit['address'] == hex(entry['address'])
                        and hit['list'] == hex(entry['list']) for hit in hits)
            self.assertTrue(match, hex(entry['address']))


if __name__ == '__main__':
    unittest.main()