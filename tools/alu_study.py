"""Bounded functional check for BMC gain controls against native ARM64 def/use.

This is a tail-gain study, not a complete DSP emulator. Unsupported arithmetic
becomes an opaque value; only explicitly tracked live coefficients are compared.
No plugin is loaded and no hardware is accessed. Generated summaries stay local.
"""
import argparse
import json
from pathlib import Path

from bmc_dsp import command_count, packets


def opaque(key):
    return ('opaque', key)


def factors(value):
    """Return only outer live-coefficient multiplications, in evaluation order."""
    result = []
    while value and value[0] == 'mul':
        left, right = value[1:]
        if right[0] == 'coef':
            result.append(right[1])
            value = left
        elif left[0] == 'coef':
            result.append(left[1])
            value = right
        else:
            break
    return list(reversed(result))


def _indexed(word):
    return word & 0xff0 == 0xfe0 and not word & 1


def coefficient_pointer_fields(code):
    """Prove constructor fields are base + 0x48*(parameter_base + slot).

    Slot labels are relative to the constructor's base parameter, not invented
    from field ordering. Stop at the constructor's first return, since Apple's
    LC_FUNCTION_STARTS sometimes groups following static-init procedures with it.
    """
    from capstone import arm64 as a64
    values, result = {}, {}
    def name(ins, operand):
        return ins.reg_name(operand.reg)[1:]
    for ins in code:
        ops, mnemonic, written = ins.operands, ins.mnemonic, None
        if mnemonic == 'ret':
            break
        if mnemonic in ('mov', 'movz') and len(ops) == 2 and ops[1].type == a64.ARM64_OP_IMM:
            written = name(ins, ops[0]); values[written] = ops[1].imm
        elif mnemonic == 'ldr' and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            written = name(ins, ops[0]); source = ins.reg_name(ops[1].mem.base)
            values[written] = ('base',) if source == 'x1' and ops[1].mem.disp == 0x30 else (
                ('index', 0) if source == 'x2' and ops[1].mem.disp == 0x18 else None)
        elif mnemonic == 'add' and len(ops) == 3 and ops[2].type == a64.ARM64_OP_IMM:
            written = name(ins, ops[0]); old = values.get(name(ins, ops[1]))
            values[written] = ('index', old[1] + ops[2].imm) if isinstance(old, tuple) and old[0] == 'index' else None
        elif mnemonic in ('madd', 'umaddl') and len(ops) == 4:
            written = name(ins, ops[0]); index, stride, base = (values.get(name(ins, op)) for op in ops[1:])
            values[written] = ('pointer', index[1]) if isinstance(index, tuple) and index[0] == 'index' and stride == 0x48 and base == ('base',) else None
        elif mnemonic == 'str' and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            value = values.get(name(ins, ops[0]))
            if isinstance(value, tuple) and value[0] == 'pointer' and ins.reg_name(ops[1].mem.base) == 'x0':
                result[ops[1].mem.disp] = value[1]
        _, writes = ins.regs_access()
        for register in writes:
            register_name = ins.reg_name(register)
            if register_name.startswith(('w', 'x')) and register_name[1:] != written:
                values.pop(register_name[1:], None)
    return result


