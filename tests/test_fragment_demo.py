import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from render_fragment_demo import build_demo, pcm16


class PcmTests(unittest.TestCase):
    def test_explicit_quantization_and_channel_validation(self):
        self.assertEqual(struct.unpack('<4h', pcm16([(-1.0, 1.0), (0.0, 0.5)])),
                         (-32767, 32767, 0, 16384))
        for rows in ([], [()], [(0, 0, 0)], [(0,), (0, 1)], [(True,)],
                     [(float('nan'),)], [(float('inf'),)], [(1.0001,)], [(10**500,)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                pcm16(rows)

    def test_existing_directory_and_invalid_counts_preserve_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'keep'; output.mkdir()
            sentinel = output / 'allpass-impulse.wav'; sentinel.write_bytes(b'user data')
            with self.assertRaises(FileExistsError):build_demo(output, 128)
            self.assertEqual(sentinel.read_bytes(), b'user data')
            for bad in (-1, 127, 1000001, True):
                with self.assertRaises(ValueError):build_demo(Path(temporary) / 'new', bad)
            self.assertFalse((Path(temporary) / 'new').exists())


class RenderTests(unittest.TestCase):
    def test_original_signals_render_and_independent_contracts_hold(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'rendered'
            result = build_demo(output, 256)
            self.assertLess(result['allpass']['impulse_energy_error'], 1e-10)
            self.assertLess(result['dry_wet']['reference_max_abs_error'], 1e-12)
            self.assertFalse(result['hardware_timing_verified'])
            for name, channels in [('allpass-impulse.wav', 1), ('dry-wet-tones.wav', 2)]:
                with wave.open(str(output / name), 'rb') as wav:
                    self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getsampwidth(), wav.getframerate()),
                                     (256, channels, 2, 48000))
                    self.assertEqual(len(wav.readframes(256)), 256 * channels * 2)
            self.assertEqual(json.loads((output / 'summary.json').read_text()), result)


if __name__ == '__main__':unittest.main()
