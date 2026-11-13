from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_fantom_core1_marker as marker
from core1_sysex import inspect

STOCK = ROOT / 'local/fantom-07-onscreen-probe-v108/stock-files/FNTM0_UPA.BIN'


class FormatTests(unittest.TestCase):
    def test_reply_is_one_checksummed_word(self):
        result = inspect(marker.MARKER)
        self.assertEqual(result['words'], [0x4f534352])
        self.assertEqual(result['byte_count'], 4)
        self.assertEqual(result['offset'], 0)

    def test_bad_container_and_unsupported_inputs_fail_closed(self):
        for raw in (b'', bytes(100), b'not a stock image'):
            with self.assertRaises(ValueError):
                marker.check_flat_c1a(raw)
            with self.assertRaises(ValueError):
                marker.patch_c1a(raw, marker.MARKER)
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'stock', Path(tmp) / 'output'
            source.write_bytes(b'unknown build')
            with self.assertRaises(ValueError):
                marker.build(source, output)
            self.assertFalse(output.exists())


@unittest.skipUnless(STOCK.exists() and shutil.which('arm-none-eabi-as'),
                     'Pinned local corpus and GNU Arm tools required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.stock_bytes = STOCK.read_bytes()
        cls.members = marker.read_upa(cls.stock_bytes)
        cls.raw = cls.members[1][1]
        cls.stub = marker.assemble()
        cls.patched, cls.patch = marker.patch_c1a(cls.raw, cls.stub)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.image = Path(cls.tmp.name) / 'core1.bin'
        cls.image.write_bytes(cls.raw)
        cls.core = Core1(cls.image)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_crc_and_precise_patch_boundaries(self):
        self.assertEqual(marker.digest(self.stock_bytes), marker.STOCK_UPA_SHA)
        self.assertEqual(marker.check_flat_c1a(self.raw), (0x28009c, 0x3538095f))
        self.assertEqual(marker.check_flat_c1a(self.members[4][1]), (0x3c563c, 0xd86934de))
        crc, _ = marker.check_flat_c1a(self.patched)
        self.assertEqual(len(self.patched), len(self.raw))
        changed = {i for i, (a, b) in enumerate(zip(self.raw, self.patched)) if a != b}
        allowed = set(range(marker.OFFSET, marker.OFFSET + marker.END - marker.ENTRY))
        allowed.update(range(crc, crc + 4))
        self.assertTrue(changed <= allowed)
        self.assertEqual(self.patched[-48:], self.raw[-48:])
        corrupted = bytearray(self.patched)
        corrupted[marker.OFFSET] ^= 1
        with self.assertRaises(ValueError):
            marker.check_flat_c1a(corrupted)
        for stub in (b'', self.stub[:-1], self.stub + bytes(334), bytes(38)):
            with self.assertRaises(ValueError):
                marker.patch_c1a(self.raw, stub)

    def test_repack_changes_only_bmc0_c1a_and_restores_exact_stock(self):
        output = Path(self.tmp.name) / 'package'
        manifest = marker.build(STOCK, output)
        repacked = marker.read_upa((output / 'FNTM0_UPA.BIN').read_bytes())
        self.assertEqual([m.name for m, _ in repacked], list(marker.MEMBERS))
        self.assertEqual([old != new for (_, old), (_, new) in zip(self.members, repacked)],
                         [False, True, False, False, False, False])
        self.assertEqual((output / 'restore/FNTM0_UPA.BIN').read_bytes(), self.stock_bytes)
        self.assertEqual(marker.digest(STOCK.read_bytes()), marker.STOCK_UPA_SHA)
        self.assertEqual(manifest['patched_upa_sha256'],
                         marker.digest((output / 'FNTM0_UPA.BIN').read_bytes()))
        self.assertFalse(manifest['flash_ready'])
        before = (output / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            marker.build(STOCK, output)
        self.assertEqual((output / 'manifest.json').read_bytes(), before)

    def emulate(self, patched=True, wrapper=False, write=0, read=0, poison=0):
        import unicorn as uc
        from unicorn import arm_const as arm
        self.assertEqual(uc.__version__, '2.1.4')
        cpu = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_THUMB | uc.UC_MODE_MCLASS)
        cpu.ctl_set_cpu_model(arm.UC_CPU_ARM_CORTEX_M7)
        data = (self.patched if patched else self.raw)[32:]
        split = self.core.eram_offset
        for base, content in ((0x01100000, data[:split]), (0x61000000, data[split:])):
            cpu.mem_map(base, (len(content) + 4095) & ~4095, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
            cpu.mem_write(base, content)
        cpu.mem_map(0x20080000, 0x30000, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
        cpu.mem_write(0x20080000, b'\xa5' * 0x30000)
        ret, request = 0x10000000, 0x10001000
        cpu.mem_map(ret, 0x1000, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
        cpu.mem_map(request, 0x1000, uc.UC_PROT_READ)
        cpu.mem_write(request, marker.REQUEST)
        queue, words, scratch, sp = 0x2008203c, 0x20095f0c, 0x2009f330, 0x200a1000
        available = 512 - ((write - read) & 511)
        cpu.mem_write(queue, struct.pack('<6I', write, read, available, available, 0, 0))
        registers = [arm.UC_ARM_REG_R4, arm.UC_ARM_REG_R5, arm.UC_ARM_REG_R6,
                     arm.UC_ARM_REG_R7, arm.UC_ARM_REG_R8, arm.UC_ARM_REG_R9,
                     arm.UC_ARM_REG_R10, arm.UC_ARM_REG_R11]
        saved = [0x12340000 + n for n in range(8)]
        for register, value in zip(registers, saved):
            cpu.reg_write(register, value)
        cpu.reg_write(arm.UC_ARM_REG_SP, sp)
        cpu.reg_write(arm.UC_ARM_REG_LR, ret | 1)
        cpu.reg_write(arm.UC_ARM_REG_R0, request if wrapper else poison)
        cpu.reg_write(arm.UC_ARM_REG_R1, len(marker.REQUEST) if wrapper else 0xffffffff)
        cpu.reg_write(arm.UC_ARM_REG_R2, 0xffffffff)
        cpu.reg_write(arm.UC_ARM_REG_PRIMASK, 0)
        calls, packets, logs = [], [], []
        completed = False
        before = bytes(cpu.mem_read(0x20080000, 0x30000))

        def code(u, address, size, _):
            nonlocal completed
            self.assertTrue(sp - 4096 <= u.reg_read(arm.UC_ARM_REG_SP) <= sp)
            if address == ret:
                completed = True
                u.emu_stop()
            elif address in (0x011020c0, 0x01134498):
                # Scheduler/overflow logger are the only mocked stock calls.
                (calls if address == 0x011020c0 else logs).append(u.reg_read(arm.UC_ARM_REG_R0))
                u.reg_write(arm.UC_ARM_REG_PC, u.reg_read(arm.UC_ARM_REG_LR))
            elif address == 0x0111f0be:
                pointer, count = (u.reg_read(r) for r in (arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1))
                self.assertEqual(count, 19)
                self.assertEqual(u.reg_read(arm.UC_ARM_REG_SP) & 7, 0)
                packets.append(bytes(u.mem_read(pointer, count)))

        cpu.hook_add(uc.UC_HOOK_CODE, code)
        # Unicorn 2.1.4's write hook corrupts this stock memclr's Thumb IT behavior.
        # Compare all SRAM instead; RX code and unmapped MMIO still fault on access.
        # ROM, DMA, shared ring, NVIC and other MMIO are deliberately unmapped.
        cpu.emu_start((0x6102d604 if wrapper else marker.ENTRY) | 1, ret + 2, count=20000)
        self.assertTrue(completed, 'Instruction budget exhausted')
        self.assertEqual(cpu.reg_read(arm.UC_ARM_REG_SP), sp)
        self.assertEqual([cpu.reg_read(r) for r in registers], saved)
        self.assertEqual(cpu.reg_read(arm.UC_ARM_REG_PRIMASK), 0)
        permitted = ((sp - 4096, sp), (queue, queue + 24), (words, words + 2048))
        if wrapper:
            permitted += ((scratch, scratch + 260),)
        after = bytes(cpu.mem_read(0x20080000, 0x30000))
        changes = [0x20080000 + i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertTrue(all(any(lo <= address < hi for lo, hi in permitted) for address in changes))
        state = struct.unpack('<6I', cpu.mem_read(queue, 24))
        count = (state[0] - write) & 511
        output = b''.join(bytes(cpu.mem_read(words + 4 * ((write + i) & 511), 4))
                          for i in range(count))
        return state, output, packets, calls, logs, changes

    def test_machine_code_and_original_packetizer_preserve_abi(self):
        expected = bytes.fromhex('34 f0 41 10 34 4e 13 00 34 00 00 00 34 04 0f 05 '
                                 '34 03 04 03 34 05 02 57 35 f7 00 00')
        for wrapper, write, read, poison in ((False, 0, 0, 0), (False, 510, 510, 0x012034c0),
                                             (True, 0, 0, 0), (False, 0, 0, 0xffffffff)):
            with self.subTest(wrapper=wrapper, write=write, poison=poison):
                state, output, packets, calls, logs, _ = self.emulate(
                    wrapper=wrapper, write=write, read=read, poison=poison)
                self.assertEqual(output, expected)
                self.assertEqual(packets, [marker.MARKER])
                self.assertEqual(calls, [2] * 7)
                self.assertEqual(logs, [])
                self.assertEqual(state[5], 7)

    def test_zero_count_request_on_stock_performs_no_mmio_or_reply(self):
        state, output, packets, calls, logs, _ = self.emulate(patched=False, wrapper=True)
        self.assertEqual((output, packets, calls, logs), (b'', [], [], []))
        self.assertEqual(state, (0, 0, 512, 512, 0, 0))

    def test_full_queue_drops_marker_instead_of_spinning_if_logger_returns(self):
        state, output, packets, calls, logs, _ = self.emulate(write=511, read=0)
        self.assertEqual(output, b'')
        self.assertEqual(state[0], 511)
        self.assertEqual((state[4], state[5]), (7, 0))
        self.assertEqual((packets, calls, logs), ([marker.MARKER], [2] * 7, [2] * 7))


if __name__ == '__main__':
    unittest.main()
