"""Check the OSC phase-add/wrap interval and its stored-state boundary."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256
from kernel_abi import program_list, read
from line_mix_variation import packet_literals
from line_shaping_study import NATIVE_SHA256, _finite
from limit_control_study import native_context
from weighted_mix_study import check_constructor_literal, require_instructions, require_words

START, END = 0x29014, 0x290c0
OSC_LIST = 0x61112114


def normalize_phase_sum(value):
    """Normalize an already computed sum under the checked signed32 rule."""
    value = _finite(value)
    if abs(value) >= 2**31:
        raise ValueError('Phase sum is outside the checked int32 domain')
    if -1 <= value < 1:
        return value
    normalizer = (int(abs(value)) + 1) & ~1
    if normalizer >= 2**31:
        normalizer -= 2**32
    return value + normalizer if value < 0 else value - normalizer


def advance_phase(phase, increment):
    """Model the checked native interval within its bounded int32 domain."""
    return normalize_phase_sum(_finite(phase) + _finite(increment))


def phase_context(program):
    rows = dict(packets(program))
    if not {0, 6, 0xe, 0x16} <= rows.keys():
        raise ValueError('OSC phase packet boundaries differ')
    for offset, words in (
            (0, (0x0c03, 0x0fe0)), (6, (0x0904, 0x0c30)),
            (0xe, (0x1604, 0x1410, 0x8ee0, 0x4200)),
            (0x16, (0x6f07, 0x3c10, 0x8ee1, 0x8fe2, 0xb9b1, 0xa800))):
        require_words(rows, offset, words)
    source, target = rows[0][2], rows[0x16][6]
    if not 0 <= source < 0x800 or not 0 <= target < 0x800 or source == target:
        raise ValueError('OSC phase addresses alias or exceed data range')
    increment, = packet_literals(program, 6, rows[6])
    if increment['width'] != 4:
        raise ValueError('OSC phase increment width differs')
    return dict(source_address=source, target_address=target, increment=increment)


def fantom_report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom BMC0 CORE1 image')
    result = []
    for segment in program_list(core, OSC_LIST)['segments']:
        if segment['length'] != 806:
            raise ValueError('Fantom OSC segment length differs')
        logical = swap_words(read(core, segment['source'], (segment['length']+3)&~3))[:segment['length']]
        result.append(dict(base=segment['base'], source=segment['source'], **phase_context(logical)))
    return result


def report():
    import capstone
    import lib
    import parse
    from condition_return_study import preserved
    from line_prefix_study import descriptor

    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    program, native, memory, fields, _ = native_context('SIM_MFX_OSC')
    context = phase_context(program)
    if fields[0x1dc] != dict(relative=4, address=5) or fields[0x1d4] != dict(relative=0x22, address=4):
        raise ValueError('OSC phase history records differ')
    increment = context['increment']
    check_constructor_literal(program, memory, native[0x29044], increment)
    require_instructions(native, START, (
        ('ldr', 'x8, [x0, #0x28]'), ('ldr', 'x9, [x0, #8]'),
        ('ldr', 'x9, [x9, #0x18]'), ('ldr', 'x11, [x9, #0x10]'),
        ('ldr', 'w10, [x0, #0x10]'), ('ldr', 'w12, [x8, #0x1dc]'),
        ('ldr', 'x9, [x11, #0x18]'), ('ldr', 'w11, [x11, #0x20]'),
        ('add', 'w12, w12, w10'), ('sub', 'w12, w12, w11'),
        ('and', 'w12, w12, #0x7ff'), ('ldr', 'd0, [x9, w12, uxtw #3]'),
        ('ldr', 'd1, [x8, #0xa8]'), ('fadd', 'd0, d0, d1'),
        ('fmov', 'd1, #-1.00000000'), ('fcmp', 'd0, d1'),
        ('b.pl', '#0x29080'),
    ))
    for start, final, operation in ((0x29058, 0x29078, 'fadd'), (0x2908c, 0x290a8, 'fsub')):
        prefix = (('fneg', 'd1, d0'),) if start == 0x29058 else ()
        source = 'd1' if prefix else 'd0'
        require_instructions(native, start, prefix + (
            ('fcvtzs', f'w12, {source}'), ('add', 'w13, w12, #1'), ('add', 'w14, w12, #2'),
            ('cmp', 'w13, #0'), ('csinc', 'w12, w14, w12, lt'),
            ('and', 'w12, w12, #0xfffffffe'), ('scvtf', 'd1, w12'),
            (operation, 'd0, d0, d1'),
        ))
        if native[final].mnemonic != operation:
            raise ValueError('OSC phase normalization endpoint differs')
    require_instructions(native, 0x2907c, (
        ('b', '#0x290ac'), ('fmov', 'd1, #1.00000000'), ('fcmp', 'd0, d1'), ('b.lt', '#0x290ac'),
    ))
    require_instructions(native, 0x290ac, (
        ('ldr', 'w12, [x8, #0x1d4]'), ('sub', 'w10, w10, w11'),
        ('add', 'w11, w10, w12'), ('and', 'w11, w11, #0x7ff'), ('str', 'd0, [x9, w11, uxtw #3]'),
    ))
    for register, start in (('x8', START+4), ('x9', 0x29030), ('w10', 0x29028), ('w11', 0x29034)):
        preserved([native[pc] for pc in range(start, 0x290ac, 4)], register)
    instructions = [native[pc] for pc in range(START, END, 4)]
    for ins in instructions:
        if ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_RET) or ins.mnemonic in ('adr', 'adrp'):
            raise ValueError('Phase interval has an unexpected external dependency')
        if ins.group(capstone.CS_GRP_JUMP) and not START <= ins.operands[-1].imm < END:
            raise ValueError('Phase branch leaves the checked interval')
    if context['source_address'] != 5 or context['target_address'] != 4:
        raise ValueError('Native OSC packet assignment differs')
    _, _, setter_code = parse.disasm_meth('CFspPiece_Oscillators', 'SetSineFrequency(double)')
    setter = {ins.address: ins for ins in setter_code}
    require_instructions(setter, 0x293900, (('ldr', 'x8, [x0, #8]'), ('cbz', 'x8, #0x293938')))
    require_instructions(setter, 0x293908, (
        ('adrp', 'x9, #0xb78000'), ('add', 'x9, x9, #0xaf0'), ('fadd', 'd0, d0, d0'),
        ('ldr', 's1, [x9]'), ('sshll', 'v1.2d, v1.2s, #0'), ('scvtf', 'd1, d1'),
        ('fdiv', 'd0, d0, d1'), ('ldr', 'x0, [x0]'), ('ldr', 'x1, [x8]'),
        ('ldr', 'x8, [x0]'), ('ldr', 'x2, [x8, #0xc8]'), ('br', 'x2'),
    ))
    ctor_code = list(lib.md().disasm(lib.Z[0x314604:0x314610], 0x314604))
    if [(ins.mnemonic, ins.op_str) for ins in ctor_code] != [
            ('adrp', 'x8, #0xa4d000'), ('add', 'x8, x8, #0x578'), ('stp', 'x19, x8, [x20, #0x18]')]:
        raise ValueError('OSC symbol-owner constructor differs')
    if struct.unpack_from('<Q', lib.Z, 0xa4d578)[0] != 0xa4d760:
        raise ValueError('OSC sine-frequency symbol differs')
    group = descriptor(lib.Z, 0xa4d760)
    if group['records'] != [dict(absolute_byte=0x402a, relative_byte=0xa, width=4)]:
        raise ValueError('OSC sine-frequency field differs')
    return dict(cls='SIM_MFX_OSC', native_interval=[START, END], source=fields[0x1dc],
                target=fields[0x1d4], increment=increment, source_load=0x29040, store=0x290bc,
                frequency_writer=dict(setter=0x293900, symbol=0xa4d760,
                                      group=group, expression='2 * frequency / sample_rate'),
                negative_threshold=-1, positive_threshold=1, model_sum_bound=2**31,
                isolated_opcode_admission=False, native_execution_verified=False,
                bmc_execution_verified=False)


def native_probes(cases):
    import ctypes
    import lib
    from native_callback_fixture import RingFixture, executable_mapping

    cases = tuple(cases)
    checked = report()
    expected = [advance_phase(phase, increment) for phase, increment in cases]
    context = ctypes.create_string_buffer(0x200)
    struct.pack_into('<I', context, 0x1dc, checked['source']['address'])
    struct.pack_into('<I', context, 0x1d4, checked['target']['address'])
    fixture = RingFixture(context)
    code = lib.Z[START:END] + bytes.fromhex('c0035fd6')
    results = []
    with executable_mapping(code) as address:
        invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(address)
        for (phase, increment), predicted in zip(cases, expected, strict=True):
            fixture.ring[checked['source']['address']] = phase
            struct.pack_into('<d', context, 0xa8, increment)
            invoke(ctypes.addressof(fixture.wrapper))
            actual = fixture.ring[checked['target']['address']]
            if actual != predicted:
                raise ValueError(f'Native phase {actual} differs from model {predicted}')
            results.append(dict(phase=phase, increment=increment, stored=actual))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-native', action='store_true')
    parser.add_argument('--core1', type=Path)
    args = parser.parse_args()
    result = report()
    if args.execute_native:
        result['native_probes'] = native_probes([(value, 0) for value in
                                                (-5, -3, -1, 0, 1, 3, 5, 2**31-1, -(2**31-1))] +
                                                [(0.99, 0.03), (-0.99, -0.03)])
        result['native_execution_verified'] = True
    if args.core1:
        from core1 import Core1
        result['fantom_placements'] = fantom_report(Core1(args.core1))
    print(json.dumps(result, indent=2, allow_nan=False))
