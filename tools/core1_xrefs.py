"""Read-only Thumb branch/veneer candidates; image bytes alone do not prove code reachability."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from core1_rtti import word_refs


def branch_candidates(data, address, target):
    """Decode immediate BL/B forms at every halfword, including possible data matches."""
    import capstone
    from capstone.arm import ARM_OP_IMM
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    rows = []
    for offset in range(0, len(data) - 1, 2):
        first = struct.unpack_from('<H', data, offset)[0]
        if first & 0xf800 not in (0xe000, 0xf000):
            continue
        ins = next(md.disasm(data[offset:offset + 4], address + offset, count=1), None)
        if (ins is not None and ins.mnemonic in ('b', 'b.w', 'bl')
                and len(ins.operands) == 1 and ins.operands[0].type == ARM_OP_IMM
                and ins.operands[0].imm == target & ~1):
            rows.append(dict(address=ins.address, instruction=ins.mnemonic))
    return rows


def veneer_candidates(data, address, target):
    """Recognize only contiguous MOVW/MOVT/BX using the same register and an odd target."""
    import capstone
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_MCLASS)
    md.detail = True
    rows = []
    for offset in range(0, len(data) - 9, 2):
        first, _, third = struct.unpack_from('<3H', data, offset)
        # The third halfword starts MOVT, after the four-byte MOVW.
        if first & 0xfbf0 != 0xf240 or third & 0xfbf0 != 0xf2c0:
            continue
        ins = list(md.disasm(data[offset:offset + 10], address + offset))
        if len(ins) != 3 or [i.mnemonic for i in ins] != ['movw', 'movt', 'bx']:
            continue
        low, high, branch = [i.operands for i in ins]
        if not (len(low) == len(high) == 2 and len(branch) == 1
                and low[0].type == high[0].type == branch[0].type == ARM_OP_REG
                and low[0].reg == high[0].reg == branch[0].reg
                and low[1].type == high[1].type == ARM_OP_IMM):
            continue
        pointer = low[1].imm | (high[1].imm << 16)
        if pointer == target | 1:
            rows.append(dict(address=address + offset, thumb_pointer=pointer))
    return rows


def references(core, target):
    if not 0 <= target <= 0xffffffff:
        raise ValueError('Expected a 32-bit target address')
    regions = ((core.data[:core.eram_offset], 0x01100000),
               (core.data[core.eram_offset:], 0x61000000))
    return dict(target=target & ~1,
                aligned_thumb_pointer_candidates=[core.address(off)
                    for off in word_refs(core.data, target | 1)],
                direct_branch_candidates=[row for data, base in regions
                    for row in branch_candidates(data, base, target)],
                movw_movt_bx_candidates=[row for data, base in regions
                    for row in veneer_candidates(data, base, target)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('target', type=lambda value: int(value, 0))
    args = parser.parse_args()
    from core1 import Core1
    core = Core1(args.image)
    result = references(core, args.target)
    result['payload_sha256'] = hashlib.sha256(core.data).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
