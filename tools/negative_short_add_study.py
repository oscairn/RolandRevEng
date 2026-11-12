"""Disambiguate paired negative-bias native chains; no new DSP opcode admission."""
import hashlib
import math

from bmc_dsp import command_count, literal, packets
from line_shaping_study import NATIVE_SHA256, _finite

# Each row selects original instructions, in dependency order, for five cutpoints.
# Native register names are compiler temporaries, not DSP port numbers.
CONTEXTS = (
    ('SIM_MFX_GASSPH', 0x25c, 0x236, 0x240, 0x1c90, (0x14a5fc, 0x14a604), (
        ('d4', ((0x14a600, 0x14a608, 0x14a60c), (0x14a620, 0x14a624, 0x14a628),
                (0x14a62c, 0x14a630), (0x14a654, 0x14a658), (0x14a678, 0x14a67c))),
        ('d3', ((0x14a634, 0x14a638, 0x14a63c), (0x14a65c, 0x14a660, 0x14a664),
                (0x14a62c, 0x14a680), (0x14a654, 0x14a698), (0x14a678, 0x14a6b4))))),
    ('SIM_MFX_GASSDLY', 0x240, 0x21c, 0x226, 0x1c90, (0x2fa180, 0x2fa188), (
        ('d3', ((0x2fa184, 0x2fa18c, 0x2fa190), (0x2fa1a4, 0x2fa1a8, 0x2fa1ac),
                (0x2fa1b0, 0x2fa1b4), (0x2fa1dc, 0x2fa1e0), (0x2fa1f8, 0x2fa1fc))),
        ('d2', ((0x2fa1b8, 0x2fa1bc, 0x2fa1c0), (0x2fa1e4, 0x2fa1e8, 0x2fa1ec),
                (0x2fa1b0, 0x2fa200), (0x2fa1dc, 0x2fa21c), (0x2fa1f8, 0x2fa238))))),
    ('SIM_MFX_GAMPSIM', 0x2a4, 0x27e, 0x28a, 0x0d90, (0x324f40, 0x324f48), (
        ('d4', ((0x324f44, 0x324f4c, 0x324f50), (0x324f78, 0x324f7c, 0x324f80),
                (0x324f84, 0x324f88), (0x324fa4, 0x324fa8), (0x324fe0, 0x324fe4))),
        ('d3', ((0x324f8c, 0x324f90, 0x324f94), (0x324fac, 0x324fb0, 0x324fb4),
                (0x324f84, 0x324fe8), (0x324fa4, 0x32500c), (0x324fe0, 0x325064))))),
)
STAGES = ('clipped', 'magnitude', 'biased', 'floor', 'gain')


def reference(value):
    value = _finite(value)
    clipped = -1. if value < -1 else min(value, 1.)
    magnitude = clipped if clipped >= 0 else -clipped
    biased = magnitude + (-.25)
    floor = max(biased, 0.)
    return dict(zip(STAGES, (clipped, magnitude, biased, floor, 1.75-floor), strict=True))


def packet_context(previous, words, following):
    """Recognize only three exact neighborhoods with explicitly variable fields."""
    templates = (
        ('SIM_MFX_GASSPH',
         (0xb10b,0x75e4,0x65a7,0x9450,0xded4,0x8fe2,0,None,0,0x24,0),
         (0x2e07,0x1e50,0x5d52,0x3fe4,0x3c00,0xa400,None),
         (0x4b09,0x75d2,0x2442,0xd554,0x1fe6,6,0x2800,0,None)),
        ('SIM_MFX_GASSDLY',
         (0x6209,0x6fe4,0x9450,0xded4,0x8fe2,0,None,0x369f,0xbe00),
         (0x2e07,0x1e50,0x5d52,0x3fe4,0x3c00,0xa400,None),
         (0x6207,0x2442,0xd550,0xfedf,0x1fe2,0,None)),
        ('SIM_MFX_GAMPSIM',
         (0xbe0b,0x7526,0x8410,0xded4,0xdfe2,0xafe4,0,None,None,0x2780,0),
         (0x2e07,0x0e10,0x5d52,0x3fe4,0x3c00,0xa400,None),
         (0x5c07,0x0580,0x3443,0xd550,0x2fe2,0,None)),
    )
    actual = (previous, words, following)
    if any(not isinstance(row, (list, tuple)) or any(type(v) is not int or not 0 <= v <= 65535 for v in row)
           for row in actual):
        raise ValueError('Expected three framed word lists')
    for cls, *expected in templates:
        if all(len(a) == len(b) and all(y is None or x == y for x,y in zip(a,b,strict=True))
               for a,b in zip(actual,expected,strict=True)):
            return cls
    raise ValueError('Unrecognized negative-bias neighborhood')


