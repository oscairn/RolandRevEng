"""Offline model of CORE1's program-RAM read path: ReadDspProg, ReadLiteralRaw and their neighbors; no device IO."""
import hashlib

from effect_lifecycle_study import IMAGE_SHA256
from label_target_study import _u32
from program_write_study import APERTURES

READ_PORT_COMMAND = 0x20000000  # width-2 command with bit 29 set, unlike the write path's raw writer


def read_geometry(dsp, address, byte_count):
    """Model nonwrapping reads with room in an otherwise empty shared DMA list."""
    if type(dsp) is not int or not 0 <= dsp < 7:
        raise ValueError('Expected a render/MDSP index in 0..6')
    address, byte_count = _u32(address), _u32(byte_count)
    if (address | byte_count) & 1:
        raise ValueError('Program byte address and count must be even')
    if address + byte_count > 0x80000:
        raise ValueError('Offline geometry excludes window crossing')
    steps = []
    remaining = byte_count
    cursor = address
    # Leading raw halfword: taken only when the byte address is word+2. The
    # loaded data word is shifted right 16 bits, so the returned word holds the
    # two logical bytes right-justified (the same convention as ReadLiteralRaw
    # with align_right true).
    if address & 2 and remaining:
        steps.append(dict(kind='raw_head', source=cursor, source_read_bytes=2,
                          words_returned=1, shift_bits=16))
        cursor += 2
        remaining -= 2
    # Trailing word: taken when the remaining count still has bit 1 set. It
    # reads one FULL stored word at cursor + (remaining & ~3) -- the word that
    # contains the final two logical bytes plus up to two bytes past the count
    # -- and stores it unshifted, so the returned word can include bytes beyond
    # the requested count.
    if remaining & 2:
        steps.append(dict(kind='full_word_tail', source=cursor + (remaining & ~3),
                          source_read_bytes=4, words_returned=1,
                          shift_bits=0, bytes_beyond_count=(address & 2) + 2))
        remaining -= 2
    if remaining:
        kind = 'cpu_copy' if remaining < 64 else 'dma_queue'
        if remaining >= 64 and address & 3:
            raise ValueError('Bulk reads require a word-aligned start address; '
                             'the listed-memcpy builder asserts otherwise')
        steps.append(dict(kind=kind, source=cursor,
                          source_read_bytes=remaining, words_returned=remaining // 4))
    descriptors = []
    if remaining >= 64:
        for offset in range(0, remaining, 0xfff * 4):
            descriptors.append(dict(word_count=min(0xfff * 4, remaining - offset) // 4))
    return dict(dsp=dsp, byte_address=address, byte_count=byte_count,
                aperture=APERTURES[dsp], port_command=READ_PORT_COMMAND | (address & 0x7ffff),
                words_returned=(byte_count + (2 if address & 2 else 0) + 3) // 4,
                steps=steps, descriptors=descriptors,
                execution_exclusion_verified=False, execution_ready=False)


def read_literal_raw(dsp, address, width, align_right):
    """Model the width-2/3/4 single-value read and its alignment shift."""
    if type(dsp) is not int or not 0 <= dsp < 7:
        raise ValueError('Expected a render/MDSP index in 0..6')
    address, width = _u32(address), _u32(width)
    if ((width - 2) & 0xffffffff) >= 3:
        # Mirrors the firmware's unsigned (width - 2) < 3 test, so widths 0, 1
        # and 5 and up also fail.
        raise ValueError('Raw reads accept widths 2, 3 or 4')
    raw = _u32(0) | (address & 0x7ffff)  # command encodes only the address
    shift = 8 * (4 - width) if align_right else 0
    return dict(dsp=dsp, byte_address=address, width=width,
                port_command=READ_PORT_COMMAND | (address & 0x7ffff),
                alignment_shift_bits=shift,
                execution_exclusion_verified=False, execution_ready=False)


def report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom CORE1 payload')
    # The read path's aperture table is the write path's table.
    from dramio_owner_study import expect
    # ReadLiteralRaw 0x0112f6e8: entry, width check, command assembly, busy-wait, data fetch.
    anchors = (
        (0x0112f6e8, 'push', '{r4, lr}'),
        (0x0112f6ea, 'cmp', 'r0, #7'),
        (0x0112f702, 'cmp.w', 'ip, #3'),
        (0x0112f71a, 'ubfx', 'r1, r1, #0, #0x13'),
        (0x0112f71e, 'orr.w', 'r1, r1, r2, lsl #28'),
        (0x0112f726, 'str.w', 'r1, [ip]'),
        (0x0112f72c, 'ldr.w', 'ip, [r1, #8]'),
        (0x0112f730, 'tst.w', 'ip, #-0x80000000'),
        (0x0112f73a, 'ldr', 'r0, [r0, #4]'),
        (0x0112f742, 'rsb.w', 'r1, r2, #4'),
        (0x0112f748, 'lsrs', 'r0, r1'),
    )
    for anchor in anchors:
        expect(core, *anchor)
    # ReadDspProg 0x0112f74c: entry, alignment, raw head, bulk, shared DMA list, wait, epilogue.
    anchors = (
        (0x0112f74c, 'push.w', '{r4, r5, r6, r7, r8, lr}'),
        (0x0112f76a, 'tst.w', 'r3, #1'),
        (0x0112f78e, 'ldr', 'r3, [pc, #0xc4]'),
        (0x0112f7ae, 'orr', 'r1, r1, #0x20000000'),
        (0x0112f7da, 'tst.w', 'r5, #2'),
        (0x0112f7f8, 'mov.w', 'r1, #0x294'),
        (0x0112f816, 'ldr.w', 'ip, [r2, r0, lsl #2]'),
        (0x0112f81e, 'orr', 'r1, r1, #0x20000000'),
        (0x0112f878, 'cmp', 'r5, #0x40'),
        (0x0112f87e, 'ldrb', 'r0, [r4]'),
        (0x0112f880, 'cmp', 'r0, #2'),
        (0x0112f8a0, 'bl', '#0x112f3b2'),
        (0x0112f8aa, 'bl', '#0x112f290'),
        (0x0112f8ea, 'cmp', 'r5, #3'),
        (0x0112f926, 'pop.w', '{r4, r5, r6, r7, r8, pc}'),
    )
    for anchor in anchors:
        expect(core, *anchor)
    if core.u32(0x112fc74) != 0x200847f0:
        raise ValueError('ReadDspProg DMA state byte differs')
    if core.u32(0x112fc78) != 0x112f42d:
        raise ValueError('ReadDspProg completion callback differs')
    for index, aperture in enumerate(APERTURES):
        if core.u32(0x113a954 + 4 * index) != aperture:
            raise ValueError('Read/write aperture table row differs')
    # ReadLiteralFloat/Fixed/ReadDspMemoryFixed entries and their port tables.
    anchors = (
        (0x01130032, 'ldr', 'r3, [pc, #0xfc]'),
        (0x01130050, 'vldr', 's0, [r0, #4]'),
        (0x0113008a, 'ldr', 'r3, [pc, #0xac]'),
    )
    for anchor in anchors:
        expect(core, *anchor)
    ports = {
        'float': 0x113aa3c, 'fixed': 0x113aa58, 'raw': 0x113aa74,
        'memory_float_kinds': 0x113aac0, 'capacities': 0x113aaf0,
    }
    raw_ports = [core.u32(ports['raw'] + 4 * index) for index in range(7)]
    if raw_ports != [0x41104700, 0x41105700, 0x41106700, 0x41107700,
                     0x41108700, 0x41109700, 0x41102700]:
        raise ValueError('Raw read port table differs')
    kind_tables = (0x113acb8, 0x113ad60, 0x113ae08, 0x113ae40, 0x113abe0, 0x113ac10)
    if tuple(core.u32(ports['memory_float_kinds'] + 4 * kind) for kind in range(6)) != kind_tables:
        raise ValueError('Data-memory kind dispatch table differs')
    # The known ReadLiteralRaw call sites: the mute scan plus the program-literal
    # and DRAM-IO address-change methods.
    callers = {0x01133bb4: 'SetMuteMode first-packet word',
               0x01133bda: 'SetMuteMode scan word',
               0x01133220: 'program-literal reader at 0x011330ae',
               0x01133698: 'DRAM-IO address-change method at 0x0113353c'}
    import struct
    for site in callers:
        offset = core.offset(site)
        first = struct.unpack_from('<H', core.data, offset)[0]
        if first & 0xf800 != 0xf000:
            raise ValueError(f'Expected BL encoding at {site:#x}')
        ins = next(core.md.disasm(core.data[offset:offset + 4], site, count=1))
        if ins.mnemonic != 'bl' or ins.operands[0].imm != 0x0112f6e8:
            raise ValueError(f'ReadLiteralRaw call site differs at {site:#x}')
    return dict(payload_sha256=IMAGE_SHA256,
                functions={'ReadLiteralRaw': 0x0112f6e8, 'ReadDspProg': 0x0112f74c,
                           'ReadLiteralFloat': 0x0112ffee, 'ReadLiteralFixed': 0x0113005a,
                           'ReadDspMemoryFloat': 0x01130260, 'ReadDspMemoryFixed': 0x01130354,
                           'GetDspProgAdrs': 0x0112f92a},
                port_tables=ports,
                hardware_execution_verified=False, execution_ready=False)


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=argparse.FileType('rb'))
    parser.add_argument('--dsp', type=int, default=4)
    parser.add_argument('--address', type=lambda value: int(value, 0), default=0x4020)
    parser.add_argument('--count', type=lambda value: int(value, 0), default=510)
    args = parser.parse_args()
    from core1 import Core1
    try:
        core = Core1(args.image.name)
        result = report(core)
        result['sample_read'] = read_geometry(args.dsp, args.address, args.count)
        result['sample_literal'] = read_literal_raw(args.dsp, 0x4021, 2, False)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, f'{error}\n')