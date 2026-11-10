"""Bounded native predicate/operand-field proof; no BMC condition decoder."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from bmc_dsp import command_count, packets, swap_words
from parent_control_study import NATIVE_SHA256


def classify(code):
    """Recognize only the three exact native branch kernels used in this study."""
    shapes = [(i.mnemonic, i.op_str) for i in code]
    if len(code) == 8 and shapes[:2] == [('ldr', 'd3, [x8, #0x678]'), ('fcmp', 'd3, #0.0')]:
        if (shapes[2] == ('b.eq', f'#{code[7].address:#x}') and
                shapes[3:6] == [('ldr', 'd3, [x8, #0x628]'), ('fcmp', 'd3, #0.0'), ('cset', 'w8, ne')] and
                shapes[6] == ('b', f'#{code[-1].address+4:#x}') and shapes[7] == ('mov', 'w8, #0')):
            return dict(kind='both_nonzero', fields=[0x678, 0x628])
    # These constants are decoded from MOV immediates, rather than supplied by the result formula.
    if len(code) in (7, 8) and code[0].mnemonic == code[3 if len(code) == 7 else 4].mnemonic == 'mov':
        second = 3 if len(code) == 7 else 4
        reg = code[0].op_str.split(',')[0]
        if code[second].op_str.split(',')[0] != reg:
            raise ValueError('Different constant registers')
        try:
            constants = [struct.unpack('<d', (code[k].operands[1].imm & ((1<<64)-1)).to_bytes(8, 'little'))[0]
                         for k in (0, second)]
        except (IndexError, AttributeError) as error:
            raise ValueError('Unsupported constant materialization') from error
        epsilon, negative = constants
        if not math.isfinite(epsilon) or epsilon <= 0 or negative != -epsilon:
            raise ValueError('Expected symmetric finite comparison constants')
        if len(code) == 7:
            expected = [shapes[0], ('fmov', f'd0, {reg}'), ('fcmp', 'd1, d0'), shapes[3],
                        ('fmov', f'd0, {reg}'), ('fccmp', 'd1, d0, #4, mi'),
                        ('b.gt', code[-1].op_str)]
            if shapes == expected:
                return dict(kind='outside_epsilon', register='d1', epsilon=epsilon,
                            bypass=code[-1].operands[0].imm)
        else:
            expected = [shapes[0], ('fmov', f'd1, {reg}'), ('fcmp', 'd0, d1'),
                        ('b.pl', code[3].op_str), shapes[4], ('fmov', f'd1, {reg}'),
                        ('fcmp', 'd0, d1'), ('b.le', code[3].op_str)]
            if shapes == expected:
                return dict(kind='outside_epsilon', register='d0', epsilon=epsilon,
                            callback=code[3].operands[0].imm)
    raise ValueError('Native condition kernel is outside the proved forms')


def evaluate(predicate, values):
    """Evaluate the recovered mathematical predicate for finite inputs only."""
    if not all(math.isfinite(x) for x in values):
        raise ValueError('This reference excludes native FP exception/NaN behavior')
    if predicate['kind'] == 'both_nonzero' and len(values) == 2:
        return all(x != 0 for x in values)
    if predicate['kind'] == 'outside_epsilon' and len(values) == 1:
        return abs(values[0]) >= predicate['epsilon']
    raise ValueError('Wrong predicate inputs')


def preserved(code, register):
    """Reject any write to a register or its scalar/vector aliases."""
    def key(name):
        if name[:1] in 'vqdshb' and name[1:].isdigit():
            return 'fp'+name[1:]
        if name[:1] in 'xw' and name[1:].isdigit():
            return name[1:]
        return name
    target = key(register)
    if any(key(i.reg_name(r)) == target for i in code for r in i.regs_access()[1]):
        raise ValueError(f'Native predicate provenance overwrites {register}')


def field_anchor(stream, base, relative, control):
    """Find an exact width-2 pool reference at the constructor's field position."""
    matches = []
    for offset, words in packets(stream):
        n = command_count(words[0])
        pool = 2*(1+n)
        for index, word in enumerate(words[1:1+n]):
            if word == control and word & 63 in range(0x10, 0x20):
                position = offset + pool + (word & 15)
                if position == relative and position + 2 <= offset + 2*len(words):
                    matches.append(dict(packet_byte=base+offset, operation=index,
                                        control=word, pool_byte_offset=word & 15,
                                        field_byte=base+position, width=2))
    if len(matches) != 1:
        raise ValueError('No unique constructor-to-control field match')
    return matches[0]


