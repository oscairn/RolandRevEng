"""Bounded LINE native-prefix oracle and static anchors; no DSP admission.

The numeric oracle uses IEEE binary64 and Python3.13+ math.fma where native
FMSUB/FMADD occurs. It excludes conversion overflow and unmeasured FPCR behavior.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from parent_control_study import NATIVE_SHA256

EPSILON = 2.0 ** -32
MASK64 = (1 << 64) - 1
GAIN_BITS = 0x3ff2d0e560418937
SCALE_BITS = 0x3feb333333333333
GAIN = struct.unpack('>d', GAIN_BITS.to_bytes(8, 'big'))[0]
SCALE = struct.unpack('>d', SCALE_BITS.to_bytes(8, 'big'))[0]


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Expected a finite number')
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError('Number exceeds binary64 range') from error
    if not math.isfinite(value):
        raise ValueError('Expected a finite number')
    return value


def _float32(value):
    try:
        return _finite(struct.unpack('>f', struct.pack('>f', _finite(value)))[0])
    except (OverflowError, struct.error) as error:
        raise ValueError('Live coefficient exceeds binary32 range') from error


def quantize_native_reference(value):
    """FCVTZS X,D,#32; LSL X,#9; SCVTF D,X; multiply by2^-32.

    Reject conversion-overflow/exception cases rather than assigning FPCR policy.
    The integer shift itself deliberately wraps in64bits, including its sign bit.
    """
    value = _finite(value)
    if not -(2.0 ** 31) <= value < 2.0 ** 31:
        raise ValueError('Outside the non-overflowing signed64 fixed32 conversion domain')
    fixed = math.trunc(math.ldexp(value, 32))
    shifted = (fixed << 9) & MASK64
    if shifted & (1 << 63):
        shifted -= 1 << 64
    return dict(fixed_integer=fixed, shifted_integer=shifted, quantized=float(shifted) * EPSILON)


def native_channel_reference(mixed, *, drive_scale, drive, mode, history,
                             smoothing, rational_scale, a, b):
    """Native-reference channel from mixed input through pre/post-rational values.

    Live drive/smoothing records are binary32; remaining arguments are constructor
    doubles. No memory, reset, ring advancement or DSP instruction is implemented.
    """
    if not hasattr(math, 'fma'):
        raise ValueError('This native oracle requires Python3.13+ math.fma')
    mixed, drive_scale, mode, history, rational_scale, a, b = [
        _finite(value) for value in (mixed, drive_scale, mode, history, rational_scale, a, b)]
    drive, smoothing = _float32(drive), _float32(smoothing)
    drive_gain = _finite(drive_scale * drive)
    prequantized = _finite(mixed * drive_gain)
    quantizer = quantize_native_reference(prequantized)
    value = quantizer['quantized']
    rectified = value if mode < EPSILON or value >= 0 else -value
    scaled = _finite(rectified * GAIN)
    shaped = -SCALE if scaled < -1 else min(scaled, 1.0) * SCALE
    old_product = _finite(history * smoothing)
    try:
        difference = _finite(math.fma(-shaped, smoothing, old_product))
        smoothed = _finite(shaped + difference)
        z = _finite(smoothed * rational_scale)
        numerator = _finite(math.fma(z, a, b))
        denominator = _finite(math.fma(z, b, a))
    except OverflowError as error:
        raise ValueError('Native-reference arithmetic overflow') from error
    if denominator == 0:
        raise ValueError('Singular rational denominator')
    factor = _finite(numerator / denominator)
    return dict(drive=drive, smoothing=smoothing, drive_gain=drive_gain,
                prequantized=prequantized, quantizer=quantizer, rectified=rectified,
                scaled=scaled, shaped=shaped, smoothed=smoothed,
                rational_input=z, numerator=numerator, denominator=denominator, factor=factor)


def _regs(ins):
    from capstone import arm64 as a64
    return [ins.reg_name(op.reg) for op in ins.operands if op.type == a64.ARM64_OP_REG]


def decode_quantizer(code):
    from capstone import arm64 as a64
    if (len(code) != 3 or [ins.mnemonic for ins in code] != ['fcvtzs', 'lsl', 'scvtf']
            or [ins.address for ins in code] != list(range(code[0].address, code[0].address + 12, 4))):
        raise ValueError('Expected one contiguous signed fixed conversion/shift/conversion kernel')
    first, shift, back = code
    registers = _regs(first)
    if (len(first.operands) != 3 or len(registers) != 2
            or not registers[0].startswith('x') or not registers[1].startswith('d')
            or first.operands[2].type != a64.ARM64_OP_IMM or first.operands[2].imm != 32
            or _regs(shift) != [registers[0], registers[0]] or len(shift.operands) != 3
            or shift.operands[2].type != a64.ARM64_OP_IMM or shift.operands[2].imm != 9
            or _regs(back) != [registers[1], registers[0]] or len(back.operands) != 2):
        raise ValueError('Not the checked signed64/fixed32/shift9 form')
    return dict(pc=first.address, integer=registers[0], floating=registers[1],
                fraction_bits=32, shift_bits=9, integer_width=64)


def decode_constant(code):
    """Recover a double from only MOV/MOVK then FMOV, or immediate FMOV."""
    from capstone import arm64 as a64
    values = {}
    for index, ins in enumerate(code):
        ops = ins.operands
        if ins.mnemonic in ('mov', 'movz') and len(ops) == 2 and ops[1].type == a64.ARM64_OP_IMM:
            register = _regs(ins)[0]
            if not register.startswith('x'):
                raise ValueError('Expected a64bit constant register')
            values[register] = ops[1].imm & MASK64
        elif ins.mnemonic == 'movk' and len(ops) == 2 and ops[1].type == a64.ARM64_OP_IMM:
            register = _regs(ins)[0]
            if register not in values:
                raise ValueError('MOVK has no preceding constant definition')
            shift = ops[1].shift.value
            values[register] = (values[register] & ~(0xffff << shift)) | (ops[1].imm << shift)
        elif ins.mnemonic == 'fmov' and len(ops) == 2 and index == len(code) - 1:
            destination = _regs(ins)[0]
            if ops[1].type == a64.ARM64_OP_FP:
                value = ops[1].fp
                bits = int.from_bytes(struct.pack('>d', value), 'big')
            elif ops[1].type == a64.ARM64_OP_REG and ins.reg_name(ops[1].reg) in values:
                bits = values[ins.reg_name(ops[1].reg)]
                value = struct.unpack('>d', bits.to_bytes(8, 'big'))[0]
            else:
                raise ValueError('FMOV has no proved constant source')
            return dict(register=destination, value=value, bits=f'{bits:016x}')
        else:
            raise ValueError('Constant materialization contains unsupported instructions')
    raise ValueError('No final FMOV')


def decode_gate(code):
    from capstone import arm64 as a64
    left = len(code) == 8
    if [ins.mnemonic for ins in code] != (['fcmp', 'cset'] if left else []) + [
            'fcmp', 'cset', 'fnmul', 'orr', 'cmp', 'fcsel']:
        raise ValueError('Not one checked sign/mode gate')
    rest = code[2:] if left else code
    compare, sign, negate, combine, test, select = rest
    positive = _regs(compare)[0]; negative, integer_source, epsilon = _regs(negate)
    target, mode, sign_source = _regs(combine)
    if (mode == sign_source or negative == positive
            or compare.operands[1].type != a64.ARM64_OP_FP or compare.operands[1].fp != 0
            or sign.cc != a64.ARM64_CC_GE or _regs(sign) != [sign_source]
            or _regs(test) != [target] or test.operands[1].imm != 0
            or select.cc != a64.ARM64_CC_NE or _regs(select) != [negative, positive, negative]):
        raise ValueError('Sign comparison, boolean combination or select differs')
    if left and (code[1].cc != a64.ARM64_CC_LT or _regs(code[1]) != [mode]
                 or _regs(code[0])[1] != epsilon or target != sign_source):
        raise ValueError('Expected strict mode<epsilon and independent sign flag')
    if not left and target != mode:
        raise ValueError('Expected the carried mode flag combined in place')
    return dict(mode_register=_regs(code[0])[0] if left else None, mode_flag=mode,
                epsilon_register=epsilon, integer_float=integer_source,
                positive=positive, output=negative, predicate='mode<epsilon or quantized>=0')


def decode_smoothing(code):
    if len(code) != 3 or [ins.mnemonic for ins in code] != ['fmul', 'fmsub', 'fadd']:
        raise ValueError('Expected multiply, fused addend-minus-product, add')
    temporary, history, coefficient = _regs(code[0])
    subtract = _regs(code[1]); new = subtract[1]
    if (temporary in (new, coefficient) or subtract != [temporary, new, coefficient, temporary]
            or _regs(code[2]) != [new, new, temporary]):
        raise ValueError('Smoothing def/use differs from the checked feedback form')
    return dict(history=history, coefficient=coefficient, shaped=new, output=new,
                expression='shaped + fma(-shaped, coefficient, history*coefficient)')


def decode_rational(code):
    if len(code) != 3 or [ins.mnemonic for ins in code] != ['fmadd', 'fmadd', 'fdiv']:
        raise ValueError('Expected two fused multiply-adds and division')
    numerator, z, a, b = _regs(code[0]); denominator = _regs(code[1])[0]
    if (len({numerator, z, a, b}) != 4 or denominator != z
            or _regs(code[1]) != [denominator, z, b, a]
            or _regs(code[2])[1:] != [numerator, denominator]):
        raise ValueError('Rational def/use differs from the checked form')
    return dict(z=z, a=a, b=b, numerator=numerator, denominator=denominator,
                output=_regs(code[2])[0], expression='fma(z,a,b)/fma(z,b,a)')


def study():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from bmc_dsp import literal, packets
    from condition_return_study import preserved
    from header_study import layout, UnsupportedLayout
    from operand_variants_study import check_bindings
    from transfer_study import constructor_memory, native_accesses, records_from_memory
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    cls = 'SIM_MFX_LINEDRIVE'
    start, end, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    by_pc = {ins.address: ins for ins in native}
    def window(lo, hi):
        code = [ins for ins in native if lo <= ins.address < hi]
        if [ins.address for ins in code] != list(range(lo, hi, 4)):
            raise ValueError('Native window is not completely decoded')
        return code
    def expect(pc, mnemonic, operands):
        ins = by_pc[pc]
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'Native source/use differs at {pc:#x}')
    expect(0x2df874, 'ldr', 'x8, [x0, #0x28]')
    preserved(window(0x2df878, 0x2dfacc), 'x8')
    constants = {name: decode_constant(window(lo, hi)) for name, lo, hi in (
        ('epsilon', 0x2df914, 0x2df91c), ('gain', 0x2df940, 0x2df954),
        ('scale', 0x2df97c, 0x2df988), ('negative_scale', 0x2df994, 0x2df9a0),
        ('one', 0x2df958, 0x2df95c), ('negative_one', 0x2df98c, 0x2df990))}
    if [constants[key]['value'] for key in constants] != [EPSILON, GAIN, SCALE, -SCALE, 1, -1]:
        raise ValueError('Native numeric constants differ')
    quantizers = [decode_quantizer(window(lo, lo + 12)) for lo in (0x2df904, 0x2df9e4)]
    gates = [decode_gate(window(0x2df920, 0x2df940)), decode_gate(window(0x2df9f4, 0x2dfa0c))]
    for quantizer, gate, pc, operands in zip(quantizers, gates, (0x2df91c, 0x2df9f0),
                                             ('d4, d1, d3', 'd5, d0, d3')):
        expect(pc, 'fmul', operands)
        if (gate['integer_float'] != quantizer['floating'] or gate['output'] != quantizer['floating']
                or gate['positive'] != ('d4' if pc == 0x2df91c else 'd5')
                or gate['epsilon_register'] != constants['epsilon']['register']):
            raise ValueError('Quantizer output/scale is not the gate input')
    if gates[0]['mode_flag'] != gates[1]['mode_flag']:
        raise ValueError('Right channel does not use the same carried mode')
    # Explicit definitions/uses across compiler scheduling, including scalar/vector aliases.
    carried = [('d0', 0x2df900, 0x2df9e0), ('w13', 0x2df928, 0x2df9fc),
               ('d3', 0x2df91c, 0x2df9f0), ('d2', 0x2df954, 0x2dfa0c),
               ('x14', 0x2df974, 0x2dfa24), ('d4', 0x2df95c, 0x2dfa10),
               ('d16', 0x2df988, 0x2dfa2c), ('d17', 0x2df990, 0x2dfa30),
               ('d1', 0x2df9a0, 0x2dfa34), ('d2', 0x2df914, 0x2df920),
               ('d1', 0x2df958, 0x2df990), ('d5', 0x2df960, 0x2df988),
               ('d2', 0x2dfa14, 0x2dfa2c), ('d0', 0x2dfa10, 0x2dfa30),
               ('d6', 0x2df970, 0x2df9a4), ('d3', 0x2dfa24, 0x2dfa38),
               ('d2', 0x2dfaa0, 0x2dfab8), ('d3', 0x2dfaa0, 0x2dfab8)]
    for register, lo, hi in carried:
        preserved(window(lo, hi), register)
    for pc, m, ops in [
        (0x2df8e4, 'fcvt', 'd0, s0'), (0x2df978, 'fcvt', 'd7, s7'),
        (0x2dfa28, 'fcvt', 'd4, s4'),
        (0x2df8fc, 'fmul', 'd0, d2, d0'), (0x2df900, 'fmul', 'd1, d1, d0'),
        (0x2df9e0, 'fmul', 'd0, d0, d5'),
        (0x2df954, 'fmul', 'd1, d1, d2'), (0x2dfa0c, 'fmul', 'd0, d0, d2'),
        (0x2df95c, 'fmin', 'd5, d1, d4'), (0x2df988, 'fmul', 'd5, d5, d16'),
        (0x2df990, 'fcmp', 'd1, d17'), (0x2df9a0, 'fcsel', 'd5, d1, d5, mi'),
        (0x2dfa10, 'fmin', 'd2, d0, d4'), (0x2dfa2c, 'fmul', 'd2, d2, d16'),
        (0x2dfa30, 'fcmp', 'd0, d17'), (0x2dfa34, 'fcsel', 'd0, d1, d2, mi'),
        (0x2dfa8c, 'fmul', 'd0, d0, d2'), (0x2dfa94, 'fmul', 'd1, d1, d2')]:
        expect(pc, m, ops)
    preserved(window(0x2df994, 0x2df9a0), 'nzcv')
    smoothing = [decode_smoothing(window(lo, lo + 12)) for lo in (0x2df9a4, 0x2dfa38)]
    rational = [decode_rational([by_pc[pc] for pc in pcs]) for pcs in (
        (0x2dfaa0, 0x2dfaa4, 0x2dfaa8), (0x2dfaac, 0x2dfab0, 0x2dfab8))]
    for pcs, roles in zip(((0x2dfaa0, 0x2dfaa4, 0x2dfaa8), (0x2dfaac, 0x2dfab0, 0x2dfab8)), rational):
        preserved(window(pcs[0] + 4, pcs[2]), roles['numerator'])
        preserved(window(pcs[1] + 4, pcs[2]), roles['denominator'])
    length, stream, *_ = parse.program(cls); decoded = packets(stream[:length])
    ctor = parse.parse_ctor(cls); lo, hi = lib.func(ctor['ctor']); md = lib.md(); md.detail = True
    constructor = list(md.disasm(lib.Z[lo:hi], lo)); memory = constructor_memory(constructor, lib.Z)
    base, count, previous = parse.parse_datsym(cls, ctor)
    records = records_from_memory(memory, base, count)
    if records != previous:
        raise ValueError('Fresh constructor address records disagree')
    fields = {base + 8 * index + 4: dict(relative=relative, address=address)
              for index, (relative, address) in enumerate(records)}
    accesses = native_accesses(native, fields, coefficient_pointer_fields(constructor))
    coefficient_reads = [row for row in accesses['coefficient_reads'] if row['pc'] < 0x2dfa64]
    if [(row['pc'], row['slot'], row['width']) for row in coefficient_reads] != [
            (0x2df8e0, 2, 4), (0x2df974, 1, 4), (0x2dfa24, 1, 4)]:
        raise ValueError('Native binary32 drive/smoothing provenance differs')
    channel_bindings = []
    for lo, hi, bindings in (
        (0x2df8dc, 0x2df9d0, [('read', 0x32, 1), ('read', 0x70, 4), ('write', 0x80, 0x27), ('write', 0x82, 3)]),
        (0x2df9d0, 0x2dfa64, [('read', 0x34, 2), ('read', 0xb2, 7), ('write', 0xc2, 0x28), ('write', 0xc4, 6)])):
        matched = check_bindings([row for row in accesses['accesses'] if lo <= row['pc'] < hi], fields,
                                 [dict(kind=kind, relative=relative, address=address) for kind, relative, address in bindings], by_pc)
        if not matched['verified']:
            raise ValueError('Channel input/history/output binding unresolved')
        channel_bindings.append(matched)
    # Constructor record positions supply ownership, not merely equal default numbers.
    literal_records = []
    for record, pc in ((0x60, 0x2df8f8), (0x20, 0x2df910), (0x30, 0x2dfa88),
                       (0x40, 0x2dfa90), (0x10, 0x2dfa98), (0, 0x2dfa9c)):
        field = int.from_bytes(bytes(memory[record + i] for i in range(4)), 'little')
        value = struct.unpack('<d', bytes(memory[record + 8 + i] for i in range(8)))[0]
        destination = 'd3' if record == 0 else 'd2'
        displacement = f', #{record + 8 if record + 8 < 16 else hex(record + 8)}'
        expect(pc, 'ldr', f'{destination}, [x8{displacement}]')
        anchors = []
        for offset, words in decoded:
            try:
                parsed = layout(words)
            except UnsupportedLayout:
                continue
            for item in parsed['fields']:
                if item['role'] == 'literal' and offset + item['offset'] == field:
                    anchors.append(dict(packet=offset, control=words[1 + item['operation']],
                                        field=field, width=item['width'],
                                        stored_value=literal(stream[field:field + item['width']])))
        if len(anchors) != 1:
            raise ValueError('No unique owned literal reference')
        literal_records.append(dict(record=record, native_load=pc, default=value, **anchors[0]))
    return dict(native_sha256=NATIVE_SHA256, cls=cls, native_callback=[start, end],
                constants=constants, quantizers=quantizers, gates=gates, smoothing=smoothing,
                rational=rational, carried_registers=[dict(register=r, start=lo, end=hi) for r, lo, hi in carried],
                channel_bindings=channel_bindings, literal_records=literal_records,
                live_coefficient_reads=coefficient_reads,
                dsp_semantic_admission=False, complete_effect=False,
                policy='IEEE binary64/binary32 plus math.fma oracle; excludes FCVTZS overflow and FPCR differences; no BMC precision claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'local/line-shaping-study.json')
    args = parser.parse_args()
    result = study(); args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['cls'], 'native prefix anchors checked; DSP admission remains false')
