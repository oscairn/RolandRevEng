#!/usr/bin/env python3
"""Build an SSH-only Fantom-0 updater; no Roland payloads or user keys included."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ASSETS = Path(__file__).with_name('fantom_ssh')
APP_SHA = '90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7'
DROPBEAR_SHA = '3b026dc09825a16ce2fab96d41f30429b538924081a2aa72de2ac5bbff0573c8'


def render_installer(binary):
    digest = hashlib.sha256(binary).hexdigest()
    if digest != DROPBEAR_SHA:
        raise ValueError('Use the hardware-tested static ARM64 Dropbear binary')
    script = (ASSETS / 'install.sh.in').read_text()
    for marker, text in {
        'DROPBEAR_SHA': digest, 'APP_SHA': APP_SHA,
        'START': (ASSETS / 'start.sh').read_text().rstrip(),
        'SERVICE': (ASSETS / 'oscairn-ssh@.service').read_text().rstrip(),
        'RULES': (ASSETS / '90-oscairn-ssh.rules').read_text().rstrip(),
    }.items():
        script = script.replace('@' + marker + '@', text)
    return script


def build(binary_path, passphrase_path, source, output):
    binary = binary_path.read_bytes()
    script = render_installer(binary)
    password = passphrase_path.read_bytes().rstrip(b'\r\n')
    if not password or b'\n' in password or len(password) > 4096:
        raise ValueError('Expected one passphrase line in external file')
    licenses = [source / n for n in ('LICENSE', 'libtomcrypt/LICENSE', 'libtommath/LICENSE')]
    notices = '\n\n'.join(p.read_text() for p in licenses)
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='fantom-ssh-gpg-') as temp:
        home = Path(temp)
        plain = home / 'install.sh'
        plain.write_text(script)
        subprocess.run(['/bin/sh', '-n', str(plain)], check=True)
        subprocess.run([
            'gpg', '--homedir', str(home), '--batch', '--pinentry-mode', 'loopback',
            '--passphrase-fd', '0', '--rfc4880', '--force-mdc', '--symmetric',
            '--cipher-algo', 'AES256', '--compress-algo', 'ZIP',
            '--s2k-digest-algo', 'SHA1', '--s2k-count', '65011712',
            '--output', str(output / 'update_fntm0'), str(plain),
        ], input=password + b'\n', check=True)
    (output / 'dropbearmulti').write_bytes(binary)
    (output / 'LICENSE.dropbear.txt').write_text(notices)
    shutil.copyfile(Path(__file__).parents[1] / 'LICENSE', output / 'LICENSE.oscairn.txt')
    shutil.copyfile(ASSETS / 'README.txt', output / 'README.txt')
    entries = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}'
               for p in sorted(output.iterdir())]
    (output / 'SHA256SUMS').write_text('\n'.join(entries) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dropbear', type=Path, required=True)
    p.add_argument('--passphrase-file', type=Path, required=True)
    p.add_argument('--dropbear-source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    build(args.dropbear, args.passphrase_file, args.dropbear_source, args.output)
    print('Built key-free SSH-only package:', args.output)


if __name__ == '__main__':
    main()
