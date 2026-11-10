"""Read-only, build-specific check of the factory-test shell endpoint and its gate."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

QCTEST_SHA256 = 'd87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6'


def direct_callers(code, base, target):
    """Return direct B/BL sites only; indirect references remain unclassified."""
    if len(code) % 4:
        raise ValueError('Expected aligned AArch64 text')
    result = []
    for offset in range(0, len(code), 4):
        word = struct.unpack_from('<I', code, offset)[0]
        if word & 0x7c000000 == 0x14000000:
            displacement = word & 0x3ffffff
            if displacement & 0x2000000:
                displacement -= 1 << 26
            if base + offset + 4*displacement == target:
                result.append(base + offset)
    return result


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
    checks = {
        0x402f10: [('adrp', 'x0, #0x45a000'), ('add', 'x0, x0, #0x2c8'),
                   ('ldr', 'w0, [x0]'), ('cmp', 'w0, #0'), ('cset', 'w0, eq'),
                   ('and', 'w0, w0, #0xff'), ('cmp', 'w0, #0'),
                   ('b.eq', '#0x402f3c'), ('mov', 'w0, #1'),
                   ('bl', '#0x402590'), ('b', '#0x402f10')],
        0x402f3c: [('mov', 'x3, #0'), ('adrp', 'x0, #0x42d000'),
                   ('add', 'x2, x0, #0x670'), ('adrp', 'x0, #0x42d000'),
                   ('add', 'x1, x0, #0x678'), ('adrp', 'x0, #0x42d000'),
                   ('add', 'x0, x0, #0x680'), ('bl', '#0x4024e0')],
        0x402ccc: [('adrp', 'x0, #0x45a000'), ('add', 'x0, x0, #0x2c8'),
                   ('mov', 'w1, #1'), ('str', 'w1, [x0]')],
        0x407fb0: [('cmp', 'w0, #0x3e'), ('b.eq', '#0x407fd0')],
        0x407fd0: [('adrp', 'x0, #0x456000'), ('add', 'x0, x0, #0xedc'),
                   ('ldr', 'w0, [x0]'), ('cmp', 'w0, #3'), ('b.ne', '#0x40813c')],
        0x408004: [('bl', '#0x4026d0'), ('adrp', 'x0, #0x5e4000'),
                   ('add', 'x0, x0, #0x18'), ('bl', '#0x402930'),
                   ('bl', '#0x402c94')],
        0x40752c: [('adrp', 'x0, #0x456000'), ('add', 'x0, x0, #0xedc'),
                   ('ldr', 'w1, [sp, #0x14]'), ('str', 'w1, [x0]')],
    }
    for address, expected in checks.items():
        actual = [(i.mnemonic, i.op_str) for i in md.disasm(read(address, 4*len(expected)), address)]
        if actual != expected:
            raise ValueError(f'Endpoint/gate instruction mismatch at {address:#x}')
    for address, literal in [(0x42d670, b'-l\0'), (0x42d678, b'sh\0'),
                             (0x42d680, b'/bin/sh\0'),
                             (0x42f768, b'/home/root/net.sh %3d\0')]:
        if read(address, len(literal)) != literal:
            raise ValueError('Endpoint string mismatch')
    # Resolve the endpoint import through the ELF relocation, not just its PLT address.
    symbols = elf.get_section_by_name('.dynsym')
    relocations = list(elf.get_section_by_name('.rela.plt').iter_relocations())
    plt = elf.get_section_by_name('.plt')['sh_addr']
    imports = {plt+32+16*i: symbols.get_symbol(r['r_info_sym']).name
               for i, r in enumerate(relocations)}
    if [imports.get(a) for a in (0x4024e0, 0x402590, 0x4026d0, 0x402930)] != ['execl', 'sleep', 'sprintf', 'system']:
        raise ValueError('Unexpected PLT import layout')
    text = elf.get_section_by_name('.text')
    callers = direct_callers(text.data(), text['sh_addr'], 0x40751c)
    if callers != [0x4080d0, 0x408104, 0x408238]:
        raise ValueError('Mode-setter direct caller set changed')
    values = []
    for site in callers:
        rows = list(md.disasm(read(site-8, 8), site-8))
        values.append(int(rows[0].op_str.split('#')[1], 0)
                      if rows[0].mnemonic == 'mov' and rows[0].op_str.startswith('w1, #') else None)
    initial = struct.unpack('<i', read(0x456edc, 4))[0]
    switch_name = struct.unpack('<Q', read(0x456930+0x3e*8, 8))[0]
    if initial != -1 or values != [0, 1, 2] or read(switch_name, 16) != b'SW_DRV_ID_ENTER\0':
        raise ValueError('Mode initialization/caller values/switch name mismatch')
    md.detail = True
    code = list(md.disasm(text.data(), text['sh_addr']))
    if len(code)*4 != len(text.data()):
        raise ValueError('Incomplete text decode')
    page_pairs = []
    for index, ins in enumerate(code):
        if ins.mnemonic != 'adrp' or ins.operands[1].imm != 0x456000:
            continue
        add = code[index+1]
        if (add.mnemonic != 'add' or add.operands[1].reg != ins.operands[0].reg
                or add.operands[2].type != capstone.arm64.ARM64_OP_IMM):
            raise ValueError('Unclassified page-base materialization')
        page_pairs.append((ins.address, 0x456000+add.operands[2].imm))
    mode_refs = [site for site, address in page_pairs if address == 0x456edc]
    if len(page_pairs) != 110 or mode_refs != [0x40752c, 0x407d90, 0x407f1c, 0x407fd0]:
        raise ValueError('Mode reference materializations changed')
    # This is a literal/form scan, not an alias or all-writers analysis.
    for target in (0x456ed8, 0x456edc, 0x40751c):
        if struct.pack('<Q', target) in data:
            raise ValueError('Previously absent raw pointer now present')
    return dict(qctest_sha256=QCTEST_SHA256, shell_call=0x402f58,
                argv=['sh', '-l'], exit_flag=0x45a2c8,
                gate=dict(switch_code=0x3e, switch_name='SW_DRV_ID_ENTER',
                          mode_address=0x456edc, required=3, file_initial=initial,
                          direct_setter_callers=callers, direct_setter_values=values,
                          page_adrp_add_count=len(page_pairs), mode_adrp_sites=mode_refs,
                          all_writers_proven=False),
                side_effect='/home/root/net.sh %3d', activation_proven=False,
                runtime_uid=None, tty_topology=None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('qctest', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.qctest.read_bytes()), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
