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
            self.assertFalse(report['upstream_arguments_from_native'])
            self.assertEqual(report['detector_identical_values'], 30840)
            self.assertEqual(report['independent_output_identical_values'], 4112)
            self.assertEqual(report['zero_log_floor'], math.log(2**-32))
            self.assertTrue(report['full_output_reference_verified'])
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

    def test_silence_release_steps_signed_zero_and_negative_live_modes(self):
        code = '''
import json, struct, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from native_transient_reference import render_native
from native_callback_fixture import RingFixture
cases = [('silence',17000,lambda _:0.0), ('signed_zero',128,lambda _:-0.0),
         ('steps',2056,lambda phase:32 if int(phase/10)%3==1 else 0)]
reports=[]
for label,frames,source in cases:
    with patch('math.sin',side_effect=source):
        samples,report=render_native(frames)
    reports.append(dict(case=label, decisions=report['detector_decisions'],
                        full=report['full_output_reference_verified']))
with patch('native_transient_reference.COEFFICIENTS',(1/3,-.5,.25,-.125)):
    samples,report=render_native(2056)
reports.append(dict(case='negative_modes',full=report['full_output_reference_verified']))
for cursor in (1,2):
    class RotatedFixture(RingFixture):
        def __init__(self,context):
            super().__init__(context)
            for offset in (0xb8,0x118):
                struct.pack_into('<I',self.owner,offset,cursor)
    with patch('native_transient_reference.RingFixture',RotatedFixture):
        samples,report=render_native(128)
    assert report['final_cache_cursors']==[cursor,cursor]
    reports.append(dict(case='rotated_cache',full=report['full_output_reference_verified']))
print(json.dumps(reports))
'''
        run = subprocess.run([sys.executable, '-c', code, str(ROOT/'tools')],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        results = json.loads(run.stdout)
        self.assertTrue(all(row['full'] for row in results))
        self.assertGreater(results[0]['decisions']['faster_release'], 0)
        self.assertGreater(results[0]['decisions']['history_rolls'], 0)
        self.assertGreater(results[2]['decisions']['phase_resets'], 0)
