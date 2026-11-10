import importlib.util
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble
from condition_return_study import classify, evaluate, field_anchor, preserved, report, return_shape


class BoundaryTests(unittest.TestCase):
    def test_finite_native_boundary_and_extra_return_payload(self):
        predicate = dict(kind='outside_epsilon', epsilon=2**-32)
        e = predicate['epsilon']
        for value, expected in [(0.0, False), (-0.0, False), (e/2, False), (-e/2, False),
                                (e, True), (-e, True), (math.nextafter(e, 0), False),
                                (-math.nextafter(e, 0), False), (1.0, True)]:
            self.assertEqual(evaluate(predicate, [value]), expected)
        for value in (math.inf, math.nan):
            with self.assertRaises(ValueError):
                evaluate(predicate, [value])
        self.assertEqual(evaluate(dict(kind='both_nonzero'), [1, -1]), True)
        self.assertEqual(evaluate(dict(kind='both_nonzero'), [1, -0.0]), False)
        self.assertEqual(return_shape([0x0b02, 0x00f8])['pool_bytes'], 0)
        self.assertEqual(return_shape([0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]),
                         dict(header=0x3d06, family=3, pool_bytes=4,
                              pool_bytes_assigned_to_other_transfers=4))
        with self.assertRaises(ValueError):
            return_shape([0x0b03, 0x00f8, 0x1234])

    def test_exact_field_identity_does_not_follow_equal_values(self):
        stream = assemble([[0x680a, 0x7050, 0x4066, 0x2fe2, 0x6fe4,
                            0, 0x20f9, 0x20fa, 0, 0x1400]])
        anchor = field_anchor(stream, 0x20, 10, 0x7050)
        self.assertEqual(anchor['field_byte'], 0x2a)
        # The equal zero at a different position cannot satisfy this record.
        with self.assertRaises(ValueError):
            field_anchor(stream, 0x20, 16, 0x7050)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'zen_arm64').exists(),
                     'Capstone and recorded native image required')
class CorpusTests(unittest.TestCase):
    def test_actual_predicates_field_paths_and_rejected_branch_mutation(self):
        import capstone
        native = (CORPUS/'zen_arm64').read_bytes()
        result = report(native)
        rows = result['predicate_sources']
        self.assertEqual([(r['record_field'], r['relative_program_field'],
                           r['dsp_reference']['field_byte']) for r in rows],
                         [(0x670, 0x7c4, 0x7e4), (0x8d0, 0x3eb4, 0x3ed4),
                          (0x80, 0x43a4, 0x43c4), (0x860, 0x445c, 0x447c)])
        self.assertEqual(result['dsp4_additional_mode_record'],
                         dict(record_field=0x620, program_position=0, default=1.0))
        for row in rows[1:]:
            self.assertEqual(row['predicate']['epsilon'], 2**-32)
            self.assertTrue(evaluate(row['predicate'], [2**-32]))
            self.assertFalse(evaluate(row['predicate'], [2**-33]))
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
        md.detail = True
        changed = bytearray(native[0x34c330:0x34c34c])
        changed[-4] ^= 1  # Invert the final B.GT condition in the actual branch kernel.
        with self.assertRaises(ValueError):
            classify(list(md.disasm(changed, 0x34c330)))
        with self.assertRaises(ValueError):
            preserved(list(md.disasm(native[0x34c2c4:0x34c2c8], 0x34c2c4)), 'v1')


if __name__ == '__main__':
    unittest.main()
