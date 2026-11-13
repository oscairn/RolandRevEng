#!/usr/bin/env python3
"""Decrypt a B6/3DES CORE0 container using a local ROM entry; require plaintext CRC."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import zlib

try:
    from Cryptodome.Cipher import DES3
except ImportError:
    from Crypto.Cipher import DES3

from c0_header import header


def reverse_blocks(data):
    if len(data) % 8:
        raise ValueError('Expected complete eight-byte blocks')
    return b''.join(data[i:i + 8][::-1] for i in range(0, len(data), 8))


def pack_key(entry24):
    if len(entry24) != 24:
        raise ValueError('Expected the raw 24-byte B6 ROM table entry')
    return reverse_blocks(entry24)


def decrypt(ciphertext, key, chunk=65536):
    if not ciphertext or len(ciphertext) % 8:
        raise ValueError('Expected nonempty complete ciphertext blocks')
    if type(chunk) is not int or chunk <= 0 or chunk % 8:
        raise ValueError('Chunk size must be a positive multiple of eight')
    cipher = DES3.new(key, DES3.MODE_ECB)
    plaintext = bytearray()
    for offset in range(0, len(ciphertext), chunk):
        block = reverse_blocks(ciphertext[offset:offset + chunk])
        plaintext.extend(reverse_blocks(cipher.decrypt(block)))
    return bytes(plaintext)


def decrypt_container(data, entry24):
    info = header(data)
    if info['crypto_control'] != 0xb6020001:
        raise ValueError('Only the observed B6, three-key 3DES encrypted form is supported')
    start, size = info['payload_offset'], info['payload_length']
    plaintext = decrypt(data[start:start + size], pack_key(entry24))
    if zlib.crc32(plaintext) != info['checksum']:
        raise ValueError('Plaintext CRC mismatch; no validated output')
    return info, plaintext


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--input', type=Path, required=True)
    parser.add_argument('-o', '--output', type=Path, required=True)
    parser.add_argument('--key-file', type=Path, required=True,
                        help='Local raw 24-byte ROM entry; its contents are never printed')
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError('Output already exists')
        data = args.input.read_bytes()
        info, plaintext = decrypt_container(data, args.key_file.read_bytes())
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(plaintext)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(dict(output=str(args.output), bytes=len(plaintext),
                          input_sha256=hashlib.sha256(data).hexdigest(),
                          plaintext_sha256=hashlib.sha256(plaintext).hexdigest(),
                          plaintext_crc32=info['checksum'], crc32_matches=True,
                          load_destination=info['load_destination']), indent=2))


if __name__ == '__main__':
    main()
