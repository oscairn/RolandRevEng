"""Check native circular save/restore banks and bounded DSP control candidates."""
import hashlib

from bmc_dsp import command_count, packets
from line_shaping_study import NATIVE_SHA256, _finite


def _cache(slots, cursor):
    if type(cursor) is not int or cursor not in (0, 1, 2):
        raise ValueError('Expected a valid native cache cursor 0, 1 or 2')
    if not isinstance(slots, list) or len(slots) != 3:
        raise ValueError('Expected three explicit native cache slots')
    return [_finite(value) for value in slots]


def cache_push(slots, cursor, value):
    slots = _cache(slots, cursor)
    slots[cursor] = _finite(value)
    return slots, (cursor+1) % 3


def cache_pop(slots, cursor):
    slots = _cache(slots, cursor)
    cursor = (cursor-1) % 3
    return slots[cursor], cursor


def inventory():
    import lib
    import parse
    from header_study import families, UnsupportedLayout

    rows, collisions = [], []
    for cls, (_, _, lists) in sorted(lib.pairs().items()):
        if not any(item[1] == 0 for item in lists or []):
            continue
        length, program, *_ = parse.program(cls)
        for offset, words in packets(program[:length]):
            try:
                kinds = families(words[0])
            except UnsupportedLayout:
                kinds = [None]*command_count(words[0])
            for operation, control in enumerate(words[1:1+command_count(words[0])]):
                if control & 0xffe != 0xf60:
                    continue
                item = dict(cls=cls, packet=offset, header=words[0], operation=operation,
                            control=control, family=kinds[operation], semantic_admission=False)
                if control & 0x8000:
                    rows.append(dict(**item, source_index_candidate=(control >> 12) & 7,
                                     action_candidate='restore' if control & 1 else 'save'))
                else:
                    collisions.append(item)
    return dict(candidates=rows, low_pattern_collisions=collisions)


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from weighted_mix_study import require_instructions, require_words

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    rows = dict(packets(program))
    require_words(rows, 0x78, (0x88cf, 0x1c8b, 0x5d8f, 0xaf60, 0xef60))
    require_words(rows, 0xa4, (0xb149, 0x08c2, 0x49c6, 0xaf61, 0xef61))
    require_words(rows, 0x3e, (0x5f07, 0x08c2, 0x48c6, 0x2fe0, 0x6fe2, 0x29, 0x2c))
    require_instructions(native, 0x305230, (
        ('add', 'x14, x12, #0x80'), ('ldr', 'w9, [x12, #0x98]'), ('cmp', 'x9, #2'),
        ('str', 'd2, [x14, x9, lsl #3]'), ('csinc', 'w15, wzr, w9, hs')))
    require_instructions(native, 0x305268, (
        ('sub', 'w16, w15, #1'), ('mov', 'w9, #2'), ('cmp', 'w15, #0'),
        ('csel', 'w15, w9, w16, eq'), ('ubfiz', 'x17, x15, #3, #0x20'),
        ('ldr', 'd5, [x14, x17]'), ('str', 'w15, [x12, #0x98]')))
    require_instructions(native, 0x30530c, (
        ('add', 'x16, x12, #0x100'), ('ldr', 'w1, [x12, #0x118]'), ('cmp', 'x1, #2'),
        ('csinc', 'w3, wzr, w1, hs'), ('str', 'd2, [x16, x1, lsl #3]')))
    require_instructions(native, 0x30533c, (
        ('sub', 'w1, w3, #1'), ('cmp', 'w3, #0'), ('csel', 'w1, w9, w1, eq'),
        ('ubfiz', 'x3, x1, #3, #0x20'), ('ldr', 'd5, [x16, x3]'), ('str', 'w1, [x12, #0x118]')))
    require_instructions(native, 0x3050f8, (('ldr', 'x9, [x0, #8]'), ('ldr', 'x12, [x9, #0x18]')))
    for register, start, end in (('x12', 0x305100, 0x305354),
                                  ('x14', 0x305234, 0x305284),
                                  ('w15', 0x305244, 0x305268),
                                  ('x16', 0x305310, 0x305354),
                                  ('w3', 0x30531c, 0x30533c),
                                  ('w9', 0x305270, 0x305344)):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    md = lib.md()
    md.detail = True
    ctor = {ins.address: ins for ins in md.disasm(lib.Z[0x16bb04:0x16bc38], 0x16bb04)}
    preserved([ctor[pc] for pc in range(0x16bb04, 0x16bb38, 4)], 'x0')
    require_instructions(ctor, 0x16bb38,
                         tuple(('str', f'wzr, [x0, #{offset:#x}]') for offset in range(0x58, 0x1d9, 0x20)))
    additions = []
    for load, field, address, save, restore, intermediate, add, mac, final, final_field, final_cell, acc in (
            (0x3051ec, 0x48, 0x29, 0x30523c, 0x30527c, 0x3052ac, 0x3052bc,
             0x3052c0, 0x305398, 0x10a, 0x24, 'd1'),
            (0x3052d0, 0x4a, 0x2c, 0x30531c, 0x30534c, 0x30537c, 0x305388,
             0x30539c, 0x3053ac, 0x10c, 0x25, 'd0')):
        preserved([native[pc] for pc in range(load+4, save, 4)], 'd2')
        preserved([native[pc] for pc in range(restore+4, add, 4)], 'd5')
        require_instructions(native, load, (('ldr', 'd2, [x11, w14, uxtw #3]'),)
                             if load == 0x3051ec else (('ldr', 'd2, [x11, w1, uxtw #3]'),))
        require_instructions(native, add, (('fadd', 'd2, d5, d2'),))
        require_instructions(native, mac, (('fmadd', f'{acc}, d2, d3, {acc}'),))
        preserved([native[pc] for pc in range(intermediate+4, add, 4)], 'd2')
        preserved([native[pc] for pc in range(add+4, mac, 4)], 'd2')
        preserved([native[pc] for pc in range(mac+4, final, 4)], acc)
        before_field, before_cell = (0xd2, 0x28) if acc == 'd1' else (0xd6, 0x2b)
        source = checked_access(native, fields, trace, load, 'read', field, address)
        before = checked_access(native, fields, trace, intermediate, 'write', before_field, before_cell)
        after = checked_access(native, fields, trace, final, 'write', final_field, final_cell)
        if (native[intermediate].reg_name(native[intermediate].operands[0].reg) != 'd2'
                or native[final].reg_name(native[final].operands[0].reg) != acc
                or any(int.from_bytes(program[relative:relative+2], 'big') != cell
                       for relative, cell in ((before_field, before_cell), (final_field, final_cell)))):
            raise ValueError('FDRV additive cutpoint store register or DSP field differs')
        additions.append(dict(saved_source=source, coissued_incoming_store=before,
                              native_add=add, native_mac=mac, following_main_store=after,
                              input_register_candidate=2 if acc == 'd1' else 6,
                              result_register_candidate=1 if acc == 'd1' else 5))
    require_words(rows, 0xc0, (0xb8cf, 0x1c42, 0x5d46, 0x9fe0, 0x3fe2, 0xdfe4, 0x7fe6, 0x2fe8, 0x6fea))
    require_words(rows, 0xde, (0x8f4d, 0x044b, 0x454f, 0x1fe4, 0x3fe6, 0x5fe8, 0x7fea, 0, 4))
    for pc in (0x3052b4, 0x305380):
        if dict(pc=pc, slot=13, width=4) not in trace['coefficient_reads']:
            raise ValueError('FDRV first additive consumer coefficient provenance differs')
    if rows[0xc0][10] != 0xc00d or rows[0xc0][12] != 0xc00d:
        raise ValueError('FDRV additive consumer coefficient fields differ')
    return dict(native_sha256=NATIVE_SHA256,
                native_banks=[dict(save_control=0xaf60, restore_control=0xaf61, bank=0x80, cursor=0x98),
                              dict(save_control=0xef60, restore_control=0xef61, bank=0x100, cursor=0x118)],
                constructor_cursor_zero_offsets=list(range(0x58, 0x1d9, 0x20)),
                save_slice=[0x305230, 0x305244], restore_slice=[0x305268, 0x305284],
                first_filter_addition_cutpoints=additions,
                inventory=inventory(), native_cache_slots=3, valid_cursors=[0, 1, 2],
                paired_roundtrip_introduces_sample_delay=False,
                invalid_native_cursor_behavior_verified=False,
                all_candidate_port_bindings_verified=False, hardware_stack_depth_verified=False,
                native_execution_verified=False, isolated_opcode_admission=False)


