import importlib.util
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
HAS_CAPSTONE=importlib.util.find_spec('capstone')


@unittest.skipUnless(HAS_CAPSTONE,'Capstone required')
class LiteralTests(unittest.TestCase):
    def test_narrow_wide_and_negative_literal_references_and_changed_pointer(self):
        import capstone
        from core1 import Core1
        from vstage_program_ownership import literal_loads,require_shape
        core=Core1.__new__(Core1);core.eram_offset=256
        data=bytearray(256);struct.pack_into('<H',data,0x20,0x4917)
        data[0x5c:0x60]=bytes.fromhex('dff82010');data[0xa0:0xa4]=bytes.fromhex('5ff82410')
        struct.pack_into('<I',data,0x80,0x611008a8);core.data=bytes(data)
        core.md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB|capstone.CS_MODE_MCLASS)
        core.md.detail=True
        hits=literal_loads(core,0x01100080)
        self.assertEqual([r['pc']for r in hits],[0x01100020,0x0110005c,0x011000a0])
        self.assertEqual({r['value']for r in hits},{0x611008a8})
        self.assertEqual(literal_loads(core,0x01100084),[])
        self.assertRaises(ValueError,require_shape,core,0x01100020,[('blx','r2')])


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
UPDATE=CORPUS/'vstage-worker/VSTAGE_UPA.BIN'
HAS_CORPUS=HAS_CAPSTONE and UPDATE.exists()and(CORPUS/'b0c1a.bin').exists()


@unittest.skipUnless(HAS_CORPUS,'Pinned Fantom/V-STAGE corpus required')
class CorpusTests(unittest.TestCase):
    def test_rtti_linked_callers_diagnostic_dispatch_and_bootstrap_list_walk(self):
        from vstage_program_ownership import report
        r=report(UPDATE,CORPUS/'b0c1a.bin');f,g0,g1=r['images']
        for image,address,entry in ((f,0x610e5a94,0x61049e68),(g1,0x611008a8,0x61053f1c)):
            row=image['fdrv_programs'][0]
            self.assertEqual(row['list_address'],address)
            self.assertEqual(row['length'],1420)
            owner=row['owner'];self.assertEqual(owner['callback_entry'],entry)
            self.assertEqual((owner['callback_slot'],owner['dispatch_slot']),(8,0x28))
            self.assertEqual(owner['encoded_class'],'11CFspMfxFDRV')
            self.assertEqual(owner['instructions'][-1]['instruction'],'blx r2')
        self.assertEqual(g1['targets'],[1,2]);self.assertEqual(g1['fdrv_programs'][0]['header_dsp'],4)
        self.assertEqual([sorted(s['length']for s in image['shared_programs'])for image in r['images']],
                         [[11572,51542],[11572,51542],[11572]])
        for image in r['images']:
            for row in image['shared_programs']:
                if row['length']==11572:
                    self.assertEqual(row['diagnostic_dispatch'][0]['dispatch_slot'],0x18)
                    self.assertIn('TestEram()',row['diagnostic_dispatch'][0]['assertion_text'])
                else:
                    self.assertEqual([x['kind']for x in row['bootstrap_references']],
                        ['selected_list_dispatch','list_count_and_16_byte_row_walk'])
        self.assertEqual(g0['shared_programs'][0]['header_dsp'],6)
        self.assertFalse(r['hardware_compatibility_verified'])

    def test_changed_baseline_is_rejected(self):
        from vstage_program_ownership import report
        with tempfile.TemporaryDirectory()as directory:
            p=Path(directory)/'changed.bin';data=bytearray((CORPUS/'b0c1a.bin').read_bytes());data[-1]^=1
            p.write_bytes(data);self.assertRaises(ValueError,report,UPDATE,p)


if __name__=='__main__':unittest.main()
