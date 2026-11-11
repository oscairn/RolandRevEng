"""Independent curve vectors, packet timing, exact templates and native cutpoints."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_cubic_study import cubic_reference, cubic_spec


class CubicTests(unittest.TestCase):
    def test_independent_inputs_and_every_packet_read_before_write(self):
        spec = cubic_spec()
        inputs = dict(zip(spec['sources'], [.125, -.25, .5, -.75]))
        before = inputs.copy()
        result = execute_fragment(assemble_fragment(spec), inputs, {})
        a, b, c, d = [.125, -.25, .5, -.75]
        ca, cb, cc, cd = [.330078125, -.578125, .875, -.984375]
        states = [[None]*8,
                  [a, None, None, None, d, None, None, None],
                  [a, None, 3*a, None, c, None, None, None],
                  [a, a*a, 3-abs(3*a), None, c, None, 3*c, None],
                  [a, a*a+3-abs(3*a), 3-abs(3*a), None, c, c*c, 3-abs(3*c), None],
                  [b, ca, 3-abs(3*a), None, c, c*c+3-abs(3*c), 3-abs(3*c), None],
                  [b, ca, 3*b, None, d, cc, 3-abs(3*c), None],
                  [b, b*b, 3-abs(3*b), None, d, cc, 3*d, None],
                  [b, b*b+3-abs(3*b), 3-abs(3*b), None, d, d*d, 3-abs(3*d), None],
                  [b, cb, 3-abs(3*b), None, d, d*d+3-abs(3*d), 3-abs(3*d), None],
                  [b, cb, 3-abs(3*b), None, d, cd, 3-abs(3*d), None],
                  [b, cb, ca, None, d, cd, cc, None]]
        writes = [{}, {0x11: d}, {}, {}, {}, {0x12: ca}, {0x13: cc}, {}, {},
                  {0x18: cb}, {0x1a: cd}]
        for index, (offset, words) in enumerate(packets(assemble_fragment(spec))):
            self.assertEqual(result['trace'][index], dict(offset=offset, header=words[0],
                             before=states[index], after=states[index+1], writes=writes[index]))
        self.assertEqual(result['data'], inputs | dict(zip(spec['targets'], [ca, cb, cc, cd])))
        self.assertEqual(inputs, before)

    def test_domain_signed_zero_and_distinct_resources(self):
        spec = cubic_spec(); program = assemble_fragment(spec)
        values = [-0.0, 0.0, math.nextafter(0, -1), math.nextafter(0, 1)]
        result = execute_fragment(program, dict(zip(spec['sources'], values)), {})
        self.assertEqual([result['data'][cell].hex() for cell in spec['targets']],
                         [cubic_reference(value).hex() for value in values])
        for value in [True, None, math.nan, math.inf, 10**1000,
                      math.nextafter(-1, -math.inf), math.nextafter(1, math.inf)]:
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                execute_fragment(program, dict(zip(spec['sources'], [value, 0, 0, 0])), {})
        self.assertRaises(ValueError, execute_fragment, program, {0xe: 0}, {})
        for name in ('sources', 'targets'):
            for value in (True, '1', -1, 0x800):
                changed = copy.deepcopy(spec); changed[name][0] = value
                self.assertRaises(ValueError, assemble_fragment, changed)
        for changed in [dict(spec, targets=spec['sources']), dict(spec, sources=[1]*4),
                        dict(spec, targets=[1, 2]), dict(spec, extra=1)]:
            self.assertRaises(ValueError, assemble_fragment, changed)

    def test_roundtrip_relocation_and_exact_constants(self):
        spec = dict(kind='cubic_quad', sources=[0, 1, 0x7fe, 0x7ff], targets=[5, 6, 7, 8])
        program = assemble_fragment(spec)
        self.assertEqual(len(program), 126)
        self.assertEqual(disassemble_fragment(program), spec)
        stored = swap_words(program+b'\0\0')
        self.assertEqual(swap_words(stored)[:126], program)
        self.assertRaises(ValueError, disassemble_fragment, stored)
        # Change every non-address byte, including headers, literal refs and duplicate reloads.
        fields = {6, 8, 20, 22, 54, 68, 70, 86, 110, 120, 122, 124}
        for offset in range(126):
            if offset & ~1 in fields:
                continue
            changed = bytearray(program); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        for offset in (20, 70, 122, 124):
            changed = bytearray(program); changed[offset+1] ^= 1
            self.assertRaises(ValueError, disassemble_fragment, bytes(changed))
        for invalid in (program[:-2], program+b'\0\0', program[10:], program+program):
            self.assertRaises(ValueError, disassemble_fragment, invalid)

    def test_cli_storage_padding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'cubic.bin'
            command = [sys.executable, str(ROOT/'tools/bmc_subset.py')]
            run = subprocess.run(command+['assemble', str(ROOT/'examples/cubic-quad.json'),
                                 str(output), '--stored'], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            original = output.read_bytes(); self.assertEqual(len(original), 128)
            run = subprocess.run(command+['disassemble', str(output), '--stored', '--length', '126'],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(assemble_fragment(json.loads(run.stdout)), swap_words(original)[:126])
            run = subprocess.run(command+['assemble', str(ROOT/'examples/cubic-quad.json'),
                                 str(output), '--stored'], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            output.write_bytes(swap_words(swap_words(original)[:-1]+b'\1'))
            run = subprocess.run(command+['disassemble', str(output), '--stored', '--length', '126'],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_original_116_byte_body_and_all_fantom_relocations(self):
        from limit_control_study import native_context
        program, *_ = native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(cubic_spec())[10:], program[0x378:0x3ec])
        if not (CORPUS/'b0c1a.bin').exists():
            self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from fdrv_cubic_study import fantom_report
        from kernel_abi import program_list, read
        core = Core1(CORPUS/'b0c1a.bin')
        for row, segment in zip(fantom_report(core), program_list(core, 0x610e5a94)['segments'], strict=True):
            spec = dict(kind='cubic_quad', sources=row['sources'], targets=row['targets'])
            original = swap_words(read(core, segment['source'], (segment['length']+3)&~3))
            self.assertEqual(assemble_fragment(spec)[10:], original[0x378:0x3ec])

    @unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Native ARM64 required')
    def test_emulator_against_isolated_native_and_full_callback_cutpoints(self):
        generator = random.Random(126)
        values = [-1, -.5, -0.0, 0.0, .5, 1, math.nextafter(0, 1), math.nextafter(0, -1)]
        values += [generator.uniform(-1, 1) for _ in range(1024)]
        command = ('import json,sys; from fdrv_cubic_study import native_probes; '
                   'from fdrv_filter_study import native_check; '
                   'print(json.dumps([native_probes(json.load(sys.stdin)), '
                   'native_check(128,(1,2),True,compare_cubic=True)]))')
        run = subprocess.run([sys.executable, '-c', command], input=json.dumps(values),
              capture_output=True, text=True, timeout=45,
              env=dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode, 0, run.stderr)
        actual, checked = json.loads(run.stdout)
        spec = cubic_spec(); program = assemble_fragment(spec)
        for offset in range(0, len(values), 4):
            result = execute_fragment(program, dict(zip(spec['sources'], values[offset:offset+4])), {})
            self.assertEqual([result['data'][cell].hex() for cell in spec['targets']],
                             [value.hex() for value in actual[offset:offset+4]])
        self.assertEqual(checked['conditional_cubic_values_checked'], 512)
        self.assertEqual(checked['distinct_cubic_input_values'], 512)
        self.assertFalse(checked['bmc_hardware_executed'])


if __name__ == '__main__':
    unittest.main()
