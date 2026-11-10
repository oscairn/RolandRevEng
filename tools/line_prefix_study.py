"""Read-only LINE literal descriptor/count proof; no new DSP opcode admission."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from parent_control_study import NATIVE_SHA256

FIRMWARE_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def descriptor(data, address):
    """Read only the observed LP64, segment-0 literal groups, respecting count."""
    if address < 0 or address+32 > len(data):
        raise ValueError('Descriptor outside image')
    table = struct.unpack_from('<Q', data, address+0x10)[0]
    count = data[address+0x18]
    if count > 16 or table % 4 or table+12*count > len(data):
        raise ValueError('Unsupported count/table range')
    records = []
    for index in range(count):
        absolute, relative, width = struct.unpack_from('<III', data, table+12*index)
        if width not in (2, 3, 4):
            raise ValueError('Outside observed segment-0 width layout')
        records.append(dict(absolute_byte=absolute, relative_byte=relative, width=width))
    return dict(symbol=address, table=table, count=count, records=records)


def literal_calls(code):
    """Trace the narrow straight-line slot-c8 load to its ADRP/ADD symbol argument."""
    from capstone import arm64 as a64
    result = []
    for index, ins in enumerate(code):
        ops = ins.operands
        if (ins.mnemonic != 'ldr' or len(ops) != 2 or ops[1].type != a64.ARM64_OP_MEM
                or ops[1].mem.disp != 0xc8):
            continue
        if ins.op_str not in ('x8, [x8, #0xc8]', 'x2, [x8, #0xc8]'):
            raise ValueError('Unclassified literal virtual-slot load')
        if index == 0 or (code[index-1].mnemonic, code[index-1].op_str) != ('ldr', 'x8, [x0]'):
            raise ValueError('Literal slot lacks checked manager-vtable path')
        target, symbol = ins.reg_name(ops[0].reg), None
        for following in code[index+1:index+17]:
            if following.mnemonic in ('blr', 'br'):
                if following.op_str != target or symbol is None:
                    raise ValueError('Unclassified literal call/argument')
                result.append(dict(slot_load=ins.address, call=following.address, symbol=symbol))
                break
            if following.mnemonic == 'bl' or following.mnemonic.startswith('b.'):
                raise ValueError('Control flow interrupts literal-call provenance')
            shape = following.op_str
            if following.mnemonic == 'adrp' and shape.startswith('x1, #'):
                symbol = following.operands[1].imm
                continue
            if following.mnemonic == 'add' and shape.startswith('x1, x1, #') and symbol is not None:
                if following.operands[2].shift.value:
                    raise ValueError('Unexpected shifted symbol address')
                symbol += following.operands[2].imm
                continue
            writes = {following.reg_name(register) for register in following.regs_access()[1]}
            if target in writes or 'w'+target[1:] in writes:
                raise ValueError('Literal call target overwritten')
            if writes & {'x1', 'w1'}:
                symbol = None
        else:
            raise ValueError('Literal slot has no bounded call')
    return result


def report(data, core=None):
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native artifact')
    import capstone
    from transfer_study import constructor_memory
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True

    def code(start, end):
        rows = list(md.disasm(data[start:end], start))
        if len(rows)*4 != end-start:
            raise ValueError('Incomplete native window')
        return rows

    def check(address, expected):
        if [(i.mnemonic, i.op_str) for i in code(address, address+4*len(expected))] != expected:
            raise ValueError(f'Native path mismatch at {address:#x}')

    calls = literal_calls(code(0x17ca58, 0x17d2ec))
    if calls != [dict(slot_load=0x17cafc, call=0x17cb08, symbol=0xa16df8),
                 dict(slot_load=0x17cb4c, call=0x17cb58, symbol=0xa16e18),
                 dict(slot_load=0x17d120, call=0x17d13c, symbol=0xa17248)]:
        raise ValueError('Scoped LINE literal call inventory changed')
    groups = [descriptor(data, call['symbol']) for call in calls]
    if [[r['relative_byte'] for r in group['records']] for group in groups] != [
            [0xec, 0xf0, 0x118, 0x11c], [0xe6, 0xe9, 0x112, 0x115], [0x45]]:
        raise ValueError('LINE literal groups changed')
    memory = constructor_memory(code(0x2dfe04, 0x2e0248), data)
    representatives = {int.from_bytes(bytes(memory[field+i] for i in range(4)), 'little'): field+8
                       for field in range(0, 0x80, 16)}
    for group in groups:
        group['native_representative_double_field'] = representatives[group['records'][0]['relative_byte']]
    if representatives.get(0x14) != 0x58 or representatives.get(0x24) != 0x78 or any(
            relative in representatives for relative in (0x17, 0x27)):
        raise ValueError('Prefix representative record mapping changed')
    check(0x2df730, [('ldr', 'x8, [x0, #0x28]'), ('ldr', 'x9, [x1, #0x10]'),
                     ('ldr', 'w9, [x9, #4]'), ('ldr', 'w10, [x8]')])
    check(0xfba54, [('ldr', 'x0, [x0, #0x28]'), ('cbz', 'x0, #0xfba80'),
                    ('fmov', 'd8, d0'), ('ldr', 'x8, [x0]'), ('ldr', 'x8, [x8, #0x10]'),
                    ('blr', 'x8'), ('cbz', 'x0, #0xfba74'), ('str', 'd8, [x0]')])
    body = code(0xfba10, 0xfbaa0)
    if [i.address for i in body if i.mnemonic == 'blr'] != [0xfba68]:
        raise ValueError('Native writer no longer has one getter call')
    getter = code(0x2df728, 0x2df824)
    reads = [i.op_str for i in getter if i.mnemonic == 'ldr' and i.op_str.startswith('w10, [x8')]
    if reads != ['w10, [x8]']+[f'w10, [x8, #{field:#x}]' for field in range(16, 128, 16)]:
        raise ValueError('Native getter record selection changed')
    check(0xfd570, [('ret', '')])
    if struct.unpack_from('<Q', data, 0x9e53f8+16+0xc8)[0] != 0xfba10:
        raise ValueError('Native manager literal slot changed')
    if struct.unpack_from('<Q', data, 0xa49620+16+0x10)[0] != 0x2df728:
        raise ValueError('LINE simulator getter slot changed')
    adjacent = [descriptor(data, address) for address in (0xa3f560, 0xa3f580, 0xa51e08, 0xa51e28)]
    if [(g['count'], g['records'][0]['relative_byte']) for g in adjacent] != [(1, 0x14), (1, 0x17)]*2:
        raise ValueError('Adjacent-record negative control changed')
    firmware = None
    if core is not None:
        if hashlib.sha256(core.data).hexdigest() != FIRMWARE_SHA256:
            raise ValueError('Unsupported firmware artifact')
        from dramio_owner_study import expect
        for address, mnemonic, operands in (
            (0x011327f0, 'vmov.f32', 's16, s0'), (0x011327f4, 'ldrb', 'r0, [r1, #0xc]'),
            (0x01132840, 'ldrb', 'r0, [r5, #0xc]'), (0x01132842, 'movs', 'r4, #0'),
            (0x0113284c, 'mov.w', 'sl, #8'),
            (0x01132858, 'ldr', 'r2, [r5, #8]'), (0x0113285a, 'add.w', 'r7, r4, r4, lsl #1'),
            (0x01132860, 'ldr.w', 'r6, [r2, r7, lsl #2]'),
            (0x011328b6, 'ldr', 'r0, [r5, #8]'),
            (0x011328b8, 'add.w', 'r2, sl, r7, lsl #2'),
            (0x011328bc, 'vmov.f32', 's0, s16'), (0x011328c0, 'ldrb', 'r2, [r0, r2]'),
            (0x011328c8, 'bl', '#0x112ff4e'), (0x011328cc, 'ldrb', 'r0, [r5, #0xc]'),
            (0x011328ce, 'adds', 'r4, r4, #1'), (0x011328d0, 'cmp', 'r0, r4'),
            (0x011328d2, 'bgt', '#0x1132854')):
            expect(core, address, mnemonic, operands)
        firmware = dict(manager=0x011327e6, driver=0x0112ff4e, count_byte=12,
                        records_pointer_field=8, record_stride=12, same_saved_float_per_record=True)
    return dict(native_sha256=NATIVE_SHA256, scoped_line_literal_calls=calls, groups=groups,
                prefix_representatives={relative: representatives.get(relative) for relative in (0x14, 0x17, 0x24, 0x27)},
                native_update='one getter result / one double store; first descriptor record selects representative',
                adjacent_count1_controls=adjacent, firmware=firmware,
                prefix_grouping_proven=False, old_value_store_semantics_proven=False,
                new_interpreter_admission=False,
                limitations=['Only the direct literal-slot calls in the contiguous LINE class bodies are inventoried.',
                             'Other manager interfaces, arbitrary descriptors/raw writers and fixed-constant rules are not excluded.',
                             'Literal byte offsets and coefficient records are not DSP register addresses.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=Path)
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    try:
        from core1 import Core1
        print(json.dumps(report(args.native_bin.read_bytes(), Core1(args.core1) if args.core1 else None), indent=2))
    except (OSError, ValueError, KeyError, struct.error) as error:
        parser.exit(2, f'{error}\n')
