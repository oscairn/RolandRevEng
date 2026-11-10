from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from core1_rtti import trace, word_refs


class RttiTests(unittest.TestCase):
    def test_only_aligned_pointer_refs_and_bounded_callback_run(self):
        data = bytearray(512)
        name = b'4Test\0'
        data[0x100:0x100 + len(name)] = name
        base = 0x61000000
        struct.pack_into('<II', data, 0x20, base + 8, base + 0x100)
        struct.pack_into('<IIII', data, 0x60, 0, base + 0x20, base + 0x81, base + 0x91)
        struct.pack_into('<I', data, 0x70, base + 0x9001)  # Out-of-image pointer stops the run.
        def offset(address):
            if not base <= address < base + len(data):
                raise ValueError('Not image-backed')
            return address - base
        core = SimpleNamespace(data=bytes(data), address=lambda value: base + value, offset=offset)
        result = trace(core, '4Test')['candidates']
        self.assertEqual(result, [dict(typeinfo=base + 0x20, vtable=base + 0x60,
                                      thumb_callback_candidates=[base + 0x81, base + 0x91])])
        self.assertEqual(word_refs(b'\0\x01\x02\x03\x04', 0x04030201), [])

    def test_missing_or_duplicate_name_fails(self):
        for data in (b'none\0', b'4Test\0 4Test\0'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                trace(SimpleNamespace(data=data), '4Test')


if __name__ == '__main__':
    unittest.main()
