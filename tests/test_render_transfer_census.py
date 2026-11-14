import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import command_count, swap_words
from render_transfer_census import (NATIVE_PROVENANCED_TAGS, RARE_TAGS,
                                    scan_segments, study, transfer_form)


def stored(words):
    """Stored LE32 form of a logical big-endian halfword stream, word padded."""
    stream = b''.join(word.to_bytes(2, 'big') for word in words)
    if len(stream) % 4:
        stream += b'\0\0'
    return b''.join(word[::-1] for word in (stream[i:i + 4] for i in range(0, len(stream), 4)))


def segment(length_halfwords, dsp=5, base=0x4020):
    """Segment geometry: length is the logical halfword count; stored data may
    be word-padded wider (scan trims to length like the loader)."""
    return ((base, length_halfwords * 2, length_halfwords * 2, 0), dsp)


class FormTests(unittest.TestCase):
    def test_admitted_controls(self):
        self.assertTrue(transfer_form(0x0fe0))
        self.assertTrue(transfer_form(0xcfe2))
        self.assertTrue(transfer_form(0x8fe8))

    def test_rejected_controls(self):
        self.assertFalse(transfer_form(0x0fe1))  # odd bit-0 form
        self.assertFalse(transfer_form(0x0da0))  # not the fe window
        self.assertFalse(transfer_form(0xfff0))  # wrong window
        self.assertFalse(transfer_form(0x0000))

    def test_6fe4_trap_word_is_admitted_form(self):
        # Run 11's slot-0 trap: 6fe4 has bit 0 clear, so the census reads its
        # pool word; its address tag f is a RARE_TAG and every occurrence is
        # recorded. (28 occurrences corpus-wide are the trap packets.)
        self.assertTrue(transfer_form(0x6fe4))
        self.assertIn(0xF, RARE_TAGS)


