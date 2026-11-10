import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from prefix_group_inventory import inventory, report


class InventoryTests(unittest.TestCase):
    def test_count_and_nonadjacent_membership(self):
        data = bytearray(256)
        struct.pack_into('<Q', data, 8, 1)
        struct.pack_into('<Q', data, 16, 128)
        data[24] = 1
        struct.pack_into('<9I', data, 128, 0x4034, 0x14, 3, 0x4099, 0x79, 3, 0x4037, 0x17, 3)
        self.assertEqual(inventory(data, 8)['matching_groups'], [])
        data[24] = 2
        self.assertEqual(inventory(data, 8)['matching_groups'], [])
        data[24] = 3
        matches = inventory(data, 8)['matching_groups']
        self.assertEqual([(m['symbol'], m['pairs']) for m in matches], [(0, [[0x14, 0x17]])])
        self.assertTrue(matches[0]['prior_lp64_parser_accepts'])
        self.assertFalse(matches[0]['ownership_proven'])
        self.assertEqual(inventory(data[:150], 8)['matching_groups'], [])
        data[24] = 255
        self.assertEqual(inventory(data, 8)['matching_groups'], [])
        data[24] = 3
        struct.pack_into('<I', data, 16, 129)
        self.assertEqual(inventory(data, 8)['matching_groups'], [])
        struct.pack_into('<Q', data, 16, 128)
        struct.pack_into('<I', data, 136, 0x103)
        self.assertFalse(inventory(data, 8)['matching_groups'][0]['prior_lp64_parser_accepts'])
        struct.pack_into('<I', data, 136, 0x99)
        self.assertEqual(inventory(data, 8)['matching_groups'], [])

    def test_arm_pointer_mapping_does_not_join_unmapped_gap(self):
        data = bytearray(256)
        struct.pack_into('<I', data, 4, 1)
        struct.pack_into('<I', data, 8, 0x61000080)
        data[12] = 2
        struct.pack_into('<6I', data, 128, 0x4044, 0x24, 3, 0x4047, 0x27, 3)
        offset = lambda address: address-0x61000000
        address = lambda offset: offset+0x61000000
        self.assertEqual(inventory(data, 4, offset, address)['matching_groups'][0]['symbol'], 0x61000000)
        def discontinuous(pointer):
            return offset(pointer)+(0x100 if pointer >= 0x6100008c else 0)
        self.assertEqual(inventory(data, 4, discontinuous, address)['matching_groups'], [])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/name).exists() for name in ('zen_arm64', 'b0c1a.bin')),
                     'Recorded native and CORE1 artifacts required')
class CorpusTests(unittest.TestCase):
    def test_no_matching_static_group_in_scanned_inventory(self):
        from core1 import Core1
        result = report((CORPUS/'zen_arm64').read_bytes(), Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([result[k]['candidate_count'] for k in ('native', 'firmware')], [665, 616])
        self.assertEqual(result['native']['matching_groups'], [])
        self.assertEqual(result['firmware']['matching_groups'], [])
        self.assertEqual([g['count'] for g in result['native_rational_positive_controls']], [4, 4])
        self.assertEqual([[r['relative_byte'] for r in g['records']]
                          for g in result['native_rational_positive_controls']],
                         [[0xec, 0xf0, 0x118, 0x11c], [0xe6, 0xe9, 0x112, 0x115]])
        self.assertFalse(result['prefix_alias_proven'])


if __name__ == '__main__':
    unittest.main()
