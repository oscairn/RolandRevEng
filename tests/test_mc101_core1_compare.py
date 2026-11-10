import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
sys.path.insert(0, str(ROOT / 'tools'))
from mc101_core1_compare import MC101Core1, report


class ComparisonTests(unittest.TestCase):
    def test_reads_cannot_cross_region_or_alias_unmapped_gap(self):
        image = object.__new__(MC101Core1)
        image.regions = [(0x1000, b'ABCD'), (0x2000, b'EFGH')]
        self.assertEqual(image.read(0x1001, 3), b'BCD')
        self.assertEqual(image.read(0x2000, 4), b'EFGH')
        for address, size in ((0x1003, 2), (0x1004, 0), (0x1800, 1), (0x2000, -1)):
            with self.assertRaises(ValueError):
                image.read(address, size)

    def test_unknown_builds_rejected_before_address_interpretation(self):
        with self.assertRaisesRegex(ValueError, 'MC-101'):
            MC101Core1(b'unrecognized', None)
        with self.assertRaisesRegex(ValueError, 'Fantom'):
            report(b'', SimpleNamespace(data=b'unrecognized'))

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_optional_official_corpus_comparison(self):
        from core1 import Core1
        mc_path = CORPUS / 'crossmodel/mc101/RPG69_C1A_up.bin'
        fantom_path = CORPUS / 'b0c1a.bin'
        if not mc_path.exists() or not fantom_path.exists():
            self.skipTest('Official MC-101 and Fantom corpus files are absent')
        result = report(mc_path.read_bytes(), Core1(fantom_path))
        self.assertEqual(result['mmio']['identical_prefix_bytes'], 324)
        self.assertEqual(result['mmio']['prefix_sha256'],
                         '454f8fe6b80521c5738b5649133668dbdf4ccda7f08ca2dcec076cc411855246')
        self.assertEqual(result['mmio']['mc101_send'], 0x6107df12)
        self.assertEqual(result['wait']['body_bytes'], 98)
        self.assertEqual(result['wait']['mc101_scaled_multiplier'], 44100)
        self.assertEqual([row['base'] for row in result['mapping']], [0x01100000, 0x61000000])


if __name__ == '__main__':
    unittest.main()
