from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_dsp import assemble, swap_words
from quantizer_context_inventory import scan


class QuantizerContextTests(unittest.TestCase):
    def test_controls_are_distinguished_from_payload_and_neighbor(self):
        stream = assemble([[0x0c03, 0x0fe0, 0x9c59], [0x0a02, 0x9c59], [0x0a02, 0x9ed9],
                           [0x0a02, 0x9c59]])
        stored = swap_words(stream.ljust(20, b'\0'))
        report = scan(stored, [(0x1000, (0x20, len(stream), len(stored), 0))])
        self.assertEqual(report['counts'], dict(framed_segments=1, framed_packets=4))
        first, last = report['matches']
        self.assertEqual((first['offset'], first['following']), (6, [0x0a02, 0x9ed9]))
        self.assertEqual((last['offset'], last['following']), (14, None))
