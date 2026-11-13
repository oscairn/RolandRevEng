from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_fantom_core1_rom_reader as reader
from build_fantom_core1_marker import MARKER, check_flat_c1a, read_upa
from fantom_core1_rom_probe import request, decode

STOCK = ROOT / 'local/fantom-07-core1-marker-v108/restore/FNTM0_UPA.BIN'


def reply(words):
    nibbles = [(word >> shift) & 15 for word in words for shift in range(28, -1, -4)]
    return bytes.fromhex('f041104e1300000000') + bytes(nibbles + [-sum(nibbles) & 127, 0xf7])


class ProtocolTests(unittest.TestCase):
    def test_all_requests_keep_stock_count_below_four(self):
        for operation in ('marker', 'snapshot', 'selftest', 'vectors', 'key'):
            packet = request(operation)
            self.assertEqual(len(packet), 15)
            self.assertTrue(all(b < 128 for b in packet[1:-1]))
            self.assertEqual(sum(packet[5:-1]) & 127, 0)
            self.assertEqual(packet[9:12], bytes(3))
            self.assertLess(packet[12], 4)
        for op, channel in (('wrong', 0), ('snapshot', -1), ('snapshot', 8)):
            with self.assertRaises(ValueError):
                request(op, channel)

    def test_key_decode_keeps_bytes_out_of_report(self):
        words = [0x52440701, 0x012034c0] + list(range(6))
        report, data = decode('key', reply(words))
        self.assertEqual(data, struct.pack('<6I', *range(6)))
        self.assertNotIn('words', report)
        self.assertTrue(report['complete'])
        words[0] = 0x52440705
        report, data = decode('key', reply(words))
        self.assertIsNone(data)
        self.assertFalse(report['complete'])
        words[1] = 0x01203500
        with self.assertRaises(ValueError):
            decode('key', reply(words))


@unittest.skipUnless(STOCK.exists() and shutil.which('arm-none-eabi-as'),
                     'Pinned stock corpus and GNU Arm tools required')
