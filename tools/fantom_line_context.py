"""Read the verified LINEDRIVE fragments and reservations in the pinned Fantom image."""
import argparse
import hashlib
import json
from pathlib import Path

from bmc_dsp import packets, swap_words
from bmc_subset import disassemble_fragment
from effect_lifecycle_study import IMAGE_SHA256, OWNERS
from emulator_target_study import CHECKED_REGIONS
from kernel_abi import placements, program_list, read, segment_info

LINE_LIST = 0x611084fc


def load_context(core, owner_address):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the recorded Fantom bmc0 CORE1 image')
    if owner_address not in OWNERS:
        raise ValueError('Expected one of the five recorded effect owner descriptors')
    program = program_list(core, LINE_LIST)
    owner = segment_info(core, owner_address)
    placement, = placements(program, owner)
    length = placement['length']
    if length != 0x242:
        raise ValueError('Unexpected LINEDRIVE program length')
    stored = read(core, placement['source'], (length+3) & ~3)
    logical = swap_words(stored)[:length]
    rows = dict(packets(logical))
    boundaries = set(rows) | {length}
    fragments = []
    fragment_report = []
    for kind, offset, size in CHECKED_REGIONS['SIM_MFX_LINEDRIVE']:
        if not {offset, offset+size} <= boundaries:
            raise ValueError('Fragment does not start and end at stock packet boundaries')
        data = logical[offset:offset+size]
        spec = disassemble_fragment(data)
        if spec['kind'] != kind:
            raise ValueError('Unexpected LINEDRIVE profile')
        fragments.append(data)
        fragment_report.append(dict(offset=offset, size=size, sha256=hashlib.sha256(data).hexdigest(),
                                    assignment=spec))

    inputs, left, right, tail = [item['assignment'] for item in fragment_report]
    if inputs['input_addresses'] != tail['input_addresses']:
        raise ValueError('Input and mix slots differ')
    if [left['targets'][4], right['targets'][4]] != tail['wet_addresses']:
        raise ValueError('Allpass outputs do not feed the mix')
    left_data = set(left['sources'] + left['targets'])
    right_data = set(right['sources'] + right['targets'])
    if left_data & right_data or (left_data | right_data) & set(tail['scratch_addresses']):
        raise ValueError('Unexpected alias between LINE stages')
    shape_addresses = []
    live_slots = []
    for chain, history_offset, write_offset in ((left, 0x66, 0x7a), (right, 0xa8, 0xbc)):
        history = rows[history_offset]
        writes = rows[write_offset]
        if (history[:5] != [0x3407, 0x2490, 0x0fe2, 0x3fe4, 0x2d99]
                or writes[:3] != [0x1e05, 0x8fe0, 0x8fe2]
                or history[6] >> 12 != 0xc or writes[3] != chain['sources'][3]):
            raise ValueError('Unexpected smoother address context')
        reads = [history[5], *chain['sources'][1:3], *chain['sources'][4:]]
        previous_writes = [writes[4], *chain['targets'][:4], chain['targets'][5]]
        if reads != [address+1 for address in previous_writes]:
            raise ValueError('Relocated addresses do not match the reference history pairs')
        shape_addresses.append((history[5], writes[4]))
        live_slots.append(history[6] & 0xfff)

    mix_inputs = rows[0x2a]
    factors = rows[0x134]
    if (mix_inputs[:4] != [0x3e07, 0xafe0, 0xbfe2, 0x5fe4]
            or mix_inputs[4:6] != [left['sources'][0], right['sources'][0]]
            or mix_inputs[6] >> 12 != 0xc
            or factors != [0x1e05, 0x8fe0, 0x9fe2, left['sources'][3], right['sources'][3]]):
        raise ValueError('Smoother input or factor context changed')
    live_slots.append(mix_inputs[6] & 0xfff)

    data_addresses = left_data | right_data | set(tail['scratch_addresses'])
    for pair in shape_addresses:
        if set(pair) & data_addresses:
            raise ValueError('Unexpected smoother history alias')
        data_addresses.update(pair)
    for addresses, memory in ((data_addresses, 0), (tail['coefficient_slots'] + live_slots, 6)):
        if not all(any(row['base'] <= address < row['base'] + row['length']
                       for row in owner['memories'][memory]) for address in addresses):
            raise ValueError('Fragment operand outside its recorded owner reservation')

    output_packet = rows[0x232]
    if output_packet[:4] != [0x3d06, 0x00f8, 0x8fe0, 0xcfe2]:
        raise ValueError('Unexpected LINE output context')
    report = dict(payload_sha256=IMAGE_SHA256, list_address=LINE_LIST, owner_descriptor=owner_address,
                  placement=placement, logical_sha256=hashlib.sha256(logical).hexdigest(),
                  reservations=owner['memories'], fragments=fragment_report,
                  checked_fragment_bytes=sum(item['size'] for item in fragment_report),
                  smoother_history=shape_addresses, output_operand_candidates=output_packet[4:],
                  runtime_selection_verified=False, hardware_execution_verified=False)
    return fragments, shape_addresses, report


def compare_readback(expected: bytes, observed: bytes):
    """Compare already normalized logical program bytes for the selected placement."""
    if len(expected) != 0x242 or len(observed) != len(expected):
        raise ValueError('Expected one complete logical LINE segment of 578 bytes')
    differences = [offset for offset, (a, b) in enumerate(zip(expected, observed)) if a != b]
    opening_mute_change = (
        differences == [3] and expected[:4] == bytes.fromhex('0a02ff71')
        and observed[:4] == bytes.fromhex('0a02ff70')
    )
    return dict(exact_match=not differences, opening_mute_change=opening_mute_change,
                different_byte_count=len(differences), first_differences=differences[:16],
                observed_sha256=hashlib.sha256(observed).hexdigest())


def main():
    from core1 import Core1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core1', type=Path)
    parser.add_argument('--owner', type=lambda value: int(value, 0), default=OWNERS[0])
    parser.add_argument('--readback', type=Path, help='Existing capture in logical byte order')
    args = parser.parse_args()
    try:
        core = Core1(args.core1)
        _, _, report = load_context(core, args.owner)
        if args.readback is not None:
            source = report['placement']['source']
            expected = swap_words(read(core, source, 0x244))[:0x242]
            report['readback_comparison'] = compare_readback(expected, args.readback.read_bytes())
        print(json.dumps(report, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
