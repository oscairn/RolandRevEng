import importlib.util
import os
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import label_target_study as lts

RES = [{'base': 0x20000000, 'capacity': 16}, {'base': 0xffff0000, 'capacity': 4}]


class LabelTargetHelperTests(unittest.TestCase):
    def test_record_parses_little_endian_fields(self):
        self.assertEqual(lts.record(b'\x20\x40\x02\x08\x01\x03'),
                         dict(absolute=0x4020, relative=0x0802, segment=1, flags=3))

    def test_record_rejects_bad_length(self):
        for bad in (b'\x20\x40\x08\x01\x02', b'', 5):
            self.assertRaises(ValueError, lts.record, bad)

    def test_resolve_absolute_fallback_vs_empty_reservation_list(self):
        raw = b'\x20\x40\x00\x08\x01\x02'
        self.assertEqual(lts.resolve(raw, None), 0x4020)
        self.assertRaises(ValueError, lts.resolve, raw, [])

    def test_resolve_segment_bounds_and_u32_base_wrap(self):
        self.assertEqual(lts.resolve(b'\x00\x00\x03\x00\x01\x00', RES), 0xffff0003)
        self.assertRaises(ValueError, lts.resolve, b'\x00\x00\x04\x00\x01\x00', RES)
        self.assertRaises(ValueError, lts.resolve, b'\x00\x00\x00\x00\x02\x00', RES)
        self.assertEqual(lts.resolve(b'\x00\x00\x03\x00\x00\x00',
                                    [{'base': 0xfffffffe, 'capacity': 4}]), 1)

    def test_encode_target_expected_constants(self):
        d = lts.encode_target(0x4020, 2)
        self.assertEqual((d['halfword_value'], d['aligned_raw_data'], d['logical_field_bytes']),
                         (0x2010, 0x20100000, '2010'))
        self.assertFalse(d['value_truncated'])
        for width, aligned, logical in ((3, 0x12345600, '123456'), (4, 0x123456, '00123456')):
            encoded = lts.encode_target(0x2468ac, width)
            self.assertEqual(encoded['aligned_raw_data'], aligned)
            self.assertEqual(encoded['logical_field_bytes'], logical)
            self.assertFalse(encoded['value_truncated'])

    def test_encode_target_truncation_and_rejected_targets_widths_bools(self):
        d = lts.encode_target(0x40200000, 2)
        self.assertTrue(d['value_truncated'])
        self.assertEqual(d['logical_field_bytes'], '0000')
        for bad in (0x4021, -2, 0x100000000, 'x', True):
            self.assertRaises(ValueError, lts.encode_target, bad, 2)
        for bad in (1, 5, '2', True, False):
            self.assertRaises(ValueError, lts.encode_target, 0x4020, bad)

    def test_reference_plan_empty_parity_skip_and_rejection_rules(self):
        self.assertEqual(lts.reference_plan([], RES, 3),
                         dict(target_parity_checked=False, patches=[], skipped=[], execution_ready=False))
        self.assertRaises(ValueError, lts.reference_plan, [b'\x00\x00\x00\x00\x00\x00'], RES, 3)
        self.assertRaises(ValueError, lts.reference_plan, [b'\x00\x00\x00\x00\xff\x10'], RES, 3)
        self.assertRaises(ValueError, lts.reference_plan, [b'\x00\x00\x00\x00\xff\x00'], RES, 4)
        self.assertRaises(ValueError, lts.reference_plan, [b'\x00\x00\x03\x00\x01\x09'], RES, 4)
        self.assertEqual(lts.reference_plan([b'\x00\x00\x00\x00\xff\x10'], RES, 4)['skipped'], [0])
        self.assertRaises(ValueError, lts.reference_plan, [b'\x00'*6]*256, RES, 4)

    def test_reference_plan_bounds_flag_site_masking_mixed_refs(self):
        big = [{'base': 0, 'capacity': 8}, {'base': 0x20100000, 'capacity': 0x801}]
        plan = lts.reference_plan([b'\x20\x40\x00\x08\x01\x02', b'\x00\x00\x00\x00\xff\x10',
                                   b'\x00\x00\x02\x00\x00\x02'], big, 0x4020)
        self.assertEqual([p['reference'] for p in plan['patches']], [0, 2])
        self.assertEqual(plan['skipped'], [1])
        p = plan['patches'][0]
        self.assertEqual((p['resolved_site'], p['effective_literal_address'], p['address_mask_alias']),
                         (0x20100800, 0x000800, True))
        self.assertFalse(p['full_field_inside_reservation'])
        q = plan['patches'][1]
        self.assertEqual((q['resolved_site'], q['effective_literal_address'],
                         q['address_mask_alias'], q['full_field_inside_reservation']),
                        (0x2, 0x2, False, True))
        self.assertFalse(plan['execution_ready'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS, 'Capstone and pinned Fantom CORE1 required')
class CorpusTests(unittest.TestCase):
    def test_firmware_anchors_zero_reference_label_and_five_numeric_fields(self):
        from core1 import Core1
        core = Core1(CORPUS/'b0c1a.bin')
        result = lts.report(core)
        self.assertEqual(result['fetdrive_resolved_entry'], 0x4020)
        self.assertEqual(result['fetdrive_entry_symbol']['reference_count'], 0)
        self.assertEqual(result['fetdrive_entry_symbol']['representative'],
                         dict(absolute=0x4020, relative=0, segment=0, flags=1))
        self.assertEqual(result['fetdrive_reference_plan']['patches'], [])
        self.assertEqual(len(result['parent_numeric_matches']), 5)
        self.assertEqual([row['halfword_value'] for row in result['parent_numeric_matches']],
                         [0x2010, 0x4020, 0x4820, 0x5020, 0x1810])
        for row in result['parent_numeric_matches']:
            self.assertFalse(row['counted_label_ownership_proven'])
        self.assertFalse(result['call_return_semantics_verified'])
        self.assertFalse(result['execution_ready'])
        core.data += b'changed'
        self.assertRaisesRegex(ValueError, 'pinned Fantom', lts.report, core)


if __name__ == '__main__':
    unittest.main()
