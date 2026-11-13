from importlib.util import find_spec
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from host_byte1_study import ROUTE, stamps, scan, summarize

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_HOST = (CORPUS / 'mi078').exists() and all(find_spec(m) for m in ('capstone', 'elftools'))


@unittest.skipUnless(HAS_HOST, 'Pinned mi078 host corpus and ELF/Capstone readers required')
class RouteByte1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites = scan(CORPUS / 'mi078')

    def test_pinned_image_route_call_population(self):
        self.assertEqual(len(self.sites), 391)
        self.assertTrue(all(s['dispatcher'] in (0xbe4270, 0xbe4418) for s in self.sites))
        self.assertEqual(summarize(self.sites)[0]['sites'], 76)

    def test_settings_and_lamp_routes_leave_byte1_at_constructor_default(self):
        # Wire: every measured kind-7/8 frame to 0xEF and kind-6 lamp word to 0x75
        # carried byte1 0x00. Static: 45 of 46 sites to 0xEF and all 11 to 0x75
        # store no immediate into message byte 1; the single 0xEF stamp is 0x60.
        self.assertEqual(stamps(self.sites, 0xef), [0x60])
        existing = [s for s in self.sites if s['dispatcher'] != ROUTE]
        self.assertEqual(existing, [])
        ef = [s for s in self.sites if s['route'] == 0xef]
        self.assertEqual(len(ef), 46)
        self.assertEqual(sum(1 for s in ef if s['byte1']), 1)
        self.assertEqual([s['call'] for s in ef if s['byte1']], [0x8d58b0])
        lamps = [s for s in self.sites if s['route'] == 0x75]
        self.assertEqual(len(lamps), 11)
        self.assertEqual([s['byte1'] for s in lamps], [None] * 11)

    def test_engine_route_stamps_are_call_site_data(self):
        # 99 of 123 calls to 0xE1 stamp byte 1 with 0x60/0x62/0x63/0x64; the rest
        # leave the constructor default 0, matching the measured byte1=0 frames.
        engine = [s for s in self.sites if s['route'] == 0xe1]
        self.assertEqual(len(engine), 123)
        self.assertEqual(stamps(self.sites, 0xe1), [0x60, 0x62, 0x63, 0x64])
        stamped = sum(1 for s in engine if s['byte1'] and s['byte1']['value'] is not None)
        self.assertEqual(stamped, 99)

    def test_cited_sites_match_their_documented_instructions(self):
        # 00c2a3c0 control-change constructor: byte1 0x60, route 0xe1 then 0x0a.
        cited = {s['call']: s for s in self.sites}
        self.assertEqual(cited[0xc2a40c]['route'], 0xe1)
        self.assertEqual(cited[0xc2a40c]['byte1'], dict(at=0xc2a408, value=0x60))
        self.assertEqual(cited[0xc2a454]['route'], 0x8)
        # 00c2c9c4 kind-3 MIDI fanout forwards an externally built message to
        # 0xE1 with no byte-1 store: the measured 0f f8 clock frames' shape.
        self.assertEqual(cited[0xc2c9c4]['route'], 0xe1)
        self.assertIsNone(cited[0xc2c9c4]['byte1'])
        # 00cf9a44 version client queues directly (byte1 0x6f), not via 00be4270.
        self.assertNotIn(0xcf9a44, cited)


if __name__ == '__main__':
    unittest.main()