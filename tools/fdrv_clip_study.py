"""Check FDRV half-sample interpolation and clipping; no silicon precision claim."""
import hashlib
import math

from bmc_dsp import packets
from bmc_subset import assemble_fragment
from line_shaping_study import NATIVE_SHA256, _finite


def clip_spec(base=0):
    return dict(kind='clipped_half_pair', sources=[base+x for x in (0x100, 0x101, 0x15, 0x17)],
                targets=[base+x for x in (0x14, 0x16, 0xe, 0x10, 0xf, 0x11)])


def clip_reference(value):
    value = _finite(value)
    return -1.0 if value < -1 else min(value, 1.0)


def half_reference(current, previous):
    current, previous = map(_finite, (current, previous))
    if not hasattr(math, 'fma'):
        raise ValueError('The native half-sample reference requires Python 3.13+ math.fma')
    return clip_reference(math.fma(current, .5, previous*.5))


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from weighted_mix_study import require_instructions, require_words

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    template = assemble_fragment(clip_spec())
    if template[14:74] != program[0x33c:0x378]:
        raise ValueError('Clipped-half template differs from the stock packet window')
    require_words(dict(packets(program)), 0x378, (0x3407, 0x2410, 0xcfe2, 0x4fe4, 0x4300))
    for pc, shape in (
            (0x305934, (('fmov', 'd3, #1.00000000'), ('fmin', 'd4, d1, d3'),
                        ('fmov', 'd5, #-1.00000000'), ('fcmp', 'd1, d5'),
                        ('fcsel', 'd4, d5, d4, mi'), ('fmov', 'd6, #0.50000000'),
                        ('fmul', 'd2, d2, d6'), ('fmadd', 'd2, d1, d6, d2'))),
            (0x305974, (('fmin', 'd7, d2, d3'), ('fcmp', 'd2, d5'))),
            (0x30598c, (('fcsel', 'd2, d5, d7, mi'),)),
            (0x3059a0, (('fmul', 'd1, d1, d6'),)),
            (0x3059b4, (('fmadd', 'd1, d0, d6, d1'), ('fmin', 'd2, d1, d3'),
                        ('fcmp', 'd1, d5'), ('fcsel', 'd1, d5, d2, mi'),
                        ('fmin', 'd2, d0, d3'), ('fcmp', 'd0, d5'),
                        ('fcsel', 'd0, d5, d2, mi')))):
        require_instructions(native, pc, shape)
    for register, start in (('d3', 0x305938), ('d5', 0x305940), ('d6', 0x30594c)):
        preserved([native[pc] for pc in range(start, 0x3059d0, 4)], register)
    bindings = []
    for name, pc, kind, field, cell, register in (
            ('previous_left', 0x305930, 'read', 0x33a, 0x15, 'd2'),
            ('previous_right', 0x305970, 'read', 0x34e, 0x17, 'd1'),
            ('save_left', 0x305960, 'write', 0x34c, 0x14, 'd1'),
            ('save_right', 0x30599c, 'write', 0x362, 0x16, 'd0'),
            ('direct_left', 0x305988, 'write', 0x360, 0x10, 'd4'),
            ('average_left', 0x3059b0, 'write', 0x36a, 0xe, 'd2'),
            ('average_right', 0x3059dc, 'write', 0x374, 0xf, 'd1'),
            ('direct_right', 0x3059ec, 'write', 0x382, 0x11, 'd0')):
        require_instructions(native, pc, ((('ldr' if kind == 'read' else 'str'),
                                          f'{register}, [x11, w13, uxtw #3]'),))
        item = checked_access(native, fields, trace, pc, kind, field, cell)
        if any(access['kind'] == 'write' and access['pc'] > pc
               and any(fields[key]['address'] == cell for key in access['fields'])
               for access in trace['accesses']):
            raise ValueError('Clipping cutpoint is overwritten later in the callback')
        bindings.append(dict(name=name, **item))
    return dict(native_sha256=NATIVE_SHA256, admitted_profile='clipped_half_pair',
                profile_bytes=80, packet_count=6, stock_body=[0x33c, 0x378], bindings=bindings,
                averaging_before_clipping=True, stored_history_is_unclipped=True,
                hardware_execution_verified=False, full_effect_executable=False)


def native_probes(values):
    """Execute checked register-only extracts; FMOV/RET provide the result ABI."""
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    report()
    values = [(_finite(current), _finite(previous)) for current, previous in values]
    constants = [0x305934, 0x30593c]
    clip_pcs = constants+[0x3059c4, 0x3059c8, 0x3059cc]
    half_pcs = constants+[0x305948, 0x3059a0, 0x3059b4, 0x3059b8, 0x3059bc, 0x3059c0]
    clip = b''.join(lib.Z[pc:pc+4] for pc in clip_pcs)+bytes.fromhex('c0035fd6')
    half = b''.join(lib.Z[pc:pc+4] for pc in half_pcs)+bytes.fromhex('2040601ec0035fd6')
    expected = [('fmov', 'd3, #1.00000000'), ('fmov', 'd5, #-1.00000000'),
                ('fmov', 'd6, #0.50000000'), ('fmul', 'd1, d1, d6'),
                ('fmadd', 'd1, d0, d6, d1'), ('fmin', 'd2, d1, d3'),
                ('fcmp', 'd1, d5'), ('fcsel', 'd1, d5, d2, mi'),
                ('fmov', 'd0, d1'), ('ret', '')]
    if [(i.mnemonic, i.op_str) for i in lib.md().disasm(half, 0)] != expected:
        raise ValueError('Native half-sample probe ABI differs')
    results = []
    with executable_mapping(clip) as first, executable_mapping(half) as second:
        clip_call = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(first)
        half_call = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double, ctypes.c_double)(second)
        for current, previous in values:
            actual = [clip_call(current), half_call(current, previous)]
            reference = [clip_reference(current), half_reference(current, previous)]
            if [value.hex() for value in actual] != [value.hex() for value in reference]:
                raise ValueError('Native clip/half arithmetic differs from reference')
            results.append(actual)
    return results


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--native-window-frames', type=int)
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        result['native_probes'] = native_probes([(2, -.5), (-.75, 3), (-0.0, -0.0)])
    if args.native_window_frames is not None:
        from fdrv_filter_study import native_check
        result['native_window'] = native_check(args.native_window_frames, compare_clip=True)
    print(json.dumps(result, indent=2, allow_nan=False))
