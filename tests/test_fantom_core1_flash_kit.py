import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_fantom_core1_flash_kit as kit


class Board1CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.target, self.usb = self.base / 'target', self.base / 'usb'
        self.usb.mkdir()
        self.app, self.dropbear, self.payload = b'fixture application', b'fixture SSH', b'fixture UPA'
        for name, content in {
            'home/root/mi078': self.app,
            'home/root/go.sh': b'unchanged custom startup',
            'home/root/bin/oscairn-dropbearmulti': self.dropbear,
            'home/root/bin/oscairn-ssh-start.sh': b'startup',
            'home/root/.oscairn-ssh/authorized_keys': b'public key sentinel',
            'home/root/.oscairn-ssh/host_ed25519': b'host key sentinel',
            'etc/systemd/system/oscairn-ssh@.service': b'service',
            'etc/udev/rules.d/90-oscairn-ssh.rules': b'rules',
        }.items():
            path = self.target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (self.target / 'home/root/bin/oscairn-dropbearmulti').chmod(0o755)
        (self.usb / 'FNTM0_UPA.BIN').write_bytes(self.payload)
        with patch.object(kit, 'APP_SHA', kit.digest(self.app)), \
                patch.object(kit, 'DROPBEAR_SHA', kit.digest(self.dropbear)):
            self.script = kit.render_check(kit.digest(self.payload), 'MARKER bmc0 CORE1')
        # Only the test fixture changes the production mount location/guard.
        self.script = self.script.replace('ROOT=/run/media/mmcblk2p2', f"ROOT='{self.target}'")
        self.script = self.script.replace('grep -qs " $ROOT " /proc/mounts', 'true')

    def run_check(self):
        files = [p for p in self.target.rglob('*') if p.is_file()]
        before = {p: (p.read_bytes(), p.stat().st_mode) for p in files}
        script = self.base / 'check.sh'
        script.write_text(self.script)
        result = subprocess.run(['/bin/sh', str(script), str(self.usb)], capture_output=True, text=True)
        after = {p: (p.read_bytes(), p.stat().st_mode) for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        return result

    def test_valid_payload_and_installed_ssh_pass_without_changes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OSCAIRN BMC CHECK OK: MARKER bmc0 CORE1', result.stdout)

    def test_wrong_or_missing_payload_fails_without_changes(self):
        for payload in (b'wrong UPA', None):
            path = self.usb / 'FNTM0_UPA.BIN'
            if payload is None:
                path.unlink()
            else:
                path.write_bytes(payload)
            result = self.run_check()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('DO NOT MOVE THE DRIVE TO EXT DEVICE', result.stderr)

    def test_old_data_wrong_application_or_missing_ssh_fails(self):
        old = self.usb / '_DATA_FNTM0'
        old.write_bytes(b'stale stock Linux updater data')
        self.assertIn('Remove the old', self.run_check().stderr)
        old.unlink()
        app = self.target / 'home/root/mi078'
        app.write_bytes(b'wrong version')
        self.assertIn('Requires the verified', self.run_check().stderr)
        app.write_bytes(self.app)
        (self.target / 'home/root/.oscairn-ssh/host_ed25519').unlink()
        self.assertIn('Persistent SSH file missing', self.run_check().stderr)

    def test_production_mount_guard_is_present_and_shell_syntax_valid(self):
        script = kit.render_check(kit.MARKER_UPA_SHA, 'MARKER bmc0 CORE1')
        self.assertIn('grep -qs " $ROOT " /proc/mounts', script)
        subprocess.run(['/bin/sh', '-n'], input=script, text=True, check=True)
        self.assertNotIn('@UPA_SHA@', script)


class KitTests(unittest.TestCase):
    def test_unknown_input_cannot_produce_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, password, output = (Path(tmp) / n for n in ('source', 'password', 'output'))
            source.write_bytes(b'unknown build')
            password.write_bytes(b'fixture passphrase')
            with self.assertRaises(ValueError):
                kit.build(source, source, password, output)
            self.assertFalse(output.exists())

    @unittest.skipUnless(shutil.which('gpg'), 'GPG required')
    def test_encrypted_verifier_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'update_fntm0'
            script = kit.render_check(kit.MARKER_UPA_SHA, 'MARKER bmc0 CORE1')
            kit.encrypt_check(script, b'fixture passphrase', output)
            result = subprocess.run([
                'gpg', '--homedir', str(root), '--batch', '--pinentry-mode', 'loopback',
                '--passphrase-fd', '0', '--decrypt', str(output),
            ], input=b'fixture passphrase\n', check=True, capture_output=True)
            self.assertEqual(result.stdout.decode(), script)
            self.assertNotIn(b'fixture passphrase', output.read_bytes())

    @unittest.skipUnless((ROOT / 'local/fantom-07-core1-marker-v108/FNTM0_UPA.BIN').exists()
                         and shutil.which('gpg'), 'Local verified UPA and GPG required')
    def test_complete_kit_pins_both_payloads_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            password = root / 'password'
            password.write_bytes(b'fixture passphrase\n')
            candidate = ROOT / 'local/fantom-07-core1-marker-v108/FNTM0_UPA.BIN'
            stock = ROOT / 'local/fantom-07-core1-marker-v108/restore/FNTM0_UPA.BIN'
            output = root / 'kit'
            manifest = kit.build(candidate, stock, password, output)
            self.assertTrue(manifest['prepared_for_first_hardware_trial'])
            self.assertFalse(manifest['hardware_tested'])
            self.assertEqual((output / 'flash-drive/FNTM0_UPA.BIN').read_bytes(), candidate.read_bytes())
            self.assertEqual((output / 'restore-drive/FNTM0_UPA.BIN').read_bytes(), stock.read_bytes())
            for entry in manifest['files']:
                self.assertEqual(kit.digest((output / entry['path']).read_bytes()), entry['sha256'])
            for directory, label, digest in (
                ('flash-drive', 'MARKER bmc0 CORE1', kit.MARKER_UPA_SHA),
                ('restore-drive', 'RESTORE stock BMC v1.08', kit.STOCK_UPA_SHA),
            ):
                self.assertEqual(sorted(p.name for p in (output / directory).iterdir()),
                                 ['FNTM0_UPA.BIN', 'update_fntm0'])
                result = subprocess.run([
                    'gpg', '--homedir', str(root), '--batch', '--pinentry-mode', 'loopback',
                    '--passphrase-fd', '0', '--decrypt', str(output / directory / 'update_fntm0'),
                ], input=b'fixture passphrase\n', check=True, capture_output=True)
                self.assertEqual(result.stdout.decode(), kit.render_check(digest, label))
            before = (output / 'manifest.json').read_bytes()
            with self.assertRaises(FileExistsError):
                kit.build(candidate, stock, password, output)
            self.assertEqual((output / 'manifest.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
