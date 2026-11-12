"""Inventory candidate short-add contexts; no new opcode semantics are admitted."""
from collections import Counter
import hashlib
import struct

from bmc_dsp import command_count, literal, packets
from header_study import UnsupportedLayout, families, reference

MASKED_CONTROLS = (0x1d40, 0x3d40, 0x5d40, 0x7d40)


def candidates(stream):
    rows = []
    for offset, words in packets(stream):
        count = command_count(words[0])
        try:
            types = families(words[0])
        except UnsupportedLayout:
            types = [None]*count
        for operation, control in enumerate(words[1:1+count]):
            if control & ~63 not in MASKED_CONTROLS:
                continue
            kind = types[operation]
            operand = None
            if kind == 1:
                operand = reference(control & 63, 2*(len(words)-count-1))
                if operand['role'] == 'literal':
                    field = offset+2*(count+1)+operand.pop('offset')
                    operand['field'] = field
                    operand['value'] = literal(stream[field:field+operand['width']])
            rows.append(dict(offset=offset, header=words[0], operation=operation,
                             control=control, family=kind, operand=operand,
                             semantic_admission=False))
    return rows


def report():
    import lib
    import parse
    from condition_return_study import preserved
    from limit_control_study import native_context
    from line_shaping_study import NATIVE_SHA256, decode_constant
    from weighted_mix_study import check_constructor_literal, require_instructions, require_words

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    found, skipped = [], []
    for cls, (_, _, lists) in sorted(lib.pairs().items()):
        if not any(item[1] == 0 for item in lists or []):
            skipped.append(cls)
            continue
        length, stream, *_ = parse.program(cls)
        found.extend(dict(cls=cls, **row) for row in candidates(stream[:length]))
    program, native, memory, fields, _ = native_context('SIM_MFX_TRANSIENT')
    require_words(dict(packets(program)), 0xfc, (0x1606, 0x5d72, 0xf510, 0xc6e8, 0x801b, 0xbe96))
    selected, = (row for row in found if row['cls'] == 'SIM_MFX_TRANSIENT'
                  and row['offset'] == 0xfc and row['family'] == 1)
    operand = selected['operand']
    if (operand['field'], operand['width']) != (0x104, 4):
        raise ValueError('TRANSIENT short literal candidate changed')
    check_constructor_literal(program, memory, native[0x1d62e8], operand, object_register='x21')
    if fields[0x1d4] != dict(relative=0xfa, address=30) or program[0xfa:0xfc] != b'\x00\x1e':
        raise ValueError('TRANSIENT decay source record changed')
    require_instructions(native, 0x1d62d8, (
        ('ldr', 'w8, [x21, #0x1d4]'), ('add', 'w8, w27, w8'), ('and', 'w8, w8, #0x7ff'),
        ('ldr', 'd1, [x23, w8, uxtw #3]'), ('ldr', 'd2, [x21, #0x78]'), ('fadd', 'd1, d1, d2')))
    for register in ('x21', 'x23'):
        preserved([native[pc] for pc in range(0x1d6058, 0x1d62d8, 4)], register)
    limit = decode_constant([native[pc] for pc in range(0x1d62f0, 0x1d6304, 4)])
    if limit['bits'] != 'c01ba18a998fffa0':
        raise ValueError('TRANSIENT clamp literal changed')
    short = [row for row in found if row['family'] == 1]
    counts = Counter(str(row['family']) for row in found)
    additions = []
    for cls, offset, pc, destination, constant, repeated in (
            ('SIM_MFX_OSC', 0x27a, 0x2974c, 'd0', 'd2', None),
            ('SIM_MFX_GASSPH', 0x25c, 0x14a62c, 'd6', 'd16', (0x14a680, 'd6, d6, d16')),
            ('SIM_MFX_GAMPSIM', 0x2a4, 0x324f84, 'd17', 'd18', (0x324fe8, 'd16, d17, d18')),
            ('SIM_MFX_GASSDLY', 0x240, 0x2fa1b0, 'd6', 'd7', (0x2fa200, 'd7, d16, d7'))):
        row, = (row for row in short if row['cls'] == cls and row['offset'] == offset)
        _, instructions, _, _, _ = native_context(cls)
        immediate = decode_constant([instructions[pc]])
        value = immediate['value']
        if immediate['register'] != constant or value != row['operand']['value']:
            raise ValueError('Candidate immediate differs from native addition constant')
        require_instructions(instructions, pc+4, (('fadd', f'{destination}, {destination}, {constant}'),))
        native_adds = [pc+4]
        if repeated:
            add_pc, operands = repeated
            require_instructions(instructions, add_pc, (('fadd', operands),))
            native_adds.append(add_pc)
        additions.append(dict(cls=cls, packet=offset, native_constant=pc,
                              native_add_candidates=native_adds, value=value,
                              source_port_binding_verified=False))
    return dict(native_sha256=NATIVE_SHA256, rows=found, skipped_without_render=skipped,
                family_counts=dict(counts), short_candidates=len(short),
                short_classes=len({row['cls'] for row in short}),
                native_addition_candidates=additions,
                transient_literal_binding=dict(field=operand['field'], width=operand['width'],
                    stored_value=operand['value'], native_field=0x78, native_load=0x1d62e8,
                    native_add=0x1d62ec, source=fields[0x1d4],
                    full_native_default=struct.unpack('<d', bytes(memory[0x78+i] for i in range(8)))[0],
                    native_clamp_limit=limit['value']),
                isolated_short_add_verified=False, bmc_execution_verified=False)


if __name__ == '__main__':
    import json
    print(json.dumps(report(), indent=2))
