from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from core1_sysex import inspect


class Core1SysExTests(unittest.TestCase):
    def test_asymmetric_high_bit_group_and_word_order(self):
        # Original synthetic record: high bits belong to bytes 0 and 2.
        self.assertEqual(inspect(bytes.fromhex('f041600a01522334f7')),
                         dict(form='internal_word', word_le=0x34a35281,
                              word_bytes='8152a334', word_high_nibble=8,
                              word_byte1=0x52, word_upper16=0x34a3))

    def test_mmio_reply_address_nibbles_and_checksum(self):
        # Synthetic reply at offset 0x1234 with two asymmetric 32-bit values.
        data = bytes.fromhex('f041104e13000024340102030405060708090a0b0c0d0e0f0030f7')
        self.assertEqual(inspect(data),
                         dict(form='debug_mmio_read_reply', offset=0x1234,
                              address=0x41101234, byte_count=8,
                              words=[0x12345678, 0x9abcdef0]))

    def test_unsupported_and_malformed_records_fail_closed(self):
        word = bytes.fromhex('f041600a01522334f7')
        reply = bytes.fromhex('f041104e13000024340102030405060708090a0b0c0d0e0f0030f7')
        for data in (b'', word[:-1], word + word, word[:3] + b'\x10' + word[4:],
                     word[:4] + b'\x80' + word[5:],
                     word[:2] + b'\x50' + word[3:],
                     reply[:-2] + b'\x71\xf7', reply[:10] + b'\xf7',
                     reply[:9] + b'\x10' + reply[10:],
                     bytes.fromhex('f041104e130000000000f7')):
            with self.subTest(data=data.hex()), self.assertRaises(ValueError):
                inspect(data)

    def test_reply_upper_bound_and_nonzero_address_high_group(self):
        prefix = bytes.fromhex('f041104e130f7f7f7c')
        for count in (16, 17):
            body = prefix + bytes(8 * count)
            data = body + bytes([-sum(body[5:]) & 127, 0xf7])
            if count == 16:
                row = inspect(data)
                self.assertEqual((row['offset'], row['address'], row['byte_count']),
                                 (0x1fffffc, 0x430ffffc, 64))
            else:
                with self.assertRaises(ValueError):
                    inspect(data)


if __name__ == '__main__':
    unittest.main()
