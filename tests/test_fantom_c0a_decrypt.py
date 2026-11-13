import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from fantom_c0a_decrypt import DES3, pack_key, reverse_blocks, decrypt, decrypt_container

ENTRY = bytes(range(24))  # Public synthetic fixture, never hardware-derived material.
PLAINTEXT = bytes(range(64))


def container():
    raw = bytearray(96)
    raw[:9] = b'App1_Main'
    struct.pack_into('<8I', raw, 64, 0, len(PLAINTEXT), 0x60000000, 0,
                     zlib.crc32(PLAINTEXT), 0xb6020001, 0, 0)
    cipher = DES3.new(pack_key(ENTRY), DES3.MODE_ECB)
    return bytes(raw) + reverse_blocks(cipher.encrypt(reverse_blocks(PLAINTEXT)))


class DecryptTests(unittest.TestCase):
    def test_packing_and_validated_payload(self):
        self.assertEqual(pack_key(ENTRY), bytes.fromhex(
            '0706050403020100 0f0e0d0c0b0a0908 1716151413121110'))
        info, plain = decrypt_container(container(), ENTRY)
        self.assertEqual(plain, PLAINTEXT)
        self.assertEqual(info['checksum'], zlib.crc32(plain))
        self.assertEqual(decrypt(container()[96:], pack_key(ENTRY), chunk=8), PLAINTEXT)

    def test_bad_key_corruption_lengths_and_mode_fail_closed(self):
        wrong = bytes([ENTRY[0] ^ 128]) + ENTRY[1:]
        for raw, key in ((container(), wrong), (container()[:-1], ENTRY),
                         (container()[:-1] + b'\xff', ENTRY), (container(), ENTRY[:-1])):
            with self.assertRaises(ValueError):
                decrypt_container(raw, key)
        changed = bytearray(container())
        struct.pack_into('<I', changed, 0x54, 0xb5020001)
        with self.assertRaises(ValueError):
            decrypt_container(changed, ENTRY)
        for chunk in (0, 1, -8, True):
            with self.assertRaises(ValueError):
                decrypt(container()[96:], pack_key(ENTRY), chunk)

    def test_cli_checks_crc_before_writing_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, key, output = (root / n for n in ('input', 'key', 'output'))
            source.write_bytes(container())
            key.write_bytes(bytes([ENTRY[0] ^ 128]) + ENTRY[1:])
            cmd = [sys.executable, str(ROOT / 'tools/fantom_c0a_decrypt.py'),
                   '-i', str(source), '-o', str(output), '--key-file', str(key)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            key.write_bytes(ENTRY)
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), PLAINTEXT)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(ENTRY.hex(), result.stdout)
            output.write_bytes(b'keep')
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b'keep')


@unittest.skipUnless((ROOT / 'local/fantom-live-recovery/fantom-bmc0-b6-entry.bin').exists(),
                     'Private local hardware entry required')
class HardwareMaterialTests(unittest.TestCase):
    def test_both_pinned_fantom_images_match_crc_and_plaintext_identity(self):
        from build_fantom_core1_marker import read_upa
        raw = (ROOT / 'local/fantom-07-core1-marker-v108/restore/FNTM0_UPA.BIN').read_bytes()
        entry = (ROOT / 'local/fantom-live-recovery/fantom-bmc0-b6-entry.bin').read_bytes()
        expected = {
            './_tmp/bmc0_MI078_C0A_up.bin': '2233c991b1e70eccd1156ec0f48df843e1b96fbca92de3b8a2099dda3a982420',
            './_tmp/bmc1_MI078_C0A_up.bin': 'b8fc33839488715590e69465eb437b3fe8e91e752817e9a029c0d036e64120ed',
        }
        checked = []
        for member, data in read_upa(raw):
            if member.name in expected:
                _, plain = decrypt_container(data, entry)
                self.assertEqual(hashlib.sha256(plain).hexdigest(), expected[member.name])
                self.assertEqual(plain[:4], bytes.fromhex('ae480168'))
                self.assertEqual(plain.find(bytes.fromhex('0aa090e8000c82448344')), 0x3e8)
                checked.append(member.name)
        self.assertEqual(set(checked), set(expected))


if __name__ == '__main__':
    unittest.main()
