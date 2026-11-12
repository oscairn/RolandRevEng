"""OSC's exact multiply/FMA/bias/wrap window; functional native-reference policy."""
import hashlib
import math
import struct

from bmc_dsp import packets,swap_words
from bmc_subset import assemble_fragment,disassemble_fragment
from line_shaping_study import NATIVE_SHA256,_finite
from oscillator_phase_study import START,OSC_LIST,normalize_phase_sum

BEGIN,END=0x29710,0x297c8
BIAS=.203125


def reference(first,second,marker):
    first,second,marker=map(_finite,(first,second,marker))
    if not hasattr(math,'fma'):raise ValueError('OSC reference requires Python3.13+ math.fma')
    try:
        scaled=_finite(first*3.)
        mixed=_finite(math.fma(second,.25,scaled))
        biased=_finite(mixed+BIAS)
    except OverflowError as error:raise ValueError('OSC arithmetic exceeds finite binary64')from error
    return dict(scaled=scaled,mixed=mixed,biased=biased,wrapped=normalize_phase_sum(biased),marker=marker)


def stock_spec(program):
    from weighted_mix_study import require_words
    rows=dict(packets(program))
    require_words(rows,0x258,(0x3306,0x2050,0x1e10,0x4fe2,0x3000))
    for offset,words in ((0x264,(0x3407,0x5510,0xafe2,0x4fe4,0x4300)),
            (0x272,(0x0804,0x5512,0x0005,0x2400)),(0x27a,(0x0903,0x5d50,0x2340)),
            (0x280,(0x0a02,0xdee5)),(0x284,(0x1e05,0xdfe0,0xdfe2))):require_words(rows,offset,words)
    spec=dict(kind='osc_bias_wrap',sources=[rows[0x258][5],rows[0x264][6],0x7ff],
        targets=[rows[0x264][5],rows[0x284][3],rows[0x284][4]])
    if assemble_fragment(spec)[10:]!=program[0x264:0x28e]:raise ValueError('OSC body differs from strict profile')
    return spec


def report():
    import capstone
    import lib
    from condition_return_study import preserved
    from limit_control_study import native_context
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    p,n,m,fields,_=native_context('SIM_MFX_OSC');spec=stock_spec(p)
    for field,relative,cell,pc,kind,register in (
            (0x1c4,0x26e,spec['targets'][0],0x29710,'str','d2'),
            (0x1fc,0x262,spec['sources'][0],0x29720,'ldr','d2'),
            (0x204,0x270,spec['sources'][1],0x29730,'ldr','d4'),
            (0x1cc,0x28a,spec['targets'][1],0x297a8,'str','d0'),
            (0x1f4,0x28c,spec['targets'][2],0x297b8,'str','d0')):
        if fields[field]!=dict(relative=relative,address=cell):raise ValueError('OSC constructor data record changed')
        require_instructions(n,pc,(('ldr',f'w11, [x8, #{field:#x}]'),('add','w11, w10, w11'),
            ('and','w11, w11, #0x7ff'),(kind,f'{register}, [x9, w11, uxtw #3]')))
    require_instructions(n,0x29590,(('fmov','d0, #0.25000000'),))
    preserved([n[pc]for pc in range(0x29594,0x29748,4)],'d0')
    require_instructions(n,0x29740,(('fmov','d5, #3.00000000'),('fmul','d2, d2, d5'),
        ('fmadd','d0, d4, d0, d2'),('fmov','d2, #0.20312500'),('fadd','d0, d0, d2')))
    require_instructions(n,0x2968c,(('fmov','d1, #-1.00000000'),('fmov','d3, #1.00000000')))
    for register in ('d1','d3'):preserved([n[pc]for pc in range(0x29694,BEGIN,4)],register)
    for pc,source,operation in ((0x29754,'d0','fsub'),(0x29780,'d3','fadd')):
        require_instructions(n,pc,(('fcvtzs',f'w11, {source}'),('add','w12, w11, #1'),
            ('add','w13, w11, #2'),('cmp','w12, #0'),('csinc','w11, w13, w11, lt'),
            ('and','w11, w11, #0xfffffffe'),('scvtf',f'{"d2"if source=="d0"else"d3"}, w11'),
            (operation,'d2, d0, d2'if source=='d0'else'd3, d0, d3')))
    require_instructions(n,0x29774,(('fcmp','d0, d3'),('fcsel','d2, d0, d2, lt'),('fneg','d3, d0')))
    require_instructions(n,0x297a0,(('fcmp','d0, d1'),('fcsel','d0, d2, d3, pl')))
    for pc in range(BEGIN,END,4):
        i=n[pc]
        if any(i.group(g)for g in (capstone.CS_GRP_CALL,capstone.CS_GRP_JUMP,capstone.CS_GRP_RET))or i.mnemonic in ('adr','adrp'):
            raise ValueError('OSC bounded native window has external control/position dependence')
    require_instructions(n,START,(('ldr','x8, [x0, #0x28]'),('ldr','x9, [x0, #8]'),
        ('ldr','x9, [x9, #0x18]'),('ldr','x11, [x9, #0x10]'),('ldr','w10, [x0, #0x10]'),
        ('ldr','w12, [x8, #0x1dc]'),('ldr','x9, [x11, #0x18]'),('ldr','w11, [x11, #0x20]')))
    # Injected bridges only pass arguments/results; arithmetic comes from the pinned image.
    for raw,expected in (('0240601e',('fmov','d2, d0')),('4040601e',('fmov','d0, d2')),
                         ('c0035fd6',('ret',''))):
        if [(i.mnemonic,i.op_str)for i in lib.md().disasm(bytes.fromhex(raw),0)]!=[expected]:
            raise ValueError('Native argument/result bridge changed')
    return dict(native_sha256=NATIVE_SHA256,stock_window=[0x264,0x28e],stock_bytes=42,
        spec=spec,profile_bytes=52,packets=6,native_window=[BEGIN,END],
        cutpoints=[0x29748,0x2974c,0x29754,END],hoisted_quarter_definition=0x29590,
        formula='normalize_phase_sum(fma(second,.25,3*first)+.203125)',
        native_policy='binary64, original FMA/order and bounded signed32 normalization',
        hardware_verified=False,complete_oscillator_executable=False,isolated_word_semantics_admitted=False)


