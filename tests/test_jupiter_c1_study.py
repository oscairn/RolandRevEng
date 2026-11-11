import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from jupiter_c1_study import compare, enable_calls, original_span


class SourceTests(unittest.TestCase):
    def test_original_member_span_and_unbacked_gap_rejection(self):
        manifest = dict(members=[dict(name='idm1.bin', offset=0x100)],
                        regions=[dict(name='idm1.bin', runtime_base=0x01100000,
                                      source_offset=0x120, size=8)])
        self.assertEqual(original_span(manifest, 0x01100004, 4),
                         dict(member='idm1.bin', container_offset=0x124, member_offset=0x24, size=4))
        for address, size in ((0x01100004, 5), (0x01100008, 1), (0x61000000, 1), (0x01100000, 0)):
            with self.assertRaises(ValueError):
                original_span(manifest, address, size)

    def test_unknown_update_rejected_before_runtime_mapping(self):
        with self.assertRaisesRegex(ValueError, 'Unknown JUPITER-X'):
            compare(b'not a supported update', SimpleNamespace(data=b'unused'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
JUPITER = CORPUS/'crossmodel/jupiter-x/MI077_C1A_up.bin'


@unittest.skipUnless(importlib.util.find_spec('capstone') and JUPITER.exists() and
                     (CORPUS/'b0c1a.bin').exists(), 'Capstone and official/local C1A inputs required')
class CorpusTests(unittest.TestCase):
    def test_enable_parser_rejects_unproved_sources_and_early_tail_branches(self):
        from core1 import Core1
        for address, replacement, error in (
                (0x610016d0, bytes.fromhex('2246'), 'Unproved enable-call source'),
                (0x610016d8+2, bytes.fromhex('e7b9'), 'unexpected nonreturning branch'),
                (0x610016d4, bytes.fromhex('00bf'), 'Unsupported instruction')):
            core = Core1(CORPUS/'b0c1a.bin')
            offset = core.offset(address)
            core.data = core.data[:offset]+replacement+core.data[offset+2:]
            self.assertRaisesRegex(ValueError, error, enable_calls, core, 0x610016b0, 0x61076aaa)

    def test_exact_routine_windows_and_different_ramclr_layout(self):
        from core1 import Core1
        result = compare(JUPITER.read_bytes(), Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual([m['length'] for m in result['exact_matches']], [158, 14, 14])
        self.assertTrue(all(m['identical'] for m in result['exact_matches']))
        self.assertEqual([m['jupiter_source']['member_offset'] for m in result['exact_matches']],
                         [0x64c70, 0x334e0, 0x2f146])
        enable = result['execution_enable']
        self.assertEqual([row['mode'] for row in enable['fantom']['calls']], [2, 0, 2, 0, 2])
        self.assertEqual([row['mode'] for row in enable['jupiter']['calls']], [2]*5)
        self.assertEqual([enable[name]['mode2_mask'] for name in ('fantom', 'jupiter')], [0x45, 0x4f])
        self.assertTrue(all(row['argument'] == 0 and row['event'] == 3
                            for model in enable.values() for row in model['calls']))
        self.assertTrue(all(not model['safe_halt_verified'] for model in enable.values()))
        segments = result['ramclr_list']['segments']
        self.assertEqual([(r['records'], r['stride']) for r in segments], [(23, 0x1900)]*9+[(22, 0x2100)]*2)
        self.assertEqual(result['mapping']['itcm_bytes'], 0x3dd0c)
        self.assertEqual(result['mapping']['scatter_records'], 10)
        self.assertFalse(result['execution_ready'])
        self.assertFalse(result['container']['members'][1]['additive_u16_matches'])
        self.assertFalse(result['container']['analysis_view_is_original'])


if __name__ == '__main__':
    unittest.main()
