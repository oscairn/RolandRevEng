import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from dramio_owner_study import fantom_controls, jupiter_owners, selected_segment


class SelectionTests(unittest.TestCase):
    def test_descriptor_first_index_selects_source_not_instance_ordinal(self):
        segments = [dict(base=0, capacity=0x100, length=8, source=0x61000100),
                    dict(base=0x100, capacity=0x100, length=16, source=0x61000200)]
        reservation = dict(base=0x100, capacity=0x100)
        self.assertIs(selected_segment(segments, 1, 1, reservation), segments[1])
        for first, count in ((0, 1), (-1, 1), (2, 1), (1, 2)):
            with self.assertRaises(ValueError):
                selected_segment(segments, first, count, reservation)
        segments[1]['length'] = 0x104
        with self.assertRaises(ValueError):
            selected_segment(segments, 1, 1, reservation)

    def test_unknown_artifacts_rejected_before_address_access(self):
        for reader in (fantom_controls, jupiter_owners):
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                reader(SimpleNamespace(data=b'not an admitted artifact'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/p).exists() for p in ('b0c1a.bin', 'zen_arm64',
                        'crossmodel/jupiter-x/MI077_C1A_up.bin')),
                     'Capstone and local Fantom/JUPITER-X/native artifacts required')
class CorpusTests(unittest.TestCase):
    def test_constructor_ownership_permutation_and_distinct_global_counts(self):
        from dramio_owner_study import study
        result = study()
        rows = result['jupiter_owners']
        self.assertEqual([r['list_index'] for r in rows], [0, 2, 3, 4, 5, 1, 6, 7, 8, 9, 10])
        self.assertEqual([r['dsp'] for r in rows], [4]*9+[5]*2)
        self.assertEqual([r['manager_storage'] for r in rows[:9]], [0x200a1890+i*0x14 for i in range(9)])
        self.assertEqual([(r['address_stride'], r['enum11']['length']) for r in rows],
                         [(0x1900, 0x23000)]*9+[(0x2100, 0x2d000)]*2)
        self.assertEqual([r['enum2']['base'] for r in rows],
                         [0, 0x134, 0x157, 0x17a, 0x19d, 0x9a, 0x1c0, 0x1e3, 0x206, 0, 0x3c])
        self.assertEqual(result['fantom']['counter_width'], 20)
        self.assertEqual(result['fantom']['setter_record_alignment'], 16)
        self.assertEqual(result['fantom']['getter_record_alignment'], 8)
        self.assertEqual(result['jupiter_global_caller']['count'], 1<<22)
        self.assertEqual(result['fantom']['observed_global_caller']['count'], 1<<23)
        self.assertFalse(result['fantom']['hardware_domain_name_proven'])
        self.assertFalse(result['execution_ready'])


if __name__ == '__main__':
    unittest.main()
