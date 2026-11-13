import json
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from host_status9_study import (GATE_DISABLE, GATE_ENABLE, RING_STORE,
                                capture_census, static_anchors, text_rows)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HOST = CORPUS / 'mi078'
CAPTURES = CORPUS / 'fantom-unit-2026-11-12' / 'link-and-panel-captures'
HAS_HOST = HOST.exists() and all(find_spec(m) for m in ('capstone', 'elftools'))
HAS_CAPTURES = CAPTURES.exists()


@unittest.skipUnless(HAS_HOST, 'Pinned mi078 host corpus and ELF/Capstone readers required')
class Selector9DispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static = static_anchors(HOST)

    def test_input_worker_dispatches_selector9_to_ring_store(self):
        # Kind 9 arrives in the input worker; byte 3 selects the service.
        # Selector 9 path: payload getter then the ring store with the ring
        # object; the documented sibling selectors stay as recorded.
        static = self.static['anchors']
        self.assertEqual(static[0xbe1b18], 'cmp w0, #9')
        self.assertEqual(static[0xbe1b24], 'bl #0xbe3688')
        self.assertEqual(static[0xbe1b34], 'bl #0x6c3070')

    def test_ring_store_is_a_gated_two_slot_112_byte_copy(self):
        # 0x6c3070 toggles the cursor at 0x40a975c and copies seven 16-byte
        # pairs (112 bytes) into slot 0x40a9760 + 112*new_cursor.
        static = self.static['anchors']
        self.assertEqual(static[0x6c3074], 'add x2, x2, #0x758')
        self.assertEqual(static[0x6c3084], 'ldr w0, [x2, #4]')
        self.assertEqual(static[0x6c3090], 'str w3, [x2, #4]')
        rows = text_rows(HOST)
        store = [ins for ins in rows if 0x6c3070 <= ins.address <= 0x6c30d4]
        self.assertEqual(sum(1 for i in store if i.mnemonic == 'ldp'), 7)
        self.assertEqual(sum(1 for i in store if i.mnemonic == 'stp'), 7)

    def test_gate_and_reader_anchors(self):
        # Enable/disable write the gate byte at 0x40a9758; readers return -60
        # with the gate clear and read slot halfwords otherwise.
        static = self.static['anchors']
        self.assertEqual(static[0x6c27e0], 'strb w1, [x0, #0x758]')
        self.assertEqual(static[0x6c27ec], 'strb wzr, [x0, #0x758]')
        self.assertEqual(static[0x6c2800], 'mov w0, #-0x3c')
        self.assertEqual(static[0x6c2a8c], 'ldrsh w0, [x1, #0x5c]')
        callers = self.static['callers']
        self.assertEqual(len(callers[f'{GATE_ENABLE:#x}']), 11)
        self.assertEqual(len(callers[f'{GATE_DISABLE:#x}']), 15)
        self.assertIn(f'{RING_STORE:#x}', callers)
        self.assertEqual(callers[f'{RING_STORE:#x}'], ['0xbe1b34'])


@unittest.skipUnless(HOST.exists() and HAS_CAPTURES and find_spec('capstone'),
                     'Pinned mi078 and saved unit captures required')
class CaptureCensusTests(unittest.TestCase):
    def test_all_captured_kind9_frames_are_e1_to_60_selector9_112_bytes(self):
        # Measured: long kind-9 status frames from 0xE1 to 0x60, sub-type 9,
        # 112-byte payload, present in every app-stopped capture.
        census = capture_census(CAPTURES)
        self.assertEqual(set(census), {'gs0-keys-app-stopped.bin',
                                       'gs0-local-off.bin', 'gs0-local-sent.bin',
                                       'gs0-panel-app-stopped.bin'})
        for name, row in census.items():
            self.assertGreater(row['kind9'], 0, name)
            self.assertEqual(row['shapes'], [(225, 96, 9)], name)
            self.assertEqual(row['payload_lengths'], [112], name)
        # The keys capture carries key activity; the sent/panel captures do not.
        varying = {name: tuple(row['varying_payload_offsets'])
                   for name, row in census.items()}
        self.assertEqual(len(varying['gs0-local-sent.bin']), 0)
        self.assertIn(92, varying['gs0-keys-app-stopped.bin'])
        self.assertIn(108, varying['gs0-keys-app-stopped.bin'])
        self.assertIn(92, varying['gs0-local-off.bin'])

    def test_census_shape_matches_static_selector(self):
        # The captured selector byte 9 is exactly the dispatch branch verified
        # statically; the census numbers are recorded for the study note.
        census = capture_census(CAPTURES)
        self.assertEqual(census['gs0-keys-app-stopped.bin']['kind9'], 181)
        self.assertEqual(census['gs0-local-off.bin']['kind9'], 180)
        self.assertEqual(census['gs0-local-sent.bin']['kind9'], 220)
        self.assertEqual(census['gs0-panel-app-stopped.bin']['kind9'], 160)


if __name__ == '__main__':
    unittest.main()