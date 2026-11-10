import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from coefficient_env_study import control_fields,firmware_report,native_report


class ControlTests(unittest.TestCase):
    def test_selector_is_separate_from_wait_event_and_operating_state(self):
        row=control_fields(0xa9b00000)
        self.assertEqual((row['event_ref'],row['mode_field'],row['wait_bit'],row['time_selector']),
                         (10,2,1,11))
        self.assertFalse(row['operating_predicate'])
        self.assertTrue(control_fields(0xadb00000)['operating_predicate'])
        self.assertFalse(control_fields(0xafb00000)['operating_predicate'])
        for bad in (-1,1<<32,True,1.5):
            with self.assertRaises(ValueError):control_fields(bad)

    def test_unknown_artifacts_fail_before_address_access(self):
        with self.assertRaisesRegex(ValueError,'Unsupported CORE1'):
            firmware_report(SimpleNamespace(data=b'authored unrelated firmware'))
        with self.assertRaisesRegex(ValueError,'Unsupported native'):
            native_report(b'authored unrelated native data')


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))


class CorpusTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                         'Capstone and retained CORE1 required')
    def test_driver_manager_and_six_completion_routes(self):
        from core1 import Core1
        row=firmware_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([r['irq'] for r in row['interrupts']],list(range(65,71)))
        self.assertEqual(row['exclusion_byte'],0x2008480f)
        self.assertEqual(row['selector_count'],16)
        self.assertFalse(row['hardware_timing_verified'])
        self.assertFalse(row['owner_offset_bounds_proven'])

    @unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'zen_arm64').exists(),
                         'Capstone and retained native artifact required')
    def test_native_selector_timing_is_not_hardware_measurement(self):
        row=native_report((CORPUS/'zen_arm64').read_bytes())
        self.assertEqual(row['selector10_nominal_ms'],12.0)
        self.assertEqual(row['native_rate_constant'],44100.0)
        self.assertTrue(row['native_manager_operating_returns_false'])
        self.assertFalse(row['hardware_timing_verified'])


if __name__=='__main__':unittest.main()
