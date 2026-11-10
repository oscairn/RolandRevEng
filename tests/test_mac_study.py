import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from alu_study import native_values
from bmc_dsp import assemble, packets
from mac_study import match_dry_wet_family, polynomial, predicted_outputs


def authored_rows():
    return [[0x1e05, 0x0fe0, 0x3fe2, 0x2016, 0xc001],
            [0x1e05, 0x1fe0, 0x7fe2, 0x0020, 0xc002],
            [0x2b07, 0x080b, 0x4fe2, 0x5fe4, 0x13c0, 0x2017, 0x0021],
            [0x1405, 0x490b, 0x3fe2, 0x53c0, 0xc003],
            [0x2e05, 0x0403, 0x4503, 0x3fe0, 0xc004],
            [0x1503, 0x0403, 0x4503]]


class MacFamilyTests(unittest.TestCase):
    def test_exact_family_extracts_independent_operands(self):
        family = match_dry_wet_family(packets(assemble(authored_rows())))
        self.assertEqual(family, {'offset': 0, 'wet_addresses': [0x20, 0x21],
                                  'coefficient_slots': [1, 2, 3, 4]})

    def test_other_extension_is_not_silently_accepted(self):
        rows = authored_rows()
        rows[2][4] = 0x1280
        self.assertIsNone(match_dry_wet_family(packets(assemble(rows))))

    def test_dry_and_wet_coefficients_cannot_be_swapped(self):
        family = match_dry_wet_family(packets(assemble(authored_rows())))
        expected = polynomial(predicted_outputs(family)[0])
        family['coefficient_slots'][:2] = [2, 1]
        self.assertNotEqual(expected, polynomial(predicted_outputs(family)[0]))

    def test_polynomial_compares_operand_identity_not_load_order(self):
        x, y, c, d = ('signal', ('input', 0)), ('signal', ('memory', 32)), ('coef', 2), ('coef', 3)
        self.assertEqual(polynomial(('add', ('mul', x, c), ('mul', y, d))),
                         polynomial(('add', ('mul', d, y), ('mul', c, x))))
        with self.assertRaises(ValueError):
            polynomial(('mul', x, ('opaque', 0)))


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone not installed')
class NativeMacTests(unittest.TestCase):
    # Original authored ARM64 fixture: coefficient loads, the observed data-array
    # pointer chain, one state read, an audio read, FMUL+FMADD and output store.
    CODE = bytes.fromhex('081440f9 098140f9 222940bd 42c0221e 098540f9 '
                         '232940bd 63c0221e 0a0440f9 4a0d40f9 4a0940f9 '
                         '4a0d40f9 0b0142b9 41596bfc 2c3440a9 800140fd '
                         '2108631e 0004421f 4e0040f9 c00100fd c0035fd6')

    def code(self):
        import capstone
        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        decoder.detail = True
        return list(decoder.disasm(self.CODE, 0x1000))

    def test_mac_expression_preserves_both_sources_and_coefficients(self):
        outputs, _ = native_values(self.code(), {0x100: 2, 0x108: 3}, {0x200: 32}, {32})
        expected = ('add', ('mul', ('signal', ('input', 0)), ('coef', 2)),
                    ('mul', ('signal', ('memory', 32)), ('coef', 3)))
        self.assertEqual(polynomial(outputs[0]), polynomial(expected))

    def test_unresolved_memory_anchor_does_not_manufacture_expression(self):
        outputs, _ = native_values(self.code(), {0x100: 2, 0x108: 3}, {0x200: 32}, {33})
        with self.assertRaises(ValueError):
            polynomial(outputs[0])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'pairs.json').exists()
                     and (CORPUS / 'zen_arm64').exists(), 'Capstone or local artifacts not prepared')
class PairedMacTests(unittest.TestCase):
    def test_supported_variant_matches_and_other_variant_remains_open(self):
        from mac_study import study
        results = {item['cls']: item for item in study()}
        self.assertEqual(set(results), {'SIM_MFX_FETDRIVE', 'SIM_MFX_LINEDRIVE', 'SIM_MFX_LFCOMP'})
        for cls in ('SIM_MFX_FETDRIVE', 'SIM_MFX_LINEDRIVE'):
            self.assertEqual(results[cls]['status'], 'matched')
            self.assertEqual(results[cls]['expected'], results[cls]['observed'])
            self.assertTrue(all(len(terms) == 2 for terms in results[cls]['observed'].values()))
        self.assertEqual(results['SIM_MFX_LFCOMP']['status'], 'unsupported encoding family')


if __name__ == '__main__':
    unittest.main()
