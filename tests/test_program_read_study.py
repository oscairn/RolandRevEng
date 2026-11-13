import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from program_read_study import read_geometry, read_literal_raw, report

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists()


class GeometryTests(unittest.TestCase):
    def test_word_aligned_body_matches_the_write_path_mirror(self):
        plan = read_geometry(4, 0x4020, 510)
        self.assertEqual(plan['aperture'], 0x41880000)
        self.assertEqual(plan['port_command'], 0x20004020)
        self.assertEqual(plan['words_returned'], 128)
        self.assertEqual([(s['kind'], s['source'], s['source_read_bytes'], s['words_returned'])
                          for s in plan['steps']],
                         [('full_word_tail', 0x4020 + 508, 4, 1),
                          ('dma_queue', 0x4020, 508, 127)])
        self.assertEqual(plan['steps'][0]['bytes_beyond_count'], 2)
        self.assertEqual(plan['descriptors'], [dict(word_count=127)])

    def test_word_plus_two_address_leads_with_a_raw_head(self):
        plan = read_geometry(5, 0x4022, 6)
        self.assertEqual([(s['kind'], s['source']) for s in plan['steps']],
                         [('raw_head', 0x4022), ('cpu_copy', 0x4024)])
        self.assertEqual([s['source_read_bytes'] for s in plan['steps']], [2, 4])

    def test_small_counts_stay_on_the_cpu_loop_and_reject_odd_inputs(self):
        self.assertEqual(read_geometry(0, 0x40, 60)['steps'][-1]['kind'], 'cpu_copy')
        # The threshold applies to the remainder after the tail word: 62 leaves
        # 60 on the CPU loop, 64 queues all 64 bytes.
        self.assertEqual(read_geometry(0, 0x40, 62)['steps'][-1]['kind'], 'cpu_copy')
        self.assertEqual(read_geometry(0, 0x40, 62)['steps'][0]['kind'], 'full_word_tail')
        self.assertEqual(read_geometry(0, 0x40, 64)['steps'][0]['kind'], 'dma_queue')
        for args in ((4, 0x4021, 510), (4, 0x4020, 509), (7, 0x4020, 4),
                     (4, 0x4020, 0x80000), (4, 0x4020, 0x80002),
                     (4, 0x4022, 66)):
            with self.assertRaises(ValueError, msg=str(args)):
                read_geometry(*args)


class LiteralTests(unittest.TestCase):
    def test_widths_two_three_four_only_and_alignment_shift(self):
        self.assertEqual(read_literal_raw(4, 0x4021, 2, False)['alignment_shift_bits'], 0)
        self.assertEqual(read_literal_raw(4, 0x4021, 3, True)['alignment_shift_bits'], 8)
        self.assertEqual(read_literal_raw(4, 0x4021, 4, True)['alignment_shift_bits'], 0)
        for width in (0, 1, 5):
            with self.assertRaises(ValueError):
                read_literal_raw(4, 0x4021, width, False)


@unittest.skipUnless(HAS_CORPUS, 'Pinned Fantom CORE1 and Capstone required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.core = Core1(str(CORPUS / 'b0c1a.bin'))

    def test_report_pins_every_annotated_anchor_and_port_word(self):
        result = report(self.core)
        self.assertEqual(result['payload_sha256'], hashlib.sha256(self.core.data).hexdigest())
        self.assertEqual(result['functions']['ReadDspProg'], 0x0112f74c)
        self.assertEqual(result['functions']['ReadLiteralRaw'], 0x0112f6e8)
        self.assertFalse(result['execution_ready'])

    def test_read_and_write_share_one_aperture_table(self):
        from program_write_study import APERTURES
        for index, aperture in enumerate(APERTURES):
            self.assertEqual(self.core.u32(0x113a954 + 4 * index), aperture)

    def test_mute_scan_and_two_manager_paths_call_read_literal_raw(self):
        expected = {0x01133bb4, 0x01133bda, 0x01133220, 0x01133698}
        found = set()
        for offset in range(0, self.core.eram_offset - 3, 2):
            first = struct.unpack_from('<H', self.core.data, offset)[0]
            if first & 0xf800 != 0xf000:
                continue
            ins = next(self.core.md.disasm(self.core.data[offset:offset + 4],
                                           0x01100000 + offset, count=1), None)
            if ins and ins.mnemonic == 'bl' and ins.operands[0].imm == 0x0112f6e8:
                found.add(ins.address)
        self.assertEqual(found, expected)

    def test_read_dspprog_has_no_direct_or_veneer_caller(self):
        from core1_xrefs import references
        empty = references(self.core, 0x0112f74c)
        self.assertEqual(empty['direct_branch_candidates'], [])
        self.assertEqual(empty['movw_movt_bx_candidates'], [])
        self.assertEqual(empty['aligned_thumb_pointer_candidates'], [])

    def test_report_fails_closed_on_a_one_bit_flip(self):
        import tempfile
        from program_write_study import APERTURES  # noqa: F401  pins the import contract
        data = bytearray(self.core.data)
        # Flip one byte of the raw port table word for DSP 4.
        offset = self.core.offset(0x113aa74 + 16)
        data[offset] ^= 1
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as handle:
            handle.write(bytes(data))
        try:
            from core1 import Core1
            mutated = Core1(handle.name)
            with self.assertRaises(ValueError):
                report(mutated)
        finally:
            os.unlink(handle.name)

    def test_sample_read_output_is_stable_json(self):
        from program_read_study import READ_PORT_COMMAND
        plan = read_geometry(4, 0x4020, 510)
        self.assertEqual(json.loads(json.dumps(plan))['port_command'],
                         READ_PORT_COMMAND | (0x4020 & 0x7ffff))


if __name__ == '__main__':
    unittest.main()