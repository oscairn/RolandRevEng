"""Count-1 literal writers for the LINE prefix fields; candidate, not ownership proof.

Static companion to the count>=2 scan in prefix_group_inventory.py and the scoped
LINE study in line_prefix_study.py. It inventories every aligned static descriptor
mentioning program-relative fields 14/17/24/27 in the pinned ZENOLOGY image, follows
code references to the count-1 records, and decodes the bounded straight-line method
that writes relative fields 17 and 27 with one computed double. The asymmetric
JUPITER-X 4822/1940 instance is checked the same way for its unequal fields d0/d3.
No DSP opcode, alias, grouped-write rule or interpreter admission follows.
"""
import argparse
import hashlib
import json
import re
import struct

from parent_control_study import NATIVE_SHA256

LINE_FIELDS = (0x14, 0x17, 0x24, 0x27)
JUPITER_FIELDS = (0xd0, 0xd3)
JUPITER_SHA256 = '9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b'
JUPITER_PATH = 'crossmodel/jupiter-x/MI077_C1A_up.bin'

WRITER = 0x1d1ac8
WRITER_END = 0x1d1b70
WRITER_TABLE = 0x81b678
WRITER_SCALE = 0xb78af0
WRITER_DIVISOR = 32000.0
NATIVE_INVENTORY = (0x9d4e30, 0x9ff988, 0xa1f7b0, 0xa1f7d0, 0xa2e778, 0xa3f560,
                    0xa3f580, 0xa519f0, 0xa51e08, 0xa51e28, 0xa52c30, 0xa54ee8, 0xa70a28)
KNOWN_REFERENCES = {0xa3f560: [0x29a9dc], 0xa3f580: [0x29a9fc, 0x29aa58],
                    0xa51e08: [0x334d84], 0xa51e28: [0x334da0]}
JUPITER_SITES = (0x61135b4c, 0x61135d3c, 0x611660dc, 0x611660ec,
                 0x611bf6f0, 0x61218334, 0x61218364, 0x61236d68)


def mentions(data, pointer_size, to_offset, to_address, fields, min_count=1):
    """Aligned descriptor candidates whose declared records touch any field."""
    unpack = '<I' if pointer_size == 4 else '<Q'
    rows = []
    for position in range(0, len(data)-3*pointer_size, pointer_size):
        count = data[position+3*pointer_size]
        if count < min_count:
            continue
        table = struct.unpack_from(unpack, data, position+2*pointer_size)[0]
        if table % 4:
            continue
        try:
            source = to_offset(table)
        except ValueError:
            continue
        if source < 0 or source+12*count > len(data):
            continue
        records = [struct.unpack_from('<III', data, source+12*index) for index in range(count)]
        if any(metadata & 255 not in (2, 3, 4) for _, _, metadata in records):
            continue
        if not fields & {relative for _, relative, _ in records}:
            continue
        rows.append(dict(symbol=to_address(position), count=count, table=table,
                         records=[dict(absolute_byte=a, relative_byte=r, width=w)
                                  for a, r, w in records]))
    return rows


