import json
import importlib.util
import math
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble, command_count, encode_literal, literal, packets, swap_words
from prepare_zenology import arm64_slice
from c0_header import header


class PacketTests(unittest.TestCase):
    def test_long_packet_and_compact_forms(self):
        # 8fd1 has seventeen words, not one; 001f occupies one word, not 31.
        rows = [[0x8fd1] + [0] * 16, [0x001f], [0x0001], [0x0a02, 0xff70]]
        stream = assemble(rows)
        self.assertEqual([offset for offset, _ in packets(stream)], [0, 34, 36, 38])
        self.assertEqual([words for _, words in packets(stream)], rows)

    def test_invalid_inputs_do_not_resynchronize(self):
        for stream in (b'\0', b'\0\0', b'\0\x02', bytes.fromhex('1e05 0fe0'), bytes.fromhex('0821')):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                packets(stream)
        with self.assertRaises(ValueError):
            packets(bytes.fromhex('3e03 0fe0 0000'))
        with self.assertRaises(ValueError):
            assemble([[0x1e05, 0]])
        with self.assertRaises(ValueError):
            swap_words(b'123')

    def test_storage_padding(self):
        stream = bytes.fromhex('0a02 ff71 0001')
        stored = swap_words(stream + b'\xa5\x5a')
        self.assertEqual(stored, bytes.fromhex('71ff 020a 5aa5 0100'))
        self.assertEqual(swap_words(stored)[:6], stream)

    def test_control_count(self):
        for header, count in [(1, 0), (31, 0), (0x0c03, 1), (0x1e05, 2),
                              (0x3e07, 3), (0x7809, 4), (0xb809, 5),
                              (0xb84b, 6), (0xb88d, 7), (0x8fd1, 8)]:
            with self.subTest(header=header):
                self.assertEqual(command_count(header), count)

    def test_literal_width_is_explicit(self):
        for encoded, expected in [('3000', 1), ('300000', 1), ('30000000', 1),
                                  ('b00000', -1), ('2fe000', 0.9921875),
                                  ('500000', 16), ('19999999', 0.09999999986030161)]:
            with self.subTest(encoded=encoded):
                self.assertEqual(literal(bytes.fromhex(encoded)), expected)
        with self.assertRaises(ValueError):
            literal(b'\x30')

    def test_literal_encoder_exact_values_quantization_and_overflow(self):
        for width in (2, 3, 4):
            quantum = 2.0 ** (-24 + 8 * (3 - width))
            limit = ((1 << (8 * width - 3)) - 1) * quantum * 4096
            for value in (0, -0.0, 1, -1, 16, -16, limit, -limit):
                with self.subTest(width=width, value=value):
                    self.assertEqual(literal(encode_literal(value, width)), value)
            self.assertEqual(literal(encode_literal(2.5 * quantum, width)), 2 * quantum)
            self.assertEqual(literal(encode_literal(3.5 * quantum, width)), 4 * quantum)
            self.assertEqual(literal(encode_literal(-2.5 * quantum, width)), -2 * quantum)
            self.assertEqual(encode_literal(-quantum / 4, width), bytes(width))
            # Equal-error values straddling two exponents keep the finer one.
            fine_limit = (1 << (8 * width - 3)) - 1
            self.assertEqual(encode_literal((fine_limit + 0.5) * quantum, width),
                             fine_limit.to_bytes(width, 'big'))
            with self.assertRaises(ValueError):
                encode_literal(math.nextafter(limit, math.inf), width)
        for value in (math.nan, math.inf, -math.inf, True, '1', 10 ** 1000):
            with self.subTest(value=repr(value)[:20]), self.assertRaises(ValueError):
                encode_literal(value, 3)
        for width in (True, 1, 5, 3.0):
            with self.assertRaises(ValueError):
                encode_literal(1, width)

    def test_all_two_byte_values_survive_numeric_decode_encode_roundtrip(self):
        for bits in range(0x10000):
            value = literal(bits.to_bytes(2, 'big'))
            self.assertEqual(literal(encode_literal(value, 2)), value)

    def test_rejects_unrelated_macho(self):
        with self.assertRaises(ValueError):
            arm64_slice(b'Not a plugin')

    def test_core0_metadata_and_bounds(self):
        data = bytearray(104)
        data[:9] = b'App1_Main'
        struct.pack_into('<8I', data, 64, 0x60060, 8, 0x60000000, 0, 123, 0xb6020001, 0, 0xffffffff)
        parsed = header(data)
        self.assertEqual((parsed['payload_offset'], parsed['mode'], parsed['key_index']), (96, 2, 0xb6))
        with self.assertRaises(ValueError):
            header(data[:-1])


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     (ROOT / 'local/zenology_inventory.json').exists(),
                     'Capstone and local artifacts required')
class CorpusTests(unittest.TestCase):
    def test_all_discovered_render_segments_round_trip(self):
        import lib
        from analyze import check_segments, core_lists
        from core1 import Core1

        inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
        segments = [(hex(item[0]), *s) for item in inventory['lists'] if item[1] == 0 for s in item[3]]
        result = check_segments(lib.Z, segments)
        self.assertEqual(result['failures'], [])
        self.assertEqual(result['counts']['segments'], 177)
        for filename, expected_count, scatter_count in [('b0c1a.bin', 377, 10), ('b1c1a.bin', 34, 12)]:
            with self.subTest(filename=filename):
                core = Core1(lib.BASE / filename)
                self.assertEqual(core.eram_offset, 0x3ffe0)
                self.assertEqual(len(core.scatter()), scatter_count)
                self.assertEqual(core.offset(core.address(0x15ac7c)), 0x15ac7c)
                segments = [(str(r['payload_offset']), *s) for r in core_lists(core) for s in r['segments']]
                result = check_segments(core.data, segments)
                self.assertEqual(result['failures'], [])
                self.assertEqual(result['counts']['segments'], expected_count)
        core = Core1(lib.BASE / 'b0c1a.bin')
        self.assertEqual([core.u32(0x113a954 + 4 * i) for i in range(7)],
                         [0x41480000, 0x41580000, 0x41680000, 0x41780000,
                          0x41880000, 0x41980000, 0x41260000])


if __name__ == '__main__':
    unittest.main()
