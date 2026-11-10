import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from line_state_study import HISTORY_PAIRS, advance_native_origin, native_ring_index


class RingAddressTests(unittest.TestCase):
    def test_unsigned_fields_mask_and_origin_wrap(self):
        self.assertEqual(native_ring_index(1, 0, 2), 0x7ff)
        self.assertEqual(native_ring_index(0xffffffff, 2, 0), 1)
        self.assertEqual(advance_native_origin(0x7ff), 0)
        self.assertEqual(advance_native_origin(0xffffffff), 0)
        for bad in (-1, 0x100000000, False, None, 1.5):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                advance_native_origin(bad)
            for field in range(3):
                args = [3, 0, 0]; args[field] = bad
                with self.subTest(value=bad, field=field), self.assertRaises(ValueError):
                    native_ring_index(*args)

    def test_nonzero_history_requires_fixed_base_and_one_forward_origin_step(self):
        for written, read in HISTORY_PAIRS:
            for base in (0, 0x7fd, 0xfffffff0):
                for origin in (0, 1, 0x7fe, 0x7ff):
                    with self.subTest(written=written, read=read, base=base, origin=origin):
                        ring = [0.0]*2048
                        ring[native_ring_index(written, base, origin)] = 3/8
                        advanced = advance_native_origin(origin)
                        self.assertEqual(ring[native_ring_index(read, base, advanced)], 3/8)
                        self.assertEqual(ring[native_ring_index(read, base, origin)], 0.0)
                        self.assertEqual(ring[native_ring_index(read, base, (origin-1)&0x7ff)], 0.0)
                        self.assertEqual(ring[native_ring_index(read, (base+1)&0xffffffff, advanced)], 0.0)
        # Explicit wrap counterexample: logical3 at O7ff and logical4 at O0 both map physical4.
        self.assertEqual(native_ring_index(3, 0, 0x7ff), 4)
        self.assertEqual(native_ring_index(4, 0, 0), 4)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt')),
                     'Capstone and pinned native/pairs/exports artifacts required')
class CorpusTests(unittest.TestCase):
    def test_native_ring_object_cadence_and_all_history_bindings(self):
        from line_state_study import study
        result = study()
        self.assertEqual(result['ring_type'], 'CDSPRingDTTemplate<double,2048>')
        self.assertEqual(result['native_core_initial_zero_bytes'], 2048*8)
        self.assertFalse(result['callback_advances_origin'])
        self.assertTrue(result['sync_advances_origin_after_routing'])
        self.assertEqual(len(result['accesses']), 46)
        self.assertEqual(sum(a['kind'] == 'read' for a in result['accesses']), 24)
        self.assertEqual(len(result['accessed_logical_addresses']), 32)
        self.assertEqual([(p['previous_write'], p['next_read']) for p in result['history_pairs']],
                         list(HISTORY_PAIRS))
        by_pc = {a['pc']: a for a in result['accesses']}
        self.assertEqual([(by_pc[p]['kind'], by_pc[p]['address']) for p in (0x2dfa74, 0x2dfab4)],
                         [('read', 0x27), ('write', 0x27)])
        self.assertEqual([by_pc[p]['address'] for p in (0x2df9bc, 0x2df9cc, 0x2dfab4, 0x2dfb08)],
                         [0x27, 3, 0x27, 0x27])
        self.assertEqual([by_pc[p]['address'] for p in (0x2dfa50, 0x2dfa60, 0x2dfac8, 0x2dfc08)],
                         [0x28, 6, 0x28, 0x28])
        self.assertEqual(result['current_factor_scratch'], [0x27, 0x28])
        self.assertEqual(result['current_wet_scratch'], [0x29, 0x2a])
        self.assertFalse(result['callback_count_per_sync_proven'])
        self.assertFalse(result['hardware_ring_semantics_proven'])


if __name__ == '__main__':
    unittest.main()
