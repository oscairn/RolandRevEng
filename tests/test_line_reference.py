import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from render_fragment_demo import SAMPLE_RATE
from render_line_reference import PARAMETERS, render_reference, write_reference


class ReferencePipelineTests(unittest.TestCase):
    def test_ring_pipeline_matches_direct_delays_through_origin_wrap(self):
        from line_shaping_study import native_channel_reference
        rows, info = render_reference(2056)
        histories, previous_q, expected = [[0.0]*5, [0.0]*5], [0.0, 0.0], []
        for frame in range(2056):
            inputs = [0.1*math.sin(2*math.pi*220*frame/SAMPLE_RATE),
                      0.08*math.sin(2*math.pi*330*frame/SAMPLE_RATE)]
            output = []
            for channel, value in enumerate(inputs):
                reference = native_channel_reference(value, history=previous_q[channel], **PARAMETERS)
                previous_q[channel] = reference['smoothed']
                k = reference['factor']
                h0, h1, h2, h3, h4 = histories[channel]
                y0 = h0 + (h1-value)*k
                y1 = h1 + (h2-y0)*k
                y2 = h2 + (h3-y1)*k
                y3 = h3 + (h4-y2)*k
                histories[channel] = [value, y0, y1, y2, y3]
                output.append(value*0.5 + y3*0.5)
            expected.append(tuple(output))
        self.assertEqual(rows, expected)
        self.assertEqual(info['final_origin'], 8)
        self.assertEqual(info['origin_steps'], 2056)
        self.assertLess(info['factor_peak'], 1)
        self.assertFalse(info['whole_dsp_program_executed'])
        self.assertFalse(info['hardware_timing_verified'])
        json.dumps(info, allow_nan=False)
        info['parameters']['mode'] = 999
        self.assertEqual(PARAMETERS['mode'], 0.5)

    def test_wav_export_refuses_existing_data_and_invalid_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'reference.wav'
            for count in (True, 127, 1000001, '256'):
                with self.subTest(count=count), self.assertRaises(ValueError):
                    write_reference(output, count)
                self.assertFalse(output.exists())
            info = write_reference(output, 256)
            with wave.open(str(output), 'rb') as wav:
                self.assertEqual((wav.getnframes(), wav.getnchannels(), wav.getsampwidth(), wav.getframerate()),
                                 (256, 2, 2, SAMPLE_RATE))
                self.assertEqual(len(wav.readframes(257)), 1024)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_reference(output, 256)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(info['frames'], 256)

    def test_native_mix_changes_wet_input_only(self):
        from line_shaping_study import native_stereo_mix

        self.assertEqual(native_stereo_mix(2, -3, mono=0.5, stereo=0.25), (0, -1.25))
        rows, info = render_reference(128, mono=0, stereo=0)
        expected = [(0.05*math.sin(2*math.pi*220*i/SAMPLE_RATE),
                     0.04*math.sin(2*math.pi*330*i/SAMPLE_RATE)) for i in range(128)]
        self.assertEqual(rows, expected)
        self.assertEqual(info['native_mix'], dict(mono=0, stereo=0))
        self.assertEqual(info['factor_peak'], 0)
        with self.assertRaises(ValueError):
            native_stereo_mix(1, 2, mono=float('nan'), stereo=1)


if __name__ == '__main__':
    unittest.main()
