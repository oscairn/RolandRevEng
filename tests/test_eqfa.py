import copy
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
from eqfa_study import coefficients,taps,encoded_taps,validate_events,CLAMP_FACTOR
from eqfa_ui_study import events as ui_events,FIELDS,TYPE_MAP


@unittest.skipUnless(hasattr(math,'fma'),'Python3.13+ required')
class MathTests(unittest.TestCase):
    def test_types_order_zero_cutoff_and_checked_domain(self):
        self.assertEqual(coefficients(1,1000),(0.,0.,0.))
        for kind in (0,2,3,4,5,6,7,8):self.assertEqual(coefficients(kind,0),(1.,0.,0.))
        for kind in range(9):
            a,b,c=coefficients(kind,1000,6.)
            self.assertEqual(taps(kind,1000,6.),(a,c,b))
        a,b,c=coefficients(6,1000);self.assertEqual(a,c);self.assertEqual(b,math.fma(a,-2.,1.))
        a,b,c=coefficients(7,1000);self.assertEqual(a,-c);self.assertEqual(b,math.fma(a,2.,-1.))
        a,b,c=coefficients(8,1000);self.assertEqual(a,-b);self.assertEqual(c,1.)
        for args in ((True,1000,0,44100),(9,1000,0,44100),(6,-1,0,44100),
            (6,1000,math.nan,44100),(6,44100*.5*CLAMP_FACTOR,0,44100),(6,1000,0,0)):
            self.assertRaises(ValueError,coefficients,*args)

    def test_native_literal_policy_is_explicit_bounded_and_different_from_encoded(self):
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from fdrv_resample_study import resample_spec,resample_reference
        from fdrv_cascade_study import cascade_spec,cascade_reference
        raw=taps(3,1200.,-3.);packed=encoded_taps(raw)
        spec=resample_spec(taps=packed);program=assemble_fragment(spec)
        values=[.0123,-.0345,.0567,-.0234,.0456,-.0678,.0789];data=dict(zip(spec['sources'],values))
        before=data.copy();r=execute_fragment(program,data,{0:8192.},native_literals=raw)
        ref=resample_reference(*values[:3],raw,8192.)
        self.assertEqual(r['data'][1].hex(),ref['history'].hex())
        self.assertEqual(r['data'][0x62].hex(),ref['output'].hex());self.assertEqual(data,before)
        encoded=execute_fragment(program,data,{0:8192.})
        self.assertNotEqual(r['data'][1].hex(),encoded['data'][1].hex())
        self.assertRaises(ValueError,execute_fragment,program,data,{0:8192.},native_literals=[raw[0]+.01,*raw[1:]])
        self.assertRaises(ValueError,execute_fragment,program,data,{0:8192.},native_literals=[math.nan,*raw[1:]])
        raw=(*taps(3,300.,6.),*taps(7,120.,0.));spec=cascade_spec(coefficients=encoded_taps(raw))
        values=[.12,-.23,.34,-.45,-.56,.67,-.78,.89,0.,0.,0.,0.]
        r=execute_fragment(assemble_fragment(spec),dict(zip(spec['sources'],values)),{},native_literals=raw)
        for channel in (0,1):
            ref=cascade_reference(*values[4*channel:4*channel+4],raw)
            for cell,key in ((spec['targets'][channel],'first'),(spec['targets'][channel+2],'second')):
                self.assertEqual(r['data'][cell].hex(),ref[key].hex())
        self.assertRaises(ValueError,execute_fragment,assemble_fragment(spec),{}, {},native_literals=raw[:3])

    def test_event_schema_order_and_no_implicit_literal_clipping(self):
        event=dict(frame=0,stage='resample',type=6,cutoff=1000.,gain=0.)
        self.assertEqual(validate_events([event],2)[0][2],taps(6,1000.))
        for changed in (dict(event,frame=True),dict(event,stage='unknown'),dict(event,rate=48000),
            dict(event,type=4,gain=96.,cutoff=20.)):
            self.assertRaises(ValueError,validate_events,[changed],2)
        self.assertRaises(ValueError,validate_events,[dict(event,frame=1),event],2)


