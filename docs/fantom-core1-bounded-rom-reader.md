# Fantom-07 bounded ROM diagnostic

2026-11-12. **The bounded diagnostic succeeded on the actual Fantom-07.** Its
self-test, boot-vector read and B6 entry read passed. The recovered material
decrypts both Fantom CORE0 images with exact plaintext CRC matches. See
[recovery and validation](fantom-core0-key-recovery.md). The implementation and
pre-trial checks below retain their declared limits.

## Implementation

`tools/fantom_core1_rom_reader.s` replaces the same read-service entry with a
10-byte Thumb trampoline. Its 724-byte body occupies checked zero-filled ITCM at
`0113d000`, within a reserved 1024-byte interval. The source copy at
`0113cf08..0113cf3f` is untouched. The scatter handler at `610000b4` zero-fills
destinations without reading its source argument; its apparent source pointers
into padding are not copy operations. File zeros and scatter checks do not prove
dynamic ownership of all padding. The new body has now executed successfully
at this placement during marker, snapshot, self-test and bounded-read operations.

The old helper interval `6102d2e6..6102d431` is exclusively repurposed for the
trampoline and permanent diagnostic data: fault latch `6102d330`, test pattern
`6102d340`, and 128-byte bounce region `6102d380..6102d3ff`. A whole-region
branch/pointer candidate scan in the marker study found no external entry other
than the function start. No DMA destination is on the stack. The new function
reserves 152 bytes including saved registers, preserves r4–r11/SP and restores
PRIMASK before using the same stock reply packetizer. That is 64 more local
stack bytes than the original helper; peak interrupt nesting is not emulated.

The builder accepts only the pinned stock UPA and preserves component lengths,
footer and all five other members. In bmc0 C1A, only the helper, ITCM reservation
and outer CRC may differ. Current diagnostic UPA SHA256:
`e1d48b363427a43a752a7dc5c5224b1985c48a59629f9d02a5709336df38cafb`.

## Requests and output

The fixed read-command header remains `F0 41 10 4E 11`. The diagnostic interprets
the count field as an operation and validates the exact payload length, count
width, permitted address, checksum and terminator. Every supported wire count is
less than four. Executing each request against the original stock bmc0 helper
returns without any peripheral read, including the candidate-entry request.

| Client operation | Wire count | Address field | Effect |
|---|---:|---|---|
| marker | 0 | 0 | Exact original constant reply; no peripheral access |
| snapshot | 1 | channel 0..7 | Read DMA global/channel registers, CPUID and CCR; no DMA writes |
| selftest | 2 | 0 | Copy one known word to the permanent bounce region |
| vectors | 3 | 0 | DMA-read exactly two words from `01200000` |
| key | 3 | `34c0` | DMA-read exactly six words from `012034c0` |

The marker reply stays 19 bytes. Other reports are eight nibble-encoded words in
75-byte, checksummed SysEx replies. Snapshot words are identifier/channel,
global control, channel A/B/source/destination, CPUID and CCR. Transfer reports
contain a status/channel word, exact source address and up to six data words.
Unused data words are zero. The client rejects wrong framing, checksums, source
windows, padding and inconsistent duplicate results. Raw entry bytes are written
to a new mode-0600 local file; JSON/stdout contains status and a hash, not those
bytes. Independent validation is required before calling ROM-table material a
usable key; those checks now pass on both Fantom images in the recovery note.

## DMA derivation and bounds

The [MC-101 reference hook](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/src/sysex_hook.s)
supplies a reported cross-bus ROM route through `40001000`. It is a research lead,
not proof of Fantom channel ownership. Fantom's own QSPI driver selects this
controller for state `40010000` and `40030000` for the other state. Its observed
CORE1 startup initializes state `40010048`, selecting the latter. The separate
DSP linked-list DMA at `40031120` is not substituted for this controller.

