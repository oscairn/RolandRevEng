import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from qctest_shell_study import direct_callers, report


class BranchTests(unittest.TestCase):
    def test_forward_backward_and_indirect_exclusion(self):
        # BL +8, B +4, BL -8 all target 0x1008; BR x0 is not a direct edge.
        words = [0x94000002, 0x14000001, 0xd61f0000, 0x94000000, 0x97fffffe]
        code = struct.pack('<5I', *words)
        self.assertEqual(direct_callers(code, 0x1000, 0x1008), [0x1000, 0x1004, 0x1010])
        with self.assertRaises(ValueError):
            direct_callers(code+b'\0', 0x1000, 0x1008)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and importlib.util.find_spec('elftools')
                     and (CORPUS/'qctest').exists(), 'Recorded ELF and installed disassemblers required')
class CorpusTests(unittest.TestCase):
    def test_endpoint_keeps_activation_unresolved(self):
        data = (CORPUS/'qctest').read_bytes()
        result = report(data)
        self.assertEqual(result['gate']['required'], 3)
        self.assertEqual(result['gate']['direct_setter_values'], [0, 1, 2])
        self.assertEqual(result['gate']['file_initial'], -1)
        self.assertFalse(result['activation_proven'])
        self.assertIsNone(result['runtime_uid'])
        with self.assertRaises(ValueError):
            report(data[:-1])


if __name__ == '__main__':
    unittest.main()
