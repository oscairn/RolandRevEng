"""Check the first stereo FDRV state-variable block; native policy, not silicon timing."""
import hashlib
import math

from line_shaping_study import NATIVE_SHA256, _finite, _float32


def filter_step(y, s, t, a, b, c, d, e):
    y, s, t = map(_finite, (y, s, t))
    a, b, c, d, e = map(_float32, (a, b, c, d, e))
    if not hasattr(math, 'fma'):
        raise ValueError('The native filter reference requires Python 3.13+ math.fma')
    try:
        next_t = _finite(_finite(math.fma(s, a, s))+t)
        highpass = _finite(_finite(math.fma(s, b, -next_t))+y)
        preliminary = _finite(math.fma(y, c, _finite(highpass*e)))
        next_s = _finite(_finite(math.fma(highpass, a, highpass))+s)
        output = _finite(math.fma(_finite(next_s+s), d, preliminary))
    except OverflowError as error:
        raise ValueError('Filter reference exceeds finite arithmetic') from error
    return dict(state_s=next_s, state_t=next_t, highpass=highpass, output=output)


def stability(a, b):
    a, b = map(_float32, (a, b))
    g, q = 1+a, -b
    return dict(g=g, damping=q, trace=2-g*q-g*g, determinant=1-g*q,
                stable=g*q > 0 and 4-2*g*q-g*g > 0,
                hardware_calibrated=False)


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from native_auxiliary_study import report as auxiliary_report
    from weighted_mix_study import require_instructions, require_words
    from bmc_dsp import packets

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    auxiliary = auxiliary_report()
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    rows = dict(packets(program))
    for offset, expected in (
            (0x66, (0x4709, 0x1c8b, 0x5d8f, 0x3fe4, 0x7fe6, 0x2001, 0x6005, 0xc00b, 0xc00b)),
            (0x96, (0x5f07, 0x2443, 0x6547, 0x3fe0, 0x7fe2, 0xc00c, 0xc00c)),
            (0xb6, (0x1005, 0x1c4b, 0x5d4f, 0x1002, 0x5006))):
        require_words(rows, offset, expected)
    bindings = []
    for channel, (source_s, source_t, t_field, t_store, s_field, s_store, output_field, output_store) in enumerate((
            (0x3051ec, 0x3051fc, 0x8e, 0x305228, 0xd2, 0x3052ac, 0x10a, 0x305398),
            (0x3052d0, 0x3052e0, 0x92, 0x305308, 0xd6, 0x30537c, 0x10c, 0x3053ac))):
        s, t = (0x29, 0x2a) if channel == 0 else (0x2c, 0x2d)
        for pc, register, relative, cell, kind in (
                (source_s, 'd2', 0x48+2*channel, s, 'read'),
                (source_t, 'd3', 0x5e+4*channel, t, 'read'),
                (t_store, 'd3', t_field, s, 'write'),
                (s_store, 'd2', s_field, s-1, 'write'),
                (output_store, 'd1' if channel == 0 else 'd0', output_field, 0x24+channel, 'write')):
            item = checked_access(native, fields, trace, pc, kind, relative, cell)
            if native[pc].reg_name(native[pc].operands[0].reg) != register:
                raise ValueError('FDRV filter cutpoint register differs')
            bindings.append(item)
    for pc, instructions in (
            (0x305214, (('fmadd', 'd4, d2, d4, d2'), ('fadd', 'd3, d3, d4'))),
            (0x305250, (('fnmsub', 'd2, d2, d4, d3'), ('fadd', 'd2, d1, d2'))),
            (0x305264, (('fmul', 'd4, d2, d5'),)),
            (0x30528c, (('fmadd', 'd1, d1, d3, d4'), ('fmadd', 'd2, d2, d6, d2'),
                         ('fadd', 'd2, d5, d2'))),
            (0x3052f4, (('fmadd', 'd4, d2, d4, d2'), ('fadd', 'd3, d3, d4'))),
            (0x305328, (('fnmsub', 'd2, d2, d5, d3'), ('fadd', 'd2, d0, d2'))),
            (0x305338, (('fmul', 'd4, d2, d4'),)),
            (0x30535c, (('fmadd', 'd0, d0, d3, d4'), ('fmadd', 'd2, d2, d6, d2'),
                         ('fadd', 'd2, d5, d2')))):
        require_instructions(native, pc, instructions)
    for pc, slot in ((0x305204, 10), (0x305210, 11), (0x305248, 14), (0x30525c, 12),
                     (0x3052b4, 13), (0x3052e4, 10), (0x3052ec, 11), (0x305320, 14),
                     (0x305330, 12), (0x305380, 13)):
        if dict(pc=pc, slot=slot, width=4) not in trace['coefficient_reads']:
            raise ValueError('FDRV filter coefficient reader differs')
    for register, start, end in (('d3', 0x30522c, 0x305250), ('d2', 0x305258, 0x305290),
                                  ('d4', 0x305268, 0x30528c), ('d1', 0x3051cc, 0x30528c),
                                  ('d3', 0x30530c, 0x305328), ('d2', 0x305330, 0x305360),
                                  ('d4', 0x30533c, 0x30535c), ('d0', 0x3051e0, 0x30535c)):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    return dict(native_sha256=NATIVE_SHA256, callback=[0x3050ec, 0x305ea8],
                auxiliary=auxiliary['native_banks'], cutpoints=bindings,
                coefficient_slots=[10, 11, 12, 13, 14],
                state_relation='next S at S-1, next T at S; advancing native origin by one recovers both',
                hardware_origin_cadence_verified=False, hardware_calibrated=False,
                admitted_profile='state_variable_pair', logical_profile_length=184,
                isolated_opcode_admission=False)


