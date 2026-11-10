from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_one_pole import filter_frames, programs
from bmc_subset import disassemble_fragment


class OnePoleTests(unittest.TestCase):
    def test_original_byte_profiles_carry_each_channels_state(self):
        frames = [(1, -0.5), (0, 0), (-0.5, 1), (0, 0), (0, 0)]
        self.assertEqual(filter_frames(frames, 0.5),
                         [(0.5, -0.25), (0.25, -0.125), (-0.125, 0.4375),
                          (-0.0625, 0.21875), (-0.03125, 0.109375)])
        self.assertEqual(filter_frames(frames, 0), frames)
        first, second = map(disassemble_fragment, programs())
        self.assertEqual(first['scratch_addresses'], second['wet_addresses'])
        self.assertEqual(second['scratch_addresses'], first['wet_addresses'])
        for feedback in (True, -1, 1, float('nan')):
            with self.subTest(feedback=feedback), self.assertRaises(ValueError):
                filter_frames(frames, feedback)


if __name__ == '__main__':
    unittest.main()
