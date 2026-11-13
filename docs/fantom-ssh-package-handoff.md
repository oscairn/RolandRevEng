# Fantom-07: verified SSH and update-package handoff

Superseded for deployment by the [persistent SSH installer](fantom-persistent-ssh-update.md):
the service is now installed and verified after reboot. The /run-only server and
host key below describe the original temporary test.

2026-11-12. **SSH works on the actual keyboard**, including public-key root login,
remote commands and a PTY (`/dev/pts/1`). No flash was performed for this test.

## Working hardware/runtime

* Fantom: `<keyboard-ip>`; Mac: `<computer-ip>` (same LAN, DHCP).
* USB MEMORY → hub → RTL8153 Ethernet adapter (`0bda:8153`) and USB keyboard.
* USB Ethernet is eth1, driver r8152; DHCP worked automatically. Both connmand
  and systemd-networkd are running. Do not launch a competing DHCP client.
* Linux aarch64, kernel `4.19.35-1.1.0+g0f9917c56d59`, UID 0.
* Existing BusyBox nc is client-only; telnetd and installed SSH daemons absent.
* g_serial/ttyGS0 carries BMC IPC. Leave it unchanged. Direct USB TO COMPUTER
  serial access remains unproven; this SSH route uses USB Ethernet and the LAN.

## Built and tested artifact

Project-local ignored directory: `bmc-research/local/fantom-ssh/`.

* `dropbearmulti`: static PIE ARM64/musl executable, about 451 KiB.
* Version: Dropbear 2026.94, official release source at
  <https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2>.
* Source SHA256: `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81`.
* Binary SHA256: `3b026dc09825a16ce2fab96d41f30429b538924081a2aa72de2ac5bbff0573c8`.
* `build.sh` reproduces the build in ARM64 Alpine Docker: configure
  `--enable-static --disable-zlib`; make
  `PROGRAMS='dropbear dropbearkey' MULTI=1 STATIC=1`; strip.
  Source hash matched upstream SHA256SUM.asc; PGP signature was not verified.
* `client_ed25519` is the **Mac-only private key**, mode 600. Never put it in
  firmware, a served directory or Git. `transfer/authorized_keys` is its public key.
* `known_hosts` pins the current temporary server host key.

## Current live server

Files are under `/run/oscairn-ssh/` on the Fantom: binary, authorized_keys,
host_ed25519, server.log and dropbear.pid. Directory mode 700; keys mode 600.
Host key was generated on-device:

```sh
/run/oscairn-ssh/dropbearmulti dropbearkey -t ed25519 -f /run/oscairn-ssh/host_ed25519
/run/oscairn-ssh/dropbearmulti dropbear -E -s -j -k -l eth1 -p 2222 \
  -D /run/oscairn-ssh -r /run/oscairn-ssh/host_ed25519 \
  -P /run/oscairn-ssh/dropbear.pid </dev/null >/run/oscairn-ssh/server.log 2>&1
```

This daemonizes, binds the USB interface, disables password login and forwarding,
and uses a custom authorized-key directory. No passwd/shadow changes are required.
The final daemon PID at handoff is 4306; check the pidfile before relying on it.
The old unencrypted reverse connection and transfer HTTP server were closed;
SSH was verified again independently afterward.

From the project directory on the Mac:

```sh
ssh -p 2222 -i bmc-research/local/fantom-ssh/client_ed25519 \
  -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=bmc-research/local/fantom-ssh/known_hosts root@<keyboard-ip>
```

## Next agent: create the update package

Use the stock v1.08 BMC image and encrypted updater, plus the successful on-screen
package as the startup reference:
`local/fantom-07-onscreen-probe-v108/{probe-files,probe-go.sh,stock-files}`.
Keep the on-screen fallback initially. Add the tested SSH binary, public key and
upstream licenses as app payloads; launch SSH from the actual installed startup
path after the USB network interface exists. Discover/bind that interface rather
than hardcoding its DHCP IP. Confirm added tar members install successfully.

Generate a device-specific host key once in a verified persistent writable
location that updates preserve; do not distribute the test host private key.
Preserve strict directory/key permissions. Retain normal mi078 startup and stock
g_serial settings. Verify archive contents/hashes and shell syntax, then test
both update stages, reboot, DHCP and SSH on hardware.

Current /run files disappear on reboot: **boot persistence and the next package
are not tested**. SFTP/SCP support is not checked. No broad BMC research was resumed.

## Subsequent installer discovery

The real recovery image and stock Linux updater were recovered/decrypted after
this handoff was drafted. See [verified Linux updater](fantom-linux-updater-decryption.md).
The plaintext is `local/fantom-live-recovery/update_fntm0.decrypted.sh`.
It copies `_DATA/bin` to `/home/root/bin`, then deletes the extracted `_DATA`
directory: put additional SSH assets under that bin subtree and use installed
paths in go.sh. This resolves the consumer's copy behavior; installation of added
assets and reboot persistence still need testing. The Linux passphrase is in
the locally retained original `local/fantom-live-recovery/uprecv.sh`; it is
separate from the still-missing BMC CORE0 key.
