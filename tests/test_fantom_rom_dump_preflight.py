import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from fantom_rom_dump_preflight import zero_candidate, report


class BoundsTests(unittest.TestCase):
    def test_zero_initializer_is_not_free_padding(self):
        result = zero_candidate(b'code' + bytes(28), 32, 16)
        self.assertEqual(result['raw_zero_start'], 4)
        self.assertEqual(result['candidate_start'], 16)
        self.assertEqual(result['bytes'], 16)
        self.assertFalse(result['runtime_ownership_proven'])

    def test_alignment_no_space_and_invalid_bounds(self):
        self.assertEqual(zero_candidate(b'x' + bytes(15), 16, 5)['candidate_start'], 8)
        self.assertEqual(zero_candidate(b'code', 4, 0)['bytes'], 0)
        for end, protected in ((5, 0), (4, 5), (-1, 0), (4, -1)):
            with self.assertRaises(ValueError):
                zero_candidate(b'code', end, protected)


@unittest.skipUnless((ROOT / 'local/b0c1a.bin').exists(), 'Pinned local corpus required')
class CorpusTests(unittest.TestCase):
    def test_pinned_anchors_without_modifying_input(self):
        from core1 import Core1
        core = Core1(ROOT / 'local/b0c1a.bin')
        before = hashlib.sha256(core.path.read_bytes()).digest()
        result = report(core)
        self.assertEqual(result['candidate_address'], 0x0113cf40)
        self.assertEqual(result['itcm_candidate']['bytes'], 0x30a0)
        self.assertEqual(result['raw_pointer_collision']['value'], 0x0113f3c1)
        self.assertFalse(result['flash_ready'])
        self.assertFalse(result['key_recovered'])
        self.assertEqual(before, hashlib.sha256(core.path.read_bytes()).digest())
        core.data = core.data[:-1]
        with self.assertRaises(ValueError):
            report(core)


if __name__ == '__main__':
    unittest.main()
