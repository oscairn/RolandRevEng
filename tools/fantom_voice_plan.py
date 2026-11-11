"""Build and verify an offline voice body for recorded Fantom resource layouts."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import bmc_allpass_oscillator as oscillator
import bmc_allpass_voice as voice
from bmc_dsp import command_count, packets, swap_words
from bmc_emulator import execute_fragment
from bmc_subset import assemble_fragment, disassemble_fragment, input_pair
from data_seed_interface_study import float_sources
from effect_lifecycle_study import OWNERS
from fantom_line_context import load_context
from header_study import families
from kernel_abi import segment_info
from line_shaping_study import _finite, _float32
from line_state_study import advance_native_origin, native_ring_index
from voice_owner_fit_study import fit


def transfer_fields(fragments):
    """Read indexed transfer fields only, within the three admitted voice profiles."""
    if [disassemble_fragment(fragment)['kind'] for fragment in fragments] != [
            'coefficient_shift4', 'allpass4', 'dry_wet_tail_with_scratch']:
        raise ValueError('Expected the three original voice profiles')
    stream = b''.join(fragments)
    result = []
    for packet, words in packets(stream):
        count = command_count(words[0])
        for operation, kind in enumerate(families(words[0])):
            if kind != 4:
                continue
            control = words[operation+1]
            if control & 0xff0 != 0xfe0 or control & 1:
                raise ValueError('Expected a proved indexed transfer')
            field = packet+2*(count+1)+(control & 15)
            if field+2 > packet+2*len(words):
                raise ValueError('Transfer field exceeds its packet')
            result.append(dict(packet=packet, field=field, port=control >> 12,
                               address=int.from_bytes(stream[field:field+2], 'big')))
    return result


def required_initial_data(fragments):
    """Read-before-write cells under the admitted profiles' per-packet memory order."""
    fields = transfer_fields(fragments)
    needed, written = set(), set()
    for packet in sorted({field['packet'] for field in fields}):
        current = [field for field in fields if field['packet'] == packet and field['address'] < 0x800]
        needed.update({field['address'] for field in current if field['port'] < 8}-written)
        written.update(field['address'] for field in current if field['port'] >= 8)
    return sorted(needed)


def verify_relocation(fragments, data_base, coefficient_base, inputs):
    """Independently patch transfer fields in original bytes; protect every other byte."""
    if any(type(value) is not int or not 0 <= value < maximum for value, maximum
           in ((data_base, 0x800), (coefficient_base, 0x1000))):
        raise ValueError('Invalid data/coefficient base')
    input_pair(inputs)
    original = voice.programs()
    expected = bytearray(b''.join(original))
    changes = []
    for field in transfer_fields(original):
        address = field['address']
        if address < 0x800:
            relocated, role = data_base+address, 'data'
            if relocated >= 0x800:
                raise ValueError('Relocated data index exceeds the native-policy ring')
        elif address >> 12 == 0xc:
            index = coefficient_base+(address & 0xfff)
            if index >= 0x1000:
                raise ValueError('Relocated coefficient exceeds its tag range')
            relocated, role = 0xc000 | index, 'coefficient'
        elif address in oscillator.PREFIX_SPEC['input_addresses']:
            relocated, role = inputs[oscillator.PREFIX_SPEC['input_addresses'].index(address)], 'input'
        else:
            raise ValueError('Unknown transfer address in original voice')
        expected[field['field']:field['field']+2] = relocated.to_bytes(2, 'big')
        changes.append(dict(**field, relocated=relocated, role=role))
    transfer_fields(fragments)
    if b''.join(fragments) != bytes(expected):
        raise ValueError('Relocated body differs from independent transfer-field substitution')
    return changes


