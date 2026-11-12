import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bmc_dsp import assemble,packets
from bmc_subset import assemble_fragment,disassemble_fragment
from bmc_emulator import execute_fragment
from osc_bias_wrap_study import boundary_cases,reference,report,fantom_specs

SPEC=dict(kind='osc_bias_wrap',sources=[9,10,2047],targets=[2,3,8])


class ModelTests(unittest.TestCase):
    def test_roundtrip_old_marker_store_and_all_arithmetic_cutpoints(self):
        program=assemble_fragment(SPEC)
        self.assertEqual((len(program),len(packets(program))),(52,6))
        self.assertEqual(disassemble_fragment(program),SPEC)
        data={9:.5,10:.25,2047:-.75};before=data.copy()
        r=execute_fragment(program,data,{})
        self.assertEqual(data,before)
        self.assertEqual(r['data'][2],-.75)
        self.assertEqual((r['data'][3],r['data'][8]),(-.234375,-.234375))
        self.assertEqual([r['trace'][i]['after'][5]for i in (1,2,3,4)],
            [1.5,1.5625,1.765625,-.234375])
        self.assertEqual(r['trace'][1]['before'][4],.5)
        self.assertEqual(r['trace'][1]['after'][4],.25)
        self.assertEqual(r['trace'][1]['writes'],{2:-.75})

    def test_fixed_context_rejects_changed_controls_literals_and_resource_aliases(self):
        program=assemble_fragment(SPEC)
        for offset in (0,2,4,10,12,14,16,18,24,26,28,30,32,34,36,38,40,42,44,46):
            bad=bytearray(program);bad[offset+1]^=1
            self.assertRaises(ValueError,disassemble_fragment,bytes(bad))
        misc=bytearray(program);misc[32:34]=bytes.fromhex('0a03')
        self.assertRaises(ValueError,disassemble_fragment,bytes(misc))
        self.assertRaises(ValueError,disassemble_fragment,assemble([[0x0903,0x5d50,0x2340]]))
        for spec in (dict(SPEC,extra=1),dict(SPEC,sources=[True,10,2047]),
                     dict(SPEC,sources=[9,10,2]),dict(SPEC,targets=[2,3,2048]),
                     dict(SPEC,targets=[2,3,3])):
            self.assertRaises(ValueError,assemble_fragment,spec)

    def test_signed32_fold_boundaries_and_bad_numeric_inputs(self):
        cases=boundary_cases()
        self.assertEqual(len(cases),13)
        for first,second,marker in cases:
            raw=math.fma(second,.25,3*first)+.203125
            self.assertLess(abs(raw),2**31)
            reference(first,second,marker)
        for target,expected in ((-3.,1.),(-1.,-1.),(1.,-1.),(3.,-1.),
                (float(2**31-1),float(2**32-1)),(-float(2**31-1),-float(2**32-1))):
            self.assertEqual(reference(0.,4*(target-.203125),0.)['wrapped'],expected)
        program=assemble_fragment(SPEC)
        for value in (True,math.nan,math.inf,1e308):
            self.assertRaises(ValueError,reference,value,0.,0.)
            self.assertRaises(ValueError,execute_fragment,program,{9:value,10:0.,2047:0.},{})
        self.assertRaises(ValueError,reference,0.,4*(2**31-.203125),0.)
        self.assertRaises(ValueError,execute_fragment,program,{9:0.,10:4*(2**31-.203125),2047:0.},{})


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/f).exists()for f in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned desktop native corpus and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_exact_native_records_hoisted_literal_and_source_identity(self):
        import lib
        r=report();self.assertEqual(r['profile_bytes'],52)
        self.assertEqual(r['hoisted_quarter_definition'],0x29590)
        self.assertEqual(r['spec'],SPEC)
        self.assertFalse(r['hardware_verified'])
        self.assertFalse(r['isolated_word_semantics_admitted'])
        with patch.object(lib,'Z',lib.Z[:-1]+bytes((lib.Z[-1]^1,))):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(),'Pinned Fantom CORE1 required')
    def test_all_four_fantom_windows_match_the_exact_body(self):
        from core1 import Core1
        placements=fantom_specs(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(len(placements),4)
        self.assertEqual([p['spec']['targets'][1]for p in placements],[259,803,953,1103])
        self.assertTrue(all(len(assemble_fragment(p['spec']))==52 for p in placements))

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64'
        and hasattr(math,'fma')and(CORPUS/'b0c1a.bin').exists(),'macOS ARM64 and both corpora required')
    def test_native_cutpoints_and_whole_ring_write_sets(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/osc_bias_wrap_study.py'),
            '--core1',str(CORPUS/'b0c1a.bin'),'--execute-native'],
            capture_output=True,text=True,timeout=90)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual((r['native_case_inputs'],r['compared_specs'],r['native_data_cutpoints']),(141,5,8460))
        self.assertEqual(r['origins'],[0,1,2047])
        self.assertTrue(r['native_execution_verified'])
        self.assertFalse(r['hardware_verified'])


if __name__=='__main__':unittest.main()
