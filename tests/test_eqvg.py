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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from eqvg_study import (TYPE_NAMES,coefficients,stored_coefficients,live_coefficients,
    output_coefficients,interpolation_stable,update_plan,validate_events)


@unittest.skipUnless(hasattr(math,'fma'),'Python3.13+ required')
class MathTests(unittest.TestCase):
    def test_q_clamps_bypass_domain_and_distinct_consumer_orders(self):
        for kind in TYPE_NAMES:
            self.assertEqual(coefficients(kind,0),(1.,-1.,1.,0.,0.))
            self.assertEqual(coefficients(kind,1000,q=-10),coefficients(kind,1000,q=.25))
            self.assertEqual(coefficients(kind,1000,q=256),coefficients(kind,1000,q=128))
        self.assertEqual(live_coefficients((.25,-.5,.75,1.,1.25)),(-.75,-.5,.75,1.25,1.))
        self.assertEqual(output_coefficients((.25,-.5,.75,1.,1.25)),(-.75,-.5,1.,.75,1.25))
        for args in ((True,1000),(8,1000),(13,-1),(13,22000),(13,5e-324),(9,1e-310,-96),(13,1000,math.nan)):
            self.assertRaises(ValueError,coefficients,*args)

    def test_valid_endpoints_can_have_an_unstable_interpolation_path(self):
        old=coefficients(13,20,q=.25);new=coefficients(13,19000,q=128)
        def jury(g,b):return min(-g*b,4+2*g*b-g*g)
        self.assertGreater(jury(*old[:2]),0);self.assertGreater(jury(*new[:2]),0)
        self.assertLess(jury(*[(a+b)*.5 for a,b in zip(old[:2],new[:2])]),0)
        self.assertFalse(interpolation_stable(*old[:2],*new[:2]))
        writes=update_plan(stored_coefficients(old)[:2],new)
        self.assertEqual([r['coefficient']for r in writes],[1,0,2,4,3])
        self.assertEqual([r['wait']for r in writes],[True,False,False,False,False])
        self.assertTrue(interpolation_stable(0,0,0,0))  # Endpoint validity is a separate requirement.

    def test_event_schema_and_bounded_output_literal_policy(self):
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from eqfa_study import encoded_taps
        from fdrv_output_study import output_spec,output_reference
        event=dict(frame=0,stage='output',type=13,cutoff=1200.,gain=0.,q=.707)
        self.assertEqual(len(validate_events([event],1)),1)
        for e in (dict(event,frame=True),dict(event,stage='bad'),dict(event,extra=1),dict(event,q=math.inf)):
            self.assertRaises(ValueError,validate_events,[e],1)
        self.assertRaises(ValueError,validate_events,[dict(event,frame=1),event],2)
        raw=output_coefficients(coefficients(13,1200.,q=.707));spec=output_spec(coefficients=encoded_taps(raw))
        program=assemble_fragment(spec);values=[.12,-.23,.34,-.45,-.56,.67,-.78,.89]
        r=execute_fragment(program,dict(zip(spec['sources'],values)),{2:.25,3:.5,4:.75},native_literals=raw)
        expected=output_reference(*values[:3],values[6],.5,.25,.75,raw)
        self.assertEqual(r['ports'][0].hex(),expected['output'].hex())
        self.assertEqual(r['data'][0x40].hex(),expected['state_s'].hex())
        self.assertRaises(ValueError,execute_fragment,program,{}, {},native_literals=[raw[0]+.1,*raw[1:]])
        changed=bytearray(program);changed[114]^=1
        self.assertRaises(ValueError,execute_fragment,bytes(changed),{}, {},native_literals=raw)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','pairs.json','exports_dem.txt'))
