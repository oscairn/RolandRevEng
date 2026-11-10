"""Check the exact LFCOMP port-2 MAC pair and same-packet store ordering.

Native pre-MAC stores supply independent wet-value cut points. Earlier filters are
not interpreted. This proves formal dataflow for the selected encodings, not DSP
precision, scheduling latency or arbitrary long-operation bitfields.
"""
import argparse
import json
from pathlib import Path

from alu_study import coefficient_pointer_fields, native_values
from mac_study import polynomial, describe
from bmc_dsp import packets


DATA_BASE = ('path', ('path', ('path', ('path', ('wrapper',), 8), 0x18), 0x10), 0x18)


def replace_roots(value, roots):
    if value in roots:
        return roots[value]
    if value[0] in ('add', 'sub', 'mul'):
        return (value[0], replace_roots(value[1], roots), replace_roots(value[2], roots))
    return value


def match_port2_family(decoded):
    for index in range(len(decoded) - 3):
        a, b, c, d = [row[1] for row in decoded[index:index + 4]]
        if not (len(a) == len(b) == 14 and len(c) == 7 and len(d) == 3):
            continue
        if not (a[:8] == [0x8f0e, 0x04aa, 0x45ad, 0x1fe4, 0x3fe6, 0x5fe8, 0, 4]
                and b[:8] == [0x8f0e, 0x046a, 0x456d, 0x1fe4, 0x2fe6, 0x5fe8, 0, 4]
                and a[11:] == b[11:] == [0, 0, 0]
                and c[:5] == [0x2b07, 0x080b, 0x8fe2, 0xcfe4, 0x1280]
                and d == [0x0803, 0x490b, 0x5280]):
            continue
        if not (a[9] >> 12 == b[9] >> 12 == 12 and a[9] != b[9]):
            continue
        wet, dry = c[5:], [b[8], b[10]]
        if len(set(wet + dry)) != 4 or any(address >> 12 for address in wet + dry):
            continue
        return dict(offset=decoded[index][0], wet_addresses=wet, dry_addresses=dry,
                    wet_coefficient=a[9] & 0xfff, dry_coefficient=b[9] & 0xfff)
    return None


def port2_outputs(family):
    return {channel: ('add', ('mul', ('signal', ('wet', wet)), ('coef', family['wet_coefficient'])),
                      ('mul', ('signal', ('memory', dry)), ('coef', family['dry_coefficient'])))
            for channel, (wet, dry) in enumerate(zip(family['wet_addresses'], family['dry_addresses']))}


def data_stores(trace, addresses):
    return [event for event in trace if event['kind'] == 'store'
            and event['key'][:2] == ('indexed', DATA_BASE) and event['key'][2] in addresses]


def check_port2_trace(trace, family):
    """Compare only candidates after both independently distinguishable wet stores."""
    expected = {channel: polynomial(value) for channel, value in port2_outputs(family).items()}
    latest, matches = {}, {0: [], 1: []}
    for event in trace:
        if event['kind'] == 'store' and event['key'][:2] == ('indexed', DATA_BASE):
            address = event['key'][2]
            if address in family['wet_addresses']:
                latest[address] = event
        if event['kind'] != 'fp' or event['instruction'] != 'fmadd' or len(latest) != 2:
            continue
        roots = {latest[address]['value']: ('signal', ('wet', address))
                 for address in family['wet_addresses']}
        if len(roots) != 2:
            continue
        try:
            terms = polynomial(replace_roots(event['value'], roots))
        except ValueError:
            continue
        for channel in matches:
            if terms == expected[channel]:
                matches[channel].append(dict(pc=event['pc'], expression=describe(terms),
                                             cut_stores={address: latest[address]['pc']
                                                         for address in family['wet_addresses']}))
    return dict(verified=all(len(found) == 1 for found in matches.values()), matches=matches)


def match_gain_store_family(decoded):
    for index in range(len(decoded) - 3):
        a, b, c, d = [row[1] for row in decoded[index:index + 4]]
        if not (len(a) == 10 and len(b) == 9):
            continue
        if (a[:7] != [0x220a, 0x0466, 0x4569, 0x3fe4, 0, 4, 0xc003]
                or a[7:] != [0, 0, 0]
                or b[:7] != [0xb809, 0x0403, 0x4503, 0x3fe0, 0x8fe2, 0xcfe4, 0xc000]
                or c != [0x1503, 0x0403, 0x4503]
                or d != [0x3d06, 0x00f8, 0x8fe0, 0xcfe2, 0x2018, 0x2019]):
            continue
        if b[7] == b[8] or b[7] >> 12 or b[8] >> 12:
            continue
        return dict(offset=decoded[index + 1][0], addresses=b[7:], gain=3, master=0)
    return None


