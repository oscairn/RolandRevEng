"""Offline census of CORE1 render program slots in the pinned images; no device IO.

Lane A2 of the feasibility order: which program slots/contexts the stock image
declares and fills, who owns each at the list level, and which slots receive
only the six-byte boot stub. Static file analysis of the header-stripped CORE1
payloads; it executes no firmware, emits no program and makes no hardware claim.
"""
import argparse
import hashlib
import json
import struct

from bmc_dsp import packets, swap_words

# Stored eight-byte record behind every six-byte boot stub segment; the loader
# writes its first six bytes (leading word then the high half of the second).
STUB_RECORD = bytes.fromhex('f800020b00000100')
STUB_PROGRAM = bytes.fromhex('0b0200f80001')

IMAGES = {
    'b0c1a': '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154',
    'b1c1a': 'c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd',
}

# Run 13/14 kernel-audio-abi descriptors: SDSPSegmentInfo render reservations
# (dsp, base, capacity). The census must contain each as a written slot.
KNOWN_B0C1A_RESERVATIONS = ((4, 0x4020, 0x1000), (5, 0x8040, 0x1000),
                            (5, 0x9040, 0x1000), (5, 0xa040, 0x1000),
                            (1, 0x3020, 0x1800))

# b1c1a stub-slot capacities with adjacent {base, capacity} reservation-shaped
# records at this table; the remaining stub-only slots have none (pinned).
B1C1A_RESERVATION_TABLE = 0x610a4f20
B1C1A_RESERVATION_RECORDS = 20


def frame_lists(core, max_count=64):
    """Frame render program lists with the analyze.core_lists predicates.

    shortcut: count <= 64 is a documented relaxation, not a firmware bound;
    the pinned images frame identically at 16 and 64, so raise only above 64.
    """
    data, result = core.data, []
    for offset in range(0, len(data) - 8, 4):
        kind, dsp, count, pad, pointer = struct.unpack_from('<BBBBI', data, offset)
        if kind or dsp > 6 or not 1 <= count <= max_count or pad or pointer % 4:
            continue
        try:
            table = core.offset(pointer)
        except ValueError:
            continue
        if table + 16 * count > len(data):
            continue
        segments = []
        for index in range(count):
            base, length, capacity, source = struct.unpack_from('<4I', data, table + 16 * index)
            if base > 0x20000 or length % 2 or not 0 <= length <= capacity <= 0x10000 \
                    or not capacity or source % 4:
                break
            try:
                source_offset = core.offset(source)
            except ValueError:
                break
            if source_offset + ((length + 3) & ~3) > len(data):
                break
            segments.append(dict(base=base, length=length, capacity=capacity,
                                 source=source_offset, source_address=source))
        if len(segments) == count:
            result.append(dict(payload_offset=offset, list_address=core.address(offset),
                               dsp=dsp, segments=segments))
    return result


def stored_segment(core, segment):
    """The stored bytes the writer would read for this segment's geometry."""
    return core.data[segment['source']:
                     segment['source'] + ((segment['length'] + 3) & ~3)]


def classify_segment(stored, length):
    """Classify one segment's stored bytes as 'stub', 'packet' or 'data'.

    'stub' requires exactly the pinned eight-byte record; anything else that
    strictly decodes under the admitted packet subset is 'packet'; the rest is
    'data' (a written tail the writer copies unchanged; it need not be packets).
    """
    if length == 6 and stored[:8] == STUB_RECORD:
        packets(STUB_PROGRAM)
        return 'stub'
    if length % 2 or length > len(stored) or (length + 3) & ~3 > len(stored):
        raise ValueError('Segment length exceeds its stored bytes')
    stream = swap_words(stored[:(length + 3) & ~3])[:length]
    try:
        packets(stream)
    except ValueError:
        return 'data'
    return 'packet'


