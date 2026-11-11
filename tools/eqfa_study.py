"""Recovered three-coefficient EqFaCal math and an owned native oracle."""
from contextlib import contextmanager
import hashlib
import math
import struct

from line_shaping_study import NATIVE_SHA256,_finite

START,END=0x20ae90,0x20b494
CLAMP_FACTOR=float.fromhex('0x1.fae1480000000p-1')
PI=float.fromhex('0x1.921fb54442d18p+1')
TARGETS=(0x20aed0,0x20aeec,0x20af8c,0x20b030,0x20b0f4,0x20b194,0x20b2fc,0x20b248)
TYPE_NAMES=('bypass','zero','EqFcLowPassCal','EqFaLowShelvingCalNew','EqFaHighShelvingCalNew',
            'EqFaHighShelvingCalTrad','EqFaLowPassCal','EqFaHighPassCal','EqFaAllPassCal')


def checked_args(kind,cutoff,gain,rate):
    if type(kind)is not int or not 0<=kind<=8 or type(rate)is not int or not 0<rate<(1<<31):
        raise ValueError('Expected EqFa type0..8 and a positive signed32-bit sample rate')
    cutoff,gain=map(_finite,(cutoff,gain))
    if cutoff<0 or abs(gain)>96 or(kind>=2 and cutoff>=rate*.5*CLAMP_FACTOR):
        raise ValueError('Outside checked cutoff/gain domain; native assertion paths are excluded')
    return cutoff,gain


def coefficients(kind,cutoff,gain=0.,rate=44100):
    """Return native structure order: (a, feedback, delayed-input)."""
    cutoff,gain=checked_args(kind,cutoff,gain,rate)
    if kind==1:return (0.,0.,0.)
    if kind==0 or cutoff==0:return (1.,0.,0.)
    if kind==2:
        z=2.-math.cos((cutoff*(PI+PI))/rate)
        pole=z-math.sqrt(math.fma(z,z,-1.))
        return (1.-pole,pole,0.)
    t=math.tan((cutoff*PI)/rate);t=t+t
    if kind==3:
        if gain<0:
            g=math.pow(10.,gain/-20.);den=t*g+2.;a=(t+2.)/den;b=(2.-t*g)/den
        else:
            g=math.pow(10.,gain/20.);den=t+2.;a=(g*t+2.)/den;b=(2.-t)/den
        return (a,b,(a-1.)-b)
    if kind in (4,5):
        g=math.pow(10.,gain/20.)
        if (kind==4 and gain>=0)or(kind==5 and gain<0):first,second=t/g,t
        else:first,second=t,g*t
        den=second+2.;a=g*((first+2.)/den);b=(2.-second)/den
        return (a,b,(1.-a)-b)
    if kind==6:
        a=t/(t+2.);return (a,math.fma(a,-2.,1.),a)
    if kind==7:
        a=2./(t+2.);return (a,math.fma(a,2.,-1.),-a)
    b=(2.-t)/(t+2.);return (-b,b,1.)


def taps(kind,cutoff,gain=0.,rate=44100):
    a,feedback,delayed=coefficients(kind,cutoff,gain,rate)
    return (a,delayed,feedback)


def encoded_taps(values):
    from bmc_dsp import encode_literal,literal
    return tuple(literal(encode_literal(v,3))for v in values)


def validate_events(events,frames):
    if not isinstance(events,list):raise ValueError('Expected an ordered EqFa event list')
    previous=-1;result=[]
    for event in events:
        if not isinstance(event,dict)or set(event)!={'frame','stage','type','cutoff','gain'}:
            raise ValueError('Invalid EqFa event fields')
        frame=event['frame'];stage=event['stage']
        if (type(frame)is not int or not previous<=frame<frames or frame<0
                or not isinstance(stage,str)or stage not in ('input','resample','post0','post1')):
            raise ValueError('Invalid EqFa event order/stage')
        raw=taps(event['type'],event['cutoff'],event['gain'])
        if stage!='input':encoded_taps(raw)
        result.append((frame,stage,raw));previous=frame
    return result


