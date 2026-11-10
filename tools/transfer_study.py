"""Bounded ARM64 provenance study of BMC data spaces; no target execution.

Detailed results belong under ignored local/. This is a prefix tracer, not an
ARM emulator: the first branch/call/return ends a trace and unknown writers kill
their destinations. Numeric field offsets alone never establish object identity.
"""
import argparse
import collections
import json
from pathlib import Path
import struct


def _reg(ins, operand):
    return ins.reg_name(operand.reg)


def _key(name):
    if name in ('fp', 'lr'):
        return '29' if name == 'fp' else '30'
    if name[1:].isdigit():
        if name[0] in 'xw':
            return name[1:]
        if name[0] in 'qdsv':
            return 'fp' + name[1:]
    return name


def _stop(mnemonic):
    return mnemonic in ('ret', 'bl', 'blr', 'br', 'b', 'cbz', 'cbnz', 'tbz', 'tbnz') or mnemonic.startswith('b.')


def _width(register):
    if register in ('fp', 'lr', 'sp'):
        return 8
    if register.startswith(('w', 's')):
        return 4
    if register.startswith(('x', 'd')):
        return 8
    if register.startswith('q'):
        return 16
    raise ValueError(f'Unsupported memory register {register}')


def constructor_memory(code, data):
    """Recover literal bytes stored through a proven x0-derived object pointer."""
    from capstone import arm64 as a64
    values, memory = {'0': ('object', 0)}, {}
    for ins in code:
        m, ops, handled = ins.mnemonic, ins.operands, set()
        if _stop(m):
            break
        if m in ('mov', 'movz', 'adrp') and len(ops) == 2:
            dst = _key(_reg(ins, ops[0]))
            values[dst] = ops[1].imm if ops[1].type == a64.ARM64_OP_IMM else values.get(_key(_reg(ins, ops[1])))
            handled.add(dst)
        elif m == 'movk' and len(ops) == 2:
            dst = _key(_reg(ins, ops[0])); old = values.get(dst)
            shift = ops[1].shift.value
            values[dst] = ((old & ~(65535 << shift)) | (ops[1].imm << shift)) if isinstance(old, int) else None
            handled.add(dst)
        elif m == 'add' and len(ops) == 3 and ops[2].type == a64.ARM64_OP_IMM:
            dst = _key(_reg(ins, ops[0])); old = values.get(_key(_reg(ins, ops[1])))
            values[dst] = old + ops[2].imm if isinstance(old, int) else (
                ('object', old[1] + ops[2].imm) if isinstance(old, tuple) and old[0] == 'object' else None)
            handled.add(dst)
        elif m in ('ldr', 'ldur') and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            dst = _key(_reg(ins, ops[0])); mem = ops[1].mem
            source = values.get(_key(ins.reg_name(mem.base)))
            width = _width(_reg(ins, ops[0]))
            address = source + mem.disp if isinstance(source, int) and not mem.index else -1
            values[dst] = data[address:address + width] if 0 <= address <= len(data) - width else None
            handled.add(dst)
        elif m in ('str', 'stur', 'strb', 'strh', 'stp') and ops[-1].type == a64.ARM64_OP_MEM:
            mem = ops[-1].mem; target = values.get(_key(ins.reg_name(mem.base)))
            if isinstance(target, tuple) and target[0] == 'object' and not mem.index:
                offset = target[1] + mem.disp
                for op in ops[:-1]:
                    register = _reg(ins, op)
                    width = 1 if m == 'strb' else 2 if m == 'strh' else _width(register)
                    value = 0 if register in ('wzr', 'xzr') else values.get(_key(register))
                    raw = (value & ((1 << (8 * width)) - 1)).to_bytes(width, 'little') if isinstance(value, int) else value
                    for byte in range(width):
                        memory.pop(offset + byte, None)
                    if isinstance(raw, bytes) and len(raw) == width:
                        memory.update((offset + i, byte) for i, byte in enumerate(raw))
                    offset += width
        _, writes = ins.regs_access()
        for register in writes:
            name = _key(ins.reg_name(register))
            if name not in handled:
                values.pop(name, None)
    return memory


