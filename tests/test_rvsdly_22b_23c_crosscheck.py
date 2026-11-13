"""Tests for the RVSDLY 22b/23c second-program cross-check."""
import struct
import unittest


class SyntheticChecks(unittest.TestCase):
    LONG_PACKET = bytes.fromhex(
        '2b09' '0ca6' '5fe2' '6fe4' '0003' 'c005' 'c006' 'aff8' '0000')
    SHORT_PACKET = bytes.fromhex(
        '2e08' '0422' '34e5' '8fe0' '000a' '2ff8' '002f' 'f000')

    def test_packet_references_finds_strict_layout_long_literal(self):
        import rvsdly_22b_23c_crosscheck as tool
        # the real GASSDLY-trap-shaped packet: long-op literal at offset 14
        hits = tool.packet_references(self.LONG_PACKET, len(self.LONG_PACKET), 0x4020, 14)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['control'], '0xca6')
        self.assertEqual(hits[0]['value'], -0.998046875)
        self.assertEqual(hits[0]['width'], 3)
        # a one-bit change to the stored triple changes the decoded value
        program2 = bytearray(self.LONG_PACKET)
        program2[14] ^= 1
        hit2 = tool.packet_references(bytes(program2), len(program2), 0x4020, 14)
        self.assertEqual(len(hit2), 1)
        self.assertNotEqual(hit2[0]['value'], -0.998046875)
        # neighboring field 15 does not match the exact-start rule
        self.assertEqual(tool.packet_references(self.LONG_PACKET, len(self.LONG_PACKET), 0x4020, 15), [])

    def test_packet_references_finds_strict_layout_short_literal(self):
        import rvsdly_22b_23c_crosscheck as tool
        hits = tool.packet_references(self.SHORT_PACKET, len(self.SHORT_PACKET), 0x4020, 13)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['operation'], 1)
        self.assertEqual(hits[0]['control'], '0x34e5')
        self.assertEqual(hits[0]['value'], 0.99609375)
        # unsupported special-short layout is skipped, not guessed
        program = bytes.fromhex('2e08' '0422' '0f01' '8fe0' '000a' '2ff8' '002f' 'f000')
        self.assertEqual(tool.packet_references(program, len(program), 0x4020, 13), [])

    def test_mentions_fails_closed_on_truncated_records(self):
        import rvsdly_22b_23c_crosscheck as tool
        # 32-byte descriptor: count 2 at +24, table at +16 naming an out-of-range source
        data = bytearray(32)
        struct.pack_into('<Q', data, 16, 1 << 40)  # table pointer beyond any data
        data[24] = 2
        self.assertEqual(tool.mentions(bytes(data), (0x22b, 0x23c)), [])
        # record metadata outside the proved tag set is rejected
        data = bytearray(64)
        struct.pack_into('<Q', data, 16, 32)
        data[24] = 1
        struct.pack_into('<III', data, 32, 0x425c, 0x23c, 0x11)  # metadata 0x11
        self.assertEqual(tool.mentions(bytes(data), (0x22b, 0x23c)), [])


class CorpusChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import lib
        cls.lib = lib
        cls.data = lib.Z

    def test_native_identity(self):
        import hashlib
        from rvsdly_22b_23c_crosscheck import NATIVE_SHA256
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), NATIVE_SHA256)

    def test_full_study_report(self):
        from rvsdly_22b_23c_crosscheck import (CALL_22B, CALL_23C, GROUP_22B,
                                               GROUP_23C, SETALG, SETALG_END, study)
        report = study(self.data)
        self.assertEqual(report['stored_bytes'],
                         {'0x22b': '2ff000', '0x23c': 'aff800'})
        self.assertNotEqual(report['stored_bytes']['0x22b'],
                            report['stored_bytes']['0x23c'])
        pairs = report['constructor']['pairs']
        self.assertEqual(pairs['0x22b']['object_offset'], '0x150')
        self.assertEqual(pairs['0x22b']['object_double'], '0x158')
        self.assertEqual(pairs['0x22b']['double'], 0.99609375)
        self.assertEqual(pairs['0x23c']['object_offset'], '0x140')
        self.assertEqual(pairs['0x23c']['object_double'], '0x148')
        self.assertEqual(pairs['0x23c']['double'], -0.998046875)
        refs = report['packet_references']
        self.assertEqual(refs['0x22b'], [dict(packet='0x21e', header='0x2e08',
                                              operation=1, control='0x34e5', width=3,
                                              value=0.99609375)])
        self.assertEqual(refs['0x23c'], [dict(packet='0x22e', header='0x2b09', operation=0,
                                              control='0xca6', width=3,
                                              value=-0.998046875)])
        self.assertEqual(report['trap_packet']['families'], [0, 4, 4])
        self.assertEqual(report['short_packet']['families'], [1, 1, 4])
        ownership = report['ownership']
        self.assertFalse(ownership['shared_value'])
        self.assertEqual(ownership['writer'], 'CFspMfxRVSDLY::SetAlg()')
        self.assertEqual(ownership['writer_bounds'], [hex(SETALG), hex(SETALG_END)])
        self.assertEqual(ownership['slot_c8_calls'],
                         ['0x2c2620', '0x2c2640', '0x2c265c', '0x2c2678', '0x2c2694',
                          '0x2c26c8'])
        self.assertEqual(ownership['group_call_arguments'],
                         {hex(CALL_23C): 'd0, d9', hex(CALL_22B): 'd0, d10'})
        self.assertEqual(ownership['groups'][hex(GROUP_22B)],
                         dict(count=1, field='0x22b', reference='0x2c2638'))
        self.assertEqual(ownership['groups'][hex(GROUP_23C)],
                         dict(count=1, field='0x23c', reference='0x2c2618'))
        self.assertEqual(ownership['gassdly_count2_group'], '0x9dfa50')

    def test_rvsdly_groups_are_single_record_and_gassdly_group_unchanged(self):
        from rvsdly_22b_23c_crosscheck import FIELDS, GROUP_22B, GROUP_23C, mentions
        found = {row['symbol']: row for row in mentions(self.data, FIELDS)}
        self.assertEqual(len(found[GROUP_22B]['records']), 1)
        self.assertEqual(found[GROUP_22B]['records'][0]['absolute_byte'], 0x424b)
        self.assertEqual(len(found[GROUP_23C]['records']), 1)
        self.assertEqual(found[GROUP_23C]['records'][0]['absolute_byte'], 0x425c)
        count2 = mentions(self.data, FIELDS, min_count=2)
        self.assertEqual([row['symbol'] for row in count2], [0x9dfa50])

    def test_stored_literals_decode_exactly_to_constructor_doubles(self):
        import parse
        from bmc_dsp import literal
        from rvsdly_22b_23c_crosscheck import constructor_pairs
        _, pair_count = constructor_pairs()
        length, program, bankb, tab, base, peer = parse.program('SIM_MFX_RVSDLY')
        self.assertEqual((base, peer), (0x4020, 0x8000))
        self.assertEqual(literal(program[0x22b:0x22e]), 0.99609375)
        self.assertEqual(literal(program[0x23c:0x23f]), -0.998046875)
        self.assertGreater(pair_count, 2)


if __name__ == '__main__':
    unittest.main()