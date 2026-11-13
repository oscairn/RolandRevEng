"""RVSDLY 0x60/0x71: a second owned field pair inside the program run 7 checked.

Run 7 (docs/rvsdly-22b-23c-crosscheck-study.md) proved that in SIM_MFX_RVSDLY the
relative program fields 0x22b and 0x23c are independently owned, written with
different computed doubles by CFspMfxRVSDLY::SetAlg(), and each is selected by
exactly one strict-decodable control whose literal equals that field's own
constructor default. The same note recorded that the same two doubles also sit at
relative fields 0x60 and 0x71 and asserted (without a test) that neither of those
fields is selected by any strict-decoder control. This tool re-examines that
aside: fields 0x60 and 0x71 turn out to be a second, structurally identical owned
pair in the same program, with their own constructor pairs, their own count-1
SetAlg write calls and their own unique strict-decoder controls, while in
SIM_MFX_GASSDLY the same relative fields hold different values, have no
constructor pairs and no strict-decoder references at all.

Checks, all failing closed on the pinned ZENOLOGY arm64 image:

* The set of 3-byte windows in the RVSDLY program decoding to each double is
  exactly {0x60, 0x22b} / {0x71, 0x23c}; no third copy exists.
* The constructor declares exactly one pair per field: object 0x1b0 names
  relative 0x60 with the double 0.99609375 at object 0x1b8, and object 0x1a0
  names relative 0x71 with the double -0.998046875 at object 0x1a8 (44 pairs
  total, unchanged from run 7).
* The count-1 width-3 descriptor groups 0xa438c0 (0x60) and 0xa438a0 (0x71) each
  hold one record (absolute 0x4080 / 0x4091) whose only code reference is the
  SetAlg slot-c8 descriptor ADD at 0x2c268c / 0x2c2670; the two skipped
  oversized functions contain no ADRP into the 0xa43000 descriptor page.
* SetAlg passes d0 = d10 to the 0x60 call (0x2c2694) and d0 = d9 to the 0x71
  call (0x2c2678) -- the same registers passed to the 0x22b and 0x23c calls.
* Exactly one strict-decoder control selects each field in the whole program:
  packet 0x56 (header 0x2e07, families [1, 1, 4], control 0x34e2) selects 0x60
  with literal 0.99609375, and packet 0x64 (header 0x1408, families [0, 4],
  control 0xc24) selects 0x71 with literal -0.998046875.
* In SIM_MFX_GASSDLY the same relative fields hold other values, no constructor
  pair names 0x60 or 0x71, and no strict-decoder control selects either field.

No DSP opcode, port semantics, fitted-family role or interpreter admission
follows. The executable subset is unchanged.
"""
import argparse
import hashlib
import struct

from rvsdly_22b_23c_crosscheck import (GROUP_22B, GROUP_23C, NATIVE_SHA256,
                                       SETALG, SETALG_END, mentions,
                                       packet_references, setalg_calls)

FIELDS = (0x60, 0x71)
VALUES = {0x60: 0.99609375, 0x71: -0.998046875}
STORED = {0x60: '2ff000', 0x71: 'aff800'}
PEER_FIELDS = {0x60: 0x22b, 0x71: 0x23c}
OBJECT_OFFSETS = {0x60: 0x1b0, 0x71: 0x1a0}
OBJECT_DOUBLES = {0x60: 0x1b8, 0x71: 0x1a8}
GROUP_60 = 0xa438c0
GROUP_71 = 0xa438a0
ADD_60 = 0x2c268c
ADD_71 = 0x2c2670
CALL_60 = 0x2c2694
CALL_71 = 0x2c2678
CONTROL_PACKETS = {0x60: (0x56, 0x2e07, 0, '0x34e2', [1, 1, 4]),
                   0x71: (0x64, 0x1408, 0, '0xc24', [0, 4])}
DESCRIPTOR_PAGE = 0xa43000
SKIPPED_WINDOWS = ((0x589000, 0x5af838), (0x6b74ec, 0x6d5138))


def stored_fields(program, length, value):
    """Every 3-byte window in the program whose literal equals value exactly."""
    from bmc_dsp import literal
    return [offset for offset in range(0, length - 2)
            if literal(program[offset:offset + 3]) == value]


