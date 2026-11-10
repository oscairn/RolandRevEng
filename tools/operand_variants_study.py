"""Exact-context MAC source/destination comparisons; static native dataflow only.

The FETDRIVE precursor remains opaque. Its two independent stores delimit the
incoming A and factor instead of assigning semantics to that precursor.
"""
import json

from bmc_dsp import packets
from mac_controls_study import (data_stores, native_trace, replace_roots,
                                straight_line_window)
from mac_study import describe, polynomial


def match_mono_prefix(decoded):
    if len(decoded) < 3:
        return None
    a, b, c = [words for _, words in decoded[:3]]
    if not (len(a) == 7 and a[:6] == [0x3e07, 0x0fe0, 0x4fe2, 0x3fe4, 0x2016, 0x2017]
            and a[6] >> 12 == 12 and b == [0x0803, 0x080b, 0x42c0]
            and len(c) == 3 and c[:2] == [0x0c03, 0x8fe0] and 0 <= c[2] <= 0x7ff):
        return None
    return dict(offset=decoded[0][0], coefficient=a[6] & 0xfff, target=c[2],
                bindings=[dict(kind='write', relative=decoded[2][0] + 4, address=c[2])])


def match_cross_allpass(decoded):
    result = []
    for index in range(len(decoded) - 2):
        (offset, a), (middle, b), (last, c) = decoded[index:index + 3]
        if not (len(a) == 8 and a[:5] == [0x7308, 0xbedb, 0x1fe0, 0x2fe2, 0x8fe4]
                and len(b) == 5 and b[:4] == [0x1405, 0x4e0b, 0xbfe2, 0x22c1]
                and len(c) == 3 and c[:2] == [0x0c03, 0xcfe0]):
            continue
        one, two, incoming, factor, target = a[5:] + [b[4], c[2]]
        resources = [one, two, incoming, factor, target]
        if len(set(resources)) != 5 or any(not 0 <= value <= 0x7ff for value in resources):
            continue
        bindings = [dict(kind=kind, relative=position, address=address)
                    for kind, position, address in (
                        ('read', offset + 10, one), ('read', offset + 12, two),
                        ('write', offset + 14, incoming), ('write', middle + 8, factor),
                        ('write', last + 4, target))]
        result.append(dict(offset=offset, one=one, two=two, incoming=incoming,
                           factor=factor, target=target, bindings=bindings))
    return result


def check_mono_trace(trace, family):
    stores = data_stores(trace, [family['target']])
    if len(stores) != 1:
        return dict(verified=False, reason='Expected one mono result store')
    expected = ('mul', ('add', ('signal', ('input', 0)), ('signal', ('input', 1))),
                ('coef', family['coefficient']))
    try:
        wanted, observed = polynomial(expected), polynomial(stores[0]['value'])
    except ValueError:
        return dict(verified=False, reason='Opaque mono result')
    return dict(verified=wanted == observed, end=stores[0]['pc'], expression=describe(observed))


def check_cross_trace(trace, family):
    addresses = [family[key] for key in ('incoming', 'factor', 'target')]
    stores = data_stores(trace, addresses)
    if len(stores) != 3 or {item['key'][2] for item in stores} != set(addresses):
        return dict(verified=False, reason='Expected one store per independent cutpoint/result')
    by_address = {item['key'][2]: item for item in stores}
    incoming, factor, target = [by_address[address] for address in addresses]
    roots = {item['value']: ('signal', ('stored', item['key'][2])) for item in (incoming, factor)}
    if len(roots) != 2 or not incoming['pc'] < factor['pc'] < target['pc']:
        return dict(verified=False, reason='Cutpoints are equal or not before the result')
    expected = ('add', ('signal', ('memory', family['one'])),
                ('mul', ('sub', ('signal', ('memory', family['two'])),
                         ('signal', ('stored', family['incoming']))),
                 ('signal', ('stored', family['factor']))))
    try:
        wanted = polynomial(expected)
        observed = polynomial(replace_roots(target['value'], roots))
    except ValueError:
        return dict(verified=False, reason='Opaque arithmetic outside cutpoints')
    return dict(verified=wanted == observed, end=target['pc'],
                cut_stores=[incoming['pc'], factor['pc']], expression=describe(observed))


