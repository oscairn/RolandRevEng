# Fantom-07 1.08 first CORE1 marker flash trial

2026-11-12. **The marker flash and USB MIDI round trip succeeded on Jacob's
Fantom-07.** Normal startup and persistent root SSH were retained, and the patched
bmc0 CORE1 helper returned the exact constant marker through external USB MIDI.
The complete two-stage kit targets v1.08 with persistent SSH. This supersedes the earlier
payload-only folder, which lacked a Linux/board1 handoff file.

Generated kit: `local/fantom-07-core1-marker-flash-kit-v108/`. Its
[`README.txt`](../tools/fantom_core1_flash_README.txt) gives the copy, install and
stock-restore instructions. Copy only the two files inside `flash-drive/` to the
USB root. `restore-drive/` is a separate, mutually exclusive stock payload layout.
Neither variant needs a public key file, private key file or separate Dropbear
binary. Do not mix this with the previous SSH-only flash-drive contents.

The physical sequence follows [Roland's v1.08 procedure](https://www.roland.com/global/support/by_product/fantom-07/updates_drivers/a0df616e-3d37-41d2-9464-d04a43c53193/):
start with WRITE and USB MEMORY, wait for board1 completion, then move the drive
to EXT DEVICE while keeping power on; wait for board2 End before powering off.
For this custom package, require **OSCAIRN BMC CHECK OK** before that handoff.
The preceding SSH-only package deliberately stopped before board2; this one must
complete board2 to install its BMC change.

## Board1 and board2 roles

`update_fntm0` decrypts to our read-only `fantom_core1_board1_check.sh.in`. It
checks the mounted installed root, exact v1.08 application hash, paired UPA hash,
the existing hardware-tested Dropbear hash, and presence of SSH state/startup
files. An old `_DATA_FNTM0` is rejected. It then prints its labelled success
message and returns. It performs no Linux install, key replacement, GPIO access,
device write or network command. The surrounding stock recovery wrapper still
saves its normal update log; board1 End alone can appear after a child failure.

`FNTM0_UPA.BIN` is read by the BMC's board2 updater through EXT DEVICE. It contains
the six stock component names and sizes. Only bmc0 C1A differs, within the
[checked helper and CRC bounds](fantom-core1-marker.md). Other component content
is unchanged; the updater may still rewrite those components. No CORE0 key, ROM
read or DMA operation is included. The footer/version strings stay stock.

The restore UPA is byte-identical stock 1.08. Its paired verifier pins the stock
hash rather than the marker hash. This prepares an attempted stock restoration
through ordinary update mode; it does not demonstrate that mode remains usable
after a failed custom flash. Power interruption or firmware failure can require
service. No claim of guaranteed rollback or brick-proofing is made.

## Validation completed

* The marker's seven offline execution/container checks passed previously.
* Seven new checks passed for verifier success/failure without filesystem changes,
  shell syntax, encryption round-trip, pinned payload rejection, both complete
  layouts/checksums and refusal to overwrite an existing output directory.
* Both exact encrypted verifier files decrypted byte-for-byte with the live
  Fantom's GPG 1.4.7 and passed its `/bin/sh -n`. They were not executed there.
  Only disposable `/tmp` files were used and removed; no hardware updater ran.
* Both production scripts executed successfully against the existing real v1.08
  Linux recovery fixture inside ARM Linux. Target and payload mounts were read-only,
  the container root was read-only and networking was disabled.
* Live read-only SSH checks confirmed the v1.08 application, cleaned startup file,
  expected Dropbear binary, SSH files and active service before preparing the kit.

Detailed reports remain local in the kit's `live-gpg-validation.json` and
`recovery-fixture-validation.json`. Those reports precede the hardware trial.

## Hardware result

Jacob reported flashing complete, rebooted and confirmed the normal screen with
USB Ethernet reconnected. The Mac authenticated root SSH with the same pinned
host key, found the SSH service active and mi078 running. Application SHA256
remained `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`;
go.sh remained `a9ad448d6b24a326cb8520ce0a4e486d290fd8f435a814f1b3f19a7c8c63bfe4`.
The saved board1 log says `OSCAIRN BMC CHECK OK: MARKER bmc0 CORE1`.

At 23:48:29 UTC, a capture opened CoreMIDI input `FANTOM-06 07 08 MIDI OUT1`
and output `FANTOM-06 07 08 MIDI IN1`. It sent **one** exact zero-count request:

```text
F0 41 10 4E 11 00 00 00 00 00 00 00 00 00 F7
```

Two identical 19-byte replies arrived about 20 ms after sending:

```text
F0 41 10 4E 13 00 00 00 00 04 0F 05 03 04 03 05 02 57 F7
```

The independent reply inspector verifies its checksum and decodes the single word
`4f534352`. This is execution evidence for the patch and an external USB MIDI
ingress/reply path. It is not just a successful boot or a version-string check:
the unmodified bmc0 helper returns no reply for this zero-count request in the
offline execution test. Only bmc0 C1A differs in the flashed UPA. The two replies
do **not** establish that bmc1 is patched; the duplication's cause is unresolved.
No repeated requests, raw internal-word injection, ROM read or DMA access was used.

Local evidence: `first-usb-midi-probe.json` and `post-flash-ssh-check.json` in the
kit directory. The initial release ZIP remains the original pre-trial build;
its warning/manifest state records what was known when packaged. Stock restore
has not been tried. General memory access, DMA ownership, CORE0 key recovery,
full BMC emulation and arbitrary custom-engine loading remain unproved. The
next diagnostic should establish a bounded ROM-read mechanism while retaining
the now-proven marker request/reply path.

## Rebuild

```sh
.venv/bin/python tools/build_fantom_core1_flash_kit.py \
  --candidate local/fantom-07-core1-marker-v108/FNTM0_UPA.BIN \
  --stock local/fantom-07-core1-marker-v108/restore/FNTM0_UPA.BIN \
  --passphrase-file local/fantom-ssh/update-passphrase.txt \
  --output local/fantom-07-core1-marker-flash-kit-v108
.venv/bin/python -m unittest discover -s tests -p test_fantom_core1_flash_kit.py -v
```

Use a new output directory. The builder pins both UPA hashes and stages the full
kit before publishing the directory. The external Linux updater passphrase file
is never bundled. Encryption uses the same RFC4880 AES256/MDC settings already
tested with the persistent SSH installer. Generated firmware stays ignored and
local; none of these vendor-derived images have been published.
