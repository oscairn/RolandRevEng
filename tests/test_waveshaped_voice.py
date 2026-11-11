"""Cubic/filter composition and the non-word-aligned original voice body."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import bmc_allpass_voice as voice
import bmc_filtered_voice as filtered
from bmc_dsp import packets, swap_words
from bmc_subset import assemble_fragment, disassemble_fragment
from fantom_voice_plan import (OWNERS, build_plan, render_check, required_initial_data,
                               transfer_fields, verify_relocation, write_plan)
from fdrv_cubic_study import cubic_reference
from fdrv_filter_study import filter_step
from voice_owner_fit_study import fit, requirements


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class VoiceTests(unittest.TestCase):
    def test_independent_scalar_shape_filter_matches_twelve_thousand_frames(self):
        actual, result = filtered.render(12000, 440, waveshape=True)
        inputs, _ = voice.render(12000, 440)
        states = [(0., 0.), (0., 0.)]
        for observed, raw in zip(actual, inputs, strict=True):
            for channel, (s, t) in enumerate(states):
                expected = filter_step(cubic_reference(raw[channel]), s, t,
                                       *result['filter_design']['coefficients'])
                self.assertEqual(observed[channel].hex(), expected['output'].hex())
                states[channel] = expected['state_s'], expected['state_t']
        self.assertEqual((result['program_bytes'], result['stored_bytes'], result['total_packet_count']),
                         (510, 512, 39))
        self.assertEqual(result['final_native_ring_origin'], 1760)
        self.assertEqual(len(result['initial_data']), 10)
        self.assertEqual(len(result['coefficients']), 11)
        self.assertFalse(result['full_engine_ready'])
        # The distortion is audible/numerical, not an unused inserted profile.
        clean, _ = filtered.render(128, 440)
        self.assertNotEqual(actual[:128], clean)

    def test_exact_resources_final_padding_seed_reuse_and_field_protection(self):
        fragments = filtered.programs(True)
        logical = b''.join(fragments)
        self.assertEqual([len(fragment) for fragment in fragments], [38, 82, 80, 126, 184])
        self.assertEqual(len(packets(logical)), 39)
        stored = filtered.storage_program(True)
        self.assertEqual(swap_words(stored), logical+b'\0\0')
        self.assertEqual(required_initial_data(fragments), required_initial_data(filtered.programs()))
        self.assertEqual(len(transfer_fields(fragments)), 70)
        self.assertEqual(len(verify_relocation(fragments, 0, 0, [0x2016, 0x2017], fragments)), 70)
        self.assertEqual(requirements(fragments)['data_extent'], 150)
        self.assertEqual(requirements(fragments)['coefficient_extent'], 11)
        spec = disassemble_fragment(fragments[-1]); spec['sources'][0] -= 1
        self.assertRaises(ValueError, verify_relocation, (*fragments[:-1], assemble_fragment(spec)),
                          0, 0, [0x2016, 0x2017], fragments)
        # Storage alignment must also fit; 510 logical bytes occupy 512 in the export.
        owner = dict(address=0, dsp=4, render=[dict(base=0x4020, capacity=512)],
                     memories={0: [dict(base=0x100, length=150)], 6: [dict(base=0x190, length=11)]})
        self.assertTrue(fit(owner, fragments)['body_capacity_fits'])
        for resource in ('program', 'data', 'coefficients'):
            changed = copy.deepcopy(owner)
            if resource == 'program': changed['render'][0]['capacity'] = 510
            else: changed['memories'][0 if resource == 'data' else 6][0]['length'] -= 1
            self.assertFalse(fit(changed, fragments)['fits'][resource])

    def test_bounded_shape_inputs_silence_and_no_implicit_flag_conversion(self):
        self.assertTrue(all(value == 0 for row in filtered.render(128, 440, gain=0, waveshape=True)[0]
                            for value in row))
        for flag in (0, 1, None, 'yes'):
            self.assertRaises(ValueError, filtered.programs, flag)
            self.assertRaises(ValueError, filtered.initialize, 440, waveshape=flag)
        for amplitude in (.50001, 1, True, math.nan):
            self.assertRaises(ValueError, filtered.initialize, 440, amplitude, waveshape=True)
        filtered.initialize(440, .5, waveshape=True)
        filtered.initialize(440, 1, waveshape=False)

    def test_renderer_cli_has_no_vendor_dependency_and_preserves_existing_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'shaped.wav'
            command = [sys.executable, str(ROOT/'tools/bmc_filtered_voice.py'), str(output),
                       '--waveshape', '--frames', '128']
            run = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                 env=dict(os.environ, BMC_CORPUS_DIR=directory))
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['stored_bytes'], 512)
            before = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), before)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS and hasattr(math, 'fma'), 'Pinned Fantom corpus and Python 3.13+ required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.core = Core1(CORPUS/'b0c1a.bin')

    def test_five_relocations_seed_canaries_and_explicit_hardware_gates(self):
        for owner in OWNERS:
            fragments, result = render_check(self.core, owner, cutoff=1000, waveshape=True)
            self.assertEqual(result['fragment_sizes'], [38, 82, 80, 126, 184])
            self.assertEqual((result['body_bytes'], result['stored_bytes']), (510, 512))
            self.assertEqual(len(result['address_changes']), 70)
            self.assertEqual(len(result['initial_data']), 10)
            self.assertEqual(result['reference_check']['identical_output_values'], 4112)
            self.assertEqual(result['reference_check']['final_origin'], 8)
            self.assertTrue(result['reference_check']['nonseed_background_canaries'])
            for key in ('load_address', 'entry_address', 'return_address'):
                self.assertIsNone(result[key])
            for key in ('execution_ready', 'wrapper_included', 'output_io_writes_included',
                        'runtime_ownership_verified', 'hardware_execution_verified'):
                self.assertFalse(result[key])
        self.assertRaises(ValueError, build_plan, self.core, OWNERS[0], waveshape=True)
        self.assertRaises(ValueError, build_plan, self.core, OWNERS[0], cutoff=1000, waveshape=1)

    def test_nonword_aligned_export_and_tampered_size_never_create_output(self):
        fragments, result = build_plan(self.core, OWNERS[0], cutoff=1000, waveshape=True)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'plan'
            altered = dict(result, stored_bytes=510)
            self.assertRaises(ValueError, write_plan, output, fragments, altered)
            self.assertFalse(output.exists())
            write_plan(output, fragments, result)
            logical = (output/'body-logical.bin').read_bytes()
            self.assertEqual(len(logical), 510)
            self.assertEqual(swap_words((output/'body-stored.bin').read_bytes()), logical+b'\0\0')
            self.assertEqual(json.loads((output/'manifest.json').read_text())['stored_bytes'], 512)


if __name__ == '__main__':
    unittest.main()
