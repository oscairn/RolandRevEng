import importlib.util
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from line_shaping_study import (EPSILON, GAIN_BITS, SCALE_BITS, decode_constant,
                                decode_gate, decode_quantizer, decode_rational,
                                decode_smoothing, native_channel_reference,
                                quantize_native_reference)


def channel(value, **changes):
    arguments = dict(drive_scale=1, drive=1, mode=0, history=0, smoothing=0,
                     rational_scale=1, a=2, b=0)
    arguments.update(changes)
    return native_channel_reference(value, **arguments)


class QuantizerTests(unittest.TestCase):
    def test_truncation_toward_zero_and_fixed_point_step(self):
        for value in (EPSILON / 2, -EPSILON / 2, math.nextafter(EPSILON, 0)):
            self.assertEqual(quantize_native_reference(value)['fixed_integer'], 0)
        self.assertEqual(quantize_native_reference(EPSILON),
                         dict(fixed_integer=1, shifted_integer=512, quantized=2 ** -23))
        self.assertEqual(quantize_native_reference(-EPSILON)['quantized'], -(2 ** -23))
        self.assertNotEqual(quantize_native_reference(EPSILON / 2)['quantized'], 512 * (EPSILON / 2))

    def test_signed_shift_wrap_is_not_a_smooth_gain(self):
        boundary = quantize_native_reference(2 ** 22)
        self.assertEqual(boundary['fixed_integer'], 2 ** 54)
        self.assertEqual(boundary['shifted_integer'], -(2 ** 63))
        self.assertEqual(boundary['quantized'], -(2 ** 31))
        self.assertEqual(quantize_native_reference(-(2 ** 31))['quantized'], 0)
        self.assertEqual(quantize_native_reference(math.nextafter(2 ** 31, 0))['quantized'], -(2 ** -13))

    def test_conversion_domain_and_finite_values_are_explicit(self):
        for value in (2 ** 31, math.nextafter(-(2 ** 31), -math.inf),
                      True, None, '1', 1j, math.inf, -math.inf, math.nan, 10 ** 1000):
            with self.subTest(type=type(value)), self.assertRaises(ValueError):
                quantize_native_reference(value)


