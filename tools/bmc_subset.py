"""Assemble/disassemble independently matched mix/filter packet templates.

This emits a program fragment in the stock MFX context, not a standalone engine.
Packet ordering is fixed: no instruction scheduling or unknown controls are invented.
"""
import argparse
import json
from pathlib import Path
import sys

from bmc_dsp import assemble, packets, swap_words


def validate(spec):
    if not isinstance(spec, dict) or set(spec) != {'kind', 'wet_addresses', 'coefficient_slots'}:
        raise ValueError('Expected kind, wet_addresses and coefficient_slots only')
    if spec['kind'] != 'dry_wet_tail':
        raise ValueError('Only the verified dry_wet_tail template is supported')
    for name, count, maximum in [('wet_addresses', 2, 0x7ff), ('coefficient_slots', 4, 0xfff)]:
        values = spec[name]
        if (not isinstance(values, list) or len(values) != count or
                any(type(value) is not int or not 0 <= value <= maximum for value in values)):
            raise ValueError(f'{name} requires {count} integer indices in 0..{maximum:#x}')
        if len(set(values)) != count:
            raise ValueError(f'{name} must be distinct in this independently checked subset')


def assemble_tail(spec):
    """Emit only the observed packet order, with explicitly assigned resources.

    Inputs remain the contextual stock slots 2016/2017. Outputs remain main A/B;
    no entry, exit, IO setup, state initialization or resource allocation is emitted.
    """
    validate(spec)
    left, right = spec['wet_addresses']
    dry, wet, post, master = [0xc000 | index for index in spec['coefficient_slots']]
    return assemble([
        [0x1e05, 0x0fe0, 0x3fe2, 0x2016, dry],
        [0x1e05, 0x1fe0, 0x7fe2, left, wet],
        [0x2b07, 0x080b, 0x4fe2, 0x5fe4, 0x13c0, 0x2017, right],
        [0x1405, 0x490b, 0x3fe2, 0x53c0, post],
        [0x2e05, 0x0403, 0x4503, 0x3fe0, master],
        [0x1503, 0x0403, 0x4503],
    ])


def disassemble_tail(stream):
    """Decode a complete, exact template; reject other instructions and suffixes."""
    decoded = packets(stream)
    if len(decoded) != 6 or [len(words) for _, words in decoded] != [5, 5, 7, 5, 5, 3]:
        raise ValueError('Not an exact six-packet dry/wet tail')
    a, b, c, d, e, _ = [words for _, words in decoded]
    spec = dict(kind='dry_wet_tail', wet_addresses=[b[3], c[6]],
                coefficient_slots=[a[4] & 0xfff, b[4] & 0xfff, d[4] & 0xfff, e[4] & 0xfff])
    if assemble_tail(spec) != stream:
        raise ValueError('Unsupported controls, extensions or address tags')
    return spec


def assemble_tail_with_scratch(spec):
    if (not isinstance(spec, dict)
            or spec.get('kind') != 'dry_wet_tail_with_scratch'
            or set(spec) != {'kind', 'wet_addresses', 'coefficient_slots', 'scratch_addresses'}):
        raise ValueError('Expected dry/wet resources and scratch_addresses')
    base = {key: spec[key] for key in ('wet_addresses', 'coefficient_slots')}
    tail = assemble_tail(dict(kind='dry_wet_tail', **base))
    scratch = spec['scratch_addresses']
    if (not isinstance(scratch, list) or len(scratch) != 2
            or any(type(value) is not int or not 0 <= value <= 0x7ff for value in scratch)
            or len(set(base['wet_addresses'] + scratch)) != 4):
        raise ValueError('Expected two distinct scratch indices separate from wet indices')
    return tail + assemble([
        [0x1e05, 0x8fe0, 0xcfe2, *scratch],
        [0x1e05, 0x0fe0, 0x4fe2, *scratch],
    ])


def disassemble_tail_with_scratch(stream):
    tail = disassemble_tail(stream[:60])
    decoded = packets(stream[60:])
    if len(decoded) != 2 or any(len(words) != 5 for _, words in decoded):
        raise ValueError('Expected exactly two scratch packets')
    spec = dict(tail, kind='dry_wet_tail_with_scratch', scratch_addresses=decoded[0][1][3:])
    if assemble_tail_with_scratch(spec) != stream:
        raise ValueError('Unsupported scratch store or reload')
    return spec