class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.stock = read_upa(STOCK.read_bytes())[1][1]
        cls.entry, cls.code, cls.symbols = reader.assemble()
        cls.patched = reader.patch_c1a(cls.stock, cls.entry, cls.code)
        cls.tmp = tempfile.TemporaryDirectory()
        image = Path(cls.tmp.name) / 'reader.bin'
        image.write_bytes(cls.patched)
        cls.core = Core1(image)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_patch_crc_and_protected_initializer(self):
        crc, _ = check_flat_c1a(self.patched)
        self.assertEqual(self.stock[0x3cf28:0x3cf60], self.patched[0x3cf28:0x3cf60])
        self.assertEqual(self.stock[-48:], self.patched[-48:])
        allowed = ((reader.OFFSET, reader.OFFSET + reader.END - reader.ENTRY),
                   (reader.CODE_OFFSET, reader.CODE_OFFSET + reader.CODE_SIZE), (crc, crc + 4))
        self.assertTrue(all(a == b or any(lo <= i < hi for lo, hi in allowed)
                            for i, (a, b) in enumerate(zip(self.stock, self.patched))))
        self.assertLessEqual(len(self.code), reader.CODE_SIZE)
        with self.assertRaises(ValueError):
            reader.patch_c1a(self.stock[:-1], self.entry, self.code)
        with self.assertRaises(ValueError):
            reader.patch_c1a(self.stock, self.entry, bytes(reader.CODE_SIZE + 1))

    def emulate(self, operation, mode='complete', channel=7, payload=None, latched=False, stock=False):
        import unicorn as uc
        from unicorn import arm_const as a
        self.assertEqual(uc.__version__, '2.1.4')
        u = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_THUMB | uc.UC_MODE_MCLASS)
        u.ctl_set_cpu_model(a.UC_CPU_ARM_CORTEX_M7)
        split = self.core.eram_offset
        image = self.stock if stock else self.patched
        for base, data in ((0x01100000, image[32:32 + split]),
                           (0x61000000, image[32 + split:])):
            u.mem_map(base, (len(data) + 4095) & ~4095, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
            u.mem_write(base, data)
        u.mem_protect(0x6102d000, 4096, uc.UC_PROT_ALL)
        u.mem_map(0x20080000, 0x30000, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
        u.mem_map(0x40001000, 4096, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
        u.mem_map(0xe000e000, 4096, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
        u.mem_write(0x40001000, struct.pack('<I', 0 if mode == 'disabled' else 0x80000000))
        u.mem_write(0xe000ed00, struct.pack('<I', 0x410fc241))
        u.mem_write(0xe000ed14, struct.pack('<I', 0x10000 if mode == 'cache' else 0))
        if mode in ('busy', 'skip7'):
            for ch in (range(8) if mode == 'busy' else (7,)):
                u.mem_write(0x40001010 + ch * 16, struct.pack('<I', 0x1234))
        if latched:
            u.mem_write(reader.LATCH, struct.pack('<I', 1))
        sp, ret, arg = 0x200a1000, 0x10000000, 0x2009f330
        u.mem_map(ret, 4096, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
        packet = request(operation, channel) if payload is None else payload
        u.mem_write(arg, struct.pack('<I', len(packet) - 5) + packet[5:])
        queue, words = 0x2008203c, 0x20095f0c
        u.mem_write(queue, struct.pack('<6I', 0, 0, 512, 512, 0, 0))
        regs = [getattr(a, 'UC_ARM_REG_R' + str(i)) for i in range(4, 12)]
        saved = [0x12340000 + i for i in range(8)]
        for reg, value in zip(regs, saved):
            u.reg_write(reg, value)
        u.reg_write(a.UC_ARM_REG_SP, sp)
        u.reg_write(a.UC_ARM_REG_LR, ret | 1)
        u.reg_write(a.UC_ARM_REG_R0, arg)
        u.reg_write(a.UC_ARM_REG_PRIMASK, 0)
        state = dict(complete=False, packets=[], triggers=[], writes=[], pending=None, signals=[])
        fake_rom = {0x01200000: 0x01060000, 0x01200004: 0x012000d1,
                    **{0x012034c0 + i * 4: 0x10101010 + i for i in range(6)}}

        def word(addr):
            return struct.unpack('<I', u.mem_read(addr, 4))[0]

        def write_hook(cpu, access, addr, size, value, _):
            allowed = ((sp - 4096, sp), (queue, queue + 24), (words, words + 2048),
                       (reader.LATCH, reader.LATCH + 4), (reader.BOUNCE, reader.BOUNCE + 128),
                       (0x40001010, 0x40001090))
            self.assertTrue(any(lo <= addr and addr + size <= hi for lo, hi in allowed),
                            f'Unexpected CPU write {addr:#x}')
            state['writes'].append((addr, size, value))
            if 0x40001010 <= addr < 0x40001090 and (addr - 0x40001010) % 16 == 0 and value & 0x80000000:
                self.assertEqual(value, 0xa0000000)
                self.assertEqual(word(addr + 4), 0x08000000)
                self.assertEqual(word(addr + 12), reader.BOUNCE)
                source = word(addr + 8)
                expected = ([reader.PATTERN] if operation == 'selftest' else
                            [0x01200000, 0x01200004] if operation == 'vectors' else
                            [0x012034c0 + i * 4 for i in range(6)])
                self.assertIn(source, expected)
                state['triggers'].append((addr, source, word(addr + 12)))
                state['pending'] = addr

        def code_hook(cpu, pc, size, _):
            self.assertTrue(sp - 4096 <= cpu.reg_read(a.UC_ARM_REG_SP) <= sp)
            if pc == ret:
                state['complete'] = True
                cpu.emu_stop()
            elif pc == 0x011020c0:
                state['signals'].append(cpu.reg_read(a.UC_ARM_REG_R0))
                cpu.reg_write(a.UC_ARM_REG_PC, cpu.reg_read(a.UC_ARM_REG_LR))
            elif pc == 0x0111f0be:
                pointer, count = (cpu.reg_read(r) for r in (a.UC_ARM_REG_R0, a.UC_ARM_REG_R1))
                self.assertIn(count, (19, 75))
                self.assertEqual(cpu.reg_read(a.UC_ARM_REG_SP) % 8, 0)
                state['packets'].append(bytes(cpu.mem_read(pointer, count)))
            elif pc == self.symbols['dma_poll'] and state['pending'] is not None and mode != 'timeout':
                base = state['pending']
                source = word(base + 8)
                value = word(reader.PATTERN) if source == reader.PATTERN else fake_rom[source]
                if mode == 'wrongdata':
                    value ^= 1
                cpu.mem_write(reader.BOUNCE, struct.pack('<I', value))
                if mode == 'canary':
                    cpu.mem_write(reader.BOUNCE + 4, b'bad!')
                advance = 8 if mode == 'count' else 4
                for addr, val in ((base, 0x20000000), (base + 4, 0x08010000 if mode == 'error' else 0x08050000),
                                  (base + 8, source + advance), (base + 12, reader.BOUNCE + advance)):
                    cpu.mem_write(addr, struct.pack('<I', val))
                state['pending'] = None

        u.hook_add(uc.UC_HOOK_CODE, code_hook)
        u.hook_add(uc.UC_HOOK_MEM_WRITE, write_hook)
        # Real ROM is deliberately unmapped; only the fake DMA model sees its bytes.
        u.emu_start(reader.ENTRY | 1, ret + 2, count=180000)
        self.assertTrue(state['complete'], 'Instruction budget exhausted')
        self.assertEqual(u.reg_read(a.UC_ARM_REG_SP), sp)
        self.assertEqual([u.reg_read(r) for r in regs], saved)
        self.assertEqual(u.reg_read(a.UC_ARM_REG_PRIMASK), 0)
        state['latch'] = word(reader.LATCH)
        state['dma_global'] = word(0x40001000)
        state['channels'] = bytes(u.mem_read(0x40001010, 128))
        return state

    def test_marker_snapshot_and_invalid_requests_never_program_dma(self):
        state = self.emulate('marker')
        self.assertEqual(state['packets'], [MARKER])
        self.assertEqual(state['triggers'], [])
        for ch in (0, 7):
            state = self.emulate('snapshot', channel=ch)
            result, _ = decode('snapshot', state['packets'][0], ch)
            self.assertEqual(result['registers']['cpuid'], 0x410fc241)
            self.assertEqual(state['triggers'], [])
            self.assertFalse(any(0x40001000 <= addr < 0x40002000 for addr, _, _ in state['writes']))
        state = self.emulate('snapshot', mode='skip7', channel=7)
        self.assertEqual(decode('snapshot', state['packets'][0], 7)[0]['registers']['channel_a'], 0x1234)
        for index in (5, 9, 13, 14):
            bad = bytearray(request('vectors'))
            bad[index] ^= 1
            state = self.emulate('vectors', payload=bytes(bad))
            self.assertEqual(state['packets'], [])
            self.assertEqual(state['triggers'], [])

    def test_every_diagnostic_request_is_readless_on_the_stock_helper(self):
        for operation in ('marker', 'snapshot', 'selftest', 'vectors', 'key'):
            state = self.emulate(operation, stock=True)
            self.assertEqual(state['packets'], [])
            self.assertEqual(state['triggers'], [])

    def test_successful_selftest_vectors_and_key_are_word_bounded(self):
        for operation, count in (('selftest', 1), ('vectors', 2), ('key', 6)):
            state = self.emulate(operation)
            self.assertEqual(len(state['triggers']), count)
            result, data = decode(operation, state['packets'][0])
            self.assertTrue(result['complete'])
            self.assertEqual(result['channel'], 7)
            self.assertEqual(len(data), count * 4)
            self.assertEqual(state['latch'], 0)
            self.assertEqual(state['channels'], bytes(128))
            self.assertEqual(state['dma_global'], 0x80000000)
            self.assertEqual(state['signals'], [2] * 25)

    def test_disabled_cache_busy_and_latch_do_not_start_dma(self):
        for mode, code in (('disabled', 2), ('cache', 4), ('busy', 3)):
            state = self.emulate('vectors', mode=mode)
            result, data = decode('vectors', state['packets'][0])
            self.assertEqual(result['status'], code)
            self.assertIsNone(data)
            self.assertEqual(state['triggers'], [])
        state = self.emulate('vectors', latched=True)
        self.assertEqual(decode('vectors', state['packets'][0])[0]['status'], 8)
        self.assertEqual(state['triggers'], [])

    def test_errors_stop_and_latch_without_exposing_a_complete_result(self):
        for mode, code in (('timeout', 5), ('error', 6), ('canary', 7), ('count', 9), ('wrongdata', 10)):
            state = self.emulate('selftest', mode=mode)
            result, data = decode('selftest', state['packets'][0])
            self.assertEqual(result['status'], code)
            self.assertIsNone(data)
            self.assertEqual(state['latch'], 1)
            self.assertEqual(len(state['triggers']), 1)
            ca, cb, source, destination = struct.unpack('<4I', state['channels'][112:128])
            self.assertEqual(ca & 0x80000000, 0)
            if mode == 'timeout':
                self.assertEqual((cb, source, destination), (0x08000000, reader.PATTERN, reader.BOUNCE))
            else:
                self.assertEqual((ca, cb, source, destination), (0, 0, 0, 0))

    def test_configured_channel_is_preserved_and_skipped(self):
        state = self.emulate('selftest', mode='skip7')
        result, _ = decode('selftest', state['packets'][0])
        self.assertEqual(result['channel'], 6)
        self.assertEqual(struct.unpack_from('<I', state['channels'], 112)[0], 0x1234)


if __name__ == '__main__':
    unittest.main()
