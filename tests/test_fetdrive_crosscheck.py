import importlib.util
import math
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fetdrive_crosscheck import shape


@unittest.skipUnless(hasattr(math,'fma'),'Python3.13+ required')
class ReferenceTests(unittest.TestCase):
    def test_shift9_has_gain512_and_a_2_to_minus23_grid(self):
        expected=math.fma(2.**-11,float.fromhex('0x1.555475a31a4bep-2'),float.fromhex('0x1.555714b9cb685p-2'))
        self.assertEqual(shape(2.**-20,1.,1.,1.),expected*expected)
        for bad in (2.**31,math.nan,math.inf,True):self.assertRaises(ValueError,shape,bad,1.,1.,1.)

    def test_native_and_encoded_literal_precision_are_not_interchangeable(self):
        a=shape(.31234,.61,.0015476426307448495,1.)
        b=shape(.31234,.61,.0015476346015930176,1.)
        self.assertNotEqual(a.hex(),b.hex())


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE and platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma'),
                     'macOS ARM64/Python3.13+ with pinned native corpus required')
class NativeTests(unittest.TestCase):
    def test_independent_mixed_and_shaped_cutpoints_through_wrap(self):
        from fetdrive_crosscheck import native_check
        r=native_check(2056)
        self.assertEqual(r['matching_native_values'],8224);self.assertEqual(r['final_origin'],8)
        self.assertEqual(r['nonzero_mix_cases'],1370);self.assertEqual(r['scale_precision_mismatches'],3255)
        self.assertFalse(r['new_opcode_admission']);self.assertFalse(r['whole_effect_packet_emulation'])


if __name__=='__main__':unittest.main()
