import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from memory_domain_study import report, unsigned_ldr_offsets


class CandidateTests(unittest.TestCase):
    def test_pc_literals_do_not_become_virtual_call_candidates(self):
        # LDR ip,[r1,#108]; LDR ip,[pc,#108]; truncated first halfword.
        data = bytes.fromhex('d1f808c1dff808c1d1f8')
        self.assertEqual(unsigned_ldr_offsets(data, 0x108), [0])
        with self.assertRaises(ValueError):
            unsigned_ldr_offsets(data, 0x1000)

    def test_unknown_build_fails_before_reading_addresses(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported CORE1'):
            report(SimpleNamespace(data=b'unknown'), b'')


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/p).exists() for p in ('b0c1a.bin', 'zen_arm64')),
                     'Capstone and local Fantom/native artifacts required')
class CorpusTests(unittest.TestCase):
    def test_monitor_names_and_control_discrepancy_are_both_preserved(self):
        from core1 import Core1
        result = report(Core1(CORPUS/'b0c1a.bin'), (CORPUS/'zen_arm64').read_bytes())
        rows = result['diagnostic_labels']
        self.assertEqual([r['register'] for r in rows],
                         [0x41100054, 0x41100058, 0x41100054, 0x41100048])
        self.assertEqual(result['bool_domain_diagnostic_names'], {'0': 'IDM', '1': 'EDM'})
        self.assertEqual(result['ldr_unsigned_candidates']['0xec'], [0x6102a3be])
        self.assertEqual(result['ldr_unsigned_candidates']['0x108'], [])
        self.assertFalse(result['bulk_clear_count_unit_proven'])
        self.assertFalse(result['physical_domain_name_validated'])


if __name__ == '__main__':
    unittest.main()
