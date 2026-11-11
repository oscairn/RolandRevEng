import importlib.util
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment


def assignment():
    return dict(kind='coefficient_shift4', input_addresses=[0x2016, 0x2017],
                coefficient_slots=[0, 1], target=1)


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class ShiftFragmentTests(unittest.TestCase):
    def test_native_float32_rounding_shift_truncation_and_old_port_store(self):
        program = assemble_fragment(assignment())
        self.assertEqual(disassemble_fragment(program), assignment())
        data, coefficients = {1: 99}, {0: 1 + 2**-24, 1: 2**-32 + 2**-56}
        result = execute_fragment(program, data, coefficients, {0x2016: 3, 0x2017: -1})
        self.assertEqual(result['ports'][0], 1)
        self.assertEqual(result['data'], {1: 2**-28})
        self.assertEqual(result['trace'][1]['before'][7], 2**-32)
        self.assertEqual(result['trace'][1]['after'][7], 2**-28)
        self.assertEqual(result['trace'][1]['writes'], {})
        self.assertEqual(result['trace'][2]['writes'], {1: 2**-28})
        self.assertEqual((data, coefficients), ({1: 99}, {0: 1 + 2**-24, 1: 2**-32 + 2**-56}))
        for coefficient, expected in ((-2**-33, 0), (-2**-32, -2**-28), (2**27, -2**31)):
            actual = execute_fragment(program, {}, {0: 1, 1: coefficient},
                                      {0x2016: 0, 0x2017: 0})
            self.assertEqual(actual['data'][1], expected)
        with self.assertRaises(ValueError):
            execute_fragment(program, {}, {0: 1, 1: 2**31}, {0x2016: 0, 0x2017: 0})

    def test_altered_conversion_or_literal_is_rejected(self):
        program = assemble_fragment(assignment())
        for offset in (0, 2, 6, 12, 16, 18, 20, 22, 24, 26, 28, 32, 34):
            changed = bytearray(program)
            changed[offset] ^= 0x10
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        for spec in (dict(assignment(), target=False),
                     dict(assignment(), coefficient_slots=[1, 1])):
            with self.assertRaises(ValueError):
                assemble_fragment(spec)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


class CorpusTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('capstone') and all((CORPUS/name).exists()
                         for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt', 'b0c1a.bin')),
                         'Prepared native and Fantom corpus required')
    def test_stock_bytes_and_independent_native_store_boundaries(self):
        import parse
        from bmc_dsp import swap_words
        from coefficient_shift_study import VSOD_LISTS, base_report
        from core1 import Core1
        from kernel_abi import program_list, read

        report = base_report()
        self.assertEqual(report['store']['pc'], 0x273984)
        self.assertEqual(report['sample_store']['pc'], 0x2739a8)
        _, program, *_ = parse.program('SIM_MFX_VSOD')
        self.assertEqual(assemble_fragment(assignment()), program[4:0x2a])
        core = Core1(CORPUS/'b0c1a.bin')
        for segment in program_list(core, VSOD_LISTS['VSOD'])['segments']:
            logical = swap_words(read(core, segment['source'], (segment['length']+3)&~3))[:segment['length']]
            spec = disassemble_fragment(logical[4:0x2a])
            self.assertEqual(assemble_fragment(spec), logical[4:0x2a])
            gain, shift = spec['coefficient_slots']
            result = execute_fragment(logical[4:0x2a], {}, {gain: 0.25, shift: -0.03125},
                                      dict(zip(spec['input_addresses'], (3, -1))))
            self.assertEqual((result['ports'][0], result['data'][spec['target']]), (0.25, -0.5))
