"""Ownership/update-group proof for the GASSDLY 6209 6fe4 literal trap.

The 6209 packet (6fe4 9450 ded4 8fe2) fails closed under the fitted four-operation
rule; its 6fe4 low-six reference would select relative field 23c, while the only
native constructor representative for the 1.414 value names relative 22b. This tool
pins that representative, proves no second representative exists, and recovers the
single stock writer that updates both fields with one declared count-2 operation.
No DSP opcode, port or execution semantics follow.
"""
import argparse
import hashlib
import struct

NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
FIELDS = (0x22b, 0x23c)
PACKET_62 = 0x22e
PACKET_5A = 0x21c
PACKET_SHORT = 0x240
GROUP = 0x9dfa50
GROUP_CALL = 0xcbf98
SETDLY = 0xcbe54
SETDLY_END = 0xcc0d4
GETTER = 0x2f9c34
REPRESENTATIVE = 0xb0
SIBLING_WRITERS = {
    0xa1f9a0: (0x1d1e4c, 'CFspMfxSPACED::SetEQHigh(int)'),
    0xa41d00: (0x2b0244, 'CFspMfxGasSChoFlg::SetAmpGain(int)'),
    0xa43840: (0x2c2618, 'CFspMfxRVSDLY::SetAlg()'),
    0xa43860: (0x2c2638, 'CFspMfxRVSDLY::SetAlg()'),
    0x9cc8c0: (0x1adb0, 'CFspRevBINHALL::SetAlg()'),
}
THRESHOLD_BITS = 0x3fb99999a0000000   # 0.1
SAME_BITS = 0x3ff69fbe80000000        # 1.4140000343322754
ONE_BITS = 0x3ff0000000000000         # 1.0


def packet_field(packet, control_low6, pool):
    """Map a control's low-six reference to an absolute program field, failing closed."""
    from bmc_dsp import literal
    from header_study import reference
    if control_low6 & ~63:
        raise ValueError('Reference is not a low-six code')
    ref = reference(control_low6, len(pool))
    if ref['role'] != 'literal':
        raise ValueError('Expected a literal reference')
    field = packet + 2 + 8 + ref['offset']
    value = literal(program_bytes(field, ref['width']))
    return dict(field=field, width=ref['width'], value=value)


def program_bytes(field, width):
    import lib
    import parse
    if not hasattr(program_bytes, 'cache'):
        program_bytes.cache = parse.program('SIM_MFX_GASSDLY')[1]
    return program_bytes.cache[field:field + width]


def mentions(data, fields, min_count=1):
    from line_prefix_single_writer import mentions as scan
    return scan(data, 8, lambda a: a, lambda o: o, set(fields), min_count=min_count)


def constructor_facts():
    import lib
    import parse
    from transfer_study import constructor_memory
    ctor = parse.parse_ctor('SIM_MFX_GASSDLY')
    start, end = lib.func(ctor['ctor'])
    md = lib.md()
    md.detail = True
    code = list(md.disasm(lib.Z[start:end], start))
    memory = constructor_memory(code, lib.Z)
    relative = int.from_bytes(bytes(memory[REPRESENTATIVE + i] for i in range(4)), 'little')
    value, = struct.unpack('<d', bytes(memory[REPRESENTATIVE + 8 + i] for i in range(8)))
    pairs = {pos: (off, val) for off, (pos, val) in ctor['coefs'].items()}
    loads = {}
    for offset in (0x168, 0x408, 0x2d8):
        rel = int.from_bytes(bytes(memory[offset - 8 + i] for i in range(4)), 'little')
        val, = struct.unpack('<d', bytes(memory[offset + i] for i in range(8)))
        loads[offset] = (rel, val)
    return dict(ctor_start=start, ctor_end=end, relative=relative, value=value,
                pairs_22b=pairs.get(0x22b), pairs_23c=pairs.get(0x23c),
                pair_count=len(ctor['coefs']), other_loads=loads)


