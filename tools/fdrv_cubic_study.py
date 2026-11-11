"""Bind native FDRV cubic cutpoints and the exact cubic_quad packet profile."""
import hashlib

from bmc_dsp import literal, packets
from line_shaping_study import NATIVE_SHA256, _finite


def cubic_spec():
    return dict(kind='cubic_quad', sources=[0xe, 0x10, 0xf, 0x11], targets=[0x12, 0x18, 0x13, 0x1a])


def cubic_reference(value):
    """Retain the native operation order over the stock clipped-input domain."""
    value = _finite(value)
    if not -1 <= value <= 1:
        raise ValueError('Expected the stock clipped input in [-1, 1]')
    scaled, square = value*3.0, value*value
    magnitude = scaled if scaled >= 0 else -scaled
    return value * (square + (3.0-magnitude))


def context(program):
    from weighted_mix_study import require_words

    rows = dict(packets(program))
    for offset, prefix in (
            (0x36c, (0x3a06, 0xcedc, 0xefe0, 0x0fe2)),
            (0x378, (0x3407, 0x2410, 0xcfe2, 0x4fe4, 0x4300)),
            (0x386, (0x2c06, 0x1400, 0x6510, 0x2e92, 0x4300, 0x4300)),
            (0x392, (0x2c05, 0x1c42, 0x5504, 0x6f90, 0x4300)),
            (0x39c, (0x2e05, 0x1440, 0x5d46, 0x0fe0)),
            (0x3a6, (0x5f08, 0x2410, 0x5544, 0x9fe2, 0x4fe4, 0x4300)),
            (0x3b6, (0x5c08, 0x1400, 0x6510, 0x2e92, 0xdfe4, 0x4300, 0x4300)),
            (0x3c6, (0x2c05, 0x1c42, 0x5504, 0x6f90, 0x4300)),
            (0x3d0, (0x1503, 0x1440, 0x5d46)),
            (0x3d6, (0x1804, 0x5544, 0x9fe0)),
            (0x3de, (0x3e07, 0xdfe0, 0x2fe2, 0x6fe4))):
        if offset not in rows:
            raise ValueError('Missing FDRV cubic packet')
        require_words(rows, offset, prefix)
    sources = [0x376, 0x3a4, 0x384, 0x3b4]
    targets = [0x3b2, 0x3dc, 0x3c4, 0x3e6]
    values = [int.from_bytes(program[field:field+2], 'big') for field in sources+targets]
    if len(set(values)) != 8 or any(value >= 0x800 for value in values):
        raise ValueError('FDRV cubic data fields alias or leave the checked data domain')
    if [rows[0x3de][5], rows[0x3de][6]] != [values[4], values[6]]:
        raise ValueError('FDRV following reloads differ from the shaped stores')
    return dict(source_fields=sources, sources=values[:4], target_fields=targets, targets=values[4:],
                constant=literal(program[0x380:0x382]),
                per_packet_port_state_verified=False, isolated_opcode_admission=False)


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from weighted_mix_study import require_instructions, require_window

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    dsp = context(program)
    require_instructions(native, 0x305a00, (('fmov', 'd1, #3.00000000'),))
    bindings = []
    for index, (start, read_pc, representative, store_pc, control, packet) in enumerate((
            (0x305a04, 0x3059fc, 0x36a, 0x305a30, 0x1c42, 0x392),
            (0x305a44, 0x305a40, 0x360, 0x305a70, 0x1c42, 0x3c6),
            (0x305a84, 0x305a80, 0x374, 0x305ab0, 0x5d46, 0x39c),
            (0x305ac4, 0x305ac0, 0x382, 0x305af0, 0x5d46, 0x3d0))):
        output = 'd1' if index == 3 else 'd2'
        require_instructions(native, start, (
            ('fmul', 'd2, d0, d1'), ('fmul', 'd3, d0, d0'), ('fnmul', 'd4, d0, d1'),
            ('fcmp', 'd2, #0.0'), ('fcsel', 'd2, d2, d4, ge'),
            ('fsub', f'{output}, d1, d2'), ('fadd', f'{output}, d3, {output}'),
            ('fmul', f'd0, d0, {output}')))
        require_window(native, read_pc, store_pc)
        require_instructions(native, read_pc, (('ldr', 'd0, [x11, w13, uxtw #3]'),))
        require_instructions(native, store_pc, (('str', 'd0, [x11, w13, uxtw #3]'),))
        preserved([native[pc] for pc in range(0x305a04, start, 4)], 'd1')
        preserved([native[pc] for pc in range(read_pc+4, start, 4)], 'd0')
        preserved([native[pc] for pc in range(start+32, store_pc, 4)], 'd0')
        source = checked_access(native, fields, trace, read_pc, 'read', representative, dsp['sources'][index])
        target = checked_access(native, fields, trace, store_pc, 'write',
                                dsp['target_fields'][index], dsp['targets'][index])
        if int.from_bytes(program[representative:representative+2], 'big') != dsp['sources'][index]:
            raise ValueError('FDRV source alias differs from its constructor representative')
        bindings.append(dict(source=source, target=target, native_arithmetic=[start, start+32],
                             candidate_short_control=control, candidate_short_packet=packet,
                             native_add=start+24, source_transfer_field=dsp['source_fields'][index],
                             source_port_binding_verified=False))
    for curve in bindings:
        for item in (curve['source'], curve['target']):
            if any(access['kind'] == 'write' and access['pc'] > item['pc']
                   and any(fields[field]['address'] == item['address'] for field in access['fields'])
                   for access in trace['accesses']):
                raise ValueError('Cubic cutpoint is overwritten later in the callback')
    input_copy = checked_access(native, fields, trace, 0x3059ec, 'write', 0x382, 0x11)
    require_instructions(native, 0x3059ec, (('str', 'd0, [x11, w13, uxtw #3]'),))
    preserved([native[pc] for pc in range(0x3059d0, 0x3059ec, 4)], 'd0')
    short_fields = [dict(control=word, destination=(word >> 12) & 7, source=(word >> 6) & 7,
                         operand_reference=word & 63, normalized_class=word & 0x8e00,
                         required_family=1, universal_semantic_admission=False)
                    for word in (0x0403, 0x4503, 0x2443, 0x6547, 0x2410, 0x6510,
                                 0x1400, 0x5504, 0x1440, 0x5544, 0x1c42, 0x5d46)]
    return dict(native_sha256=NATIVE_SHA256, context=dsp, curves=bindings,
                formula='x * (x*x + (3 - abs(3*x)))', native_probe_interval=[0x305a00, 0x305a24],
                incoming_second_right_store=input_copy, short_control_fields=short_fields,
                admitted_profile='cubic_quad', profile_logical_bytes=126,
                native_execution_verified=False, bmc_execution_verified=False,
                isolated_opcode_admission=False, complete_program_executable=False)


