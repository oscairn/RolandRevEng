import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_host_receiver_study import ReceiverOracle,HostImage,checked_events,coalesced_ranges,report


class ModelTests(unittest.TestCase):
    def test_union_first_arrival_order_and_native_context_aliases(self):
        self.assertEqual(coalesced_ranges([]),[])
        events=[(7,0,1,3505,3505),(6,0,0,3504,3504),(7,0,1,3504,3504)]
        self.assertEqual(coalesced_ranges(events),[(7,0,1,3504,3505),(6,0,0,3504,3504)])
        events=[(7,16383,255,3505,3505),(6,1,255,3505,3505),(7,0,0,3504,3504)]
        self.assertEqual(coalesced_ranges(events),[(7,0,0,3504,3505),(6,0,0,3505,3505)])

    def test_unchecked_events_fail_before_cpu_access(self):
        checked_events([(6,16383,255,3504,3505)])
        for events in (None,[(6,0,0,3504,3504)]*33,[(True,0,0,3504,3504)],
                [(8,0,0,3504,3504)],[(6,16384,0,3504,3504)],[(7,0,256,3504,3504)],
                [(6,0,0,3505,3504)],[(6,0,0,3503,3504)],[(6,0,0,4917,4917)]):
            self.assertRaises(ValueError,checked_events,events)
            self.assertRaises(ValueError,object.__new__(ReceiverOracle).run_case,events)
        self.assertRaises(ValueError,object.__new__(ReceiverOracle).run_case,[],True)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_HOST=(CORPUS/'mi078').exists()and all(importlib.util.find_spec(m)for m in ('capstone','elftools'))


@unittest.skipUnless(HAS_HOST,'Pinned host image and readers required')
class CorpusTests(unittest.TestCase):
    def test_static_activation_provider_rtti_and_distinct_emitter(self):
        data=(CORPUS/'mi078').read_bytes();r=report(HostImage(data))
        self.assertEqual(r['registry_static_initializer'],0x438240)
        self.assertEqual(r['family6_provider_rtti'],'CIDMinMaxBlock<1,1>')
        self.assertEqual(r['family7_provider_rtti'],'CIDMinMaxBlock<1,2>')
        self.assertTrue(r['sys_ex_kind2_destination8_source_checked'])
        self.assertFalse(r['sys_ex_emitter_executed'])
        self.assertFalse(r['full_worker_thread_executed'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertRaises(ValueError,HostImage,data[:-1]+bytes((data[-1]^1,)))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'),'Unicorn and private-RAM JIT permission required')
    def test_original_registry_receiver_coalescing_and_clean_drain_reuse(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_host_receiver_study.py'),
            str(CORPUS/'mi078'),'--execute-arm64'],text=True,capture_output=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_receiver_cases'],777)
        self.assertEqual(r['incoming_local_notifications'],2178)
        self.assertEqual(r['coalesced_emitter_calls'],1488)
        self.assertEqual(r['original_registry_allocations'],78)
        self.assertTrue(r['original_registry_receiver_provider_wake_and_drain_executed'])
        self.assertTrue(r['mutex_sem_thread_runtime_and_delays_intercepted'])
        self.assertFalse(r['sys_ex_emitter_executed'])
        self.assertFalse(r['host_to_core1_translation_proved'])


if __name__=='__main__':unittest.main()
