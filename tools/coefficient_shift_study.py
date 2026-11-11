"""Trace signed fixed-point shift-by-four coefficient paths in VMCP and VSOD."""
import argparse
import hashlib
import json
from pathlib import Path

from bmc_dsp import command_count, packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256
from kernel_abi import program_list, read
from limit_control_study import checked_access, native_context, vmcp_report
from line_mix_variation import packet_literals
from line_shaping_study import EPSILON, NATIVE_SHA256, _finite, _float32, decode_constant
from line_shaping_study import decode_quantizer, quantize_native_reference
from weighted_mix_study import check_constructor_literal, require_instructions, require_window, require_words

VSOD_LISTS = {'VSOD': 0x611402f4, 'VSODDSAW': 0x611421fc, 'VSODDSTW': 0x611444e0}


def native_shift4_coefficient(coefficient):
    """Transform one live float under the checked native numeric policy."""
    return quantize_native_reference(_float32(coefficient), shift_bits=4)['quantized']


def native_selected_gain(coefficient, mode_delta):
    """Select the converted coefficient or unity using the native VSOD predicate."""
    shifted = native_shift4_coefficient(coefficient)
    return shifted if -EPSILON < _finite(mode_delta) < EPSILON else 1.0


def indexed_operand(words, control):
    return words[1 + command_count(words[0]) + ((control & 15) // 2)]


def packet_context(effect, program):
    rows = dict(packets(program))
    if effect == 'VSOD':
        require_words(rows, 4, (0x3e07, 0x0fe0, 0x1fe2, 0x7fe4))
        require_words(rows, 0x12, (0x2808, 0x0812, 0xfdd4, 0x3fe6, 0x1500))
        require_words(rows, 0x22, (0x1804, 0x0403, 0xffe0))
        address = indexed_operand(rows[4], 0x7fe4)
        if indexed_operand(rows[0x12], 0x3fe6) != address - 1:
            raise ValueError('VSOD companion C0 load differs')
        result = dict(packet=0x12, control=0xfdd4, load_port=7,
                      store_port=7, data_store=indexed_operand(rows[0x22], 0xffe0))
    elif effect == 'VSODDSAW':
        require_words(rows, 0x17e, (0x220a, 0x04a6, 0x6569, 0x3fe4))
        require_words(rows, 0x192, (0xb14d, 0x0426, 0x7050, 0xee12, 0xde69, 0x8fe4, 0xb9b3))
        require_words(rows, 0x1ac, (0x4b0a, 0x04a4, 0x4067, 0xbcd4, 0x2fe2))
        address = indexed_operand(rows[0x17e], 0x3fe4)
        result = dict(packet=0x1ac, control=0xbcd4, load_port=3)
    elif effect == 'VSODDSTW':
        require_words(rows, 0x1a8, (0x8f0e, 0x04aa, 0x652d, 0x2fe4, 0x3fe6, 0x4fe8))
        require_words(rows, 0x1c4, (0x884e, 0x04a8, 0x652b, 0xbcd4, 0xfe14, 0xb9b4, 0x4fe6))
        address = indexed_operand(rows[0x1a8], 0x3fe6)
        result = dict(packet=0x1c4, control=0xbcd4, load_port=3)
    else:
        raise ValueError('Expected one of the three VSOD contexts')
    if address >> 12 != 0xc:
        raise ValueError('VSOD coefficient operand is outside the coefficient space')
    return dict(coefficient_slot=address & 0xfff, **result)


def check_conversion(native, start, source, output, scaled, epsilon, *, shift_bits=4):
    quantizer = decode_quantizer([native[pc] for pc in range(start, start+12, 4)],
                                 shift_bits=shift_bits, output_register=output)
    constant = decode_constant([native[start+12], native[start+16]])
    if (quantizer['floating'] != source or constant['value'] != EPSILON
            or constant['register'] != epsilon):
        raise ValueError('VSOD source or scale differs')
    require_instructions(native, start+20, (('fmul', f'{scaled}, {output}, {epsilon}'),))
    return quantizer


def base_report():
    from condition_return_study import preserved

    program, native, _, fields, trace = native_context('SIM_MFX_VSOD')
    context = packet_context('VSOD', program)
    require_window(native, 0x273928, 0x273984)
    require_instructions(native, 0x273930, (('fcvt', 'd3, s0'),))
    preserved([native[pc] for pc in range(0x273934, 0x27394c, 4)], 'd3')
    for pc, slot in ((0x27392c, context['coefficient_slot']), (0x273938, context['coefficient_slot'] - 1)):
        if dict(pc=pc, slot=slot, width=4) not in trace['coefficient_reads']:
            raise ValueError('VSOD live coefficient provenance differs')
    quantizer = check_conversion(native, 0x27394c, 'd3', 'd2', 'd3', 'd3')
    require_instructions(native, 0x273984, (('str', 'd3, [x10, w14, uxtw #3]'),))
    preserved([native[pc] for pc in range(0x273964, 0x273984, 4)], 'd3')
    store = checked_access(native, fields, trace, 0x273984, 'write', 0x28, context['data_store'])
    return dict(packets=context, quantizer=quantizer, store=store)


def coefficient_context(cls):
    import lib
    import parse
    from alu_study import coefficient_pointer_fields

    size, program, *_ = parse.program(cls)
    ctor = parse.parse_ctor(cls)
    lo, hi = lib.func(ctor['ctor'])
    md = lib.md()
    md.detail = True
    constructor = list(md.disasm(lib.Z[lo:hi], lo))
    entry, _, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    return program[:size], constructor, coefficient_pointer_fields(constructor), entry, code


def check_entry(code, native, entry, start, end, other_entries):
    import capstone
    from capstone import arm64
    from condition_return_study import preserved

    require_instructions(native, entry, (('ldr', 'x8, [x0, #0x28]'),))
    preserved([native[pc] for pc in range(entry+4, start, 4)], 'x8')
    if any(ins.group(capstone.CS_GRP_CALL) or ins.mnemonic == 'br' for ins in code if ins.address < end):
        raise ValueError('Coefficient path crosses an unchecked call or indirect branch')
    inbound = [(ins.address, ins.operands[-1].imm) for ins in code
               if ins.group(capstone.CS_GRP_JUMP) and ins.operands[-1].type == arm64.ARM64_OP_IMM
               and start < ins.operands[-1].imm <= end]
    if inbound != other_entries:
        raise ValueError('Coefficient interval has an unchecked control-flow entry')
    require_window(native, start, end)


def variant_report(effect):
    from condition_return_study import preserved

    program, _, coefficient_fields, entry, code = coefficient_context('SIM_MFX_' + effect)
    context = packet_context(effect, program)
    native = {ins.address: ins for ins in code}

    def window(start, end):
        return [native[pc] for pc in range(start, end, 4)]

    if effect == 'VSODDSAW':
        pointer, field, load, fp = 0x178fe8, 0xbb0, 0x179188, '3'
        quant, output, eps, epsilon_neg, select = 0x1791d4, 'd3', 'd2', 0x1791f8, 0x179268
        other_entries = [(0x178f8c, 0x179114)]
        require_instructions(native, 0x178f84, (('cbz', 'w12, #0x178f90'),
                                                ('ldr', 'x12, [x8, #0xbb0]'), ('b', '#0x179114')))
        require_instructions(native, 0x17925c, (('fcmp', 'd6, d1'), ('fccmp', 'd6, d2, #0, gt'),
                                                ('fmov', 'd5, #1.00000000'), ('fcsel', 'd6, d3, d5, mi')))
    else:
        pointer, field, load, fp = 0x281390, 0xc38, 0x281394, '7'
        quant, output, eps, epsilon_neg, select = 0x2813bc, 'd4', 'd3', 0x28142c, 0x28143c
        other_entries = []
        require_instructions(native, 0x2810d8, (('fmov', 'd1, #1.00000000'),))
        preserved(window(0x2810dc, select), 'd1')
        require_instructions(native, 0x281434, (('fcmp', 'd5, d2'), ('fccmp', 'd5, d3, #0, gt'),
                                                ('fcsel', 'd5, d4, d1, mi')))

    check_entry(code, native, entry, pointer, select, other_entries)
    if coefficient_fields.get(field) != context['coefficient_slot']:
        raise ValueError('VSOD live coefficient slot differs')
    require_instructions(native, pointer, (('ldr', f'x12, [x8, #{field:#x}]'),))
    preserved(window(pointer+4, load), 'x12')
    require_instructions(native, load, (('ldr', f's{fp}, [x12, #0x28]'), ('fcvt', f'd{fp}, s{fp}')))
    preserved(window(load+8, quant), f'd{fp}')
    conversion = check_conversion(native, quant, f'd{fp}', output, output, eps)
    negative = decode_constant(window(epsilon_neg, epsilon_neg+8))
    if negative['value'] != -EPSILON or negative['register'] != ('d1' if effect == 'VSODDSAW' else 'd2'):
        raise ValueError('VSOD negative gate bound differs')
    preserved(window(epsilon_neg+8, select), negative['register'])
    for register in (output, eps):
        preserved(window(quant+24, select), register)
    return dict(packets=context, coefficient_load=load, quantizer=conversion, select=select)


def formant_report():
    import lib
    from condition_return_study import preserved
    from transfer_study import constructor_memory

    program, constructor, coefficients, entry, code = coefficient_context('SIM_MFX_FORMANT')
    native = {ins.address: ins for ins in code}
    rows = dict(packets(program))
    require_words(rows, 0x5c, (0x3e07, 0x0fe0, 0x4fe2, 0x3fe4, 0x2016, 0x2017, 0xc002))
    require_words(rows, 0x6a, (0x2808, 0x0812, 0xbcd2, 0x7fe6, 0x4500, 0x2800, 0x2800, 0xc000))
    require_words(rows, 0x7a, (0x1505, 0x0407, 0x34e0))
    check_entry(code, native, entry, 0x3cdb10, 0x3cdb54, [])
    require_instructions(native, 0x3cdb10, (('ldr', 'x11, [x8, #0x8a0]'),
                                            ('ldr', 's0, [x11, #0x28]'), ('fcvt', 'd3, s0'),
                                            ('ldr', 'x11, [x8, #0x890]'),
                                            ('ldr', 's0, [x11, #0x28]'), ('fcvt', 'd4, s0')))
    if (coefficients.get(0x8a0), coefficients.get(0x890)) != (2, 0):
        raise ValueError('FORMANT independent live coefficient slots differ')
    preserved([native[pc] for pc in range(0x3cdb1c, 0x3cdb34, 4)], 'd3')
    conversion = check_conversion(native, 0x3cdb34, 'd3', 'd2', 'd2', 'd3', shift_bits=2)
    require_instructions(native, 0x3cdb4c, (('fmul', 'd3, d1, d4'), ('ldr', 'd1, [x8, #0x288]'),
                                           ('fmul', 'd1, d1, d2')))
    field, = packet_literals(program, 0x7a, rows[0x7a])
    check_constructor_literal(program, constructor_memory(constructor, lib.Z), native[0x3cdb50], field)
    return dict(packet=0x6a, control=0xbcd2, coefficient_slot=2, load_port=3,
                quantizer=conversion, native_product=0x3cdb54)


def gassph_report():
    from condition_return_study import preserved

    program, native, _, fields, _ = native_context('SIM_MFX_GASSPH')
    rows = dict(packets(program))
    require_words(rows, 0x28a, (0xb40a, 0x04a4, 0x4544, 0xfdd2, 0x5fe0, 0x2fe2))
    require_words(rows, 0x29e, (0x1408, 0x38e4, 0xffe2, 0x19c0, 0x0046))
    check_entry(list(native.values()), native, 0x14a098, 0x14a6b8, 0x14a730, [])
    require_instructions(native, 0x14a6b8, (('fmov', 'd6, #0.25000000'), ('fmsub', 'd6, d3, d3, d6')))
    preserved([native[pc] for pc in range(0x14a6c0, 0x14a6f8, 4)], 'd6')
    require_instructions(native, 0x14a6f8, (('fcvtzs', 'x13, d6, #0x20'), ('fmul', 'd6, d17, d0'),
                                           ('lsl', 'x13, x13, #2'), ('scvtf', 'd17, x13')))
    constant = decode_constant([native[0x14a708], native[0x14a70c]])
    if constant['value'] != EPSILON or constant['register'] != 'd0':
        raise ValueError('GASSPH rescale differs')
    require_instructions(native, 0x14a710, (('fmul', 'd17, d17, d0'),))
    preserved([native[pc] for pc in range(0x14a714, 0x14a730, 4)], 'd17')
    require_instructions(native, 0x14a09c, (('ldr', 'x9, [x0, #8]'), ('ldr', 'x9, [x9, #0x18]'),
                                           ('ldr', 'x11, [x9, #0x10]')))
    require_instructions(native, 0x14a0c8, (('ldr', 'x10, [x11, #0x18]'),))
    require_instructions(native, 0x14a0cc, (('ldr', 'w11, [x11, #0x20]'),))
    require_instructions(native, 0x14a0e4, (('sub', 'w11, w13, w11'),))
    preserved([native[pc] for pc in range(0x14a0cc, 0x14a730, 4)], 'x10')
    preserved([native[pc] for pc in range(0x14a0e8, 0x14a730, 4)], 'w11')
    require_instructions(native, 0x14a724, (('ldr', 'w13, [x8, #0x9c4]'), ('add', 'w13, w11, w13'),
                                           ('and', 'w13, w13, #0x7ff'), ('str', 'd17, [x10, w13, uxtw #3]')))
    address = indexed_operand(rows[0x29e], 0xffe2)
    if fields[0x9c4] != dict(relative=0xa2, address=address):
        raise ValueError('GASSPH native record and DSP store cell differ')
    return dict(packet=0x28a, control=0xfdd2, quantizer=0x14a6f8, shift_bits=2,
                store_port=7, data_store=address, native_store=0x14a730,
                native_record=0xa2, dsp_store_operand=0x2a6)


def native_report():
    import lib

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded native image')
    vmcp = vmcp_report()
    return dict(VSOD=base_report(), VSODDSAW=variant_report('VSODDSAW'),
                VSODDSTW=variant_report('VSODDSTW'), FORMANT=formant_report(), GASSPH=gassph_report(), VMCP=dict(
                    coefficient_slot=vmcp['packets']['coefficient_slot'], quantizer=vmcp['quantizers'][1],
                    after_gain=vmcp['after_gain']), strict_dsp_admission=False)


def fantom_report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the recorded Fantom CORE1 image')
    result = {}
    for effect, address in VSOD_LISTS.items():
        result[effect] = []
        for segment in program_list(core, address)['segments']:
            length, source = segment['length'], segment['source']
            program = swap_words(read(core, source, (length+3) & ~3))[:length]
            result[effect].append(dict(base=segment['base'], **packet_context(effect, program)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    report = native_report()
    if args.core1:
        from core1 import Core1

        report['fantom'] = fantom_report(Core1(args.core1))
    print(json.dumps(report, indent=2, allow_nan=False))
