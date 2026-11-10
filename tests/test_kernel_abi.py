import importlib.util
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble, swap_words
from kernel_abi import placements, program_list, read, segment_info


def fixture():
    data = bytearray(512)
    struct.pack_into('<4BI', data, 0, 0, 1, 2, 0, 0x20)
    stream = assemble([[0x1e05, 0x0fe0, 0x4fe2, 0x2016, 0x2017],
                       [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]])
    stored = swap_words(stream + bytes(-len(stream) % 4))
    for index, base in enumerate((0x4000, 0x8000)):
        struct.pack_into('<4I', data, 0x20+16*index, base, len(stream), 32, 0x100)
    data[0x100:0x100+len(stored)] = stored
    struct.pack_into('<IIBB', data, 0x60, 5, 0xc0, 1, 1)
    struct.pack_into('<II', data, 0xc0, 0x8000, 32)
    for offset in (0x18, 0x20, 0x28, 0x30, 0x38, 0x40):
        struct.pack_into('<IB', data, 0x60+offset, 0xd0, 1)
    struct.pack_into('<II', data, 0xd0, 0x47e, 0)
    def offset(address):
        if not 0 <= address < len(data):
            raise ValueError('Unmapped')
        return address
    return SimpleNamespace(data=data, offset=offset)


class LayoutTests(unittest.TestCase):
    def test_context_header_is_not_segment_destination_dsp(self):
        core = fixture()
        program, owner = program_list(core, 0), segment_info(core, 0x60)
        self.assertEqual(program['header_dsp'], 1)
        self.assertEqual(owner['first'], 1)
        self.assertEqual(owner['memories'][1], [dict(base=0x47e, length=0)])
        self.assertEqual(placements(program, owner), [dict(list_index=1, dsp=5,
            destination=0x8000, length=22, capacity=32, source=0x100)])
        self.assertEqual(placements(program, owner, True)[0]['list_index'], 0)
        self.assertEqual(placements(program, owner, True)[0]['destination'], 0x8000)
        segment = program['segments'][0]
        self.assertEqual(segment['framing_controls'], [dict(offset=10, control=0xf8)])
        self.assertEqual([t['operand'] for t in segment['indexed_transfers']],
                         [0x2016, 0x2017, 0x2018, 0x2019])

    def test_capacity_and_unreserved_destination_fail(self):
        core = fixture()
        program, owner = program_list(core, 0), segment_info(core, 0x60)
        owner['render'][0]['capacity'] = 20
        with self.assertRaises(ValueError):
            placements(program, owner)
        owner['render'][0]['capacity'] = 32
        program['segments'][1]['base'] += 2
        with self.assertRaises(ValueError):
            placements(program, owner)
        owner['first'] = 2
        with self.assertRaises(ValueError):
            placements(program, owner)

    def test_unmapped_truncated_and_unsupported_records_fail(self):
        for location, fmt, value in ((0, '<B', 1), (2, '<B', 0), (3, '<B', 1),
                                     (0x24, '<I', 33), (0x24, '<I', 34), (0x2c, '<I', 0x1fc)):
            core = fixture()
            struct.pack_into(fmt, core.data, location, value)
            with self.subTest(location=location), self.assertRaises(ValueError):
                program_list(core, 0)
        core = fixture()
        stream = assemble([[0x0c03, 0x0fee, 0x2016]])
        core.data[0x100:0x108] = swap_words(stream + bytes(2))
        struct.pack_into('<I', core.data, 0x24, len(stream))
        with self.assertRaisesRegex(ValueError, 'Indexed transfer'):
            program_list(core, 0)
        for location, value in ((0x69, 17), (0x6a, 1), (0x7d, 1)):
            core = fixture()
            core.data[location] = value
            with self.subTest(location=location), self.assertRaises(ValueError):
                segment_info(core, 0x60)
        core = fixture()
        for address, size in ((511, 2), (-1, 1), (0, 0)):
            with self.assertRaises(ValueError):
                read(core, address, size)
        discontinuous = SimpleNamespace(data=bytes(16), offset=lambda a: a if a < 8 else a-8)
        with self.assertRaises(ValueError):
            read(discontinuous, 4, 8)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                     'Capstone and local CORE1 artifact required')
class CorpusTests(unittest.TestCase):
    def test_stock_fetdrive_contexts_and_frame_counterexample(self):
        from core1 import Core1
        import hashlib
        core = Core1(CORPUS / 'b0c1a.bin')
        self.assertEqual(hashlib.sha256(core.data).hexdigest(),
                         '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154')
        program = program_list(core, 0x610e7b88)
        owners = [0x610a1674 + i*0x48 for i in range(4)] + [0x610a1d14]
        self.assertEqual([placements(program, segment_info(core, a))[0]['dsp'] for a in owners],
                         [4, 5, 5, 5, 1])
        self.assertEqual([placements(program, segment_info(core, a))[0]['list_index'] for a in owners],
                         [0, 1, 2, 3, 4])
        segment = program['segments'][0]
        self.assertEqual(segment['framing_controls'], [dict(offset=0, control=0xff71),
                         dict(offset=0x1ba, control=0xf8), dict(offset=0x1c6, control=0xff70)])
        self.assertEqual([t['operand'] for t in segment['indexed_transfers'] if t['offset'] == 4],
                         [0x2000, 0x2001])
        routing = program_list(core, 0x610a1f18)
        self.assertEqual(routing['segments'][1]['framing_controls'], [dict(offset=0, control=0xf8)])

    @unittest.skipUnless((CORPUS / 'zen_arm64').exists() and (CORPUS / 'pairs.json').exists(),
                         'Native comparison artifacts required')
    def test_firmware_preserves_native_control_schedule_but_relocates_io(self):
        from bmc_dsp import command_count, packets
        from core1 import Core1
        import parse
        core = Core1(CORPUS / 'b0c1a.bin')
        for cls, address in [('SIM_MFX_FETDRIVE', 0x610e7b88),
                             ('SIM_MFX_LINEDRIVE', 0x611084fc)]:
            length, native, peer, *_ = parse.program(cls)
            program = program_list(core, address)
            first = program['segments'][0]
            start = core.offset(first['source'])
            firmware = swap_words(core.data[start:start + ((length+3) & ~3)])[:length]
            self.assertEqual(first['length'], length)
            def schedule(stream):
                return [(offset, words[:1+command_count(words[0])]) for offset, words in packets(stream)]
            self.assertEqual(schedule(native[:length]), schedule(firmware))
            self.assertEqual([t['operand'] for t in first['indexed_transfers'] if t['offset'] == 4],
                             [0x2000, 0x2001])
            self.assertEqual(packets(native[:length])[1][1][-2:], [0x2016, 0x2017])
            self.assertEqual(packets(peer[:length])[1][1][-2:], [0x2459, 0x245a])
        # The stock setter changes only the mute-mode bit in the first packet's control.
        label = core.data[core.offset(0x610e7b98):core.offset(0x610e7b98)+5]
        self.assertEqual(struct.unpack('<HHB', label), (0x4020, 0, 0))
        self.assertEqual(core.u32(0x6117647c+0xe0), 0x01133b39)


if __name__ == '__main__':
    unittest.main()
