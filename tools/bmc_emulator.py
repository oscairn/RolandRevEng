"""Functional float reference for exact BMC fragments, not silicon precision.

No device IO, scheduling, history advancement, clipping or unknown operations.
Only complete profiles accepted by bmc_subset may enter the packet interpreter.
"""
import math

from bmc_dsp import command_count, literal, packets
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


def _fma(first, second, addend):
    try:
        return _finite(math.fma(first, second, addend), 'Native-reference FMA result')
    except OverflowError as error:
        raise ValueError('Native-reference FMA exceeds the finite domain') from error


def execute_fragment(program: bytes, data: dict[int, float], coefficients: dict[int, float],
                     io: dict[int, float] | None = None, *, native_literals=None) -> dict:
    """Step a complete supported logical fragment without mutating its inputs."""
    if not isinstance(program, bytes):
        raise ValueError('Program must be logical bytes')
    spec = disassemble_fragment(program)
    literal_values={}
    if native_literals is not None:
        from bmc_dsp import encode_literal
        fields={'resample_drive_pair':(32,56,72),'cascaded_history_pair':(32,56,72,92,116,140),
                'fdrv_output_pair':((38,114),66,78,98,148)}
        expected=fields.get(spec['kind'])
        if expected is None or not isinstance(native_literals,(list,tuple))or len(native_literals)!=len(expected):
            raise ValueError('Native literals require a checked resample/cascade/output coefficient list')
        for locations,value in zip(expected,native_literals,strict=True):
            value=_finite(value,'Native literal')
            for field in locations if isinstance(locations,tuple)else(locations,):
                if encode_literal(value,3)!=program[field:field+3]or program[field:field+3]!=program[field+3:field+6]:
                    raise ValueError('Native literal does not encode to the checked stereo fields')
                literal_values[field]=literal_values[field+3]=value
    native_coefficient_prefix = spec['kind'] in ('coefficient_shift4', 'register_add_mac_pair',
                                                'state_variable_pair', 'stereo_prefilter',
                                                'state_variable_pair_with_output', 'state_variable_recombine_pair',
                                                'state_variable_recombine_pair_with_output',
                                                'state_variable_terminal_pair_with_output', 'resample_drive_pair',
                                                'post_cubic_mix_pair','cascaded_history_pair','fdrv_output_pair')
    if (native_coefficient_prefix or spec['kind'] == 'clipped_half_pair') and not hasattr(math, 'fma'):
        raise ValueError('This native-reference profile requires Python 3.13+ math.fma')
    io_addresses = spec.get('input_addresses', DEFAULT_INPUT_ADDRESSES)
    memory = _values(data, 'data', range(0x800))
    coefs = _values(coefficients, 'coefficients', range(0x1000))
    inputs = _values({} if io is None else io, 'io', io_addresses)
    if spec['kind'] == 'cubic_quad':
        for cell in spec['sources']:
            if cell not in memory or not -1 <= memory[cell] <= 1:
                raise ValueError('Cubic inputs must be provided in the checked [-1,1] domain')
    ports, trace, auxiliary_saved = [None] * 8, [], {}

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
        def pool_literal(index):
            field=offset+2*(1+count)+index
            if field in literal_values:return literal_values[field]
            raw=b''.join(value.to_bytes(2,'big')for value in pool)
            return literal(raw[index:index+3])
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
                elif port in (8, 9, 10, 12, 13, 14, 15):
                    if not 0 <= address < 0x800:
                        raise ValueError('Only data stores below 0x800 are supported')
                    writes[address] = old_value(port - 8)
                else:
                    raise ValueError('Unsupported transfer port')
                continue
            if word in (0x0ca4,0x4da7,0x0ca8,0x4dab,0x0c24,0x4d27):
                destination=0 if word<0x4000 else 4
                factor=pool_literal(word&15)
                if word in (0x0ca4,0x4da7):
                    value=_fma(old_value(destination+2),factor,old_value(destination+2))+old_value(destination)
                elif word in (0x0ca8,0x4dab):
                    value=_fma(old_value(destination+2),factor,-old_value(destination))+old_value(destination+1)
                else:
                    value=_fma(old_value(destination),factor,old_value(destination))+old_value(destination+2)
            elif word in (0x2420,0x6523,0x1426,0x5529):
                destination,source=(word>>12)&7,(word>>6)&7
                factor=pool_literal(word&15)
                value=(old_value(source)*factor if word in (0x2420,0x6523)else
                       _fma(old_value(source),factor,old_value(destination)))
            elif word in (0x0c02,0x4d06):
                destination=0 if word==0x0c02 else 4
                value=old_value(destination)+old_value(destination+2)
            elif word in (0x08c1,0x48c5):
                destination=0 if word==0x08c1 else 4
                value=_fma(old_value(destination),old_value(3),old_value(destination+1))
            elif word in (0x14a8,0x55ab,0x1464,0x5567,0x1424,0x5527):
                destination,source=(word>>12)&7,(word>>6)&7
                index=word&15;factor=pool_literal(index)
                value=(_fma(old_value(source),factor,old_value(destination+1))if words[0]==0x420a else
                       old_value(source)*factor if word in (0x14a8,0x55ab,0x1464,0x5567)
                       else _fma(old_value(source),factor,old_value(destination)))
            elif word in (0x04a4,0x45a7,0x0468,0x456b,0x2466,0x6569):
                destination,source=(word>>12)&7,(word>>6)&7
                raw=b''.join(value.to_bytes(2,'big')for value in pool)
                index=word&15
                factor=literal(raw[index:index+3])
                value=(old_value(source)*factor if words[0]==0x5f0a else
                       _fma(old_value(source),factor,old_value(0 if destination<4 else 4)))
            elif word in (0x24a0,0x65a3):
                from fdrv_post_cubic_study import POST_SCALES
                destination=2 if word==0x24a0 else 6
                # Native constructor policy until silicon literal precision is measured.
                value=old_value(destination)*POST_SCALES[spec['post_scale_literal']]
            elif word in (0x1428,0x552b,0x0424,0x4527):
                destination,source=(word>>12)&7,(word>>6)&7
                index=word&15
                factor=pool_literal(index)
                value=old_value(source)*factor if words[0]==0xb84e else _fma(
                    old_value(source),factor,old_value(1 if destination<4 else 5))
            elif word in (0x0426,0x4529):
                from fdrv_resample_study import DRIVE_SCALES
                destination=0 if word==0x0426 else 4
                # Native constructor double differs from the encoded DSP literal.
                value=old_value(destination)*DRIVE_SCALES[spec['drive_literal']]
            elif word in (0x0403, 0x4503, 0x2443, 0x6547, 0x2410, 0x6510,
                        0x1400, 0x5504, 0x1440, 0x5544, 0x2403, 0x6503,0x2483,0x6583,0x1443,0x5543):
                destination, source, operand = (word >> 12) & 7, (word >> 6) & 7, word & 63
                if operand < 8:
                    factor = old_value(operand)
                elif operand == 0x10:
                    factor = literal(pool[0].to_bytes(2, 'big'))
                else:
                    raise ValueError('Unsupported short-multiply operand')
                value = old_value(source)*factor
            elif word in (0x2e92, 0x6f90):
                destination = 2 if word == 0x2e92 else 6
                value = old_value(destination)
                magnitude = value if value >= 0 else -value
                constant = literal(pool[(word & 15)//2].to_bytes(2, 'big'))
                value = constant-magnitude
            elif word in (0xaf60, 0xef60):
                destination = 2 if word == 0xaf60 else 6
                # The exact state-variable profile contains one balanced pair per port.
                if destination in auxiliary_saved:
                    raise ValueError('Nested auxiliary saves are outside this profile')
                auxiliary_saved[destination] = old_value(destination)
                continue
            elif word in (0xaf61, 0xef61):
                destination = 2 if word == 0xaf61 else 6
                if destination not in auxiliary_saved:
                    raise ValueError('Auxiliary restore lacks the matching save')
                next_ports[destination] = auxiliary_saved.pop(destination)
                continue
            elif word in (0x1c8b, 0x5d8f):
                destination = 1 if word == 0x1c8b else 5
                s = old_value(destination+1)
                if pool[:2] == [0x2001, 0x6005]:
                    value = _fma(s, old_value(3), s)+old_value(destination)
                elif pool[:2] == [0x9000, 0xd004]:
                    value = _fma(s, old_value(3), -old_value(destination))+old_value(destination-1)
                else:
                    raise ValueError('Unsupported state-variable long extension pair')
            elif word in (0x240b, 0x650b) and pool[:2] == [2, 6]:
                destination, main = (2, 0) if word == 0x240b else (6, 4)
                value = _fma(old_value(main), old_value(3), old_value(destination))
            elif word in (0x08c2, 0x48c6, 0x49c6):
                destination = 0 if word == 0x08c2 else 4
                value = _fma(old_value(destination), old_value(3), old_value(destination+2))
            elif word in (0x1c4b, 0x5d4f) and pool == [0x1002, 0x5006]:
                destination = 1 if word == 0x1c4b else 5
                value = _fma(old_value(destination), old_value(3), old_value(destination))+old_value(destination+1)
            elif word in (0x1c42, 0x5d46):
                destination = 1 if word == 0x1c42 else 5
                value = old_value(destination) + old_value(destination+1)
            elif word in (0x1bc1, 0x5bc5):
                destination = 1 if word == 0x1bc1 else 5
                value = _fma(-old_value(destination), old_value(7), old_value(destination))
            elif word in (0x09c1, 0x49c5):
                destination = 0 if word == 0x09c1 else 4
                value = _fma(old_value(destination), old_value(7), old_value(destination+1))
            elif word in (0x044b, 0x454f) and pool[:2] == [0, 4]:
                destination = 0 if word == 0x044b else 4
                # Both possible coefficient ports carry the same value in this exact profile.
                value = _fma(old_value(destination+1), old_value(3), old_value(destination))
            elif word == 0xfdd4:
                destination = 7
                # shortcut: native fixed32 policy until BMC conversion measurements are available.
                value = quantize_native_reference(old_value(7), shift_bits=4)['quantized']
            elif word == 0x0812 and pool == [0x1500, 0x2800, 0x2800, 0xc000 | spec['coefficient_slots'][0]]:
                destination = 0
                value = math.fma(old_value(0), 0.5, old_value(1) * 0.5)
            elif word in (0x2812, 0x6912):
                destination, current = (2, 0) if word == 0x2812 else (6, 4)
                value = math.fma(old_value(current), .5, old_value(destination)*.5)
            elif word in (0x8ed8, 0xaeda, 0xcedc, 0xeede):
                destination = (word >> 12) & 7
                incoming = old_value(destination)
                value = -1.0 if incoming < -1 else min(incoming, 1.0)
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
        if spec['kind'] == 'state_variable_pair':
            trace[-1]['auxiliary_saved'] = auxiliary_saved.copy()
    if auxiliary_saved:
        raise ValueError('Unbalanced auxiliary state at fragment end')
    return dict(ports=ports.copy(), data=memory, trace=trace)
