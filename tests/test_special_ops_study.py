import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from special_ops_study import indirect_symbols, math_cutpoints


class SymbolTests(unittest.TestCase):
    def test_only_indirect_symbol_rows_are_imported(self):
        self.assertEqual(indirect_symbols('Indirect symbols for section\n'
                                         '0x00001000 17 _exp\n0x0000100c 18 _log\n'
                                         '0x00001018 missing _sin\n'),
                         {0x1000: '_exp', 0x100c: '_log'})


@unittest.skipUnless(importlib.util.find_spec('capstone'), 'Capstone not installed')
class CutpointTests(unittest.TestCase):
    # Authored fixture: a proven object/data path, two distinct constructor-record
    # fields, an unchanged D0 argument store, a local call and its direct return store.
    CODE = bytes.fromhex('f30300aa 741640f9 750640f9 b50e40f9 b50a40f9 b50e40f9 '
                         '880641b9 08290012 00106e1e a05a28fc 05000094 880e41b9 '
                         '08290012 a05a28fc c0035fd6 c0035fd6')
    FIELDS = {0x104: ('field', 0x104, 0x20, 7), 0x10c: ('field', 0x10c, 0x50, 7)}

    def check(self, data=None, symbols=None):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        md.detail = True
        return math_cutpoints(list(md.disasm(data or self.CODE, 0x1000)), self.FIELDS,
                              {0x103c: '_exp'} if symbols is None else symbols)

    def test_equal_numeric_addresses_keep_distinct_field_provenance(self):
        row = self.check()['calls'][0]
        self.assertEqual(row['call'], 0x1028)
        self.assertEqual(row['input_store']['relative'], 0x20)
        self.assertEqual(row['output_store']['relative'], 0x50)
        self.assertEqual(row['input_store']['address'], row['output_store']['address'])

    def test_argument_and_return_overwrites_do_not_claim_identity(self):
        fadd = bytes.fromhex('0028601e')  # fadd d0,d0,d0
        inserted = self.CODE[:40] + fadd + self.CODE[40:]
        row = self.check(inserted, {0x1040: '_exp'})['calls'][0]
        self.assertIsNone(row['input_store'])
        self.assertIsNotNone(row['output_store'])
        for writer in (fadd, bytes.fromhex('00e4004f')):  # movi v0.16b,#0 overlaps D0
            overwritten = self.CODE[:44] + writer + self.CODE[48:]
            self.assertIsNone(self.check(overwritten)['calls'][0]['output_store'])

    def test_wrong_data_path_branch_and_unknown_call_remain_unresolved(self):
        wrong_path = self.CODE[:20] + bytes.fromhex('b51640f9') + self.CODE[24:]  # final pointer load at +28
        row = self.check(wrong_path)['calls'][0]
        self.assertIsNone(row['input_store'])
        self.assertIsNone(row['output_store'])
        wrong_scale = self.CODE[:36] + bytes.fromhex('a04a28fc') + self.CODE[40:52] + bytes.fromhex('a04a28fc') + self.CODE[56:]
        row = self.check(wrong_scale)['calls'][0]
        self.assertIsNone(row['input_store'])
        self.assertIsNone(row['output_store'])
        branched = self.CODE[:32] + bytes.fromhex('02000014') + self.CODE[36:]
        self.assertEqual(self.check(branched)['calls'], [])
        result = self.check(symbols={})
        self.assertEqual(result['calls'], [])
        self.assertEqual(result['stop'], {'pc': 0x1028, 'mnemonic': 'bl'})


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT / 'local'))


@unittest.skipUnless(importlib.util.find_spec('capstone') and (CORPUS / 'zen_arm64').exists()
                     and (CORPUS / 'pairs.json').exists(), 'Capstone or local corpus not prepared')
class CorpusTests(unittest.TestCase):
    def test_two_native_exp_windows_and_branch_limit(self):
        from special_ops_study import study
        results = {row['cls']: row for row in study()}
        uplift = results['SIM_MFX_UPLIFT_EXCITER']
        self.assertEqual(uplift['exp_stub_calls'], 2)
        self.assertEqual([(row['input_store']['address'], row['output_store']['address'])
                          for row in uplift['calls']], [(8, 11), (6, 10)])
        self.assertEqual([[item['control'] for item in row['intervening_exceptional']]
                          for row in uplift['calls']], [[0x20a0], [0x20a5]])
        transient = results['SIM_MFX_TRANSIENT']
        self.assertEqual(transient['exp_stub_calls'], 2)
        self.assertEqual(transient['calls'], [])
        self.assertEqual(transient['stop'], {'pc': 0x1d6128, 'mnemonic': 'b.ge'})


if __name__ == '__main__':
    unittest.main()
