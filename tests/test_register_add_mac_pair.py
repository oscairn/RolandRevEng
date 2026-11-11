import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment


def spec():
    return dict(kind='register_add_mac_pair', sources=list(range(10)), targets=[10, 11],
                coefficient_slots=[13, 10])


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class ProfileTests(unittest.TestCase):
    def test_every_port_old_stores_and_next_packet_loads(self):
        assignment = spec()
        program = assemble_fragment(assignment)
        self.assertEqual(len(program), 84)
        self.assertEqual(disassemble_fragment(program), assignment)
        data = dict(enumerate([2, 3, 5, 7, 11, 13, 17, 19, 23, 29]))
        coefficients = {13: .5, 10: -.25}
        original = data.copy(), coefficients.copy()
        result = execute_fragment(program, data, coefficients)
        self.assertEqual(result['ports'], [6, 23, 17, -.25, 19, 29, 19, -.25])
        self.assertEqual(result['data'], data | {10: 3, 11: 11})
        self.assertEqual([row['offset'] for row in result['trace']], [0, 14, 28, 58])
        self.assertEqual(result['trace'][2]['after'], [2, 8, 17, .5, 7, 24, 19, .5])
        self.assertEqual(result['trace'][2]['writes'], {10: 3, 11: 11})
        self.assertEqual(result['trace'][3]['before'], result['trace'][2]['after'])
        self.assertEqual(result['trace'][3]['writes'], {})
        self.assertEqual((data, coefficients), original)

    def test_resources_controls_coefficient_duplicates_and_extensions_fail_closed(self):
        for name, index, value in (('sources', 0, True), ('sources', 0, 0x800),
                                   ('sources', 1, 0), ('targets', 1, 0),
                                   ('coefficient_slots', 1, 13), ('coefficient_slots', 0, 0x1000)):
            changed = spec()
            changed[name][index] = value
            self.assertRaises(ValueError, assemble_fragment, changed)
        program = assemble_fragment(spec())
        for field in (2, 16, 30, 32, 34, 52, 60, 72, 82):
            changed = bytearray(program)
            changed[field] ^= 1
            self.assertRaises(ValueError, disassemble_fragment, bytes(changed))
        for changed in (program[:-2], program+bytes(2), program[:28]+program[58:]):
            self.assertRaises(ValueError, disassemble_fragment, changed)
        for name in ('sources', 'targets', 'coefficient_slots'):
            changed = spec()
            changed[name].pop()
            self.assertRaises(ValueError, assemble_fragment, changed)

    def test_missing_values_and_nonfinite_intermediate_are_rejected(self):
        program = assemble_fragment(spec())
        data = {key: 1.0 for key in range(10)}
        self.assertRaises(ValueError, execute_fragment, program, data, {13: .5})
        changed = data.copy()
        changed.pop(7)
        self.assertRaises(ValueError, execute_fragment, program, changed, {13: .5, 10: 0})
        changed = data | {1: 1e308, 2: 1e308}
        self.assertRaises(ValueError, execute_fragment, program, changed, {13: .5, 10: 0})
        changed = data | {1: 1e308, 2: 0}
        self.assertRaises(ValueError, execute_fragment, program, changed, {13: 1e10, 10: 0})


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_last_fifty_six_bytes_match_the_proved_native_paired_program(self):
        from limit_control_study import native_context
        from native_auxiliary_study import report
        report()
        program, *_ = native_context('SIM_MFX_FDRV')
        assignment = spec()
        assignment['sources'] = list(range(6))+[0x2f, 0x32, 0x30, 0x33]
        assignment['targets'] = [0x28, 0x2b]
        self.assertEqual(assemble_fragment(assignment)[28:], program[0xc0:0xf8])

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_same_typed_body_tail_matches_five_fantom_placements(self):
        from bmc_dsp import swap_words
        from core1 import Core1
        from fdrv_cubic_study import fantom_report
        from kernel_abi import program_list, read
        core = Core1(CORPUS/'b0c1a.bin')
        placements = fantom_report(core)
        segments = program_list(core, 0x610e5a94)['segments']
        for row, segment, coefficient in zip(placements, segments, [0x190, 0x1f4, 0x208, 0x21c, 0xe], strict=True):
            base = row['data_base']
            assignment = spec()
            assignment['sources'] = [base+value for value in list(range(6))+[0x2f, 0x32, 0x30, 0x33]]
            assignment['targets'] = [base+0x28, base+0x2b]
            assignment['coefficient_slots'] = [coefficient+13, coefficient+10]
            stream = swap_words(read(core, segment['source'], (segment['length']+3) & ~3))
            emitted = assemble_fragment(assignment)
            self.assertEqual(emitted[28:], stream[0xc0:0xf8])
            self.assertEqual(disassemble_fragment(emitted), assignment)


@unittest.skipUnless(HAS_NATIVE and hasattr(math, 'fma') and platform.system() == 'Darwin'
                     and platform.machine() == 'arm64', 'macOS ARM64, Python 3.13+ and native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_asymmetric_model_outputs_match_real_native_add_and_mac(self):
        generator = random.Random(704)
        program = assemble_fragment(spec())
        cases, wanted = [], []
        for _ in range(512):
            values = [generator.uniform(-100, 100) for _ in range(10)]
            factor = generator.uniform(-1, 1)
            output = execute_fragment(program, dict(enumerate(values)), {13: factor, 10: .1})
            cases.extend([(*values[:3], factor), (*values[3:6], factor)])
            wanted.extend([output['ports'][0], output['ports'][4]])
            self.assertEqual(output['trace'][2]['writes'], {10: values[1], 11: values[4]})
        command = ('import json,sys; from native_auxiliary_study import native_add_probes; '
                   'print(json.dumps(native_add_probes(json.load(sys.stdin))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', command], input=json.dumps(cases),
                             capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual([value.hex() for value in json.loads(run.stdout)], [value.hex() for value in wanted])


if __name__ == '__main__':
    unittest.main()
