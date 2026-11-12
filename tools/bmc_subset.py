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


def _validate_state_resources(spec, kind, source_count, coefficient_count):
    if (not isinstance(spec, dict) or spec.get('kind') != kind
            or set(spec) != {'kind', 'sources', 'targets', 'coefficient_slots'}):
        raise ValueError('Expected exact state-filter resource keys')
    for name, count, maximum in (('sources', source_count, 0x800), ('targets', 4, 0x800),
                                  ('coefficient_slots', coefficient_count, 0x1000)):
        if (not isinstance(spec[name], list) or len(spec[name]) != count
                or any(type(value) is not int or not 0 <= value < maximum for value in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    y, t, state, yr, tr, sr = spec['sources'][:6]
    if (t != state+1 or tr != sr+1 or spec['targets'] != [state, sr, state-1, sr-1]
            or len(set(spec['sources']+[state-1, sr-1])) != source_count+2
            or len(set(spec['coefficient_slots'])) != coefficient_count):
        raise ValueError('State-variable resources violate the checked history/alias relations')


def assemble_state_variable_pair(spec):
    _validate_state_resources(spec, 'state_variable_pair', 10, 5)
    y, t, s, yr, tr, sr, next_s, next_sr, next_t, next_tr = spec['sources']
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


def _validate_filter_outputs(outputs, spec):
    if (not isinstance(outputs, list) or len(outputs) != 2
            or any(type(value) is not int or not 0 <= value < 0x800 for value in outputs)
            or len(set(outputs)) != 2
            or set(outputs) & set(spec['sources']+spec['targets'])):
        raise ValueError('Expected two distinct filter output cells outside its state/sources')


def assemble_filter_with_output(spec):
    base_kinds = {'state_variable_pair_with_output': 'state_variable_pair',
                  'state_variable_recombine_pair_with_output': 'state_variable_recombine_pair'}
    if (not isinstance(spec, dict) or spec.get('kind') not in base_kinds
            or 'output_addresses' not in spec):
        raise ValueError('Expected filter output_addresses')
    base = dict(spec); outputs = base.pop('output_addresses')
    base['kind'] = base_kinds[spec['kind']]
    program = (assemble_state_variable_pair(base) if base['kind'] == 'state_variable_pair'
               else assemble_filter_recombine(base))
    _validate_filter_outputs(outputs, base)
    return program+assemble([[0x1e05, 0x8fe0, 0xcfe2, *outputs]])


def assemble_filter_recombine(spec):
    _validate_state_resources(spec, 'state_variable_recombine_pair', 10, 7)
    slots = spec['coefficient_slots']
    y, t, s, yr, tr, sr, next_s, next_sr, next_t, next_tr = spec['sources']
    a, b, c, d, e, g, following = [0xc000 | value for value in slots]
    return assemble([
        [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, y, t, s],
        [0x3e07, 0x4fe0, 0x5fe2, 0x6fe4, yr, tr, sr],
        [0x1e05, 0x3fe0, 0x7fe2, a, a],
        [0x8f4d, 0x1c8b, 0x5d8f, 0x8fe4, 0xcfe6, 0x3fe8, 0x7fea, 0x2001, 0x6005, y, yr, b, b],
        [0x88cf, 0x1c8b, 0x5d8f, 0xaf60, 0xef60, 0x9fe4, 0x3fe6, 0xdfe8, 0x7fea,
         0x9000, 0xd004, s, e, sr, e],
        [0x5f07, 0x2443, 0x6547, 0x3fe0, 0x7fe2, c, c],
        [0xb149, 0x08c2, 0x49c6, 0xaf61, 0xef61, 0x3fe0, 0x7fe2, a, a],
        [0x1005, 0x1c4b, 0x5d4f, 0x1002, 0x5006],
        [0xb84b, 0x1c42, 0x5d46, 0x9fe0, 0x3fe2, 0xdfe4, 0x7fe6, s-1, d, sr-1, d],
        [0x8f0b, 0x044b, 0x454f, 0x1fe4, 0x5fe6, 0x7fe8, 0, 4, y, yr, g],
        [0x5f07, 0x1bc1, 0x5bc5, 0x2fe0, 0x6fe2, next_s, next_sr],
        [0xb84b, 0x09c1, 0x49c5, 0x1fe0, 0x3fe2, 0x5fe4, 0x7fe6,
         next_t, following, next_tr, following],
    ])


def assemble_terminal_filter(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'state_variable_terminal_pair_with_output'
            or 'output_addresses' not in spec):
        raise ValueError('Expected terminal filter output assignment')
    base = dict(spec); outputs = base.pop('output_addresses')
    _validate_state_resources(base, 'state_variable_terminal_pair_with_output', 6, 6)
    _validate_filter_outputs(outputs, base)
    y, t, state, yr, tr, sr = spec['sources']
    a, b, c, d, e, g = [0xc000 | slot for slot in spec['coefficient_slots']]
    return assemble([
        [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, y, t, state],
        [0x3e07, 0x4fe0, 0x5fe2, 0x6fe4, yr, tr, sr],
        [0x1e05, 0x3fe0, 0x7fe2, a, a],
        [0x8f4d, 0x1c8b, 0x5d8f, 0x8fe4, 0xcfe6, 0x3fe8, 0x7fea, 0x2001, 0x6005, y, yr, b, b],
        [0x88cf, 0x1c8b, 0x5d8f, 0xaf60, 0xef60, 0x9fe4, 0x3fe6, 0xdfe8, 0x7fea,
         0x9000, 0xd004, state, e, sr, e],
        [0x5f07, 0x2443, 0x6547, 0x3fe0, 0x7fe2, c, c],
        [0xb149, 0x08c2, 0x49c6, 0xaf61, 0xef61, 0x3fe0, 0x7fe2, a, a],
        [0x1005, 0x1c4b, 0x5d4f, 0x1002, 0x5006],
        [0xb84b, 0x1c42, 0x5d46, 0x9fe0, 0x3fe2, 0xdfe4, 0x7fe6, state-1, d, sr-1, d],
        [0x8f0b, 0x044b, 0x454f, 0x1fe4, 0x5fe6, 0x7fe8, 0, 4, y, yr, g],
        [0x1503, 0x1bc1, 0x5bc5],
        [0x1503, 0x09c1, 0x49c5],
        [0x1e05, 0x8fe0, 0xcfe2, *outputs],
    ])


def assemble_resample_drive_pair(spec):
    from bmc_dsp import encode_literal, literal
    if (not isinstance(spec, dict) or spec.get('kind') != 'resample_drive_pair'
            or set(spec) != {'kind','sources','output_addresses','coefficient_slots','tap_coefficients','drive_literal'}):
        raise ValueError('Expected exact resample/drive resource and tap assignments')
    if not isinstance(spec['drive_literal'],str) or spec['drive_literal'] not in ('0656d2','100000'):
        raise ValueError('Expected a checked ZENOLOGY or Fantom drive literal')
    for name,count,maximum in (('sources',7,0x800),('output_addresses',2,0x800),
                               ('coefficient_slots',1,0x1000)):
        if (not isinstance(spec[name],list) or len(spec[name]) != count
                or any(type(v) is not int or not 0 <= v < maximum for v in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    left,l1,l2,right,r1,r2,previous_left=spec['sources']
    if ([l1,l2,r1,r2] != [left+1,left+2,right+1,right+2]
            or len(set(spec['sources']+spec['output_addresses'])) != 9):
        raise ValueError('Resample history/output resources violate checked adjacency or alias rules')
    taps=spec['tap_coefficients']
    if not isinstance(taps,list) or len(taps) != 3:
        raise ValueError('Expected three exactly representable 24-bit tap coefficients')
    encoded=[encode_literal(v,3) for v in taps]
    if any(literal(data).hex() != float(v).hex() for data,v in zip(encoded,taps,strict=True)):
        raise ValueError('Tap coefficients must be exactly representable as 24-bit literals')
    pairs=[list(int.from_bytes((data+data)[i:i+2],'big') for i in range(0,6,2)) for data in encoded]
    drive=bytes.fromhex(spec['drive_literal'])*2
    drive_words=[int.from_bytes(drive[i:i+2],'big')for i in range(0,6,2)]
    return assemble([
        [0x1e05,0x0fe0,0x4fe2,left,right],
        [0xb84e,0x1428,0x552b,0x0fe0,0x8fe2,0x4fe4,0xcfe6,l1,left,r1,right,*pairs[0]],
        [0x470c,0x1428,0x552b,0x0fe4,0x4fe6,1,5,l2,r2,*pairs[1]],
        [0x1008,0x0424,0x4527,1,5,*pairs[2]],
        [0xb80c,0x0426,0x4529,0x8fe0,0xcfe2,0x3fe4,l1,r1,
         0xc000|spec['coefficient_slots'][0],*drive_words],
        [0x2e05,0x0403,0x4503,0x2fe0,previous_left],
        [0x1e05,0x8fe0,0xcfe2,*spec['output_addresses']],
    ])


def assemble_post_cubic_mix_pair(spec):
    if (not isinstance(spec,dict) or spec.get('kind')!='post_cubic_mix_pair'
            or set(spec)!={'kind','sources','targets','output_addresses','coefficient_slots','post_scale_literal'}):
        raise ValueError('Expected exact post-cubic mix resources and scale')
    for name,count,maximum in (('sources',6,0x800),('targets',2,0x800),
                              ('output_addresses',2,0x800),('coefficient_slots',1,0x1000)):
        if (not isinstance(spec[name],list) or len(spec[name])!=count
                or any(type(v)is not int or not 0<=v<maximum for v in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    av,direct,history,ar,dr,hr=spec['sources']
    if (history!=direct+1 or hr!=dr+1
            or len(set(spec['sources']+spec['targets']+spec['output_addresses']))!=10):
        raise ValueError('Post-cubic history/resources violate checked adjacency or alias rules')
    value=spec['post_scale_literal']
    if not isinstance(value,str) or value not in ('628624','500000'):
        raise ValueError('Expected a checked ZENOLOGY or Fantom post-scale literal')
    raw=bytes.fromhex(value)*2
    scale=[int.from_bytes(raw[i:i+2],'big')for i in range(0,6,2)]
    return assemble([
        [0x1e05,0x2fe0,0x6fe2,av,ar],
        [0x5f0a,0x04a4,0x45a7,0x1fe0,0x5fe2,direct,dr,0x2800,0x0028,0],
        [0x470c,0x0468,0x456b,0x1fe4,0x5fe6,0,4,history,hr,0x2400,0x0024,0],
        [0x220a,0x2466,0x6569,0x3fe4,0,4,0xc000|spec['coefficient_slots'][0],0x2400,0x0024,0],
        [0x5f07,0x2483,0x6583,0xafe0,0xefe2,*spec['targets']],
        [0x1506,0x24a0,0x65a3,*scale],
        [0x1e05,0xafe0,0xefe2,*spec['output_addresses']],
    ])


def assemble_cascaded_history_pair(spec):
    from bmc_dsp import encode_literal,literal
    if (not isinstance(spec,dict) or spec.get('kind')!='cascaded_history_pair'
            or set(spec)!={'kind','sources','targets','filter_coefficients'}):
        raise ValueError('Expected exact cascaded-history resources and coefficients')
    for name,count in (('sources',12),('targets',4)):
        if (not isinstance(spec[name],list) or len(spec[name])!=count
                or any(type(v)is not int or not 0<=v<0x800 for v in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    x,h1,h2,h3,xr,r1,r2,r3,ns,nsr,nt,ntr=spec['sources']
    if ([h1,h2,h3,r1,r2,r3]!=[x+1,x+2,x+3,xr+1,xr+2,xr+3]
            or len(set(spec['sources']))!=12 or spec['targets']!=[h1,r1,h2,r2]):
        raise ValueError('Cascaded-history resources violate checked adjacency/alias rules')
    values=spec['filter_coefficients']
    if not isinstance(values,list) or len(values)!=6:
        raise ValueError('Expected six exactly representable 24-bit filter coefficients')
    encoded=[encode_literal(v,3)for v in values]
    if any(literal(data).hex()!=float(v).hex()for data,v in zip(encoded,values,strict=True)):
        raise ValueError('Filter coefficients must be exactly representable as 24-bit literals')
    pairs=[[int.from_bytes((data+data)[i:i+2],'big')for i in range(0,6,2)]for data in encoded]
    return assemble([
        [0x1e05,0x2fe0,0x6fe2,x,xr],
        [0xb84e,0x14a8,0x55ab,0x0fe0,0xafe2,0x4fe4,0xefe6,h1,x,r1,xr,*pairs[0]],
        [0x470c,0x1428,0x552b,0x0fe4,0x4fe6,1,5,h2,r2,*pairs[1]],
        [0x1008,0x1424,0x5527,1,5,*pairs[2]],
        [0x5f0a,0x1464,0x5567,0x9fe0,0xdfe2,h1,r1,*pairs[3]],
        [0x470c,0x1428,0x552b,0x0fe4,0x4fe6,1,5,h3,r3,*pairs[4]],
        [0x470c,0x1428,0x552b,0x2fe4,0x6fe6,1,5,ns,nsr,*pairs[5]],
        [0x7809,0x9fe0,0xdfe2,0x0fe4,0x4fe6,h2,r2,nt,ntr],
    ])


def assemble_fdrv_output_pair(spec):
    from bmc_dsp import encode_literal,literal
    if (not isinstance(spec,dict) or spec.get('kind')!='fdrv_output_pair'
            or set(spec)!={'kind','sources','targets','coefficient_slots','filter_coefficients'}):
        raise ValueError('Expected exact FDRV output resources and coefficients')
    for name,count,limit in (('sources',8,0x800),('targets',4,0x800),('coefficient_slots',3,0x1000)):
        if (not isinstance(spec[name],list) or len(spec[name])!=count
                or any(type(v)is not int or not 0<=v<limit for v in spec[name])):
            raise ValueError(f'Expected {count} valid {name} indices')
    y,s,t,yr,sr,tr,dry,dryr=spec['sources']
    if (len(set(spec['sources']))!=8 or t!=s+1 or tr!=sr+1 or min(s,sr)<1
            or spec['targets']!=[s,sr,s-1,sr-1]
            or set((s-1,sr-1))&set(spec['sources']) or len(set(spec['coefficient_slots']))!=3):
        raise ValueError('FDRV output resources violate checked state/alias rules')
    values=spec['filter_coefficients']
    if not isinstance(values,list) or len(values)!=5:
        raise ValueError('Expected five exactly representable 24-bit filter coefficients')
    encoded=[encode_literal(v,3)for v in values]
    if any(literal(data).hex()!=float(v).hex()for data,v in zip(encoded,values,strict=True)):
        raise ValueError('Output filter coefficients must be exactly representable')
    a,b,c,d,e=[[int.from_bytes((data+data)[i:i+2],'big')for i in range(0,6,2)]for data in encoded]
    wet,dry_gain,master=[0xc000|v for v in spec['coefficient_slots']]
    return assemble([
        [0x3e07,0x1fe0,0x2fe2,0x0fe4,y,s,t],
        [0x3e07,0x5fe0,0x6fe2,0x4fe4,yr,sr,tr],
        [0x1008,0x0ca4,0x4da7,0x2000,0x6004,*a],
        [0x884e,0x0ca8,0x4dab,0xaf60,0xef60,0x8fe4,0xcfe6,0x8001,0xc005,s,sr,*b],
        [0x1506,0x2420,0x6523,*c],
        [0x420a,0x1464,0x5567,0xaf61,0xef61,0x0002,0x0006,*d],
        [0x1008,0x0c24,0x4d27,0x0002,0x4006,*a],
        [0x5f07,0x0c02,0x4d06,0x8fe0,0xcfe2,s-1,sr-1],
        [0x220a,0x1426,0x5529,0x3fe4,0x0001,0x0005,wet,*e],
        [0xb809,0x1443,0x5543,0x0fe0,0x3fe2,0x4fe4,dry,dry_gain,dryr],
        [0x2e05,0x08c1,0x48c5,0x3fe0,master],
        # The stock coissued 00f8 return is outside the arithmetic profile.
        [0x1503,0x0403,0x4503],
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


def assemble_stereo_prefilter(spec):
    if (not isinstance(spec, dict) or spec.get('kind') != 'stereo_prefilter'
            or set(spec) != {'kind', 'input_addresses', 'sources', 'targets', 'coefficient_slots'}):
        raise ValueError('Expected stereo_prefilter input, data and coefficient assignments')
    input_pair(spec['input_addresses'])
    for name, count, maximum in (('sources', 6, 0x800), ('targets', 4, 0x800),
                                  ('coefficient_slots', 3, 0x1000)):
        if (not isinstance(spec[name], list) or len(spec[name]) != count
                or any(type(value) is not int or not 0 <= value < maximum for value in spec[name])):
            raise ValueError('Invalid prefilter resource assignment')
    l1, l2, r1, r2, next_l, next_r = spec['sources']
    raw_l, raw_r, mixed_l, mixed_r = spec['targets']
    if (l1 != raw_l+1 or l2 != raw_l+2 or r1 != raw_r+1 or r2 != raw_r+2
            or [mixed_l, mixed_r] != [l1, r1]
            or len(set(spec['sources']+[raw_l, raw_r])) != 8
            or len(set(spec['coefficient_slots'])) != 3):
        raise ValueError('Prefilter history/alias relations differ from the checked subset')
    c5, c6, c7 = [0xc000 | value for value in spec['coefficient_slots']]
    left, right = spec['input_addresses']
    return assemble([
        [0x3e07, 0x0fe0, 0x4fe2, 0x3fe4, left, right, c5],
        [0xb88d, 0x2403, 0x6503, 0x0fe0, 0x3fe2, 0x8fe4, 0x4fe6, 0xcfe8,
         l1, c6, raw_l, r1, raw_r],
        [0x8f0b, 0x240b, 0x650b, 0x0fe4, 0x3fe6, 0x4fe8, 2, 6, l2, c7, r2],
        [0x5f07, 0x08c2, 0x48c6, 0x2fe0, 0x6fe2, next_l, next_r],
        [0x1e05, 0x8fe0, 0xcfe2, mixed_l, mixed_r],
    ])


def assemble_osc_bias_wrap(spec):
    if (not isinstance(spec,dict) or set(spec)!={'kind','sources','targets'}
            or spec['kind']!='osc_bias_wrap'):
        raise ValueError('Expected osc_bias_wrap with three sources and three targets')
    for name in ('sources','targets'):
        if (not isinstance(spec[name],list) or len(spec[name])!=3
                or any(type(v)is not int or not 0<=v<0x800 for v in spec[name])):
            raise ValueError('Expected three data addresses per resource list')
    if len(set(spec['sources']+spec['targets']))!=6:
        raise ValueError('OSC bias/wrap resources must not alias')
    first,second,marker=spec['sources'];save,out0,out1=spec['targets']
    return assemble([
        [0x1e05,0x4fe0,0x2fe2,first,marker],
        [0x3407,0x5510,0xafe2,0x4fe4,0x4300,save,second],
        [0x0804,0x5512,0x0005,0x2400],
        [0x0903,0x5d50,0x2340],
        [0x0a02,0xdee5],
        [0x1e05,0xdfe0,0xdfe2,out0,out1],
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
    if spec.get('kind') in ('state_variable_pair_with_output', 'state_variable_recombine_pair_with_output'):
        return assemble_filter_with_output(spec)
    if spec.get('kind') == 'state_variable_recombine_pair':
        return assemble_filter_recombine(spec)
    if spec.get('kind') == 'state_variable_terminal_pair_with_output':
        return assemble_terminal_filter(spec)
    if spec.get('kind') == 'resample_drive_pair':
        return assemble_resample_drive_pair(spec)
    if spec.get('kind') == 'post_cubic_mix_pair':
        return assemble_post_cubic_mix_pair(spec)
    if spec.get('kind') == 'cascaded_history_pair':
        return assemble_cascaded_history_pair(spec)
    if spec.get('kind') == 'fdrv_output_pair':
        return assemble_fdrv_output_pair(spec)
    if spec.get('kind') == 'cubic_quad':
        return assemble_cubic_quad(spec)
    if spec.get('kind') == 'clipped_half_pair':
        return assemble_clipped_half_pair(spec)
    if spec.get('kind') == 'stereo_prefilter':
        return assemble_stereo_prefilter(spec)
    if spec.get('kind') == 'osc_bias_wrap':
        return assemble_osc_bias_wrap(spec)
    if spec.get('kind') == 'dry_wet_tail_with_scratch':
        return assemble_tail_with_scratch(spec)
    return assemble_tail(spec)


def disassemble_fragment(stream):
    if len(stream)==52:
        rows=[words for _,words in packets(stream)]
        if [len(row)for row in rows]!=[5,7,4,3,2,5]:
            raise ValueError('Not an exact OSC bias/wrap profile')
        spec=dict(kind='osc_bias_wrap',sources=[rows[0][3],rows[1][6],rows[0][4]],
                  targets=[rows[1][5],rows[5][3],rows[5][4]])
        if assemble_osc_bias_wrap(spec)!=stream:
            raise ValueError('Unsupported OSC bias/wrap controls, literals or resources')
        return spec
    if len(stream)==188:
        from bmc_dsp import literal
        rows=packets(stream)
        if [len(w)for _,w in rows]!=[7,7,8,14,6,10,8,7,10,9,5,3]:
            raise ValueError('Not an exact FDRV output profile')
        a,b,c,d,e,f,g,h,i,j,k,l=[w for _,w in rows]
        spec=dict(kind='fdrv_output_pair',sources=a[4:7]+b[4:7]+[j[6],j[8]],
            targets=d[9:11]+h[5:7],coefficient_slots=[i[6]&0xfff,j[7]&0xfff,k[4]&0xfff],
            filter_coefficients=[literal(stream[o+n:o+n+3])for o,n in
                ((rows[2][0],10),(rows[3][0],22),(rows[4][0],6),(rows[5][0],14),(rows[8][0],14))])
        if assemble_fdrv_output_pair(spec)!=stream:
            raise ValueError('Unsupported FDRV output controls, coefficients, tags or aliases')
        return spec
    if len(stream)==164:
        from bmc_dsp import literal
        rows=packets(stream)
        if [len(w)for _,w in rows]!=[5,14,12,8,10,12,12,9]:
            raise ValueError('Not an exact cascaded-history profile')
        a,b,c,d,e,f,g,h=[w for _,w in rows]
        spec=dict(kind='cascaded_history_pair',
            sources=[a[3],b[7],c[7],f[7],a[4],b[9],c[8],f[8],g[7],g[8],h[7],h[8]],
            targets=e[5:7]+h[5:7],filter_coefficients=[literal(stream[o+i:o+i+3])
                for o,i in ((rows[1][0],22),(rows[2][0],18),(rows[3][0],10),
                            (rows[4][0],14),(rows[5][0],18),(rows[6][0],18))])
        if assemble_cascaded_history_pair(spec)!=stream:
            raise ValueError('Unsupported cascade controls, coefficients, tags or aliases')
        return spec
    if len(stream)==110:
        rows=packets(stream)
        if [len(words)for _,words in rows]!=[5,10,12,10,7,6,5]:
            raise ValueError('Not an exact post-cubic mix profile')
        a,b,c,d,e,f,g=[words for _,words in rows]
        spec=dict(kind='post_cubic_mix_pair',sources=[a[3],b[5],c[7],a[4],b[6],c[8]],
                  targets=e[5:7],output_addresses=g[3:5],coefficient_slots=[d[6]&0xfff],
                  post_scale_literal=stream[rows[5][0]+6:rows[5][0]+9].hex())
        if assemble_post_cubic_mix_pair(spec)!=stream:
            raise ValueError('Unsupported post-cubic controls, literals, tags or aliases')
        return spec
    if len(stream) == 122:
        from bmc_dsp import literal
        rows=packets(stream)
        if [len(words) for _,words in rows] != [5,14,12,8,12,5,5]:
            raise ValueError('Not an exact resample/drive profile')
        a,b,c,d,e,f,g=[words for _,words in rows]
        spec=dict(kind='resample_drive_pair',sources=[a[3],b[7],c[7],a[4],b[9],c[8],f[4]],
                  output_addresses=g[3:5],coefficient_slots=[e[8]&0xfff],
                  drive_literal=stream[rows[4][0]+18:rows[4][0]+21].hex(),
                  tap_coefficients=[literal(stream[offset+field:offset+field+3])
                                    for offset,field in ((rows[1][0],22),(rows[2][0],18),(rows[3][0],10))])
        if assemble_resample_drive_pair(spec) != stream:
            raise ValueError('Unsupported resample/drive controls, literals, duplicates or aliases')
        return spec
    if len(stream) in (194, 226):
        base_length = len(stream)-10
        base = disassemble_fragment(stream[:base_length])
        rows = packets(stream[base_length:])
        if len(rows) != 1 or len(rows[0][1]) != 5:
            raise ValueError('Expected one exact filter output-store packet')
        kind = ('state_variable_pair_with_output' if base_length == 184
                else 'state_variable_recombine_pair_with_output')
        spec = dict(base, kind=kind, output_addresses=rows[0][1][3:5])
        if assemble_filter_with_output(spec) != stream:
            raise ValueError('Unsupported filter output stores')
        return spec
    if len(stream) == 202:
        rows = [words for _, words in packets(stream)]
        if [len(row) for row in rows] != [7,7,5,13,15,7,9,5,11,11,3,3,5]:
            raise ValueError('Not an exact terminal filter profile')
        spec = dict(kind='state_variable_terminal_pair_with_output',
                    sources=rows[0][4:7]+rows[1][4:7],
                    targets=[rows[4][11],rows[4][13],rows[8][7],rows[8][9]],
                    coefficient_slots=[rows[i][j] & 0xfff for i,j in
                                       ((2,3),(3,11),(5,5),(8,8),(4,12),(9,10))],
                    output_addresses=rows[12][3:5])
        if assemble_terminal_filter(spec) != stream:
            raise ValueError('Unsupported terminal filter controls, fields or aliases')
        return spec
    if len(stream) == 216:
        rows = [words for _, words in packets(stream)]
        if [len(row) for row in rows] != [7, 7, 5, 13, 15, 7, 9, 5, 11, 11, 7, 11]:
            raise ValueError('Not an exact filter/recombination profile')
        spec = dict(kind='state_variable_recombine_pair',
                    sources=rows[0][4:7]+rows[1][4:7]+rows[10][5:7]+[rows[11][7], rows[11][9]],
                    targets=[rows[4][11], rows[4][13], rows[8][7], rows[8][9]],
                    coefficient_slots=[rows[i][j] & 0xfff for i,j in
                                       ((2,3),(3,11),(5,5),(8,8),(4,12),(9,10),(11,8))])
        if assemble_filter_recombine(spec) != stream:
            raise ValueError('Unsupported filter/recombination controls, aliases or tags')
        return spec
    if len(stream) == 86:
        rows = [words for _, words in packets(stream)]
        if [len(row) for row in rows] != [7, 13, 11, 7, 5]:
            raise ValueError('Not an exact stereo_prefilter profile')
        a, b, c, d, e = rows
        spec = dict(kind='stereo_prefilter', input_addresses=a[4:6],
                    sources=[b[8], c[8], b[11], c[10], *d[5:7]], targets=[b[10], b[12], *e[3:5]],
                    coefficient_slots=[a[6] & 0xfff, b[9] & 0xfff, c[9] & 0xfff])
        if assemble_stereo_prefilter(spec) != stream:
            raise ValueError('Unsupported prefilter controls, extensions or resource fields')
        return spec
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
