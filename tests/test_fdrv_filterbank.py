import copy
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
from fdrv_filterbank_study import bridge_spec, third_spec, terminal_spec, program_specs, programs
from fdrv_second_stage_study import recombine, second_spec


@unittest.skipUnless(hasattr(math,'fma'),'Python 3.13+ required')
class FragmentTests(unittest.TestCase):
    def test_terminal_states_and_raw_outputs_match_scalar_recurrence(self):
        spec=terminal_spec(); program=assemble_fragment(spec)
        randoms=random.Random(202)
        samples=[[0.]*6,[-0.]*6,[2,.25,-.125,-3,-.75,.5]]
        samples += [[randoms.uniform(-2,2) for _ in range(6)] for _ in range(128)]
        for values in samples:
            for g in (0.,1.,.6187):
                data=dict(zip(spec['sources'],values)); before=data.copy()
                coefs=dict(zip(spec['coefficient_slots'],[-.3813,-.4171,.2937,.1739,-.0823,g]))
                actual=execute_fragment(program,data,coefs)
                for channel in (0,1):
                    y,t,s=values[3*channel:3*channel+3]
                    model=filter_step(y,s,t,*[coefs[slot] for slot in spec['coefficient_slots'][:5]])
                    expected=recombine(y,model['output'],g)
                    self.assertEqual(actual['ports'][4*channel].hex(),expected.hex())
                    self.assertEqual(actual['data'][spec['output_addresses'][channel]].hex(),expected.hex())
                    self.assertEqual(actual['data'][spec['targets'][channel]].hex(),model['state_t'].hex())
                    self.assertEqual(actual['data'][spec['targets'][channel+2]].hex(),model['state_s'].hex())
                self.assertEqual(data,before)
        self.assertEqual([row[1][0] for row in packets(program)][-3:],[0x1503,0x1503,0x1e05])

    def test_bridge_stores_roundtrips_and_exact_control_gate(self):
        bridge=bridge_spec(); data=dict.fromkeys(bridge['sources'],.125)
        coefs=dict(zip(bridge['coefficient_slots'],[-.5,-.25,.375,.125,-.0625,.3737,-.3813]))
        actual=execute_fragment(assemble_fragment(bridge),data,coefs)
        base=execute_fragment(assemble_fragment(second_spec()),data,coefs)
        self.assertEqual(actual['ports'],base['ports'])
        self.assertEqual(actual['trace'][:-1],base['trace'])
        self.assertEqual([actual['data'][cell] for cell in bridge['output_addresses']],
                         [base['ports'][0],base['ports'][4]])
        self.assertEqual([len(p) for p in programs()],[86,194,226,194,202])
        combined=b''.join(programs()); stored=swap_words(combined+b'\0\0')
        self.assertEqual((len(combined),len(stored)),(902,904))
        self.assertEqual(swap_words(stored),combined+b'\0\0')
        self.assertEqual(sum(len(packets(p)) for p in programs()),53)
        for spec in program_specs():
            program=assemble_fragment(spec)
            self.assertEqual(disassemble_fragment(program),spec)
        for spec in (bridge,terminal_spec()):
            program=assemble_fragment(spec); fields=set()
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
            for changed in (program+b'\0\0',program[:-2]):
                self.assertRaises(ValueError,disassemble_fragment,changed)
            for offset,mask in ((34,0x40),(37,1)):
                changed=bytearray(program);changed[offset]^=mask
                self.assertRaises(ValueError,disassemble_fragment,bytes(changed))

    def test_invalid_resource_assignments_and_checked_qwen_cases(self):
        # Qwen's fourth suggestion duplicates target mismatch; add the missing T/S case.
        mutations=[('sources',0,True),('sources',4,2048),('coefficient_slots',3,15),
                   ('targets',1,63),('targets',3,64),('output_addresses',0,38),
                   ('sources',1,61),('output_addresses',1,0),('coefficient_slots',0,4096)]
        for field,index,value in mutations:
            spec=terminal_spec();spec[field][index]=value
            with self.subTest(field=field,index=index,value=value),self.assertRaises(ValueError):
                assemble_fragment(spec)
        for original in program_specs()[1:]:
            for field in ('sources','targets','coefficient_slots','output_addresses'):
                spec=copy.deepcopy(original);spec[field][0]=True
                self.assertRaises(ValueError,assemble_fragment,spec)
            self.assertRaises(ValueError,assemble_fragment,dict(original,extra=1))
        self.assertRaises(ValueError,assemble_fragment,dict(bridge_spec(),output_addresses=[0x35,0x61]))


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                         for name in ('zen_arm64','pairs.json','exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_native_bodies_and_five_fantom_relocations(self):
        from limit_control_study import native_context
        from fdrv_filterbank_study import report
        original,*_=native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(third_spec())[38:184],original[0x1aa:0x23c])
        self.assertEqual(assemble_fragment(terminal_spec())[38:192],original[0x23c:0x2d6])
        checked=report()
        self.assertEqual((checked['combined_bytes'],checked['prefix_instruction_count']),(902,494))
        self.assertFalse(checked['resampling_arithmetic_executed'])
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
            third=third_spec()
            for key in ('sources','targets','output_addresses'):
                third[key]=[base+cell for cell in third[key]]
            third['coefficient_slots']=[coefficient_base+slot for slot in third['coefficient_slots']]
            self.assertEqual(assemble_fragment(third)[38:184],stream[0x1aa:0x23c])
            self.assertEqual(assemble_fragment(terminal_spec(base,coefficient_base))[38:192],stream[0x23c:0x2d6])

    def test_changed_native_arithmetic_pointer_stack_and_coefficient_are_rejected(self):
        import lib
        from limit_control_study import native_context
        from fdrv_filterbank_study import report
        p,n,m,f,t=native_context('SIM_MFX_FDRV'); md=lib.md();md.detail=True
        for pc,replacement in ((0x305574,n[0x30559c]),(0x30587c,n[0x305844]),
                (0x30584c,next(md.disasm(bytes.fromhex('e20300aa'),0x30584c))),
                (0x30584c,next(md.disasm(bytes.fromhex('ff430091'),0x30584c))),
                (0x30584c,n[0x305844]),(0x305880,n[0x30587c])):
            changed=dict(n);changed[pc]=replacement
            with patch('limit_control_study.native_context',return_value=(p,changed,m,f,t)):
                self.assertRaises(ValueError,report)
        changed=copy.deepcopy(t)
        next(row for row in changed['coefficient_reads'] if row['pc']>=0x30553c)['slot']=0
        with patch('limit_control_study.native_context',return_value=(p,n,m,f,changed)):
            self.assertRaises(ValueError,report)

    @unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64'
                         and hasattr(math,'fma'),'macOS ARM64/Python 3.13+ required')
    def test_independent_filterbank_ring_through_wrap(self):
        code=('import json;from fdrv_filter_study import native_check;'
              'print(json.dumps(native_check(2056,(1,2),compare_filterbank=True)))')
        run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,
                           timeout=45,env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode,0,run.stderr)
        checked=json.loads(run.stdout)
        self.assertEqual(checked['independent_packet_filterbank_values'],57568)
        self.assertTrue(checked['native_prefix_executed'])
        self.assertFalse(checked['native_callback_executed'])
        self.assertEqual(checked['native_prefix_end'],0x3058a4)
        self.assertEqual(checked['final_origin'],8)
        self.assertEqual(checked['final_cursors'],[1,2])
        self.assertFalse(checked['bmc_hardware_executed'])


if __name__=='__main__':unittest.main()
