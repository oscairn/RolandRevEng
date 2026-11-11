"""Offline CORE1 render-write geometry and completion-state model; no device IO."""
import hashlib

from effect_lifecycle_study import IMAGE_SHA256
from label_target_study import _u32

APERTURES = (0x41480000, 0x41580000, 0x41680000, 0x41780000,
             0x41880000, 0x41980000, 0x41260000)


def write_geometry(dsp, address, byte_count):
    """Model nonwrapping writes with room in an otherwise empty shared DMA list."""
    if type(dsp) is not int or not 0 <= dsp < 7:
        raise ValueError('Expected a render/MDSP index in 0..6')
    address, byte_count = _u32(address), _u32(byte_count)
    if (address | byte_count) & 1:
        raise ValueError('Program byte address and count must be even')
    if address+byte_count > 0x80000:
        raise ValueError('Offline geometry excludes literal-port aliases and window crossing')
    remaining, destination, source = byte_count, address, 0
    steps = []
    if remaining and destination & 2:
        steps.append(dict(kind='raw_head', destination=destination, byte_count=2,
                          source_offset=source, source_read_bytes=2, value_part='low16', alignment=True))
        remaining -= 2
        destination += 2
        source += 4
    if remaining & 2:
        last = ((remaining+3) >> 2)-1
        steps.append(dict(kind='raw_tail', destination=destination+(remaining & ~3), byte_count=2,
                          source_offset=source+4*last, source_read_bytes=4,
                          value_part='high16', alignment=False))
        remaining -= 2
    if remaining:
        kind = 'cpu_copy' if remaining < 64 else 'dma_queue'
        steps.append(dict(kind=kind, destination=destination, byte_count=remaining,
                          source_offset=source, source_read_bytes=remaining))
    descriptors = []
    if remaining >= 64:
        for offset in range(0, remaining, 0xfff*4):
            if len(descriptors) == 32:
                raise ValueError('Write exceeds the empty shared 32-descriptor DMA list')
            descriptors.append(dict(destination=destination+offset, source_offset=source+offset,
                                    byte_count=min(0xfff*4, remaining-offset)))
    prefix = address & 2 if byte_count else 0
    return dict(dsp=dsp, byte_address=address, byte_count=byte_count,
                program_aperture=APERTURES[dsp], logical_source_prefix_bytes=prefix,
                stored_buffer_bytes=(prefix+byte_count+3)&~3,
                actual_source_read_extent=max((step['source_offset']+step['source_read_bytes']
                                              for step in steps), default=0),
                steps=steps, dma_descriptors=descriptors,
                empty_dma_list_assumed=True, source_u32_alignment_required=True,
                execution_exclusion_verified=False, execution_ready=False)


def completion_plan(state, wait, event_flags=0):
    """Describe this helper's control path; a waiting path still needs a real IRQ event."""
    if type(state) is not int or state not in (0, 1, 2) or type(wait) is not bool:
        raise ValueError('Expected state 0/1/2 and boolean wait')
    event_flags = _u32(event_flags)
    if state != 1:
        return dict(starts_queue=False, waits=False, state_on_return=state,
                    event_flags_on_return=event_flags, completion_proven=False)
    return dict(starts_queue=True, waits=wait, state_on_return=0 if wait else 2,
                event_flags_before_start=event_flags & ~4,
                event_flags_on_return=(event_flags & ~4) if wait else None,
                return_requires_new_completion_event=wait, completion_proven=False)