The register fields match the primary
[Linux Milbeaut HDMAC driver](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/master/drivers/dma/milbeaut-hdmac.c):
enable bit31, software trigger bit29, burst type23:20, block count19:16,
transfer count15:0, width27:26 and stop status18:16. Fantom QSPI code independently
uses the count-minus-one convention and tests stop status5. A/B values
`a0000000`/`08000000` select one 32-bit software block transfer, with both count
fields zero. Each transfer must advance source and destination by exactly four.

The diagnostic requires the controller already enabled, data cache disabled and
an all-zero channel A/B/source/destination configuration. It searches channels
7 down to 0 and rechecks the chosen configuration before each word. It never
writes the global controller register, enables channel interrupts or changes
another configured channel. The self-test verifies the known word and all
remaining 124 bounce bytes. The same guards are checked after every ROM word.

Only the selected channel is programmed. A terminal completion permits clearing
its registers back to their original zero state. A timeout clears **only EB**,
leaves the other register values intact and latches further DMA off until reboot.
The permanent buffer remains allocated even if a late transfer completes. Error,
unexpected address advance, guard failure or pattern mismatch also latch DMA
off. Each word has at most 8192 poll iterations. Snapshot and marker operations
remain available after a latched error.

These checks do not establish a cross-core ownership lock. Another core could
configure a channel between the checks and use; try this only while the synth is
idle. A stalled bus read is not bounded by a software loop counter. The tests
establish software behavior under the explicit hardware model, not physical bus
access, actual controller ownership or recovery after a hung transfer.

## Build, tests and trial

```sh
.venv/bin/python tools/build_fantom_core1_rom_reader.py \
  --stock local/fantom-07-core1-marker-v108/restore/FNTM0_UPA.BIN \
  --passphrase-file local/fantom-ssh/update-passphrase.txt \
  --output local/fantom-07-core1-rom-diagnostic-v108
.venv/bin/python -m unittest discover -s tests -p test_fantom_core1_rom_reader.py -v
```

Nine reader/protocol tests passed. They execute the real trampoline, reader and
stock packetizer/enqueue in Unicorn 2.1.4, with ROM deliberately unmapped to the
CPU. A fake HDMAC supplies synthetic ROM bytes only via the programmed DMA
destination. Tests check exact four-byte transfers, both fixed windows, preserved
registers/SP/PRIMASK, read-only snapshots, cache/disabled/busy guards, timeout,
hardware error, address/count mismatch, bounce corruption, pattern mismatch,
error latching, configured-channel preservation and all requests' behavior on
the unmodified stock helper. The scheduler is mocked. This is not full BMC
emulation. Seven flash-kit regression checks also passed after extracting the
shared kit writer; its original marker hash and input guards remain in force.

Qwen on the Mac Studio reviewed the exact assembly. Its proposed guard-loop
overflow was disproved by the bounds (last load covers bounce bytes124..127).
Its nibble-order concern contradicts the stock decoder and the hardware-proven
marker format. Its suggestion to clear all channel registers on timeout was
rejected: DMA may not have reached a terminal state, so only EB is cleared and
further transfers are latched off. The timeout and latch paths are execution-tested.
Its snapshot concern was checked with nonzero channel7 state and a configured
channel skip test. The model review is not hardware validation.

Use the kit's [README](../tools/fantom_core1_rom_README.txt) for the two-stage
installation. Its new board1 success label is
`OSCAIRN BMC CHECK OK: ROM DIAGNOSTIC bmc0 CORE1`. No SSH key or Dropbear file is
added. The firmware is local/ignored and has not been published. The earlier
marker kit remains the known-working custom image; stock restoration is untested.

After normal boot, run marker and snapshots first, then the one-word self-test.
Only after those results are checked should vector and candidate-entry operations
be attempted. The client is `tools/fantom_core1_rom_probe.py`, using the existing
Python 3.13 environment with mido/python-rtmidi. For example, from the repo:

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/fantom_core1_rom_probe.py \
  marker --out local/fantom-live-recovery/rom-reader-marker.json
```

Further probes depend on those observed results. Material from the candidate
entry still requires packing and independent Fantom ciphertext/plaintext integrity
validation before it can be called the usable CORE0 key.
