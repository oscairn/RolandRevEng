"""Verified second FDRV filter/recombination and an owned native prefix fixture."""
import hashlib
import math

from bmc_subset import assemble_fragment
from fdrv_filter_study import filter_spec, prefilter_spec
from line_shaping_study import NATIVE_SHA256, _finite, _float32


def first_spec():
    return dict(filter_spec(), kind='state_variable_pair_with_output', output_addresses=[0x24, 0x25])


def second_spec(data_base=0, coefficient_base=0):
    return dict(kind='state_variable_recombine_pair',
                sources=[data_base+x for x in (0x24,0x30,0x2f,0x25,0x33,0x32,0x35,0x38,0x36,0x39)],
                targets=[data_base+x for x in (0x2f,0x32,0x2e,0x31)],
                coefficient_slots=[coefficient_base+x for x in (10,11,12,13,14,8,15)])


def programs():
    return tuple(map(assemble_fragment, (prefilter_spec(), first_spec(), second_spec())))


def recombine(dry, wet, coefficient):
    dry, wet = map(_finite, (dry, wet))
    coefficient = _float32(coefficient)
    try:
        return _finite(math.fma(wet, coefficient, _finite(math.fma(-dry, coefficient, dry))))
    except OverflowError as error:
        raise ValueError('Recombination exceeds finite native-reference arithmetic') from error


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    if assemble_fragment(second_spec())[38:] != program[0xf8:0x1aa]:
        raise ValueError('Second filter/recombination body differs from stock')
    for pc, shape in (
            (0x3053dc, (('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
            (0x305404, (('fnmsub','d3, d2, d4, d3'),('fadd','d3, d1, d3'))),
            (0x305414, (('fmul','d5, d3, d5'),)),
            (0x305424, (('fmadd','d1, d1, d4, d5'),('fmadd','d3, d3, d6, d3'),('fadd','d3, d2, d3'))),
            (0x305450, (('fadd','d2, d2, d3'),('fmadd','d1, d2, d4, d1'))),
            (0x305488, (('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
            (0x3054ac, (('fnmsub','d3, d2, d5, d3'),('fadd','d3, d0, d3'))),
            (0x3054bc, (('fmul','d4, d3, d4'),)),
            (0x3054cc, (('fmadd','d0, d0, d5, d4'),('fmadd','d3, d3, d6, d3'),('fadd','d3, d2, d3'))),
            (0x3054f8, (('fadd','d2, d2, d3'),('fmadd','d0, d2, d4, d0'))),
            (0x30552c, (('fmsub','d2, d2, d4, d2'),('fmsub','d3, d3, d4, d3'),
                        ('fmadd','d1, d1, d4, d2'),('fmadd','d0, d0, d4, d3'))),
            (0x3050ec, (('stp','x22, x21, [sp, #-0x20]!'),('stp','x20, x19, [sp, #0x10]'))),
            (0x305e90, (('ldp','x8, x9, [x2]'),('str','d1, [x8]'),('str','d0, [x9]'),
                        ('ldp','x20, x19, [sp, #0x10]'),('ldp','x22, x21, [sp], #0x20'),('ret','')))):
        require_instructions(native, pc, shape)
    prefix = [native[pc] for pc in range(0x3050ec,0x30553c,4)]
    if len(prefix) != 276:
        raise ValueError('Native prefix extent differs')
    preserved(prefix, 'x2')
    preserved(prefix[1:], 'sp')
    bindings = []
    for pc, kind, field, cell in ((0x3053bc,'read',0xda,0x2f),(0x3053cc,'read',0xf0,0x30),
                                 (0x3053f0,'write',0x128,0x2f),(0x305444,'write',0x168,0x2e),
                                 (0x305464,'read',0xdc,0x32),(0x305474,'read',0xf4,0x33),
                                 (0x30549c,'write',0x12c,0x32),(0x3054ec,'write',0x16c,0x31),
                                 (0x30550c,'read',0x10a,0x24),(0x30551c,'read',0x10c,0x25)):
        bindings.append(checked_access(native,fields,trace,pc,kind,field,cell))
    if dict(pc=0x305524,slot=8,width=4) not in trace['coefficient_reads']:
        raise ValueError('Recombination coefficient binding differs')
    for pc,slot in ((0x3053d0,10),(0x3053d8,11),(0x3053fc,14),(0x30540c,12),
                    (0x30541c,10),(0x305448,13),(0x305478,10),(0x305480,11),
                    (0x3054a4,14),(0x3054b4,12),(0x3054c4,10),(0x3054f0,13)):
        if dict(pc=pc,slot=slot,width=4) not in trace['coefficient_reads']:
            raise ValueError('Second-filter coefficient binding differs')
    return dict(native_sha256=NATIVE_SHA256, stock_body=[0xf8,0x1aa], stock_bytes=178,
                profile_bytes=216, combined_bytes=sum(map(len,programs())), bindings=bindings,
                native_prefix=[0x3050ec,0x30553c], appended_output_epilogue=[0x305e90,0x305ea8],
                original_complete_callback_executed=False, hardware_execution_verified=False,
                full_effect_executable=False)


def prefix_code():
    import lib
    report()
    return lib.Z[0x3050ec:0x30553c]+lib.Z[0x305e90:0x305ea8]


def native_probes(values):
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    report()
    # Original FMSUB/FMADD, with checked register moves for a three-double call ABI.
    code = (bytes.fromhex('4440601e0240601e')+lib.Z[0x30552c:0x305530]
            +lib.Z[0x305534:0x305538]+bytes.fromhex('2040601ec0035fd6'))
    expected = [('fmov','d4, d2'),('fmov','d2, d0'),('fmsub','d2, d2, d4, d2'),
                ('fmadd','d1, d1, d4, d2'),('fmov','d0, d1'),('ret','')]
    if [(i.mnemonic,i.op_str) for i in lib.md().disasm(code,0)] != expected:
        raise ValueError('Recombination probe ABI differs')
    results = []
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(ctypes.c_double,ctypes.c_double,ctypes.c_double,ctypes.c_double)(address)
        for dry,wet,g in values:
            reference = recombine(dry,wet,g)
            actual = invoke(_finite(dry),_finite(wet),_float32(g))
            if actual.hex() != reference.hex():
                raise ValueError('Native recombination sign/rounding differs')
            results.append(actual)
    return results


if __name__ == '__main__':
    import argparse,json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--frames',type=int,default=12000)
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['sign_probe'] = native_probes([(2,5,.25),(2,5,0),(2,5,1)])
        result['native_check'] = native_check(args.frames, compare_second_stage=True)
    print(json.dumps(result,indent=2,allow_nan=False))
