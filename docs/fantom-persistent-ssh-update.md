# Persistent SSH-only Fantom-0 installer

2026-11-12. Persistent key-only root SSH was installed on a test FANTOM-07 and
**verified after reboot**, including reuse of its pinned host key. This replaces
the temporary /run-only server. Installation through the actual USB MEMORY/board1
recovery screen is now verified: the saved recovery log contains INSTALL OK and
root SSH returned after normal boot. The isolated recovery filesystem test and
live GnuPG 1.4.7 decryption/installation checks also passed.

**Risk.** Use this at your own risk. It modifies the instrument's system, and it
was tested on one FANTOM-07 only; the FANTOM-06 and FANTOM-08 are untested. No
removal procedure is documented yet.

**Requirements.** System version 1.08, a USB flash drive, and a USB Ethernet
adapter. The only adapter verified is the Realtek RTL8153; other adapters are
untested. Generate an Ed25519 key on your computer; the README covers key
generation, drive preparation, installation, connecting and reinstalling.

Download the [key-free installer ZIP](../packages/fantom-07-persistent-ssh-update.zip).
User instructions are in the package's [README.txt](../tools/fantom_ssh/README.txt).
The keyboard must already run Roland system version **1.08**. After board1 End,
power off, remove the drive and reboot normally; **do not insert the drive into
EXT DEVICE for board2**. This package does not perform a full firmware upgrade.
The revised package also removes the exact earlier Oscairn popup startup block;
that cleanup was tested separately on the live keyboard. After the subsequent
USB installation and normal boot, the cleaned script hash was retained and no
popup-shell process was present.

## Distribution layout

The audited distribution is `packages/fantom-07-persistent-ssh-update.zip`.
The local extracted working copy is `../fantom-07-persistent-ssh-update/`:

* `update_fntm0`: encrypted original SSH installer code, containing no user key.
* `dropbearmulti`: separate hardware-tested ARM64 static Dropbear binary.
* README, SHA256SUMS and Oscairn/Dropbear/library license notices.

**No public or private authentication key is included.** The reader generates
an Ed25519 key on their computer and adds only its .pub file to the USB root as
`FANTOM_SSH_AUTHORIZED_KEYS`. Missing, private, malformed or oversized key files
are rejected before Linux target files are changed. Multiple plain Ed25519 keys
are supported; authorized_keys options, certificates and other algorithms are not.
The installer verifies the external binary's SHA256 and the installed v1.08
mi078 SHA256 before writing.

This is an SSH-only installer: remove old `_DATA_FNTM0` and `FNTM0_UPA.BIN` from
the USB root. It does not include or update BMC firmware, the application, factory
content or partitions. It removes the popup only when go.sh matches the pinned
earlier Oscairn probe, preserving a backup as `.oscairn-ssh/go.sh.with-popup`;
stock or unfamiliar startup scripts are unchanged. Follow its included README: this custom installer
finishes after board1, with no board2 payload. The stock wrapper can display End
even after a child-script error; require the installer’s explicit
`OSCAIRN SSH INSTALL OK` message. Installation interruption can leave partial files.

## Installed files and startup

* `/home/root/bin/oscairn-dropbearmulti`
* `/home/root/bin/oscairn-ssh-start.sh`
* `/home/root/.oscairn-ssh/{authorized_keys,host_ed25519}`
* `/etc/systemd/system/oscairn-ssh@.service`
* `/etc/udev/rules.d/90-oscairn-ssh.rules`

The host key is generated on-device during installation and preserved on
reinstalls. State directory mode is 700; key files are 600, owned by root.
Reinstalling replaces the authorized public-key list. udev requests a service
instance for USB network devices; systemd binds its lifetime to that device.
Dropbear runs in the foreground under systemd, bound to that interface on port
2222, with passwords and forwarding disabled. DHCP remains managed by existing
ConnMan/systemd-networkd. No ttyGS or GPIO configuration is touched.

To connect, with your private key and the keyboard's address (see your router's
DHCP leases):

```sh
ssh -p 2222 -i ~/.ssh/id_ed25519 \
  -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=<known-hosts-file> root@<keyboard-ip>
```

`<known-hosts-file>` holds the keyboard's pinned host key. Verify the fingerprint
on the first connection as described in the README before pinning it.

## Removal

No removal procedure is documented yet. Stock-update removal/rollback has not
been tested.

This is USB Ethernet/LAN SSH, not USB TO COMPUTER serial access. The adapter
used in hardware testing is the RTL8153 on eth1. Interface/IP names are not
hardcoded in the service.

## Build and checks

```sh
python3 tools/build_fantom_ssh_update.py \
  --dropbear local/fantom-ssh/dropbearmulti \
  --passphrase-file local/fantom-ssh/update-passphrase.txt \
  --dropbear-source local/fantom-ssh/dropbear-2026.94 \
  --output ../fantom-07-persistent-ssh-update
python3 -m unittest discover -s tests -p test_fantom_ssh_update.py -v
```

Use a new output directory. The passphrase file stays ignored/local; it is never
included in the package or command-line arguments. The builder pins the binary
that was hardware-tested (see the earlier SSH handoff for source/binary hashes)
and uses RFC4880 AES256/MDC encryption compatible with the installed GPG 1.4.7.

Ten automated tests passed: missing/private/malformed/oversized keys, binary
integrity, shell syntax, package encryption round-trip/key exclusion and guarded
popup cleanup, backup and preservation on integrity failure. An
ARM64 Alpine container with no networking tested the exact decrypted installer
against a disposable mounted target containing the real application. Installation,
permissions, repeat installation, host-key preservation and unchanged stock
sentinels passed. Detailed fixture remains ignored at
`local/fantom-ssh/recovery-fixture/`.

The revised fixture at `local/fantom-ssh/recovery-fixture-v2/` also verified the
real probe script's cleanup, unchanged application/content, backup preservation
and repeat installation. Live cleanup changed go.sh from SHA256
`36b4fc75965f736f5254db6f1dc53706e0a0395cbbfac9021c4a20c3caa1bd45`
to `a9ad448d6b24a326cb8520ce0a4e486d290fd8f435a814f1b3f19a7c8c63bfe4`,
retained the original backup and left the SSH service active.

Live testing: root login and a PTY worked before reboot. After reboot, the same
pinned host key authenticated, systemd reported the USB service active, and the
temporary /run bootstrap directory was absent. No new bootstrap command was sent
after reboot. Physical USB hot-unplug/replug and stock-update removal/rollback
have not been separately tested. The tester reconnected USB Ethernet after normal
startup following the physical installation, and automatic SSH access worked.
Unrelated BMC research remains deferred for this priority.

Physical package installation evidence: `id` returned UID/GID 0, `tty` was
`/dev/pts/0`, `oscairn-ssh@eth1.service` was active, go.sh retained SHA256
`a9ad448d6b24a326cb8520ce0a4e486d290fd8f435a814f1b3f19a7c8c63bfe4`,
and `/home/root/update_sd*.log` contained the explicit installer success marker.
No process matching the earlier `OSCAIRN shell probe` command was present.
