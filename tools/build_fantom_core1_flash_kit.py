"""Prepare a first-trial BMC marker flash kit and stock restore kit; never flashes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_fantom_core1_marker import STOCK_UPA_SHA, digest, read_upa
from build_fantom_ssh_update import APP_SHA, DROPBEAR_SHA

MARKER_UPA_SHA = '598a1a2be7db21461adadbd37eda4d7411aae480992f6d8f42b24dc097dd03e1'
ASSETS = Path(__file__).parent


def render_check(upa_sha, label):
    script = (ASSETS / 'fantom_core1_board1_check.sh.in').read_text()
    for name, value in dict(UPA_SHA=upa_sha, LABEL=label, APP_SHA=APP_SHA,
                            DROPBEAR_SHA=DROPBEAR_SHA).items():
        script = script.replace('@' + name + '@', value)
    return script


def encrypt_check(script, password, output):
    with tempfile.TemporaryDirectory(prefix='fantom-bmc-check-') as tmp:
        plain = Path(tmp) / 'check.sh'
        plain.write_text(script)
        subprocess.run(['/bin/sh', '-n', str(plain)], check=True)
        subprocess.run([
            'gpg', '--homedir', tmp, '--batch', '--pinentry-mode', 'loopback',
            '--passphrase-fd', '0', '--rfc4880', '--force-mdc', '--symmetric',
            '--cipher-algo', 'AES256', '--compress-algo', 'ZIP',
            '--s2k-digest-algo', 'SHA1', '--s2k-count', '65011712',
            '--output', str(output), str(plain),
        ], input=password + b'\n', check=True, capture_output=True)


def build(candidate, stock, passphrase_file, output):
    marker_data, stock_data = candidate.read_bytes(), stock.read_bytes()
    if digest(marker_data) != MARKER_UPA_SHA or digest(stock_data) != STOCK_UPA_SHA:
        raise ValueError('Expected the verified marker UPA and exact stock 1.08 UPA')
    before, after = read_upa(stock_data), read_upa(marker_data)
    if [a != b for (_, a), (_, b) in zip(before, after)] != [False, True, False, False, False, False]:
        raise ValueError('Unexpected changed BMC member set')
    return write_kit(marker_data, stock_data, passphrase_file, output,
                     'MARKER bmc0 CORE1', ASSETS / 'fantom_core1_flash_README.txt')


def write_kit(candidate_data, stock_data, passphrase_file, output, label, readme):
    """Called after the experiment builder has validated both payloads."""
    password = passphrase_file.read_bytes().rstrip(b'\r\n')
    if not password or b'\n' in password or len(password) > 4096:
        raise ValueError('Expected one passphrase line in a local external file')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    # Stage the complete kit before publishing its output directory.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fantom-flash-kit-', dir=output.parent) as tmp:
        staging = Path(tmp) / output.name
        staging.mkdir()
        files = []
        for name, content, drive_label in (
            ('flash-drive', candidate_data, label),
            ('restore-drive', stock_data, 'RESTORE stock BMC v1.08'),
        ):
            drive = staging / name
            drive.mkdir()
            (drive / 'FNTM0_UPA.BIN').write_bytes(content)
            encrypt_check(render_check(digest(content), drive_label), password, drive / 'update_fntm0')
            for path in sorted(drive.iterdir()):
                files.append(dict(path=path.relative_to(staging).as_posix(),
                                  bytes=path.stat().st_size, sha256=digest(path.read_bytes())))
        shutil.copyfile(readme, staging / 'README.txt')
        manifest = dict(prepared_for_first_hardware_trial=True, hardware_tested=False,
                        board1_effect='Read-only payload, v1.08 application and SSH checks',
                        linux_files_installed=False, authentication_keys_included=False,
                        board2_acceptance_proven=False, external_marker_route_proven=False,
                        recovery_proven=False, files=files)
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (staging / 'SHA256SUMS').write_text(''.join(
            f"{entry['sha256']}  {entry['path']}\n" for entry in files))
        staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--passphrase-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.candidate, args.stock, args.passphrase_file, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    print('Prepared first-trial BMC flash kit:', args.output)


if __name__ == '__main__':
    main()
