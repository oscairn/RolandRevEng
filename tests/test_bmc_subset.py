import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from bmc_dsp import packets, swap_words
from bmc_subset import assemble_allpass, assemble_fragment, assemble_tail, disassemble_fragment, disassemble_tail


def assignment():
    return dict(kind='dry_wet_tail', wet_addresses=[32, 33], coefficient_slots=[1, 2, 3, 4])


def filter_assignment():
    return dict(kind='allpass4', sources=list(range(7)), targets=list(range(7, 13)))


class SubsetTests(unittest.TestCase):
    def test_allpass_controls_and_pre_arithmetic_store_destinations(self):
        stream = assemble_fragment(filter_assignment())
        self.assertEqual(len(stream), 82)
        rows = [words for _, words in packets(stream)]
        self.assertEqual(rows[3], [0x2b07, 0x0e0b, 0x2fe2, 0x8fe4, 0x12c2, 5, 8])
        self.assertEqual(rows[4], [0x2b07, 0x0e0b, 0x1fe2, 0x8fe4, 0x22c1, 6, 9])
        self.assertEqual(rows[-1], [0x1e05, 0x8fe0, 0x8fe2, 11, 12])
        self.assertEqual(disassemble_fragment(stream), filter_assignment())
        for offset in (2, 10, 12, 24, 30, 40, 44, 54, 58, 64, 70, 74):
            altered = bytearray(stream)
            altered[offset] ^= 0x10
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_fragment(bytes(altered))
        for key, value in [('sources', [0, 1, 2, 3, 4, 5, 0x800]),
                           ('sources', [0, 1, 2, 3, 4, 5, False]), ('targets', [0, 8, 9, 10, 11, 12])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                assemble_allpass(dict(filter_assignment(), **{key: value}))

    def test_authored_assignment_matches_expected_controls_and_byte_order(self):
        stream = assemble_tail(assignment())
        self.assertEqual(len(stream), 60)
        decoded = packets(stream)
        self.assertEqual([offset for offset, _ in decoded], [0, 10, 20, 34, 44, 54])
        self.assertEqual(decoded[2][1], [0x2b07, 0x080b, 0x4fe2, 0x5fe4, 0x13c0, 0x2017, 33])
        self.assertEqual(swap_words(stream)[:4], bytes.fromhex('e00f051e'))
        self.assertEqual(disassemble_tail(stream), assignment())

    def test_resource_bounds_and_unsupported_schema_are_rejected(self):
        for key, value in [('wet_addresses', [0, 0x800]), ('wet_addresses', [0, 0]),
                           ('wet_addresses', [False, 1]), ('wet_addresses', [0]),
                           ('coefficient_slots', [0, 1, 2, 0x1000]),
                           ('coefficient_slots', [0, 1, 2, 2]), ('kind', 'oscillator')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                assemble_tail(dict(assignment(), **{key: value}))
        for spec in [None, [], dict(assignment(), schedule='guess')]:
            with self.assertRaises(ValueError):
                assemble_tail(spec)

    def test_unknown_extensions_tags_controls_trailing_and_truncated_data_fail(self):
        stream = assemble_tail(assignment())
        for offset in (0, 2, 8, 20, 22, 28, 34, 40, 44, 46, 54, 56):
            altered = bytearray(stream)
            altered[offset] ^= 0x10
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disassemble_tail(bytes(altered))
        for altered in (stream[:-1], stream + b'\0\1', b''):
            with self.assertRaises(ValueError):
                disassemble_tail(altered)

    def test_cli_storage_roundtrip_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            spec, target = Path(temporary) / 'spec.json', Path(temporary) / 'tail.bin'
            spec.write_text(json.dumps(assignment()))
            command = [sys.executable, str(ROOT / 'tools/bmc_subset.py')]
            result = subprocess.run(command + ['assemble', str(spec), str(target), '--stored'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), swap_words(assemble_tail(assignment())))
            result = subprocess.run(command + ['disassemble', str(target), '--stored'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), assignment())
            result = subprocess.run(command + ['assemble', str(spec), str(target)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), swap_words(assemble_tail(assignment())))

    def test_cli_allpass_padding_is_explicit_and_cannot_hide_extra_packets(self):
        with tempfile.TemporaryDirectory() as temporary:
            spec, target = Path(temporary) / 'spec.json', Path(temporary) / 'tail.bin'
            spec.write_text(json.dumps(filter_assignment()))
            command = [sys.executable, str(ROOT / 'tools/bmc_subset.py')]
            result = subprocess.run(command + ['assemble', str(spec), str(target), '--stored'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), swap_words(assemble_allpass(filter_assignment()) + b'\0\0'))
            read = command + ['disassemble', str(target), '--stored']
            result = subprocess.run(read + ['--length', '82'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), filter_assignment())
            for length in ('78', '83', '86', '-2'):
                result = subprocess.run(read + ['--length', length], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
            target.write_bytes(swap_words(assemble_allpass(filter_assignment()) + b'\0\1'))
            result = subprocess.run(read + ['--length', '82'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'pairs.json').exists()
                     and (CORPUS / 'zen_arm64').exists(), 'Capstone or local artifacts not prepared')
class SubsetCorpusTests(unittest.TestCase):
    def test_emitter_recreates_both_allpass_chains_with_native_store_checks(self):
        import parse
        from mac_controls_study import study

        checked = study()['allpass_chains']
        self.assertEqual(len(checked['chains']), 2)
        length, stream, *_ = parse.program(checked['cls'])
        for chain in checked['chains']:
            self.assertTrue(chain['verified'])
            self.assertEqual(len(chain['stores']), 6)
            spec = dict(kind='allpass4', sources=chain['family']['sources'], targets=chain['family']['targets'])
            encoded = assemble_fragment(spec)
            start = chain['family']['offset']
            self.assertEqual(encoded, stream[start:start + 82])
            self.assertEqual(disassemble_fragment(encoded), spec)

    def test_emitter_recreates_both_independently_matched_stock_tails(self):
        import parse
        from mac_study import match_dry_wet_family, study

        checked = [item for item in study() if item['status'] == 'matched']
        self.assertEqual({item['cls'] for item in checked}, {'SIM_MFX_FETDRIVE', 'SIM_MFX_LINEDRIVE'})
        for item in checked:
            length, stream, *_ = parse.program(item['cls'])
            family = match_dry_wet_family(packets(stream[:length]))
            spec = dict(kind='dry_wet_tail', wet_addresses=family['wet_addresses'],
                        coefficient_slots=family['coefficient_slots'])
            encoded = assemble_tail(spec)
            with self.subTest(cls=item['cls']):
                self.assertEqual(encoded, stream[family['offset']:family['offset'] + 60])
                self.assertEqual(disassemble_tail(encoded), spec)


if __name__ == '__main__':
    unittest.main()
