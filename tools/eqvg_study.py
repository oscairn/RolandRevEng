"""Recovered EqVg generation and the stock four-argument interpolation predicate."""
from contextlib import contextmanager
from functools import cache
import hashlib
import math
import struct

from eqfa_study import PI,CLAMP_FACTOR,_adr
from line_shaping_study import NATIVE_SHA256,_finite

BEGIN,START,END=0x20cee8,0x20d8f4,0x20defc
TARGETS=(0x20d940,0x20da60,0x20da88,0x20decc,0x20dab0,0x20ddc8,0x20dbb8,0x20dcac)
TYPE_NAMES={0:'bypass',9:'EqVgPeakingCal',10:'EqVgLowShelvingCalNew',
    11:'EqVgHighShelvingCalNew',12:'bypass',13:'EqVgLowPassCal',
    14:'EqVgHighPassCal',15:'EqVgAllPassCal',16:'EqVgBandPassCal'}


@cache
def _combined_sincos():
    import sys
    if sys.platform!='darwin':return None
    import ctypes
    class Pair(ctypes.Structure):
        _fields_=[('sin',ctypes.c_double),('cos',ctypes.c_double)]
    function=ctypes.CDLL(None).__sincos_stret
    function.argtypes=[ctypes.c_double];function.restype=Pair
    return function


def _sincos(angle):
    # Separate Darwin sin/cos calls can differ by one ULP from the imported combined function.
    function=_combined_sincos()
    if function is None:return math.sin(angle),math.cos(angle)
    pair=function(angle);return pair.sin,pair.cos


def checked_args(kind,cutoff,gain,q,rate):
    if type(kind)is not int or kind not in TYPE_NAMES or type(rate)is not int or not 0<rate<(1<<31):
        raise ValueError('Expected EqVg type0/9..16 and a positive signed32-bit rate')
    cutoff,gain,q=map(_finite,(cutoff,gain,q))
    if (cutoff<0 or(cutoff and cutoff/rate<float.fromhex('0x1p-1022'))or abs(gain)>96
            or(kind not in (0,12)and cutoff>=rate*.5*CLAMP_FACTOR)):
        raise ValueError('Outside checked EqVg domain; native assertion paths are excluded')
    return cutoff,gain,min(max(q,.25),128.)


def coefficients(kind,cutoff,gain=0.,q=1.,rate=44100):
    """Native structure order (g,b,c,d,e); g is not the stored g-1 coefficient."""
    cutoff,gain,q=checked_args(kind,cutoff,gain,q,rate)
    if kind in (0,12)or cutoff==0:return (1.,-1.,1.,0.,0.)
    if kind in (10,11):
        t=math.tan((cutoff*PI)/rate);t=t+t
        if kind==10 and gain<0:t=math.sqrt(math.pow(10.,gain/-20.))*t
        linear=math.pow(10.,gain/20.)
        v=t*(math.sqrt(linear)if kind==11 and gain<0 else 1.)
        twice=v+v;root=math.sqrt(math.fma(v,v,twice/q+4.))
        g=twice/root;b=-2./(q*root)
        d=math.fma(g*-.25,g,math.fma(g*.5,b,1.));half=b*-.5
        if kind==10:return (g,b,linear,(1.-linear)*d,(math.sqrt(linear)-linear)*half)
        return (g,b,1.,(linear-1.)*d,(math.sqrt(linear)-1.)*half)
    angle=(cutoff/rate)*PI;s,c=_sincos(angle)
    linear=math.pow(10.,gain/20.)if kind in (9,16)else 1.
    if kind in (9,15,16):
        if kind==9:q=(linear if gain<0 else 1.)*q
        factor=((q*angle)*c)/s
        root=math.sqrt((s*c)/factor+1.)
        g=(s+s)/root;b=-c/(factor*root)
        if kind==9:return (g,b,1.,0.,((linear-1.)*b)*-.5)
        if kind==15:return (g,b,1.,0.,(b+b)*.5)
        return (g,b,0.,0.,(linear*b)*-.5)
    root=math.sqrt((s*c)/q+1.);g=(s+s)/root;b=-c/(q*root)
    d=math.fma(g*-.25,g,math.fma(g*.5,b,1.))
    if kind==13:return (g,b,1.,-d,b*.5)
    return (g,b,0.,d,0.)


def stored_coefficients(values,subtract_one=True):
    if not isinstance(values,(list,tuple))or len(values)!=5 or type(subtract_one)is not bool:
        raise ValueError('Expected five EqVg coefficients and an explicit offset flag')
    g,b,c,d,e=map(_finite,values)
    return (g-1. if subtract_one else g,b,c,d,e)


def live_coefficients(values):
    a,b,c,d,e=stored_coefficients(values)
    return (a,b,c,e,d)


def output_coefficients(values):
    a,b,c,d,e=stored_coefficients(values)
    return (a,b,d,c,e)


