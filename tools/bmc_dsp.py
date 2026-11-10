"""Byte-preserving BMC packet tools; this is not a semantic assembler or emulator."""
import argparse
import math
from pathlib import Path
import struct


def swap_words(data):
    """Convert between stored LE32 words and the logical BE byte stream."""
    if len(data) % 4:
        raise ValueError('Stored data must include padding to a complete 32-bit word')
    return b''.join(data[i:i + 4][::-1] for i in range(0, len(data), 4))


def command_count(header):
    """Count base operation words; extension operands remain in the common pool."""
    return 5 + ((header >> 6) & 3) if header & 0x8000 else (header >> 11).bit_length()


def packets(stream):
    """Deterministic observed subset: length includes header, in 16-bit words.

    shortcut: header bit 5 is unexercised in paired render programs, reject it
    until a render-program example establishes its meaning.
    """
    if len(stream) % 2:
        raise ValueError('Program length must be even')
    offset, result = 0, []
    while offset < len(stream):
        header = int.from_bytes(stream[offset:offset + 2], 'big')
        # 0001 and 001f are compact single-word forms, not 1/31-word payloads.
        length = 1 if 0 < header < 32 else header & 31
        if header & 32 or not length or (header < 32 and header not in (1, 31)) or offset + 2 * length > len(stream):
            raise ValueError(f'Unsupported or truncated packet at {offset:#x}: {header:04x}')
        if 1 + command_count(header) > length:
            raise ValueError(f'Control words exceed packet length at {offset:#x}')
        words = list(struct.unpack_from(f'>{length}H', stream, offset))
        result.append((offset, words))
        offset += 2 * length
    return result


def assemble(rows):
    """Reassemble raw packet words, checking the header count and subset."""
    stream = bytearray()
    for words in rows:
        if not words or not words[0] or words[0] & 32 or (words[0] < 32 and words[0] not in (1, 31)):
            raise ValueError('Unsupported packet header')
        length = 1 if words[0] < 32 else words[0] & 31
        if length != len(words):
            raise ValueError('Packet header does not match its word count')
        if 1 + command_count(words[0]) > length:
            raise ValueError('Control words exceed packet length')
        stream.extend(struct.pack(f'>{len(words)}H', *words))
    return bytes(stream)


def literal(data):
    """Decode an explicitly sized literal; CORE1's write API accepts 2/3/4 bytes."""
    if len(data) not in (2, 3, 4):
        raise ValueError('Literal width must be 2, 3 or 4 bytes')
    first = data[0]
    magnitude = int.from_bytes(data, 'big') & ((1 << (8 * len(data) - 3)) - 1)
    exponent = -24 + 4 * ((first >> 5) & 3) + 8 * (3 - len(data))
    return (-1 if first & 128 else 1) * magnitude * 2.0 ** exponent


def encode_literal(value, width):
    """Encode a finite constant with software nearest/ties-to-even quantization.

    This is an assembler policy, not a claim about the hardware float-write port.
    Reject overflow instead of clipping; prefer the finest exponent on equal error.
    """
    if type(width) is not int or width not in (2, 3, 4):
        raise ValueError('Literal width must be 2, 3 or 4 bytes')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Literal value must be a finite number')
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError('Literal value exceeds the representable range') from error
    if not math.isfinite(value):
        raise ValueError('Literal value must be finite')
    magnitude_bits = 8 * width - 3
    limit = (1 << magnitude_bits) - 1
    base_exponent = -24 + 8 * (3 - width)
    if abs(value) > limit * 2.0 ** (base_exponent + 12):
        raise ValueError('Literal value exceeds the representable range')
    choices = []
    for exponent in range(4):
        quantum = 2.0 ** (base_exponent + 4 * exponent)
        magnitude = min(round(abs(value) / quantum), limit)
        bits = ((value < 0 and magnitude != 0) << (8 * width - 1)) | (exponent << magnitude_bits) | magnitude
        encoded = bits.to_bytes(width, 'big')
        choices.append((abs(literal(encoded) - value), exponent, encoded))
    return min(choices)[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--offset', type=lambda s: int(s, 0), default=0)
    parser.add_argument('--length', type=lambda s: int(s, 0))
    parser.add_argument('--stored', action='store_true', help='Input uses swapped LE32 storage')
    args = parser.parse_args()
    data = args.file.read_bytes()
    length = args.length if args.length is not None else len(data) - args.offset
    size = (length + 3) & ~3 if args.stored else length
    if args.offset < 0 or length < 0 or args.offset + size > len(data):
        parser.error('Requested range is outside the file')
    data = data[args.offset:args.offset + size]
    if args.stored:
        data = swap_words(data)[:length]
    for offset, words in packets(data):
        end = 1 + command_count(words[0])
        print(f'{offset:04x}: {words[0]:04x} | ' +
              ' '.join(f'{word:04x}' for word in words[1:end]) + ' | ' +
              ' '.join(f'{word:04x}' for word in words[end:]))


if __name__ == '__main__':
    main()
