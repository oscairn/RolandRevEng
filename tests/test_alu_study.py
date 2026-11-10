import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from alu_study import coefficient_pointer_fields, dsp_gain_tail, native_gain_tail
from bmc_dsp import assemble, packets


class GainModelTests(unittest.TestCase):
    def test_asymmetric_inputs_then_shared_gain(self):
        # Authored test packets, not extracted Roland programs.
        rows = [[0x1e05, 0x3fe0, 0x7fe2, 0xc002, 0xc003],
                [0x1503, 0x0403, 0x4507],
                [0x0c03, 0x3fe0, 0xc004],
                [0x1503, 0x0403, 0x4503],
                [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
        self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [2, 4], 1: [3, 4]})

    def test_unknown_arithmetic_discards_stale_coefficients(self):
        rows = [[0x0c03, 0x3fe0, 0xc005], [0x0902, 0x1111],
                [0x1503, 0x0403, 0x4503],
                [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
        self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [], 1: []})

    def test_transfer_bounds_are_checked(self):
        with self.assertRaises(ValueError):
            dsp_gain_tail([(0, [0x0c03, 0x3fee, 0xc005])])

    def test_same_packet_stores_capture_before_gain(self):
        rows = [[0x0c03, 0x3fe0, 0xc002], [0x1503, 0x0403, 0x4503],
                [0x0c03, 0x3fe0, 0xc003],
                [0xb809, 0x0403, 0x4503, 0x3fe0, 0x8fe2, 0xcfe4,
                 0xc004, 0x10, 0x11],
                [0x1e05, 0x0fe0, 0x4fe2, 0x10, 0x11],
                [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
        self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [2], 1: [2]})

    def test_arithmetic_consumes_old_coefficient_before_same_packet_load(self):
        rows = [[0x0c03, 0x3fe0, 0xc002],
                [0x2e05, 0x0403, 0x4503, 0x3fe0, 0xc003],
                [0x1503, 0x0403, 0x4503],
                [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
        self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [2, 3], 1: [2, 3]})

    def test_unknown_store_invalidates_aliased_memory(self):
        rows = [[0x0c03, 0x3fe0, 0xc005], [0x1503, 0x0403, 0x4503],
                [0x0c03, 0x8fe0, 0x0010], [0x0c03, 0x9fe0, 0x0010],
                [0x0c03, 0x0fe0, 0x0010],
                [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
        self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [], 1: [5]})

    def test_unproved_header_context_does_not_assign_gain_semantics(self):
        for other in ([0x0804, 0x0403, 0, 0], [0x0903, 0x3fe0, 0xc005], [0x0902, 0x0403]):
            rows = [[0x0c03, 0x3fe0, 0xc005], other, [0x1503, 0x0403, 0x4503],
                    [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]]
            self.assertEqual(dsp_gain_tail(packets(assemble(rows))), {0: [], 1: []})


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone not installed')
class NativeDefinitionTests(unittest.TestCase):
    # Original synthetic ARM64 programs assembled solely for these tests.
    # Gain: load object/coef pointer, load+convert float, multiply both paths,
    # load output pointers, store both paths, return.
    GAIN = bytes.fromhex('081440f9 098140f9 222940bd 42c0221e 0008621e 2108621e '
                         '482440a9 000100fd 210100fd c0035fd6')
    # Ctor: stride72; resource base; base index; index+7; pointer computation;
    # store in object+100; return. A field-rank heuristic would incorrectly say0.
    CTOR = bytes.fromhex('08098052 291840f9 4a1840b9 4b1d0011 6b25a89b 0b8000f9 c0035fd6')

    def code(self, data):
        import capstone
        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        decoder.detail = True
        return list(decoder.disasm(data, 0x1000))

    def test_native_gain_uses_verified_pointer_field(self):
        result, products = native_gain_tail(self.code(self.GAIN), {0x100: 5}, {})
        self.assertEqual(result, {0: [5], 1: [5]})
        self.assertEqual(len(products), 2)

    def test_similar_field_offset_without_pointer_provenance_is_opaque(self):
        result, _ = native_gain_tail(self.code(self.GAIN), {0x108: 5}, {})
        self.assertEqual(result, {0: [], 1: []})
        wrong_object = bytes.fromhex('081040f9') + self.GAIN[4:]
        result, _ = native_gain_tail(self.code(wrong_object), {0x100: 5}, {})
        self.assertEqual(result, {0: [], 1: []})

    def test_constructor_relative_slot_is_not_field_rank(self):
        self.assertEqual(coefficient_pointer_fields(self.code(self.CTOR)), {0x100: 7})
        wrong_stride = bytes.fromhex('28098052') + self.CTOR[4:]
        self.assertEqual(coefficient_pointer_fields(self.code(wrong_stride)), {})

    def test_constructor_stops_at_return(self):
        appended = self.CTOR + bytes.fromhex('0b8400f9 c0035fd6')
        self.assertEqual(coefficient_pointer_fields(self.code(appended)), {0x100: 7})

    def test_vector_write_invalidates_overlapping_scalar(self):
        # Insert an authored MOVI v0.16b,#0 after scalar multiplies.
        vector_write = bytes.fromhex('00e4004f')
        code = self.GAIN[:24] + vector_write + self.GAIN[24:]
        result, _ = native_gain_tail(self.code(code), {0x100: 5}, {})
        self.assertEqual(result, {0: [], 1: [5]})

    def test_unknown_call_invalidates_stored_memory_alias(self):
        # Original fixture keeps output/base in callee-saved x20/x19 and a
        # factor in d8; only the reload through memory must lose provenance.
        code = bytes.fromhex('f40302aa 081440f9 098140f9 222940bd 42c0221e '
                             '0808621e 130440f9 680200fd 06000094 600240fd '
                             '882640a9 000100fd 280100fd c0035fd6 c0035fd6')
        result, _ = native_gain_tail(self.code(code), {0x100: 5}, {})
        self.assertEqual(result, {0: [], 1: [5]})


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'pairs.json').exists()
                     and (CORPUS / 'zen_arm64').exists(), 'Capstone or local artifacts not prepared')
class PairedGainTests(unittest.TestCase):
    def test_selected_native_effect_tails_match(self):
        from alu_study import study
        results = study()
        self.assertEqual(len(results), 12)
        self.assertTrue(all(item['verified'] for item in results))
        self.assertTrue(all(item['predicted'] == item['observed'] for item in results))
        self.assertTrue(all(len(values) == 2 for item in results for values in item['observed'].values()))


if __name__ == '__main__':
    unittest.main()
