"""Packet-only four-section FDRV filter bank, ending before resampling arithmetic."""
import hashlib

from bmc_subset import assemble_fragment
from fdrv_filter_study import prefilter_spec
from fdrv_second_stage_study import first_spec, second_spec
from line_shaping_study import NATIVE_SHA256


def bridge_spec():
    return dict(second_spec(), kind='state_variable_recombine_pair_with_output', output_addresses=[0x60,0x61])


def third_spec():
    return dict(kind='state_variable_pair_with_output',
                sources=[0x60,0x36,0x35,0x61,0x39,0x38,0x3b,0x3e,0x3c,0x3f],
                targets=[0x35,0x38,0x34,0x37],coefficient_slots=[15,16,17,18,19],
                output_addresses=[0x26,0x27])


def terminal_spec(data_base=0, coefficient_base=0):
    return dict(kind='state_variable_terminal_pair_with_output',
                sources=[data_base+x for x in (0x26,0x3c,0x3b,0x27,0x3f,0x3e)],
                targets=[data_base+x for x in (0x3b,0x3e,0x3a,0x3d)],
                coefficient_slots=[coefficient_base+x for x in (15,16,17,18,19,9)],
                output_addresses=[data_base,data_base+3])


def program_specs():
    return [prefilter_spec(),first_spec(),bridge_spec(),third_spec(),terminal_spec()]


def programs():
    return tuple(map(assemble_fragment,program_specs()))


def report():
    import lib
    from condition_return_study import preserved
    from fdrv_second_stage_study import report as second_report
    from limit_control_study import native_context, checked_access
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    second_report()
    program,native,_,fields,trace=native_context('SIM_MFX_FDRV')
    if assemble_fragment(third_spec())[38:184] != program[0x1aa:0x23c]:
        raise ValueError('Third-filter stock body differs')
    if assemble_fragment(terminal_spec())[38:192] != program[0x23c:0x2d6]:
        raise ValueError('Terminal-filter stock body differs')
    for pc,shape in (
            (0x305574,(('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
            (0x30559c,(('fnmsub','d3, d2, d5, d3'),('fadd','d3, d1, d3'))),
            (0x3055b0,(('fmul','d4, d3, d4'),)),
            (0x3055c0,(('fmadd','d1, d1, d5, d4'),('fmadd','d3, d3, d6, d3'),('fadd','d3, d2, d3'))),
            (0x305628,(('fmadd','d2, d5, d2, d5'),('fadd','d2, d3, d2'))),
            (0x30564c,(('fnmsub','d2, d5, d4, d2'),('fadd','d2, d0, d2'))),
            (0x30565c,(('fmul','d3, d2, d3'),)),
            (0x30566c,(('fmadd','d0, d0, d4, d3'),('fmadd','d2, d2, d6, d2'),('fadd','d2, d5, d2'))),
            (0x3056f0,(('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
            (0x305714,(('fnmsub','d3, d2, d5, d3'),('fadd','d3, d1, d3'))),
            (0x305724,(('fmul','d4, d3, d4'),)),
            (0x305734,(('fmadd','d1, d1, d5, d4'),('fmadd','d3, d3, d6, d3'),('fadd','d3, d2, d3'))),
            (0x305798,(('fmadd','d4, d2, d4, d2'),('fadd','d3, d3, d4'))),
            (0x3057bc,(('fnmsub','d3, d2, d5, d3'),('fadd','d3, d0, d3'))),
            (0x3057cc,(('fmul','d4, d3, d4'),)),
            (0x3057dc,(('fmadd','d3, d3, d6, d3'),('fadd','d3, d2, d3'))),
            (0x3057fc,(('fmadd','d0, d0, d5, d4'),)),
            (0x30583c,(('fmsub','d2, d2, d4, d2'),('fmsub','d3, d3, d4, d3'),('fmadd','d1, d1, d4, d2'))),
            (0x30587c,(('fmadd','d0, d0, d4, d3'),))):
        require_instructions(native,pc,shape)
    prefix=[native[pc] for pc in range(0x3050ec,0x3058a4,4)]
    preserved(prefix,'x2');preserved(prefix[1:],'sp')
    preserved([native[pc] for pc in range(0x305848,0x3058a4,4)],'d1')
    preserved([native[pc] for pc in range(0x305880,0x3058a4,4)],'d0')
    bindings=[]
    for pc,kind,field,cell in (
            (0x305548,'read',0x190,0x35),(0x305558,'read',0x1a2,0x36),
            (0x305588,'write',0x1d2,0x35),(0x3055e0,'write',0x216,0x34),
            (0x3055fc,'read',0x192,0x38),(0x305610,'read',0x1a6,0x39),
            (0x30563c,'write',0x1d6,0x38),(0x30568c,'write',0x21a,0x37),
            (0x3056a8,'write',0x24e,0x26),(0x3056bc,'write',0x250,0x27),
            (0x3056cc,'read',0x21e,0x3b),(0x3056dc,'read',0x234,0x3c),
            (0x305704,'write',0x26c,0x3b),(0x305754,'write',0x2ac,0x3a),
            (0x305774,'read',0x220,0x3e),(0x305784,'read',0x238,0x3f),
            (0x3057ac,'write',0x270,0x3e),(0x3057f8,'write',0x2b0,0x3d),
            (0x305878,'write',0x2e6,0),(0x3058a0,'write',0x2ea,3)):
        bindings.append(checked_access(native,fields,trace,pc,kind,field,cell))
    slots=[15,16,19,17,15,18]*4+[9]
    actual=[row['slot'] for row in trace['coefficient_reads'] if 0x30553c<=row['pc']<0x3058a4]
    if actual != slots:
        raise ValueError('Filter-bank live coefficient sequence differs')
    return dict(native_sha256=NATIVE_SHA256,combined_bytes=sum(map(len,programs())),
                fragment_sizes=list(map(len,programs())),third_stock_body=[0x1aa,0x23c],
                terminal_stock_body=[0x23c,0x2d6],bindings=bindings,
                synthetic_bridge_cells=[0x60,0x61],native_prefix=[0x3050ec,0x3058a4],
                prefix_instruction_count=len(prefix),next_packet_raw_history_stores_included=True,
                resampling_arithmetic_executed=False,hardware_execution_verified=False,
                original_complete_callback_executed=False,full_effect_executable=False)


def prefix_code():
    import lib
    report()
    return lib.Z[0x3050ec:0x3058a4]+lib.Z[0x305e90:0x305ea8]


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native',action='store_true')
    parser.add_argument('--frames',type=int,default=12000)
    args=parser.parse_args()
    result=report()
    if args.execute_native:
        from fdrv_filter_study import native_check
        result['native_check']=native_check(args.frames,compare_filterbank=True)
    print(json.dumps(result,indent=2,allow_nan=False))
