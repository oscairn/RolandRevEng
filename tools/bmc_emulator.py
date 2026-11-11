"""Functional float reference for exact BMC fragments, not silicon precision.

No device IO, scheduling, history advancement, clipping or unknown operations.
Only complete profiles accepted by bmc_subset may enter the packet interpreter.
"""
import math

from bmc_dsp import command_count, packets
from bmc_subset import DEFAULT_INPUT_ADDRESSES, disassemble_fragment
from line_shaping_study import _float32, quantize_native_reference


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be a finite int or float')
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError(f'{label} exceeds finite float range') from error
    if not math.isfinite(value):
        raise ValueError(f'{label} must be finite')
    return value


def _values(mapping, label, keys):
    if not isinstance(mapping, dict):
        raise ValueError(f'{label} must be a dict')
    result = {}
    for key, value in mapping.items():
        if type(key) is not int or key not in keys:
            raise ValueError(f'Unsupported {label} key')
        result[key] = _finite(value, f'{label} value')
    return result


def execute_fragment(program: bytes, data: dict[int, float], coefficients: dict[int, float],
                     io: dict[int, float] | None = None) -> dict:
    """Step a complete supported logical fragment without mutating its inputs."""
    if not isinstance(program, bytes):
        raise ValueError('Program must be logical bytes')
    spec = disassemble_fragment(program)
    native_coefficient_prefix = spec['kind'] in ('coefficient_shift4', 'register_add_mac_pair')
    if native_coefficient_prefix and not hasattr(math, 'fma'):
        raise ValueError('This native-reference profile requires Python 3.13+ math.fma')
    io_addresses = spec.get('input_addresses', DEFAULT_INPUT_ADDRESSES)
    memory = _values(data, 'data', range(0x800))
    coefs = _values(coefficients, 'coefficients', range(0x1000))
    inputs = _values({} if io is None else io, 'io', io_addresses)
    ports, trace = [None] * 8, []

    def load(address):
        if address in io_addresses:
            source, key, label = inputs, address, 'io'
        elif 0 <= address < 0x800:
            source, key, label = memory, address, 'data'
        elif address >> 12 == 0xc:
            source, key, label = coefs, address & 0xfff, 'coefficient'
        else:
            raise ValueError('Unsupported transfer address/tag')
        if key not in source:
            raise ValueError(f'Missing {label} value at {key:#x}')
        return _float32(source[key]) if native_coefficient_prefix and source is coefs else source[key]

    for offset, words in packets(program):
        count = command_count(words[0])
        controls, pool = words[1:1 + count], words[1 + count:]
        old, next_ports, writes = ports.copy(), ports.copy(), {}

        def old_value(index):
            if old[index] is None:
                raise ValueError(f'Uninitialized port {index} at packet {offset:#x}')
            return old[index]

        for word in controls:
            if word & 0xff0 == 0xfe0 and not word & 1:
                index, port = (word & 15) // 2, word >> 12
                if index >= len(pool):
                    raise ValueError('Transfer operand outside shared pool')
                address = pool[index]
                if port < 8:
                    next_ports[port] = load(address)
                elif port in (8, 9, 12, 13, 15):
                    if not 0 <= address < 0x800:
                        raise ValueError('Only data stores below 0x800 are supported')
                    writes[address] = old_value(port - 8)
                else:
                    raise ValueError('Unsupported transfer port')
                continue
            if word in (0x0403, 0x4503):
                destination = 0 if word == 0x0403 else 4
                value = old_value(destination) * old_value(3)
            elif word in (0x1c42, 0x5d46):
                destination = 1 if word == 0x1c42 else 5
                value = old_value(destination) + old_value(destination+1)
            elif word in (0x044b, 0x454f) and pool[:2] == [0, 4]:
                destination = 0 if word == 0x044b else 4
                # Both possible coefficient ports carry the same value in this exact profile.
                try:
                    value = math.fma(old_value(destination+1), old_value(3), old_value(destination))
                except OverflowError as error:
                    raise ValueError('Add/MAC result exceeds the finite reference domain') from error
            elif word == 0xfdd4:
                destination = 7
                # shortcut: native fixed32 policy until BMC conversion measurements are available.
                value = quantize_native_reference(old_value(7), shift_bits=4)['quantized']
            elif word == 0x0812 and pool == [0x1500, 0x2800, 0x2800, 0xc000 | spec['coefficient_slots'][0]]:
                destination = 0
                value = math.fma(old_value(0), 0.5, old_value(1) * 0.5)
            elif word in (0x080b, 0x490b, 0x0e0b) and pool:
                destination = 4 if word == 0x490b else 0
                form = word, pool[0]
                if form == (0x080b, 0x13c0):
                    value = old_value(0) * old_value(3) + old_value(1) * old_value(7)
                elif form == (0x490b, 0x53c0):
                    value = old_value(4) * old_value(3) + old_value(5) * old_value(7)
                elif form == (0x0e0b, 0x22c1):
                    value = old_value(1) + (old_value(2) - old_value(0)) * old_value(3)
                elif form == (0x0e0b, 0x12c2):
                    value = old_value(2) + (old_value(1) - old_value(0)) * old_value(3)
                else:
                    raise ValueError('Unsupported long-operation extension')
            else:
                raise ValueError('Unsupported arithmetic operation')
            next_ports[destination] = _finite(value, f'Arithmetic result at packet {offset:#x}')
        memory.update(writes)
        ports = next_ports
        trace.append(dict(offset=offset, header=words[0], before=old.copy(),
                          after=next_ports.copy(), writes=writes.copy()))
    return dict(ports=ports.copy(), data=memory, trace=trace)