def report():
    import lib
    from fdrv_parameter_study import imported_stub
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    md=lib.md();md.detail=True;code=list(md.disasm(lib.Z[START:END],START));by_pc={i.address:i for i in code}
    if [i.address for i in code]!=list(range(START,END,4)):raise ValueError('Incomplete EqFaCal body')
    raw=lib.Z[0x7c660c:0x7c661c]
    if tuple(0x20aed0+4*x for x in struct.unpack('<8H',raw))!=TARGETS:raise ValueError('EqFa dispatch changed')
    imports={target:imported_stub(lib.Z,target)for target in (0x6d8800,0x6d91a8,0x6d8c98)}
    if list(imports.values())!=['_cos','_tan','_pow']:raise ValueError('EqFa math imports changed')
    for kind,address in ((2,0x8e0fe0),(3,0x8e103d),(4,0x8e1053),(5,0x8e1025),
                         (6,0x8e0fef),(7,0x8e0ffe),(8,0x8e106a)):
        if not lib.Z[address:].startswith(TYPE_NAMES[kind].encode()+b'\0'):
            raise ValueError('EqFa assertion-linked type name changed')
    for ins in code:
        if ins.mnemonic=='bl'and ins.operands[0].imm not in {*imports,0xaa144}:
            raise ValueError('Unexpected EqFa call')
        if (ins.mnemonic=='b'or ins.mnemonic.startswith('b.'))and not START<=ins.operands[0].imm<END:
            raise ValueError('EqFa branch leaves the bounded function')
        if ins.mnemonic=='br'and(ins.address!=0x20aecc or ins.op_str!='x10'):
            raise ValueError('Unexpected indirect EqFa branch')
    require_instructions(by_pc,0x20aecc,(('br','x10'),))
    require_instructions(by_pc,0x20af68,(('fmov','d1, #2.00000000'),('fsub','d0, d1, d0'),
        ('fmov','d1, #-1.00000000'),('fmadd','d1, d0, d0, d1'),('fsqrt','d1, d1')))
    require_instructions(by_pc,0x20b378,(('fadd','d0, d0, d0'),('fmov','d1, #2.00000000'),
        ('fadd','d0, d0, d1'),('fdiv','d0, d1, d0'),('fneg','d2, d0')))
    setters={i.address:i for i in md.disasm(lib.Z[0xe7418:0xe7888],0xe7418)};bindings=[]
    for call,argument in ((0xe7460,0xe7450),(0xe763c,0xe7634),(0xe77d8,0xe77d0)):
        require_instructions(setters,argument,(('add','x1, sp, #8'),))
        require_instructions(setters,call,(('bl','#0x20ae90'),))
    for stage,loads in (('input',(0xe748c,0xe74b4,0xe74dc)),
        ('resample',(0xe7658,0xe7674,0xe7690)),('post0',(0xe77e0,0xe7844,0xe7860)),
        ('post1',(0xe77e0,0xe7800,0xe781c))):
        for index,pc in zip((0,2,1),loads,strict=True):
            require_instructions(setters,pc,(('ldr',f'd0, [sp, #{8+8*index:#x}]'),)
                if index else(('ldr','d0, [sp, #8]'),))
        bindings.append(dict(stage=stage,load_pcs=loads,structure_indices=[0,2,1]))
    return dict(native_sha256=NATIVE_SHA256,function=[START,END],dispatch_targets=TARGETS,type_names=TYPE_NAMES,
        dispatch_sha256=hashlib.sha256(raw).hexdigest(),imports=imports,
        default_rate=struct.unpack_from('<i',lib.Z,0xb78af0)[0],clamp_factor=CLAMP_FACTOR,
        structure_order=['a','feedback','delayed_input'],setter_order=['a','delayed_input','feedback'],
        setter_bindings=bindings,
        assertion_paths_executed=False,hardware_precision_verified=False)


def _adr(register,delta):
    if not -(1<<20)<=delta<(1<<20):raise ValueError('ADR displacement outside range')
    return struct.pack('<I',0x10000000|((delta&3)<<29)|(((delta>>2)&0x7ffff)<<5)|register)


@contextmanager
def native_function():
    """Clone only the audited math function; bind libm and explicit owned rate/output."""
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    checked=report();blob=bytearray(lib.Z[START:END]);blob.extend(bytes(-len(blob)%8))
    table=len(blob);blob.extend(lib.Z[0x7c660c:0x7c661c])
    system=ctypes.CDLL(None);stubs={}
    for target,symbol in checked['imports'].items():
        pointer=ctypes.cast(getattr(system,symbol[1:]),ctypes.c_void_p).value
        stubs[target]=len(blob);blob.extend(struct.pack('<IIQ',0x58000050,0xd61f0200,pointer))
    error=len(blob);blob.extend(struct.pack('<II',0xd4200000,0xd65f03c0))
    md=lib.md();md.detail=True
    for ins in md.disasm(lib.Z[START:END],START):
        offset=ins.address-START
        if ins.mnemonic=='bl':
            target=ins.operands[0].imm;destination=error if target==0xaa144 else stubs[target]
            blob[offset:offset+4]=struct.pack('<I',0x94000000|(((destination-offset)//4)&0x3ffffff))
        elif ins.mnemonic=='adrp'and ins.op_str=='x8, #0xb78000':
            # The original rate load reads the int32 supplied through x2 in this fixture.
            blob[offset:offset+8]=bytes.fromhex('e80302aa1f2003d5')
        elif ins.address==0x20aeb8:
            blob[offset:offset+8]=_adr(9,table-offset)+bytes.fromhex('1f2003d5')
    with executable_mapping(bytes(blob))as address:
        invoke=ctypes.CFUNCTYPE(None,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_double,ctypes.c_double)(address)
        def calculate(kind,cutoff,gain=0.,rate=44100):
            cutoff,gain=checked_args(kind,cutoff,gain,rate)
            output=(ctypes.c_double*3)();sample_rate=ctypes.c_int32(rate)
            invoke(kind,ctypes.addressof(output),ctypes.addressof(sample_rate),cutoff,gain)
            return tuple(output)
        yield calculate


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--events',type=Path);parser.add_argument('--frames',type=int,default=12000)
    parser.add_argument('--literal-policy',choices=('native','encoded'),default='native')
    args=parser.parse_args();result=report()
    if args.execute_native:
        count=0
        with native_function()as native:
            for rate in (44100,48000):
                for kind in range(9):
                    for cutoff in (0.,20.,100.,1000.,8000.,rate*.4):
                        for gain in (-12.,0.,9.):
                            actual=native(kind,cutoff,gain,rate);expected=coefficients(kind,cutoff,gain,rate)
                            if [v.hex()for v in actual]!=[v.hex()for v in expected]:
                                raise ValueError(f'EqFa mismatch {kind,cutoff,gain,rate}: {actual} != {expected}')
                            count+=3
        result['matching_native_coefficients']=count
        if args.events:
            from fdrv_filter_study import native_check
            result['dynamic']=native_check(args.frames,compare_full=True,
                filter_events=json.loads(args.events.read_text()),filter_literal_policy=args.literal_policy)
    elif args.events:parser.error('--events requires --execute-native')
    print(json.dumps(result,indent=2))