def ctor_pairs(fields, object_offsets, object_doubles, values):
    """Constructor pairs for the given fields, at pinned object offsets."""
    import parse
    ctor = parse.parse_ctor('SIM_MFX_RVSDLY')
    found = {}
    for object_offset, (relative, value) in ctor['coefs'].items():
        if relative in fields:
            if relative in found:
                raise ValueError(f'Duplicate constructor pair for {relative:#x}')
            found[relative] = (object_offset, value)
    if set(found) != set(fields):
        raise ValueError(f'Constructor pairs for {fields} changed')
    if {rel: off for rel, (off, _) in found.items()} != object_offsets:
        raise ValueError(f'Constructor object offsets for {fields} changed')
    if {rel: off + 8 for rel, (off, _) in found.items()} != object_doubles:
        raise ValueError(f'Constructor double offsets for {fields} changed')
    if {rel: val for rel, (_, val) in found.items()} != values:
        raise ValueError(f'Constructor doubles for {fields} changed')
    return found, len(ctor['coefs'])


def page_references(data, low, high, page):
    """ADRP page addresses used inside one address window."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    pages = set()
    for instruction in md.disasm(data[low:high], low):
        if instruction.mnemonic != 'adrp':
            continue
        operands = instruction.op_str.split(', ')
        if len(operands) == 2 and operands[1].startswith('#'):
            pages.add(int(operands[1][1:], 16))
    return sorted(candidate for candidate in pages
                  if page <= candidate < page + 0x1000)


def gassdly_contrast():
    """GASSDLY fields 0x60/0x71: other bytes, no ctor pair, no strict control."""
    from bmc_dsp import literal
    import parse
    length, program, _, _, base, _ = parse.program('SIM_MFX_GASSDLY')
    ctor = parse.parse_ctor('SIM_MFX_GASSDLY')
    return dict(stored_bytes={hex(f): program[f:f + 3].hex() for f in FIELDS},
                stored_values={hex(f): literal(program[f:f + 3]) for f in FIELDS},
                constructor_fields=sorted(hex(r) for r in ctor['coefs'].values()
                                          if r in FIELDS),
                packet_references={hex(f): packet_references(program, length, base, f)
                                   for f in FIELDS})


def study(data):
    if hashlib.sha256(data).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected the pinned native image')
    import parse
    import lib
    from line_prefix_single_writer import code_references
    length, program, _, _, base, _ = parse.program('SIM_MFX_RVSDLY')
    if base != 0x4020:
        raise ValueError('RVSDLY render segment base changed')
    stored = {hex(f): program[f:f + 3].hex() for f in FIELDS}
    if stored != {hex(f): value for f, value in STORED.items()}:
        raise ValueError('Stored 0x60/0x71 literal bytes changed')
    # exactly one other copy of each double exists: the run 7 field
    copies = {hex(f): stored_fields(program, length, VALUES[f]) for f in FIELDS}
    if copies != {hex(0x60): [0x60, 0x22b], hex(0x71): [0x71, 0x23c]}:
        raise ValueError(f'The double-copy field sets changed: {copies}')
    copies = {field: [hex(offset) for offset in offsets]
              for field, offsets in copies.items()}
    # constructor pairs, one per field, at pinned object offsets
    pairs, pair_count = ctor_pairs(FIELDS, OBJECT_OFFSETS, OBJECT_DOUBLES, VALUES)
    peer_pairs, _ = ctor_pairs((0x22b, 0x23c),
                               {0x22b: 0x150, 0x23c: 0x140},
                               {0x22b: 0x158, 0x23c: 0x148},
                               {0x22b: 0.99609375, 0x23c: -0.998046875})
    if set(peer_pairs) != {0x22b, 0x23c}:
        raise ValueError('Run 7 constructor pairs changed')
    # count-1 width-3 SetAlg groups and their sole code references
    found = mentions(data, FIELDS + (0x22b, 0x23c))
    for group, field, add in ((GROUP_60, 0x60, ADD_60), (GROUP_71, 0x71, ADD_71)):
        rows = [row for row in found if row['symbol'] == group]
        if len(rows) != 1 or rows[0]['count'] != 1:
            raise ValueError(f'Group {group:#x} is no longer count 1')
        record = rows[0]['records'][0]
        if (record['absolute_byte'], record['relative_byte'], record['width']) != \
                (base + field, field, 3):
            raise ValueError(f'Group {group:#x} record changed')
        if code_references(data, group, lib.STARTS) != [add]:
            raise ValueError(f'Group {group:#x} code reference changed')
    for low, high in SKIPPED_WINDOWS:
        if page_references(data, low, high, DESCRIPTOR_PAGE):
            raise ValueError(f'A skipped window {low:#x}..{high:#x} gained an '
                             'adrp into the descriptor page')
    # SetAlg call shape: same argument registers as the 22b/23c calls
    calls, _ = setalg_calls(data)
    by_call = {call['call']: call for call in calls}
    if by_call[hex(CALL_60)]['argument'] != 'd0, d10' or \
            by_call[hex(CALL_60)]['descriptor_add'] != '0x8c0':
        raise ValueError('The 0x60 SetAlg call changed')
    if by_call[hex(CALL_71)]['argument'] != 'd0, d9' or \
            by_call[hex(CALL_71)]['descriptor_add'] != '0x8a0':
        raise ValueError('The 0x71 SetAlg call changed')
    if by_call[hex(0x2c2640)]['argument'] != 'd0, d10' or \
            by_call[hex(0x2c2620)]['argument'] != 'd0, d9':
        raise ValueError('The 22b/23c SetAlg call arguments changed')
    # exactly one strict-decoder control per field, literal exactly the double
    references = {hex(f): packet_references(program, length, base, f)
                  for f in FIELDS}
    for field in FIELDS:
        packet, header, operation, control, families = CONTROL_PACKETS[field]
        if references[hex(field)] != [dict(packet=hex(packet), header=hex(header),
                                           operation=operation, control=control,
                                           width=3, value=VALUES[field])]:
            raise ValueError(f'The {field:#x} strict-decoder reference set changed')
        from bmc_dsp import packets
        from header_study import layout
        words = dict(packets(program[:length]))[packet]
        if layout(words)['families'] != families:
            raise ValueError(f'The {field:#x} control-packet layout changed')
    contrast = gassdly_contrast()
    if contrast['stored_bytes'] == STORED:
        raise ValueError('GASSDLY 0x60/0x71 unexpectedly match the RVSDLY bytes')
    if contrast['constructor_fields'] or any(contrast['packet_references'].values()):
        raise ValueError('GASSDLY 0x60/0x71 gained a constructor pair or strict '
                         'control')
    return dict(native_sha256=NATIVE_SHA256, program_length=length,
                stored_bytes=stored,
                stored_values={hex(f): VALUES[f] for f in FIELDS},
                double_copy_fields=copies,
                constructor=dict(pairs={hex(f): dict(object_offset=hex(OBJECT_OFFSETS[f]),
                                                     object_double=hex(OBJECT_DOUBLES[f]),
                                                     double=VALUES[f])
                                        for f in FIELDS},
                                 pair_count=pair_count),
                ownership=dict(groups={hex(GROUP_60): dict(count=1, field='0x60',
                                                           record_absolute=hex(0x4080),
                                                           add=hex(ADD_60),
                                                           call=hex(CALL_60),
                                                           argument='d0, d10',
                                                           descriptor_add='0x8c0'),
                                       hex(GROUP_71): dict(count=1, field='0x71',
                                                           record_absolute=hex(0x4091),
                                                           add=hex(ADD_71),
                                                           call=hex(CALL_71),
                                                           argument='d0, d9',
                                                           descriptor_add='0x8a0')},
                               writer='CFspMfxRVSDLY::SetAlg()',
                               writer_bounds=[hex(SETALG), hex(SETALG_END)],
                               peer_pairs={hex(0x60): dict(field='0x22b',
                                                           group=hex(GROUP_22B),
                                                           call='0x2c2640'),
                                           hex(0x71): dict(field='0x23c',
                                                           group=hex(GROUP_23C),
                                                           call='0x2c2620')}),
                packet_references=references,
                gassdly_contrast=contrast,
                limits=['DSP execution of these packet controls is unobserved; the '
                        'constructor, stored-literal and strict-decoder agreement '
                        'is static evidence, not hardware traces.',
                        'Runtime-built descriptors, raw writes and other builds are '
                        'not excluded; fields 0x60/0x71 are also declared by other '
                        'count>=1 groups (widths 2/4) whose writers were not named.',
                        'The equal-argument reading (d9/d10 reused across calls) '
                        'relies on AAPCS64 callee-saved d8..d15 for the calls in '
                        'between; it is register-level evidence, not value tracing.',
                        'No opcode, fitted-family role or interpreter admission '
                        'follows.'])


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=argparse.FileType('rb'))
    args = parser.parse_args()
    try:
        print(json.dumps(study(args.native_bin.read()), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')