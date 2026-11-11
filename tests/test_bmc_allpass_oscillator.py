import math
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))

import bmc_allpass_oscillator as osc
from bmc_subset import disassemble_fragment
from bmc_dsp import packets, swap_words

TOL = 1e-8


class Programs(unittest.TestCase):
    def test_fragments_and_decoders(self):
        prefix, allpass = osc.programs()
        self.assertEqual((len(prefix), len(allpass)), (38, 82))
        self.assertEqual(disassemble_fragment(prefix)['kind'], 'coefficient_shift4')
        self.assertEqual(disassemble_fragment(allpass)['kind'], 'allpass4')
        self.assertEqual(len(prefix + allpass), 120)
        self.assertEqual(len(packets(prefix+allpass)), 10)
        self.assertEqual(packets(prefix+allpass)[3][0], 38)
        self.assertEqual(swap_words(swap_words(prefix+allpass)), prefix+allpass)
        self.assertEqual(osc.programs(), (prefix, allpass))


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class Render(unittest.TestCase):
    def compare(self, frequency, amplitude=0.25, frames=4096):
        _, quantized = osc.factor_for(frequency)
        omega = osc.actual_omega(quantized)
        samples, meta = osc.render(frames, frequency, amplitude)
        self.assertEqual(len(samples), frames)
        self.assertEqual(len(meta['initial_data']), 6)
        self.assertEqual(meta['coefficients'][0], 0)
        self.assertTrue(all(math.isfinite(s) for s in samples))
        self.assertAlmostEqual(meta['actual_frequency'], omega * 48000 / (2 * math.pi))
        worst = max(abs(s - amplitude * math.sin(omega * n)) for n, s in enumerate(samples))
        self.assertLess(worst, TOL)
        return omega, meta

    def test_origin_crosses_ring_wrap_twice(self):
        _, meta = self.compare(9600.0, 0.5, frames=4096)
        self.assertEqual(meta['origin_wraps'], 2)
        self.assertEqual(meta['final_native_ring_origin'], 0)
        self.assertFalse(meta['hardware_execution_verified'])
        self.assertFalse(meta['full_engine_ready'])

    def test_440_origin_wraps_twice(self):
        _, meta = self.compare(440.0)
        self.assertLess(abs(meta['actual_frequency']-440), 0.001)
        self.assertEqual(meta['origin_wraps'], 2)
        self.assertEqual(meta['final_native_ring_origin'], 0)

    def test_9600_quantized_zero_factor(self):
        _, quantized = osc.factor_for(9600.0)
        self.assertEqual(quantized, 0.0)
        omega, _ = self.compare(9600.0, 0.5)
        self.assertAlmostEqual(omega, 2 * math.pi * 9600 / 48000, places=12)

    def test_deterministic_and_silent(self):
        a, ma = osc.render(512, 440.0)
        b, mb = osc.render(512, 440.0)
        self.assertEqual(a, b)
        self.assertEqual(ma['program_sha256'], mb['program_sha256'])
        with patch.dict(osc.IO_ADDRESSES, {0x2016: 0.4, 0x2017: -0.3}):
            independent, _ = osc.render(512, 440.0)
        self.assertEqual(a, independent)
        silence, _ = osc.render(128, 440.0, 0.0)
        self.assertEqual(set(silence), {0.0})

    def test_malformed(self):
        for args in ((4096, 0.0), (4096, 24000.0), (4096, 440.0, 1.5),
                     (4096, 440.0, -0.1), (127, 440.0), (1_000_001, 440.0),
                     (4096.0, 440.0), (True, 440.0), (4096, True), (4096, float('nan')),
                     (4096, math.ulp(0.0)), (4096, 1e-300), (4096, math.nextafter(24000.0, 0))):
            with self.assertRaises(ValueError):
                osc.render(*args)


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class NoPerSampleSine(unittest.TestCase):
    def test_seed_only_sine(self):
        calls = 0
        real = math.sin

        def counting(value):
            nonlocal calls
            calls += 1
            if calls > 6:
                raise AssertionError('analytic sin fallback during render')
            return real(value)

        original = osc.math.sin
        osc.math.sin = counting
        try:
            samples, _ = osc.render(4096, 440.0)
        finally:
            osc.math.sin = original
        self.assertEqual(calls, 5)
        self.assertEqual(len(samples), 4096)


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class CliTests(unittest.TestCase):
    def test_corpus_free_render_and_existing_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'oscillator.wav'
            command = [sys.executable, str(ROOT/'tools/bmc_allpass_oscillator.py'),
                       str(output), '--frequency', '440', '--frames', '2056']
            env = dict(os.environ, BMC_CORPUS_DIR=str(Path(directory)/'absent-corpus'))
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report['program_bytes'], 120)
            self.assertEqual(report['sine_evaluations_for_initialization'], 5)
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getframerate()), (2056, 1, 48000))
            before = output.read_bytes()
            again = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
