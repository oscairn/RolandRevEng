"""One bounded request to the Fantom ROM diagnostic; key bytes stay in a local file."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from build_fantom_core1_marker import MARKER
from core1_sysex import inspect

OPERATIONS = {'marker': 0, 'snapshot': 1, 'selftest': 2, 'vectors': 3, 'key': 3}
STATUS = {1: 'complete', 2: 'DMA disabled', 3: 'no unconfigured DMA channel',
          4: 'data cache enabled', 5: 'DMA timeout', 6: 'DMA error',
          7: 'bounce guard changed', 8: 'DMA latched off after an error',
          9: 'unexpected DMA address advance', 10: 'self-test data mismatch'}


def request(operation, channel=7):
    if operation not in OPERATIONS or type(channel) is not int or not 0 <= channel <= 7:
        raise ValueError('Expected a known operation and channel 0..7')
    address = 0x34c0 if operation == 'key' else channel if operation == 'snapshot' else 0
    body = [(address >> shift) & 127 for shift in (21, 14, 7, 0)]
    body += [0, 0, 0, OPERATIONS[operation]]
    return bytes.fromhex('f0 41 10 4e 11') + bytes(body + [-sum(body) & 127, 0xf7])


def decode(operation, packet, channel=7):
    if operation not in OPERATIONS:
        raise ValueError('Unknown diagnostic operation')
    if operation == 'marker':
        if packet != MARKER:
            raise ValueError('Not the exact marker reply')
        return dict(operation=operation, complete=True), None
    result = inspect(packet)
    words = result.get('words', [])
    if result['form'] != 'debug_mmio_read_reply' or result['offset'] != 0 or len(words) != 8:
        raise ValueError('Expected an eight-word diagnostic reply')
    if operation == 'snapshot':
        if words[0] != 0x444d0000 | channel:
            raise ValueError('Wrong snapshot identifier/channel')
        names = ('global', 'channel_a', 'channel_b', 'source', 'destination', 'cpuid', 'ccr')
        return dict(operation=operation, channel=channel, registers=dict(zip(names, words[1:])),
                    complete=True), None
    if words[0] & 0xffff0000 != 0x52440000:
        raise ValueError('Wrong DMA report identifier')
    expected_source = {'selftest': 0x6102d340, 'vectors': 0x01200000, 'key': 0x012034c0}[operation]
    if words[1] != expected_source:
        raise ValueError('Wrong reported source window')
    status = words[0] & 255
    if status not in STATUS:
        raise ValueError('Unknown DMA status')
    report = dict(operation=operation, status=status, status_text=STATUS[status],
                  channel=words[0] >> 8 & 255, source=words[1], complete=status == 1)
    if status != 1:
        return report, None
    count = {'selftest': 1, 'vectors': 2, 'key': 6}[operation]
    if any(words[2 + count:]):
        raise ValueError('Nonzero report padding')
    data = b''.join(word.to_bytes(4, 'little') for word in words[2:2 + count])
    if operation == 'selftest' and words[2] != 0x4f534352:
        raise ValueError('Self-test pattern does not match')
    report['data_sha256'] = hashlib.sha256(data).hexdigest()
    if operation != 'key':
        report['words'] = words[2:2 + count]
    return report, data


def exclusive_write(path, data):
    import os
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=OPERATIONS)
    parser.add_argument('--channel', type=int, default=7)
    parser.add_argument('--out', type=Path, required=True,
                        help='New JSON report, or new raw 24-byte file for key operation')
    args = parser.parse_args()
    packet = request(args.operation, args.channel)
    report_path = args.out.with_suffix(args.out.suffix + '.json') if args.operation == 'key' else args.out
    if args.out.exists() or report_path.exists():
        parser.error('Output already exists; nothing sent')
    if not args.out.parent.is_dir():
        parser.error('Output directory must already exist; nothing sent')
    import mido
    source, destination = 'FANTOM-06 07 08 MIDI OUT1', 'FANTOM-06 07 08 MIDI IN1'
    if source not in mido.get_input_names() or destination not in mido.get_output_names():
        parser.error('Exact Fantom MIDI endpoints are not present; nothing sent')
    replies = []
    with mido.open_input(source) as incoming, mido.open_output(destination) as outgoing:
        outgoing.send(mido.Message.from_bytes(packet))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            for message in incoming.iter_pending():
                if message.type == 'sysex' and len(replies) < 16:
                    replies.append(bytes(message.bytes()))
            time.sleep(0.005)
    decoded = []
    for reply in replies:
        if reply[:5] != bytes.fromhex('f0 41 10 4e 13'):
            continue
        decoded.append(decode(args.operation, reply, args.channel))
    report = dict(request_hex=packet.hex(' '), requests_sent=1, reply_count=len(decoded),
                  results=[result for result, _ in decoded], complete=False)
    data = [value for result, value in decoded if result['complete']]
    if decoded and len(data) == len(decoded) and all(value == data[0] for value in data):
        report['complete'] = True
        if args.operation == 'key':
            exclusive_write(args.out, data[0])
            report['private_data_path'] = str(args.out)
    exclusive_write(report_path, (json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps(report, indent=2))
    if not report['complete']:
        parser.exit(1, 'No consistent complete reply; no key file written\n')


if __name__ == '__main__':
    main()