def build_plan(core, owner_address, frequency=440, gain=0.5, amplitude=0.25):
    if type(owner_address) is not int:
        raise ValueError('Expected an integer owner descriptor address')
    _, _, stock = load_context(core, owner_address)
    resources = fit(segment_info(core, owner_address))
    if not resources['body_capacity_fits']:
        raise ValueError('Voice body exceeds the recorded owner capacities')
    data_base, coefficient_base = resources['enum0']['base'], resources['enum6']['base']
    inputs = stock['fragments'][0]['assignment']['input_addresses']
    specs = [disassemble_fragment(fragment) for fragment in voice.programs()]
    for spec in specs:
        if spec['kind'] != 'allpass4':
            spec['input_addresses'] = inputs.copy()
        for key in ('target', 'sources', 'targets', 'wet_addresses', 'scratch_addresses'):
            if key in spec:
                value = spec[key]
                spec[key] = [data_base+index for index in value] if isinstance(value, list) else data_base+value
        if 'coefficient_slots' in spec:
            spec['coefficient_slots'] = [coefficient_base+slot for slot in spec['coefficient_slots']]
    fragments = tuple(assemble_fragment(spec) for spec in specs)
    changes = verify_relocation(fragments, data_base, coefficient_base, inputs)
    _, coefficients, seed = oscillator.initialize(frequency, amplitude)
    gain = _finite(gain)
    if not 0 <= gain <= 1:
        raise ValueError('Expected gain in 0..1')
    coefficients.update({2: 0.0, 3: _float32(gain), 4: 1.0, 5: 1.0})
    coefficients = {coefficient_base+index: value for index, value in coefficients.items()}
    initial_data = {data_base+index: value for index, value in seed['initial_data'].items()}
    needed = required_initial_data(fragments)
    if sorted(initial_data) != needed:
        raise ValueError('Seed manifest differs from proved read-before-write dependencies')
    logical = b''.join(fragments)
    result = dict(payload_sha256=stock['payload_sha256'], owner_descriptor=owner_address,
                  dsp=resources['dsp'], stock_placement=stock['placement'],
                  render_reservation=resources['program'], enum0=resources['enum0'], enum6=resources['enum6'],
                  stock_input_pair=inputs, stock_output_operand_candidates=stock['output_operand_candidates'],
                  specs=specs, fragment_sizes=list(map(len, fragments)), body_bytes=len(logical),
                  logical_sha256=hashlib.sha256(logical).hexdigest(),
                  stored_sha256=hashlib.sha256(swap_words(logical)).hexdigest(),
                  address_changes=changes, non_address_bytes_verified=True,
                  initial_data=initial_data, required_initial_data=needed, coefficients=coefficients,
                  cpu_float32_data_sources=float_sources(initial_data),
                  cpu_float32_coefficient_sources=[dict(coefficient_index=index, requested=value,
                      source_float32=_float32(value), cpu_little_endian_bytes=struct.pack('<f', _float32(value)).hex())
                      for index, value in sorted(coefficients.items())],
                  requested_frequency=frequency, actual_frequency=seed['actual_frequency'],
                  requested_gain=gain, source_gain=_float32(gain),
                  software_sample_rate=48000, wrapper_base=0,
                  state_value_policy='requested native-policy binary64 values; CPU float32 rows are source buffers',
                  relocated_original_body_emitted=True,
                  whole_ring_clear_required_by_model=False, hardware_seed_conversion_verified=False,
                  load_address=None, entry_address=None, return_address=None,
                  wrapper_included=False, output_io_writes_included=False,
                  runtime_ownership_verified=False, hardware_execution_verified=False, execution_ready=False)
    return fragments, result


def render_check(core, owner_address, frames=2056, frequency=440, gain=0.5, amplitude=0.25):
    if type(frames) is not int or not 128 <= frames <= 1000000:
        raise ValueError('Expected 128..1000000 verification frames')
    fragments, result = build_plan(core, owner_address, frequency, gain, amplitude)
    ring = [0.125+index/65536 for index in range(2048)]
    for cell, value in result['initial_data'].items():
        ring[cell] = value
    fields = transfer_fields(fragments)
    destinations = {field['address'] for field in fields if field['port'] >= 8}
    rows, origin = [], 0
    for _ in range(frames):
        for fragment, spec in zip(fragments, result['specs']):
            sources = spec.get('sources', spec.get('wet_addresses', []))
            data = {cell: ring[native_ring_index(cell, 0, origin)] for cell in sources}
            io = {cell: 0.0 for cell in spec.get('input_addresses', [])}
            executed = execute_fragment(fragment, data, result['coefficients'], io)
            for step in executed['trace']:
                for cell, value in step['writes'].items():
                    if cell not in destinations:
                        raise ValueError('Interpreter wrote outside the declared voice destinations')
                    ring[native_ring_index(cell, 0, origin)] = value
        rows.append((executed['ports'][0], executed['ports'][4]))
        origin = advance_native_origin(origin)
    baseline, _ = voice.render(frames, frequency, amplitude, gain)
    for frame, (observed, expected) in enumerate(zip(rows, baseline, strict=True)):
        if [value.hex() for value in observed] != [value.hex() for value in expected]:
            raise ValueError(f'Relocated voice differs from original output at frame {frame}')
    result['reference_check'] = dict(frames=frames, identical_output_values=2*frames,
                                     final_origin=origin, nonseed_background_canaries=True,
                                     native_policy_only=True)
    return fragments, result


def write_plan(output, fragments, result):
    logical = b''.join(fragments)
    if (len(logical) != result['body_bytes'] or hashlib.sha256(logical).hexdigest() != result['logical_sha256']
            or hashlib.sha256(swap_words(logical)).hexdigest() != result['stored_sha256']):
        raise ValueError('Export bytes differ from the verified plan hashes')
    payloads = {'body-logical.bin': logical, 'body-stored.bin': swap_words(logical),
                'manifest.json': (json.dumps(result, indent=2, allow_nan=False)+'\n').encode()}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        with (output/name).open('xb') as stream:
            stream.write(data)


if __name__ == '__main__':
    from core1 import Core1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core1', type=Path)
    parser.add_argument('output', type=Path, help='New directory for original body bytes and manifest')
    parser.add_argument('--owner', type=lambda value: int(value, 0), default=OWNERS[0])
    parser.add_argument('--frequency', type=float, default=440)
    parser.add_argument('--gain', type=float, default=0.5)
    parser.add_argument('--frames', type=int, default=2056)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Refusing to replace an existing output directory')
        fragments, result = render_check(Core1(args.core1), args.owner, args.frames, args.frequency, args.gain)
        write_plan(args.output, fragments, result)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