def fantom_specs(core):
    from effect_lifecycle_study import IMAGE_SHA256
    from kernel_abi import program_list,read
    if hashlib.sha256(core.data).hexdigest()!=IMAGE_SHA256:raise ValueError('Expected pinned Fantom CORE1')
    rows=[]
    for segment in program_list(core,OSC_LIST)['segments']:
        p=swap_words(read(core,segment['source'],(segment['length']+3)&~3))[:segment['length']]
        rows.append(dict(base=segment['base'],source=segment['source'],spec=stock_spec(p)))
    return rows


def native_check(cases,spec):
    import ctypes
    from contextlib import ExitStack
    import lib
    from bmc_emulator import execute_fragment
    from native_callback_fixture import RingFixture,executable_mapping
    report();cases=tuple(cases)
    program=assemble_fragment(spec)
    if disassemble_fragment(program)!=spec:raise ValueError('OSC profile round trip differs')
    context=ctypes.create_string_buffer(0x280)
    for field,cell in zip((0x1fc,0x204,0x1c4,0x1cc,0x1f4),spec['sources'][:2]+spec['targets'],strict=True):
        struct.pack_into('<I',context,field,cell)
    fixture=RingFixture(context)
    prefix=(lib.Z[START:0x29034]+bytes.fromhex('0240601e')+
        lib.Z[0x29590:0x29594]+lib.Z[0x2968c:0x29694])
    count=0
    with ExitStack()as stack:
        invoke=[]
        for end in (0x29748,0x2974c,0x29754,END):
            suffix=bytes.fromhex('4040601e')if end==0x29748 else b''  # FMOV D0,D2.
            code=prefix+lib.Z[BEGIN:end]+suffix+bytes.fromhex('c0035fd6')
            address=stack.enter_context(executable_mapping(code))
            invoke.append(ctypes.CFUNCTYPE(ctypes.c_double,ctypes.c_void_p,ctypes.c_double)(address))
        for origin in (0,1,2047):
            struct.pack_into('<I',fixture.wrapper,0x10,origin)
            for first,second,marker in cases:
                expected=reference(first,second,marker)
                data=dict(zip(spec['sources'],(first,second,marker),strict=True))
                data.update({cell:.918 for cell in spec['targets']})
                modeled=execute_fragment(program,data,{})
                actual_cuts=[modeled['trace'][i]['after'][5]for i in (1,2,3,4)]
                if any(a.hex()!=expected[k].hex()for a,k in zip(actual_cuts,('scaled','mixed','biased','wrapped'),strict=True)):
                    raise ValueError('Packet cutpoint differs from independent native-order model')
                baseline=[0.]*2048
                for cell,value in data.items():baseline[(cell+origin)&2047]=float(value)
                raw=struct.pack('<2048d',*baseline)
                for index,call in enumerate(invoke):
                    ctypes.memmove(fixture.ring,raw,len(raw))
                    result=call(ctypes.addressof(fixture.wrapper),marker)
                    key=('scaled','mixed','biased','wrapped')[index]
                    if result.hex()!=expected[key].hex():raise ValueError(f'Native OSC {key} differs')
                    wanted=baseline.copy();wanted[(spec['targets'][0]+origin)&2047]=float(marker)
                    if index==3:
                        for cell in spec['targets'][1:]:wanted[(cell+origin)&2047]=expected['wrapped']
                    if bytes(fixture.ring)!=struct.pack('<2048d',*wanted):raise ValueError('Native OSC ring write set/value differs')
                    count+=1
                for cell in spec['targets']:
                    expected_value=marker if cell==spec['targets'][0]else expected['wrapped']
                    if modeled['data'][cell].hex()!=float(expected_value).hex():raise ValueError('OSC modeled store differs')
    return count


def boundary_cases():
    targets=[-5.,-3.,-1.,0.,1.,3.,5.,float(2**31-1),-float(2**31-1),
        math.nextafter(float(2**31),0),-math.nextafter(float(2**31),0)]
    targets.extend(math.nextafter(t,d)for t in (-1.,1.)for d in (-math.inf,math.inf))
    cases=set()
    for target in targets:
        second=4*(target-BIAS)
        if abs(target)<2**31 and math.fma(second,.25,0)+BIAS==target:
            cases.add((0.,second,.375))
    return sorted(cases)


if __name__=='__main__':
    import argparse,json,random
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--core1')
    parser.add_argument('--execute-native',action='store_true');args=parser.parse_args();result=report()
    specs=[result['spec']]
    if args.core1:
        from core1 import Core1
        placements=fantom_specs(Core1(args.core1));result['fantom_placements']=placements
        specs.extend(row['spec']for row in placements)
    if args.execute_native:
        generator=random.Random(500)
        cases=[(generator.uniform(-8,8),generator.uniform(-8,8),generator.uniform(-1,1))for _ in range(128)]
        cases.extend(boundary_cases())
        result.update(native_case_inputs=len(cases),native_data_cutpoints=sum(native_check(iter(cases),spec)for spec in specs),
            compared_specs=len(specs),origins=[0,1,2047],native_execution_verified=True)
    print(json.dumps(result,indent=2,allow_nan=False))
