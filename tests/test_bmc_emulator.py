"""Authored numerical vectors and strict boundaries for the fragment interpreter."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import swap_words
from bmc_subset import assemble_fragment
from bmc_emulator import execute_fragment


def tail_inputs():
    spec = dict(kind='dry_wet_tail', wet_addresses=[0x21, 0x35], coefficient_slots=[2, 6, 9, 13])
    return (assemble_fragment(spec), {0x21: 5, 0x35: -7, 0x7ff: 42},
            {2: 2, 6: -0.5, 9: 3, 13: -2}, {0x2016: -3, 0x2017: 11})


def allpass_inputs():
    spec = dict(kind='allpass4', sources=[1, 3, 5, 7, 9, 11, 13], targets=[2, 4, 6, 8, 10, 12])
    data = dict(zip(spec['sources'], [2, -3, 5, 0.25, 7, -11, 13]))
    data.update({address: -999 for address in spec['targets']})
    return assemble_fragment(spec), data, {}, None


class FragmentNumericsTests(unittest.TestCase):
    def test_tail_every_packet_and_old_coefficient_load_timing(self):
        program, data, coefficients, io = tail_inputs()
        result = execute_fragment(program, data, coefficients, io)
        states = [[None] * 8,
                  [-3, None, None, 2, None, None, None, None],
                  [-3, 5, None, 2, None, None, None, -0.5],
                  [-8.5, 5, None, 2, 11, -7, None, -0.5],
                  [-8.5, 5, None, 3, 25.5, -7, None, -0.5],
                  [-25.5, 5, None, -2, 76.5, -7, None, -0.5],
                  [51, 5, None, -2, -153, -7, None, -0.5]]
        offsets = [0, 10, 20, 34, 44, 54]
        headers = [0x1e05, 0x1e05, 0x2b07, 0x1405, 0x2e05, 0x1503]
        self.assertEqual(len(result['trace']), 6)
        for index, row in enumerate(result['trace']):
            self.assertEqual(row, dict(offset=offsets[index], header=headers[index],
                                       before=states[index], after=states[index + 1], writes={}))
        self.assertEqual(result['ports'], states[-1])
        self.assertEqual(result['data'], data)
        self.assertTrue(all(type(value) is float for value in result['data'].values()))

    def test_allpass_every_packet_uses_incoming_stores_and_old_loads(self):
        result = execute_fragment(*allpass_inputs())
        empty_right = [None] * 4
        states = [[None] * 8,
                  [2, -3, None, None] + empty_right,
                  [2, -3, 5, 0.25] + empty_right,
                  [-2.25, 7, 5, 0.25] + empty_right,
                  [7.3125, 7, -11, 0.25] + empty_right,
                  [2.421875, 13, -11, 0.25] + empty_right,
                  [-8.35546875, 13, -11, 0.25] + empty_right,
                  [-8.35546875, 13, -11, 0.25] + empty_right]
        writes = [{}, {2: 2}, {}, {4: -2.25}, {6: 7.3125},
                  {8: 2.421875}, {10: -8.35546875, 12: -8.35546875}]
        offsets = [0, 10, 24, 34, 48, 62, 72]
        headers = [0x1e05, 0x3e07, 0x1405, 0x2b07, 0x2b07, 0x1405, 0x1e05]
        self.assertEqual(len(result['trace']), 7)
        for index, row in enumerate(result['trace']):
            self.assertEqual(row, dict(offset=offsets[index], header=headers[index],
                                       before=states[index], after=states[index + 1], writes=writes[index]))
        self.assertEqual(result['ports'], states[-1])
        for changes in writes:
            for address, value in changes.items():
                self.assertEqual(result['data'][address], value)
        self.assertTrue(all(type(value) is float or value is None for value in result['ports']))

    def test_zero_is_a_real_value_but_unused_ports_remain_uninitialized(self):
        program, data, _, _ = allpass_inputs()
        result = execute_fragment(program, {key: 0 for key in data}, {})
        self.assertEqual(result['ports'], [0, 0, 0, 0, None, None, None, None])
        self.assertTrue(all(value == 0 for value in result['data'].values()))
        program, data, coefficients, io = tail_inputs()
        coefficients[6] = 0
        del data[0x21]
        with self.assertRaises(ValueError):
            execute_fragment(program, data, coefficients, io)

    def test_map_boundaries_are_valid_without_collapsing_address_spaces(self):
        spec = dict(kind='dry_wet_tail', wet_addresses=[0x7fe, 0x7ff],
                    coefficient_slots=[0, 1, 0xffe, 0xfff])
        result = execute_fragment(assemble_fragment(spec), {0x7fe: 5, 0x7ff: -7},
                                  {0: 2, 1: -0.5, 0xffe: 3, 0xfff: -2},
                                  {0x2016: -3, 0x2017: 11})
        self.assertEqual([result['ports'][0], result['ports'][4]], [51, -153])

    def test_inputs_and_trace_snapshots_have_no_mutable_aliases(self):
        arguments = tail_inputs(); before = copy.deepcopy(arguments)
        result = execute_fragment(*arguments)
        self.assertEqual(arguments, before)
        result['ports'][0] = 999
        self.assertEqual(result['trace'][-1]['after'][0], 51)
        result['trace'][0]['after'][0] = 888
        self.assertEqual(result['trace'][1]['before'][0], -3)
        result['data'][0x21] = 777
        self.assertEqual(arguments, before)
        arguments = allpass_inputs(); before = copy.deepcopy(arguments)
        result = execute_fragment(*arguments)
        result['trace'][1]['writes'][2] = 888
        self.assertEqual(result['data'][2], 2)
        self.assertEqual(arguments, before)


class FragmentBoundaryTests(unittest.TestCase):
    def test_requires_a_complete_exact_profile_before_execution(self):
        program, data, coefficients, io = tail_inputs()
        changed = bytearray(program); changed[28] ^= 0x01
        invalid = [b'', program[:10], program[:-1], program + b'\0\1', program + program,
                   swap_words(program), bytes(changed)]
        allpass, *_ = allpass_inputs()
        invalid.extend([allpass + b'\0\0', swap_words(allpass + b'\0\0')])
        for candidate in invalid:
            with self.subTest(length=len(candidate)), self.assertRaises(ValueError):
                execute_fragment(candidate, data, coefficients, io)
        for candidate in (bytearray(program), memoryview(program), None, 'not bytes'):
            with self.subTest(type=type(candidate)), self.assertRaises(ValueError):
                execute_fragment(candidate, data, coefficients, io)

    def test_missing_inputs_never_become_zero(self):
        program, data, coefficients, io = tail_inputs()
        for name, key in [('data', 0x21), ('data', 0x35), ('coefficients', 2),
                          ('coefficients', 6), ('coefficients', 9), ('coefficients', 13),
                          ('io', 0x2016), ('io', 0x2017)]:
            maps = dict(data=data.copy(), coefficients=coefficients.copy(), io=io.copy())
            del maps[name][key]
            before = copy.deepcopy(maps)
            with self.subTest(name=name, key=key), self.assertRaises(ValueError):
                execute_fragment(program, **maps)
            self.assertEqual(maps, before)
        with self.assertRaises(ValueError):
            execute_fragment(program, data, coefficients)

    def test_key_and_container_validation_covers_unused_entries(self):
        program, data, coefficients, io = tail_inputs()
        invalid_keys = dict(data=[-1, 0x800, False, 1.5, '1'],
                            coefficients=[-1, 0x1000, False, 1.5, '1'],
                            io=[0, 0x2015, 0x2018, False, 'input0'])
        for name, keys in invalid_keys.items():
            for key in keys:
                maps = dict(data=data.copy(), coefficients=coefficients.copy(), io=io.copy())
                maps[name][key] = 1.0
                with self.subTest(name=name, key=key), self.assertRaises(ValueError):
                    execute_fragment(program, **maps)
        with self.assertRaises(ValueError):
            execute_fragment(program, data, coefficients, {float(0x2016): -3, 0x2017: 11})
        for name in ('data', 'coefficients', 'io'):
            maps = dict(data=data, coefficients=coefficients, io=io); maps[name] = []
            with self.subTest(name=name), self.assertRaises(ValueError):
                execute_fragment(program, **maps)
        for name in ('data', 'coefficients'):
            maps = dict(data=data, coefficients=coefficients, io=io); maps[name] = None
            with self.subTest(name=name), self.assertRaises(ValueError):
                execute_fragment(program, **maps)

    def test_all_values_must_be_finite_numbers_even_when_unused(self):
        program, data, coefficients, io = tail_inputs()
        invalid = [False, None, '2', 1j, float('inf'), -float('inf'), float('nan'), 10 ** 1000]
        for name, key in [('data', 0x700), ('coefficients', 0xffe), ('io', 0x2016)]:
            for value in invalid:
                maps = dict(data=data.copy(), coefficients=coefficients.copy(), io=io.copy())
                maps[name][key] = value
                with self.subTest(name=name, value_type=type(value)), self.assertRaises(ValueError):
                    execute_fragment(program, **maps)

    def test_late_missing_read_and_arithmetic_overflow_leave_callers_unchanged(self):
        program, data, coefficients, io = allpass_inputs()
        del data[13]  # Earlier packets have already produced pending/local stores.
        before = copy.deepcopy(data)
        with self.assertRaises(ValueError):
            execute_fragment(program, data, coefficients, io)
        self.assertEqual(data, before)
        program, data, coefficients, io = tail_inputs()
        io[0x2016] = coefficients[2] = 1e308
        arguments = (program, data, coefficients, io); before = copy.deepcopy(arguments)
        with self.assertRaises(ValueError):
            execute_fragment(*arguments)
        self.assertEqual(arguments, before)
        program, data, coefficients, io = allpass_inputs()
        data[1], data[5], data[7] = -1e308, 1e308, 0
        arguments = (program, data, coefficients, io); before = copy.deepcopy(arguments)
        with self.assertRaises(ValueError):
            execute_fragment(*arguments)
        self.assertEqual(arguments, before)


if __name__ == '__main__':
    unittest.main()