def check_gain_store_trace(trace, outputs, family):
    stores = data_stores(trace, family['addresses'])
    if len(stores) != 2 or len({event['key'][2] for event in stores}) != 2:
        return dict(verified=False, reason='Expected one store per cut point')
    roots = {event['value']: ('signal', ('stored', event['key'][2])) for event in stores}
    if len(roots) != 2 or set(outputs) != {0, 1}:
        return dict(verified=False, reason='Cut points/output channels are not independent')
    observed, expected, after_gain = {}, {}, {}
    try:
        for channel, address in enumerate(family['addresses']):
            observed[channel] = polynomial(replace_roots(outputs[channel], roots))
            stored = ('signal', ('stored', address))
            expected[channel] = polynomial(('mul', ('mul', stored, ('coef', family['gain'])),
                                             ('coef', family['master'])))
            after_gain[channel] = polynomial(('mul', stored, ('coef', family['master'])))
    except ValueError:
        return dict(verified=False, reason='Opaque arithmetic after store cut points')
    return dict(verified=observed == expected and observed != after_gain,
                stored_before_arithmetic=True if observed == expected else None,
                store_pcs={event['key'][2]: event['pc'] for event in stores},
                observed={channel: describe(terms) for channel, terms in observed.items()})


def match_allpass_chains(decoded):
    """Admit the exact alternating four-stage LINEDRIVE family only."""
    result = []
    for index in range(len(decoded) - 6):
        a, b, c, d, e, f, g = [row[1] for row in decoded[index:index + 7]]
        if [len(row) for row in (a, b, c, d, e, f, g)] != [5, 7, 5, 7, 7, 5, 5]:
            continue
        if not (a[:3] == [0x1e05, 0x1fe0, 0x0fe2]
                and b[:4] == [0x3e07, 0x2fe0, 0x3fe2, 0x8fe4]
                and c[:4] == [0x1405, 0x0e0b, 0x1fe2, 0x22c1]
                and d[:5] == [0x2b07, 0x0e0b, 0x2fe2, 0x8fe4, 0x12c2]
                and e[:5] == [0x2b07, 0x0e0b, 0x1fe2, 0x8fe4, 0x22c1]
                and f[:4] == [0x1405, 0x0e0b, 0x8fe2, 0x12c2]
                and g[:3] == [0x1e05, 0x8fe0, 0x8fe2]):
            continue
        sources = [a[4], a[3], b[4], b[5], c[4], d[5], e[5]]
        targets = [b[6], d[6], e[6], f[4], g[3], g[4]]
        if len(set(sources + targets)) != 13 or any(address >> 12 for address in sources + targets):
            continue
        result.append(dict(offset=decoded[index][0], sources=sources, targets=targets))
    return result


def allpass_stores(chain):
    main, one, two, factor, next_one, next_two, last_one = [
        ('signal', ('memory', address)) for address in chain['sources']]
    previous = main
    stage0 = ('add', one, ('mul', ('sub', two, main), factor))
    stage1 = ('add', two, ('mul', ('sub', next_one, stage0), factor))
    stage2 = ('add', next_one, ('mul', ('sub', next_two, stage1), factor))
    stage3 = ('add', next_two, ('mul', ('sub', last_one, stage2), factor))
    return dict(zip(chain['targets'], (previous, stage0, stage1, stage2, stage3, stage3)))


def check_allpass_trace(trace, chain):
    expected = allpass_stores(chain)
    found = data_stores(trace, expected)
    matches = []
    for address, expression in expected.items():
        stores = [event for event in found if event['key'][2] == address]
        if len(stores) != 1:
            return dict(verified=False, reason='Expected exactly one store at each stage', address=address)
        try:
            observed, wanted = polynomial(stores[0]['value']), polynomial(expression)
        except ValueError:
            return dict(verified=False, reason='Opaque native stage expression', address=address)
        if observed != wanted:
            return dict(verified=False, reason='Native and predicted stage differ', address=address)
        matches.append(dict(address=address, pc=stores[0]['pc'], expression=describe(observed)))
    return dict(verified=True, stores=matches)