@unittest.skipUnless(hasattr(math, 'fma'), 'Native numeric oracle requires Python3.13+ math.fma')
class ChannelOracleTests(unittest.TestCase):
    def test_strict_mode_boundary_and_quantize_before_clamp(self):
        x = -(2 ** -10)
        signed = channel(x, mode=math.nextafter(EPSILON, 0))
        rectified = channel(x, mode=EPSILON)
        self.assertLess(signed['factor'], 0)
        self.assertGreater(rectified['factor'], 0)
        self.assertEqual(-signed['factor'], rectified['factor'])
        self.assertEqual(channel(2 ** 22)['shaped'], -0.85)
        self.assertEqual(channel(2 ** 22, mode=EPSILON)['shaped'], 0.85)
        # Saturation is at the post-quantizer 1.176-scaled input, not raw input.
        q = math.floor((2 ** 23) / 1.176)
        below = channel(math.ldexp(q, -32))
        above = channel(math.ldexp(q + 1, -32))
        self.assertLess(below['scaled'], 1)
        self.assertGreater(above['scaled'], 1)
        self.assertEqual(below['shaped'], below['scaled'] * 0.85)
        self.assertEqual(above['shaped'], 0.85)

    def test_shared_drive_multiply_order_changes_a_quantizer_bin(self):
        value = float.fromhex('0x1.1ab025914c49cp-11')
        scale = float.fromhex('0x1.13d161e45b492p-4')
        drive = float.fromhex('0x1.1705640000000p+3')
        result = channel(value, drive_scale=scale, drive=drive)
        self.assertEqual(result['quantizer']['fixed_integer'], 1359712)
        reassociated = quantize_native_reference((value * scale) * drive)
        self.assertEqual(reassociated['fixed_integer'], 1359711)

    def test_live_binary32_coefficients_are_not_constructor_doubles(self):
        result = channel(2 ** -10, drive=1 + 2 ** -25, smoothing=1 + 2 ** -25, history=0.25)
        self.assertEqual(result['drive'], 1)
        self.assertEqual(result['smoothing'], 1)
        self.assertEqual(result['smoothed'], 0.25)
        self.assertEqual(result['factor'], 0.25)

    def test_fused_subtract_order_has_an_original_one_ulp_counterexample(self):
        value = float.fromhex('-0x1.60f4280000000p-11')
        history = float.fromhex('-0x1.1b6ea4ee239f2p-1')
        coefficient = float.fromhex('0x1.7912c20000000p-1')
        result = channel(value, history=history, smoothing=coefficient)
        self.assertEqual(result['shaped'].hex(), '-0x1.60d0038793dd9p-2')
        self.assertEqual(result['smoothed'].hex(), '-0x1.fe74a1637292ap-2')
        unfused = result['shaped'] + (history * coefficient - result['shaped'] * coefficient)
        self.assertEqual(unfused.hex(), '-0x1.fe74a1637292bp-2')
        self.assertNotEqual(result['smoothed'], unfused)

    def test_nonzero_history_and_post_rational_values_remain_separate(self):
        result = channel(2 ** -10, history=-0.75, smoothing=0.25,
                         rational_scale=0.5, a=2, b=0.25)
        self.assertAlmostEqual(result['smoothed'], 0.18735)
        self.assertAlmostEqual(result['factor'], 0.21614408782166322)
        self.assertNotEqual(result['smoothed'], result['factor'])
        no_history = channel(2 ** -10, history=0, smoothing=0.25)
        nonzero = channel(2 ** -10, history=1, smoothing=0.25)
        self.assertAlmostEqual(nonzero['smoothed'] - no_history['smoothed'], 0.25)

    def test_invalid_coefficients_overflow_and_singular_ratio_reject(self):
        for name in ('drive_scale', 'drive', 'mode', 'history', 'smoothing', 'rational_scale', 'a', 'b'):
            for value in (False, math.nan, math.inf, None):
                with self.subTest(name=name, value_type=type(value)), self.assertRaises(ValueError):
                    channel(2 ** -10, **{name: value})
        for changes in (dict(drive=1e39), dict(smoothing=1e39),
                        dict(drive_scale=1e308, drive=1e38),
                        dict(history=1e308, smoothing=1e38), dict(a=0, b=0)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                channel(1, **changes)


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone unavailable')
class NativePrimitiveTests(unittest.TestCase):
    # Original authored register assignment; no vendor instruction bytes.
    QUANT = bytes.fromhex('4981589e 29d977d3 2a01629e')
    CONST = bytes.fromhex('e82691d2 2808acf2 a81cdaf2 48fee7f2 1401679e')
    GATE = bytes.fromhex('8022751e e8a79f1a c822601e e9b79f1a 178b751e 0901092a 3f010071 d71e771e')
    SMOOTH = bytes.fromhex('49096b1e 89a54b1f 8c29691e')
    RATIONAL = bytes.fromhex('4e314b1f 4a2d4c1f ca196a1e')

    def code(self, data):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
        return list(md.disasm(data, 0x1000))

    def test_quantizer_width_fraction_shift_and_back_conversion_are_independent(self):
        result = decode_quantizer(self.code(self.QUANT))
        self.assertEqual((result['integer_width'], result['fraction_bits'], result['shift_bits']), (64, 32, 9))
        for offset, word in [(0, '4985589e'), (4, '29dd78d3'), (8, '2a81429e'), (0, '4981599e')]:
            changed = self.QUANT[:offset] + bytes.fromhex(word) + self.QUANT[offset + 4:]
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                decode_quantizer(self.code(changed))
        with self.assertRaises(ValueError):
            decode_quantizer(self.code(self.QUANT)[::2])

    def test_constants_and_strict_sign_mode_conditions_are_checked(self):
        self.assertEqual(decode_constant(self.code(self.CONST))['bits'], f'{GAIN_BITS:016x}')
        with self.assertRaises(ValueError):
            decode_constant(self.code(self.CONST[4:]))
        result = decode_gate(self.code(self.GATE))
        self.assertEqual(result['mode_flag'], 'w8')
        self.assertEqual(result['epsilon_register'], 'd21')
        changed = self.GATE[:4] + bytes.fromhex('e8c79f1a') + self.GATE[8:]
        with self.assertRaises(ValueError):
            decode_gate(self.code(changed))

    def test_subtract_direction_and_rational_operand_order_are_checked(self):
        self.assertEqual(decode_smoothing(self.code(self.SMOOTH))['history'], 'd10')
        with self.assertRaises(ValueError):
            decode_smoothing(self.code(self.SMOOTH[:4] + bytes.fromhex('89a56b1f') + self.SMOOTH[8:]))
        self.assertEqual(decode_rational(self.code(self.RATIONAL))['a'], 'd11')
        with self.assertRaises(ValueError):
            decode_rational(self.code(bytes.fromhex('4e2d4c1f') + self.RATIONAL[4:]))

    def test_destructive_temporary_and_gate_aliases_are_rejected(self):
        # Original authored complete kernels with internally consistent operands
        # but overwritten later inputs; shape matching alone must not accept them.
        for raw in ('4b096b1e 8bad4b1f 8c296b1e',  # Temporary overwrites coefficient.
                    '4c096b1e 8cb14b1f 8c296c1e'):  # Temporary overwrites shaped input.
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_smoothing(self.code(bytes.fromhex(raw)))
        mode_alias = bytes.fromhex('8022751e e8a79f1a c822601e e8b79f1a '
                                   '178b751e 0801082a 1f010071 d71e771e')
        for code in (self.code(mode_alias), self.code(mode_alias)[2:]):
            with self.assertRaises(ValueError):
                decode_gate(code)
        positive_alias = bytes.fromhex('8022751e e8a79f1a c822601e e9b79f1a '
                                       '168b751e 0901092a 3f010071 d61e761e')
        with self.assertRaises(ValueError):
            decode_gate(self.code(positive_alias))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'zen_arm64').exists()
                     and (CORPUS / 'pairs.json').exists(), 'Capstone or prepared native corpus unavailable')
