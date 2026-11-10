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
from operand_variants_study import (check_bindings, check_cross_trace, check_mono_trace,
                                    match_cross_allpass, match_mono_prefix)


def authored_cross():
    return packets(assemble([
        [0x7308, 0xbedb, 0x1fe0, 0x2fe2, 0x8fe4, 0x21, 0x23, 0x25],
        [0x1405, 0x4e0b, 0xbfe2, 0x22c1, 0x27],
        [0x0c03, 0xcfe0, 0x29],
    ]))


def cross_trace():
    a, k = ('opaque', 'incoming A'), ('opaque', 'factor')
    value = ('add', ('signal', ('memory', 0x21)),
             ('mul', ('sub', ('signal', ('memory', 0x23)), a), k))
    return [dict(kind='store', pc=0x1000 + 4 * i, key=('indexed', DATA_BASE, address), value=value)
            for i, (address, value) in enumerate([(0x25, a), (0x27, k), (0x29, value)])]


class VariantTests(unittest.TestCase):
    def test_cross_destination_is_b_while_incoming_cutpoint_is_a(self):
        family = match_cross_allpass(authored_cross())[0]
        self.assertEqual([binding['relative'] for binding in family['bindings']], [10, 12, 14, 24, 30])
        self.assertTrue(check_cross_trace(cross_trace(), family)['verified'])
        for packet, position, value in [(0, 4, 0xcfe4), (1, 1, 0x0e0b),
                                        (1, 2, 0xffe2), (1, 3, 0x12c2), (2, 1, 0x8fe0)]:
            rows = authored_cross(); rows[packet][1][position] = value
            with self.subTest(packet=packet, position=position):
                self.assertEqual(match_cross_allpass(rows), [])

    def test_aliases_and_other_spaces_are_not_admitted(self):
        for packet, position, value in [(0, 6, 0x21), (1, 4, 0x25), (2, 2, 0x2018), (0, 5, 0x800)]:
            rows = authored_cross(); rows[packet][1][position] = value
            with self.subTest(packet=packet, position=position):
                self.assertEqual(match_cross_allpass(rows), [])

    def test_swapped_inputs_signs_and_unrelated_store_paths_fail(self):
        family = match_cross_allpass(authored_cross())[0]
        swapped = dict(family, one=family['two'], two=family['one'])
        self.assertFalse(check_cross_trace(cross_trace(), swapped)['verified'])
        trace = cross_trace()
        trace[-1]['value'] = ('add', trace[-1]['value'][1],
                              ('mul', ('sub', trace[0]['value'], ('signal', ('memory', 0x23))),
                               trace[1]['value']))
        self.assertFalse(check_cross_trace(trace, family)['verified'])
        trace = cross_trace(); trace[0]['key'] = ('indexed', ('wrong-array',), 0x25)
        self.assertFalse(check_cross_trace(trace, family)['verified'])

    def test_equal_repeated_and_late_cutpoints_are_rejected(self):
        family = match_cross_allpass(authored_cross())[0]
        for mutation in ('equal', 'repeated', 'late', 'opaque-result'):
            trace = cross_trace()
            if mutation == 'equal':
                trace[1]['value'] = trace[0]['value']
            elif mutation == 'repeated':
                trace.append(trace[0].copy())
            elif mutation == 'late':
                trace[0]['pc'] = trace[-1]['pc'] + 4
            else:
                trace[-1]['value'] = ('opaque', 'unsupported writer')
            with self.subTest(mutation=mutation):
                self.assertFalse(check_cross_trace(trace, family)['verified'])

    def test_mono_requires_both_channels_and_live_coefficient(self):
        rows = packets(assemble([[0x3e07, 0x0fe0, 0x4fe2, 0x3fe4, 0x2016, 0x2017, 0xc007],
                                 [0x0803, 0x080b, 0x42c0], [0x0c03, 0x8fe0, 0x30]]))
        family = match_mono_prefix(rows)
        value = ('mul', ('add', ('signal', ('input', 0)), ('signal', ('input', 1))), ('coef', 7))
        trace = [dict(kind='store', pc=0x2000, key=('indexed', DATA_BASE, 0x30), value=value)]
        self.assertTrue(check_mono_trace(trace, family)['verified'])
        self.assertFalse(check_mono_trace(trace, dict(family, coefficient=8))['verified'])
        trace[0]['value'] = ('mul', ('signal', ('input', 0)), ('coef', 7))
        self.assertFalse(check_mono_trace(trace, family)['verified'])
        for packet, index, altered in [(0, 2, 0x1fe2), (0, 6, 0x4007), (1, 2, 0x43c0), (2, 1, 0xcfe0)]:
            changed = copy.deepcopy(rows); changed[packet][1][index] = altered
            self.assertIsNone(match_mono_prefix(changed))


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone not installed')
class ProvenanceTests(unittest.TestCase):
    def test_record_identity_pointer_mask_scale_and_width_are_independent_requirements(self):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
        # Original fixture: str d0,[x21,w8,uxtw #3].
        instructions = {ins.address: ins for ins in md.disasm(bytes.fromhex('a05a28fc'), 0x1000)}
        fields = {0x104: dict(relative=0x20, address=7), 0x10c: dict(relative=0x40, address=7)}
        expected = [dict(kind='write', relative=0x20, address=7)]
        access = dict(kind='write', pc=0x1000, fields=[0x104],
                      path=['wrapper', 8, 0x18, 0x10, 0x18], mask=0x7ff)
        self.assertTrue(check_bindings([access], fields, expected, instructions)['verified'])
        for change in [dict(fields=[0x10c]), dict(fields=[0x104, 0x10c]),
                       dict(path=['wrapper', 8, 0x18, 0x18, 0x18]), dict(mask=None), dict(kind='read')]:
            self.assertFalse(check_bindings([dict(access, **change)], fields, expected, instructions)['verified'])
        self.assertFalse(check_bindings([access, access], fields, expected, instructions)['verified'])
        for code in ['a04a28fc', 'a05a28bc']:  # wrong scale; S0 instead of D0
            wrong = {ins.address: ins for ins in md.disasm(bytes.fromhex(code), 0x1000)}
            self.assertFalse(check_bindings([access], fields, expected, wrong)['verified'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'pairs.json').exists()
                     and (CORPUS / 'zen_arm64').exists(), 'Capstone or local artifacts not prepared')
class CorpusTests(unittest.TestCase):
    def test_three_comparisons_have_exact_native_record_and_dataflow_agreement(self):
        from operand_variants_study import study
        results = study()
        items = [item for row in results for item in row['comparisons']]
        self.assertEqual([item['end'] for item in items], [0xadba0, 0x2f7f5c, 0x2f808c])
        self.assertTrue(all(item['verified'] and item['provenance']['verified']
                            and item['native_window']['verified'] for item in items))
        self.assertEqual([len(item['expression']) for item in items], [2, 3, 3])
        self.assertEqual([access['object_field'] for access in items[1]['provenance']['accesses']],
                         [0x4fc, 0x504, 0xac, 0x9c, 0xb4])


if __name__ == '__main__':
    unittest.main()
