"""Exact FDRV post-cubic history mix and gain; native-policy offline evidence."""
import hashlib
import math
import struct

from bmc_subset import assemble_fragment
from line_shaping_study import NATIVE_SHA256,_finite,_float32

POST_SCALES={'628624':float.fromhex('0x1.43126e978d4fep+5'),'500000':16.}
DRIVE_TO_POST={'0656d2':'628624','100000':'500000'}


def post_mix_spec(data_base=0,coefficient_base=0,post_scale_literal='628624'):
    return dict(kind='post_cubic_mix_pair',
                sources=[data_base+x for x in (0x12,0x18,0x19,0x13,0x1a,0x1b)],
                targets=[data_base+0x1c,data_base+0x1d],
                output_addresses=[data_base+6,data_base+0xa],
                coefficient_slots=[coefficient_base+1],post_scale_literal=post_scale_literal)


def program_specs(taps=(1.,0.,0.),drive_literal='0656d2'):
    from fdrv_resample_study import program_specs as shaped
    return shaped(taps,drive_literal)+[post_mix_spec(post_scale_literal=DRIVE_TO_POST[drive_literal])]


def mix_reference(average,direct,history,gain,post_scale_literal='628624'):
    average,direct,history=map(_finite,(average,direct,history));gain=_float32(gain)
    if not isinstance(post_scale_literal,str) or post_scale_literal not in POST_SCALES:
        raise ValueError('Expected a checked post-scale literal')
    if not hasattr(math,'fma'):
        raise ValueError('Native post-cubic policy requires Python 3.13+ math.fma')
    try:
        mixed=_finite(math.fma(history,.25,_finite(math.fma(direct,.25,_finite(average*.5)))))
        return dict(mixed=mixed,output=_finite(_finite(mixed*gain)*POST_SCALES[post_scale_literal]))
    except OverflowError as error:
        raise ValueError('Post-cubic mix exceeds finite native-reference arithmetic') from error


def report():
    import lib
    from bmc_dsp import packets
    from condition_return_study import preserved
    from fdrv_resample_study import report as resample_report
    from limit_control_study import checked_access,native_context
    from line_mix_variation import packet_literals
    from weighted_mix_study import check_constructor_literal,require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    resample_report()
    p,n,m,f,t=native_context('SIM_MFX_FDRV')
    if assemble_fragment(post_mix_spec())[10:100]!=p[0x3ec:0x446]:
        raise ValueError('Post-cubic stock body differs')
    for pc,shape in (
            (0x305b28,(('fmul','d0, d0, d3'),)),(0x305b3c,(('fmul','d1, d1, d3'),)),
            (0x305b54,(('fmadd','d0, d2, d5, d0'),)),
            (0x305b68,(('fmadd','d1, d4, d5, d1'),('fmadd','d0, d3, d5, d0'),
                       ('fmadd','d1, d2, d5, d1'))),
            (0x305b74,(('ldr','x13, [x8, #0x828]'),('ldr','s2, [x13, #0x28]'),('fcvt','d2, s2'))),
            (0x305b90,(('fmul','d0, d0, d2'),)),(0x305ba4,(('fmul','d1, d1, d2'),)),
            (0x305ba8,(('ldr','d2, [x8, #0x38]'),('fmul','d0, d0, d2'),('fmul','d1, d1, d2')))):
        require_instructions(n,pc,shape)
    rows=dict(packets(p));literals=[]
    for offset,pc,aliases in ((0x3ec,0x305b24,(0x3fa,0x3fd)),
                              (0x400,0x305b50,(0x412,0x415,0x426,0x429)),
                              (0x43a,0x305ba8,(0x440,0x443))):
        field=packet_literals(p,offset,rows[offset])[0]
        check_constructor_literal(p,m,n[pc],field)
        literals.append(dict(native_pc=pc,wire_fields=list(aliases),**field))
    scale=struct.unpack('<d',bytes(m[i]for i in range(0x38,0x40)))[0]
    if scale.hex()!=POST_SCALES['628624'].hex():
        raise ValueError('Native post-scale constructor double differs')
    bindings=[]
    for pc,kind,field,cell in (
            (0x305b00,'read',0x3b2,0x12),(0x305b10,'read',0x3c4,0x13),
            (0x305b20,'read',0x3f6,0x18),(0x305b38,'read',0x3f8,0x1a),
            (0x305b4c,'read',0x40e,0x19),(0x305b64,'read',0x410,0x1b),
            (0x305b8c,'write',0x436,0x1c),(0x305ba0,'write',0x438,0x1d),
            (0x305bd8,'write',0x456,6),(0x305c00,'write',0x45a,0xa)):
        item=checked_access(n,f,t,pc,kind,field,cell)
        if kind=='write' and any(row['kind']=='write' and row['pc']>pc
                and any(f[key]['address']==cell for key in row['fields'])for row in t['accesses']):
            raise ValueError('Post-cubic cutpoint is overwritten later')
        bindings.append(item)
    if dict(pc=0x305b78,slot=1,width=4)not in t['coefficient_reads']:
        raise ValueError('Post-cubic live gain path differs')
    for register,start,end in (('d0',0x305b2c,0x305b54),('d1',0x305b40,0x305b68),
                                ('d0',0x305b58,0x305b6c),('d0',0x305b70,0x305b8c),
                                ('d1',0x305b74,0x305ba0),('d2',0x305b80,0x305ba8),
                                ('d0',0x305bb4,0x305bd8),('d1',0x305bb4,0x305c00)):
        preserved([n[pc]for pc in range(start,end,4)],register)
    sizes=[len(assemble_fragment(spec))for spec in program_specs()]
    return dict(native_sha256=NATIVE_SHA256,stock_body=[0x3ec,0x446],stock_bytes=90,
                profile_bytes=110,fragment_sizes=sizes,combined_bytes=sum(sizes),
                bindings=bindings,literals=literals,native_post_scale_hex=scale.hex(),
                encoded_post_scale=packet_literals(p,0x43a,rows[0x43a])[0]['value'],
                output_stores_from_following_packet=True,compared_cutpoint_end=0x305c04,
                remaining_stock_bytes=len(p)-0x446,
                remaining_stock_packets=sum(offset>=0x446 for offset,_ in packets(p)),
                full_effect_executable=False,hardware_execution_verified=False)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--frames',type=int,default=12000)
    args=parser.parse_args();result=report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['native_check']=native_check(args.frames,compare_post_mix=True)
        result['fantom_literal_check']=native_check(args.frames,compare_post_mix=True,resample_drive_literal='100000')
    print(json.dumps(result,indent=2,allow_nan=False))
