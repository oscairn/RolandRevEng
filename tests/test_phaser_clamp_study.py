import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from phaser_clamp_study import check_join, clamp_reference, packet_context


class ReferenceTests(unittest.TestCase):
    def test_packet_targets_relocate_and_malformed_contexts_are_rejected(self):
        words = [0x1b04, 0xbedb, 0xafe0, 0x120]
        following = [0x3e07, 0xbfe0, 0x0fe2, 0x4fe4, 0x121, 0x110, 0x120]
        self.assertEqual(packet_context(words, following), dict(form='STPS', targets=[0x120, 0x121]))
        for bad_words, bad_next in ((words[:-1], following), (words, following[:-1]),
                                    ([0x1b04, 0x9ed9, 0xafe0, 0x120], following),
                                    (words[:-1]+[0x121], following), (words[:-1]+[0x800], following)):
            with self.assertRaises(ValueError):
                packet_context(bad_words, bad_next)

    def test_finite_clamp_and_signed_zero(self):
        for value in (-100, -1, -0.5, -0.0, 0.0, 0.5, 1, 100):
            expected = -1.0 if value < -1 else 1.0 if value > 1 else float(value)
            self.assertEqual(clamp_reference(value).hex(), expected.hex())
        for invalid in (True, None, '1', math.nan, math.inf, 10**1000):
            with self.subTest(value=type(invalid)), self.assertRaises(ValueError):
                clamp_reference(invalid)


HAS_CAPSTONE = importlib.util.find_spec('capstone') is not None


@unittest.skipUnless(HAS_CAPSTONE, 'Capstone required')
class JoinTests(unittest.TestCase):
    def test_numeric_forward_join_and_rejected_calls_backedges_and_clobbers(self):
        import capstone

        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        decoder.detail = True

        def code(first='1f2003d5', branch='02000014'):
            # Study-owned NOP / B +8 / NOP / NOP / NOP fixture.
            data = bytes.fromhex(first+branch+'1f2003d5'*3)
            return {ins.address: ins for ins in decoder.disasm(data, 0)}

        self.assertEqual(check_join(code(), 0, 12, 20), [dict(pc=4, target=12)])
        for branch in ('00000094', '00000014', '03000014', '00001fd6', '010000d4'):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                check_join(code(branch=branch), 0, 12, 20)
        with self.assertRaises(ValueError):
            check_join(code(first='e8031f2a'), 0, 12, 20)  # MOV W8,WZR clobbers X8.
        missing = code()
        del missing[8]
        with self.assertRaises(ValueError):
            check_join(missing, 0, 12, 20)


CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_NATIVE = HAS_CAPSTONE and all((CORPUS/name).exists() for name in
                                ('zen_arm64', 'pairs.json', 'exports_dem.txt'))


@unittest.skipUnless(HAS_NATIVE, 'Pinned native corpus required')
class CorpusTests(unittest.TestCase):
    @unittest.skipUnless((CORPUS/'b0c1a.bin').exists(), 'Pinned Fantom image required')
    def test_fantom_has_twelve_relocated_stps_form_contexts(self):
        from core1 import Core1
        from phaser_clamp_study import fantom_report

        result = fantom_report(Core1(CORPUS/'b0c1a.bin'))
        self.assertEqual(len(result['matches']), 12)
        self.assertEqual({row['form'] for row in result['matches']}, {'STPS'})
        self.assertEqual({row['descriptor'] for row in result['matches']}, {0x6112c8d8, 0x61137e20})
        self.assertTrue(all(row['targets'][1] == row['targets'][0]+1 for row in result['matches']))
        self.assertEqual(result['unmatched_bedb_contexts'], 22)
        self.assertFalse(result['algorithm_ownership_verified'])

    def test_both_late_store_pairs_have_complete_provenance(self):
        from phaser_clamp_study import report

        result = report()
        self.assertEqual([[row['pc'] for row in context['stores']] for context in result['contexts']],
                         [[0x149000, 0x14901c], [0x279128, 0x279144]])
        for context in result['contexts']:
            self.assertEqual([row['address'] for row in context['stores']], [18, 19])
            self.assertEqual(len(context['branches']), 6)
            self.assertEqual(len(context['checked_numeric_stores']), 6)
            self.assertEqual(context['result_store_port'], 3)
            self.assertFalse(context['input_port_verified'])
        self.assertFalse(result['isolated_opcode_admission'])
        import capstone
        from limit_control_study import native_context
        from transfer_study import native_accesses

        program, native, memory, fields, _ = native_context('SIM_MFX_STPS')
        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        decoder.detail = True
        bypass = 0x54000005 | (((0x148f00-0x148e94)//4) << 5)  # B.PL into STR, past address setup.
        for pc, data in ((0x148f00, bytes.fromhex('c00200f9')),
                         (0x148bf8, bytes.fromhex('c00200f9')),
                         (0x148e94, struct.pack('<I', bypass))):
            changed = dict(native)
            changed[pc] = next(decoder.disasm(data, pc))
            trace = native_accesses(list(changed.values()), fields, {})
            with self.subTest(pc=hex(pc)), patch('phaser_clamp_study.native_context',
                    return_value=(program, changed, memory, fields, trace)), self.assertRaises(ValueError):
                report()


@unittest.skipUnless(HAS_NATIVE and platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'macOS ARM64 and pinned native corpus required')
class ExecutionTests(unittest.TestCase):
    def test_native_clamp_boundary_and_random_finite_inputs(self):
        values = [-1e308, -1.4, math.nextafter(-1, -math.inf), -1, math.nextafter(-1, 0),
                  -0.0, -math.ulp(0.0), 0.0, math.ulp(0.0), math.nextafter(1, 0),
                  1, math.nextafter(1, math.inf), 1.4, 1e308]
        generator = random.Random(31)
        values += [generator.uniform(-100, 100) for _ in range(512)]
        code = ('import json,sys; from phaser_clamp_study import native_probes; '
                'print(json.dumps(native_probes(iter(json.load(sys.stdin)))))')
        env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'), BMC_CORPUS_DIR=str(CORPUS))
        run = subprocess.run([sys.executable, '-c', code], env=env, input=json.dumps(values),
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(json.loads(run.stdout)), len(values))
