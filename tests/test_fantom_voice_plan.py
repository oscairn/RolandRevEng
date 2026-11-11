import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import bmc_allpass_voice as voice
from bmc_dsp import packets, swap_words
from bmc_subset import assemble_fragment, disassemble_fragment
from fantom_voice_plan import (OWNERS, build_plan, render_check, required_initial_data,
                               transfer_fields, verify_relocation, write_plan)


class FieldTests(unittest.TestCase):
    def test_only_transfer_operands_are_walked_in_the_misc_quantizer_packet(self):
        from header_study import UnsupportedLayout, layout
        original = voice.programs()
        with self.assertRaises(UnsupportedLayout):
            layout(dict(packets(b''.join(original)))[0xe])
        fields = transfer_fields(original)
        self.assertEqual(len(fields), 30)
        self.assertEqual(len({field['field'] for field in fields}), 30)
        self.assertEqual((fields[2]['port'], fields[2]['address']), (7, 0xc001))
        self.assertIn(0x1c, {field['field'] for field in fields})
        self.assertTrue({0x16, 0x18, 0x1a}.isdisjoint(field['field'] for field in fields))
        self.assertEqual(required_initial_data(original), [0x21, 0x31, 0x41, 0x51, 0x61, 0x71])
        self.assertEqual(len(verify_relocation(original, 0, 0, [0x2016, 0x2017])), 30)

    def test_valid_profile_with_wrong_resource_and_nonaddress_edits_are_rejected(self):
        original = voice.programs()
        spec = disassemble_fragment(original[0])
        spec['target'] += 1
        altered = (assemble_fragment(spec), *original[1:])
        with self.assertRaisesRegex(ValueError, 'independent transfer-field'):
            verify_relocation(altered, 0, 0, [0x2016, 0x2017])
        changed = bytearray(original[0])
        changed[0x18] ^= 1
        with self.assertRaises(ValueError):
            verify_relocation((bytes(changed), *original[1:]), 0, 0, [0x2016, 0x2017])
        for data, coefficient in ((True, 0), (-1, 0), (0x800, 0), (0, 0x1000), (0x7ff, 0)):
            with self.assertRaises(ValueError):
                verify_relocation(original, data, coefficient, [0x2016, 0x2017])
        with self.assertRaisesRegex(ValueError, 'recorded Fantom'):
            build_plan(SimpleNamespace(data=b'unknown'), OWNERS[0])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS, 'Capstone and pinned Fantom CORE1 required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.core = Core1(CORPUS/'b0c1a.bin')

    def test_actual_five_resource_assignments_and_stock_address_separation(self):
        for owner, data_base, coefficient_base, first_input in zip(OWNERS,
                [0x100, 0x320, 0x3b6, 0x44c, 0xc0], [0x190, 0x1f4, 0x208, 0x21c, 0xe],
                [0x2000, 0x2005, 0x2009, 0x200d, 0x20ee]):
            with self.subTest(owner=hex(owner)):
                fragments, result = build_plan(self.core, owner)
                logical = b''.join(fragments)
                self.assertEqual(len(logical), 200)
                self.assertEqual(int.from_bytes(logical[8:10], 'big'), first_input)
                self.assertEqual(int.from_bytes(logical[10:12], 'big'), first_input+1)
                self.assertEqual(int.from_bytes(logical[12:14], 'big'), 0xc000 | (coefficient_base+1))
                self.assertEqual(int.from_bytes(logical[0x24:0x26], 'big'), data_base+0x80)
                self.assertEqual(result['stock_output_operand_candidates'], [first_input+2, first_input+3])
                self.assertEqual(sorted(result['coefficients']), list(range(coefficient_base, coefficient_base+6)))
                self.assertEqual(result['required_initial_data'],
                                 [data_base+cell for cell in (0x21, 0x31, 0x41, 0x51, 0x61, 0x71)])
                self.assertEqual(result['stock_placement']['length'], 578)
                self.assertIsNone(result['load_address'])
                self.assertFalse(result['wrapper_included'])
                self.assertFalse(result['output_io_writes_included'])
                self.assertFalse(result['execution_ready'])

    def test_parameters_change_values_without_changing_the_compiled_body(self):
        fragments, a = build_plan(self.core, OWNERS[0])
        same, b = build_plan(self.core, OWNERS[0], frequency=880, gain=1/3, amplitude=.5)
        self.assertEqual(same, fragments)
        self.assertNotEqual(a['initial_data'], b['initial_data'])
        self.assertNotEqual(a['coefficients'][0x191], b['coefficients'][0x191])
        self.assertEqual(b['coefficients'][0x193], 0.3333333432674408)
        self.assertEqual(len(b['cpu_float32_data_sources']), 6)
        self.assertEqual(len(b['cpu_float32_coefficient_sources']), 6)
        with self.assertRaises(ValueError):
            build_plan(self.core, 0)
        for owner in (True, None, float(OWNERS[0])):
            with self.assertRaises(ValueError):
                build_plan(self.core, owner)
        for parameters in ({'frequency': 0}, {'gain': True}, {'gain': math.inf}, {'amplitude': -1}):
            with self.assertRaises(ValueError):
                build_plan(self.core, OWNERS[0], **parameters)

    @unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
    def test_all_five_relocations_match_through_wrap_with_nonseed_canaries(self):
        for owner in OWNERS:
            with self.subTest(owner=hex(owner)):
                _, result = render_check(self.core, owner)
                self.assertEqual(result['reference_check']['identical_output_values'], 4112)
                self.assertEqual(result['reference_check']['final_origin'], 8)
                self.assertTrue(result['reference_check']['nonseed_background_canaries'])
                self.assertFalse(result['whole_ring_clear_required_by_model'])
        for frames in (True, 127, 128.0, 1000001):
            with self.assertRaises(ValueError):
                render_check(self.core, OWNERS[0], frames)

    def test_incomplete_seed_manifest_and_export_hash_mismatch_fail_closed(self):
        import bmc_allpass_oscillator as oscillator
        initialize = oscillator.initialize
        def missing_seed(*args):
            ring, coefficients, seed = initialize(*args)
            seed['initial_data'].pop(0x21)
            return ring, coefficients, seed
        with patch('fantom_voice_plan.oscillator.initialize', side_effect=missing_seed):
            with self.assertRaisesRegex(ValueError, 'read-before-write'):
                build_plan(self.core, OWNERS[0])
        fragments, result = build_plan(self.core, OWNERS[0])
        changed = copy.deepcopy(result)
        changed['logical_sha256'] = '0'*64
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'plan'
            with self.assertRaisesRegex(ValueError, 'verified plan hashes'):
                write_plan(output, fragments, changed)
            self.assertFalse(output.exists())

    @unittest.skipUnless(hasattr(math, 'fma'), 'Python 3.13+ math.fma required')
    def test_cli_exports_only_original_body_and_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'voice-plan'
            command = [sys.executable, str(ROOT/'tools/fantom_voice_plan.py'),
                       str(CORPUS/'b0c1a.bin'), str(output)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertIsNone(result['load_address'])
            self.assertEqual({path.name for path in output.iterdir()},
                             {'body-logical.bin', 'body-stored.bin', 'manifest.json'})
            logical = (output/'body-logical.bin').read_bytes()
            self.assertEqual(len(logical), 200)
            self.assertEqual(swap_words((output/'body-stored.bin').read_bytes()), logical)
            self.assertEqual(json.loads((output/'manifest.json').read_text()), result)
            before = {path.name: path.read_bytes() for path in output.iterdir()}
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
