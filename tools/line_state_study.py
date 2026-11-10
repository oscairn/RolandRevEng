"""Read-only LINEDRIVE native ring ABI; no DSP circular addressing is inferred."""
import hashlib
import json
from pathlib import Path
import struct

NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
HISTORY_PAIRS = ((3, 4), (6, 7), (9, 10), (12, 13), (15, 16), (18, 19), (21, 22),
                 (24, 25), (27, 28), (30, 31), (33, 34), (36, 37))


def _u32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('Expected unsigned 32-bit field bits')
    return value


def native_ring_index(address, wrapper_base, ring_origin):
    """Index a native double element; address and P/O are explicit caller inputs."""
    return (_u32(address) + _u32(wrapper_base) - _u32(ring_origin)) & 0x7ff


def advance_native_origin(ring_origin):
    """Model descriptor slot0 once, not a LINEDRIVE callback or hardware tick."""
    return (_u32(ring_origin) + 1) & 0x7ff


def study():
    import capstone
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from operand_variants_study import check_bindings
    from transfer_study import constructor_memory, native_accesses, records_from_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native artifact')
    md = lib.md(); md.detail = True

    def expect(address, mnemonic, operands):
        ins = next(md.disasm(lib.Z[address:address+4], address), None)
        if ins is None or (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'Instruction differs at {address:#x}')

    for anchor in (
            (0x2ac178, 'add', 'x21, x21, #0xd30'),
            (0x2ac17c, 'add', 'x8, x21, #0x10'), (0x2ac180, 'str', 'x8, [x0]'),
            (0x2ac188, 'str', 'wzr, [x0, #0x20]'), (0x2ac190, 'str', 'x0, [x20, #0x40]'),
            (0x16bb1c, 'ldp', 'x8, x9, [x3, #0x40]'),
            (0x16bb7c, 'stp', 'x8, x9, [x0, #0x10]'),
            (0x16bbbc, 'str', 'wzr, [x8, #0x20]'),
            (0x16bbc0, 'str', 'x0, [x8, #0x18]'),
            (0x16bbc4, 'mov', 'w1, #0x4000'), (0x16bbc8, 'bl', '#0x6d87c4'),
            (0x2ac570, 'ldr', 'w8, [x0, #0x20]'), (0x2ac574, 'add', 'w8, w8, #1'),
            (0x2ac578, 'and', 'w8, w8, #0x7ff'), (0x2ac57c, 'str', 'w8, [x0, #0x20]'),
            (0x16c364, 'blr', 'x8'), (0x16c398, 'bl', '#0x16c1e8'),
            (0x16c39c, 'ldr', 'x0, [x19, #0x10]'), (0x16c3a0, 'ldr', 'x8, [x0]'),
            (0x16c3a4, 'ldr', 'x8, [x8]'), (0x16c3a8, 'blr', 'x8'),
            (0x2df6f0, 'mov', 'w0, #0x5a8'), (0x2df6f4, 'bl', '#0x6d8614'),
            (0x2df704, 'bl', '#0x2dfe04'), (0x2df708, 'str', 'x0, [x19, #0x28]'),
            (0x2df8a8, 'ldr', 'w13, [x0, #0x10]'),
            (0x2df8b4, 'ldr', 'w10, [x10, #0x20]'),
            (0x2df8b8, 'add', 'w14, w14, w13'), (0x2df8bc, 'sub', 'w14, w14, w10'),
            (0x2df8c0, 'and', 'w14, w14, #0x7ff'), (0x2df8cc, 'sub', 'w10, w13, w10'),
            (0x2dfa64, 'ldr', 'w13, [x8, #0xfc]'), (0x2dfa68, 'add', 'w13, w10, w13'),
            (0x2dfa6c, 'and', 'w13, w13, #0x7ff'),
            (0x2dfa70, 'ubfiz', 'x13, x13, #3, #0x20'),
            (0x2dfa74, 'ldr', 'd0, [x9, x13]'), (0x2dfab4, 'str', 'd0, [x9, x13]'),
            (0x2df9bc, 'str', 'd5, [x9, w15, uxtw #3]'),
            (0x2df9cc, 'str', 'd5, [x9, w15, uxtw #3]'),
            (0x2dfa50, 'str', 'd0, [x9, w13, uxtw #3]'),
            (0x2dfa60, 'str', 'd0, [x9, w13, uxtw #3]')):
        expect(*anchor)
    if struct.unpack_from('<Q', lib.Z, 0xa40d40)[0] != 0x2ac570:
        raise ValueError('Ring increment vtable slot differs')
    name = struct.unpack_from('<Q', lib.Z, 0xa40d60)[0] & 0x7fffffffffffffff
    if lib.Z[name:name+len(b'18CDSPRingDTTemplateIdLi2048EE\0')] != b'18CDSPRingDTTemplateIdLi2048EE\0':
        raise ValueError('Ring typeinfo identity differs')
    ctor = parse.parse_ctor('SIM_MFX_LINEDRIVE')
    lo, hi = lib.func(ctor['ctor'])
    constructor = list(md.disasm(lib.Z[lo:hi], lo))
    base, count, old_records = parse.parse_datsym('SIM_MFX_LINEDRIVE', ctor)
    records = records_from_memory(constructor_memory(constructor, lib.Z), base, count)
    if (lo, base, count) != (0x2dfe04, 0x80, 159) or records != old_records:
        raise ValueError('Constructor/getter record reconstruction differs')
    fields = {base+8*i+4: dict(relative=relative, address=address)
              for i, (relative, address) in enumerate(records)}
    length, program, *_ = parse.program('SIM_MFX_LINEDRIVE')
    program_sha = hashlib.sha256(program[:length]).hexdigest()
    if length != 0x242 or program_sha != 'a7306c45ee503e60061261f9fa0fde3f8dfc708e6c245b3868e917e6a7d3ea02':
        raise ValueError('Logical program identity differs')
    start, end, code = parse.disasm_meth('SIM_MFX_LINEDRIVE', 'VSubProc(double const**, double**)')
    instructions = {ins.address: ins for ins in code}
    if (start, end) != (0x2df874, 0x2dfd94) or list(instructions) != list(range(start, end, 4)):
        raise ValueError('Callback range is not fully decoded')
    if any(any(ins.group(group) for group in (capstone.CS_GRP_JUMP, capstone.CS_GRP_CALL,
               capstone.CS_GRP_RET)) for ins in code[:-1]) or code[-1].mnemonic != 'ret':
        raise ValueError('Callback has an unmodeled control transfer')
    for ins in code:
        _, writes = ins.regs_access()
        if 0x2dfa74 < ins.address <= 0x2dfab4 and any(
                ins.reg_name(reg) in ('x13', 'w13') for reg in writes):
            raise ValueError('Pre-scaled left factor index was overwritten')
        if ins.address > 0x2df8cc and any(ins.reg_name(reg) in ('x10', 'w10') for reg in writes):
            raise ValueError('P-minus-origin changed inside callback')
        for first, second, register in ((0x2df9bc, 0x2df9cc, '5'), (0x2dfa50, 0x2dfa60, '0')):
            if first < ins.address < second and any(
                    ins.reg_name(reg) in {prefix+register for prefix in ('d', 's', 'q', 'v')}
                    for reg in writes):
                raise ValueError('Duplicated smoother source changed between stores')
    traced = native_accesses(code, fields, coefficient_pointer_fields(constructor))
    accesses = traced['accesses']
    if len(accesses) != 44 or any(a['path'] != ['wrapper', 8, 0x18, 0x10, 0x18]
            or a['mask'] != 0x7ff or len(a['fields']) != 1 for a in accesses):
        raise ValueError('Ordinary native access provenance differs')
    indexed = {ins.address for ins in code if ins.mnemonic in ('ldr', 'str')
               and ins.reg_name(ins.operands[-1].mem.base) == 'x9' and ins.operands[-1].mem.index}
    if indexed - {a['pc'] for a in accesses} != {0x2dfa74, 0x2dfab4}:
        raise ValueError('Unexpected accesses missing from the prefix tracer')
    history = []
    for written, read in HISTORY_PAIRS:
        selected = [next(a for a in accesses if a['kind'] == kind and
                         fields[a['fields'][0]]['address'] == address)
                    for kind, address in (('write', written), ('read', read))]
        expected = [dict(kind=a['kind'], **fields[a['fields'][0]]) for a in selected]
        checked = check_bindings(accesses, fields, expected, instructions)
        if not checked['verified'] or read != written+1:
            raise ValueError('History record/operand/native binding differs')
        history.append(dict(previous_write=written, next_read=read, bindings=checked['accesses']))
    resolved = [dict(pc=a['pc'], kind=a['kind'], object_field=a['fields'][0],
                     **fields[a['fields'][0]]) for a in accesses]
    resolved.extend(dict(pc=pc, kind=kind, object_field=0xfc, **fields[0xfc])
                    for pc, kind in ((0x2dfa74, 'read'), (0x2dfab4, 'write')))
    for access in resolved:
        relative = access['relative']
        if relative+2 > length or int.from_bytes(program[relative:relative+2], 'big') != access['address']:
            raise ValueError('Native constructor address differs from actual program operand')
    spans = [(0x2df874, 0x520), (0x2df6e0, 0x38), (0x2dfe04, 0x394),
             (0x2ac16c, 0x2c), (0x2ac570, 0x14), (0x16bb1c, 0xb0), (0x16c2e4, 0x108)]
    return dict(native_sha256=NATIVE_SHA256, cls='SIM_MFX_LINEDRIVE',
        program_sha256=program_sha, callback=[start, end], record_count=count,
        ring_type='CDSPRingDTTemplate<double,2048>',
        native_ring_elements=2048, native_element_bytes=8, wrapper_base_field=0x10,
        ring_pointer_path=['wrapper', 8, 0x18, 0x10, 0x18], ring_origin_field=0x20,
        ring_vtable=0xa40d40, ring_increment=0x2ac570, native_core_initial_zero_bytes=0x4000,
        core_zero_import=0x6d87c4, core_initial_origin=0,
        callback_advances_origin=False, sync_advances_origin_after_routing=True,
        ordinary_traced_accesses=44, directly_checked_scaled_accesses=2,
        accesses=sorted(resolved, key=lambda a: a['pc']), history_pairs=history,
        accessed_logical_addresses=sorted({a['address'] for a in resolved}),
        pre_rational_history={'left': [3, 4], 'right': [6, 7]},
        current_factor_scratch=[0x27, 0x28], current_wet_scratch=[0x29, 0x2a],
        spans=[dict(address=address, length=size,
                    sha256=hashlib.sha256(lib.Z[address:address+size]).hexdigest()) for address, size in spans],
        hardware_ring_semantics_proven=False, callback_count_per_sync_proven=False,
        limits=['Fixed P and no intervening writers are conditions on history-value reuse.',
                'Native core construction zeroing is not a per-LINEDRIVE reset.',
                'Other callers, DSP5 cadence, hardware timing and reset coverage are not admitted.'])


if __name__ == '__main__':
    result = study()
    destination = Path(__file__).resolve().parents[1]/'local/line-state-study.json'
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print('46 native data accesses; 12 conditional prior-write/read aliases; hardware cadence unproved')
