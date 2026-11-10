import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from additional_firmware_study import components, find_windows, report


class WindowTests(unittest.TestCase):
    def test_only_original_regions_match_including_overlaps(self):
        manifest = dict(regions=[dict(name='a', runtime_base=0x1000, analysis_offset=0,
                                      source_offset=0x80, size=4),
                                 dict(name='b', runtime_base=0x2000, analysis_offset=4,
                                      source_offset=0x100, size=3)])
        rows = find_windows(manifest, b'AAAAxyz', [('overlap', b'AAA'), ('cross-gap', b'Ax')])
        self.assertEqual(rows[0]['hits'], [dict(member='a', runtime=0x1000, container_offset=0x80),
                                          dict(member='a', runtime=0x1001, container_offset=0x81)])
        self.assertEqual(rows[1]['hits'], [])
        with self.assertRaises(ValueError):
            find_windows(manifest, b'AAAAxyz', [('empty', b'')])
        manifest['regions'][1]['size'] = 4
        with self.assertRaises(ValueError):
            find_windows(manifest, b'AAAAxyz', [('bound', b'xyz')])

    def test_unknown_archives_and_reference_fail_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'archive digest'):
            components(b'unrecognized', '0'*64)
        with self.assertRaisesRegex(ValueError, 'Fantom'):
            report(b'', b'', SimpleNamespace(data=b'unrecognized'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
INPUTS = [CORPUS/'crossmodel/sh-4d/SH4d_UPA_up.bin',
          CORPUS/'crossmodel/tr-8s/TR8S_UP.bin', CORPUS/'b0c1a.bin']


@unittest.skipUnless(importlib.util.find_spec('capstone') and all(p.exists() for p in INPUTS),
                     'Capstone and official/local artifacts required')
class CorpusTests(unittest.TestCase):
    def test_official_archives_and_shared_windows(self):
        from core1 import Core1
        result = report(INPUTS[0].read_bytes(), INPUTS[1].read_bytes(), Core1(INPUTS[2]))
        self.assertEqual([r['length'] for r in result['sh4d']['exact_windows']], [324, 158, 14])
        self.assertTrue(result['sh4d']['c1']['footer_crc32_valid'])
        self.assertFalse(result['tr8s']['plaintext_c1_component_present'])
        for model in ('sh4d', 'tr8s'):
            self.assertEqual(result[model]['c0']['crypto_control'], 0xb6020001)
        self.assertFalse(result['execution_ready'])


if __name__ == '__main__':
    unittest.main()
