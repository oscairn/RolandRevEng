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
from render_transient_reference import render_reference


class InputTests(unittest.TestCase):
    def test_invalid_frames_are_rejected_before_corpus_access(self):
        for frames in (True, None, 127, 1000001, 128.0):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                render_reference(frames)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_CORPUS and hasattr(math, 'fma'), 'Python 3.13+ and pinned corpus required')
class CorpusTests(unittest.TestCase):
    def test_history_pairs_defaults_and_distinct_log_limit(self):
        from transient_state_study import report
        checked = report()
        self.assertEqual(len(checked['history']), 10)
        for pair in checked['history']:
            self.assertEqual(pair['previous']['address'], pair['store']['address']+1)
        self.assertEqual(math.nextafter(checked['log_limit'], -math.inf), checked['defaults'][8])
        self.assertFalse(checked['bmc_instruction_admission'])

    def test_independent_cli_wrap_and_existing_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'reference.wav'
            command = [sys.executable, str(ROOT/'tools/render_transient_reference.py'),
                       str(output), '--frames', '2056']
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertFalse(result['native_callback_executed'])
            self.assertFalse(result['bmc_instructions_executed'])
            self.assertFalse(result['upstream_arguments_from_native'])
            self.assertEqual(result['final_origin'], 8)
            before = output.read_bytes()
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
