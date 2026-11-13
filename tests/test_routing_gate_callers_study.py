"""Checks for the routing gate callers study.

tools/routing_gate_callers_study.py answers run 9's open question about
CSimDspMgr::WriteDspCoefFloat (0xfba10): the function has no direct BL callers
in the pinned image; it is reached only as a function pointer (aligned quad at
0x9e54d0, inside the consecutive manager-function-pointer table at 0x9e53f8..)
and called virtually through manager vtable byte 0xc8 (162 strict virtual-call
sites, of which five load the manager global 0x9c8480 nearby, all inside the
parameter-apply function at 0x354184). Pure checks run without the corpus; the
pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import routing_gate_callers_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'zen_arm64'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class AbiModelTests(unittest.TestCase):
    def test_gate_keys_are_the_four_decoded_records(self):
        # Run 9's decoded gate record keys, kept distinct and nonempty.
        self.assertEqual(sorted(study.GATE_KEYS),
                         [0x0000, 0x07c4, 0x4d02, 0x4fce])
        self.assertEqual(study.EXPECTED_CALL_SITES,
                         [0x354388, 0x3543a0, 0x3543b8, 0x3543d0, 0x3543e8])

    def test_bl_decoder_round_trip(self):
        # The strict BL scan decodes immediate BLs both directions. Encodings:
        # '00000094' = bl +0 (target = the instruction itself at offset 0);
        # 'fbfffe97' = bl -0x1014*... use a computed pair instead: bl at 4 to 0
        # is imm26 = (0-4)/4 = -1 -> 0x17ffffff; bl at 0 to 8 is imm26 = 2
        # -> 0x94000002.
        data = bytes.fromhex('02000094'   # at 0: bl 0+2*4 = 8
                             'ffffff97'   # at 4: bl 4+(-1)*4 = 0
                             '00000094')  # at 8: bl 8 (also -> 8)
        self.assertIn(0, study.bl_callers(data, 8))
        self.assertEqual(study.bl_callers(data, 0), [4])
        self.assertEqual(study.bl_callers(data, 4), [])
        self.assertEqual(study.bl_callers(data, 0xfba10), [])

    def test_virtual_pattern_requires_all_three_parts(self):
        # Encodings (AArch64, little-endian words):
        # ldr x9,[x10]        = 0xf9400140? no: imm12 0, rn 10, rt 9 ->
        #   0xf9400149; bytes LE 49 01 40 f9.
        # ldr x9,[x8,#0xc8]   = imm12 0xc8>>3 = 0x19; 0x19<<10 = 0x6400;
        #   Rn 9 (same reg as Rt of the first ldr) -> word 0xf9406529,
        #   bytes 29 65 40 f9.
        # blr x9              = 0xd63f0120 -> bytes 20 01 3f d6.
        data = bytes.fromhex(
            '490140f9'    # ldr x9,[x10]
            '296540f9'    # ldr x9,[x9,#0xc8]
            '20013fd6'    # blr x9
            'c0035fd6')   # ret (padding so the 4-byte scan window covers offset 4)
        self.assertEqual(study.virtual_call_sites(data, 0xc8), [0])
        # Without the BLR the pattern is absent.
        truncated = data[:8] + b'\x00' * 4
        self.assertEqual(study.virtual_call_sites(truncated, 0xc8), [])


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned zen_arm64 image and capstone required')
        cls.data = study.load_image(IMAGE)

    def test_anchors_are_byte_exact(self):
        _, problems = study.check_anchors(self.data)
        self.assertEqual(problems, [])

    def test_write_path_has_no_direct_callers(self):
        self.assertEqual(study.bl_callers(self.data, study.WRITE_DSP_COEF_FLOAT), [])
        self.assertEqual(
            study.bl_callers(self.data, study.WRITE_DSP_COEF_FLOAT_THUMB), [])

    def test_write_path_is_a_manager_table_pointer(self):
        quads = study.aligned_quads(self.data, study.WRITE_DSP_COEF_FLOAT,
                                    study.WRITE_DSP_COEF_FLOAT_THUMB)
        self.assertIn(0x9e54d0, quads)

    def test_manager_global_call_sites_match_the_parameter_apply_function(self):
        strict = study.virtual_call_sites(self.data, 0xc8)
        self.assertGreater(len(strict), 0)
        manager_sites = study.manager_global_call_sites(self.data, strict)
        self.assertEqual(manager_sites, study.EXPECTED_CALL_SITES)

    def test_tool_report_is_clean(self):
        report = study.report(IMAGE)
        self.assertTrue(report['ok'])
        self.assertEqual(report['anchors_checked'], len(study.ANCHORS))
        self.assertEqual(report['direct_bl_callers'], 0)
        self.assertEqual(report['manager_global_call_sites'],
                         [hex(a) for a in study.EXPECTED_CALL_SITES])


if __name__ == '__main__':
    unittest.main()