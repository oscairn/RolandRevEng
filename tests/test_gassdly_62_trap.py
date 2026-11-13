"""Tests for the GASSDLY 6209 6fe4 literal trap ownership study."""
import struct
import unittest


class SyntheticChecks(unittest.TestCase):
    def test_decode_movk_sequence_rebuilds_the_threshold_immediate(self):
        from gassdly_62_trap import THRESHOLD_BITS

        class Row:
            def __init__(self, address, mnemonic, op_str):
                self.address, self.mnemonic, self.op_str = address, mnemonic, op_str

        rows = [Row(0x10, 'mov', 'x9, #0xa0000000'),
                Row(0x14, 'movk', 'x9, #0x9999, lsl #32'),
                Row(0x18, 'movk', 'x9, #0x3fb9, lsl #48'),
                Row(0x1c, 'fmov', 'd1, x9')]
        from gassdly_62_trap import decode_movk_sequence
        self.assertEqual(decode_movk_sequence(rows, 0x10, 0x18, 'x9'), THRESHOLD_BITS)
        self.assertEqual(THRESHOLD_BITS, 0x3fb99999a0000000)

    def test_decode_movk_sequence_fails_closed(self):
        from gassdly_62_trap import decode_movk_sequence

        class Row:
            def __init__(self, address, mnemonic, op_str):
                self.address, self.mnemonic, self.op_str = address, mnemonic, op_str

        with self.assertRaises(ValueError):
            decode_movk_sequence([Row(0x14, 'movk', 'x9, #0x1, lsl #4')], 0x10, 0x18, 'x9')
        with self.assertRaises(ValueError):
            decode_movk_sequence([Row(0x10, 'mov', 'x8, #0x1')], 0x10, 0x10, 'x9')

    def test_low6_reference_rejects_non_reference_codes(self):
        from gassdly_62_trap import packet_field
        with self.assertRaises(ValueError):
            packet_field(0, 64, b'')
        with self.assertRaises(ValueError):
            # register reference 0x02 must fail closed without a literal role
            packet_field(0, 0x02, b'\x00\x00\x00\x00')


class CorpusChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import lib
        cls.lib = lib
        cls.data = lib.Z.read_bytes() if hasattr(lib.Z, 'read_bytes') else lib.Z

    def test_native_identity(self):
        import hashlib
        from gassdly_62_trap import NATIVE_SHA256
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), NATIVE_SHA256)

    def test_full_study_report(self):
        from gassdly_62_trap import GROUP, SETDLY, SETDLY_END, study
        report = study(self.data)
        self.assertEqual(report['representative']['relative_field'], 0x22b)
        self.assertEqual(report['representative']['double'], 1.414)
        self.assertFalse(report['representative']['second_representative_for_23c'])
        trap = report['trap']
        self.assertEqual(trap['low6_field']['field'], '0x23c')
        self.assertEqual(trap['field_22b']['field'], '0x22b')
        self.assertEqual(trap['field_22b']['stored_bytes'], '369fbe')
        self.assertTrue(trap['stored_bytes_equal'])
        self.assertEqual(trap['field_22b']['native_loads'], ['0x2fa1c4', '0x2fa1f0'])
        ownership = report['ownership']
        self.assertEqual(ownership['group'], hex(GROUP))
        self.assertEqual(ownership['count'], 2)
        self.assertEqual(ownership['writer'], 'CFspMfxGASSDLY::SetDLY(bool, int, int)')
        self.assertEqual(ownership['writer_bounds'], [hex(SETDLY), hex(SETDLY_END)])
        self.assertEqual(ownership['unique_call'], '0xcbf98')
        self.assertEqual(ownership['slot_c8_calls'], 1)
        self.assertEqual(len(ownership['sibling_writers']), 5)

    def test_group_is_the_only_count2_group_and_its_call_is_in_setdly(self):
        from gassdly_62_trap import FIELDS, GROUP, SETDLY, SETDLY_END, mentions
        count2 = mentions(self.data, FIELDS, min_count=2)
        self.assertEqual([row['symbol'] for row in count2], [GROUP])
        group, = count2
        self.assertEqual([(r['absolute_byte'], r['relative_byte'], r['width'])
                          for r in group['records']],
                         [(0x424b, 0x22b, 3), (0x425c, 0x23c, 3)])
        from line_prefix_single_writer import code_references
        self.assertEqual(code_references(self.data, GROUP, self.lib.STARTS), [GROUP_CALL])
        self.assertEqual(self.lib.func(GROUP_CALL), (SETDLY, SETDLY_END))

    def test_constructor_has_no_second_23c_pair_and_stored_literals_match(self):
        import parse
        from gassdly_62_trap import constructor_facts
        ctor = constructor_facts()
        self.assertEqual(ctor['pairs_22b'], (0xb0, 1.414))
        self.assertIsNone(ctor['pairs_23c'])
        import lib
        length, program, bankb, tab, base, peer = parse.program('SIM_MFX_GASSDLY')
        self.assertEqual((base, peer), (0x4020, 0x8000))
        self.assertEqual(program[0x22b:0x22e], program[0x23c:0x23f])


GROUP_CALL = 0xcbf98

if __name__ == '__main__':
    unittest.main()