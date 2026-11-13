"""Build a local, experimental Fantom-07 1.08 CORE1 marker UPA; no device I/O."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib

STOCK_UPA_SHA = '44993228fc0b407a6b198d8ef3da953f861393d929f47cce08ce1a79fc108f75'
STOCK_C1A_SHA = '0de38e6406b14701bfc93fa7491cc2dda8e8ac590cb44caae6702d7b494d6472'
STOCK_HELPER_SHA = '283375610970084451cbb2db5329ac6e61b2eabe8a866a847e23e4f410e171dd'
MEMBERS = tuple(f'./_tmp/bmc{b}_MI078_C{k}_up.bin'
                for b in (0, 1) for k in ('0A', '1A', '1C'))
TARGET = MEMBERS[1]
ENTRY, END, OFFSET = 0x6102d2e6, 0x6102d432, 0x6d2e6
MARKER = bytes.fromhex('f0 41 10 4e 13 00 00 00 00 04 0f 05 03 04 03 05 02 57 f7')
# Zero count exits the unmodified stock helper before any MMIO read.
REQUEST = bytes.fromhex('f0 41 10 4e 11 00 00 00 00 00 00 00 00 00 f7')
SOURCE = Path(__file__).with_name('fantom_core1_marker.s')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_flat_c1a(raw):
    """Check the flat length/CRC/footer convention; not the QSPI directory format."""
    if len(raw) < 84 or struct.unpack_from('<I', raw)[0] != len(raw) - 48:
        raise ValueError('Invalid flat C1A length')
    if raw[4:32] != bytes(28) or not raw[-48:].startswith(b'Roland MI078_C1A'):
        raise ValueError('Unexpected flat C1A prefix/footer')
    offset = len(raw) - 52
    crc = zlib.crc32(raw[:offset])
    if struct.unpack_from('<I', raw, offset)[0] != crc:
        raise ValueError('Invalid flat C1A CRC')
    return offset, crc


def assemble():
    names = ('arm-none-eabi-as', 'arm-none-eabi-ld', 'arm-none-eabi-objcopy')
    paths = [shutil.which(name) for name in names]
    if not all(paths):
        raise ValueError('GNU Arm assembler, linker and objcopy are required')
    with tempfile.TemporaryDirectory(prefix='fantom-marker-') as tmp:
        obj, elf, binary = (str(Path(tmp) / name) for name in ('marker.o', 'marker.elf', 'marker.bin'))
        for args in (
            [paths[0], '-mcpu=cortex-m4', '-mthumb', '-o', obj, str(SOURCE)],
            [paths[1], f'-Ttext={ENTRY - 2:#x}', '--entry=marker_reply', '-o', elf, obj],
            [paths[2], '-O', 'binary', '--only-section=.text', elf, binary],
        ):
            subprocess.run(args, check=True, capture_output=True, text=True)
        if struct.unpack_from('<I', Path(elf).read_bytes(), 24)[0] != ENTRY | 1:
            raise ValueError('Unexpected linked Thumb entry')
        linked = Path(binary).read_bytes()
    if linked[:2] != bytes.fromhex('00bf') or not 16 <= len(linked) - 2 <= END - ENTRY:
        raise ValueError('Marker does not fit the checked function boundary')
    return linked[2:]


def patch_c1a(raw, stub):
    if digest(raw) != STOCK_C1A_SHA:
        raise ValueError('Unsupported bmc0 C1A build')
    crc_offset, old_crc = check_flat_c1a(raw)
    size = END - ENTRY
    if digest(raw[OFFSET:OFFSET + size]) != STOCK_HELPER_SHA:
        raise ValueError('Unexpected debug helper')
    if not stub or len(stub) % 2 or len(stub) > size or stub.count(MARKER) != 1:
        raise ValueError('Invalid bounded marker stub')
    patched = bytearray(raw)
    patched[OFFSET:OFFSET + size] = stub + bytes.fromhex('00bf') * ((size - len(stub)) // 2)
    struct.pack_into('<I', patched, crc_offset, zlib.crc32(patched[:crc_offset]))
    check_flat_c1a(patched)
    if (patched[:OFFSET] != raw[:OFFSET]
            or patched[OFFSET + size:crc_offset] != raw[OFFSET + size:crc_offset]
            or patched[crc_offset + 4:] != raw[crc_offset + 4:]):
        raise ValueError('Patch escaped the helper and CRC boundaries')
    return bytes(patched), dict(file_offset=OFFSET, runtime_entry=ENTRY,
                               replaced_bytes=size, stub_bytes=len(stub),
                               crc_offset=crc_offset, old_crc=old_crc,
                               new_crc=struct.unpack_from('<I', patched, crc_offset)[0])


def read_upa(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        members = archive.getmembers()
        if tuple(m.name for m in members) != MEMBERS or not all(m.isfile() for m in members):
            raise ValueError('Unexpected UPA member inventory/order/type')
        return [(m, archive.extractfile(m).read()) for m in members]


def build(stock, output):
    raw = stock.read_bytes()
    if digest(raw) != STOCK_UPA_SHA:
        raise ValueError('Expected the pinned stock Fantom-07 1.08 FNTM0_UPA.BIN')
    members = read_upa(raw)
    stub = assemble()
    patched, patch = patch_c1a(members[1][1], stub)
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w', format=tarfile.GNU_FORMAT) as archive:
        for member, content in members:
            content = patched if member.name == TARGET else content
            header = copy.copy(member)
            header.size = len(content)
            archive.addfile(header, io.BytesIO(content))
    candidate = data.getvalue()
    verified = read_upa(candidate)
    if any(new != (patched if member.name == TARGET else old)
           for (member, old), (_, new) in zip(members, verified)):
        raise ValueError('Repacked UPA content mismatch')
    manifest = dict(experiment='Fantom-07 1.08 bmc0 CORE1 constant marker',
                    hardware_tested=False, flash_ready=False, rom_reads=False,
                    dma_access=False, key_recovered=False,
                    stock_upa_sha256=digest(raw), patched_upa_sha256=digest(candidate),
                    assembly_sha256=digest(SOURCE.read_bytes()),
                    stub_sha256=digest(stub), patch=patch,
                    request_hex=REQUEST.hex(' '), reply_hex=MARKER.hex(' '),
                    members=[dict(name=m.name, size=len(old), changed=old != new,
                                  stock_sha256=digest(old), patched_sha256=digest(new))
                             for (m, old), (_, new) in zip(members, verified)])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'restore').mkdir()
    (output / 'FNTM0_UPA.BIN').write_bytes(candidate)
    (output / 'restore/FNTM0_UPA.BIN').write_bytes(raw)
    (output / 'marker.bin').write_bytes(stub)
    (output / 'request.syx').write_bytes(REQUEST)
    (output / 'expected-reply.syx').write_bytes(MARKER)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'README.txt').write_text(
        'EXPERIMENTAL OFFLINE BUILD — NOT HARDWARE VALIDATED\n\n'
        'Only FNTM0_UPA.BIN is a candidate BMC update payload.\n'
        'The restore/ payload is byte-identical stock Fantom-07 1.08.\n'
        'Keep the two payloads separate. A stock file is not a proven recovery path.\n'
        'No Linux board1 updater is included; this is not the persistent-SSH installer.\n'
        'Do not use the SSH-only instruction to skip board2 for this BMC experiment.\n'
        'Do not flash or transmit request.syx until the update/transport path is reviewed.\n'
        'See docs/fantom-core1-marker.md for boundaries, tests and unresolved gates.\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stock_upa', type=Path)
    parser.add_argument('output', type=Path, help='New local directory; must not exist')
    args = parser.parse_args()
    try:
        result = build(args.stock_upa, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
