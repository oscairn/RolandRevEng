from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from bmc_ipc import frames


class IpcTests(unittest.TestCase):
    def test_original_inline_example_and_little_endian_word(self):
        # Synthetic routing bytes and MIDI-style payload; no captured device traffic.
        data = bytes.fromhex('0660e1000b923456aabbcc04')
        row, = frames(data)
        self.assertEqual(row, dict(offset=0, size=12, kind=3, variable=False,
                                  prefix=data.hex(), payload='0b923456', word_le=0x5634920b))

    def test_variable_and_concatenated_frames(self):
        prefix = bytes.fromhex('13610100123456789abcdef0')
        variable = prefix + struct.pack('<I', 3) + b'abc'
        empty = bytes(12)
        rows = list(frames(variable + empty))
        self.assertEqual((rows[0]['kind'], rows[0]['size'], rows[0]['payload']), (9, 19, '616263'))
        self.assertTrue(rows[0]['variable'])
        self.assertEqual((rows[1]['offset'], rows[1]['payload']), (19, ''))
        self.assertEqual(list(frames(b'')), [])

    def test_truncation_and_unknown_layout_fail_without_resynchronizing(self):
        fixed = bytes.fromhex('0660e1000b923456aabbcc04')
        variable = bytes.fromhex('130000000000000000000000') + struct.pack('<I', 3) + b'abc'
        for data in (fixed[:11], variable[:13], variable[:-1],
                     fixed[:-1] + b'\x08', b'\x14' + fixed[1:],
                     variable[:12] + b'\xff\xff\xff\xff'):
            with self.subTest(data=data.hex()), self.assertRaises(ValueError):
                list(frames(data))


if __name__ == '__main__':
    unittest.main()