def native_probes(cases):
    import ctypes
    import struct
    import lib
    from native_callback_fixture import executable_mapping

    cases = list(cases)
    expected = []
    for slots, cursor, value in cases:
        saved, next_cursor = cache_push(slots, cursor, value)
        restored, end_cursor = cache_pop(saved, next_cursor)
        expected.append((saved, restored, end_cursor))
    checked = report()
    # Authored ABI moves surround the original, separately checked save/restore slices.
    prefix, suffix = bytes.fromhex('ec0300aa0240601e'), bytes.fromhex('a040601ec0035fd6')
    code = prefix + b''.join(lib.Z[start:end] for start, end in
                              (checked['save_slice'], checked['restore_slice'])) + suffix
    shapes = [(ins.mnemonic, ins.op_str) for ins in lib.md().disasm(prefix+suffix, 0)]
    if shapes != [('mov', 'x12, x0'), ('fmov', 'd2, d0'), ('fmov', 'd0, d5'), ('ret', '')]:
        raise ValueError('Authored cache fixture ABI moves differ')
    results = []
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_void_p, ctypes.c_double)(address)
        for (slots, cursor, value), (saved, restored, end_cursor) in zip(cases, expected, strict=True):
            image = bytearray(b'\xa5'*0x120)
            struct.pack_into('<3dI', image, 0x80, *_cache(slots, cursor), cursor)
            wanted = image.copy()
            struct.pack_into('<3dI', wanted, 0x80, *saved, end_cursor)
            owner = ctypes.create_string_buffer(bytes(image), len(image))
            actual = invoke(ctypes.addressof(owner), value)
            if actual.hex() != restored.hex() or bytes(owner) != wanted:
                raise ValueError('Native auxiliary roundtrip result or memory differs')
            results.append(dict(restored=actual, cursor=end_cursor, slots=saved))
    return results


