"""Tests for the RVSDLY 0x60/0x71 second-pair cross-check."""
import unittest


class SyntheticChecks(unittest.TestCase):
    # the real RVSDLY packet 0x56 bytes: header 2e07, families [1, 1, 4],
    # control 34e2, literal 2ff000 at packet-relative offset 10
    PACKET_56 = bytes.fromhex('2e0734e25dc68fe000042ff00000')
    # the real RVSDLY packet 0x64 bytes: header 1408, families [0, 4],
    # control 0c24, literal aff800 at packet-relative offset 13
    PACKET_64 = bytes.fromhex('14080c24dfe229c300022ff800aff800')

    def test_packet_56_shape_selects_field_0x60(self):
        import rvsdly_60_71_pair_crosscheck as tool
        hits = tool.packet_references(self.PACKET_56, len(self.PACKET_56),
                                      0x4020, 10)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['control'], '0x34e2')
        self.assertEqual(hits[0]['value'], 0.99609375)
        self.assertEqual(hits[0]['width'], 3)
        # a one-bit change to the stored triple changes the decoded value
        program2 = bytearray(self.PACKET_56)
        program2[10] ^= 1
        hit2 = tool.packet_references(bytes(program2), len(program2), 0x4020, 10)
        self.assertEqual(len(hit2), 1)
        self.assertNotEqual(hit2[0]['value'], 0.99609375)

    def test_packet_64_shape_selects_field_0x71(self):
        import rvsdly_60_71_pair_crosscheck as tool
        hits = tool.packet_references(self.PACKET_64, len(self.PACKET_64),
                                      0x4020, 13)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['control'], '0xc24')
        self.assertEqual(hits[0]['value'], -0.998046875)
        # neighboring offsets do not match the exact-start rule
        self.assertEqual(tool.packet_references(self.PACKET_64, len(self.PACKET_64),
                                                0x4020, 12), [])

    def test_stored_fields_needs_exact_value(self):
        import rvsdly_60_71_pair_crosscheck as tool
        # two 3-byte literal windows plus surrounding filler bytes
        program = bytes.fromhex('000000' '2ff000' 'ff7fff' '2ff001' '0000')
        self.assertEqual(tool.stored_fields(program, len(program), 0.99609375),
                         [3])
        # a one-bit change moves the window out of the result
        program2 = bytes.fromhex('000000' '2ff001' 'ff7fff' '2ff000' '0000')
        self.assertEqual(tool.stored_fields(program2, len(program2), 0.99609375),
                         [9])


class CorpusChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import lib
        from rvsdly_22b_23c_crosscheck import GROUP_22B, GROUP_23C
        cls.lib = lib
        cls.data = lib.Z
        cls.GROUP_22B = GROUP_22B
        cls.GROUP_23C = GROUP_23C

    def test_native_identity(self):
        import hashlib
        from rvsdly_60_71_pair_crosscheck import NATIVE_SHA256
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), NATIVE_SHA256)

    def test_full_study_report(self):
        from rvsdly_60_71_pair_crosscheck import (ADD_60, ADD_71, CALL_60, CALL_71,
                                                  GROUP_60, GROUP_71, SETALG,
                                                  SETALG_END, study)
        report = study(self.data)
        self.assertEqual(report['stored_bytes'],
                         {'0x60': '2ff000', '0x71': 'aff800'})
        self.assertEqual(report['double_copy_fields'],
                         {'0x60': ['0x60', '0x22b'], '0x71': ['0x71', '0x23c']})
        pairs = report['constructor']['pairs']
        self.assertEqual(pairs['0x60'], dict(object_offset='0x1b0',
                                             object_double='0x1b8',
                                             double=0.99609375))
        self.assertEqual(pairs['0x71'], dict(object_offset='0x1a0',
                                             object_double='0x1a8',
                                             double=-0.998046875))
        self.assertEqual(report['constructor']['pair_count'], 44)
        self.assertEqual(report['packet_references']['0x60'],
                         [dict(packet='0x56', header='0x2e07', operation=0,
                               control='0x34e2', width=3, value=0.99609375)])
        self.assertEqual(report['packet_references']['0x71'],
                         [dict(packet='0x64', header='0x1408', operation=0,
                               control='0xc24', width=3, value=-0.998046875)])
        ownership = report['ownership']
        self.assertEqual(ownership['writer'], 'CFspMfxRVSDLY::SetAlg()')
        self.assertEqual(ownership['writer_bounds'], [hex(SETALG), hex(SETALG_END)])
        self.assertEqual(ownership['groups'][hex(GROUP_60)],
                         dict(count=1, field='0x60', record_absolute='0x4080',
                              add=hex(ADD_60), call=hex(CALL_60),
                              argument='d0, d10', descriptor_add='0x8c0'))
        self.assertEqual(ownership['groups'][hex(GROUP_71)],
                         dict(count=1, field='0x71', record_absolute='0x4091',
                              add=hex(ADD_71), call=hex(CALL_71),
                              argument='d0, d9', descriptor_add='0x8a0'))
        self.assertEqual(ownership['peer_pairs']['0x60'],
                         dict(field='0x22b', group=hex(self.GROUP_22B),
                              call='0x2c2640'))
        self.assertEqual(ownership['peer_pairs']['0x71'],
                         dict(field='0x23c', group=hex(self.GROUP_23C),
                              call='0x2c2620'))

    def test_gassdly_contrast(self):
        from rvsdly_60_71_pair_crosscheck import study
        report = study(self.data)
        contrast = report['gassdly_contrast']
        self.assertNotEqual(contrast['stored_bytes']['0x60'], '2ff000')
        self.assertNotEqual(contrast['stored_bytes']['0x71'], 'aff800')
        self.assertNotEqual(contrast['stored_values']['0x60'], 0.99609375)
        self.assertNotEqual(contrast['stored_values']['0x71'], -0.998046875)
        self.assertEqual(contrast['constructor_fields'], [])
        self.assertEqual(contrast['packet_references'], {'0x60': [], '0x71': []})

    def test_rvsdly_60_71_groups_are_count1_with_sole_setalg_reference(self):
        from rvsdly_60_71_pair_crosscheck import FIELDS, GROUP_60, GROUP_71, mentions
        from line_prefix_single_writer import code_references
        found = {row['symbol']: row for row in mentions(self.data, FIELDS)}
        for group, absolute in ((GROUP_60, 0x4080), (GROUP_71, 0x4091)):
            self.assertEqual(found[group]['count'], 1)
            self.assertEqual(len(found[group]['records']), 1)
            self.assertEqual(found[group]['records'][0]['absolute_byte'], absolute)
            self.assertEqual(found[group]['records'][0]['width'], 3)
        # SetAlg is the writer; the skipped oversized windows carry no references
        from rvsdly_60_71_pair_crosscheck import page_references
        for low, high in ((0x589000, 0x5af838), (0x6b74ec, 0x6d5138)):
            self.assertEqual(page_references(self.data, low, high, 0xa43000), [])

    def test_ctor_pairs_fails_closed(self):
        import rvsdly_60_71_pair_crosscheck as tool
        # a requested field with no constructor pair must raise
        with self.assertRaises(ValueError):
            tool.ctor_pairs((0x60, 0x14), {0x60: 0x1b0, 0x14: 0x0},
                            {0x60: 0x1b8, 0x14: 0x8},
                            {0x60: 0.99609375, 0x14: 0.0})
        # wrong offset and wrong double must raise
        with self.assertRaises(ValueError):
            tool.ctor_pairs((0x60, 0x22b), {0x60: 0x1b0, 0x22b: 0x151},
                            {0x60: 0x1b8, 0x22b: 0x158},
                            {0x60: 0.99609375, 0x22b: 0.99609375})
        with self.assertRaises(ValueError):
            tool.ctor_pairs((0x60, 0x22b), {0x60: 0x1b0, 0x22b: 0x150},
                            {0x60: 0x1b8, 0x22b: 0x158},
                            {0x60: 0.99609375, 0x22b: 0.99609374})
        # the real pairs pass
        found, _ = tool.ctor_pairs((0x60, 0x22b), {0x60: 0x1b0, 0x22b: 0x150},
                                   {0x60: 0x1b8, 0x22b: 0x158},
                                   {0x60: 0.99609375, 0x22b: 0.99609375})
        self.assertEqual(set(found), {0x60, 0x22b})

    def test_page_references_scans_only_the_given_window(self):
        import rvsdly_60_71_pair_crosscheck as tool
        # the real SetAlg adrp x1, #0xa43000 / add x1, x1, #0x8c0 pair
        self.assertEqual(tool.page_references(self.data, 0x2c2688, 0x2c2690,
                                              0xa43000), [0xa43000])
        # the adrp at 0x2c26d8 targets 0x821000, not the descriptor page
        self.assertEqual(tool.page_references(self.data, 0x2c26d8, 0x2c26e0,
                                              0xa43000), [])

    def test_run7_fields_are_unchanged(self):
        from rvsdly_22b_23c_crosscheck import (GROUP_22B, GROUP_23C, study as
                                               run7_study)
        report = run7_study(self.data)
        self.assertEqual(report['stored_bytes'],
                         {'0x22b': '2ff000', '0x23c': 'aff800'})
        self.assertEqual(report['ownership']['groups'][hex(GROUP_22B)],
                         dict(count=1, field='0x22b', reference='0x2c2638'))
        self.assertEqual(report['ownership']['groups'][hex(GROUP_23C)],
                         dict(count=1, field='0x23c', reference='0x2c2618'))