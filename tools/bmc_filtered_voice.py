"""Original packet-executed oscillator, gain and stereo lowpass filter voice."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

import bmc_allpass_oscillator as oscillator
import bmc_allpass_voice as voice
from bmc_dsp import packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment
from fdrv_filter_study import filter_spec, stability
from line_shaping_study import _finite, _float32
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

FILTER_SPEC = filter_spec()
FILTER_SPEC['sources'][0], FILTER_SPEC['sources'][3] = voice.TAIL_SPEC['scratch_addresses']
# Final prefetches consume cells already written by the oscillator.
FILTER_SPEC['sources'][6:] = [0x20, 0x30, 0x40, 0x50]
FILTER_SPEC['coefficient_slots'] = [6, 7, 8, 9, 10]
FILTER_SEEDS = sorted(FILTER_SPEC['sources'][index] for index in (1, 2, 4, 5))
CUBIC_SPEC = dict(kind='cubic_quad', sources=[0x60, 0x90, 0x70, 0x91],
                  targets=[0x92, 0x93, 0x94, 0x95])


def design_lowpass(cutoff, damping=math.sqrt(2)):
    """Design [a,b,c,d,e] for the admitted native SVF; no firmware execution."""
    cutoff = _finite(cutoff)
    damping = _finite(damping)
    if not 0 < cutoff < SAMPLE_RATE/2:
        raise ValueError('Expected 0 < cutoff < %d' % (SAMPLE_RATE // 2))
    if damping <= 0:
        raise ValueError('Expected damping > 0')
    g0 = 2 * math.sin(math.pi * cutoff / SAMPLE_RATE)
    a = _float32(g0 - 1)
    b = _float32(-damping)
    check = stability(a, b)
    g, q = check['g'], check['damping']
    if not check['stable'] or g <= 0 or q <= 0:
        raise ValueError('Unstable admitted-SVF pole pair for cutoff/damping')
    coefs = [a, b, 1.0, _float32(-q / 2), _float32(q * g / 2 - 1)]
    return dict(coefficients=coefs, nominal_cutoff=cutoff,
                requested_damping=damping, sample_rate=SAMPLE_RATE,
                stability=check, hardware_calibrated=False)


def programs(waveshape=False):
    if type(waveshape) is not bool:
        raise ValueError('Expected a boolean waveshape option')
    if not waveshape:
        return (*voice.programs(), assemble_fragment(FILTER_SPEC))
    spec = dict(FILTER_SPEC, sources=FILTER_SPEC['sources'].copy())
    spec['sources'][0], spec['sources'][3] = CUBIC_SPEC['targets'][1::2]
    return (*voice.programs(), assemble_fragment(CUBIC_SPEC), assemble_fragment(spec))


def storage_program(waveshape=False):
    logical = b''.join(programs(waveshape))
    return swap_words(logical+bytes(-len(logical) % 4))


def initialize(frequency, amplitude=.25, gain=.5, cutoff=1000, damping=math.sqrt(2), waveshape=False):
    if type(waveshape) is not bool:
        raise ValueError('Expected a boolean waveshape option')
    if waveshape and not 0 <= _finite(amplitude) <= .5:
        raise ValueError('Waveshaping requires amplitude in 0..0.5 to retain input headroom')
    gain = _finite(gain)
    if not 0 <= gain <= 1:
        raise ValueError('Expected gain in 0..1')
    design = design_lowpass(cutoff, damping)
    ring, coefficients, seed = oscillator.initialize(frequency, amplitude)
    coefficients.update({2: 0.0, 3: _float32(gain), 4: 1.0, 5: 1.0})
    coefficients.update(zip(FILTER_SPEC['coefficient_slots'], design['coefficients'], strict=True))
    for cell in FILTER_SEEDS:
        ring[cell] = 0.0
        seed['initial_data'][cell] = 0.0
    seed['filter_design'] = design
    return ring, coefficients, seed


def render(frames, frequency, amplitude=.25, gain=.5, cutoff=1000, damping=math.sqrt(2), waveshape=False):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    ring, coefficients, seed = initialize(frequency, amplitude, gain, cutoff, damping, waveshape)
    fragments = programs(waveshape)
    specs = [disassemble_fragment(fragment) for fragment in fragments]
    rows, origin = [], 0
    for _ in range(frames):
        for fragment, spec in zip(fragments, specs, strict=True):
            sources = spec.get('sources', spec.get('wet_addresses', []))
            data = {cell: ring[native_ring_index(cell, 0, origin)] for cell in sources}
            result = execute_fragment(fragment, data, coefficients, oscillator.IO_ADDRESSES)
            for step in result['trace']:
                for cell, value in step['writes'].items():
                    ring[native_ring_index(cell, 0, origin)] = value
        rows.append((result['ports'][0], result['ports'][4]))
        origin = advance_native_origin(origin)
    logical = b''.join(fragments)
    return rows, dict(program_sha256=hashlib.sha256(logical).hexdigest(), program_bytes=len(logical),
                      stored_bytes=(len(logical)+3)&~3, waveshape=waveshape,
                      total_packet_count=len(packets(logical)), **seed,
                      requested_gain=_finite(gain), source_gain=coefficients[3],
                      final_native_ring_origin=origin, origin_wraps=frames//2048,
                      program_format='logical big-endian BMC packet bytes',
                      software_sample_rate=SAMPLE_RATE, wrapper_base=0,
                      oscillator_seed_sine_evaluations=5, filter_design_sine_evaluations=1,
                      state_representation='native-policy binary64; hardware encoding unverified',
                      hardware_execution_verified=False, full_engine_ready=False, **metrics(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new stereo WAV path')
    parser.add_argument('--frequency', type=float, default=440)
    parser.add_argument('--gain', type=float, default=.5)
    parser.add_argument('--cutoff', type=float, default=1000)
    parser.add_argument('--damping', type=float, default=math.sqrt(2))
    parser.add_argument('--waveshape', action='store_true', help='Shape the oscillator before the filter')
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        rows, result = render(args.frames, args.frequency, gain=args.gain,
                              cutoff=args.cutoff, damping=args.damping, waveshape=args.waveshape)
        payload = pcm16(rows)
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
