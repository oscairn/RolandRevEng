"""Inspect constructor-selected DRAM-IO owners and stock clear/counter interfaces offline."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

from dramio_clear_study import FIRMWARE_SHA256, NATIVE_SHA256
from jupiter_c1_study import JUPITER_SHA256
from kernel_abi import read, segment_info
from qspi_c1 import parse_c1

JUPITER_VIEW_SHA256 = '9cb7fdce212675611bbec0592c1dd4c56e43c1a12854e2bd5723debb12a7c7ee'


def expect(core, address, mnemonic, operands):
    ins = next(core.md.disasm(read(core, address, 4), address, count=1))
    if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
        raise ValueError(f'Instruction mismatch at {address:#x}')


def selected_segment(segments, first, count, reservation):
    """Select by the descriptor's first index, never by the instance ordinal."""
    if count != 1 or not 0 <= first < len(segments):
        raise ValueError('Unsupported DRAM-IO segment selection')
    segment = segments[first]
    if (segment['base'] != reservation['base'] or
            segment['capacity'] != reservation['capacity'] or
            not 0 <= segment['length'] <= reservation['capacity']):
        raise ValueError('DRAM-IO segment differs from its reservation')
    return segment


def jupiter_owners(core):
    if hashlib.sha256(core.data).hexdigest() != JUPITER_VIEW_SHA256:
        raise ValueError('Unsupported JUPITER-X analysis view')
    for address, mnemonic, operands in (
            (0x6102e60c, 'movs', 'r4, #0'),
            (0x6102e60e, 'sub.w', 'sb, sl, #0x600'),
            (0x6102e67e, 'add.w', 'r2, r4, r4, lsl #3'),
            (0x6102e682, 'add.w', 'ip, r1, r2, lsl #3'),
            (0x6102e686, 'str.w', 'ip, [r0, #8]'),
            (0x6102e6b8, 'cmp', 'r4, #9'),
            (0x6102e6c0, 'movs', 'r4, #0'),
            (0x6102e6c2, 'subw', 'sb, sl, #0x4ac'),
            (0x6102e73a, 'add.w', 'r2, r4, r4, lsl #3'),
            (0x6102e742, 'add.w', 'r2, r1, r2, lsl #3'),
            (0x6102e748, 'str', 'r2, [r0, #8]'),
            (0x6102e76c, 'cmp', 'r4, #2')):
        expect(core, address, mnemonic, operands)
    if [core.u32(a) for a in (0x6102e9dc, 0x6102ea0c, 0x6102ea10, 0x6102ea28)] != [
            0x200a1e90, 0x610c0d58, 0x200a1fb0, 0x610c0fe0]:
        raise ValueError('Constructor descriptor/storage anchors differ')
    kind, dsp, count, pad, table = struct.unpack('<4BI', read(core, 0x6118ab70, 8))
    if (kind, dsp, count, pad) != (1, 5, 11, 0):
        raise ValueError('Unexpected RAMCLR list')
    segments = [dict(zip(('base', 'length', 'capacity', 'source'),
                         struct.unpack('<4I', read(core, table+16*i, 16)))) for i in range(count)]
    rows = []
    for group, number, descriptor, managers in (('nine', 9, 0x610c0d58, 0x200a1890),
                                               ('two', 2, 0x610c0fe0, 0x200a1b04)):
        for index in range(number):
            address = descriptor + index*0x48
            owner = segment_info(core, address)
            pointer, first, n = struct.unpack('<IBB', read(core, address+0xc, 6))
            base, capacity = struct.unpack('<II', read(core, pointer, 8))
            segment = selected_segment(segments, first, n, dict(base=base, capacity=capacity))
            edm, data2 = owner['memories'][11], owner['memories'][2]
            if len(edm) != 1 or len(data2) != 1:
                raise ValueError('Unsupported owner memory groups')
            pairs = list(struct.iter_unpack('<II', read(core, segment['source'], segment['length'])))
            stride = (pairs[1][0] & 0x7fffff) - (pairs[0][0] & 0x7fffff)
            if any(a & 0x7fffff != edm[0]['base']+i*stride or b >> 20 != data2[0]['base']
                   for i, (a, b) in enumerate(pairs)):
                raise ValueError('RAMCLR record fields disagree with selected owner')
            rows.append(dict(group=group, instance=index, manager_storage=managers+index*0x14,
                descriptor=address, dsp=owner['dsp'], list_index=first, segment=segment,
                enum11=edm[0], enum2=data2[0], records=len(pairs), address_stride=stride,
                render=owner['render']))
    if sorted(r['list_index'] for r in rows) != list(range(11)):
        raise ValueError('Constructor-selected owners do not cover the RAMCLR list once')
    return rows


