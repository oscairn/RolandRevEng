"""Pinned checks of the bmc0 CORE1 byte-1 consumers beyond run 5's route.

Checks tools/core1_ef_319_consumers_study.py against the pinned b0c1a payload:
the route-0 fallthrough helper (0x01126d2e), the ASGN router's second call into
the byte-stream parser (0x0110d962) and the parser's byte-1 dispatch chain.
Pure checks run without the corpus; the pinned-image checks need BMC_CORPUS_DIR
(or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from core1_ef_319_consumers_study import (ANCHORS, HELPER_BYTE1, PARSER_BYTE1,
                                          check_tbb_bytes, core1, report)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
CORE1 = CORPUS / 'b0c1a.bin'
HAS_CORE1 = (CORE1.exists() and find_spec('capstone') is not None)


class TableTests(unittest.TestCase):
    def test_parser_byte1_set_is_disjoint_and_covers_ef(self):
        # The parser consumes 0xEF; the helper ignores it (fallthrough tail).
        self.assertIn(0xef, PARSER_BYTE1)
        self.assertNotIn(0xef, HELPER_BYTE1)
        self.assertFalse(set(PARSER_BYTE1) & set(HELPER_BYTE1)
                         - {0x80, 0xbc, 0xbd, 0xbe})
        # 0xE1/0xE2 are not parser byte-1 commands: they fall through the chain.
        self.assertNotIn(0xe1, PARSER_BYTE1)
        self.assertNotIn(0xe2, PARSER_BYTE1)


class AnchorTableTests(unittest.TestCase):
    def test_anchors_decode_to_recorded_text(self):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB
                         | capstone.CS_MODE_MCLASS)
        for address, bytehex, mnemonic, operands in ANCHORS:
            if mnemonic == '.byte':
                self.assertEqual(bytehex,
                                 bytes.fromhex(bytehex).hex())
                continue
            ins = next(md.disasm(bytes.fromhex(bytehex), address), None)
            self.assertIsNotNone(ins, f'{address:#x} did not decode')
            self.assertEqual((ins.mnemonic, ins.op_str), (mnemonic, operands),
                             f'{address:#x} mismatch')

    def test_every_value_in_both_sets_has_an_anchor_or_reject_branch(self):
        # Every accepted byte-1 value is either an explicit cmp anchor or one of
        # the TBB-selected 0x80..0x85 ranges; the sets contain nothing else.
        anchored = {a[3] for a in ANCHORS if a[2].startswith('cmp')}
        for value in HELPER_BYTE1:
            if 0x80 <= value <= 0x85:
                continue
            self.assertTrue(any(f'#0x{value:x}' in op for op in anchored),
                            f'helper 0x{value:02x} lacks an anchor')
        for value in PARSER_BYTE1:
            if 0xa6 <= value <= 0xad or value in (0xbc, 0xbd, 0xbe):
                # 0xa6..0xad via the two sub-0xa6 TBBs; 0xbc..0xbe via sub-chain.
                continue
            self.assertTrue(any(f'#0x{value:x}' in op for op in anchored),
                            f'parser 0x{value:02x} lacks an anchor')


@unittest.skipUnless(HAS_CORE1, 'Pinned b0c1a CORE1 payload and capstone required')
class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = core1(CORE1)
        cls.result = report(CORE1)

    def test_digest_and_anchors(self):
        self.assertEqual(self.result['payload_sha256'],
                         '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154')
        self.assertTrue(self.result['anchors_match'])
        self.assertTrue(all(row['match'] for row in self.result['anchors']))

    def test_helper_tbb_targets_are_inside_helper(self):
        rows = check_tbb_bytes(self.core)
        self.assertTrue(all(0x01126d2e <= t < 0x01126f40 for t in rows['helper']))
        # and the entry 0x80 target lands in the helper's mask bodies
        self.assertEqual(rows['helper'][0], 0x01126d5a)

    def test_parser_tbb_targets_are_inside_parser(self):
        rows = check_tbb_bytes(self.core)
        self.assertTrue(all(0x0110d982 <= t < 0x0110e2ba for t in rows['parser']))
        self.assertTrue(all(0x0110dd6a <= t < 0x0110e2ba for t in rows['parser_low1']))
        self.assertTrue(all(0x0110dd86 <= t < 0x0110e2ba for t in rows['parser_low2']))

    def test_helper_consumes_only_high_nibble_two_words(self):
        # The helper's entry cmp pins byte0 high nibble == 2 and its TBB covers
        # exactly byte1 0x80..0x85; everything else falls to the shared tail.
        self.assertEqual(self.core.data[self.core.offset(0x01126d54):
                                        self.core.offset(0x01126d54) + 6].hex(),
                         '03f05b5d2a1c')

    def test_parser_reached_from_asgn_router_second_call(self):
        # The BL at 0x0110a6ba targets the parser entry and the parser's first
        # table rejects low nibble 15.
        self.assertEqual(self.core.data[self.core.offset(0x0110a6ba):
                                        self.core.offset(0x0110a6ba) + 4].hex(),
                         '03f052f9')
        self.assertEqual(self.core.data[self.core.offset(0x0110d974):
                                        self.core.offset(0x0110d974) + 15].hex(),
                         '07f0f4f38ef4f2f1f0ef0829eeb5f4')


if __name__ == '__main__':
    unittest.main()