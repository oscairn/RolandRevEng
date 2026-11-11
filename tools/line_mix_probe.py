"""Offline prediction for two exact weighted-mix contexts. Hardware unverified."""
import argparse
import json
import math
from pathlib import Path

from bmc_dsp import packets, swap_words
from jupiter_c1_study import JUPITER_SHA256, original_span
from line_mix_variation import LINE_MIX, packet_literals
from qspi_c1 import read_c1


def decode_fantom_mix(fragment):
    """Read the three stock packets after the independently checked stereo load."""
    rows = packets(fragment)
    if [offset for offset, _ in rows] != [0, 12, 28]:
        raise ValueError('Unexpected LINE mix packet boundaries')
    (_, shared), (offset, stereo), (_, stores) = rows
    if (tuple(shared[:3]) != LINE_MIX or stereo[:5] != [0x1008, 0x2424, 0x3467, 4, 4]
            or stores[:4] != [0x3e07, 0xafe0, 0xbfe2, 0x5fe4]
            or not 0 <= stores[4] < stores[5] < 0x800 or stores[6] >> 12 != 0xc):
        raise ValueError('Unexpected LINE mix controls or operands')
    fields = packet_literals(fragment, 0, shared) + packet_literals(fragment, offset, stereo)
    return dict(literal_values=[field['value'] for field in fields], targets=stores[4:6],
                coefficient_slot=stores[6] & 0xfff)


def predict_fantom_mix(left, right, literals):
    """Predict the two stored samples under the candidate port dataflow."""
    mono_left, mono_right, stereo_left, stereo_right = literals
    shared = math.fma(left, mono_left, right * mono_right)
    return math.fma(left, stereo_left, shared), math.fma(right, stereo_right, shared)


def predict_jupiter_mix(fragment, first, second):
    """Predict the B value seen by the successor's co-issued store."""
    rows = packets(fragment)
    if [offset for offset, _ in rows] != [0, 10, 22]:
        raise ValueError('Unexpected JUPITER-X mix packet boundaries')
    (_, loads), (offset, mix), (_, store) = rows
    if (loads[:3] != [0x1e05, 0x0fe0, 0x1fe2] or tuple(mix[:3]) != LINE_MIX
            or store[:4] != [0x1408, 0x5824, 0xcfe2, 0x19c0]
            or len(set([*loads[3:], store[4]])) != 3
            or any(address >> 12 != 2 for address in (*loads[3:], store[4]))):
        raise ValueError('Unexpected JUPITER-X mix controls or operands')
    left, right = (field['value'] for field in packet_literals(fragment, offset, mix))
    return dict(input_addresses=loads[3:], store_address=store[4], literal_values=[left, right],
                predicted_store=math.fma(first, left, second * right))


def jupiter_report(path, first, second):
    if not hasattr(math, 'fma'):
        raise ValueError('This probe requires Python 3.13+ math.fma')
    manifest, view = read_c1(path)
    if manifest['container_sha256'] != JUPITER_SHA256:
        raise ValueError('Expected the recorded JUPITER-X C1A container')
    if not (math.isfinite(first) and math.isfinite(second) and first != second):
        raise ValueError('Use two different, finite sample values')
    results = []
    for base, address in ((0x2020, 0x612155b0), (0x7020, 0x61216c58)):
        source = original_span(manifest, address, 0x16a8)
        region = next(item for item in manifest['regions'] if item['name'] == source['member'])
        start = region['analysis_offset'] + address - region['runtime_base']
        # Start and end rounded to stored 32-bit words before the logical slice.
        fragment = swap_words(view[start + 0xc0:start + 0xe8])[:0x26]
        results.append(dict(base=base, **predict_jupiter_mix(fragment, first, second)))
    return dict(container_sha256=JUPITER_SHA256, input_values=[first, second],
                hardware_execution_verified=False, banks=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jupiter_c1a', type=Path)
    parser.add_argument('--first', type=float, default=0.25)
    parser.add_argument('--second', type=float, default=-0.125)
    args = parser.parse_args()
    try:
        print(json.dumps(jupiter_report(args.jupiter_c1a, args.first, args.second), indent=2, allow_nan=False))
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(2, f'{error}\n')
