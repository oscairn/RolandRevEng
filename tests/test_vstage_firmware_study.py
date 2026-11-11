import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from vstage_firmware_study import report,UPDATE_SHA256


class TrustBoundaryTests(unittest.TestCase):
    def test_wrong_digest_is_rejected_before_archive_parsing(self):
        with tempfile.TemporaryDirectory()as directory:
            p=Path(directory)/'bad.bin';p.write_bytes(b'not an official update')
            with patch('tarfile.open',side_effect=AssertionError('Must hash first')):
                self.assertRaises(ValueError,report,p)


CORPUS=Path(os.environ.get('BMC_CORPUS_DIR',ROOT/'local'))
UPDATE=CORPUS/'vstage-worker/VSTAGE_UPA.BIN'


@unittest.skipUnless(UPDATE.exists()and importlib.util.find_spec('capstone'),'Pinned V-STAGE corpus required')
class CorpusTests(unittest.TestCase):
    def test_five_targets_three_image_groups_and_mapped_core1_layouts(self):
        r=report(UPDATE)
        self.assertEqual(r['update_sha256'],UPDATE_SHA256)
        self.assertEqual((r['component_count'],r['bmc_target_indices']),(15,[0,1,2,3,4]))
        self.assertEqual(r['identical_component_groups'],[[0],[1,2],[3,4]])
        self.assertEqual([target['components'][1]['core1']['scatter_records']for target in r['targets']],
                         [10,12,12,8,8])
        for target in r['targets']:
            c0,c1,_=target['components']
            self.assertEqual(c0['header']['key_index'],0xb6)
            self.assertEqual(c0['header']['enabled'],1)
            self.assertTrue(c1['core1']['reset_entry']&1)
        for key in ('physical_chip_count_verified','host_cpu_identified','dsp_isa_compatibility_verified',
                    'key_recovered','decryption_performed','hardware_execution'):
            self.assertFalse(r[key])

    def test_missing_target_and_wrong_footer_are_rejected(self):
        from edge_juno_firmware_study import update_parts
        rows=list(update_parts(UPDATE,UPDATE_SHA256))
        with patch('vstage_firmware_study.update_parts',return_value=iter(rows[:-1])):
            self.assertRaises(ValueError,report,UPDATE)
        changed=list(rows);name,data=changed[0];data=bytearray(data);data[-10:]=b'X'*10
        changed[0]=(name,bytes(data))
        with patch('vstage_firmware_study.update_parts',return_value=iter(changed)):
            self.assertRaises(ValueError,report,UPDATE)


if __name__=='__main__':unittest.main()
