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
from fantom_parameter_buffer_study import BUFFERS,BufferOracle,initial_state,update_state,report


class ModelTests(unittest.TestCase):
    def test_first_identical_snapshot_marks_prefix_then_repeat_clears_it(self):
        original=initial_state(32,[-32768,32767]+[0]*30)
        first=update_state(original,[-32768,32767])
        self.assertEqual(first['count'],2);self.assertEqual(first['changed'],[1]*32)
        self.assertEqual(update_state(first,[-32768,32767])['changed'],[0,0]+[1]*30)
        self.assertEqual(original['count'],0)

    def test_zero_shrink_growth_and_oversize_keep_unvisited_state(self):
        state=update_state(initial_state(20,list(range(20))),list(range(20)))
        state=update_state(state,[0]*20)
        self.assertEqual(state['changed'],[0]+[1]*19)
        shrunk=update_state(state,[0,0])
        self.assertEqual(shrunk['changed'],[0,0]+[1]*18)
        grown=update_state(shrunk,[0,0,0])
        self.assertEqual(grown['changed'],[0,0,0]+[1]*17)
        empty=update_state(grown,[])
        self.assertEqual(empty['count'],0);self.assertEqual(empty['changed'],grown['changed'])
        self.assertEqual(update_state(empty,[0,0])['changed'][:3],[1,1,0])
        self.assertEqual(update_state(empty,[7]*21),empty)

    def test_signed_boundaries_and_caller_owned_values_are_preserved(self):
        values=[-32768,32767,-1,0,1]*4
        state=initial_state(20,values);values[0]=9
        self.assertEqual(state['values'][0],-32768)
        updated=update_state(state,[32767,-32768])
        self.assertEqual(updated['values'],[32767,-32768]+state['values'][2:])
        self.assertEqual(updated['changed'],[1]*20)

    def test_invalid_storage_or_connected_inputs_fail_before_cpu_access(self):
        for capacity,values in ((True,[0]),(21,[0]*21),(20,[0]*19),(20,[True]*20),(20,[32768]*20)):
            self.assertRaises(ValueError,initial_state,capacity,values)
        state=initial_state(24,[0]*24)
        for change in ({'count':-1},{'count':25},{'count':True},{'changed':[2]*24},{'changed':[0]*23}):
            self.assertRaises(ValueError,update_state,dict(state,**change),[])
        for values in ([False],[32768],[-32769],b'\0\0'):
            self.assertRaises(ValueError,update_state,state,values)
        oracle=object.__new__(BufferOracle)
        self.assertRaises(ValueError,oracle.snapshot,[0]*31,[0]*32)
        changed=[0]*32;changed[4]=1
        self.assertRaises(ValueError,oracle.snapshot,[0]*32,changed)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_template_rtti_factory_binding_and_source_identity(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');result=report(core)
        self.assertEqual(result['buffer_capacities'],[20,24,32])
        self.assertEqual(result['fdrv_buffer_capacity'],32)
        self.assertFalse(result['raw_count_is_bytes']);self.assertFalse(result['raw_flags_are_input'])
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core);self.assertRaises(ValueError,BufferOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and private-RAM JIT permission required')
    def test_original_prefix_copy_getters_and_connected_fdrv_dispatch(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_parameter_buffer_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr);result=json.loads(run.stdout)
        self.assertEqual(result['original_buffer_cases'],24)
        self.assertEqual(result['original_raw_dispatch_cases'],96)
        self.assertEqual(result['raw_dispatch_coefficient_writes'],360)
        self.assertTrue(result['original_buffer_routines_executed'])
        self.assertFalse(result['registered_task_to_setter_route_proved'])
        self.assertFalse(result['firmware_startup_or_os_tasks_executed'])
        self.assertFalse(result['hardware_timing_verified'])


if __name__=='__main__':unittest.main()
