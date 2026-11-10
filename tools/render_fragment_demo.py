"""Render original signals through the strict offline fragment interpreter; no device IO."""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import struct
import time
import wave

from bmc_subset import assemble_allpass, assemble_tail

SAMPLE_RATE = 48000  # Software output grid, not a measurement of DSP timing.


def pcm16(rows):
    """Explicit symmetric PCM quantization; refuse non-finite values and clipping."""
    if not rows or len(rows[0]) not in (1, 2):
        raise ValueError('Expected nonempty mono or stereo frames')
    channels = len(rows[0])
    values = []
    for row in rows:
        if len(row) != channels:
            raise ValueError('Inconsistent channel count')
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError('PCM value is not a real number')
            try:
                value = float(value)
            except OverflowError as error:
                raise ValueError('PCM value exceeds the finite range') from error
            if not math.isfinite(value) or abs(value) > 1:
                raise ValueError('PCM value is non-finite or would clip')
            values.append(round(value * 32767))
    return struct.pack('<' + str(len(values)) + 'h', *values)


def metrics(rows):
    energy = math.fsum(value * value for row in rows for value in row)
    count = len(rows) * len(rows[0])
    return dict(frames=len(rows), channels=len(rows[0]),
                peak=max(abs(value) for row in rows for value in row),
                energy=energy, rms=math.sqrt(energy / count))


def render_allpass(frames):
    from bmc_emulator import execute_fragment
    spec = dict(kind='allpass4', sources=list(range(7)), targets=list(range(7, 13)))
    program = assemble_allpass(spec)
    history = [0.0] * 5
    rows = []
    for index in range(frames):
        value = 0.5 if index == 0 else 0.0
        data = dict(enumerate([value, history[0], history[1], 0.4,
                               history[2], history[3], history[4]]))
        result = execute_fragment(program, data, {})
        state = result['data']
        history = [state[address] for address in (7, 8, 9, 10, 11)]
        rows.append((state[11],))
    measured = metrics(rows)
    error = abs(measured['energy'] - 0.25)
    if error > 1e-10:
        raise ValueError('Allpass impulse energy differs from the independent unit-magnitude contract')
    return rows, dict(program_sha256=hashlib.sha256(program).hexdigest(),
                      factor=0.4, impulse_energy_error=error, **measured)


def render_mix(frames):
    from bmc_emulator import execute_fragment
    spec = dict(kind='dry_wet_tail', wet_addresses=[32, 33], coefficient_slots=[0, 1, 2, 3])
    program = assemble_tail(spec)
    coefficients = {0: 0.75, 1: 0.25, 2: 0.8, 3: 0.9}
    left_delay, right_delay = deque([0.0] * 11), deque([0.0] * 17)
    rows, largest_error = [], 0.0
    for index in range(frames):
        left = 0.25 * math.sin(2 * math.pi * 220 * index / SAMPLE_RATE)
        right = 0.2 * math.sin(2 * math.pi * 330 * index / SAMPLE_RATE)
        wet_left, wet_right = left_delay.popleft(), right_delay.popleft()
        left_delay.append(left); right_delay.append(right)
        result = execute_fragment(program, {32: wet_left, 33: wet_right}, coefficients,
                                  {0x2016: left, 0x2017: right})
        actual = result['ports'][0], result['ports'][4]
        expected = ((left * 0.75 + wet_left * 0.25) * 0.8 * 0.9,
                    (right * 0.75 + wet_right * 0.25) * 0.8 * 0.9)
        if any(value is None for value in actual):
            raise ValueError('Interpreter did not produce both main values')
        error = max(abs(a - b) for a, b in zip(actual, expected))
        largest_error = max(largest_error, error)
        if error > 1e-12:
            raise ValueError('Dry/wet result differs from the independent reference equation')
        rows.append(actual)
    return rows, dict(program_sha256=hashlib.sha256(program).hexdigest(),
                      reference_max_abs_error=largest_error, **metrics(rows))


def build_demo(output, frames=12000):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    output = Path(output)
    if output.exists():
        raise FileExistsError('Refusing to replace an existing output directory')
    started = time.perf_counter()
    allpass, allpass_info = render_allpass(frames)
    mixed, mix_info = render_mix(frames)
    encoded = [('allpass-impulse.wav', allpass, pcm16(allpass)),
               ('dry-wet-tones.wav', mixed, pcm16(mixed))]
    result = dict(model='strict floating-point fragment interpreter', sample_rate=SAMPLE_RATE,
                  software_grid_only=True, hardware_timing_verified=False,
                  allpass=allpass_info, dry_wet=mix_info,
                  render_seconds=time.perf_counter() - started)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows, payload in encoded:
        with (output / name).open('xb') as stream:
            with wave.open(stream, 'wb') as wav:
                wav.setnchannels(len(rows[0])); wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE); wav.writeframes(payload)
    with (output / 'summary.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='A new directory for two WAV files and their validation summary')
    parser.add_argument('--frames', type=int, default=12000)
    args = parser.parse_args()
    try:
        print(json.dumps(build_demo(args.output, args.frames), indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
