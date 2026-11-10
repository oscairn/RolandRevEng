from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from qspi_c1 import parse_c1


def container():
    data = bytearray(0x100)
    data[0x20:0x24] = b'QSPI'
    struct.pack_into('<3I', data, 0x24, 32, 32, 2)
    for i, (name, payload) in enumerate(((b'idm1.bin', b'12345678'), (b'sdram1.bin', b'abcdefgh'))):
        offset = 0x80 + i*0x40
        member = bytes(32)+payload
        entry = 0x30+i*32
        data[entry:entry+len(name)] = name
        struct.pack_into('<4I', data, entry+16, offset, len(member), 0, 0)
        data[offset:offset+len(member)] = member
    struct.pack_into('<I', data, 0, len(data)+4)
    return bytes(data)+struct.pack('<I', zlib.crc32(data))+b'Roland TEST C1A'.ljust(48, b' ')


def repair_crc(data):
    data = bytearray(data)
    struct.pack_into('<I', data, len(data)-52, zlib.crc32(data[:-52]))
    return bytes(data)


class QspiC1Tests(unittest.TestCase):
    def test_original_ranges_and_synthetic_gap_free_view(self):
        manifest, view = parse_c1(container())
        self.assertEqual(view, b'12345678abcdefgh')
        self.assertFalse(manifest['analysis_view_is_original'])
        self.assertEqual([(r['runtime_base'], r['source_offset'], r['size'], r['analysis_offset'])
                         for r in manifest['regions']],
                         [(0x01100000, 0xa0, 8, 0), (0x61000000, 0xe0, 8, 8)])
        self.assertTrue(manifest['footer_crc32_valid'])
        self.assertFalse(manifest['members'][0]['additive_u16_matches'])

    def test_bad_crc_header_names_ranges_prefix_and_overlap_rejected(self):
        original = container()
        corrupt = bytearray(original);corrupt[0xa0] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC32'):
            parse_c1(corrupt)
        changes = [(0x28, struct.pack('<I', 16)), (0x30, b'../x\0'),
                   (0x40, struct.pack('<I', 0x38)), (0x44, struct.pack('<I', 0x10000)),
                   (0x60, struct.pack('<I', 0x80)), (0x80, b'\1')]
        for address, replacement in changes:
            bad = bytearray(original);bad[address:address+len(replacement)] = replacement
            with self.subTest(address=address), self.assertRaises(ValueError):
                parse_c1(repair_crc(bad))
        with self.assertRaises(ValueError):
            parse_c1(original[:-1])


if __name__ == '__main__':
    unittest.main()
