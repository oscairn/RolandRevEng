"""Read-only routing control candidates; this is not a call/return decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import command_count, packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256, OWNERS
from kernel_abi import program_list, read, segment_info

NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'


def controls(stream, base, entries):
    """Inspect the observed even 00aN pool-index hypothesis and exact 00f8 controls."""
    references, returns = [], []
    for offset, words in packets(stream):
        n = command_count(words[0])
        pool = words[1+n:]
        for index, control in enumerate(words[1:1+n]):
            if control == 0x00f8:
                returns.append(dict(packet_address=base+offset, operation=index))
            if control & 0xfff0 != 0x00a0 or control & 1:
                continue
            byte_offset = control & 15
            if byte_offset // 2 >= len(pool):
                raise ValueError('Candidate 00aN reference is outside its shared pool')
            value = pool[byte_offset // 2]
            references.append(dict(packet_address=base+offset, header=words[0],
                operation=index, control=control, pool_byte_offset=byte_offset,
                pool_value=value, candidate_entry_byte=value*2 if value*2 in entries else None))
    return dict(indexed_00a_candidates=references, return_00f8_candidates=returns)


def native_list(data, address):
    """Inspect a selected LP64 list, including the 24-record DSP4 routing list.

    Only selected streams are framed later; list membership does not prove every
    segment uses the same packet grammar.
    """
    def bounded(address, size):
        if address < 0 or size <= 0 or address + size > len(data):
            raise ValueError('Native record outside image')
        return data[address:address+size]
    kind, packed, table = struct.unpack('<IIQ', bounded(address, 16))
    dsp, count = packed & 255, packed >> 8
    if kind or dsp > 6 or not 1 <= count <= 32 or table % 8:
        raise ValueError('Unsupported native render-list header')
    segments = []
    for index in range(count):
        base, length, capacity, pad, source = struct.unpack('<IIIIQ', bounded(table+24*index, 24))
        if pad or base % 2 or length % 2 or not 0 <= length <= capacity <= 0x10000 or source % 4:
            raise ValueError('Invalid native segment bounds/alignment')
        if length:
            bounded(source, (length+3) & ~3)
        segments.append(dict(base=base, length=length, capacity=capacity, source=source))
    return dict(address=address, dsp=dsp, segments=segments)


def report(core, native):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected recorded bmc0 CORE1 payload')
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    firmware = []
    owner_entries = {r['base'] for a in OWNERS for r in segment_info(core, a)['render']}
    for address in (0x610a1ef8, 0x610b88f0, 0x610a1f18, 0x610a1f28):
        parent = program_list(core, address)
        segment = parent['segments'][0]
        length = segment['length']
        stream = swap_words(read(core, segment['source'], (length+3) & ~3))[:length]
        entries = owner_entries | {s['base'] for s in parent['segments'][1:]}
        firmware.append(dict(address=address, dsp=parent['header_dsp'],
                             **controls(stream, segment['base'], entries)))
    desktop = []
    for address in (0x9faed0, 0x9faee0):
        parent = native_list(native, address)
        segment = parent['segments'][0]
        source, length = segment['source'], segment['length']
        stream = swap_words(native[source:source+((length+3) & ~3)])[:length]
        entries = {s['base'] for s in parent['segments'][1:]}
        stubs = []
        for s in parent['segments'][1:]:
            if s['length'] != 6:
                continue
            stub = swap_words(native[s['source']:s['source']+8])[:6]
            stubs.append(dict(base=s['base'], **controls(stub, s['base'], set())))
        desktop.append(dict(address=address, dsp=parent['dsp'], segment_count=len(parent['segments']),
                            **controls(stream, segment['base'], entries), six_byte_stubs=stubs))
    return dict(core1_sha256=IMAGE_SHA256, native_sha256=NATIVE_SHA256,
                firmware=firmware, desktop=desktop, execution_ready=False,
                limitations=['00aN operand indexing is a routing-context hypothesis, not opcode admission.',
                             'No condition, link register, return stack or transfer timing is decoded.',
                             'Only primary streams and six-byte placeholders are framed.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--native-bin', type=Path, required=True)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(Core1(args.image), args.native_bin.read_bytes()), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
