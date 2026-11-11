"""Inspect CORE1 label-target records and numeric write behavior without device IO."""
import hashlib
import struct

from core1_wait_study import IMAGE_SHA256
from bmc_dsp import swap_words
from kernel_abi import program_list, read, segment_info


def record(raw):
    if not isinstance(raw, bytes) or len(raw) != 6:
        raise ValueError('Expected one six-byte LP32 label record')
    absolute, relative, segment, flags = struct.unpack('<HHBB', raw)
    return dict(absolute=absolute, relative=relative, segment=segment, flags=flags)


def _u32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('Expected unsigned 32-bit register bits')
    return value


def resolve(raw, reservations):
    """Model the observed start-address check; None means a null reservation pointer."""
    item = record(raw)
    if reservations is None:
        return item['absolute']
    if not isinstance(reservations, list) or not 0 <= len(reservations) <= 127:
        raise ValueError('Expected a list representable by the signed reservation count')
    if item['segment'] >= len(reservations):
        raise ValueError('Label segment fails the firmware count check')
    selected = reservations[item['segment']]
    base, capacity = _u32(selected['base']), _u32(selected['capacity'])
    if item['relative'] >= capacity:
        raise ValueError('Label start fails the firmware capacity check')
    return (base+item['relative']) & 0xffffffff


def encode_target(target, width):
    """Model shift and raw data alignment, retaining truncation instead of hiding it."""
    target = _u32(target)
    if target & 1:
        raise ValueError('Firmware label target must be an even byte address')
    if type(width) is not int or width not in (2, 3, 4):
        raise ValueError('Raw literal width must be 2, 3 or 4')
    halfword = target >> 1
    mask = (1 << (8*width))-1
    return dict(byte_target=target, halfword_value=halfword, width=width,
                aligned_raw_data=(halfword << (8*(4-width))) & 0xffffffff,
                logical_field_bytes=(halfword & mask).to_bytes(width, 'big').hex(),
                value_truncated=halfword > mask)


def reference_plan(records, reservations, target):
    """Describe the manager's eligible reference writes; never perform a patch."""
    target = _u32(target)
    if not isinstance(records, list) or len(records) > 255:
        raise ValueError('Expected the label reference list described by one count byte')
    if not records:
        return dict(target_parity_checked=False, patches=[], skipped=[], execution_ready=False)
    if target & 1:
        raise ValueError('Firmware label target must be even before processing references')
    patches, skipped = [], []
    for index, raw in enumerate(records):
        item = record(raw)
        if item['flags'] & 0xf0:
            skipped.append(index)
            continue
        site = resolve(raw, reservations)
        width = item['flags'] & 15
        encoded = encode_target(target, width)
        extent = (item['relative']+width <= reservations[item['segment']]['capacity']
                  if reservations is not None else None)
        patches.append(dict(reference=index, resolved_site=site, effective_literal_address=site & 0x7ffff,
                            address_mask_alias=site != (site & 0x7ffff),
                            full_field_inside_reservation=extent, **encoded))
    return dict(target_parity_checked=True, patches=patches, skipped=skipped, execution_ready=False)


def read_symbol(core, address):
    header = read(core, address, 16)
    pointer, = struct.unpack_from('<I', header, 8)
    count = header[12]
    raw = read(core, pointer, 6*count) if count else b''
    references = [raw[6*index:6*index+6] for index in range(count)]
    return dict(address=address, representative=record(header[:6]),
                reference_table=pointer, reference_count=count,
                references=[record(item) for item in references]), references


def parent_encodings(core):
    """Check five recorded numeric fields; do not infer label ownership or flow."""
    matches = []
    for parent, field, target in (
            (0x610a1f18, 0x2f0, 0x4020),
            (0x610a1f28, 0x1064, 0x8040),
            (0x610a1f28, 0x178c, 0x9040),
            (0x610a1f28, 0x1844, 0xa040),
            (0x610b88f0, 0x10d2, 0x3020)):
        segment = program_list(core, parent)['segments'][0]
        stream = swap_words(read(core, segment['source'], (segment['length']+3) & ~3))
        offset = field-segment['base']
        if not 0 <= offset <= segment['length']-2:
            raise ValueError('Recorded parent field is outside the primary stream')
        encoded = encode_target(target, 2)
        if stream[offset:offset+2].hex() != encoded['logical_field_bytes']:
            raise ValueError('Recorded parent numeric target differs')
        matches.append(dict(parent_list=parent, absolute_field=field, relative_field=offset,
                            **encoded, counted_label_ownership_proven=False))
    return matches