def classify_lists(core, lists):
    counts = dict(stub=0, packet=0, data=0)
    data_segments = []
    for item in lists:
        for segment in item['segments']:
            kind = classify_segment(stored_segment(core, segment),
                                    segment['length'])
            counts[kind] += 1
            if kind == 'data':
                base_hex = f'{segment["base"]:#x}'
                data_segments.append(dict(list_offset=item['payload_offset'],
                                          dsp=item['dsp'], base=base_hex,
                                          length=segment['length']))
    return dict(counts=counts, data_segments=data_segments)


def reference_census(core, lists):
    """Every framed list must be referenced by exactly one stored u32 word.

    This is the framing-liveness invariant of both pinned images; a change in
    the corpus that breaks it must fail loudly rather than dilute the census.
    """
    index = {}
    data = core.data
    for offset in range(0, len(data) - 3, 4):
        index.setdefault(struct.unpack_from('<I', data, offset)[0], []).append(offset)
    sites = {}
    for item in lists:
        target = core.address(item['payload_offset'])
        found = [core.address(o) for o in index.get(target, [])
                 if abs(o - item['payload_offset']) > 4]
        if len(found) != 1:
            raise ValueError(f'Expected exactly one reference to list at '
                             f'{item["list_address"]:#x}, found {len(found)}')
        sites[item['payload_offset']] = found[0]
    return sites


def pointer_runs(core, lists):
    """Maximal runs of at least two consecutive stored words naming framed lists."""
    referenced = set(reference_census(core, lists).values())
    words = {}
    for address in referenced:
        words[core.offset(address)] = address
    data, runs = core.data, []
    count = (len(data) - 3) // 4
    words_by_offset = set(words)
    start = None
    for k in range(count + 1):
        live = k < count and k * 4 in words_by_offset
        if live and start is None:
            start = k
        elif not live and start is not None:
            if k - start >= 2:
                runs.append(dict(start=core.address(start * 4), length=k - start))
            start = None
    return runs


def reservation_records(core, base, capacity):
    """Offsets of adjacent {base, capacity} reservation-shaped word pairs."""
    n = (len(core.data) - 3) // 4
    words = struct.unpack(f'<{n}I', core.data[:n * 4])
    return [core.address(k * 4) for k in range(n - 1)
            if words[k] == base and words[k + 1] == capacity]


def descriptor_crosscheck(core, lists):
    """Each known b0c1a MFX reservation must be used by real content.

    The kernel-audio-abi study pins five SDSPSegmentInfo render reservations
    (dsp, base, capacity). This check verifies, at list level only, that each
    geometry receives at least one framed segment with real packet content,
    which is how a segmented manager path reaches the slot. Only the four
    FETDRIVE-family reservations are also boot-stubbed; the LINEDRIVE
    reservation receives real content without any stub. Owner identity of
    the writing descriptor is not established here.
    """
    report = []
    for dsp, base, capacity in KNOWN_B0C1A_RESERVATIONS:
        geometry = [classify_segment(stored_segment(core, segment),
                                     segment['length'])
                    for item in lists for segment in item['segments']
                    if segment['base'] == base and segment['capacity'] == capacity]
        if not geometry:
            raise ValueError(f'Reservation ({dsp:#x}, {base:#x}, {capacity:#x}) '
                             'is written by no framed segment')
        if not any(kind == 'packet' for kind in geometry):
            raise ValueError(f'Reservation ({dsp:#x}, {base:#x}, {capacity:#x}) '
                             'has no real-content segment')
        report.append(dict(dsp=dsp, base=f'{base:#x}', capacity=f'{capacity:#x}',
                           stub_segments=geometry.count('stub'),
                           packet_segments=geometry.count('packet')))
    return report


