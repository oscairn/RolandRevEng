# Fantom-07 CORE0 ROM-reader preflight

**Completed follow-up: [bounded reads recovered usable B6 material and validated
both Fantom CORE0 decryptions](fantom-core0-key-recovery.md).** This note retains
the earlier planning stage.

2026-11-12. Persistent Linux SSH is now working after reboot. BMC CORE0 key
recovery still requires an actual applicable ROM/key artifact or a proven BMC
memory-read path. This pass maps a bounded next experiment; it does not patch,
flash or execute BMC code, and does not recover a key.

Later on the same date, the [marker hardware trial](fantom-core1-flash-trial.md)
succeeded: a patched bmc0 CORE1 helper returned its exact constant through external
USB MIDI, with normal startup and persistent SSH retained. The planning observations
below precede that trial. A ROM-read mechanism and the CORE0 key remain unresolved.

## Pinned CORE1 anchors

Input: bmc0 CORE1 payload SHA256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
The read-only checker is `tools/fantom_rom_dump_preflight.py`.

* IRQ6 call site `01102958` supplies one ring word by value in r0 to `0111ed12`.
  That wrapper disables interrupts, enqueues the word, schedules RXDT/task3 and
  unconditionally enables interrupts. It is a provenance/ABI anchor, not a suitable
  place for a lengthy DMA poll or whole-ROM transmission.
* Stock outgoing packetizer `0111f0be` takes bytes/count in r0/r1 and selects
  output word type3. Its software queue has 511 usable slots. External delivery
  through the opaque peer still needs live proof; the existing transmit study
  records the backpressure and priority limitations.
* The raw ITCM zero tail begins at payload offset `3cf07`, but 56 zero bytes at
  `0113cf08..0113cf3f` are copied to the shared-ring header during startup.
  Excluding this source leaves candidate `0113cf40..0113ffdf`, length `30a0`.
  This is zero-filled placement space, not proven free runtime memory.

## Two false shortcuts to avoid

A raw aligned word at `01104208` equals `0113f3c1`, which resembles a Thumb
function pointer into that zero tail. It is actually the four-byte instruction
`UBFX r1,r1,#0,#20`. Similar numerical matches must not be promoted to pointers
without checking their code/data context. The first scratch scan's apparent
references therefore do not by themselves establish live code in the zero area.

Conversely, a real literal load at `01122ae6` reads `40001000` and follows a
branch to the store at `01122ad0`, assigning object/state field +30. The surrounding
setup at `01122ab2` selects this branch for the `40010000` state base; the other
branch supplies `40030000`. Nearby routines implement flash identification/SFDP
handling. This supports investigating a stock peripheral-driver path, **not**
assuming the MC-101 dumper's DMA channel1 is free on Fantom. Channel ownership,
cross-core users and safe completion/restoration are unresolved.

## Smallest useful next hardware experiment

Build an **echo-only** CORE1 diagnostic before a ROM reader. One candidate is the
existing debug read helper region `6102d2e6..6102d431` (332 bytes), ending before
the next function at `6102d432`. Its only established service dispatch in this
trace is the read-command path ending in a tail branch at `6102d602`.

A small replacement could ignore address/count and return a fixed, clearly
identified marker through the existing reply packetizer. Its buffer could be
constant data inside that replaced region, avoiding a new ITCM allocation and
DMA entirely. First verify its caller ABI and return behavior, stack/register
preservation, bounded packet size and which physical BMC/image receives the
request. No proposed wire command has yet been sent. This replacement would
temporarily change that debug service; it is not claimed ready for flashing.

Only after a marker is observed should a second version read a bounded ROM
window. Establish memory accessibility, DMA channel/scratch ownership if needed,
timeouts, output routing and a recovery path before doing so. The MC-101-reported
ROM is `01200000..01203fff`; candidate B6 entry is 24 bytes at `012034c0`.
Those remain BMC-side candidates, not Linux /dev/mem addresses. Validate any
recovered material against actual Fantom ciphertext and independent plaintext
structures before claiming the key is correct.

The Fantom C1A wrapper differs from MC-101's QSPI directory layout, but its outer
length/CRC convention is now verified against both stock Fantom images. The
leading word is **file length minus 48**, not a payload size measured after the
32-byte prefix. The CRC is the word at **file length minus 52**, calculated over
all preceding bytes; the final 48 bytes are an identification footer. Stock
bmc0 CRC `3538095f` and bmc1 CRC `d86934de` both match `zlib.crc32` exactly.
The earlier interpretation of 16 unexplained trailing bytes was incorrect.
This establishes a reproducible container check, not hardware updater acceptance.

The [marker experiment](fantom-core1-marker.md) now implements this bounded
replacement, with an offline-tested builder, stock restore payload and emulated
execution checks. It has not been flashed and does not recover the CORE0 key.

## Checks and local-model review

```sh
python3 tools/fantom_rom_dump_preflight.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_fantom_rom_dump_preflight.py -v
```

Three tests passed, including protected zero-initializer bounds, alignment,
unsupported-image rejection and the actual pinned instruction/scatter anchors.
The checker verifies its input remains unchanged. Detailed output is ignored at
`local/fantom-live-recovery/rom-dumper-preflight.json`.

OMP/Qwen on the Mac Studio returned a bounded review in 30.8 seconds. Its IRQ,
ownership and bridge cautions were checked against the stock instructions. Its
suggestion to read a peripheral ID/GPIO for initial proof was narrowed to a fixed
constant reply, avoiding any unknown register access. Its interpretation of the
zero/scatter region was not accepted as a free-space or allocation proof. The
local review is evidence of an analysis pass, not hardware validation.
