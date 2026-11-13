"""Fail-closed inventory and structural facts for unresolved 5e09 four-control packets.

The negative-bias study (docs/negative-short-add-study.md) left four 5d52 uses under
header 5e09 unresolved. This tool enumerates every 5e09 packet across the prepared
images and proves per-context structural invariants. It admits no opcode, family or
interpreter change: 5e09 stays outside header_study.families().
"""
import argparse
import collections
import json
from pathlib import Path
import tempfile

from bmc_dsp import command_count, literal, packets, swap_words


# Payload word roles for the three observed 5e09 control shapes. Offsets are payload
# byte offsets; 'resource' marks words that vary across relocated copies.
SHAPES = {
    # controls(1e50,5d52,4014,0fe6): 1.75 and -.25 exactly as the admitted 2e07 chains;
    # the two tail words vary across relocated copies (no known-syntax control consumes
    # offset 4; 0fe6 selects offset 6)
    (0x1e50, 0x5d52, 0x4014, 0x0fe6): dict(gain=(0, 1.75), bias=(2, -0.25),
                                           resource=(4, 6)),
    # controls(2c80,edf4,4010,0fe2): SBF325 shape
    (0x2c80, 0xedf4, 0x4010, 0x0fe2): dict(resource=(2, 4), constant=(0,)),
    # controls(0cc8,5074,4010,8fe2): STTMDLY shape, 8fe2 is a main-A store
    (0x0cc8, 0x5074, 0x4010, 0x8fe2): dict(resource=(2, 4), constant=(0,)),
    # dsp6/b1c1a/JX/SH-4d shared diagnostic shape with the known special short 0094
    (0x4050, 0x1052, 0x0094, 0x0fe6): dict(resource=(2,), special_short=2,
                                           words=(4, 6, 8)),
}


def shape_of(words):
    """Return the known control shape or None; unknown shapes stay unresolved."""
    return SHAPES.get(tuple(words[1:5]))


def payload_bytes(words):
    """Concatenate the 16-bit payload words big-endian, as the byte stream reads."""
    return b''.join(word.to_bytes(2, 'big') for word in words[1 + command_count(words[0]):])


def resource_words(stream, offset, words, shape):
    """The resource words of a 5e09 packet, as plain 16-bit values.

    Fail closed unless every declared resource offset is inside the payload and
    even, and the declared constant/gain/bias words decode to the pinned values.
    """
    payload = payload_bytes(words)
    for key in ('gain', 'bias'):
        if key in shape:
            off, expected = shape[key]
            if literal(payload[off:off + 2]) != expected:
                raise ValueError(f'{offset:#x}: {key} literal {payload[off:off+2].hex()} '
                                 f'is not {expected:#g}')
    for off in shape.get('resource', ()):
        if off % 2 or off + 2 > len(payload):
            raise ValueError(f'{offset:#x}: resource offset {off} outside payload {payload.hex()}')
        yield off, int.from_bytes(payload[off:off + 2], 'big')
    for off in shape.get('constant', ()):
        if off + 2 > len(payload):
            raise ValueError(f'{offset:#x}: constant offset {off} outside payload')
        yield off, int.from_bytes(payload[off:off + 2], 'big')


def scan_segments(data, segments):
    """Scan one image's framed segments; every 5e09 packet becomes a record.

    Segments are (base, length, capacity, source) tuples over stored LE32 words,
    optionally paired with a dsp tag. Unframeable segments are counted, not
    fatal; any 5e09 packet with an unknown control shape is fatal, because this
    study claims full inventory coverage.
    """
    counts = collections.Counter()
    records = []
    for entry in segments:
        segment = entry[0] if isinstance(entry, tuple) and len(entry) == 2 else entry
        base, length, capacity, source = segment
        if not length:
            continue
        stream = swap_words(data[source:source + ((length + 3) & ~3)])[:length]
        try:
            decoded = packets(stream)
        except ValueError:
            counts['unframeable_segments'] += 1
            continue
        counts['framed_segments'] += 1
        counts['framed_packets'] += len(decoded)
        for offset, words in decoded:
            if words[0] != 0x5e09:
                continue
            counts['five_e_packets'] += 1
            shape = shape_of(words)
            if shape is None:
                raise ValueError(f'{offset:#x}: unknown 5e09 control shape '
                                 + ' '.join(f'{x:04x}' for x in words))
            counts[f'shape_{words[1]:04x}'] += 1
            if command_count(words[0]) != 4 or len(words) != words[0] & 31:
                raise ValueError(f'{offset:#x}: 5e09 count or length changed')
            resources = [(off, value) for off, value in resource_words(stream, offset, words, shape)]
            records.append(dict(base=base, source=source, offset=offset,
                                controls=[f'{word:04x}' for word in words[1:5]],
                                resources=resources, payload=payload_bytes(words).hex(),
                                length=words[0] & 31))
    counts['unframeable_segments'] = counts['unframeable_segments']
    return records, counts