class SourceAnchorsTests(unittest.TestCase):
    def test_constants_flags_float_records_and_circular_state_bindings(self):
        from line_shaping_study import study
        result = study()
        self.assertFalse(result['dsp_semantic_admission'] or result['complete_effect'])
        self.assertEqual(result['constants']['epsilon']['bits'], '3df0000000000000')
        self.assertEqual(result['constants']['gain']['bits'], f'{GAIN_BITS:016x}')
        self.assertEqual(result['constants']['scale']['bits'], f'{SCALE_BITS:016x}')
        self.assertEqual([item['field'] for item in result['literal_records']], [0x42, 0x45, 0xd6, 0xd9, 0xe6, 0xec])
        self.assertTrue(all(item['verified'] for item in result['channel_bindings']))
        self.assertEqual([row['address'] for row in result['channel_bindings'][0]['accesses']], [1, 4, 0x27, 3])
        self.assertEqual([row['address'] for row in result['channel_bindings'][1]['accesses']], [2, 7, 0x28, 6])
        self.assertEqual([row['slot'] for row in result['live_coefficient_reads']], [2, 1, 1])

    def test_wrong_artifact_identity_is_rejected(self):
        from unittest.mock import patch
        from line_shaping_study import study
        with patch('lib.Z', b'unrelated artifact'), self.assertRaises(ValueError):
            study()


if __name__ == '__main__':
    unittest.main()
