"""Cross-check the fitted 4b/5c miscellaneous-slot predictions against the corpus.

The fitted four-operation rule (header_family_crosscheck.ranked_choices) predicts
the ordered families 4b=(0,1,2,4) and 5c=(1,1,2,4): exactly one transfer slot at
position 3 and none elsewhere, while 5a=(1,1,2,2) predicts no transfer slot at
all. Run 4 proved only that such packets fail closed. This census adds the
corpus-decidable positional invariant, calibrated on the admitted anchor syntax
and the count-1 classes 08..0c:

  C1 every fe0..fee-window control word in any fitted count-4 packet sits in a
     slot the rule predicts as transfer, except the known 62/6fe4 slot-0 trap;
  C2 for 4b/5c specifically, the fe-window control set per packet is [] or [3];
  C3 5a packets carry no fe-window control;
  C4 count-1 controls of 08/09/0a/0b never use the fe window, 0c does.

Nothing is admitted into header_study; the decoder is unchanged. Fail closed.
"""
import argparse
import collections
import json
from pathlib import Path
import tempfile

from bmc_dsp import command_count, packets, swap_words
from header_family_crosscheck import ranked_choices
from header_study import UnsupportedLayout, layout

TRAP_CODE, TRAP_SLOT = 0x62, 0


def is_fe_window(word):
    return 0xfe0 <= word & 0xfff <= 0xfee