def straight_line_window(code, trace, sources, end, extra_starts=()):
    """Require fresh source definitions in one completely decoded branch-free block."""
    import capstone
    starts = list(extra_starts)
    for source in sources:
        loads = [event['pc'] for event in trace if event['kind'] == 'fp'
                 and event['value'] == source and event['pc'] <= end]
        if not loads:
            return dict(verified=False, reason='No source definition in native trace')
        starts.append(max(loads))
    if not starts:
        return dict(verified=False, reason='No comparison window')
    start = min(starts)
    instructions = [ins for ins in code if start <= ins.address <= end]
    contiguous = [ins.address for ins in instructions] == list(range(start, end + 4, 4))
    transfers = [ins.address for ins in instructions
                 if any(ins.group(group) for group in (capstone.CS_GRP_JUMP, capstone.CS_GRP_CALL,
                                                       capstone.CS_GRP_RET, capstone.CS_GRP_INT))]
    return dict(start=start, end=end, verified=contiguous and not transfers,
                control_transfers=transfers)


def native_trace(cls, signal_addresses):
    import lib
    import parse
    constructor = parse.parse_ctor(cls)
    start, end = lib.func(constructor['ctor'])
    md = lib.md(); md.detail = True
    pointers = coefficient_pointer_fields(md.disasm(lib.Z[start:end], start))
    if pointers != {offset: index for index, offset in enumerate(constructor['tail'])}:
        raise ValueError('Constructor coefficient-pointer provenance unresolved')
    base, _, records = parse.parse_datsym(cls, constructor)
    addresses = {base + 8 * index + 4: address for index, (offset, address) in enumerate(records)
                 if offset is not None}
    start, end, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    trace = []
    outputs, _ = native_values(native, pointers, addresses, signal_addresses, trace=trace)
    return start, end, outputs, trace, native


def study():
    import parse
    cls = 'SIM_MFX_LFCOMP'
    length, stream, *_ = parse.program(cls)
    decoded = packets(stream[:length])
    mac, gain = match_port2_family(decoded), match_gain_store_family(decoded)
    if mac is None or gain is None:
        raise ValueError('Local artifact does not have the studied LFCOMP families')
    start, end, outputs, trace, native = native_trace(cls, mac['dry_addresses'])
    result = dict(cls=cls, native_start=start, native_end=end,
                  port2_mac=dict(family=mac, **check_port2_trace(trace, mac)),
                  gain_store_order=dict(family=gain, **check_gain_store_trace(trace, outputs, gain)))
    mac_result, gain_result = result['port2_mac'], result['gain_store_order']
    if mac_result['verified']:
        mac_end = max(match['pc'] for matches in mac_result['matches'].values() for match in matches)
        cut_starts = [pc for matches in mac_result['matches'].values()
                      for match in matches for pc in match['cut_stores'].values()]
        sources = [('signal', ('memory', address)) for address in mac['dry_addresses']]
        sources.extend(('coef', slot) for slot in (mac['dry_coefficient'], mac['wet_coefficient']))
        mac_result['native_window'] = straight_line_window(native, trace, sources, mac_end, cut_starts)
        mac_result['verified'] &= mac_result['native_window']['verified']
    if gain_result['verified']:
        output_end = max(event['pc'] for event in trace if event['kind'] == 'store'
                         and event['key'][0] == 'direct' and event['key'][1][0] == 'output')
        sources = [('coef', gain['gain']), ('coef', gain['master'])]
        gain_result['native_window'] = straight_line_window(native, trace, sources, output_end,
                                                           gain_result['store_pcs'].values())
        gain_result['verified'] &= gain_result['native_window']['verified']
    length, stream, *_ = parse.program('SIM_MFX_LINEDRIVE')
    chains = match_allpass_chains(packets(stream[:length]))
    sources = {address for chain in chains for address in chain['sources']}
    start, end, _, trace, native = native_trace('SIM_MFX_LINEDRIVE', sources)
    checked = []
    for chain in chains:
        item = dict(family=chain, **check_allpass_trace(trace, chain))
        if item['verified']:
            sources = [('signal', ('memory', address)) for address in chain['sources']]
            item['native_window'] = straight_line_window(native, trace, sources,
                                                         max(store['pc'] for store in item['stores']))
            item['verified'] &= item['native_window']['verified']
        checked.append(item)
    result['allpass_chains'] = dict(cls='SIM_MFX_LINEDRIVE', native_start=start, native_end=end, chains=checked)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'local/mac_controls_study.json')
    args = parser.parse_args()
    result = study()
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
