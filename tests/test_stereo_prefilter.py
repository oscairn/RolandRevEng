import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble, packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_filter_study import prefilter_spec, prefilter_report, filter_spec
from line_shaping_study import _float32


@unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ required')
class PrefilterTests(unittest.TestCase):
    def test_all_packets_preserve_old_coefficient_timing_and_raw_history(self):
        spec = prefilter_spec(); program = assemble_fragment(spec)
        data = dict(zip(spec['sources'], [2, 3, 7, -11, 9, 13])); before = data.copy()
        result = execute_fragment(program, data, {5: -.5, 6: .25, 7: -.125}, {0x2016: 4, 0x2017: -5})
        states = [[None]*8,
                  [4., None, None, -.5, -5., None, None, None],
                  [2., None, -2., .25, 7., None, 2.5, None],
                  [3., None, -1.5, -.125, -11., None, 4.25, None],
                  [-1.875, None, 9., -.125, 5.625, None, 13., None],
                  [-1.875, None, 9., -.125, 5.625, None, 13., None]]
        writes = [{}, {0x1e: 4., 0x21: -5.}, {}, {}, {0x1f: -1.875, 0x22: 5.625}]
        for index, (offset, words) in enumerate(packets(program)):
            self.assertEqual(result['trace'][index], dict(offset=offset, header=words[0],
                             before=states[index], after=states[index+1], writes=writes[index]))
        self.assertEqual(data, before)
        self.assertEqual((len(program), len(packets(program))), (86, 5))
        self.assertEqual(len(program+assemble_fragment(filter_spec())), 270)

    def test_float32_coefficients_exact_template_and_validation(self):
        spec = prefilter_spec(); program = assemble_fragment(spec)
        self.assertEqual(disassemble_fragment(program), spec)
        self.assertEqual(swap_words(swap_words(program+b'\0\0'))[:86], program)
        data = dict.fromkeys(spec['sources'], 0)
        result = execute_fragment(program, data, {5: 1/3, 6: 0, 7: 0}, {0x2016: 1, 0x2017: -1})
        self.assertEqual(result['ports'][0], _float32(1/3))
        self.assertEqual(result['ports'][4], -_float32(1/3))
        fields = {8,10,12,30,32,34,36,38,56,58,60,72,74,82,84}
        for offset in range(86):
            if offset & ~1 in fields: continue
            changed = bytearray(program); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_fragment(bytes(changed))
        for name, value in (('sources', True), ('targets', -1), ('coefficient_slots', 0x1000)):
            changed = copy.deepcopy(spec); changed[name][0] = value
            self.assertRaises(ValueError, assemble_fragment, changed)
        changed = copy.deepcopy(spec); changed['targets'][2] += 1
        self.assertRaises(ValueError, assemble_fragment, changed)
        changed = copy.deepcopy(spec); changed['coefficient_slots'][1] = 5
        self.assertRaises(ValueError, assemble_fragment, changed)
        self.assertRaises(ValueError, execute_fragment, program, {}, {5: 1, 6: 0, 7: 0},
                          {0x2016: 1, 0x2017: 2})
        for value in (True, math.nan, math.inf):
            self.assertRaises(ValueError, execute_fragment, program, data, {5: value, 6: 0, 7: 0},
                              {0x2016: 1, 0x2017: 2})


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_actual_native_bindings_and_all_five_fantom_byte_spans(self):
        from limit_control_study import native_context
        original, *_ = native_context('SIM_MFX_FDRV')
        self.assertEqual(assemble_fragment(prefilter_spec())[:76], original[:0x4c])
        self.assertEqual(len(prefilter_report()['bindings']), 8)
        if not (CORPUS/'b0c1a.bin').exists(): self.skipTest('Pinned Fantom image required')
        from core1 import Core1
        from effect_lifecycle_study import IMAGE_SHA256
        from kernel_abi import program_list, read
        core = Core1(CORPUS/'b0c1a.bin')
        self.assertEqual(hashlib.sha256(core.data).hexdigest(), IMAGE_SHA256)
        for segment in program_list(core, 0x610e5a94)['segments']:
            stream = swap_words(read(core, segment['source'], (segment['length']+3)&~3))
            targets = [int.from_bytes(stream[field:field+2], 'big') for field in (0x5a, 0x5c)]
            candidate = stream[:76]+assemble([[0x1e05, 0x8fe0, 0xcfe2, *targets]])
            spec = disassemble_fragment(candidate)
            self.assertEqual(assemble_fragment(spec), candidate)
            data = dict(zip(spec['sources'], [2, 3, 7, -11, 9, 13]))
            coefficients = dict(zip(spec['coefficient_slots'], [-.5, .25, -.125]))
            actual = execute_fragment(candidate, data, coefficients,
                                      dict(zip(spec['input_addresses'], [4, -5])))
            self.assertEqual([actual['ports'][0], actual['ports'][4]], [-1.875, 5.625])

    def test_changed_arithmetic_and_wrong_constructor_representative_are_rejected(self):
        from limit_control_study import native_context
        program, native, memory, fields, trace = native_context('SIM_MFX_FDRV')
        changed = dict(native); changed[0x3051a0] = native[0x305148]
        with patch('limit_control_study.native_context', return_value=(program,changed,memory,fields,trace)):
            self.assertRaises(ValueError, prefilter_report)
        changed_fields = copy.deepcopy(fields)
        for key, value in changed_fields.items():
            if value['relative'] == 0x24: value['address'] += 1
        with patch('limit_control_study.native_context',
                   return_value=(program,native,memory,changed_fields,trace)):
            self.assertRaises(ValueError, prefilter_report)

    @unittest.skipUnless(sys.platform == 'darwin' and platform.machine() == 'arm64' and hasattr(math, 'fma'), 'Native fixture platform required')
    def test_private_packet_ring_matches_native_through_wrap(self):
        command = ('import json; from fdrv_filter_study import native_check; '
                   'print(json.dumps(native_check(2056,(1,2),True,compare_input_stage=True)))')
        run = subprocess.run([sys.executable, '-c', command], capture_output=True, text=True, timeout=45,
                             env=dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS)))
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['independent_packet_input_stage_values'], 20560)
        self.assertEqual(result['final_origin'], 8)
        self.assertFalse(result['bmc_hardware_executed'])


if __name__ == '__main__': unittest.main()
