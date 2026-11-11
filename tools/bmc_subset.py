"""Assemble/disassemble independently matched mix/filter packet templates.

This emits a program fragment in the stock MFX context, not a standalone engine.
Packet ordering is fixed: no instruction scheduling or unknown controls are invented.
"""
import argparse
import json
from pathlib import Path
import sys

from bmc_dsp import assemble, packets, swap_words


DEFAULT_INPUT_ADDRESSES = (0x2016, 0x2017)
STEREO_INPUT_ADDRESSES = (
    DEFAULT_INPUT_ADDRESSES, (0x2459, 0x245a),
    (0x2000, 0x2001), (0x2005, 0x2006), (0x2009, 0x200a),
    (0x200d, 0x200e), (0x20ee, 0x20ef),
)


def input_pair(addresses):
    if (not isinstance(addresses, list) or len(addresses) != 2
            or any(type(address) is not int for address in addresses)
            or tuple(addresses) not in STEREO_INPUT_ADDRESSES):
        raise ValueError('Expected one checked stereo input pair in channel order')
    return addresses


def assemble_stereo_input(spec):
    if (not isinstance(spec, dict) or set(spec) != {'kind', 'input_addresses'}
            or spec['kind'] != 'stereo_input'):
        raise ValueError('Expected stereo_input and input_addresses')
    return assemble([[0x1e05, 0x0fe0, 0x1fe2, *input_pair(spec['input_addresses'])]])


def assemble_coefficient_shift4(spec):
    if (not isinstance(spec, dict) or set(spec) !=
            {'kind', 'input_addresses', 'coefficient_slots', 'target'}
            or spec['kind'] != 'coefficient_shift4'):
        raise ValueError('Expected coefficient_shift4 with input_addresses, coefficient_slots and target')
    input_pair(spec['input_addresses'])
    slots = spec['coefficient_slots']
    if (not isinstance(slots, list) or len(slots) != 2
            or any(type(slot) is not int or not 0 <= slot < 0x1000 for slot in slots)
            or len(set(slots)) != 2
            or type(spec['target']) is not int or not 0 <= spec['target'] < 0x800):
        raise ValueError('Expected two distinct coefficient slots and one data target')
    gain, shift = [0xc000 | slot for slot in slots]
    return assemble([
        [0x3e07, 0x0fe0, 0x1fe2, 0x7fe4, *spec['input_addresses'], shift],
        [0x2808, 0x0812, 0xfdd4, 0x3fe6, 0x1500, 0x2800, 0x2800, gain],
        [0x1804, 0x0403, 0xffe0, spec['target']],
    ])


def validate(spec):
    if not isinstance(spec, dict) or set(spec) - {'input_addresses'} != {'kind', 'wet_addresses', 'coefficient_slots'}:
        raise ValueError('Expected kind, wet_addresses, coefficient_slots and optional input_addresses')
    if spec['kind'] != 'dry_wet_tail':
        raise ValueError('Only the verified dry_wet_tail template is supported')
    if 'input_addresses' in spec:
        input_pair(spec['input_addresses'])
    for name, count, maximum in [('wet_addresses', 2, 0x7ff), ('coefficient_slots', 4, 0xfff)]:
        values = spec[name]
        if (not isinstance(values, list) or len(values) != count or
                any(type(value) is not int or not 0 <= value <= maximum for value in values)):
            raise ValueError(f'{name} requires {count} integer indices in 0..{maximum:#x}')
        if len(set(values)) != count:
            raise ValueError(f'{name} must be distinct in this independently checked subset')


