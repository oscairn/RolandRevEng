"""Validate the fitted four-operation header rule against every render-list packet.

The rule, recorded in the agent handoff as hypothesis only, ranks
combinations_with_replacement(range(5), 4) under the constraint
sum(kind < 2) <= 2 or (sum(kind < 2) == 3 and last == 2) and indexes that list by
(header >> 8) - 0x40. This cross-check never admits the rule into header_study;
it only searches the prepared packet corpora for counterexamples. Fail closed.
"""
import argparse
import collections
import json
from itertools import combinations_with_replacement
from pathlib import Path
import tempfile

from bmc_dsp import command_count, packets, swap_words
from header_study import UnsupportedLayout, families, layout
from qspi_c1 import read_c1

RULE_SIZE = 57
ANCHORS = {0x47: (0, 0, 4, 4), 0x4e: (0, 1, 4, 4), 0x58: (0, 4, 4, 4),
           0x5f: (1, 1, 4, 4), 0x69: (1, 4, 4, 4), 0x78: (4, 4, 4, 4)}


def ranked_choices():
    """Rebuild the fitted ranking; size and anchors must agree or fail."""
    choices = [tuple(s) for s in combinations_with_replacement(range(5), 4)
               if sum(t < 2 for t in s) <= 2
               or (sum(t < 2 for t in s) == 3 and s[-1] == 2)]
    if len(choices) != RULE_SIZE:
        raise ValueError(f'Fitted ranking has {len(choices)} entries, expected {RULE_SIZE}')
    rule = {0x40 + index: fam for index, fam in enumerate(choices)}
    for code, expected in ANCHORS.items():
        if rule[code] != expected:
            raise ValueError(f'Anchor {code:04x} disagrees: {rule[code]} vs {expected}')
    return rule


def strictly_decodable_codes(rule):
    """Codes whose fitted families contain only long/short/transfer kinds."""
    return {code for code, fam in rule.items() if all(kind in (0, 1, 4) for kind in fam)}


def crosscheck_core(data, segments, rule, counterexamples):
    """Scan render-list segments; every finding appends a counterexample row.

    Data uses the stored LE32 word form; segments carry their own source offsets.
    """
    counts = collections.Counter()
    codes = collections.Counter()
    decoded_codes = collections.Counter()
    for base, length, capacity, source in segments:
        if not length:
            continue
        stream = swap_words(data[source:source + ((length + 3) & ~3)])[:length]
        try:
            decoded = packets(stream)
        except ValueError as error:
            counts['unframeable_segments'] += 1
            continue
        counts['packets'] += len(decoded)
        for offset, words in decoded:
            header = words[0]
            if header & 32 or command_count(header) != 4:
                continue
            counts['count4_packets'] += 1
            code = header >> 8
            if code not in rule:
                counterexamples.append(dict(offset=offset, header=f'{header:04x}',
                                            problem='code outside the fitted ranking range 40..78'))
                continue
            codes[code] += 1
            try:
                decoded_layout = layout(words)
            except UnsupportedLayout:
                counts['unsupported_packets'] += 1
                continue
            except ValueError as error:
                counts['rejected_packets'] += 1
                counterexamples.append(dict(offset=offset, header=f'{header:04x}',
                                            problem=f'strict decode rejected: {error}'))
                continue
            decoded_codes[code] += 1
            counts['decoded_packets'] += 1
            actual = tuple(decoded_layout['families'])
            if actual != rule[code]:
                counterexamples.append(dict(offset=offset, header=f'{header:04x}',
                                            strict_families=list(actual),
                                            fitted_families=list(rule[code])))
    counts['distinct_codes'] = len(codes)
    counts['min_code'] = min(codes) if codes else None
    counts['max_code'] = max(codes) if codes else None
    counts['anchor_decoded'] = sum(decoded_codes[code] for code in ANCHORS)
    counts['nonanchor_decoded'] = counts['decoded_packets'] - counts['anchor_decoded']
    # Deterministic JSON: every count key must exist even when zero.
    for key in ('packets', 'count4_packets', 'decoded_packets', 'unsupported_packets',
                'rejected_packets', 'unframeable_segments'):
        counts.setdefault(key, 0)
    return dict(sorted(counts.items()))


def study(core1=(), qspi=()):
    import lib
    from analyze import core_lists
    from core1 import Core1

    rule = ranked_choices()
    counterexamples = []
    reports = {}
    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    segments = [tuple(segment) for row in inventory['lists'] if row[1] == 0
                for segment in row[3]]
    reports['zen_arm64'] = crosscheck_core(lib.Z, segments, rule, counterexamples)
    for path in core1:
        core = Core1(path)
        segments = [tuple(segment) for row in core_lists(core) for segment in row['segments']]
        reports[path.name] = crosscheck_core(core.data, segments, rule, counterexamples)
    for path in qspi:
        manifest, view = read_c1(path)
        with tempfile.TemporaryDirectory(prefix='header-xcheck-') as directory:
            analysis = Path(directory) / 'analysis.bin'
            analysis.write_bytes(view)
            core = Core1(analysis)
        segments = [tuple(segment) for row in core_lists(core) for segment in row['segments']]
        reports[path.name] = crosscheck_core(core.data, segments, rule, counterexamples)
    if counterexamples:
        raise ValueError(f'Fitted-rule counterexamples: {counterexamples[:10]}')
    return dict(rule_size=len(rule),
                strictly_decodable_codes=sorted(f'{code:04x}' for code in strictly_decodable_codes(rule)),
                counterexamples=counterexamples, images=reports)


def main(description=__doc__):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--core1', type=Path, action='append', default=[])
    parser.add_argument('--qspi', type=Path, action='append', default=[])
    args = parser.parse_args()
    print(json.dumps(study(args.core1, args.qspi), indent=2))


if __name__ == '__main__':
    main()