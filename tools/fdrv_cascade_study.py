"""FDRV post-shaping cascaded history filters; exact offline packet context."""
import hashlib
import math
import struct

from bmc_subset import assemble_fragment
from line_shaping_study import NATIVE_SHA256,_finite

DEFAULT_COEFFICIENTS=(1.,0.,0.,1.,0.,0.)
FIXTURE_COEFFICIENTS=(.5,.25,-.125,.75,-.1875,.0625)


def cascade_spec(data_base=0,coefficients=DEFAULT_COEFFICIENTS):
    return dict(kind='cascaded_history_pair',
                sources=[data_base+x for x in (6,7,8,9,0xa,0xb,0xc,0xd,0x41,0x44,0x42,0x45)],
                targets=[data_base+x for x in (7,0xb,8,0xc)],filter_coefficients=list(coefficients))


def program_specs(taps=(1.,0.,0.),drive_literal='0656d2',coefficients=DEFAULT_COEFFICIENTS):
    from fdrv_post_cubic_study import program_specs as previous
    return previous(taps,drive_literal)+[cascade_spec(coefficients=coefficients)]


def cascade_reference(value,history1,history2,history3,coefficients=DEFAULT_COEFFICIENTS):
    value,history1,history2,history3=map(_finite,(value,history1,history2,history3))
    a,b,c,d,e,f=map(_finite,coefficients)
    if not hasattr(math,'fma'):
        raise ValueError('Native cascade reference requires Python 3.13+ math.fma')
    try:
        first=_finite(math.fma(history2,c,_finite(math.fma(history1,b,_finite(value*a)))))
        second=_finite(math.fma(history3,f,_finite(math.fma(history2,e,_finite(first*d)))))
        return dict(first=first,second=second)
    except OverflowError as error:
        raise ValueError('Cascade exceeds finite native-reference arithmetic')from error


def report():
    import lib
    from bmc_dsp import packets
    from condition_return_study import preserved
    from fdrv_post_cubic_study import report as previous_report
    from limit_control_study import checked_access,native_context
    from line_mix_variation import packet_literals
    from weighted_mix_study import check_constructor_literal,require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    previous_report()
    p,n,m,f,t=native_context('SIM_MFX_FDRV')
    if assemble_fragment(cascade_spec())[10:]!=p[0x446:0x4e0]:
        raise ValueError('Cascade stock body differs')
    for pc,shape in (
            (0x305bc8,(('fmul','d3, d0, d3'),)),(0x305bf0,(('fmul','d4, d1, d4'),)),
            (0x305c18,(('fmadd','d2, d2, d5, d3'),)),
            (0x305c2c,(('fmadd','d0, d0, d5, d4'),)),
            (0x305c34,(('fmadd','d2, d1, d4, d2'),('fmadd','d0, d3, d4, d0'))),
            (0x305c40,(('fmul','d4, d2, d4'),)),(0x305c58,(('fmul','d2, d0, d2'),)),
            (0x305c80,(('fmadd','d1, d1, d5, d4'),)),
            (0x305c94,(('fmadd','d2, d3, d5, d2'),)),
            (0x305c9c,(('fmadd','d1, d0, d3, d1'),('fmadd','d0, d4, d3, d2')))):
        require_instructions(n,pc,shape)
    rows=dict(packets(p));literals=[]
    for packet,pcs in ((0x446,(0x305bc4,0x305bec)),(0x462,(0x305c14,)),
                        (0x47a,(0x305c30,)),(0x48a,(0x305c3c,0x305c54)),
                        (0x49e,(0x305c7c,)),(0x4b6,(0x305c98,))):
        fields=packet_literals(p,packet,rows[packet])
        for pc in pcs:
            check_constructor_literal(p,m,n[pc],fields[0])
            address=n[pc].operands[-1].mem.disp
            value=struct.unpack('<d',bytes(m[i]for i in range(address,address+8)))[0]
            if value.hex()!=fields[0]['value'].hex():
                raise ValueError('Native cascade literal is not the exact decoded default')
            literals.append(dict(native_pc=pc,wire_fields=[v['field']for v in fields],**fields[0]))
    bindings=[]
    for pc,kind,field,cell in (
            (0x305bc0,'read',0x454,7),(0x305bd8,'write',0x456,6),
            (0x305be8,'read',0x458,0xb),(0x305c00,'write',0x45a,0xa),
            (0x305c10,'read',0x470,8),(0x305c28,'read',0x472,0xc),
            (0x305c50,'write',0x454,7),(0x305c68,'write',0x458,0xb),
            (0x305c78,'read',0x4ac,9),(0x305c90,'read',0x4ae,0xd),
            (0x305cb0,'write',0x470,8),(0x305cc0,'write',0x472,0xc),
            (0x305cd0,'read',0x4c4,0x41),(0x305ce0,'read',0x4dc,0x42),
            (0x305d8c,'read',0x4c6,0x44),(0x305d9c,'read',0x4de,0x45)):
        bindings.append(checked_access(n,f,t,pc,kind,field,cell))
        if kind=='write' and any(row['kind']=='write' and row['pc']>pc
                and any(f[key]['address']==cell for key in row['fields'])for row in t['accesses']):
            raise ValueError('Cascade state cutpoint is overwritten later')
    for register,start,end in (('d2',0x305c44,0x305c50),('d0',0x305c3c,0x305c58),
                                ('d1',0x305c38,0x305c80),('d3',0x305c3c,0x305c94),
                                ('d1',0x305ca4,0x305cb0),('d0',0x305ca4,0x305cc0)):
        preserved([n[pc]for pc in range(start,end,4)],register)
    sizes=[len(assemble_fragment(spec))for spec in program_specs()]
    return dict(native_sha256=NATIVE_SHA256,stock_body=[0x446,0x4e0],stock_bytes=154,
                profile_bytes=164,fragment_sizes=sizes,combined_bytes=sum(sizes),
                bindings=bindings,literals=literals,compared_cutpoint_end=0x305cc4,
                future_prefetch_values_compared=False,
                remaining_stock_bytes=len(p)-0x4e0,
                remaining_stock_packets=sum(offset>=0x4e0 for offset,_ in packets(p)),
                full_effect_executable=False,hardware_execution_verified=False)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--frames',type=int,default=12000)
    args=parser.parse_args();result=report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['native_check']=native_check(args.frames,compare_cascade=True)
        result['fantom_literal_check']=native_check(args.frames,compare_cascade=True,resample_drive_literal='100000')
    print(json.dumps(result,indent=2,allow_nan=False))
