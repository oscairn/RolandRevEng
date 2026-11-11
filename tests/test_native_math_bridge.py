import importlib.util
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_math_bridge import bind_math_calls, TRAMPOLINE

# Study-owned ABI snippets: save FP/LR, BL self placeholders, restore, RET.
ONE = bytes.fromhex('fd7bbfa9fd03009100000094fd7bc1a8c0035fd6')
TWO = bytes.fromhex('fd7bbfa9fd0300910000009400000094fd7bc1a8c0035fd6')
HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None


class InputTests(unittest.TestCase):
    def test_invalid_binding_shapes_are_rejected_before_decoding(self):
        for code, base, bindings in ((b'', 0, {}), (b'abc', 0, {}), (ONE, True, {}),
                (ONE, 0x1001, {}), (ONE, 0x1000, {}), (ONE, 0x1000, {0x1008: (None, 'log')}),
                (ONE, 0x1000, {0x1008: (0x1008, 'system')})):
            with self.subTest(base=base), self.assertRaises(ValueError):
                bind_math_calls(code, base, bindings)


@unittest.skipUnless(HAS_CAPSTONE, 'Capstone required')
class RelocationTests(unittest.TestCase):
    def test_nonzero_source_base_and_shared_stubs_preserve_other_bytes(self):
        import capstone

        with patch('native_math_bridge._math_address', return_value=0x123456789abcdef0):
            result, info = bind_math_calls(TWO, 0x1000, {0x1008: (0x1008, 'exp'), 0x100c: (0x100c, 'exp')})
        self.assertEqual(info['trampolines'], 1)
        self.assertEqual(info['callback_length'], len(TWO))
        self.assertEqual([row['trampoline_offset'] for row in info['calls']], [32, 32])
        self.assertEqual(result[32:40], TRAMPOLINE)
        self.assertEqual(struct.unpack_from('<Q', result, 40)[0], 0x123456789abcdef0)
        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        decoder.detail = True
        instructions = list(decoder.disasm(result[:len(TWO)], 0x1000))
        self.assertEqual([ins.operands[-1].imm for ins in instructions if ins.mnemonic == 'bl'], [0x1020, 0x1020])
        self.assertEqual(result[:8], TWO[:8])
        self.assertEqual(result[16:len(TWO)], TWO[16:])

    def test_extra_calls_wrong_targets_external_branches_and_pc_relative_data_are_rejected(self):
        valid = {0x1008: (0x1008, 'log')}
        mutations = [('wrong target', ONE, {0x1008: (0x100c, 'log')}),
                     ('missing call', TWO, valid),
                     ('extra binding', ONE, {**valid, 0x100c: (0x100c, 'exp')})]
        # Authored replacements at PC1004: B outside, BR X0, BLR X0, ADRP X0, LDR literal, SVC, RET.
        for name, word in (('b', 0x14000400), ('br', 0xd61f0000), ('blr', 0xd63f0000),
                           ('b.eq', 0x54008000), ('cbz', 0xb4008000), ('tbz', 0x36008000),
                           ('adrp', 0x90000000), ('ldr literal', 0x58000000),
                           ('svc', 0xd4000001), ('early ret', 0xd65f03c0)):
            mutations.append((name, ONE[:4]+struct.pack('<I', word)+ONE[8:], valid))
        mutations.append(('ret x0', ONE[:-4]+struct.pack('<I', 0xd65f0000), valid))
        mutations.append(('undecodable', ONE[:4]+bytes.fromhex('ffffffff')+ONE[8:], valid))
        for name, code, bindings in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                bind_math_calls(code, 0x1000, bindings)


@unittest.skipUnless(HAS_CAPSTONE and platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'macOS ARM64 and Capstone required')
class ExecutionTests(unittest.TestCase):
    def test_authored_one_and_two_call_functions_match_libm_in_isolated_process(self):
        code = '''import ctypes,json,math,sys
sys.path.insert(0,sys.argv[1])
from native_callback_fixture import executable_mapping
from native_math_bridge import bind_math_calls
result=[]
for raw,names,values in json.loads(sys.stdin.read()):
 data=bytes.fromhex(raw)
 expected={0x1008+4*i:(0x1008+4*i,name) for i,name in enumerate(names)}
 patched,metadata=bind_math_calls(data,0x1000,expected)
 with executable_mapping(patched) as address:
  invoke=ctypes.CFUNCTYPE(ctypes.c_double,ctypes.c_double)(address)
  for value in values:
   expected=value
   for name in names: expected=getattr(math,name)(expected)
   actual=invoke(value)
   assert actual.hex()==expected.hex(),(names,value,actual,expected)
   result.append(actual)
print(json.dumps(result))
'''
        cases = [(ONE.hex(), ['exp'], [-4, -0.5, 0, 0.5, 4]),
                 (ONE.hex(), ['log'], [0.125, 0.5, 1, 2, 10]),
                 (TWO.hex(), ['log', 'exp'], [0.125, 0.5, 1, 2, 10])]
        run = subprocess.run([sys.executable, '-c', code, str(ROOT/'tools')], input=json.dumps(cases),
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(json.loads(run.stdout)), 15)
