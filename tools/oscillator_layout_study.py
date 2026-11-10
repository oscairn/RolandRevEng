"""Compare bounded oscillator operand-layout candidates; no decoder expansion.

Opaque control slots are preserved as unknown. Projection into the existing regular
layout checks known references only; a fit cannot exclude hidden aliases or effects.
"""
from itertools import product
import json
from pathlib import Path

from bmc_dsp import assemble, command_count, packets, swap_words
from header_study import layout, UnsupportedLayout

# Exact observed control contexts, not high-byte families or arithmetic meanings.
CONTEXTS = {
    0xbd4b: ((0x3074, 0xff75, 0xef75, 0x00d7, 0x1fe0, 0x2fe2), (0,), (4, 5)),
    0x5c07: ((0x08c1, 0x4d20, 0xeef6, 0xa9b1), (0, 1), (3,)),
    0xa50c: ((0x28a6, 0x8ed8, 0x00d5, 0xafe2, 0xdfe4), (0,), (3, 4)),
    0x4d0d: ((0x2d64, 0x0c3b, 0x1220, 0xdfe2), (0, 1), (3,)),
}
PROJECTED_FAMILY = {(0, 4, 4): 0x2b, (1, 4, 4): 0x34,
                    (0, 0, 4): 0x22, (0, 1, 4): 0x25, (1, 1, 4): 0x2e}


def candidates(words):
    """Return all long/short assignments compatible with known pool coverage.

    This deliberately permits extension/address aliases, as layout() does. Opaque
    controls contribute no guessed pool references and remain explicitly unknown.
    """
    if not words or words[0] not in CONTEXTS:
        raise UnsupportedLayout('Not one of the four studied oscillator contexts')
    stream = assemble([words])
    controls, arithmetic, transfers = CONTEXTS[words[0]]
    count = command_count(words[0])
    if count != len(controls) or tuple(words[1:count + 1]) != controls:
        raise UnsupportedLayout('Control context differs from the studied packet')
    pool = words[count + 1:]
    opaque = [i for i in range(count) if i not in arithmetic + transfers]
    results, rejected = [], []
    for kinds in product((0, 1), repeat=len(arithmetic)):
        kept = [(i, kind, controls[i]) for i, kind in zip(arithmetic, kinds)]
        kept += [(i, 4, controls[i]) for i in transfers]
        kept.sort(key=lambda row: row[1])
        types = tuple(row[1] for row in kept)
        projected = [(PROJECTED_FAMILY[types] << 8) | (1 + len(kept) + len(pool))]
        projected += [row[2] for row in kept] + pool
        try:
            decoded = layout(projected)
        except (UnsupportedLayout, ValueError) as error:
            rejected.append(dict(arithmetic_families=list(kinds), error=str(error)))
            continue
        # Removing opaque base words shifts the pool; its internal offsets stay put.
        delta = 2 * len(opaque)
        for field in decoded['fields'] + decoded['registers']:
            field['operation'] = kept[field['operation']][0]
            if 'offset' in field:
                field['offset'] += delta
        results.append(dict(arithmetic_families=list(kinds), fields=decoded['fields'],
                            registers=decoded['registers'], padding=decoded['padding']))
    return dict(header=words[0], size=len(stream), arithmetic_operations=list(arithmetic),
                opaque_operations=[dict(operation=i, control=controls[i]) for i in opaque],
                candidates=results, rejected=rejected, fully_decoded=False)


def study():
    from oscillator_regions_study import study as anchors_study
    from core1 import Core1
    import os

    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1] / 'local'))
    core = Core1(corpus / 'b0c1a.bin')
    anchors = anchors_study()
    start, length = core.offset(anchors['source']), anchors['length']
    stream = swap_words(core.data[start:start + ((length + 3) & ~3)])[:length]
    packet_words = dict(packets(stream))
    reports = {}
    for anchor in anchors['anchors']:
        offset = anchor['packet_offset']
        if offset not in reports:
            reports[offset] = dict(packet_offset=offset, **candidates(packet_words[offset]), anchors=[])
        row = reports[offset]
        matches = []
        for candidate in row['candidates']:
            fields = [field for field in candidate['fields'] if field['role'] == 'literal'
                      and offset + field['offset'] == anchor['relative'] and field['width'] == anchor['width']]
            if not fields:
                raise ValueError('A surviving layout fails an owner-proven literal anchor')
            matches.append(dict(arithmetic_families=candidate['arithmetic_families'], fields=fields))
        if not matches:
            raise ValueError('No candidate explains the owner-proven literal')
        row['anchors'].append(dict(name=anchor['name'], relative=anchor['relative'],
                                   width=anchor['width'], value=anchor['value'], matches=matches))
    return dict(list_address=anchors['list_address'], source=anchors['source'],
                assumptions=['Opaque slots retain unknown operand syntax and effects; no extra pool references are invented.',
                             'Regular ALU reference rules and transfer slots are tested as hypotheses in these exact contexts.'],
                packets=[reports[offset] for offset in sorted(reports)], fully_decoded=False)


if __name__ == '__main__':
    result = study()
    target = Path(__file__).resolve().parents[1] / 'local/oscillator-layout-study.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    for packet in result['packets']:
        print(hex(packet['packet_offset']), hex(packet['header']),
              [candidate['arithmetic_families'] for candidate in packet['candidates']],
              [anchor['name'] for anchor in packet['anchors']])
