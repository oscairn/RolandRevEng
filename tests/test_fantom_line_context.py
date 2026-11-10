import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from fantom_line_context import OWNERS, compare_readback, load_context
from render_line_reference import render_reference


class ReadbackTests(unittest.TestCase):
    def test_only_the_opening_mute_bit_is_classified_separately(self):
        baseline = bytes.fromhex('0a02ff71') + bytes(574)
        self.assertTrue(compare_readback(baseline, baseline)['exact_match'])
        muted = baseline[:3] + b'\x70' + baseline[4:]
        report = compare_readback(baseline, muted)
        self.assertFalse(report['exact_match'])
        self.assertTrue(report['opening_mute_change'])
        self.assertEqual(report['first_differences'], [3])
        changed = muted[:-1] + b'\x01'
        self.assertFalse(compare_readback(baseline, changed)['opening_mute_change'])
        self.assertEqual(compare_readback(baseline, changed)['first_differences'], [3, 577])
        with self.assertRaises(ValueError):
            compare_readback(baseline, muted[:-1])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                     'Capstone and recorded CORE1 image required')
class CorpusTests(unittest.TestCase):
    def test_all_five_relocated_byte_streams_match_the_reference_through_wrap(self):
        from core1 import Core1

        core = Core1(CORPUS/'b0c1a.bin')
        expected, _ = render_reference(2056)
        for owner, base, io in zip(
            OWNERS, [0x4020, 0x8040, 0x9040, 0xa040, 0x3020],
            [0x2000, 0x2005, 0x2009, 0x200d, 0x20ee],
        ):
            with self.subTest(owner=hex(owner)):
                context = load_context(core, owner)
                _, histories, report = context
                self.assertEqual(report['placement']['destination'], base)
                self.assertEqual(report['checked_fragment_bytes'], 254)
                self.assertEqual(report['fragments'][0]['assignment']['input_addresses'], [io, io+1])
                self.assertEqual(report['output_operand_candidates'], [io+2, io+3])
                data_base = report['reservations'][0][0]['base']
                self.assertEqual(histories, [(data_base+4, data_base+3), (data_base+6, data_base+5)])
                self.assertFalse(report['runtime_selection_verified'])
                frames, info = render_reference(2056, firmware_context=context)
                self.assertEqual(frames, expected)
                self.assertEqual(info['final_origin'], 8)

    def test_unknown_owner_and_image_are_rejected(self):
        from types import SimpleNamespace
        from core1 import Core1

        with self.assertRaisesRegex(ValueError, 'recorded Fantom'):
            load_context(SimpleNamespace(data=b'another image'), OWNERS[0])
        with self.assertRaisesRegex(ValueError, 'owner'):
            load_context(Core1(CORPUS/'b0c1a.bin'), 0)


if __name__ == '__main__':
    unittest.main()
