"""Compare one exact dry/wet MAC encoding family with native symbolic expressions.

Unknown extension forms and opaque native values remain unresolved. Equality is
formal polynomial equality, not a floating-point or hardware timing guarantee.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from alu_study import coefficient_pointer_fields, native_values
from bmc_dsp import command_count, packets


def polynomial(value):
    """Normalize a bounded sum/product of independent coefficient/signal symbols."""
    if value[0] in ('coef', 'signal'):
        return Counter({(value,): 1})
    if value[0] not in ('add', 'mul'):
        raise ValueError('Opaque or unsupported arithmetic in output expression')
    left, right = polynomial(value[1]), polynomial(value[2])
    if value[0] == 'add':
        result = left + right
    else:
        result = Counter()
        for a, ca in left.items():
            for b, cb in right.items():
                result[tuple(sorted(a + b))] += ca * cb
                if len(result) > 32:
                    raise ValueError('Expression exceeds this bounded MAC study')
    if len(result) > 32:
        raise ValueError('Expression exceeds this bounded MAC study')
    return result


def describe(terms):
    def label(symbol):
        if symbol[0] == 'coef':
            return f'C{symbol[1]}'
        kind, index = symbol[1]
        return f'input{index}' if kind == 'input' else f'memory{index:#x}'
    return [{'coefficient': count, 'factors': [label(symbol) for symbol in symbols]}
            for symbols, count in sorted(terms.items())]


def match_dry_wet_family(decoded):
    """Recognize an exact encoding pair, without generalizing extension bits."""
    for index in range(len(decoded) - 5):
        rows = [row[1] for row in decoded[index:index + 6]]
        a, b, c, d, e, f = rows
        if not (len(a) == len(b) == len(d) == len(e) == 5 and len(c) == 7 and len(f) == 3):
            continue
        if not (a[:4] == [0x1e05, 0x0fe0, 0x3fe2, 0x2016] and b[:3] == [0x1e05, 0x1fe0, 0x7fe2]
                and c[:6] == [0x2b07, 0x080b, 0x4fe2, 0x5fe4, 0x13c0, 0x2017]
                and d[:4] == [0x1405, 0x490b, 0x3fe2, 0x53c0]
                and e[:4] == [0x2e05, 0x0403, 0x4503, 0x3fe0] and f == [0x1503, 0x0403, 0x4503]):
            continue
        coefficients = [a[4], b[4], d[4], e[4]]
        wet = [b[3], c[6]]
        if not all(word >> 12 == 12 for word in coefficients) or any(word >> 12 != 0 for word in wet):
            continue
        if len(set(coefficients)) != 4 or wet[0] == wet[1]:
            continue
        return dict(offset=decoded[index][0], wet_addresses=wet,
                    coefficient_slots=[word & 0xfff for word in coefficients])
    return None


def predicted_outputs(family):
    dry, wet, post, master = [('coef', slot) for slot in family['coefficient_slots']]
    result = {}
    for channel, address in enumerate(family['wet_addresses']):
        mix = ('add', ('mul', ('signal', ('input', channel)), dry),
               ('mul', ('signal', ('memory', address)), wet))
        result[channel] = ('mul', ('mul', mix, post), master)
    return result


def study():
    import lib
    import parse
    results = []
    for cls, (_, _, lists) in sorted(lib.pairs().items()):
        if not any(item[1] == 0 for item in lists or []):
            continue
        length, stream, *_ = parse.program(cls)
        decoded = packets(stream[:length])
        control_words = {word for _, words in decoded for word in words[1:1 + command_count(words[0])]}
        if not {0x080b, 0x490b} <= control_words:
            continue
        family = match_dry_wet_family(decoded)
        if family is None:
            results.append(dict(cls=cls, status='unsupported encoding family'))
            continue
        constructor = parse.parse_ctor(cls)
        ctor_start, ctor_end = lib.func(constructor['ctor'])
        decoder = lib.md(); decoder.detail = True
        pointers = coefficient_pointer_fields(decoder.disasm(lib.Z[ctor_start:ctor_end], ctor_start))
        if pointers != {offset: index for index, offset in enumerate(constructor['tail'])}:
            results.append(dict(cls=cls, status='unresolved constructor pointer provenance'))
            continue
        base, _, records = parse.parse_datsym(cls, constructor)
        addresses = {base + 8 * i + 4: address for i, (offset, address) in enumerate(records) if offset is not None}
        start, end, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
        observed, _ = native_values(native, pointers, addresses, family['wet_addresses'])
        try:
            expected_terms = {channel: polynomial(value) for channel, value in predicted_outputs(family).items()}
            observed_terms = {channel: polynomial(value) for channel, value in observed.items()}
        except ValueError as error:
            results.append(dict(cls=cls, status='unresolved native expression', error=str(error)))
            continue
        results.append(dict(cls=cls, status='matched' if expected_terms == observed_terms else 'different',
                            native_start=start, native_end=end, family=family,
                            expected={channel: describe(terms) for channel, terms in expected_terms.items()},
                            observed={channel: describe(terms) for channel, terms in observed_terms.items()}))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'local/mac_study.json')
    args = parser.parse_args()
    results = study()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    for item in results:
        print(item['cls'], item['status'])
        if item['status'] == 'matched':
            print(' ', item['family'])
            print(' ', item['observed'])
    print(f'{sum(r["status"] == "matched" for r in results)}/{len(results)} candidate classes matched')


if __name__ == '__main__':
    main()
