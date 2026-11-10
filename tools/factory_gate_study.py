"""Bounded static factory-page initialization and dispatch study; never executes qctest."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from qctest_shell_study import QCTEST_SHA256


def literal_pointer_copy(code, read):
    """Summarize only the six-instruction pointer-copy form in this initializer."""
    if len(code) != 6 or [i.mnemonic for i in code] != ['adrp', 'add', 'ldr', 'adrp', 'add', 'str']:
        raise ValueError('Not a literal pointer-copy record')
    first, add1, load, second, add2, store = code
    if (first.op_str.split(',')[0] != 'x0' or second.op_str.split(',')[0] != 'x0'
            or not add1.op_str.startswith('x0, x0, #')
            or not add2.op_str.startswith('x0, x0, #')
            or load.op_str != 'x1, [x0]' or not store.op_str.startswith('x1, [x0')
            or add1.operands[2].shift.value or add2.operands[2].shift.value
            or store.operands[1].mem.index or store.writeback):
        raise ValueError('Unexpected pointer width/register/address form')
    source = first.operands[1].imm + add1.operands[2].imm
    destination = second.operands[1].imm + add2.operands[2].imm + store.operands[1].mem.disp
    return dict(source=source, destination=destination,
                pointer=struct.unpack('<Q', read(source, 8))[0])


def report(data):
    if hashlib.sha256(data).hexdigest() != QCTEST_SHA256:
        raise ValueError('Expected recorded stock v1.08 qctest')
    import capstone
    from elftools.elf.elffile import ELFFile
    elf = ELFFile(io.BytesIO(data))

    def read(address, size):
        for segment in elf.iter_segments():
            start = segment['p_vaddr']
            if (segment['p_type'] == 'PT_LOAD' and start <= address and
                    address+size <= start+segment['p_filesz']):
                offset = segment['p_offset']+address-start
                return data[offset:offset+size]
        raise ValueError('Requested range is not file-backed')

    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True

    def code(address, size):
        rows = list(md.disasm(read(address, size), address))
        if len(rows)*4 != size:
            raise ValueError('Incomplete instruction window')
        return rows

    def check(address, expected):
        if [(i.mnemonic, i.op_str) for i in code(address, len(expected)*4)] != expected:
            raise ValueError(f'Factory dispatch mismatch at {address:#x}')

    copies = [literal_pointer_copy(code(address, 24), read)
              for address in range(0x406f58, 0x407288, 24)]
    pointers = {row['destination']: row['pointer'] for row in copies}
    groups = []
    for index in range(3):
        base, count = struct.unpack('<QQ', read(0x456ea8+16*index, 16))
        entries = []
        for offset in range(count):
            slot = base+16*offset
            name = struct.unpack('<Q', read(slot+8, 8))[0]
            entries.append(dict(object=pointers[slot], name=read(name, 64).split(b'\0')[0].decode()))
        groups.append(dict(index=index, base=base, count=count, entries=entries))
    expected_destinations = {0x5e3f58} | {g['base']+16*i for g in groups for i in range(g['count'])}
    if len(copies) != 34 or set(pointers) != expected_destinations or pointers[0x5e3f58] != 0x5e3f60:
        raise ValueError('Unexpected page-pointer initializer coverage')
    if any(row['destination'] < 0x456ee0 and row['destination']+8 > 0x456edc for row in copies):
        raise ValueError('Initializer overlaps mode')
    vtable = list(struct.unpack('<7Q', read(0x42f790, 56)))
    if vtable != [0x407bec, 0x407c00, 0x407d2c, 0x407d40, 0x407e9c, 0x407eb0, 0x4081b8]:
        raise ValueError('Unexpected introductory-page virtual table')
    if any(entry['object'] == 0x5e3f60 for g in groups for entry in g['entries']):
        raise ValueError('Introductory page unexpectedly appears in a test group')
    init_array = elf.get_section_by_name('.init_array')
    init_values = struct.unpack('<'+str(init_array['sh_size']//8)+'Q', init_array.data())
    if init_values.index(0x407294)+1 != init_values.index(0x407318):
        raise ValueError('Unexpected table/page initializer ordering')
    text = elf.get_section_by_name('.text')
    rows = code(text['sh_addr'], text['sh_size'])
    table_loads = []
    for index, ins in enumerate(rows[:-5]):
        if ins.mnemonic != 'adrp' or ins.op_str != 'x0, #0x456000':
            continue
        window = rows[index:index+6]
        if window[1].op_str != 'x1, x0, #0xea8':
            continue
        shapes = [(i.mnemonic, i.op_str) for i in window]
        if (shapes[1] != ('add', 'x1, x0, #0xea8') or
                shapes[2] not in [('sxtw', 'x0, w2'), ('sxtw', 'x0, w3')] or
                shapes[3:5] != [('lsl', 'x0, x0, #4'), ('add', 'x0, x1, x0')] or
                shapes[5] not in [('ldr', 'x1, [x0]'), ('ldr', 'w0, [x0, #8]')]):
            raise ValueError('Unclassified indexed group-table address use')
        table_loads.append(dict(site=ins.address, field=window[5].operands[1].mem.disp))
    if len(table_loads) != 23 or sum(row['field'] == 8 for row in table_loads) != 5:
        raise ValueError('Indexed table-load coverage changed')
    check(0x40661c, [('adrp', 'x0, #0x5e3000'), ('add', 'x0, x0, #0xf58'),
                     ('str', 'xzr, [x0]'), ('adrp', 'x0, #0x5e3000'),
                     ('add', 'x0, x0, #0xf54'), ('ldr', 'w1, [sp, #0x1c]'), ('str', 'w1, [x0]')])
    for address in (0x407580, 0x4075f8, 0x407608):
        check(address, [('ldr', 'w0, [sp, #0x14]'), ('bl', '#0x406610')])
    check(0x407574, [('cmp', 'w0, #3'), ('b.eq', '#0x407614')])
    check(0x407614, [('nop', ''), ('b', '#0x407620')])
    check(0x406d60, [('adrp', 'x0, #0x5e3000'), ('add', 'x0, x0, #0xf58'),
                     ('ldr', 'x0, [x0]'), ('ldr', 'x0, [x0]'), ('add', 'x0, x0, #0x28'),
                     ('ldr', 'x2, [x0]'), ('ldr', 'x1, [sp, #0x18]'), ('mov', 'x0, x3'), ('blr', 'x2')])
    check(0x406e5c, [('adrp', 'x0, #0x5e3000'), ('add', 'x0, x0, #0xf58'),
                     ('ldr', 'x0, [x0]'), ('ldr', 'x0, [x0]'), ('add', 'x0, x0, #0x30'),
                     ('ldr', 'x3, [x0]'), ('ldr', 'x2, [sp, #0x10]'),
                     ('ldr', 'x1, [sp, #0x18]'), ('mov', 'x0, x4'), ('blr', 'x3')])
    check(0x407d14, [('bl', '#0x4073d8'), ('ldr', 'x0, [sp, #0x18]'), ('str', 'wzr, [x0, #8]')])
    check(0x408230, [('mov', 'w1, #2'), ('ldr', 'x0, [sp, #0x28]'), ('bl', '#0x40751c')])
    imports = {symbol.name for symbol in elf.get_section_by_name('.dynsym').iter_symbols()}
    return dict(qctest_sha256=QCTEST_SHA256, initializer_copies=len(copies),
                intro_pointer=0x5e3f58, intro_object=0x5e3f60, intro_virtual_methods=vtable,
                groups=groups, indexed_group_loads=table_loads,
                setters_leaving_intro=[0, 1, 2], mode3_preserves_intro=True,
                direct_environment_imports=sorted(imports & {'getenv', 'secure_getenv', 'getopt', 'getopt_long'}),
                mode3_activation_proven=False, all_aliases_resolved=False,
                limitations=['Literal initializer summaries use file-backed source pointer values.',
                             'Dispatch proof is for the introductory page and recorded group table.',
                             'No arbitrary alias/indirect-call proof, hardware input or execution observation.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('qctest', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.qctest.read_bytes()), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'{error}\n')
