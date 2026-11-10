"""Inventory LINE input-mix literal variation in local DSP packet streams."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from bmc_dsp import command_count, literal, packets
from emulator_target_study import segment_stream
from header_study import layout

LINE_MIX = (0x0806, 0x4822, 0x1940)


def packet_literals(stream, offset, words):
    return [dict(field=offset + field['offset'], width=field['width'],
                 value=literal(stream[offset + field['offset']:
                                      offset + field['offset'] + field['width']]))
            for field in layout(words)['fields'] if field['role'] == 'literal']


def scan(data, segments):
    """Return exact long-form matches, retaining different following packets."""
    counts, matches = Counter(), []
    for descriptor, segment in segments:
        stream = segment_stream(data, segment)
        try:
            rows = packets(stream)
        except ValueError:
            counts['unframed_segments'] += 1
            continue
        counts['framed_segments'] += 1
        counts['framed_packets'] += len(rows)
        for index, (offset, words) in enumerate(rows):
            if tuple(words[:3]) != LINE_MIX:
                continue
            following = None
            if index + 1 < len(rows):
                next_offset, next_words = rows[index + 1]
                following = dict(offset=next_offset, header=next_words[0],
                                 controls=next_words[1:1 + command_count(next_words[0])])
                try:
                    following['literals'] = packet_literals(stream, next_offset, next_words)
                except ValueError as error:
                    following['layout_error'] = str(error)
            matches.append(dict(descriptor=descriptor, base=segment[0], source=segment[3],
                                length=segment[1],
                                offset=offset, literals=packet_literals(stream, offset, words),
                                following=following))
    return dict(counts=dict(counts), matches=matches)


def core_report(core):
    from analyze import core_lists

    segments = [(core.address(row['payload_offset']), segment)
                for row in core_lists(core) for segment in row['segments']]
    return scan(core.data, segments)


def study(firmware, qspi):
    import lib
    from core1 import Core1
    from jupiter_c1_study import original_span
    from qspi_c1 import read_c1

    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    native_digest = hashlib.sha256(lib.Z).hexdigest()
    if inventory['sha256'] != native_digest:
        raise ValueError('ZENOLOGY inventory hash differs from prepared image')
    segments = [(row[0], segment) for row in inventory['lists'] if row[1] == 0
                for segment in row[3]]
    result = dict(zenology=dict(sha256=native_digest, **scan(lib.Z, segments)))
    for path in firmware:
        core = Core1(path)
        result[path.name] = dict(payload_sha256=hashlib.sha256(core.data).hexdigest(),
                                 **core_report(core))
    for path in qspi:
        manifest, view = read_c1(path)
        with TemporaryDirectory(prefix='line-mix-') as directory:
            analysis = Path(directory) / 'analysis.bin'
            analysis.write_bytes(view)
            core = Core1(analysis)
        if core.eram_offset != manifest['regions'][1]['analysis_offset']:
            raise ValueError('CORE1 bootstrap disagrees with split-member mapping')
        report = core_report(core)
        for match in report['matches']:
            # Logical offsets within swapped words are distinct from original-file offsets.
            match['original_source'] = original_span(
                manifest, core.address(match['source']), (match['length'] + 3) & ~3)
        result[path.name] = dict(container_sha256=manifest['container_sha256'], **report)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1', type=Path, action='append', default=[])
    parser.add_argument('--qspi', type=Path, action='append', default=[])
    args = parser.parse_args()
    names = [path.name for path in args.core1 + args.qspi]
    if len(names) != len(set(names)) or 'zenology' in names:
        parser.error('Supply distinct artifact basenames')
    print(json.dumps(study(args.core1, args.qspi), indent=2))
