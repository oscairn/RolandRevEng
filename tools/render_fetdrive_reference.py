"""Render the checked native FETDRIVE arithmetic with explicit fixture state."""
import argparse
import json
import math
from pathlib import Path
import struct
import wave

from fetdrive_quantizer_study import native_report, native_shaped_store
from fetdrive_state_study import report as state_report
from limit_control_study import native_context
from line_shaping_study import native_stereo_mix
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16


def render_reference(frames):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    if not hasattr(math, 'fma'):
        raise ValueError('The FETDRIVE reference requires Python 3.13+ math.fma')
    from native_fetdrive_reference import COEFFICIENTS

    checked = state_report()
    shape = native_report()
    _, _, memory, fields, _ = native_context('SIM_MFX_FETDRIVE')

    def default(field):
        return struct.unpack('<d', bytes(memory[field+i] for i in range(8)))[0]

    b, a, c = [row['default'] for row in checked['filter_coefficients']]
    mono, stereo = default(0x48), default(0x68)
    master, drive, dry, wet_gain, post = COEFFICIENTS
    ring, origin, rows = [0.0]*2048, 0, []

    def read(address):
        return ring[native_ring_index(address, 0, origin)]

    def write(address, value):
        ring[native_ring_index(address, 0, origin)] = value

    for frame in range(frames):
        inputs = (0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE),
                  0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE))
        mixed = native_stereo_mix(*inputs, mono=mono, stereo=stereo)
        for channel, sample in enumerate(mixed):
            write(fields[0x7c+8*channel]['address'], sample)
        for channel in range(2):
            sample = read(fields[0x7c+8*channel]['address'])
            shaped = native_shaped_store(sample, drive=drive, **shape['native_defaults'])['stored']
            write(fields[0x8c+8*channel]['address'], shaped)
            factor = min(1.0, max(-1.0, (2.0-shaped)/(shaped+2.0)))
            pairs = checked['history'][4*channel:4*channel+4]
            previous_input, previous_output = [read(pair['previous']['address']) for pair in pairs[:2]]
            write(pairs[0]['store']['address'], sample)
            write(fields[0x9c+8*channel]['address'], factor)
            allpass = previous_input + math.fma(-sample, factor, previous_output*factor)
            write(pairs[1]['store']['address'], allpass)
            previous_input, previous_output = [read(pair['previous']['address']) for pair in pairs[2:]]
            write(pairs[2]['store']['address'], allpass)
            filtered = allpass*b + math.fma(previous_input, a, previous_output*c)
            write(pairs[3]['store']['address'], filtered)
            write(fields[0xec+8*channel]['address'], filtered)
        for channel, sample in enumerate(inputs):
            wet = read(fields[0xec+8*channel]['address'])
            output = (math.fma(sample, dry, wet*wet_gain)*post)*master
            write(fields[0xfc+8*channel]['address'], output)
        output = tuple(read(fields[field]['address']) for field in (0xfc, 0x104))
        if not all(math.isfinite(value) for value in output):
            raise ValueError('FETDRIVE reference produced a non-finite sample')
        rows.append(output)
        origin = advance_native_origin(origin)
    return rows, dict(model='checked native FETDRIVE arithmetic with explicit cold ring',
                      native_callback_executed=False, bmc_instructions_executed=False,
                      hardware_timing_verified=False, constructor_filters_uncalibrated=True,
                      software_sample_rate=SAMPLE_RATE, wrapper_base=0, final_origin=origin,
                      live_coefficients=list(COEFFICIENTS), filter_coefficients=[b, a, c],
                      history=checked['history'], **metrics(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new WAV path')
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        samples, report = render_reference(args.frames)
        payload = pcm16(samples)
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
        print(json.dumps(report, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
