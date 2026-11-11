import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bmc_dsp import packets,swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment,disassemble_fragment
from fdrv_output_study import output_spec,output_reference,program_specs,execute_frame,FIXTURE_COEFFICIENTS


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_independent_reference_timing_and_live_gain(self):
        rng=random.Random(188)
        for cofs in ((0.,0.,0.,1.,0.),FIXTURE_COEFFICIENTS):
            spec=output_spec(coefficients=cofs);p=assemble_fragment(spec)
            self.assertEqual(disassemble_fragment(p),spec)
            cases=[[0.]*8,[-0.]*8,[2,-3,5,-7,11,-13,17,-19]]+[
                [rng.uniform(-4,4)for _ in range(8)]for _ in range(128)]
            for wet,dry,master in ((0.,.4137,.8279),(.7313,0.,.8279),(.7313,.4137,.8279),(.7313,.4137,0.)):
                for values in cases:
                    result=execute_fragment(p,dict(zip(spec['sources'],values)),{3:wet,2:dry,4:master})
                    for channel in (0,1):
                        y,s,t=values[3*channel:3*channel+3]
                        ref=output_reference(y,s,t,values[6+channel],wet,dry,master,cofs)
                        for cell,key in ((spec['targets'][channel],'state_t'),(spec['targets'][2+channel],'state_s')):
                            self.assertEqual(result['data'][cell].hex(),ref[key].hex())
                        self.assertEqual(result['ports'][4*channel].hex(),ref['output'].hex())
                        self.assertEqual(result['trace'][7]['writes'][spec['targets'][2+channel]].hex(),
                                         result['trace'][7]['before'][4*channel].hex())

    def test_exact_inverse_rejects_control_mutations_and_invalid_resources(self):
        spec=output_spec();p=assemble_fragment(spec)
        self.assertEqual(len(p),188)
        for offset in range(len(p)):
            changed=bytearray(p);changed[offset]^=1
            # Literal/resource changes can form another valid assignment; controls cannot.
            try:decoded=disassemble_fragment(bytes(changed))
            except ValueError:continue
            self.assertEqual(assemble_fragment(decoded),bytes(changed))
        for start,words in packets(p):
            from bmc_dsp import command_count
            for offset in range(start,start+2*(1+command_count(words[0]))):
                changed=bytearray(p);changed[offset]^=1
                with self.subTest(control_byte=offset),self.assertRaises(ValueError):
                    disassemble_fragment(bytes(changed))
        for bad in (p[:-2],p+bytes.fromhex('0b0200f8'),p[:-6]+bytes.fromhex('2d040403450300f8')):
            self.assertRaises(ValueError,disassemble_fragment,bad)
        for field,index,value in (('sources',0,2048),('sources',1,0),('sources',2,0x43),
            ('sources',6,0x40),('targets',0,0x40),('coefficient_slots',0,2),('filter_coefficients',0,.1),
            ('filter_coefficients',0,-0.),('filter_coefficients',0,True),('filter_coefficients',0,math.inf)):
            bad=copy.deepcopy(spec);bad[field][index]=value
            self.assertRaises(ValueError,assemble_fragment,bad)

    def test_complete_packet_only_runner_preserves_inputs_and_uses_ephemeral_bridges(self):
        from fdrv_cascade_study import FIXTURE_COEFFICIENTS as cascade
        specs=program_specs((.5,.25,-.125),'0656d2',cascade,FIXTURE_COEFFICIENTS)
        programs=list(map(assemble_fragment,specs));ring=[((i*37%101)-50)/10000 for i in range(2048)]
        caches=[([-11.,23.,-37.],1),([-11.,23.,-37.],2)]
        before=copy.deepcopy((ring,caches))
        cofs={i:0. for i in range(20)}
        cofs.update({0:8192.,1:.7313,2:.4137,3:.7313,4:.8279,5:.7313,6:.1279,7:.0623,
            8:.3737,9:.6187,10:-.4973,11:-.2531,12:.3737,13:.1279,14:-.0623,
            15:-.3813,16:-.4171,17:.2937,18:.1739,19:-.0823})
        result=execute_frame(programs,ring,0,cofs,[.0123,-.0234],caches)
        self.assertEqual((ring,caches),before)
        self.assertEqual(result['ring'][0x46:],ring[0x46:])
        self.assertEqual([c[1]for c in result['auxiliary']],[1,2])
        self.assertTrue(all(math.isfinite(v)for v in result['output']))
        self.assertEqual((sum(map(len,programs)),sum(len(packets(p))for p in programs)),(1692,104))
        self.assertEqual(swap_words(swap_words(b''.join(programs))),b''.join(programs))
        self.assertRaises(ValueError,execute_frame,programs[:-1],ring,0,cofs,[0,0],caches)
        self.assertRaises(ValueError,execute_frame,iter(programs),ring,0,cofs,[0,0],caches)
        changed=specs.copy();changed[-1]=output_spec(0x100)
        self.assertRaises(ValueError,execute_frame,list(map(assemble_fragment,changed)),ring,0,cofs,[0,0],caches)
        self.assertRaises(ValueError,execute_frame,programs,ring,2048,cofs,[0,0],caches)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_native_provenance_and_five_relocated_fantom_bodies(self):
        from fdrv_output_study import report
        from limit_control_study import native_context
        p,*_=native_context('SIM_MFX_FDRV');r=report()
        self.assertEqual((r['combined_bytes'],r['composed_packets']),(1692,104))
        self.assertFalse(r['dsp_return_00f8_executed'])
        self.assertEqual(assemble_fragment(output_spec())[28:-6],p[0x4e0:0x57a])
        if not(CORPUS/'b0c1a.bin').exists():self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from effect_lifecycle_study import IMAGE_SHA256
        from kernel_abi import program_list,read
        core=Core1(CORPUS/'b0c1a.bin');self.assertEqual(hashlib.sha256(core.data).hexdigest(),IMAGE_SHA256)
        for db,seg in zip((0x100,0x320,0x3b6,0x44c,0xc0),program_list(core,0x610e5a94)['segments'],strict=True):
            stream=swap_words(read(core,seg['source'],(seg['length']+3)&~3))
            spec=output_spec(db)
            # The Fantom body uses its class-specific live coefficient relocation.
            cb=int.from_bytes(stream[0x556:0x558],'big')&0xfff
            spec=output_spec(db,cb-3)
            self.assertEqual(assemble_fragment(spec)[28:-6],stream[0x4e0:0x57a])

    def test_native_math_and_exact_default_mutations_rejected(self):
        from fdrv_output_study import report
        from limit_control_study import native_context
        p,n,m,f,t=native_context('SIM_MFX_FDRV')
        changed=dict(n);changed[0x305d70]=n[0x305e00]
        with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
            self.assertRaises(ValueError,report)
        changed=dict(m)
        for i,v in enumerate(struct.pack('<d',1e-9)):changed[0xe8+i]=v
        with patch('limit_control_study.native_context',return_value=(p,n,changed,f,t)):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma'),
                         'macOS ARM64/Python 3.13+ required')
    def test_complete_audio_ring_and_auxiliary_state_cross_wrap_all_cursors(self):
        code=('import json;from fdrv_filter_study import native_check;'
            'print(json.dumps([native_check(2056,cursors=c,compare_full=True,output_coefficients=f,resample_drive_literal=d)'
            'for c,f,d in (((0,1),(0.,0.,0.,1.,0.),"0656d2"),'
            '((1,2),(.125,-.25,.5,.75,-.1875),"0656d2"),'
            '((2,0),(.125,-.25,.5,.75,-.1875),"100000"))]))')
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=60,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr)
        for result in json.loads(r.stdout):
            self.assertEqual(result['independent_full_state_and_output_values'],2056*2058)
            self.assertEqual(result['final_origin'],8)
            self.assertTrue(result['final_stereo_output_checked'])
            self.assertEqual(result['initial_cursors'],result['final_cursors'])
            self.assertFalse(result['bmc_hardware_executed'])


if __name__=='__main__':unittest.main()
