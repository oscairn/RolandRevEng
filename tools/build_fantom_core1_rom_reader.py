"""Build the pinned Fantom-07 CORE1 bounded ROM diagnostic; never opens a device."""
import argparse
import copy
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib

from build_fantom_core1_marker import (ENTRY, END, OFFSET, STOCK_UPA_SHA,
                                      STOCK_C1A_SHA, check_flat_c1a, digest, read_upa)

CODE, CODE_SIZE = 0x0113d000, 0x400
CODE_OFFSET = 32 + CODE - 0x01100000
LATCH, PATTERN, BOUNCE = 0x6102d330, 0x6102d340, 0x6102d380
SOURCE = Path(__file__).with_name('fantom_core1_rom_reader.s')


def assemble():
    from elftools.elf.elffile import ELFFile
    names = ('arm-none-eabi-as', 'arm-none-eabi-ld', 'arm-none-eabi-objcopy')
    paths = [shutil.which(name) for name in names]
    if not all(paths):
        raise ValueError('GNU Arm assembler, linker and objcopy are required')
    with tempfile.TemporaryDirectory(prefix='fantom-reader-') as tmp:
        obj, elf = (str(Path(tmp) / n) for n in ('reader.o', 'reader.elf'))
        for args in ([paths[0], '-mcpu=cortex-m4', '-mthumb', str(SOURCE), '-o', obj],
                     [paths[1], f'--section-start=.entry={ENTRY:#x}',
                      f'--section-start=.text={CODE:#x}', '--entry=rom_reader', obj, '-o', elf]):
            subprocess.run(args, check=True, capture_output=True, text=True)
        with open(elf, 'rb') as stream:
            parsed = ELFFile(stream)
            if parsed.header.e_entry != CODE | 1:
                raise ValueError('Wrong reader Thumb entry')
            symbols = {s.name: s.entry.st_value for s in parsed.get_section_by_name('.symtab').iter_symbols()
                       if s.name in ('rom_reader', 'reader_entry', 'dma_trigger', 'dma_poll')}
        sections = []
        for section in ('.entry', '.text'):
            output = str(Path(tmp) / (section[1:] + '.bin'))
            subprocess.run([paths[2], '-O', 'binary', '--only-section=' + section, elf, output],
                           check=True, capture_output=True)
            sections.append(Path(output).read_bytes())
    entry, code = sections
    if len(entry) != 10 or not 16 <= len(code) <= CODE_SIZE:
        raise ValueError('Reader exceeds its fixed patch bounds')
    return entry, code, symbols


def patch_c1a(raw, entry, code):
    if digest(raw) != STOCK_C1A_SHA:
        raise ValueError('Unsupported bmc0 C1A build')
    crc_offset, _ = check_flat_c1a(raw)
    if raw[CODE_OFFSET:CODE_OFFSET + CODE_SIZE] != bytes(CODE_SIZE):
        raise ValueError('The checked ITCM padding is not zero')
    if len(entry) != 10 or not 16 <= len(code) <= CODE_SIZE:
        raise ValueError('Invalid patch lengths')
    patched = bytearray(raw)
    patched[OFFSET:OFFSET + END - ENTRY] = bytes.fromhex('00bf') * ((END - ENTRY) // 2)
    patched[OFFSET:OFFSET + len(entry)] = entry
    def off(address):
        return OFFSET + address - ENTRY
    struct.pack_into('<I', patched, off(LATCH), 0)
    patched[off(PATTERN):off(PATTERN) + 32] = bytes.fromhex('5243534f') + bytes(range(4, 32))
    patched[off(BOUNCE):off(BOUNCE) + 128] = b'\xa5' * 128
    patched[CODE_OFFSET:CODE_OFFSET + CODE_SIZE] = code.ljust(CODE_SIZE, b'\0')
    struct.pack_into('<I', patched, crc_offset, zlib.crc32(patched[:crc_offset]))
    check_flat_c1a(patched)
    allowed = ((OFFSET, OFFSET + END - ENTRY), (CODE_OFFSET, CODE_OFFSET + CODE_SIZE),
               (crc_offset, crc_offset + 4))
    if any(a != b and not any(lo <= i < hi for lo, hi in allowed)
           for i, (a, b) in enumerate(zip(raw, patched))):
        raise ValueError('Patch escaped the helper, checked ITCM padding and CRC')
    return bytes(patched)


def build(stock, passphrase_file, output):
    from build_fantom_core1_flash_kit import write_kit
    from core1 import Core1
    from fantom_rom_dump_preflight import report
    raw = stock.read_bytes()
    if digest(raw) != STOCK_UPA_SHA:
        raise ValueError('Expected pinned stock Fantom-07 1.08 UPA')
    members = read_upa(raw)
    with tempfile.TemporaryDirectory(prefix='fantom-reader-preflight-') as tmp:
        path = Path(tmp) / 'stock-c1a.bin'
        path.write_bytes(members[1][1])
        core = Core1(path)
        checked = report(core)
        if not checked['candidate_address'] <= CODE < CODE + CODE_SIZE <= 0x01100000 + core.eram_offset:
            raise ValueError('ITCM reader overlaps protected initialization data')
    entry, code, symbols = assemble()
    patched = patch_c1a(members[1][1], entry, code)
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w', format=tarfile.GNU_FORMAT) as archive:
        for index, (member, data) in enumerate(members):
            header = copy.copy(member)
            archive.addfile(header, io.BytesIO(patched if index == 1 else data))
    candidate = result.getvalue()
    verified = read_upa(candidate)
    if [old != new for (_, old), (_, new) in zip(members, verified)] != [False, True, False, False, False, False]:
        raise ValueError('Wrong UPA changed-member set')
    kit = write_kit(candidate, raw, passphrase_file, output, 'ROM DIAGNOSTIC bmc0 CORE1',
                    SOURCE.with_name('fantom_core1_rom_README.txt'))
    metadata = dict(source_sha256=digest(SOURCE.read_bytes()), upa_sha256=digest(candidate),
                    c1a_sha256=digest(patched), code_address=CODE, reserved_code_bytes=CODE_SIZE,
                    code_bytes=len(code), entry_bytes=len(entry), symbols=symbols,
                    latch_address=LATCH, pattern_address=PATTERN, bounce_address=BOUNCE,
                    bounce_bytes=128, dma_word_bytes=4, poll_iterations_per_word=8192,
                    rom_windows=[dict(address=0x01200000, bytes=8), dict(address=0x012034c0, bytes=24)],
                    runtime_padding_ownership_proven=False, hardware_tested=False,
                    limits=['No cross-core DMA ownership lock is established.',
                            'Zero channel registers are an idle/configuration guard, not a hardware ownership guarantee.',
                            'An iteration limit cannot bound a stalled hardware bus access.',
                            'DMA error/timeout latches further DMA off until reboot.'])
    (output / 'reader-manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return kit, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--passphrase-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        _, metadata = build(args.stock, args.passphrase_file, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
