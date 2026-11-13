"""Pinned checks of the bmc1 receive path and its byte-1 handling.

Checks tools/core1_b1_route_study.py against the pinned b1c1a payload: the
bmc1 ASGN-analog/CUMDWRx/helper/parser instruction anchors, the two TBB
tables, the derived byte-1 consumption sets, and the cross-image compare
census against bmc0's committed scanner numbers. Pure checks run without the
corpus; the pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from core1_b1_route_study import (ANCHORS, B0_CENSUS, CANDIDATES,
                                  CUMDWRX_COMMANDS, HELPER_BYTE1,
                                  PARSER_BYTE1, check_anchors,
                                  census_immediates, check_value_sets)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
CORE1 = CORPUS / 'b1c1a.bin'
CORE0 = CORPUS / 'b0c1a.bin'
HAS_CORE1 = (CORE1.exists() and find_spec('capstone') is not None)
HAS_BOTH = HAS_CORE1 and CORE0.exists()


class ValueSetTests(unittest.TestCase):
    def test_consumption_sets_are_consistent(self):
        self.assertEqual(check_value_sets(), [])

    def test_parser_consumes_ef_not_e1_e2(self):
        self.assertIn(0xef, PARSER_BYTE1)
        self.assertNotIn(0xe1, PARSER_BYTE1)
        self.assertNotIn(0xe2, PARSER_BYTE1)

    def test_bmc1_adds_command_53(self):
        self.assertIn(0x53, CUMDWRX_COMMANDS)
        self.assertEqual(len(CUMDWRX_COMMANDS), 9)


class EncodingTests(unittest.TestCase):
    def test_anchors_carry_expected_thumbs(self):
        # The helper's TBB covers nine byte-1 values 0x80..0x88.
        helper_tbb = next(row for row in ANCHORS if row[0] == 0x0112a1f6)
        self.assertEqual(helper_tbb[1], 'efeecfbf9ded14aedf')

    def test_census_candidate_values_match_wire_byte1_set(self):
        self.assertEqual(set(CANDIDATES),
                         {0x02, 0x07, 0x60, 0x61, 0x62, 0x63, 0x64, 0x75,
                          0xe0, 0xe1, 0xe2, 0xef})


@unittest.skipUnless(HAS_CORE1, 'Pinned b1c1a CORE1 payload and capstone required')
class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1_b1_route_study import core1
        cls.core = core1(CORE1)

    def test_all_anchors_match_pinned_bytes(self):
        rows = check_anchors(self.core)
        bad = [row for row in rows if not row['match']]
        self.assertEqual(bad, [])

    def test_parser_tbb_table_bytes(self):
        offset = self.core.offset(0x0110f728)
        self.assertEqual(self.core.data[offset:offset + 15],
                         bytes.fromhex('f8f7a3f8f6f5f4f30835f2c7f8f9f0'))

    def test_parser_tbb_decodes_to_expected_regions(self):
        base = 0x0110f728
        tbl = [self.core.data[self.core.offset(base) + i] for i in range(15)]
        # Nibble 11 (0x80..0x8f records) reaches the shared byte-1 chain at
        # 0x110f8b6; nibble 8/9/12/14 reach their own bodies; 0xf* target the
        # nibble-1..3/12/14 shared region.
        self.assertEqual(base + 2 * tbl[11], 0x0110f8b6)
        self.assertEqual(base + 2 * tbl[8], 0x0110f738)
        self.assertEqual(base + 2 * tbl[9], 0x0110f792)

    def test_ef_body_reaches_only_from_parser_chain(self):
        # 0x1110176 (the 0xEF body) is reachable only via beq.w at 0x0110fb90.
        offset = self.core.offset(0x0110fb90)
        self.assertEqual(self.core.data[offset:offset + 4],
                         bytes.fromhex('00f0f182'))

    def test_walker_bound_is_sixteen_entries(self):
        offset = self.core.offset(0x011101d6)
        self.assertEqual(self.core.data[offset:offset + 2], b'\x10\x2d')

    def test_getter_returns_b1_singleton(self):
        offset = self.core.offset(0x01110cfc)
        self.assertEqual(self.core.data[offset:offset + 2], b'\xf7\x48')
        # The getter's literal pool at 0x011110dc holds the singleton object.
        self.assertEqual(self.core.u32(0x011110dc), 0x61402164)


@unittest.skipUnless(HAS_BOTH, 'Pinned b0c1a/b1c1a payloads and capstone required')
class CrossImageTests(unittest.TestCase):
    def test_b1_census_differs_from_b0_committed_numbers(self):
        counts, _ = census_immediates(self.core())
        self.assertEqual(counts.get(0xef), 47)
        self.assertEqual(counts.get(0xe1), 14)
        self.assertEqual(counts.get(0xe2), 6121)
        self.assertNotEqual(counts.get(0xef), B0_CENSUS[0xef])
        self.assertNotEqual(counts.get(0xe1), B0_CENSUS[0xe1])

    def test_b0_census_reference_still_reproduces(self):
        counts, _ = census_immediates(self.b0_core())
        self.assertEqual({k: counts.get(k, 0) for k in sorted(B0_CENSUS)},
                         B0_CENSUS)

    @classmethod
    def core(cls):
        from core1_b1_route_study import core1
        return core1(CORE1)

    @classmethod
    def b0_core(cls):
        from core1_b1_route_study import core1
        return core1(CORE0)


if __name__ == '__main__':
    unittest.main()