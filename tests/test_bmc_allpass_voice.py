import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import bmc_allpass_oscillator as oscillator
import bmc_allpass_voice as voice
from bmc_dsp import packets, swap_words
from bmc_subset import disassemble_fragment
from line_shaping_study import _float32


class Programs(unittest.TestCase):
    def test_static_composition_and_whole_storage_conversion(self):
        fragments = voice.programs()
        self.assertEqual([len(program) for program in fragments], [38, 82, 80])
        self.assertEqual([disassemble_fragment(program)['kind'] for program in fragments],
                         ['coefficient_shift4', 'allpass4', 'dry_wet_tail_with_scratch'])
        logical = b''.join(fragments)
        self.assertEqual(len(logical), 200)
        self.assertEqual(len(packets(logical)), 18)
        self.assertEqual([offset for offset, _ in packets(logical)][3:4], [38])
        self.assertEqual(swap_words(voice.storage_program()), logical)


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class Render(unittest.TestCase):
    def test_output_gain_after_shared_ring_feedback_and_wrap(self):
        for frequency, gain in ((440, 1/3), (9600, 0.75)):
            with self.subTest(frequency=frequency):
                mono, original = oscillator.render(2056, frequency)
                rows, result = voice.render(2056, frequency, gain=gain)
                expected = [value*_float32(gain) for value in mono]
                self.assertEqual([left for left, _ in rows], expected)
                self.assertTrue(all(left == right for left, right in rows))
                self.assertEqual(result['final_native_ring_origin'], 8)
                self.assertEqual(result['initial_data'], original['initial_data'])
                self.assertEqual(result['source_gain'], _float32(gain))
                self.assertEqual(result['program_sha256'], hashlib.sha256(b''.join(voice.programs())).hexdigest())
                self.assertEqual(len(result['coefficients']), 6)
                self.assertEqual(result['scratch_addresses'], [0x90, 0x91])
                self.assertFalse(result['hardware_execution_verified'])
                self.assertFalse(result['full_engine_ready'])

    def test_zero_unity_gain_and_external_input_independence(self):
        quiet, _ = voice.render(128, 440, gain=0)
        self.assertEqual(set(quiet), {(0.0, 0.0)})
        mono, _ = oscillator.render(128, 440)
        rows, _ = voice.render(128, 440, gain=1)
        self.assertEqual([left for left, _ in rows], mono)
        with patch.dict(oscillator.IO_ADDRESSES, {0x2016: 0.4, 0x2017: -0.3}):
            external, _ = voice.render(128, 440, gain=1)
        self.assertEqual(external, rows)

    def test_initialization_is_the_only_sine_source(self):
        sine = math.sin
        with patch('math.sin', side_effect=sine) as counted:
            rows, _ = voice.render(2056, 440)
        self.assertEqual(counted.call_count, 5)
        self.assertEqual(len(rows), 2056)

    def test_invalid_parameters_and_initializer_validation(self):
        for args in ((True, 440), (127, 440), (1000001, 440), (128.0, 440),
                     (128, 0), (128, 24000), (128, 440, -1), (128, 440, True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                voice.render(*args)
        for gain in (True, None, math.nan, math.inf, -0.1, 1.1):
            with self.subTest(gain=gain), self.assertRaises(ValueError):
                voice.render(128, 440, gain=gain)
        for amplitude in (True, None, math.nan, -0.1, 1.1):
            with self.assertRaises(ValueError):
                oscillator.initialize(440, amplitude)

    def test_corpus_free_cli_and_existing_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'voice.wav'
            command = [sys.executable, str(ROOT/'tools/bmc_allpass_voice.py'), str(output),
                       '--frames', '2056', '--gain', '0.25']
            env = dict(os.environ, BMC_CORPUS_DIR=str(Path(directory)/'absent'))
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['program_bytes'], 200)
            self.assertEqual(result['total_packet_count'], 18)
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnchannels(), wav.getnframes(), wav.getframerate()), (2, 2056, 48000))
            before = output.read_bytes()
            again = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
