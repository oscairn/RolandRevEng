"""Original oscillator with packet-executed stereo gain and scratch output."""
import argparse
import hashlib
import json
from pathlib import Path
import wave

import bmc_allpass_oscillator as oscillator
from bmc_dsp import packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_tail_with_scratch
from line_shaping_study import _finite, _float32
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

TAIL_SPEC = dict(kind='dry_wet_tail_with_scratch', wet_addresses=[0x60, 0x70],
                 coefficient_slots=[2, 3, 4, 5], scratch_addresses=[0x90, 0x91])


def programs():
    return (*oscillator.programs(), assemble_tail_with_scratch(TAIL_SPEC))


def storage_program():
    """Convert the complete logical stream, including the unaligned slice boundary."""
    return swap_words(b''.join(programs()))


def render(frames, frequency, amplitude=0.25, gain=0.5):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    gain = _finite(gain)
    if not 0 <= gain <= 1:
        raise ValueError('Expected gain in 0..1')
    source_gain = _float32(gain)
    ring, coefficients, seed = oscillator.initialize(frequency, amplitude)
    coefficients.update({2: 0.0, 3: source_gain, 4: 1.0, 5: 1.0})
    fragments = programs()
    blocks = tuple(zip(fragments, (oscillator.SOURCES, oscillator.SOURCES, TAIL_SPEC['wet_addresses'])))
    rows, origin = [], 0
    for _ in range(frames):
        for program, sources in blocks:
            data = {cell: ring[native_ring_index(cell, 0, origin)] for cell in sources}
            result = execute_fragment(program, data, coefficients, oscillator.IO_ADDRESSES)
            for step in result['trace']:
                for cell, value in step['writes'].items():
                    ring[native_ring_index(cell, 0, origin)] = value
        rows.append((result['ports'][0], result['ports'][4]))
        origin = advance_native_origin(origin)
    logical = b''.join(fragments)
    return rows, dict(program_sha256=hashlib.sha256(logical).hexdigest(), program_bytes=len(logical),
                      total_packet_count=len(packets(logical)), **seed,
                      requested_gain=gain, source_gain=source_gain,
                      final_native_ring_origin=origin, origin_wraps=frames//2048,
                      program_format='logical big-endian BMC packet bytes',
                      software_sample_rate=SAMPLE_RATE, wrapper_base=0,
                      scratch_addresses=TAIL_SPEC['scratch_addresses'].copy(),
                      state_representation='native-policy binary64; hardware encoding unverified',
                      sine_evaluations_for_initialization=5,
                      hardware_execution_verified=False, full_engine_ready=False, **metrics(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new stereo WAV path')
    parser.add_argument('--frequency', type=float, default=440.0)
    parser.add_argument('--gain', type=float, default=0.5)
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        rows, result = render(args.frames, args.frequency, gain=args.gain)
        payload = pcm16(rows)
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
