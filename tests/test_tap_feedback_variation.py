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
from tap_feedback_variation_study import (check_auxiliary_cut, check_trace,
                                          first_mac_port_models, match_variations)


def authored_rows(second=False):
    a = ([0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4, 0xc008, 0xc008] if second else
         [0x5f09, 0x0410, 0x4512, 0x3fe4, 0x7fe6, 0x2400, 0x2400, 0xc008, 0xc008])
    d = ([0x2207, 0x044b, 0x454f, 0x3fe4, 0, 4, 0xc003] if second else
         [0x1005, 0x044b, 0x454f, 0, 4])
    e = ([0xb809, 0x0403, 0x4503, 0x8fe0, 0xcfe2, 0x3fe4, 0x21, 0x31, 0xc004] if second else
         [0xb80c, 0x0426, 0x4529, 0x8fe0, 0xcfe2, 0x3fe4,
          0x21, 0x31, 0xc007, 0x3000, 0x0030, 0])
    return [a, [0xb84b, 0x2403, 0x6507, 0x1fe0, 0x3fe2, 0x5fe4, 0x7fe6,
                0x21, 0xc009, 0x31, 0xc009],
            [0x8fd1, 0x044b, 0x454f, 0x1fe4, 0x8fe6, 0x3fe8, 0x5fea, 0xcfec, 0x7fee,
             2, 6, 0x22, 0x20, 0xc00a, 0x32, 0x30, 0xc00a], d, e]


def family():
    return match_variations(packets(assemble(authored_rows())))[0]


def authored_trace():
    trace = []
    for channel, (cut, one, two) in enumerate(((0x20, 0x21, 0x22), (0x30, 0x31, 0x32))):
        pc = 0x1000 + 0x18 * channel
        incoming = ('opaque', ('retained-input', channel))
        product = ('mul', ('coef', 8), incoming)
        first = ('add', ('mul', ('signal', ('memory', one)), ('coef', 9)), product)
        second = ('add', first, ('mul', ('coef', 10), ('signal', ('memory', two))))
        trace.extend([
            dict(kind='fp', pc=pc, instruction='fmul', value=product),
            dict(kind='store', pc=pc + 4, key=('indexed', DATA_BASE, cut), value=incoming),
            dict(kind='fp', pc=pc + 8, instruction='fmadd', value=first),
            dict(kind='fp', pc=pc + 12, instruction='fmadd', value=second),
            dict(kind='store', pc=pc + 16, key=('indexed', DATA_BASE, one), value=second),
        ])
    return trace