class UiTests(unittest.TestCase):
    def test_group_flags_selector_lookup_and_float32_gain_scaling(self):
        values={0:200,1:17,4:1,5:4000,6:-31,8:3,9:600,10:63,11:2,12:90,13:0}
        before=copy.deepcopy(values);r=ui_events(values,[0,6,9,13],7)
        self.assertEqual([e['stage']for e in r],['input','resample','post0','post1'])
        self.assertEqual([e['type']for e in r],[3,6,3,7]);self.assertEqual(values,before)
        self.assertEqual(r[1]['gain'],-3.0999999046325684)
        self.assertNotEqual(r[1]['gain'],-3.1)
        self.assertEqual(TYPE_MAP,(0,6,7,3,4));self.assertEqual(ui_events(values,[]),[])
        self.assertRaises(ValueError,ui_events,{4:1,5:1000},[5])
        self.assertRaises(ValueError,ui_events,dict(values,**{'2':1}),[5])
        bad=values.copy();bad[4]=5;self.assertRaises(ValueError,ui_events,bad,[4])
        self.assertRaises(ValueError,ui_events,values,[2])


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_NATIVE=importlib.util.find_spec('capstone')and all((CORPUS/n).exists()for n in ('zen_arm64','pairs.json','exports_dem.txt'))
CAN_EXECUTE=platform.system()=='Darwin'and platform.machine()=='arm64'and hasattr(math,'fma')


@unittest.skipUnless(HAS_NATIVE,'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_source_dispatch_imports_ui_slots_and_hash_first_rejection(self):
        import lib
        from eqfa_study import report
        from eqfa_ui_study import report as ui_report
        r=report();self.assertEqual(r['default_rate'],44100)
        self.assertEqual(set(r['imports'].values()),{'_cos','_tan','_pow'})
        self.assertEqual(len(r['dispatch_targets']),8)
        self.assertEqual(ui_report()['ui_type_map'],TYPE_MAP)
        with patch('lib.Z',lib.Z[:-1]+bytes([lib.Z[-1]^1])):
            self.assertRaises(ValueError,report);self.assertRaises(ValueError,ui_report)

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_native_coefficients_all_types_irregular_inputs_and_both_rates(self):
        from eqfa_study import native_function
        rng=random.Random(0x20ae90)
        with native_function()as native:
            for rate in (44100,48000):
                for kind in range(9):
                    cases=[(0.,0.),(rate/4,0.),(math.nextafter(rate*.5*CLAMP_FACTOR,0.),-6.)]+[
                        (rng.uniform(20.,rate*.45),rng.uniform(-24.,24.))for _ in range(24)]
                    for cutoff,gain in cases:
                        self.assertEqual([v.hex()for v in native(kind,cutoff,gain,rate)],
                                         [v.hex()for v in coefficients(kind,cutoff,gain,rate)])

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_original_ui_dispatch_each_changed_field_and_all_five_selectors(self):
        from eqfa_ui_study import native_function
        snapshot={0:200,1:17,4:1,5:4000,6:-31,8:3,9:600,10:63,11:2,12:90,13:0}
        with native_function()as native:
            for kind in range(5):
                values=dict(snapshot);values.update({4:kind,8:kind,11:kind})
                for changed in ([*sorted(FIELDS)],*[[k]for k in sorted(FIELDS)]):
                    self.assertEqual(native(values,changed,17),ui_events(values,changed,17))
            for event in json.loads((ROOT/'examples/fdrv-eqfa-events.json').read_text()):
                stage=event['stage'];indices={'input':(0,1),'resample':(4,5,6),
                    'post0':(8,9,10),'post1':(11,12,13)}[stage]
                raw=[int(event['cutoff']),round(event['gain']*10)]
                if stage!='input':raw.insert(0,TYPE_MAP.index(event['type']))
                self.assertEqual(native(dict(zip(indices,raw)),list(indices),event['frame']),[event])

    @unittest.skipUnless(CAN_EXECUTE,'macOS ARM64/Python3.13+ required')
    def test_audio_state_coefficient_order_and_explicit_literal_policies_through_wrap(self):
        source=json.loads((ROOT/'examples/fdrv-eqfa-events.json').read_text())
        events=[e for e in source if e['frame']<2056]
        code=('import json;from fdrv_filter_study import native_check;'
            f'print(json.dumps([native_check(2056,(1,2),compare_full=True,filter_events={events!r},'
            'filter_literal_policy=p)for p in ("native","encoded")]))')
        # Both wrap replays repeat the full source/constructor provenance checks.
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=120,
            env=dict(os.environ,PYTHONPATH=str(ROOT/'tools'),BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(r.returncode,0,r.stderr)
        for result in json.loads(r.stdout):
            self.assertEqual(result['filter_event_count'],len(events))
            self.assertEqual(result['filter_native_coefficients_checked'],3*len(events))
            self.assertEqual(result['independent_full_state_and_output_values'],2056*2058)
            self.assertEqual(result['coefficient_envelope_values_checked'],2056*80)
            self.assertGreater(result['nonexact_generated_literals'],0)
            self.assertGreater(result['max_literal_quantization_error'],0.)
            self.assertEqual(result['final_origin'],8)


if __name__=='__main__':unittest.main()
