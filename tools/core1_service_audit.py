"""Offline, build-pinned CORE1 initializer and MMIO reply-frame checks; no device I/O."""
import argparse
import hashlib
import json
from pathlib import Path


BUILDS = {
    '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154':
        dict(name='bmc0', reset=0x01100e54, veneer=0x61076a64,
             walker=0x0112ce90, constructor=0x0111ed24, read=0x6102d2e6),
    'c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd':
        dict(name='bmc1', reset=0x01100e14, veneer=0x6107750c,
             walker=0x0112cad8, constructor=0x011258b0, read=0x61028846),
}


def prel32_entries(read_word, start, end):
    """Resolve every slot, including negative displacements, with 32-bit wrapping."""
    if not (0 <= start <= end <= 0xffffffff and start % 4 == end % 4 == 0
            and 0 < end - start <= 4096):
        raise ValueError('Invalid bounded initializer table')
    rows = []
    for slot in range(start, end, 4):
        pointer = (slot + read_word(slot)) & 0xffffffff
        if not pointer & 1:
            raise ValueError(f'Non-Thumb initializer at {slot:#x}')
        rows.append(dict(index=len(rows), slot=slot, thumb_pointer=pointer))
    return rows


def decoded_count(groups):
    """Model the four byte loads/BFI operations; accepts bytes, not a request record."""
    if len(groups) != 4 or any(not 0 <= byte <= 255 for byte in groups):
        raise ValueError('Expected four byte values')
    value = 0
    for byte in groups:
        value = ((value << 7) | (byte & 127)) & 0xffffffff
    return value


def reply_frame(count):
    """Report occupied half-open stack offsets; this is not a safe live-read limit."""
    if not isinstance(count, int) or not 0 <= count < 1 << 28:
        raise ValueError('Expected the decoded nonnegative 28-bit count')
    if count < 4:
        return dict(count=count, words=0, emitted=0, overlap={})
    words = min(count, 64) // 4
    emitted = 11 + 8 * words
    regions = {'local': (0, 80), 'saved_r4': (80, 84),
               'saved_lr': (84, 88), 'caller': (88, emitted)}
    return dict(count=count, words=words, emitted=emitted,
                data=[9, 9 + 8 * words], checksum=9 + 8 * words,
                terminator=10 + 8 * words,
                overlap={name: [lo, min(hi, emitted)]
                         for name, (lo, hi) in regions.items() if emitted > lo})


