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
from fantom_parameter_dispatch_study import DispatchOracle,APPLY,UPDATE,inputs,report


class ModelTests(unittest.TestCase):
    def test_logical_live1_fields_modes_changed_sets_and_fixed_q(self):
        for mode in (0,1,2):
            result=inputs({2:mode,3:1000},[3],0,0)
            self.assertEqual(len(result),1);self.assertEqual(result[0]['type'],13 if mode else 0)
            self.assertEqual(result[0]['cutoff'],1000.)
            self.assertEqual(result[0]['q'],0.7070000171661377)
        self.assertEqual(inputs({2:1,3:1000},[],0,0),[])

    def test_unsupported_ui_inputs_fail_before_cpu_access(self):
        oracle=object.__new__(DispatchOracle)
        for values,changed,count,index in (({2:True,3:1000},[2],0,0),({2:3,3:1000},[2],0,0),
                ({2:1,3:-1},[3],0,0),({2:1,3:24000},[3],0,0),({2:1,3:1000},[14],0,0),
                ({2:1,3:1000},[True],0,0),({2:1},[2],0,0),({2:1,3:1000},[3],-1,0),
                ({2:1,3:1000},[3],0,4)):
            self.assertRaises(ValueError,oracle.parameter,values,changed,count,index)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_outer_vtable_parameter_rtti_and_mask_helpers(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['parameter_apply'],APPLY);self.assertEqual(r['outer_update'],UPDATE)
        self.assertEqual(r['fields'],[2,3]);self.assertFalse(r['helper_preserves_incoming_primask'])
        self.assertFalse(r['registered_task_to_setter_route_proved'])
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core);self.assertRaises(ValueError,DispatchOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and JIT permission required')
    def test_original_outer_parameter_mode_and_coefficient_dispatch_cli(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/fantom_parameter_dispatch_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=120)
        self.assertEqual(r.returncode,0,r.stderr);result=json.loads(r.stdout)
        self.assertEqual(result['original_dispatch_cases'],96)
        self.assertEqual(result['coefficient_writes_compared'],360)
        self.assertFalse(result['registered_task_to_setter_route_proved'])
        self.assertFalse(result['algorithm_change_path_executed'])
        self.assertFalse(result['firmware_startup_or_os_tasks_executed'])
        self.assertFalse(result['hardware_timing_verified'])


if __name__=='__main__':unittest.main()
