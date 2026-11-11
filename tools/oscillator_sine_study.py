"""Check native OSC sine folding, polynomial literals and stored results."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from bmc_dsp import packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256
from kernel_abi import program_list, read
from limit_control_study import native_context
from line_mix_variation import packet_literals
from line_shaping_study import EPSILON, NATIVE_SHA256, _finite, decode_constant
from oscillator_phase_study import OSC_LIST, START, advance_phase, normalize_phase_sum
from oscillator_phase_study import report as phase_report
from weighted_mix_study import check_constructor_literal, require_instructions, require_words

END = 0x29210
SINE_PI = float.fromhex('0x1.921fb50000000p+1')
COEFFICIENTS = {
    0x148: 0.00012626262626262626,
    0x158: 0.0064102564102564,
    0x168: 3.0525030525030525e-05,
    0x178: 0.16666666666667,
    0x188: 0.0083333333333333,
    0x198: 0.0001984126984126984,
    0x1a8: 0.013888888888889,
}


def sine_reference(phase):
    """Evaluate the checked native arithmetic with its original operation order."""
    if not hasattr(math, 'fma'):
        raise ValueError('The sine reference requires Python 3.13+ math.fma')
    phase = _finite(phase)
    polarity = -1.0 if abs(phase) - 0.5 > -EPSILON else 1.0
    folded_phase = normalize_phase_sum(phase + phase)
    argument = (folded_phase * 0.5) * SINE_PI
    squared = argument * argument
    cubed = argument * squared
    quartic = squared * squared
    quartic_scale = COEFFICIENTS[0x148] * quartic
    quintic = squared * cubed
    negative_cubic = -(argument * squared)
    lower = math.fma(quintic, COEFFICIENTS[0x168], COEFFICIENTS[0x158] * negative_cubic)
    lower = argument + lower
    higher = math.fma(lower, quartic_scale, COEFFICIENTS[0x1a8] * negative_cubic)
    higher = argument + higher
    cubic_correction = cubed * COEFFICIENTS[0x198]
    quintic_correction = quintic * COEFFICIENTS[0x188]
    sixth_correction = cubed * cubic_correction
    leading = argument + quintic_correction
    difference = math.fma(-higher, sixth_correction, COEFFICIENTS[0x178] * negative_cubic)
    polynomial = _finite(leading + difference)
    return dict(polarity=polarity, folded_phase=folded_phase, argument=argument,
                polynomial=polynomial, output=polarity * polynomial)


def sine_context(program):
    rows = dict(packets(program))
    if not {0x24, 0x2e, 0x3c, 0x44, 0x4a, 0x54, 0x62, 0x6c, 0x7a, 0x80, 0x8e, 0x96} <= rows.keys():
        raise ValueError('OSC sine packet boundaries differ')
    for offset, words in (
            (0x24, (0x1805, 0x0410, 0x7fe2, 0x2800, 0xe037)),
            (0x2e, (0x5907, 0x3050, 0x3052, 0x1407, 0x1b12, 0xb000, 0x3000)),
            (0x3c, (0x1804, 0x2441, 0xbfe0)),
            (0x44, (0x1503, 0x3442, 0x4482)), (0x4a, (0x1505, 0x6530, 0x5483)),
            (0x54, (0x0807, 0x0d72, 0xbd81)), (0x62, (0x0805, 0x0c0e, 0xbc81)),
            (0x6c, (0x1507, 0x64f0, 0x7574)), (0x7a, (0x1503, 0x6583, 0x7c47)),
            (0x80, (0x1407, 0x0e0e, 0x3fe2, 0xbd07)),
            (0x8e, (0x1804, 0x0403, 0x8fe0)), (0x96, (0x0c03, 0x8fe0))):
        require_words(rows, offset, words)
    targets = [rows[offset][-1] for offset in (0x3c, 0x8e, 0x96)]
    if len(set(targets)) != 3 or any(not 0 <= address < 0x800 for address in targets):
        raise ValueError('OSC sine result addresses alias or exceed data range')
    if rows[0x80][4] != targets[0]:
        raise ValueError('OSC sine polarity reload does not match its stored target')
    literals = []
    for offset in (0x4a, 0x54, 0x62, 0x6c, 0x80):
        literals.extend(packet_literals(program, offset, rows[offset]))
    return dict(polarity_target=targets[0], polynomial_target=targets[1], output_target=targets[2],
                literals=literals)


def report():
    import capstone
    import lib
    from condition_return_study import preserved

    phase = phase_report()
    program, native, memory, fields, _ = native_context('SIM_MFX_OSC')
    context = sine_context(program)
    gate = decode_constant([native[0x290d4], native[0x290d8]])
    pi = decode_constant([native[pc] for pc in range(0x29160, 0x29170, 4)])
    if gate['value'] != -EPSILON or pi['value'] != SINE_PI:
        raise ValueError('OSC gate or polynomial scale constant differs')
    require_instructions(native, 0x290c0, (
        ('fneg', 'd1, d0'), ('fcmp', 'd0, #0.0'), ('fcsel', 'd1, d0, d1, ge'),
        ('fmov', 'd2, #-0.50000000'), ('fadd', 'd1, d1, d2'),
        ('mov', 'x11, #-0x4210000000000000'), ('fmov', 'd2, x11'), ('fcmp', 'd1, d2'),
        ('fmov', 'd1, #1.00000000'), ('fmov', 'd2, #-1.00000000'), ('fcsel', 'd3, d2, d1, gt'),
    ))
    require_instructions(native, 0x290fc, (
        ('fadd', 'd0, d0, d0'), ('fcmp', 'd0, d2'), ('b.pl', '#0x29130'),
        ('fneg', 'd1, d0'),
    ))
    for pc, source, operation in ((0x2910c, 'd1', 'fadd'), (0x29138, 'd0', 'fsub')):
        require_instructions(native, pc, (
            ('fcvtzs', f'w11, {source}'), ('add', 'w12, w11, #1'), ('add', 'w13, w11, #2'),
            ('cmp', 'w12, #0'), ('csinc', 'w11, w13, w11, lt'),
            ('and', 'w11, w11, #0xfffffffe'), ('scvtf', 'd1, w11'),
            (operation, 'd0, d0, d1'),
        ))
    require_instructions(native, 0x2912c, (
        ('b', '#0x29158'), ('fcmp', 'd0, d1'), ('b.lt', '#0x29158'),
    ))
    require_instructions(native, 0x29158, (('fmov', 'd1, #0.50000000'), ('fmul', 'd0, d0, d1')))
    require_instructions(native, 0x29170, (('fmul', 'd0, d0, d1'),))
    bindings = []
    for field, relative, address, pc, register in (
            (0x1ec, 0x42, 7, 0x290ec, 'd3'),
            (0x1e4, 0x94, 6, 0x291ec, 'd0'),
            (0x1b4, 0x9a, 0, 0x29200, 'd0')):
        if fields[field] != dict(relative=relative, address=address):
            raise ValueError('OSC sine store record differs')
        require_instructions(native, pc, (
            ('ldr', f'w11, [x8, #{field:#x}]'), ('add', 'w11, w10, w11'),
            ('and', 'w11, w11, #0x7ff'), ('str', f'{register}, [x9, w11, uxtw #3]'),
        ))
        bindings.append(dict(field=field, relative=relative, address=address, native_store=pc+12))
    require_instructions(native, 0x291cc, (
        ('ldr', 'w11, [x8, #0x1ec]'), ('add', 'w11, w10, w11'),
        ('and', 'w11, w11, #0x7ff'), ('ldr', 'd4, [x9, w11, uxtw #3]'),
        ('ldr', 'd5, [x8, #0x178]'), ('fmul', 'd1, d5, d1'),
        ('fmsub', 'd1, d3, d2, d1'), ('fadd', 'd0, d0, d1'),
    ))
    require_instructions(native, 0x291fc, (('fmul', 'd0, d4, d0'),))
    literal_bindings = []
    for field, pc in ((0x148, 0x29180), (0x158, 0x29190), (0x168, 0x2918c),
                      (0x178, 0x291dc), (0x188, 0x291bc), (0x198, 0x291b4), (0x1a8, 0x291a4)):
        relative, = struct.unpack('<I', bytes(memory[field-8+i] for i in range(4)))
        literal, = [item for item in context['literals'] if item['field'] == relative]
        check_constructor_literal(program, memory, native[pc], literal)
        default, = struct.unpack('<d', bytes(memory[field+i] for i in range(8)))
        if default != COEFFICIENTS[field]:
            raise ValueError('OSC polynomial default differs')
        literal_bindings.append(dict(native_field=field, native_load=pc, default=default, literal=literal))
    for register, start in (('x8', START+4), ('x9', 0x29030), ('w10', 0x290b4)):
        preserved([native[pc] for pc in range(start, END, 4)], register)
    for pc in range(START, END, 4):
        ins = native[pc]
        if ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_RET) or ins.mnemonic in ('adr', 'adrp'):
            raise ValueError('OSC sine interval has an unexpected external dependency')
        if ins.group(capstone.CS_GRP_JUMP) and not START <= ins.operands[-1].imm < END:
            raise ValueError('OSC sine branch leaves the checked interval')
    return dict(native_sha256=NATIVE_SHA256,
                native_interval=[START, END], phase=phase, context=context, stores=bindings,
                literal_bindings=literal_bindings, gate_epsilon=EPSILON, pi=SINE_PI,
                pi_input_candidate=dict(operand=0xe037, load_port=7, following_control=0x1407,
                                        native_value=SINE_PI, hardware_verified=False),
                native_execution_verified=False, bmc_execution_verified=False,
                isolated_opcode_admission=False)


def native_probes(phases):
    import ctypes
    import lib
    from native_callback_fixture import RingFixture, executable_mapping

    phases = tuple(phases)
    checked = report()
    image = bytearray(0x200)
    _, _, memory, _, _ = native_context('SIM_MFX_OSC')
    for offset, value in memory.items():
        if offset < len(image):
            image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    struct.pack_into('<d', context, 0xa8, 0)
    fixture = RingFixture(context)
    updated_phases = [advance_phase(phase, 0) for phase in phases]
    expected = [sine_reference(phase) for phase in updated_phases]
    code = lib.Z[START:END] + bytes.fromhex('c0035fd6')
    result = []
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(address)
        for phase, updated, reference in zip(phases, updated_phases, expected, strict=True):
            fixture.ring[checked['phase']['source']['address']] = phase
            invoke(ctypes.addressof(fixture.wrapper))
            actual = {name: fixture.ring[checked['context'][target]] for name, target in
                      (('polarity', 'polarity_target'), ('polynomial', 'polynomial_target'),
                       ('output', 'output_target'))}
            stored_phase = fixture.ring[checked['phase']['target']['address']]
            if stored_phase.hex() != updated.hex() or any(
                    actual[key].hex() != reference[key].hex() for key in actual):
                raise ValueError(f'Native sine differs at phase {phase!r}: {actual} / {reference}')
            result.append(dict(phase=phase, updated_phase=updated, **reference))
    return result


def fantom_report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom image')
    result = []
    for segment in program_list(core, OSC_LIST)['segments']:
        stream = swap_words(read(core, segment['source'], (segment['length']+3)&~3))[:segment['length']]
        result.append(dict(base=segment['base'], **sine_context(stream)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        values = [-0.5, math.nextafter(-0.5, -math.inf), -0.5+EPSILON,
                  math.nextafter(-0.5+EPSILON, -0.5), 0.5-EPSILON,
                  math.nextafter(0.5-EPSILON, 0.5), math.nextafter(0.5, 0), 0.5]
        result['native_probes'] = native_probes(values)
        result['native_execution_verified'] = True
    if args.core1:
        from core1 import Core1
        result['fantom_placements'] = fantom_report(Core1(args.core1))
    print(json.dumps(result, indent=2, allow_nan=False))
