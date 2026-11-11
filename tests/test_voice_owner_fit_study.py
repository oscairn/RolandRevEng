import copy
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from voice_owner_fit_study import fit, report, requirements


class FitTests(unittest.TestCase):
    def test_extents_and_independent_capacity_failures(self):
        required = requirements()
        self.assertEqual((required['body_bytes'], required['data_extent'], required['coefficient_extent']),
                         (200, 146, 6))
        owner = dict(address=0x100, dsp=4, render=[dict(base=0x4020, capacity=200)],
                     memories={0: [dict(base=0x100, length=146)], 6: [dict(base=0x190, length=6)]})
        self.assertTrue(fit(owner)['body_capacity_fits'])
        for resource in ('program', 'data', 'coefficients'):
            candidate = copy.deepcopy(owner)
            if resource == 'program':
                candidate['render'][0]['capacity'] -= 1
            else:
                candidate['memories'][0 if resource == 'data' else 6][0]['length'] -= 1
            result = fit(candidate)
            self.assertFalse(result['fits'][resource])
            self.assertFalse(result['body_capacity_fits'])
        owner['memories'][0][0]['base'] = 0x800-145
        self.assertFalse(fit(owner)['fits']['data'])
        with self.assertRaisesRegex(ValueError, 'pinned Fantom'):
            report(SimpleNamespace(data=b'unknown'))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS/'b0c1a.bin').exists(),
                     'Capstone and pinned Fantom firmware required')
class CorpusTests(unittest.TestCase):
    def test_five_actual_owners_fit_body_but_do_not_authorize_replacement(self):
        from core1 import Core1
        result = report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(len(result['owners']), 5)
        self.assertTrue(all(row['body_capacity_fits'] for row in result['owners']))
        self.assertEqual([row['enum0']['length'] for row in result['owners']], [150, 150, 150, 150, 192])
        self.assertTrue(all(not row['available_for_custom_voice'] and not row['execution_ready']
                            and not row['relocated_program_emitted'] for row in result['owners']))


if __name__ == '__main__':
    unittest.main()
