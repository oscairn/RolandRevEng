import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_auxiliary_study import cache_pop, cache_push


class CacheTests(unittest.TestCase):
    def test_all_cursors_restore_the_current_value_with_distinct_canaries(self):
        original = [-11, 23, -37]
        for cursor in range(3):
            for value in (.25, -.375, -0.0):
                saved, advanced = cache_push(original, cursor, value)
                actual, restored = cache_pop(saved, advanced)
                self.assertEqual((advanced, restored), ((cursor+1) % 3, cursor))
                self.assertEqual(actual.hex(), value.hex())
                self.assertEqual(original, [-11, 23, -37])
                self.assertIsNot(saved, original)
                self.assertEqual([saved[i] for i in range(3) if i != cursor],
                                 [original[i] for i in range(3) if i != cursor])

    def test_nested_wrap_and_untracked_occupancy(self):
        for start in range(3):
            slots, cursor = [11, 23, 37], start
            for value in (1, 2, 3, 4):
                slots, cursor = cache_push(slots, cursor, value)
            self.assertEqual(cursor, (start+1) % 3)
            for value in (4, 3, 2, 4):
                actual, cursor = cache_pop(slots, cursor)
                self.assertEqual(actual, value)
        self.assertEqual(cache_pop([11, 23, 37], 0), (37, 2))

    def test_invalid_state_or_value_is_rejected_without_mutation(self):
        original = [11, 23, 37]
        for cursor in (-1, 3, True, 1.0, None):
            self.assertRaises(ValueError, cache_push, original, cursor, 1)
            self.assertRaises(ValueError, cache_pop, original, cursor)
        for slots in ([], [1, 2], [1, 2, 3, 4], (1, 2, 3), None,
                      [1, 2, True], [1, 2, math.nan], [1, 2, 10**1000]):
            self.assertRaises(ValueError, cache_push, slots, 0, 1)
            self.assertRaises(ValueError, cache_pop, slots, 0)
        for value in (None, True, math.inf, math.nan, 10**1000):
            self.assertRaises(ValueError, cache_push, original, 0, value)
        self.assertEqual(original, [11, 23, 37])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_native_banks_additive_cutpoints_and_control_inventory(self):
        from native_auxiliary_study import report
        result = report()
        self.assertEqual([row['bank'] for row in result['native_banks']], [0x80, 0x100])
        self.assertEqual([row['native_add'] for row in result['first_filter_addition_cutpoints']],
                         [0x3052bc, 0x305388])
        self.assertEqual([row['coissued_incoming_store']['address']
                          for row in result['first_filter_addition_cutpoints']], [0x28, 0x2b])
        self.assertEqual(len(result['constructor_cursor_zero_offsets']), 13)
        rows = result['inventory']['candidates']
        self.assertEqual(len(rows), 118)
        self.assertEqual({row['source_index_candidate'] for row in rows}, {0, 2, 3, 4, 6, 7})
        collisions = result['inventory']['low_pattern_collisions']
        self.assertEqual([(row['cls'], row['control'], row['family']) for row in collisions],
                         [('SIM_MFX_STEPFIL', 0x1f60, 1)]*2)
        self.assertFalse(result['paired_roundtrip_introduces_sample_delay'])
        self.assertFalse(result['hardware_stack_depth_verified'])
        self.assertFalse(result['isolated_opcode_admission'])

    def test_modified_cursor_direction_or_additive_consumer_is_rejected(self):
        from native_auxiliary_study import report
        from limit_control_study import native_context
        program, native, memory, fields, trace = native_context('SIM_MFX_FDRV')
        for target, replacement in ((0x305240, 0x305270), (0x305274, 0x305268),
                                     (0x3052bc, 0x305218), (0x3052c0, 0x305294)):
            changed = dict(native)
            changed[target] = native[replacement]
            with self.subTest(pc=hex(target)), patch('limit_control_study.native_context',
                    return_value=(program, changed, memory, fields, trace)):
                self.assertRaises(ValueError, report)


@unittest.skipUnless(HAS_NATIVE and platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'macOS ARM64 and pinned native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_original_native_slices_preserve_all_other_memory_for_each_cursor(self):
        generator = random.Random(703)
        values = [-0.0, 0.0, math.nextafter(0, 1), math.nextafter(0, -1)]
        values += [generator.uniform(-10, 10) for _ in range(128)]
        cases = [([-11, 23, -37], cursor, value) for cursor in range(3) for value in values]
        command = ('import json,sys; from native_auxiliary_study import native_probes; '
                   'print(json.dumps(native_probes(json.load(sys.stdin))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', command], input=json.dumps(cases),
                             capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = json.loads(run.stdout)
        self.assertEqual(len(rows), 396)
        for (_, cursor, value), row in zip(cases, rows, strict=True):
            self.assertEqual(row['restored'].hex(), value.hex())
            self.assertEqual(row['cursor'], cursor)


if __name__ == '__main__':
    unittest.main()
