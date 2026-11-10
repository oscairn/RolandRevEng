import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import key_material_scan as scanner


class ScanTests(unittest.TestCase):
    def test_full_identity_is_required_and_no_material_is_emitted(self):
        authored = scanner.ROM_VECTOR_PREFIX + b'authored-test-material'
        authored = authored.ljust(scanner.ROM_SIZE, b'\xa5')
        data = b'prefix' + authored + b'suffix'
        result = scanner.scan(data)
        self.assertEqual(result['vector_prefix']['first_offsets'], [6])
        self.assertTrue(result['vector_windows'][0]['complete_16k_window'])
        self.assertFalse(result['documented_rom_found'])
        self.assertNotIn('authored-test-material', json.dumps(result))
        with patch.object(scanner, 'ROM_SHA256', hashlib.sha256(authored).hexdigest()):
            result = scanner.scan(data)
            self.assertEqual(result['exact_documented_rom_offsets'], [6])
            self.assertTrue(result['documented_rom_found'])
            self.assertFalse(result['key_bytes_emitted'])

    def test_truncated_prefix_is_not_a_complete_rom(self):
        result = scanner.scan(b'\0'+scanner.ROM_VECTOR_PREFIX+b'\xff'*10)
        self.assertEqual(result['vector_prefix']['count'], 1)
        self.assertFalse(result['vector_windows'][0]['complete_16k_window'])
        self.assertIsNone(result['vector_windows'][0]['sha256'])
        self.assertFalse(result['documented_rom_found'])

    def test_literal_pointer_is_metadata_not_a_key(self):
        value = scanner.ANCHORS['rom_key_table'].to_bytes(4, 'little')
        result = scanner.scan(b'x'+value+b'y')
        self.assertEqual(result['literal_address_anchors']['rom_key_table']['first_offsets'], [1])
        self.assertFalse(result['documented_rom_found'])
        self.assertEqual(result['exact_documented_rom_offsets'], [])

    def test_hit_counts_are_complete_even_when_offset_samples_are_capped(self):
        result = scanner.offsets(b'a'*40, b'aa')
        self.assertEqual(result['count'], 39)
        self.assertEqual(result['first_offsets'], list(range(16)))
        self.assertTrue(result['offsets_truncated'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
REQUIRED = ['b0c1a.bin', 'b1c1a.bin', 'bmc0_MI078_C0A_up.bin', 'bmc1_MI078_C0A_up.bin',
            'mi078', 'qctest', 'crossmodel/mc101/MC101_UPA_up.bin',
            'crossmodel/jupiter-x/MI077_UPA_up.bin', 'crossmodel/sh-4d/SH4d_UPA_up.bin',
            'crossmodel/tr-8s/TR8S_UP.bin']


@unittest.skipUnless(importlib.util.find_spec('capstone') and all((CORPUS/p).exists() for p in REQUIRED),
                     'Capstone and all scoped local firmware artifacts required')
class CorpusTests(unittest.TestCase):
    def test_current_artifacts_and_verified_expansions_have_no_documented_rom(self):
        report = scanner.study(CORPUS)
        self.assertEqual(report['unique_objects'], 27)
        self.assertEqual(report['total_scanned_bytes'], 146004684)
        self.assertEqual(report['exact_rom_copies'], 0)
        self.assertEqual(sum(r['vector_prefix']['count'] for r in report['objects']), 0)
        self.assertEqual(sum(len(e['recognized_expansions']) for e in report['initial_data_expansions']), 5)
        for row in report['objects']:
            for anchor in ('rom_key_table', 'selected_b6_entry', 'des_key_registers'):
                self.assertEqual(row['literal_address_anchors'][anchor]['count'], 0)
        self.assertFalse(report['key_bytes_emitted'])


if __name__ == '__main__':
    unittest.main()
