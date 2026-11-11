"""Check the first stereo FDRV state-variable block; native policy, not silicon timing."""
import hashlib
import math

from line_shaping_study import NATIVE_SHA256, _finite, _float32


def filter_step(y, s, t, a, b, c, d, e):
    y, s, t = map(_finite, (y, s, t))
    a, b, c, d, e = map(_float32, (a, b, c, d, e))
    if not hasattr(math, 'fma'):
        raise ValueError('The native filter reference requires Python 3.13+ math.fma')
    try:
        next_t = _finite(_finite(math.fma(s, a, s))+t)
        highpass = _finite(_finite(math.fma(s, b, -next_t))+y)
        preliminary = _finite(math.fma(y, c, _finite(highpass*e)))
        next_s = _finite(_finite(math.fma(highpass, a, highpass))+s)
        output = _finite(math.fma(_finite(next_s+s), d, preliminary))
    except OverflowError as error:
        raise ValueError('Filter reference exceeds finite arithmetic') from error
    return dict(state_s=next_s, state_t=next_t, highpass=highpass, output=output)


def stability(a, b):
    a, b = map(_float32, (a, b))
    g, q = 1+a, -b
    return dict(g=g, damping=q, trace=2-g*q-g*g, determinant=1-g*q,
                stable=g*q > 0 and 4-2*g*q-g*g > 0,
                hardware_calibrated=False)


def report():
    import lib
    from condition_return_study import preserved
    from limit_control_study import checked_access, native_context
    from native_auxiliary_study import report as auxiliary_report
    from weighted_mix_study import require_instructions, require_words
    from bmc_dsp import packets

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    auxiliary = auxiliary_report()
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    rows = dict(packets(program))
    for offset, expected in (
            (0x66, (0x4709, 0x1c8b, 0x5d8f, 0x3fe4, 0x7fe6, 0x2001, 0x6005, 0xc00b, 0xc00b)),
            (0x96, (0x5f07, 0x2443, 0x6547, 0x3fe0, 0x7fe2, 0xc00c, 0xc00c)),
            (0xb6, (0x1005, 0x1c4b, 0x5d4f, 0x1002, 0x5006))):
        require_words(rows, offset, expected)
    bindings = []
    for channel, (source_s, source_t, t_field, t_store, s_field, s_store, output_field, output_store) in enumerate((
            (0x3051ec, 0x3051fc, 0x8e, 0x305228, 0xd2, 0x3052ac, 0x10a, 0x305398),
            (0x3052d0, 0x3052e0, 0x92, 0x305308, 0xd6, 0x30537c, 0x10c, 0x3053ac))):
        s, t = (0x29, 0x2a) if channel == 0 else (0x2c, 0x2d)
        for pc, register, relative, cell, kind in (
                (source_s, 'd2', 0x48+2*channel, s, 'read'),
                (source_t, 'd3', 0x5e+4*channel, t, 'read'),
                (t_store, 'd3', t_field, s, 'write'),
                (s_store, 'd2', s_field, s-1, 'write'),
                (output_store, 'd1' if channel == 0 else 'd0', output_field, 0x24+channel, 'write')):
            item = checked_access(native, fields, trace, pc, kind, relative, cell)
            if native[pc].reg_name(native[pc].operands[0].reg) != register:
                raise ValueError('FDRV filter cutpoint register differs')
            bindings.append(item)
    for pc, instructions in (
            (0x305214, (('fmadd', 'd4, d2, d4, d2'), ('fadd', 'd3, d3, d4'))),
            (0x305250, (('fnmsub', 'd2, d2, d4, d3'), ('fadd', 'd2, d1, d2'))),
            (0x305264, (('fmul', 'd4, d2, d5'),)),
            (0x30528c, (('fmadd', 'd1, d1, d3, d4'), ('fmadd', 'd2, d2, d6, d2'),
                         ('fadd', 'd2, d5, d2'))),
            (0x3052f4, (('fmadd', 'd4, d2, d4, d2'), ('fadd', 'd3, d3, d4'))),
            (0x305328, (('fnmsub', 'd2, d2, d5, d3'), ('fadd', 'd2, d0, d2'))),
            (0x305338, (('fmul', 'd4, d2, d4'),)),
            (0x30535c, (('fmadd', 'd0, d0, d3, d4'), ('fmadd', 'd2, d2, d6, d2'),
                         ('fadd', 'd2, d5, d2')))):
        require_instructions(native, pc, instructions)
    for pc, slot in ((0x305204, 10), (0x305210, 11), (0x305248, 14), (0x30525c, 12),
                     (0x3052b4, 13), (0x3052e4, 10), (0x3052ec, 11), (0x305320, 14),
                     (0x305330, 12), (0x305380, 13)):
        if dict(pc=pc, slot=slot, width=4) not in trace['coefficient_reads']:
            raise ValueError('FDRV filter coefficient reader differs')
    for register, start, end in (('d3', 0x30522c, 0x305250), ('d2', 0x305258, 0x305290),
                                  ('d4', 0x305268, 0x30528c), ('d1', 0x3051cc, 0x30528c),
                                  ('d3', 0x30530c, 0x305328), ('d2', 0x305330, 0x305360),
                                  ('d4', 0x30533c, 0x30535c), ('d0', 0x3051e0, 0x30535c)):
        preserved([native[pc] for pc in range(start, end, 4)], register)
    return dict(native_sha256=NATIVE_SHA256, callback=[0x3050ec, 0x305ea8],
                auxiliary=auxiliary['native_banks'], cutpoints=bindings,
                coefficient_slots=[10, 11, 12, 13, 14],
                state_relation='next S at S-1, next T at S; advancing native origin by one recovers both',
                hardware_origin_cadence_verified=False, hardware_calibrated=False,
                admitted_profile='state_variable_pair', logical_profile_length=184,
                isolated_opcode_admission=False)


