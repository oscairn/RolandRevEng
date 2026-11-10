import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from core0_provider_refs import category, regions, scan_region


class ProviderTests(unittest.TestCase):
    def test_range_boundaries_and_unknown_digest(self):
        self.assertIsNotNone(category(0x01200000))
        self.assertIsNone(category(0x01210000))
        self.assertIsNotNone(category(0x40020424))
        self.assertIsNone(category(0x40020428))
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'unknown'
            file.write_bytes(b'not a firmware image')
            with self.assertRaisesRegex(ValueError, 'digest'):
                regions(file)

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_original_literal_and_mov_pair_candidates(self):
        # ldr r0,[pc,#0]; nop; original address literal; movw/movt r4; bx lr.
        data = bytes.fromhex('004800bf') + struct.pack('<I', 0x012023b0)
        data += bytes.fromhex('42f2b034c0f220147047')
        result = scan_region(data, 0x1000)
        self.assertEqual(result['exact_provider_words'], [dict(address=0x1004, value=0x012023b0)])
        self.assertEqual([(r['address'], r['mnemonic'], r['value'])
                          for r in result['instruction_candidates']],
                         [(0x1000, 'ldr', 0x012023b0), (0x1008, 'movw', 0x012023b0)])

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_region_boundary_and_mismatched_pair_are_not_followed(self):
        self.assertEqual(scan_region(bytes.fromhex('004800bf'), 0x1000)['instruction_candidates'], [])
        # MOVT writes r5, so it cannot complete the preceding MOVW r4.
        result = scan_region(bytes.fromhex('42f2b034c0f220157047'), 0x1000)
        self.assertEqual(result['instruction_candidates'], [])
        branch = scan_region(bytes.fromhex('02e000bf00bf00bf'), 0x01200000)
        self.assertEqual(branch['instruction_candidates'][0]['value'], 0x01200008)


if __name__ == '__main__':
    unittest.main()
