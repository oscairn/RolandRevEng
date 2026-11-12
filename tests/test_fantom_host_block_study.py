import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fantom_host_block_study import HostImage,checked_args,report


class ModelTests(unittest.TestCase):
    def test_source_identity_fails_before_parsing_or_cpu(self):
        for data in (b'',b'\x7fELF'+bytes(100)):
            self.assertRaises(ValueError,HostImage,data)

    def test_bounded_unsigned_arguments_and_authored_bytes(self):
        checked_args(0xffffffff,0xffffffff,0xffffffff,0xffffffff,b'\xff'*0x660,255)
        for args in ((True,0,0,0,b'',0),(0,-1,0,0,b'',0),(0,0,1<<32,0,b'',0),
                     (0,0,0,0,bytearray(),0),(0,0,0,0,b'\0'*0x661,0),
                     (0,0,0,0,b'',256),(0,0,0,0,b'',True)):
            self.assertRaises(ValueError,checked_args,*args)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
HAS_HOST=(CORPUS/'mi078').exists()and all(importlib.util.find_spec(m)for m in ('capstone','elftools'))


@unittest.skipUnless(HAS_HOST,'Pinned mi078 host corpus and ELF/Capstone readers required')
class CorpusTests(unittest.TestCase):
    def test_source_calls_layout_and_mutation_rejection(self):
        data=(CORPUS/'mi078').read_bytes();r=report(HostImage(data))
        self.assertEqual(len(r['direct_block_constructor_callers']),37)
        self.assertEqual(r['inline_data_limit'],3)
        self.assertFalse(r['variable_native_pointer_transmitted'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertRaises(ValueError,HostImage,data[:-1]+bytes((data[-1]^1,)))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'),'Unicorn and private-RAM JIT permission required')
    def test_original_constructor_and_serializer_match_layout(self):
        import json
        run=subprocess.run([sys.executable,str(ROOT/'tools/fantom_host_block_study.py'),
            str(CORPUS/'mi078'),'--execute-arm64'],text=True,capture_output=True,timeout=60)
        self.assertEqual(run.returncode,0,run.stderr);r=json.loads(run.stdout)
        self.assertEqual(r['original_host_block_cases'],108)
        self.assertTrue(r['constructor_copies_input'])
        self.assertTrue(r['padding_depends_on_seeded_memory'])
        self.assertTrue(r['allocations_and_memcpy_intercepted'])
        self.assertFalse(r['original_queue_execution'])
        self.assertFalse(r['host_to_core1_translation_proved'])
        self.assertFalse(r['live_host_queue_or_device_executed'])


if __name__=='__main__':unittest.main()
