"""FDRV three-tap resampling/drive through clipping and cubic shaping, offline only."""
import hashlib
import math
import struct

from bmc_subset import assemble_fragment
from line_shaping_study import NATIVE_SHA256, _finite, _float32

# Native constructor policy; the encoded 24-bit literal is slightly smaller.
DRIVE_SCALE=float.fromhex('0x1.95b489f0954cbp-6')
DRIVE_SCALES={'0656d2':DRIVE_SCALE,'100000':.0625}


def resample_spec(data_base=0,coefficient_base=0,taps=(1.,0.,0.),drive_literal='0656d2'):
    return dict(kind='resample_drive_pair',sources=[data_base+x for x in (0,1,2,3,4,5,0x15)],
                output_addresses=[data_base+0x62,data_base+0x63],
                coefficient_slots=[coefficient_base],tap_coefficients=list(taps),drive_literal=drive_literal)


def program_specs(taps=(1.,0.,0.),drive_literal='0656d2'):
    from fdrv_filterbank_study import program_specs as filters
    from fdrv_clip_study import clip_spec
    from fdrv_cubic_study import cubic_spec
    clip=clip_spec();clip['sources']=[0x62,0x63,0x15,0x17]
    return filters()+[resample_spec(taps=taps,drive_literal=drive_literal),clip,cubic_spec()]


def resample_reference(current,history1,history2,taps,drive,drive_literal='0656d2'):
    current,history1,history2=map(_finite,(current,history1,history2))
    a,b,c=map(_finite,taps);drive=_float32(drive)
    if not hasattr(math,'fma'):
        raise ValueError('Native resampling policy requires Python 3.13+ math.fma')
    if not isinstance(drive_literal,str) or drive_literal not in DRIVE_SCALES:
        raise ValueError('Expected a checked drive literal')
    try:
        mixed=_finite(math.fma(history2,c,_finite(math.fma(history1,b,_finite(current*a)))))
        return dict(history=mixed,output=_finite(_finite(mixed*DRIVE_SCALES[drive_literal])*drive))
    except OverflowError as error:
        raise ValueError('Resampling exceeds finite native-reference arithmetic') from error


def report():
    import lib
    from condition_return_study import preserved
    from fdrv_filterbank_study import report as filter_report
    from fdrv_clip_study import report as clip_report
    from fdrv_cubic_study import report as cubic_report
    from limit_control_study import checked_access,native_context
    from line_mix_variation import packet_literals
    from bmc_dsp import packets
    from weighted_mix_study import check_constructor_literal,require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    filter_report();clip_report();cubic_report()
    p,n,m,f,t=native_context('SIM_MFX_FDRV')
    if assemble_fragment(resample_spec())[10:112]!=p[0x2d6:0x33c]:
        raise ValueError('Resample/drive stock body differs')
    for pc,shape in (
            (0x3058a4,(('fmul','d1, d1, d5'),)),(0x3058b8,(('fmul','d0, d0, d4'),)),
            (0x3058c0,(('fmadd','d1, d2, d4, d1'),)),
            (0x3058d4,(('fmadd','d0, d3, d4, d0'),)),
            (0x3058dc,(('fmadd','d1, d5, d3, d1'),('fmadd','d0, d2, d3, d0'))),
            (0x305908,(('ldr','s2, [x13, #0x28]'),('fcvt','d2, s2'),
                       ('ldr','d3, [x8, #0x28]'),('fmul','d1, d1, d3'),
                       ('fmul','d0, d0, d3'),('fmul','d1, d1, d2'),('fmul','d0, d0, d2')))):
        require_instructions(n,pc,shape)
    rows=dict(packets(p));literals=[]
    for offset,pcs in ((0x2d6,(0x305864,0x305890)),(0x2f2,(0x3058bc,)),
                       (0x30a,(0x3058d8,)),(0x31a,(0x305910,))):
        fields=packet_literals(p,offset,rows[offset])
        if [field['value'] for field in fields[:1]]!=[fields[-1]['value']]:
            raise ValueError('Resample stereo literal fields differ')
        for pc in pcs:
            # The right channel reuses the left literal's constructor record.
            field=fields[0]
            check_constructor_literal(p,m,n[pc],field)
            literals.append(dict(native_pc=pc,wire_fields=[item['field'] for item in fields],**field))
    if struct.unpack('<d',bytes(m[i] for i in range(0x28,0x30)))[0].hex()!=DRIVE_SCALE.hex():
        raise ValueError('Native fixed drive scale differs')
    bindings=[]
    for pc,kind,field,cell in (
            (0x305860,'read',0x2e4,1),(0x305878,'write',0x2e6,0),
            (0x30588c,'read',0x2e8,4),(0x3058a0,'write',0x2ea,3),
            (0x3058b4,'read',0x300,2),(0x3058d0,'read',0x302,5),
            (0x3058f0,'write',0x2e4,1),(0x305900,'write',0x2e8,4),
            (0x305930,'read',0x33a,0x15)):
        bindings.append(checked_access(n,f,t,pc,kind,field,cell))
    if dict(pc=0x305908,slot=0,width=4) not in t['coefficient_reads']:
        raise ValueError('Live drive coefficient binding differs')
    preserved([n[pc] for pc in range(0x3058a8,0x3058c0,4)],'d1')
    preserved([n[pc] for pc in range(0x3058bc,0x3058d4,4)],'d0')
    cells=[0,1,3,4,0x14,0x16,0xe,0x10,0xf,0x11,0x12,0x18,0x13,0x1a]
    for cell in cells:
        writes=[row for row in t['accesses'] if row['kind']=='write'
                and any(f[key]['address']==cell for key in row['fields'])]
        if len(writes)!=1 or writes[0]['pc']>=0x305af4:
            raise ValueError('Native resampling/shaping cutpoint is ambiguous or overwritten')
    sizes=[len(assemble_fragment(spec)) for spec in program_specs()]
    return dict(native_sha256=NATIVE_SHA256,stock_body=[0x2d6,0x33c],stock_bytes=102,
                profile_bytes=122,fragment_sizes=sizes,combined_bytes=sum(sizes),
                bindings=bindings,literals=literals,synthetic_bridge_cells=[0x60,0x61,0x62,0x63],
                native_drive_scale_hex=DRIVE_SCALE.hex(),
                encoded_drive_scale=packet_literals(p,0x31a,rows[0x31a])[0]['value'],
                compared_cutpoint_end=0x305af4,full_effect_executable=False,
                hardware_execution_verified=False)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--frames',type=int,default=12000)
    args=parser.parse_args();result=report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['native_check']=native_check(args.frames,compare_resample=True)
        result['fantom_literal_check']=native_check(args.frames,compare_resample=True,resample_drive_literal='100000')
    print(json.dumps(result,indent=2,allow_nan=False))
