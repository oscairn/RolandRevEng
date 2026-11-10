"""Render an original LINE-shaped reference pipeline; unknown DSP prefix is not executed."""
import argparse
import json
import math
from pathlib import Path
import wave

from bmc_emulator import execute_fragment
from bmc_subset import DEFAULT_INPUT_ADDRESSES, assemble_allpass, assemble_fragment, disassemble_fragment
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

LEFT = dict(kind='allpass4', sources=[1, 0xa, 0xd, 0x27, 0x10, 0x13, 0x16],
            targets=[9, 0xc, 0xf, 0x12, 0x29, 0x15])
RIGHT = dict(kind='allpass4', sources=[2, 0x19, 0x1c, 0x28, 0x1f, 0x22, 0x25],
             targets=[0x18, 0x1b, 0x1e, 0x21, 0x2a, 0x24])
PARAMETERS = dict(drive_scale=1/512, drive=0.5, mode=0.5, smoothing=0.75,
                  rational_scale=0.5, a=1.0, b=0.0)


def render_reference(frames, *, firmware_context=None, mono=0.0, stereo=1.0):
    from line_shaping_study import native_channel_reference, native_stereo_mix
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if firmware_context is None:
        input_program = assemble_fragment(dict(kind='stereo_input', input_addresses=list(DEFAULT_INPUT_ADDRESSES)))
        left_program, right_program = assemble_allpass(LEFT), assemble_allpass(RIGHT)
        tail = assemble_fragment(dict(kind='dry_wet_tail_with_scratch', wet_addresses=[0x29, 0x2a],
                                      coefficient_slots=[3, 4, 5, 0], scratch_addresses=[0x2b, 0x2c]))
        shape_addresses = [(4, 3), (7, 6)]
    else:
        programs, shape_addresses, _ = firmware_context
        input_program, left_program, right_program, tail = programs
    input_addresses = disassemble_fragment(input_program)['input_addresses']
    chains = [disassemble_fragment(program) for program in (left_program, right_program)]
    mix_coefficients = dict(zip(disassemble_fragment(tail)['coefficient_slots'], (0.5, 0.5, 1, 1)))
    # Explicit experiment: fixed P=0, cold zero ring, one origin step per generated frame.
    ring, origin, rows = [0.0]*2048, 0, []
    source_addresses = set(chains[0]['sources'] + chains[1]['sources'])
    factor_peak = 0.0
    for frame in range(frames):
        left = 0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE)
        right = 0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE)
        inputs = dict(zip(input_addresses, (left, right)))
        ports = execute_fragment(input_program, {}, {}, inputs)['ports']
        data = {address: ring[native_ring_index(address, 0, origin)] for address in source_addresses}
        mixed_inputs = native_stereo_mix(*ports[:2], mono=mono, stereo=stereo)
        for mixed, chain, (history_address, saved) in zip(mixed_inputs, chains, shape_addresses):
            current, _, _, factor_address, *_ = chain['sources']
            history = ring[native_ring_index(history_address, 0, origin)]
            reference = native_channel_reference(mixed, history=history, **PARAMETERS)
            data[current], data[saved], data[factor_address] = mixed, reference['smoothed'], reference['factor']
            factor_peak = max(factor_peak, abs(reference['factor']))
        if factor_peak >= 1:
            raise ValueError('Reference fixture left its chosen allpass-factor domain')
        data = execute_fragment(left_program, data, {})['data']
        data = execute_fragment(right_program, data, {})['data']
        result = execute_fragment(tail, data, mix_coefficients, inputs)
        output = result['ports'][0], result['ports'][4]
        for address, value in result['data'].items():
            ring[native_ring_index(address, 0, origin)] = value
        rows.append(output)
        origin = advance_native_origin(origin)
    info = dict(model='native input mix and shaping + strict packet interpreter',
                whole_dsp_program_executed=False, hardware_timing_verified=False,
                native_plugin_audio_verified=False, software_sample_rate=SAMPLE_RATE,
                wrapper_base=0, origin_steps=frames, final_origin=origin,
                ring_initialization='explicit cold zero fixture', parameters=dict(PARAMETERS),
                native_mix=dict(mono=mono, stereo=stereo),
                factor_peak=factor_peak, **metrics(rows))
    if firmware_context is not None:
        info['firmware_context'] = firmware_context[2]
    return rows, info


def write_reference(output, frames=12000, *, firmware_context=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Refusing to replace an existing output')
    rows, info = render_reference(frames, firmware_context=firmware_context)
    payload = pcm16(rows)
    with output.open('xb') as stream:
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new WAV path in an existing directory')
    parser.add_argument('--frames', type=int, default=12000)
    parser.add_argument('--core1', type=Path, help='Use stock fragments from the pinned Fantom image')
    parser.add_argument('--owner', type=lambda value: int(value, 0), help='Fantom effect owner descriptor')
    args = parser.parse_args()
    if args.owner is not None and args.core1 is None:
        parser.error('--owner requires --core1')
    try:
        context = None
        if args.core1 is not None:
            from core1 import Core1
            from fantom_line_context import OWNERS, load_context
            context = load_context(Core1(args.core1), OWNERS[0] if args.owner is None else args.owner)
        print(json.dumps(write_reference(args.output, args.frames, firmware_context=context),
                         indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
