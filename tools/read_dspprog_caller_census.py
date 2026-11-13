"""Exhaustive static reference census for ReadDspProg in the CORE1 images; no device IO.

Run 13 found no direct BL/B, no veneer and no stored Thumb pointer for
ReadDspProg and named initializer/scatter tables as the remaining computed-call
paths. This tool closes the census: it additionally scans MOVW/MOVT constructor
pairs, PC-relative ADR forms, every stored ERAM word, the Cortex-M vector table
and the *expanded* compressed initial-data image (RAM vtables), in both pinned
CORE1 payloads. Zero decoder changes; no hardware claim.
"""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

from core1_wait_study import expand_initial_data

# Push encoding {r4, r5, r6, r7, r8, lr} in little-endian Thumb word order.
PUSH_R4R8LR = 0x41f0e92d
TWIN_SIGNATURE = ('push.w', 'mov', 'cmp #7', 'orr r3, r1, r2', 'tst r3, #1')

IMAGES = {
    'b0c1a': ('6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154',
              dict(read_dspprog=0x0112f74c, aperture_table=0x113a954,
                   raw_ports=0x113aa74, dma_state=0x200847f0,
                   dma_state_pool=0x112fc74)),
    'b1c1a': ('c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd',
              dict(read_dspprog=0x0112f394, aperture_table=0x113b1b4,
                   raw_ports=0x113b2d4, dma_state=0x20084774,
                   dma_state_pool=0x112f8bc)),
}
APERTURES = [0x41480000, 0x41580000, 0x41680000, 0x41780000,
             0x41880000, 0x41980000, 0x41260000]
RAW_PORTS = [0x41104700, 0x41105700, 0x41106700, 0x41107700,
             0x41108700, 0x41109700, 0x41102700]


def locate_read_dspprog(core):
    """Find the ReadDspProg twin by build-independent prologue shape."""
    import capstone
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    low = core.data[:core.eram_offset]
    for offset in range(0, len(low) - 4, 2):
        if struct.unpack_from('<I', low, offset)[0] != PUSH_R4R8LR:
            continue
        address = core.address(offset)
        instructions = list(md.disasm(low[offset:offset + 0x40], address))
        for index, ins in enumerate(instructions):
            if (ins.mnemonic.startswith('cmp') and len(ins.operands) == 2
                    and ins.operands[0].type == ARM_OP_REG
                    and md.reg_name(ins.operands[0].reg) == 'r0'
                    and ins.operands[1].type == ARM_OP_IMM
                    and ins.operands[1].imm == 7):
                window = [(y.mnemonic, y.op_str) for y in instructions[index:index + 12]]
                if (any(m in ('orr.w', 'orr') and 'r3, r1, r2' in o for m, o in window)
                        and any(m in ('tst.w', 'tst') and 'r3, #1' in o for m, o in window)):
                    yield address
                break


def movw_movt_pairs(core, target):
    """Every contiguous MOVW/MOVT pair materializing the unmarked target address."""
    import capstone
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    pairs = []
    for base, data in ((0x01100000, core.data[:core.eram_offset]),
                       (0x61000000, core.data[core.eram_offset:])):
        for offset in range(0, len(data) - 9, 2):
            first, _second, third = struct.unpack_from('<3H', data, offset)
            if first & 0xfbf0 != 0xf240 or third & 0xfbf0 != 0xf2c0:
                continue
            instructions = list(md.disasm(data[offset:offset + 8], base + offset))
            if len(instructions) != 2 or [i.mnemonic for i in instructions] != ['movw', 'movt']:
                continue
            low, high = instructions
            if (len(low.operands) == len(high.operands) == 2
                    and low.operands[0].type == high.operands[0].type == ARM_OP_REG
                    and low.operands[0].reg == high.operands[0].reg
                    and low.operands[1].type == high.operands[1].type == ARM_OP_IMM
                    and low.operands[1].imm | (high.operands[1].imm << 16) == target):
                pairs.append(base + offset)
    return pairs


def adr_references(core, target):
    """PC-relative ADD/SUB (ADR) forms computing the target address in place."""
    import capstone
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    hits = []
    # Capstone names the PC-relative T3/T4 forms "addw"/"subw" (the ADR alias)
    # and the wide register forms "add.w"/"sub.w"; accept both spellings.
    for base, data in ((0x01100000, core.data[:core.eram_offset]),
                       (0x61000000, core.data[core.eram_offset:])):
        for offset in range(0, len(data) - 3, 2):
            ins = next(md.disasm(data[offset:offset + 4], base + offset, count=1), None)
            if ins is None or ins.mnemonic not in ('add', 'add.w', 'addw',
                                                   'sub', 'sub.w', 'subw'):
                continue
            operands = ins.operands
            if (len(operands) != 3 or operands[1].type != ARM_OP_REG
                    or md.reg_name(operands[1].reg) != 'pc'
                    or operands[2].type != ARM_OP_IMM):
                continue
            pc = (ins.address + 4) & ~3
            value = pc + operands[2].imm if ins.mnemonic.startswith('add') \
                else pc - operands[2].imm
            if value == target:
                hits.append(ins.address)
    return hits


