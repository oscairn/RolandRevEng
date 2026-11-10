"""Exact live-coefficient stereo tap accumulation; offline symbolic evidence only.

The supported five-packet TS808 context keeps earlier shaping opaque. Both main
inputs are independent native store cut points. No decoder/emitter is extended.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bmc_dsp import packets
from mac_controls_study import data_stores, native_trace, replace_roots, straight_line_window
from mac_study import describe, polynomial
from operand_variants_study import check_bindings
from parent_control_study import NATIVE_SHA256


def match_stereo_taps(decoded):
    matches = []
    for index in range(len(decoded) - 4):
        selected = decoded[index:index + 5]
        (ao, a), (bo, b), (co, c), (do, d), (eo, e) = selected
        if [len(words) for _, words in selected] != [5, 13, 11, 5, 10]:
            continue
        if not (a[:4] == [0x2e05, 0x0407, 0x4507, 0x7fe0]
                and b[:8] == [0xb88d, 0x0407, 0x4507, 0x1fe0, 0x5fe2, 0x8fe4, 0xcfe6, 0x7fe8]
                and c[:8] == [0x8f0b, 0x044f, 0x454f, 0x2fe4, 0x6fe6, 0x7fe8, 0, 4]
                and d == [0x1005, 0x048f, 0x458f, 0, 4]
                and e[:5] == [0x5f0a, 0x0424, 0x4527, 0x8fe0, 0xcfe2]):
            continue
        if any(selected[i + 1][0] != offset + 2 * len(words)
               for i, (offset, words) in enumerate(selected[:-1])):
            continue
        coefficients = [a[4], b[12], c[10]]
        if any(word >> 12 != 12 for word in coefficients) or len(set(coefficients)) != 3:
            continue
        first, cuts, second = b[8:10], b[10:12], c[8:10]
        if e[5:7] != first or len(set(first + cuts + second)) != 6:
            continue
        if any(not 0 <= address <= 0x7ff for address in first + cuts + second):
            continue
        bindings = []
        for channel in range(2):
            first_field, second_field, cut_field = bo + 16 + 2 * channel, co + 16 + 2 * channel, bo + 20 + 2 * channel
            # The native code reuses the first state record for its later write;
            # it does not have another constructor record owning that wire field.
            bindings.extend([
                dict(kind='read', relative=first_field, address=first[channel]),
                dict(kind='read', relative=second_field, address=second[channel]),
                dict(kind='write', relative=cut_field, address=cuts[channel]),
                dict(kind='write', relative=first_field, address=first[channel],
                     wire_field=eo + 10 + 2 * channel, alias_of=first_field),
            ])
        matches.append(dict(offset=ao, end=eo + 2 * len(e), coefficients=[word & 0xfff for word in coefficients],
                            cuts=cuts, first=first, second=second, bindings=bindings,
                            arithmetic_packets=[bo, co, do], stores_packet=eo))
    return matches


def expressions(family):
    gain, first, second = [('coef', slot) for slot in family['coefficients']]
    result = {}
    for channel in range(2):
        incoming = ('signal', ('stored', family['cuts'][channel]))
        scaled = ('mul', incoming, gain)
        tap1 = ('add', scaled, ('mul', ('signal', ('memory', family['first'][channel])), first))
        tap2 = ('add', tap1, ('mul', ('signal', ('memory', family['second'][channel])), second))
        result[channel] = [scaled, tap1, tap2]
    return result


def check_trace(trace, family):
    stores = data_stores(trace, family['cuts'] + family['first'])
    grouped = {address: [event for event in stores if event['key'][2] == address]
               for address in family['cuts'] + family['first']}
    if any(len(events) != 1 for events in grouped.values()):
        return dict(verified=False, reason='Need exactly one input cut and output store per channel')
    cuts = [grouped[address][0] for address in family['cuts']]
    outputs = [grouped[address][0] for address in family['first']]
    roots = {event['value']: ('signal', ('stored', event['key'][2])) for event in cuts}
    if len(roots) != 2 or max(event['pc'] for event in cuts) >= min(event['pc'] for event in outputs):
        return dict(verified=False, reason='Equal, overwritten or late input cut points')
    expected = expressions(family)
    matched = []
    for channel in range(2):
        stages = []
        for index, expression in enumerate(expected[channel]):
            wanted = polynomial(expression)
            candidates = []
            for event in trace:
                if (event['kind'] != 'fp' or event['instruction'] != ('fmul' if index == 0 else 'fmadd')
                        or not max(cut['pc'] for cut in cuts) < event['pc'] < outputs[channel]['pc']):
                    continue
                try:
                    observed = polynomial(replace_roots(event['value'], roots))
                except ValueError:
                    continue
                if observed == wanted:
                    candidates.append(event['pc'])
            if len(candidates) != 1 or stages and candidates[0] <= stages[-1]['pc']:
                return dict(verified=False, reason='Missing, ambiguous or reordered native arithmetic stage',
                            channel=channel, stage=index)
            stages.append(dict(pc=candidates[0], expression=describe(wanted)))
        try:
            observed = polynomial(replace_roots(outputs[channel]['value'], roots))
        except ValueError:
            return dict(verified=False, reason='Opaque final state store')
        if observed != polynomial(expected[channel][-1]):
            return dict(verified=False, reason='Final store differs from accumulated result')
        matched.append(dict(channel=channel, cut_pc=cuts[channel]['pc'], store_pc=outputs[channel]['pc'], stages=stages))
    return dict(verified=True, channels=matched)


def study():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from header_study import layout
    from transfer_study import constructor_memory, native_accesses, records_from_memory
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded ZENOLOGY arm64 image')
    cls = 'SIM_MFX_TS808'
    length, stream, _, _, program_base, _ = parse.program(cls)
    families = match_stereo_taps(packets(stream[:length]))
    if len(families) != 1:
        raise ValueError('Expected exactly one studied TS808 context')
    family = families[0]
    for offset, words in packets(stream[:length]):
        if family['offset'] <= offset < family['end']:
            layout(words)
    signals = set(family['first'] + family['second'])
    start, end, _, trace, native = native_trace(cls, signals)
    ctor = parse.parse_ctor(cls)
    base, count, previous = parse.parse_datsym(cls, ctor)
    lo, hi = lib.func(ctor['ctor']); md = lib.md(); md.detail = True
    constructor = list(md.disasm(lib.Z[lo:hi], lo))
    records = records_from_memory(constructor_memory(constructor, lib.Z), base, count)
    if records != previous:
        raise ValueError('Fresh constructor memory differs from getter records')
    fields = {base + 8 * index + 4: dict(relative=relative, address=address)
              for index, (relative, address) in enumerate(records)}
    provenance = native_accesses(native, fields, coefficient_pointer_fields(constructor))
    result = check_trace(trace, family)
    result.update(cls=cls, native_sha256=NATIVE_SHA256, native_start=start, native_end=end,
                  program_base=program_base, family=family)
    result['bindings'] = check_bindings(provenance['accesses'], fields, family['bindings'],
                                       {ins.address: ins for ins in native})
    # In addition to constructor pointer arithmetic, require fresh float loads
    # through each live coefficient record in this comparison's native window.
    if result['verified']:
        native_end = max(channel['store_pc'] for channel in result['channels'])
        native_start = min(channel['cut_pc'] for channel in result['channels'])
        coefficient_reads = []
        for slot in family['coefficients']:
            candidates = [row for row in provenance['coefficient_reads']
                          if row['slot'] == slot and row['pc'] < native_end]
            if len(candidates) != 1:
                raise ValueError('Expected one distinct coefficient load per live slot')
            coefficient_reads.append(candidates[0])
        native_start = min(native_start, *(row['pc'] for row in coefficient_reads))
        sources = [('coef', slot) for slot in family['coefficients']]
        sources.extend(('signal', ('memory', address)) for address in signals)
        result['native_window'] = straight_line_window(native, trace, sources, native_end, [native_start])
        result['coefficient_reads'] = coefficient_reads
        result['verified'] &= result['native_window']['verified']
    result['verified'] &= result['bindings']['verified']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'local/stereo-tap-study.json')
    args = parser.parse_args()
    result = study()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('MATCH' if result['verified'] else 'UNRESOLVED', result['cls'],
          hex(result['family']['offset']), [(row['channel'], [hex(stage['pc']) for stage in row['stages']])
                                          for row in result.get('channels', [])])


if __name__ == '__main__':
    main()
