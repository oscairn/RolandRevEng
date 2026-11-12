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
from fantom_parameter_producer_study import ProducerOracle,normalized,checked_slot,report,fields


class ModelTests(unittest.TestCase):
    def test_descriptor_fallback_is_default_rather_than_edge_clamping(self):
        cutoff=(3740,20,16000,22,2)
        for value in (20,1000,16000):self.assertEqual(normalized(value,cutoff),value)
        for value in (19,16001,19000,-1):self.assertEqual(normalized(value,cutoff),3740)
        self.assertEqual(normalized(3,(2,0,2,20,2)),2)
        self.assertEqual(normalized(-1,(2,0,2,20,2)),2)

    def test_negative_minimum_controls_signed_halfword_decoding(self):
        gain=(-140,-240,240,18,2)
        self.assertEqual(normalized(-240,gain),-240);self.assertEqual(normalized(240,gain),240)
        self.assertEqual(normalized(-241,gain),-140)
        self.assertEqual(normalized(241,gain),-140)
        self.assertEqual([checked_slot(i)for i in (1,2,3)],[0,1,2])

    def test_bad_inputs_fail_before_cpu_or_descriptor_access(self):
        for value,descriptor in ((True,(2,0,2,20,2)),(32768,(2,0,2,20,2)),
                (0,(2,0,2,20,1)),(0,(2,3,1,20,2)),(0,(3,0,2,20,2)),
                (0,(2.,0,2,20,2)),(0,(2,0,2,20))):
            self.assertRaises(ValueError,normalized,value,descriptor)
        oracle=object.__new__(ProducerOracle)
        for index in (0,4,True):self.assertRaises(ValueError,oracle.producer,[0]*22,[0]*22,index=index)
        for previous,values,enabled in (([0]*21,[0]*22,True),([0]*22,[0]*23,True),
                ([0]*22,[0]*22,1),([0]*22,[False]*22,True)):
            self.assertRaises(ValueError,oracle.producer,previous,values,enabled=enabled)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_efct_registration_factory_id_and_stock_field_range(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['task']['id'],8);self.assertEqual(r['task']['name'],'EFCT')
        self.assertEqual(r['task']['irq'],139);self.assertEqual(r['task']['priority_byte'],0xe0)
        self.assertEqual(r['fdrv_factory_id'],85);self.assertEqual(r['stock_snapshot_count'],22)
        self.assertEqual(len(fields(core)),22)
        self.assertTrue(r['registered_task_to_setter_route_proved'])
        self.assertTrue(r['producer_reenables_task5_before_apply'])
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core);self.assertRaises(ValueError,ProducerOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and private-RAM JIT permission required')
    def test_original_irq_wrapper_producer_descriptor_fallback_and_fdrv(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/fantom_parameter_producer_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stderr);r=json.loads(result.stdout)
        self.assertEqual(r['original_registered_route_cases'],288)
        self.assertEqual(r['producer_coefficient_writes'],1080)
        self.assertEqual([row['normalized']for row in r['descriptor_fallback_cases']],
            [[2,3740],[2,3740],[1,3740],[0,3740]])
        self.assertTrue(r['irq_wrapper_body_executed'])
        self.assertTrue(r['original_notification_executed'])
        self.assertFalse(r['irq_arrival_or_preemption_observed'])
        self.assertFalse(r['hardware_task_execution_verified'])
        self.assertFalse(r['algorithm_change_path_executed'])


if __name__=='__main__':unittest.main()
