"""Check FETDRIVE native history records and paired filter-literal ownership."""
import hashlib
import json
import struct

from bmc_dsp import packets
from limit_control_study import checked_access, native_context
from line_mix_variation import packet_literals
from line_prefix_study import descriptor, literal_calls
from line_shaping_study import NATIVE_SHA256
from weighted_mix_study import check_constructor_literal, require_instructions

# Store field/PC, previous-frame read field/PC, grouped by channel and filter.
HISTORY = (
    (0xac, 0x2f7f24, 0x4fc, 0x2f7f04), (0xb4, 0x2f7f5c, 0x504, 0x2f7f14),
    (0xcc, 0x2f7f8c, 0x51c, 0x2f7f6c), (0xd4, 0x2f7fb8, 0x524, 0x2f7f7c),
    (0xbc, 0x2f8054, 0x50c, 0x2f8034), (0xc4, 0x2f808c, 0x514, 0x2f8044),
    (0xdc, 0x2f80bc, 0x52c, 0x2f809c), (0xe4, 0x2f80e8, 0x534, 0x2f80ac),
)


def report():
    import lib

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, memory, fields, trace = native_context('SIM_MFX_FETDRIVE')
    history = []
    for store_field, store_pc, read_field, read_pc in HISTORY:
        bindings = []
        for field, pc, kind in ((store_field, store_pc, 'write'), (read_field, read_pc, 'read')):
            record = fields[field]
            if int.from_bytes(program[record['relative']:record['relative']+2], 'big') != record['address']:
                raise ValueError('FETDRIVE native record differs from its DSP operand')
            binding = checked_access(native, fields, trace, pc, kind, **record)
            if binding['object_field'] != field:
                raise ValueError('FETDRIVE history uses a different constructor record')
            bindings.append(binding)
        store, previous = bindings
        if previous['address'] != store['address']+1:
            raise ValueError('FETDRIVE unit-delay record relation differs')
        history.append(dict(store=store, previous=previous,
                            delay_frames_if_origin_advances_once=1))
    require_instructions(native, 0x2f7f90, (
        ('ldr', 'd18, [x8, #8]'), ('fmul', 'd7, d7, d18'),
        ('ldr', 'd18, [x8, #0x18]'), ('ldr', 'd19, [x8, #0x28]'),
        ('fmul', 'd17, d17, d19'), ('fmadd', 'd16, d16, d18, d17'), ('fadd', 'd7, d7, d16'),
    ))
    require_instructions(native, 0x2f80c0, (
        ('ldr', 'd3, [x8, #8]'), ('fmul', 'd0, d0, d3'),
        ('ldr', 'd3, [x8, #0x18]'), ('ldr', 'd4, [x8, #0x28]'),
        ('fmul', 'd2, d2, d4'), ('fmadd', 'd1, d1, d3, d2'), ('fadd', 'd0, d0, d1'),
    ))
    rows = dict(packets(program))
    literals = {item['field']: item for offset in (0xa8, 0xbc, 0x13e, 0x152)
                for item in packet_literals(program, offset, rows[offset])}
    coefficients = []
    decoder = lib.md()
    decoder.detail = True
    setup = {ins.address: ins for ins in decoder.disasm(lib.Z[0x32c8fc:0x32c984], 0x32c8fc)}
    require_instructions(setup, 0x32c8fc, (('ldr', 'x20, [x19, #8]'),))
    require_instructions(setup, 0x32c924, (
        ('ldr', 'x8, [x20]'), ('ldr', 'x8, [x8, #0xc8]'), ('fdiv', 'd8, d1, d0'),
        ('adrp', 'x1, #0xa50000'), ('add', 'x1, x1, #0xd98'),
        ('mov', 'x0, x20'), ('fmov', 'd0, d8'), ('blr', 'x8'),
    ))
    calls = [dict(slot_load=0x32c928, call=0x32c940, symbol=0xa50d98)]
    calls += literal_calls([setup[pc] for pc in range(0x32c944, 0x32c984, 4)])
    if calls != [dict(slot_load=slot, call=call, symbol=symbol) for slot, call, symbol in (
            (0x32c928, 0x32c940, 0xa50d98), (0x32c950, 0x32c95c, 0xa50db8),
            (0x32c974, 0x32c980, 0xa50dd8))]:
        raise ValueError('FETDRIVE setup filter-group calls differ')
    for field, load, symbol, relatives in (
            (8, 0x2f7f90, 0xa50d98, (0xb8, 0x14e)),
            (0x18, 0x2f7f98, 0xa50db8, (0xc2, 0x158)),
            (0x28, 0x2f7f9c, 0xa50dd8, (0xc5, 0x15b))):
        group = descriptor(lib.Z, symbol)
        if [(item['relative_byte'], item['width']) for item in group['records']] != [
                (relative, 3) for relative in relatives]:
            raise ValueError('FETDRIVE paired filter group differs')
        check_constructor_literal(program, memory, native[load], literals[relatives[0]])
        if literals[relatives[0]]['value'] != literals[relatives[1]]['value']:
            raise ValueError('FETDRIVE paired default literals differ')
        default, = struct.unpack('<d', bytes(memory[field+i] for i in range(8)))
        coefficients.append(dict(native_field=field, native_load=load, default=default,
                                 symbol=symbol, group=group, literals=[literals[r] for r in relatives]))
    return dict(history=history, filter_coefficients=coefficients, filter_setup_calls=calls,
                filter_expression='b * current + fma(a, previous_input, c * previous_output)',
                hardware_cadence_verified=False, isolated_opcode_admission=False)


if __name__ == '__main__':
    print(json.dumps(report(), indent=2, allow_nan=False))