def records_from_memory(memory, base, count):
    records = []
    for index in range(count):
        offset = base + 8 * index
        if not all(offset + byte in memory for byte in range(8)):
            raise ValueError(f'Constructor does not establish record {index}')
        relative, value = struct.unpack('<II', bytes(memory[offset + byte] for byte in range(8)))
        records.append((relative, value))
    return records


def native_accesses(code, address_fields, coefficient_fields):
    """Trace only the straight-line prefix, retaining pointer and address provenance."""
    from capstone import arm64 as a64
    values = {'0': ('pointer', ('wrapper',)), '1': ('pointer', ('inputs',)), '2': ('pointer', ('outputs',))}
    accesses, coefs, stop = [], [], None
    for ins in code:
        m, ops, handled = ins.mnemonic, ins.operands, set()
        if _stop(m):
            stop = dict(pc=ins.address, mnemonic=m)
            break
        if m == 'mov' and len(ops) == 2 and ops[1].type == a64.ARM64_OP_REG:
            dst = _key(_reg(ins, ops[0])); values[dst] = values.get(_key(_reg(ins, ops[1])))
            handled.add(dst)
        elif m in ('ldr', 'ldur', 'ldp') and ops[-1].type == a64.ARM64_OP_MEM:
            mem = ops[-1].mem; base = values.get(_key(ins.reg_name(mem.base)))
            displacement = mem.disp
            for op in ops[:-1]:
                register = _reg(ins, op); dst = _key(register); disp = displacement
                displacement += _width(register)
                result = None
                if base and base[0] == 'pointer' and not mem.index:
                    path = base[1]
                    if register.startswith('x'):
                        result = ('pointer', ('object',)) if path == ('wrapper',) and disp == 0x28 else (
                            ('coefficient', coefficient_fields[disp]) if path == ('object',) and disp in coefficient_fields
                            else ('pointer', (*path, disp)))
                    elif register.startswith('w'):
                        result = ('index', frozenset([disp]), None) if path == ('object',) and disp in address_fields else (
                            ('index', frozenset(), None))
                if base and base[0] == 'coefficient' and register.startswith('s') and not mem.index and disp == 0x28:
                    coefs.append(dict(pc=ins.address, slot=base[1], width=4))
                if mem.index and register.startswith(('d', 's')) and base and base[0] == 'pointer':
                    idx = values.get(_key(ins.reg_name(mem.index)))
                    if idx and idx[0] == 'index':
                        accesses.append(dict(pc=ins.address, kind='read', path=list(base[1]),
                                             fields=sorted(idx[1]), mask=idx[2]))
                values[dst] = result; handled.add(dst)
        elif m in ('str', 'stur') and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            mem = ops[1].mem; base = values.get(_key(ins.reg_name(mem.base)))
            if _reg(ins, ops[0]).startswith(('d', 's')) and mem.index and base and base[0] == 'pointer':
                idx = values.get(_key(ins.reg_name(mem.index)))
                if idx and idx[0] == 'index':
                    accesses.append(dict(pc=ins.address, kind='write', path=list(base[1]),
                                         fields=sorted(idx[1]), mask=idx[2]))
        elif m in ('add', 'sub') and len(ops) == 3 and all(op.type == a64.ARM64_OP_REG for op in ops):
            dst = _key(_reg(ins, ops[0])); left, right = (values.get(_key(_reg(ins, op))) for op in ops[1:])
            if left and right and left[0] == right[0] == 'index':
                values[dst] = ('index', left[1] | right[1], None)
            else:
                values[dst] = None
            handled.add(dst)
        elif m == 'and' and len(ops) == 3 and ops[2].type == a64.ARM64_OP_IMM:
            dst = _key(_reg(ins, ops[0])); source = values.get(_key(_reg(ins, ops[1])))
            values[dst] = ('index', source[1], ops[2].imm) if source and source[0] == 'index' else None
            handled.add(dst)
        _, writes = ins.regs_access()
        for register in writes:
            key = _key(ins.reg_name(register))
            if key not in handled:
                values.pop(key, None)
    return dict(accesses=accesses, coefficient_reads=coefs, stop=stop)


