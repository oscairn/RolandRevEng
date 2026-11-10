import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
sys.path.insert(0, str(ROOT / 'tools'))
from core1_task_context_study import nvic_lines, priority_byte, report


class ContextTests(unittest.TestCase):
    def test_priority_radix_and_nvic_bank_edges(self):
        self.assertEqual([priority_byte(n) for n in (10, 18, 20)], [0x50, 0x90, 0xa0])
        self.assertEqual(nvic_lines(31)['bit'], 0x80000000)
        self.assertEqual(nvic_lines(32)['enable_address'], 0xe000e104)
        self.assertEqual(nvic_lines(32)['bit'], 1)
        self.assertEqual(nvic_lines(231)['disable_address'], 0xe000e19c)
        self.assertEqual(nvic_lines(231)['bit'], 0x80)
        for value in (-1, 32, 1.5):
            with self.assertRaises(ValueError):
                priority_byte(value)
        for value in (-1, 240, 1.5):
            with self.assertRaises(ValueError):
                nvic_lines(value)

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_unknown_image_rejected_before_address_access(self):
        with self.assertRaisesRegex(ValueError, 'digest'):
            report(SimpleNamespace(data=b'unrecognized'))

    @unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                         'Capstone and local CORE1 image required')
    def test_actual_registration_vectors_and_slots(self):
        from core1 import Core1
        result = report(Core1(CORPUS / 'b0c1a.bin'))
        self.assertEqual([(t['name'], t['irq'], t['callback_slot']) for t in result['tasks']],
                         [('RXDT', 231, 0x20084964), ('ASGN', 233, 0x2008496c)])
        self.assertEqual([t['handler'] for t in result['tasks']], [0x0110216c, 0x011021cc])


if __name__ == '__main__':
    unittest.main()
