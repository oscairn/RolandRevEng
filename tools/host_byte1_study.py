#!/usr/bin/env python3
"""Census message byte-1 stores at pinned mi078 route-call sites.

Static, read-only file analysis of the pinned Fantom-0 v1.08 `mi078` ELF: no
device access, no execution, no capture. For every direct call of the outer
route dispatchers 00be4270 (explicit route argument) and 00be4418 (existing
message byte 2), the scanner walks back over the straight-line block since the
previous branch/call boundary and records:

- the route immediate (last `mov/movz w0, #imm` in the block, 00be4270 only),
- whether the block stored an immediate into message byte 1 (`strb wN, [xM, #1]`
  where xM is the message base register), and that immediate's value.

This checks the wire observation in docs/fantom-host-link-measurements.md that
every frame written to /dev/ttyGS0 carried byte 1 0x00 while earlier studies
cited constructors storing 0x60 there: the stamps are call-site data, not a
send-path rewrite. See docs/host-byte1-study.md.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

HOST_SHA256 = '90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
ROUTE, ROUTE_EXISTING = 0xbe4270, 0xbe4418
BLOCK_LIMIT = 140


def text_section(path):
    from elftools.elf.elffile import ELFFile
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != HOST_SHA256:
        raise ValueError('Expected pinned Fantom-0 v1.08 mi078 ELF')
    elf = ELFFile(io.BytesIO(data))
    text = elf.get_section_by_name('.text')
    return text.data(), text['sh_addr']


def scan(path):
    import capstone
    from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_MEM, ARM64_OP_REG
    data, base = text_section(path)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    rows = list(md.disasm(data, base))

    def reg(index):
        return md.reg_name(index)

    def immediate(ins):
        if ins.mnemonic not in ('mov', 'movz') or len(ins.operands) != 2:
            return None
        destination, source = ins.operands
        if destination.type != ARM64_OP_REG or source.type != ARM64_OP_IMM:
            return None
        return source.imm

    sites = []
    for index, ins in enumerate(rows):
        if ins.mnemonic != 'bl':
            continue
        try:
            target = int(ins.op_str.lstrip('#'), 0)
        except ValueError:
            continue
        if target not in (ROUTE, ROUTE_EXISTING):
            continue
        start = index
        while start > 0 and index - start < BLOCK_LIMIT:
            previous = rows[start - 1]
            if previous.mnemonic in ('bl', 'ret', 'br', 'b', 'cbz', 'cbnz',
                                     'tbz', 'tbnz'):
                break
            start -= 1
        base_register, offset = None, None
        written = {}
        route = None
        byte1 = None
        for member in rows[start:index]:
            operands = member.operands
            value = immediate(member)
            if value is not None:
                name = reg(operands[0].reg)
                if name.startswith('w'):
                    written[name] = value
                if name == 'w0' and target == ROUTE:
                    route = value
            elif (member.mnemonic == 'add' and len(operands) == 3
                  and operands[0].type == ARM64_OP_REG
                  and operands[2].type == ARM64_OP_IMM
                  and reg(operands[0].reg) == 'x1'):
                base_register, offset = reg(operands[1].reg), operands[2].imm
            elif (member.mnemonic == 'mov' and len(operands) == 2
                  and operands[0].type == ARM64_OP_REG
                  and operands[1].type == ARM64_OP_REG
                  and reg(operands[0].reg) == 'x1'):
                base_register, offset = reg(operands[1].reg), 0
            elif (member.mnemonic == 'strb' and len(operands) == 2
                  and operands[1].type == ARM64_OP_MEM):
                memory = operands[1].mem
                if (base_register is not None
                        and reg(memory.base) == base_register
                        and memory.disp == offset + 1):
                    source = reg(operands[0].reg)
                    byte1 = dict(at=member.address, value=written.get(source))
        sites.append(dict(call=ins.address, dispatcher=target, route=route,
                          byte1=byte1))
    return sites


def summarize(sites):
    counts = {}
    for site in sites:
        value = site['byte1']['value'] if site['byte1'] else 'constructor-default'
        if value is None and site['byte1']:
            value = 'non-immediate'
        key = (site['dispatcher'], site['route'], value)
        counts[key] = counts.get(key, 0) + 1
    return [dict(dispatcher=f'{dispatcher:#x}',
                 route=None if route is None else f'{route:#x}',
                 byte1=value, sites=count)
            for (dispatcher, route, value), count
            in sorted(counts.items(), key=lambda item: (-item[-1], str(item[:2])))]


def stamps(sites, route, dispatcher=ROUTE):
    """Byte-1 immediate values observed for one destination route."""
    return sorted({site['byte1']['value'] for site in sites
                   if site['dispatcher'] == dispatcher and site['route'] == route
                   and site['byte1'] and site['byte1']['value'] is not None})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--sites', action='store_true',
                        help='Print every route-call site as JSON lines')
    args = parser.parse_args()
    sites = scan(args.image)
    print(json.dumps(dict(total_route_calls=len(sites), groups=summarize(sites)),
                      indent=2))
    if args.sites:
        for site in sites:
            row = dict(site)
            row['dispatcher'] = f"{site['dispatcher']:#x}"
            row['route'] = None if site['route'] is None else f"{site['route']:#x}"
            print(json.dumps(row))


if __name__ == '__main__':
    main()