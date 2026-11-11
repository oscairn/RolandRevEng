"""Render independent native TRANSIENT arithmetic over an explicit cold ring."""
import argparse
import json
import math
from pathlib import Path
import wave

from line_shaping_study import EPSILON, _float32
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16
from transient_detector_reference import HISTORY, detector_step
from transient_envelope_reference import envelope_step, tail_reference
from transient_state_study import report as state_report


def render_reference(frames):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if not hasattr(math, 'fma'):
        raise ValueError('TRANSIENT reference requires Python 3.13+ math.fma')
    from native_transient_reference import COEFFICIENTS

    checked = state_report()
    defaults = checked['defaults']
    first_positive, second_positive = (_float32(COEFFICIENTS[slot]) > -EPSILON for slot in (1, 3))
    rates = [dict(above=defaults[0x68 if first_positive else 0x48],
                  below=defaults[0x58 if first_positive else 0x38]),
             dict(above=defaults[0xb8 if second_positive else 0x98],
                  below=defaults[0xa8 if second_positive else 0x88])]
    ring, origin, rows = [0.0]*2048, 0, []
    decisions = dict(phase_resets=0, history_rolls=0, faster_release=0)

    def read(cell):
        return ring[native_ring_index(cell, 0, origin)]

    def write(cell, value):
        ring[native_ring_index(cell, 0, origin)] = value

    for frame in range(frames):
        left = 0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE)
        right = 0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE)
        detector = detector_step(left, right, {cell: read(cell) for cell in HISTORY}, defaults)
        for cell, value in detector['writes'].items():
            write(cell, value)
        first = envelope_step(read(36), read(39), **rates[0])
        second = envelope_step(read(37), read(41), **rates[1])
        write(38, first)
        write(40, second)
        tail = tail_reference(left, right, first, second, COEFFICIENTS)
        write(16, tail['gain'])
        rows.append(tail['output'])
        decisions['phase_resets'] += detector['phase_reset']
        decisions['history_rolls'] += detector['history_roll']
        decisions['faster_release'] += detector['release_rate_field'] == 0xe8
        origin = advance_native_origin(origin)
    return rows, dict(model='independent native TRANSIENT arithmetic with explicit cold ring',
                      native_callback_executed=False, bmc_instructions_executed=False,
                      hardware_timing_verified=False, upstream_arguments_from_native=False,
                      software_sample_rate=SAMPLE_RATE, wrapper_base=0, final_origin=origin,
                      live_coefficients=list(COEFFICIENTS), history=checked['history'],
                      detector_decisions=decisions, **metrics(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new stereo WAV path')
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        samples, result = render_reference(args.frames)
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(pcm16(samples))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
