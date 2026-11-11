"""Run the pinned native TRANSIENT callback with explicit libm and memory fixtures."""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import wave

from line_shaping_study import EPSILON, NATIVE_SHA256, _float32, decode_constant
from line_state_study import advance_native_origin, native_ring_index
from native_callback_fixture import RingFixture, executable_mapping
from native_math_bridge import bind_math_calls
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16
from transient_envelope_reference import envelope_step, tail_reference
from weighted_mix_study import check_constructor_literal, require_instructions

CALLBACK = (0x1d5fd0, 0x1d66c4)
CALLS = {0x1d606c: (0x6d8adc, 'log'), 0x1d647c: (0x6d886c, 'exp'), 0x1d6518: (0x6d886c, 'exp')}
COEFFICIENTS = (1.0, 0.5, 0.25, 0.125)


def render_native(frames):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native TRANSIENT execution requires macOS ARM64')
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if not hasattr(math, 'fma'):
        raise ValueError('TRANSIENT reference comparisons require Python 3.13+ math.fma')
    import lib
    from bmc_dsp import packets
    from coefficient_shift_study import coefficient_context
    from limit_control_study import native_context
    from line_mix_variation import packet_literals
    from transfer_study import constructor_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, constructor, pointer_fields, entry, instructions = coefficient_context('SIM_MFX_TRANSIENT')
    if (entry, instructions[-1].address+4) != CALLBACK:
        raise ValueError('Native TRANSIENT callback bounds differ')
    allowed = {'add', 'and', 'b', 'b.ge', 'b.le', 'b.ls', 'b.lt', 'b.pl', 'bl', 'cmp', 'csel',
               'csinc', 'fadd', 'fcmp', 'fcsel', 'fcvt', 'fcvtzs', 'fmadd', 'fmaxnm', 'fmov',
               'fmul', 'fneg', 'fsub', 'ldp', 'ldr', 'mov', 'movk', 'ret', 'scvtf', 'stp', 'str', 'sub'}
    if any(ins.mnemonic not in allowed for ins in instructions):
        raise ValueError('Unexpected instruction in the pinned TRANSIENT body')
    native = {ins.address: ins for ins in instructions}
    memory = constructor_memory(constructor, lib.Z)
    if pointer_fields != {0x660+8*slot: slot for slot in range(4)} or max(memory) != 0x65f:
        raise ValueError('TRANSIENT constructor/pointer layout differs')
    image = bytearray(0x680)
    for offset, value in memory.items():
        if not 0 <= offset < 0x660:
            raise ValueError('TRANSIENT constructor overlaps its live-coefficient pointers')
        image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    records = []
    for field, slot in pointer_fields.items():
        record = ctypes.create_string_buffer(0x48)
        struct.pack_into('<f', record, 0x28, COEFFICIENTS[slot])
        records.append(record)
        struct.pack_into('<Q', context, field, ctypes.addressof(record))
    normalization, = struct.unpack_from('<d', image, 0x28)
    literal, = packet_literals(program, 0xe, dict(packets(program))[0xe])
    check_constructor_literal(program, memory, native[0x1d6040], literal, object_register='x21')
    floor = decode_constant([native[pc] for pc in range(0x1d6074, 0x1d6088, 4)])['value']
    if floor != math.log(2**-32):
        raise ValueError('TRANSIENT zero-log floor differs')
    require_instructions(native, 0x1d6068, (('fmov', 'd0, d8'), ('bl', '#0x6d8adc'),
                                          ('fcmp', 'd8, #0.0')))
    require_instructions(native, 0x1d6088, (('fcsel', 'd0, d1, d0, eq'),))
    _, _, _, fields, _ = native_context('SIM_MFX_TRANSIENT')
    if [fields[field] for field in (0xf4, 0xfc)] != [
            dict(relative=0x1c, address=0), dict(relative=0x5c, address=1)]:
        raise ValueError('TRANSIENT peak/log store records differ')
    require_instructions(native, 0x1d6094, (('add', 'w8, w9, w8'), ('and', 'w8, w8, #0x7ff'),
                                          ('str', 'd0, [x23, w8, uxtw #3]')))
    from condition_return_study import preserved

    for field, relative, address in ((0x204, 0x180, 36), (0x20c, 0x18c, 37),
            (0x214, 0x27c, 38), (0x21c, 0x23c, 39), (0x224, 0x2a2, 40),
            (0x22c, 0x26c, 41), (0x164, 0x312, 16)):
        if fields[field] != dict(relative=relative, address=address):
            raise ValueError('TRANSIENT envelope/gain record differs')
    for pc, field, register in ((0x1d6430, 0x204, 'd0'), (0x1d646c, 0x20c, 'd8'),
            (0x1d64d0, 0x214, 'd0'), (0x1d6530, 0x224, 'd0')):
        require_instructions(native, pc, (
            ('ldr', f'w8, [x21, #{field:#x}]'), ('add', 'w8, w27, w8'),
            ('and', 'w8, w8, #0x7ff'), ('str', f'{register}, [x23, w8, uxtw #3]'),
        ))
    preserved([native[pc] for pc in range(0x1d6440, 0x1d647c, 4)], 'd0')
    # D8's low 64 bits are callee-saved by the libm ABI as well as explicitly preserved here.
    preserved([native[pc] for pc in range(0x1d647c, 0x1d6518, 4)], 'd8')
    require_instructions(native, 0x1d6644, (
        ('fmul', 'd3, d3, d6'), ('fmadd', 'd2, d5, d2, d3'),
        ('fadd', 'd2, d2, d4'), ('fmadd', 'd2, d16, d7, d2'),
    ))

    def rate(offset):
        return struct.unpack_from('<d', image, offset)[0]

    # Truncating fixed32 preserves this threshold predicate within the conversion domain.
    positive_first, positive_second = (_float32(COEFFICIENTS[slot]) > -EPSILON for slot in (1, 3))
    first_rates = dict(above=rate(0x68 if positive_first else 0x48), below=rate(0x58 if positive_first else 0x38))
    second_rates = dict(above=rate(0xb8 if positive_second else 0x98), below=rate(0xa8 if positive_second else 0x88))

    callback = lib.Z[entry:CALLBACK[1]]
    code, bridge = bind_math_calls(callback, entry, CALLS)
    fixture = RingFixture(context)
    if ctypes.sizeof(fixture.owner) < 0x120:
        raise ValueError('TRANSIENT owner does not cover both three-slot caches')
    left, right, output_left, output_right = [ctypes.c_double() for _ in range(4)]
    inputs = (ctypes.c_void_p*2)(ctypes.addressof(left), ctypes.addressof(right))
    outputs = (ctypes.c_void_p*2)(ctypes.addressof(output_left), ctypes.addressof(output_right))
    rows, origin = [], 0
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        for frame in range(frames):
            left.value = 0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE)
            right.value = 0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE)
            struct.pack_into('<I', fixture.ring_context, 0x20, origin)
            previous_first, previous_second = [fixture.ring[native_ring_index(cell, 0, origin)] for cell in (39, 41)]
            invoke(ctypes.addressof(fixture.wrapper), ctypes.addressof(inputs), ctypes.addressof(outputs))
            peak = normalization*max(abs(left.value), abs(right.value))
            logarithm = floor if peak == 0 else math.log(peak)
            observed = [fixture.ring[native_ring_index(cell, 0, origin)] for cell in (0, 1)]
            if [value.hex() for value in observed] != [peak.hex(), logarithm.hex()]:
                raise ValueError(f'Native TRANSIENT peak/log differs at frame {frame}: {observed}')
            sample = output_left.value, output_right.value
            if not all(math.isfinite(value) for value in sample):
                raise ValueError('Native TRANSIENT produced a non-finite output')
            argument_first, argument_second = [fixture.ring[native_ring_index(cell, 0, origin)] for cell in (36, 37)]
            first = envelope_step(argument_first, previous_first, **first_rates)
            second = envelope_step(argument_second, previous_second, **second_rates)
            tail = tail_reference(left.value, right.value, first, second, COEFFICIENTS)
            actual = [fixture.ring[native_ring_index(cell, 0, origin)] for cell in (38, 40, 16)] + list(sample)
            expected = [first, second, tail['gain'], *tail['output']]
            if [value.hex() for value in actual] != [value.hex() for value in expected]:
                raise ValueError(f'Native TRANSIENT envelope/tail differs at frame {frame}')
            rows.append(sample)
            origin = advance_native_origin(origin)
    cursors = [struct.unpack_from('<I', fixture.owner, offset)[0] for offset in (0xb8, 0x118)]
    if any(cursor not in range(3) for cursor in cursors):
        raise ValueError('Native TRANSIENT cache cursor left its three-slot domain')
    return rows, dict(model='pinned native ARM64 TRANSIENT callback with explicit libm/memory fixture',
                      image_sha256=NATIVE_SHA256, callback=list(CALLBACK),
                      callback_sha256=hashlib.sha256(callback).hexdigest(), math_bridge=bridge,
                      native_callback_executed=True, bmc_instructions_executed=False,
                      software_sample_rate=SAMPLE_RATE, live_coefficients=list(COEFFICIENTS),
                      constructor_defaults_retained=True, cold_zero_ring=True, wrapper_base=0,
                      final_origin=origin, final_cache_cursors=cursors, zero_log_floor=floor,
                      owner_bytes=ctypes.sizeof(fixture.owner),
                      peak_normalization=normalization, peak_log_identical_values=2*frames,
                      envelope_tail_identical_values=5*frames, conditional_output_reference_verified=True,
                      upstream_arguments_from_native=True, envelope_rates=[first_rates, second_rates],
                      full_output_reference_verified=False, **metrics(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new WAV path')
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        samples, report = render_native(args.frames)
        payload = pcm16(samples)
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
        print(json.dumps(report, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
