FANTOM-07 v1.08 — FIRST BMC CORE1 MARKER FLASH TRIAL

This is a complete two-stage test layout for Jacob's already-rooted Fantom-07.
It requires the verified v1.08 application and previously installed persistent
SSH. It does not install SSH, replace keys, update Linux or extract _DATA_FNTM0.
No public/private SSH key or separate Dropbear file needs to be added.

The marker patch passed offline execution and container checks. Acceptance by
the physical BMC updater and the external marker reply path are not yet tested.
Firmware flashing can leave the keyboard unable to start. The stock restore
files are provided, but recovery from a failed custom BMC boot is not proven.
Use stable power and save current work/back up user data before the trial.

PREPARE THE FLASH DRIVE

Use a USB drive already formatted by the Fantom. Back up its contents first;
this package does not format drives. Remove old updater files from its root,
including the old update_fntm0, FNTM0_UPA.BIN, _DATA_FNTM0, dropbearmulti and
FANTOM_SSH_AUTHORIZED_KEYS. Keep any backups on the Mac.

Copy ONLY the two files INSIDE flash-drive/ to the USB drive's ROOT:

    update_fntm0
    FNTM0_UPA.BIN

Do not copy the ZIP, enclosing directory, restore-drive directory or files from
the earlier SSH-only installer. The two-file layout is intentional: our board1
script checks the installed system and the UPA hash, then returns. It does not
use the stock Linux installer and therefore does not need _DATA_FNTM0.

Optional Mac check, substituting your drive name:

    shasum -a 256 /Volumes/YOUR_USB/FNTM0_UPA.BIN

Expected marker payload SHA256:
598a1a2be7db21461adadbd37eda4d7411aae480992f6d8f42b24dc097dd03e1

INSTALL — BOTH STAGES ARE REQUIRED FOR THIS BMC TRIAL

1. Power the Fantom off. Leave its Ethernet adapter disconnected for the update;
   reconnect it after normal boot. Connect the flash drive to USB MEMORY.
2. Hold WRITE and power on. Keep holding WRITE until the board1 insert-memory
   screen appears, then release.
3. The board1 check should print:

       OSCAIRN BMC CHECK OK: MARKER bmc0 CORE1

   It changes no Linux/SSH files. The normal recovery wrapper will save a log.
   If you see CHECK FAILED, do not move the drive to EXT DEVICE. The stock UI
   can say board1 End even when a child script failed; End alone is not proof
   that our check passed. If the result is unclear, leave EXT DEVICE empty and
   stop before board2; board1 itself has not flashed BMC firmware.
4. After CHECK OK and Update (board1) End, KEEP THE POWER ON. Move the same
   drive from USB MEMORY to the EXT DEVICE jack. This is deliberately different
   from the earlier SSH-only package, which stopped before board2.
5. Wait through Running Update. Do not remove the drive or interrupt power.
   Stock Roland instructions estimate about five minutes for board2; this is
   not a timeout guarantee for the modified payload.
6. Only after Update (board2) End, power off, remove the drive, then boot normally.
   If an error appears, record its complete text/code and leave the board powered
   while an update is actively running; do not improvise more update attempts.
7. Reconnect USB Ethernet. Existing SSH should return on port 2222 with the same
   key. The panel should start normally. A normal boot/version display alone
   does not prove the marker patch executed; we will test the zero-count request
   and capture its reply separately. Do not send arbitrary memory-read commands.

The package preserves stock version/footer strings. It does not add an on-screen
marker, ROM reader or CORE0 decryption key. The archive contains all six stock
BMC update components; only bmc0 C1A bytes differ. The updater may rewrite other
unchanged components too; this is not claimed to be a single-component flash.

STOCK RESTORE FILES

Keep restore-drive/ on the Mac. To attempt stock BMC restoration using the
standard update mode, replace BOTH root files on the USB with the two files
inside restore-drive/, and repeat the same two-stage sequence. Its board1
success marker says RESTORE stock BMC v1.08. Never mix a restore verifier with
the marker UPA: hashes differ and the check will reject it.

Expected stock BMC payload SHA256:
44993228fc0b407a6b198d8ef3da953f861393d929f47cce08ce1a79fc108f75

This restores BMC component bytes only and leaves Linux/SSH alone. It does not
prove the physical updater will remain accessible after a failed custom flash.
Do not initialize the keyboard or run a factory reset as part of this test.

The physical port sequence follows Roland's v1.08 instructions; our read-only
board1 script and marker UPA are custom research code, not an official release:
https://www.roland.com/global/support/by_product/fantom-07/updates_drivers/a0df616e-3d37-41d2-9464-d04a43c53193/
