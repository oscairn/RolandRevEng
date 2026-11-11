import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64'
                     and hasattr(math, 'fma') and importlib.util.find_spec('capstone')
                     and all((CORPUS/name).exists() for name in ('zen_arm64', 'exports_dem.txt', 'pairs.json')),
                     'macOS ARM64, Python 3.13+ and the pinned native corpus required')
class NativeFetdriveTests(unittest.TestCase):
    def run_cli(self, directory, name, frames):
        output = Path(directory)/name
        run = subprocess.run(
            [sys.executable, str(ROOT/'tools/native_fetdrive_reference.py'),
             str(output), '--frames', str(frames)],
            capture_output=True, text=True, timeout=120)
        return output, run

    def test_isolated_callback_matches_reference_through_ring_wrap(self):
        with tempfile.TemporaryDirectory() as directory:
            output, run = self.run_cli(directory, 'native-fetdrive.wav', 2056)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertTrue(report['native_callback_executed'])
            self.assertFalse(report['bmc_instructions_executed'])
            self.assertTrue(report['cold_zero_ring'])
            self.assertTrue(report['constructor_filters_uncalibrated'])
            self.assertEqual(report['software_sample_rate'], 48000)
            self.assertEqual(report['wrapper_base'], 0)
            self.assertEqual(report['final_origin'], 8)
            self.assertEqual(report['first_store_max_abs_error'], 0.0)
            self.assertEqual(report['coefficients']['drive_scale'], 0.0015476426307448495)
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getframerate()), (2056, 2, 48000))
                samples = struct.unpack('<4112h', wav.readframes(2056))
                self.assertNotEqual(samples[::2], samples[1::2])

    def test_fresh_renders_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            reports = []
            for name in ('first.wav', 'second.wav'):
                output, run = self.run_cli(directory, name, 2056)
                self.assertEqual(run.returncode, 0, run.stderr)
                reports.append(json.loads(run.stdout))
            self.assertEqual(reports[0], reports[1])
            self.assertEqual((Path(directory)/'first.wav').read_bytes(),
                             (Path(directory)/'second.wav').read_bytes())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'native-fetdrive.wav'
            output.write_bytes(b'existing')
            _, run = self.run_cli(directory, output.name, 2056)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_bytes(), b'existing')


if __name__ == '__main__':
    unittest.main()
