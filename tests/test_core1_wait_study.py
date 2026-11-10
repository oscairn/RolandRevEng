import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from core1_wait_study import compare_target, expand_initial_data, report, scaled_count, wait_chunks


class WaitTests(unittest.TestCase):
    def test_only_last_chunk_can_remain_pending(self):
        self.assertEqual(list(wait_chunks(0, 1)), [])
        self.assertEqual(list(wait_chunks(0xffff, 0)),
                         [dict(count=0xfffe, wait=True), dict(count=1, wait=False)])
        self.assertEqual(list(wait_chunks(0xffff, 1)),
                         [dict(count=0xfffe, wait=True), dict(count=1, wait=True)])
        chunks = list(wait_chunks(0xffffffff, 0))
        self.assertEqual(sum(row['count'] for row in chunks), 0xffffffff)
        self.assertTrue(all(row['wait'] for row in chunks[:-1]))
        self.assertFalse(chunks[-1]['wait'])

    def test_store_arithmetic_and_scaled_signed_overflow(self):
        self.assertEqual(compare_target(10, 0), 11)
        self.assertEqual(compare_target(0xffffffff, 1), 1)
        self.assertEqual(compare_target(5, 0xffffffff), 5+0xfffe+1)
        self.assertEqual(scaled_count(1000), 48000)
        self.assertEqual(scaled_count(44739), 2147472)
        self.assertEqual(scaled_count(44740), (-2147447) & 0xffffffff)
        self.assertEqual(scaled_count(0xffffffff), (-48) & 0xffffffff)
        for invalid in (-1, 1 << 32, 1.5):
            with self.assertRaises(ValueError):
                list(wait_chunks(invalid, 0))

    def test_compressed_literals_zeros_extensions_and_overlapping_copy(self):
        self.assertEqual(expand_initial_data(bytes([0x10, 3, 65, 66]), 3), (b'AB\0', 4))
        self.assertEqual(expand_initial_data(bytes([0, 2, 3, 88]), 4), (b'X\0\0\0', 4))
        self.assertEqual(expand_initial_data(bytes([2, 0, 65, 0x29, 1, 99]), 5), (b'AAAAA', 5))

    def test_compressed_bounds_and_unknown_build_fail_closed(self):
        for data, size in ((b'', 0), (b'', 1), (bytes([0]), 1), (bytes([0, 0, 1]), 1),
                           (bytes([0x29, 1]), 4), (bytes([2, 0, 65, 0x29, 0]), 5),
                           (bytes([0x21]), 1), (bytes([0x10, 3, 65, 66]), 1)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                expand_initial_data(data, size)
        with self.assertRaisesRegex(ValueError, 'digest'):
            report(SimpleNamespace(data=b'unrecognized firmware'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                     'Capstone and local CORE1 artifact required')
class CorpusTests(unittest.TestCase):
    def test_pinned_initial_data_and_irq(self):
        from core1 import Core1
        result = report(Core1(CORPUS / 'b0c1a.bin'))
        self.assertEqual(result['compressed_bytes_used'], 0x1f43)
        self.assertEqual(result['initial_data_sha256'],
                         '9a35747f56872b1f2f81bd375c17a57fd2f17a4b00b4ed6cdcd460f2b067bca8')
        self.assertEqual((result['initial_done'], result['initial_registered']), (1, 0))
        self.assertEqual(result['irq91_handler'], 0x01103470)


if __name__ == '__main__':
    unittest.main()
