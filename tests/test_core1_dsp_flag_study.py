"""Tests for the CORE1 SetDspFlag family study."""
import unittest
from pathlib import Path
import os

from core1_dsp_flag_study import (EXPECTED_FLAG_PORTS, SHA256,
                                  check_anchors, census, flag_bit_byte,
                                  initial_flag_word, load_image, pack_exe_mode,
                                  pack_flag)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin'
HAS_CORPUS = CORPUS.exists()


class ModelTests(unittest.TestCase):
    def test_pack_flag(self):
        self.assertEqual(pack_flag(0, 2, 2), 0x20000002)
        self.assertEqual(pack_flag(0, 8, 8), 0x80000008)
        self.assertEqual(pack_flag(6, 0x7f, 0), 0x7f)
        with self.assertRaises(ValueError):
            pack_flag(7, 1, 1)
        with self.assertRaises(ValueError):
            pack_flag(0, 0x80, 1)
        with self.assertRaises(ValueError):
            pack_flag(0, 1, 9)

    def test_pack_exe_mode(self):
        self.assertEqual(pack_exe_mode(0, 2, 0, 3), 0x32000000)
        self.assertEqual(pack_exe_mode(1, 0, 0, 3), 0x30000000)
        self.assertEqual(pack_exe_mode(2, 2, 1, 3), 0x32000001)
        self.assertEqual(pack_exe_mode(6, 2, 0, 3), 0x32000000)
        with self.assertRaises(ValueError):
            pack_exe_mode(7, 2, 0, 3)
        with self.assertRaises(ValueError):
            pack_exe_mode(0, 3, 0, 3)
        with self.assertRaises(ValueError):
            pack_exe_mode(0, 2, 0, 9)
        with self.assertRaises(ValueError):
            pack_exe_mode(5, 0, 0, 3)
        with self.assertRaises(ValueError):
            pack_exe_mode(4, 2, 0, 3)
        with self.assertRaises(ValueError):
            pack_exe_mode(0, 2, 2, 3)
        with self.assertRaises(ValueError):
            pack_exe_mode(0, 2, 0x10000, 3)
        self.assertEqual(pack_exe_mode(0, 2, 1, 3), 0x32000001)

    def test_flag_bit_byte(self):
        self.assertEqual(flag_bit_byte(0, 1, True), 2)
        self.assertEqual(flag_bit_byte(0xff, 3, False), 0xf7)
        self.assertEqual(flag_bit_byte(0x02, 1, True), 0x02)
        with self.assertRaises(ValueError):
            flag_bit_byte(0, 7, True)


class VtableTests(unittest.TestCase):
    def test_expected_flag_ports_closed_form(self):
        self.assertEqual(EXPECTED_FLAG_PORTS[0], 0x41104318)
        self.assertEqual(EXPECTED_FLAG_PORTS[5], 0x41109318)
        self.assertEqual(EXPECTED_FLAG_PORTS[6], 0x41102318)


@unittest.skipUnless(HAS_CORPUS, 'pinned b0c1a.bin not present')
class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = load_image(CORPUS)
        digest = __import__('hashlib').sha256(cls.core.data).hexdigest()
        if digest != SHA256:
            raise unittest.SkipTest(f'image hash differs: {digest}')

    def test_anchors(self):
        count, problems = check_anchors(self.core)
        self.assertEqual(count, 40)
        self.assertEqual(problems, [])

    def test_port_tables(self):
        ports = tuple(self.core.u32(0x113a9d0 + 4 * i) for i in range(7))
        self.assertEqual(ports, EXPECTED_FLAG_PORTS)
        exec_ports = tuple(self.core.u32(0x113a9ec + 4 * i) for i in range(7))
        self.assertEqual(exec_ports,
                         tuple([0x41104310 + d * 0x1000 for d in range(6)]
                               + [0x41102310]))

    def test_census(self):
        rows, problems = census(self.core)
        self.assertEqual(problems, [])
        # No direct BL caller of the manager wrappers; they are reached only
        # through manager vtable bytes 0x10/0x14.
        self.assertEqual(rows['mgr_set']['bl'], [])
        self.assertEqual(rows['mgr_set_bit']['bl'], [])
        # The global setter's only direct BL caller is the manager thunk.
        self.assertEqual(rows['global_set']['bl'], [0x1131bbe])
        # The boot verify routine is one of exactly four veneer callers.
        self.assertIn(0x610016c2, rows['veneer_global_set']['bl'])
        self.assertEqual(len(rows['veneer_global_set']['bl']), 4)

    def test_initial_dma_state_word(self):
        self.assertEqual(initial_flag_word(self.core), 0)


if __name__ == '__main__':
    unittest.main()