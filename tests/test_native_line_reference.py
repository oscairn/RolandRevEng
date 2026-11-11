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
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64'
                     and hasattr(math, 'fma') and importlib.util.find_spec('capstone')
                     and all((CORPUS/name).exists() for name in ('zen_arm64', 'exports_dem.txt', 'pairs.json')),
                     'macOS ARM64, Python 3.13+ and the pinned native corpus required')
class NativeLineTests(unittest.TestCase):
    def test_isolated_callback_matches_reference_through_ring_wrap_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'native-line.wav'
            command = [sys.executable, str(ROOT/'tools/native_line_reference.py'), str(output), '--frames', '2056']
            run = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertTrue(report['native_callback_executed'])
            self.assertFalse(report['bmc_instructions_executed'])
            self.assertLessEqual(report['reference_max_abs_error'], 2e-16)
            self.assertEqual(report['final_origin'], 8)
            with wave.open(str(output)) as wav:
                self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getframerate()), (2056, 2, 48000))
            before = output.read_bytes()
            again = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)
