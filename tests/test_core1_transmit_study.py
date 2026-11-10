import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from core1_transmit_study import report,ring_metrics


class RingTests(unittest.TestCase):
    def test_all_quiescent_states_reserve_one_slot(self):
        for write in range(64):
            for read in range(64):
                metrics=ring_metrics(write,read)
                self.assertEqual(metrics['usable_free']+metrics['used'],63)
                self.assertEqual(metrics['reported_free'],metrics['usable_free']+1)
                self.assertEqual(metrics['enqueue_allowed'],metrics['usable_free']>0)
        self.assertEqual(ring_metrics(0,63)['used'],1)
        self.assertEqual(ring_metrics(63,0)['reported_free'],1)
        self.assertFalse(ring_metrics(63,0)['enqueue_allowed'])
        for bad in (-1,64,1.5):
            with self.assertRaises(ValueError):ring_metrics(bad,0)

    @unittest.skipUnless(importlib.util.find_spec('capstone'),'Capstone required')
    def test_unsupported_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'digest'):
            report(SimpleNamespace(data=b'authored non-firmware data'))


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                     'Recorded CORE1 and Capstone required')
class CorpusTests(unittest.TestCase):
    def test_outbound_reply_and_bounded_backpressure_contract(self):
        from core1 import Core1
        result=report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(result['shared']['usable_slots'],63)
        self.assertEqual(result['software']['usable_slots'],511)
        self.assertEqual(result['output_task']['irq'],230)
        self.assertEqual(result['output_task']['priority_byte'],0x90)
        self.assertEqual(len(result['retry_loops']),4)
        self.assertEqual(result['reply_word_type'],3)
        self.assertFalse(result['external_peer_proven'])
        self.assertFalse(result['execution_ready'])


if __name__=='__main__':unittest.main()