CAN_EXECUTE=platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma')


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_source_hash_type_names_descriptor_permutations_and_mutation_rejection(self):
        import lib
        from eqvg_study import report
        r=report();self.assertEqual(r['live_descriptors'][0]['descriptor_order_slots'],(10,11,12,14,13))
        self.assertEqual(r['imports'][0x6d86f8],'___sincos_stret')
        with patch('lib.Z',lib.Z[:-1]+bytes([lib.Z[-1]^1])):self.assertRaises(ValueError,report)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_generator_irregular_inputs_both_rates_and_q_boundaries(self):
        from eqvg_study import native_function
        rng=random.Random(0x20d8f4)
        for rate in (44100,48000):
            with native_function(rate)as native:
                for kind in TYPE_NAMES:
                    for q in (-1.,.25,128.,256.):
                        for _ in range(10):
                            cutoff=rng.uniform(10,rate*.49);gain=rng.uniform(-24,24)
                            self.assertEqual([v.hex()for v in native(kind,cutoff,gain,q)],
                                [v.hex()for v in coefficients(kind,cutoff,gain,q,rate)],(kind,cutoff,gain,q,rate))

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_stability_predicate_random_and_degenerate_cases(self):
        from eqvg_study import native_interpolation_function
        rng=random.Random(0x20defc)
        with native_interpolation_function()as native:
            for args in [(1,-1,1,-2),(1,-1,2,-1),(0,0,0,0),(1,-1,2,-.5)]+[
                    tuple(rng.uniform(-4,4)for _ in range(4))for _ in range(20000)]:
                self.assertEqual(native(*args),interpolation_stable(*args))

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_setter_order_wait_flags_and_output_batch_split(self):
        from eqvg_setter_study import native_function_setter
        old=coefficients(13,20,q=.25);current=stored_coefficients(old)[:2]
        with native_function_setter()as native,native_function_setter(True)as output:
            for kind in TYPE_NAMES:
                for cutoff in (20.,19000.):
                    for envelope in (False,True):
                        for offset in (False,True):
                            raw=coefficients(kind,cutoff,6.,128.)
                            plan=update_plan(current,raw,envelope=envelope,subtract_one=offset)
                            args=dict(current=current,envelope=envelope,subtract_one=offset)
                            self.assertEqual(native(kind,cutoff,6.,128.,**args),plan)
                            result=output(kind,cutoff,6.,128.,**args)
                            if not envelope:
                                expected=[dict(r,manager_slot=0xc8)for r in plan]
                            else:
                                groups=[plan[:1],plan[1:]]if plan[0]['wait']else[plan]
                                expected=[dict(manager_slot=0xf8,coefficients=[r['coefficient']+1 for r in group],
                                    values=[r['value']for r in group],count=len(group),time_selector=100)for group in groups]
                            self.assertEqual(result,expected)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_ui_types_float32_q_gain_and_companion_slope_updates(self):
        from eqfa_ui_study import native_function,vg_events,VG_FIELDS
        with native_function(eqvg=True)as native:
            for mode in (0,1,2):
                for selector in range(5):
                    v={2:mode,3:1600,14:selector,15:2400,16:-31,17:71}
                    for changed in ([*sorted(VG_FIELDS)],*[[i]for i in VG_FIELDS]):
                        self.assertEqual(native(v,changed,7),vg_events(v,changed,7))
        self.assertEqual(vg_events(v,[17])[0]['q'],7.099999904632568)
        self.assertRaises(ValueError,vg_events,{14:5,15:1000,16:0,17:7},[14])

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_full_immediate_setter_and_packet_replay_through_wrap_both_policies(self):
        events=[e for e in json.loads((ROOT/'examples/fdrv-eqvg-events.json').read_text())if e['frame']<2056]
        code=('import json;from fdrv_filter_study import native_check;'
            f'print(json.dumps([native_check(2056,(1,2),compare_full=True,vg_events={events!r},'
            'filter_literal_policy=p)for p in ("native","encoded")]))')
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=180,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr)
        for result in json.loads(r.stdout):
            self.assertEqual(result['vg_event_count'],len(events))
            self.assertEqual(result['vg_native_coefficients_checked'],5*len(events))
            self.assertEqual(result['vg_original_setter_writes_checked'],5*len(events))
            self.assertEqual(result['independent_full_state_and_output_values'],2056*2058)
            self.assertGreater(result['nonexact_generated_literals'],0)
            self.assertEqual(result['final_origin'],8)


if __name__=='__main__':unittest.main()
