import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from core1_service_audit import audit, decoded_count, prel32_entries, reply_frame


class ServiceAuditTests(unittest.TestCase):
    def test_prel32_displacements_and_thumb_bit(self):
        words = {0x1000: 0xfffff001, 0x1004: 0x2001}
        self.assertEqual(prel32_entries(words.__getitem__, 0x1000, 0x1008), [
            dict(index=0, slot=0x1000, thumb_pointer=1),
            dict(index=1, slot=0x1004, thumb_pointer=0x3005)])
        with self.assertRaises(ValueError):
            prel32_entries(lambda _: 0, 0x1000, 0x1004)

    def test_table_bounds_fail_closed(self):
        for start, end in ((0, 0), (4, 0), (1, 5), (-4, 4), (0, 4100),
                           (0xfffffffc, 0x100000000)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                prel32_entries(lambda _: 1, start, end)

    def test_count_bfi_chain_cannot_set_sign_bit(self):
        self.assertEqual(decoded_count([0xff] * 4), 0x0fffffff)
        self.assertEqual(decoded_count([1, 2, 3, 4]), 0x208184)
        self.assertEqual(decoded_count([0x81, 0x82, 0x83, 0x84]), 0x208184)
        self.assertEqual(decoded_count([0, 0, 0, 0x80]), 0)
        for bad in ([], [0] * 3, [0] * 5, [256, 0, 0, 0], [-1, 0, 0, 0]):
            with self.assertRaises(ValueError):
                decoded_count(bad)

    def test_exact_frame_boundaries_and_remainders(self):
        self.assertEqual(reply_frame(3)['emitted'], 0)
        for n in (32, 33, 34, 35):
            self.assertEqual(reply_frame(n)['emitted'], 75)
            self.assertNotIn('saved_r4', reply_frame(n)['overlap'])
        self.assertEqual(reply_frame(36)['overlap']['saved_r4'], [80, 83])
        self.assertNotIn('saved_lr', reply_frame(36)['overlap'])
        result = reply_frame(40)
        self.assertEqual((result['data'], result['checksum'], result['terminator']),
                         ([9, 89], 89, 90))
        self.assertEqual(result['overlap']['saved_lr'], [84, 88])
        self.assertEqual(result['overlap']['caller'], [88, 91])
        self.assertEqual(reply_frame(64)['emitted'], 139)
        self.assertEqual(reply_frame(0x0fffffff)['emitted'], 139)
        for n in (-1, 1 << 28, 4.5):
            with self.assertRaises(ValueError):
                reply_frame(n)

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_unknown_build_rejected_before_address_access(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported CORE1'):
            audit(SimpleNamespace(data=b'not a supported firmware'))

    @unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone is not installed')
    def test_optional_local_corpus(self):
        from core1 import Core1
        inputs = [ROOT / 'local' / name for name in ('b0c1a.bin', 'b1c1a.bin')]
        if not all(path.exists() for path in inputs):
            self.skipTest('Local vendor inputs are absent')
        results = [audit(Core1(path)) for path in inputs]
        self.assertEqual([r['initializer_table']['count'] for r in results], [89, 91])
        self.assertEqual([r['initializer_table']['receiver_entry']['index']
                          for r in results], [67, 70])
        self.assertEqual([r['receivers'][0]['object'] for r in results],
                         [0x20094ee4, 0x200993a8])
        self.assertEqual([r['receivers'][0]['callback_thumb'] for r in results],
                         [0x01135de1, 0x011362b1])


if __name__ == '__main__':
    unittest.main()
