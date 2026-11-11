import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_eqvg_study import (ACTIVE_TYPES,FLAGS,ThumbOracle,coefficients,stored_coefficients,
    interpolation_stable,update_plan,literal_operations,control_request,report)


class ModelTests(unittest.TestCase):
    def test_fantom_fallback_q_and_checked_domain(self):
        for kind in range(17):
            self.assertEqual(coefficients(kind,0),(0.,0.,1.,0.,0.))
            if kind not in ACTIVE_TYPES:self.assertEqual(coefficients(kind,1000),(0.,0.,1.,0.,0.))
        self.assertEqual(coefficients(13,1000,q=-10),coefficients(13,1000,q=.25))
        self.assertEqual(coefficients(13,1000,q=256),coefficients(13,1000,q=128))
        for args in ((True,1000),(17,1000),(13,-1),(13,24000),(13,5e-324),(13,1000,math.nan)):
            self.assertRaises(ValueError,coefficients,*args)

    def test_g_rounds_before_subtracting_one(self):
        g=coefficients(13,10000,q=.707)[0]
        self.assertEqual(stored_coefficients((g,0,0,0,0))[0],-0.06153059005737305)
        self.assertEqual(stored_coefficients((g,0,0,0,0),False)[0],g)
        self.assertEqual(stored_coefficients(coefficients(0,1000)),(-1.,0.,1.,0.,0.))
        self.assertRaises(ValueError,stored_coefficients,[1,2])

    def test_waited_order_and_immediate_order_are_distinct(self):
        current=stored_coefficients(coefficients(13,20,q=.25))[:2]
        raw=coefficients(13,19000,q=128)
        self.assertFalse(interpolation_stable(current[0]+1,current[1],raw[0],raw[1]))
        live=update_plan(current,raw)
        self.assertEqual([v['coefficient']for v in live],[1,0,2,4,3])
        self.assertEqual([v['wait']for v in live],[True,False,False,False,False])
        immediate=update_plan(current,raw,envelope=False)
        self.assertEqual([v['coefficient']for v in immediate],[0,1,2,4,3])
        self.assertEqual({v['manager_slot']for v in immediate},{0xc0})
        output=update_plan(current,raw,output=True)
        self.assertEqual([v['coefficients']for v in output],[[1],[0,2,4,3]])
        self.assertEqual([v['amount']for v in output],[100,100])

    def test_literal_count_rounding_and_unchanged_final_target(self):
        self.assertEqual(literal_operations([],[],3),[('wait',1,True),('wait',1,True)])
        self.assertEqual(literal_operations([0],[1],-3),literal_operations([0],[1],3))
        self.assertEqual(literal_operations([.5,-0.],[1.,-0.],0),[('write',0,1.),('write',1,-0.)])
        ops=literal_operations([.1,.2],[.9,.2],100)
        self.assertEqual(sum(v[0]=='wait'for v in ops),99)
        self.assertEqual(sum(v[0]=='write'for v in ops),101)
        for args in (([0],[],2),([],[],True),([],[],257),([0],[math.inf],3)):
            self.assertRaises(ValueError,literal_operations,*args)

    def test_control_clears_only_waited_envelope_bit_before_arm(self):
        request=control_request(3,.123)
        self.assertEqual(request['flags'],1);self.assertEqual(request['control'],0x29a00000)
        self.assertEqual(control_request(3,.123,wait=False)['flags'],3)
        for kwargs in (dict(flags=-1),dict(selector=16),dict(event_ref=9),dict(wait=1)):
            args=dict(flags=3,target=1.);args.update(kwargs)
            self.assertRaises(ValueError,control_request,**args)

    def test_execution_rejects_unadmitted_entries_and_negative_it_path(self):
        oracle=object.__new__(ThumbOracle)
        self.assertRaises(ValueError,oracle._run,0)
        self.assertRaisesRegex(ValueError,'Unicorn IT-path',oracle.interpolate,[0.]*5,[1.]*5,-3)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_hash_first_descriptors_and_real_vtable(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['live_descriptors'][0]['raw_field_slots'],(10,11,12,14,13))
        self.assertEqual(r['manager_slots'][0xb8],0x011350cd)
        self.assertEqual([v['relative']for v in r['output_groups'][0]['records']],[0x4ea,0x4ed,0x536,0x539])
        self.assertEqual(r['envelope_flag'],FLAGS)
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core)
            self.assertRaises(ValueError,ThumbOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 required; JIT execution must be permitted')
    def test_full_selected_entry_cli_and_control_protocol(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_eqvg_study.py'),str(CORPUS/'b0c1a.bin'),
            '--execute-thumb'],capture_output=True,text=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr)
        r=json.loads(run.stdout)
        self.assertEqual(r['regular_coefficient_fields_compared'],4080)
        self.assertEqual(r['irregular_coefficient_fields_compared'],500)
        self.assertEqual(r['stability_cases_compared'],2000)
        self.assertEqual(r['setter_cases_compared'],48)
        self.assertEqual(r['control_cases_compared'],48)
        self.assertEqual(r['literal_cases_compared'],20)
        self.assertEqual(r['literal_sample_wait_requests_compared'],408)
        self.assertFalse(r['hardware_execution_verified'])
        self.assertFalse(r['real_caller_exclusion_proved'])
        self.assertFalse(r['negative_amount_execution_verified'])
        self.assertFalse(r['os_or_firmware_startup_executed'])


if __name__=='__main__':unittest.main()
