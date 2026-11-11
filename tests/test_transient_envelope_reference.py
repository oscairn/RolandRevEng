import math
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_shaping_study import EPSILON
from transient_envelope_reference import envelope_step, tail_reference


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class EnvelopeTests(unittest.TestCase):
    def test_exponential_delta_and_strict_negative_epsilon_threshold(self):
        self.assertEqual(envelope_step(0, 0, above=0.25, below=0.75), 0.25)
        self.assertEqual(envelope_step(0, 2, above=0.25, below=0.75), 1.25)
        at = 1+EPSILON
        within = math.nextafter(at, 1)
        self.assertEqual(envelope_step(0, at, above=0, below=1), 1)
        self.assertEqual(envelope_step(0, within, above=0, below=1), within)

    def test_tail_gain_branches_and_binary32_coefficients(self):
        result = tail_reference(0.25, -0.5, 0.5, 0.25, [2, 0.5, 0.25, 0.125])
        self.assertEqual(result, dict(gain=1.328125, output=(0.6640625, -1.328125)))
        rounded, = struct.unpack('<f', struct.pack('<f', 1/3))
        self.assertEqual(tail_reference(1, 0, 1, 1, [1/3, 0, 0, 0])['output'], (rounded, 0))

    def test_invalid_inputs_and_nonfinite_exponential_are_rejected(self):
        for invalid in (True, None, math.nan, math.inf, 1e308):
            with self.subTest(invalid=type(invalid)), self.assertRaises(ValueError):
                envelope_step(invalid, 0, above=0.5, below=0.25)
        for coefficients in ([1, 0], [1, 0, 0, math.nan], [True, 0, 0, 0]):
            with self.assertRaises(ValueError):
                tail_reference(1, 0, 1, 1, coefficients)