def core_segments(path):
    from analyze import core_lists
    from core1 import Core1
    core = Core1(path)
    return core.data, [(tuple(segment), row['dsp'])
                       for row in core_lists(core) for segment in row['segments']]


def qspi_segments(path):
    from analyze import core_lists
    from qspi_c1 import read_c1
    from core1 import Core1
    manifest, view = read_c1(path)
    with tempfile.TemporaryDirectory(prefix='five-e09-') as directory:
        image = Path(directory) / 'analysis.bin'
        image.write_bytes(view)
        core = Core1(image)
        data = bytes(core.data)
        segments = [(tuple(segment), row['dsp'])
                    for row in core_lists(core) for segment in row['segments']]
    return data, segments


def zen_segments():
    import lib
    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    return lib.Z, [(tuple(segment), row[1]) for row in inventory['lists'] for segment in row[3]]


def study(zen=True):
    """Full cross-image report. The GASS-type 5d52 facts are checked per image."""
    result = collections.OrderedDict()
    sources = []
    if zen:
        sources.append(('zen_arm64', zen_segments()))
    for path in (Path('local/b0c1a.bin'), Path('local/b1c1a.bin')):
        if path.exists():
            sources.append((path.name, core_segments(path)))
    for path in (Path('local/crossmodel/jupiter-x/MI077_C1A_up.bin'),
                 Path('local/crossmodel/mc101/RPG69_C1A_up.bin'),
                 Path('local/crossmodel/sh-4d/DD013_C1A_up.bin')):
        if path.exists():
            sources.append((path.name, qspi_segments(path)))
    if not sources:
        raise ValueError('No prepared corpus image found under BMC_CORPUS_DIR')
    totals = collections.Counter()
    for name, (data, segments) in sources:
        records, counts = scan_segments(data, segments)
        totals.update(counts)
        gass = [row for row in records if row['controls'][1] == '5d52']
        # Structural invariant: every GASS-type 5e09 packet keeps gain 1.75, bias -.25
        # and carries exactly two resource words; the first one (offset 4) is consumed
        # by no known-syntax control. This is the negative-bias study's unknown group.
        for row in gass:
            offsets = [off for off, _ in row['resources']]
            if offsets != [4, 6] or literal(bytes.fromhex(row['payload'])[2:4]) != -0.25:
                raise ValueError(f"{name}: GASS-type 5e09 facts changed at {row['offset']:#x}")
        distinct = {tuple(row['resources']) for row in gass}
        result[name] = dict(counts=dict(sorted(counts.items())),
                            five_e_packets=records,
                            gass_5d52_packets=len(gass),
                            distinct_resource_pairs=len(distinct),
                            opcode_admission=False, hardware_verified=False)
    result['totals'] = dict(sorted(totals.items()))
    gass_pairs = set()
    for name, report in result.items():
        if name == 'totals':
            continue
        gass_pairs.update(tuple(row['resources']) for row in report['five_e_packets']
                          if row['controls'][1] == '5d52')
    result['totals']['distinct_gass_resource_pairs'] = len(gass_pairs)
    return result


def main(description=__doc__):
    parser = argparse.ArgumentParser(description=description)
    parser.parse_args()
    print(json.dumps(study(), indent=2))


if __name__ == '__main__':
    main()