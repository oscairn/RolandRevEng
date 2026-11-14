FANTOM-07 v1.08 — BOUNDED CORE1 ROM DIAGNOSTIC

This follows the marker package that was flashed and returned its exact response
over USB MIDI. It preserves that marker command and adds a DMA register snapshot,
a one-word self-test and two fixed read windows: 8 vector bytes at 0x01200000,
and the 24-byte candidate B6 entry at 0x012034c0. It is not an arbitrary memory
reader. The candidate entry still needs independent decryption validation.

REQUIREMENTS AND SCOPE

Use the owner's Fantom-07 running the verified v1.08 application with persistent
SSH already installed. No key file, Dropbear binary or _DATA_FNTM0 is needed.
The board1 step only checks the existing installation and this kit's UPA hash.
It does not change Linux, SSH keys, startup files, user data or partitions.

The new DMA path has offline execution tests with simulated hardware. It has
not yet been tested on the physical Fantom. It uses a previously zero-filled
ITCM region and data space inside the replaced debug helper. Dynamic ownership
of the padding and a cross-core DMA lock have not been established. Zero DMA
channel registers are a configuration guard, not proof that another core can
never use that channel. Save current work and do the trial while idle.

FLASH-DRIVE PREPARATION

Back up the USB drive's contents. Use a drive already formatted by the Fantom.
Remove the old updater files from its root, then copy ONLY the two files INSIDE
this kit's flash-drive/ directory to the drive's root:

    update_fntm0
    FNTM0_UPA.BIN

Do not copy enclosing folders or the ZIP. Remove any old _DATA_FNTM0. Do not
mix flash-drive/ with restore-drive/ or the preceding marker/SSH package files.
Keep the known-working marker flash kit on the Mac as well as this kit's stock
restore-drive/ files.

INSTALL BOTH STAGES

1. With power off, connect the drive to USB MEMORY. Hold WRITE and power on;
   release WRITE once the board1 insert-memory screen appears.
2. Require this exact success line before moving the drive:

       OSCAIRN BMC CHECK OK: ROM DIAGNOSTIC bmc0 CORE1

   If CHECK FAILED appears, do not proceed to EXT DEVICE. The stock recovery
   wrapper can display board1 End after a failed child script; End alone is
   insufficient. The board1 checker itself has not flashed BMC firmware.
3. After CHECK OK and board1 End, KEEP POWER ON and move the same drive to
   EXT DEVICE. Wait through Running Update. Do not interrupt an active update.
4. After board2 End, power off, remove the drive and start normally. Reconnect
   USB Ethernet for SSH and USB COMPUTER to the Mac for MIDI. No on-screen
   version or splash change is expected.

AFTER NORMAL BOOT

The agent will run these in order while capturing replies:

    marker -> register snapshots -> selftest -> vectors -> candidate entry

All requests use a wire count below four, so the unmodified stock bmc0 read
helper exits without a peripheral read. The ROM diagnostic assigns its own
meaning to those counts. Do not send larger stock memory-read requests.

The DMA self-test must pass before a ROM read is attempted. Transfers use one
32-bit word at a time, a permanent 128-byte bounce region, exact address-advance
checks and guard words. The code requires an already-enabled controller and
an all-zero channel configuration, never enables/resets the controller globally,
does not configure interrupts, and restores zero channel state after terminal
completion. Each word has an 8192-iteration polling bound. A timeout clears
only the channel enable bit and preserves its other registers; an error latches
all further DMA commands off until reboot. The permanent buffer avoids returning
a stack buffer while DMA might still complete later.

The code declines DMA if the CPU's data cache is enabled. It does not install
fault handlers or attempt a direct CPU load from the candidate ROM range. A
poll-iteration bound cannot guarantee a wall-clock timeout if the hardware bus
itself stalls. Normal boot, the new ITCM code placement and DMA access still
require physical observations. The preceding marker result alone does not
validate those new parts.

ROM entry bytes, if obtained, are written only to an ignored local file with
mode 0600. The client prints status and a hash rather than the entry bytes.
No recovered key is included in this kit or public source.

RESTORE

restore-drive/ contains the exact stock v1.08 BMC UPA and its matching read-only
board1 checker. Replace BOTH root files on the USB with that pair and use the
same two-stage procedure to attempt stock BMC restoration. Alternatively, the
previous marker kit is the known-working custom image. Neither restores Linux
or removes SSH. Recovery after a failed BMC image or DMA hang has not been
demonstrated; do not initialize the keyboard or perform a factory reset.

Firmware flashing can leave the keyboard unable to start. Use stable power.
The physical port sequence is Roland's standard two-stage process; this is a
custom research payload, not an official Roland release.
