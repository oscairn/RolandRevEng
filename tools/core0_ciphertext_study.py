"""Compare pinned CORE0 ciphertext blocks; never derives, guesses or prints keys."""
import hashlib
import json
import os
from pathlib import Path
import struct

from c0_header import header

INPUTS = {
    'fantom0': ('bmc0_MI078_C0A_up.bin', '0ecb9c16adf67349c0f1efd6e8c257465972690a3ca1b5e5af29dbb1f2c480c9'),
    'fantom1': ('bmc1_MI078_C0A_up.bin', '2929219309206f7f9ac0abab429a6a20e5eff45c6caf7c417af197f2275911f5'),
    'mc101': ('crossmodel/mc101/RPG69_C0A_up.bin', 'ebdb8d987232a31972c881065254419187d586d73bb1c808e681b5dd278d8cf6'),
    'jupiter': ('crossmodel/jupiter-x/MI077_C0A_up.bin', '56d7382ad6b642e2213e417311ab49c89ba6359e34339115316521346a66fbb1'),
    'sh4d': ('crossmodel/sh-4d/DD013_C0A_up.bin', 'f2fcdaf174e7730e7f5a005debf92d1f6a25207d7143600714c9ae9b4d22cc0c'),
    'tr8s': ('crossmodel/tr-8s/rpg42_m0c0a_up.bin', 'cfdc444c03a9d41655f02d9bf3dd3c28b335c292b09cbede23924aa8ed97620d'),
}


def reported_entry_address(index):
    """Arithmetic from the cited MC-101 report, not a verified Fantom ROM layout."""
    if not isinstance(index, int) or not 0 <= index <= 255:
        raise ValueError('Expected an eight-bit container key index')
    return 0x012023b0 + index*24


def payload_blocks(data):
    info = header(data)
    if info['crypto_control'] != 0xb6020001:
        raise ValueError('Outside the observed crypto-control form')
    start = info['payload_offset']
    payload = data[start:start+info['payload_length']]
    return info, {row[0] for row in struct.iter_unpack('<Q', payload)} - {0, 0xffffffffffffffff}


def report(corpus):
    rows, baseline = [], None
    for name, (filename, expected) in INPUTS.items():
        data = (Path(corpus)/filename).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError(f'Unsupported {name} artifact digest')
        info, blocks = payload_blocks(data)
        if baseline is None:
            baseline = blocks
        rows.append(dict(name=name, sha256=digest, payload_offset=info['payload_offset'],
                         payload_length=info['payload_length'], crypto_control=info['crypto_control'],
                         distinct_nontrivial_blocks=len(blocks),
                         shared_with_fantom0=len(baseline & blocks)))
    return dict(images=rows, key_recovery_claimed=False, decryption_performed=False,
                reported_mc101_location=dict(rom_base=0x01200000, table_base=0x012023b0,
                    entry_size=24, index=0xb6, entry=reported_entry_address(0xb6),
                    verified_on_fantom=False),
                limits=['Matching ciphertext is evidence of a shared transformation, not key recovery.',
                        'No ROM bytes, key bytes, hardware read route or plaintext validation are supplied.'])


if __name__ == '__main__':
    corpus = Path(os.environ.get('BMC_CORPUS_DIR', Path(__file__).resolve().parents[1]/'local'))
    result = report(corpus)
    target = Path(__file__).resolve().parents[1]/'local/core0-ciphertext-study.json'
    target.write_text(json.dumps(result, indent=2)+'\n')
    for row in result['images']:
        print(row['name'], row['shared_with_fantom0'], 'distinct ciphertext blocks shared with fantom0')
