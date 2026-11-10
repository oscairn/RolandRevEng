"""Offline MC-101 v1.82 CORE1 comparison; parses files only and emits metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from qspi_c1 import parse_c1

MC101_SHA256 = '6de1e182e531d672ef9bcc0aabf853dd724f59e70dfd9c9aa34c28a393d62a21'
FANTOM_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class MC101Core1:
    """Split-file mapping specific to the independently checked MC-101 package."""
    def __init__(self, container, md):
        if sha256(container) != MC101_SHA256:
            raise ValueError('Unsupported MC-101 CORE1 build')
        manifest, analysis = parse_c1(container)
        self.directory = manifest['members']
        self.regions = [(row['runtime_base'], analysis[row['analysis_offset']:
                                                    row['analysis_offset'] + row['size']])
                        for row in manifest['regions']]
        self.md = md
        if self.u32(0x01100004) != 0x01100de5 or self.u32(0x01100e70) != 0x61000001:
            raise ValueError('Split mapping reset anchors differ')

    def read(self, address, size):
        if size < 0:
            raise ValueError('Negative read size')
        for base, data in self.regions:
            offset = address - base
            if 0 <= offset < len(data) and offset + size <= len(data):
                return data[offset:offset + size]
        raise ValueError('Read outside one mapped region')

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def instructions(self, address, size):
        return list(self.md.disasm(self.read(address, size), address))


def report(container, fantom):
    if sha256(fantom.data) != FANTOM_SHA256:
        raise ValueError('Unsupported Fantom comparison build')
    mc = MC101Core1(container, fantom.md)

    def fantom_read(address, size):
        offset = fantom.offset(address)
        return fantom.data[offset:offset + size]

    prefix = fantom_read(0x6102d2e6, 324)
    if mc.read(0x6103205a, 324) != prefix:
        raise ValueError('MMIO read-prefix mismatch')
    matches = sum(data.count(prefix) for _, data in mc.regions)
    if matches != 1 or mc.read(0x610321a2, 4) != fantom_read(0x6102d42e, 4):
        raise ValueError('Unexpected MMIO prefix count or epilogue')
    calls = mc.instructions(0x6103219e, 4)
    if len(calls) != 1 or calls[0].mnemonic != 'bl':
        raise ValueError('Missing MC-101 reply output call')

    # The wait bodies differ only in their three PC-relative BL relocations.
    original, other = bytearray(fantom_read(0x011271b8, 0x62)), bytearray(mc.read(0x01124c5c, 0x62))
    wait_calls = []
    for delta in (0x14, 0x1a, 0x4a):
        ins = mc.instructions(0x01124c5c + delta, 4)
        if len(ins) != 1 or ins[0].mnemonic != 'bl':
            raise ValueError('Unexpected wait-call relocation')
        wait_calls.append(ins[0].operands[0].imm)
        original[delta:delta + 4] = other[delta:delta + 4] = bytes(4)
    if original != other or wait_calls != [0x0110285a, 0x01102864, 0x0110286a]:
        raise ValueError('Wait body differs beyond reviewed relocations')
    scale = mc.instructions(0x01124cc2, 4)[0]
    if scale.mnemonic != 'movw' or scale.operands[1].imm != 44100:
        raise ValueError('Unexpected scaled-wait multiplier')
    return dict(mc101_core1_sha256=sha256(container), fantom_payload_sha256=sha256(fantom.data),
                footer=container[-48:].decode('ascii'), members=mc.directory,
                mapping=[dict(base=base, prefix_removed=32, length=len(data), sha256=sha256(data))
                         for base, data in mc.regions],
                mmio=dict(fantom_read=0x6102d2e6, mc101_read=0x6103205a,
                          identical_prefix_bytes=324, prefix_sha256=sha256(prefix),
                          mc101_send=calls[0].operands[0].imm, identical_epilogue_bytes=4),
                wait=dict(fantom=0x011271b8, mc101=0x01124c5c, body_bytes=0x62,
                          only_differences='Three PC-relative BL immediates', mc101_calls=wait_calls,
                          fantom_scaled_multiplier=48000, mc101_scaled_multiplier=44100),
                limits=['Static factory-image comparison; runtime reachability is not observed.',
                        'No external transport, hardware clock or safe request bound established.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mc101_core1', type=Path)
    parser.add_argument('fantom_core1', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(args.mc101_core1.read_bytes(), Core1(args.fantom_core1)), indent=2))
    except (ValueError, OSError, UnicodeError, struct.error) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