def scan_segments(data, segments, rule):
    """Scan framed packets; every invariant breach raises. Zero decoder changes."""
    counts = collections.Counter()
    vocab = collections.defaultdict(collections.Counter)
    for base, length, capacity, source in segments:
        if not length:
            continue
        end = min(source + ((length + 3) & ~3), (len(data) // 4) * 4)
        stream = swap_words(data[source:end])[:length]
        try:
            decoded = packets(stream)
        except ValueError:
            counts['unframeable_segments'] += 1
            continue
        counts['framed_segments'] += 1
        counts['framed_packets'] += len(decoded)
        for offset, words in decoded:
            header = words[0]
            if header & 32:
                counts['bit5_packets'] += 1
                continue
            code, count = header >> 8, command_count(header)
            if count == 1 and 8 <= code <= 12:
                counts[f'count1_{code:02x}'] += 1
                vocab[('count1', code)][words[1]] += 1
                if is_fe_window(words[1]):
                    counts[f'count1_{code:02x}_fe_window'] += 1
            if count != 4 or code not in rule:
                continue
            counts['count4_fitted'] += 1
            controls = words[1:5]
            fe_slots = [index for index, control in enumerate(controls) if is_fe_window(control)]
            try:
                layout(words)
                counts['decoded_packets'] += 1
            except UnsupportedLayout:
                counts['unsupported_packets'] += 1
            except ValueError as error:
                counts['rejected_packets'] += 1
                raise ValueError(f'{offset:#x} {header:04x}: strict framing rejected: {error}')
            for index in fe_slots:
                if rule[code][index] == 4:
                    continue
                if (code, index) == (TRAP_CODE, TRAP_SLOT):
                    counts['code62_slot0_fe'] += 1
                    continue
                raise ValueError(f'{offset:#x} {header:04x}: fe-window control in slot {index} '
                                 f'which the fitted rule does not predict as transfer')
            if code == TRAP_CODE:
                counts['code62_packets'] += 1
            elif code == 0x5a:
                counts['code5a_packets'] += 1
                if fe_slots:
                    raise ValueError(f'{offset:#x} {header:04x}: 5a packet carries a fe-window '
                                     'control although the rule predicts no transfer slot')
            elif code in (0x4b, 0x5c):
                counts[f'code{code:02x}_packets'] += 1
                counts[f'code{code:02x}_fe3_packets'] += (fe_slots == [3])
                counts[f'code{code:02x}_no_fe_packets'] += (not fe_slots)
                if fe_slots not in ([], [3]):
                    raise ValueError(f'{offset:#x} {header:04x}: 4b/5c fe-window controls {fe_slots} '
                                     'are not [] or [3]')
                for index, control in enumerate(controls):
                    vocab[(code, index)][control] += 1
    if counts['rejected_packets']:
        raise ValueError('unreachable: rejections already raise')
    return counts, dict(vocab)


def calibration(vocab):
    """Pin the count-1 window calibration; classes 08..0b must avoid the window."""
    result = {}
    for code in range(8, 13):
        controls = vocab.get(('count1', code), collections.Counter())
        result[f'{code:02x}'] = dict(occurrences=sum(controls.values()), distinct=len(controls),
                                     fe_window_occurrences=sum(count for control, count in controls.items()
                                                               if is_fe_window(control)),
                                     fe_window_distinct=len({control for control in controls
                                                             if is_fe_window(control)}))
    if [result[f'{code:02x}']['fe_window_occurrences'] for code in range(8, 12)] != [0, 0, 0, 0]:
        raise ValueError('Classes 08..0b use the fe window; the calibration changed')
    return result


def vocab_crosscheck(vocab):
    """Compare 4b/5c leading-slot vocabularies with the long/short count-1 classes.

    The count-1 08 (long) and 09 (short) vocabularies overlap in only six words,
    so mostly class-exclusive words discriminate. Recorded, not asserted.
    """
    long8, short9 = set(vocab[('count1', 8)]), set(vocab[('count1', 9)])
    report = dict(long8_distinct=len(long8), short9_distinct=len(short9),
                  overlap=len(long8 & short9))
    for label, code, indices in (('4b_slot0', 0x4b, (0,)), ('5c_slot01', 0x5c, (0, 1))):
        slot_words = set().union(*(set(vocab[(code, index)]) for index in indices))
        report[label] = dict(distinct=len(slot_words),
                             long8_inside=len(slot_words & long8),
                             short9_inside=len(slot_words & short9),
                             outside_both=len(slot_words - long8 - short9))
    return report


def study():
    import lib
    from analyze import core_lists
    from core1 import Core1

    rule = ranked_choices()
    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    sources = [('zen_arm64', lib.Z,
                [tuple(segment) for row in inventory['lists'] for segment in row[3]])]
    for filename in ('b0c1a.bin', 'b1c1a.bin'):
        core = Core1(lib.BASE / filename)
        sources.append((filename, core.data, [tuple(segment) for row in core_lists(core)
                        for segment in row['segments']]))
    for path in (lib.BASE / 'crossmodel/jupiter-x/MI077_C1A_up.bin',
                 lib.BASE / 'crossmodel/mc101/RPG69_C1A_up.bin',
                 lib.BASE / 'crossmodel/sh-4d/DD013_C1A_up.bin'):
        if not path.exists():
            raise ValueError(f'Missing pinned cross-model image {path}')
        from qspi_c1 import read_c1
        manifest, view = read_c1(path)
        with tempfile.TemporaryDirectory(prefix='four-b-five-c-') as directory:
            image = Path(directory) / 'analysis.bin'
            image.write_bytes(view)
            core = Core1(image)
            data, segments = bytes(core.data), [tuple(segment) for row in core_lists(core)
                                                for segment in row['segments']]
        sources.append((path.name, data, segments))

    combined, totals = collections.Counter(), {}
    vocab = collections.defaultdict(collections.Counter)
    for name, data, segments in sources:
        counts, image_vocab = scan_segments(data, segments, rule)
        combined.update(counts)
        for key, counter in image_vocab.items():
            vocab[key].update(counter)
        fe3 = sum(counts[f'code{code:02x}_fe3_packets'] for code in (0x4b, 0x5c))
        totals[name] = dict(
            count4_fitted=counts['count4_fitted'],
            packets_4b5c=sum(counts[f'code{code:02x}_packets'] for code in (0x4b, 0x5c)),
            fe3_packets=fe3,
            no_fe_packets=sum(counts[f'code{code:02x}_no_fe_packets'] for code in (0x4b, 0x5c)),
            code5a_packets=counts['code5a_packets'],
            code62_packets=counts['code62_packets'],
            code62_slot0_fe=counts['code62_slot0_fe'])
    combined_keys = ('count4_fitted', 'decoded_packets', 'unsupported_packets',
                     'code5a_packets', 'code62_packets', 'code62_slot0_fe')
    summary = {key: combined[key] for key in combined_keys}
    summary['packets_4b5c'] = sum(totals[name]['packets_4b5c'] for name in totals)
    summary['fe3_packets'] = sum(totals[name]['fe3_packets'] for name in totals)
    summary['no_fe_packets'] = sum(totals[name]['no_fe_packets'] for name in totals)
    summary['count1'] = {f'{code:02x}': combined[f'count1_{code:02x}'] for code in range(8, 13)}
    summary['count1_fe_window'] = {f'{code:02x}': combined[f'count1_{code:02x}_fe_window']
                                   for code in range(8, 13)}
    summary['calibration'] = calibration(vocab)
    summary['vocab_crosscheck'] = vocab_crosscheck(vocab)
    totals['totals'] = summary
    return totals


def main(description=__doc__):
    parser = argparse.ArgumentParser(description=description)
    parser.parse_args()
    print(json.dumps(study(), indent=2))


if __name__ == '__main__':
    main()