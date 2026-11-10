"""Inspect the exact RAMCLR DRAM-IO records and separate native clear geometry offline."""
import hashlib
import json
import os
from pathlib import Path
import struct

from kernel_abi import read, segment_info

FIRMWARE_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'
NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
OWNERS = (0x610a1674, 0x610a16bc, 0x610a1704, 0x610a174c)


def ramclr_records(data):
    """Split only the observed 23 two-word records; control meanings remain unknown."""
    if len(data) != 0xb8:
        raise ValueError('Expected the observed 0xb8-byte RAMCLR segment')
    result = []
    for offset in range(0, len(data), 8):
        word0, word1 = struct.unpack_from('<II', data, offset)
        if word0 & 0xff800000 != 0x80000000 or word1 & 0xfffff:
            raise ValueError('Not an observed RAMCLR record shape')
        result.append(dict(offset=offset, address_field=word0 & 0x7fffff,
                           control_bits=word0 & 0xff800000,
                           companion_high12=word1 >> 20))
    return result


def native_clear_geometry(base, length, origin, mask):
    """Model the native descending store loop, including its excluded start index."""
    if mask not in (0x7ff, 0x3fffff) or any(
            not isinstance(n, int) or not 0 <= n <= 0xffffffff
            for n in (base, length, origin)):
        raise ValueError('Expected u32 inputs and an observed native ring mask')
    start, count = (base - origin) & mask, (length - 1) & mask
    first = (start + 1) & mask
    stop = first + count
    spans = [] if not count else ([[first, stop]] if stop <= mask + 1 else
                                 [[first, mask + 1], [0, stop - mask - 1]])
    return dict(excluded_start=start, stores=count,
                first_store=(start + count) & mask if count else None,
                last_store=first if count else None,
                occupied_half_open_spans=spans)


def native_reference(path):
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unknown native artifact; no address assumptions applied')
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    def expect(address, mnemonic, operands):
        ins = next(md.disasm(data[address:address+4], address))
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'Native instruction mismatch at {address:#x}')
    for enum, target, group in ((0, 0xfc0e8, 0x40), (1, 0xfc168, 0x50), (11, 0xfc368, 0x80)):
        if 0xfc0e8 + 4*data[0x769f50+enum] != target:
            raise ValueError('Native memory-enum jump table differs')
        expect(target+4, 'ldr', f'x8, [x20, #{group:#x}]!')
    loops = []
    for address, group, mask in ((0x23456c, 0x80, 0x3fffff),
                                  (0x23460c, 0x40, 0x7ff),
                                  (0x2346a8, 0x50, 0x7ff)):
        expect(address, 'ldp', 'w16, w15, [x15]')
        expect(address+4, 'mvn', 'w17, w12')
        expect(address+8, 'add', 'w15, w16, w15')
        expect(address+12, 'add', 'w15, w17, w15')
        expect(address+16, 'and', f'w15, w15, #{mask:#x}')
        expect(address+20, 'sub', 'w16, w16, w12')
        expect(address+24, 'and', f'w16, w16, #{mask:#x}')
        expect(address+28, 'cmp', 'w15, w16')
        expect(address+40, 'str', 'xzr, [x17, w15, uxtw #3]')
        loops.append(dict(loop=address, descriptor_pointer_offset=group, mask=mask))
    expect(0x234808, 'mov', 'w0, #1')
    expect(0x23480c, 'ret', '')
    expect(0x36cbac, 'ret', '')
    return dict(sha256=NATIVE_SHA256, set_alg=0x234420, loops=loops,
                wait_return=1, sample_body_returns_immediately=True)


def firmware_report(core):
    if hashlib.sha256(core.data).hexdigest() != FIRMWARE_SHA256:
        raise ValueError('Unknown firmware artifact; no address assumptions applied')
    offset = core.offset(0x0113383c)
    rewrite = [(ins.mnemonic, ins.op_str) for ins in
               core.md.disasm(core.data[offset:offset+14], 0x0113383c)]
    if rewrite != [('ldr', 'r0, [sp, #8]'), ('str.w', 'sb, [sp]'),
                   ('bfc', 'r0, #0, #0x17'), ('orrs', 'r0, r7'),
                   ('str', 'r0, [sp, #8]')]:
        raise ValueError('Firmware low23 rewrite instructions differ')
    kind, dsp, count, pad, table = struct.unpack('<4BI', read(core, 0x61115b14, 8))
    if (kind, dsp, count, pad, table) != (1, 5, 4, 0, 0x61115e3c):
        raise ValueError('RAMCLR DRAM-IO list identity differs')
    segments = [dict(zip(('base', 'length', 'capacity', 'source'),
                         struct.unpack('<4I', read(core, table + 16*i, 16))))
                for i in range(count)]
    result = []
    for address in OWNERS:
        owner = segment_info(core, address)
        info = read(core, address, 0x48)
        dramio, first, number = struct.unpack_from('<IBB', info, 0xc)
        if number != 1 or first >= count:
            raise ValueError('Unexpected owner DRAM-IO selection')
        reserved_base, capacity = struct.unpack('<II', read(core, dramio, 8))
        segment = segments[first]
        if (segment['base'], segment['capacity'], segment['length']) != (reserved_base, capacity, 0xb8):
            raise ValueError('RAMCLR segment disagrees with owner reservation')
        records = ramclr_records(read(core, segment['source'], segment['length']))
        edm, shared = owner['memories'][11], owner['memories'][2]
        if len(edm) != 1 or len(shared) != 1:
            raise ValueError('Unexpected owner memory reservations')
        for index, record in enumerate(records):
            if (record['address_field'], record['companion_high12']) != (
                    edm[0]['base'] + index*0x1900, shared[0]['base']):
                raise ValueError('Record fields disagree with owner metadata')
        result.append(dict(owner_descriptor=address, dsp=owner['dsp'], list_index=first,
                           segment=segment, enum11=edm[0], enum2=shared[0], records=records))
    return dict(sha256=FIRMWARE_SHA256, list_address=0x61115b14, segments=result,
                record_count=23, address_stride=0x1900,
                exact_history_clear_proven=False,
                limitations=['Low23 address-field rewrites are proven only on the named firmware path.',
                             'The companion high12/enum2 match does not independently decode its source semantics.',
                             'No hardware execution, time sweep, opcode semantics or loader is established.'])


def study():
    from core1 import Core1
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1] / 'local'))
    return dict(firmware=firmware_report(Core1(corpus/'b0c1a.bin')),
                native=native_reference(corpus/'zen_arm64'))


if __name__ == '__main__':
    result = study()
    target = Path(__file__).resolve().parents[1] / 'local/dramio-clear-study.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('Four owner-matched DRAM-IO record sets; three separate native clear loops; no hardware clearing proof')
