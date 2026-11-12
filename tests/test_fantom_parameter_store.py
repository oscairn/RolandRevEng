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
from fantom_parameter_store_study import StoreOracle,stored_short,control_writes,block_payload,report


class ModelTests(unittest.TestCase):
    def test_scalar_low16_bits_and_signed_word_boundaries(self):
        for source,wanted in ((65537,1),(65539,3),(65535,-1),(66536,1000),
                (-2147483648,0),(2147483647,-1),(-65535,1)):
            self.assertEqual(stored_short(source),wanted)

    def test_generic_relative_field_index_and_complete_block_width(self):
        self.assertEqual(block_payload([(2,1),(3,1000)]),bytes.fromhex('12000100e803'))
        self.assertEqual(block_payload([(3,65535)]),bytes.fromhex('1300ffff'))
        self.assertEqual(block_payload([]),bytes.fromhex('1200'))
        self.assertEqual(control_writes([(3,1000),(2,65537)],'scalar'),[(3,1000),(2,1)])
        self.assertEqual(control_writes([(2,2),(2,2)],'scalar'),[(2,2),(2,2)])

    def test_unknown_fields_bad_blocks_and_bad_values_fail_before_cpu(self):
        for value in (True,2147483648,-2147483649,1.5):self.assertRaises(ValueError,stored_short,value)
        for changes,form in (([(0,1)],'scalar'),([(True,1)],'scalar'),([(4,1)],'block'),
                ([(2,1),(2,2)],'block'),([(3,1),(2,2)],'block'),([(2,1)]*3,'scalar'),
                ([(2,True)],'scalar'),([2],'block'),([(2,1)],'unknown')):
            self.assertRaises(ValueError,control_writes,changes,form)
        oracle=object.__new__(StoreOracle)
        self.assertRaises(ValueError,oracle.write_controls,[0]*22,[(0,1)])
        self.assertRaises(ValueError,oracle.write_controls,[0]*21,[(2,1)])
        self.assertRaises(ValueError,oracle.write_controls,[0]*22,[(2,1)],index=0)
        self.assertRaises(ValueError,oracle.write_controls,[0]*22,[(2,1)],enabled=1)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORE=importlib.util.find_spec('capstone')and(CORPUS/'b0c1a.bin').exists()
HAS_UNICORN=importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(HAS_CORE,'Pinned Fantom CORE1 corpus required')
class CorpusTests(unittest.TestCase):
    def test_stream_rtti_generic_vs_typed_ids_and_source_identity(self):
        from core1 import Core1
        core=Core1(CORPUS/'b0c1a.bin');r=report(core)
        self.assertEqual(r['generic_live1_parameter_ids'],[0x599,0x59a])
        self.assertEqual(r['typed_live1_parameter_ids'],[2846,2847])
        self.assertFalse(r['writer_validates_value_range'])
        self.assertTrue(r['writer_retains_low16_bits'])
        self.assertFalse(r['finalizer_resets_dirty_range'])
        self.assertEqual(r['finalizer_reserved_word_mask'],0x1fc0)
        with patch.object(core,'data',core.data[:-1]+bytes([core.data[-1]^1])):
            self.assertRaises(ValueError,report,core);self.assertRaises(ValueError,StoreOracle,core)

    @unittest.skipUnless(HAS_UNICORN,'Pinned Unicorn2.1.4 and private-RAM JIT permission required')
    def test_original_scalar_block_finalize_and_connected_efct_route(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_parameter_store_study.py'),
            str(CORPUS/'b0c1a.bin'),'--execute-thumb'],capture_output=True,text=True,timeout=180)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_write_route_cases'],576)
        self.assertEqual(r['writer_coefficient_writes'],2160)
        self.assertEqual(r['original_finalizer_notifications'],864)
        self.assertEqual(len(r['low16_boundary_cases']),8)
        self.assertEqual([x['normalized']for x in r['low16_boundary_cases']],
            [1,2,1000,3740]*2)
        self.assertEqual(r['same_value_notifications'],2)
        self.assertEqual(r['same_value_coefficient_writes'],0)
        self.assertTrue(r['original_store_constructor_writer_finalizer_executed'])
        self.assertFalse(r['optional_external_serialization_executed'])
        self.assertFalse(r['host_wire_bridge_proved'])
        self.assertFalse(r['hardware_task_execution_verified'])


if __name__=='__main__':unittest.main()
