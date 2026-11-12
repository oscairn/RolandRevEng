# Fantom-0 persistent SSH package

[Download the installer ZIP](fantom-07-persistent-ssh-update.zip) and read the
[complete instructions](../tools/fantom_ssh/README.txt) before installing.

The keyboard **must already run Roland system version 1.08**. This package does
not upgrade its system version. Hardware installation and reboot-time SSH were
verified on Fantom-07 with an RTL8153 USB Ethernet adapter.

Generate an Ed25519 SSH key and put only its public key on the flash drive as
`FANTOM_SSH_AUTHORIZED_KEYS`. No authentication key is included in the ZIP.

**After Update (board1) End: power off, remove the drive and reboot normally.
Do not move the drive to EXT DEVICE for board2.** This is an SSH-only installer,
not a full Roland firmware update. It contains no Roland firmware payloads.

Verify the ZIP with `shasum -a 256 -c SHA256SUMS` from this directory. Source,
hardware-test boundaries and build details are in the
[persistent SSH study](../docs/fantom-persistent-ssh-update.md). The ZIP includes
the relevant Dropbear, library/runtime and Oscairn license notices.
