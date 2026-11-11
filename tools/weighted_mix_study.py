"""Compare exact BMC weighted-mix packets with native audio dataflow."""
import hashlib
import json
import struct

from bmc_dsp import packets
from header_study import layout
from line_mix_variation import packet_literals
from line_state_study import NATIVE_SHA256
from mac_controls_study import DATA_BASE, replace_roots
from mac_study import describe, polynomial

WINDOW_BASE = ('path', ('path', ('path', ('path', ('wrapper',), 8), 0x18), 0x28), 0x18)


def reference_shape(control, extension):
    """Separate literal-reference bits from the remaining control bits."""
    references = control & 63, (extension >> 6) & 63
    if any(code < 16 for code in references):
        raise ValueError('Expected two literal references')
    return control & ~63, extension & ~0xfc0


def weighted_sum(first, second, coefficient0, coefficient1):
    return ('add', ('mul', first, coefficient0), ('mul', second, coefficient1))


def compare(value, expected, roots):
    observed = polynomial(replace_roots(value, roots))
    if observed != polynomial(expected):
        raise ValueError('Native weighted expression differs from expected field/source order')
    return describe(observed)


def check_trecho(program, rows, instructions, trace, memory, records):
    require_words(rows, 0x1cc, (0x1e05, 0x0fe0, 0x1fe2, 0x2016, 0))
    require_words(rows, 0x1d6, (0x2b09, 0x4812, 0x0fe6, 0x1fe8, 0x1500,
                               0x2400, 0x2400, 0x2017, 1))
    require_words(rows, 0x1e8, (0x1407, 0x5812, 0xcfe6, 0x1500, 0x2400, 0x2400, 0x4001))
    require_words(rows, 0x1f6, (0x0c03, 0xdfe0, 0x4002))
    require_window(instructions, 0xcfb4, 0xd02c)
    if (instructions[0xcffc].mnemonic, instructions[0xcffc].op_str) != ('fmov', 'd4, #0.25000000'):
        raise ValueError('TRECHO immediate coefficient differs')
    factor = ('signal', ('quarter', 0))
    roots = {event(trace, 0xcffc, 'fp')['value']: factor}
    result = []
    for channel, (offset, state, read_pc, target, pc, port) in enumerate((
            (0x1d6, 0x19c, 0xcfe4, 0x1f4, 0xd018, 4),
            (0x1e8, 0x1ca, 0xcff8, 0x1fa, 0xd02c, 5))):
        state_value = ('signal', ('memory', state))
        if event(trace, read_pc, 'fp')['value'] != state_value:
            raise ValueError('TRECHO source field differs')
        if dict(records)[state] != channel or dict(records)[target] != channel + 1:
            raise ValueError('TRECHO constructor cell assignment differs')
        if [f['value'] for f in packet_literals(program, offset, rows[offset])] != [0.25, 0.25]:
            raise ValueError('TRECHO literal values differ')
        value = store_value(trace, pc, WINDOW_BASE, target)
        expected = weighted_sum(('signal', ('input', channel)), state_value, factor, factor)
        result.append(dict(packet=offset, destination_port=port, native_store=pc,
                           expression=compare(value, expected, roots)))
    return result


def check_bitcrush(program, rows, instructions, trace, memory, records):
    require_words(rows, 0xf6, (0x850e, 0x550b, 0x550b, 0x707c, 0x1b12, 0x8fe4))
    require_words(rows, 0x112, (0xac4b, 0x4524, 0x4045, 0x2407, 0xee50, 0x1a12, 0x1fe2))
    if [(offset, dict(records)[offset], int.from_bytes(program[offset:offset+2], 'big'))
            for offset in (0x106, 0x122)] != [(0x106, 12, 12), (0x122, 13, 13)]:
        raise ValueError('BITCRUSH constructor/source records differ')
    first = store_value(trace, 0x241a9c, DATA_BASE, 0x106)
    second = ('signal', ('memory', 0x122))
    if event(trace, 0x241ad8, 'fp')['value'] != second:
        raise ValueError('BITCRUSH second source field differs')
    for offset in (0x15c, 0x1a8, 0x1f4):
        require_words(rows, offset, (0x0805, 0x4812, 0x1500))
    return [check_weighted_stage(program, rows, instructions, trace, memory,
                                 offset, loads, pc, first, second)
            for offset, loads, pc in (
                (0x15c, (0x241b98, 0x241b9c), 0x241ba4),
                (0x1a8, (0x241c6c, 0x241c70), 0x241c78),
                (0x1f4, (0x241d44, 0x241d48), 0x241d60))]


