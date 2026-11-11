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
from bmc_dsp import command_count,literal,packets,swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment,disassemble_fragment
from fdrv_post_cubic_study import POST_SCALES,mix_reference,post_mix_spec,program_specs


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_asymmetric_trace_stores_pre_gain_and_uses_delayed_coefficient(self):
        spec=post_mix_spec();data=dict(zip(spec['sources'],[2,-3,5,-7,11,-13]));before=data.copy()
        r=execute_fragment(assemble_fragment(spec),data,{1:.75})
        self.assertEqual([r['trace'][i]['after'][0]for i in (1,2,3)],[1.,.25,.25])
        self.assertEqual([r['trace'][i]['after'][4]for i in (1,2,3)],[-3.5,-.75,-.75])
        self.assertEqual([r['trace'][i]['after'][2]for i in (0,3,4,5)],
                         [2.,1.5,1.125,1.125*POST_SCALES['628624']])
        self.assertEqual(r['trace'][3]['after'][6],-4.)
        self.assertIsNone(r['trace'][3]['before'][3])
        self.assertEqual(r['trace'][3]['after'][3],.75)
        self.assertEqual(r['trace'][4]['writes'],{0x1c:1.5,0x1d:-4.})
        self.assertEqual(r['data'][6],1.125*POST_SCALES['628624'])
        self.assertEqual(r['data'][0xa],-3.*POST_SCALES['628624'])
        self.assertEqual(data,before)
        self.assertNotEqual(POST_SCALES['628624'],literal(bytes.fromhex('628624')))
        spec['post_scale_literal']='500000'
        r=execute_fragment(assemble_fragment(spec),data,{1:.75})
        self.assertEqual((r['ports'][2],r['ports'][6]),(18.,-48.))

    def test_independent_scalar_random_and_zero_gain_cases(self):
        rng=random.Random(110)
        cases=[[0.]*6,[-0.]*6]+[[rng.uniform(-8,8)for _ in range(6)]for _ in range(128)]
        for scale in POST_SCALES:
            spec=post_mix_spec(post_scale_literal=scale);p=assemble_fragment(spec)
            self.assertEqual(disassemble_fragment(p),spec)
            for values in cases:
                for gain in (0.,1.,-.25,.7313):
                    r=execute_fragment(p,dict(zip(spec['sources'],values)),{1:gain})
                    for channel in (0,1):
                        ref=mix_reference(*values[3*channel:3*channel+3],gain,scale)
                        for actual,expected in ((r['data'][spec['targets'][channel]],ref['mixed']),
                                                (r['ports'][2+4*channel],ref['output']),
                                                (r['data'][spec['output_addresses'][channel]],ref['output'])):
                            self.assertEqual(actual.hex(),expected.hex())

    def test_resource_control_and_storage_boundaries(self):
        spec=post_mix_spec();p=assemble_fragment(spec);fields=set()
        for offset,words in packets(p):
            count=command_count(words[0])
            for word in words[1:1+count]:
                if word&0xff0==0xfe0 and not word&1:
                    fields.add(offset+2*(count+1)+(word&15))
        for offset in range(len(p)):
            if offset&~1 in fields:continue
            changed=bytearray(p);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        changed=bytearray(p);changed[66]^=0x40
        self.assertRaises(ValueError,disassemble_fragment,bytes(changed))
        for bad in (p+b'\0\0',p[:-2]):self.assertRaises(ValueError,disassemble_fragment,bad)
        for field in ('sources','targets','output_addresses','coefficient_slots'):
            for value in (True,-1,4096):
                bad=copy.deepcopy(spec);bad[field][0]=value
                self.assertRaises(ValueError,assemble_fragment,bad)
            bad=copy.deepcopy(spec);bad[field].pop()
            self.assertRaises(ValueError,assemble_fragment,bad)
        for field,index,value in (('sources',2,0x1f),('targets',0,0x12),('output_addresses',0,0x1c)):
            bad=copy.deepcopy(spec);bad[field][index]=value
            self.assertRaises(ValueError,assemble_fragment,bad)
        for value in ('628625',True,None):
            self.assertRaises(ValueError,assemble_fragment,dict(spec,post_scale_literal=value))
        self.assertRaises(ValueError,assemble_fragment,dict(spec,extra=1))
        self.assertRaises(ValueError,execute_fragment,p,{}, {})
        parts=[assemble_fragment(s)for s in program_specs()];body=b''.join(parts)
        self.assertEqual(list(map(len,parts)),[86,194,226,194,202,122,80,126,110])
        self.assertEqual((len(body),sum(len(packets(x))for x in parts)),(1340,84))
        self.assertEqual(swap_words(swap_words(body)),body)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                           for name in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_stock_body_and_all_five_fantom_literal_variants(self):
        from fdrv_post_cubic_study import report
        from limit_control_study import native_context
        p,*_=native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(post_mix_spec())[10:100],p[0x3ec:0x446])
        r=report()
        self.assertEqual((r['combined_bytes'],r['remaining_stock_bytes'],r['remaining_stock_packets']),(1340,326,18))
        if not (CORPUS/'b0c1a.bin').exists():self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from effect_lifecycle_study import IMAGE_SHA256
        from kernel_abi import program_list,read
        core=Core1(CORPUS/'b0c1a.bin')
        self.assertEqual(hashlib.sha256(core.data).hexdigest(),IMAGE_SHA256)
        for base,segment in zip((0x100,0x320,0x3b6,0x44c,0xc0),
                               program_list(core,0x610e5a94)['segments'],strict=True):
            stream=swap_words(read(core,segment['source'],(segment['length']+3)&~3))
            cb=(int.from_bytes(stream[12:14],'big')&0xfff)-5
            self.assertEqual(stream[0x440:0x446],bytes.fromhex('500000500000'))
            candidate=assemble_fragment(post_mix_spec(base,cb,'500000'))
            self.assertEqual(candidate[10:100],stream[0x3ec:0x446])

    def test_native_mutations_reject_wrong_math_scale_and_later_overwrite(self):
        from fdrv_post_cubic_study import report
        from limit_control_study import native_context
        p,n,m,f,t=native_context('SIM_MFX_FDRV')
        changed=dict(n);changed[0x305b54]=n[0x305b68]
        with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
            self.assertRaises(ValueError,report)
        changed=dict(m)
        for i,value in enumerate(struct.pack('<d',POST_SCALES['628624']+1e-7)):changed[0x38+i]=value
        with patch('limit_control_study.native_context',return_value=(p,n,changed,f,t)):
            self.assertRaises(ValueError,report)
        changed=copy.deepcopy(t);row=copy.deepcopy(next(r for r in t['accesses']if r['pc']==0x305bd8))
        row['pc']=0x305e00;changed['accesses'].append(row)
        with patch('limit_control_study.native_context',return_value=(p,n,m,f,changed)):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64'
                         and hasattr(math,'fma'),'macOS ARM64/Python 3.13+ required')
    def test_both_scale_pairs_match_native_across_wrap(self):
        code=('import json;from fdrv_filter_study import native_check;'
              'print(json.dumps([native_check(2056,(2,1),compare_post_mix=True,resample_drive_literal=d)'
              'for d in ("0656d2","100000")]))')
        run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=45,
                           env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode,0,run.stderr)
        for r in json.loads(run.stdout):
            self.assertEqual(r['independent_packet_post_mix_chain_values'],86352)
            self.assertGreater(r['post_mix_fixture_gain'],0)
            self.assertTrue(r['native_callback_executed'])
            self.assertFalse(r['native_prefix_executed'])
            self.assertEqual(r['final_origin'],8)
            self.assertEqual(r['final_cursors'],[2,1])
            self.assertFalse(r['bmc_hardware_executed'])


if __name__=='__main__':unittest.main()
