# Fantom-07 Linux updater: verified decryption

2026-11-12. The `update_fntm0` passphrase was recovered from the keyboard's
actual recovery image and successfully decrypted the exact stock v1.08 file.
This supersedes the earlier missing-passphrase status for the Linux updater.
It does **not** recover the separate BMC CORE0 firmware key.

## Evidence and reproduction

The live normal rootfs contains no useful updater reference in the bounded
search. Its update logs describe initial installation. The mounted boot partition
at `/run/media/mmcblk2p1` contains the actual recovery image:
`roland-update-image-imx8mmmi078.ext4.u-boot` (240734272 bytes), SHA256
`a65c0ff6108cd5002778dd578c3552098de473465b172b37b3e2a66e66760240`.
It was copied read-only over verified SSH. U-Boot header size, header CRC and
payload CRC passed. Its payload is uncompressed; removing the 64-byte header
produces a filesystem readable with debugfs, without mounting/executing it.

Boot partition boot.scr selects this image for `gpio_update=1`, with root on ram0.
Inside the image, `/home/root/bin/uprecv.sh` explicitly feeds the passphrase
to `/usr/bin/gpg --batch --yes --passphrase-fd 0` and decrypts the USB drive's
`update_fntm0` into `/tmp/update_fntm0.sh` before executing it. The recovered
original script, containing the passphrase, is retained ignored/local at
`local/fantom-live-recovery/uprecv.sh`, SHA256
`7ba161c71b633ae894cccc75c84bdbf4025a4769e5c19047d948b7e8228b312d`.

GPG successfully decrypted the stock encrypted updater (SHA256
`ef69453ca9dfa7af7cff043e43bcbc5598fc07fe4e445e55e13e03d812103013`)
using that exact passphrase. GPG reported AES256.CFB and exited successfully.
Plaintext SHA256:
`062643150eb665151e96bddbc6654b4476f4c0df56bec130a8cc6cb45f36dda0`.
It is retained at `local/fantom-live-recovery/update_fntm0.decrypted.sh`.
`/bin/sh -n` passed. The vendor script was **not executed** during this analysis.
An isolated local GNUPGHOME was used; no keyboard update was performed.

## Consequences for the SSH package agent

The decrypted script extracts `_DATA_FNTM0` into `/home/root`, then moves
`_DATA/{mi078,qctest,go.sh}` to `/home/root/` and copies `_DATA/bin` recursively
to `/home/root/bin`. It later deletes the extracted `_DATA` directory.
Thus extra SSH binary/public-key/startup-helper files should be placed beneath
`_DATA/bin` if retaining this stock consumer, and launched from their installed
`/home/root/bin` paths. Do not assume arbitrary new top-level members persist.
This copy path is established from code; added-file installation still needs a
hardware test. Existing stock encrypted update_fntm0 can remain unchanged.

The script also recreates swap, installs factory data and updates the DTB. It has
a conditional partition-resize path; do not execute it merely to inspect or
decrypt it. Successful decryption is not a rollback guarantee or BMC key recovery.
