import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble, packets
from mac_controls_study import DATA_BASE
from stereo_tap_study import check_trace, match_stereo_taps


def authored_rows():
    # Authored resource assignment, not a copied firmware/program body.
    return [
        [0x2e05, 0x0407, 0x4507, 0x7fe0, 0xc008],
        [0xb88d, 0x0407, 0x4507, 0x1fe0, 0x5fe2, 0x8fe4, 0xcfe6, 0x7fe8,
         0x21, 0x31, 0x20, 0x30, 0xc009],
        [0x8f0b, 0x044f, 0x454f, 0x2fe4, 0x6fe6, 0x7fe8,
         0, 4, 0x22, 0x32, 0xc00a],
        [0x1005, 0x048f, 0x458f, 0, 4],
        [0x5f0a, 0x0424, 0x4527, 0x8fe0, 0xcfe2, 0x21, 0x31, 0x3000, 0x0030, 0x0000],
    ]


def authored_family():
    return match_stereo_taps(packets(assemble(authored_rows())))[0]


def authored_trace():
    a, b = ('opaque', 'incoming left'), ('opaque', 'incoming right')
    gains = [('mul', ('coef', 8), value) for value in (a, b)]
    one = [('add', ('mul', ('coef', 9), ('signal', ('memory', address))), value)
           for address, value in zip((0x21, 0x31), gains)]
    two = [('add', ('mul', ('signal', ('memory', address)), ('coef', 10)), value)
           for address, value in zip((0x22, 0x32), one)]
    events = [dict(kind='store', pc=0x1000 + 4 * i,
                   key=('indexed', DATA_BASE, address), value=value)
              for i, (address, value) in enumerate(((0x20, a), (0x30, b)))]
    for stage, values in enumerate((gains, one, two)):
        events.extend(dict(kind='fp', pc=0x1008 + stage * 8 + channel * 4,
                           instruction='fmul' if stage == 0 else 'fmadd', value=value)
                      for channel, value in enumerate(values))
    events.extend(dict(kind='store', pc=0x1020 + 4 * channel,
                       key=('indexed', DATA_BASE, address), value=value)
                  for channel, (address, value) in enumerate(zip((0x21, 0x31), two)))
    return events


class StereoTapTests(unittest.TestCase):
    def test_exact_context_binds_all_sources_and_explicit_result_aliases(self):
        family = authored_family()
        self.assertEqual(family['coefficients'], [8, 9, 10])
        self.assertEqual(family['first'], [0x21, 0x31])
        self.assertEqual(family['second'], [0x22, 0x32])
        aliases = [row for row in family['bindings'] if 'alias_of' in row]
        self.assertEqual([(row['relative'], row['wire_field']) for row in aliases], [(26, 78), (28, 80)])
        self.assertTrue(check_trace(authored_trace(), family)['verified'])

    def test_unknown_header_opcode_extension_or_packet_gap_is_rejected(self):
        changes = [(1, 0, 0xb84d), (2, 1, 0x044b), (2, 6, 2),
                   (3, 2, 0x458b), (3, 4, 0), (4, 3, 0x9fe0)]
        for packet, index, value in changes:
            rows = packets(assemble(authored_rows()))
            rows[packet][1][index] = value
            with self.subTest(packet=packet, index=index):
                self.assertFalse(match_stereo_taps(rows))
        rows = packets(assemble(authored_rows()))
        rows[2] = (rows[2][0] + 2, rows[2][1])
        self.assertFalse(match_stereo_taps(rows))

    def test_aliased_or_wrong_tag_resources_do_not_become_independent_variables(self):
        for packet, index, value in [(0, 4, 0x4008), (1, 12, 0xc008),
                                     (1, 11, 0x20), (2, 8, 0x21), (2, 9, 0x800),
                                     (4, 5, 0x22)]:
            rows = packets(assemble(authored_rows())); rows[packet][1][index] = value
            with self.subTest(packet=packet, index=index):
                self.assertFalse(match_stereo_taps(rows))

    def test_swapped_states_and_live_coefficient_slots_change_full_expressions(self):
        for change in ('states', 'coefficients'):
            family = copy.deepcopy(authored_family())
            if change == 'states':
                family['first'].reverse()
            else:
                family['coefficients'][1:] = reversed(family['coefficients'][1:])
            with self.subTest(change=change):
                self.assertFalse(check_trace(authored_trace(), family)['verified'])

    def test_each_intermediate_accumulation_is_required(self):
        for change in ('negative', 'missing-feedback', 'duplicate', 'reordered'):
            trace = authored_trace()
            if change == 'negative':
                value = trace[4]['value']; trace[4]['value'] = ('sub', value[1], value[2])
            elif change == 'missing-feedback':
                trace[4]['value'] = trace[4]['value'][1]
            elif change == 'duplicate':
                trace.append(trace[4].copy())
            else:
                trace[4]['pc'] = trace[6]['pc'] + 1
            with self.subTest(change=change):
                self.assertFalse(check_trace(trace, authored_family())['verified'])

    def test_opaque_equal_duplicate_late_or_wrong_path_cutpoints_fail(self):
        for change in ('equal', 'duplicate', 'late', 'wrong-path', 'opaque-result'):
            trace = authored_trace()
            if change == 'equal':
                trace[1]['value'] = trace[0]['value']
            elif change == 'duplicate':
                trace.append(trace[0].copy())
            elif change == 'late':
                trace[0]['pc'] = 0x1024
            elif change == 'wrong-path':
                trace[0]['key'] = ('indexed', ('different-array',), 0x20)
            else:
                trace[-1]['value'] = ('opaque', 'unknown writer')
            with self.subTest(change=change):
                self.assertFalse(check_trace(trace, authored_family())['verified'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'zen_arm64').exists()
                     and (CORPUS / 'pairs.json').exists(), 'Capstone or prepared local corpus unavailable')
class NativeStereoTapTests(unittest.TestCase):
    def test_changed_native_identity_is_rejected_before_analysis(self):
        from unittest.mock import patch
        from stereo_tap_study import study
        with patch('lib.Z', b'an unrelated native artifact'):
            with self.assertRaisesRegex(ValueError, 'recorded ZENOLOGY'):
                study()

    def test_ts808_stages_records_live_coefficients_and_branch_free_window_agree(self):
        from stereo_tap_study import study
        row = study()
        self.assertTrue(row['verified'])
        self.assertEqual(row['family']['offset'], 0x1e)
        self.assertEqual([[stage['pc'] for stage in channel['stages']] for channel in row['channels']],
                         [[0x208698, 0x2086cc, 0x2086d4], [0x2086ac, 0x2086d0, 0x2086d8]])
        self.assertTrue(row['bindings']['verified'] and row['native_window']['verified'])
        self.assertEqual(len(row['bindings']['accesses']), 8)
        self.assertEqual([entry['object_field'] for entry in row['bindings']['accesses']],
                         [0x94, 0x9c, 0x8c, 0x94, 0xac, 0xb4, 0xa4, 0xac])
        self.assertEqual([entry['pc'] for entry in row['coefficient_reads']], [0x208628, 0x208690, 0x2086c4])
        self.assertEqual([len(stage['expression']) for stage in row['channels'][0]['stages']], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
