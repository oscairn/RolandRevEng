"""Exact TS808 tap-feedback variations, with auxiliary products kept distinct.

This is a native symbolic comparison of two packet contexts. It is not a global
extension-bit/register decoder and does not change production ISA coverage.
"""
import argparse
import hashlib
import json
from pathlib import Path

from mac_controls_study import data_stores, native_trace, replace_roots, straight_line_window
from mac_study import describe, polynomial
from operand_variants_study import check_bindings
from parent_control_study import NATIVE_SHA256
from stereo_tap_study import expressions


def match_variations(decoded):
    result = []
    for index in range(len(decoded) - 4):
        selected = decoded[index:index + 5]
        (ao, a), (bo, b), (co, c), (do, d), (eo, e) = selected
        if len(a) != 9 or len(b) != 11 or len(c) != 17:
            continue
        first = (a[:5] == [0x5f09, 0x0410, 0x4512, 0x3fe4, 0x7fe6]
                 and d == [0x1005, 0x044b, 0x454f, 0, 4]
                 and len(e) == 12 and e[:6] == [0xb80c, 0x0426, 0x4529, 0x8fe0, 0xcfe2, 0x3fe4])
        second = (a[:7] == [0x4709, 0x044b, 0x454b, 0x3fe4, 0x7fe6, 0, 4]
                  and len(d) == 7 and d[:6] == [0x2207, 0x044b, 0x454f, 0x3fe4, 0, 4]
                  and len(e) == 9 and e[:6] == [0xb809, 0x0403, 0x4503, 0x8fe0, 0xcfe2, 0x3fe4])
        if not (first or second):
            continue
        if (b[:7] != [0xb84b, 0x2403, 0x6507, 0x1fe0, 0x3fe2, 0x5fe4, 0x7fe6]
                or c[:11] != [0x8fd1, 0x044b, 0x454f, 0x1fe4, 0x8fe6, 0x3fe8,
                               0x5fea, 0xcfec, 0x7fee, 2, 6]):
            continue
        if any(selected[i + 1][0] != offset + 2 * len(words)
               for i, (offset, words) in enumerate(selected[:-1])):
            continue
        if not (a[7] == a[8] and b[8] == b[10] and c[13] == c[16]):
            continue
        coefficients = [a[7], b[8], c[13]]
        if len(set(coefficients)) != 3 or any(word >> 12 != 12 for word in coefficients):
            continue
        cuts, state1, state2 = [c[12], c[15]], [b[7], b[9]], [c[11], c[14]]
        if (e[6:8] != state1 or len(set(cuts + state1 + state2)) != 6
                or any(not 0 <= address <= 0x7ff for address in cuts + state1 + state2)):
            continue
        bindings = []
        for channel in range(2):
            bindings.extend(dict(kind=kind, relative=relative, address=address)
                            for kind, relative, address in (
                                ('read', bo + 14 + 4 * channel, state1[channel]),
                                ('read', co + 22 + 6 * channel, state2[channel]),
                                ('write', co + 24 + 6 * channel, cuts[channel]),
                                ('write', eo + 12 + 2 * channel, state1[channel])))
        result.append(dict(offset=ao, end=eo + 2 * len(e), coefficients=[word & 0xfff for word in coefficients],
                           cuts=cuts, first=state1, second=state2, bindings=bindings,
                           auxiliary_packet=bo, first_mac_packet=co, second_mac_packet=do,
                           first_mac_extensions=[2, 6], second_mac_extensions=[0, 4]))
    return result


def check_trace(trace, family):
    wanted_stores = family['cuts'] + family['first']
    stores = data_stores(trace, wanted_stores)
    groups = {address: [event for event in stores if event['key'][2] == address] for address in wanted_stores}
    if any(len(rows) != 1 for rows in groups.values()):
        return dict(verified=False, reason='Need one distinct cut/result store per channel')
    cuts = [groups[address][0] for address in family['cuts']]
    outputs = [groups[address][0] for address in family['first']]
    roots = {event['value']: ('signal', ('stored', event['key'][2])) for event in cuts}
    if len(roots) != 2:
        return dict(verified=False, reason='Input cut values are indistinguishable')
    expected, channels = expressions(family), []
    for channel in range(2):
        cut, output = cuts[channel], outputs[channel]
        if cut['pc'] >= output['pc']:
            return dict(verified=False, reason='Input cut follows its result')
        stages = []
        for stage, value in enumerate(expected[channel]):
            wanted, candidates = polynomial(value), []
            for event in trace:
                if (event['kind'] != 'fp' or event['instruction'] != ('fmul' if stage == 0 else 'fmadd')
                        or event['pc'] >= output['pc'] or stage > 0 and event['pc'] <= cut['pc']):
                    continue
                try:
                    observed = polynomial(replace_roots(event['value'], roots))
                except ValueError:
                    continue
                if observed == wanted:
                    candidates.append(event['pc'])
            if len(candidates) != 1 or stages and candidates[0] <= stages[-1]['pc']:
                return dict(verified=False, reason='Missing, duplicate or reordered arithmetic stage', channel=channel, stage=stage)
            stages.append(dict(pc=candidates[0], expression=describe(wanted)))
        # The compiler computes the auxiliary product first, then captures its
        # unchanged input before the two MACs. Native register preservation is
        # checked separately; a late store is not accepted by equality alone.
        if not stages[0]['pc'] < cut['pc'] < stages[1]['pc']:
            return dict(verified=False, reason='Unsupported auxiliary/cut/MAC ordering')
        try:
            final = polynomial(replace_roots(output['value'], roots))
        except ValueError:
            return dict(verified=False, reason='Opaque result outside the input cut')
        if final != polynomial(expected[channel][-1]):
            return dict(verified=False, reason='State result differs from full accumulated expression')
        channels.append(dict(channel=channel, cut_pc=cut['pc'], store_pc=output['pc'], stages=stages))
    return dict(verified=True, channels=channels)


