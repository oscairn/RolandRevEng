"""FDRV setter descriptors and bounded native coefficient-envelope reference."""
from contextlib import contextmanager
import hashlib
import math
import struct

from line_shaping_study import NATIVE_SHA256,_finite,_float32

TIMES_MS=tuple(range(1,11))+(12,14,16,18,20,24)
LEVEL_TABLE_SHA256='a4218b6632614d7d49d228d1b6e7db535bd3dadcb3b016fa97799fee6c87a9e4'


def imported_stub(data,address):
    if struct.unpack_from('<I',data)[0]!=0xfeedfacf:raise ValueError('Expected little-endian Mach-O64')
    offset=32;symtab=None;indirect=None;section=None
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        command,size=struct.unpack_from('<II',data,offset)
        if size<8 or offset+size>len(data):raise ValueError('Invalid load-command bounds')
        if command==2:symtab=struct.unpack_from('<4I',data,offset+8)
        if command==11:indirect=struct.unpack_from('<II',data,offset+56)
        if command==25:
            for n in range(struct.unpack_from('<I',data,offset+64)[0]):
                s=offset+72+80*n
                if s+80>offset+size:raise ValueError('Section outside segment command')
                base,length=struct.unpack_from('<QQ',data,s+32)
                if data[s:s+16].rstrip(b'\0')==b'__stubs'and base<=address<base+length:
                    first,stride=struct.unpack_from('<II',data,s+68)
                    if not stride or(address-base)%stride:raise ValueError('Unaligned stub')
                    section=first+(address-base)//stride
        offset+=size
    if symtab is None or indirect is None or section is None or section>=indirect[1]:raise ValueError('Missing stub metadata')
    index=struct.unpack_from('<I',data,indirect[0]+4*section)[0]
    if index>=symtab[1]:raise ValueError('Invalid indirect symbol index')
    name=struct.unpack_from('<I',data,symtab[0]+16*index)[0]
    if name>=symtab[3]:raise ValueError('Invalid symbol string index')
    return data[symtab[2]+name:symtab[2]+symtab[3]].split(b'\0',1)[0].decode('ascii')


def live_targets(method,args,level_table=None):
    """Setter arguments, not UI parameter numbers; no hardware update is sent."""
    if not isinstance(args,(list,tuple)):raise ValueError('Expected explicit setter arguments')
    counts={'drive':2,'wet':2,'level':1,'slope':2}
    if not isinstance(method,str)or method not in counts or len(args)!=counts[method]:
        raise ValueError('Unsupported setter/argument count')
    if method=='drive':
        db0,db1=map(_finite,args)
        if not all(-100<=v<=100 for v in (db0,db1)):raise ValueError('Outside checked finite dB domain')
        gain0,gain1=(math.pow(10.,v/20.)for v in (db0,db1))
        value=min(gain0*gain1,1.)
        denominator=math.fma(value,3.,math.fma(value*value,value,value*(abs(value)*-3.)))
        return {0:gain0,1:_finite(gain1/denominator)}
    if method=='wet':
        ratio,db=map(_finite,args)
        if not -100<=db<=100:raise ValueError('Outside checked finite dB domain')
        ratio=min(max(ratio,0.),1.)
        return {2:1.-ratio,3:ratio*math.pow(10.,db/20.)}
    if method=='slope':
        index,slope=args
        if type(index)is not int or index not in (0,1)or type(slope)is not int or slope not in (0,1):
            raise ValueError('Expected checked filter/slope indices 0 or 1')
        return {8+index:float(slope!=0)}
    level,=args
    if (type(level)is not int or not -(1<<31)<=level<(1<<31)
            or not isinstance(level_table,(list,tuple))or len(level_table)!=128):
        raise ValueError('Expected signed32-bit level and explicit 128-entry native level table')
    return {4:_finite(level_table[min(max(level,0),127)])}


def envelope_state(current,target,selector=10):
    if type(selector)is not int or not 0<=selector<16:raise ValueError('Expected EnvTC selector 0..15')
    current,target=map(_float32,(current,target))
    numerator=_float32(_float32(target-current)*1000.)
    increment=_float32(numerator/(TIMES_MS[selector]*44100.))
    control=(2<<28)|(2<<26)|(selector<<20)
    if increment:control=(control&0xf3ffffff)|0x84000000
    return (current,increment,control,target)


