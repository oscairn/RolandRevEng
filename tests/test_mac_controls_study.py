import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from mac_controls_study import (DATA_BASE, check_gain_store_trace, check_port2_trace,
                                match_port2_family, port2_outputs, replace_roots,
                                allpass_stores, check_allpass_trace, straight_line_window)
from mac_study import polynomial


def family():
    return dict(wet_addresses=[0x20, 0x21], dry_addresses=[0, 1],
                wet_coefficient=2, dry_coefficient=1)


def authored_trace():
    # Independent authored values, not copied plugin/firmware instructions.
    wet = [('opaque', 'left upstream filter'), ('opaque', 'right upstream filter')]
    trace = [dict(kind='store', pc=0x1000 + 4 * channel,
                  key=('indexed', DATA_BASE, address), value=wet[channel])
             for channel, address in enumerate(family()['wet_addresses'])]
    for channel in range(2):
        expression = ('add', ('mul', wet[channel], ('coef', 2)),
                      ('mul', ('signal', ('memory', channel)), ('coef', 1)))
        trace.append(dict(kind='fp', pc=0x1010 + 4 * channel, instruction='fmadd',
                          register=f'd{channel}', value=expression))
    return trace


class MacControlTests(unittest.TestCase):
    def test_port2_mac_retains_both_independent_inputs(self):
        result = check_port2_trace(authored_trace(), family())
        self.assertTrue(result['verified'])
        self.assertEqual([len(rows) for rows in result['matches'].values()], [1, 1])

    def test_swapped_coefficients_and_wrong_memory_space_fail(self):
        swapped = family(); swapped['wet_coefficient'], swapped['dry_coefficient'] = 1, 2
        self.assertFalse(check_port2_trace(authored_trace(), swapped)['verified'])
        trace = authored_trace()
        trace[0]['key'] = ('indexed', ('unrelated-array',), 0x20)
        self.assertFalse(check_port2_trace(trace, family())['verified'])

    def test_equal_or_ambiguous_cut_points_do_not_count_as_proof(self):
        trace = authored_trace()
        trace[1]['value'] = trace[0]['value']
        self.assertFalse(check_port2_trace(trace, family())['verified'])
        trace = authored_trace(); trace.append(trace[-1].copy())
        self.assertFalse(check_port2_trace(trace, family())['verified'])

    def test_other_extension_is_rejected(self):
        a = [0x8f0e, 0x04aa, 0x45ad, 0x1fe4, 0x3fe6, 0x5fe8,
             0, 4, 0x14, 0xc002, 0x19, 0, 0, 0]
        b = [0x8f0e, 0x046a, 0x456d, 0x1fe4, 0x2fe6, 0x5fe8,
             0, 4, 0, 0xc001, 1, 0, 0, 0]
        c, d = [0x2b07, 0x080b, 0x8fe2, 0xcfe4, 0x1280, 0x20, 0x21], [0x0803, 0x490b, 0x5280]
        rows = list(enumerate([a, b, c, d]))
        self.assertIsNotNone(match_port2_family(rows))
        c[4] = 0x13c0
        self.assertIsNone(match_port2_family(rows))

    def test_store_order_distinguishes_pre_and_post_gain(self):
        trace = authored_trace()[:2]
        specification = dict(addresses=[0x20, 0x21], gain=3, master=0)
        outputs = {channel: ('mul', ('mul', event['value'], ('coef', 3)), ('coef', 0))
                   for channel, event in enumerate(trace)}
        self.assertTrue(check_gain_store_trace(trace, outputs, specification)['verified'])
        outputs = {channel: ('mul', event['value'], ('coef', 0))
                   for channel, event in enumerate(trace)}
        self.assertFalse(check_gain_store_trace(trace, outputs, specification)['verified'])

    def test_upstream_opaque_value_only_becomes_a_named_cut_point(self):
        value = ('opaque', 'unknown filter')
        with self.assertRaises(ValueError):
            polynomial(value)
        self.assertEqual(polynomial(replace_roots(value, {value: ('signal', ('wet', 32))})),
                         polynomial(('signal', ('wet', 32))))

    def test_signed_polynomial_keeps_negative_terms_through_addition(self):
        a, b = ('signal', ('memory', 1)), ('signal', ('memory', 2))
        terms = polynomial(('add', ('sub', a, b), a))
        self.assertEqual(terms, {(a,): 2, (b,): -1})
        self.assertFalse(polynomial(('sub', ('sub', a, b), ('sub', a, b))))

    def test_allpass_first_stage_and_store_alias_checks(self):
        chain = dict(sources=list(range(7)), targets=list(range(0x10, 0x16)))
        values = [('signal', ('memory', address)) for address in chain['sources']]
        expected = ('sub', ('add', values[1], ('mul', values[2], values[3])),
                    ('mul', values[0], values[3]))
        stores = allpass_stores(chain)
        self.assertEqual(polynomial(stores[0x11]), polynomial(expected))
        trace = [dict(kind='store', pc=0x1000 + 4 * index,
                      key=('indexed', DATA_BASE, address), value=value)
                 for index, (address, value) in enumerate(stores.items())]
        self.assertTrue(check_allpass_trace(trace, chain)['verified'])
        trace.append(trace[0].copy())
        self.assertFalse(check_allpass_trace(trace, chain)['verified'])


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone not installed')
class NativeSignedArithmeticTests(unittest.TestCase):
    # Original authored fixture: FMSUB is addend-product; FNMSUB reverses it.
    CODE = bytes.fromhex('081440f9 098140f9 222940bd 42c0221e 098540f9 '
                         '232940bd 63c0221e 2c3440a9 800140fd 0108621e '
                         '0484431f 0584631f 4e3c40a9 c40100fd e50100fd c0035fd6')

    def test_comparison_window_rejects_branches_gaps_and_missing_sources(self):
        import capstone
        from mac_controls_study import straight_line_window
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
        source = ('signal', ('memory', 32))
        trace = [dict(kind='fp', pc=0x1000, value=source)]
        for suffix, expected in [('1f2003d5', True), ('01000014', False),
                                 ('01000094', False), ('c0035fd6', False)]:
            code = list(md.disasm(bytes.fromhex('000040fd' + suffix), 0x1000))
            self.assertEqual(straight_line_window(code, trace, [source], 0x1004)['verified'], expected)
        code = list(md.disasm(bytes.fromhex('000040fd1f2003d51f2003d5'), 0x1000))
        self.assertFalse(straight_line_window([code[0], code[2]], trace, [source], 0x1008)['verified'])
        self.assertFalse(straight_line_window(code, [], [source], 0x1008)['verified'])

    def test_arm64_fused_subtract_directions_are_distinct(self):
        import capstone
        from alu_study import native_values
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
        code, trace = list(md.disasm(self.CODE, 0x1000)), []
        outputs, _ = native_values(code, {0x100: 2, 0x108: 3}, {}, {32}, trace=trace)
        signal = ('signal', ('input', 0))
        expected = ('sub', ('mul', signal, ('coef', 2)), ('mul', signal, ('coef', 3)))
        self.assertEqual(polynomial(outputs[0]), polynomial(expected))
        self.assertEqual(polynomial(outputs[1]), polynomial(('sub', ('mul', signal, ('coef', 3)),
                                                            ('mul', signal, ('coef', 2)))))
        self.assertNotEqual(polynomial(outputs[0]), polynomial(outputs[1]))
        self.assertTrue(straight_line_window(code, trace, [('coef', 2)], code[-2].address)['verified'])
        self.assertFalse(straight_line_window(code, trace, [('coef', 2)], code[-1].address)['verified'])
        self.assertFalse(straight_line_window(code[:-3] + code[-2:], trace,
                                             [('coef', 2)], code[-2].address)['verified'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'pairs.json').exists()
                     and (CORPUS / 'zen_arm64').exists(), 'Capstone or local artifacts not prepared')
class NativePort2MacTests(unittest.TestCase):
    def test_lfcomp_mac_and_store_order_match_independently(self):
        from mac_controls_study import study
        result = study()
        self.assertTrue(result['port2_mac']['verified'])
        self.assertTrue(result['gain_store_order']['verified'])
        self.assertEqual(result['port2_mac']['matches'][0][0]['pc'], 0x3713c4)
        self.assertEqual(result['port2_mac']['matches'][1][0]['pc'], 0x3713ec)
        self.assertEqual(result['gain_store_order']['store_pcs'], {0x22: 0x3714e0, 0x26: 0x3714f4})
        chains = result['allpass_chains']['chains']
        self.assertEqual(len(chains), 2)
        self.assertTrue(all(chain['verified'] and len(chain['stores']) == 6 for chain in chains))
        self.assertEqual([len(store['expression']) for store in chains[0]['stores']], [1, 3, 5, 7, 9, 9])


if __name__ == '__main__':
    unittest.main()
