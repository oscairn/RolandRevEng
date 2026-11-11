"""Model the stock CORE1 mute-word search offline; never modify firmware or a device."""
import hashlib

from bmc_dsp import command_count, packets, swap_words
from effect_lifecycle_study import IMAGE_SHA256, OWNERS
from kernel_abi import program_list, read, segment_info
from label_target_study import _u32, record


def resolve_entry(raw, reservations):
    """Unlike label-field relocation, SetMuteMode never reads the capacity word."""
    item = record(raw)
    if reservations is None:
        return item['absolute']
    if not isinstance(reservations, list) or not 0 <= len(reservations) <= 127:
        raise ValueError('Expected a signed-byte-sized reservation list or null pointer')
    if item['segment'] >= len(reservations):
        raise ValueError('Mute label segment fails the firmware count check')
    return (_u32(reservations[item['segment']]['base'])+item['relative']) & 0xffffffff


def scan_first_packet(stream, muted):
    """Describe the first raw-halfword match, including matches in literal payloads."""
    if type(muted) is not bool or not isinstance(stream, bytes):
        raise ValueError('Expected logical bytes and a boolean mute value')
    decoded = packets(stream)
    if len(decoded) != 1:
        raise ValueError('Supply exactly one complete framed first packet')
    _, words = decoded[0]
    if words[0] & 31 != len(words):
        raise ValueError('Firmware raw scan extent differs from compact packet framing')
    count = command_count(words[0])
    for index, value in enumerate(words[1:], 1):
        if value & 0xfffc == 0xff70:
            return dict(packet_words=len(words), scanned_halfwords=index, word_index=index,
                        byte_offset=2*index, original_word=value, replacement_word=0xff70 | muted,
                        role='control' if index <= count else 'payload',
                        raw_width=2, raw_alignment=True, firmware_search_assert=False,
                        hardware_mute_effect_verified=False, execution_ready=False)
    return dict(packet_words=len(words), scanned_halfwords=max(0, len(words)-1),
                word_index=None, firmware_search_assert=True,
                hardware_mute_effect_verified=False, execution_ready=False)


def report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom CORE1 payload')
    from dramio_owner_study import expect
    # These contiguous ranges expose the resolver and search without skipping a capacity check.
    anchors = (
        (0x01133b7a, 'ldr', 'r0, [r5, #8]'), (0x01133b7c, 'ldrh', 'r6, [r4]'),
        (0x01133b7e, 'ldr', 'r2, [r0, #4]'), (0x01133b80, 'cbz', 'r2, #0x1133ba8'),
        (0x01133b82, 'ldrb', 'r1, [r4, #4]'), (0x01133b84, 'ldrsb.w', 'r3, [r0, #9]'),
        (0x01133b88, 'cmp', 'r3, r1'), (0x01133b8a, 'bgt', '#0x1133ba0'),
        (0x01133ba0, 'ldr.w', 'r1, [r2, r1, lsl #3]'), (0x01133ba4, 'ldrh', 'r2, [r4, #2]'),
        (0x01133ba6, 'adds', 'r6, r1, r2'), (0x01133ba8, 'movs', 'r1, #2'),
        (0x01133baa, 'str', 'r1, [sp, #4]'), (0x01133bac, 'mov', 'r2, r1'),
        (0x01133bae, 'ldr', 'r0, [r0]'), (0x01133bb0, 'movs', 'r3, #1'),
        (0x01133bb2, 'mov', 'r1, r6'), (0x01133bb4, 'bl', '#0x112f6e8'),
        (0x01133bb8, 'and', 'sb, r0, #0x1f'), (0x01133bbc, 'movs', 'r4, #1'),
        (0x01133bbe, 'cmp.w', 'sb, #1'), (0x01133bc2, 'it', 'hi'),
        (0x01133bc4, 'movw', 'fp, #0x3fdc'), (0x01133bc8, 'bls', '#0x1133c12'),
        (0x01133bca, 'nop', ''), (0x01133bcc, 'ldr', 'r0, [r5, #8]'),
        (0x01133bce, 'add.w', 'r7, r6, r4, lsl #1'), (0x01133bd2, 'movs', 'r3, #1'),
        (0x01133bd4, 'ldr', 'r0, [r0]'), (0x01133bd6, 'mov', 'r1, r7'),
        (0x01133bd8, 'ldr', 'r2, [sp, #4]'), (0x01133bda, 'bl', '#0x112f6e8'),
        (0x01133bde, 'ubfx', 'r0, r0, #2, #0xe'), (0x01133be2, 'cmp', 'r0, fp'),
        (0x01133be4, 'bne', '#0x1133c0c'), (0x01133be6, 'ldr', 'r0, [sp, #0x10]'),
        (0x01133be8, 'movw', 'r2, #0xff70'), (0x01133bec, 'orr.w', 'r3, r0, r2'),
        (0x01133c0c, 'adds', 'r4, r4, #1'), (0x01133c0e, 'cmp', 'r4, sb'),
        (0x01133c10, 'blo', '#0x1133bcc'), (0x01133c1a, 'bl', '#0x1134ef2'),
        (0x01133bfc, 'bl', '#0x112f528'), (0x01133c00, 'movs', 'r0, #0'),
        (0x01133c02, 'strb.w', 'r0, [r8]'),
        (0x01133c08, 'pop.w', '{r4, r5, r6, r7, r8, sb, sl, fp, pc}'))
    for anchor in anchors:
        expect(core, *anchor)
    if core.u32(0x6117647c+0xe0) != 0x01133b39:
        raise ValueError('Mute manager slot differs')
    label = read(core, 0x610e7b98, 6)
    rows = []
    for owner, segment in zip(OWNERS, program_list(core, 0x610e7b88)['segments'], strict=True):
        reservation = segment_info(core, owner)['render']
        entry = resolve_entry(label, reservation)
        if entry != segment['base']:
            raise ValueError('Mute entry differs from the selected FETDRIVE placement')
        logical = swap_words(read(core, segment['source'], (segment['length']+3)&~3))[:segment['length']]
        first = packets(logical)[0][1]
        stream = b''.join(word.to_bytes(2, 'big') for word in first)
        candidate = scan_first_packet(stream, False)
        if candidate.get('original_word') != 0xff71 or candidate['role'] != 'control':
            raise ValueError('Recorded FETDRIVE first packet differs')
        rows.append(dict(owner=owner, entry=entry, patch_byte_address=(entry+candidate['byte_offset'])&0xffffffff,
                         **candidate))
    return dict(payload_sha256=IMAGE_SHA256, method=0x01133b38, manager_slot=0xe0,
                label_capacity_checked=False, packet_family_checked=False,
                halfword_scan_mask=0xfffc, first_match_only=True,
                fetdrive_placements=rows, live_pc_or_continuation_observed=False,
                hardware_mute_effect_verified=False, execution_ready=False)


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
