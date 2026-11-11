import copy
import importlib.util
import hashlib
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
from bmc_dsp import packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_clip_study import clip_spec, clip_reference, half_reference


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
class ClipTests(unittest.TestCase):
    def test_each_packet_averages_unclipped_inputs_and_stores_incoming_ports(self):
        spec = clip_spec(); program = assemble_fragment(spec)
        data = dict(zip(spec['sources'], (2, -.75, -.5, 3)))
        saved = data.copy(); result = execute_fragment(program, data, {})
        states = [[None]*8, [2., None, -.5, None, -.75, None, None, None],
                  [1., None, .75, None, -.75, None, 3., None],
                  [1., None, .75, None, -.75, None, 1.125, None],
                  [1., None, .75, None, -.75, None, 1., None],
                  [.75, None, .75, None, -.75, None, 1., None],
                  [.75, None, .75, None, -.75, None, 1., None]]
        writes = [{}, {0x14: 2.}, {0x10: 1., 0x16: -.75}, {0xe: .75}, {0xf: 1.}, {0x11: -.75}]
        for index, (offset, words) in enumerate(packets(program)):
            self.assertEqual(result['trace'][index], dict(offset=offset, header=words[0],
                             before=states[index], after=states[index+1], writes=writes[index]))
        self.assertEqual(data, saved)
        self.assertEqual([result['data'][cell] for cell in spec['targets']], [2, -.75, .75, 1, 1, -.75])
        self.assertNotEqual(result['data'][0xe], .5*(clip_reference(2)+clip_reference(-.5)))

    def test_signed_zero_saturation_large_finite_and_invalid_inputs(self):
        spec = clip_spec(); program = assemble_fragment(spec)
        for value in (-0.0, 0.0, -4.0, 4.0, -sys.float_info.max, sys.float_info.max):
            data = dict.fromkeys(spec['sources'], value)
            result = execute_fragment(program, data, {})
            expected = [value, value, half_reference(value, value), clip_reference(value),
                        half_reference(value, value), clip_reference(value)]
            self.assertEqual([result['data'][cell].hex() for cell in spec['targets']],
                             [number.hex() for number in expected])
        for value in (True, None, math.nan, math.inf, 10**1000):
            data = dict.fromkeys(spec['sources'], 0); data[0x100] = value
            self.assertRaises(ValueError, execute_fragment, program, data, {})
        self.assertRaises(ValueError, execute_fragment, program, {}, {})

    def test_exact_roundtrip_mutations_resources_and_the_other_eighty_byte_profile(self):
        spec = clip_spec(); program = assemble_fragment(spec)
        self.assertEqual((len(program), len(packets(program))), (80, 6))
        self.assertEqual(disassemble_fragment(program), spec)
        self.assertEqual(swap_words(swap_words(program)), program)
        address_fields = {8, 10, 12, 30, 32, 50, 52, 60, 70, 72, 78}
        for offset in range(80):
            if offset & ~1 in address_fields: continue
            changed = bytearray(program); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        for name, value in (('sources', True), ('sources', 0x800), ('targets', -1), ('targets', '1')):
            changed = copy.deepcopy(spec); changed[name][0] = value
            self.assertRaises(ValueError, assemble_fragment, changed)
        for changed in (dict(spec, targets=spec['targets'][:-1]), dict(spec, extra=1),
                        dict(spec, sources=[0x100, 0x101, 0x14, 0x17])):
            self.assertRaises(ValueError, assemble_fragment, changed)
        for offset in (72, 78):
            changed = bytearray(program); changed[offset:offset+2] = bytes.fromhex('0014')
            self.assertRaises(ValueError, disassemble_fragment, bytes(changed))
        tail = dict(kind='dry_wet_tail_with_scratch', wet_addresses=[1, 2],
                    scratch_addresses=[3, 4], coefficient_slots=[0, 1, 2, 3])
        self.assertEqual(len(assemble_fragment(tail)), 80)
        self.assertEqual(disassemble_fragment(assemble_fragment(tail)), tail)
        self.assertRaises(ValueError, disassemble_fragment, program[:-2])
        self.assertRaises(ValueError, disassemble_fragment, program+bytes(2))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    def test_original_sixty_byte_window_and_all_fantom_placements(self):
        from limit_control_study import native_context
        from fdrv_clip_study import report
        original, native, memory, fields, trace = native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(clip_spec())[14:74], original[0x33c:0x378])
        checked = report(); self.assertEqual(len(checked['bindings']), 8)
        self.assertFalse(checked['full_effect_executable'])
        changed = dict(native); changed[0x3059c0] = native[0x30598c]
        with patch('limit_control_study.native_context',
                   return_value=(original, changed, memory, fields, trace)):
            self.assertRaises(ValueError, report)
        if not (CORPUS/'b0c1a.bin').exists(): self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from kernel_abi import program_list, read
        core = Core1(CORPUS/'b0c1a.bin')
        from effect_lifecycle_study import IMAGE_SHA256
        self.assertEqual(hashlib.sha256(core.data).hexdigest(), IMAGE_SHA256)
        for base, segment in zip((0x100, 0x320, 0x3b6, 0x44c, 0xc0),
                                 program_list(core, 0x610e5a94)['segments'], strict=True):
            stream = swap_words(read(core, segment['source'], (segment['length']+3)&~3))
            self.assertEqual(assemble_fragment(clip_spec(base))[14:74], stream[0x33c:0x378])
            self.assertEqual(int.from_bytes(stream[0x33a:0x33c], 'big'), base+0x15)
            self.assertEqual(int.from_bytes(stream[0x382:0x384], 'big'), base+0x11)

    @unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64'
                         and hasattr(math, 'fma'), 'Native ARM64 and Python 3.13+ required')
    def test_native_arithmetic_boundaries_random_pairs_and_conditional_callback(self):
        generator = random.Random(80)
        values = [(-0.0, -0.0), (0., 0.), (2., -.5), (-.75, 3.), (-3., 0.),
                  (sys.float_info.max, sys.float_info.max), (-sys.float_info.max, -sys.float_info.max),
                  (math.nextafter(0, 1), math.nextafter(0, -1))]
        values += [(generator.uniform(-4, 4), generator.uniform(-4, 4)) for _ in range(1024)]
        command = ('import json,sys; from fdrv_clip_study import native_probes; '
                   'from fdrv_filter_study import native_check; '
                   'print(json.dumps([native_probes(json.load(sys.stdin)), '
                   'native_check(128,compare_emulator=True,compare_clip=True,compare_cubic=True)]))')
        run = subprocess.run([sys.executable, '-c', command], input=json.dumps(values),
              capture_output=True, text=True, timeout=45,
              env=dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode, 0, run.stderr)
        actual, checked = json.loads(run.stdout)
        spec = clip_spec(); program = assemble_fragment(spec)
        for offset in range(0, len(values), 2):
            (left, previous_left), (right, previous_right) = values[offset:offset+2]
            result = execute_fragment(program, dict(zip(spec['sources'],
                                      (left, right, previous_left, previous_right))), {})
            expected = [actual[offset][1], actual[offset][0], actual[offset+1][1], actual[offset+1][0]]
            self.assertEqual([result['data'][cell].hex() for cell in spec['targets'][2:]],
                             [value.hex() for value in expected])
        self.assertEqual(checked['conditional_clipped_values_checked'], 768)
        self.assertEqual(checked['conditional_cubic_values_checked'], 512)
        self.assertFalse(checked['bmc_hardware_executed'])


if __name__ == '__main__':
    unittest.main()