def return_shape(words):
    """Count pool bytes left after other indexed transfers in two proved return forms."""
    from header_study import families
    kinds = families(words[0])
    n = command_count(words[0])
    if len(words) != (words[0] & 31) or words[1:1+n].count(0x00f8) != 1:
        raise ValueError('Expected one framed 00f8 control')
    covered = set()
    for kind, control in zip(kinds, words[1:1+n]):
        if control == 0x00f8 and kind == 3:
            continue
        if kind != 4 or control & 0xff0 != 0xfe0 or control & 1:
            raise ValueError('Other coissued operation is outside this check')
        offset = control & 15
        covered.update((offset, offset+1))
    pool_bytes = 2*(len(words)-1-n)
    if covered != set(range(pool_bytes)):
        raise ValueError('Unassigned/out-of-range pool bytes')
    return dict(header=words[0], family=3, pool_bytes=pool_bytes,
                pool_bytes_assigned_to_other_transfers=len(covered))


def return_inventory(native, pairings):
    """Locate 00f8 base words and their following packets in primary render streams."""
    from emulator_target_study import segment_stream, verify_list
    from header_study import UnsupportedLayout, families

    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    scanned = 0
    occurrences = []
    for cls, (_, _, lists) in sorted(pairings.items()):
        render = [entry for entry in lists or [] if entry[1] == 0]
        if not render:
            continue
        if len(render) != 1:
            raise ValueError(f'{cls}: expected one render list')
        entry = render[0]
        verify_list(native, entry)
        segment = max(entry[3], key=lambda item: item[1])
        rows = packets(segment_stream(native, segment))
        scanned += 1
        for index, (offset, words) in enumerate(rows):
            controls = words[1:1+command_count(words[0])]
            if 0x00f8 not in controls:
                continue
            try:
                layout = families(words[0])
            except UnsupportedLayout:
                layout = None
            remaining = len(rows)-index-1
            for slot, word in enumerate(controls):
                if word == 0x00f8:
                    occurrences.append(dict(cls=cls, source=segment[3], offset=offset,
                                            header=words[0], slot=slot,
                                            family=None if layout is None else layout[slot],
                                            remaining_packets=remaining,
                                            successor=rows[index+1][1] if remaining else []))
    return dict(primary_streams=scanned, occurrences=occurrences)


