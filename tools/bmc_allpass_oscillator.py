"""Original BMC feedback oscillator under the explicit native-ring convention."""
import argparse
import hashlib
import math
import json
from pathlib import Path
import wave

from bmc_emulator import execute_fragment
from bmc_subset import assemble_allpass, assemble_fragment
from line_shaping_study import _finite, _float32, quantize_native_reference
from line_state_study import advance_native_origin, native_ring_index
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16

PREFIX_SPEC = dict(kind='coefficient_shift4', input_addresses=[0x2016, 0x2017],
                   coefficient_slots=[0, 1], target=0x80)
ALLPASS_SPEC = dict(kind='allpass4', sources=[0x61, 0x21, 0x31, 0x80, 0x41, 0x51, 0x71],
                    targets=[0x20, 0x30, 0x40, 0x50, 0x60, 0x70])
SOURCES = ALLPASS_SPEC['sources']
RING_LENGTH, IO_ADDRESSES = 2048, {0x2016: 0.0, 0x2017: 0.0}


def programs():
    """Return the two static byte slices reused unchanged every frame."""
    return (assemble_fragment(PREFIX_SPEC), assemble_allpass(ALLPASS_SPEC))


def factor_for(frequency):
    frequency = _finite(frequency)
    if not 0.0 < frequency < SAMPLE_RATE / 2:
        raise ValueError('frequency must satisfy 0 < frequency < 24000')
    omega = 2.0 * math.pi * frequency / SAMPLE_RATE
    if not 0 < omega < math.pi or math.tan(omega/2) == 0:
        raise ValueError('Frequency cannot be represented by this factor profile')
    K = math.tan((2.0 * math.pi - omega) / 8.0) / math.tan(omega / 2.0)
    factor = (K - 1.0) / (K + 1.0)
    quantized = quantize_native_reference(_float32(factor / 16.0), shift_bits=4)['quantized']
    if not math.isfinite(quantized) or abs(quantized) >= 1.0:
        raise ValueError('quantized factor must stay inside the unit circle')
    return factor, quantized


def actual_omega(quantized):
    quantized = _finite(quantized)
    if not -1 < quantized < 1:
        raise ValueError('Expected a factor strictly inside (-1,1)')
    ratio = (1.0 + quantized) / (1.0 - quantized)
    low, high = 0.0, math.pi
    for _ in range(64):
        middle = (low + high) / 2.0
        if middle + 8.0 * math.atan(ratio * math.tan(middle / 2.0)) > 2.0 * math.pi:
            high = middle
        else:
            low = middle
    return (low + high) / 2.0


def render(frames, frequency, amplitude=0.25):
    """Run the two fragments per frame over the zero-initial native ring."""
    if type(frames) is not int or not 128 <= frames <= 1_000_000:
        raise ValueError('frames must be an int in 128..1000000')
    amplitude = _finite(amplitude)
    if not 0.0 <= amplitude <= 1.0:
        raise ValueError('amplitude must satisfy 0 <= amplitude <= 1')
    prefix, allpass = programs()
    factor, quantized = factor_for(frequency)
    omega = actual_omega(quantized)
    phase = -2.0 * math.atan(((1.0 + quantized) / (1.0 - quantized)) * math.tan(omega / 2.0))
    ring = [0.0] * RING_LENGTH
    ring[0x21] = amplitude * math.sin(-2.0 * omega)
    ring[0x31] = amplitude * math.sin(-2.0 * omega + phase)
    ring[0x41] = amplitude * math.sin(-2.0 * omega + 2.0 * phase)
    ring[0x51] = amplitude * math.sin(-2.0 * omega + 3.0 * phase)
    ring[0x61] = ring[0x71] = amplitude * math.sin(-omega)
    initial_data = {address: ring[address] for address in (0x21, 0x31, 0x41, 0x51, 0x61, 0x71)}
    coefficients = {0: 0.0, 1: factor / 16.0}
    samples, origin = [], 0
    for _ in range(frames):
        for program in (prefix, allpass):
            data = {a: ring[native_ring_index(a, 0, origin)] for a in SOURCES}
            result = execute_fragment(program, data, coefficients, IO_ADDRESSES)
            for step in result['trace']:
                for address, value in step['writes'].items():
                    ring[native_ring_index(address, 0, origin)] = value
        samples.append(result['ports'][0])
        origin = advance_native_origin(origin)
    return samples, dict(program_sha256=hashlib.sha256(prefix + allpass).hexdigest(),
                         program_bytes=len(prefix) + len(allpass), factor=factor,
                         quantized_factor=quantized, requested_frequency=frequency,
                         actual_frequency=omega * SAMPLE_RATE / (2.0 * math.pi),
                         final_native_ring_origin=origin,
                         origin_wraps=frames // RING_LENGTH,
                         program_format='logical big-endian BMC packet bytes',
                         software_sample_rate=SAMPLE_RATE, wrapper_base=0,
                         initial_data=initial_data, coefficients=coefficients,
                         state_representation='native-policy binary64; hardware encoding unverified',
                         sine_evaluations_for_initialization=5,
                         hardware_execution_verified=False, full_engine_ready=False,
                         **metrics([(sample,) for sample in samples]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new mono WAV path')
    parser.add_argument('--frequency', type=float, default=440.0)
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output')
        samples, report = render(args.frames, args.frequency)
        payload = pcm16([(sample,) for sample in samples])
        with args.output.open('xb') as stream, wave.open(stream, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(payload)
        print(json.dumps(report, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