def writer_facts(data):
    import capstone
    import lib
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    rows = list(md.disasm(data[SETDLY:SETDLY_END], SETDLY))
    slot_loads = [ins.address for ins in rows
                  if ins.mnemonic == 'ldr' and '#0xc8]' in ins.op_str]
    d1_bits = decode_movk_sequence(rows, 0xcbf68, 0xcbf74, 'x9')
    d0_bits = decode_movk_sequence(rows, 0xcbf7c, 0xcbf88, 'x9')
    constants = dict(d1=[(0xcbf74, d1_bits)], d0=[(0xcbf88, d0_bits)],
                     d9=[(ins.address, ONE_BITS) for ins in rows
                         if ins.mnemonic == 'fmov' and '#1.00000000' in ins.op_str])
    return dict(instruction_count=len(rows), slot_loads=slot_loads, constants=constants)


def decode_movk_sequence(rows, start, end, register):
    """Rebuild one 64-bit immediate from its mov/movk chain, failing closed."""
    bits, seen = 0, False
    for ins in rows:
        if ins.address < start or ins.address > end:
            continue
        if not ins.op_str.startswith(register + ','):
            continue
        if ins.mnemonic == 'mov':
            bits = int(ins.op_str.split('#')[1], 16)
            seen = True
        elif ins.mnemonic == 'movk':
            if not seen:
                raise ValueError(f'movk before mov at {ins.address:#x}')
            shift = int(ins.op_str.split('lsl #')[1]) if ', lsl #' in ins.op_str else 0
            bits |= int(ins.op_str.split('#')[1].split(',')[0], 16) << shift
    if not seen:
        raise ValueError(f'No immediate sequence for {register} at {start:#x}')
    return bits


