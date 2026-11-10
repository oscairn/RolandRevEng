"""Partial BMC operand-layout study; no arithmetic or hardware execution.

Unrecognized header families and long-operation subtypes fail closed. Local corpus
imports are lazy so the layout checks can run without any vendor artifact.
"""
from itertools import combinations_with_replacement
import json
from pathlib import Path
import collections

from bmc_dsp import command_count, packets, swap_words


class UnsupportedLayout(ValueError):
    pass


LITERAL_WIDTH = (0, 2, 3, 4)


def families(header):
    """Classify base-op families; higher-arity classifications remain candidates.

    layout() deliberately admits a narrower independently checked subset.
    """
    if header in (1, 31):
        return ()
    code, count = header >> 8, command_count(header)
    if count == 1 and 8 <= code <= 12:
        return (code - 8,)
    if count == 2 and 16 <= code <= 30:
        return tuple(combinations_with_replacement(range(5), 2))[code - 16]
    if count == 3 and 32 <= code <= 62:
        # This restricted rank is tested against payload positions; it is not a
        # claimed global header enumeration for packets with four or more ops.
        choices = [seq for seq in combinations_with_replacement(range(5), 3)
                   if sum(kind in (0, 1) for kind in seq) <= 2]
        return choices[code - 32]
    observed = {0x47: (0, 0, 4, 4), 0x58: (0, 4, 4, 4), 0x5f: (1, 1, 4, 4),
                0x69: (1, 4, 4, 4), 0x78: (4, 4, 4, 4),
                0xab: (0, 4, 4, 4, 4)}
    if code in observed and count == len(observed[code]):
        return observed[code]
    if code == 0xb8:
        return (1, 1) + (4,) * (count - 2)
    if code == 0xe4:
        return (4,) * count
    raise UnsupportedLayout(f'Unresolved header family {header:04x}')


SPECIAL_SHORT = frozenset((0x4091, 0x0094, 0x2091, 0x3092, 0x1090))


def reference(code, payload_bytes):
    """Decode a six-bit ALU operand reference, without arithmetic semantics."""
    if not isinstance(code, int) or not 0 <= code < 64 or payload_bytes < 0:
        raise ValueError('Invalid operand code or payload size')
    width, index = LITERAL_WIDTH[code >> 4], code & 15
    if not width:
        return dict(role='register', index=index)
    if index + width > payload_bytes:
        raise ValueError('Literal reference is outside the common payload')
    return dict(role='literal', offset=index, width=width)


