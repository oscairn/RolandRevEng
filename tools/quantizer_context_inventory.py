"""Find the exact FETDRIVE conversion control in framed render segments."""
from collections import Counter

from bmc_dsp import command_count, packets
from emulator_target_study import segment_stream
from header_study import families, UnsupportedLayout
from line_mix_variation import main


def scan(data, segments, *, controls=(0x9c59,)):
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
            control_words = words[1:1 + command_count(words[0])]
            hits = [(slot, control) for slot, control in enumerate(control_words) if control in controls]
            if hits:
                try:
                    operation_families = families(words[0])
                except UnsupportedLayout:
                    operation_families = None
                control_slots = [dict(slot=slot, control=control,
                                      family=operation_families[slot] if operation_families else None)
                                 for slot, control in hits]
                previous = rows[index - 1][1] if index else None
                following = rows[index + 1][1] if index + 1 < len(rows) else None
                matches.append(dict(descriptor=descriptor, base=segment[0], length=segment[1],
                                    source=segment[3], offset=offset, packet=words,
                                    previous=previous, following=following, control_slots=control_slots))
    return dict(counts=dict(counts), matches=matches)


if __name__ == '__main__':
    main(scan, __doc__)
