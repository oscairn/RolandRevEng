import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import assemble
from effect_lifecycle_study import entry_candidates, report


class CandidateTests(unittest.TestCase):
    def test_owner_dsp_and_control_boundaries(self):
        owners = [dict(address=0x100, dsp=4, render=[dict(base=0x4020, capacity=0x1000)])]
        stream = assemble([[0x1a05, 0x00a0, 0x00a2, 0x2010, 0x2000]])
        self.assertEqual(entry_candidates(stream, 0x20, 4, owners), [dict(
            packet_address=0x20, owner_descriptor=0x100, candidate_entry_byte=0x4020,
            pool_halfword_index=0, pool_value=0x2010)])
        self.assertEqual(entry_candidates(stream, 0x20, 5, owners), [])
        # Matching numbers in the payload cannot substitute for actual controls.
        payload_only = assemble([[0x0b05, 0x1710, 0x00a0, 0x00a2, 0x2010]])
        self.assertEqual(entry_candidates(payload_only, 0x20, 4, owners), [])
        owners[0]['render'][0]['base'] = 0x8040
        self.assertEqual(entry_candidates(stream, 0x20, 4, owners), [])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'b0c1a.bin').exists(),
                     'Capstone and local CORE1 artifact required')
class CorpusTests(unittest.TestCase):
    def test_four_independent_parent_references_and_reset_reservations(self):
        from core1 import Core1
        core = Core1(CORPUS / 'b0c1a.bin')
        result = report(core)
        rows = result['parent_entry_reference_candidates']
        self.assertEqual([(r['dsp'], r['packet_address'], r['candidate_entry_byte']) for r in rows],
                         [(4, 0x2e0, 0x4020), (5, 0x1056, 0x8040),
                          (5, 0x177a, 0x9040), (5, 0x1832, 0xa040)])
        self.assertEqual([r['pool_halfword_index'] for r in rows], [1, 1, 1, 1])
        self.assertEqual([r['enum6'] for r in result['coefficient_reservations']],
                         [[dict(base=base, length=0x14)] for base in (0x190, 0x1f4, 0x208, 0x21c, 0xe)])
        self.assertEqual(core.u32(0x6117647c + 0xbc), 0x0113391f)
        self.assertEqual(core.u32(0x611781d4 + 8), 0x61056b15)
        core.data = core.data[:-1]
        with self.assertRaisesRegex(ValueError, 'recorded bmc0'):
            report(core)


if __name__ == '__main__':
    unittest.main()