class ScanTests(unittest.TestCase):
    def test_load_and_store_are_counted(self):
        result = scan_segments(stored([0x0c03, 0x0fe0, 0x2016]), [segment(3, 5)])
        self.assertEqual(result['counts']['transfer_controls'], 1)
        self.assertEqual(result['counts']['port_0'], 1)
        self.assertEqual(result['tags']['2']['loads'], 1)
        self.assertEqual(result['tags']['2']['stores'], 0)
        result = scan_segments(stored([0x0c03, 0x8fe0, 0x0056]), [segment(3, 5)])
        self.assertEqual(result['tags']['0']['stores'], 1)
        self.assertEqual(result['counts']['port_8'], 1)

    def test_tag_is_pool_word_top_nibble(self):
        result = scan_segments(stored([0x0c03, 0x0fe0, 0xc055]), [segment(3, 5)])
        self.assertEqual(result['tags']['c']['accesses'], 1)
        self.assertEqual(result['tags']['c']['min_address'], 0x55)
        self.assertEqual(result['tags']['c']['max_address'], 0x55)
        result = scan_segments(stored([0x0c03, 0x0fe0, 0x2016]), [segment(3, 5)])
        self.assertEqual(result['tags']['2']['accesses'], 1)

    def test_odd_form_counted_not_tagged(self):
        result = scan_segments(stored([0x0c03, 0x0fe1, 0x2016]), [segment(3, 5)])
        self.assertEqual(result['counts']['odd_form_controls'], 1)
        self.assertNotIn('transfer_controls', result['counts'])
        self.assertEqual(result['tags']['2']['accesses'], 0)

    def test_pool_index_overflow_counted(self):
        # 0x0c06: length 6 = 1 count + 4 pool words. Control 0x0fe8 -> pool
        # index 4, one past the pool: counted, never guessed.
        words = [0x0c06, 0x0fe8, 0x2016, 0, 0, 0]
        result = scan_segments(stored(words), [segment(6, 5)])
        self.assertEqual(result['counts']['pool_index_overflow'], 1)
        self.assertEqual(result['tags']['2']['accesses'], 0)

    def test_unframeable_segment_counted(self):
        # count-4 header with one control: packets() raises, counted not fatal.
        words = [0x4709, 0x044b]
        result = scan_segments(stored(words), [segment(2, 5)])
        self.assertEqual(result['counts']['unframeable_segments'], 1)
        self.assertNotIn('transfer_controls', result['counts'])

    def test_rare_context_fields(self):
        # 0x0c03: count 1, length 3 = header + control + one pool word. Control
        # 0x0fe0 -> pool index 0 -> address 0x1999 (tag 1, a RARE_TAG): loads.
        words = [0x0c03, 0x0fe0, 0x1999]
        result = scan_segments(stored(words), [segment(3, 5)])
        rare = result['rare_contexts']
        self.assertEqual(len(rare), 1)
        context = rare[0]
        self.assertEqual(context['dsp'], 5)
        self.assertEqual(context['base'], 0x4020)
        self.assertEqual(context['offset'], 0)
        self.assertEqual(context['header'], 0x0c03)
        self.assertEqual(context['controls'], ['0fe0'])
        self.assertEqual(context['pool'], ['1999'])
        self.assertEqual(context['port'], 0)
        self.assertEqual(context['address'], '1999')
        self.assertEqual(result['tags']['1']['accesses'], 1)
        self.assertEqual(result['tags']['1']['min_address'], 2457)

    def test_program_and_dsp_attribution(self):
        words = [0x0c03, 0x0fe0, 0x2016]
        result = scan_segments(stored(words), [segment(3, dsp=4)])
        self.assertEqual(result['tags']['2']['dsps'], [4])
        self.assertEqual(result['tags']['2']['programs'], 1)
        result = scan_segments(stored(words),
                               [segment(3, dsp=4),
                                segment(3, dsp=5, base=0x8040)])
        self.assertEqual(result['tags']['2']['dsps'], [4, 5])
        self.assertEqual(result['tags']['2']['programs'], 2)

    def test_rare_and_native_sets(self):
        self.assertEqual(RARE_TAGS, frozenset({1, 3, 0xF}))
        self.assertEqual(NATIVE_PROVENANCED_TAGS, frozenset({0, 2, 4, 0xC}))


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_CORPUS = ((CORPUS / 'zen_arm64').exists()
              and (CORPUS / 'zenology_inventory.json').exists()
              and (CORPUS / 'b0c1a.bin').exists() and (CORPUS / 'b1c1a.bin').exists()
              and all((CORPUS / rel).exists() for rel in
                      ('crossmodel/jupiter-x/MI077_C1A_up.bin',
                       'crossmodel/mc101/RPG69_C1A_up.bin',
                       'crossmodel/sh-4d/DD013_C1A_up.bin')))


