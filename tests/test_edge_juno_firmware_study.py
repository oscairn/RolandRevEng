import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from edge_juno_firmware_study import INPUTS, study, update_parts


class ArchiveTests(unittest.TestCase):
    def check_archive(self, entries):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'update.bin'
            with tarfile.open(path, 'w') as archive:
                for name, kind in entries:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.size = 3 if kind == tarfile.REGTYPE else 0
                    archive.addfile(info, io.BytesIO(b'abc') if info.size else None)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return list(update_parts(path, digest))

    def test_regular_nested_members_are_read_without_extraction(self):
        self.assertEqual(self.check_archive([('./_tmp/C1A.bin', tarfile.REGTYPE)]), [('C1A.bin', b'abc')])

    def test_rejects_unsafe_paths_nonregular_members_and_basename_collision(self):
        for entries in [[('../C1A.bin', tarfile.REGTYPE)], [('/C1A.bin', tarfile.REGTYPE)],
                        [('link', tarfile.SYMTYPE)], [('folder', tarfile.DIRTYPE)],
                        [('one/C1A.bin', tarfile.REGTYPE), ('two/C1A.bin', tarfile.REGTYPE)]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.check_archive(entries)

    def test_unknown_digest_is_rejected_before_tar_parsing(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'update.bin'; path.write_bytes(b'not a tar')
            with self.assertRaisesRegex(ValueError, 'digest'):
                list(update_parts(path, '0'*64))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
REQUIRED = [CORPUS/'b0c1a.bin', CORPUS/'bmc0_MI078_C0A_up.bin'] + [
    CORPUS/'crossmodel'/model/record[0] for model, record in INPUTS.items()]


@unittest.skipUnless(importlib.util.find_spec('capstone') and all(p.exists() for p in REQUIRED),
                     'Capstone and pinned official/local images required')
class CorpusTests(unittest.TestCase):
    def test_component_scans_c1_bounds_and_new_ciphertext_comparisons(self):
        result = study(CORPUS)
        rows = {r['model']: r for r in result['models']}
        self.assertEqual(set(rows), set(INPUTS))
        self.assertEqual(rows['ax-edge']['c0']['shared_with_fantom0'], 13659)
        self.assertEqual(rows['juno-x']['c0']['shared_with_fantom0'], 15780)
        self.assertEqual([len(w['hits']) for w in rows['ax-edge']['c1']['exact_windows']], [0, 0, 0])
        self.assertEqual([len(w['hits']) for w in rows['juno-x']['c1']['exact_windows']], [1, 1, 1])
        for row in rows.values():
            self.assertEqual(len(row['components']), 5)
            self.assertTrue(row['c1']['manifest']['footer_crc32_valid'])
            self.assertEqual(row['c0']['header']['crypto_control'], 0xb6020001)
            self.assertFalse(row['c1']['manifest']['analysis_view_is_original'])
            for member in row['components']:
                self.assertFalse(member['documented_rom_found'])
                self.assertFalse(member['key_bytes_emitted'])
                self.assertEqual(member['literal_address_anchors']['rom_key_table']['count'], 0)
                self.assertEqual(member['literal_address_anchors']['selected_b6_entry']['count'], 0)
        self.assertFalse(result['key_recovered'])
        self.assertFalse(result['decryption_performed'])
        self.assertFalse(result['hardware_execution'])


if __name__ == '__main__':
    unittest.main()
