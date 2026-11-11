"""Complete FDRV arithmetic/output reference; DSP entry/return remain unmodeled."""
import hashlib
import math
import struct

from bmc_subset import assemble_fragment
from line_shaping_study import NATIVE_SHA256,_finite,_float32

DEFAULT_COEFFICIENTS=(0.,0.,0.,1.,0.)
FIXTURE_COEFFICIENTS=(.125,-.25,.5,.75,-.1875)


def output_spec(data_base=0,coefficient_base=0,coefficients=DEFAULT_COEFFICIENTS):
    return dict(kind='fdrv_output_pair',
        sources=[data_base+x for x in (8,0x41,0x42,0xc,0x44,0x45,0,3)],
        targets=[data_base+x for x in (0x41,0x44,0x40,0x43)],
        coefficient_slots=[coefficient_base+x for x in (3,2,4)],filter_coefficients=list(coefficients))


def program_specs(taps=(1.,0.,0.),drive_literal='0656d2',cascade_coefficients=None,
                  coefficients=DEFAULT_COEFFICIENTS):
    from fdrv_cascade_study import program_specs as previous,DEFAULT_COEFFICIENTS as cascade_defaults
    return previous(taps,drive_literal,cascade_defaults if cascade_coefficients is None else cascade_coefficients)+[
        output_spec(coefficients=coefficients)]


def output_reference(y,s,t,dry,wet_gain,dry_gain,master,coefficients=DEFAULT_COEFFICIENTS):
    y,s,t,dry=map(_finite,(y,s,t,dry));a,b,c,d,e=map(_finite,coefficients)
    wet_gain,dry_gain,master=map(_float32,(wet_gain,dry_gain,master))
    if not hasattr(math,'fma'):raise ValueError('Python 3.13+ math.fma required')
    next_t=_finite(_finite(math.fma(s,a,s))+t)
    high=_finite(_finite(math.fma(s,b,-next_t))+y)
    next_s=_finite(_finite(math.fma(high,a,high))+s)
    preliminary=_finite(math.fma(y,d,_finite(high*c)))
    filtered=_finite(math.fma(_finite(next_s+s),e,preliminary))
    mixed=_finite(math.fma(dry,dry_gain,_finite(filtered*wet_gain)))
    return dict(state_s=next_s,state_t=next_t,output=_finite(mixed*master))


def execute_frame(programs,ring,origin,coefficients,samples,auxiliary,*,native_literals=None):
    """Run the complete checked arithmetic chain; return new state without device IO."""
    from bmc_dsp import command_count,packets
    from bmc_emulator import execute_fragment
    from bmc_subset import disassemble_fragment
    from line_state_study import native_ring_index
    from native_auxiliary_study import _cache,cache_push,cache_pop
    if (not isinstance(programs,(list,tuple))or not isinstance(ring,list) or len(ring)!=2048 or type(origin)is not int
            or not 0<=origin<2048 or not isinstance(samples,(list,tuple))or len(samples)!=2
            or not isinstance(auxiliary,(list,tuple))or len(auxiliary)!=2):
        raise ValueError('Expected 2048 ring cells, valid origin, stereo input and two cache banks')
    memory=list(map(_finite,ring));samples=list(map(_finite,samples));caches=[]
    for bank in auxiliary:
        if not isinstance(bank,(list,tuple))or len(bank)!=2:raise ValueError('Expected cache slots/cursor pairs')
        slots,cursor=bank;caches.append((_cache(slots,cursor),cursor))
    specs=[disassemble_fragment(p)for p in programs]
    if native_literals is None:native_literals={}
    if not isinstance(native_literals,dict)or any(type(k)is not int or k not in (5,9,10)for k in native_literals):
        raise ValueError('Native literal lists are restricted to the resample/cascade/output fragments')
    if [s['kind']for s in specs]!=[s['kind']for s in program_specs()]:
        raise ValueError('Expected the complete ordered FDRV arithmetic chain')
    expected=program_specs(specs[5]['tap_coefficients'],specs[5]['drive_literal'],
        specs[9]['filter_coefficients'],specs[10]['filter_coefficients'])
    if specs!=expected:raise ValueError('FDRV fragment resources do not match the checked chain')
    bridge={}
    for index,(program,spec)in enumerate(zip(programs,specs,strict=True)):
        data={cell:(bridge[cell]if cell in (0x60,0x61,0x62,0x63)else
            memory[native_ring_index(cell,0,origin)])for cell in spec['sources']}
        stage=execute_fragment(program,data,coefficients,dict(zip((0x2016,0x2017),samples)),
            native_literals=native_literals.get(index))
        for (_,words),trace in zip(packets(program),stage['trace'],strict=True):
            for cell,value in trace['writes'].items():
                if cell in (0x60,0x61,0x62,0x63):bridge[cell]=value
                else:memory[native_ring_index(cell,0,origin)]=value
            for control in words[1:1+command_count(words[0])]:
                if control not in (0xaf60,0xef60,0xaf61,0xef61):continue
                bank=0 if control<0xc000 else 1;slots,cursor=caches[bank]
                if not control&1:caches[bank]=cache_push(slots,cursor,trace['before'][2+4*bank])
                else:
                    restored,cursor=cache_pop(slots,cursor)
                    if restored.hex()!=trace['after'][2+4*bank].hex():
                        raise ValueError('Packet auxiliary restore differs from independent cache')
                    caches[bank]=(slots,cursor)
    return dict(ring=memory,auxiliary=caches,output=[stage['ports'][0],stage['ports'][4]])