def dsp_gain_tail(decoded):
    """Evaluate only gain controls and four main/coef transfer ports.

    shortcut: unsupported controls erase the current arithmetic result, extend
    this model only when another opcode's behavior is independently established.
    """
    from header_study import families, UnsupportedLayout
    state = [opaque('A'), opaque('B')]
    inputs = [opaque(('input', index)) for index in range(8)]
    memory, output = {}, {}
    for offset, words in decoded:
        try:
            types = families(words[0])
        except UnsupportedLayout:
            state = [opaque((offset, 'A')), opaque((offset, 'B'))]
            inputs = [opaque((offset, 'input', index)) for index in range(8)]
            memory.clear()
            continue
        count = command_count(words[0])
        payload = words[1 + count:]
        for kind, word in zip(types, words[1:1 + count]):
            if kind == 4 and _indexed(word):
                index = (word & 15) // 2
                if index >= len(payload):
                    raise ValueError('Indexed transfer outside packet')
                address, port = payload[index], word >> 12
                if port < 8:
                    inputs[port] = ('coef', address & 0xfff) if address >> 12 == 12 else memory.get(address, opaque(('memory', address)))
                    if port in (0, 4):
                        state[port // 4] = inputs[port]
                elif port in (8, 12):
                    channel = (port - 8) // 4
                    memory[address] = state[channel]
                    if address in (0x2018, 0x2019):
                        output[address - 0x2018] = state[channel]
                else:
                    # Unknown store sources still overwrite their destination.
                    memory.pop(address, None)
                    if address in (0x2018, 0x2019):
                        output[address - 0x2018] = opaque(('unknown-store', offset))
            elif words[0] in (0x1503, 0x2e05, 0xb809, 0x5f07) and kind == 1 and word in (0x0401, 0x4501, 0x0403, 0x4503, 0x0407, 0x4507):
                channel = int(word >= 0x4000)
                state[channel] = ('mul', state[channel], inputs[word & 7])
            elif not (kind == 2 and words[0] == 0x0a02 and word in (0xff70, 0xff71, 0xff75)
                      or kind == 3 and words[0] == 0x3d06 and word == 0x00f8):
                state = [opaque((offset, 'A')), opaque((offset, 'B'))]
                inputs = [opaque((offset, 'input', index)) for index in range(8)]
                memory.clear()
    return {channel: factors(value) for channel, value in output.items()}


def native_values(code, pointer_fields, address_fields, signal_addresses=()):
    """Track actual ARM64 register definitions, not field-offset matches alone.

    Supported pointer paths start at this/input/output arguments. Any unsupported
    writer or call invalidates its destinations rather than retaining stale data.
    Memory store/reload aliases require the same base provenance and data address.
    """
    from capstone import arm64 as a64
    registers = {'x0': ('wrapper',), 'x1': ('inputs',), 'x2': ('outputs',)}
    fp, integer, memory, output, products = {}, {}, {}, {}, []

    def write_fp(register, value):
        fp.pop(('s' if register.startswith('d') else 'd') + register[1:], None)
        fp[register] = value

    def invalidate_vector(register, pc):
        if register[0] in 'qvhb' and register[1:].isdigit():
            for prefix in ('s', 'd'):
                fp[prefix + register[1:]] = opaque(('vector-write', pc))

    def reg(ins, operand):
        return ins.reg_name(operand.reg)

    def mem_key(ins, operand):
        base = registers.get(ins.reg_name(operand.mem.base))
        if base is None:
            return None
        if operand.mem.index:
            index_name = ins.reg_name(operand.mem.index)
            address = integer.get('w' + index_name[1:])
            return ('indexed', base, address) if address is not None else None
        return ('direct', base, operand.mem.disp)

    for ins in code:
        ops, name = ins.operands, ins.mnemonic
        _, writes = ins.regs_access()
        for register in writes:
            invalidate_vector(ins.reg_name(register), ins.address)
        handled = set()
        if name == 'mov' and len(ops) == 2 and all(o.type == a64.ARM64_OP_REG for o in ops):
            dst, src = (reg(ins, op) for op in ops)
            if dst.startswith('x'):
                registers[dst] = registers.get(src)
                integer.pop('w' + dst[1:], None)
            elif dst.startswith('w'):
                integer[dst] = integer.get(src)
                registers.pop('x' + dst[1:], None)
            handled.add(dst)
        elif name in ('ldr', 'ldur') and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            dst, op = reg(ins, ops[0]), ops[1]
            base = registers.get(ins.reg_name(op.mem.base))
            key = mem_key(ins, op)
            if dst.startswith('x'):
                if base == ('wrapper',) and op.mem.disp == 0x28:
                    value = ('object',)
                elif base == ('object',) and op.mem.disp in pointer_fields:
                    value = ('coefficient-pointer', pointer_fields[op.mem.disp])
                elif base in (('inputs',), ('outputs',)) and op.mem.disp in (0, 8):
                    value = ('input' if base == ('inputs',) else 'output', op.mem.disp // 8)
                else:
                    value = ('path', base, op.mem.disp) if base is not None else None
                registers[dst] = value
                integer.pop('w' + dst[1:], None)
            elif dst.startswith('w'):
                integer[dst] = address_fields.get(op.mem.disp) if base == ('object',) else None
                registers.pop('x' + dst[1:], None)
            elif dst[0] in 'sd':
                if base and base[0] == 'coefficient-pointer' and op.mem.disp == 0x28:
                    value = ('coef', base[1])
                elif signal_addresses and base and base[0] == 'input' and op.mem.disp == 0:
                    value = ('signal', ('input', base[1]))
                else:
                    # Observed wrapper+8 -> +18 -> +10 -> +18 data-array path.
                    data_base = ('path', ('path', ('path', ('path', ('wrapper',), 8), 0x18), 0x10), 0x18)
                    value = (('signal', ('memory', key[2])) if key and key[0] == 'indexed' and key[1] == data_base and key[2] in signal_addresses
                             else memory.get(key, opaque(('load', ins.address))) if key is not None
                             else opaque(('load', ins.address)))
                write_fp(dst, value)
            handled.add(dst)
        elif name == 'ldp' and len(ops) == 3 and ops[2].type == a64.ARM64_OP_MEM:
            base = registers.get(ins.reg_name(ops[2].mem.base))
            for index, op in enumerate(ops[:2]):
                dst = reg(ins, op)
                disp = ops[2].mem.disp + 8 * index
                if dst.startswith('x'):
                    registers[dst] = (('input' if base == ('inputs',) else 'output', disp // 8)
                                      if base in (('inputs',), ('outputs',)) and disp in (0, 8) else None)
                    integer.pop('w' + dst[1:], None)
                else:
                    write_fp(dst, opaque(('pair-load', ins.address, index)))
                handled.add(dst)
        elif name in ('add', 'sub', 'and') and len(ops) >= 3 and ops[0].type == a64.ARM64_OP_REG:
            dst = reg(ins, ops[0])
            if dst.startswith('w'):
                values = [integer.get(reg(ins, op)) for op in ops[1:] if op.type == a64.ARM64_OP_REG]
                known = [value for value in values if value is not None]
                integer[dst] = known[0] if len(known) == 1 else None
                registers.pop('x' + dst[1:], None)
                handled.add(dst)
        elif name == 'fcvt' and len(ops) == 2:
            dst, src = (reg(ins, op) for op in ops)
            write_fp(dst, fp.get(src, opaque(('fcvt', ins.address))))
            handled.add(dst)
        elif name == 'fmul' and len(ops) == 3:
            dst, left, right = (reg(ins, op) for op in ops)
            value = ('mul', fp.get(left, opaque(('register', left, ins.address))), fp.get(right, opaque(('register', right, ins.address))))
            write_fp(dst, value)
            products.append(ins.address)
            handled.add(dst)
        elif signal_addresses and name in ('fadd', 'fmadd'):
            names = [reg(ins, op) for op in ops]
            dst = names[0]
            values = [fp.get(source, opaque(('register', source, ins.address))) for source in names[1:]]
            value = ('add', values[0], values[1]) if name == 'fadd' else ('add', ('mul', values[0], values[1]), values[2])
            write_fp(dst, value)
            handled.add(dst)
        elif name == 'str' and len(ops) == 2 and ops[1].type == a64.ARM64_OP_MEM:
            src = reg(ins, ops[0])
            if src.startswith('d'):
                value = fp.get(src, opaque(('store', ins.address)))
                key = mem_key(ins, ops[1])
                if key is not None:
                    memory[key] = value
                    base = key[1]
                    if base and base[0] == 'output':
                        output[base[1]] = value
        if name in ('bl', 'blr'):
            memory.clear()
            output.clear()
            for index in range(18):
                registers.pop(f'x{index}', None)
                integer.pop(f'w{index}', None)
            for index in list(range(8)) + list(range(16, 32)):
                fp.pop(f'd{index}', None)
                fp.pop(f's{index}', None)
        else:
            for register in writes:
                dst = ins.reg_name(register)
                if dst not in handled:
                    if dst.startswith('x'):
                        registers.pop(dst, None)
                        integer.pop('w' + dst[1:], None)
                    elif dst.startswith('w'):
                        integer.pop(dst, None)
                        registers.pop('x' + dst[1:], None)
                    elif dst[0] in 'sd':
                        write_fp(dst, opaque(('arithmetic', ins.address)))
    return output, products


def native_gain_tail(code, pointer_fields, address_fields):
    output, products = native_values(code, pointer_fields, address_fields)
    return {channel: factors(value) for channel, value in output.items()}, products


def study():
    import lib
    import parse
    results = []
    for cls, (_, _, lists) in sorted(lib.pairs().items()):
        if not any(item[1] == 0 for item in lists or []):
            continue
        length, stream, *_ = parse.program(cls)
        decoded = packets(stream[:length])
        # The selected family has an independent pure final gain-pair packet.
        if not any(words[1:1 + command_count(words[0])] == [0x0403, 0x4503]
                   for _, words in decoded[-9:]):
            continue
        constructor = parse.parse_ctor(cls)
        base, _, records = parse.parse_datsym(cls, constructor)
        addresses = {base + 8 * i + 4: address for i, (offset, address) in enumerate(records)
                     if offset is not None}
        ctor_start, ctor_end = lib.func(constructor['ctor'])
        md = lib.md(); md.detail = True
        pointers = coefficient_pointer_fields(md.disasm(lib.Z[ctor_start:ctor_end], ctor_start))
        if pointers != {offset: index for index, offset in enumerate(constructor['tail'])}:
            raise ValueError(f'{cls}: constructor pointer order/provenance is not established')
        start, end, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
        predicted = dsp_gain_tail(decoded)
        observed, product_pcs = native_gain_tail(code, pointers, addresses)
        # This study selects complete two-gain tails; partial suffix agreement is
        # insufficient, even when the last common master-volume factor matches.
        verdict = set(predicted) == {0, 1} and observed == predicted and all(len(values) == 2 for values in predicted.values())
        results.append(dict(cls=cls, native_start=start, native_end=end,
                            predicted=predicted, observed=observed, verified=verdict,
                            native_multiply_count=len(product_pcs), constructor_stride=constructor['stride']))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'local/alu_study.json')
    args = parser.parse_args()
    results = study()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    for item in results:
        print(item['cls'], 'PASS' if item['verified'] else 'UNRESOLVED', item['predicted'], item['observed'])
    print(f'{sum(r["verified"] for r in results)}/{len(results)} selected tails matched')


if __name__ == '__main__':
    main()
