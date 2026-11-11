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
from oscillator_phase_study import advance_phase


class PhaseTests(unittest.TestCase):
    def test_negative_odd_boundary_and_increment_carry(self):
        for value, expected in ((-5, 1), (-3, 1), (-1, -1), (0, 0), (1, -1), (3, -1), (5, -1)):
            self.assertEqual(advance_phase(value, 0), expected)
        self.assertEqual(advance_phase(math.nextafter(1, 0), 0), math.nextafter(1, 0))
        self.assertEqual(advance_phase(math.nextafter(-1, -math.inf), 0),
                         math.nextafter(-1, -math.inf) + 2)
        self.assertAlmostEqual(advance_phase(0.99, 0.03), -0.98)
        self.assertAlmostEqual(advance_phase(-0.99, -0.03), 0.98)
        self.assertEqual(advance_phase(2**31-1, 0), 2**32-1)
        self.assertEqual(advance_phase(-(2**31-1), 0), -(2**32-1))

    def test_invalid_inputs_and_integer_domain_are_rejected(self):
        for value in (True, None, '1', math.nan, math.inf, 10**1000, 2**31, -2**31):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                advance_phase(value, 0)
        with self.assertRaises(ValueError):
            advance_phase(1e308, 1e308)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_phase_increment_and_history_have_owned_records(self):
        from oscillator_phase_study import report

        result = report()
        self.assertEqual((result['increment']['field'], result['increment']['width']), (0xa, 4))
        self.assertEqual((result['source']['address'], result['target']['address']), (5, 4))
        self.assertEqual(result['store'], 0x290bc)
        self.assertFalse(result['isolated_opcode_admission'])

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_fantom_relocated_phase_assignments(self):
        from core1 import Core1
        from oscillator_phase_study import fantom_report

        result = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([row['base'] for row in result], [0x4020, 0x8040, 0x9040, 0xa040])
        self.assertTrue(all(row['source_address'] == row['target_address']+1 for row in result))
        self.assertEqual({row['increment']['width'] for row in result}, {4})


@unittest.skipUnless(HAS_NATIVE and platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'macOS ARM64 and pinned native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_isolated_native_interval_agrees_at_boundaries_and_random_inputs(self):
        generator = random.Random(7)
        cases = [(value, 0) for value in (-5, -3, -1, 0, 1, 3, 5,
                                         math.nextafter(1, 0), math.nextafter(1, math.inf),
                                         math.nextafter(-1, -math.inf))]
        cases += [(0.99, 0.03), (-0.99, -0.03), (2**31-1, 0), (-(2**31-1), 0),
                  (math.nextafter(2**31, 0), 0), (-math.nextafter(2**31, 0), 0)]
        cases += [(generator.uniform(-100, 100), generator.uniform(-3, 3)) for _ in range(256)]
        code = ('import json,sys; from oscillator_phase_study import native_probes; '
                'print(json.dumps(native_probes(json.load(sys.stdin))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', code], env=env,
                             input=json.dumps(cases), capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        outputs = json.loads(run.stdout)
        self.assertEqual(len(outputs), len(cases))
        self.assertEqual([row['stored'] for row in outputs],
                         [advance_phase(*case) for case in cases])
