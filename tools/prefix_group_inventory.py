"""Bounded static count-2+ literal-group inventory; candidate shape is not ownership."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from line_prefix_study import descriptor, FIRMWARE_SHA256
from parent_control_study import NATIVE_SHA256

PAIRS = ((0x14, 0x17), (0x24, 0x27))


def inventory(data, pointer_size, to_offset=None, to_address=None):
    """Scan aligned static descriptors, keeping all count-byte values 2..255.

    Only file-backed contiguous arrays with known width bytes 2/3/4 qualify.
    Other record metadata is retained, not assigned a segment/flag meaning.
    """
    if pointer_size not in (4, 8):
        raise ValueError('Expected the observed ARM32 or LP64 pointer size')
    to_offset = to_offset or (lambda address: address)
    to_address = to_address or (lambda offset: offset)
    unpack = '<I' if pointer_size == 4 else '<Q'
    candidates, matches = [], []
    for position in range(0, len(data)-3*pointer_size, pointer_size):
        count = data[position+3*pointer_size]
        if count < 2:
            continue
        table = struct.unpack_from(unpack, data, position+2*pointer_size)[0]
        if table % 4:
            continue
        try:
            source, last = to_offset(table), to_offset(table+12*count-1)
        except ValueError:
            continue
        if source < 0 or source+12*count > len(data) or last != source+12*count-1:
            continue
        records = [struct.unpack_from('<III', data, source+12*index) for index in range(count)]
        if any(metadata & 255 not in (2, 3, 4) for _, _, metadata in records):
            continue
        row = dict(symbol=to_address(position), table=table, count=count,
                   header_word=struct.unpack_from(unpack, data, position+pointer_size)[0])
        candidates.append(row)
        fields = {relative for _, relative, _ in records}
        pairs = [list(pair) for pair in PAIRS if set(pair) <= fields]
        if pairs:
            checked = False
            if pointer_size == 8:
                try:
                    descriptor(data, position)
                    checked = True
                except ValueError:
                    pass  # Retain matching candidates outside the prior parser's narrower admission.
            matches.append(dict(**row, pairs=pairs, prior_lp64_parser_accepts=checked,
                                records=[dict(absolute_byte=a, relative_byte=r, metadata=m)
                                         for a, r, m in records], ownership_proven=False))
    return dict(candidate_count=len(candidates), count_histogram=dict(Counter(r['count'] for r in candidates)),
                header_word_histogram=dict(Counter(r['header_word'] for r in candidates)),
                candidates=candidates, matching_groups=matches,
                scope='Aligned static descriptors; pointer at 2*pointer_size, count byte at 3*pointer_size; contiguous 12-byte record arrays with width byte 2/3/4.')


def report(native, core):
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native artifact')
    if hashlib.sha256(core.data).hexdigest() != FIRMWARE_SHA256:
        raise ValueError('Unsupported CORE1 artifact')
    native_result = inventory(native, 8)
    controls = [descriptor(native, address) for address in (0xa16df8, 0xa16e18)]
    catalogued = {row['symbol']: row for row in native_result['candidates']}
    if any(group['count'] != 4 or group['symbol'] not in catalogued for group in controls):
        raise ValueError('Known rational count-4 positive control missing from inventory')
    return dict(native_sha256=NATIVE_SHA256, firmware_sha256=FIRMWARE_SHA256,
                native=native_result, firmware=inventory(core.data, 4, core.offset, core.address),
                native_rational_positive_controls=controls,
                prefix_alias_proven=False,
                limits=['Candidate shape does not prove _CoefSym type, caller ownership or LINE applicability.',
                        'Runtime-built/patched descriptors, independent count-1 writes, encoded pointers, other width/layout forms and other builds are outside this inventory.',
                        'No arbitrary alias, fixed-constant or never-written proof follows from a negative match.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=Path)
    parser.add_argument('core1', type=Path)
    args = parser.parse_args()
    try:
        from core1 import Core1
        print(json.dumps(report(args.native_bin.read_bytes(), Core1(args.core1)), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')