def report():
    import lib
    from bmc_dsp import literal,packets
    from condition_return_study import preserved
    from fdrv_cascade_study import report as previous_report
    from limit_control_study import checked_access,native_context
    from weighted_mix_study import check_constructor_literal,require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    previous_report()
    p,n,m,f,t=native_context('SIM_MFX_FDRV');body=assemble_fragment(output_spec())
    if body[28:-6]!=p[0x4e0:0x57a]:raise ValueError('FDRV output stock body differs')
    if p[0x57a:]!=bytes.fromhex('2d040403450300f81e058fe0cfe220182019'):
        raise ValueError('FDRV return/output boundary differs')
    for pc,shape in (
        (0x305ce8,(('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
        (0x305d24,(('fnmsub','d2, d2, d4, d3'),('fadd','d2, d1, d2'))),
        (0x305d30,(('fmul','d3, d3, d2'),)),
        (0x305d50,(('fmadd','d2, d2, d6, d2'),('fadd','d2, d4, d2'))),
        (0x305d70,(('fmadd','d1, d1, d5, d3'),('fadd','d2, d4, d2'))),
        (0x305d7c,(('fmadd','d1, d2, d3, d1'),)),
        (0x305da4,(('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
        (0x305dd8,(('fnmsub','d2, d2, d4, d3'),('fadd','d2, d0, d2'))),
        (0x305de4,(('fmul','d3, d3, d2'),)),
        (0x305e00,(('fmadd','d0, d0, d5, d3'),)),
        (0x305e08,(('fmadd','d2, d2, d3, d2'),('fadd','d2, d4, d2'))),
        (0x305e28,(('fadd','d2, d4, d2'),)),(0x305e30,(('fmadd','d0, d2, d3, d0'),)),
        (0x305e5c,(('fmul','d1, d1, d2'),)),(0x305e70,(('fmul','d0, d0, d2'),)),
        (0x305e80,(('fmadd','d1, d3, d4, d1'),('fmadd','d0, d5, d4, d0'),
                     ('fmul','d1, d1, d2'),('fmul','d0, d0, d2'))),
        (0x305e90,(('ldp','x8, x9, [x2]'),('str','d1, [x8]'),('str','d0, [x9]')))):
        require_instructions(n,pc,shape)
    literals=[]
    for field,pcs in ((0x4ea,(0x305ce4,0x305d4c,0x305da0,0x305e04)),
                      (0x506,(0x305d20,0x305dd4)),(0x512,(0x305d2c,0x305de0)),
                      (0x526,(0x305d48,0x305dfc)),(0x558,(0x305d78,0x305e2c))):
        item=dict(field=field,width=3,value=literal(p[field:field+3]))
        if p[field:field+3]!=p[field+3:field+6]:raise ValueError('Stereo literals differ')
        for pc in pcs:
            check_constructor_literal(p,m,n[pc],item)
            offset=n[pc].operands[-1].mem.disp
            if struct.unpack('<d',bytes(m[i]for i in range(offset,offset+8)))[0].hex()!=item['value'].hex():
                raise ValueError('Native output literal differs from exact encoded default')
            literals.append(dict(native_pc=pc,**item))
    bindings=[]
    for pc,kind,field,cell in ((0x305cd0,'read',0x4c4,0x41),(0x305ce0,'read',0x4dc,0x42),
        (0x305cfc,'write',0x502,0x41),(0x305d6c,'write',0x546,0x40),
        (0x305d8c,'read',0x4c6,0x44),(0x305d9c,'read',0x4de,0x45),
        (0x305db8,'write',0x504,0x44),(0x305e24,'write',0x548,0x43),
        (0x305e4c,'read',0x2e6,0),(0x305e6c,'read',0x2ea,3)):
        bindings.append(checked_access(n,f,t,pc,kind,field,cell))
    if [r for r in t['coefficient_reads']if r['pc']>=0x305e34]!=[
        dict(pc=0x305e38,slot=3,width=4),dict(pc=0x305e54,slot=2,width=4),dict(pc=0x305e78,slot=4,width=4)]:
        raise ValueError('Output live coefficient paths differ')
    for pc,shape in ((0x305d08,(('add','x13, x12, #0x80'),('ldr','w14, [x12, #0x98]'),
        ('cmp','x14, #2'),('str','d2, [x13, x14, lsl #3]'),('csinc','w14, wzr, w14, hs'),
        ('str','w14, [x12, #0x98]'))),
        (0x305d34,(('sub','w15, w14, #1'),('cmp','w14, #0'),('csel','w14, w9, w15, eq'),
        ('ldr','d4, [x13, w14, uxtw #3]'),('str','w14, [x12, #0x98]'))),
        (0x305dbc,(('add','x13, x12, #0x100'),('ldr','w14, [x12, #0x118]'),
        ('cmp','x14, #2'),('csinc','w15, wzr, w14, hs'),('str','d2, [x13, x14, lsl #3]'),
        ('str','w15, [x12, #0x118]'))),
        (0x305de8,(('sub','w14, w15, #1'),('cmp','w15, #0'),('csel','w9, w9, w14, eq'),
        ('ldr','d4, [x13, w9, uxtw #3]'),('str','w9, [x12, #0x118]')))):
        require_instructions(n,pc,shape)
    for register,start,end in (('d4',0x305d44,0x305d74),('d4',0x305df8,0x305e28),
                              ('d1',0x305e8c,0x305e94),('d0',0x305e90,0x305e98)):
        preserved([n[pc]for pc in range(start,end,4)],register)
    sizes=[len(assemble_fragment(s))for s in program_specs()]
    return dict(native_sha256=NATIVE_SHA256,profile_bytes=len(body),combined_bytes=sum(sizes),
        composed_packets=sum(len(packets(assemble_fragment(s)))for s in program_specs()),
        stock_body=[0x4e0,0x57a],stock_bytes=154,bindings=bindings,literals=literals,
        full_arithmetic_path_mapped=True,dsp_return_00f8_executed=False,
        hardware_execution_verified=False,synthetic_bridge_cells=[0x60,0x61,0x62,0x63])


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true');parser.add_argument('--frames',type=int,default=12000)
    args=parser.parse_args();result=report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['native_check']=native_check(args.frames,compare_full=True)
        result['fantom_literal_check']=native_check(args.frames,compare_full=True,resample_drive_literal='100000')
    print(json.dumps(result,indent=2,allow_nan=False))