def validate_events(events,frames):
    from eqfa_study import encoded_taps
    if not isinstance(events,list):raise ValueError('Expected an ordered EqVg event list')
    result=[];previous=-1
    for event in events:
        if not isinstance(event,dict)or set(event)!={'frame','stage','type','cutoff','gain','q'}:
            raise ValueError('Invalid EqVg event fields')
        frame=event['frame'];stage=event['stage']
        if type(frame)is not int or not previous<=frame<frames or frame<0 or stage not in ('live0','live1','output'):
            raise ValueError('Invalid EqVg event frame/order/stage')
        raw=coefficients(event['type'],event['cutoff'],event['gain'],event['q'])
        if stage=='output':encoded_taps(output_coefficients(raw))
        result.append((frame,stage,raw));previous=frame
    return result


def interpolation_stable(old_g,old_b,new_g,new_b):
    """The stock path predicate; it assumes valid endpoints, not arbitrary stable filters."""
    g0,b0,g1,b1=(abs(_finite(v))for v in (old_g,old_b,new_g,new_b))
    delta=g1-g0
    if delta==0 or b0-b1==0:return True
    slope=(b0-b1)/delta;den=math.fma(slope,2.,-1.)
    if den==0:return True
    vertex=math.fma(slope,g0,b0)/den
    if (vertex-g0)*(vertex-g1)>=0:return True
    numerator=-math.fma(slope,g0,b0)
    return 4.-(numerator*numerator)/den>0


def update_plan(current,target,*,envelope=True,subtract_one=True):
    """Ordered stock EqVGenv writes, with manager slots and wait flags retained."""
    if type(envelope)is not bool or type(subtract_one)is not bool:
        raise ValueError('Expected explicit envelope/offset booleans')
    if not isinstance(current,(list,tuple))or len(current)!=2:
        raise ValueError('Expected current stored a/b values')
    a0,b0=map(_finite,current);g,b,c,d,e=map(_finite,stored_coefficients(target,False))
    safe=interpolation_stable(a0+(1. if subtract_one else 0.),b0,g,b)if envelope else True
    order=(1,0,2,4,3)if abs(b)<abs(b0)else(0,1,2,4,3)
    values=stored_coefficients((g,b,c,d,e),subtract_one)
    return [dict(coefficient=i,value=values[i],manager_slot=0x178 if envelope else 0x188,
        time_selector=10 if envelope else None,wait=envelope and not safe and n==0)
        for n,i in enumerate(order)]


def report():
    import lib
    from fdrv_parameter_study import imported_stub
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    md=lib.md();md.detail=True;code=list(md.disasm(lib.Z[BEGIN:END],BEGIN))
    if [i.address for i in code]!=list(range(BEGIN,END,4)):raise ValueError('Incomplete EqVg body')
    if tuple(0x20d940+4*v for v in struct.unpack_from('<8H',lib.Z,0x7c663c))!=TARGETS:
        raise ValueError('EqVg dispatch changed')
    imports={a:imported_stub(lib.Z,a)for a in (0x6d86f8,0x6d8c98,0x6d91a8)}
    if tuple(imports.values())!=('___sincos_stret','_pow','_tan'):raise ValueError('EqVg imports changed')
    for ins in code:
        if ins.mnemonic=='bl'and ins.operands[0].imm not in {*imports,0xaa144}:
            raise ValueError('Unexpected EqVg external call')
        if (ins.mnemonic=='b'or ins.mnemonic.startswith('b.'))and not BEGIN<=ins.operands[0].imm<END:
            raise ValueError('EqVg branch leaves checked region')
        if ins.mnemonic=='br'and(ins.address!=0x20d93c or ins.op_str!='x10'):
            raise ValueError('Unexpected EqVg indirect branch')
    if struct.unpack_from('<2d',lib.Z,0x7220f0)!=(1.,-1.)or struct.unpack_from('<2d',lib.Z,0x7c6650)!=(1.,0.):
        raise ValueError('EqVg constant vectors changed')
    for kind,pc in ((9,0x8e11ab),(10,0x8e11e0),(11,0x8e11c9),(13,0x8e117c),
        (14,0x8e118b),(15,0x8e11ba),(16,0x8e119b)):
        if not lib.Z[pc:].startswith(TYPE_NAMES[kind].encode()+b'\0'):raise ValueError('EqVg type name changed')
    leaf={i.address:i for i in md.disasm(lib.Z[END:0x20df8c],END)}
    require_instructions(leaf,0x20df28,(('fdiv','d3, d3, d4'),('fmov','d4, #-1.00000000'),
        ('fmov','d5, #2.00000000'),('fmadd','d4, d3, d5, d4')))
    for i in leaf.values():
        if i.mnemonic in ('bl','blr','br','adrp')or(i.mnemonic.startswith('b.')and not END<=i.operands[0].imm<0x20df8c):
            raise ValueError('Unexpected interpolation dependency')
    descriptors=[]
    for base,slots in ((0x9e32a0,(10,11,12,14,13)),(0x9e32d0,(15,16,17,19,18))):
        if lib.Z[base]!=1:raise ValueError('EqVg g-1 flag changed')
        pointers=struct.unpack_from('<5Q',lib.Z,base+8)
        if tuple(struct.unpack_from('<I',lib.Z,p+12)[0]for p in pointers)!=slots:
            raise ValueError('EqVg raw-to-live coefficient ordering changed')
        descriptors.append(dict(address=base,descriptor_order_slots=slots))
    if lib.Z[0x9e3300]!=1 or struct.unpack_from('<5Q',lib.Z,0x9e3308)!=(0x9e3598,0x9e35b8,0x9e35d8,0x9e35f8,0x9e3618):
        raise ValueError('Output EqVg descriptor changed')
    return dict(native_sha256=NATIVE_SHA256,function=[START,END],owned_math_region=[BEGIN,END],
        type_names=TYPE_NAMES,dispatch_targets=TARGETS,imports=imports,q_clamp=[.25,128.],
        structure_order=['g','b','c','d','e'],interpolation_function=[END,0x20df8c],
        live_descriptors=descriptors,live_model_order=['g-1','b','c','e','d'],
        output_model_order=['g-1','b','d','c','e'],
        sincos_policy='Darwin combined host libm; separate math.sin/cos fallback elsewhere is not bit-calibrated',
        hardware_precision_verified=False,endpoint_stability_checked_by_predicate=False)