def study(data):
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    import lib
    import parse
    from bmc_dsp import command_count, literal, packets
    length, program, bankb, tab, base, peer = parse.program('SIM_MFX_GASSDLY')
    rows = dict(packets(program[:length]))
    if base != 0x4020 or peer != 0x8000:
        raise ValueError('GASSDLY render segment bases changed')
    ctor = constructor_facts()
    if (ctor['relative'], ctor['value']) != (0x22b, 1.414) or ctor['pairs_22b'] != (REPRESENTATIVE, 1.414):
        raise ValueError('Constructor representative for 1.414 changed')
    if ctor['pairs_23c'] is not None:
        raise ValueError('Unexpected second constructor representative for 23c')
    if {rel for rel, _ in ctor['other_loads'].values()} != {0x218, 0x228, 0x274}:
        raise ValueError('Remaining constructor-double loads changed')
    if tuple(rows[PACKET_62]) != (0x6209, 0x6fe4, 0x9450, 0xded4, 0x8fe2, 0x0, 0x13, 0x369f, 0xbe00):
        raise ValueError('The 6209 packet changed')
    if command_count(0x6209) != 4:
        raise ValueError('6209 control count changed')
    pool_62 = program[PACKET_62 + 10:PACKET_62 + 18]
    field_23c = packet_field(PACKET_62, 0x6fe4 & 63, pool_62)
    if field_23c != dict(field=0x23c, width=3, value=1.4139995574951172):
        raise ValueError('6fe4 low-six reference no longer selects field 23c')
    if tuple(rows[PACKET_5A]) != (0x5a09, 0x422, 0x75e5, 0x1c90, 0xcedc, 0xa400, 0x510, 0xa636, 0x9fbe):
        raise ValueError('The 5a09 packet changed')
    pool_5a = program[PACKET_5A + 10:PACKET_5A + 18]
    field_22b = packet_field(PACKET_5A, 0x75e5 & 63, pool_5a)
    if field_22b != dict(field=0x22b, width=3, value=1.4139995574951172):
        raise ValueError('75e5 low-six reference no longer selects field 22b')
    if program[0x22b:0x22e] != program[0x23c:0x23f]:
        raise ValueError('The stored 22b/23c literal bytes differ')
    found = mentions(data, FIELDS)
    if len(found) != 6:
        raise ValueError('Descriptor mention inventory changed')
    count2 = mentions(data, FIELDS, min_count=2)
    if [row['symbol'] for row in count2] != [GROUP]:
        raise ValueError('The count>=2 group inventory changed')
    group, = count2
    if [(r['absolute_byte'], r['relative_byte'], r['width']) for r in group['records']] != \
            [(0x424b, 0x22b, 3), (0x425c, 0x23c, 3)]:
        raise ValueError('Group records changed')
    from line_prefix_single_writer import code_references
    references = {row['symbol']: code_references(data, row['symbol'], lib.STARTS)
                  for row in found}
    if references[GROUP] != [GROUP_CALL]:
        raise ValueError('Group reference changed')
    if lib.func(GROUP_CALL) != (SETDLY, SETDLY_END):
        raise ValueError('Group call is no longer inside SetDLY')
    for symbol, (site, export) in SIBLING_WRITERS.items():
        if references[symbol] != [site] or lib.load_exports().get(export) is None:
            raise ValueError(f'Sibling writer for {symbol:#x} changed')
    writer = writer_facts(data)
    if len(writer['slot_loads']) != 1:
        raise ValueError('SetDLY no longer has exactly one slot-c8 call')
    flat = {reg: values for reg, values in writer['constants'].items()}
    if [bits for _, bits in flat.get('d0', [])] != [SAME_BITS] or \
       [bits for _, bits in flat.get('d1', [])] != [THRESHOLD_BITS] or \
       not any(address == 0xcbf8c for address, bits in flat.get('d9', []) if bits == ONE_BITS):
        raise ValueError('SetDLY selection constants changed')
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    getter = list(md.disasm(data[GETTER:GETTER + 76], GETTER))
    if [(i.mnemonic, i.op_str) for i in getter[:6]] != [
            ('ldrb', 'w8, [x1, #0x18]'), ('cbz', 'w8, #0x2f9c6c'), ('mov', 'x8, #0'),
            ('ldr', 'x9, [x0, #0x28]'), ('ldr', 'x10, [x1, #0x10]'),
            ('ldr', 'w10, [x10, #4]')]:
        raise ValueError('GASSDLY getter shape changed')
    if [i.op_str for i in getter if i.mnemonic == 'cmp'][-1] != 'x8, #0x7b':
        raise ValueError('GASSDLY getter entry count changed')
    result = dict(native_sha256=NATIVE_SHA256, program_length=length,
                  segment_bases=[hex(base), hex(peer)],
                  representative=dict(object_offset=REPRESENTATIVE,
                                      relative_field=ctor['relative'],
                                      double=ctor['value'], pair_count=ctor['pair_count'],
                                      second_representative_for_23c=False,
                                      other_loads={hex(k): (hex(v[0]), v[1])
                                                   for k, v in ctor['other_loads'].items()}),
                  trap=dict(packet_62=hex(PACKET_62), control_6fe4='0x6fe4',
                            low6_field=dict(field=hex(field_23c['field']), width=field_23c['width'],
                                            value=field_23c['value']),
                            field_22b=dict(packet_5a=hex(PACKET_5A), control='0x75e5',
                                           field='0x22b', stored_bytes=program[0x22b:0x22e].hex(),
                                           stored_value=1.4139995574951172,
                                           native_double=ctor['value'],
                                           native_loads=['0x2fa1c4', '0x2fa1f0']),
                            stored_bytes_equal=True),
                  ownership=dict(group=hex(GROUP), count=2,
                                 records=[(hex(0x424b), hex(0x22b), 3), (hex(0x425c), hex(0x23c), 3)],
                                 writer='CFspMfxGASSDLY::SetDLY(bool, int, int)',
                                 writer_bounds=[hex(SETDLY), hex(SETDLY_END)],
                                 unique_call=hex(GROUP_CALL), slot_c8_calls=1,
                                 selection=dict(threshold=struct.unpack('<d', struct.pack('<Q', THRESHOLD_BITS))[0],
                                                same=struct.unpack('<d', struct.pack('<Q', SAME_BITS))[0],
                                                one=struct.unpack('<d', struct.pack('<Q', ONE_BITS))[0]),
                                 sibling_writers={hex(s): e for s, (a, e) in SIBLING_WRITERS.items()}),
                  limits=['DSP execution of the 6fe4 operand and the fitted 62-family reading remain unproved.',
                          'Runtime-built descriptors, raw writes and other builds are not excluded.',
                          'The grouped-write equality follows from the checked ABI writers, not from a DSP observation.'])
    return result


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=argparse.FileType('rb'))
    args = parser.parse_args()
    try:
        print(json.dumps(study(args.native_bin.read()), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')