def first_mac_port_models(family, port_slots):
    """Compare source-port hypotheses without assuming the ports are distinguishable."""
    scaled = expressions(family)[0][0]
    state = ('signal', ('memory', family['first'][0]))
    return {port: polynomial(('add', scaled, ('mul', state, ('coef', slot))))
            for port, slot in port_slots.items()}


def check_auxiliary_cut(code, product_pc, cut_pc):
    """Prove the later store captures an unchanged source of the earlier product."""
    from condition_return_study import preserved
    instructions = {ins.address: ins for ins in code}
    if product_pc >= cut_pc or product_pc not in instructions or cut_pc not in instructions:
        return dict(verified=False, reason='Missing or reversed native cut instructions')
    product, cut = instructions[product_pc], instructions[cut_pc]
    if product.mnemonic != 'fmul' or cut.mnemonic != 'str':
        return dict(verified=False, reason='Expected a native multiply and store')
    source = cut.reg_name(cut.operands[0].reg)
    if not source.startswith('d') or source not in [product.reg_name(op.reg) for op in product.operands[1:]]:
        return dict(verified=False, reason='Store source is not the retained multiply input')
    middle = [ins for ins in code if product_pc < ins.address < cut_pc]
    if [ins.address for ins in middle] != list(range(product_pc + 4, cut_pc, 4)):
        return dict(verified=False, reason='Gap in source-preservation window')
    try:
        preserved(middle, source)
    except ValueError:
        return dict(verified=False, reason='Multiply input overwritten before its cut store')
    return dict(verified=True, source=source, product_pc=product_pc, cut_pc=cut_pc)


def study():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from bmc_dsp import packets
    from header_study import layout
    from transfer_study import constructor_memory, native_accesses, records_from_memory
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded ZENOLOGY arm64 image')
    cls = 'SIM_MFX_TS808'
    length, stream, _, _, program_base, _ = parse.program(cls)
    decoded = packets(stream[:length]); families = match_variations(decoded)
    if len(families) != 2:
        raise ValueError('Expected two independently anchored feedback-variation contexts')
    signals = {address for family in families for key in ('first', 'second') for address in family[key]}
    start, end, _, trace, native = native_trace(cls, signals)
    ctor = parse.parse_ctor(cls); base, count, previous = parse.parse_datsym(cls, ctor)
    lo, hi = lib.func(ctor['ctor']); md = lib.md(); md.detail = True
    constructor = list(md.disasm(lib.Z[lo:hi], lo))
    records = records_from_memory(constructor_memory(constructor, lib.Z), base, count)
    if records != previous:
        raise ValueError('Fresh constructor records differ from getter extraction')
    fields = {base + 8 * index + 4: dict(relative=relative, address=address)
              for index, (relative, address) in enumerate(records)}
    provenance = native_accesses(native, fields, coefficient_pointer_fields(constructor))
    checked = []
    for family in families:
        for offset, words in decoded:
            if family['offset'] <= offset < family['end']:
                layout(words)
        item = dict(family=family, **check_trace(trace, family))
        # Both source-port hypotheses receive the SAME live slot in
        # this stock family. Equality is a counterexample to unique selection.
        models = first_mac_port_models(family, {3: family['coefficients'][1], 7: family['coefficients'][1]})
        item['coefficient_port_ambiguity'] = dict(ports=[3, 7], shared_live_slot=family['coefficients'][1],
                                                indistinguishable=models[3] == models[7],
                                                hypotheses={port: describe(terms) for port, terms in models.items()})
        item['bindings'] = check_bindings(provenance['accesses'], fields, family['bindings'],
                                           {ins.address: ins for ins in native})
        if item['verified']:
            item['auxiliary_cuts'] = [check_auxiliary_cut(native, channel['stages'][0]['pc'], channel['cut_pc'])
                                      for channel in item['channels']]
            native_end = max(channel['store_pc'] for channel in item['channels'])
            coefficient_reads = []
            for slot in family['coefficients']:
                candidates = [row for row in provenance['coefficient_reads'] if row['slot'] == slot and row['pc'] < native_end]
                if len(candidates) != 2:
                    raise ValueError('Expected two separately traced float loads per coefficient slot')
                coefficient_reads.extend(candidates)
            sources = [('coef', slot) for slot in family['coefficients']]
            sources.extend(('signal', ('memory', address)) for key in ('first', 'second') for address in family[key])
            item['coefficient_reads'] = coefficient_reads
            item['native_window'] = straight_line_window(native, trace, sources, native_end,
                                                          [row['pc'] for row in coefficient_reads])
            item['verified'] &= item['native_window']['verified'] and all(row['verified'] for row in item['auxiliary_cuts'])
        item['verified'] &= item['bindings']['verified']
        checked.append(item)
    return dict(native_sha256=NATIVE_SHA256, cls=cls, native_start=start, native_end=end,
                program_base=program_base, comparisons=checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'local/tap-feedback-variation.json')
    args = parser.parse_args()
    result = study(); args.output.write_text(json.dumps(result, indent=2) + '\n')
    for row in result['comparisons']:
        print('MATCH' if row['verified'] else 'UNRESOLVED', hex(row['family']['offset']),
              [[hex(stage['pc']) for stage in channel['stages']] for channel in row.get('channels', [])])


if __name__ == '__main__':
    main()
