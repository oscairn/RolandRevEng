"""Read-only, build-pinned CORE1 ROM-reader planning; never patches an image."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PAYLOAD_SHA = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def zero_candidate(data, end, protected_end):
    if not 0 <= protected_end <= end <= len(data):
        raise ValueError('Invalid ITCM/protected bounds')
    start = end
    while start > 0 and data[start - 1] == 0:
        start -= 1
    candidate = (max(start, protected_end) + 3) & ~3
    candidate = min(candidate, end)
    return dict(raw_zero_start=start, candidate_start=candidate, end=end,
                bytes=end - candidate, runtime_ownership_proven=False)


def report(core):
    if hashlib.sha256(core.data).hexdigest() != PAYLOAD_SHA:
        raise ValueError('Unsupported CORE1 build')

    def expect(address, rows):
        offset = core.offset(address)
        actual = list(core.md.disasm(core.data[offset:offset + 4 * len(rows)],
                                     address, count=len(rows)))
        if [(i.mnemonic, i.op_str) for i in actual] != rows:
            raise ValueError(f'Unexpected instructions at {address:#x}')

    expect(0x01102956, [('ldr', 'r0, [sp]'), ('bl', '#0x111ed12')])
    expect(0x0111ed12, [('push', '{r4, lr}'), ('cpsid', 'i'), ('bl', '#0x111f254')])
    expect(0x0111ed20, [('cpsie', 'i'), ('pop', '{r4, pc}')])
    # A pointer-shaped u32 here is actually an ordinary Thumb instruction.
    expect(0x01104208, [('ubfx', 'r1, r1, #0, #0x14')])
    expect(0x01122ae6, [('ldr', 'r0, [pc, #0x300]'), ('b', '#0x1122ad0')])
    expect(0x01122ad0, [('str', 'r0, [r4, #0x30]')])
    if core.u32(0x01122de8) != 0x40001000:
        raise ValueError('Controller-base literal changed')
    copied = [r for r in core.scatter()
              if r['handler'] == 0x61000098 and 0x01100000 <= r['source'] < 0x01140000]
    last = max(copied, key=lambda r: r['source'] + r['length'])
    if (last['source'], last['length'], last['destination']) != (0x0113cf08, 56, 0xe0043000):
        raise ValueError('Protected shared-ring initializer changed')
    region = zero_candidate(core.data, core.eram_offset,
                            core.offset(last['source']) + last['length'])
    return dict(payload_sha256=PAYLOAD_SHA, irq6_word_call=0x01102958,
                ingress_wrapper=0x0111ed12, argument='r0 holds one word by value',
                wrapper_changes_primask=True, protected_copy=last,
                itcm_candidate=region,
                candidate_address=0x01100000 + region['candidate_start'],
                raw_pointer_collision=dict(address=0x01104208, value=core.u32(0x01104208),
                                           interpretation='Thumb UBFX, not a function pointer'),
                peripheral_setup=dict(function=0x01122ab2, selected_controller=0x40001000,
                                      selected_field_offset=0x30, dma_channel_ownership_proven=False),
                next_test='Fixed-constant response through a validated stock output path; no ROM/peripheral reads',
                key_recovered=False, image_modified=False, flash_ready=False,
                limits=['Zero bytes are a placement candidate, not proof of free runtime memory.',
                        'MC-101 hook addresses, DMA channels and scratch addresses are not portable.',
                        'External response routing and Fantom update acceptance still need proof.'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    args = p.parse_args()
    from core1 import Core1
    print(json.dumps(report(Core1(args.image)), indent=2))


if __name__ == '__main__':
    main()
