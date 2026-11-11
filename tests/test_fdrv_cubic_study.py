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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from fdrv_cubic_study import context, cubic_reference


class ReferenceTests(unittest.TestCase):
    def test_known_curve_values_and_signed_zero(self):
        for value, expected in ((-1, -1), (-.5, -.875), (0, 0), (.5, .875), (1, 1)):
            self.assertEqual(cubic_reference(value), expected)
        self.assertEqual(cubic_reference(-0.0).hex(), '-0x0.0p+0')
        self.assertEqual(cubic_reference(0.0).hex(), '0x0.0p+0')

    def test_rejects_inputs_outside_the_stock_clipped_domain(self):
        for value in (True, None, math.nan, math.inf, 10**1000,
                      math.nextafter(-1, -math.inf), math.nextafter(1, math.inf)):
            with self.subTest(kind=type(value)), self.assertRaises(ValueError):
                cubic_reference(value)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_four_curve_bindings_and_nonsequential_short_add_candidates(self):
        from fdrv_cubic_study import report
        result = report()
        self.assertEqual(result['context']['sources'], [0xe, 0x10, 0xf, 0x11])
        self.assertEqual(result['context']['targets'], [0x12, 0x18, 0x13, 0x1a])
        self.assertEqual(result['context']['constant'], 3)
        self.assertEqual([row['native_add'] for row in result['curves']],
                         [0x305a1c, 0x305a5c, 0x305a9c, 0x305adc])
        self.assertEqual([row['candidate_short_packet'] for row in result['curves']],
                         [0x392, 0x3c6, 0x39c, 0x3d0])
        self.assertFalse(result['isolated_opcode_admission'])
        self.assertFalse(result['complete_program_executable'])

    def test_changed_control_literal_alias_and_native_add_are_rejected(self):
        from fdrv_cubic_study import report
        from limit_control_study import native_context
        program, native, memory, fields, trace = native_context('SIM_MFX_FDRV')
        self.assertRaises(ValueError, context, program[:0x378])
        for field in (0x394, 0x380, 0x3dc):
            changed = bytearray(program)
            if field == 0x3dc:
                changed[field:field+2] = program[0x376:0x378]
            else:
                changed[field] ^= 1
            with self.subTest(field=hex(field)), self.assertRaises(ValueError):
                context(bytes(changed))
        for destination, replacement in ((0x305a1c, 0x305a18), (0x3059fc, 0x305a00),
                                         (0x305a30, 0x305a00)):
            changed_native = dict(native)
            changed_native[destination] = native[replacement]
            with self.subTest(pc=hex(destination)), patch('limit_control_study.native_context',
                    return_value=(program, changed_native, memory, fields, trace)):
                self.assertRaisesRegex(ValueError, 'instruction sequence', report)

    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_five_fantom_placements_retain_each_cubic_context(self):
        from core1 import Core1
        from fdrv_cubic_study import fantom_report
        core = Core1(CORPUS/'b0c1a.bin')
        rows = fantom_report(core)
        self.assertEqual([row['program_base'] for row in rows], [0x4020, 0x8040, 0x9040, 0xa040, 0x3020])
        self.assertEqual([row['data_base'] for row in rows], [0x100, 0x320, 0x3b6, 0x44c, 0xc0])
        self.assertTrue(all(not row['isolated_opcode_admission'] for row in rows))
        core.data += b'changed'
        self.assertRaisesRegex(ValueError, 'pinned Fantom', fantom_report, core)


@unittest.skipUnless(HAS_NATIVE and platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'macOS ARM64 and pinned native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_bit_exact_native_curve_at_finite_boundaries_and_random_inputs(self):
        generator = random.Random(701)
        values = [-1, math.nextafter(-1, 0), -.5, -0.0, 0.0, .5,
                  math.nextafter(1, 0), 1, math.nextafter(0, 1), math.nextafter(0, -1)]
        values += [generator.uniform(-1, 1) for _ in range(1024)]
        command = ('import json,sys; from fdrv_cubic_study import native_probes; '
                   'print(json.dumps(native_probes(json.load(sys.stdin))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', command], input=json.dumps(values),
                             capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        actual = json.loads(run.stdout)
        self.assertEqual([value.hex() for value in actual], [cubic_reference(value).hex() for value in values])


if __name__ == '__main__':
    unittest.main()
