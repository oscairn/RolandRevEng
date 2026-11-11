"""Check native TRANSIENT defaults and ten one-origin-step history relations."""
import hashlib
import struct

from bmc_dsp import packets
from limit_control_study import native_context
from line_mix_variation import packet_literals
from line_shaping_study import NATIVE_SHA256, decode_constant
from transient_detector_reference import DEFAULTS, LOG_LIMIT, ZERO_LOG
from weighted_mix_study import check_constructor_literal, require_instructions

PAIRS = ((0x16c, 0x174, 17, 18), (0x17c, 0x184, 19, 20),
         (0x18c, 0x194, 21, 22), (0x19c, 0x1a4, 23, 24),
         (0x1ac, 0x1b4, 25, 26), (0x1cc, 0x1d4, 29, 30),
         (0x1dc, 0x1e4, 31, 32), (0x1f4, 0x1fc, 34, 35),
         (0x214, 0x21c, 38, 39), (0x224, 0x22c, 40, 41))


def report():
    import lib
    from condition_return_study import preserved

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, memory, fields, _ = native_context('SIM_MFX_TRANSIENT')
    history = []
    for store_field, read_field, written, previous in PAIRS:
        for field, address in ((store_field, written), (read_field, previous)):
            record = fields[field]
            if record['address'] != address or int.from_bytes(
                    program[record['relative']:record['relative']+2], 'big') != address:
                raise ValueError('TRANSIENT history record differs from its packet operand')
        history.append(dict(store=fields[store_field], previous=fields[read_field],
                            delay_frames_if_origin_advances_once=1))
    body = [native[pc] for pc in range(0x1d6058, 0x1d6698, 4)]
    for register in ('x21', 'x23', 'x24'):
        preserved(body, register)
    for pc, instructions in (
            (0x1d612c, (('ldr', 'd1, [x21, #0x18]'), ('fadd', 'd1, d0, d1'),
                        ('fmov', 'd2, #-1.00000000'), ('fadd', 'd0, d1, d2'))),
            (0x1d616c, (('fmov', 'd1, #-1.00000000'), ('fmov', 'd0, #-2.00000000'))),
            (0x1d6238, (('fcmp', 'd0, d7'), ('b.ls', '#0x1d625c'))),
            (0x1d6290, (('fcmp', 'd0, d2'), ('b.le', '#0x1d62a8'))),
            (0x1d6350, (('fcmp', 'd2, d1'), ('mov', 'w8, #0xd8'),
                        ('mov', 'w9, #0xe8'), ('csel', 'x8, x9, x8, lt'))),
            (0x1d642c, (('fsub', 'd0, d0, d2'),)),
            (0x1d6468, (('fsub', 'd8, d3, d1'),))):
        require_instructions(native, pc, instructions)
    for start, end, expected in ((0x1d6074, 0x1d6088, ZERO_LOG),
                                  (0x1d62f0, 0x1d6304, LOG_LIMIT),
                                  (0x1d6320, 0x1d6334, -LOG_LIMIT)):
        if decode_constant([native[pc] for pc in range(start, end, 4)])['value'] != expected:
            raise ValueError('TRANSIENT literal constant differs')
    defaults = {field: struct.unpack('<d', bytes(memory[field+i] for i in range(8)))[0]
                for field in (*DEFAULTS, 0x38, 0x48, 0x58, 0x68, 0x88, 0x98, 0xa8, 0xb8)}
    rows = dict(packets(program))
    # Other defaults occur in packet layouts the strict literal reader rejects.
    literal, = packet_literals(program, 0xe, rows[0xe])
    check_constructor_literal(program, memory, native[0x1d6040], literal, object_register='x21')
    return dict(native_sha256=NATIVE_SHA256, defaults=defaults, history=history,
                zero_log_floor=ZERO_LOG, log_limit=LOG_LIMIT,
                hardware_cadence_verified=False, bmc_instruction_admission=False)
