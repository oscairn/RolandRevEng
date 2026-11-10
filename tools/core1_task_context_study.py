"""Read-only, build-pinned stock CORE1 software-IRQ callback and queue metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PAYLOAD_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def priority_byte(argument):
    if not isinstance(argument, int) or not 0 <= argument < 32:
        raise ValueError('Expected a supported five-bit priority argument')
    return argument << 3


def nvic_lines(irq):
    if not isinstance(irq, int) or not 0 <= irq < 240:
        raise ValueError('Expected an external IRQ number below 240')
    bank = 4 * (irq // 32)
    return dict(irq=irq, priority_address=0xe000e400 + irq,
                enable_address=0xe000e100 + bank,
                disable_address=0xe000e180 + bank, bit=1 << (irq % 32))


def report(core):
    from capstone.arm import ARM_OP_MEM, ARM_REG_PC
    if hashlib.sha256(core.data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')

    def ins(address):
        offset = core.offset(address)
        return next(core.md.disasm(core.data[offset:offset + 4], address, count=1))

    def expect(address, mnemonic, operands):
        row = ins(address)
        if (row.mnemonic, row.op_str) != (mnemonic, operands):
            raise ValueError(f'Unexpected instruction at {address:#x}')
        return row

    def literal(address):
        row = ins(address)
        op = row.operands[1]
        if (row.mnemonic not in ('ldr', 'ldr.w') or op.type != ARM_OP_MEM
                or op.mem.base != ARM_REG_PC):
            raise ValueError('Expected a PC-relative literal load')
        return core.u32(((address + 4) & ~3) + op.mem.disp)

    table, callback_base = literal(0x011020ce), literal(0x011020b6)
    for site, target in ((0x011004de, 0x01100e2a), (0x01100e42, 0x01102986),
                         (0x01102aa6, 0x01103304), (0x01103332, 0x0110a760),
                         (0x0110334a, 0x0111ece0)):
        expect(site, 'bl', f'#{target:#x}')
    expect(0x01100e2e, 'movw', 'r2, #0xf8ff')
    expect(0x01100e34, 'orr', 'r1, r1, #0x300')
    expect(0x01102a28, 'movs', 'r0, #0x10')
    if literal(0x01102a26) + 0x400 != nvic_lines(6)['priority_address']:
        raise ValueError('Unexpected ingress priority register')
    expect(0x011020b8, 'str.w', 'r2, [r1, r0, lsl #2]')
    expect(0x01102098, 'lsls', 'r3, r3, #0x1b')
    expect(0x0110209a, 'lsrs', 'r3, r3, #0x18')
    expect(0x011020d6, 'str', 'r0, [r1]')
    if literal(0x011020d4) != 0xe000ef00:
        raise ValueError('Unexpected software-trigger register')
    tasks = []
    for initializer, task_id, priority, callback in (
            (0x0111ece0, 3, 10, 0x0111ea25),
            (0x0110a760, 5, 20, 0x0110a65d)):
        expect(initializer + 2, 'movs', f'r3, #{priority:#x}')
        offset = expect(initializer + 4, 'subw',
                        f'r2, pc, #{initializer + 8 - callback:#x}').operands[2].imm
        resolved = initializer + 8 - offset
        name_ins = ins(initializer + 8)
        if name_ins.mnemonic != 'adr':
            raise ValueError('Expected task name ADR')
        name_address = ((initializer + 12) & ~3) + name_ins.operands[1].imm
        name_offset = core.offset(name_address)
        name = core.data[name_offset:name_offset + 16].split(b'\0')[0].decode('ascii')
        expect(initializer + 10, 'movs', f'r0, #{task_id}')
        expect(initializer + 12, 'bl', '#0x1102064')
        irq = struct.unpack_from('<h', core.data, core.offset(table + 2 * task_id))[0]
        vector = 0x01100000 + 4 * (16 + irq)
        handler = core.u32(vector) & ~1
        displacement = task_id * 4
        if literal(handler + 2) + 0x80 != callback_base:
            raise ValueError('Callback wrapper base differs from registration table')
        expect(handler + 8, 'sub.w', 'r0, r4, #0x40')
        expect(handler + 18, 'add.w', 'r1, r4, #0x40')
        expect(handler + 26, 'add.w', 'r0, r1, #0x40')
        expect(handler + 30, 'ldr', f'r0, [r0, #{displacement:#x}]')
        expect(handler + 36, 'blx', 'r0')
        tasks.append(dict(id=task_id, name=name, initializer=initializer,
                          callback_thumb=resolved, callback_slot=callback_base + displacement,
                          priority_argument_decimal=priority, priority_byte=priority_byte(priority),
                          vector_address=vector, handler=handler, **nvic_lines(irq)))
    expect(0x0110a47c, 'cmp.w', 'r0, #0x600')
    expect(0x011271ca, 'movs', 'r0, #0x12')
    expect(0x011271cc, 'bl', '#0x1103762')
    expect(0x01103762, 'lsls', 'r0, r0, #3')
    if literal(0x01103764) + 0x400 != nvic_lines(91)['priority_address']:
        raise ValueError('Unexpected wait-timer priority register')
    expect(0x0110a5c4, 'ldr', 'r0, [r4]')
    expect(0x0110a5c6, 'bl', '#0x110a390')
    expect(0x0110a3b2, 'str.w', 'r0, [r3, ip, lsl #2]')
    return dict(payload_sha256=PAYLOAD_SHA256, task_irq_map=table,
                callback_table=callback_base, software_trigger=0xe000ef00, tasks=tasks,
                startup_aircr_group_bits=3,
                ingress_irq=dict(priority_byte=0x10, **nvic_lines(6)),
                wait_timer=dict(priority_argument_decimal=18, priority_byte=priority_byte(18),
                                **nvic_lines(91)),
                queues=dict(ingress_slots=512, assignment_slots=2048,
                            assignment_high_water=0x600, assignment_copies_word_by_value=True,
                            gating_sites=[0x0110295e, 0x0110a5b0],
                            reenable_sites=[0x0111ec9a, 0x0110a748]),
                limits=['Compiled callback bindings, not observed runtime state.',
                        'Priority grouping, implemented bits and interrupt masks remain relevant.',
                        'No external IPC peer or universally safe manager-call context established.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(Core1(args.image)), indent=2))
    except (ValueError, OSError, StopIteration, IndexError) as exc:
        parser.error(str(exc))
