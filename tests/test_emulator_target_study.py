import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from bmc_subset import assemble_tail
from emulator_target_study import assess_stream, remaining_regions, study


class RegionTests(unittest.TestCase):
    def test_packet_partition_and_rejected_partial_admission(self):
        self.assertEqual(remaining_regions(24, [(4, 12), (12, 20)], {0, 4, 12, 20, 24}),
                         [[0, 4], [20, 24]])
        for regions in [[(4, 13)], [(4, 20), (12, 24)], [(4, 28)], [(12, 4)]]:
            with self.assertRaises(ValueError):
                remaining_regions(24, regions, {0, 4, 12, 20, 24})

    def test_template_words_do_not_admit_an_unproved_whole_program(self):
        stream = assemble_tail(dict(kind='dry_wet_tail', wet_addresses=[3, 4],
                                    coefficient_slots=[0, 1, 2, 3]))
        result = assess_stream('original_test_program', stream)
        self.assertEqual(result['exact_checked_fragment_regions'], [])
        self.assertEqual(result['remaining_regions'], [[0, 60]])
        self.assertEqual(len(result['unhandled_packets']), 6)
        self.assertFalse(result['complete_program_executable'])


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and
                     all((CORPUS/name).exists() for name in ['zen_arm64', 'pairs.json', 'exports_dem.txt']),
                     'Recorded native image and generated pairing metadata required')
class CorpusTests(unittest.TestCase):
    def test_exact_contexts_leave_complete_program_gaps(self):
        result = study()
        self.assertEqual(result['paired_classes_checked'], 75)
        rows = {r['cls']: r for r in result['candidates']}
        line = rows['SIM_MFX_LINEDRIVE']
        self.assertEqual(line['remaining_regions'], [[0, 0x13e], [0x21e, 0x242]])
        self.assertEqual([(r['kind'], r['start'], r['end']) for r in line['exact_checked_fragment_regions']],
                         [('allpass4', 0x13e, 0x190), ('allpass4', 0x190, 0x1e2),
                          ('dry_wet_tail', 0x1e2, 0x21e)])
        self.assertEqual(rows['SIM_MFX_FETDRIVE']['remaining_regions'], [[0, 0x16a], [0x1a6, 0x1ca]])
        self.assertEqual(rows['SIM_MFX_GATE']['unresolved_family_headers'], [0x6508, 0xbf07, 0xde4c])
        self.assertEqual(line['unresolved_family_headers'], [])
        self.assertTrue(all(not row['complete_program_executable'] for row in rows.values()))
        self.assertEqual(line['native_control_flow'], [])


if __name__ == '__main__':
    unittest.main()