def stub_record_census(core, stub_only):
    """Every stub-only slot's 6-byte segment record must appear exactly once.

    The framed-list segment record is {base, length, capacity, source}; for a
    stub segment its first three words are {base, 6, capacity} and the fourth
    word is the stored source of the pinned boot-stub record. A stub-only
    slot whose record appears zero or several times is a corpus change that
    must fail loudly.
    """
    n = (len(core.data) - 3) // 4
    words = struct.unpack(f'<{n}I', core.data[:n * 4])
    report = []
    for _dsp, base_hex, capacities in stub_only:
        base, capacity = int(base_hex, 16), int(capacities[0], 16)
        if len(capacities) != 1:
            raise ValueError(f'Stub-only slot {base_hex} has capacities '
                             f'{capacities}; census pinned exactly one')
        hits = [core.address(k * 4) for k in range(n - 3)
                if words[k] == base and words[k + 1] == 6 and words[k + 2] == capacity]
        if len(hits) != 1:
            raise ValueError(f'Stub-only slot {base_hex} capacity {capacity:#x} '
                             f'has {len(hits)} {{base, 6, capacity}} segment '
                             'records, expected exactly one')
        source = words[core.offset(hits[0]) // 4 + 3]
        record = core.data[core.offset(source):core.offset(source) + 8]
        if record != STUB_RECORD:
            raise ValueError(f'Stub-only slot {base_hex} record at {hits[0]:#x} '
                             f'source {source:#x} holds {record.hex()}, not the '
                             'pinned boot-stub record')
        report.append(dict(base=base_hex, capacity=f'{capacity:#x}',
                           record=hex(hits[0]), source=hex(source)))
    return report


def study(core, image):
    lists = frame_lists(core)
    classification = classify_lists(core, lists)
    slots = {}
    for item in lists:
        for segment in item['segments']:
            key = (item['dsp'], segment['base'])
            if key not in slots:
                slots[key] = dict(capacities=[], stub_capacities=[], real=False)
            slot = slots[key]
            if segment['capacity'] not in slot['capacities']:
                slot['capacities'] = sorted(slot['capacities'] + [segment['capacity']])
            if segment['length'] == 6 and \
                    core.data[segment['source']:segment['source'] + 8] == STUB_RECORD:
                if segment['capacity'] not in slot['stub_capacities']:
                    slot['stub_capacities'] = sorted(slot['stub_capacities'] +
                                                     [segment['capacity']])
            else:
                slot['real'] = True
    stub_only = sorted(
        [dsp, f'{base:#x}', [f'{cap:#x}' for cap in slot['stub_capacities']]
         ]
        for (dsp, base), slot in slots.items()
        if not slot['real'])
    stub_records = stub_record_census(core, stub_only)
    runs = [dict(start=f'{run["start"]:#x}', length=run['length'])
            for run in pointer_runs(core, lists)]
    result = dict(lists=len(lists), classification=classification,
                  slots=len(slots), stub_only=stub_only,
                  stub_records=stub_records, pointer_runs=runs)
    if image == 'b0c1a':
        result['descriptor_crosscheck'] = descriptor_crosscheck(core, lists)
    if image == 'b1c1a':
        result['b1c1a_reservation_table'] = b1c1a_reservation_table(core)
    return result


def b1c1a_reservation_table(core):
    """The pinned b1c1a reservation-shaped table beside the boot stubs."""
    records = []
    for index in range(B1C1A_RESERVATION_RECORDS):
        base, capacity = struct.unpack_from(
            '<II', core.data, core.offset(B1C1A_RESERVATION_TABLE + 8 * index))
        records.append((base, capacity))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', choices=sorted(IMAGES), help='Pinned CORE1 payload key')
    args = parser.parse_args()
    from core1 import Core1
    from pathlib import Path
    core = Core1(Path('local') / f'{args.image}.bin')
    digest = hashlib.sha256(core.data).hexdigest()
    if digest != IMAGES[args.image]:
        raise SystemExit(f'Unexpected payload SHA-256 {digest}')
    result = study(core, args.image)
    result['image'] = args.image
    result['payload_sha256'] = digest
    print(json.dumps(result, indent=2, default=lambda value: sorted(value)
                     if isinstance(value, set) else value))


if __name__ == '__main__':
    main()