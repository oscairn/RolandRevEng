import importlib.util
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from core1_xrefs import branch_candidates, references, veneer_candidates


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
class XrefTests(unittest.TestCase):
    def test_original_immediate_branch_fixtures(self):
        # b 0x1008; nop; bl 0x1008; b.w 0x100c (original synthetic Thumb code).
        data = bytes.fromhex('02e000bf00f000f800f000b8')
        self.assertEqual(branch_candidates(data, 0x1000, 0x1009), [
            dict(address=0x1000, instruction='b'), dict(address=0x1004, instruction='bl')])
        self.assertEqual(branch_candidates(data, 0x1000, 0x100c), [
            dict(address=0x1008, instruction='b.w')])
        self.assertEqual(branch_candidates(data, 0x1000, 0x100e), [])

    def test_only_exact_same_register_veneer(self):
        # movw r4,#0x1235; movt r4,#0x6100; bx r4.
        data = bytes.fromhex('41f23524c6f200142047')
        self.assertEqual(veneer_candidates(data, 0x2000, 0x61001234), [
            dict(address=0x2000, thumb_pointer=0x61001235)])
        for bad in (data[:-1], data[:-2] + bytes.fromhex('2847'),
                    data[:6] + bytes.fromhex('0015') + data[8:],
                    bytes.fromhex('41f23424') + data[4:]):
            self.assertEqual(veneer_candidates(bad, 0x2000, 0x61001234), [])

    def test_regions_are_not_joined_into_instructions(self):
        data = bytearray(24)
        data[:4] = bytes.fromhex('00f000f8')
        struct.pack_into('<I', data, 4, 0x01100005)
        data[12:14] = bytes.fromhex('00f0')
        data[14:16] = bytes.fromhex('00f8')
        core = SimpleNamespace(data=bytes(data), eram_offset=14,
                               address=lambda off: 0x01100000 + off if off < 14
                               else 0x61000000 + off - 14)
        result = references(core, 0x01100004)
        self.assertEqual(result['aligned_thumb_pointer_candidates'], [0x01100004])
        self.assertEqual(result['direct_branch_candidates'], [
            dict(address=0x01100000, instruction='bl')])
        for target in (-1, 1 << 32):
            with self.assertRaises(ValueError):
                references(core, target)


if __name__ == '__main__':
    unittest.main()
