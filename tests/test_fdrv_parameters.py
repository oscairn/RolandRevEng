import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fdrv_parameter_study import live_targets,envelope_state,envelope_step,validate_events


@unittest.skipUnless(hasattr(math,'fma'),'Python3.13+ required')
class ReferenceTests(unittest.TestCase):
    def test_setter_targets_clamps_and_explicit_domains(self):
        self.assertEqual(live_targets('drive',[0.,0.]),{0:1.,1:1.})
        self.assertEqual(live_targets('wet',[-1.,0.]),{2:1.,3:0.})
        self.assertEqual(live_targets('wet',[2.,0.]),{2:0.,3:1.})
        self.assertEqual(live_targets('slope',[1,0]),{9:0.})
        self.assertEqual(live_targets('level',[-10],list(range(128))),{4:0.})
        self.assertEqual(live_targets('level',[200],list(range(128))),{4:127.})
        self.assertRaises(ValueError,live_targets,'level',[1<<32],list(range(128)))
        for method,args in (('drive',[math.nan,0]),('drive',[101.,0]),('wet',[.5,math.inf]),
            ('slope',[-1,1]),('slope',[True,1]),('level',[True]),('unknown',[]),([],[])):
            self.assertRaises(ValueError,live_targets,method,args)

    def test_envelope_endpoint_float32_stall_escape_and_retarget(self):
        state=envelope_state(0.,1.);before=state
        for _ in range(600):state=envelope_step(state)
        self.assertEqual(state[0],1.);self.assertEqual(state[2]&0xcc000000,0)
        self.assertEqual(before[0],0.)
        adjacent=struct.unpack('<f',struct.pack('<I',0x3f800001))[0]
        state=envelope_step(envelope_state(1.,adjacent,15))
        self.assertEqual(state[0],adjacent)
        state=envelope_step(envelope_state(-1.,-adjacent,15))
        self.assertEqual(state[0],-adjacent)
        state=envelope_step(envelope_state(.2,.8));retarget=envelope_state(state[0],-.3)
        self.assertEqual(retarget[0],state[0]);self.assertLess(retarget[1],0)
        for invalid in (-1,16,True):self.assertRaises(ValueError,envelope_state,0.,1.,invalid)

    def test_event_validation_preserves_order_and_input(self):
        events=[dict(frame=0,method='wet',args=[.3,0]),dict(frame=0,method='slope',args=[0,1])]
        before=copy.deepcopy(events);self.assertEqual(len(validate_events(events,8,None)),2);self.assertEqual(events,before)
        for bad in ([dict(frame=8,method='wet',args=[.3,0])],
            [dict(frame=2,method='wet',args=[.3,0]),dict(frame=1,method='wet',args=[.3,0])],
            [dict(frame=True,method='wet',args=[.3,0])],[dict(frame=0,method='wet',args=[.3,0],extra=1)]):
            self.assertRaises(ValueError,validate_events,bad,8,None)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','pairs.json','exports_dem.txt'))
CAN_EXECUTE=platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma')


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_all_live_slots_literal_copies_pow_import_and_hash_first_rejection(self):
        import lib
        from fdrv_parameter_study import report,imported_stub
        r=report();slots={c['slot']for c in r['live_setter_calls']}
        slots.update(v for p in r['state_filter_pieces']for v in p['slots'])
        self.assertEqual(slots,set(range(20)))
        groups={g['name']:g for g in r['literal_groups']}
        self.assertEqual([q['relative_byte']for q in groups['output_a']['records']],[0x4ea,0x4ed,0x536,0x539])
        self.assertEqual(len(groups),14);self.assertEqual(len(r['literal_setter_calls']),9)
        self.assertEqual(imported_stub(lib.Z,0x6d8c98),'_pow')
        self.assertEqual(imported_stub(lib.Z,0x6d8ca4),'_powf')
        self.assertRaises(ValueError,imported_stub,lib.Z,0x6d8c99)
        with patch('lib.Z',lib.Z[:-1]+bytes([lib.Z[-1]^1])):self.assertRaises(ValueError,report)
        self.assertFalse(r['filter_coefficient_generation_replayed'])

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(),'Pinned Fantom image required')
    def test_fantom_slot_dispatch_and_level_table_without_precision_equivalence(self):
        from core1 import Core1
        from fdrv_parameter_study import firmware_report
        c=Core1(CORPUS/'b0c1a.bin');r=firmware_report(c)
        self.assertEqual({v['slot']for v in r['live_setter_calls']},{0,1,2,3,4,8,9})
        self.assertEqual({v['manager_slot']for v in r['live_setter_calls']},{0xb0})
        self.assertIn('binary32',r['setter_arithmetic_precision'])
        self.assertFalse(r['firmware_setters_executed'])
        c.data=c.data[:-1]+bytes([c.data[-1]^1]);self.assertRaises(ValueError,firmware_report,c)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_native_envelope_trajectories_all_selectors_and_setter_math(self):
        from fdrv_parameter_study import native_envelope_probes,native_target_functions,native_live_targets
        cases=[(0.,1.,i)for i in range(16)]+[(1.,0.,i)for i in range(16)]+[
            (1.,1.+2.**-23,15),(-1.,-1.-2.**-23,15),(-0.,0.,10)]
        r=native_envelope_probes(cases,1100)
        self.assertEqual(r['compared_values'],len(cases)*1100*4)
        with native_target_functions()as funcs:
            for method,args in [('drive',[-12.,-6.]),('drive',[12.,3.]),('drive',[0.,0.]),
                ('wet',[-.2,-3.]),('wet',[.37,6.]),('wet',[1.2,0.]),('wet',[-0.,0.])]:
                self.assertEqual(native_live_targets(method,args,funcs,None),live_targets(method,args))

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_dynamic_full_audio_and_state_through_wrap_and_interrupted_ramps(self):
        events=json.loads((ROOT/'examples/fdrv-parameter-events.json').read_text())
        events=[e for e in events if e['frame']<2056]
        code=('import json;from fdrv_filter_study import native_check;'
            f'print(json.dumps(native_check(2056,(2,1),compare_full=True,parameter_events={events!r})))')
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=45,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr);result=json.loads(r.stdout)
        self.assertEqual(result['parameter_event_count'],len(events))
        self.assertEqual(result['coefficient_envelope_values_checked'],2056*80)
        self.assertEqual(result['independent_full_state_and_output_values'],2056*2058)
        self.assertEqual(result['final_origin'],8);self.assertTrue(result['final_stereo_output_checked'])


if __name__=='__main__':unittest.main()