def layout(words):
    """Resolve the supported base-op/reference layouts within a single packet.

    The bounded subset is one-op long ALU, one/two-op short ALU, pure indexed
    transfers, and the observed 47xx pair-of-long-ops/two-transfers form. Returned
    byte offsets count from packet start. Other mixed families fail closed.
    """
    if not words:
        raise ValueError('Empty packet')
    expected = 1 if words[0] in (1, 31) else words[0] & 31
    if words[0] & 32 or len(words) != expected:
        raise ValueError('Packet length is not valid for the observed header subset')
    types = families(words[0])
    count = command_count(words[0])
    if len(types) != count:
        raise ValueError('Operation-family count mismatch')
    if words[0] in (1, 31):
        if len(words) != 1:
            raise ValueError('Compact packet has a payload')
        return dict(families=[], fields=[], registers=[], padding=0)
    if types not in ((0,), (1,), (1, 1), (0, 0, 4, 4)) and any(kind != 4 for kind in types):
        raise UnsupportedLayout('Mixed or miscellaneous operation layouts remain unresolved')
    payload, size = 2 * (count + 1), 2 * len(words)
    if payload > size:
        raise ValueError('Truncated base-op area')
    fields, registers, extensions_seen = [], [], 0
    for index, (kind, control) in enumerate(zip(types, words[1:])):
        if kind in (0, 1):
            if kind == 1 and control in SPECIAL_SHORT:
                raise UnsupportedLayout('Known special short operation has a different operand syntax')
            codes = [control & 63]
            if kind == 0:
                extension_offset = payload + 2 * extensions_seen
                if extension_offset + 2 > size:
                    raise ValueError('Missing long-operation extension word')
                extension = words[extension_offset // 2]
                fields.append(dict(operation=index, role='extension', offset=extension_offset, width=2))
                extensions_seen += 1
                codes.extend(((extension >> 6) & 63, extension & 63))
            for slot, code in enumerate(codes):
                field = reference(code, size - payload)
                field.update(operation=index, slot=slot)
                if field['role'] == 'register':
                    registers.append(field)
                else:
                    field['offset'] += payload
                    fields.append(field)
        else:
            address = control & 0xfff
            if 0xfe0 <= address <= 0xfee and not address & 1:
                fields.append(dict(operation=index, role='address',
                                   offset=payload + (address & 15), width=2))
            elif address >= 0xfe0:
                raise UnsupportedLayout('Transfer window outside the proved FE0..FEE form')
    covered = set()
    extensions = set()
    for field in fields:
        start, width = field['offset'], field['width']
        if start < payload or start + width > size:
            raise ValueError('Operand field outside packet payload')
        region = set(range(start, start + width))
        if field['role'] == 'extension':
            extensions.update(region)
        covered.update(region)
    if any(set(range(f['offset'], f['offset'] + f['width'])) & extensions
           for f in fields if f['role'] == 'literal'):
        raise ValueError('Literal reference overlaps a long-operation extension')
    uncovered = set(range(payload, size)) - covered
    if uncovered not in (set(), {size - 1}):
        raise ValueError('Payload contains unexplained bytes')
    return dict(families=list(types), fields=fields, registers=registers, padding=len(uncovered))


def study():
    import lib
    from analyze import coefficient_widths, core_lists
    from core1 import Core1

    root = Path(__file__).resolve().parents[1]
    inventory = json.loads((lib.BASE / 'zenology_inventory.json').read_text())
    artifacts = [('zenology', lib.Z, [(str(item[0]), segment)
                  for item in inventory['lists'] if item[1] == 0 for segment in item[3]])]
    for filename in ('b0c1a.bin', 'b1c1a.bin'):
        core = Core1(lib.BASE / filename)
        artifacts.append((filename, core.data, [(str(row['payload_offset']), segment)
                         for row in core_lists(core) for segment in row['segments']]))
    results = {}
    for name, data, segments in artifacts:
        counts, rejected, failures = collections.Counter(), collections.Counter(), []
        for label, (base, length, capacity, source) in segments:
            stream = swap_words(data[source:source + ((length + 3) & ~3)])[:length]
            for offset, words in packets(stream):
                counts['packets'] += 1
                try:
                    decoded = layout(words)
                except UnsupportedLayout as error:
                    rejected[str(error)] += 1
                    continue
                except ValueError as error:
                    failures.append(dict(segment=label, offset=offset, header=f'{words[0]:04x}', error=str(error)))
                    continue
                counts['decoded'] += 1
                counts['literal_fields'] += sum(field['role'] == 'literal' for field in decoded['fields'])
                counts['extension_fields'] += sum(field['role'] == 'extension' for field in decoded['fields'])
                counts['address_fields'] += sum(field['role'] == 'address' for field in decoded['fields'])
        results[name] = dict(counts=dict(counts), rejected=dict(rejected), failures=failures)
    named = collections.defaultdict(list)
    for record in coefficient_widths(inventory)['records']:
        named[record['cls']].append(record)
    anchors = collections.Counter()
    anchor_failures = []
    for cls, (_, _, lists) in lib.pairs().items():
        render = [item for item in lists or [] if item[1] == 0]
        if not render:
            continue
        _, length, _, source = max(render[0][3], key=lambda s: s[1])
        stream = swap_words(lib.Z[source:source + ((length + 3) & ~3)])[:length]
        for offset, words in packets(stream):
            try:
                decoded = layout(words)
            except UnsupportedLayout:
                continue
            actual = {(offset + f['offset'], f['width']) for f in decoded['fields'] if f['role'] == 'literal'}
            for record in named[cls]:
                if offset <= record['relative'] < offset + 2 * len(words):
                    anchors['named_width_position_anchors'] += 1
                    if (record['relative'], record['width']) not in actual:
                        anchor_failures.append(dict(cls=cls, offset=offset, symbol_offset=record['relative']))
                    else:
                        anchors['matching_anchors'] += 1
    results['independent_symbols'] = dict(counts=dict(anchors), failures=anchor_failures)
    target = root / 'local/header-study.json'
    target.write_text(json.dumps(results, indent=2) + '\n')
    for name, result in results.items():
        print(name, result['counts'], f'{len(result["failures"])} counterexamples')
    return results


if __name__ == '__main__':
    study()
