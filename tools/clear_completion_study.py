"""Read-only, build-pinned audit of the Fantom CORE1 global-clear completion path."""
import argparse
import hashlib
import json
from pathlib import Path

from core1_wait_study import IMAGE_SHA256, expand_initial_data
from dramio_owner_study import expect
from kernel_abi import read


def external_irq(vector_address, thumb_pointer):
    """Decode the vector identity, not the unrelated callback/event number."""
    offset = vector_address - 0x01100000
    if not 64 <= offset < 4*(16+240) or offset % 4 or not 0 <= thumb_pointer <= 0xffffffff or not thumb_pointer & 1:
        raise ValueError('Expected an aligned external vector and a Thumb handler')
    return offset // 4 - 16


def report(core):
    digest = hashlib.sha256(core.data).hexdigest()
    if digest != IMAGE_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')
    for address, mnemonic, operands in (
            (0x0113191e, 'cmp', 'r0, #0x1f'),
            (0x01131920, 'itt', 'lo'),
            (0x01131924, 'str.w', 'r1, [r2, r0, lsl #2]'),
            (0x0112f498, 'movs', 'r0, #0x17'),
            (0x0112f49a, 'bl', '#0x113191e'),
            (0x0112f448, 'orr', 'r1, r1, #1'),
            (0x01131624, 'ldr.w', 'r0, [r4, #0x35c]'),
            (0x0113162a, 'str.w', 'r1, [r4, #0x35c]'),
            (0x01131630, 'str', 'r0, [r1, #0x5c]'),
            (0x01131638, 'str', 'r2, [r1, #0x5c]'),
            (0x0113163e, 'ldr', 'r1, [r1, #0x5c]'),
            (0x01131642, 'it', 'ne'),
            (0x01131644, 'blx', 'r1'), (0x0113164a, 'dsb', 'sy'),
            (0x01130c40, 'movs', 'r0, #0x20'),
            (0x01130d8a, 'strb.w', 'r0, [ip, #0x400]'),
            (0x01130d8e, 'mov.w', 'ip, #0x10000'),
            (0x01130d92, 'str.w', 'ip, [r1, #0x100]'),
            (0x01130e10, 'orn', 'r0, r0, #-0x40000000'),
            (0x01130e18, 'str.w', 'r0, [r1, #0x200]'),
            (0x6102d61c, 'bl', '#0x61077748'),
            (0x6102d8d6, 'bl', '#0x61077752'),
            (0x6102d73a, 'str', 'r4, [r5, #0x50]'),
            (0x6102d73e, 'str', 'r0, [r5, #0x54]'),
            (0x6102d750, 'str', 'r4, [r5, #0x40]'),
            (0x6102d754, 'str', 'r0, [r5, #0x44]'),
            (0x01130b1a, 'add.w', 'r5, r1, r4'),
            (0x01130b1e, 'ittee', 'ne'),
            (0x01130b20, 'str.w', 'r5, [ip, #0x40]'),
            (0x01130b28, 'str.w', 'r5, [ip, #0x50]'),
            (0x01130b5e, 'str.w', 'r5, [r3, r4, lsl #2]')):
        expect(core, address, mnemonic, operands)
    literals = {a: core.u32(a) for a in (
        0x01100180, 0x01131960, 0x0112f830, 0x011318e0, 0x011318e4,
        0x01131070, 0x01131054, 0x01131028, 0x0113102c,
        0x6102da68, 0x6102da6c)}
    if list(literals.values()) != [0x01131621, 0x200a18a4, 0x0112f445,
            0x41100000, 0x200a16b8, 0xe000e050, 0xe000e008,
            0x20084800, 0x41100000, 0xc0020000, 0xc0800000]:
        raise ValueError('Completion/vector/configuration literal mismatch')
    initial_record = next(r for r in core.scatter() if r['destination'] == 0x2008008c)
    initial, _ = expand_initial_data(core.data[core.offset(initial_record['source']):],
                                     initial_record['length'])
    flag = int.from_bytes(initial[0x200847f8-initial_record['destination']:][:4], 'little')
    zero_record = next(r for r in core.scatter() if r['destination'] == 0x20084818)
    if flag or zero_record['handler'] != 0x610000b4 or not (
            zero_record['destination'] <= 0x200a1900 <
            zero_record['destination'] + zero_record['length']):
        raise ValueError('Unexpected initial flag/table allocation')
    spans = [(0x0112f444, 12), (0x01131620, 0x30), (0x01130d86, 16),
             (0x01130814, 0x7e), (0x6102d732, 0x2c), (0x01130b00, 0x6c)]
    return dict(payload_sha256=digest, event=0x17, callback=0x0112f444,
        callback_slot=0x200a18a4+4*0x17, irq=external_irq(0x01100180, literals[0x01100180]),
        vector=0x01100180, handler=0x01131620, status=0x4110035c,
        status_snapshot=0x200a1714, invocation_counter=0x200a1698,
        initial_flag=flag, callback_table_zero_record=zero_record,
        priority_store=dict(address=0xe000e450, value=0x20),
        enable_store=dict(address=0xe000e108, value=1<<16),
        event_mask_or=dict(address=0x41100200, value=0x3fffffff),
        startup_polling_controls=dict(bool0=0xc0020000, bool1=0xc0800000),
        one_address_step_per_32bit_cpu_element=True,
        physical_domain_name_proven=False, bulk_clear_count_unit_proven=False,
        spans=[dict(address=a, file_offset=core.offset(a), length=n,
                    sha256=hashlib.sha256(read(core,a,n)).hexdigest()) for a,n in spans],
        execution_ready=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    print(json.dumps(report(Core1(args.image)), indent=2))
