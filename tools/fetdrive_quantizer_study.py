"""Trace FETDRIVE from mixed input to the first shaped-value store."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from bmc_dsp import literal, packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256
from kernel_abi import program_list, read
from header_study import layout
from line_mix_variation import packet_literals
from line_shaping_study import (EPSILON, NATIVE_SHA256, _finite, _float32, decode_constant,
                                decode_quantizer, quantize_native_reference)
from weighted_mix_study import require_instructions, require_window, require_words

FET_LIST = 0x610e7b88
BIAS = 0.33334
SLOPE = 0.33333


def native_shaped_store(mixed, *, drive, scale, post_gain):
    """Compute the native T cutpoint under the same IEEE policy as LINE."""
    if not hasattr(math, 'fma'):
        raise ValueError('This reference requires Python 3.13+ math.fma')
    gain = _finite(_float32(drive) * _finite(scale))
    prequantized = _finite(gain * _finite(mixed))
    quantized = quantize_native_reference(prequantized)['quantized']
    clipped = min(1.0, max(-1.0, quantized))
    affine = math.fma(clipped, SLOPE, BIAS)
    return dict(prequantized=prequantized, quantized=quantized, clipped=clipped,
                stored=_finite(_finite(post_gain) * (affine * affine)))


def packet_context(stream):
    """Locate the two bounded windows and read their actual operand fields."""
    rows = dict(packets(stream))
    require_words(rows, 0x1a, (0x220a, 0x2426, 0x3469, 0x5fe4, 4, 4))
    require_words(rows, 0x2e, (0x3408, 0x5564, 0xafe0, 0xbfe2))
    coefficient = rows[0x1a][6]
    if coefficient >> 12 != 0xc:
        raise ValueError('FETDRIVE drive coefficient tag differs')
    sources = rows[0x2e][4:6]
    targets, affine_fields = [], []
    for start, source in zip((0x3e, 0xd4), sources):
        for delta, words in (
            (0, (0x0c03, 0x0fe0, source)), (6, (0x0902, 0x1405)),
            (0xa, (0x0a02, 0x9c59)), (0xe, (0x0a02, 0x9ed9)),
            (0x12, (0x0805, 0x3452, 0x0014)), (0x1c, (0x0902, 0x14c3)),
            (0x20, (0x0904, 0x1460)), (0x28, (0x0c03, 0x9fe0)),
        ):
            require_words(rows, start + delta, words)
        targets.append(rows[start + 0x28][2])
        affine = rows[start + 0x12]
        if [reg['index'] for reg in layout(affine)['registers']] != [0]:
            raise ValueError('FETDRIVE affine packet register reference differs')
        fields = packet_literals(stream, start + 0x12, affine)
        if len(fields) != 2 or any(field['width'] != 2 for field in fields):
            raise ValueError('FETDRIVE affine literal references differ')
        affine_fields.append(fields)
    if len(set(sources + targets)) != 4 or any(address >= 0x800 for address in sources + targets):
        raise ValueError('FETDRIVE mixed-input and shaped-output addresses alias or exceed data range')
    return dict(sources=sources, targets=targets, coefficient_slot=coefficient & 0xfff,
                scale=literal(stream[0x3a:0x3d]),
                affine_literals=[[field['value'] for field in fields] for fields in affine_fields],
                post_gain=[literal(stream[pos:pos+3]) for pos in (0x62, 0xf8)])


def transient_gain_report():
    """Independently anchor the 1406/5506 short-gain pair and next stores."""
    from condition_return_study import preserved
    from limit_control_study import native_context

    program, native, _, fields, _ = native_context('SIM_MFX_TRANSIENT')
    rows = dict(packets(program))
    require_words(rows, 0x2a4, (0x1e05, 0x3fe0, 0x7fe2, 0x26, 0x28))
    require_words(rows, 0x2ae, (0x5f08, 0x6ed0, 0x74c7, 0x0fe2, 0x4fe4, 0x3000, 0x2016, 0x2017))
    require_words(rows, 0x2be, (0x1503, 0x1406, 0x5506))
    require_words(rows, 0x2c4, (0xb408, 0x1407, 0x5507, 0xbecf, 0x9fe0, 0xdfe2, 8, 9))
    field, = packet_literals(program, 0x2ae, rows[0x2ae])
    if field['value'] != 1.0:
        raise ValueError('TRANSIENT complement literal differs')
    if [fields[field] for field in (0x214, 0x124, 0x12c)] != [
            dict(relative=0x27c, address=0x26), dict(relative=0x2d0, address=8),
            dict(relative=0x2d2, address=9)]:
        raise ValueError('TRANSIENT gain and store records differ')
    require_instructions(native, 0x1d6004, (('ldr', 'x21, [x0, #0x28]'), ('ldr', 'x8, [x0, #8]'),
                                           ('ldr', 'x22, [x8, #0x18]'), ('ldr', 'x8, [x22, #0x10]'),
                                           ('ldp', 'x25, x26, [x1]')))
    require_instructions(native, 0x1d6050, (('ldr', 'x23, [x8, #0x18]'),))
    for reg, start in (('x21', 0x1d6008), ('x25', 0x1d6018), ('x26', 0x1d6018),
                       ('x23', 0x1d6054), ('w27', 0x1d6228)):
        preserved([native[pc] for pc in range(start, 0x1d6594, 4)], reg)
    require_window(native, 0x1d6540, 0x1d6594)
    require_instructions(native, 0x1d6540, (('ldr', 'w8, [x21, #0x214]'), ('add', 'w8, w27, w8'),
                                           ('and', 'w8, w8, #0x7ff'), ('ldr', 'd2, [x23, w8, uxtw #3]')))
    require_instructions(native, 0x1d6560, (
        ('fmov', 'd4, #1.00000000'), ('fsub', 'd5, d4, d2'), ('ldr', 'd0, [x25]'), ('ldr', 'd1, [x26]'),
        ('fmul', 'd6, d5, d0'), ('ldr', 'w8, [x21, #0x124]'), ('add', 'w8, w27, w8'),
        ('and', 'w8, w8, #0x7ff'), ('str', 'd6, [x23, w8, uxtw #3]'), ('fmul', 'd6, d5, d1'),
        ('ldr', 'w8, [x21, #0x12c]'), ('add', 'w8, w27, w8'), ('and', 'w8, w8, #0x7ff'),
        ('str', 'd6, [x23, w8, uxtw #3]'),
    ))
    return dict(packet=0x2be, controls=[0x1406, 0x5506], sample_load_ports=[0, 4],
                store_ports=[1, 5], native_stores=[0x1d6580, 0x1d6594],
                native_factor='1 - data[0x26]')


def native_report():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from condition_return_study import preserved
    from line_prefix_study import descriptor, literal_calls
    from operand_variants_study import check_bindings
    from transfer_study import constructor_memory, native_accesses, records_from_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded native artifact')
    cls = 'SIM_MFX_FETDRIVE'
    length, program, *_ = parse.program(cls)
    context = packet_context(program[:length])
    _, _, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    instructions = {ins.address: ins for ins in code}

    def window(start, end):
        return [instructions[pc] for pc in range(start, end, 4)]

    require_window(instructions, 0x2f7e18, 0x2f8018)
    require_instructions(instructions, 0x2f7e20, (('fcvt', 'd2, s2'),))
    require_instructions(instructions, 0x2f7e58, (('ldr', 'd0, [x8, #0x58]'), ('fmul', 'd2, d0, d2')))
    preserved(window(0x2f7e24, 0x2f7e5c), 'd2')
    preserved(window(0x2f7e60, 0x2f7fdc), 'd2')
    preserved(window(0x2f7e20, 0x2f8018), 'x8')
    for lo, expected in (
        (0x2f7e70, (('fmul', 'd0, d2, d7'),)),
        (0x2f7e88, (('fmul', 'd4, d0, d3'), ('fmov', 'd0, #1.00000000'),
                    ('fmin', 'd5, d4, d0'), ('fmov', 'd1, #-1.00000000'),
                    ('fcmp', 'd4, d1'), ('fcsel', 'd6, d1, d5, mi'))),
        (0x2f7ec8, (('fmadd', 'd6, d6, d5, d4'), ('fmul', 'd6, d6, d6'),
                    ('ldr', 'd16, [x8, #0x38]'), ('fmul', 'd16, d16, d6'))),
        (0x2f7fdc, (('fmul', 'd2, d2, d7'),)),
        (0x2f7fec, (('fmul', 'd2, d2, d3'), ('fmin', 'd3, d2, d0'), ('fcmp', 'd2, d1'),
                    ('fcsel', 'd2, d1, d3, mi'), ('fmadd', 'd2, d2, d5, d4'),
                    ('fmul', 'd2, d2, d2'), ('ldr', 'd3, [x8, #0x38]'), ('fmul', 'd2, d3, d2'))),
        (0x2f7ee4, (('str', 'd16, [x9, w13, uxtw #3]'),)),
        (0x2f8018, (('str', 'd2, [x9, w13, uxtw #3]'),)),
    ):
        require_instructions(instructions, lo, expected)
    for register, start, end in (('d0', 0x2f7e90, 0x2f7ff0), ('d1', 0x2f7e98, 0x2f7ff4),
                                 ('d3', 0x2f7e88, 0x2f7fec), ('d4', 0x2f7eb4, 0x2f7ffc),
                                 ('d5', 0x2f7ec8, 0x2f7ffc), ('d6', 0x2f7ea0, 0x2f7ec8),
                                 ('d16', 0x2f7ed8, 0x2f7ee4), ('d2', 0x2f800c, 0x2f8018)):
        preserved(window(start, end), register)
    constants = [decode_constant(window(start, end))['value'] for start, end in (
        (0x2f7e80, 0x2f7e88), (0x2f7ea0, 0x2f7eb4), (0x2f7eb4, 0x2f7ec8))]
    if constants != [EPSILON, BIAS, SLOPE]:
        raise ValueError('Native scale, bias or slope differs')
    quantizers = [decode_quantizer(window(start, start+12)) for start in (0x2f7e74, 0x2f7fe0)]
    if [row['floating'] for row in quantizers] != ['d0', 'd2']:
        raise ValueError('Native quantizer register changed')

    ctor = parse.parse_ctor(cls)
    start, end = lib.func(ctor['ctor'])
    md = lib.md()
    md.detail = True
    constructor = list(md.disasm(lib.Z[start:end], start))
    memory = constructor_memory(constructor, lib.Z)
    base, count, previous = parse.parse_datsym(cls, ctor)
    records = records_from_memory(memory, base, count)
    if records != previous:
        raise ValueError('Constructor address records differ')
    fields = {base + 8*i + 4: dict(relative=relative, address=address)
              for i, (relative, address) in enumerate(records)}
    accesses = native_accesses(code, fields, coefficient_pointer_fields(constructor))
    if accesses['coefficient_reads'][0] != dict(pc=0x2f7e1c, slot=context['coefficient_slot'], width=4):
        raise ValueError('Native FETDRIVE live gain binding differs')
    for start, end, source_field, target_field, channel in (
        (0x2f7e60, 0x2f7ee4, 0x36, 0x6a, 0), (0x2f7fcc, 0x2f8018, 0x38, 0x100, 1),
    ):
        checked = check_bindings([row for row in accesses['accesses'] if start <= row['pc'] <= end], fields,
                                 [dict(kind='read', relative=source_field, address=context['sources'][channel]),
                                  dict(kind='write', relative=target_field, address=context['targets'][channel])],
                                 instructions)
        if not checked['verified'] or [row['pc'] for row in checked['accesses']] != [start+12, end]:
            raise ValueError('Native FETDRIVE data binding differs')
        quantizers[channel]['data_bindings'] = checked['accesses']
    defaults = {}
    for name, field, record in (('scale', 0x3a, 0x50), ('post_gain', 0x62, 0x30)):
        if int.from_bytes(bytes(memory[i] for i in range(record, record+4)), 'little') != field:
            raise ValueError('Native constructor literal field differs')
        defaults[name], = struct.unpack('<d', bytes(memory[i] for i in range(record+8, record+16)))
    setup = {ins.address: ins for ins in md.disasm(lib.Z[0x32c8a4:0x32ca48], 0x32c8a4)}
    require_instructions(setup, 0x32c8e8, (('adrp', 'x8, #0xb78000'), ('add', 'x8, x8, #0xaf0'),
                                           ('ldr', 's0, [x8]'), ('sshll', 'v0.2d, v0.2s, #0'),
                                           ('scvtf', 'd9, d0')))
    preserved([setup[pc] for pc in range(0x32c8fc, 0x32c994, 4)], 'd9')
    require_instructions(setup, 0x32c994, (('fdiv', 'd0, d0, d9'),))
    numerator = decode_constant([setup[pc] for pc in range(0x32c988, 0x32c994, 4)])
    calls = literal_calls([setup[pc] for pc in range(0x32c984, 0x32c9ac, 4)])
    if numerator['value'] != 44100 or calls != [dict(slot_load=0x32c99c, call=0x32c9a8, symbol=0xa50df8)]:
        raise ValueError('FETDRIVE setup post-gain call differs')
    group = descriptor(lib.Z, calls[0]['symbol'])
    if [(row['relative_byte'], row['width']) for row in group['records']] != [(0x62, 3), (0xf8, 3)]:
        raise ValueError('FETDRIVE setup post-gain group differs')
    initial_divisor, = struct.unpack_from('<i', lib.Z, 0xb78af0)
    return dict(native_defaults=defaults, bias=BIAS, slope=SLOPE, quantizers=quantizers,
                gain_comparison=transient_gain_report(),
                quantizer_input_port_candidate=1, first_store_port=1, isolated_writeback_verified=False,
                desktop_packets=context, post_gain_setup=dict(numerator=numerator['value'],
                    initial_divisor=initial_divisor, divisor_field=0xb78af0, group=group))


def fantom_report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the recorded Fantom CORE1 image')
    result = []
    for segment in program_list(core, FET_LIST)['segments']:
        length = segment['length']
        program = swap_words(read(core, segment['source'], (length+3) & ~3))[:length]
        result.append(dict(base=segment['base'], source=segment['source'], **packet_context(program)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    result = native_report()
    if args.core1:
        from core1 import Core1

        result['fantom_packets'] = fantom_report(Core1(args.core1))
    result['hardware_execution_verified'] = False
    print(json.dumps(result, indent=2, allow_nan=False))
