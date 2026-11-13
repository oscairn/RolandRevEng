"""Fail-closed checks for the ReadDspProg reference census; no device IO."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from read_dspprog_caller_census import (IMAGES, PUSH_R4R8LR, adr_references,
                                        census, expanded_initial_data,
                                        locate_read_dspprog, movw_movt_pairs,
                                        report)

CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))
HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None
HAS_CORPUS = HAS_CAPSTONE and (CORPUS / 'b0c1a.bin').exists()


class Stub:
    """Minimal core stand-in: low region, ERAM region and an identity mapper."""

    def __init__(self, data, eram_offset=0x40):
        self.data = bytearray(data)
        self.eram_offset = eram_offset

    def address(self, offset):
        if offset < self.eram_offset:
            return 0x01100000 + offset
        return 0x61000000 + offset - self.eram_offset


LOW_BASE = 0x01100000


class SyntheticTests(unittest.TestCase):
    def test_locator_matches_only_the_full_prologue_shape(self):
        # Real b0c1a ReadDspProg prologue bytes, dumped at 0x0112f74c this run:
        # push {r4-r8,lr}; mov r8,r3; cmp r0,#7; blt; orr.w r3,r1,r2; tst.w r3,#1.
        prologue = bytes.fromhex('2de9f0419846072807db' '41ea0203' '13f0010f')
        stub = Stub(prologue + b'\0' * 0xc0)  # scan window needs len > eram_offset
        self.assertEqual(list(locate_read_dspprog(stub)), [LOW_BASE])
        # One bit flipped in the push word kills the match.
        mutated = bytearray(prologue)
        mutated[0] ^= 1
        self.assertEqual(list(locate_read_dspprog(Stub(bytes(mutated) + b'\0' * 0xc0))), [])
        # The push alone, without the gate instructions: no match.
        self.assertEqual(list(locate_read_dspprog(Stub(prologue[:8] + b'\0' * 0xc0))), [])

    def test_movw_movt_pairs_use_real_image_bytes_and_exact_value(self):
        # Real pair from b0c1a at 0x1134380: movw ...,#0x5b77 / movt ...,#0x6101
        # materializing 0x61015b77 (bytes and value disassembled this run).
        pair = bytes.fromhex('45f6773c' 'c6f2011c')
        stub = Stub(pair + b'\0' * 16)
        self.assertEqual(movw_movt_pairs(stub, 0x61015b77), [LOW_BASE])
        # A one-bit different target: no hit.
        self.assertEqual(movw_movt_pairs(stub, 0x61015b76), [])
        # A one-bit flip in the stored MOVT halfword: no hit.
        mutated = bytearray(pair)
        mutated[5] ^= 1
        self.assertEqual(movw_movt_pairs(Stub(bytes(mutated) + b'\0' * 16),
                                         0x61015b77), [])

    def test_adr_references_use_real_image_bytes_and_exact_sum(self):
        # Real add.w r6, pc, #0x204 bytes from b0c1a at 0x112e74e (pc-relative
        # sum verified this run: 0x0112e750 + 0x204 = 0x0112e954). Planted at
        # stub offset 0 the same bytes compute 0x01100004 + 0x204.
        stub = Stub(bytes.fromhex('0ff20426') + b'\0' * 12)
        self.assertEqual(adr_references(stub, 0x01100004 + 0x204), [LOW_BASE])
        self.assertEqual(adr_references(stub, 0x01100004 + 0x205), [])
        # Planted at offset 2 the aligned pc is the same, so the same sum hits.
        stub2 = Stub(b'\0' * 2 + bytes.fromhex('0ff20426') + b'\0' * 10)
        self.assertEqual(adr_references(stub2, 0x01100004 + 0x204), [LOW_BASE + 2])

    def test_census_finds_a_planted_pointer_word_in_stored_and_expanded_regions(self):
        # Stored hit: target word placed in the ERAM region.
        target = 0x0112f74c
        data = bytearray(b'\0' * 0x40)
        struct.pack_into('<I', data, 0x20, target)
        stub = Stub(bytes(data))
        stub.scatter = lambda: [dict(destination=0x2008008c, source=0,
                                     length=0x10, handler=0x6100003c)]
        planted = b'\0' * 8 + struct.pack('<I', target) + b'\0' * 4
        expanded_calls = iter([planted])
        import read_dspprog_caller_census as module
        original = module.expanded_initial_data

        def fake_expansion(_core):
            record = dict(destination=0x2008008c, source=0, length=0x10,
                          handler=0x6100003c)
            return record, bytes(next(expanded_calls)), 12

        module.expanded_initial_data = fake_expansion
        try:
            result = census(stub, target)
        finally:
            module.expanded_initial_data = original
        self.assertEqual(result['stored_word_hits'], [stub.address(0x20)])
        self.assertEqual(result['expanded_ram_word_hits'], [0x2008008c + 8])
        # No planted pointer: both lists empty.
        clean = Stub(b'\0' * 0x40)
        clean.scatter = stub.scatter
        original2 = module.expanded_initial_data

        def fake_clean(_core):
            record = dict(destination=0x2008008c, source=0, length=0x10,
                          handler=0x6100003c)
            return record, b'\0' * 16, 12

        module.expanded_initial_data = fake_clean
        try:
            result = census(clean, target)
        finally:
            module.expanded_initial_data = original2
        self.assertEqual(result['stored_word_hits'], [])
        self.assertEqual(result['expanded_ram_word_hits'], [])


@unittest.skipUnless(HAS_CORPUS, 'Pinned Fantom CORE1 payloads and Capstone required')
class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core1 import Core1
        cls.cores = {name: Core1(str(CORPUS / f'{name}.bin')) for name in IMAGES}

    def test_both_images_locate_exactly_the_pinned_twin(self):
        for name, (sha256, addresses) in IMAGES.items():
            core = self.cores[name]
            self.assertEqual(hashlib.sha256(core.data).hexdigest(), sha256)
            self.assertEqual(list(locate_read_dspprog(core)),
                             [addresses['read_dspprog']])

    def test_twin_tables_are_value_identical_across_images(self):
        for name, (_sha256, addresses) in IMAGES.items():
            core = self.cores[name]
            for index, aperture in enumerate((0x41480000, 0x41580000, 0x41680000,
                                              0x41780000, 0x41880000, 0x41980000,
                                              0x41260000)):
                self.assertEqual(core.u32(addresses['aperture_table'] + 4 * index),
                                 aperture)
            self.assertEqual([core.u32(addresses['raw_ports'] + 4 * index)
                              for index in range(7)],
                             [0x41104700, 0x41105700, 0x41106700, 0x41107700,
                              0x41108700, 0x41109700, 0x41102700])

    def test_census_is_exhaustively_empty_in_both_images(self):
        for name, (sha256, addresses) in IMAGES.items():
            result = census(self.cores[name], addresses['read_dspprog'])
            for key in ('aligned_thumb_pointer_candidates', 'direct_branch_candidates',
                        'movw_movt_bx_candidates', 'movw_movt_constructor_pairs',
                        'adr_references', 'stored_word_hits', 'expanded_ram_word_hits'):
                self.assertEqual(result[key], [], msg=f'{name}.{key}')
            self.assertFalse(result['callers_found'] if 'callers_found' in result else False)

    def test_report_passes_and_pins_the_state_bytes(self):
        for name, (sha256, addresses) in IMAGES.items():
            result = report(self.cores[name], sha256, addresses)
            self.assertEqual(result['dma_state_byte'], addresses['dma_state'])
            self.assertFalse(result['callers_found'])
            self.assertFalse(result['execution_ready'])

    def test_report_fails_closed_on_a_one_bit_flip(self):
        import tempfile
        name, (sha256, addresses) = 'b0c1a', IMAGES['b0c1a']
        data = bytearray(self.cores[name].data)
        data[0x10] ^= 1  # any bit flip inside the low region changes the digest path
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as handle:
            handle.write(bytes(data))
        try:
            from core1 import Core1
            mutated = Core1(handle.name)
            with self.assertRaises(ValueError):
                report(mutated, sha256, addresses)
        finally:
            os.unlink(handle.name)

    def test_expanded_initial_data_matches_pinned_sizes(self):
        sizes = {'b0c1a': (0x478c, 0x1f43), 'b1c1a': (0x4710, 0x1c47)}
        for name, (expanded_bytes, consumed) in sizes.items():
            core = self.cores[name]
            record, data, used = expanded_initial_data(core)
            self.assertEqual(len(data), expanded_bytes, msg=name)
            self.assertEqual(used, consumed, msg=name)
            self.assertEqual(record['destination'], 0x2008008c, msg=name)
            self.assertEqual(record['handler'], 0x6100003c, msg=name)


if __name__ == '__main__':
    unittest.main()