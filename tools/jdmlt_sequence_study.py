"""Static JDMLT_B sequence-selector and return-context checks."""
import hashlib
import json
import struct

from bmc_dsp import command_count, literal, packets
from condition_return_study import preserved
from emulator_target_study import segment_stream, verify_list
from header_study import families, reference
from line_prefix_study import descriptor, literal_calls
from parent_control_study import NATIVE_SHA256, controls, native_list

CLASS = 'SIM_MFX_JDMLT_B'
SEQUENCES = ((1, 0, 2), (1, 2, 0), (0, 1, 2), (0, 2, 1), (2, 1, 0), (2, 0, 1))
FUNCTIONS = (0x131bec, 0x131e74, 0x132298, 0x13275c)


def sequence_word(sequence, reverb_type):
    """Evaluate the stock setter's clamped selectors, with the setter's write enabled."""
    if type(sequence) is not int or type(reverb_type) is not int:
        raise ValueError('Expected integer selectors')
    order = SEQUENCES[min(5, max(0, sequence))]
    gate = min(6, max(0, reverb_type)) >= 3
    return sum((3 if gate and selector == 2 else selector) << (4*slot)
               for slot, selector in enumerate(order))


def study():
    import lib
    import parse
    from transfer_study import constructor_memory, records_from_memory

    native = lib.Z
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    render = [item for item in lib.pairs()[CLASS][2] if item[1] == 0]
    if len(render) != 1 or render[0][0] != 0xa46f00:
        raise ValueError('Expected one JDMLT_B render list')
    verify_list(native, render[0])
    segment = max(render[0][3], key=lambda item: item[1])
    base, length, _, source = segment
    if (base, length) != (0x8000, 0x78a):
        raise ValueError('Unexpected JDMLT_B primary segment')
    stream = segment_stream(native, segment)
    rows = dict(packets(stream))

    decoder = lib.md()
    decoder.detail = True

    def code(start, end):
        result = list(decoder.disasm(native[start:end], start))
        if [ins.address for ins in result] != list(range(start, end, 4)):
            raise ValueError('Incomplete native instruction range')
        return result

    def expect(pc, mnemonic, operands):
        ins = code(pc, pc+4)[0]
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'Unexpected instruction at {pc:#x}')

    if tuple(struct.iter_unpack('<HHH', native[0x829258:0x82927c])) != SEQUENCES:
        raise ValueError('Sequence table changed')
    if struct.unpack_from('<4Q', native, 0xa01ec0) != FUNCTIONS:
        raise ValueError('Native dispatch table changed')
    setter = code(0x2d1150, 0x2d1364)
    if literal_calls(setter) != [dict(slot_load=0x2d1308, call=0x2d1314, symbol=0xa47750)]:
        raise ValueError('Unexpected setter literal destination')
    selector = descriptor(native, 0xa47750)
    if selector['records'] != [dict(absolute_byte=0x8018, relative_byte=0x18, width=2)]:
        raise ValueError('Selector descriptor changed')
    for anchor in (
        (0x2d0004, 'ldr', 'x8, [x8, #0x50]'), (0x2d0008, 'adrp', 'x1, #0xa46000'),
        (0x2d000c, 'add', 'x1, x1, #0xf00'), (0x2d0010, 'blr', 'x8'),
        (0x2d1268, 'adrp', 'x8, #0x829000'), (0x2d126c, 'add', 'x8, x8, #0x258'),
        (0x2d1274, 'ldrh', 'w9, [x8, x9]'), (0x2d128c, 'csel', 'w9, w9, w12, ne'),
        (0x2d12a4, 'orr', 'w9, w9, #0x30'), (0x2d12b8, 'orr', 'w9, w9, w12, lsl #4'),
        (0x2d12dc, 'lsl', 'w8, w8, #8'), (0x2d12f0, 'ucvtf', 'd0, w8'),
        (0x2d12f8, 'mov', 'x8, #0x3f10000000000000'), (0x2d1300, 'fmul', 'd0, d0, d1'),
        (0x130c94, 'ldr', 'x20, [x22, #0x18]'), (0x130c98, 'add', 'x24, x20, #0x5c0'),
        (0x130cb0, 'ldr', 'd0, [x20, #0x18]'), (0x130cb8, 'ldr', 'd0, [x20, #8]'),
        (0x130cc0, 'and', 'x11, x10, x9'), (0x130cd4, 'fcvtzu', 'w11, d0, #0xe'),
        (0x130cd8, 'asr', 'x9, x9, #4'), (0x130ce4, 'adrp', 'x9, #0xa01000'),
        (0x130ce8, 'add', 'x9, x9, #0xec0'), (0x130cec, 'ldr', 'x11, [x9, w11, uxtw #3]'),
        (0x130cf4, 'and', 'x10, x12, x10'), (0x130d00, 'fcvtzu', 'w10, d0, #0xe'),
        (0x130d04, 'asr', 'x12, x12, #4'), (0x130d10, 'fcvtzu', 'w12, d0, #0xe'),
        (0x130d14, 'ldr', 'x19, [x9, w10, uxtw #3]'),
        (0x130d18, 'ldr', 'x9, [x9, w12, uxtw #3]'), (0x130d1c, 'str', 'x9, [sp, #0x20]'),
        (0x130f14, 'ldr', 'x8, [sp, #0x20]'),
    ):
        expect(*anchor)
    for setup, call, target in ((0x130d7c, 0x130d90, 'x11'),
                                (0x130e30, 0x130e44, 'x19'),
                                (0x130f00, 0x130f18, 'x8')):
        expect(setup, 'mov', 'x3, x24')
        preserved(code(setup+4, call), 'x3')
        expect(call, 'blr', target)
    for anchor in (
        (0x130d70, 'add', 'x1, sp, #0x50'), (0x130da0, 'ldp', 'd2, d1, [sp, #0x50]'),
        (0x130e24, 'add', 'x1, sp, #0x40'), (0x130e88, 'ldr', 'd3, [sp, #0x48]'),
        (0x130e90, 'ldr', 'd3, [sp, #0x40]'), (0x130ef4, 'add', 'x1, sp, #0x30'),
        (0x130f5c, 'ldr', 'd3, [sp, #0x38]'), (0x130f64, 'ldr', 'd3, [sp, #0x30]'),
    ):
        expect(*anchor)
    preserved(code(0x130cf0, 0x130d90), 'x11')
    preserved(code(0x130d18, 0x130d90), 'x19')

    ctor = parse.parse_ctor(CLASS)
    ctor_start, ctor_end = lib.func(ctor['ctor'])
    memory = constructor_memory(code(ctor_start, ctor_end), native)
    first_field, count, records = parse.parse_datsym(CLASS, ctor)
    if records != records_from_memory(memory, first_field, count) or first_field != 0x5c0:
        raise ValueError('Constructor record provenance changed')
    defaults = [struct.unpack('<d', bytes(memory[field+i] for i in range(8)))[0]
                for field in (8, 0x18)]
    positions = [int.from_bytes(bytes(memory[field+i] for i in range(4)), 'little')
                 for field in (0, 0x10)]
    if (positions != [0x30, 0x18] or defaults != [15/16384, 0x210/16384]
            or defaults != [literal(stream[pos:pos+2]) for pos in positions]):
        raise ValueError('Unexpected selector or mask default')

    def transfer_operand(relative, raw):
        packet = max(offset for offset in rows if offset <= relative)
        words = rows[packet]
        kinds = families(words[0])
        pool = packet+2*(1+len(kinds))
        matching = [word for kind, word in zip(kinds, words[1:])
                    if kind == 4 and word & 0xff1 == 0xfe0 and pool+(word & 15) == relative]
        if len(matching) != 1 or int.from_bytes(stream[relative:relative+2], 'big') != raw:
            raise ValueError('Checked field is not the expected indexed transfer operand')
        return packet, matching[0]

    anchors = []
    for slot, (pc, operands, displacement, relative, address, raw, ret) in enumerate((
        (0x131c44, 'w9, [x3, #0x94]', 0x94, 0x13e, 0x15, 0x01a5, 0x208),
        (0x131ec4, 'w10, [x3, #0x11c]', 0x11c, 0x22c, 0x26, 0x01b6, 0x332),
        (0x1322b4, 'w12, [x3, #0x164]', 0x164, 0x34a, 0x2f, 0x01bf, 0x564),
        (0x132960, 'w11, [x3, #0x564]', 0x564, 0x678, 0x16, 0x4016, 0x76e),
    )):
        expect(pc, 'ldr', operands)
        preserved(code(FUNCTIONS[slot], pc), 'x3')
        if records[(displacement-4)//8] != (relative, address):
            raise ValueError('Native field does not resolve to the checked DSP operand')
        transfer_operand(relative, raw)
        if 0x00f8 not in rows[ret][1:1+command_count(rows[ret][0])]:
            raise ValueError('Expected the nearby 00f8 base word')
        anchors.append(dict(selector=slot, native_function=FUNCTIONS[slot], native_load=pc,
                            object_displacement=displacement, relative_operand=relative,
                            native_index=address, stored_operand=raw, following_00f8=ret))

    for anchor in (
        (0x131c18, 'mov', 'x22, x5'), (0x131c20, 'mov', 'x23, x3'),
        (0x131e18, 'ldr', 'w8, [x26]'), (0x131e1c, 'ldr', 'w9, [x23, #0xb4]'),
        (0x131e20, 'ldr', 'x10, [x22, #0x18]'), (0x131e24, 'ldr', 'w11, [x22, #0x20]'),
        (0x131e28, 'add', 'w8, w9, w8'), (0x131e2c, 'sub', 'w8, w8, w11'),
        (0x131e30, 'and', 'w8, w8, #0x7ff'), (0x131e34, 'str', 'd0, [x10, w8, uxtw #3]'),
        (0x131ea8, 'mov', 'x20, x5'), (0x131eac, 'mov', 'x22, x3'),
        (0x1321ec, 'ldr', 'w8, [x25]'), (0x1321f0, 'ldr', 'x9, [x20, #0x18]'),
        (0x1321f4, 'ldr', 'w10, [x20, #0x20]'), (0x132224, 'ldr', 'w11, [x22, #0x144]'),
        (0x132228, 'add', 'w8, w11, w8'), (0x13222c, 'sub', 'w8, w8, w10'),
        (0x132230, 'and', 'w8, w8, #0x7ff'), (0x132234, 'str', 'd2, [x9, w8, uxtw #3]'),
        (0x131e70, 'ret', ''), (0x132294, 'ret', ''),
    ):
        expect(*anchor)
    for lo, hi, register in (
        (0x131c1c, 0x131e20, 'x22'), (0x131c24, 0x131e1c, 'x23'),
        (0x131eac, 0x1321f4, 'x20'), (0x131eb0, 0x132224, 'x22'),
        (0x1321f0, 0x132228, 'w8'), (0x1321f4, 0x132234, 'x9'),
        (0x1321f8, 0x13222c, 'w10'),
    ):
        preserved(code(lo, hi), register)
    stores = []
    for displacement, relative, index, raw, packet, control, store, ret in (
        (0xb4, 0x21c, 0x19, 0x01a9, 0x210, 0x9fe4, 0x131e34, 0x131e70),
        (0x144, 0x33a, 0x2b, 0x01bb, 0x332, 0xbfe0, 0x132234, 0x132294),
    ):
        if records[(displacement-4)//8] != (relative, index) or transfer_operand(relative, raw) != (packet, control):
            raise ValueError('Return-adjacent store provenance changed')
        stores.append(dict(native_store=store, native_return=ret, dsp_packet=packet,
                           dsp_control=control, relative_operand=relative, native_index=index))

    branch = rows[0x11c]
    if families(branch[0]) != (1, 1, 3) or branch[3] != 0x0080:
        raise ValueError('Unexpected 0080 packet')
    uses = [reference(word & 63, 8) for word in branch[1:3]]
    if [(use['offset'], use['width']) for use in uses] != [(2, 3), (5, 3)]:
        raise ValueError('The two ALU literals no longer leave the first pool word')
    target = 2*branch[4]
    if (target-base != 0x784 or rows[target-base] != [0x0b02, 0x00f8]
            or rows[0x788] != [0x0001]):
        raise ValueError('The remaining word no longer matches the terminal 00f8 location')
    parent = native_list(native, 0x9faee0)['segments'][0]
    segment_tuple = tuple(parent[key] for key in ('base', 'length', 'capacity', 'source'))
    parent_refs = controls(segment_stream(native, segment_tuple), parent['base'], {base})
    return dict(source=source, base=base, selector=selector, default_word=0x210,
                sequence_words=[[sequence_word(i, t) for t in (0, 3)] for i in range(6)],
                anchors=anchors, stores=stores, candidate_target=target, target_packet=0x784,
                local_indexed_00a=controls(stream, base, set())['indexed_00a_candidates'],
                parent_references=[r for r in parent_refs['indexed_00a_candidates']
                                   if r['candidate_entry_byte'] == base])


if __name__ == '__main__':
    print(json.dumps(study(), indent=2))