def native_probes(values):
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping

    values = tuple(values)
    expected = [cubic_reference(value) for value in values]
    checked = report()
    start, end = checked['native_probe_interval']
    code = lib.Z[start:end] + bytes.fromhex('c0035fd6')
    results = []
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(address)
        for value, reference in zip(values, expected, strict=True):
            actual = invoke(value)
            if actual.hex() != reference.hex():
                raise ValueError(f'Native cubic differs for {value!r}: {actual.hex()} / {reference.hex()}')
            results.append(actual)
    return results


def fantom_report(core):
    from effect_lifecycle_study import IMAGE_SHA256
    from kernel_abi import program_list, read
    from bmc_dsp import swap_words

    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom image')
    result = []
    for segment in program_list(core, 0x610e5a94)['segments']:
        stream = swap_words(read(core, segment['source'], (segment['length']+3) & ~3))[:segment['length']]
        found = context(stream)
        base = found['sources'][0]-0xe
        if (found['sources'] != [base+value for value in (0xe, 0x10, 0xf, 0x11)]
                or found['targets'] != [base+value for value in (0x12, 0x18, 0x13, 0x1a)]):
            raise ValueError('Fantom FDRV cubic relative resource relations differ')
        result.append(dict(program_base=segment['base'], data_base=base, **found))
    return result


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--core1', type=Path)
    parser.add_argument('--native-window-frames', type=int,
                        help='Compare the byte window against native callback input/output cutpoints')
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        result['native_probes'] = native_probes([-1, -.5, -0.0, 0.0, .5, 1])
        result['native_execution_verified'] = True
    if args.core1:
        from core1 import Core1
        result['fantom_placements'] = fantom_report(Core1(args.core1))
    if args.native_window_frames is not None:
        from fdrv_filter_study import native_check
        result['native_window'] = native_check(args.native_window_frames, (1, 2), True, compare_cubic=True)
    print(json.dumps(result, indent=2, allow_nan=False))
