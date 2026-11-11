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
from coefficient_manager_study import (literal_operations,ManagerModel,compare_snapshots,
    compare_action,report,native_manager,eqvg_check)


@unittest.skipUnless(hasattr(math,'fma'),'Python3.13+ required')
class ModelTests(unittest.TestCase):
    def test_literal_zero_sign_unchanged_final_targets_and_checked_domain(self):
        for amount in (-1,0,1):
            self.assertEqual(literal_operations([.5,-0.],[1.,-0.],amount),[('write',0,1.),('write',1,-0.)])
        self.assertEqual(literal_operations([],[],3),[('wait',1,True),('wait',1,True)])
        operations=literal_operations([.1,.2],[.9,.2],100)
        self.assertEqual(sum(op[0]=='wait'for op in operations),99)
        self.assertEqual(sum(op[0]=='write'for op in operations),101)
        self.assertEqual(operations[-1],('write',1,.2))
        for args in (([0.],[math.inf],3),([0.],[],2),([],[],True),([],[],4097),([1e308],[-1e308],2)):
            self.assertRaises(ValueError,literal_operations,*args)

    def test_counter_plus_one_and_preposted_flag_are_distinct_from_elapsed_time(self):
        model=ManagerModel([0.]);model.wait_samples(1,False)
        self.assertEqual(model.counter,2);model.step();self.assertEqual(model.counter,1)
        model.step();self.assertEqual(model.flag,4)
        model.wait_samples(1,True)
        self.assertEqual(model.clock,2);self.assertEqual(model.counter,2);self.assertEqual(model.flag,3)
        external=ManagerModel([0.],current=False);external.wait_samples(1)
        self.assertEqual(external.clock,0);self.assertEqual(external.counter,0)
        external.write_env(0,1.,wait=True)
        self.assertEqual(external.states[0][0],1.);self.assertFalse(external.active)
        posted=ManagerModel([0.],flag=4);posted.write_env(0,1.,wait=True)
        self.assertEqual(posted.states[0][0],0.);self.assertEqual(posted.active,{0})
        self.assertEqual(posted.clock,0)
        self.assertRaises(ValueError,model.write_env,True,1.)
        self.assertRaises(ValueError,model.write_env,0,math.nan)
        self.assertRaises(ValueError,model.wait_samples,4097)
        self.assertRaises(ValueError,ManagerModel,[],flag=3)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','exports_dem.txt'))
CAN_EXECUTE=platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma')


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_virtual_slots_imports_and_hash_first_rejection(self):
        import lib
        r=report();self.assertEqual(r['manager_vtable'],0x9e5408)
        self.assertEqual(len(r['regions']),19)
        self.assertEqual(r['primitive_imports'][0x6d8d58],'_pthread_cond_signal')
        with patch('lib.Z',lib.Z[:-1]+bytes([lib.Z[-1]^1])):self.assertRaises(ValueError,report)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_literal_empty_and_maximum_counts_with_bit_exact_operation_trace(self):
        for size in (0,127):
            initial=[-.0 if i%2 else .123 for i in range(size)]
            targets=[a if i%3 else -.456 for i,a in enumerate(initial)]
            with native_manager([0.],literal_initial=initial)as native:
                model=ManagerModel([0.],literal_initial=initial)
                compare_action(model,native,lambda x:x.interpolate(list(range(size)),targets,-3))
                self.assertEqual(native.clock,4)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_live_wait_contexts_bitmap_word_boundaries_restarts_and_zero_increment(self):
        for current in (True,False):
            for flag in (3,4):
                with native_manager([0.]*130,current=current,flag=flag)as native:
                    model=ManagerModel([0.]*130,current=current,flag=flag)
                    actions=((0,1.,0,False),(63,-.5,15,False),(64,.5,10,True),
                        (129,0.,10,True),(0,-.25,1,False),(65,1e-45,15,True))
                    for slot,target,selector,wait in actions:
                        compare_action(model,native,lambda x:x.write_env(slot,target,selector,wait))
                        for _ in range(3):model.step();native.step();compare_snapshots(model,native)
        with native_manager([0.]*1024)as native:
            model=ManagerModel([0.]*1024)
            compare_action(model,native,lambda x:x.write_env(1023,0.,0,True))
            self.assertEqual(native.snapshot()['pending'],[1023])

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_wait_counter_deferred_posted_and_disabled_paths(self):
        for current,enabled in ((True,True),(True,False),(False,True)):
            with native_manager([0.],current=current,enabled=enabled)as native:
                model=ManagerModel([0.],current=current,enabled=enabled)
                for count,wait in ((0,True),(1,False),(1,True),(3,True)):
                    compare_action(model,native,lambda x:x.wait_samples(count,wait))
                    for _ in range(3):model.step();native.step();compare_snapshots(model,native)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_eqvg_setters_drive_original_manager_and_shared_flag_canary(self):
        live=eqvg_check();self.assertEqual(live['manager_requests'],5)
        self.assertEqual(live['wait_driven_ticks_compared'],530)
        self.assertEqual(live['total_fixture_ticks'],1060)
        self.assertGreater(live['minimum_jury_margin'],0)
        posted=eqvg_check(flag=4);self.assertEqual(posted['wait_driven_ticks_compared'],0)
        self.assertLess(posted['minimum_jury_margin'],0)
        literal=eqvg_check(True)
        self.assertEqual(literal['manager_requests'],2);self.assertEqual(literal['literal_wait_requests'],198)
        self.assertEqual(literal['total_fixture_ticks'],396)
        self.assertGreater(literal['minimum_jury_margin'],0)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_complete_native_protocol_cli_and_12000_tick_live_state_comparison(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/coefficient_manager_study.py'),'--execute-native'],
            capture_output=True,text=True,timeout=90,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr);result=json.loads(r.stdout)
        self.assertEqual(result['literal_context_cases'],40)
        self.assertEqual(result['live_record_fields_compared'],960000)
        self.assertEqual(result['explicit_live_sync_ticks'],12000)
        self.assertEqual(result['live_writes'],95)
        self.assertEqual(len(result['eqvg_protocol_cases']),4)
        self.assertFalse(result['os_primitives_executed']);self.assertFalse(result['hardware_timing_verified'])


if __name__=='__main__':unittest.main()
