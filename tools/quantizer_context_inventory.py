"""Find the exact FETDRIVE conversion control in framed render segments."""
from collections import Counter

from bmc_dsp import command_count, packets
from emulator_target_study import segment_stream
from line_mix_variation import main


def scan(data, segments):
    counts, matches = Counter(), []
    for descriptor, segment in segments:
        try:
            rows = packets(segment_stream(data, segment))
        except ValueError:
            counts['unframed_segments'] += 1
            continue
        counts['framed_segments'] += 1
        counts['framed_packets'] += len(rows)
        for index, (offset, words) in enumerate(rows):
            controls = words[1:1 + command_count(words[0])]
            if 0x9c59 in controls:
                previous = rows[index - 1][1] if index else None
                following = rows[index + 1][1] if index + 1 < len(rows) else None
                matches.append(dict(descriptor=descriptor, base=segment[0], length=segment[1],
                                    source=segment[3], offset=offset, packet=words,
                                    previous=previous, following=following))
    return dict(counts=dict(counts), matches=matches)


if __name__ == '__main__':
    main(scan, __doc__)