def native_check(frames=128, cursors=(0, 0), compare_emulator=False, state_seeds=None,
                  compare_cubic=False, compare_clip=False, compare_input_stage=False,
                  compare_second_stage=False, compare_filterbank=False,
                  compare_resample=False, resample_taps=(.5,.25,-.125),
                  resample_drive_literal='0656d2', compare_post_mix=False,
                  compare_cascade=False,cascade_coefficients=(.5,.25,-.125,.75,-.1875,.0625),
                  compare_full=False,output_coefficients=(.125,-.25,.5,.75,-.1875),parameter_events=None,
                  filter_events=None,filter_literal_policy='native'):
    import ctypes
    from contextlib import ExitStack
    import struct
    import lib
    from coefficient_shift_study import coefficient_context
    from line_state_study import advance_native_origin, native_ring_index
    from native_auxiliary_study import _cache
    from native_callback_fixture import RingFixture, executable_mapping
    from transfer_study import constructor_memory

    compare_cascade = compare_cascade or compare_full
    compare_post_mix = compare_post_mix or compare_cascade
    compare_resample = compare_resample or compare_post_mix
    compare_filterbank = compare_filterbank or compare_resample
    compare_second_stage = compare_second_stage or compare_filterbank
    if compare_second_stage and (compare_cubic or compare_clip):
        raise ValueError('The native prefix fixture stops before clipping and cubic stages')
    compare_input_stage = compare_input_stage or compare_second_stage
    if type(frames) is not int or not 1 <= frames <= 1000000 or len(cursors) != 2:
        raise ValueError('Expected 1..1000000 frames and two valid cursors')
    for cursor in cursors:
        _cache([0, 0, 0], cursor)
    if state_seeds is not None:
        if not isinstance(state_seeds, (list, tuple)) or len(state_seeds) != 4:
            raise ValueError('Expected four explicit initial S/T values')
        state_seeds = list(map(_finite, state_seeds))
    checked = report()
    if filter_events is not None:
        if not compare_full or filter_literal_policy not in ('native','encoded'):
            raise ValueError('EqFa events require full comparison and a native/encoded literal policy')
        if parameter_events is None:parameter_events=[]
        from eqfa_study import (native_function,encoded_taps,validate_events as validate_filters,
            report as eqfa_report)
        eqfa_report();eq_events=validate_filters(filter_events,frames)
    else:eq_events=[]
    if parameter_events is not None and not compare_full:
        raise ValueError('Setter replay requires the complete FDRV comparison')
    _, constructor, pointers, entry, instructions = coefficient_context('SIM_MFX_FDRV')
    if (entry, instructions[-1].address+4) != tuple(checked['callback']) or pointers != {
            0x820+8*slot: slot for slot in range(20)}:
        raise ValueError('FDRV callback or live pointer layout differs')
    allowed = {'add', 'and', 'cmp', 'csel', 'csinc', 'fadd', 'fcmp', 'fcsel', 'fcvt', 'fmadd',
               'fmin', 'fmov', 'fmsub', 'fmul', 'fnmsub', 'fnmul', 'fsub', 'ldp', 'ldr',
               'mov', 'stp', 'str', 'sub', 'ubfiz'}
    if ([i.address for i in instructions] != list(range(entry, checked['callback'][1], 4))
            or (instructions[-1].mnemonic, instructions[-1].op_str) != ('ret', '')
            or any(i.mnemonic not in allowed for i in instructions[:-1])):
        raise ValueError('Expected the checked call-free position-independent FDRV callback')
    image = bytearray(0x8c0)
    for offset, value in constructor_memory(constructor, lib.Z).items():
        if not 0 <= offset < 0x820:
            raise ValueError('FDRV constructor data overlaps live pointers')
        image[offset] = value
    context = ctypes.create_string_buffer(bytes(image), len(image))
    if compare_resample:
        from fdrv_resample_study import report as resample_report,resample_spec,DRIVE_SCALES
        from bmc_subset import assemble_fragment
        resample_report()
        assemble_fragment(resample_spec(taps=resample_taps,drive_literal=resample_drive_literal))
        for offset,value in zip((0x48,0x58,0x68),resample_taps,strict=True):
            struct.pack_into('<d',context,offset,value)
        struct.pack_into('<d',context,0x28,DRIVE_SCALES[resample_drive_literal])
    if compare_post_mix:
        from fdrv_post_cubic_study import report as post_report,POST_SCALES,DRIVE_TO_POST
        post_report()
        struct.pack_into('<d',context,0x38,POST_SCALES[DRIVE_TO_POST[resample_drive_literal]])
    if compare_cascade:
        from fdrv_cascade_study import cascade_spec,report as cascade_report
        cascade_report()
        assemble_fragment(cascade_spec(coefficients=cascade_coefficients))
        for offset,value in zip((0x78,0x88,0x98,0xa8,0xb8,0xc8),cascade_coefficients,strict=True):
            struct.pack_into('<d',context,offset,value)
    if compare_full:
        from fdrv_output_study import output_spec,report as output_report
        output_report()
        assemble_fragment(output_spec(coefficients=output_coefficients))
        for offset,value in zip((0xe8,0x108,0xf8,0x118,0xd8),output_coefficients,strict=True):
            struct.pack_into('<d',context,offset,value)
    values = [0.0]*20
    values[5] = 1.0
    values[10:15] = [-.4973, -.2531, .3737, .1279, -.0623]
    values[15:20] = [-.5, -.25, 0, .5, 0]
    if compare_input_stage:
        prefilter_report()
        values[5:8] = list(map(_float32, (.7313, .1279, .0623)))
    if compare_second_stage:
        values[8] = _float32(.3737)
    if compare_filterbank:
        values[9] = _float32(.6187)
        values[15:20] = list(map(_float32,(-.3813,-.4171,.2937,.1739,-.0823)))
    if compare_cubic or compare_clip:
        values[0] = .75
    if compare_resample:
        values[0] = _float32(8192.)
    if compare_post_mix:
        values[1] = _float32(.7313)
    if compare_full:
        values[2:5]=list(map(_float32,(.4137,.7313,.8279)))
    events=[];event_index=0;envelope_values=0
    if parameter_events is not None:
        from fdrv_parameter_study import (TIMES_MS,envelope_state,envelope_step,native_envelope_functions,
            native_target_functions,native_live_targets,validate_events,report as parameter_report)
        parameter_report()
        level_table=list(struct.unpack_from('<128d',lib.Z,0x818d20))
        events=validate_events(parameter_events,frames,level_table)
        values=list(map(_float32,values))
        envelope_states=[envelope_state(value,value)for value in values]
        envelope_records=[ctypes.create_string_buffer(struct.pack('<ffIf',*state),16)for state in envelope_states]
        envelope_owners=[ctypes.create_string_buffer(0x48)for _ in values]
        for owner,record in zip(envelope_owners,envelope_records,strict=True):
            struct.pack_into('<Q',owner,0x20,ctypes.addressof(record))
        times=(ctypes.c_double*16)(*TIMES_MS)
    records = []
    for offset, slot in pointers.items():
        record = ctypes.create_string_buffer(0x48)
        struct.pack_into('<f', record, 0x28, values[slot])
        records.append(record)
        struct.pack_into('<Q', context, offset, ctypes.addressof(record))
    fixture = RingFixture(context)
    for bank, cursor in zip((0x80, 0x100), cursors, strict=True):
        struct.pack_into('<3dI', fixture.owner, bank, -11, 23, -37, cursor)
    for index in range(2048):
        fixture.ring[index] = ((index*37 % 101)-50)/10000
    if state_seeds is not None:
        for cell, value in zip((0x29, 0x2a, 0x2c, 0x2d), state_seeds, strict=True):
            fixture.ring[cell] = value
    left, right, out_left, out_right = [ctypes.c_double() for _ in range(4)]
    inputs = (ctypes.c_void_p*2)(ctypes.addressof(left), ctypes.addressof(right))
    outputs = (ctypes.c_void_p*2)(ctypes.addressof(out_left), ctypes.addressof(out_right))
    origin, count, cubic_count, cubic_input_values = 0, 0, 0, set()
    clip_count = 0
    stage_count = 0
    second_count = 0
    filterbank_count = 0
    resample_count,clipped_values = 0,0
    post_count=0
    cascade_count=0
    full_count=0
    model_caches=[([-11.,23.,-37.],cursor)for cursor in cursors]
    filter_index=0;filter_values=0;nonexact_literals=0;max_literal_error=0.;native_literals={}
    raw_cascade=list(cascade_coefficients)
    if compare_input_stage:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        stage_specs = [prefilter_spec(), filter_spec()]
        if compare_second_stage:
            from fdrv_second_stage_study import first_spec, second_spec
            stage_specs = [prefilter_spec(), first_spec(), second_spec()]
        if compare_filterbank:
            from fdrv_filterbank_study import program_specs
            stage_specs = program_specs()
        if compare_resample:
            from fdrv_resample_study import program_specs as resample_specs
            stage_specs = resample_specs(resample_taps,resample_drive_literal)
        if compare_post_mix:
            from fdrv_post_cubic_study import program_specs as post_specs
            stage_specs = post_specs(resample_taps,resample_drive_literal)
        if compare_cascade:
            from fdrv_cascade_study import program_specs as cascade_specs
            stage_specs = cascade_specs(resample_taps,resample_drive_literal,cascade_coefficients)
        if compare_full:
            from fdrv_output_study import execute_frame,program_specs as full_specs
            stage_specs=full_specs(resample_taps,resample_drive_literal,cascade_coefficients,output_coefficients)
        stage_programs = [assemble_fragment(spec) for spec in stage_specs]
        model_ring = list(fixture.ring)
    if compare_emulator:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        spec = filter_spec()
        program = assemble_fragment(spec)
    if compare_cubic:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from fdrv_cubic_study import cubic_reference, cubic_spec, report as cubic_report
        cubic_report()
        shape_spec = cubic_spec()
        shape_program = assemble_fragment(shape_spec)
    if compare_clip:
        from bmc_emulator import execute_fragment
        from bmc_subset import assemble_fragment
        from fdrv_clip_study import clip_reference, half_reference, clip_spec, report as clip_report
        clip_report()
        clipped_spec = clip_spec()
        clipped_program = assemble_fragment(clipped_spec)
    code = lib.Z[entry:checked['callback'][1]]
    if compare_second_stage and not compare_resample:
        from fdrv_second_stage_study import prefix_code
        code = prefix_code()
    if compare_filterbank and not compare_resample:
        from fdrv_filterbank_study import prefix_code as bank_prefix_code
        code = bank_prefix_code()
    with ExitStack()as stack:
        address=stack.enter_context(executable_mapping(code))
        if parameter_events is not None:
            native_increment,native_step=stack.enter_context(native_envelope_functions())
            target_functions=stack.enter_context(native_target_functions())
        if filter_events is not None:eqfa_native=stack.enter_context(native_function())
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        for frame in range(frames):
            while event_index<len(events)and events[event_index][0]==frame:
                _,targets=events[event_index];event=parameter_events[event_index]
                native_targets=native_live_targets(event['method'],event['args'],target_functions,level_table)
                for slot,target in targets.items():
                    envelope_states[slot]=envelope_state(envelope_states[slot][0],target)
                    current=struct.unpack_from('<f',envelope_records[slot])[0]
                    initial=envelope_state(current,native_targets[slot])
                    struct.pack_into('<ffIf',envelope_records[slot],0,initial[0],0.,initial[2],initial[3])
                    native_increment(ctypes.addressof(envelope_records[slot]),ctypes.addressof(times))
                event_index+=1
            while filter_index<len(eq_events)and eq_events[filter_index][0]==frame:
                _,which,raw=eq_events[filter_index];event=filter_events[filter_index]
                generated=eqfa_native(event['type'],event['cutoff'],event['gain'])
                native_raw=(generated[0],generated[2],generated[1])
                if [v.hex()for v in native_raw]!=[v.hex()for v in raw]:
                    raise ValueError('EqFa generator differs before parameter application')
                filter_values+=3
                if which=='input':
                    for slot,target,actual in zip((5,6,7),raw,native_raw,strict=True):
                        envelope_states[slot]=envelope_state(envelope_states[slot][0],target)
                        current=struct.unpack_from('<f',envelope_records[slot])[0]
                        initial=envelope_state(current,actual)
                        struct.pack_into('<ffIf',envelope_records[slot],0,initial[0],0.,initial[2],initial[3])
                        native_increment(ctypes.addressof(envelope_records[slot]),ctypes.addressof(times))
                else:
                    packed=encoded_taps(raw)
                    nonexact_literals+=sum(a.hex()!=b.hex()for a,b in zip(raw,packed,strict=True))
                    max_literal_error=max(max_literal_error,*(abs(a-b)for a,b in zip(raw,packed,strict=True)))
                    applied=native_raw if filter_literal_policy=='native'else packed
                    if which=='resample':
                        fields=(0x48,0x58,0x68);index=5
                        stage_specs[index]=dict(stage_specs[index],tap_coefficients=list(packed))
                        if filter_literal_policy=='native':native_literals[index]=raw
                    else:
                        half=0 if which=='post0'else 3;index=9
                        fields=(0x78,0x88,0x98)if half==0 else(0xa8,0xb8,0xc8)
                        raw_cascade[half:half+3]=raw
                        stage_specs[index]=dict(stage_specs[index],filter_coefficients=list(encoded_taps(raw_cascade)))
                        if filter_literal_policy=='native':native_literals[index]=tuple(raw_cascade)
                    for field,value in zip(fields,applied,strict=True):struct.pack_into('<d',context,field,value)
                    stage_programs[index]=assemble_fragment(stage_specs[index])
                filter_index+=1
            if parameter_events is not None:
                for slot,(owner,record)in enumerate(zip(envelope_owners,envelope_records,strict=True)):
                    envelope_states[slot]=envelope_step(envelope_states[slot])
                    native_step(ctypes.addressof(owner))
                    if bytes(record)!=struct.pack('<ffIf',*envelope_states[slot]):
                        raise ValueError(f'Coefficient envelope differs at frame {frame}, slot {slot}')
                    values[slot]=envelope_states[slot][0]
                    struct.pack_into('<f',records[slot],0x28,struct.unpack_from('<f',record)[0])
                    envelope_values+=4
            left.value = .08*math.sin(2*math.pi*220*frame/48000)
            right.value = -.06*math.cos(2*math.pi*337*frame/48000)
            read = lambda cell: fixture.ring[native_ring_index(cell, 0, origin)]
            mixed = [math.fma(read(old2), values[7], math.fma(read(old1), values[6], sample*values[5]))
                     for old1, old2, sample in ((0x1f, 0x20, left.value), (0x22, 0x23, right.value))]
            model = [filter_step(y, read(s), read(s+1), *values[10:15])
                     for y, s in zip(mixed, (0x29, 0x2c), strict=True)]
            if compare_full:
                full_stage=execute_frame(stage_programs,model_ring,origin,dict(enumerate(values)),
                    [left.value,right.value],model_caches,native_literals=native_literals)
                model_ring,model_caches=full_stage['ring'],full_stage['auxiliary']
            elif compare_input_stage:
                for fragment, assignment in zip(stage_programs, stage_specs, strict=True):
                    data = {cell: model_ring[native_ring_index(cell, 0, origin)]
                            for cell in assignment['sources']}
                    stage = execute_fragment(fragment, data, dict(enumerate(values)),
                                             {0x2016: left.value, 0x2017: right.value})
                    for step in stage['trace']:
                        for cell, value in step['writes'].items():
                            model_ring[native_ring_index(cell, 0, origin)] = value
            if compare_emulator:
                data = {cell: read(cell) for cell in spec['sources']}
                data.update({0x1f: mixed[0], 0x22: mixed[1]})
                emulated = execute_fragment(program, data, dict(enumerate(values)))
                for index, item in enumerate(model):
                    for key, actual in (('state_s', emulated['data'][0x28+3*index]),
                                        ('state_t', emulated['data'][0x29+3*index]),
                                        ('output', emulated['ports'][4*index])):
                        if item[key].hex() != actual.hex():
                            raise ValueError('Byte-emulated filter differs from independent reference')
            struct.pack_into('<I', fixture.ring_context, 0x20, origin)
            invoke(ctypes.addressof(fixture.wrapper), ctypes.addressof(inputs), ctypes.addressof(outputs))
            if compare_full:
                if bytes(fixture.ring)!=struct.pack('<2048d',*model_ring):
                    different=[i for i in range(2048)if fixture.ring[i].hex()!=model_ring[i].hex()]
                    raise ValueError(f'Full FDRV ring differs at frame {frame}, physical cells {different[:8]}')
                for port,actual in enumerate((out_left.value,out_right.value)):
                    if actual.hex()!=full_stage['output'][port].hex():
                        raise ValueError(f'Full FDRV output differs at frame {frame}, port {port}')
                for bank,(slots,cursor)in enumerate(model_caches):
                    if bytes(fixture.owner)[0x80+0x80*bank:0x9c+0x80*bank]!=struct.pack('<3dI',*slots,cursor):
                        raise ValueError(f'Full FDRV auxiliary state differs at frame {frame}, bank {bank}')
                full_count+=2058
            if compare_input_stage:
                for cell in (0x1e, 0x21, 0x1f, 0x22, 0x28, 0x29, 0x2b, 0x2c):
                    if read(cell).hex() != model_ring[native_ring_index(cell, 0, origin)].hex():
                        raise ValueError('Independent packet input-stage state differs from native callback')
                    stage_count += 1
                for cell, port in ((0x24, 0), (0x25, 4)):
                    expected_output = (model_ring[native_ring_index(cell,0,origin)]
                                       if compare_second_stage else stage['ports'][port])
                    if read(cell).hex() != expected_output.hex():
                        raise ValueError('Independent packet input-stage output differs from native callback')
                    stage_count += 1
            if compare_second_stage:
                for cell in (0x2e,0x2f,0x31,0x32):
                    if read(cell).hex() != model_ring[native_ring_index(cell,0,origin)].hex():
                        raise ValueError('Second packet filter state differs from native prefix')
                    second_count += 1
                if not compare_filterbank:
                    for port, actual in ((0,out_left.value),(4,out_right.value)):
                        if actual.hex() != stage['ports'][port].hex():
                            raise ValueError('Packet recombination differs from native prefix output')
                        second_count += 1
            if compare_filterbank:
                for cell in (0x34,0x35,0x37,0x38,0x26,0x27,0x3a,0x3b,0x3d,0x3e,0,3):
                    if read(cell).hex() != model_ring[native_ring_index(cell,0,origin)].hex():
                        raise ValueError('Packet filter-bank state differs from native prefix')
                    filterbank_count += 1
                if not compare_resample:
                    for port,actual in ((0,out_left.value),(4,out_right.value)):
                        if actual.hex() != stage['ports'][port].hex():
                            raise ValueError('Packet filter-bank recombination differs from native prefix')
                        filterbank_count += 1
            if compare_resample:
                for cell in (1,4,0x14,0x16,0xe,0x10,0xf,0x11,0x12,0x18,0x13,0x1a):
                    if read(cell).hex() != model_ring[native_ring_index(cell,0,origin)].hex():
                        raise ValueError(f'Packet resampling/shaping differs at frame {frame}, cell {cell:#x}')
                    resample_count += 1
                for cell in (0xe,0x10,0xf,0x11):
                    cubic_input_values.add(read(cell).hex())
                    clipped_values += abs(read(cell))==1
            if compare_post_mix:
                for cell in (0x1c,0x1d,6,0xa):
                    if read(cell).hex()!=model_ring[native_ring_index(cell,0,origin)].hex():
                        raise ValueError(f'Packet post-cubic mix differs at frame {frame}, cell {cell:#x}')
                    post_count+=1
            if compare_cascade:
                for cell in (7,0xb,8,0xc):
                    if read(cell).hex()!=model_ring[native_ring_index(cell,0,origin)].hex():
                        raise ValueError(f'Packet cascade differs at frame {frame}, cell {cell:#x}')
                    cascade_count+=1
            for index, item in enumerate(model):
                for cell, expected in ((0x1f+3*index, mixed[index]), (0x28+3*index, item['state_s']),
                                       (0x29+3*index, item['state_t']), (0x24+index, item['output'])):
                    if read(cell).hex() != expected.hex():
                        raise ValueError(f'Native FDRV filter differs at frame {frame}, cell {cell:#x}')
                    count += 1
            if compare_cubic:
                # The cubic study proves these inputs/results are not overwritten later.
                captured = {cell: read(cell) for cell in shape_spec['sources']}
                cubic_input_values.update(value.hex() for value in captured.values())
                shaped = execute_fragment(shape_program, captured, {})
                for source, target in zip(shape_spec['sources'], shape_spec['targets'], strict=True):
                    expected = cubic_reference(captured[source])
                    if read(target).hex() != expected.hex() or shaped['data'][target].hex() != expected.hex():
                        raise ValueError('Cubic byte window differs from conditional native cutpoints')
                    cubic_count += 1
            if compare_clip:
                # The clip checker audits these source/result cutpoints for later overwrites.
                current_left, current_right = read(0x14), read(0x16)
                previous_left, previous_right = read(0x15), read(0x17)
                captured = dict(zip(clipped_spec['sources'],
                                    (current_left, current_right, previous_left, previous_right)))
                clipped = execute_fragment(clipped_program, captured, {})
                expected = (current_left, current_right,
                            half_reference(current_left, previous_left), clip_reference(current_left),
                            half_reference(current_right, previous_right), clip_reference(current_right))
                for target, value in zip(clipped_spec['targets'], expected, strict=True):
                    if read(target).hex() != value.hex() or clipped['data'][target].hex() != value.hex():
                        raise ValueError('Clipped-half bytes differ from conditional native cutpoints')
                    clip_count += 1
            origin = advance_native_origin(origin)
    actual_cursors = tuple(struct.unpack_from('<I', fixture.owner, offset)[0] for offset in (0x98, 0x118))
    if actual_cursors != tuple(cursors):
        raise ValueError('Native FDRV filter cursors did not roundtrip')
    if (compare_cubic or compare_resample) and frames >= 128 and len(cubic_input_values) < 32:
        raise ValueError('Native cubic comparison did not exercise varied input cutpoints')
    return dict(frames=frames, identical_native_values=count, final_origin=origin,
                initial_cursors=list(cursors), final_cursors=list(actual_cursors),
                explicit_state_seeds=state_seeds,
                emulator_checked=compare_emulator, native_callback_executed=not compare_second_stage or compare_resample,
                native_prefix_executed=compare_second_stage and not compare_resample,
                conditional_cubic_values_checked=cubic_count,
                conditional_clipped_values_checked=clip_count,
                independent_packet_input_stage_values=stage_count,
                independent_packet_second_stage_values=second_count,
                independent_packet_two_filter_values=(stage_count+second_count)
                    if compare_second_stage and not compare_filterbank else 0,
                independent_packet_filterbank_values=(stage_count+second_count+filterbank_count)
                    if compare_filterbank and not compare_resample else 0,
                independent_packet_resample_chain_values=(stage_count+second_count+filterbank_count+resample_count)
                    if compare_resample else 0,
                independent_packet_post_mix_chain_values=(stage_count+second_count+filterbank_count+resample_count+post_count)
                    if compare_post_mix else 0,
                post_mix_fixture_gain=values[1] if compare_post_mix else None,
                independent_packet_cascade_chain_values=(stage_count+second_count+filterbank_count+
                    resample_count+post_count+cascade_count)if compare_cascade else 0,
                cascade_fixture_coefficients=list(cascade_coefficients)if compare_cascade else None,
                independent_full_state_and_output_values=full_count,
                full_ring_cells_per_frame=2048 if compare_full else 0,
                full_auxiliary_values_per_frame=8 if compare_full else 0,
                final_stereo_output_checked=compare_full,
                output_fixture_coefficients=list(output_coefficients)if compare_full else None,
                parameter_event_count=event_index,coefficient_envelope_values_checked=envelope_values,
                native_envelope_updates_per_fixture_frame=1 if parameter_events is not None else 0,
                filter_event_count=filter_index,filter_native_coefficients_checked=filter_values,
                filter_literal_policy=filter_literal_policy if filter_events is not None else None,
                nonexact_generated_literals=nonexact_literals,max_literal_quantization_error=max_literal_error,
                resample_fixture_taps=list(resample_taps) if compare_resample else None,
                resample_fixture_drive=values[0] if compare_resample else None,
                resample_fixture_drive_literal=resample_drive_literal if compare_resample else None,
                clipped_boundary_values=clipped_values,
                native_prefix_end=None if compare_resample else 0x3058a4 if compare_filterbank
                    else 0x30553c if compare_second_stage else None,
                filterbank_fixture_coefficients=dict(C8=values[8],C9=values[9],C15_to_C19=values[15:20])
                    if compare_filterbank else None,
                distinct_cubic_input_values=len(cubic_input_values),
                bmc_hardware_executed=False, coefficient_sources=values[10:15],
                coefficients=list(map(_float32, values[10:15])))


