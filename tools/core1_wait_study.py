"""Offline models of the pinned CORE1 wait loop and compressed initial data."""
import argparse
import hashlib
import json
from pathlib import Path

IMAGE_SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'


def u32(value):
    if not isinstance(value, int) or not 0 <= value <= 0xffffffff:
        raise ValueError('Expected unsigned 32-bit register bits')
    return value


def wait_chunks(count, completion):
    """Model arms/waits after the mandatory drain of the previous global flag."""
    remaining, completion = u32(count), u32(completion)
    while remaining:
        chunk = min(remaining, 0xfffe)
        remaining -= chunk
        yield dict(count=chunk, wait=bool(completion or remaining))


def scaled_count(argument):
    """MULS low 32 bits followed by SDIV by 1000, returned as register bits."""
    product = (u32(argument) * 48000) & 0xffffffff
    signed = product if product < 0x80000000 else product - 0x100000000
    quotient = (abs(signed) // 1000) * (-1 if signed < 0 else 1)
    return quotient & 0xffffffff


def compare_target(counter, count):
    """Model the store value; peripheral comparison width/behavior is unknown."""
    return (u32(counter) + min(u32(count), 0xfffe) + 1) & 0xffffffff


def expand_initial_data(data, length):
    """Model handler 6100003c, bounded by the declared destination size."""
    if not isinstance(length, int) or not 0 < length <= 0x100000:
        raise ValueError('Unsupported initial-data size')
    output, cursor = bytearray(), 0

    def byte():
        nonlocal cursor
        if cursor == len(data):
            raise ValueError('Truncated compressed initial data')
        value = data[cursor]
        cursor += 1
        return value

    while len(output) < length:
        token = byte()
        literals, run = token & 7, token >> 4
        if literals == 0:
            literals = byte()
        if run == 0:
            run = byte()
        if literals == 0:
            raise ValueError('Invalid zero literal-count encoding')
        literals -= 1
        if len(output) + literals > length:
            raise ValueError('Literal output exceeds declared size')
        for _ in range(literals):
            output.append(byte())
        if token & 8:
            distance = byte()
            run += 2
            if not 0 < distance <= len(output):
                raise ValueError('Backreference outside initialized output')
            if len(output) + run > length:
                raise ValueError('Backreference output exceeds declared size')
            for _ in range(run):
                output.append(output[-distance])
        else:
            if len(output) + run > length:
                raise ValueError('Zero output exceeds declared size')
            output.extend(bytes(run))
    return bytes(output), cursor


def report(core):
    digest = hashlib.sha256(core.data).hexdigest()
    if digest != IMAGE_SHA256:
        raise ValueError('Unsupported CORE1 payload digest')
    record = next(r for r in core.scatter() if r['destination'] == 0x2008008c)
    if (record['source'], record['length'], record['handler']) != (0x0113afc4, 0x478c, 0x6100003c):
        raise ValueError('Unexpected compressed initial-data record')
    offset = core.offset(record['source'])
    initial, consumed = expand_initial_data(core.data[offset:offset+0x1f44], record['length'])
    flag = initial[0x200845b4-record['destination']:0x200845b6-record['destination']]
    if flag != b'\x01\x00' or core.u32(0x011001ac) != 0x01103471:
        raise ValueError('Unexpected initial flags or IRQ91 vector')
    return dict(payload_sha256=digest, scatter_record=record, compressed_bytes_used=consumed,
                initial_data_sha256=hashlib.sha256(initial).hexdigest(),
                initial_done=flag[0], initial_registered=flag[1], irq91_handler=0x01103470,
                callback=0x011271ac, callback_slot=0x20084c38, timer_base=0x40059000,
                chunks={str(n): list(wait_chunks(n, 0)) for n in (0, 1, 0xfffe, 0xffff, 0x1fffd)},
                scaled_examples={str(n): scaled_count(n) for n in (0, 1, 1000, 44739, 44740)},
                limitations=['Previous pending completion is drained even for count zero.',
                             'Global callback/flags do not establish concurrent-caller safety.',
                             'No hardware frequency, timeout, DSP fence or execution is modeled.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    from core1 import Core1
    try:
        print(json.dumps(report(Core1(args.image)), indent=2))
    except (OSError, ValueError, StopIteration) as error:
        parser.exit(2, f'{error}\n')
