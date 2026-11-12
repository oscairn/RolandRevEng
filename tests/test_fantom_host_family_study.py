import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_host_family_study import FamilyOracle,HostImage,notification_bytes,report


class ModelTests(unittest.TestCase):
    def test_exact_generic_typed_range_and_fourteen_bit_index(self):
        self.assertEqual(notification_bytes(6,0,0,3504,3505).hex(),'06000000010132')
        self.assertEqual(notification_bytes(7,65535,1,3504,3505).hex(),'07fcff01010132')
        self.assertEqual(notification_bytes(7,65535,1,4917,4918).hex(),'07fcff01595987')
        self.assertEqual(notification_bytes(7,0,1,3486,3533).hex(),'070000010002f0')
        self.assertEqual(notification_bytes(7,16383,1,3504,3505),notification_bytes(7,65535,1,3504,3505))

    def test_bad_family_and_unchecked_ranges_fail_before_cpu(self):
        for args in ((True,0,0,3504,3505),(8,0,0,3504,3505),(6,-1,0,3504,3505),
                     (6,0,256,3504,3505),(6,0,0,3505,3504),(6,0,0,3503,3504),
                     (6,0,0,4916,4917),(6,0,0,True,3505)):
            self.assertRaises(ValueError,notification_bytes,*args)
        oracle=object.__new__(FamilyOracle)
        self.assertRaises(ValueError,oracle.callback,3,0,3504,3505)
        self.assertRaises(ValueError,oracle.callback,0,0,3504,3505,flags=4)
        self.assertRaises(ValueError,oracle.callback,0,0,3504,3505,force_full=1)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_CORPUS=all((CORPUS/f).exists()for f in ('mi078','b0c1a.bin'))and all(importlib.util.find_spec(m)for m in ('capstone','elftools'))


@unittest.skipUnless(HAS_CORPUS,'Pinned host/CORE1 images and readers required')
class CorpusTests(unittest.TestCase):
    def test_matching_descriptor_domains_and_actual_callback_registrations(self):
        from core1 import Core1
        host=(CORPUS/'mi078').read_bytes();core=Core1(CORPUS/'b0c1a.bin')
        r=report(HostImage(host),core)
        self.assertEqual((r['matching_generic_descriptors'],r['matching_fdrv_typed_descriptors']),(48,26))
        self.assertEqual(r['id_shift'],2071)
        self.assertEqual(r['host_live1_generic_ids'],[3504,3505])
        self.assertEqual(r['host_live1_typed_ids'],[4917,4918])
        self.assertFalse(r['core1_slot_assignment_proved'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertRaises(ValueError,HostImage,host[:-1]+bytes((host[-1]^1,)))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'),'Unicorn and private-RAM JIT permission required')
    def test_original_callbacks_getters_and_paired_routes(self):
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_host_family_study.py'),
            str(CORPUS/'mi078'),str(CORPUS/'b0c1a.bin'),'--execute-arm64'],
            text=True,capture_output=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_family_callback_cases'],432)
        self.assertEqual(r['paired_message_count'],432)
        self.assertEqual(r['copied_block_data_bytes'],8928)
        self.assertEqual(r['forced_full_range_cases'],3)
        self.assertTrue(r['original_getters_router_and_temporary_destruction_executed'])
        self.assertTrue(r['output_queue_storage_and_mutex_effects_intercepted'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertFalse(r['core1_slot_assignment_proved'])


if __name__=='__main__':unittest.main()
