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
from negative_short_add_study import CONTEXTS, boundary_cases, packet_context, reference, report


class ReferenceTests(unittest.TestCase):
    def test_shape_boundaries_extremes_and_signed_zero(self):
        for value,gain in ((-2.,1.),(-1.,1.),(-.5,1.5),(-.25,1.75),
                           (0.,1.75),(.25,1.75),(.5,1.5),(1.,1.),(2.,1.)):
            self.assertEqual(reference(value)['gain'],gain)
        for key in ('clipped','magnitude'):
            self.assertEqual(reference(-0.)[key].hex(),'-0x0.0p+0')
        for value in boundary_cases():
            result=reference(value)
            self.assertTrue(all(math.isfinite(v)for v in result.values()))
            self.assertGreaterEqual(result['gain'],1.)
            self.assertLessEqual(result['gain'],1.75)
        for value in (True,None,'1',math.inf,math.nan,10**1000):
            self.assertRaises(ValueError,reference,value)

    def test_word_collision_and_changed_neighborhood_do_not_gain_admission(self):
        previous=[0x6209,0x6fe4,0x9450,0xded4,0x8fe2,0,0x113,0x369f,0xbe00]
        words=[0x2e07,0x1e50,0x5d52,0x3fe4,0x3c00,0xa400,0x400d]
        following=[0x6207,0x2442,0xd550,0xfedf,0x1fe2,0,0x400e]
        self.assertEqual(packet_context(previous,words,following),'SIM_MFX_GASSDLY')
        for which,index in ((0,1),(0,3),(1,0),(1,2),(1,5),(2,2)):
            rows=[previous.copy(),words.copy(),following.copy()];rows[which][index]^=1
            self.assertRaises(ValueError,packet_context,*rows)
        self.assertRaises(ValueError,packet_context,previous,words[:-1],following)
        self.assertRaises(ValueError,packet_context,previous,words,None)
        changed=words.copy();changed[-1]=True
        self.assertRaises(ValueError,packet_context,previous,changed,following)
        # The fourth Fantom context has the same literal/word but an unknown header.
        self.assertRaises(ValueError,packet_context,previous,
            [0x5e09,0x1e50,0x5d52,0x4014,0x0fe6,0x3c00,0xa400,13,0x13f],following)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/f).exists()for f in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_both_native_biases_remain_candidates_and_changed_dependencies_reject(self):
        import lib
        from limit_control_study import native_context
        from negative_short_add_study import checked_chain
        r=report()
        self.assertEqual([row['native_add_candidates']for row in r['contexts']],
            [[0x14a630,0x14a680],[0x2fa1b4,0x2fa200],[0x324f88,0x324fe8]])
        self.assertTrue(all(not row['unique_short_add_binding_verified']for row in r['contexts']))
        self.assertFalse(r['isolated_opcode_admission'])
        self.assertFalse(r['bmc_execution_verified'])
        cls,_,_,_,_,bounds,chains=CONTEXTS[0]
        _,native,_,_,_=native_context(cls)
        altered=dict(native);altered[0x14a680]=native[0x14a67c]
        self.assertRaises(ValueError,checked_chain,altered,bounds,*chains[1])
        # A clobber in the compiler interleaving invalidates the reused -.25.
        altered=dict(native)
        decoder=lib.md();decoder.detail=True
        altered[0x14a668]=next(decoder.disasm(bytes.fromhex('1040601e'),0x14a668))
        self.assertRaises(ValueError,checked_chain,altered,bounds,*chains[1])
        with patch.object(lib,'Z',lib.Z[:-1]+bytes((lib.Z[-1]^1,))):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(),'Pinned Fantom CORE1 required')
    def test_fantom_known_and_unresolved_contexts_stay_distinct(self):
        from collections import Counter
        from core1 import Core1
        from negative_short_add_study import fantom_report
        core=Core1(CORPUS/'b0c1a.bin');r=fantom_report(core)
        self.assertEqual(Counter(row['cls']for row in r['known_neighborhoods']),
            {'SIM_MFX_GASSPH':4,'SIM_MFX_GASSDLY':4,'SIM_MFX_GAMPSIM':5})
        self.assertEqual(len(r['unresolved_neighborhoods']),4)
        self.assertTrue(all(row['header']==0x5e09 for row in r['unresolved_neighborhoods']))
        self.assertFalse(r['hardware_verified'])
        core.data+=b'changed'
        self.assertRaises(ValueError,fantom_report,core)

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64',
        'macOS ARM64 required')
    def test_original_native_slices_at_every_cutpoint(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/negative_short_add_study.py'),
            '--execute-native'],capture_output=True,text=True,timeout=60)
        self.assertEqual(run.returncode,0,run.stderr)
        r=json.loads(run.stdout)
        self.assertEqual((r['native_inputs'],r['native_cutpoints']),(281,8430))
        self.assertTrue(r['native_execution_verified'])
        self.assertFalse(r['isolated_opcode_admission'])


if __name__=='__main__':unittest.main()
