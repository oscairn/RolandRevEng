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
from render_fetdrive_reference import render_reference


class InputTests(unittest.TestCase):
    def test_invalid_frame_counts_are_rejected_before_corpus_access(self):
        for invalid in (None, True, 127, 1000001, 128.0):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                render_reference(invalid)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE and hasattr(math, 'fma'), 'Pinned corpus and Python 3.13+ required')
class ReferenceTests(unittest.TestCase):
    def test_portable_python_reference_renders_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'fet-reference.wav'
            command = [sys.executable, str(ROOT/'tools/render_fetdrive_reference.py'),
                       str(output), '--frames', '2056']
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertFalse(report['native_callback_executed'])
            self.assertFalse(report['bmc_instructions_executed'])
            self.assertEqual(report['final_origin'], 8)
            self.assertEqual(len(report['history']), 8)
            before = output.read_bytes()
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)
