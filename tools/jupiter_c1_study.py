"""Compare bounded JUPITER-X/Fantom CORE1 routines and enable calls without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

from kernel_abi import read
from qspi_c1 import parse_c1

JUPITER_SHA256 = '9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b'
FANTOM_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def original_span(manifest, address, size):
    if size <= 0:
        raise ValueError('Expected positive source span')
    members = {m['name']: m for m in manifest['members']}
    for region in manifest['regions']:
        delta = address - region['runtime_base']
        if 0 <= delta and delta + size <= region['size']:
            offset = region['source_offset'] + delta
            return dict(member=region['name'], container_offset=offset,
                        member_offset=offset-members[region['name']]['offset'], size=size)
    raise ValueError('Source span is not backed by one original member')


def enable_calls(core, start, veneer):
    """Track only the MOV-defined register arguments in the bounded five-call suffix."""
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    registers, calls = {}, []
    for ins in core.md.disasm(read(core, start+0x20, 0x40), start+0x20):
        if ins.mnemonic in ('mov', 'movs') and len(ins.operands) == 2:
            destination, source = ins.operands
            name = ins.reg_name(destination.reg)
            if destination.type != ARM_OP_REG or name not in ('r0', 'r1', 'r2', 'r3'):
                raise ValueError('Unsupported enable-call destination')
            if source.type == ARM_OP_IMM:
                registers[name] = source.imm
            elif source.type == ARM_OP_REG and ins.reg_name(source.reg) in registers:
                registers[name] = registers[ins.reg_name(source.reg)]
            else:
                raise ValueError('Unproved enable-call source')
        elif ins.mnemonic in ('bl', 'b.w') and ins.op_str == f'#{veneer:#x}':
            if (ins.mnemonic == 'b.w') != (ins.address == start+0x5c):
                raise ValueError('Enable suffix has an unexpected nonreturning branch')
            if len(registers) != 4:
                raise ValueError('Missing enable-call argument')
            calls.append(dict(pc=ins.address, dsp=registers['r0'], mode=registers['r1'],
                              argument=registers['r2'], event=registers['r3']))
            registers.clear()
        elif (ins.mnemonic, ins.op_str) != ('pop.w', '{r4, lr}'):
            raise ValueError('Unsupported instruction in enable-call suffix')
    if len(calls) != 5:
        raise ValueError('Expected five stock enable calls')
    return calls


def compare(data, fantom):
    if hashlib.sha256(data).hexdigest() != JUPITER_SHA256:
        raise ValueError('Unknown JUPITER-X container identity')
    if hashlib.sha256(fantom.data).hexdigest() != FANTOM_SHA256:
        raise ValueError('Unknown Fantom payload identity')
    from core1 import Core1
    from core1_rtti import trace
    manifest, view = parse_c1(data)
    # Reuse the existing mapper on an ignored temporary analysis view, never an update.
    with tempfile.TemporaryDirectory(prefix='bmc-jupiter-') as folder:
        path = Path(folder)/'analysis-view.bin'
        path.write_bytes(view)
        jupiter = Core1(path)
    if jupiter.eram_offset != manifest['regions'][1]['analysis_offset']:
        raise ValueError('Scatter bootstrap disagrees with explicit split-member mapping')
    try:
        jupiter.offset(0x01100000 + jupiter.eram_offset)
    except ValueError:
        pass
    else:
        raise ValueError('Unbacked ITCM gap was mapped')
    rtti = trace(jupiter, '13CFspMfxRAMCLR')
    if len(rtti['candidates']) != 1 or rtti['candidates'][0]['thumb_callback_candidates'][2] != 0x61064c51:
        raise ValueError('RAMCLR RTTI callback differs')
    matches = []
    for name, faddr, jaddr, length in (
            ('RAMCLR SetAlg body', 0x61056b14, 0x61064c50, 158),
            ('DRAM-IO low23 rewrite', 0x0113383c, 0x011334c0, 14),
            ('Global enable-mask OR body', 0x0112f4a6, 0x0112f126, 14)):
        left, right = read(fantom, faddr, length), read(jupiter, jaddr, length)
        if left != right:
            raise ValueError(f'Exact routine window differs: {name}')
        source = original_span(manifest, jaddr, length)
        if data[source['container_offset']:source['container_offset']+length] != right:
            raise ValueError('Analysis bytes disagree with original member bytes')
        matches.append(dict(name=name, fantom_runtime=faddr, jupiter_runtime=jaddr,
                            fantom_payload_offset=fantom.offset(faddr), jupiter_source=source,
                            length=length, identical=True, sha256=hashlib.sha256(right).hexdigest()))
    from core1_xrefs import veneer_candidates
    from dramio_owner_study import expect
    enable = {}
    for name, core, start, veneer, setter, mask, log, mask_veneer, mask_writer in (
            ('fantom', fantom, 0x610016b0, 0x61076aaa, 0x01130b6c, 0x45c5, 0x610017fc,
             0x61076aa0, 0x0112f4a6),
            ('jupiter', jupiter, 0x610029c8, 0x6108d054, 0x011307ec, 0x4fcf, 0x61002b40,
             0x6108d04a, 0x0112f126)):
        expect(core, start+0xe, 'movw', f'r0, #{mask:#x}')
        expect(core, start+0x12, 'bl', f'#{mask_veneer:#x}')
        if not veneer_candidates(read(core, mask_veneer, 10), mask_veneer, mask_writer):
            raise ValueError('Global enable-mask veneer differs')
        if not veneer_candidates(read(core, veneer, 10), veneer, setter):
            raise ValueError('Enable-call veneer target differs')
        signature = b'void CBmcDspDrv::SetExeMode('
        if read(core, core.u32(setter+0xb4), len(signature)) != signature:
            raise ValueError('Execution setter assertion identity differs')
        text = b'%08d: CORE1_DSPEnable\n\0'
        if read(core, log, len(text)) != text:
            raise ValueError('CORE1 enable log identity differs')
        calls = enable_calls(core, start, veneer)
        mode2_mask = sum(1 << row['dsp'] for row in calls if row['mode'] == 2)
        if (mask & 127) != mode2_mask or ((mask >> 8) & 127) != mode2_mask:
            raise ValueError('Stock mode2/mask correlation differs')
        enable[name] = dict(routine=start, setter=setter, veneer=veneer, calls=calls,
                            global_mask_writer=mask_writer,
                            global_or_mask=mask, mode2_mask=mode2_mask,
                            mode_names_verified=False, safe_halt_verified=False)
    kind, dsp, count, pad, table = struct.unpack('<4BI', read(jupiter, 0x6118ab70, 8))
    if (kind, dsp, count, pad, table) != (1, 5, 11, 0, 0x6118b390):
        raise ValueError('JUPITER-X RAMCLR list identity differs')
    segments = []
    for index in range(count):
        base, length, capacity, source = struct.unpack('<4I', read(jupiter, table+16*index, 16))
        if length not in (0xb8, 0xb0) or length > capacity:
            raise ValueError('Unexpected RAMCLR source bounds')
        words = list(struct.iter_unpack('<II', read(jupiter, source, length)))
        addresses = [a & 0x7fffff for a, b in words]
        companion = words[0][1] >> 20
        stride = addresses[1]-addresses[0]
        if any(a & 0xff800000 != 0x80000000 or b & 0xfffff or b >> 20 != companion
               for a, b in words) or any(a != addresses[0]+i*stride for i, a in enumerate(addresses)):
            raise ValueError('RAMCLR repeated-record shape differs')
        segments.append(dict(index=index, base=base, length=length, capacity=capacity, source=source,
                             records=len(words), first_address_field=addresses[0], stride=stride,
                             companion_high12=companion))
    if (jupiter.u32(0x6118ab78+8)-jupiter.u32(0x6118ab78)) != 0x1900:
        raise ValueError('First-record wait difference changed')
    for core, address, maximum in ((fantom, 0x61056bee, 4), (jupiter, 0x61064d2a, 11)):
        ins = next(core.md.disasm(read(core, address, 2), address))
        if (ins.mnemonic, ins.op_str) != ('cmp', f'r0, #{maximum:#x}' if maximum > 9 else f'r0, #{maximum}'):
            raise ValueError('RAMCLR wait-query segment bound differs')
    # These are local comparison windows, not cross-product ABI or full-function equivalence.
    return dict(container=manifest, rtti=rtti, mapping=dict(itcm_bytes=jupiter.eram_offset,
                eram_base=0x61000000, eram_bytes=len(jupiter.data)-jupiter.eram_offset,
                scatter_records=len(jupiter.scatter()), reset_thumb=jupiter.u32(0x01100004)),
                exact_matches=matches, execution_enable=enable,
                ramclr_list=dict(address=0x6118ab70, header_dsp=dsp,
                segment_count=count, first_record_difference=0x1900, segments=segments),
                execution_ready=False,
                limitations=['Exact windows do not establish common whole functions, routing or firmware compatibility.',
                             'Eleven source segments differ from Fantom four; upper instruction/source semantics remain open.',
                             'No device access, update execution, decryption or hardware clear-coverage proof.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jupiter_c1a', type=Path)
    parser.add_argument('fantom_payload', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    print(json.dumps(compare(args.jupiter_c1a.read_bytes(), Core1(args.fantom_payload)), indent=2))


if __name__ == '__main__':
    main()
