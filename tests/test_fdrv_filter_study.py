import cmath
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_filter_study import filter_spec, filter_step, stability


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class FilterTests(unittest.TestCase):
    def test_reference_vectors_and_binary64_signal_preservation(self):
        first = filter_step(1, 0, 0, -.5, -.25, 0, .5, 0)
        self.assertEqual(first, dict(state_s=.5, state_t=0, highpass=1, output=.25))
        second = filter_step(.5, 1, .25, -.5, -.25, 0, .5, 0)
        self.assertEqual(second, dict(state_s=.75, state_t=.75, highpass=-.5, output=.875))
        precise = 1+2**-40
        self.assertEqual(filter_step(precise, 0, 0, -.5, -.25, 0, .5, 0)['output'], precise/4)
        self.assertEqual(filter_step(1e39, 0, 0, -.5, -.25, 0, .5, 0)['output'], 1e39/4)
        for bad in (True, None, math.nan, math.inf, 10**1000):
            self.assertRaises(ValueError, filter_step, bad, 0, 0, -.5, -.25, 0, .5, 0)
        self.assertRaises(ValueError, filter_step, 1, 0, 0, 1e39, -.25, 0, .5, 0)
        self.assertRaises(ValueError, filter_step, 1, 1e308, 1e308, 1, -.25, 0, .5, 0)

    def test_jury_condition_agrees_with_independent_pole_calculation(self):
        for a, b, expected in ((-.5, -.25, True), (-1, -.25, False), (-.5, 0, False),
                                (0, -1.5, False), (1, -.25, False), (.125, -.1, True),
                                (-1.5, .25, True), (-1.5, -.25, False)):
            result = stability(a, b)
            self.assertEqual(result['stable'], expected)
            discriminant = cmath.sqrt(result['trace']**2-4*result['determinant'])
            poles = [(result['trace']+sign*discriminant)/2 for sign in (1, -1)]
            self.assertEqual(max(map(abs, poles)) < 1, expected)
            self.assertFalse(result['hardware_calibrated'])
        for bad in (True, math.nan, 1e39):
            self.assertRaises(ValueError, stability, bad, -.25)

    def test_profile_roundtrip_all_states_and_balanced_auxiliary_lifetime(self):
        spec = filter_spec()
        program = assemble_fragment(spec)
        self.assertEqual(len(program), 184)
        self.assertEqual(disassemble_fragment(program), spec)
        data = dict(zip(spec['sources'], [.5, .25, 1, -.75, .5, -.25, 11, 13, 17, 19], strict=True))
        original = data.copy()
        coefficients = dict(zip(spec['coefficient_slots'], [-.5, -.25, 0, .5, 0], strict=True))
        actual = execute_fragment(program, data, coefficients)
        for channel, y, s, t in ((0, .5, 1, .25), (1, -.75, -.25, .5)):
            model = filter_step(y, s, t, -.5, -.25, 0, .5, 0)
            self.assertEqual(actual['ports'][4*channel], model['output'])
            self.assertEqual(actual['data'][0x28+3*channel], model['state_s'])
            self.assertEqual(actual['data'][0x29+3*channel], model['state_t'])
        self.assertEqual(data, original)
        self.assertEqual([row['offset'] for row in actual['trace']],
                         [0, 14, 28, 38, 56, 86, 100, 118, 128, 158])
        self.assertEqual(actual['trace'][4]['auxiliary_saved'], {2: 1, 6: -.25})
        self.assertEqual(actual['trace'][5]['auxiliary_saved'], {2: 1, 6: -.25})
        self.assertEqual(actual['trace'][6]['auxiliary_saved'], {})
        self.assertEqual(actual['trace'][6]['after'][2], 1)
        self.assertEqual(actual['trace'][6]['after'][6], -.25)
        self.assertEqual(actual['trace'][-1]['auxiliary_saved'], {})
        self.assertEqual([actual['ports'][i] for i in (1, 2, 5, 6)], [17, 11, 19, 13])

    def test_invalid_aliases_controls_coefficients_and_truncation_are_rejected(self):
        for key, index, value in (('sources', 1, 0x2b), ('sources', 0, True),
                                  ('sources', 6, 0x28), ('targets', 0, 0x2a),
                                  ('coefficient_slots', 0, 14), ('coefficient_slots', 2, 0x1000)):
            changed = filter_spec()
            changed[key][index] = value
            self.assertRaises(ValueError, assemble_fragment, changed)
        program = assemble_fragment(filter_spec())
        for field in (40, 48, 62, 66, 82, 88, 102, 108, 120, 128, 172):
            changed = bytearray(program)
            changed[field] ^= 1
            self.assertRaises(ValueError, disassemble_fragment, bytes(changed))
        self.assertRaises(ValueError, disassemble_fragment, program[:-2])
        self.assertRaises(ValueError, disassemble_fragment, program+bytes(2))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_unchanged_native_paired_body_and_producer_instruction_anchors(self):
        from fdrv_filter_study import report
        from limit_control_study import native_context
        report()
        program, native, memory, fields, trace = native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(filter_spec())[38:], program[0x66:0xf8])
        changed = dict(native)
        changed[0x305250] = native[0x305214]
        with patch('limit_control_study.native_context', return_value=(program, changed, memory, fields, trace)):
            self.assertRaises(ValueError, report)

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_five_fantom_bodies_with_typed_state_and_coefficient_substitutions(self):
        from bmc_dsp import swap_words
        from core1 import Core1
        from fdrv_cubic_study import fantom_report
        from kernel_abi import program_list, read
        core = Core1(CORPUS/'b0c1a.bin')
        placements = fantom_report(core)
        for row, segment, coefficient in zip(placements, program_list(core, 0x610e5a94)['segments'],
                [0x190, 0x1f4, 0x208, 0x21c, 0xe], strict=True):
            spec = filter_spec()
            for key in ('sources', 'targets'):
                spec[key] = [row['data_base']+value for value in spec[key]]
            spec['coefficient_slots'] = [coefficient+slot for slot in spec['coefficient_slots']]
            stream = swap_words(read(core, segment['source'], (segment['length']+3) & ~3))
            emitted = assemble_fragment(spec)
            self.assertEqual(emitted[38:], stream[0x66:0xf8])
            self.assertEqual(disassemble_fragment(emitted), spec)


@unittest.skipUnless(HAS_NATIVE and hasattr(math, 'fma') and platform.system() == 'Darwin'
                     and platform.machine() == 'arm64', 'macOS ARM64, Python 3.13+ and native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_full_native_callback_against_both_models_through_wrap_and_all_cursor_pairs(self):
        command = '''import json
from fdrv_filter_study import native_check
rows=[native_check(128,(left,right),True) for left in range(3) for right in range(3)]
rows.append(native_check(12000,(1,2),True))
rows.append(native_check(1,(0,2),True,[-0.0,0.0,0.0,-0.0]))
rows.append(native_check(1,(2,1),True,[1e39,0.0,1+2**-40,0.0]))
print(json.dumps(rows))'''
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', command], capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = json.loads(run.stdout)
        self.assertEqual(sum(row['identical_native_values'] for row in rows), 105232)
        self.assertEqual(rows[9]['final_origin'], 1760)
        self.assertTrue(all(row['initial_cursors'] == row['final_cursors'] for row in rows))
        self.assertTrue(all(row['coefficient_sources'] != row['coefficients'] for row in rows))
        self.assertTrue(all(row['emulator_checked'] and not row['bmc_hardware_executed'] for row in rows))


if __name__ == '__main__':
    unittest.main()