def validate_allpass(spec):
    if not isinstance(spec, dict) or set(spec) != {'kind', 'sources', 'targets'} or spec['kind'] != 'allpass4':
        raise ValueError('Expected an allpass4 assignment with sources and targets only')
    for name, count in [('sources', 7), ('targets', 6)]:
        if (not isinstance(spec[name], list) or len(spec[name]) != count or
                any(type(value) is not int or not 0 <= value <= 0x7ff for value in spec[name])):
            raise ValueError(f'{name} requires {count} data indices in 0..0x7ff')
    if len(set(spec['sources'] + spec['targets'])) != 13:
        raise ValueError('The checked allpass4 subset requires 13 distinct data indices')


def assemble_allpass(spec):
    """Emit the exact four-stage allpass chain with pre-arithmetic stores."""
    validate_allpass(spec)
    main, one, two, factor, next_one, next_two, last_one = spec['sources']
    previous, stage0, stage1, stage2, output, copy = spec['targets']
    return assemble([
        [0x1e05, 0x1fe0, 0x0fe2, one, main],
        [0x3e07, 0x2fe0, 0x3fe2, 0x8fe4, two, factor, previous],
        [0x1405, 0x0e0b, 0x1fe2, 0x22c1, next_one],
        [0x2b07, 0x0e0b, 0x2fe2, 0x8fe4, 0x12c2, next_two, stage0],
        [0x2b07, 0x0e0b, 0x1fe2, 0x8fe4, 0x22c1, last_one, stage1],
        [0x1405, 0x0e0b, 0x8fe2, 0x12c2, stage2],
        [0x1e05, 0x8fe0, 0x8fe2, output, copy],
    ])


def disassemble_allpass(stream):
    decoded = packets(stream)
    if len(decoded) != 7 or [len(words) for _, words in decoded] != [5, 7, 5, 7, 7, 5, 5]:
        raise ValueError('Not an exact seven-packet allpass4 chain')
    a, b, c, d, e, f, g = [words for _, words in decoded]
    spec = dict(kind='allpass4', sources=[a[4], a[3], b[4], b[5], c[4], d[5], e[5]],
                targets=[b[6], d[6], e[6], f[4], g[3], g[4]])
    if assemble_allpass(spec) != stream:
        raise ValueError('Unsupported allpass controls, extensions or address tags')
    return spec


def assemble_fragment(spec):
    if not isinstance(spec, dict):
        raise ValueError('Expected a JSON object')
    if spec.get('kind') == 'allpass4':
        return assemble_allpass(spec)
    if spec.get('kind') == 'dry_wet_tail_with_scratch':
        return assemble_tail_with_scratch(spec)
    return assemble_tail(spec)


def disassemble_fragment(stream):
    if len(stream) == 80:
        return disassemble_tail_with_scratch(stream)
    if len(stream) == 82:
        return disassemble_allpass(stream)
    return disassemble_tail(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('assemble', help='Emit the fixed template from a JSON resource assignment')
    build.add_argument('spec', type=Path)
    build.add_argument('output', type=Path)
    build.add_argument('--stored', action='store_true', help='Emit swapped LE32 storage words')
    read = commands.add_parser('disassemble', help='Decode an exact template to its JSON assignment')
    read.add_argument('file', type=Path)
    read.add_argument('--stored', action='store_true', help='Read swapped LE32 storage words')
    read.add_argument('--length', type=int, help='Logical byte length before storage padding (allpass4: 82)')
    args = parser.parse_args()
    try:
        if args.command == 'assemble':
            stream = assemble_fragment(json.loads(args.spec.read_text()))
            logical_length = len(stream)
            if args.stored:
                stream = swap_words(stream + bytes(-len(stream) % 4))
            with args.output.open('xb') as output:
                output.write(stream)
            print(f'{logical_length} logical bytes, {len(stream)} file bytes: fragment only; execution wrapper required',
                  file=sys.stderr)
        else:
            stream = args.file.read_bytes()
            if args.stored:
                stream = swap_words(stream)
            if args.length is not None:
                if (not args.stored or args.length < 0 or args.length % 2 or
                        ((args.length + 3) & ~3) != len(stream) or any(stream[args.length:])):
                    raise ValueError('Length must describe the complete stored fragment with zero padding only')
                stream = stream[:args.length]
            print(json.dumps(disassemble_fragment(stream), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
