import base64
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_fantom_ssh_update as package

FAKE_BINARY = b'fixture; never execute'
KEY = 'ssh-ed25519 ' + base64.b64encode(
    struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes(range(32))
).decode() + ' test\n'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with patch.object(package, 'DROPBEAR_SHA', hashlib.sha256(FAKE_BINARY).hexdigest()):
            self.script = package.render_installer(FAKE_BINARY)
        self.path = self.root / 'install.sh'
        self.path.write_text(self.script)

    def run_installer(self, key):
        if key is not None:
            (self.root / 'FANTOM_SSH_AUTHORIZED_KEYS').write_text(key)
        # The intentionally wrong binary stops execution before any target writes.
        (self.root / 'dropbearmulti').write_bytes(b'wrong binary')
        return subprocess.run(['/bin/sh', str(self.path), str(self.root)],
                              capture_output=True, text=True)

    def test_syntax_and_unmodified_usb_gadget(self):
        subprocess.run(['/bin/sh', '-n', str(self.path)], check=True)
        self.assertNotIn('@APP_SHA@', self.script)
        self.assertNotIn('ttyGS', self.script)
        self.assertNotIn('modprobe', self.script)
        self.assertNotIn('fdisk', self.script)

    def test_missing_key_fails_before_target_changes(self):
        result = self.run_installer(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing FANTOM_SSH_AUTHORIZED_KEYS', result.stderr)

    def test_private_key_and_invalid_public_keys_rejected(self):
        for key in ('-----BEGIN OPENSSH PRIVATE KEY-----\n', '# comment only\n',
                    'ssh-rsa AAAA test\n', KEY.replace('AAAAC3', 'BAAAC3'),
                    'command="id" ' + KEY):
            with self.subTest(key=key[:20]):
                result = self.run_installer(key)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Expected plain ssh-ed25519 PUBLIC keys', result.stderr)

    def test_valid_keys_pass_key_guard_but_wrong_binary_rejected(self):
        result = self.run_installer('# two public keys\n' + KEY + KEY)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Dropbear SHA256 mismatch', result.stderr)

    def test_oversized_key_file_rejected(self):
        result = self.run_installer(KEY * 300)
        self.assertIn('exceeds 16 KiB', result.stderr)

    def test_unverified_binary_cannot_be_packaged(self):
        with self.assertRaises(ValueError):
            package.render_installer(FAKE_BINARY)

    @unittest.skipUnless(shutil.which('gpg'), 'GPG required')
    def test_encrypted_package_roundtrip_contains_no_user_key(self):
        source = self.root / 'source'
        for name in ('LICENSE', 'libtomcrypt/LICENSE', 'libtommath/LICENSE'):
            p = source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('fixture license\n')
        binary = self.root / 'binary'
        binary.write_bytes(FAKE_BINARY)
        password = self.root / 'password'
        password.write_text('test-only-passphrase\n')
        out = self.root / 'out'
        with patch.object(package, 'DROPBEAR_SHA', hashlib.sha256(FAKE_BINARY).hexdigest()):
            package.build(binary, password, source, out)
        self.assertFalse((out / 'FANTOM_SSH_AUTHORIZED_KEYS').exists())
        self.assertFalse((out / 'FNTM0_UPA.BIN').exists())
        self.assertFalse((out / '_DATA_FNTM0').exists())
        self.assertIn('musl 1.2.6', (out / 'LICENSE.dropbear.txt').read_text())
        self.assertIn('GCC RUNTIME LIBRARY EXCEPTION', (out / 'LICENSE.dropbear.txt').read_text())
        home = self.root / 'gpg'
        home.mkdir(mode=0o700)
        result = subprocess.run([
            'gpg', '--homedir', str(home), '--batch', '--pinentry-mode', 'loopback',
            '--passphrase-fd', '0', '--decrypt', str(out / 'update_fntm0'),
        ], input=b'test-only-passphrase\n', capture_output=True, check=True)
        self.assertEqual(result.stdout.decode(), self.script)
        for line in (out / 'SHA256SUMS').read_text().splitlines():
            digest, name = line.split()
            self.assertEqual(digest, hashlib.sha256((out / name).read_bytes()).hexdigest())


class PopupTests(unittest.TestCase):
    BEFORE = '#!/bin/sh\nprintf before\n    (\n        printf popup\n    ) &\nprintf synth\n'
    AFTER = '#!/bin/sh\nprintf before\nprintf synth\n'

    def exercise(self, content, expected=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        go, backup = root / 'go.sh', root / 'backup.sh'
        go.write_text(content)
        go.chmod(0o755)
        script = (package.ASSETS / 'remove_popup.sh.in').read_text()
        script = script.replace('@POPUP_SHA@', hashlib.sha256(self.BEFORE.encode()).hexdigest())
        script = script.replace('@CLEAN_GO_SHA@', expected or hashlib.sha256(self.AFTER.encode()).hexdigest())
        cleanup = root / 'cleanup.sh'
        cleanup.write_text(script + '\nremove_popup "$1" "$2"\n')
        result = subprocess.run(['/bin/sh', str(cleanup), str(go), str(backup)],
                                capture_output=True, text=True)
        return go, backup, result

    def test_known_popup_removed_with_backup_and_permissions(self):
        go, backup, result = self.exercise(self.BEFORE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(go.read_text(), self.AFTER)
        self.assertEqual(backup.read_text(), self.BEFORE)
        self.assertEqual(go.stat().st_mode & 0o777, 0o755)

    def test_unknown_startup_is_untouched(self):
        go, backup, result = self.exercise('#!/bin/sh\nprintf custom\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(go.read_text(), '#!/bin/sh\nprintf custom\n')
        self.assertFalse(backup.exists())

    def test_failed_output_integrity_preserves_original(self):
        go, backup, result = self.exercise(self.BEFORE, '0' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(go.read_text(), self.BEFORE)
        self.assertFalse(backup.exists())
        self.assertEqual(sorted(p.name for p in go.parent.iterdir()), ['cleanup.sh', 'go.sh'])


if __name__ == '__main__':
    unittest.main()