def checked_chain(native, bounds, source, groups):
    from condition_return_study import preserved
    from weighted_mix_study import require_instructions
    def exact(pc, mnemonic, operands):
        require_instructions(native, pc, ((mnemonic, operands),))
    def destination(pc):
        return native[pc].op_str.split(',')[0]
    upper, lower = map(destination, bounds)
    for pc,value in zip(bounds,(1.,-1.),strict=True):
        exact(pc,'fmov',f'{destination(pc)}, #{value:.8f}')
    clip, magnitude, bias, floor, gain = groups
    temp, clipped = destination(clip[0]), destination(clip[2])
    exact(clip[0],'fmin',f'{temp}, {source}, {upper}')
    exact(clip[1],'fcmp',f'{source}, {lower}')
    exact(clip[2],'fcsel',f'{clipped}, {lower}, {temp}, mi')
    mag = destination(magnitude[0])
    exact(magnitude[0],'fneg',f'{mag}, {clipped}')
    exact(magnitude[1],'fcmp',f'{clipped}, #0.0')
    exact(magnitude[2],'fcsel',f'{mag}, {clipped}, {mag}, ge')
    constant, biased = map(destination,bias)
    exact(bias[0],'fmov',f'{constant}, #-0.25000000')
    exact(bias[1],'fadd',f'{biased}, {mag}, {constant}')
    zero, floored = map(destination,floor)
    exact(floor[0],'movi',f'{zero}, #0000000000000000')
    exact(floor[1],'fmaxnm',f'{floored}, {biased}, {zero}')
    ceiling, coefficient = map(destination,gain)
    exact(gain[0],'fmov',f'{ceiling}, #1.75000000')
    exact(gain[1],'fsub',f'{coefficient}, {ceiling}, {floored}')
    # Verify every dependency across the original compiler's interleaving.
    for reg,start,end in ((upper,bounds[0]+4,clip[0]),(lower,bounds[1]+4,clip[2]),
            (clipped,clip[2]+4,magnitude[2]),(mag,magnitude[2]+4,bias[1]),
            (constant,bias[0]+4,bias[1]),(biased,bias[1]+4,floor[1]),
            (zero,floor[0]+4,floor[1]),(floored,floor[1]+4,gain[1]),
            (ceiling,gain[0]+4,gain[1])):
        preserved([native[pc]for pc in range(start,end,4)],reg)
    return [clipped,mag,biased,floored,coefficient]


def report():
    import lib
    from header_study import families
    from limit_control_study import native_context
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected pinned native image')
    result=[]
    for cls,packet,earlier,field,control,bounds,chains in CONTEXTS:
        program,native,_,_,_=native_context(cls)
        rows=packets(program);index=next(i for i,row in enumerate(rows)if row[0]==packet)
        if packet_context(*(rows[i][1]for i in (index-1,index,index+1)))!=cls:
            raise ValueError('Native class differs from the packet neighborhood')
        words=rows[index][1]
        if families(words[0])!=(1,1,4) or literal(program[packet+10:packet+12])!=-.25:
            raise ValueError('Selected short literal or operation family differs')
        prior=dict(rows)[earlier]
        if control not in prior[1:1+command_count(prior[0])] or literal(program[field:field+2])!=-.25:
            raise ValueError('Earlier negative literal/control context changed')
        outputs=[checked_chain(native,bounds,*chain)for chain in chains]
        result.append(dict(cls=cls,packet=packet,short_literal_field=packet+10,
            earlier_packet=earlier,earlier_control=control,earlier_literal_field=field,
            native_bias_definition=chains[0][1][2][0],
            native_add_candidates=[chain[1][2][1]for chain in chains],native_cutpoint_registers=outputs,
            native_distinct_clipped_sources=[source for source,_ in chains],
            unique_short_add_binding_verified=False,source_port_binding_verified=False))
    return dict(native_sha256=NATIVE_SHA256,contexts=result,native_chains=6,
        formula='1.75 - max(abs(clip(x,-1,1)) + (-.25), 0)',
        ambiguous_additions_per_context=2,isolated_opcode_admission=False,
        bmc_execution_verified=False,native_execution_verified=False)