def collect():
    import lib
    import parse
    from alu_study import coefficient_pointer_fields
    from bmc_dsp import command_count, packets
    md = lib.md(); md.detail = True
    rows, totals, spaces, skipped = [], collections.Counter(), collections.Counter(), []
    for cls, (defaults, driver, lists) in lib.pairs().items():
        if not any(item[1] == 0 for item in lists or []):
            continue
        try:
            ctor = parse.ctor_addr(cls); start, end = lib.func(ctor)
            code = list(md.disasm(lib.Z[start:end], start))
            memory = constructor_memory(code, lib.Z)
            base, count, old_records = parse.parse_datsym(cls, parse.parse_ctor(cls))
            records = records_from_memory(memory, base, count)
            if records != old_records:
                raise ValueError('Fresh constructor records differ from old reader')
            fields = {base + 8 * index + 4: dict(relative=relative, value=value)
                      for index, (relative, value) in enumerate(records)}
            pointer_fields = coefficient_pointer_fields(code)
            _, _, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
            traced = native_accesses(native, fields, pointer_fields)
            length, stream, peer, table, pbase, peerbase = parse.program(cls)
            slot_order = []
            for offset, words in packets(stream[:length]):
                n = command_count(words[0]); payload = words[1 + n:]
                for word in words[1:1 + n]:
                    if word & 0xff0 == 0xfe0 and not word & 1 and word >> 12 < 8:
                        address = payload[(word & 15) // 2]
                        if address >> 12 == 12 and (address & 0xfff) not in slot_order:
                            slot_order.append(address & 0xfff)
            native_order = list(dict.fromkeys(item['slot'] for item in traced['coefficient_reads']))
            for access in traced['accesses']:
                if len(access['fields']) != 1:
                    totals['ambiguous_or_unresolved_accesses'] += 1
                    continue
                field = fields[access['fields'][0]]
                relative = field['relative']
                if relative + 2 > length:
                    totals['record_outside_primary'] += 1
                    continue
                word = int.from_bytes(stream[relative:relative + 2], 'big')
                access.update(relative=relative, table_value=field['value'], tag=word >> 12,
                              program_index=word & 0xfff)
                spaces[(word >> 12, tuple(access['path']), access['mask'], access['kind'])] += 1
                totals['resolved_accesses'] += 1
            totals['classes'] += 1
            totals['constructor_records'] += len(records)
            totals['native_coef_reads'] += len(traced['coefficient_reads'])
            totals['classes_with_coef_prefix'] += bool(native_order)
            totals['coef_prefix_order_matches'] += bool(native_order) and native_order == slot_order[:len(native_order)]
            rows.append(dict(cls=cls, ctor=ctor, getter_record_base=base, getter_record_count=count,
                             native_coef_order=native_order, dsp_coef_order=slot_order, **traced))
        except (ValueError, KeyError, TypeError, IndexError, struct.error) as error:
            skipped.append(dict(cls=cls, error=str(error)))
    return dict(totals=dict(totals), spaces=[dict(tag=tag, path=list(path), mask=mask, kind=kind, count=count)
                                           for (tag, path, mask, kind), count in sorted(spaces.items(), key=lambda item: str(item[0]))],
                skipped=skipped, classes=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'local/transfer_study.json')
    args = parser.parse_args()
    result = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(totals=result['totals'], skipped=result['skipped'], spaces=result['spaces']), indent=2))


if __name__ == '__main__':
    main()