def expanded_initial_data(core):
    """Decompress the scatter record into 0x2008008c with the verified handler."""
    record = next(r for r in core.scatter() if r['destination'] == 0x2008008c)
    if record['handler'] != 0x6100003c:
        raise ValueError('Expected the verified compressed initial-data handler')
    source = core.offset(record['source'])
    data, consumed = expand_initial_data(core.data[source:source + 0x1f44],
                                         record['length'])
    return record, data, consumed


def census(core, target):
    """Union of every enumerable static reference form for one target."""
    from core1_xrefs import references
    result = references(core, target)
    stored_hits = [core.address(offset)
                   for offset in range(0, len(core.data) - 3, 4)
                   if struct.unpack_from('<I', core.data, offset)[0]
                   in (target, target | 1)]
    record, expanded, consumed = expanded_initial_data(core)
    expanded_hits = [record['destination'] + offset
                     for offset in range(0, len(expanded) - 3, 4)
                     if struct.unpack_from('<I', expanded, offset)[0]
                     in (target, target | 1)]
    return dict(aligned_thumb_pointer_candidates=result['aligned_thumb_pointer_candidates'],
                direct_branch_candidates=result['direct_branch_candidates'],
                movw_movt_bx_candidates=result['movw_movt_bx_candidates'],
                movw_movt_constructor_pairs=[core.address(o) for o in movw_movt_pairs(core, target)],
                adr_references=[core.address(o) for o in adr_references(core, target)],
                stored_word_hits=stored_hits,
                expanded_ram_word_hits=expanded_hits,
                expanded_bytes=len(expanded), compressed_bytes_used=consumed)


def report(core, payload_sha256, addresses):
    """Full two-image census: locate the twin, prove table identity, exhaust references."""
    if hashlib.sha256(core.data).hexdigest() != payload_sha256:
        raise ValueError('Unexpected CORE1 payload digest')
    located = list(locate_read_dspprog(core))
    expected = addresses['read_dspprog']
    if located != [expected]:
        raise ValueError(f'ReadDspProg twin located at {[hex(a) for a in located]}, '
                         f'expected exactly {expected:#x}')
    for index, aperture in enumerate(APERTURES):
        if core.u32(addresses['aperture_table'] + 4 * index) != aperture:
            raise ValueError('Aperture table row differs between the twins')
    if [core.u32(addresses['raw_ports'] + 4 * index) for index in range(7)] != RAW_PORTS:
        raise ValueError('Raw read port table differs between the twins')
    # The twin loads the DMA state byte's address from its own literal pool;
    # the pool word must equal the pinned per-image constant.
    if core.u32(addresses['dma_state_pool']) != addresses['dma_state']:
        raise ValueError('ReadDspProg DMA state byte pool word differs')
    if core.u32(0x01100004) & ~1 == 0:
        raise ValueError('Expected a Thumb reset entry')
    # Liveness anchors: prove each scanner form actually fires in this image so
    # an empty census means "no reference", never "dead scanner".
    if expected == 0x0112f74c:  # b0c1a
        # add.w r6, pc, #0x204 at 0x112e74e computes 0x0112e954 (disassembled
        # this run); the ADR scan must resolve it.
        if adr_references(core, 0x0112e954) != [0x0112e74e]:
            raise ValueError('ADR scanner failed its liveness anchor')
        # The movw/movt pair at 0x1134380 materializes 0x61015b77.
        if movw_movt_pairs(core, 0x61015b77) != [0x1134380]:
            raise ValueError('MOVW/MOVT scanner failed its liveness anchor')
    else:  # b1c1a
        # addw at 0x110165e computes 0x1101a14 (disassembled this run).
        if adr_references(core, 0x01101a14) != [0x0110165e]:
            raise ValueError('ADR scanner failed its liveness anchor')
        # The movw/movt pair at 0x1133ffc materializes 0x61070181.
        if movw_movt_pairs(core, 0x61070181) != [0x1133ffc]:
            raise ValueError('MOVW/MOVT scanner failed its liveness anchor')
    census_result = census(core, expected)
    empty = {key: value for key, value in census_result.items() if isinstance(value, list)}
    if any(empty.values()):
        raise ValueError(f'ReadDspProg reference found: {empty}')
    return dict(payload_sha256=payload_sha256, read_dspprog=expected,
                aperture_table=addresses['aperture_table'],
                raw_ports=addresses['raw_ports'], dma_state_byte=addresses['dma_state'],
                **census_result, callers_found=False, execution_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', choices=sorted(IMAGES),
                        help='Pinned CORE1 payload to census, under BMC_CORPUS_DIR or ./local')
    args = parser.parse_args()
    from core1 import Core1
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', 'local'))
    try:
        payload_sha256, addresses = IMAGES[args.image]
        core = Core1(str(corpus / f'{args.image}.bin'))
        print(json.dumps(report(core, payload_sha256, addresses), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()