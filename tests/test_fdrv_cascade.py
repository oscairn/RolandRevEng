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
from bmc_dsp import command_count,encode_literal,literal,packets,swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment,disassemble_fragment
from fdrv_cascade_study import cascade_spec,cascade_reference,program_specs,FIXTURE_COEFFICIENTS


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_asymmetric_stages_store_old_ports_and_prefetch_cannot_change_outputs(self):
        spec=cascade_spec(coefficients=FIXTURE_COEFFICIENTS)
        values=[2,-3,5,7,-7,11,-13,17,101,203,307,409]
        data=dict(zip(spec['sources'],values));before=data.copy()
        r=execute_fragment(assemble_fragment(spec),data,{})
        self.assertEqual([step['after'][1]for step in r['trace'][1:7]],
                         [1.,.25,-.375,-.28125,-1.21875,-.78125])
        self.assertEqual([step['after'][5]for step in r['trace'][1:7]],
                         [-3.5,-.75,.875,.65625,3.09375,4.15625])
        self.assertEqual(r['trace'][1]['writes'],{6:2.,0xa:-7.})
        self.assertEqual(r['trace'][4]['writes'],{7:-.375,0xb:.875})
        self.assertEqual(r['trace'][7]['writes'],{8:-.78125,0xc:4.15625})
        self.assertEqual([r['ports'][i]for i in (0,4,2,6)],[307.,409.,101.,203.])
        self.assertEqual(data,before)
        changed=dict(data)
        for cell in spec['sources'][8:]:changed[cell]*=-100
        again=execute_fragment(assemble_fragment(spec),changed,{})
        self.assertEqual([again['data'][c]for c in spec['targets']],[r['data'][c]for c in spec['targets']])

    def test_independent_scalar_recurrence_default_nonzero_and_random(self):
        rng=random.Random(164)
        cases=[[0.]*12,[-0.]*12]+[[rng.uniform(-8,8)for _ in range(12)]for _ in range(128)]
        nonbinary=[literal(encode_literal(v,3))for v in (.7313,.1279,-.0623,.6187,-.1739,.0823)]
        for cofs in ((1.,0.,0.,1.,0.,0.),FIXTURE_COEFFICIENTS,nonbinary):
            spec=cascade_spec(coefficients=cofs);p=assemble_fragment(spec)
            self.assertEqual(disassemble_fragment(p),spec)
            for values in cases:
                r=execute_fragment(p,dict(zip(spec['sources'],values)),{})
                for channel in (0,1):
                    ref=cascade_reference(*values[4*channel:4*channel+4],cofs)
                    for cell,key in ((spec['targets'][channel],'first'),(spec['targets'][channel+2],'second')):
                        self.assertEqual(r['data'][cell].hex(),ref[key].hex())

    def test_strict_controls_literals_resource_aliases_and_storage(self):
        spec=cascade_spec();p=assemble_fragment(spec);fields=set()
        for off,words in packets(p):
            count=command_count(words[0])
            for word in words[1:1+count]:
                if word&0xff0==0xfe0 and not word&1:fields.add(off+2*(count+1)+(word&15))
        for offset in range(len(p)):
            if offset&~1 in fields:continue
            changed=bytearray(p);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        for bad in (p+b'\0\0',p[:-2]):self.assertRaises(ValueError,disassemble_fragment,bad)
        for field in ('sources','targets','filter_coefficients'):
            bad=copy.deepcopy(spec);bad[field].pop()
            self.assertRaises(ValueError,assemble_fragment,bad)
            bad=copy.deepcopy(spec);bad[field][0]=True
            self.assertRaises(ValueError,assemble_fragment,bad)
        for field,index,value in (('sources',0,2048),('sources',2,7),('sources',8,6),('targets',0,8),
                                  ('filter_coefficients',0,.1),('filter_coefficients',0,-0.),
                                  ('filter_coefficients',0,math.nan),('filter_coefficients',0,math.inf)):
            bad=copy.deepcopy(spec);bad[field][index]=value
            self.assertRaises(ValueError,assemble_fragment,bad)
        self.assertRaises(ValueError,assemble_fragment,dict(spec,extra=1))
        self.assertRaises(ValueError,execute_fragment,p,{}, {})
        parts=[assemble_fragment(s)for s in program_specs()];body=b''.join(parts)
        self.assertEqual((len(p),len(body),sum(len(packets(x))for x in parts)),(164,1504,92))
        self.assertEqual(swap_words(swap_words(body)),body)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/name).exists()
                           for name in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_native_bindings_and_five_fantom_bodies(self):
        from fdrv_cascade_study import report
        from limit_control_study import native_context
        p,*_=native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(cascade_spec())[10:],p[0x446:0x4e0])
        r=report();self.assertEqual((r['remaining_stock_packets'],r['remaining_stock_bytes']),(11,172))
        if not(CORPUS/'b0c1a.bin').exists():self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from effect_lifecycle_study import IMAGE_SHA256
        from kernel_abi import program_list,read
        core=Core1(CORPUS/'b0c1a.bin');self.assertEqual(hashlib.sha256(core.data).hexdigest(),IMAGE_SHA256)
        for base,seg in zip((0x100,0x320,0x3b6,0x44c,0xc0),program_list(core,0x610e5a94)['segments'],strict=True):
            stream=swap_words(read(core,seg['source'],(seg['length']+3)&~3))
            self.assertEqual(assemble_fragment(cascade_spec(base))[10:],stream[0x446:0x4e0])

    def test_wrong_math_subquantum_constant_and_later_store_rejected(self):
        from fdrv_cascade_study import report
        from limit_control_study import native_context
        p,n,m,f,t=native_context('SIM_MFX_FDRV')
        changed=dict(n);changed[0x305c18]=n[0x305c2c]
        with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
            self.assertRaises(ValueError,report)
        changed=dict(m)
        for i,v in enumerate(struct.pack('<d',1.+1e-7)):changed[0x78+i]=v
        with patch('limit_control_study.native_context',return_value=(p,n,changed,f,t)):
            self.assertRaises(ValueError,report)
        changed=copy.deepcopy(t);row=copy.deepcopy(next(r for r in t['accesses']if r['pc']==0x305cb0))
        row['pc']=0x305e00;changed['accesses'].append(row)
        with patch('limit_control_study.native_context',return_value=(p,n,m,f,changed)):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma'),
                         'macOS ARM64/Python 3.13+ required')
    def test_default_and_nondegenerate_native_modes_cross_wrap(self):
        code=('import json;from fdrv_filter_study import native_check;'
              'print(json.dumps([native_check(2056,(1,2),compare_cascade=True,cascade_coefficients=c,resample_drive_literal=d)'
              'for c,d in (((1.,0.,0.,1.,0.,0.),"0656d2"),((.5,.25,-.125,.75,-.1875,.0625),"0656d2"),'
              '((.5,.25,-.125,.75,-.1875,.0625),"100000"))]))')
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=45,
                         env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr)
        for item in json.loads(r.stdout):
            self.assertEqual(item['independent_packet_cascade_chain_values'],94576)
            self.assertEqual(item['final_origin'],8)
            self.assertEqual(item['final_cursors'],[1,2])
            self.assertTrue(item['native_callback_executed'])
            self.assertFalse(item['bmc_hardware_executed'])


if __name__=='__main__':unittest.main()