def code_references(data, target, starts, limit=60000, reach=17):
    """adrp page references resolved by add/ldr inside the same straight-line window."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    page = target & ~0xfff
    hits = []
    for index, start in enumerate(starts[:-1]):
        end = starts[index+1]
        if end-start > limit:
            continue
        window = list(md.disasm(data[start:end], start))
        for position, ins in enumerate(window):
            if ins.mnemonic != 'adrp':
                continue
            ops = ins.op_str.split(', ')
            if len(ops) != 2 or not ops[1].startswith('#') or int(ops[1][1:], 16) != page:
                continue
            reg = ops[0]
            for follow in window[position+1:position+reach]:
                if follow.mnemonic == 'add':
                    parts = follow.op_str.split(', ')
                    if len(parts) == 3 and parts[1] == reg and parts[2].startswith('#'):
                        if page+int(parts[2][1:], 16) == target:
                            hits.append(follow.address)
                        if parts[0] == reg:
                            break
                elif follow.mnemonic == 'ldr' and f'[{reg}' in follow.op_str:
                    found = re.search(r'#(0x[0-9a-f]+)', follow.op_str)
                    if page+(int(found.group(1), 16) if found else 0) == target:
                        hits.append(follow.address)
                    if follow.op_str.split(',')[0].strip() == reg:
                        break
                elif follow.mnemonic in ('b', 'bl', 'ret', 'br', 'blr') or follow.mnemonic.startswith('b.'):
                    break
                elif follow.op_str.split(',')[0].strip() == reg:
                    break
    return hits


WRITER_CHECKS = (
    (12, 'ldr', 'd0, [x9, w8, uxtw #3]'),
    (15, 'ldr', 's1, [x8]'),
    (17, 'scvtf', 'd1, d1'),
    (18, 'fmul', 'd0, d0, d1'),
    (21, 'fmov', 'd1, x8'),
    (22, 'fdiv', 'd0, d0, d1'),
    (23, 'fmov', 'd1, #0.25000000'),
    (24, 'fmul', 'd8, d0, d1'),
    (27, 'ldr', 'x8, [x8, #0xc8]'),
    (29, 'add', 'x1, x1, #0x7b0'),
    (30, 'fmov', 'd0, d8'),
    (31, 'blr', 'x8'),
    (34, 'ldr', 'x2, [x8, #0xc8]'),
    (36, 'add', 'x1, x1, #0x7d0'),
    (37, 'fmov', 'd0, d8'),
    (41, 'br', 'x2'),
)


def writer_shape(data):
    """Decode the bounded straight-line method writing relative 17 and 27."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    rows = [(ins.mnemonic, ins.op_str) for ins in md.disasm(data[WRITER:WRITER_END], WRITER)]
    if len(rows) != 42:
        raise ValueError('Writer method length changed')
    for index, mnemonic, operands in WRITER_CHECKS:
        if rows[index] != (mnemonic, operands):
            raise ValueError(f'Writer instruction {index} changed: {rows[index]!r}')
    if rows[28][1] != 'x1, #0xa1f000' or rows[35][1] != 'x1, #0xa1f000':
        raise ValueError('Writer descriptor pages changed')
    divisor = struct.unpack('<d', struct.pack('<Q', (0x40df << 48) | 0x400000000000))[0]
    if divisor != WRITER_DIVISOR or struct.unpack_from('<i', data, WRITER_SCALE)[0] != 44100:
        raise ValueError('Writer numeric constants changed')
    table = struct.unpack_from('<128d', data, WRITER_TABLE)
    if min(table) != 0.0 or max(table) != 0.775390625 or not all(value == value for value in table):
        raise ValueError('Writer lookup table changed')
    return dict(method=WRITER, end=WRITER_END, table=WRITER_TABLE, scale_int32=44100,
                divisor=WRITER_DIVISOR, post_scale=0.25, table_entries=128,
                table_min=0.0, table_max=0.775390625,
                writes=[dict(relative_byte=0x17, descriptor=0xa1f7b0),
                        dict(relative_byte=0x27, descriptor=0xa1f7d0)],
                same_d8_both_writes=True,
                literal_driver=0xfba10, driver_preserves_d8=True)


