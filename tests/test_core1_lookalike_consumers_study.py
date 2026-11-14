"""Checks for the CORE1 lookalike-reservation consumer trace study.

tools/core1_lookalike_consumers_study.py answers the A2 follow-up queued by
run 15: who consumes the same-shape (header, list) run at 0x610a1ee8..0x610a1f74
that the boot verify walk does not, and do DSP1/3/4/5 therefore receive runtime
program loads in the stock image? It byte-pins the two consumer functions and
their call chains (diagnostic dispatcher 0x1126a6c -> TestEram 0x6103f4b2 via
veneer 0x1134c7c; consumers 0x610293b2 / 0x6102a230 / 0x6102a608 via veneer
0x1134cea and tail calls), decodes all 16 entries of the lookalike run plus the
four seed entries of the first consumer, maps their record word0 offsets onto
the run-13/15 aperture tables, and checks the manager upload wrappers. Pure
checks run without the corpus; the pinned-image checks need BMC_CORPUS_DIR
(or local/) plus capstone.
"""
import os
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import core1_lookalike_consumers_study as study

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
IMAGE = CORPUS / 'b0c1a.bin'
HAS_IMAGE = IMAGE.exists() and find_spec('capstone') is not None


class ModelTests(unittest.TestCase):
    def test_expected_table2_covers_sixteen_entries(self):
        self.assertEqual(len(study.EXPECTED_TABLE2), 16)
        covered = {}
        for header, _ in study.EXPECTED_TABLE2.values():
            covered.setdefault((header >> 8) & 0xFF, set()).add(header & 1)
        self.assertEqual(sorted(covered), [1, 3, 4, 5])
        self.assertEqual(covered[1], {0, 1})
        self.assertEqual(covered[3], {0, 1})
        self.assertEqual(covered[4], {0, 1})
        self.assertEqual(covered[5], {0, 1})

    def test_program_aperture_closed_form(self):
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[1], 0x41580000)
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[3], 0x41780000)
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[4], 0x41880000)
        self.assertEqual(study.PROGRAM_APERTURE_WORDS[5], 0x41980000)
        self.assertEqual(study.DRAMIO_BANK0[1], 0x41540000)
        self.assertEqual(study.DRAMIO_BANK0[5], 0x41940000)

    def test_aperture_mapping_uses_phase_to_select_table(self):
        rows = [dict(address='0x0', dsp=1, phase=0, records=[(0x20, 0x27a, 0x1000, 0)])]
        mapped = study.apertures(rows)
        self.assertEqual(mapped[0]['base'], '0x41580000')
        self.assertEqual(mapped[0]['ranges'][0]['start'], '0x41580020')
        rows = [dict(address='0x0', dsp=1, phase=1, records=[(0x80, 8, 0x528, 0)])]
        mapped = study.apertures(rows)
        self.assertEqual(mapped[0]['base'], '0x41540000')
        self.assertEqual(mapped[0]['ranges'][0]['start'], '0x41540080')


class PinnedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_IMAGE:
            raise unittest.SkipTest('Pinned b0c1a.bin image and capstone required')
        cls.core = study.load_image(IMAGE)
        cls.report = study.report(IMAGE)

    def test_payload_sha_matches_pinned_image(self):
        import hashlib
        self.assertEqual(hashlib.sha256(self.core.data).hexdigest(),
                         study.SHA256)

    def test_anchors_are_byte_exact(self):
        self.assertEqual(self.report['anchor_problems'], [])
        self.assertGreater(self.report['anchors_checked'], 0)

    def test_table2_entries_match_pinned_values(self):
        self.assertTrue(self.report['table2_matches'])
        rows = {int(r['address'], 16): r for r in self.report['table2_entries']}
        # DSP1/3/4/5 all carry both phases here, unlike the boot table.
        for dsp in (1, 3, 4, 5):
            self.assertIn(dsp, {r['dsp'] for r in rows.values()})
        # The stub pair records: (0x0, 0x12, 0x20, src) then (0x20, 0, 0, src).
        stub = rows[0x610a1f38]
        self.assertEqual(stub['records'][0][:3], (0, 0x12, 0x20))
        self.assertEqual(stub['records'][1][:3], (0x20, 0, 0))
        # The 198-byte diagnostic program record is repeated on all four DSPs.
        for address in (0x610a1f58, 0x610a1f60, 0x610a1f68, 0x610a1f70):
            record = rows[address]['records'][0]
            self.assertEqual(record[0], 0x20)
            self.assertEqual(record[1], 0xc6)
            self.assertEqual(record[2], 0xc6)

    def test_table1_seed_records_match_pinned_values(self):
        self.assertTrue(self.report['table1_matches'])
        rows = {int(r['address'], 16): r for r in self.report['table1_entries']}
        self.assertEqual(rows[0x610a1ef8]['count'], 3)
        self.assertEqual(rows[0x610a1f28]['count'], 11)
        # DSP5 seed list largest record word0 0xfc40 maps into the DSP5 aperture.
        last = rows[0x610a1f28]['records'][-1]
        self.assertEqual(last[0], 0xfc40)
        self.assertEqual(last[1], 6)

    def test_aperture_ranges_are_within_per_dsp_windows(self):
        stride = 0x100000
        for entry in (self.report['table1_apertures']
                      + self.report['table2_apertures']):
            base = int(entry['base'], 16)
            window = base & ~(stride - 1)
            for span in entry['ranges']:
                start = int(span['start'], 16)
                self.assertGreaterEqual(start, window, entry)
                self.assertLess(start + span['length'],
                                window + stride, entry)

    def test_call_chain_binds_both_consumers_to_the_dispatcher(self):
        chains = self.report['call_chains']
        # Table-1 consumer reached by BL 0x6102a478 / tail b.w 0x6102a662.
        self.assertIn(['0x6102a478', 'bl'], chains['0x610293b2']['branches'])
        self.assertIn(['0x6102a662', 'b.w'], chains['0x610293b2']['branches'])
        # Table-2 consumer reached only via the veneer at 0x1134cea.
        self.assertIn('0x1134cea', chains['0x6102a608']['veneers'])
        # The veneer cell is called from the diagnostic dispatcher (0x1126d1e).
        self.assertIn(['0x1126d1e', 'b.w'], chains['0x1134cea']['branches'])
        # TestEram: BL from the qctest state machine + veneer from the dispatcher.
        self.assertIn(['0x6108104e', 'bl'], chains['0x6103f4b2']['branches'])
        self.assertIn('0x1134c7c', chains['0x6103f4b2']['veneers'])
        self.assertIn(['0x1126bba', 'bl'], chains['0x1134c7c']['branches'])
        # The qctest state machine has no direct entry: one pointer-table word.
        self.assertEqual(chains['0x61080fe1']['words'], ['0x6117b0f0'])
        self.assertEqual(chains['0x61080fe1']['branches'], [])

    def test_manager_upload_wrappers_are_pinned(self):
        chains = self.report['call_chains']
        self.assertEqual(chains['0x1135099']['words'], ['0x61176494'])
        self.assertEqual(chains['0x11350a9']['words'], ['0x61176498'])
        self.assertEqual(self.core.u32(0x6117647c + 0x18), 0x1135099)
        self.assertEqual(self.core.u32(0x6117647c + 0x1c), 0x11350a9)

    def test_efct_context_word_is_nonzero_in_image(self):
        self.assertNotEqual(self.report['efct_context_word_0x2009bbf8'], '0x0')

    def test_manager_cells_still_zero_in_stock_image(self):
        self.assertEqual(self.report['manager_cells'],
                         {'0x20084b8c': '0x0', '0x20084ba0': '0x0',
                          '0x20084bb4': '0x0'})


if __name__ == '__main__':
    unittest.main()