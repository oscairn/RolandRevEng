"""Check 9ed9 and later fixed-point windows against native store cutpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import literal, packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256
from kernel_abi import program_list, read
from line_mix_variation import packet_literals
from line_shaping_study import EPSILON, NATIVE_SHA256, _finite, decode_constant, decode_quantizer
from weighted_mix_study import check_constructor_literal, require_instructions, require_window, require_words

VMCP_LIST = 0x6113d2b8


def vmcp_detector_reference(held, state, *, scale, bias):
    """Model the finite native interval between the checked VMCP stores."""
    product = _finite(held) * _finite(state)
    unclipped = _finite(product * _finite(scale))
    return _finite(min(1.0, max(-1.0, unclipped)) + _finite(bias))


def vmcp_packets(program):
    rows = dict(packets(program))
    for offset, prefix in (
        (0x36, (0x1b04, 0x9442, 0x3fe0)), (0x3e, (0x1804, 0x1443, 0x9fe0)),
        (0x46, (0x0904, 0x1460)), (0x4e, (0x0a02, 0x9ed9)),
        (0x52, (0x3408, 0x1c64, 0x6fe0, 0x7fe2)), (0x62, (0x2e08, 0x0462, 0x44e5, 0x9fe0)),
        (0xe2, (0x1b04, 0xbc12, 0x8fe0)), (0xea, (0x1e05, 0x0fe0, 0x4fe2)),
        (0xf4, (0x5f07, 0x0403, 0x4503, 0x8fe0, 0xcfe2)), (0x102, (0x0c03, 0x3fe0)),
        (0x108, (0x0a02, 0xbcd4)), (0x10c, (0x1503, 0x0403, 0x4503)),
        (0x112, (0x1e05, 0x8fe0, 0xcfe2)),
    ):
        require_words(rows, offset, prefix)
    if rows[0x102][2] >> 12 != 0xc:
        raise ValueError('VMCP gain transfer is outside the coefficient space')
    state, held, detector = (rows[offset][index] for offset, index in ((0x36, 3), (0x3e, 3), (0x62, 4)))
    before_shift = rows[0xe2][3]
    after_gain = rows[0x112][3:5]
    cells = [state, held, detector, before_shift, *after_gain]
    if len(set(cells)) != len(cells) or any(address >= 0x800 for address in cells):
        raise ValueError('VMCP cutpoint addresses alias or exceed data range')
    return dict(state=state, held=held, detector=detector, before_shift=before_shift,
                coefficient_slot=rows[0x102][2] & 0xfff, after_gain=after_gain,
                scale=literal(program[0x4a:0x4d]), bias=literal(program[0x5e:0x61]))


def native_context(cls):
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from transfer_study import constructor_memory, native_accesses, records_from_memory

    length, program, *_ = parse.program(cls)
    ctor = parse.parse_ctor(cls)
    lo, hi = lib.func(ctor['ctor'])
    md = lib.md()
    md.detail = True
    constructor = list(md.disasm(lib.Z[lo:hi], lo))
    memory = constructor_memory(constructor, lib.Z)
    base, count, previous = parse.parse_datsym(cls, ctor)
    records = records_from_memory(memory, base, count)
    if records != previous:
        raise ValueError(f'{cls}: constructor address records differ')
    fields = {base+8*i+4: dict(relative=relative, address=address)
              for i, (relative, address) in enumerate(records)}
    _, _, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    trace = native_accesses(code, fields, coefficient_pointer_fields(constructor))
    return program[:length], {ins.address: ins for ins in code}, memory, fields, trace


def checked_access(instructions, fields, trace, pc, kind, relative, address):
    from operand_variants_study import check_bindings

    result = check_bindings([row for row in trace['accesses'] if row['pc'] == pc], fields,
                            [dict(kind=kind, relative=relative, address=address)], instructions)
    if not result['verified']:
        raise ValueError(f'Native data path or field differs at {pc:#x}')
    return result['accesses'][0]


def vmcp_report():
    from condition_return_study import preserved

    program, native, memory, fields, trace = native_context('SIM_MFX_VMCP')
    context = vmcp_packets(program)
    rows = dict(packets(program))
    require_window(native, 0x39da68, 0x39dac8)
    require_instructions(native, 0x39da90, (
        ('str', 'd0, [x10, w14, uxtw #3]'), ('fmul', 'd0, d2, d0'), ('ldr', 'd1, [x8, #0xd8]'),
        ('fmul', 'd0, d0, d1'), ('fmov', 'd1, #1.00000000'), ('fmin', 'd3, d0, d1'),
        ('fmov', 'd4, #-1.00000000'), ('fcmp', 'd0, d4'), ('fcsel', 'd0, d4, d3, mi'),
        ('ldr', 'd3, [x8, #0x58]'), ('fadd', 'd0, d3, d0'),
    ))
    require_instructions(native, 0x39da78, (('ldr', 'd2, [x10, w14, uxtw #3]'),))
    require_instructions(native, 0x39dac8, (('str', 'd0, [x10, w14, uxtw #3]'),))
    preserved([native[pc] for pc in range(0x39da7c, 0x39da94, 4)], 'd2')
    preserved([native[pc] for pc in range(0x39dabc, 0x39dac8, 4)], 'd0')
    for offset, pc in ((0x46, 0x39da98), (0x52, 0x39dab4)):
        field, = packet_literals(program, offset, rows[offset])
        check_constructor_literal(program, memory, native[pc], field)
    def access(pc, kind, relative, address):
        return checked_access(native, fields, trace, pc, kind, relative, address)

    detector = [access(pc, kind, relative, context[key]) for pc, kind, relative, key in (
        (0x39da78, 'read', 0x3c, 'state'), (0x39da90, 'write', 0x44, 'held'),
        (0x39dac8, 'write', 0x6a, 'detector'))]

    require_window(native, 0x39dba8, 0x39dc44)
    require_instructions(native, 0x39dba8, (('str', 'd0, [x10, w14, uxtw #3]'),))
    require_instructions(native, 0x39dbc0, (('fmul', 'd0, d0, d1'),))
    require_instructions(native, 0x39dbec, (('fmul', 'd2, d2, d0'),))
    require_instructions(native, 0x39dc00, (('fmul', 'd0, d3, d0'),))
    require_instructions(native, 0x39dc0c, (('fcvt', 'd3, s3'),))
    require_instructions(native, 0x39dc1c, (('fmul', 'd1, d3, d1'), ('fmul', 'd2, d2, d1')))
    require_instructions(native, 0x39dc34, (('fmul', 'd0, d0, d1'),))
    if dict(pc=0x39dc08, slot=context['coefficient_slot'], width=4) not in trace['coefficient_reads']:
        raise ValueError('VMCP shift-four coefficient binding differs')
    epsilon = decode_constant([native[0x39dbb8], native[0x39dbbc]])
    if epsilon['value'] != EPSILON or epsilon['register'] != 'd1':
        raise ValueError('VMCP fixed-point rescale differs')
    for register, start, end in (('d0', 0x39dbc4, 0x39dc00), ('d1', 0x39dbc0, 0x39dc1c),
                                 ('d2', 0x39dbf0, 0x39dc20), ('d0', 0x39dc04, 0x39dc34)):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    fixed = [decode_quantizer([native[pc] for pc in range(start, start+12, 4)], shift_bits=shift)
             for start, shift in ((0x39dbac, 2), (0x39dc10, 4))]
    if [row['floating'] for row in fixed] != ['d0', 'd3']:
        raise ValueError('VMCP quantizer floating source differs')
    before_shift = access(0x39dba8, 'write', 0xbc, context['before_shift'])
    after_gain = [access(pc, 'write', relative, address) for pc, relative, address in
                  zip((0x39dc30, 0x39dc44), (0x118, 0x11a), context['after_gain'])]
    return dict(packets=context, detector_bindings=detector, quantizers=fixed,
                before_shift=before_shift, after_gain=after_gain)


def ring_report():
    from condition_return_study import preserved

    program, native, _, fields, trace = native_context('SIM_MFX_RING')
    rows = dict(packets(program))
    require_words(rows, 0xdc, (0x3e06, 0x0f20, 0x1fe0, 0x2fe2, 7, 8))
    require_words(rows, 0xfa, (0x1405, 0x140b, 0x8fe2, 2, 6))
    require_words(rows, 0x104, (0x3106, 0x0410, 0x9ed9, 0x3fe2, 0x4200, 0xc007))
    require_words(rows, 0x110, (0xb84b, 0x3403, 0x7403, 0x9fe0, 0x0fe2, 0x1fe4, 0x2fe6, 7))
    require_window(native, 0x277c4c, 0x277e00)
    require_instructions(native, 0x277c4c, (('fmov', 'd0, #1.00000000'),))
    require_instructions(native, 0x277c54, (('fmov', 'd1, #-1.00000000'),))
    require_instructions(native, 0x277dd0, (('fmadd', 'd2, d3, d2, d4'),))
    require_instructions(native, 0x277de0, (('fmin', 'd0, d2, d0'), ('fcmp', 'd2, d1'),
                                           ('fcsel', 'd0, d1, d0, mi'), ('fadd', 'd1, d3, d3'),
                                           ('fmul', 'd1, d1, d4')))
    require_instructions(native, 0x277e00, (('str', 'd0, [x9, w14, uxtw #3]'),))
    for register, start, end in (('d0', 0x277c50, 0x277de0), ('d1', 0x277c58, 0x277de8),
                                 ('d2', 0x277dd4, 0x277de4), ('d0', 0x277dec, 0x277e00)):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    before = checked_access(native, fields, trace, 0x277dcc, 'write', 0x102, 6)
    after = checked_access(native, fields, trace, 0x277e00, 'write', 0xe4, 7)
    if dict(pc=0x277dd8, slot=7, width=4) not in trace['coefficient_reads']:
        raise ValueError('RING co-issued coefficient path differs')
    return dict(before=before, after=after, store_operand=0x11e, same_cell_as_field=0xe4)


def native_report():
    import lib
    from line_prefix_study import descriptor, literal_calls

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded ZENOLOGY image')
    md = lib.md()
    md.detail = True
    setter = list(md.disasm(lib.Z[0x17e318:0x17e350], 0x17e318))
    require_instructions({ins.address: ins for ins in setter}, 0x17e330,
                         (('adrp', 'x9, #0x7b5000'), ('add', 'x9, x9, #0x730'),
                          ('ldr', 'd0, [x9, w8, uxtw #3]')))
    calls = literal_calls(setter)
    if calls != [dict(slot_load=0x17e340, call=0x17e34c, symbol=0xa177c8)]:
        raise ValueError('Native VMCP threshold writer differs')
    group = descriptor(lib.Z, 0xa177c8)
    if group['records'] != [dict(absolute_byte=0x406a, relative_byte=0x4a, width=3)]:
        raise ValueError('Native VMCP threshold field differs')
    native_values = struct.unpack_from('<128d', lib.Z, 0x7b5730)
    table = struct.pack('<128f', *native_values)
    if struct.unpack('<128f', table) != native_values:
        raise ValueError('Native VMCP threshold values cannot be represented exactly in float32')
    return dict(vmcp=vmcp_report(), ring=ring_report(), strict_dsp_admission=False,
                threshold=dict(field=0x4a, table_sha256=hashlib.sha256(table).hexdigest(),
                               endpoints=[native_values[0], native_values[-1]]))


def fantom_report(core):
    from dramio_owner_study import expect

    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the recorded Fantom CORE1 image')
    results = []
    for segment in program_list(core, VMCP_LIST)['segments']:
        size, source = segment['length'], segment['source']
        stream = swap_words(read(core, source, (size+3) & ~3))[:size]
        results.append(dict(base=segment['base'], source=source, **vmcp_packets(stream)))
    for pc, mnemonic, operands in (
        (0x610641e8, 'ldr', 'r2, [pc, #0x230]'),
        (0x610641ec, 'add.w', 'r1, r2, r1, lsl #2'),
        (0x610641f0, 'vldr', 's0, [r1]'), (0x610641f4, 'ldr', 'r1, [r0]'),
        (0x610641f6, 'ldr', 'r2, [r1, #0x64]'),
        (0x610641f8, 'ldr', 'r1, [pc, #0x224]'), (0x610641fa, 'bx', 'r2'),
    ):
        expect(core, pc, mnemonic, operands)
    if (core.u32(0x61176d88) != 0x610641db or core.u32(0x611764e0) != 0x011327e7
            or core.u32(0x6106441c) != 0x6113d86c or core.u32(0x61064420) != 0x6113d348):
        raise ValueError('Fantom VMCP threshold call targets differ')
    table = read(core, 0x6113d86c, 128*4)
    values = struct.unpack('<128f', table)
    pointer, count = struct.unpack('<IB3x', read(core, 0x6113d350, 8))
    if count != 1 or struct.unpack('<III', read(core, pointer, 12)) != (0x406a, 0x4a, 3):
        raise ValueError('Fantom VMCP threshold field differs')
    return dict(placements=results, threshold=dict(field=0x4a, table_sha256=hashlib.sha256(table).hexdigest(),
                                                  endpoints=[values[0], values[-1]]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    report = native_report()
    if args.core1:
        from core1 import Core1

        report['fantom_vmcp'] = fantom_report(Core1(args.core1))
        if report['threshold'] != report['fantom_vmcp']['threshold']:
            parser.error('Native and Fantom VMCP threshold tables differ')
    print(json.dumps(report, indent=2, allow_nan=False))
