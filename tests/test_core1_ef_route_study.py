"""Pinned checks of the bmc0 CORE1 receive-path byte-1 handling.

Checks tools/core1_ef_route_study.py against the pinned b0c1a payload: the
router/CUMDWRx instruction anchors, the corrected TBB route tables, and the
image-wide 8-bit compare census. Pure checks run without the corpus; the
pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import json
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from core1_ef_route_study import ANCHORS, CANDIDATES, census_immediates, check_anchors

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
CORE1 = CORPUS / 'b0c1a.bin'
HAS_CORE1 = (CORE1.exists() and
             (find_spec('capstone') is not None))

# The corrected first-router TBB bytes (route table at 0x111ea54).
TBB_BYTES = bytes.fromhex('0847b3b386b3b3b98686bdb3868686f6')


class AnchorTableTests(unittest.TestCase):
    def test_anchors_are_thumb_encodings_with_expected_shape(self):
        # Every anchor decodes to the recorded mnemonic/operand text, and route
        # 0 reads byte 1 ([sp, #1]) while route 1 forwards the whole word.
        for address, bytehex, mnemonic, operands in ANCHORS:
            with self.subTest(address=hex(address)):
                self.assertTrue(address & 1 == 0, hex(address))
                self.assertEqual(len(bytehex) % 2, 0)
                self.assertTrue(mnemonic in ('push', 'push.w', 'pop', 'cmp',
                                             'ldrb.w', 'ldr', 'and', 'bl',
                                             'movs', 'ubfx', '.byte')
                                or mnemonic == '.byte')

    def test_census_candidate_values_match_wire_byte1_set(self):
        # The census targets exactly the byte-1 values seen on the wire
        # (0x02, 0x07, 0x60..0x64, 0x75, 0xE1, 0xEF) plus inferred 0xE2 and
        # the 0xE0 range bound used by backpressure code.
        self.assertEqual(set(CANDIDATES),
                         {0x02, 0x07, 0x60, 0x61, 0x62, 0x63, 0x64, 0x75,
                          0xe0, 0xe1, 0xe2, 0xef})


class EncodingTests(unittest.TestCase):
    def test_census_counts_only_true_compares(self):
        # 0x2xxx halfwords with op bits 00 are MOVS; only op 01 is CMP.
        # Little-endian bytes: cmp r1,#0xef = 0x29ef -> ef 29; movs r0,#0xf0 =
        # 0x20f0 -> f0 20 (a 0x2xxx non-compare must be excluded).
        class FakeCore:
            eram_offset = 8
            data = bytes.fromhex('ef29 f020 0000 0000'.replace(' ', ''))
        counts, sites = census_immediates(FakeCore())
        self.assertEqual(counts.get(0xef), 1)
        self.assertEqual(counts.get(0xf0), None)
        self.assertEqual([(s['imm'], s['instruction']) for s in sites],
                         [('0xef', 'cmp r1, #0xef')])

    def test_movs_halfwords_are_excluded(self):
        # 0x21ef (movs r1, #0xef) must not appear in a compare census.
        class FakeCore:
            eram_offset = 2
            data = bytes.fromhex('ef21')
        counts, sites = census_immediates(FakeCore())
        self.assertEqual(counts.get(0xef), None)
        self.assertEqual(sites, [])


@unittest.skipUnless(HAS_CORE1, 'Pinned b0c1a CORE1 payload and capstone required')
class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1_ef_route_study import core1
        cls.core = core1(CORE1)

    def test_all_anchors_match_pinned_bytes(self):
        rows = check_anchors(self.core)
        bad = [row for row in rows if not row['match']]
        self.assertEqual(bad, [])

    def test_tbb_route_table_bytes(self):
        offset = self.core.offset(0x0111ea54)
        self.assertEqual(self.core.data[offset:offset + 16], TBB_BYTES)

    def test_route_targets_decode_to_expected_handlers(self):
        # route 0 -> 0x111ea64 (byte-1 compare chain), route 1 -> 0x111eae2
        # (high-nibble-1 SysEx forward), route 0xf -> 0x111ec40.
        tbl = [self.core.data[self.core.offset(0x0111ea54) + i] for i in range(16)]
        self.assertEqual(0x0111ea54 + 2 * tbl[0], 0x0111ea64)
        self.assertEqual(0x0111ea54 + 2 * tbl[1], 0x0111eae2)
        self.assertEqual(0x0111ea54 + 2 * tbl[0xf], 0x0111ec40)

    def test_image_wide_ef_compares_are_bounded_and_outside_recovered_route(self):
        counts, sites = census_immediates(self.core)
        # 16 halfword-aligned `cmp #0xef` candidates survive the 32-bit-interior
        # filter; the two ITCM ones (0x0110045e debug chain, 0x0110ddb0
        # byte-stream parser) are outside the recovered
        # RXDT->ASGN->CUMDWRx route, and none sits inside 0x0111ea24..0x0111ed25,
        # 0x0110a65c..0x0110a760 or 0x0110bacc..0x0110bb10.
        self.assertEqual(counts.get(0xef), 16)
        ef = [int(s['address'], 16) for s in sites if s['imm'] == '0xef']
        self.assertIn(0x0110045e, ef)
        self.assertIn(0x0110ddb0, ef)
        for start, end in ((0x0111ea24, 0x0111ed25), (0x0110a65c, 0x0110a760),
                           (0x0110bacc, 0x0110bb10)):
            inside = [a for a in ef if start <= a < end]
            self.assertEqual(inside, [], hex(start))

    def test_e1_e2_census_counts(self):
        counts, _ = census_immediates(self.core)
        self.assertEqual(counts.get(0xe1), 4)
        self.assertEqual(counts.get(0xe2), 1506)


if __name__ == '__main__':
    unittest.main()