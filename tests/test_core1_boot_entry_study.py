"""Checks for the CORE1 boot-entry chain study.

tools/core1_boot_entry_study.py binds how the boot verify routine 0x610010d0
(run 11's only end-to-end load-route user) is reached: reset vector word
0x1100004 = 0x1100e55 -> reset entry clears registers, configures SCB AIRCR,
enters ERAM, then bl 0x1102986 (boot task) -> bl 0x113439e (veneer cell, its
only BL caller) -> 0x610010d1. The router-reached path (byte-1 0xFE -> bl
0x1102970 -> tail bl 0x1102986) and the interrupt tick handler sharing state
word 0x200800d8 are pinned too. Pure checks run without the corpus; the
pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import core1_boot_entry_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'b0c1a.bin'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ModelTests(unittest.TestCase):
    def test_chain_constants_are_consistent(self):
        self.assertEqual(study.RESET_VECTOR_WORD, 0x1100004)
        self.assertEqual(study.RESET_ENTRY, 0x01100e55)
        self.assertEqual(study.RESET_MAIN, 0x01100e42)
        self.assertEqual(study.BOOT_TASK, 0x01102986)
        self.assertEqual(study.VERIFY_VENEER, 0x0113439e)
        self.assertEqual(study.VERIFY_CALLER, 0x01102a3a)
        self.assertEqual(study.VERIFY_ROUTINE, 0x610010d0)
        self.assertEqual(study.BOOT_TASK_SCHEDULER, 0x01102970)

    def test_anchors_cover_vectors_and_veneer(self):
        addresses = {address for address, _ in study.ANCHORS}
        for required in (study.RESET_VECTOR_WORD, study.TICK_VECTOR_WORD,
                         study.SYSTICK_VECTOR_WORD, study.VERIFY_VENEER,
                         study.VERIFY_CALLER, study.RESET_MAIN,
                         study.BOOT_TASK_SCHEDULER, 0x0111ea8e):
            self.assertIn(required, addresses)

    def test_verify_veneer_bytes_encode_the_target(self):
        anchor = dict(study.ANCHORS)
        movw = int.from_bytes(bytes.fromhex(anchor[study.VERIFY_VENEER]), 'little')
        movt = int.from_bytes(bytes.fromhex(anchor[study.VERIFY_VENEER + 4]), 'little')
        # Thumb-2 MOVW/MOVT T3 encoding; halfwords are stored little-endian,
        # so the first halfword of each pair is the low 16 bits of the word.
        def imm16(word):
            hw1, hw2 = word & 0xffff, word >> 16
            return (((hw1 & 0xf) << 12) | (((hw1 >> 10) & 1) << 11)
                    | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xff))
        target = (imm16(movt) << 16) | imm16(movw)
        self.assertEqual(target, study.VERIFY_ROUTINE + 1)


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

    def test_vectors_hold_the_pinned_entries(self):
        self.assertEqual(self.core.u32(study.RESET_VECTOR_WORD), study.RESET_ENTRY)
        self.assertEqual(self.core.u32(study.TICK_VECTOR_WORD),
                         study.TICK_HANDLER_THUMB)
        self.assertEqual(self.core.u32(study.SYSTICK_VECTOR_WORD),
                         study.SYSTICK_HANDLER_THUMB)

    def test_chain_is_exactly_one_path_to_the_boot_task(self):
        report = study.census(self.core)
        self.assertEqual(report['boot_task_callers'], [hex(study.RESET_MAIN)])
        self.assertEqual(report['verify_veneer_callers'], [hex(study.VERIFY_CALLER)])
        self.assertEqual(report['scheduler_callers'], [hex(0x111ea8e)])

    def test_report_is_ok(self):
        import hashlib
        self.assertEqual(hashlib.sha256(self.core.data).hexdigest(), study.SHA256)
        _, problems = study.check_anchors(self.core)
        self.assertEqual(problems, [])
        report = study.census(self.core)
        self.assertEqual(report['boot_task_callers'], [hex(study.RESET_MAIN)])
        self.assertEqual(report['verify_veneer_callers'], [hex(study.VERIFY_CALLER)])


if __name__ == '__main__':
    unittest.main()