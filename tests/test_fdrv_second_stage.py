import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bmc_dsp import command_count, packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_filter_study import filter_step
from fdrv_second_stage_study import first_spec, second_spec, programs, recombine
from line_shaping_study import _float32


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_second_filter_states_and_recombination_use_old_coefficient_and_addend(self):
        spec=second_spec(); program=assemble_fragment(spec)
        data=dict(zip(spec['sources'],[2,.25,-.125,-3,-.75,.5,.1,-.2,.3,-.4])); original=data.copy()
        coefficients=dict(zip(spec['coefficient_slots'],[-.5,-.25,.375,.125,-.0625,.25,-.5313]))
        result=execute_fragment(program,data,coefficients)
        for channel,(y,t,s) in enumerate(((2,.25,-.125),(-3,-.75,.5))):
            scalar=filter_step(y,s,t,*[coefficients[i] for i in spec['coefficient_slots'][:5]])
            self.assertEqual(result['ports'][channel*4].hex(),recombine(y,scalar['output'],.25).hex())
            self.assertEqual(result['data'][spec['targets'][channel]],scalar['state_t'])
            self.assertEqual(result['data'][spec['targets'][channel+2]],scalar['state_s'])
            summed=result['trace'][-3]['after']
            self.assertEqual(summed[1+4*channel],float(y))
            self.assertEqual(summed[channel*4].hex(),scalar['output'].hex())
            self.assertEqual(result['trace'][-2]['after'][1+4*channel],math.fma(-y,.25,y))
        self.assertEqual(result['trace'][-1]['before'][7],.25)
        self.assertEqual(result['trace'][-1]['after'][7],_float32(-.5313))
        self.assertEqual(data,original)
        changed=dict(coefficients); changed[15]=.9973
        again=execute_fragment(program,data,changed)
        self.assertEqual([again['ports'][i] for i in (0,4)],[result['ports'][i] for i in (0,4)])
        self.assertEqual(recombine(2,5,.25),2.75)
        self.assertEqual(recombine(2,5,0),2)
        self.assertEqual(recombine(2,5,1),5)

    def test_first_output_stores_and_exact_profile_rejections(self):
        first=first_spec(); first_program=assemble_fragment(first)
        data=dict.fromkeys(first['sources'],.125)
        coefs=dict(zip(first['coefficient_slots'],[-.5,-.25,.375,.125,-.0625]))
        result=execute_fragment(first_program,data,coefs)
        self.assertEqual([result['data'][cell] for cell in first['output_addresses']],
                         [result['ports'][0],result['ports'][4]])
        self.assertEqual(len(first_program),194)
        self.assertEqual([len(p) for p in programs()],[86,194,216])
        self.assertEqual(len(b''.join(programs())),496)
        self.assertEqual(swap_words(swap_words(b''.join(programs()))),b''.join(programs()))
        for spec in (first,second_spec()):
            program=assemble_fragment(spec); self.assertEqual(disassemble_fragment(program),spec)
            fields=set()
            for offset,words in packets(program):
                count=command_count(words[0])
                for control in words[1:1+count]:
                    if control & 0xff0 == 0xfe0 and not control & 1:
                        fields.add(offset+2*(count+1)+(control&15))
            for offset in range(len(program)):
                if offset & ~1 in fields:continue
                changed=bytearray(program);changed[offset]^=1
                with self.subTest(kind=spec['kind'],offset=offset),self.assertRaises(ValueError):
                    disassemble_fragment(bytes(changed))
            self.assertRaises(ValueError,disassemble_fragment,program+b'\0\0')
            self.assertRaises(ValueError,disassemble_fragment,program[:-2])
        for spec in (dict(first,output_addresses=[0x29,0x25]),dict(first,output_addresses=[True,1]),
                     dict(second_spec(),coefficient_slots=[10]*7),dict(second_spec(),extra=1)):
            self.assertRaises(ValueError,assemble_fragment,spec)
        self.assertRaises(ValueError,execute_fragment,assemble_fragment(second_spec()),{}, {})
        for value in (True,math.nan,math.inf,1e39):
            self.assertRaises(ValueError,recombine,2,5,value)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                         for name in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_exact_native_body_and_five_fantom_relocations(self):
        from limit_control_study import native_context
        from fdrv_second_stage_study import report
        original,*_=native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(second_spec())[38:],original[0xf8:0x1aa])
        self.assertEqual(report()['combined_bytes'],496)
        if not (CORPUS/'b0c1a.bin').exists():self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from effect_lifecycle_study import IMAGE_SHA256
        from kernel_abi import program_list,read
        core=Core1(CORPUS/'b0c1a.bin')
        self.assertEqual(hashlib.sha256(core.data).hexdigest(),IMAGE_SHA256)
        for base,segment in zip((0x100,0x320,0x3b6,0x44c,0xc0),
                                program_list(core,0x610e5a94)['segments'],strict=True):
            stream=swap_words(read(core,segment['source'],(segment['length']+3)&~3))
            coefficient_base=(int.from_bytes(stream[12:14],'big') & 0xfff)-5
            self.assertEqual(assemble_fragment(second_spec(base,coefficient_base))[38:],stream[0xf8:0x1aa])

    def test_changed_arithmetic_output_abi_and_clobbered_output_pointer_are_rejected(self):
        import lib
        from limit_control_study import native_context
        from fdrv_second_stage_study import report
        p,n,m,f,t=native_context('SIM_MFX_FDRV')
        md=lib.md(); md.detail=True
        for destination,replacement in ((0x30552c,n[0x3053dc]),
                (0x305e94,n[0x305e98]),
                (0x3053b0,next(md.disasm(bytes.fromhex('e20300aa'),0x3053b0))),
                (0x3053b0,next(md.disasm(bytes.fromhex('ff430091'),0x3053b0)))):
            changed=dict(n);changed[destination]=replacement
            with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
                self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64'
                         and hasattr(math,'fma'),'macOS ARM64/Python 3.13+ required')
    def test_native_sign_probe_and_independent_two_filter_ring_through_wrap(self):
        randoms=random.Random(216)
        values=[(2,5,.25),(2,5,0),(2,5,1),(-0.,-0.,0),(-0.,0.,-0.)]
        values += [(randoms.uniform(-4,4),randoms.uniform(-4,4),randoms.uniform(-.5,1.5)) for _ in range(1024)]
        code=('import json,sys;from fdrv_second_stage_study import native_probes;'
              'from fdrv_filter_study import native_check;'
              'print(json.dumps([native_probes(json.load(sys.stdin)),'
              'native_check(2056,(2,1),True,compare_second_stage=True)]))')
        run=subprocess.run([sys.executable,'-c',code],input=json.dumps(values),capture_output=True,text=True,
                           timeout=45,env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode,0,run.stderr)
        actual,checked=json.loads(run.stdout)
        self.assertEqual([x.hex() for x in actual],[recombine(*row).hex() for row in values])
        self.assertEqual(checked['independent_packet_two_filter_values'],32896)
        self.assertTrue(checked['native_prefix_executed'])
        self.assertFalse(checked['native_callback_executed'])
        self.assertEqual(checked['final_origin'],8)
        self.assertFalse(checked['bmc_hardware_executed'])
        from fdrv_filter_study import native_check
        self.assertRaises(ValueError,native_check,128,compare_second_stage=True,compare_clip=True)


if __name__=='__main__':unittest.main()