def check_binhall(program, rows, instructions, trace, memory, records):
    require_words(rows, 0x326, (0x1407, 0x4424, 0x0fe2, 4, 0x409f))
    require_words(rows, 0x334, (0x1408, 0x5824, 0xcfe2, 0x49c0, 0x02bc))
    require_words(rows, 0x344, (0x0c03, 0xdfe0, 0x40be))
    if [dict(records)[field] for field in (0x32e, 0x33c, 0x348)] != [0x13, 0x32, 0x32]:
        raise ValueError('BINHALL constructor/source records differ')
    require_instructions(instructions, 0x1a3be0, (
        ('ldr', 'w13, [x8, #0x7bc]'), ('add', 'w13, w13, w9'),
        ('ldr', 'd1, [x10, w13, uxtw #3]')))
    first = event(trace, 0x1a3be8, 'fp')['value']
    second = store_value(trace, 0x1a3c00, DATA_BASE, 0x33c)
    result = check_weighted_stage(program, rows, instructions, trace, memory, 0x334,
                                  (0x1a3c04, 0x1a3c08), 0x1a3c10, first, second)
    if event(trace, 0x1a3c10, 'fp')['value'] != store_value(trace, 0x1a3c1c, WINDOW_BASE, 0x348):
        raise ValueError('BINHALL weighted result did not reach the port-5 store')
    require_window(instructions, 0x1a3be0, 0x1a3c1c)
    return result


def check_brhl(program, rows, instructions, trace, memory, records):
    require_words(rows, 0xe8, (0x2b0a, 0x4926, 0x0fe2, 0xcfe4, 0x6a40, 0x40b6))
    require_words(rows, 0xfc, (0x1407, 0x2424, 0xcfe2, 4, 0x0299))
    require_words(rows, 0x10a, (0x2b0a, 0x1826, 0x5fe2, 0xafe4, 0x4a40, 0x40bd, 0x40b4))
    if [dict(records)[field] for field in (0xf2, 0x104, 0x116)] != [0x2a, 0xf, 0x28]:
        raise ValueError('BRHL constructor/source records differ')
    require_window(instructions, 0x2d9908, 0x2d9960)
    require_instructions(instructions, 0x2d9908, (
        ('ldr', 'w14, [x8, #0x95c]'), ('add', 'w14, w14, w11'),
        ('ldr', 'd2, [x12, w14, uxtw #3]')))
    first = event(trace, 0x2d9910, 'fp')['value']
    second = store_value(trace, 0x2d9940, DATA_BASE, 0x104)
    field, = packet_literals(program, 0xfc, rows[0xfc])
    check_constructor_literal(program, memory, instructions[0x2d9944], field)
    coefficient = event(trace, 0x2d9944, 'fp')['value']
    a, b, k = [('signal', (name, 0)) for name in ('A', 'B', 'literal')]
    roots = dict(zip((first, second, coefficient), (a, b, k)))
    if len(roots) != 3:
        raise ValueError('BRHL sources alias')
    expression = compare(store_value(trace, 0x2d9960, WINDOW_BASE, 0x116),
                         ('add', ('mul', a, k), b), roots)
    return dict(packet=0xfc, native_store=0x2d9960, destination_port=2,
                literal=field, expression=expression)


