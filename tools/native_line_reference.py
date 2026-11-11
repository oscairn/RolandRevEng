"""Run the pinned translated LINE callback in an explicit macOS ARM64 fixture."""
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
from line_state_study import advance_native_origin
from native_callback_fixture import executable_mapping
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16
from render_line_reference import PARAMETERS, render_reference


def render_native(frames):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Native LINE execution requires macOS ARM64')
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if not hasattr(math, 'fma'):
        raise ValueError('The native fixture comparison requires Python 3.13+ math.fma')
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from transfer_study import constructor_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned ZENOLOGY ARM64 image')
    start, end, native = parse.disasm_meth('SIM_MFX_LINEDRIVE', 'VSubProc(double const**, double**)')
    if (start, end) != (0x2df874, 0x2dfd94):
        raise ValueError('Native LINE callback bounds differ')
    allowed = {'add', 'and', 'cmp', 'cset', 'fadd', 'fcmp', 'fcsel', 'fcvt', 'fcvtzs',
               'fdiv', 'fmadd', 'fmin', 'fmov', 'fmsub', 'fmul', 'fnmul', 'ldp', 'ldr',
               'lsl', 'mov', 'movk', 'orr', 'scvtf', 'str', 'sub', 'ubfiz'}
    if ([ins.address for ins in native] != list(range(start, end, 4))
            or (native[-1].mnemonic, native[-1].op_str) != ('ret', '')
            or any(ins.mnemonic not in allowed for ins in native[:-1])):
        raise ValueError('Expected the checked call-free, position-independent LINE body')
    ctor = parse.parse_ctor('SIM_MFX_LINEDRIVE')
    low, high = lib.func(ctor['ctor'])
    decoder = lib.md()
    decoder.detail = True
    instructions = list(decoder.disasm(lib.Z[low:high], low))
    memory = constructor_memory(instructions, lib.Z)
    pointer_fields = coefficient_pointer_fields(instructions)
    if pointer_fields != {0x578 + 8*slot: slot for slot in range(6)}:
        raise ValueError('Native LINE live-coefficient fields differ')
    image = bytearray(0x5a8)
    for offset, value in memory.items():
        if not 0 <= offset < 0x578:
            raise ValueError('Constructor data overlaps the live-coefficient pointers')
        image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    parameters = dict(PARAMETERS)
    for record, value in (
            (0, parameters['b']), (0x10, parameters['a']), (0x20, parameters['mode']),
            (0x30, parameters['rational_scale']), (0x40, parameters['rational_scale']),
            (0x50, 0), (0x60, parameters['drive_scale']), (0x70, 1)):
        struct.pack_into('<d', context, record+8, value)
    coefficients = (1, parameters['smoothing'], parameters['drive'], 0.5, 0.5, 1)
    records = []
    for field, slot in pointer_fields.items():
        record = ctypes.create_string_buffer(0x48)
        struct.pack_into('<f', record, 0x28, coefficients[slot])
        records.append(record)
        struct.pack_into('<Q', context, field, ctypes.addressof(record))

    ring = (ctypes.c_double * 2048)()
    ring_context = ctypes.create_string_buffer(0x28)
    owner = ctypes.create_string_buffer(0x20)
    manager = ctypes.create_string_buffer(0x20)
    wrapper = ctypes.create_string_buffer(0x30)
    for buffer, offset, target in (
            (ring_context, 0x18, ring), (owner, 0x10, ring_context),
            (manager, 0x18, owner), (wrapper, 8, manager), (wrapper, 0x28, context)):
        struct.pack_into('<Q', buffer, offset, ctypes.addressof(target))
    left, right, output_left, output_right = [ctypes.c_double() for _ in range(4)]
    inputs = (ctypes.c_void_p * 2)(ctypes.addressof(left), ctypes.addressof(right))
    outputs = (ctypes.c_void_p * 2)(ctypes.addressof(output_left), ctypes.addressof(output_right))

    callback = lib.Z[start:end]
    # Original MRS X0,FPCR / RET helper, separate from the copied vendor callback.
    fpcr_reader = bytes.fromhex('00443bd5c0035fd6')
    if [(ins.mnemonic, ins.op_str) for ins in decoder.disasm(fpcr_reader, 0)] != [
            ('mrs', 'x0, fpcr'), ('ret', '')]:
        raise ValueError('Host FPCR reader encoding differs')
    with executable_mapping(callback + fpcr_reader) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        read_fpcr = ctypes.CFUNCTYPE(ctypes.c_uint64)(address + len(callback))
        fpcr = read_fpcr()
        rows, origin = [], 0
        for frame in range(frames):
            left.value = 0.1 * math.sin(2 * math.pi * 220 * frame / SAMPLE_RATE)
            right.value = 0.08 * math.sin(2 * math.pi * 330 * frame / SAMPLE_RATE)
            struct.pack_into('<I', ring_context, 0x20, origin)
            invoke(ctypes.addressof(wrapper), ctypes.addressof(inputs), ctypes.addressof(outputs))
            sample = output_left.value, output_right.value
            if not all(math.isfinite(value) for value in sample):
                raise ValueError('Native LINE fixture produced a non-finite sample')
            rows.append(sample)
            origin = advance_native_origin(origin)
        if read_fpcr() != fpcr:
            raise ValueError('Host FPCR changed during the callback fixture')
    reference, _ = render_reference(frames)
    error = max(abs(actual-expected) for pair, model in zip(rows, reference, strict=True)
                for actual, expected in zip(pair, model, strict=True))
    if error > 1e-12:
        raise ValueError(f'Native callback differs from the conditional LINE reference by {error}')
    return rows, dict(model='pinned native ARM64 LINE callback with explicit memory fixture',
                      image_sha256=NATIVE_SHA256, callback=[start, end],
                      callback_sha256=hashlib.sha256(callback).hexdigest(),
                      native_callback_executed=True, bmc_instructions_executed=False,
                      host_fpcr=fpcr, software_sample_rate=SAMPLE_RATE,
                      parameters=parameters, cold_zero_ring=True, wrapper_base=0,
                      final_origin=origin, reference_max_abs_error=error,
                      reference_identical_frames=sum(a == b for a, b in zip(rows, reference, strict=True)),
                      **metrics(rows))


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