class VariationTests(unittest.TestCase):
    def test_two_exact_context_shapes_keep_products_and_retained_inputs_distinct(self):
        for second in (False, True):
            found = match_variations(packets(assemble(authored_rows(second))))
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['coefficients'], [8, 9, 10])
            self.assertEqual(found[0]['first_mac_extensions'], [2, 6])
            self.assertEqual(found[0]['second_mac_extensions'], [0, 4])
            self.assertTrue(check_trace(authored_trace(), found[0])['verified'])
            self.assertFalse(any('alias_of' in binding for binding in found[0]['bindings']))

    def test_unproved_extensions_controls_headers_and_gaps_fail(self):
        for packet, index, value in [(1, 0, 0xb84d), (1, 1, 0x0403), (2, 1, 0x044f),
                                     (2, 9, 0), (2, 10, 4), (3, 3, 2), (4, 3, 0x9fe0)]:
            rows = packets(assemble(authored_rows())); rows[packet][1][index] = value
            with self.subTest(packet=packet, index=index):
                self.assertFalse(match_variations(rows))
        rows = packets(assemble(authored_rows())); rows[2] = (rows[2][0] + 2, rows[2][1])
        self.assertFalse(match_variations(rows))

    def test_aliases_mismatched_coefficient_loads_and_other_spaces_fail(self):
        for packet, index, value in [(0, 8, 0xc00b), (1, 8, 0xc008), (1, 10, 0xc00b),
                                     (2, 16, 0xc00b), (2, 12, 0x21), (2, 14, 0x800),
                                     (2, 15, 0x20), (4, 6, 0x22)]:
            rows = packets(assemble(authored_rows())); rows[packet][1][index] = value
            with self.subTest(packet=packet, index=index):
                self.assertFalse(match_variations(rows))

    def test_unchanged_main_feedback_or_dropped_first_tap_is_not_a_match(self):
        trace = authored_trace()
        # The first MAC must retain W*Cgain, not merely the unscaled store value W.
        trace[2]['value'] = ('add', trace[2]['value'][1], trace[1]['value'])
        self.assertFalse(check_trace(trace, family())['verified'])
        trace = authored_trace()
        trace[3]['value'] = ('add', trace[0]['value'], trace[3]['value'][2])
        self.assertFalse(check_trace(trace, family())['verified'])

    def test_same_live_slot_on_both_ports_cannot_identify_a_source_selector(self):
        models = first_mac_port_models(family(), {3: 9, 7: 9})
        self.assertEqual(models[3], models[7])
        # Independent live slots would discriminate the hypotheses; the two
        # actual families do not provide that experiment for ports3 versus7.
        asymmetric = first_mac_port_models(family(), {3: 9, 7: 11})
        self.assertNotEqual(asymmetric[3], asymmetric[7])

    def test_asymmetric_state_and_coefficient_identities_are_required(self):
        for alteration in ('channel', 'coefficient', 'negative', 'duplicate-stage'):
            specification, trace = copy.deepcopy(family()), authored_trace()
            if alteration == 'channel':
                specification['second'].reverse()
            elif alteration == 'coefficient':
                specification['coefficients'][1:] = reversed(specification['coefficients'][1:])
            elif alteration == 'negative':
                trace[2]['value'] = ('sub', *trace[2]['value'][1:])
            else:
                trace.append(trace[2].copy())
            with self.subTest(alteration=alteration):
                self.assertFalse(check_trace(trace, specification)['verified'])

    def test_overwritten_equal_repeated_or_late_cuts_and_opaque_results_fail(self):
        for alteration in ('equal', 'repeated', 'late', 'wrong-path', 'opaque-result'):
            trace = authored_trace()
            if alteration == 'equal':
                trace[6]['value'] = trace[1]['value']
            elif alteration == 'repeated':
                trace.append(trace[1].copy())
            elif alteration == 'late':
                trace[1]['pc'] = trace[2]['pc'] + 1
            elif alteration == 'wrong-path':
                trace[1]['key'] = ('indexed', ('unrelated-array',), 0x20)
            else:
                trace[-1]['value'] = ('opaque', 'unsupported downstream arithmetic')
            with self.subTest(alteration=alteration):
                self.assertFalse(check_trace(trace, family())['verified'])


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone unavailable')
class NativePreservationTests(unittest.TestCase):
    # Original authored FMUL D2,D0,D3; FADD D4,D5,D6; STR D0,[X21,W8,UXTW#3].
    CODE = bytes.fromhex('0208631e a428661e a05a28fc')

    def code(self, data):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
        return list(md.disasm(data, 0x1000))

    def test_later_cut_requires_the_unchanged_actual_multiply_source(self):
        self.assertTrue(check_auxiliary_cut(self.code(self.CODE), 0x1000, 0x1008)['verified'])
        for middle in ('a028661e', '00e4004f'):  # D0 write or overlapping V0 write.
            changed = self.CODE[:4] + bytes.fromhex(middle) + self.CODE[8:]
            self.assertFalse(check_auxiliary_cut(self.code(changed), 0x1000, 0x1008)['verified'])
        wrong_source = self.CODE[:8] + bytes.fromhex('a15a28fc')
        self.assertFalse(check_auxiliary_cut(self.code(wrong_source), 0x1000, 0x1008)['verified'])
        self.assertFalse(check_auxiliary_cut(self.code(self.CODE)[::2], 0x1000, 0x1008)['verified'])
        self.assertFalse(check_auxiliary_cut(self.code(self.CODE), 0x1008, 0x1000)['verified'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'zen_arm64').exists()
                     and (CORPUS / 'pairs.json').exists(), 'Capstone or prepared native corpus unavailable')
class NativeVariationTests(unittest.TestCase):
    def test_two_contexts_have_exact_stages_and_separately_owned_input_output_fields(self):
        from tap_feedback_variation_study import study
        rows = study()['comparisons']
        self.assertEqual([row['family']['offset'] for row in rows], [0x14e, 0x1cc])
        expected = [[[0x2088bc, 0x2088ec, 0x2088f0], [0x208928, 0x208954, 0x208958]],
                    [[0x2089d0, 0x208a00, 0x208a04], [0x208a38, 0x208a64, 0x208a68]]]
        for row, pcs in zip(rows, expected):
            self.assertTrue(row['verified'] and row['bindings']['verified'] and row['native_window']['verified'])
            self.assertEqual([[stage['pc'] for stage in channel['stages']] for channel in row['channels']], pcs)
            self.assertTrue(all(proof['verified'] for proof in row['auxiliary_cuts']))
            self.assertEqual(len(row['bindings']['accesses']), 8)
            self.assertEqual(len(row['coefficient_reads']), 6)
            self.assertTrue(row['coefficient_port_ambiguity']['indistinguishable'])
            for channel in range(2):
                read, _, _, write = row['bindings']['accesses'][4 * channel:4 * channel + 4]
                self.assertNotEqual(read['object_field'], write['object_field'])
                self.assertNotEqual(read['relative'], write['relative'])
                self.assertEqual(read['address'], write['address'])

    def test_changed_native_image_is_rejected_before_provenance_analysis(self):
        from unittest.mock import patch
        from tap_feedback_variation_study import study
        with patch('lib.Z', b'not the recorded native image'):
            with self.assertRaisesRegex(ValueError, 'recorded ZENOLOGY'):
                study()


if __name__ == '__main__':
    unittest.main()
