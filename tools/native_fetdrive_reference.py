"""Run the pinned translated FETDRIVE callback in an explicit macOS ARM64 fixture."""
import argparse
import ctypes
import hashlib
import json
import math
import platform
from pathlib import Path
import struct
import wave

from line_shaping_study import NATIVE_SHA256
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

CALLBACK = (0x2f7de4, 0x2f81c4)
FINAL_RET = 0x2f81c0
CONTEXT_SIZE = 0x560
COEFFICIENTS = (1.0, 0.5, 0.5, 0.5, 1.0)


def render_native(frames):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native FETDRIVE execution requires macOS ARM64')
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if not hasattr(math, 'fma'):
        raise ValueError('The native fixture comparison requires Python 3.13+ math.fma')
    import lib
    from coefficient_shift_study import coefficient_context
    from fetdrive_quantizer_study import native_report, native_shaped_store
    from line_state_study import advance_native_origin, native_ring_index
    from native_callback_fixture import RingFixture, executable_mapping
    from transfer_study import constructor_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned ZENOLOGY ARM64 image')
    _, constructor, pointer_fields, entry, instructions = coefficient_context('SIM_MFX_FETDRIVE')
    start, end = entry, entry + 4*len(instructions)
    if (start, end) != CALLBACK:
        raise ValueError('Native FETDRIVE callback bounds differ')
    allowed = {'add', 'and', 'fadd', 'fcmp', 'fcsel', 'fcvt', 'fcvtzs', 'fdiv', 'fmadd',
               'fmin', 'fmov', 'fmsub', 'fmul', 'fsub', 'ldp', 'ldr', 'lsl', 'mov',
               'movk', 'scvtf', 'str', 'sub'}
    if ([ins.address for ins in instructions] != list(range(start, end, 4))
            or instructions[-1].address != FINAL_RET
            or (instructions[-1].mnemonic, instructions[-1].op_str) != ('ret', '')
            or any(ins.mnemonic not in allowed for ins in instructions[:-1])):
        raise ValueError('Expected the checked call-free, position-independent FETDRIVE body')
    checked = native_report()
    post_gain = checked['native_defaults']['post_gain']
    stores = [row['data_bindings'][-1] for row in checked['quantizers']]
    if [(row['kind'], row['pc'], row['address']) for row in stores] != [
            ('write', 0x2f7ee4, 3), ('write', 0x2f8018, 4)]:
        raise ValueError('Native FETDRIVE first shaped-store bindings differ')
    memory = constructor_memory(constructor, lib.Z)
    if pointer_fields != {0x538 + 8*slot: slot for slot in range(len(COEFFICIENTS))}:
        raise ValueError('Native FETDRIVE live-coefficient fields differ')
    image = bytearray(CONTEXT_SIZE)
    for offset, value in memory.items():
        if not 0 <= offset < min(pointer_fields):
            raise ValueError('Constructor data overlaps the live-coefficient pointers')
        image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    scale, = struct.unpack_from('<d', image, 0x58)
    if ([struct.unpack_from('<d', image, offset)[0] for offset in (0x48, 0x68, 0x38)]
            != [0.0, 1.0, 1.0] or scale != 0.0015476426307448495):
        raise ValueError('Native FETDRIVE mix, post-gain or drive scale differs')
    coefficients = dict(master=COEFFICIENTS[0], drive=COEFFICIENTS[1], dry=COEFFICIENTS[2],
                        wet=COEFFICIENTS[3], post=COEFFICIENTS[4], drive_scale=scale)
    records = []
    for field, slot in sorted(pointer_fields.items()):
        record = ctypes.create_string_buffer(0x48)
        struct.pack_into('<f', record, 0x28, COEFFICIENTS[slot])
        records.append(record)
        struct.pack_into('<Q', context, field, ctypes.addressof(record))

    fixture = RingFixture(context)
    left, right, output_left, output_right = [ctypes.c_double() for _ in range(4)]
    inputs = (ctypes.c_void_p * 2)(ctypes.addressof(left), ctypes.addressof(right))
    outputs = (ctypes.c_void_p * 2)(ctypes.addressof(output_left), ctypes.addressof(output_right))

    callback = lib.Z[start:end]
    with executable_mapping(callback) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        rows, error, origin = [], 0.0, 0
        for frame in range(frames):
            left.value = 0.1 * math.sin(2 * math.pi * 220 * frame / SAMPLE_RATE)
            right.value = 0.08 * math.sin(2 * math.pi * 330 * frame / SAMPLE_RATE)
            struct.pack_into('<I', fixture.ring_context, 0x20, origin)
            invoke(ctypes.addressof(fixture.wrapper), ctypes.addressof(inputs), ctypes.addressof(outputs))
            sample = output_left.value, output_right.value
            if not all(math.isfinite(value) for value in sample):
                raise ValueError('Native FETDRIVE fixture produced a non-finite sample')
            shaped = tuple(fixture.ring[native_ring_index(row['address'], 0, origin)] for row in stores)
            expected = tuple(native_shaped_store(value, drive=COEFFICIENTS[1], scale=scale,
                                                 post_gain=post_gain)['stored']
                             for value in (left.value, right.value))
            if any(actual.hex() != model.hex()
                   for actual, model in zip(shaped, expected, strict=True)):
                raise ValueError(
                    f'Native first shaped stores differ at frame {frame}: '
                    + ' '.join(f'{actual.hex()}!={model.hex()}'
                               for actual, model in zip(shaped, expected, strict=True)))
            error = max(error, *(abs(actual-model) for actual, model in zip(shaped, expected, strict=True)))
            rows.append(sample)
            origin = advance_native_origin(origin)
    return rows, dict(model='pinned native ARM64 FETDRIVE callback with explicit memory fixture',
                      image_sha256=NATIVE_SHA256, callback=[start, end],
                      callback_sha256=hashlib.sha256(callback).hexdigest(),
                      native_callback_executed=True, bmc_instructions_executed=False,
                      cold_zero_ring=True, software_sample_rate=SAMPLE_RATE, wrapper_base=0,
                      final_origin=origin, drive=COEFFICIENTS[1], post_gain=post_gain,
                      constructor_filters_uncalibrated=True, coefficients=coefficients,
                      shaped_stores=stores,
                      first_store_max_abs_error=error, **metrics(rows))


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
