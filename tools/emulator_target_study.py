"""Select bounded paired-program targets; structural inventory is not execution coverage."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from bmc_dsp import command_count, packets, swap_words
from bmc_subset import disassemble_fragment
from header_study import families, UnsupportedLayout
from parent_control_study import NATIVE_SHA256

SHORTLIST = ('SIM_CHO_CHO', 'SIM_MFX_GATE', 'SIM_MFX_FETDRIVE',
             'SIM_MFX_LINEDRIVE', 'SIM_MFX_TS808')
# Admission comes from independent native/DSP studies, not searching for equal words.
CHECKED_REGIONS = {
    'SIM_MFX_FETDRIVE': [('dry_wet_tail', 0x16a, 60)],
    'SIM_MFX_LINEDRIVE': [('allpass4', 0x13e, 82), ('allpass4', 0x190, 82),
                         ('dry_wet_tail', 0x1e2, 60)],
}


def remaining_regions(length, regions, boundaries):
    """Partition only whole packets; refuse overlaps, truncation or partial admission."""
    if length <= 0 or 0 not in boundaries or length not in boundaries:
        raise ValueError('Expected complete packet boundaries')
    cursor, result = 0, []
    for start, end in sorted(regions):
        if start < cursor or end <= start or end > length or start not in boundaries or end not in boundaries:
            raise ValueError('Invalid or overlapping checked region')
        if cursor < start:
            result.append([cursor, start])
        cursor = end
    if cursor < length:
        result.append([cursor, length])
    return result


def segment_stream(data, segment):
    base, length, capacity, source = segment
    stored_length = (length+3) & ~3
    if length <= 0 or length % 2 or capacity < length or source < 0 or source+stored_length > len(data):
        raise ValueError('Segment outside recorded image')
    return swap_words(data[source:source+stored_length])[:length]


def verify_list(data, item):
    """Cross-check generated LP64 metadata against the actual descriptor bytes."""
    address, kind, packed, segments = item
    if address < 0 or address+16 > len(data) or not 1 <= len(segments) <= 16:
        raise ValueError('List descriptor outside recorded image')
    actual_kind, actual_packed, table = struct.unpack_from('<IIQ', data, address)
    if (kind, packed) != (actual_kind, actual_packed) or packed >> 8 != len(segments):
        raise ValueError('Program-list metadata differs from artifact')
    if table % 8 or table+24*len(segments) > len(data):
        raise ValueError('Segment table outside recorded image')
    for index, expected in enumerate(segments):
        base, length, capacity, padding, source = struct.unpack_from('<IIIIQ', data, table+24*index)
        if padding or list(expected) != [base, length, capacity, source]:
            raise ValueError('Segment metadata differs from artifact')


def assess_stream(cls, stream):
    decoded = packets(stream)
    boundaries = {offset for offset, _ in decoded} | {len(stream)}
    checked = []
    for kind, start, length in CHECKED_REGIONS.get(cls, []):
        end = start+length
        if start not in boundaries or end not in boundaries or end > len(stream):
            raise ValueError('Checked native context does not align with packets')
        assignment = disassemble_fragment(stream[start:end])
        if assignment['kind'] != kind:
            raise ValueError('Checked context changed template kind')
        checked.append(dict(kind=kind, start=start, end=end, assignment=assignment))
    gaps = remaining_regions(len(stream), [(r['start'], r['end']) for r in checked], boundaries)
    unhandled = []
    for offset, words in decoded:
        if not any(start <= offset < end for start, end in gaps):
            continue
        count = command_count(words[0])
        try:
            family = list(families(words[0]))
        except UnsupportedLayout:
            family = None
        unhandled.append(dict(start=offset, end=offset+2*len(words), header=words[0],
                              base_controls=words[1:1+count], structural_families=family,
                              pool_range=[offset+2*(1+count), offset+2*len(words)],
                              pool_roles='unadmitted for whole-program execution'))
    return dict(logical_length=len(stream), exact_checked_fragment_regions=checked,
                remaining_regions=gaps, unhandled_packets=unhandled,
                unresolved_family_headers=sorted({r['header'] for r in unhandled if r['structural_families'] is None}),
                complete_program_executable=False,
                execution_blockers=['Remaining packet controls/pool roles are not all semantically admitted.',
                                    'Entry/mute/return execution contract remains unproved.',
                                    'History initialization, circular indexing and parameter/memory ABI need explicit models.',
                                    'Native-reference arithmetic is not calibrated BMC numeric or issue behavior.'])


def study():
    import lib
    import parse
    if hashlib.sha256(lib.Z).hexdigest() != NATIVE_SHA256:
        raise ValueError('Expected recorded ZENOLOGY arm64 image')
    paired = {}
    for cls, (defaults, driver, lists) in lib.pairs().items():
        render = [item for item in lists or [] if item[1] == 0]
        if not render:
            continue
        if len(render) != 1:
            raise ValueError('This selector requires one render list per paired class')
        verify_list(lib.Z, render[0])
        paired[cls] = (defaults, driver, render[0])
    shortest = sorted((max(s[1] for s in item[3]), cls) for cls, (_, _, item) in paired.items())[:7]
    rows = []
    for cls in SHORTLIST:
        defaults, driver, item = paired[cls]
        primary = max(item[3], key=lambda segment: segment[1])
        stream = segment_stream(lib.Z, primary)
        assessment = assess_stream(cls, stream)
        start, end, native = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
        controls = [dict(pc=i.address, mnemonic=i.mnemonic, operands=i.op_str) for i in native
                    if i.mnemonic in ('b', 'bl', 'blr', 'br', 'cbz', 'cbnz', 'tbz', 'tbnz')
                    or i.mnemonic.startswith('b.')]
        exports = lib.load_exports()
        rows.append(dict(cls=cls, driver_class=driver, program_list=item[0], dsp=item[2] & 255,
                         primary_segment=primary, primary_logical_sha256=hashlib.sha256(stream).hexdigest(),
                         all_render_segments=item[3], native_sample=[start, end],
                         native_init=exports[cls+'::Init()'], native_end=exports[cls+'::EndProc()'],
                         native_control_flow=controls, constructor_default_record_count=len(defaults),
                         default_record_limit='Metadata count, not a history-memory or live-parameter allocation.',
                         **assessment))
    return dict(native_sha256=NATIVE_SHA256, paired_classes_checked=len(paired),
                metadata_only_shortest=[dict(cls=cls, largest_segment_bytes=length) for length, cls in shortest],
                candidates=rows, engineering_priority=['SIM_MFX_LINEDRIVE', 'SIM_MFX_FETDRIVE', 'SIM_MFX_TS808'],
                priority_basis='Exact reusable fragment proofs, straight-line native callbacks, then remaining semantic gaps; not ISA completeness.',
                scope='Five primary native/DSP program pairs. Peer banks and hardware activation remain separate requirements.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Detailed local JSON; omit to print')
    args = parser.parse_args()
    try:
        result = json.dumps(study(), indent=2)+'\n'
        if args.out:
            args.out.write_text(result)
        else:
            print(result, end='')
    except (OSError, ValueError, KeyError, struct.error) as error:
        parser.exit(2, f'{error}\n')
