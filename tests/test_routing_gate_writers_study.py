"""Checks for the routing gate writers study.

tools/routing_gate_writers_study.py pins who writes the routing gate floats
[struct+0x628] (enable) and [struct+0x678] (bypass) that run 8 proved gate the
per-pass effect dispatch: the 0x1b40 initializer 0x42e14 and the 0x46c8
initializer 0x34d690, each writing both floats exactly once, and the two
hard-coded record searchers (routing vtable slots 2/3) that give the manager
its plain-offset view of the same structure. Pure checks run without the
corpus; the pinned-image checks need BMC_CORPUS_DIR (or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import routing_gate_writers_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'zen_arm64'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class GateDefaultsTests(unittest.TestCase):
    def test_record_layout_consistency(self):
        for core, gate in study.GATE_DEFAULTS.items():
            # Each gate value store is preceded 8 bytes earlier by its 32-bit
            # record-key store (key at +0, value at +8 of the tail record).
            # The key immediates differ per core: DSP4 uses 0x0000/0x07c4,
            # DSP5 uses 0x4fce/0x4d02.
            self.assertEqual(gate['enable_default'], 1.0)
            self.assertEqual(gate['bypass_default'], 0.0)
        anchors = {address: (mnemonic, operand)
                   for address, _, mnemonic, operand in study.ANCHORS}
        for core in ('DSP4', 'DSP5'):
            gate = study.GATE_DEFAULTS[core]
            # mov wN, #key then str wN, [x0, #<value_offset-8>], then the
            # 64-bit value store at #<value_offset>.
            key_addr, value_addr = gate['bypass_write'] - 8, gate['bypass_write']
            self.assertEqual(anchors[key_addr][0], 'mov', core)
            self.assertTrue(anchors[key_addr][1].endswith(
                f', #{gate["bypass_key"]:#x}'), core)
            self.assertEqual(anchors[value_addr][0], 'str', core)
            self.assertIn(f'#0x{gate["bypass_offset"]:x}',
                          anchors[value_addr][1], core)

    def test_dsp5_keys_are_real_record_keys(self):
        gate = study.GATE_DEFAULTS['DSP5']
        self.assertEqual(gate['enable_key'], 0x4fce)
        self.assertEqual(gate['bypass_key'], 0x4d02)
        self.assertEqual(gate['record_stride'], 0x50)


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned zen_arm64 image and capstone required')
        cls.data = study.load_image(IMAGE)

    def test_anchors_are_byte_exact(self):
        _, problems = study.check_anchors(self.data)
        self.assertEqual(problems, [])

    def test_initializer_writes_each_gate_exactly_once(self):
        # The scanner is authoritative: single write, at the pinned address,
        # per core and per gate float.
        for core, start, end in (('DSP4', 0x42e14, 0x4439c),
                                 ('DSP5', 0x34d690, 0x351808)):
            gate = study.GATE_DEFAULTS[core]
            writers = study.scan_struct_writers(
                self.data, start, end - start,
                (gate['enable_offset'], gate['bypass_offset']))
            self.assertEqual(writers[gate['enable_offset']],
                             [gate['enable_write']], core)
            self.assertEqual(writers[gate['bypass_offset']],
                             [gate['bypass_write']], core)

    def test_tool_report_is_clean(self):
        report = study.report(IMAGE)
        self.assertTrue(report['ok'])
        self.assertEqual(report['anchors_checked'], len(study.ANCHORS))


if __name__ == '__main__':
    unittest.main()