def report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom CORE1 payload')
    from dramio_owner_study import expect
    for anchor in (
            (0x01133390, 'mov', 'r8, r0'), (0x01133392, 'ldrb', 'r0, [r1, #0xc]'),
            (0x01133396, 'mov', 'r5, r1'), (0x0113339a, 'itt', 'eq'),
            (0x011333f4, 'tst.w', 'r2, #1'), (0x011333f8, 'beq', '#0x113340e'),
            (0x0113340e, 'lsrs', 'r1, r2, #1'), (0x01133412, 'str', 'r1, [sp, #4]'),
            (0x01133418, 'mov.w', 'sl, #5'), (0x0113341c, 'mov.w', 'sb, #1'),
            (0x01133428, 'add.w', 'r1, r4, r4, lsl #1'), (0x0113342c, 'ldr', 'r0, [r5, #8]'),
            (0x0113342e, 'add.w', 'r7, sl, r1, lsl #1'), (0x01133432, 'ldrb', 'r2, [r0, r7]'),
            (0x01133434, 'tst.w', 'r2, #0xf0'), (0x01133438, 'bne', '#0x11334c8'),
            (0x0113343e, 'ldrh.w', 'r6, [r0, r1, lsl #1]'),
            (0x01133442, 'ldr.w', 'ip, [r3, #4]'), (0x0113344a, 'beq', '#0x1133494'),
            (0x01133454, 'ldrsb.w', 'r3, [r3, #9]'), (0x01133458, 'ldrb', 'r2, [r0, r2]'),
            (0x0113346c, 'add.w', 'r3, fp, r2, lsl #3'), (0x01133470, 'ldr.w', 'fp, [ip, r3]'),
            (0x01133474, 'movs', 'r3, #2'), (0x01133476, 'add.w', 'r1, r3, r1, lsl #1'),
            (0x0113347a, 'ldrh', 'r0, [r0, r1]'), (0x0113347c, 'cmp', 'fp, r0'),
            (0x01133486, 'bhi', '#0x1133494'), (0x0113349a, 'and', 'fp, r0, #0xf'),
            (0x011334ac, 'strb.w', 'sb, [r7]'), (0x011334b0, 'str.w', 'sb, [sp]'),
            (0x011334bc, 'ldr', 'r0, [r0]'), (0x011334be, 'ldr', 'r3, [sp, #4]'),
            (0x011334c0, 'bl', '#0x112f528'), (0x011334c6, 'strb', 'r0, [r7]'),
            (0x011334e2, 'ldrh', 'r2, [r2]'), (0x0113350c, 'ldrh', 'r1, [r4, #2]'),
            (0x0113352a, 'adds', 'r2, r0, r1'), (0x01133530, 'ldr.w', 'r3, [r0, #0xa4]'),
            (0x0113353a, 'bx', 'r3'),
            (0x0112f540, 'subs', 'r4, r2, #2'), (0x0112f542, 'cmp', 'r4, #3'),
            (0x0112f544, 'blo', '#0x112f554'), (0x0112f554, 'ubfx', 'r1, r1, #0, #0x13'),
            (0x0112f558, 'orr.w', 'r4, r1, r2, lsl #28'),
            (0x0112f56a, 'rsb.w', 'r2, r2, #4'), (0x0112f56e, 'lsls', 'r2, r2, #3'),
            (0x0112f570, 'lsls', 'r3, r2'), (0x0112f576, 'str', 'r3, [r0, #4]')):
        expect(core, *anchor)
    if (core.u32(0x6117647c+0xa4), core.u32(0x6117647c+0xa8), core.u32(0x011337e0)) != (
            0x0113338d, 0x011334d7, 0x2008480c):
        raise ValueError('Label manager/guard anchors differ')
    symbol, references = read_symbol(core, 0x610e7b98)
    owner = segment_info(core, 0x610a1674)
    resolved = resolve(read(core, symbol['address'], 6), owner['render'])
    return dict(payload_sha256=IMAGE_SHA256, unsigned_target_method=0x0113338c,
                label_target_method=0x011334d6, manager_slots=[0xa4, 0xa8],
                record_stride=6, reference_pointer_offset=8, reference_count_offset=12,
                guard_byte=0x2008480c, exclusion_scope='one eligible reference at a time',
                width_values=[2, 3, 4], literal_address_bits=19, target_shift=1,
                firmware_checks_patch_start_only=True, target_width_fit_checked=False,
                fetdrive_entry_symbol=symbol, fetdrive_resolved_entry=resolved,
                fetdrive_target_encoding=encode_target(resolved, 2),
                fetdrive_reference_plan=reference_plan(references, owner['render'], resolved),
                parent_numeric_matches=parent_encodings(core),
                parent_field_ownership_proven=False, saved_return_state_identified=False,
                call_return_semantics_verified=False, execution_ready=False)


if __name__ == '__main__':
    import argparse
    import json
    from core1 import Core1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    args = parser.parse_args()
    try:
        print(json.dumps(report(Core1(args.image)), indent=2))
    except (OSError, ValueError, struct.error) as error:
        parser.exit(2, f'{error}\n')
