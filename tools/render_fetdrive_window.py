"""Render an experimental prediction of the first FETDRIVE stores from stock bytes."""
import argparse
import json
import math
from pathlib import Path
import wave

from fetdrive_quantizer_study import fantom_report
from line_shaping_study import EPSILON, _finite, _float32, quantize_native_reference
from render_fragment_demo import SAMPLE_RATE, metrics, pcm16


def predict_channel(mixed, gain, affine_literals, post_gain):
    """Apply the bounded packet hypothesis under the native numeric policy."""
    # shortcut: use native numeric behavior until isolated hardware results are available.
    slope, bias = affine_literals
    prequantized = _finite(_finite(mixed) * gain)
    quantizer = quantize_native_reference(prequantized)
    clipped = min(1.0, max(-1.0, quantizer['quantized']))
    affine = math.fma(clipped, slope, bias)
    square = affine * affine
    return dict(prequantized=prequantized, **quantizer, clipped=clipped, affine=affine,
                square=square, stored=_finite(square * post_gain))


def boundary_probes(context, gain):
    """Test sub-bin signals and both sides of the clip with the decoded literals."""
    if gain == 0:
        return []
    thresholds = (EPSILON/2, EPSILON, 2 ** -9 - EPSILON, 2 ** -9, 2 ** -9 + EPSILON)
    probes = []
    for polarity in (-1, 1):
        for threshold in thresholds:
            sample = polarity * threshold / gain
            result = predict_channel(sample, gain, context['affine_literals'][0], context['post_gain'][0])
            probes.append(dict(mixed_input=sample, gain_only=result['prequantized'] * 512, **result))
    return probes


def render(context, frames, *, drive=0.5):
    if not hasattr(math, 'fma'):
        raise ValueError('This renderer requires Python 3.13+ math.fma')
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 frames')
    live_drive = _float32(drive)
    gain = _finite(context['scale'] * live_drive)
    rows = []
    for frame in range(frames):
        mixed = (1.25 * math.sin(2 * math.pi * 220 * frame / SAMPLE_RATE),
                 0.9 * math.sin(2 * math.pi * 330 * frame / SAMPLE_RATE))
        rows.append(tuple(predict_channel(sample, gain, affine, post)['stored']
                          for sample, affine, post in zip(mixed, context['affine_literals'],
                                                          context['post_gain'], strict=True)))
    report = dict(model='experimental stock FETDRIVE window through its first data stores',
                  hardware_execution_verified=False, whole_dsp_program_executed=False,
                  software_sample_rate=SAMPLE_RATE, live_drive=live_drive, gain=gain,
                  placement=context, boundary_probes=boundary_probes(context, gain), **metrics(rows))
    return rows, report


def write_wav(output, context, frames, *, drive=0.5):
    if output.exists():
        raise FileExistsError('Refusing to replace an existing output')
    rows, report = render(context, frames, drive=drive)
    samples = pcm16(rows)
    with output.open('xb') as stream, wave.open(stream, 'wb') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core1', type=Path, help='Pinned Fantom bmc0 CORE1 image')
    parser.add_argument('output', type=Path, help='New WAV path')
    parser.add_argument('--base', type=lambda value: int(value, 0), default=0x4020)
    parser.add_argument('--frames', type=int, default=12000)
    parser.add_argument('--drive', type=float, default=0.5)
    args = parser.parse_args()
    try:
        from core1 import Core1

        contexts = {row['base']: row for row in fantom_report(Core1(args.core1))}
        if args.base not in contexts:
            raise ValueError('Unknown stock FETDRIVE placement')
        print(json.dumps(write_wav(args.output, contexts[args.base], args.frames, drive=args.drive),
                         indent=2, allow_nan=False))
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(2, f'{error}\n')
