import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_envelope_mode_study import (ModeOracle,INTERFACE,MANAGERS,QUERY,
    envelope_enabled,mute_transition,report)


class ModelTests(unittest.TestCase):
    def test_normal_count_domain_and_envelope_polarity(self):
        self.assertTrue(envelope_enabled(0))
        for count in (1,2,65535,0x7ffffffe):self.assertFalse(envelope_enabled(count))
        for count in (True,-1,1.5,0x7fffffff):self.assertRaises(ValueError,envelope_enabled,count)
        for index in (-1,4,True):self.assertRaises(ValueError,mute_transition,0,True,index)
        self.assertRaises(ValueError,mute_transition,0,1)
        self.assertRaises(ValueError,mute_transition,0,True,wait=1)

    def test_nested_mutes_defer_boundary_helpers_and_release_on_last_off(self):
        count=0;helpers=[];modes=[]
        for enabled in (True,True,False,False):
            count,calls=mute_transition(count,enabled,2,False)
            helpers.extend(calls);modes.append(envelope_enabled(count))
        self.assertEqual(count,0);self.assertEqual(modes,[False,False,False,True])
        self.assertEqual(helpers,[('gate',2,True),('skip',2,False),('skip',2,True),('gate',2,False)])
        self.assertEqual(mute_transition(0,True,wait=True),(1,[('gate',0,True),('skip',0,True)]))

    def test_zero_count_off_repeats_boundary_operations_without_underflow(self):
        self.assertEqual(mute_transition(0,False),(0,[('skip',0,True),('gate',0,False)]))
        self.assertEqual(mute_transition(2,False),(1,[]))

    def test_bad_fdrv_arguments_are_rejected_before_cpu_access(self):
        oracle=object.__new__(ModeOracle)
        for kwargs in (dict(counter=-1),dict(index=4),dict(filter_index=2),dict(filter_index=True)):
            args=dict(counter=0);args.update(kwargs)
            self.assertRaises(ValueError,oracle.fdrv,**args)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_rtti_manager_binding_counter_and_separate_completion_domains(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['query'],QUERY);self.assertEqual(r['interface'],INTERFACE)
        self.assertEqual(r['manager_array'],MANAGERS);self.assertEqual(r['manager_stride'],20)
        self.assertEqual(r['counter_addresses'],[0x2009bc34,0x2009bc38,0x2009bc3c,0x2009bc40])
        self.assertNotEqual(r['sample_wait_flag'],r['clear_completion_word'])
        self.assertFalse(r['source_task_identity_query'])
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core)
            self.assertRaises(ValueError,ModeOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and JIT permission required')
    def test_original_query_nested_counter_and_full_fdrv_caller_cli(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_envelope_mode_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['query_cases'],20);self.assertEqual(r['mute_transition_cases'],80)
        self.assertEqual(r['original_fdrv_caller_cases'],40)
        self.assertFalse(r['actual_task_exclusion_proved']);self.assertFalse(r['hardware_timing_verified'])


if __name__=='__main__':unittest.main()
