"""Bounded native math-call cutpoints for exceptional BMC short-operation research.

This identifies reference-function windows, not individual opcode semantics.
Only straight-line ARM64 prefixes with named pure math calls are admitted.
"""
import json
import re
import subprocess

from alu_study import native_values
from header_study import UNPROVEN_SHORT, UnsupportedLayout, families
from transfer_study import constructor_memory, records_from_memory


DATA_PATH = ('path', ('path', ('path', ('path', ('wrapper',), 8), 0x18), 0x10), 0x18)


def indirect_symbols(listing):
    """Read otool's address/index/name rows, without treating headings as symbols."""
    return {int(address, 16): name for address, name in re.findall(
        r'^\s*(0x[0-9a-fA-F]+)\s+\d+\s+(\S+)\s*$', listing, re.M)}


def math_cutpoints(code, address_fields, symbols):
    """Find exact D0 stores before/after _exp, stopping at control-flow joins.

    The existing native reader proves the object/data pointer paths. Field markers
    preserve constructor-record identity instead of matching equal numeric addresses.
    """
    from capstone import arm64 as a64
    admitted, stop = [], None
    for ins in code:
        name = ins.mnemonic
        if name == 'bl' and symbols.get(ins.operands[0].imm) in ('_exp', '_log'):
            admitted.append(ins)
        elif name in ('ret', 'bl', 'blr', 'br', 'b', 'cbz', 'cbnz', 'tbz', 'tbnz') or name.startswith('b.'):
            stop = dict(pc=ins.address, mnemonic=name)
            break
        else:
            admitted.append(ins)
    trace = []
    native_values(admitted, {}, address_fields, trace=trace)
    stores = {item['pc']: item for item in trace if item['kind'] == 'store'}

    def writes_d0(ins):
        _, writes = ins.regs_access()
        return any(ins.reg_name(register) in ('d0', 's0', 'q0', 'v0', 'h0', 'b0') for register in writes)

    def anchor(ins):
        if (ins.mnemonic != 'str' or len(ins.operands) != 2
                or ins.operands[0].type != a64.ARM64_OP_REG
                or ins.reg_name(ins.operands[0].reg) != 'd0'):
            return None
        operand = ins.operands[1]
        if (operand.type != a64.ARM64_OP_MEM or operand.mem.disp or ins.writeback
                or not operand.mem.index or operand.ext != a64.ARM64_EXT_UXTW
                or operand.shift.type != a64.ARM64_SFT_LSL or operand.shift.value != 3):
            return None
        entry = stores.get(ins.address)
        if not entry:
            return None
        kind, path, marker = entry['key']
        if kind != 'indexed' or path != DATA_PATH or not isinstance(marker, tuple) or marker[0] != 'field':
            return None
        return dict(pc=ins.address, object_field=marker[1], relative=marker[2], address=marker[3])

    result = []
    for index, ins in enumerate(admitted):
        if ins.mnemonic != 'bl' or symbols.get(ins.operands[0].imm) != '_exp':
            continue
        row = dict(call=ins.address, input_store=None, output_store=None)
        for key, direction in (('input_store', admitted[:index][::-1]), ('output_store', admitted[index + 1:])):
            for other in direction:
                if other.mnemonic in ('bl', 'blr') or writes_d0(other):
                    break
                found = anchor(other)
                if found:
                    row[key] = found
                    break
        result.append(row)
    return dict(calls=result, stop=stop)


def study():
    import lib
    import parse
    from bmc_dsp import packets

    listing = subprocess.run(['xcrun', 'otool', '-Iv', str(lib.BASE / 'zen_arm64')],
                             check=True, capture_output=True, text=True).stdout
    symbols = indirect_symbols(listing)
    if '_exp' not in symbols.values():
        raise ValueError('The native artifact has no identified _exp import stub')
    md = lib.md(); md.detail = True
    results = []
    for cls in ('SIM_MFX_UPLIFT_EXCITER', 'SIM_MFX_TRANSIENT'):
        ctor = parse.ctor_addr(cls); start, end = lib.func(ctor)
        memory = constructor_memory(md.disasm(lib.Z[start:end], start), lib.Z)
        base, count, old = parse.parse_datsym(cls, parse.parse_ctor(cls))
        records = records_from_memory(memory, base, count)
        if records != old:
            raise ValueError(f'{cls}: fresh constructor records differ from old extraction')
        fields = {base + 8 * index + 4: ('field', base + 8 * index + 4, relative, address)
                  for index, (relative, address) in enumerate(records)}
        start, end, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
        # Function-start ranges can contain another procedure after the first return.
        first_return = next(index for index, ins in enumerate(code) if ins.mnemonic == 'ret')
        code = code[:first_return + 1]
        native = math_cutpoints(code, fields, symbols)
        length, stream, *_ = parse.program(cls)
        decoded = packets(stream[:length])
        exceptional = []
        for offset, words in decoded:
            try:
                types = families(words[0])
            except UnsupportedLayout:
                continue
            exceptional.extend(dict(offset=offset, control=control) for kind, control in zip(types, words[1:])
                               if kind == 1 and control in UNPROVEN_SHORT)
        for row in native['calls']:
            if row['input_store'] and row['output_store']:
                lo, hi = row['input_store']['relative'], row['output_store']['relative']
                row['intervening_exceptional'] = [item for item in exceptional if lo < item['offset'] < hi]
        results.append(dict(cls=cls, native_start=start, native_end=end,
                            exp_stub_calls=sum(ins.mnemonic == 'bl' and symbols.get(ins.operands[0].imm) == '_exp'
                                               for ins in code), exceptional=exceptional, **native))
    output = lib.BASE / 'special-ops-study.json'
    output.write_text(json.dumps(results, indent=2) + '\n')
    return results


if __name__ == '__main__':
    for row in study():
        print(row['cls'], 'exp imports', row['exp_stub_calls'], 'proven native cutpoints',
              sum(bool(call['input_store'] and call['output_store']) for call in row['calls']))
        print(json.dumps(row['calls']))