def filter_spec():
    return dict(kind='state_variable_pair', sources=[0x1f, 0x2a, 0x29, 0x22, 0x2d, 0x2c,
                                                   0x2f, 0x32, 0x30, 0x33],
                targets=[0x29, 0x2c, 0x28, 0x2b], coefficient_slots=[10, 11, 12, 13, 14])


def prefilter_spec():
    return dict(kind='stereo_prefilter', input_addresses=[0x2016, 0x2017],
                sources=[0x1f, 0x20, 0x22, 0x23, 0x29, 0x2c],
                targets=[0x1e, 0x21, 0x1f, 0x22], coefficient_slots=[5, 6, 7])


def prefilter_report():
    import lib
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    from bmc_subset import assemble_fragment
    from limit_control_study import checked_access, native_context
    from weighted_mix_study import require_instructions
    program, native, _, fields, trace = native_context('SIM_MFX_FDRV')
    if (assemble_fragment(prefilter_spec())[:76] != program[:0x4c]
            or program[0x5a:0x5e] != bytes.fromhex('001f0022')):
        raise ValueError('Prefilter differs from stock input packets')
    for pc, shape in ((0x305148, (('fmul', 'd5, d0, d2'),)),
                      (0x305170, (('fmul', 'd2, d1, d2'),)),
                      (0x3051a0, (('fmadd', 'd3, d3, d4, d5'),)),
                      (0x3051b4, (('fmadd', 'd0, d0, d4, d2'), ('fmadd', 'd1, d1, d6, d3'))),
                      (0x3051cc, (('fmadd', 'd0, d5, d6, d0'),))):
        require_instructions(native, pc, shape)
    bindings = []
    for pc, kind, field, cell in ((0x305138, 'read', 0x1e, 0x1f),
                                 (0x30516c, 'read', 0x24, 0x22),
                                 (0x305190, 'read', 0x38, 0x20),
                                 (0x3051b0, 'read', 0x3c, 0x23),
                                 (0x30515c, 'write', 0x22, 0x1e),
                                 (0x305180, 'write', 0x26, 0x21),
                                 (0x3051c8, 'write', 0x1e, 0x1f),
                                 (0x3051dc, 'write', 0x24, 0x22)):
        bindings.append(checked_access(native, fields, trace, pc, kind, field, cell))
    for pc, slot in ((0x305114, 5), (0x305140, 6), (0x305198, 7)):
        if dict(pc=pc, slot=slot, width=4) not in trace['coefficient_reads']:
            raise ValueError('Prefilter coefficient source differs')
    owned = {0x1e, 0x21, 0x1f, 0x22, 0x28, 0x29, 0x2b, 0x2c}
    if any(access['kind'] == 'write' and access['pc'] > 0x3053ac
           and any(fields[key]['address'] in owned for key in access['fields'])
           for access in trace['accesses']):
        raise ValueError('Input-stage state is overwritten by a later component')
    return dict(native_sha256=NATIVE_SHA256, stock_bytes=76, profile_bytes=86, combined_bytes=270,
                combined_stored_bytes=272, bindings=bindings,
                coefficient_slots=[5, 6, 7], hardware_execution_verified=False)


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=128)
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--input-stage', action='store_true')
    args = parser.parse_args()
    result = report()
    if args.input_stage:
        result['input_stage'] = prefilter_report()
    if args.execute_native:
        result['native_check'] = native_check(args.frames, compare_emulator=True,
                                              compare_input_stage=args.input_stage)
    print(json.dumps(result, indent=2, allow_nan=False))