def envelope_step(state):
    current,increment,control,target=state
    if not increment:
        return (current,increment,control&0x33ffffff,target)
    if abs(_float32(target-current))<=abs(increment):
        return (target,increment,control&0x33ffffff,target)
    updated=_float32(current+increment)
    if updated==current:
        bits=struct.unpack('<I',struct.pack('<f',updated))[0]
        decrease_bits=(current<0)if increment>0 else(current>0)
        updated=struct.unpack('<f',struct.pack('<I',(bits+(-1 if decrease_bits else 1))&0xffffffff))[0]
    return (updated,increment,control,target)


def validate_events(events,frames,level_table):
    if not isinstance(events,list):raise ValueError('Expected an ordered list of setter events')
    previous=-1;result=[]
    for event in events:
        if not isinstance(event,dict)or set(event)!={'frame','method','args'}:raise ValueError('Invalid setter event')
        frame=event['frame']
        if type(frame)is not int or not previous<=frame<frames or frame<0:raise ValueError('Invalid event frame/order')
        result.append((frame,live_targets(event['method'],event['args'],level_table)));previous=frame
    return result


def report():
    import lib
    from coefficient_env_study import native_report
    from coefficient_shift_study import coefficient_context
    from line_prefix_study import descriptor
    from transfer_study import constructor_memory
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    native_report(lib.Z)
    if tuple(struct.unpack_from('<16d',lib.Z,0x839df0))!=TIMES_MS:raise ValueError('Native EnvTC table differs')
    if imported_stub(lib.Z,0x6d8c98)!='_pow':raise ValueError('dB2Gain import is not pow')
    _,ctor,_,_,_=coefficient_context('SIM_MFX_FDRV');memory=constructor_memory(ctor,lib.Z)
    md=lib.md();md.detail=True
    instructions={i.address:i for lo,hi in ((0xe7418,0xe79cc),(0x20a644,0x20a654),
        (0x3463d8,0x346518),(0x346870,0x3468f0))for i in md.disasm(lib.Z[lo:hi],lo)}
    live=[]
    for method,argument,call,symbol,slot in (
        ('drive',0xe7740,0xe7758,0x9e37c0,0),('drive',0xe7768,0xe778c,0x9e37e8,1),
        ('wet',0xe78f4,0xe7908,0x9e38d0,2),('wet',0xe791c,0xe7940,0x9e38f8,3),
        ('level',0xe79a8,0xe79c8,0x9e3920,4),
        ('input_filter',0xe7498,0xe74ac,0x9e3698,5),('input_filter',0xe74c0,0xe74d4,0x9e36c0,6),
        ('input_filter',0xe74e8,0xe74fc,0x9e36e8,7)):
        require_instructions(instructions,argument,(('adrp','x2, #0x9e3000'),('add',f'x2, x2, #{symbol-0x9e3000:#x}')))
        if instructions[call].mnemonic not in ('br','blr'):raise ValueError('Setter no longer dispatches')
        register=instructions[call].op_str
        require_instructions(instructions,argument-8,(('ldr','x8, [x0]'),('ldr',f'{register}, [x8, #0x160]')))
        path=[(instructions[pc].mnemonic,instructions[pc].op_str)for pc in range(argument+8,call,4)]
        if ('mov','w3, #0xa')not in path or ('mov','w4, #0')not in path:
            raise ValueError('Setter EnvTC/wait arguments differ')
        if lib.Z[symbol+16:symbol+20]!=bytes.fromhex('06000100'):
            raise ValueError('Expected the checked kind6 single-slot descriptor')
        if any(struct.unpack_from('<I',lib.Z,symbol+o)[0]!=slot for o in (0,4,12)):
            raise ValueError('FDRV live descriptor slot changed')
        live.append(dict(method=method,symbol=symbol,slot=slot,argument_pc=argument,call=call,
                         manager_slot=0x160,env_selector=10,wait=False))
    require_instructions(instructions,0xe75d4,(('adrp','x8, #0x9e3000'),('add','x8, x8, #0x350'),
        ('ldr','x2, [x8, w20, sxtw #3]')))
    require_instructions(instructions,0xe75f0,(('ldr','x8, [x0]'),('ldr','x5, [x8, #0x160]'),
        ('mov','w3, #0xa'),('mov','w4, #0')))
    for index in (0,1):
        symbol=struct.unpack_from('<Q',lib.Z,0x9e3350+8*index)[0]
        if lib.Z[symbol+16:symbol+20]!=bytes.fromhex('06000100')or struct.unpack_from('<I',lib.Z,symbol+12)[0]!=8+index:
            raise ValueError('Slope descriptor changed')
        live.append(dict(method='slope',index=index,symbol=symbol,slot=8+index,call=0xe760c,
                         manager_slot=0x160,env_selector=10,wait=False))
    groups=[]
    for name,symbol,field in (
        ('resample_a',0x9e3760,0x48),('resample_b',0x9e3780,0x58),('resample_c',0x9e37a0,0x68),
        ('cascade_a',0x9e3810,0x78),('cascade_b',0x9e3830,0x88),('cascade_c',0x9e3850,0x98),
        ('cascade_d',0x9e3870,0xa8),('cascade_e',0x9e3890,0xb8),('cascade_f',0x9e38b0,0xc8),
        ('output_a',0x9e3598,0xe8),('output_b',0x9e35b8,0x108),('output_d',0x9e35d8,0x118),
        ('output_c',0x9e35f8,0xf8),('output_e',0x9e3618,0xd8)):
        group=descriptor(lib.Z,symbol)
        representative=int.from_bytes(bytes(memory[field-8+i]for i in range(4)),'little')
        if group['records'][0]['relative_byte']!=representative or any(r['width']!=3 for r in group['records']):
            raise ValueError('FDRV literal representative changed')
        groups.append(dict(name=name,native_double_field=field,**group))
    literal_calls=[]
    for pc in (0xe7660,0xe767c,0xe7698,0xe77e8,0xe7808,0xe7824,0xe784c,0xe7868):
        require_instructions(instructions,pc,(('ldr','x8, [x8, #0xc8]'),))
    require_instructions(instructions,0xe77ec,(('cbz','w20, #0xe7834'),))
    require_instructions(instructions,0xe7830,(('b','#0xe7874'),))
    for argument,call,symbol in ((0xe7664,0xe766c,0x9e3760),(0xe7680,0xe7688,0x9e3780),
        (0xe769c,0xe76a4,0x9e37a0),(0xe7834,0xe783c,0x9e3810),(0xe7850,0xe7858,0x9e3830),
        (0xe786c,0xe7874,0x9e3850),(0xe77f0,0xe77f8,0x9e3870),(0xe780c,0xe7814,0x9e3890),
        (0xe7828,0xe7874,0x9e38b0)):
        require_instructions(instructions,argument,(('adrp','x1, #0x9e3000'),('add',f'x1, x1, #{symbol-0x9e3000:#x}')))
        require_instructions(instructions,call,(('blr','x8'),))
        literal_calls.append(dict(argument_pc=argument,call=call,symbol=symbol,manager_slot=0xc8))
    require_instructions(instructions,0x20a644,(('fmov','d1, #20.00000000'),('fdiv','d1, d0, d1'),
        ('fmov','d0, #10.00000000'),('b','#0x6d8c98')))
    require_instructions(instructions,0xe76e0,(('fmul','d1, d9, d0'),('fmov','d2, #1.00000000'),
        ('fmin','d1, d1, d2'),('fmul','d2, d1, d1'),('fabs','d3, d1'),('fmov','d4, #-3.00000000'),
        ('fmul','d3, d3, d4'),('fmul','d3, d1, d3'),('fmadd','d2, d2, d1, d3'),
        ('fmov','d3, #3.00000000'),('fmadd','d1, d1, d3, d2'),('fdiv','d8, d0, d1')))
    require_instructions(instructions,0x3463e8,(('fcmp','s0, #0.0'),('b.eq','#0x34644c'),
        ('fabd','s3, s2, s1'),('fabs','s4, s0'),('fcmp','s3, s4'),('b.le','#0x346448')))
    raw=lib.Z[0x818d20:0x819120]
    if hashlib.sha256(raw).hexdigest()!=LEVEL_TABLE_SHA256:raise ValueError('Level table changed')
    pieces=[]
    for index,table in enumerate((0x9e32a0,0x9e32d0)):
        symbols=struct.unpack_from('<5Q',lib.Z,table+8)
        slots=[struct.unpack_from('<I',lib.Z,s+12)[0]for s in symbols]
        if slots!=[10+5*index+v for v in (0,1,2,4,3)]:raise ValueError('State-filter live group changed')
        pieces.append(dict(index=index,piece=table,slots=slots,symbols=symbols))
    return dict(native_sha256=NATIVE_SHA256,live_setter_calls=live,literal_groups=groups,literal_setter_calls=literal_calls,
        state_filter_pieces=pieces,level_table_sha256=LEVEL_TABLE_SHA256,
        level_table_address=0x818d20,selector10_nominal_ms=12,native_rate_constant=44100,
        independently_replayed_setters=['drive','wet','level','slope'],
        filter_coefficient_generation_replayed=False,hardware_timing_verified=False,
        history_reset_performed_in_fixture=False,
        limitations=['Replay selects the with-envelope/no-wait branch explicitly; runtime dispatcher selection is not proved.',
            'EqFaCal/EqVgCal generation and UI parameter-index conversions are not replayed.',
            'One VProcSync call per fixture frame is an explicit test convention, not calibrated hardware cadence.',
            'SetAlg/history initialization and atomic literal-group application remain separate requirements.'])


