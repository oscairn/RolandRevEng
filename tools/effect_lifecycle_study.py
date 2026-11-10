"""Inspect effect reset reservations and parent entry-reference candidates offline."""
import argparse
import hashlib
import json
from pathlib import Path

from bmc_dsp import command_count, packets, swap_words
from kernel_abi import program_list, read, segment_info


IMAGE_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'
OWNERS = (0x610a1674, 0x610a16bc, 0x610a1704, 0x610a174c, 0x610a1d14)
PARENTS = (0x610a1ef8, 0x610a1f08, 0x610a1f18, 0x610a1f28)


def entry_candidates(stream, base, dsp, owners):
    """Find numeric owner-entry matches beside the observed 00a0/00a2 pair.

    This deliberately does not decode either operation's operand or semantics.
    """
    rows = []
    for offset, words in packets(stream):
        n = command_count(words[0])
        controls, pool = words[1:1+n], words[1+n:]
        if not any(controls[i:i+2] == [0x00a0, 0x00a2]
                   for i in range(len(controls)-1)):
            continue
        for owner in owners:
            if owner['dsp'] != dsp:
                continue
            for reservation in owner['render']:
                target = reservation['base']
                for index, value in enumerate(pool):
                    if value * 2 == target:
                        rows.append(dict(packet_address=base+offset,
                                         owner_descriptor=owner['address'],
                                         candidate_entry_byte=target,
                                         pool_halfword_index=index,
                                         pool_value=value))
    return rows


def report(core):
    digest = hashlib.sha256(core.data).hexdigest()
    if digest != IMAGE_SHA256:
        raise ValueError('This build-specific study requires the recorded bmc0 CORE1 image')
    owners = [segment_info(core, address) for address in OWNERS]
    candidates = []
    for address in PARENTS:
        parent = program_list(core, address)
        for segment in parent['segments']:
            length = segment['length']
            if not length:
                continue
            stream = swap_words(read(core, segment['source'], (length+3) & ~3))[:length]
            for row in entry_candidates(stream, segment['base'], parent['header_dsp'], owners):
                candidates.append(dict(parent_list=address, dsp=parent['header_dsp'], **row))
    return dict(payload_sha256=digest,
                coefficient_reservations=[dict(owner_descriptor=o['address'], dsp=o['dsp'],
                    enum6=o['memories'][6]) for o in owners],
                parent_entry_reference_candidates=candidates,
                execution_ready=False,
                limitations=['Numeric references beside 00a0/00a2 are candidates, not decoded calls.',
                             'RAMCLR coefficient zeroing does not establish a complete history reset.',
                             'No device access, relocation, code emission or runtime observation.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(Core1(args.image)), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