def report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom CORE1 payload')
    from dramio_owner_study import expect
    anchors = (
        (0x0112f5a0, 'orr.w', 'r0, r6, r4'), (0x0112f5a4, 'tst.w', 'r0, #1'),
        (0x0112f5ba, 'ldrb', 'r0, [r5]'), (0x0112f5bc, 'cmp', 'r0, #2'),
        (0x0112f5c6, 'bl', '#0x1134ef2'), (0x0112f5ca, 'cmp', 'r4, #0'),
        (0x0112f5de, 'tst.w', 'r6, #2'), (0x0112f5e8, 'ldrh', 'r0, [r7]'),
        (0x0112f5ea, 'movs', 'r2, #2'), (0x0112f5f2, 'bl', '#0x112f528'),
        (0x0112f5f6, 'subs', 'r4, r4, #2'), (0x0112f5f8, 'adds', 'r6, r6, #2'),
        (0x0112f5fa, 'adds', 'r7, r7, #4'), (0x0112f5fc, 'tst.w', 'r4, #2'),
        (0x0112f606, 'bic', 'r0, r4, #3'), (0x0112f60a, 'adds', 'r1, r0, r6'),
        (0x0112f60c, 'adds', 'r0, r4, #3'), (0x0112f60e, 'mov.w', 'r2, #-1'),
        (0x0112f612, 'add.w', 'r0, r2, r0, lsr #2'),
        (0x0112f61a, 'ldr.w', 'r3, [r7, r0, lsl #2]'),
        (0x0112f620, 'bfc', 'r3, #0, #0x10'), (0x0112f626, 'bl', '#0x112f528'),
        (0x0112f62a, 'subs', 'r4, r4, #2'), (0x0112f62c, 'cmp', 'r4, #0x40'),
        (0x0112f62e, 'blo', '#0x112f666'), (0x0112f662, 'b.w', '#0x112f290'),
        (0x0112f66e, 'lsrs', 'r2, r4, #2'),
        (0x0112f2c8, 'cmp.w', 'ip, #0x20'), (0x0112f2e4, 'cmp.w', 'ip, #0x1000'),
        (0x0112f2ea, 'movw', 'r4, #0xfff'), (0x0112f2f0, 'add.w', 'r2, r7, r3, lsl #4'),
        (0x0112f2fa, 'strd', 'r1, r0, [r2]'), (0x0112f304, 'bfi', 'r5, r4, #0, #0xc'),
        (0x0112f30c, 'orr', 'r5, r5, #0x4000000'),
        (0x0112f312, 'add.w', 'r0, r0, r4, lsl #2'),
        (0x0112f316, 'add.w', 'r1, r1, r4, lsl #2'),
        (0x0112f6aa, 'ldrb', 'r0, [r4]'), (0x0112f6ac, 'cmp', 'r0, #1'),
        (0x0112f6ae, 'it', 'ne'), (0x0112f6b0, 'pop', '{r4, r5, r6, pc}'),
        (0x0112f6b4, 'bic', 'r0, r0, #4'), (0x0112f6ba, 'movs', 'r0, #2'),
        (0x0112f6bc, 'strb', 'r0, [r4]'), (0x0112f6c0, 'bl', '#0x112f3ba'),
        (0x0112f6c4, 'cmp', 'r5, #0'), (0x0112f6c6, 'it', 'eq'), (0x0112f6c8, 'pop', '{r4, r5, r6, pc}'),
        (0x0112f6d6, 'tst', 'r1, r0'), (0x0112f6d8, 'beq', '#0x112f6d4'),
        (0x0112f6dc, 'bic.w', 'r0, r1, r0'), (0x0112f6e2, 'movs', 'r0, #0'),
        (0x0112f6e4, 'strb', 'r0, [r4]'),
        (0x0112f42e, 'ldr', 'r1, [r0, #8]'), (0x0112f430, 'orr', 'r1, r1, #4'),
        (0x0112f434, 'str', 'r1, [r0, #8]'), (0x0112f436, 'bx', 'lr'))
    for anchor in anchors:
        expect(core, *anchor)
    if tuple(core.u32(0x0113a954+4*index) for index in range(7)) != APERTURES:
        raise ValueError('Program aperture table differs')
    if core.u32(0x0112f828) != 0x200847f0 or core.u32(0x0112f858) != 0x0112f42d:
        raise ValueError('DMA state/callback pointers differ')
    return dict(payload_sha256=IMAGE_SHA256, stack_writer=0x0112f582,
                completion_helper=0x0112f6a4, callback=0x0112f42c,
                state_address=0x200847f0, event_offset=8, completion_mask=4,
                start_then_later_wait_drains=False, callback_resets_state=False,
                examples=[write_geometry(4, address, size) for address, size in
                          ((0x4020, 510), (0x4022, 4), (0x4022, 2))],
                state_paths=[dict(initial_state=state, wait=wait, **completion_plan(state, wait))
                             for state in (0, 1, 2) for wait in (False, True)],
                hardware_execution_verified=False, execution_ready=False)


if __name__ == '__main__':
    import argparse
    import json
    from core1 import Core1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    args = parser.parse_args()
    try:
        print(json.dumps(report(Core1(args.image)), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
