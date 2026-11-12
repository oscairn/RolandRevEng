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
from fantom_host_write_study import WriteOracle,HostImage,clamped_value,report


class ModelTests(unittest.TestCase):
    def test_host_clamp_differs_from_halfword_truncation(self):
        self.assertEqual(clamped_value(65537,0,2),2)
        self.assertEqual(clamped_value(65535,20,16000),16000)
        self.assertEqual(clamped_value(65537,-20000,20000),20000)
        self.assertEqual(clamped_value(-1,-20000,20000),-1)
        self.assertEqual(clamped_value(-2147483648,20,16000),20)
        self.assertEqual(clamped_value(2147483647,-20000,20000),20000)
        self.assertEqual(clamped_value(16000,20,16000),16000)
        class IntSubclass(int):pass
        for value in (True,1.,IntSubclass(1),-2147483649,2147483648):
            self.assertRaises(ValueError,clamped_value,value,0,2)

    def test_unchecked_edit_arguments_fail_before_cpu_access(self):
        oracle=object.__new__(WriteOracle)
        for placement,param,value,gate,canary in ((3,3504,1,0,0),(True,3504,1,0,0),
                (0,3503,1,0,0),(0,3504,True,0,0),(0,3504,1,1,0),
                (0,3504,1,True,0),(0,3504,1,0,256),(0,3504,2147483648,0,0)):
            self.assertRaises(ValueError,oracle.edit,placement,param,value,gate,canary)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORPUS=all((CORPUS/f).exists()for f in ('mi078','b0c1a.bin'))and all(importlib.util.find_spec(m)for m in ('capstone','elftools'))


@unittest.skipUnless(HAS_CORPUS,'Pinned host/CORE1 corpus and readers required')
class CorpusTests(unittest.TestCase):
    def test_original_wrapper_and_writer_source_binding(self):
        from core1 import Core1
        image=HostImage((CORPUS/'mi078').read_bytes());core=Core1(CORPUS/'b0c1a.bin')
        r=report(image,core)
        self.assertEqual(r['original_edit_wrappers'],[0x478d60,0x478dd8])
        self.assertTrue(r['host_writer_clamps_to_descriptor_bounds'])
        self.assertTrue(r['checked_live1_identical_values_still_written'])
        self.assertFalse(r['optional_notify_flag_live_value_proved'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        with patch.object(core,'data',core.data[:-1]+bytes((core.data[-1]^1,))):
            self.assertRaises(ValueError,report,image,core)

    @unittest.skipUnless(importlib.util.find_spec('unicorn'),'Unicorn and private-RAM JIT permission required')
    def test_original_scalar_edits_storage_and_routed_messages(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_host_write_study.py'),
            str(CORPUS/'mi078'),str(CORPUS/'b0c1a.bin'),'--execute-arm64'],
            text=True,capture_output=True,timeout=150)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_host_scalar_edit_cases'],648)
        self.assertEqual(r['serialized_edit_messages'],2268)
        self.assertEqual(r['identical_store_edits_still_written_and_notified'],72)
        self.assertEqual([(e['parameter'],e['stored'])for e in r['clamp_examples']],
            [(3504,20000),(3505,20000),(4917,2),(4918,16000)])
        self.assertTrue(r['original_wrapper_writer_destructor_callback_route_executed'])
        self.assertTrue(r['output_queues_mutex_effects_and_global_flag_seeded'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertFalse(r['core1_slot_assignment_proved'])


if __name__=='__main__':unittest.main()
