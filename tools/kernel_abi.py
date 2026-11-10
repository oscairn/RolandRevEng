"""Inspect CORE1 render reservations and framing; never emit or upload a program."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import command_count, packets, swap_words


def read(core, address, size):
    """Require the entire read to stay in one file-backed runtime mapping."""
    if size <= 0:
        raise ValueError('Expected a positive read size')
    start, end = core.offset(address), core.offset(address + size - 1)
    if end != start + size - 1 or end >= len(core.data):
        raise ValueError('Read crosses a runtime mapping or the image end')
    return core.data[start:end + 1]


def program_list(core, address):
    kind, dsp, count, pad, table = struct.unpack('<4BI', read(core, address, 8))
    if kind != 0 or dsp > 6 or not 1 <= count <= 16 or pad or table % 4:
        raise ValueError('Expected an observed CORE1 render-list header')
    rows = []
    for index in range(count):
        base, length, capacity, source = struct.unpack('<4I', read(core, table + 16*index, 16))
        if base % 2 or length % 2 or not 0 <= length <= capacity or source % 4:
            raise ValueError('Invalid render segment bounds/alignment')
        stream = swap_words(read(core, source, (length + 3) & ~3))[:length] if length else b''
        decoded = packets(stream)
        frames = [dict(offset=offset, control=control) for offset, words in decoded
                  for control in words[1:1 + command_count(words[0])]
                  if control in (0xff70, 0xff71, 0xff75, 0x00f8)]
        transfers = []
        for offset, words in decoded:
            n = command_count(words[0])
            for control in words[1:1+n]:
                if control & 0xff0 == 0xfe0 and not control & 1:
                    operand = 1 + n + (control & 15) // 2
                    if operand >= len(words):
                        raise ValueError('Indexed transfer outside packet')
                    transfers.append(dict(offset=offset, port=control >> 12, operand=words[operand]))
        rows.append(dict(base=base, length=length, capacity=capacity, source=source,
                         logical_sha256=hashlib.sha256(stream).hexdigest(),
                         framing_controls=frames, indexed_transfers=transfers))
    return dict(address=address, header_dsp=dsp, segments=rows)


def segment_info(core, address):
    """Read the recovered SDSPSegmentInfo fields; numeric memory enums stay numeric."""
    raw = read(core, address, 0x48)
    dsp, table, first, count = struct.unpack_from('<IIBB', raw)
    if dsp > 6 or not 1 <= count <= 16 or table % 4 or any(raw[10:12]):
        raise ValueError('Unsupported render reservation descriptor')
    render = [dict(base=base, capacity=capacity) for base, capacity in
              struct.iter_unpack('<II', read(core, table, count*8))]
    if any(r['base'] % 2 or r['capacity'] % 2 for r in render):
        raise ValueError('Unaligned render reservation')
    memories = {}
    for enum, offset in ((0, 0x20), (1, 0x28), (2, 0x30), (5, 0x38), (6, 0x18), (11, 0x40)):
        pointer, n = struct.unpack_from('<IB', raw, offset)
        if n > 16 or any(raw[offset+5:offset+8]) or pointer % 4:
            raise ValueError('Unsupported memory reservation descriptor')
        memories[enum] = [dict(base=base, length=length) for base, length in
                         struct.iter_unpack('<II', read(core, pointer, n*8))] if n else []
    return dict(address=address, dsp=dsp, first=first, render=render, memories=memories)


def placements(program, owner, unique=False):
    """Model only the two recovered segmented-render destination rules.

    This checks structure/reservations, not safe task context or runnable code.
    """
    first = 0 if unique else owner['first']
    if first + len(owner['render']) > len(program['segments']):
        raise ValueError('Program list lacks the manager-selected segments')
    result = []
    for index, reserved in enumerate(owner['render']):
        segment = program['segments'][first + index]
        if segment['length'] > reserved['capacity']:
            raise ValueError('Program exceeds the manager reservation')
        destination = reserved['base'] if unique else segment['base']
        # Offline policy: stock non-unique code checks length but trusts the list base.
        if destination != reserved['base'] or destination + segment['length'] > 0x100000000:
            raise ValueError('Destination does not match the owner reservation')
        result.append(dict(list_index=first+index, dsp=owner['dsp'], destination=destination,
                           length=segment['length'], capacity=reserved['capacity'],
                           source=segment['source']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--list', required=True, type=lambda value: int(value, 0))
    parser.add_argument('--segment-info', required=True, type=lambda value: int(value, 0))
    parser.add_argument('--unique', action='store_true')
    args = parser.parse_args()
    from core1 import Core1
    try:
        core = Core1(args.image)
        program = program_list(core, args.list)
        owner = segment_info(core, args.segment_info)
        result = dict(payload_sha256=hashlib.sha256(core.data).hexdigest(),
                      program=program, owner=owner, unique=args.unique,
                      placements=placements(program, owner, args.unique),
                      execution_ready=False,
                      limitations=['Static layout only; no task, routing, timing or control semantics proof.',
                                   'No relocation of operands, state or coefficients is performed.'])
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
