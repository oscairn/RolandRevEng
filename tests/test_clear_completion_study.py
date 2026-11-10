import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from clear_completion_study import external_irq, report


class IdentityTests(unittest.TestCase):
    def test_vector_identity_does_not_use_event_number(self):
        self.assertEqual(external_irq(0x01100180, 0x01131621), 80)
        for address, handler in ((0x0110003c, 1), (0x01100181, 1),
                                 (0x01100180, 0x01131620)):
            with self.assertRaises(ValueError):
                external_irq(address, handler)

    def test_unknown_build_rejected_before_address_reads(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            report(SimpleNamespace(data=b'unknown image'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                     'Capstone and local Fantom artifact required')
class CorpusTests(unittest.TestCase):
    def test_registration_vector_and_initialization_join(self):
        from core1 import Core1
        result = report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual((result['event'], result['irq'], result['callback_slot']),
                         (23, 80, 0x200a1900))
        self.assertEqual(result['enable_store']['value'], 1 << (80 % 32))
        self.assertTrue(result['event_mask_or']['value'] & (1 << result['event']))
        self.assertEqual(result['initial_flag'], 0)
        self.assertTrue(result['one_address_step_per_32bit_cpu_element'])
        self.assertFalse(result['bulk_clear_count_unit_proven'])
        self.assertFalse(result['execution_ready'])


if __name__ == '__main__':
    unittest.main()
