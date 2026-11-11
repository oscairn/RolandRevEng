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
from fdrv_resample_study import DRIVE_SCALE,program_specs,resample_reference,resample_spec


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_asymmetric_packet_trace_and_native_scale_precision(self):
        spec=resample_spec(taps=(.5,.25,-.125));p=assemble_fragment(spec)
        data=dict(zip(spec['sources'],[2,3,5,-7,11,13,17]));before=data.copy()
        r=execute_fragment(p,data,{0:.75})
        stages=[(2.,-7.),(3.,11.),(5.,13.),(1.125,-2.375),
                (1.125*DRIVE_SCALE,-2.375*DRIVE_SCALE),
                (1.125*DRIVE_SCALE*.75,-2.375*DRIVE_SCALE*.75)]
        for step,(left,right) in zip(r['trace'][:6],stages,strict=True):
            self.assertEqual((step['after'][0],step['after'][4]),(left,right))
        self.assertEqual([r['trace'][i]['after'][1] for i in (1,2,3)],[1.,1.75,1.75])
        self.assertEqual([r['trace'][i]['after'][5] for i in (1,2,3)],[-3.5,-.75,-.75])
        self.assertEqual(r['trace'][1]['writes'],{0:2.,3:-7.})
        self.assertEqual(r['trace'][4]['writes'],{1:1.125,4:-2.375})
        self.assertIsNone(r['trace'][4]['before'][3])
        self.assertEqual(r['trace'][4]['after'][3],.75)
        self.assertEqual(r['trace'][5]['after'][2],17)
        self.assertEqual([r['data'][c] for c in spec['output_addresses']],list(stages[-1]))
        self.assertNotEqual(DRIVE_SCALE,literal(bytes.fromhex('0656d2')))
        self.assertEqual(data,before)
        fantom=execute_fragment(assemble_fragment(dict(spec,drive_literal='100000')),data,{0:.75})
        self.assertEqual([fantom['ports'][i] for i in (0,4)],[1.125*.0625*.75,-2.375*.0625*.75])

    def test_scalar_recurrence_random_inputs_and_resource_rejections(self):
        rand=random.Random(122)
        cases=[[0.]*7,[-0.]*7]+[[rand.uniform(-8,8)for _ in range(7)]for _ in range(128)]
        taps=[literal(encode_literal(v,3))for v in (.7313,-.1279,.0623)]
        for taps in ((1.,0.,0.),(.5,.25,-.125),taps):
            spec=resample_spec(taps=taps);p=assemble_fragment(spec)
            self.assertEqual(disassemble_fragment(p),spec)
            for values in cases:
                data=dict(zip(spec['sources'],values));r=execute_fragment(p,data,{0:.7313})
                for channel in (0,1):
                    expected=resample_reference(*values[3*channel:3*channel+3],taps,.7313)
                    for actual,wanted in ((r['data'][1+3*channel],expected['history']),
                                          (r['ports'][4*channel],expected['output'])):
                        self.assertEqual(actual.hex(),wanted.hex())
        # Independently checked Qwen suggestions; the fourth is not a cross-channel case.
        mutations=[('output_addresses',0,True),('sources',5,2048),('sources',2,7),
                   ('sources',4,99),('output_addresses',1,0),('output_addresses',1,98),
                   ('coefficient_slots',0,4096),('tap_coefficients',0,.1)]
        mutations += [('tap_coefficients',0,v) for v in (True,math.inf,math.nan,-0.)]
        for field,index,value in mutations:
            spec=resample_spec();spec[field][index]=value
            self.assertRaises(ValueError,assemble_fragment,spec)
        spec=resample_spec();spec['sources'][3:6]=[0,1,2]
        self.assertRaises(ValueError,assemble_fragment,spec)
        for field in ('sources','output_addresses','coefficient_slots','tap_coefficients'):
            spec=resample_spec();spec[field].pop()
            self.assertRaises(ValueError,assemble_fragment,spec)
        self.assertRaises(ValueError,assemble_fragment,dict(resample_spec(),extra=1))
        for value in (True,'ffffff','0656D2',None):
            self.assertRaises(ValueError,assemble_fragment,dict(resample_spec(),drive_literal=value))
        self.assertRaises(ValueError,execute_fragment,assemble_fragment(resample_spec()),{}, {})

    def test_exact_template_gate_and_composed_storage(self):
        spec=resample_spec();p=assemble_fragment(spec)
        fields=set()
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
        for bad in (p+b'\0\0',p[:-2]):self.assertRaises(ValueError,disassemble_fragment,bad)
        parts=[assemble_fragment(s) for s in program_specs()]
        self.assertEqual(list(map(len,parts)),[86,194,226,194,202,122,80,126])
        body=b''.join(parts)
        self.assertEqual((len(body),len(swap_words(body+b'\0\0'))),(1230,1232))
        self.assertEqual(sum(len(packets(p))for p in parts),77)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                           for name in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_stock_body_literals_and_five_fantom_relocations(self):
        from fdrv_resample_study import report
        from limit_control_study import native_context
        p,*_=native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(resample_spec())[10:112],p[0x2d6:0x33c])
        self.assertEqual(report()['combined_bytes'],1230)
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
            self.assertEqual(stream[0x32c:0x332],bytes.fromhex('100000100000'))
            spec=resample_spec(base,cb,drive_literal='100000')
            self.assertEqual(assemble_fragment(spec)[10:112],stream[0x2d6:0x33c])
            self.assertEqual(disassemble_fragment(assemble_fragment(spec)),spec)

    def test_changed_native_arithmetic_constructor_and_overwritten_cutpoint_rejected(self):
        from fdrv_resample_study import report
        from limit_control_study import native_context
        p,n,m,f,t=native_context('SIM_MFX_FDRV')
        changed=dict(n);changed[0x3058c0]=n[0x3058d4]
        with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
            self.assertRaises(ValueError,report)
        changed=dict(m)
        for i,value in enumerate(struct.pack('<d',DRIVE_SCALE+1e-9)):changed[0x28+i]=value
        with patch('limit_control_study.native_context',return_value=(p,n,changed,f,t)):
            self.assertRaises(ValueError,report)
        changed=copy.deepcopy(t)
        row=copy.deepcopy(next(r for r in t['accesses']if r['pc']==0x3058f0))
        row['pc']=0x305e00;changed['accesses'].append(row)
        with patch('limit_control_study.native_context',return_value=(p,n,m,f,changed)):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin'and platform.machine()=='arm64'
                         and hasattr(math,'fma'),'macOS ARM64/Python 3.13+ required')
    def test_stock_and_nondegenerate_native_chain_cross_wrap(self):
        code=('import json;from fdrv_filter_study import native_check;'
              'print(json.dumps([native_check(2056,(1,2),compare_resample=True,resample_taps=t,resample_drive_literal=d)'
              'for t,d in (((1.,0.,0.),"0656d2"),((.5,.25,-.125),"0656d2"),((.5,.25,-.125),"100000"))]))')
        run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=45,
                           env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode,0,run.stderr)
        for result in json.loads(run.stdout):
            self.assertEqual(result['independent_packet_resample_chain_values'],78128)
            self.assertTrue(result['native_callback_executed'])
            self.assertFalse(result['native_prefix_executed'])
            self.assertGreater(result['distinct_cubic_input_values'],32)
            self.assertGreater(result['clipped_boundary_values'],0)
            self.assertEqual(result['final_origin'],8)
            self.assertEqual(result['final_cursors'],[1,2])
            self.assertFalse(result['bmc_hardware_executed'])


if __name__=='__main__':unittest.main()