@contextmanager
def native_function(rate=44100):
    """Execute only pinned original math, copied constant data and host libm."""
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    checked_args(0,0,0,1,rate);checked=report();blob=bytearray(lib.Z[BEGIN:END])
    blob.extend(bytes(-len(blob)%16));pages={}
    for page in (0x722000,0x7c6000):
        pages[page]=len(blob);blob.extend(lib.Z[page:page+4096])
    rate_offset=len(blob);blob.extend(struct.pack('<i',rate));blob.extend(bytes(-len(blob)%8))
    system=ctypes.CDLL(None);stubs={}
    for target,symbol in checked['imports'].items():
        pointer=ctypes.cast(getattr(system,symbol[1:]),ctypes.c_void_p).value
        stubs[target]=len(blob);blob.extend(struct.pack('<IIQ',0x58000050,0xd61f0200,pointer))
    error=len(blob);blob.extend(struct.pack('<II',0xd4200000,0xd65f03c0))
    md=lib.md();md.detail=True
    for ins in md.disasm(lib.Z[BEGIN:END],BEGIN):
        offset=ins.address-BEGIN
        if ins.mnemonic=='bl':
            target=ins.operands[0].imm;destination=error if target==0xaa144 else stubs[target]
            blob[offset:offset+4]=struct.pack('<I',0x94000000|(((destination-offset)//4)&0x3ffffff))
        elif ins.mnemonic=='adrp':
            register=ins.operands[0].reg;number=int(ins.reg_name(register)[1:]);page=ins.operands[1].imm
            if page in pages:blob[offset:offset+4]=_adr(number,pages[page]-offset)
            elif page==0xb78000:
                blob[offset:offset+8]=_adr(number,rate_offset-offset)+bytes.fromhex('1f2003d5')
            elif page not in (0x8e1000,0x8b2000):raise ValueError('Unexpected EqVg global access')
    with executable_mapping(bytes(blob))as address:
        invoke=ctypes.CFUNCTYPE(None,ctypes.c_int,ctypes.c_void_p,ctypes.c_double,
            ctypes.c_double,ctypes.c_double)(address+START-BEGIN)
        def calculate(kind,cutoff,gain=0.,q=1.):
            checked_args(kind,cutoff,gain,q,rate)
            output=(ctypes.c_double*5)();invoke(kind,ctypes.addressof(output),cutoff,gain,q)
            return tuple(output)
        calculate.address=address+START-BEGIN
        yield calculate


@contextmanager
def native_interpolation_function():
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    report()
    with executable_mapping(lib.Z[END:0x20df8c])as address:
        invoke=ctypes.CFUNCTYPE(ctypes.c_bool,*([ctypes.c_double]*4))(address)
        def calculate(*args):
            if len(args)!=4:raise ValueError('Expected four interpolation arguments')
            return invoke(*map(_finite,args))
        calculate.address=address
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
        for rate in (44100,48000):
            with native_function(rate)as native:
                for kind in TYPE_NAMES:
                    for cutoff in (0.,20.,1000.,rate*.4):
                        for gain in (-12.,0.,9.):
                            for q in (.1,.25,1.,128.,256.):
                                actual=native(kind,cutoff,gain,q);expected=coefficients(kind,cutoff,gain,q,rate)
                                if [v.hex()for v in actual]!=[v.hex()for v in expected]:
                                    raise ValueError(f'EqVg mismatch {kind,cutoff,gain,q,rate}: {actual} != {expected}')
                                count+=5
        result['matching_native_coefficients']=count
        if args.events:
            from fdrv_filter_study import native_check
            result['dynamic']=native_check(args.frames,compare_full=True,
                vg_events=json.loads(args.events.read_text()),filter_literal_policy=args.literal_policy)
    elif args.events:parser.error('--events requires --execute-native')
    print(json.dumps(result,indent=2))