@unittest.skipUnless(HAS_CORPUS, 'Pinned cross-image corpus required')
class CorpusTests(unittest.TestCase):
    def test_pinned_totals(self):
        totals = study(str(CORPUS))['totals']
        self.assertEqual(totals['transfer_controls'], 529931)
        self.assertEqual(totals['framed_segments'], 5635)
        self.assertEqual(totals['framed_packets'], 473989)
        self.assertEqual(totals.get('unframeable_segments', 0), 136)
        self.assertEqual(totals.get('odd_form_controls', 0), 88)
        self.assertEqual(totals.get('pool_index_overflow', 0), 0)
        self.assertEqual(totals['observed_tags'],
                         ['0', '1', '2', '3', '4', '6', '8', 'a', 'c', 'e', 'f'])
        self.assertEqual(totals['absent_tags'], ['5', '7', '9', 'b', 'd'])
        self.assertEqual(totals['native_provenanced_tags'], ['0', '2', '4', 'c'])

    def test_pinned_tag_counts(self):
        totals = study(str(CORPUS))['totals']
        expected = {'tag_0_accesses': 381028, 'tag_1_accesses': 134,
                    'tag_2_accesses': 40997, 'tag_3_accesses': 134,
                    'tag_4_accesses': 33066, 'tag_6_accesses': 725,
                    'tag_8_accesses': 1299, 'tag_a_accesses': 8107,
                    'tag_c_accesses': 55850, 'tag_e_accesses': 8474,
                    'tag_f_accesses': 117}
        for key, value in expected.items():
            self.assertEqual(totals[key], value, key)

    def test_pinned_per_image_counts(self):
        result = study(str(CORPUS))
        expected = (('zen_arm64', 17957, 177, 128), ('b0c1a', 37626, 377, 0),
                    ('b1c1a', 145138, 1632, 1), ('MI077_C1A_up.bin', 100092, 979, 0),
                    ('RPG69_C1A_up.bin', 143736, 1561, 6),
                    ('DD013_C1A_up.bin', 85382, 909, 1))
        for name, transfers, framed, unframeable in expected:
            counts = result[name]['counts']
            self.assertEqual(counts['transfer_controls'], transfers, name)
            self.assertEqual(counts['framed_segments'], framed, name)
            self.assertEqual(counts.get('unframeable_segments', 0),
                             unframeable, name)

    def test_pinned_singleton_tags(self):
        # Tags 1 and 3 hit exactly one address each, loads only, in dsp4/5
        # GASS-type programs (the negative-short-add 5e09 family neighborhoods);
        # the desktop image reaches them from dsp0 programs.
        result = study(str(CORPUS))
        for name in ('zen_arm64', 'b0c1a', 'b1c1a', 'MI077_C1A_up.bin',
                     'RPG69_C1A_up.bin', 'DD013_C1A_up.bin'):
            for tag in ('1', '3'):
                row = result[name]['tags'][tag]
                self.assertEqual(row['distinct_addresses'], 1, (name, tag))
                self.assertEqual(row['min_address'], row['max_address'], (name, tag))
                self.assertEqual(row['stores'], 0, (name, tag))
                self.assertEqual(set(row['dsps']) <= {0, 4, 5}, True, (name, tag))

    def test_pinned_tag1_tag3_addresses(self):
        result = study(str(CORPUS))
        addresses = {'1': set(), '3': set()}
        for name in ('zen_arm64', 'b0c1a', 'b1c1a', 'MI077_C1A_up.bin',
                     'RPG69_C1A_up.bin', 'DD013_C1A_up.bin'):
            for tag in addresses:
                row = result[name]['tags'][tag]
                if row['accesses']:
                    addresses[tag].add(row['min_address'])
        self.assertEqual(addresses['1'], {2457})  # 0x999 low 12 bits of 1999
        self.assertEqual(addresses['3'], {1695})  # 0x69f low 12 bits of 369f

    def test_pinned_native_tags_are_majority(self):
        # Tags 0/2/4/c carry 511k of 530k accesses; the unprovenanced tags
        # (1/3/6/8/a/e/f) are a minority. This is the scoping claim, not proof.
        totals = study(str(CORPUS))['totals']
        native = sum(totals[f'tag_{t}_accesses']
                     for t in ('0', '2', '4', 'c'))
        other = sum(totals[f'tag_{t}_accesses']
                    for t in ('1', '3', '6', '8', 'a', 'e', 'f'))
        self.assertEqual(native, 381028 + 40997 + 33066 + 55850)
        self.assertEqual(native + other, totals['transfer_controls'])
        self.assertGreater(native, other * 5)

    def test_run19_census_still_frames(self):
        # Cross-check: b0c1a framed segment count equals run 19's census.
        from program_slot_census import frame_lists
        from core1 import Core1
        core = Core1(CORPUS / 'b0c1a.bin')
        self.assertEqual(sum(len(row['segments']) for row in frame_lists(core)), 377)


if __name__ == '__main__':
    unittest.main()