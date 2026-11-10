import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from core0_ciphertext_study import INPUTS, payload_blocks, report, reported_entry_address


def container(payload, trailer=b''):
    data = bytearray(96)
    data[:9] = b'App1_Main'
    struct.pack_into('<I', data, 0x44, len(payload))
    struct.pack_into('<I', data, 0x54, 0xb6020001)
    return bytes(data)+payload+trailer


class CiphertextTests(unittest.TestCase):
    def test_exact_payload_boundary_duplicates_and_trivial_blocks(self):
        payload = struct.pack('<5Q', 0x123456789abcdef0, 0, 0xffffffffffffffff,
                              0x123456789abcdef0, 7)
        info, blocks = payload_blocks(container(payload, struct.pack('<Q', 99)))
        self.assertEqual(info['payload_offset'], 96)
        self.assertEqual(blocks, {0x123456789abcdef0, 7})
        with self.assertRaises(ValueError):
            payload_blocks(container(payload)[:-1])
        with self.assertRaises(ValueError):
            payload_blocks(container(b'not-eight'))
        changed = bytearray(container(payload));changed[0x54] = 0
        with self.assertRaises(ValueError):
            payload_blocks(changed)

    def test_reported_key_slot_is_only_address_arithmetic(self):
        self.assertEqual(reported_entry_address(0xb6), 0x012034c0)
        self.assertEqual(reported_entry_address(0xb5), 0x012034a8)
        for bad in (-1, 256, 1.5):
            with self.assertRaises(ValueError):
                reported_entry_address(bad)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(all((CORPUS/path).exists() for path, _ in INPUTS.values()),
                     'Six retained CORE0 containers required')
class CorpusTests(unittest.TestCase):
    def test_distinct_shared_counts_and_no_key_claim(self):
        result = report(CORPUS)
        self.assertEqual([row['shared_with_fantom0'] for row in result['images']],
                         [148654, 14335, 10597, 15985, 14858, 8124])
        self.assertFalse(result['key_recovery_claimed'])
        self.assertFalse(result['decryption_performed'])
        self.assertFalse(result['reported_mc101_location']['verified_on_fantom'])


if __name__ == '__main__':
    unittest.main()
