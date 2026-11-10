"""Actual stock fragments versus native-proven equations; no plugin execution."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
CORPUS = Path(os.environ.get('BMC_CORPUS_DIR', ROOT/'local'))
HAS_CORPUS = importlib.util.find_spec('capstone') and all(
    (CORPUS/name).exists() for name in ('zen_arm64', 'pairs.json', 'exports_dem.txt'))
NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
PROGRAMS = {
    'SIM_MFX_FETDRIVE': (0x8372f4, 0x1ca,
        'f9bba6a4925d42d331321ef4978f9d2f53b35b251c5074eef72e119ec3670689'),
    'SIM_MFX_LINEDRIVE': (0x7b47f4, 0x242,
        'a7306c45ee503e60061261f9fa0fde3f8dfc708e6c245b3868e917e6a7d3ea02'),
}
FRAGMENTS = {
    ('SIM_MFX_FETDRIVE', 0x16a): 'b3f2705a2b17a1a14069732abed9601c7f573d42a4d62e08cd70412493dbc424',
    ('SIM_MFX_LINEDRIVE', 0x1e2): 'ea486c0fd1b373ad63cb605bf403876b5377bef41aecde0d68b550353e5b4638',
    ('SIM_MFX_LINEDRIVE', 0x13e): '3093df0fae326f90368be9f7e01bf4bff4a5196bdf46517296b29d39a6c6cda3',
    ('SIM_MFX_LINEDRIVE', 0x190): 'b75c1844217c33115f7dadbabf7c2d2d1f382e4ad5ab48b46ea3efc38357338f',
}


@lru_cache(maxsize=1)
def stock_fragments():
    import lib
    import parse
    from mac_study import study as mix_study
    from mac_controls_study import study as controls_study

    assert hashlib.sha256(lib.Z).hexdigest() == NATIVE_SHA256
    programs = {}
    for cls, (stored, size, digest) in PROGRAMS.items():
        length, stream, *_ = parse.program(cls)
        segments = next(row[3] for row in lib.pairs()[cls][2] if row[1] == 0)
        assert max(segments, key=lambda row: row[1])[3] == stored
        assert length == size and hashlib.sha256(stream[:length]).hexdigest() == digest
        programs[cls] = stream[:length]
    tails = [row for row in mix_study() if row['status'] == 'matched']
    assert {row['cls'] for row in tails} == set(PROGRAMS)
    result = []
    for row in tails:
        assert row['expected'] == row['observed']
        assert (row['native_start'], row['native_end']) == {
            'SIM_MFX_FETDRIVE': (0x2f7de4, 0x2f81c4),
            'SIM_MFX_LINEDRIVE': (0x2df874, 0x2dfd94)}[row['cls']]
        result.append(dict(cls=row['cls'], kind='tail', **row['family']))
    checked = controls_study()['allpass_chains']
    assert checked['cls'] == 'SIM_MFX_LINEDRIVE' and len(checked['chains']) == 2
    for row in checked['chains']:
        assert row['verified'] and row['native_window']['verified'] and len(row['stores']) == 6
        assert (row['native_window']['start'], row['native_window']['end']) == {
            0x13e: (0x2dfad8, 0x2dfbc8), 0x190: (0x2dfbd8, 0x2dfcc8)}[row['family']['offset']]
        result.append(dict(cls=checked['cls'], kind='allpass', **row['family']))
    assert {(row['cls'], row['offset']) for row in result} == set(FRAGMENTS)
    for row in result:
        size = 60 if row['kind'] == 'tail' else 82
        row['program'] = programs[row['cls']][row['offset']:row['offset']+size]
        assert hashlib.sha256(row['program']).hexdigest() == FRAGMENTS[row['cls'], row['offset']]
    return result


TAIL_VECTORS = (
    (3/8, -5/16, 7/32, -11/64, 5/8, -3/16, 7/16, -9/32),
    (-13/32, 17/64, -19/128, 23/256, -7/16, 9/32, -11/64, 13/128),
    (5/64, 29/128, -31/256, 37/512, 15/32, -17/64, 19/128, 21/256),
)
ALLPASS_VECTORS = (
    (3/8, -5/16, 7/32, -3/8, 11/64, -13/128, 17/256),
    (-19/64, 23/128, -29/256, 5/16, 31/512, -37/1024, 41/2048),
    (43/128, -47/256, 53/512, -7/16, -59/1024, 61/2048, -67/4096),
)


def tail_case(fragment, values):
    left, right, wet_left, wet_right, dry, wet, post, master = values
    data = dict(zip(fragment['wet_addresses'], (wet_left, wet_right)))
    coefficients = dict(zip(fragment['coefficient_slots'], (dry, wet, post, master)))
    io = {0x2016: left, 0x2017: right}
    # Direct channel equations from the native polynomial proof, not interpreter code.
    mix_left = left*dry + wet_left*wet
    mix_right = right*dry + wet_right*wet
    after = [
        [left, None, None, dry, None, None, None, None],
        [left, wet_left, None, dry, None, None, None, wet],
        [mix_left, wet_left, None, dry, right, wet_right, None, wet],
        [mix_left, wet_left, None, post, mix_right, wet_right, None, wet],
        [mix_left*post, wet_left, None, master, mix_right*post, wet_right, None, wet],
        [(mix_left*post)*master, wet_left, None, master,
         (mix_right*post)*master, wet_right, None, wet],
    ]
    return data, coefficients, io, after, [{} for _ in after]


def allpass_case(fragment, values):
    x, a, b, k, c, d, e = values
    data = dict(zip(fragment['sources'], values))
    previous, stage0, stage1, stage2, output, copy = fragment['targets']
    # Unrolled recurrence independently established by all twelve native stores.
    u0 = a + (b-x)*k
    u1 = b + (c-u0)*k
    u2 = c + (d-u1)*k
    u3 = d + (e-u2)*k
    assert len(set((x, u0, u1, u2, u3))) == 5
    after = [
        [x, a, None, None, None, None, None, None],
        [x, a, b, k, None, None, None, None],
        [u0, c, b, k, None, None, None, None],
        [u1, c, d, k, None, None, None, None],
        [u2, e, d, k, None, None, None, None],
        [u3, e, d, k, None, None, None, None],
        [u3, e, d, k, None, None, None, None],
    ]
    writes = [{}, {previous: x}, {}, {stage0: u0}, {stage1: u1},
              {stage2: u2}, {output: u3, copy: u3}]
    return data, {}, None, after, writes


@unittest.skipUnless(HAS_CORPUS, 'Capstone and pinned native/pairs/exports artifacts required')
class NativeEvidenceTests(unittest.TestCase):
    def test_actual_fragment_identities_require_existing_native_proofs(self):
        self.assertEqual(len(stock_fragments()), 4)


@unittest.skipUnless(HAS_CORPUS, 'Capstone and pinned native/pairs/exports artifacts required')
class EmulatorCorpusTests(unittest.TestCase):
    def check_execution(self, fragment, data, coefficients, io, after, writes):
        from bmc_emulator import execute_fragment
        original = deepcopy((data, coefficients, io))
        result = execute_fragment(fragment['program'], data, coefficients, io)
        self.assertEqual((data, coefficients, io), original)
        self.assertIsNot(result['data'], data)
        expected_data = dict(data)
        for event in writes:
            expected_data.update(event)
        self.assertEqual(result['data'], expected_data)
        self.assertEqual(result['ports'], after[-1])
        offsets = [0, 10, 20, 34, 44, 54] if fragment['kind'] == 'tail' else [0, 10, 24, 34, 48, 62, 72]
        headers = [0x1e05, 0x1e05, 0x2b07, 0x1405, 0x2e05, 0x1503] if fragment['kind'] == 'tail' else [
            0x1e05, 0x3e07, 0x1405, 0x2b07, 0x2b07, 0x1405, 0x1e05]
        self.assertEqual(len(result['trace']), len(after))
        before = [None]*8
        for row, offset, header, current, stores in zip(result['trace'], offsets, headers, after, writes):
            self.assertEqual(row, dict(offset=offset, header=header, before=before,
                                       after=current, writes=stores))
            before = current
        return result

    def test_stereo_input_packet_in_both_stock_banks(self):
        import parse
        from bmc_emulator import execute_fragment
        from bmc_subset import disassemble_fragment

        from bmc_dsp import literal, packets
        from header_study import layout

        stock_fragments()  # Pins the native image and both primary programs.
        for cls, load in [('SIM_MFX_LINEDRIVE', 0x2df884), ('SIM_MFX_FETDRIVE', 0x2f7df4)]:
            _, _, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
            self.assertEqual([(ins.mnemonic, ins.op_str) for ins in code if load <= ins.address < load+12],
                             [('ldp', 'x12, x11, [x1]'), ('ldr', 'd0, [x12]'), ('ldr', 'd1, [x11]')])
            _, primary, peer, _, base, peer_base = parse.program(cls)
            self.assertEqual((base, peer_base), (0x4020, 0x8000))
            for blob, addresses in [(primary, [0x2016, 0x2017]), (peer, [0x2459, 0x245a])]:
                with self.subTest(cls=cls, addresses=addresses):
                    program = blob[4:14]
                    self.assertEqual(disassemble_fragment(program),
                                     dict(kind='stereo_input', input_addresses=addresses))
                    result = execute_fragment(program, {}, {}, dict(zip(addresses, (-5/8, 13/32))))
                    self.assertEqual(result['ports'], [-5/8, 13/32] + [None]*6)
                    fields = {}
                    literal_end = 0x2a if cls.endswith('LINEDRIVE') else 0x2e
                    for offset, words in packets(blob[14:literal_end]):
                        for field in layout(words)['fields']:
                            if field['role'] == 'literal':
                                start = 14 + offset + field['offset']
                                fields[start] = literal(blob[start:start+field['width']])
                    stereo_offsets = (0x24, 0x27) if cls.endswith('LINEDRIVE') else (0x28, 0x2b)
                    self.assertEqual(fields, {0x14: 0, 0x17: 0, **dict.fromkeys(stereo_offsets, 1)})

    def test_stock_scratch_packets_match_native_cell_and_output_provenance(self):
        import lib
        import parse
        from alu_study import coefficient_pointer_fields
        from bmc_emulator import execute_fragment
        from bmc_subset import disassemble_fragment
        from mac_controls_study import native_trace
        from mac_study import polynomial
        from operand_variants_study import check_bindings
        from transfer_study import constructor_memory, native_accesses, records_from_memory

        for fragment in stock_fragments():
            if fragment['kind'] != 'tail':
                continue
            cls = fragment['cls']
            with self.subTest(cls=cls):
                _, stream, *_ = parse.program(cls)
                start = fragment['offset']
                program = stream[start:start+80]
                scratch = disassemble_fragment(program)['scratch_addresses']
                self.assertEqual(scratch, [0x2b, 0x2c] if cls.endswith('LINEDRIVE') else [0x19, 0x1a])
                _, _, outputs, trace, native = native_trace(cls, fragment['wet_addresses'])
                ctor = parse.parse_ctor(cls)
                lo, hi = lib.func(ctor['ctor'])
                decoder = lib.md()
                decoder.detail = True
                constructor = list(decoder.disasm(lib.Z[lo:hi], lo))
                base, count, old_records = parse.parse_datsym(cls, ctor)
                records = records_from_memory(constructor_memory(constructor, lib.Z), base, count)
                self.assertEqual(records, old_records)
                fields = {base+8*i+4: dict(relative=relative, address=address)
                          for i, (relative, address) in enumerate(records)}
                accesses = native_accesses(native, fields, coefficient_pointer_fields(constructor))['accesses']
                # Native reloads reuse the constructor record for the DSP store operand.
                expected = [dict(kind=kind, relative=start+66+2*channel, address=address)
                            for kind in ('write', 'read')
                            for channel, address in enumerate(scratch)]
                instructions = {ins.address: ins for ins in native}
                proof = check_bindings(accesses, fields, expected, instructions)
                self.assertTrue(proof['verified'], proof)
                stores = {row['pc']: row for row in trace if row['kind'] == 'store'}
                fields_used = [row['object_field'] for row in proof['accesses']]
                self.assertEqual(fields_used[:2], fields_used[2:])
                self.assertNotEqual(*fields_used[:2])
                pc = [row['pc'] for row in proof['accesses']]
                self.assertEqual(pc, sorted(set(pc)))
                for channel in (0, 1):
                    self.assertEqual(polynomial(stores[pc[channel]]['value']), polynomial(outputs[channel]))
                    self.assertTrue(instructions[pc[channel+2]].op_str.startswith(f'd{channel}, '))
                for vector in TAIL_VECTORS:
                    data, coefs, io, after, _ = tail_case(fragment, vector)
                    data.update(dict(zip(scratch, (-99, 99))))
                    expected_writes = dict(zip(scratch, (after[-1][0], after[-1][4])))
                    result = execute_fragment(program, data, coefs, io)
                    self.assertEqual(result['ports'], after[-1])
                    self.assertEqual(result['data'], data | expected_writes)
                    self.assertEqual(result['trace'][-2]['writes'], expected_writes)
                    self.assertEqual(result['trace'][-1]['after'], after[-1])

    def test_stock_dry_wet_outputs_and_coefficient_load_timing(self):
        for fragment in stock_fragments():
            if fragment['kind'] != 'tail':
                continue
            for vector in TAIL_VECTORS:
                with self.subTest(cls=fragment['cls'], vector=vector):
                    data, coefficients, io, after, writes = tail_case(fragment, vector)
                    data[0x7ff] = 47/32
                    self.check_execution(fragment, data, coefficients, io, after, writes)

    def test_both_allpass_regions_all_six_stores_and_port_load_timing(self):
        for fragment in stock_fragments():
            if fragment['kind'] != 'allpass':
                continue
            for vector in ALLPASS_VECTORS:
                with self.subTest(offset=fragment['offset'], vector=vector):
                    data, coefficients, io, after, writes = allpass_case(fragment, vector)
                    data.update({address: (index+73)/16 for index, address in enumerate(fragment['targets'])})
                    data[0x7ff] = -83/32
                    self.check_execution(fragment, data, coefficients, io, after, writes)

    def test_adjacent_stock_allpass_outputs_feed_the_actual_tail_memory_reads(self):
        rows = {row['offset']: row for row in stock_fragments() if row['cls'] == 'SIM_MFX_LINEDRIVE'}
        first, second, tail = (rows[offset] for offset in (0x13e, 0x190, 0x1e2))
        self.assertEqual(first['offset']+len(first['program']), second['offset'])
        self.assertEqual(second['offset']+len(second['program']), tail['offset'])
        self.assertEqual([first['targets'][4], second['targets'][4]], tail['wet_addresses'])
        for frame, gains in enumerate(TAIL_VECTORS):
            with self.subTest(frame=frame):
                left, _, _, left_ports, left_writes = allpass_case(first, ALLPASS_VECTORS[frame])
                right, _, _, right_ports, right_writes = allpass_case(
                    second, ALLPASS_VECTORS[(frame+1) % len(ALLPASS_VECTORS)])
                current = {**left, **right, 0x7ff: -97/64}
                current.update({address: (index+101)/16 for index, address in
                                enumerate(first['targets']+second['targets'])})
                first_result = self.check_execution(first, current, {}, None, left_ports, left_writes)
                second_result = self.check_execution(
                    second, first_result['data'], {}, None, right_ports, right_writes)
                # Expected wet values come from independent equations. Do not inject
                # them into carried memory: the tail must read the emulator's stores.
                vector = (gains[0], gains[1], left_ports[-1][0], right_ports[-1][0], *gains[4:])
                _, coefficients, io, after, writes = tail_case(tail, vector)
                self.check_execution(tail, second_result['data'], coefficients, io, after, writes)

    def test_sequential_calls_copy_memory_and_do_not_reuse_result_or_trace_state(self):
        for fragment in stock_fragments():
            case, vectors = (tail_case, TAIL_VECTORS) if fragment['kind'] == 'tail' else (
                allpass_case, ALLPASS_VECTORS)
            current, saved = {0x7ff: 89/64}, []
            for frame, vector in enumerate(vectors):
                with self.subTest(cls=fragment['cls'], offset=fragment['offset'], frame=frame):
                    sources, coefficients, io, after, writes = case(fragment, vector)
                    current.update(sources)
                    result = self.check_execution(fragment, current, coefficients, io, after, writes)
                    for previous, snapshot in saved:
                        self.assertEqual(previous, snapshot)
                    saved.append((result, deepcopy(result)))
                    current = dict(result['data'])


if __name__ == '__main__':
    unittest.main()
