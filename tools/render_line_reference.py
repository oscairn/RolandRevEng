"""Render an original LINE-shaped reference pipeline; unknown DSP prefix is not executed."""
import argparse
import json
import math
from pathlib import Path
import wave

from bmc_emulator import execute_fragment
from bmc_subset import assemble_allpass, assemble_fragment
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

LEFT = dict(kind='allpass4', sources=[1, 0xa, 0xd, 0x27, 0x10, 0x13, 0x16],
            targets=[9, 0xc, 0xf, 0x12, 0x29, 0x15])
RIGHT = dict(kind='allpass4', sources=[2, 0x19, 0x1c, 0x28, 0x1f, 0x22, 0x25],
             targets=[0x18, 0x1b, 0x1e, 0x21, 0x2a, 0x24])
PARAMETERS = dict(drive_scale=1/512, drive=0.5, mode=0.5, smoothing=0.75,
                  rational_scale=0.5, a=1.0, b=0.0)


def render_reference(frames):
    from line_shaping_study import native_channel_reference
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    input_program = assemble_fragment(dict(kind='stereo_input', input_addresses=[0x2016, 0x2017]))
    left_program, right_program = assemble_allpass(LEFT), assemble_allpass(RIGHT)
    tail = assemble_fragment(dict(kind='dry_wet_tail_with_scratch', wet_addresses=[0x29, 0x2a],
                                  coefficient_slots=[3, 4, 5, 0], scratch_addresses=[0x2b, 0x2c]))
    # Explicit experiment: fixed P=0, cold zero ring, one origin step per generated frame.
    ring, origin, rows = [0.0]*2048, 0, []
    source_addresses = set(LEFT['sources'] + RIGHT['sources'])
    factor_peak = 0.0
    for frame in range(frames):
        left = 0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE)
        right = 0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE)
        inputs = {0x2016: left, 0x2017: right}
        ports = execute_fragment(input_program, {}, {}, inputs)['ports']
        data = {address: ring[native_ring_index(address, 0, origin)] for address in source_addresses}
        for mixed, history_address, current, saved, factor_address in (
                (ports[0], 4, 1, 3, 0x27), (ports[1], 7, 2, 6, 0x28)):
            history = ring[native_ring_index(history_address, 0, origin)]
            reference = native_channel_reference(mixed, history=history, **PARAMETERS)
            data[current], data[saved], data[factor_address] = mixed, reference['smoothed'], reference['factor']
            factor_peak = max(factor_peak, abs(reference['factor']))
        if factor_peak >= 1:
            raise ValueError('Reference fixture left its chosen allpass-factor domain')
        data = execute_fragment(left_program, data, {})['data']
        data = execute_fragment(right_program, data, {})['data']
        result = execute_fragment(tail, data, {0: 1, 3: 0.5, 4: 0.5, 5: 1},
                                  inputs)
        output = result['ports'][0], result['ports'][4]
        for address, value in result['data'].items():
            ring[native_ring_index(address, 0, origin)] = value
        rows.append(output)
        origin = advance_native_origin(origin)
    info = dict(model='native shaping oracle + strict allpass/tail fragment interpreter',
                whole_dsp_program_executed=False, hardware_timing_verified=False,
                native_plugin_audio_verified=False, software_sample_rate=SAMPLE_RATE,
                wrapper_base=0, origin_steps=frames, final_origin=origin,
                ring_initialization='explicit cold zero fixture', parameters=dict(PARAMETERS),
                factor_peak=factor_peak, **metrics(rows))
    return rows, info


def write_reference(output, frames=12000):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Refusing to replace an existing output')
    rows, info = render_reference(frames)
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
    args = parser.parse_args()
    try:
        print(json.dumps(write_reference(args.output, args.frames), indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