def fantom_controls(core):
    if hashlib.sha256(core.data).hexdigest() != FIRMWARE_SHA256:
        raise ValueError('Unsupported Fantom payload')
    for address, mnemonic, operands in (
            (0x01130732, 'tst.w', 'r1, #7'), (0x01130748, 'cmp.w', 'r2, #0x100000'),
            (0x0113075e, 'tst.w', 'r1, #8'), (0x011307f2, 'ubfx', 'r0, r0, #0, #0x14'),
            (0x01130800, 'ubfx', 'r0, r0, #0, #0x14'),
            (0x01130856, 'orr.w', 'r1, r8, r6, lsl #28'),
            (0x0113085a, 'orr', 'r1, r1, #0xc0000000'),
            (0x01130874, 'ldr', 'r2, [r0, #8]'),
            (0x0112f448, 'orr', 'r1, r1, #1'),
            (0x0112f498, 'movs', 'r0, #0x17'),
            (0x01133e64, 'b.w', '#0x1130814'),
            (0x6102a232, 'movs', 'r6, #1'), (0x6102a3b4, 'str', 'r6, [sp]'),
            (0x6102a3b8, 'lsls', 'r3, r6, #0x17'),
            (0x6102a3ba, 'movs', 'r2, #0'), (0x6102a3be, 'ldr.w', 'ip, [r1, #0xec]'),
            (0x6102a3c2, 'movs', 'r1, #1')):
        expect(core, address, mnemonic, operands)
    if core.u32(0x6117647c+0xec) != 0x01133e55 or core.u32(0x6117647c+0xf0) != 0x01133e69:
        raise ValueError('Manager clear/busy vtable anchors differ')
    return dict(counter_driver=0x0113071c, counter_getter=0x011307a6,
                counter_width=20, setter_record_alignment=16, getter_record_alignment=8,
                counter_signed_dsp_upper_bound=6, counter_no_explicit_negative_dsp_guard=True,
                counter_alias_tables=[[core.u32(a+4*i) for i in range(6)]
                    for a in (0x0113a9a0, 0x0113a9b8)],
                clear_wrapper=0x01133e54, clear_driver=0x01130814,
                clear_busy_driver=0x01130806, clear_done_flag=0x200847f8,
                clear_callback=0x0112f444, registered_event=0x17,
                bool0_start_control=[0x41100050,0x41100054],
                bool1_start_control=[0x41100040,0x41100044],
                observed_global_caller=dict(address=0x6102a3c4, domain_bool=1,
                    start=0, count=1<<23, completion=1),
                hardware_domain_name_proven=False, hardware_address_unit_proven=False)


def study():
    from core1 import Core1
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1]/'local'))
    data = (corpus/'crossmodel/jupiter-x/MI077_C1A_up.bin').read_bytes()
    if hashlib.sha256(data).hexdigest() != JUPITER_SHA256:
        raise ValueError('Unsupported JUPITER-X container')
    manifest, view = parse_c1(data)
    native = (corpus/'zen_arm64').read_bytes()
    if hashlib.sha256(native).hexdigest() != NATIVE_SHA256:
        raise ValueError('Unsupported native interface artifact')
    if [struct.unpack_from('<Q', native, 0x9e5408+offset)[0]
            for offset in (0x1c8, 0x1d0, 0x1d8, 0x1e0)] != [0xfcf64, 0xfd000, 0xfd0ac, 0xfd0b0]:
        raise ValueError('Native manager interface slots differ')
    with tempfile.TemporaryDirectory(prefix='bmc-dramio-owners-') as directory:
        path = Path(directory)/'analysis-view.bin';path.write_bytes(view)
        jupiter = Core1(path)
    for address, mnemonic, operands in (
            (0x61028942, 'movs', 'r6, #1'), (0x610289b8, 'str', 'r6, [sp]'),
            (0x610289bc, 'lsls', 'r3, r6, #0x16'), (0x610289be, 'movs', 'r2, #0'),
            (0x610289c2, 'ldr.w', 'ip, [r1, #0xec]'), (0x610289c6, 'movs', 'r1, #1')):
        expect(jupiter, address, mnemonic, operands)
    return dict(jupiter_container_sha256=manifest['container_sha256'],
                native_sha256=NATIVE_SHA256,
                jupiter_owners=jupiter_owners(jupiter),
                jupiter_global_caller=dict(address=0x610289c8, domain_bool=1,
                    start=0, count=1<<22, completion=1),
                fantom=fantom_controls(Core1(corpus/'b0c1a.bin')),
                execution_ready=False,
                limits=['Constructor-selected ownership is static; later owner changes and physical routing remain open.',
                        'Companion-high12/enum2 matching is not a hardware source opcode proof.',
                        'Counter progression, hardware clear domains/units and selective-reset safety remain unproved.'])


if __name__ == '__main__':
    result = study()
    path = Path(__file__).resolve().parents[1]/'local/dramio-owner-study.json'
    path.write_text(json.dumps(result, indent=2)+'\n')
    print('11 constructor-selected owners; separate counter/clear contracts; no hardware clear-coverage proof')
