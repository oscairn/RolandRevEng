import importlib.util
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from fetdrive_quantizer_study import BIAS, SLOPE, fantom_report, native_shaped_store
from render_fetdrive_window import boundary_probes, predict_channel, render, write_wav


CONTEXT = dict(scale=1/256, affine_literals=[[0.25, 0.5], [0.125, 0.25]], post_gain=[0.5, 0.25])


class WindowTests(unittest.TestCase):
    def test_stock_shaped_hypothesis_distinguishes_truncation_and_clamp(self):
        probes = {item['mixed_input']: item for item in boundary_probes(CONTEXT, 1/512)}
        for sign in (-1, 1):
            half_bin = probes[sign * 2**-24]
            self.assertEqual(half_bin['gain_only'], sign * 2**-24)
            self.assertEqual(half_bin['quantized'], 0)
            self.assertEqual(probes[sign * 2**-23]['quantized'], sign * 2**-23)
            below = probes[sign * (1 - 2**-23)]
            above = probes[sign * (1 + 2**-23)]
            self.assertEqual(below['clipped'], sign * (1 - 2**-23))
            self.assertEqual(above['clipped'], sign)
            self.assertEqual(above['stored'], probes[float(sign)]['stored'])
        self.assertEqual(predict_channel(0.5, 1/512, [0.25, 0.5], 0.5)['stored'], 0.1953125)

    def test_native_values_agree_under_same_coefficients(self):
        for sample in (0, 2**-24, 2**-23, -0.5, 0.999999, -1.25, 1.25):
            native = native_shaped_store(sample, drive=0.5, scale=1/256, post_gain=0.5)
            model = predict_channel(sample, 1/512, [SLOPE, BIAS], 0.5)
            self.assertEqual({key: model[key] for key in native}, native)

    def test_wav_contains_first_stores_and_preserves_existing_output(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary)/'stores.wav'
            info = write_wav(output, CONTEXT, 128)
            self.assertFalse(info['whole_dsp_program_executed'])
            self.assertFalse(info['hardware_execution_verified'])
            with wave.open(str(output), 'rb') as wav:
                self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getnframes()), (2, 48000, 128))
            with self.assertRaises(FileExistsError):
                write_wav(output, CONTEXT, 128)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                     'Recorded Fantom image required')
class CorpusTests(unittest.TestCase):
    def test_five_stock_placements_predict_equal_samples(self):
        from core1 import Core1

        contexts = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        expected, _ = render(contexts[0], 128)
        for context in contexts:
            rows, info = render(context, 128)
            self.assertEqual(rows, expected)
            self.assertEqual(info['gain'], 1/512)
            self.assertEqual(info['placement']['targets'], [source + 2 for source in context['sources']])
