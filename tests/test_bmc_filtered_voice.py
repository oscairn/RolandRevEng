import cmath
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import bmc_allpass_voice as voice
import bmc_filtered_voice as filtered
from bmc_dsp import packets, swap_words
from bmc_subset import assemble_fragment, disassemble_fragment
from fantom_voice_plan import (OWNERS, build_plan, render_check, required_initial_data,
                               transfer_fields, verify_relocation)
from fdrv_filter_study import filter_step
from voice_owner_fit_study import fit, requirements


def response(coefficients, frequency):
    a, b, c, d, e = coefficients
    g, q = 1+a, -b
    r = cmath.exp(-2j*math.pi*frequency/48000)
    denominator = 1+(-2+g*q+g*g)*r+(1-g*q)*r*r
    numerator = c*denominator+e*(1-2*r+r*r)+d*g*(1-r*r)
    return abs(numerator/denominator)


class DesignTests(unittest.TestCase):
    def test_float32_coefficients_ideal_dc_and_relative_stopband(self):
        design = filtered.design_lowpass(1000)
        values = design['coefficients']
        self.assertTrue(design['stability']['stable'])
        self.assertFalse(design['hardware_calibrated'])
        self.assertEqual(design['nominal_cutoff'], 1000)
        self.assertTrue(all(value == struct.unpack('<f', struct.pack('<f', value))[0] for value in values))
        self.assertAlmostEqual(response(values, 0), 1, delta=1e-10)
        self.assertLess(response(values, 8000), .05*response(values, 100))
        self.assertLess(response(filtered.design_lowpass(100)['coefficients'], 440),
                        .1*response(filtered.design_lowpass(3000)['coefficients'], 440))

    def test_nonfinite_quantized_zero_and_unstable_controls_are_rejected(self):
        for cutoff in (True, None, math.nan, math.inf, 10**1000, 0, -1, 1e-12, 23999, 24000):
            self.assertRaises(ValueError, filtered.design_lowpass, cutoff)
        for damping in (True, None, math.nan, math.inf, 10**1000, 0, -1, 1e-100):
            self.assertRaises(ValueError, filtered.design_lowpass, 1000, damping)


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class VoiceTests(unittest.TestCase):
    def test_shared_ring_matches_separate_voice_and_scalar_filter_through_wrap(self):
        actual, result = filtered.render(12000, 440)
        raw, _ = voice.render(12000, 440)
        states = [(0., 0.), (0., 0.)]
        coefficients = result['filter_design']['coefficients']
        for samples, inputs in zip(actual, raw, strict=True):
            for channel, (s, t) in enumerate(states):
                expected = filter_step(inputs[channel], s, t, *coefficients)
                self.assertEqual(samples[channel].hex(), expected['output'].hex())
                states[channel] = expected['state_s'], expected['state_t']
        self.assertEqual((result['program_bytes'], result['total_packet_count']), (384, 28))
        self.assertEqual(result['final_native_ring_origin'], 1760)
        self.assertEqual(len(result['initial_data']), 10)
        self.assertEqual(len(result['coefficients']), 11)
        self.assertFalse(result['full_engine_ready'])
        self.assertFalse(result['hardware_execution_verified'])

    def test_resources_field_protection_seed_dependencies_and_stored_order(self):
        from header_study import UnsupportedLayout, layout
        original = filtered.programs()
        logical = b''.join(original)
        self.assertEqual(logical[:200], b''.join(voice.programs()))
        self.assertEqual(swap_words(filtered.storage_program()), logical)
        self.assertEqual(required_initial_data(original),
                         [0x21, 0x29, 0x2a, 0x2c, 0x2d, 0x31, 0x41, 0x51, 0x61, 0x71])
        fields = transfer_fields(original)
        self.assertEqual(len(fields), 58)
        self.assertEqual(len(verify_relocation(original, 0, 0, [0x2016, 0x2017], original)), 58)
        self.assertNotIn(0x112, {field['field'] for field in fields})
        for packet in (0x100, 0x12c):
            self.assertRaises(UnsupportedLayout, layout, dict(packets(logical))[packet])
        changed = disassemble_fragment(original[-1])
        changed['sources'][6] = 0x22
        self.assertRaises(ValueError, verify_relocation, (*original[:3], assemble_fragment(changed)),
                          0, 0, [0x2016, 0x2017], original)
        needed = requirements(original)
        self.assertEqual((needed['body_bytes'], needed['data_extent'], needed['coefficient_extent']), (384, 146, 11))
        owner = dict(address=0, dsp=4, render=[dict(base=0x4020, capacity=384)],
                     memories={0: [dict(base=0x100, length=146)], 6: [dict(base=0x190, length=11)]})
        self.assertTrue(fit(owner, original)['body_capacity_fits'])
        for resource in ('program', 'data', 'coefficients'):
            candidate = copy.deepcopy(owner)
            if resource == 'program':
                candidate['render'][0]['capacity'] -= 1
            else:
                candidate['memories'][0 if resource == 'data' else 6][0]['length'] -= 1
            self.assertFalse(fit(candidate, original)['fits'][resource])

    def test_silence_and_invalid_render_inputs(self):
        rows, _ = filtered.render(128, 440, gain=0)
        self.assertTrue(all(value == 0 for row in rows for value in row))
        for frames in (True, 127, 128.0, 1000001):
            self.assertRaises(ValueError, filtered.render, frames, 440)
        for parameters in ({'gain': True}, {'gain': -1}, {'cutoff': 0}, {'damping': 0}):
            self.assertRaises(ValueError, filtered.render, 128, 440, **parameters)

    def test_cli_without_vendor_inputs_and_existing_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'filtered.wav'
            command = [sys.executable, str(ROOT/'tools/bmc_filtered_voice.py'), str(output), '--frames', '128']
            env = dict(os.environ, BMC_CORPUS_DIR=str(Path(directory)/'absent'))
            run = subprocess.run(command, capture_output=True, text=True, timeout=30, env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['program_bytes'], 384)
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnchannels(), wav.getnframes(), wav.getframerate()), (2, 128, 48000))
            before = output.read_bytes()
            repeated = subprocess.run(command, capture_output=True, text=True, timeout=30, env=env)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(output.read_bytes(), before)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS and hasattr(math, 'fma'), 'Pinned Fantom corpus and Python 3.13+ required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.core = Core1(CORPUS/'b0c1a.bin')

    def test_all_five_layouts_preserve_old_body_and_add_ten_seeds_eleven_coefficients(self):
        for owner in OWNERS:
            original, _ = build_plan(self.core, owner)
            fragments, result = build_plan(self.core, owner, cutoff=1000)
            self.assertEqual(fragments[:3], original)
            self.assertEqual(result['body_bytes'], 384)
            self.assertEqual(result['fragment_sizes'], [38, 82, 80, 184])
            self.assertEqual(len(result['initial_data']), 10)
            self.assertEqual(len(result['coefficients']), 11)
            self.assertEqual(len(result['address_changes']), 58)
            self.assertEqual(len(result['cpu_float32_data_sources']), 10)
            self.assertEqual(len(result['cpu_float32_coefficient_sources']), 11)
            self.assertIsNone(result['load_address'])
            self.assertFalse(result['wrapper_included'])
            self.assertFalse(result['output_io_writes_included'])
            self.assertFalse(result['execution_ready'])
        first, a = build_plan(self.core, OWNERS[0], cutoff=100)
        second, b = build_plan(self.core, OWNERS[0], cutoff=3000)
        self.assertEqual(first, second)
        self.assertNotEqual(a['coefficients'], b['coefficients'])

    def test_five_relocations_match_through_wrap_with_nonseed_canaries(self):
        for owner in OWNERS:
            _, result = render_check(self.core, owner, cutoff=1000)
            self.assertEqual(result['reference_check']['identical_output_values'], 4112)
            self.assertEqual(result['reference_check']['final_origin'], 8)
            self.assertTrue(result['reference_check']['nonseed_background_canaries'])

    def test_missing_state_seed_and_unused_damping_are_rejected(self):
        initialize = filtered.initialize
        def missing(*args):
            ring, coefficients, seed = initialize(*args)
            seed['initial_data'].pop(0x29)
            return ring, coefficients, seed
        with patch('bmc_filtered_voice.initialize', side_effect=missing):
            self.assertRaisesRegex(ValueError, 'read-before-write', build_plan, self.core, OWNERS[0], cutoff=1000)
        self.assertRaises(ValueError, build_plan, self.core, OWNERS[0], damping=.5)

    def test_filtered_plan_cli_exports_only_original_bytes_and_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'plan'
            command = [sys.executable, str(ROOT/'tools/fantom_voice_plan.py'), str(CORPUS/'b0c1a.bin'),
                       str(output), '--cutoff', '1000', '--frames', '128']
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['body_bytes'], 384)
            logical = (output/'body-logical.bin').read_bytes()
            self.assertEqual(swap_words((output/'body-stored.bin').read_bytes()), logical)
            self.assertFalse(result['execution_ready'])
            before = {path.name: path.read_bytes() for path in output.iterdir()}
            repeated = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