def native_add_probes(cases):
    import ctypes
    import math
    import lib
    from line_shaping_study import _float32
    from native_callback_fixture import executable_mapping

    inputs = [tuple(map(_finite, case)) for case in cases]
    if any(len(case) != 4 for case in inputs) or not hasattr(math, 'fma'):
        raise ValueError('Expected A, W, S, factor and Python 3.13+ math.fma')
    inputs = [(a, w, s, _float32(factor)) for a, w, s, factor in inputs]
    try:
        expected = [_finite(math.fma(_finite(w+s), factor, a)) for a, w, s, factor in inputs]
    except OverflowError as error:
        raise ValueError('Native add/MAC probe exceeds the finite reference domain') from error
    report()
    prefix = bytes.fromhex('4540601e2440601e0140601e8240601e')
    suffix = bytes.fromhex('2040601ec0035fd6')
    if [(i.mnemonic, i.op_str) for i in lib.md().disasm(prefix+suffix, 0)] != [
            ('fmov', 'd5, d2'), ('fmov', 'd4, d1'), ('fmov', 'd1, d0'),
            ('fmov', 'd2, d4'), ('fmov', 'd0, d1'), ('ret', '')]:
        raise ValueError('Authored add/MAC fixture ABI moves differ')
    code = prefix+lib.Z[0x3052bc:0x3052c4]+suffix
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(ctypes.c_double, *([ctypes.c_double]*4))(address)
        actual = [invoke(*case) for case in inputs]
    if any(a.hex() != b.hex() for a, b in zip(actual, expected, strict=True)):
        raise ValueError('Native add/MAC cutpoint reference differs')
    return actual


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        result['native_probes'] = native_probes([([-11, 23, -37], cursor, .125) for cursor in range(3)])
        result['native_execution_verified'] = True
    print(json.dumps(result, indent=2, allow_nan=False))