@contextmanager
def native_envelope_functions():
    """Owned math buffers only; no manager/event/hardware state is accessed."""
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    report()
    ret=bytes.fromhex('c0035fd6')
    increment=(bytes.fromhex('e80300aa')+lib.Z[0x346870:0x346894]+bytes.fromhex('ea0301aa')+
               lib.Z[0x34689c:0x3468bc]+ret)
    step=lib.Z[0x3463d8:0x346518]
    with executable_mapping(increment)as a,executable_mapping(step)as b:
        yield (ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p)(a),
               ctypes.CFUNCTYPE(None,ctypes.c_void_p)(b))


def native_envelope_probes(cases,steps=1024):
    import ctypes
    if type(steps)is not int or not 1<=steps<=100000:raise ValueError('Invalid probe length')
    cases=[envelope_state(*case)for case in cases]
    times=(ctypes.c_double*16)(*TIMES_MS);compared=0
    with native_envelope_functions()as(increment,step):
        for initial in cases:
            record=ctypes.create_string_buffer(struct.pack('<ffIf',initial[0],0.,initial[2],initial[3]),16)
            owner=ctypes.create_string_buffer(0x48);struct.pack_into('<Q',owner,0x20,ctypes.addressof(record))
            increment(ctypes.addressof(record),ctypes.addressof(times))
            if bytes(record)!=struct.pack('<ffIf',*initial):raise ValueError('Native envelope increment differs')
            state=initial
            for _ in range(steps):
                state=envelope_step(state);step(ctypes.addressof(owner))
                if bytes(record)!=struct.pack('<ffIf',*state):raise ValueError('Native VProcSync differs')
                compared+=4
    return dict(compared_values=compared,hardware_execution_verified=False)


