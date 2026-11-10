"""Inspect coefficient-envelope selectors, completion and native-model limits offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

from core1_wait_study import IMAGE_SHA256
from parent_control_study import NATIVE_SHA256


def control_fields(word):
    """Decode the observed control fields and exact operating predicate; emits no command."""
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError('Expected one unsigned 32-bit control word')
    return dict(event_ref=word >> 28, mode_field=(word >> 26) & 3,
                wait_bit=(word >> 24) & 1, time_selector=(word >> 20) & 15,
                operating_predicate=(word & 0x0e000000) == 0x0c000000)


def firmware_report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')
    from dramio_owner_study import expect
    for address, mnemonic, operands in (
        (0x0113047e,'cmp','r0, #6'), (0x01130480,'ldr.w','ip, [sp, #8]'),
        (0x0113049c,'cmp','r1, r4'), (0x011304b0,'cmp','r2, #0x10'),
        (0x011304c4,'cmp.w','ip, #9'), (0x011304da,'usat','r2, #4, r2'),
        (0x011304de,'cbz','r3, #0x11304ea'),
        (0x011304e4,'bic','r5, r5, #2'), (0x011304e8,'str','r5, [r4, #8]'),
        (0x011304f0,'add.w','r0, r0, r1, lsl #4'),
        (0x011304f4,'lsl.w','r1, ip, #0x1c'),
        (0x011304f8,'orr.w','r1, r1, r3, lsl #24'),
        (0x011304fc,'orr.w','r1, r1, r2, lsl #20'),
        (0x01130500,'orr','r1, r1, #0x8000000'),
        (0x01130504,'str','r1, [r0, #8]'), (0x01130506,'vstr','s0, [r0, #0xc]'),
        (0x01130620,'ldr','r2, [r0, #8]'), (0x01130622,'tst','r2, r1'),
        (0x0113061e,'movs','r1, #2'),
        (0x01130624,'beq','#0x1130620'), (0x01130628,'bic.w','r1, r2, r1'),
        (0x0113062c,'str','r1, [r0, #8]'),
        (0x01130670,'and','r0, r0, #0xe000000'),
        (0x01130674,'cmp.w','r0, #0xc000000'),
        (0x01133958,'cmp','r0, #6'), (0x01133976,'bl','#0x1131968'),
        (0x01133980,'ldrb','r0, [r5, #3]'), (0x01133990,'strb','r0, [r5, #3]'),
        (0x0113398e,'movs','r0, #1'), (0x011339c0,'movs','r0, #0'),
        (0x01133992,'movs','r0, #2'), (0x01133994,'str','r0, [sp]'),
        (0x01133998,'add.w','r1, r7, r8'), (0x011339a0,'mov','r2, sb'),
        (0x011339a6,'bl','#0x113047c'), (0x011339aa,'cmp','r6, #0'),
        (0x011339bc,'bl','#0x113061c'), (0x011339c2,'strb','r0, [r5, #3]'),
        (0x011350ec,'ldr.w','ip, [r3, #0xb4]'), (0x011350f0,'movs','r3, #0'),
        (0x01135104,'cbz','r1, #0x1135116'),
        (0x01135106,'ldr.w','ip, [r2, #0xc4]'),
        (0x0113511a,'ldr.w','ip, [r2, #0xbc]')):
        expect(core,address,mnemonic,operands)
    bases=[core.u32(0x0113aa90+4*dsp) for dsp in range(6)]
    capacities=[core.u32(0x0113aaa8+4*dsp) for dsp in range(6)]
    if bases != [0x414a0000+dsp*0x100000 for dsp in range(6)] or capacities != [2048,2048,1024,1024,1024,1024]:
        raise ValueError('Live coefficient bank table changed')
    slots={offset:core.u32(0x6117647c+offset) & ~1 for offset in (0xb0,0xb4,0xbc,0xc4)}
    if list(slots.values()) != [0x011350de,0x011350f8,0x0113391e,0x011339ce]:
        raise ValueError('Envelope dispatch chain changed')
    if (core.u32(0x0112f82c) != 0x0112f439 or core.u32(0x01133c7c) != 0x2008480c
            or any(core.u32(a) != 0x200847f0 for a in (0x01130594,0x011309ac,0x0112f828))):
        raise ValueError('Completion/manager state anchors changed')
    expect(core,0x0112f43a,'ldr','r1, [r0, #8]')
    expect(core,0x0112f43c,'orr','r1, r1, #2')
    expect(core,0x0112f440,'str','r1, [r0, #8]')
    interrupts=[]
    for dsp in range(6):
        site=0x0112f466+8*dsp
        event=8+dsp
        immediate=str(event) if event<10 else hex(event)
        expect(core,site+2,'movs',f'r0, #{immediate}')
        expect(core,site+4,'bl','#0x113191e')
        vector=0x01100144+4*dsp;handler=core.u32(vector) & ~1
        if handler != 0x01131342+0x30*dsp:
            raise ValueError('Envelope vector changed')
        expect(core,handler+4,'ldr.w',f'r0, [r4, #{0x320+4*dsp:#x}]')
        expect(core,handler+10,'str.w',f'r1, [r4, #{0x320+4*dsp:#x}]')
        expect(core,handler+0x22,'it','ne')
        expect(core,handler+0x24,'blx','r1')
        interrupts.append(dict(dsp=dsp,event=8+dsp,irq=(vector-0x01100000)//4-16,
                               vector=vector,handler=handler,status=0x41100320+4*dsp,
                               callback_slot=0x200a18a4+4*(8+dsp)))
    return dict(payload_sha256=IMAGE_SHA256,bases=bases,capacities=capacities,
                driver=0x0113047c,manager=0x0113391e,dispatch_slots=slots,
                manager_symbol_kind=6,selector_count=16,manager_event_ref=2,
                completion_flags=0x200847f8,completion_bit=1,exclusion_byte=0x2008480f,
                interrupts=interrupts,hardware_timing_verified=False,
                owner_offset_bounds_proven=False,execution_ready=False)


def native_report(data):
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native payload digest')
    import capstone
    md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    def check(address,rows):
        actual=list(md.disasm(data[address:address+4*len(rows)],address))
        if [(i.mnemonic,i.op_str) for i in actual] != rows:
            raise ValueError(f'Native envelope mismatch at {address:#x}')
    check(0x3460cc,[('lsl','w8, w2, #0x1a'),('orr','w8, w8, w1, lsl #28'),
        ('orr','w8, w8, w3, lsl #24'),('orr','w8, w8, w4, lsl #20')])
    check(0x16c4d8,[('and','w4, w22, #0xff'),('add','x0, sp, #8'),('mov','w1, #2'),
        ('mov','w2, #2'),('mov','x3, x21'),('bl','#0x3460cc')])
    check(0x16c508,[('ldr','d0, [sp, #8]'),('fcvtzu','w9, d0'),
        ('add','x10, x21, w20, uxtw #3'),('lsl','x20, x10, #3'),
        ('add','x8, x8, x20'),('ldr','x8, [x8, #0x20]'),('str','w9, [x8, #8]')])
    check(0x16c52c,[('fcvt','s0, d8'),('mov','w1, #-1'),('bl','#0x346734')])
    check(0x3467b8,[('ldr','w9, [x8, #8]'),('ubfx','w9, w9, #0x1a, #2'),
        ('adrp','x10, #0x839000'),('add','x10, x10, #0xde4'),
        ('adr','x11, #0x3467b4'),('ldrb','w12, [x10, x9]'),
        ('add','x11, x11, x12, lsl #2'),('br','x11')])
    table=data[0x839de4:0x839de8]
    if len(table) != 4 or 0x3467b4+4*table[2] != 0x346870:
        raise ValueError('Native SetBP mode2 dispatch changed')
    check(0x346870,[('ldr','s0, [x8, #0xc]'),('ldr','s1, [x8]'),('fsub','s0, s0, s1'),
        ('mov','w9, #0x447a0000'),('fmov','s1, w9'),('fmul','s0, s0, s1'),
        ('fcvt','d0, s0'),('ldr','w9, [x8, #8]'),('ubfx','x9, x9, #0x14, #4'),
        ('adrp','x10, #0x839000'),('add','x10, x10, #0xdf0'),
        ('ldr','d1, [x10, x9, lsl #3]'),('mov','x9, #0x888000000000'),
        ('movk','x9, #0x40e5, lsl #48'),('fmov','d2, x9'),
        ('fmul','d1, d1, d2'),('fdiv','d0, d0, d1'),('fcvt','s0, d0'),('str','s0, [x8, #4]')])
    check(0xfcee0,[('mov','w0, #0'),('ldp','x29, x30, [sp], #0x10'),('ret','')])
    raw=data[0x839df0:0x839e70]
    if hashlib.sha256(raw).hexdigest() != '7921c8fef9a5176a795ac75f81271637a0407bb5eab8bdb5a5a67cbd27d758b5':
        raise ValueError('Native time selector table changed')
    times=struct.unpack('<16d',raw)
    return dict(native_sha256=NATIVE_SHA256,time_selector_count=len(times),
                selector10_nominal_ms=times[10],table_sha256=hashlib.sha256(raw).hexdigest(),
                native_rate_constant=44100.0,native_manager_operating_returns_false=True,
                hardware_timing_verified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core1',type=Path)
    parser.add_argument('--native',type=Path,default=Path(os.environ.get('BMC_CORPUS_DIR',Path(__file__).resolve().parents[1]/'local'))/'zen_arm64')
    args=parser.parse_args()
    from core1 import Core1
    print(json.dumps(dict(firmware=firmware_report(Core1(args.core1)),
                         native=native_report(args.native.read_bytes())),indent=2))
