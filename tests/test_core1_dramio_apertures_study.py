"""Checks for the CORE1 DRAM-IO aperture study.

tools/core1_dramio_apertures_study.py decodes the bmc0 CORE1 DRAM-IO program
aperture tables at 0x0113a970/0x0113a988 (run 11/12 follow-up): the closed-form
24-word array (bank b, DSP d -> 0x41440000 + b*0x40000 + d*0x100000), the
GetDramIOProgAdrs bank selector, the TBB upload dispatches of the boot verify
routine's two phases (static decode cross-checked against Unicorn), the literal
port tables that follow the aperture array, and the page-copy contract of
CopyDramIOProgPage. Pure checks run without the corpus; the pinned-image
checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import core1_dramio_apertures_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'b0c1a.bin'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ModelTests(unittest.TestCase):
    def test_closed_form_layout_matches_pinned_words(self):
        self.assertEqual(study.expected_aperture_words()[:4],
                         [0x41440000, 0x41540000, 0x41640000, 0x41740000])
        self.assertEqual(study.expected_aperture_words()[-1], 0x4194c000)
        self.assertEqual(len(study.expected_aperture_words()),
                         study.BANKS * study.BANK_WORDS)

    def test_phase_expectations_are_self_consistent(self):
        # The phase-1 TBB table bytes are 04 1a 06 1a 1a 1a 08 00 at 0x610010e6,
        # each scaled by two: only indices 0, 2, 6 dispatch to an upload.
        self.assertEqual(study.PHASE1_TBB_INSN, 0x610010e2)
        self.assertEqual(study.PHASE2_TBB_INSN, 0x61001128)
        self.assertEqual(sorted(study.PHASE1_TBB_OBJECTS), [0, 2, 6])
        self.assertEqual(sorted(study.PHASE2_UPLOAD_SITES), [0, 2, 6])

    def test_object_headers_decode_as_tag_count_list(self):
        # tag and next tag are consecutive (0x10000/0x10001, 0x10200/0x10201,
        # 0x10600), so the header is tag:u32, count:u8 at +2, list:u32 at +4.
        self.assertEqual(study.PHASE1_TBB_OBJECTS[0], 0x61085dc4)
        self.assertEqual(study.PHASE2_UPLOAD_OBJECTS[6], ('sram_deref', 0x20084bb4))


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

    def test_aperture_words_match_closed_form(self):
        self.assertEqual(study.aperture_words(self.core),
                         study.expected_aperture_words())

    def test_tbb_decode_matches_unicorn_single_step(self):
        unicorn = study.unicorn_tbb_targets(study.PHASE2_TBB_INSN, 4, IMAGE)
        if unicorn is None:
            self.skipTest('unicorn unavailable')
        self.assertEqual(study.tbb_targets(self.core, study.PHASE2_TBB_INSN, 4),
                         [unicorn[i] for i in range(4)])

    def test_verify_objects_have_single_stock_records(self):
        rows = study.object_records(self.core)
        self.assertEqual([row['count'] for row in rows], [1] * len(rows))
        stub = rows[1]['records'][0]
        self.assertEqual(stub['length'], 16)
        # The 16-byte DRAM-IO stub payload itself.
        offset = self.core.offset(int(rows[1]['records'][0]['word3'])
                                  if isinstance(rows[1]['records'][0]['word3'], int)
                                  else int(rows[1]['records'][0]['word3'], 16))
        self.assertEqual(self.core.data[offset:offset + 4], b'\xff\xff\x7f\x80')

    def test_report_is_ok(self):
        report = study.report(IMAGE, skip_unicorn=True)
        self.assertTrue(report['ok'])
        self.assertEqual(report['anchor_problems'], [])
        self.assertTrue(report['aperture_words_match_closed_form'])
        # Only bank0/bank1 are consumed by upload/read paths; banks 2/3 only by
        # the mute-counter pair.
        self.assertTrue(report['aperture_users']['bank0'])
        self.assertTrue(report['aperture_users']['bank3'])


if __name__ == '__main__':
    unittest.main()