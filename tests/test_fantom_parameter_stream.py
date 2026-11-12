import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_parameter_stream_study import StreamOracle,parameter_words,checked_cursor,report


class ModelTests(unittest.TestCase):
    def test_exact_words_terminal_full_group_and_all_terminal_sizes(self):
        self.assertEqual(parameter_words(0,[(2,1),(3,1000)]),[0x00008434,0x01001234,0x03e80037])
        for changes,tag,count in (([],0x36,2),([(2,1)],0x35,3),([(2,1),(3,1000)],0x37,3)):
            for part in range(3):
                words=parameter_words(part,changes)
                self.assertEqual(len(words),count);self.assertEqual(words[-1]&255,tag)
                self.assertTrue(all(w&255==0x34 for w in words[:-1]))
                self.assertEqual((words[0]>>16)&255,part)
                self.assertTrue(all(w&0xf0==0x30 for w in words))

    def test_data_octets_and_empty_ring_wrap_cursor_bounds(self):
        self.assertEqual(parameter_words(0,[(3,65535)]),[0x00008434,0xff001334,0x0000ff35])
        for cursor in (0,2046,2047):self.assertEqual(checked_cursor(cursor),cursor)

    def test_bad_part_fields_blocks_or_cursor_fail_before_cpu(self):
        class IntSubclass(int):pass
        for part in (-1,3,True,0.,IntSubclass(0)):
            self.assertRaises(ValueError,parameter_words,part,[])
        for changes in ([(0,1)],[(2,1),(2,2)],[(3,1),(2,2)],[(2,True)]):
            self.assertRaises(ValueError,parameter_words,0,changes)
        for cursor in (-1,2048,True,0.):self.assertRaises(ValueError,checked_cursor,cursor)
        oracle=object.__new__(StreamOracle)
        self.assertRaises(ValueError,oracle.stream_controls,[0]*22,[],cursor=2048)
        self.assertRaises(ValueError,oracle.stream_controls,[0]*22,[],index=0)
        self.assertRaises(ValueError,oracle.stream_controls,[0]*22,[(0,1)])


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_prmedit_binding_asgn_selector_and_source_identity(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['edit_rtti'],'CUMDWRxPRMEdit')
        self.assertEqual(r['assignment_irq'],233)
        self.assertEqual(r['stream_selector'],0x84)
        self.assertTrue(r['rxdt_kind3_forward_edge_source_checked'])
        self.assertTrue(r['receive_path_passes_serialization_false'])
        self.assertFalse(r['global_serialization_flag_required'])
        self.assertFalse(r['full_rxdt_or_ingress_irq_executed'])
        self.assertEqual(r['scalar_adapter_rtti'],'CEZSNDTonePrmSFSub')
        self.assertFalse(r['global_serialization_flag_runtime_proved'])
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core);self.assertRaises(ValueError,StreamOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and private-RAM JIT permission required')
    def test_original_queue_reassembly_block_write_and_efct_route(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_parameter_stream_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=180)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_stream_route_cases'],576)
        self.assertEqual(r['stream_coefficient_writes'],2160)
        self.assertEqual(r['incoming_assignment_words'],1584)
        self.assertEqual(r['stream_notifications'],864)
        self.assertEqual(r['assignment_wrap_cursors'],[0,2047])
        self.assertTrue(r['original_assignment_queue_and_receiver_executed'])
        self.assertTrue(r['incoming_input_storage_overwritten_before_consume'])
        self.assertEqual(r['serialization_flag_canary'],0x80)
        self.assertEqual(r['all_ones_cutoff_normalized'],3740)
        self.assertFalse(r['task_arrivals_or_preemption_observed'])
        self.assertFalse(r['host_wire_bridge_proved'])


if __name__=='__main__':unittest.main()
