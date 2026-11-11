"""Bind two short literal controls to native FREQ_SHIFTER stores."""
import hashlib
import json

from bmc_dsp import packets
from header_study import layout
from limit_control_study import checked_access, native_context
from line_mix_variation import packet_literals
from line_shaping_study import NATIVE_SHA256
from weighted_mix_study import check_constructor_literal, require_instructions, require_window, require_words


def report():
    import lib
    from condition_return_study import preserved

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the recorded native image')
    program, native, memory, fields, trace = native_context('SIM_MFX_FREQ_SHIFTER')
    rows = dict(packets(program))
    require_words(rows, 0, (0x5f0b, 0x3074, 0x7078, 0x0fe0, 0x4fe2, 1, 14))
    require_words(rows, 0x16, (0xde4b, 0xbe08, 0x1fe0, 0x2fe2, 0xbfe4, 0x99b1, 0xffe6, 3, 4, 0, 13))
    if layout(rows[0])['families'] != [1, 1, 4, 4]:
        raise ValueError('Literal-copy arithmetic arities differ')
    require_window(native, 0x45588, 0x45614)
    require_instructions(native, 0x45588, (('ldr', 'x8, [x0, #0x28]'),))
    preserved([native[pc] for pc in range(0x4558c, 0x45614, 4)], 'x8')
    result = []
    for field, control, load, register, store, relative, address, port in zip(
            packet_literals(program, 0, rows[0]), (0x3074, 0x7078),
            (0x455cc, 0x455e0), ('d2', 'd0'), (0x45600, 0x45614),
            (0x28, 0x2a), (0, 13), (3, 7), strict=True):
        check_constructor_literal(program, memory, native[load], field)
        preserved([native[pc] for pc in range(load+4, store, 4)], register)
        require_instructions(native, store, (('str', f'{register}, [x9, w12, uxtw #3]'),))
        binding = checked_access(native, fields, trace, store, 'write', relative, address)
        result.append(dict(control=control, family=1, literal=field, native_load=load,
                           native_store=binding, observed_store_port=port))
    other_contexts = []
    for cls, offset, field_offset, load, owner_pc, owner in (
            ('SIM_MFX_BPMLP', 0xbe, 0xca, 0x2f2d8, 0x2f064, 'x22'),
            ('SIM_MFX_DJFXLP', 0x176, 0x182, 0x124820, 0x12439c, 'x21')):
        other_program, other_native, other_memory, _, _ = native_context(cls)
        words = dict(packets(other_program))[offset]
        if words[:2] != [0x3408, 0x3074] or layout(words)['families'] != [1, 4, 4]:
            raise ValueError('Independent short literal context differs')
        field, = packet_literals(other_program, offset, words)
        if field['field'] != field_offset or field['width'] != 4:
            raise ValueError('Independent short literal field differs')
        require_instructions(other_native, owner_pc, (('ldr', f'{owner}, [x0, #0x28]'),))
        preserved([other_native[pc] for pc in range(owner_pc+4, load, 4)], owner)
        check_constructor_literal(other_program, other_memory, other_native[load], field,
                                  object_register=owner)
        other_contexts.append(dict(cls=cls, packet=offset, literal=field, native_load=load))
    return dict(cls='SIM_MFX_FREQ_SHIFTER', copies=result, other_contexts=other_contexts,
                isolated_opcode_admission=False,
                limitation='Port and literal correspondence is bounded to the checked load/store context.')


if __name__ == '__main__':
    print(json.dumps(report(), indent=2))