def fantom_report(core):
    from functools import partial
    from effect_lifecycle_study import IMAGE_SHA256
    from line_mix_variation import core_report
    from quantizer_context_inventory import scan
    if hashlib.sha256(core.data).hexdigest()!=IMAGE_SHA256:
        raise ValueError('Expected pinned Fantom CORE1 image')
    found=core_report(core,partial(scan,controls=(0x5d52,)))
    matched,unresolved=[],[]
    for row in found['matches']:
        selected={key:row[key]for key in ('descriptor','base','source','offset','control_slots')}
        try:cls=packet_context(row['previous'],row['packet'],row['following'])
        except ValueError:
            unresolved.append(dict(**selected,header=row['packet'][0]));continue
        matched.append(dict(**selected,cls=cls))
    return dict(counts=found['counts'],known_neighborhoods=matched,unresolved_neighborhoods=unresolved,
                hardware_verified=False,distinct_algorithms=len({row['cls']for row in matched}))


def native_probes(values):
    """Execute register-only dependency slices; no claim of a whole packet replay."""
    import ctypes
    from contextlib import ExitStack
    import lib
    from limit_control_study import native_context
    from native_callback_fixture import executable_mapping
    report();values=tuple(_finite(v)for v in values)
    expected=[reference(v)for v in values]
    def bridge(dst,src):
        raw=(0x1e604000|int(dst[1:])|(int(src[1:])<<5)).to_bytes(4,'little')
        if [(i.mnemonic,i.op_str)for i in lib.md().disasm(raw,0)]!=[('fmov',f'{dst}, {src}')]:
            raise ValueError('Native register bridge differs')
        return raw
    count=0
    with ExitStack()as stack:
        for cls,_,_,_,_,bounds,chains in CONTEXTS:
            _,native,_,_,_=native_context(cls)
            for source,groups in chains:
                outputs=checked_chain(native,bounds,source,groups)
                pcs=list(bounds)
                for stage,group,output in zip(STAGES,groups,outputs,strict=True):
                    pcs.extend(group)
                    code=bridge(source,'d0')+b''.join(lib.Z[pc:pc+4]for pc in pcs)+bridge('d0',output)+bytes.fromhex('c0035fd6')
                    address=stack.enter_context(executable_mapping(code))
                    call=ctypes.CFUNCTYPE(ctypes.c_double,ctypes.c_double)(address)
                    for value,wanted in zip(values,expected,strict=True):
                        actual=call(value)
                        if actual.hex()!=wanted[stage].hex():
                            raise ValueError(f'{cls} native {stage} differs for {value.hex()}')
                        count+=1
    return count


def boundary_cases():
    values=[-0.,0.,-float.fromhex('0x1.fffffffffffffp1023'),float.fromhex('0x1.fffffffffffffp1023')]
    for value in (-2.,-1.,-.25,0.,.25,1.,2.):
        values.extend((math.nextafter(value,-math.inf),value,math.nextafter(value,math.inf)))
    return values


if __name__=='__main__':
    import argparse,json,random
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core1');parser.add_argument('--execute-native',action='store_true')
    args=parser.parse_args();result=report()
    if args.core1:
        from core1 import Core1
        result['fantom']=fantom_report(Core1(args.core1))
    if args.execute_native:
        generator=random.Random(552)
        values=boundary_cases()+[generator.uniform(-4,4)for _ in range(256)]
        result.update(native_inputs=len(values),native_cutpoints=native_probes(values),native_execution_verified=True)
    print(json.dumps(result,indent=2,allow_nan=False))
