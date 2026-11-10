"""Check pinned CORE1 outbound queues and retry behavior; never sends a word."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from core1_task_context_study import PAYLOAD_SHA256, nvic_lines, priority_byte


def ring_metrics(write, read):
    """Quiescent six-bit indices only; the firmware's free count includes the sentinel."""
    if any(not isinstance(n, int) or not 0 <= n < 64 for n in (write, read)):
        raise ValueError('Expected two quiescent six-bit ring indices')
    used = (write-read) & 63
    return dict(used=used, reported_free=64-used, usable_free=63-used,
                enqueue_allowed=((write+1) & 63) != read)


def report(core):
    from capstone.arm import ARM_OP_MEM, ARM_REG_PC
    from core1_wait_study import expand_initial_data
    if hashlib.sha256(core.data).hexdigest() != PAYLOAD_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')

    def expect(address, rows):
        off = core.offset(address)
        actual = list(core.md.disasm(core.data[off:off+4*len(rows)], address, count=len(rows)))
        if [(i.mnemonic, i.op_str) for i in actual] != rows:
            raise ValueError(f'Unexpected outbound instruction sequence at {address:#x}')

    def literal(address):
        off = core.offset(address)
        ins = next(core.md.disasm(core.data[off:off+4], address, count=1))
        operand = ins.operands[1]
        if ins.mnemonic != 'ldr' or operand.type != ARM_OP_MEM or operand.mem.base != ARM_REG_PC:
            raise ValueError('Expected a PC-relative literal')
        return core.u32(((address+4) & ~3)+operand.mem.disp)

    expect(0x01125eae, [('ldr','r2, [r1, #0x24]'),('ldr','r3, [r1, #0x28]'),
        ('adds','r2, r2, #1'),('and','r2, r2, #0x3f'),('cmp','r2, r3'),
        ('bne','#0x1125ec6'),('ldr','r0, [r1, #0x30]'),('adds','r0, r0, #1'),
        ('str','r0, [r1, #0x30]'),('movs','r0, #0'),('bx','lr')])
    expect(0x01125ec8, [('ldr.w','ip, [r1, #0x24]'),
        ('str.w','r0, [r3, ip, lsl #2]'),('str','r2, [r1, #0x24]')])
    expect(0x01125ed2,[('ldr','r0, [r1, #0x34]'),('adds','r0, r0, #1'),
        ('str','r0, [r1, #0x34]'),('ldr','r3, [r1, #0x24]'),('ldr','r2, [r1, #0x28]'),
        ('movs','r0, #0'),('cmp','r3, r2'),('beq','#0x1125eee'),('nop',''),
        ('itte','lo'),('rsblo.w','r0, r2, #0x40'),('addlo','r0, r3'),
        ('subhs','r0, r3, r2'),('ldr','r2, [r1, #0x2c]'),('cmp','r2, r0'),
        ('it','lo'),('strlo','r0, [r1, #0x2c]')])
    expect(0x01125ef6, [('sev',''),('movs','r0, #1'),('bx','lr')])
    expect(0x01125f40,[('ldr','r2, [r0, #0x24]'),('ldr','r1, [r0, #0x28]'),
        ('movs','r0, #0'),('cmp','r2, r1'),('beq','#0x1125f56'),('nop',''),
        ('itte','lo'),('rsblo.w','r0, r1, #0x40'),('addlo','r0, r2'),
        ('subhs','r0, r2, r1'),('rsb.w','r0, r0, #0x40'),('bx','lr')])
    if (literal(0x01125eac),literal(0x01125ec6),literal(0x01125f68),
            literal(0x01125f78),literal(0x01125f3e)) != (
            0xe0043000,0xe0043138,0xe0043000,0xe0043038,0xe0043000):
        raise ValueError('Shared ring bases changed')
    expect(0x01125f7e, [('adds','r2, r2, #1'),('str','r2, [r1, #0x10]'),
        ('ldr','r2, [r3]'),('str','r2, [r0]'),('ldr','r0, [r1, #0x10]'),
        ('and','r0, r0, #0x3f'),('str','r0, [r1, #0x10]')])
    for site,target in ((0x01102a1e,0x01125ffc),(0x01102a22,0x0112600e),
                        (0x0110334e,0x0111ef96)):
        expect(site,[('bl',f'#{target:#x}')])
    expect(0x0111ef96,[('movs','r3, #0x12'),('subw','r2, pc, #0x133'),
        ('adr','r1, #0x158'),('movs','r0, #2'),('b.w','#0x1102064')])
    irq=struct.unpack_from('<h',core.data,core.offset(0x6108499e+4))[0]
    vector=0x01100000+4*(16+irq)
    if irq != 230 or core.u32(vector) != 0x0110213d:
        raise ValueError('TXDT vector changed')
    expect(0x0110215a,[('ldr','r0, [r0, #8]'),('cmp','r0, #0'),
        ('it','ne'),('blxne','r0')])
    expect(0x0111efb2,[('cpsid','i'),('bl','#0x111f4d8'),('movs','r0, #2'),
        ('bl','#0x11020c0'),('cpsie','i')])
    if literal(0x0111f4dc) != 0x2008203c or literal(0x0111f4ec) != 0x20095f0c:
        raise ValueError('Software output ring changed')
    expect(0x0111f4e2,[('adds','r1, r1, #1'),('ubfx','r1, r1, #0, #9'),
        ('cmp','r1, r2'),('beq','#0x111f50c')])
    expect(0x0111f50c,[('adr','r1, #0x98'),('movs','r0, #2'),('bl','#0x1134498'),
        ('ldr','r0, [r4, #0x10]'),('adds','r0, r0, #1'),('str','r0, [r4, #0x10]'),
        ('cpsie','i'),('pop','{r4, pc}')])
    loops=[]
    for address in (0x0111eee6,0x0111ef10,0x0111ef5a,0x0111ef84):
        expect(address,[('ldr','r0, [r4]'),('adds','r0, r0, #1'),('str','r0, [r4]'),
            ('ldr','r0, [sp, #4]'),('bl','#0x1125eac'),('cmp','r0, #0'),
            ('beq',f'#{address:#x}')])
        loops.append(address)
    expect(0x0111ee6c,[('add','r0, sp, #4'),('bl','#0x111f51e')])
    expect(0x0111eed4,[('bl','#0x1101a06'),('cmp','r0, #0'),('beq','#0x111eea2')])
    # The reply uses type3, not the ingress type1: follow its exact far veneer.
    expect(0x6102d42a,[('bl','#0x6107773e')])
    expect(0x6107773e,[('movw','ip, #0xf0bf'),('movt','ip, #0x111'),('bx','ip')])
    expect(0x0111f0be,[('mov','r2, r1'),('mov','r1, r0'),('movs','r0, #3'),('b','#0x111efc2')])
    expect(0x0111efc8,[('movs','r2, #4'),('movs','r3, #5'),
        ('orr.w','r2, r2, r0, lsl #4'),('orr.w','r3, r3, r0, lsl #4')])
    expect(0x0111efde,[('movs','r3, #6'),('orr.w','r3, r3, r0, lsl #4')])
    expect(0x0111efe8,[('movs','r3, #7'),('orr.w','r0, r3, r0, lsl #4')])
    expect(0x0111f042,[('bl','#0x111f4d8'),('movs','r0, #2'),('bl','#0x11020c0')])
    scatter=next(r for r in core.scatter() if r['destination']==0x2008008c)
    source=core.offset(scatter['source'])
    expanded,_=expand_initial_data(core.data[source:core.eram_offset],scatter['length'])
    initial=struct.unpack_from('<6I',expanded,0x2008203c-scatter['destination'])
    if initial != (0,0,512,512,0,0):
        raise ValueError('Software output initial state changed')
    return dict(payload_sha256=PAYLOAD_SHA256,
        shared=dict(base=0xe0043000,rx_words=0xe0043038,tx_words=0xe0043138,
                    physical_slots=64,usable_slots=63,tx_write_offset=0x24,tx_read_offset=0x28,
                    failed_attempt_offset=0x30,success_offset=0x34),
        software=dict(state=0x2008203c,data=0x20095f0c,physical_slots=512,usable_slots=511,
                      initial_words=initial,full_path_stores_word=False),
        output_task=dict(id=2,callback=0x0111ee68,callback_slot=0x20084960,
                         vector=vector,handler=0x0110213c,priority_argument=18,
                         priority_byte=priority_byte(18),**nvic_lines(irq)),
        retry_loops=loops,reply_word_type=3,reply_tail_call=0x0111f0be,
        external_peer_proven=False,execution_ready=False,
        limits=['Full-ring loops contain no wait or timeout; peer progress is unobserved.',
                'Enqueue/SEV/dequeue are not remote acknowledgements or DSP completion.',
                'No universal lossless/reentrant queue contract or memory-order guarantee is proved.',
                'Shared addresses and outbound word tags do not establish Linux frame conversion.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    args=parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(Core1(args.image)),indent=2))
    except (OSError,ValueError,StopIteration) as error:
        parser.exit(2,f'{error}\n')