def check_uplift(program, rows, instructions, trace, memory, records):
    require_words(rows, 0x1d0, (0x470c, 0x2468, 0x656b, 0x1fe4, 0x5fe6, 2, 6, 0x32, 0x37))
    require_words(rows, 0x1e8, (0x1008, 0x3464, 0x7567, 2, 6))
    require_words(rows, 0x1f8, (0xb84e, 0x2428, 0x652b, 0xbfe0, 0xffe2,
                                0x1fe4, 0x5fe6, 0x30, 0x35))
    if [dict(records)[field] for field in (0x1de, 0x206)] != [0x32, 0x30]:
        raise ValueError('UPLIFT constructor/source records differ')
    require_window(instructions, 0x8b650, 0x8b67c)
    require_instructions(instructions, 0x8b294, (('ldr', 'x20, [x0, #0x28]'),))
    source = ('signal', ('memory', 0x1de))
    if event(trace, 0x8b65c, 'fp')['value'] != source:
        raise ValueError('UPLIFT port-1 source field differs')
    field = packet_literals(program, 0x1e8, rows[0x1e8])[0]
    check_constructor_literal(program, memory, instructions[0x8b668], field, object_register='x20')
    prior, coefficient = ('signal', ('prior', 0)), ('signal', ('literal', 0))
    roots = {event(trace, 0x8b664, 'fp')['value']: prior,
             event(trace, 0x8b668, 'fp')['value']: coefficient}
    expression = compare(store_value(trace, 0x8b67c, DATA_BASE, 0x206),
                         ('add', ('mul', source, coefficient), prior), roots)
    return dict(packet=0x1e8, native_store=0x8b67c, destination_port=3,
                literal=field, expression=expression)


def check_weighted_stage(program, rows, instructions, trace, memory, offset, loads, pc, first, second):
    require_window(instructions, loads[0], pc)
    literals = packet_literals(program, offset, rows[offset])
    terms = [('signal', (kind, index)) for kind in ('source', 'literal') for index in (0, 1)]
    start = next(iter(instructions))
    entry = instructions[start]
    if (entry.mnemonic, entry.op_str) != ('ldr', 'x8, [x0, #0x28]') or any(
            {'x8', 'w8'}.intersection(map(ins.reg_name, ins.regs_access()[1]))
            for address, ins in instructions.items() if start < address <= loads[-1]):
        raise ValueError('Constructor-object pointer changed before the coefficient loads')
    coefficients = []
    for load, field in zip(loads, literals, strict=True):
        check_constructor_literal(program, memory, instructions[load], field)
        coefficients.append(event(trace, load, 'fp')['value'])
    roots = dict(zip((first, second, *coefficients), terms, strict=True))
    if len(roots) != 4:
        raise ValueError('Weighted inputs or coefficient roots alias')
    expression = compare(event(trace, pc, 'fp')['value'], weighted_sum(*terms), roots)
    return dict(packet=offset, native_result=pc, literals=literals, expression=expression)


def check_constructor_literal(program, memory, ins, field, *, object_register='x8'):
    from capstone import arm64

    operand = ins.operands[-1]
    if (ins.mnemonic != 'ldr' or operand.type != arm64.ARM64_OP_MEM or ins.writeback
            or ins.reg_name(operand.mem.base) != object_register or operand.mem.index
            or not ins.reg_name(ins.operands[0].reg).startswith('d')):
        raise ValueError('Expected a native constructor-double load')
    address = operand.mem.disp
    relative = int.from_bytes(bytes(memory[i] for i in range(address - 8, address - 4)), 'little')
    value, = struct.unpack('<d', bytes(memory[i] for i in range(address, address + 8)))
    exponent = (program[field['field']] >> 5) & 3
    quantum = 2 ** (-24 + 4 * exponent + 8 * (3 - field['width']))
    if relative != field['field'] or not abs(value - field['value']) < quantum:
        raise ValueError('Constructor literal binding or encoded value differs')


