import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from oscillator_phase_study import normalize_phase_sum
from oscillator_sine_study import EPSILON, sine_reference


def boundaries():
    return [-1, -0.5, math.nextafter(-0.5, -math.inf), math.nextafter(-0.5, 0),
            -0.5+EPSILON, math.nextafter(-0.5+EPSILON, -0.5), -0.0, 0.0,
            0.5-EPSILON, math.nextafter(0.5-EPSILON, 0.5), math.nextafter(0.5, 0), 0.5, 1]


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class SineTests(unittest.TestCase):
    def test_polarity_changes_before_positive_half_phase_wrap(self):
        below = sine_reference(0.5-EPSILON)
        within = sine_reference(math.nextafter(0.5-EPSILON, 0.5))
        wrapped = sine_reference(0.5)
        self.assertEqual((below['polarity'], within['polarity']), (1, -1))
        self.assertGreater(below['output'], 0.99)
        self.assertLess(within['output'], -0.99)
        self.assertGreater(wrapped['output'], 0.99)
        self.assertLess(sine_reference(math.nextafter(-0.5, -math.inf))['output'], -0.99)
        self.assertGreater(sine_reference(-0.5)['output'], 0.99)
        self.assertLess(sine_reference(-0.5+EPSILON)['output'], -0.99)

    def test_finite_input_domain_and_signed_zero_normalization(self):
        self.assertEqual(math.copysign(1, normalize_phase_sum(-0.0)), -1)
        for invalid in (True, None, math.nan, math.inf, 10**1000, 2**30, -(2**30)):
            with self.subTest(value=type(invalid)), self.assertRaises(ValueError):
                sine_reference(invalid)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_owned_polynomial_literals_and_three_stores(self):
        from limit_control_study import native_context
        from oscillator_sine_study import report, sine_context

        result = report()
        self.assertEqual([row['literal']['field'] for row in result['literal_bindings']],
                         [0x50, 0x5e, 0x5a, 0x8a, 0x76, 0x72, 0x68])
        self.assertEqual([row['native_store'] for row in result['stores']], [0x290f8, 0x291f8, 0x2920c])
        self.assertFalse(result['isolated_opcode_admission'])
        program, *_ = native_context('SIM_MFX_OSC')
        for offset in (0x46, 0x89):
            changed = bytearray(program)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                sine_context(changed)

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_fantom_sine_targets_relocate_across_four_placements(self):
        from core1 import Core1
        from oscillator_sine_study import fantom_report

        rows = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([row['output_target'] for row in rows], [0x100, 0x320, 0x3b6, 0x44c])
        self.assertTrue(all(row['polarity_target'] == row['output_target']+7 and
                            row['polynomial_target'] == row['output_target']+6 for row in rows))


@unittest.skipUnless(HAS_NATIVE and hasattr(math, 'fma') and platform.system() == 'Darwin'
                     and platform.machine() == 'arm64', 'macOS ARM64 and pinned native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_bit_exact_native_gate_polynomial_and_output_at_boundaries_and_random_phases(self):
        generator = random.Random(19)
        phases = boundaries() + [generator.uniform(-1, 1) for _ in range(512)]
        code = ('import json,sys; from oscillator_sine_study import native_probes; '
                'print(json.dumps(native_probes(iter(json.load(sys.stdin)))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', code], input=json.dumps(phases),
                             capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(json.loads(run.stdout)), len(phases))
