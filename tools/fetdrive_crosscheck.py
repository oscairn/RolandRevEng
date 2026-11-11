"""Independent FETDRIVE mix/shaping cutpoints; no new DSP opcode admission."""
import hashlib
import math
import random
import struct

from line_shaping_study import NATIVE_SHA256,_finite,_float32


def shape(mixed,drive,scale,post):
    mixed,drive,scale,post=map(_finite,(mixed,drive,scale,post))
    value=_finite(_finite(_float32(drive)*scale)*mixed)
    if not -(2.**31)<=value<2.**31:raise ValueError('Outside checked fixed32 conversion domain')
    integer=(math.trunc(math.ldexp(value,32))<<9)&((1<<64)-1)
    if integer&(1<<63):integer-=1<<64
    clipped=min(1.,max(-1.,float(integer)*2.**-32))
    affine=math.fma(clipped,float.fromhex('0x1.555475a31a4bep-2'),float.fromhex('0x1.555714b9cb685p-2'))
    return _finite(post*(affine*affine))


def native_check(frames=2056):
    import ctypes
    import lib
    from coefficient_shift_study import coefficient_context
    from fetdrive_quantizer_study import native_report
    from line_state_study import advance_native_origin,native_ring_index
    from native_callback_fixture import RingFixture,executable_mapping
    from native_fetdrive_reference import CALLBACK,CONTEXT_SIZE
    from transfer_study import constructor_memory
    from weighted_mix_study import require_instructions
    if type(frames)is not int or not 128<=frames<=100000:raise ValueError('Expected 128..100000 frames')
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    checked=native_report()
    _,constructor,pointers,entry,code=coefficient_context('SIM_MFX_FETDRIVE')
    if (entry,code[-1].address+4)!=CALLBACK or pointers!={0x538+8*n:n for n in range(5)}:
        raise ValueError('FETDRIVE callback/layout changed')
    allowed={'add','and','fadd','fcmp','fcsel','fcvt','fcvtzs','fdiv','fmadd','fmin','fmov','fmsub',
        'fmul','fsub','ldp','ldr','lsl','mov','movk','scvtf','str','sub'}
    if (code[-1].mnemonic!='ret'or any(i.mnemonic not in allowed for i in code[:-1])):
        raise ValueError('Expected checked call-free callback')
    instructions={i.address:i for i in code}
    require_instructions(instructions,0x2f7e04,(('fmul','d3, d1, d2'),('fmadd','d2, d0, d2, d3'),
        ('ldr','d3, [x8, #0x68]'),('fmadd','d0, d0, d3, d2'),('fmadd','d1, d1, d3, d2')))
    image=bytearray(CONTEXT_SIZE)
    for offset,value in constructor_memory(constructor,lib.Z).items():
        if not 0<=offset<0x538:raise ValueError('Constructor overlaps live pointers')
        image[offset]=value
    context=ctypes.create_string_buffer(bytes(image),len(image));records=[]
    for offset,slot in pointers.items():
        record=ctypes.create_string_buffer(0x48);struct.pack_into('<f',record,0x28,(1.,.5,.5,.5,1.)[slot])
        records.append(record);struct.pack_into('<Q',context,offset,ctypes.addressof(record))
    fixture=RingFixture(context)
    left,right,outleft,outright=[ctypes.c_double()for _ in range(4)]
    inputs=(ctypes.c_void_p*2)(ctypes.addressof(left),ctypes.addressof(right))
    outputs=(ctypes.c_void_p*2)(ctypes.addressof(outleft),ctypes.addressof(outright))
    scale=checked['native_defaults']['scale'];encoded=checked['desktop_packets']['scale']
    rng=random.Random(4822);origin=0;different=0;nonzero_mix_cases=0
    with executable_mapping(lib.Z[CALLBACK[0]:CALLBACK[1]])as address:
        invoke=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p)(address)
        for frame in range(frames):
            alpha,beta=((0.,1.),(.25,.75),(-.125,.5))[frame%3]
            drive=(.61,-1.35,.999,1.,-.001,.3737)[frame%6];post=(1.,.5,.25)[frame%3]
            left.value,right.value=rng.uniform(-1.,1.),rng.uniform(-1.,1.)
            struct.pack_into('<d',context,0x48,alpha);struct.pack_into('<d',context,0x68,beta)
            struct.pack_into('<d',context,0x38,post);struct.pack_into('<f',records[1],0x28,drive)
            common=math.fma(left.value,alpha,right.value*alpha)
            mixed=[math.fma(sample,beta,common)for sample in (left.value,right.value)]
            struct.pack_into('<I',fixture.ring_context,0x20,origin)
            invoke(ctypes.addressof(fixture.wrapper),ctypes.addressof(inputs),ctypes.addressof(outputs))
            for channel,y in enumerate(mixed):
                for cell,want in ((1+channel,y),(3+channel,shape(y,drive,scale,post))):
                    if fixture.ring[native_ring_index(cell,0,origin)].hex()!=want.hex():
                        raise ValueError(f'FETDRIVE independent cutpoint differs at frame {frame}, cell {cell}')
                different+=shape(y,drive,scale,post).hex()!=shape(y,drive,encoded,post).hex()
            nonzero_mix_cases+=alpha!=0.
            origin=advance_native_origin(origin)
    return dict(native_sha256=NATIVE_SHA256,frames=frames,matching_native_values=4*frames,
        nonzero_mix_cases=nonzero_mix_cases,final_origin=origin,scale_precision_mismatches=different,
        quantizer_scale_gain=512,scaled_quantizer_grid=2.**-23,
        new_opcode_admission=False,whole_effect_packet_emulation=False,hardware_verified=False,
        limitations=['Nondefault native prefix constants are fixture substitutions; DSP prefix alias/writeback remains unresolved.',
            'Matching native constructor precision does not identify physical DSP literal precision.',
            'The full original callback executes, but only mixed and first shaped memory cutpoints are compared.'])


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frames',type=int,default=2056)
    args=parser.parse_args();print(json.dumps(native_check(args.frames),indent=2))
