"""Audit stock IDM/EDM diagnostic labels without executing memory operations."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from core1_wait_study import IMAGE_SHA256
from dramio_clear_study import NATIVE_SHA256
from dramio_owner_study import expect
from kernel_abi import read


def unsigned_ldr_offsets(data, immediate):
    """Candidate LDR.W unsigned-immediate encodings, excluding PC-relative literals.

    These halfword candidates can include data and do not establish calls or reachability.
    """
    if not 0 <= immediate <= 0xfff:
        raise ValueError('Expected a 12-bit unsigned immediate')
    offsets = []
    for off in range(0, len(data)-3, 2):
        first, second = struct.unpack_from('<HH', data, off)
        if first & 0xfff0 == 0xf8d0 and first & 15 != 15 and second & 0xfff == immediate:
            offsets.append(off)
    return offsets


def report(core, native):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native image digest')
    for address, mnemonic, operands in (
            (0x61018266, 'ldr', 'r0, [pc, #0x39c]'),
            (0x6101826c, 'ldr.w', 'fp, [r0, #0x54]'),
            (0x61018270, 'ldr', 'r1, [r0, #0x54]'),
            (0x61018272, 'str', 'r1, [sp]'),
            (0x61018274, 'ldr.w', 'sl, [r0, #0x58]'),
            (0x61018278, 'ldr.w', 'sb, [r0, #0x48]'),
            (0x610182ac, 'mov', 'r1, fp'),
            (0x610182ae, 'adr', 'r0, #0x358'),
            (0x610182bc, 'mov', 'r1, sl'),
            (0x610182be, 'adr', 'r0, #0x358'),
            (0x610182d4, 'adr', 'r0, #0x358'),
            (0x610182d6, 'ldr', 'r1, [sp]'),
            (0x610182e8, 'mov', 'r1, sb'),
            (0x610182ea, 'adr', 'r0, #0x354'),
            (0x610182b0, 'bl', '#0x610153e8'),
            (0x610182c2, 'bl', '#0x610153e8'),
            (0x610182d8, 'bl', '#0x610153e8'),
            (0x610182ee, 'bl', '#0x610153e8'),
            (0x6107db54, 'bl', '#0x61021320'),
            (0x61021324, 'mov.w', 'r6, #0x1100000'),
            (0x6102132e, 'add.w', 'r1, r6, r5, lsl #14'),
            (0x6102133e, 'ldrh', 'r7, [r1, #2]')):
        expect(core, address, mnemonic, operands)
    labels = []
    for adr, offset, source in ((0x610182ae, 0x54, 0x6101826c),
            (0x610182be, 0x58, 0x61018274), (0x610182d4, 0x54, 0x61018270),
            (0x610182ea, 0x48, 0x61018278)):
        # All four are the 16-bit ADR r0 form in the instruction anchors above.
        halfword = int.from_bytes(read(core, adr, 2), 'little')
        address = ((adr+4) & ~3) + (halfword & 255)*4
        text = read(core, address, 40).split(b'\0', 1)[0].decode('ascii')
        labels.append(dict(label=text, label_address=address, register=0x41100000+offset,
                           register_load=source, format_adr=adr))
    if core.u32(0x61018604) != 0x41100000 or [r['label'] for r in labels] != [
            'IDM_CTRL  %08lX', 'IDM_MON   %08lX(%04lX)',
            'EDM_CTRL  %08lX', 'EDM_MON   %08lX(%04lX)']:
        raise ValueError('Unexpected diagnostic strings or peripheral base')
    if native[0xfd0ac:0xfd0c0] != bytes.fromhex('c0035fd600008052c0035fd6c0035fd6c0035fd6'):
        raise ValueError('Native clear/busy/float endpoint stubs differ')
    spans = [(0x61018260, 0xa4), (0x61018608, 0x50), (0x61021320, 0x62)]
    return dict(payload_sha256=IMAGE_SHA256, native_sha256=NATIVE_SHA256,
        diagnostic_labels=labels,
        bool_domain_diagnostic_names={'0': 'IDM', '1': 'EDM'},
        control_labels_share_register=True,
        ldr_unsigned_candidates={hex(n): [core.address(off) for off in
            unsigned_ldr_offsets(core.data, n)] for n in (0xec, 0xf4, 0xf8, 0xfc, 0x100, 0x104, 0x108)},
        native_clear_or_float_domain_routing_present=False,
        idmem_checksum_source=0x01100000,
        bulk_clear_count_unit_proven=False, physical_domain_name_validated=False,
        spans=[dict(address=a, file_offset=core.offset(a), length=n,
                    sha256=hashlib.sha256(read(core,a,n)).hexdigest()) for a,n in spans],
        execution_ready=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('native', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    print(json.dumps(report(Core1(args.image), args.native.read_bytes()), indent=2))
