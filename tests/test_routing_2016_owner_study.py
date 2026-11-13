"""Checks for the routing-2016 owner study.

tools/routing_2016_owner_study.py pins the native routing context: the
CSimDSP4Routing::VSubProc slot stores (2016..2019 analog), the two-float
condition gate, the allocation/ownership chain
(EfctLoadFixedAlg -> Core Init -> core+0x230) and the vtable slot 4 dispatch.
Pure checks run without the corpus; the pinned-image check needs
BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import routing_2016_owner_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'zen_arm64'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ConditionModelTests(unittest.TestCase):
    def test_condition_model_matches_decoded_semantics(self):
        self.assertEqual(study.check_condition_model(), [])

    def test_bypass_is_tight(self):
        # [x8+0x678]==0 forces bypass regardless of the second float.
        self.assertEqual(study.condition_word(0.0, 1.0), 0)
        self.assertEqual(study.condition_word(0.0, -3.0), 0)
        self.assertEqual(study.condition_word(2.0, 0.0), 0)

    def test_dispatch_requires_both_nonzero(self):
        self.assertEqual(study.condition_word(1.0, 1.0), 1)
        self.assertEqual(study.condition_word(1e-30, -1.0), 1)


class SlotTests(unittest.TestCase):
    def test_vtable_slot_arithmetic(self):
        self.assertEqual(study.check_slots(), [])
        self.assertEqual(study.vtable_slot(0xa76210, 0xa761f0), 4)
        self.assertEqual(study.vtable_slot(0xa761f0, 0xa761f0), 0)
        with self.assertRaises(ValueError):
            study.vtable_slot(0xa76211, 0xa761f0)

    def test_anchor_addresses_are_distinct(self):
        addresses = [row[0] for row in study.ANCHORS]
        self.assertEqual(len(addresses), len(set(addresses)))


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned zen_arm64 image and capstone required')
        cls.data = study.load_image(IMAGE)

    def test_anchors_are_byte_exact(self):
        _, problems = study.check_anchors(self.data)
        self.assertEqual(problems, [])

    def test_owner_chain_addresses_resolve_in_image(self):
        # The whole claimed chain must lie inside bounded image functions.
        import lib
        import os
        os.environ.setdefault('BMC_CORPUS_DIR', str(CORPUS))
        import importlib
        importlib.reload(lib)
        for address in (0x165fd8, 0x16bc68, 0x292220, 0x41288, 0x34c0f8,
                        0x413d0, 0x34c244, 0x3b1cd8):
            start, end = lib.func(address)
            self.assertTrue(end > start)

    def test_routing_ctor_allocates_before_call(self):
        # 0x41c234 mov w0,#0x1b40 precedes bl 0x6d8614 and the ctor call.
        self.assertEqual(self.data[0x41234:0x41238].hex(), '00688352')

    def test_tool_report_is_clean(self):
        report = study.report(IMAGE)
        self.assertTrue(report['ok'])
        self.assertEqual(report['anchors_checked'], len(study.ANCHORS))


if __name__ == '__main__':
    unittest.main()