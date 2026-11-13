"""Second-program cross-check of the GASSDLY 22b/23c ownership reading.

Run 6 (docs/gassdly-62-trap-study.md) proved that in SIM_MFX_GASSDLY the
relative program fields 0x22b and 0x23c hold one shared value: they are declared
together in one count-2 descriptor group written by one slot-c8 call in
CFspMfxGASSDLY::SetDLY, and the native constructor names only 0x22b. That proof
relied on grouped equality, so a critic can object that the two fields are the
same storage by construction. This tool cross-checks the same fields in
SIM_MFX_RVSDLY, the independent program run 6 already listed as a sibling
writer: there the two fields are owned by two separate count-1 groups written
with two different computed doubles, so the equality shortcut is unavailable
and each field must stand on its own evidence.

Checks, all failing closed on the pinned ZENOLOGY arm64 image:

* parse.program('SIM_MFX_RVSDLY') segment bases and stored field bytes.
* The reconstructed constructor declares exactly one pair per field, at exactly
  relative 0x22b (0.99609375, object+0x158) and relative 0x23c
  (-0.998046875, object+0x148), and the stored bytes decode exactly to both.
* The count>=1 descriptor inventory matches the run 6 sibling table: the RVSDLY
  groups 0xa43860 (0x22b) and 0xa43840 (0x23c) each have count 1 and one
  record, both referenced from CFspMfxRVSDLY::SetAlg(); 0x9dfa50 remains the
  only count>=2 group mentioning the two fields.
* SetAlg contains exactly two slot-c8 literal calls, at 0x2c2620 (descriptor
  0xa43840, d0 = -d8) and 0x2c2640 (descriptor 0xa43860, d0 = d8*d10+d11), so
  the two fields receive different values by construction.
* In the whole program, exactly one control exactly selects each field under
  the strict decoder: the long-op literal of packet 0x22e (header 0x2b09,
  families [0,4,4]) selects field 0x23c, and the short control 0x34e5 of packet
  0x21e (header 0x2e08, families [1,1,4]) selects field 0x22b. Both literals
  decode exactly to their field's constructor double.

No DSP opcode, port semantics, fitted-family role or interpreter admission
follows. The executable subset is unchanged.
"""
import argparse
import hashlib
import struct

NATIVE_SHA256 = 'b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30'
FIELDS = (0x22b, 0x23c)
VALUES = {0x22b: 0.99609375, 0x23c: -0.998046875}
STORED = {0x22b: '2ff000', 0x23c: 'aff800'}
OBJECT_OFFSETS = {0x22b: 0x150, 0x23c: 0x140}
OBJECT_DOUBLES = {0x22b: 0x158, 0x23c: 0x148}
BASE = 0x4020
GROUP_22B = 0xa43860
GROUP_23C = 0xa43840
CALL_23C = 0x2c2620
CALL_22B = 0x2c2640
SETALG = 0x2c2508
SETALG_END = 0x2c2740
GASSDLY_GROUP = 0x9dfa50
SIBLING_TABLE = {
    0xa1f9a0: (0x1d1e4c, 'CFspMfxSPACED::SetEQHigh(int)'),
    0xa41d00: (0x2b0244, 'CFspMfxGasSChoFlg::SetAmpGain(int)'),
    GROUP_23C: (0x2c2618, 'CFspMfxRVSDLY::SetAlg()'),
    GROUP_22B: (0x2c2638, 'CFspMfxRVSDLY::SetAlg()'),
    0x9cc8c0: (0x1adb0, 'CFspRevBINHALL::SetAlg()'),
}
TRAP_PACKET = 0x22e
TRAP_HEADER = 0x2b09
TRAP_CONTROL = 0x6fe4


def mentions(data, fields, min_count=1):
    from line_prefix_single_writer import mentions as scan
    return scan(data, 8, lambda a: a, lambda o: o, set(fields), min_count=min_count)


def packet_references(program, length, base, field):
    """Controls whose strict-layout literal reference starts exactly at field.

    Uses header_study.layout, the repo's strict decoder: literal offsets count
    from the payload end (header + controls + long-form extensions). Unsupported
    layouts fail closed and are skipped without guesses.
    """
    from bmc_dsp import literal, packets
    from header_study import UnsupportedLayout, layout
    hits = []
    for offset, words in packets(program[:length]):
        try:
            parsed = layout(words)
        except (ValueError, UnsupportedLayout):
            continue
        for parsed_field in parsed['fields']:
            if parsed_field['role'] != 'literal':
                continue
            field_offset = offset + parsed_field['offset']
            if field_offset != field:
                continue
            value = literal(program[field_offset:field_offset + parsed_field['width']])
            hits.append(dict(packet=hex(offset), header=hex(words[0]),
                             operation=parsed_field['operation'],
                             control=hex(words[1 + parsed_field['operation']]),
                             width=parsed_field['width'], value=value))
    return hits


