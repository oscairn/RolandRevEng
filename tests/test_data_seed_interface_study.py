import importlib.util
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from data_seed_interface_study import float_sources, report


class SourceTests(unittest.TestCase):
    def test_cpu_float_rounding_is_explicit_and_keeps_signed_zero(self):
        rows = float_sources({17: 1/3, 0: -0.0, 2047: 1.0})
        self.assertEqual([row['logical_index'] for row in rows], [0, 17, 2047])
        self.assertEqual([row['cpu_little_endian_bytes'] for row in rows],
                         ['00000080', 'abaaaa3e', '0000803f'])
        self.assertEqual(rows[1]['source_float32'], 0.3333333432674408)
        self.assertGreater(rows[1]['error'], 0)

    def test_bad_sources_and_unrecognized_firmware_are_rejected(self):
        for values in ([], {True: 0}, {-1: 0}, {2048: 0}, {'17': 0}, {1: True},
                       {1: float('nan')}, {1: float('inf')}, {1: 1e100}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                float_sources(values)
        with self.assertRaisesRegex(ValueError, 'Unsupported CORE1'):
            report(SimpleNamespace(data=b'unknown'), b'')

    @unittest.skipUnless(hasattr(math, 'fma'), 'Packet coefficient prefix needs Python 3.13+')
    def test_binary32_source_rounding_in_the_original_packet_oscillator(self):
        from bmc_allpass_oscillator import render
        sine = math.sin
        for frequency in (440, 9600):
            with self.subTest(frequency=frequency):
                reference, original = render(2056, frequency)
                # Amplitude .25 is an exact power of two: rounding sine rounds the seed.
                with patch('bmc_allpass_oscillator.math.sin', side_effect=lambda phase:
                           float_sources({0: sine(phase)})[0]['source_float32']) as seed_sine:
                    samples, rounded = render(2056, frequency)
                self.assertEqual(seed_sine.call_count, 5)
                self.assertEqual(rounded['initial_data'], {row['logical_index']: row['source_float32']
                                 for row in float_sources(original['initial_data'])})
                difference = max(abs(a-b) for a, b in zip(reference, samples))
                self.assertGreater(difference, 0)
                self.assertLess(difference, 1e-8)
                self.assertFalse(rounded['hardware_execution_verified'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/p).exists() for p in ('b0c1a.bin', 'zen_arm64')),
                     'Capstone and local Fantom/native artifacts required')
class CorpusTests(unittest.TestCase):
    def test_enum0_ring_and_typed_writer_have_separate_portal_boundaries(self):
        from core1 import Core1
        result = report(Core1(CORPUS/'b0c1a.bin'), (CORPUS/'zen_arm64').read_bytes())
        dsp4 = next(row for row in result['banks'] if row['kind'] == 0 and row['dsp'] == 4)
        self.assertEqual(dsp4['float_write_aperture'], 0x41800000)
        self.assertEqual(dsp4['element_capacity'], 2048)
        self.assertEqual(result['native_enum0_ring_pointer'], 0x10)
        self.assertFalse(dsp4['stock_typed_read_allowed'])
        self.assertFalse(result['global_portal_to_enum0_join_proven'])
        self.assertFalse(result['execution_ready'])


if __name__ == '__main__':
    unittest.main()
