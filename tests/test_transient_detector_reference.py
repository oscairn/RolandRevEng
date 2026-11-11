import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_shaping_study import EPSILON
from transient_detector_reference import HISTORY, LOG_LIMIT, ZERO_LOG, detector_step


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.history = dict.fromkeys(HISTORY, 0.0)
        self.defaults = {8: -4.0, 0x18: 0.25, 0x28: 1.0, 0x78: -0.5,
                         0xc8: 0.25, 0xd8: -0.125, 0xe8: -0.25}

    def step(self, left=1, right=0):
        return detector_step(left, right, self.history, self.defaults)

    def test_zero_log_and_native_peak_signed_zero_tie(self):
        self.assertEqual(ZERO_LOG, math.log(2**-32))
        for right in (0.0, -0.0):
            result = self.step(-0.0, right)
            self.assertEqual(result['writes'][0].hex(), right.hex())
            self.assertEqual(result['writes'][1], ZERO_LOG)

    def test_peak_window_roll_and_copy_branches(self):
        self.defaults[0x18] = 0
        self.history.update({18: 5, 22: 2, 24: 3, 26: 9})
        rolled = self.step()
        self.assertTrue(rolled['history_roll'])
        self.assertEqual([rolled['writes'][a] for a in (17, 21, 23, 25, 27, 34, 36)],
                         [5, 2, 3, 9, 9, 2.25, -6.75])
        self.history[20] = 1
        copied = self.step()
        self.assertFalse(copied['history_roll'])
        self.assertEqual([copied['writes'][a] for a in (17, 21, 23, 25, 27, 34, 36)],
                         [0, 5, 2, 3, 5, 1.25, -3.75])

    def test_reset_includes_positive_epsilon_boundary(self):
        self.history[18] = -EPSILON
        at = self.step()
        self.assertTrue(at['phase_reset'])
        self.assertEqual((at['writes'][19], at['retained_phase_guard']), (-1, -2))
        self.history[18] = math.nextafter(-EPSILON, 0)
        self.assertFalse(self.step()['phase_reset'])

    def test_phase_guard_keeps_unwrapped_sum_and_negative_epsilon_boundary(self):
        self.defaults[0x18] = 0
        self.history[20] = 1-EPSILON
        at = self.step()
        self.assertEqual(at['retained_phase_guard'], -EPSILON)
        self.assertTrue(at['history_roll'])
        self.history[20] = math.nextafter(1-EPSILON, 1)
        self.assertFalse(self.step()['history_roll'])
        self.history[20] = 1
        wrapped = self.step()
        self.assertEqual(wrapped['writes'][19], -1)
        self.assertEqual(wrapped['retained_phase_guard'], 0)
        self.assertFalse(wrapped['history_roll'])

    def test_release_rate_threshold_and_distinct_native_log_floor(self):
        self.defaults[0x78] = 0
        self.history[30] = LOG_LIMIT+EPSILON
        self.assertEqual(self.step(0, 0)['release_rate_field'], 0xd8)
        self.history[30] = math.nextafter(LOG_LIMIT+EPSILON, LOG_LIMIT)
        self.assertEqual(self.step(0, 0)['release_rate_field'], 0xe8)
        self.assertEqual(math.nextafter(LOG_LIMIT, -math.inf),
                         float.fromhex('-0x1.ba18a998fffa1p+2'))

    def test_invalid_values_missing_state_and_conversion_overflow(self):
        for invalid in (True, None, math.nan, math.inf):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.step(invalid, 0)
        for history, defaults in (({}, self.defaults), ([], self.defaults),
                                  (self.history, {}), (self.history, None)):
            with self.assertRaises(ValueError):
                detector_step(0, 0, history, defaults)
        self.defaults[0x28] = -1
        with self.assertRaises(ValueError):
            self.step()
        self.defaults[0x28] = 1
        self.history[20] = 2**31
        with self.assertRaises(ValueError):
            self.step()


if __name__ == '__main__':
    unittest.main()
