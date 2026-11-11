import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_transient_reference import render_native


class InputTests(unittest.TestCase):
    def test_invalid_frame_counts_are_rejected_before_native_execution(self):
        for value in (True, None, 127, 1000001, 128.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_native(value)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE and hasattr(math, 'fma') and platform.system() == 'Darwin'
                     and platform.machine() == 'arm64', 'macOS ARM64, Python 3.13+ and pinned corpus required')
class ExecutionTests(unittest.TestCase):
    def test_native_peak_log_and_caches_through_wrap_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'transient.wav'
            command = [sys.executable, str(ROOT/'tools/native_transient_reference.py'),
                       str(output), '--frames', '2056']
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertTrue(report['native_callback_executed'])
            self.assertFalse(report['bmc_instructions_executed'])
            self.assertEqual(report['math_bridge']['trampolines'], 2)
            self.assertEqual([row['symbol'] for row in report['math_bridge']['calls']], ['log', 'exp', 'exp'])
            self.assertEqual(report['final_origin'], 8)
            self.assertEqual(report['owner_bytes'], 0x120)
            self.assertEqual(report['final_cache_cursors'], [0, 0])
            self.assertEqual(report['peak_log_identical_values'], 4112)
            self.assertEqual(report['envelope_tail_identical_values'], 10280)
            self.assertTrue(report['conditional_output_reference_verified'])
            self.assertTrue(report['upstream_arguments_from_native'])
            self.assertEqual(report['zero_log_floor'], math.log(2**-32))
            self.assertFalse(report['full_output_reference_verified'])
            before = output.read_bytes()
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getframerate()), (2056, 2, 48000))
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)

    def test_fresh_native_renders_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            results = []
            for name in ('a.wav', 'b.wav'):
                output = Path(directory)/name
                run = subprocess.run([sys.executable, str(ROOT/'tools/native_transient_reference.py'),
                                      str(output), '--frames', '2056'],
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stderr)
                results.append((output.read_bytes(), json.loads(run.stdout)))
            self.assertEqual(results[0], results[1])