def assemble_tail(spec):
    """Emit only the observed packet order, with explicitly assigned resources.

    Inputs use a checked stereo pair and outputs use main A/B.
    The caller supplies entry, exit, IO setup, state and resource assignments.
    """
    validate(spec)
    left, right = spec['wet_addresses']
    input_left, input_right = spec.get('input_addresses', DEFAULT_INPUT_ADDRESSES)
    dry, wet, post, master = [0xc000 | index for index in spec['coefficient_slots']]
    return assemble([
        [0x1e05, 0x0fe0, 0x3fe2, input_left, dry],
        [0x1e05, 0x1fe0, 0x7fe2, left, wet],
        [0x2b07, 0x080b, 0x4fe2, 0x5fe4, 0x13c0, input_right, right],
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
    addresses = a[3], c[5]
    if addresses != DEFAULT_INPUT_ADDRESSES:
        spec['input_addresses'] = list(addresses)
    if assemble_tail(spec) != stream:
        raise ValueError('Unsupported controls, extensions or address tags')
    return spec


def assemble_tail_with_scratch(spec):
    if (not isinstance(spec, dict)
            or spec.get('kind') != 'dry_wet_tail_with_scratch'
            or set(spec) - {'input_addresses'} != {'kind', 'wet_addresses', 'coefficient_slots', 'scratch_addresses'}):
        raise ValueError('Expected dry/wet resources and scratch_addresses')
    base = {key: value for key, value in spec.items() if key != 'scratch_addresses'}
    tail = assemble_tail(dict(base, kind='dry_wet_tail'))
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


def assemble_register_add_mac_pair(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'register_add_mac_pair'
            or set(spec) != {'kind', 'sources', 'targets', 'coefficient_slots'}):
        raise ValueError('Expected register_add_mac_pair with sources, targets and coefficient_slots')
    for name, count, maximum in (('sources', 10, 0x800), ('targets', 2, 0x800),
                                  ('coefficient_slots', 2, 0x1000)):
        if (not isinstance(spec[name], list) or len(spec[name]) != count
                or any(type(value) is not int or not 0 <= value < maximum for value in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    if (len(set(spec['sources']+spec['targets'])) != 12
            or len(set(spec['coefficient_slots'])) != 2):
        raise ValueError('The checked add/MAC profile requires distinct resources')
    a, w1, s2, b, w5, s6, next2, next6, next1, next5 = spec['sources']
    first, second = spec['targets']
    current, following = [0xc000 | value for value in spec['coefficient_slots']]
    return assemble([
        [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, a, w1, s2],
        [0x3e07, 0x4fe0, 0x5fe2, 0x6fe4, b, w5, s6],
        [0xb8cf, 0x1c42, 0x5d46, 0x9fe0, 0x3fe2, 0xdfe4, 0x7fe6, 0x2fe8, 0x6fea,
         first, current, second, current, next2, next6],
        [0x8f4d, 0x044b, 0x454f, 0x1fe4, 0x3fe6, 0x5fe8, 0x7fea,
         0, 4, next1, following, next5, following],
    ])


def assemble_state_variable_pair(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'state_variable_pair'
            or set(spec) != {'kind', 'sources', 'targets', 'coefficient_slots'}):
        raise ValueError('Expected state_variable_pair sources, targets and coefficient_slots')
    for name, count, maximum in (('sources', 10, 0x800), ('targets', 4, 0x800),
                                  ('coefficient_slots', 5, 0x1000)):
        if (not isinstance(spec[name], list) or len(spec[name]) != count
                or any(type(value) is not int or not 0 <= value < maximum for value in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    y, t, s, yr, tr, sr, next_s, next_sr, next_t, next_tr = spec['sources']
    if (t != s+1 or tr != sr+1 or spec['targets'] != [s, sr, s-1, sr-1]
            or len(set(spec['sources']+[s-1, sr-1])) != 12
            or len(set(spec['coefficient_slots'])) != 5):
        raise ValueError('State-variable resources violate the checked history/alias relations')
    a, b, c, d, e = [0xc000 | value for value in spec['coefficient_slots']]
    return assemble([
        [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, y, t, s],
        [0x3e07, 0x4fe0, 0x5fe2, 0x6fe4, yr, tr, sr],
        [0x1e05, 0x3fe0, 0x7fe2, a, a],
        [0x4709, 0x1c8b, 0x5d8f, 0x3fe4, 0x7fe6, 0x2001, 0x6005, b, b],
        [0x88cf, 0x1c8b, 0x5d8f, 0xaf60, 0xef60, 0x9fe4, 0x3fe6, 0xdfe8, 0x7fea,
         0x9000, 0xd004, s, e, sr, e],
        [0x5f07, 0x2443, 0x6547, 0x3fe0, 0x7fe2, c, c],
        [0xb149, 0x08c2, 0x49c6, 0xaf61, 0xef61, 0x3fe0, 0x7fe2, a, a],
        [0x1005, 0x1c4b, 0x5d4f, 0x1002, 0x5006],
        [0xb8cf, 0x1c42, 0x5d46, 0x9fe0, 0x3fe2, 0xdfe4, 0x7fe6, 0x2fe8, 0x6fea,
         s-1, d, sr-1, d, next_s, next_sr],
        [0x8f4d, 0x044b, 0x454f, 0x1fe4, 0x3fe6, 0x5fe8, 0x7fea,
         0, 4, next_t, a, next_tr, a],
    ])


def assemble_cubic_quad(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'cubic_quad'
            or set(spec) != {'kind', 'sources', 'targets'}):
        raise ValueError('Expected cubic_quad with four sources and four targets')
    for name in ('sources', 'targets'):
        if (not isinstance(spec[name], list) or len(spec[name]) != 4
                or any(type(value) is not int or not 0 <= value < 0x800 for value in spec[name])):
            raise ValueError('Expected four data indices in 0..0x7ff')
    if len(set(spec['sources']+spec['targets'])) != 8:
        raise ValueError('The checked cubic profile requires eight distinct data indices')
    left1, left2, right1, right2 = spec['sources']
    out_left1, out_left2, out_right1, out_right2 = spec['targets']
    return assemble([
        [0x1e05, 0x0fe0, 0x4fe2, left1, right2],
        [0x3407, 0x2410, 0xcfe2, 0x4fe4, 0x4300, right2, right1],
        [0x2c06, 0x1400, 0x6510, 0x2e92, 0x4300, 0x4300],
        [0x2c05, 0x1c42, 0x5504, 0x6f90, 0x4300],
        [0x2e05, 0x1440, 0x5d46, 0x0fe0, left2],
        [0x5f08, 0x2410, 0x5544, 0x9fe2, 0x4fe4, 0x4300, out_left1, right2],
        [0x5c08, 0x1400, 0x6510, 0x2e92, 0xdfe4, 0x4300, 0x4300, out_right1],
        [0x2c05, 0x1c42, 0x5504, 0x6f90, 0x4300],
        [0x1503, 0x1440, 0x5d46],
        [0x1804, 0x5544, 0x9fe0, out_left2],
        [0x3e07, 0xdfe0, 0x2fe2, 0x6fe4, out_right2, out_left1, out_right1],
    ])


def assemble_clipped_half_pair(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'clipped_half_pair'
            or set(spec) != {'kind', 'sources', 'targets'}):
        raise ValueError('Expected clipped_half_pair sources and targets')
    for name, count in (('sources', 4), ('targets', 6)):
        if (not isinstance(spec[name], list) or len(spec[name]) != count
                or any(type(value) is not int or not 0 <= value < 0x800 for value in spec[name])):
            raise ValueError('Invalid clipped-half data indices')
    left, right, previous_left, previous_right = spec['sources']
    save_left, save_right, average_left, direct_left, average_right, direct_right = spec['targets']
    if (previous_left != save_left+1 or previous_right != save_right+1
            or len(set(spec['sources']+spec['targets'])) != 10):
        raise ValueError('Clipped-half resources violate the checked history/distinctness relations')
    return assemble([
        [0x3e07, 0x0fe0, 0x4fe2, 0x2fe4, left, right, previous_left],
        [0x540a, 0x2812, 0x8ed8, 0x8fe6, 0x6fe8, 0x2500, 0x2800, 0x2800,
         save_left, previous_right],
        [0x540a, 0x6912, 0xaeda, 0x8fe6, 0xcfe8, 0x6500, 0x2800, 0x2800,
         direct_left, save_right],
        [0x1b04, 0xeede, 0xafe0, average_left],
        [0x3a06, 0xcedc, 0xefe0, 0x0fe2, average_right, average_left],
        [0x0c03, 0xcfe0, direct_right],
    ])


def assemble_fragment(spec):
    if not isinstance(spec, dict):
        raise ValueError('Expected a JSON object')
    if spec.get('kind') == 'stereo_input':
        return assemble_stereo_input(spec)
    if spec.get('kind') == 'coefficient_shift4':
        return assemble_coefficient_shift4(spec)
    if spec.get('kind') == 'allpass4':
        return assemble_allpass(spec)
    if spec.get('kind') == 'register_add_mac_pair':
        return assemble_register_add_mac_pair(spec)
    if spec.get('kind') == 'state_variable_pair':
        return assemble_state_variable_pair(spec)
    if spec.get('kind') == 'cubic_quad':
        return assemble_cubic_quad(spec)
    if spec.get('kind') == 'clipped_half_pair':
        return assemble_clipped_half_pair(spec)
    if spec.get('kind') == 'dry_wet_tail_with_scratch':
        return assemble_tail_with_scratch(spec)
    return assemble_tail(spec)


def disassemble_fragment(stream):
    if len(stream) == 126:
        rows = [words for _, words in packets(stream)]
        if len(rows) != 11 or [len(row) for row in rows] != [5, 7, 6, 5, 5, 8, 8, 5, 3, 4, 7]:
            raise ValueError('Not an exact cubic_quad profile')
        spec = dict(kind='cubic_quad', sources=[rows[0][3], rows[4][4], rows[1][6], rows[0][4]],
                    targets=[rows[5][6], rows[9][3], rows[6][7], rows[10][4]])
        if assemble_cubic_quad(spec) != stream:
            raise ValueError('Unsupported cubic controls, literals, aliases or field references')
        return spec
    if len(stream) == 184:
        rows = [words for _, words in packets(stream)]
        if len(rows) != 10 or [len(row) for row in rows] != [7, 7, 5, 9, 15, 7, 9, 5, 15, 13]:
            raise ValueError('Not an exact state_variable_pair profile')
        spec = dict(kind='state_variable_pair', sources=rows[0][4:7]+rows[1][4:7]+rows[8][13:15]
                    +[rows[9][9], rows[9][11]],
                    targets=[rows[4][11], rows[4][13], rows[8][9], rows[8][11]],
                    coefficient_slots=[rows[index][field] & 0xfff for index, field in
                                       ((2, 3), (3, 7), (5, 5), (8, 10), (4, 12))])
        if assemble_state_variable_pair(spec) != stream:
            raise ValueError('Unsupported state-variable controls, extensions, aliases or tags')
        return spec
    if len(stream) == 84:
        rows = [words for _, words in packets(stream)]
        if len(rows) != 4 or [len(row) for row in rows] != [7, 7, 15, 13]:
            raise ValueError('Not an exact register_add_mac_pair profile')
        first, second, third, fourth = rows
        spec = dict(kind='register_add_mac_pair', sources=first[4:7]+second[4:7]+third[13:15]
                    +[fourth[9], fourth[11]], targets=[third[9], third[11]],
                    coefficient_slots=[third[10] & 0xfff, fourth[10] & 0xfff])
        if assemble_register_add_mac_pair(spec) != stream:
            raise ValueError('Unsupported add/MAC controls, extensions, duplicates or tags')
        return spec
    if len(stream) == 38:
        rows = [words for _, words in packets(stream)]
        if len(rows) != 3 or [len(row) for row in rows] != [7, 8, 4]:
            raise ValueError('Not an exact coefficient_shift4 prefix')
        first, middle, last = rows
        spec = dict(kind='coefficient_shift4', input_addresses=first[4:6],
                    coefficient_slots=[middle[7] & 0xfff, first[6] & 0xfff], target=last[3])
        if assemble_coefficient_shift4(spec) != stream:
            raise ValueError('Unsupported coefficient-shift controls, literals or tags')
        return spec
    if len(stream) == 10:
        spec = dict(kind='stereo_input', input_addresses=[
            int.from_bytes(stream[offset:offset+2], 'big') for offset in (6, 8)])
        if assemble_stereo_input(spec) != stream:
            raise ValueError('Unsupported stereo input packet')
        return spec
    if len(stream) == 80:
        rows = [words for _, words in packets(stream)]
        if [len(row) for row in rows] == [7, 10, 10, 4, 6, 3]:
            spec = dict(kind='clipped_half_pair', sources=[*rows[0][4:7], rows[1][9]],
                        targets=[rows[1][8], rows[2][9], rows[3][3], rows[2][8], rows[4][4], rows[5][2]])
            if assemble_clipped_half_pair(spec) != stream:
                raise ValueError('Unsupported clipped-half controls, literals, fields or history relations')
            return spec
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
    read.add_argument('--length', type=int, help='Logical byte length before storage padding (for example cubic_quad: 126)')
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