def constructor_pairs():
    import parse
    ctor = parse.parse_ctor('SIM_MFX_RVSDLY')
    found = {}
    for object_offset, (relative, value) in ctor['coefs'].items():
        if relative in FIELDS:
            if relative in found:
                raise ValueError(f'Duplicate constructor pair for {relative:#x}')
            found[relative] = (object_offset, value)
    if set(found) != set(FIELDS):
        raise ValueError('Constructor pairs for 22b/23c changed')
    if {rel: off for rel, (off, _) in found.items()} != OBJECT_OFFSETS:
        raise ValueError('Constructor object offsets changed')
    if {rel: off + 8 for rel, (off, _) in found.items()} != OBJECT_DOUBLES:
        raise ValueError('Constructor double offsets changed')
    if {rel: val for rel, (_, val) in found.items()} != VALUES:
        raise ValueError('Constructor doubles for 22b/23c changed')
    return found, len(ctor['coefs'])


def setalg_calls(data):
    """The two slot-c8 literal calls and their descriptor/argument registers."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    rows = list(md.disasm(data[SETALG:SETALG_END], SETALG))
    calls = []
    for index, ins in enumerate(rows):
        if ins.mnemonic != 'blr' or index < 3:
            continue
        if rows[index - 1].mnemonic != 'fmov' or not rows[index - 1].op_str.startswith('d0, '):
            continue
        descriptor = rows[index - 2]
        if descriptor.mnemonic != 'add' or not descriptor.op_str.startswith('x1, x1, #'):
            continue
        slot = [j for j in range(index - 2, max(0, index - 10), -1)
                if rows[j].mnemonic == 'ldr' and '#0xc8]' in rows[j].op_str]
        if not slot:
            raise ValueError(f'Slot load missing before call at {ins.address:#x}')
        calls.append(dict(call=hex(ins.address), slot_load=hex(rows[slot[0]].address),
                          descriptor_page=rows[slot[0] + 1].op_str.split('#')[1],
                          descriptor_add=descriptor.op_str.split('#')[1],
                          argument=rows[index - 1].op_str))
    if [call['call'] for call in calls] != [hex(CALL_23C), hex(CALL_22B),
                                            '0x2c265c', '0x2c2678', '0x2c2694',
                                            '0x2c26c8']:
        raise ValueError(f'SetAlg slot-c8 calls changed: {calls}')
    if [call['descriptor_add'] for call in calls] != \
            ['0x840', '0x860', '0x880', '0x8a0', '0x8c0', '0x8e0']:
        raise ValueError('SetAlg descriptor offsets changed')
    if [call['argument'] for call in calls] != \
            ['d0, d9', 'd0, d10', 'd0, d8', 'd0, d9', 'd0, d10', 'd0, #1.00000000']:
        raise ValueError('SetAlg call arguments changed')
    if calls[0]['descriptor_page'] != '0xa43000' or calls[1]['descriptor_page'] != '0xa43000':
        raise ValueError('SetAlg descriptor pages changed')
    return calls, len(rows)


def study(data):
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    import parse
    import lib
    from line_prefix_single_writer import code_references
    length, program, bankb, tab, base, peer = parse.program('SIM_MFX_RVSDLY')
    if base != BASE or peer != 0x8000:
        raise ValueError('RVSDLY render segment bases changed')
    stored = {hex(field): program[field:field + 3].hex() for field in FIELDS}
    if stored != {hex(f): value for f, value in STORED.items()}:
        raise ValueError('Stored 22b/23c literal bytes changed')
    if stored[hex(0x22b)] == stored[hex(0x23c)]:
        raise ValueError('RVSDLY fields unexpectedly share one value')
    pairs, pair_count = constructor_pairs()
    references = {hex(field): packet_references(program, length, base, field)
                  for field in FIELDS}
    if references[hex(0x23c)] != [dict(packet=hex(TRAP_PACKET), header=hex(TRAP_HEADER),
                                       operation=0, control='0xca6', width=3,
                                       value=VALUES[0x23c])]:
        raise ValueError('The 23c packet-reference set changed')
    if references[hex(0x22b)] != [dict(packet=hex(0x21e), header=hex(0x2e08),
                                       operation=1, control='0x34e5', width=3,
                                       value=VALUES[0x22b])]:
        raise ValueError('The 22b packet-reference set changed')
    from bmc_dsp import packets
    from header_study import layout
    trap_words = dict(packets(program[:length]))[TRAP_PACKET]
    trap_layout = layout(trap_words)
    if trap_layout['families'] != [0, 4, 4]:
        raise ValueError('The trap-packet layout changed')
    short_words = dict(packets(program[:length]))[0x21e]
    short_layout = layout(short_words)
    if short_layout['families'] != [1, 1, 4]:
        raise ValueError('The 22b packet layout changed')
    found = mentions(data, FIELDS)
    if [row['symbol'] for row in found] != [0x9cc8c0, GASSDLY_GROUP, 0xa1f9a0,
                                            0xa41d00, GROUP_23C, GROUP_22B]:
        raise ValueError('Descriptor mention inventory changed')
    count2 = mentions(data, FIELDS, min_count=2)
    if [row['symbol'] for row in count2] != [GASSDLY_GROUP]:
        raise ValueError('The only count>=2 group must remain the GASSDLY pair')
    for row in found:
        records = [(record['absolute_byte'], record['relative_byte'], record['width'])
                   for record in row['records']]
        if row['symbol'] in (GROUP_22B, GROUP_23C):
            field = 0x22b if row['symbol'] == GROUP_22B else 0x23c
            if len(records) != 1 or records[0] != (BASE + field, field, 3):
                raise ValueError(f'RVSDLY group records changed for {row["symbol"]:#x}')
            site, _ = SIBLING_TABLE[row['symbol']]
            if code_references(data, row['symbol'], lib.STARTS) != [site]:
                raise ValueError(f'RVSDLY group reference changed for {row["symbol"]:#x}')
    if lib.func(CALL_22B) != (SETALG, SETALG_END) or \
            lib.func(CALL_23C) != (SETALG, SETALG_END):
        raise ValueError('SetAlg bounds changed')
    calls, instruction_count = setalg_calls(data)
    return dict(native_sha256=NATIVE_SHA256, program_length=length,
                segment_bases=[hex(base), hex(peer)],
                stored_bytes=stored,
                stored_values={hex(f): VALUES[f] for f in FIELDS},
                constructor=dict(pairs={hex(rel): dict(object_offset=hex(off),
                                                       object_double=hex(OBJECT_DOUBLES[rel]),
                                                       double=val)
                                        for rel, (off, val) in pairs.items()},
                                 pair_count=pair_count),
                packet_references=references,
                trap_packet=dict(packet=hex(TRAP_PACKET), header=hex(TRAP_HEADER),
                                 control=hex(TRAP_CONTROL),
                                 families=trap_layout['families']),
                short_packet=dict(packet='0x21e', header='0x2e08',
                                  families=short_layout['families']),
                ownership=dict(groups={hex(GROUP_22B): dict(count=1, field=hex(0x22b),
                                                            reference=hex(0x2c2638)),
                                       hex(GROUP_23C): dict(count=1, field=hex(0x23c),
                                                            reference=hex(0x2c2618))},
                               writer='CFspMfxRVSDLY::SetAlg()',
                               writer_bounds=[hex(SETALG), hex(SETALG_END)],
                               slot_c8_calls=[call['call'] for call in calls],
                               group_call_arguments={calls[0]['call']: calls[0]['argument'],
                                                     calls[1]['call']: calls[1]['argument']},
                               group_descriptor_adds={calls[0]['call']: calls[0]['descriptor_add'],
                                                      calls[1]['call']: calls[1]['descriptor_add']},
                               shared_value=False,
                               gassdly_count2_group=hex(GASSDLY_GROUP),
                               sibling_writers={hex(s): e for s, (a, e) in SIBLING_TABLE.items()}),
                limits=['DSP execution of these packet controls is unobserved; the '
                        'constructor and stored-literal bindings are strict-decoder '
                        'evidence, not hardware traces.',
                        'Runtime-built descriptors, raw writes and other builds are not excluded.',
                        '0.99609375 also occurs at field 0x60 in this program; the '
                        'discrimination rests on exact field offsets and constructor '
                        'pairs, not on values alone.',
                        'No opcode, fitted-family role or interpreter admission follows.'])


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=argparse.FileType('rb'))
    args = parser.parse_args()
    try:
        print(json.dumps(study(args.native_bin.read()), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')