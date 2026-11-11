"""Compare original voice resource extents with stock owners; never relocate or upload."""
import hashlib

from bmc_allpass_voice import programs
from bmc_subset import disassemble_fragment
from effect_lifecycle_study import IMAGE_SHA256, OWNERS
from kernel_abi import segment_info


def requirements():
    prefix, allpass, tail = [disassemble_fragment(program) for program in programs()]
    data = sorted(set([prefix['target'], *allpass['sources'], *allpass['targets'],
                       *tail['wet_addresses'], *tail['scratch_addresses']]))
    coefficients = sorted(set(prefix['coefficient_slots']+tail['coefficient_slots']))
    return dict(body_bytes=sum(map(len, programs())), data_indices=data,
                coefficient_indices=coefficients, data_extent=max(data)+1,
                coefficient_extent=max(coefficients)+1)


def fit(owner):
    needed = requirements()
    if any(len(group) != 1 for group in (owner['render'], owner['memories'][0], owner['memories'][6])):
        raise ValueError('Expected one render, enum-0 and enum-6 reservation')
    program, data, coefficients = owner['render'][0], owner['memories'][0][0], owner['memories'][6][0]
    fits = dict(program=needed['body_bytes'] <= program['capacity'] and 0 <= program['base']
                     and program['base']+needed['body_bytes'] <= 2**32,
                data=needed['data_extent'] <= data['length'] and 0 <= data['base']
                     and data['base']+needed['data_extent'] <= 0x800,
                coefficients=needed['coefficient_extent'] <= coefficients['length']
                     and 0 <= coefficients['base'] and coefficients['base']+needed['coefficient_extent'] <= 0x1000)
    return dict(descriptor=owner['address'], dsp=owner['dsp'], program=program,
                enum0=data, enum6=coefficients, requirements=needed, fits=fits,
                body_capacity_fits=all(fits.values()), wrapper_bytes_included=False,
                relocated_program_emitted=False, available_for_custom_voice=False,
                execution_ready=False)


def report(core):
    if hashlib.sha256(core.data).hexdigest() != IMAGE_SHA256:
        raise ValueError('Expected the pinned Fantom BMC0 CORE1 payload')
    return dict(payload_sha256=IMAGE_SHA256,
                owners=[fit(segment_info(core, address)) for address in OWNERS],
                live_ownership_verified=False, execution_ready=False)


if __name__ == '__main__':
    import argparse
    import json
    from core1 import Core1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    args = parser.parse_args()
    print(json.dumps(report(Core1(args.image)), indent=2))