def check_bindings(accesses, fields, expected, instructions):
    """Require the exact constructor record, pointer path and scaled double access."""
    from capstone import arm64 as a64
    matched = []
    for binding in expected:
        candidates = [access for access in accesses if access['kind'] == binding['kind']
                      and any(fields[field]['relative'] == binding['relative'] for field in access['fields'])]
        if len(candidates) != 1:
            return dict(verified=False, reason='Missing or ambiguous record access', binding=binding)
        access = candidates[0]
        if (len(access['fields']) != 1 or access['kind'] != binding['kind']
                or access['path'] != ['wrapper', 8, 0x18, 0x10, 0x18] or access['mask'] != 0x7ff
                or fields[access['fields'][0]]['address'] != binding['address']):
            return dict(verified=False, reason='Record identity, data path or mask differs', binding=binding)
        ins = instructions[access['pc']]
        mem = ins.operands[-1]
        if (ins.mnemonic != ('ldr' if binding['kind'] == 'read' else 'str')
                or not ins.reg_name(ins.operands[0].reg).startswith('d') or ins.writeback
                or mem.type != a64.ARM64_OP_MEM or mem.mem.disp or not mem.mem.index
                or mem.ext != a64.ARM64_EXT_UXTW or mem.shift.type != a64.ARM64_SFT_LSL
                or mem.shift.value != 3):
            return dict(verified=False, reason='Not an unsigned scaled double access', binding=binding)
        matched.append(dict(**binding, pc=access['pc'], object_field=access['fields'][0]))
    return dict(verified=True, accesses=matched)


def study():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from transfer_study import constructor_memory, native_accesses, records_from_memory

    results = []
    for cls in ('SIM_MFX_CHO_JU106', 'SIM_MFX_FETDRIVE'):
        length, stream, *_ = parse.program(cls)
        decoded = packets(stream[:length])
        families = ([match_mono_prefix(decoded)] if cls.endswith('JU106') else match_cross_allpass(decoded))
        if not families or any(family is None for family in families):
            raise ValueError(f'{cls}: missing studied encoding')
        signals = {family[key] for family in families for key in ('one', 'two') if key in family}
        start, end, _, trace, native = native_trace(cls, signals or {families[0]['target']})
        ctor = parse.parse_ctor(cls)
        base, count, old = parse.parse_datsym(cls, ctor)
        lo, hi = lib.func(ctor['ctor']); md = lib.md(); md.detail = True
        constructor = list(md.disasm(lib.Z[lo:hi], lo))
        records = records_from_memory(constructor_memory(constructor, lib.Z), base, count)
        if records != old:
            raise ValueError(f'{cls}: independent constructor records differ')
        fields = {base + 8 * index + 4: dict(relative=relative, address=address)
                  for index, (relative, address) in enumerate(records)}
        accesses = native_accesses(native, fields, coefficient_pointer_fields(constructor))['accesses']
        checked = []
        for family in families:
            item = (check_mono_trace(trace, family) if 'coefficient' in family
                    else check_cross_trace(trace, family))
            item['family'] = family
            item['provenance'] = check_bindings(accesses, fields, family['bindings'],
                                                {ins.address: ins for ins in native})
            if item['verified']:
                sources = ([('signal', ('input', channel)) for channel in (0, 1)]
                           + [('coef', family['coefficient'])] if 'coefficient' in family else
                           [('signal', ('memory', family[key])) for key in ('one', 'two')])
                item['native_window'] = straight_line_window(native, trace, sources, item['end'],
                                                              item.get('cut_stores', ()))
                item['verified'] &= item['native_window']['verified']
            item['verified'] &= item['provenance']['verified']
            checked.append(item)
        results.append(dict(cls=cls, native_start=start, native_end=end, comparisons=checked))
    return results


if __name__ == '__main__':
    from pathlib import Path
    result = study()
    (Path(__file__).resolve().parents[1] / 'local/operand-variants-study.json').write_text(
        json.dumps(result, indent=2) + '\n')
    for row in result:
        for item in row['comparisons']:
            print(row['cls'], hex(item['family']['offset']), 'MATCH' if item['verified'] else 'UNRESOLVED')