@contextmanager
def native_target_functions():
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    report();ret=bytes.fromhex('c0035fd6')
    drive=(lib.Z[0xe76b8:0xe76c8]+lib.Z[0xe76d4:0xe76d8]+lib.Z[0xe78b4:0xe78b8]+
        lib.Z[0xe76e0:0xe7710]+bytes.fromhex('0920006d')+lib.Z[0xe7780:0xe778c]+ret)
    wet=(lib.Z[0xe7888:0xe789c]+struct.pack('<I',0x1e604028)+lib.Z[0xe78a0:0xe78b4]+
        lib.Z[0xe78e8:0xe78ec]+struct.pack('<I',0xfd000000)+lib.Z[0xe7910:0xe7914]+
        struct.pack('<I',0xfd000400)+lib.Z[0xe7930:0xe7940]+ret)
    with executable_mapping(drive)as a,executable_mapping(wet)as b:
        signature=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_double,ctypes.c_double)
        yield signature(a),signature(b)


def native_live_targets(method,args,functions,level_table):
    import ctypes
    expected=live_targets(method,args,level_table)
    if method not in ('drive','wet'):return expected
    output=(ctypes.c_double*2)()
    if method=='drive':
        functions[0](ctypes.addressof(output),*(math.pow(10.,v/20.)for v in args))
    else:functions[1](ctypes.addressof(output),args[0],math.pow(10.,args[1]/20.))
    actual=dict(zip(expected,output,strict=True))
    if any(actual[k].hex()!=v.hex()for k,v in expected.items()):raise ValueError('Native setter arithmetic differs')
    return actual