def report(native):
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    import capstone
    from transfer_study import constructor_memory
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    def code(start, end):
        rows = list(md.disasm(native[start:end], start))
        if len(rows)*4 != end-start:
            raise ValueError('Native window is not completely decoded')
        return rows
    # Exact constructor boundaries from the Mach-O function-start table.
    memories = {address: constructor_memory(code(address, end), native)
                for address, end in ((0x42e14, 0x4439c), (0x34d690, 0x3518b8))}
    required = {
        0x41400: ('mov', 'x19, x0'), 0x41b38: ('ldr', 'x8, [x19, #0x38]'),
        0x34c268: ('mov', 'x19, x0'), 0x34c2a4: ('mov', 'x22, x19'),
        0x34c2a8: ('ldr', 'x8, [x22, #8]!'), 0x34c2ac: ('mov', 'x21, x22'),
        0x34c2b0: ('ldr', 'x9, [x21, #0x30]!'),
        0x34c2c4: ('ldr', 'd1, [x9, #0x8d8]'),
        0x34c73c: ('ldr', 'x8, [x21]'), 0x34c74c: ('ldr', 'd0, [x8, #0x88]'),
        0x34c9e8: ('ldr', 'x8, [x21]'), 0x34c9f8: ('ldr', 'd0, [x8, #0x868]'),
        0x41cac: ('tbz', 'w8, #0, #0x41ce0'),
    }
    for pc, expected in required.items():
        ins = code(pc, pc+4)[0]
        if (ins.mnemonic, ins.op_str) != expected:
            raise ValueError('Native pointer/input definition does not match the proved path')
    specs = [
        (0x42e14, 0x670, 0x41c14, 0x41c34, 0x77d494, 0x1766, 0x1052),
        (0x34d690, 0x8d0, 0x34c330, 0x34c34c, 0x77ece0, 0x519a, 0xae54),
        (0x34d690, 0x80, 0x34c7bc, 0x34c7dc, 0x77ece0, 0x519a, 0x7050),
        (0x34d690, 0x860, 0x34ca60, 0x34ca80, 0x77ece0, 0x519a, 0xfe50),
    ]
    rows = []
    for ctor, field, begin, end, source, length, control in specs:
        memory = memories[ctor]
        relative = int.from_bytes(bytes(memory[field+i] for i in range(4)), 'little')
        default = struct.unpack('<d', bytes(memory[field+8+i] for i in range(8)))[0]
        stream = swap_words(native[source:source+((length+3) & ~3)])[:length]
        rows.append(dict(native_condition=begin, constructor=ctor, record_field=field,
                         relative_program_field=relative, default=default,
                         predicate=classify(code(begin, end)),
                         dsp_reference=field_anchor(stream, 0x20, relative, control)))
    # Concrete def-use bridges, checked independently of constructor constants.
    preserved(code(0x41b3c, 0x41c14), 'x8')
    preserved(code(0x41c34, 0x41cac), 'w8')
    preserved(code(0x34c2c8, 0x34c338), 'd1')
    preserved(code(0x34c750, 0x34c7c4), 'd0')
    preserved(code(0x34c9fc, 0x34ca68), 'd0')
    preserved(code(0x34c2b4, 0x34c9e8), 'x21')
    preserved(code(0x41404, 0x41c14), 'x19')
    preserved(code(0x34c26c, 0x34ca68), 'x19')
    preserved(code(0x34c2b4, 0x34c2c4), 'x9')
    preserved(code(0x34c740, 0x34c74c), 'x8')
    preserved(code(0x34c9ec, 0x34c9f8), 'x8')
    mode_field = memories[0x42e14]
    mode = dict(record_field=0x620,
                program_position=int.from_bytes(bytes(mode_field[0x620+i] for i in range(4)), 'little'),
                default=struct.unpack('<d', bytes(mode_field[0x628+i] for i in range(8)))[0])
    stub = packets(swap_words(native[0x77ec44:0x77ec4c])[:6])[0][1]
    fet = swap_words(native[0x8372f4:0x8372f4+0x1cc])[:0x1ca]
    tail = next(words for off, words in packets(fet) if off == 0x1ba)
    return dict(native_sha256=NATIVE_SHA256, predicate_sources=rows, execution_ready=False,
                dsp4_additional_mode_record=mode,
                return_examples=[return_shape(stub), return_shape(tail)],
                limitations=['Native predicates and exact DSP field anchors, not a BMC register/condition-bit decoder.',
                             'DSP4 constructor record at +620 has program position zero and is not assigned a DSP literal.',
                             'Finite native reference only; no saved return state or pipeline timing proof.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=Path)
    parser.add_argument('--inventory', action='store_true', help='Inspect primary streams using the prepared pairing metadata')
    args = parser.parse_args()
    try:
        native = args.native_bin.read_bytes()
        if args.inventory:
            import lib
            result = return_inventory(native, lib.pairs())
        else:
            result = report(native)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