def audit(core):
    from capstone.arm import ARM_OP_MEM, ARM_REG_PC
    digest = hashlib.sha256(core.data).hexdigest()
    if digest not in BUILDS:
        raise ValueError('Unsupported CORE1 payload digest; no address guesses applied')
    build = BUILDS[digest]
    read_start = build['read']
    read_offset = core.offset(read_start)
    # Decode together to retain Thumb IT conditions on following instructions.
    read_instructions = {ins.address: ins for ins in core.md.disasm(
        core.data[read_offset:read_offset + 0x14c], read_start)}

    def instruction(address):
        if address in read_instructions:
            return read_instructions[address]
        offset = core.offset(address)
        return next(core.md.disasm(core.data[offset:offset + 4], address, count=1))

    def expect(address, mnemonic, operands):
        ins = instruction(address)
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'Unexpected instruction at {address:#x}')
        return ins

    def literal(address):
        ins = instruction(address)
        operand = ins.operands[1]
        if (ins.mnemonic != 'ldr' or operand.type != ARM_OP_MEM
                or operand.mem.base != ARM_REG_PC):
            raise ValueError(f'Expected literal load at {address:#x}')
        return core.u32(((address + 4) & ~3) + operand.mem.disp)

    reset, veneer, walker, ctor, read = (build[key] for key in
                                       ('reset', 'veneer', 'walker', 'constructor', 'read'))
    if core.u32(0x01100004) != reset | 1 or literal(reset + 0x6c) != 0x61000001:
        raise ValueError('Reset path mismatch')
    expect(reset + 0x6e, 'bx', 'r0')
    expect(0x61000004, 'bl', f'#{veneer:#x}')
    expect(0x6100001a, 'bl', f'#{veneer:#x}')
    expect(veneer, 'movw', 'ip, #0x4d7')
    expect(veneer + 4, 'movt', 'ip, #0x110')
    expect(veneer + 8, 'bx', 'ip')
    expect(0x011004da, 'bl', '#0x1100490')
    expect(0x011004be, 'bl', f'#{walker:#x}')

    expect(walker + 4, 'add', 'r4, pc')
    expect(walker + 8, 'add', 'r5, pc')
    start = (literal(walker + 2) + walker + 8) & 0xffffffff
    end = (literal(walker + 6) + walker + 12) & 0xffffffff
    for delta, mnemonic, operands in (
        (10, 'b', f'#{walker + 20:#x}'), (12, 'ldr', 'r0, [r4]'),
        (14, 'add', 'r0, r4'), (16, 'blx', 'r0'), (18, 'adds', 'r4, r4, #4'),
        (20, 'cmp', 'r4, r5'), (22, 'bne', f'#{walker + 12:#x}')):
        expect(walker + delta, mnemonic, operands)
    entries = prel32_entries(core.u32, start, end)
    for row in entries:
        core.offset(row['thumb_pointer'] & ~1)
    matching = [row for row in entries if row['thumb_pointer'] == ctor | 1]
    if len(matching) != 1:
        raise ValueError('Expected exactly one receiver initializer')

    base = literal(ctor + 2)
    vtables = [literal(ctor + 14), literal(ctor + 30)]
    initializer = instruction(ctor + 10).operands[0].imm
    expect(ctor + 10, 'bl', f'#{initializer:#x}')
    expect(ctor + 26, 'bl', f'#{initializer:#x}')
    expect(initializer, 'movs', 'r1, #0x10')
    expect(initializer + 2, 'str', 'r1, [r0, #4]')
    expect(initializer + 4, 'movs', 'r1, #0')
    expect(initializer + 6, 'strh.w', 'r1, [r0, #0x208]')
    expect(initializer + 10, 'bx', 'lr')
    expect(ctor + 16, 'str', 'r0, [r4]')
    expect(ctor + 18, 'add.w', 'r4, r4, #0x20c')
    expect(ctor + 32, 'str', 'r0, [r4]')
    expect(read, 'push', '{r4, lr}')
    expect(read + 20, 'sub', 'sp, #0x50')
    expect(read + 92, 'mov', 'r0, sp')
    expect(read + 158, 'adds', 'r0, #9')
    expect(read + 78, 'cmp', 'r2, #0x40')
    expect(read + 82, 'movgt', 'r2, #0x40')
    expect(read + 84, 'cmple', 'r2, #4')
    expect(read + 182, 'ldr', 'r1, [r3], #4')
    expect(read + 186, 'subs', 'r2, r2, #4')
    for delta in (192, 200, 208, 216, 224, 232, 240):
        expect(read + delta, 'strb', 'ip, [r0], #1')
    expect(read + 248, 'strb', 'r1, [r0], #1')
    expect(read + 252, 'cmp', 'r2, #4')
    expect(read + 254, 'bge', f'#{read + 182:#x}')
    expect(read + 256, 'add.w', 'r2, sp, #5')
    expect(read + 264, 'mov', 'ip, sp')
    expect(read + 308, 'strb', 'r1, [r0], #1')
    expect(read + 314, 'strb', 'r1, [r0], #1')
    expect(read + 318, 'sub.w', 'r1, r0, ip')
    expect(read + 322, 'mov', 'r0, ip')
    expect(read + 328, 'add', 'sp, #0x50')
    expect(read + 330, 'pop', '{r4, pc}')
    return dict(build=build['name'], payload_sha256=digest,
                initializer_table=dict(walker=walker, start=start, end=end,
                                       count=len(entries), receiver_entry=matching[0],
                                       base_initializer=initializer),
                receivers=[dict(object=base + i * 0x20c, vtable=vtable,
                                callback_thumb=core.u32(vtable + 4))
                           for i, vtable in enumerate(vtables)],
                mmio=dict(read_helper=read, local_bytes=80, saved_r4=[80, 84],
                          saved_lr=[84, 88], caller_start=88,
                          examples=[reply_frame(n) for n in (32, 35, 36, 40, 64)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(audit(Core1(args.image)), indent=2))
    except (ValueError, IndexError, StopIteration) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