def firmware_report(core):
    from core1_rtti import trace
    from dramio_owner_study import expect
    from effect_lifecycle_study import IMAGE_SHA256
    from kernel_abi import read
    from capstone.arm import ARM_OP_MEM,ARM_REG_PC
    if hashlib.sha256(core.data).hexdigest()!=IMAGE_SHA256:raise ValueError('Unsupported Fantom image')
    rtti=trace(core,'11CFspMfxFDRV')
    if len(rtti['candidates'])!=1:raise ValueError('Expected one FDRV RTTI chain')
    candidate=rtti['candidates'][0];callbacks=candidate['thumb_callback_candidates']
    if [callbacks[n]&~1 for n in (7,9,10)]!=[0x6104a036,0x6104a1b0,0x6104a2a2]:
        raise ValueError('FDRV setter callbacks differ')
    live=[]
    for method,pc,pool,slotload,call,slot in (
        ('drive',0x6104a0d2,0x6104a270,0x6104a0d4,0x6104a0da,0),
        ('drive',0x6104a0e8,0x6104a274,0x6104a0ea,0x6104a0f0,1),
        ('wet',0x6104a21c,0x6104a290,0x6104a21e,0x6104a224,2),
        ('wet',0x6104a232,0x6104a294,0x6104a234,0x6104a298,3),
        ('level',0x6104a2e8,0x6104a30c,0x6104a2e4,0x6104a2ea,4)):
        ins=next(core.md.disasm(read(core,pc,4),pc,count=1));operand=ins.operands[1]
        if (ins.mnemonic!='ldr'or operand.type!=ARM_OP_MEM or operand.mem.base!=ARM_REG_PC
                or ((pc+4)&~3)+operand.mem.disp!=pool):raise ValueError('Fantom setter literal load differs')
        symbol=core.u32(pool)
        if read(core,symbol+16,4)!=bytes.fromhex('06000100')or core.u32(symbol+12)!=slot:
            raise ValueError('Fantom FDRV kind6 slot differs')
        expect(core,slotload,'ldr.w',f'ip, [r{2 if method=="level"else 1}, #0xb0]')
        expect(core,call,'blx','ip')
        live.append(dict(method=method,slot=slot,symbol=symbol,argument_pc=pc,call=call,manager_slot=0xb0))
    expect(core,0x6104a23a,'b','#0x6104a298')
    expect(core,0x61049fac,'ldr.w','r4, [r1, #0xb0]');expect(core,0x61049fb4,'blx','r4')
    slope_table=core.u32(0x6104a260)
    for index in (0,1):
        symbol=core.u32(slope_table+4*index)
        if read(core,symbol+16,4)!=bytes.fromhex('06000100')or core.u32(symbol+12)!=8+index:
            raise ValueError('Fantom slope slot differs')
        live.append(dict(method='slope',index=index,slot=8+index,symbol=symbol,call=0x61049fb4,manager_slot=0xb0))
    expect(core,0x6104a07c,'vmul.f32','s1, s0, s16')
    expect(core,0x6104a0ac,'vmls.f32','s2, s4, s1');expect(core,0x6104a0b0,'vmla.f32','s2, s1, s3')
    expect(core,0x6104a0b4,'vdiv.f32','s17, s0, s2')
    expect(core,0x6104a218,'vsub.f32','s0, s0, s16');expect(core,0x6104a22a,'vmul.f32','s0, s16, s17')
    table=core.u32(0x6104a308);raw=read(core,table,512)
    import lib
    if tuple(struct.unpack('<128f',raw))!=tuple(map(_float32,struct.unpack_from('<128d',lib.Z,0x818d20))):
        raise ValueError('Fantom/native level tables disagree after binary32 conversion')
    return dict(payload_sha256=IMAGE_SHA256,live_setter_calls=live,level_table_address=table,
        level_table_sha256=hashlib.sha256(raw).hexdigest(),rtti=candidate,
        setter_arithmetic_precision='Observed binary32 VFP arithmetic; not assumed identical to native binary64/FMA targets',
        firmware_setters_executed=False,hardware_timing_verified=False)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--events',type=Path);parser.add_argument('--frames',type=int,default=12000)
    parser.add_argument('--core1',type=Path)
    args=parser.parse_args();result=report()
    if args.core1:
        from core1 import Core1
        result['firmware']=firmware_report(Core1(args.core1))
    if args.execute_native:
        result['native_envelopes']=native_envelope_probes([(0.,1.,10),(1.,0.,10),(-.2,.7,0)])
        with native_target_functions()as functions:
            result['native_target_checks']=[native_live_targets(m,a,functions,None)for m,a in
                [('drive',[-12.,-6.]),('drive',[12.,3.]),('wet',[-.2,-3.]),('wet',[.37,6.]),('wet',[1.2,0.])]]
        if args.events:
            from fdrv_filter_study import native_check
            events=json.loads(args.events.read_text())
            result['dynamic']=native_check(args.frames,compare_full=True,parameter_events=events)
            result['dynamic_fantom_scale']=native_check(args.frames,compare_full=True,parameter_events=events,
                resample_drive_literal='100000')
    elif args.events:parser.error('--events requires --execute-native')
    print(json.dumps(result,indent=2))