def require_words(rows, offset, prefix):
    if tuple(rows[offset][:len(prefix)]) != prefix:
        raise ValueError(f'DSP packet changed at {offset:#x}')


def require_instructions(instructions, start, expected):
    actual = tuple((instructions[address].mnemonic, instructions[address].op_str)
                   for address in range(start, start + 4 * len(expected), 4))
    if actual != expected:
        raise ValueError(f'Native instruction sequence changed at {start:#x}')


def require_window(instructions, start, end):
    import capstone

    for address in range(start, end + 1, 4):
        ins = instructions[address]
        if any(ins.group(group) for group in (capstone.CS_GRP_CALL, capstone.CS_GRP_JUMP,
                                             capstone.CS_GRP_RET, capstone.CS_GRP_INT)):
            raise ValueError(f'Control transfer inside native window at {address:#x}')


def event(trace, pc, kind):
    item, = (item for item in trace if item['pc'] == pc and item['kind'] == kind)
    return item


def store_value(trace, pc, base, field):
    item = event(trace, pc, 'store')
    if item['key'] != ('indexed', base, field):
        raise ValueError(f'Native store path or field differs at {pc:#x}')
    return item['value']


def study():
    import lib
    import parse
    from alu_study import native_values
    from transfer_study import constructor_memory, records_from_memory

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported prepared ZENOLOGY image')
    result = {}
    for cls, check in (('SIM_MFX_TRECHO', check_trecho), ('SIM_MFX_BITCRUSH', check_bitcrush),
                       ('SIM_REV_BINHALL', check_binhall), ('SIM_REV_BRHL', check_brhl),
                       ('SIM_MFX_UPLIFT_EXCITER', check_uplift)):
        length, program, *_ = parse.program(cls)
        program = program[:length]
        ctor = parse.parse_ctor(cls)
        start, end = lib.func(ctor['ctor'])
        md = lib.md()
        md.detail = True
        memory = constructor_memory(md.disasm(lib.Z[start:end], start), lib.Z)
        base, count, original = parse.parse_datsym(cls, ctor)
        records = records_from_memory(memory, base, count)
        if records != original:
            raise ValueError('Independent constructor record reconstruction differs')
        fields = {base + 8 * index + 4: relative for index, (relative, _) in enumerate(records)}
        _, _, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
        trace = []
        native_values(native, {}, fields, fields.values(), trace=trace)
        result[cls] = check(program, dict(packets(program)), {ins.address: ins for ins in native},
                            trace, memory, records)
    bitcrush_shape = reference_shape(0x4812, 0x1500)
    if reference_shape(0x4822, 0x1940) != bitcrush_shape:
        raise ValueError('LINE and BITCRUSH control bits differ outside literal references')
    length, line, *_ = parse.program('SIM_MFX_LINEDRIVE')
    rows = dict(packets(line[:length]))
    require_words(rows, 0x4, (0x1e05, 0x0fe0, 0x1fe2, 0x2016, 0x2017))
    require_words(rows, 0xe, (0x0806, 0x4822, 0x1940))
    require_words(rows, 0x1a, (0x1008, 0x2424, 0x3467, 4, 4))
    require_words(rows, 0x2a, (0x3e07, 0xafe0, 0xbfe2, 0x5fe4, 1, 2, 0xc002))
    mix = layout(rows[0x1a])
    if mix['families'] != [0, 0] or [ref['index'] for ref in mix['registers']] != [0, 4, 0, 4]:
        raise ValueError('LINE paired long-operation layout changed')
    result['line_candidate'] = dict(control=0x4822, extension=0x1940, reference_shape=bitcrush_shape,
                                    expression='B = A * literal0 + I1 * literal1',
                                    left_consumer='I2 = A * literal + B',
                                    right_consumer='I3 = I1 * literal + B', admitted=False)
    return result


if __name__ == '__main__':
    print(json.dumps(study(), indent=2))