def study(native, jupiter=None):
    """Full static report; jupiter is an optional (view bytes, manifest) pair."""
    import lib
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native artifact')
    rows = mentions(native, 8, lambda address: address, lambda offset: offset,
                    set(LINE_FIELDS))
    if [row['symbol'] for row in rows] != list(NATIVE_INVENTORY):
        raise ValueError('Native count>=1 descriptor inventory changed')
    from line_prefix_study import descriptor
    for row in rows:
        if row['count'] == 1:
            descriptor(native, row['symbol'])
    keys = [(row['symbol'], row['count'],
             [(record['relative_byte'], record['width']) for record in row['records']])
            for row in rows if row['symbol'] in (0xa1f7b0, 0xa1f7d0)]
    if keys != [(0xa1f7b0, 1, [(0x17, 3)]), (0xa1f7d0, 1, [(0x27, 3)])]:
        raise ValueError('Prefix 17/27 single-writer records changed')
    references = {symbol: code_references(native, symbol, lib.STARTS)
                  for symbol in (0xa1f7b0, 0xa1f7d0, *KNOWN_REFERENCES)}
    # The two functions larger than the 60000-byte straight-line limit are scanned
    # separately so the reference claim covers the whole image.
    large = [(0x589000, 0x5af838), (0x6b74ec, 0x6d5138)]
    large_references = {symbol: [hit for begin, end in large
                                 for hit in code_references(native, symbol, [begin, end],
                                                            limit=len(native))]
                        for symbol in (0xa1f7b0, 0xa1f7d0)}
    if any(large_references.values()):
        raise ValueError('Large-function reference scan found unexpected references')
    if references[0xa1f7b0] != [0x1d1b3c] or references[0xa1f7d0] != [0x1d1b58]:
        raise ValueError('Prefix 17/27 record references changed')
    if lib.func(0x1d1b3c) != (WRITER, WRITER_END) or lib.func(0x1d1b58) != (WRITER, WRITER_END):
        raise ValueError('Writer method bounds changed')
    if any(references[symbol] != expected for symbol, expected in KNOWN_REFERENCES.items()):
        raise ValueError('Known count-1 control references changed')
    count2_pairs = [row for row in rows if row['count'] >= 2
                    and ({0x14, 0x17} <= {r['relative_byte'] for r in row['records']}
                         or {0x24, 0x27} <= {r['relative_byte'] for r in row['records']})]
    result = dict(native_sha256=NATIVE_SHA256,
                  mentioning=[dict(symbol=row['symbol'], count=row['count'], table=hex(row['table']),
                                   records=row['records']) for row in rows],
                  count2_pair_groups=[row['symbol'] for row in count2_pairs],
                  relative17_27_writers=dict(
                      methods={0x1d1ac8: [0x1d1b3c, 0x1d1b58],
                               0x334d40: [0x334d84, 0x334da0],
                               0x29a9c8: [0x29a9dc, 0x29a9fc, 0x29aa58]},
                      single_writer_for_17_and_27_pair=0x1d1ac8,
                      shape=writer_shape(native)),
                  references={hex(symbol): [hex(a) for a in found]
                              for symbol, found in references.items()},
                  limits=['Method/class ownership, runtime descriptor construction, other programs and other writers are not excluded.',
                          'Count-1 records do not prove a grouped-write relation by themselves.',
                          'The same computed double at both writes relies on callee-saved d8 through the checked driver.',
                          'Static literals are not DSP register addresses; no opcode or port semantics follow.'])
    if jupiter is not None:
        result['jupiter_x'] = jupiter_section(jupiter)
    return result


def jupiter_section(jupiter):
    """Static descriptor facts for the asymmetric JUPITER-X 4822/1940 instance."""
    view, manifest = jupiter
    regions = [(region['runtime_base'], region['analysis_offset'], region['size'])
               for region in manifest['regions']]

    def to_offset(address):
        for base, analysis, size in regions:
            if base <= address < base+size:
                return analysis+address-base
        raise ValueError('Unmapped')

    def to_address(offset):
        for base, analysis, size in regions:
            if analysis <= offset < analysis+size:
                return base+offset-analysis
        raise ValueError('Outside regions')

    found = mentions(view, 4, to_offset, to_address, set(JUPITER_FIELDS))
    if len(found) != len(JUPITER_SITES) or any(row['count'] != 1 for row in found):
        raise ValueError('JUPITER-X d0/d3 descriptor inventory changed')
    if [row['symbol'] for row in found] != list(JUPITER_SITES):
        raise ValueError('JUPITER-X descriptor sites changed')
    asymmetric = [row for row in found if row['symbol'] in (0x61218334, 0x61218364)]
    if [r['relative_byte'] for r in asymmetric[0]['records']] != [0xd0] or \
       [r['relative_byte'] for r in asymmetric[1]['records']] != [0xd3]:
        raise ValueError('Asymmetric instance records changed')
    pair_groups = mentions(view, 4, to_offset, to_address, set(JUPITER_FIELDS), min_count=2)
    if any({0xd0, 0xd3} <= {r['relative_byte'] for r in row['records']} for row in pair_groups):
        raise ValueError('Unexpected count>=2 group for the asymmetric fields')
    return dict(container_sha256=JUPITER_SHA256, path=JUPITER_PATH,
                field_mentions=[dict(symbol=row['symbol'], count=row['count'],
                                     records=row['records']) for row in found],
                asymmetric_instance_sites=[0x61218334, 0x61218364],
                count2_group_containing_d0_d3=False,
                literal_values=[1.0, 0.0],
                hardware_execution_verified=False,
                limits=['Static container facts; no DSP capture or native cutpoint exists here.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_bin', type=argparse.FileType('rb'))
    parser.add_argument('--jupiter-c1a', help='Optional JUPITER-X C1A container path')
    args = parser.parse_args()
    try:
        jupiter = None
        if args.jupiter_c1a:
            from qspi_c1 import read_c1
            manifest, view = read_c1(args.jupiter_c1a)
            jupiter = (view, manifest)
        print(json.dumps(study(args.native_bin.read(), jupiter), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')