def native_check(frames=128, cursors=(0, 0), compare_emulator=False, state_seeds=None,
                  compare_cubic=False, compare_clip=False):
    import ctypes
    import struct
    import lib
    from coefficient_shift_study import coefficient_context
    from line_state_study import advance_native_origin, native_ring_index
    from native_auxiliary_study import _cache
    from native_callback_fixture import RingFixture, executable_mapping
    from transfer_study import constructor_memory

    if type(frames) is not int or not 1 <= frames <= 1000000 or len(cursors) != 2:
        raise ValueError('Expected 1..1000000 frames and two valid cursors')
    for cursor in cursors:
        _cache([0, 0, 0], cursor)
    if state_seeds is not None:
        if not isinstance(state_seeds, (list, tuple)) or len(state_seeds) != 4:
            raise ValueError('Expected four explicit initial S/T values')
        state_seeds = list(map(_finite, state_seeds))
    checked = report()
    _, constructor, pointers, entry, instructions = coefficient_context('SIM_MFX_FDRV')
    if (entry, instructions[-1].address+4) != tuple(checked['callback']) or pointers != {
            0x820+8*slot: slot for slot in range(20)}:
        raise ValueError('FDRV callback or live pointer layout differs')
    allowed = {'add', 'and', 'cmp', 'csel', 'csinc', 'fadd', 'fcmp', 'fcsel', 'fcvt', 'fmadd',
               'fmin', 'fmov', 'fmsub', 'fmul', 'fnmsub', 'fnmul', 'fsub', 'ldp', 'ldr',
               'mov', 'stp', 'str', 'sub', 'ubfiz'}
    if ([i.address for i in instructions] != list(range(entry, checked['callback'][1], 4))
            or (instructions[-1].mnemonic, instructions[-1].op_str) != ('ret', '')
            or any(i.mnemonic not in allowed for i in instructions[:-1])):
        raise ValueError('Expected the checked call-free position-independent FDRV callback')
    image = bytearray(0x8c0)
    for offset, value in constructor_memory(constructor, lib.Z).items():
        if not 0 <= offset < 0x820:
            raise ValueError('FDRV constructor data overlaps live pointers')
        image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    values = [0.0]*20
    values[5] = 1.0
    values[10:15] = [-.4973, -.2531, .3737, .1279, -.0623]
    values[15:20] = [-.5, -.25, 0, .5, 0]
    if compare_cubic or compare_clip:
        values[0] = .75
    records = []
    for offset, slot in pointers.items():
        record = ctypes.create_string_buffer(0x48)
        struct.pack_into('<f', record, 0x28, values[slot])
        records.append(record)
        struct.pack_into('<Q', context, offset, ctypes.addressof(record))
    fixture = RingFixture(context)
    for bank, cursor in zip((0x80, 0x100), cursors, strict=True):
        struct.pack_into('<3dI', fixture.owner, bank, -11, 23, -37, cursor)
    for index in range(2048):
        fixture.ring[index] = ((index*37 % 101)-50)/10000
    if state_seeds is not None:
        for cell, value in zip((0x29, 0x2a, 0x2c, 0x2d), state_seeds, strict=True):
            fixture.ring[cell] = value
    left, right, out_left, out_right = [ctypes.c_double() for _ in range(4)]
    inputs = (ctypes.c_void_p*2)(ctypes.addressof(left), ctypes.addressof(right))
    outputs = (ctypes.c_void_p*2)(ctypes.addressof(out_left), ctypes.addressof(out_right))
    origin, count, cubic_count, cubic_input_values = 0, 0, 0, set()
    clip_count = 0
    if compare_emulator:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        spec = filter_spec()
        program = assemble_fragment(spec)
    if compare_cubic:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from fdrv_cubic_study import cubic_reference, cubic_spec, report as cubic_report
        cubic_report()
        shape_spec = cubic_spec()
        shape_program = assemble_fragment(shape_spec)
    if compare_clip:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from fdrv_clip_study import clip_reference, half_reference, clip_spec, report as clip_report
        clip_report()
        clipped_spec = clip_spec()
        clipped_program = assemble_fragment(clipped_spec)
    with executable_mapping(lib.Z[entry:checked['callback'][1]]) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        for frame in range(frames):
            left.value = .08*math.sin(2*math.pi*220*frame/48000)
            right.value = -.06*math.cos(2*math.pi*337*frame/48000)
            read = lambda cell: fixture.ring[native_ring_index(cell, 0, origin)]
            mixed = [math.fma(read(old2), values[7], math.fma(read(old1), values[6], sample*values[5]))
                     for old1, old2, sample in ((0x1f, 0x20, left.value), (0x22, 0x23, right.value))]
            model = [filter_step(y, read(s), read(s+1), *values[10:15])
                     for y, s in zip(mixed, (0x29, 0x2c), strict=True)]
            if compare_emulator:
                data = {cell: read(cell) for cell in spec['sources']}
                data.update({0x1f: mixed[0], 0x22: mixed[1]})
                emulated = execute_fragment(program, data, dict(enumerate(values)))
                for index, item in enumerate(model):
                    for key, actual in (('state_s', emulated['data'][0x28+3*index]),
                                        ('state_t', emulated['data'][0x29+3*index]),
                                        ('output', emulated['ports'][4*index])):
                        if item[key].hex() != actual.hex():
                            raise ValueError('Byte-emulated filter differs from independent reference')
            struct.pack_into('<I', fixture.ring_context, 0x20, origin)
            invoke(ctypes.addressof(fixture.wrapper), ctypes.addressof(inputs), ctypes.addressof(outputs))
            for index, item in enumerate(model):
                for cell, expected in ((0x1f+3*index, mixed[index]), (0x28+3*index, item['state_s']),
                                       (0x29+3*index, item['state_t']), (0x24+index, item['output'])):
                    if read(cell).hex() != expected.hex():
                        raise ValueError(f'Native FDRV filter differs at frame {frame}, cell {cell:#x}')
                    count += 1
            if compare_cubic:
                # The cubic study proves these inputs/results are not overwritten later.
                captured = {cell: read(cell) for cell in shape_spec['sources']}
                cubic_input_values.update(value.hex() for value in captured.values())
                shaped = execute_fragment(shape_program, captured, {})
                for source, target in zip(shape_spec['sources'], shape_spec['targets'], strict=True):
                    expected = cubic_reference(captured[source])
                    if read(target).hex() != expected.hex() or shaped['data'][target].hex() != expected.hex():
                        raise ValueError('Cubic byte window differs from conditional native cutpoints')
                    cubic_count += 1
            if compare_clip:
                # The clip checker audits these source/result cutpoints for later overwrites.
                current_left, current_right = read(0x14), read(0x16)
                previous_left, previous_right = read(0x15), read(0x17)
                captured = dict(zip(clipped_spec['sources'],
                                    (current_left, current_right, previous_left, previous_right)))
                clipped = execute_fragment(clipped_program, captured, {})
                expected = (current_left, current_right,
                            half_reference(current_left, previous_left), clip_reference(current_left),
                            half_reference(current_right, previous_right), clip_reference(current_right))
                for target, value in zip(clipped_spec['targets'], expected, strict=True):
                    if read(target).hex() != value.hex() or clipped['data'][target].hex() != value.hex():
                        raise ValueError('Clipped-half bytes differ from conditional native cutpoints')
                    clip_count += 1
            origin = advance_native_origin(origin)
    actual_cursors = tuple(struct.unpack_from('<I', fixture.owner, offset)[0] for offset in (0x98, 0x118))
    if actual_cursors != tuple(cursors):
        raise ValueError('Native FDRV filter cursors did not roundtrip')
    if compare_cubic and frames >= 128 and len(cubic_input_values) < 32:
        raise ValueError('Native cubic comparison did not exercise varied input cutpoints')
    return dict(frames=frames, identical_native_values=count, final_origin=origin,
                initial_cursors=list(cursors), final_cursors=list(actual_cursors),
                explicit_state_seeds=state_seeds,
                emulator_checked=compare_emulator, native_callback_executed=True,
                conditional_cubic_values_checked=cubic_count,
                conditional_clipped_values_checked=clip_count,
                distinct_cubic_input_values=len(cubic_input_values),
                bmc_hardware_executed=False, coefficient_sources=values[10:15],
                coefficients=list(map(_float32, values[10:15])))


def filter_spec():
    return dict(kind='state_variable_pair', sources=[0x1f, 0x2a, 0x29, 0x22, 0x2d, 0x2c,
                                                   0x2f, 0x32, 0x30, 0x33],
                targets=[0x29, 0x2c, 0x28, 0x2b], coefficient_slots=[10, 11, 12, 13, 14])


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=128)
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        result['native_check'] = native_check(args.frames, compare_emulator=True)
    print(json.dumps(result, indent=2, allow_nan=False))
