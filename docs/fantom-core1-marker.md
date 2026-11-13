# Fantom-07 1.08 CORE1 marker experiment

2026-11-12. Built locally, checked in isolated ARM emulation, then **flashed and
observed returning the exact marker over external USB MIDI on Jacob's Fantom-07**.
See the [hardware trial and two-stage kit](fantom-core1-flash-trial.md).
The original folder below is payload-only. This is a
small step toward [CORE0 key recovery](fantom-rom-dumper-plan.md): prove a
specific bmc0 CORE1 patch and its external reply path before accessing ROM or DMA.
No key has been recovered by this experiment.

## Exact change

`tools/build_fantom_core1_marker.py` accepts only the stock Fantom-07 1.08
`FNTM0_UPA.BIN` with SHA256
`44993228fc0b407a6b198d8ef3da953f861393d929f47cce08ce1a79fc108f75`.
It changes only tar member `./_tmp/bmc0_MI078_C1A_up.bin`, whose stock SHA256 is
`0de38e6406b14701bfc93fa7491cc2dda8e8ac590cb44caae6702d7b494d6472`.
The other five members, including both encrypted CORE0 images, stay byte-identical.
The tool never opens a device, runs the vendor updater or transmits MIDI.

The stock debug-read helper at `6102d2e6..6102d431` is replaced with a 38-byte
Thumb stub, its constant packet and a stock function pointer, followed by NOPs
to fill the original 332-byte region. The next function at `6102d432` is preserved.
The raw C1A offset is `6d2e6`. A whole-image branch/veneer/pointer candidate scan
found one immediate branch to the entry, `6102d602`, and no aligned Thumb pointer
or MOVW/MOVT/BX candidates to that entry. A separate immediate-branch and aligned
pointer scan covering the entire replaced region also found only that entry
branch. This is not proof of every indirect use.

Assembly lives in `tools/fantom_core1_marker.s`. It saves r4/lr, loads an inline
constant packet, calls stock packetizer `0111f0be` via Thumb pointer `0111f0bf`,
then restores r4/pc. It leaves r4–r11 and the incoming SP intact, with eight-byte
stack alignment at the call. A two-byte link prefix handles the original entry's
halfword alignment; the prefix is removed after linking. The constant is in
code memory; the packetizer only reads it. No new code cave, SRAM allocation,
address decoding, ROM read, peripheral access or DMA operation is introduced.

For this build the read service temporarily returns one fixed word `4f534352`
regardless of its input. The saved expected SysEx reply is:

```text
F0 41 10 4E 13 00 00 00 00 04 0F 05 03 04 03 05 02 57 F7
```

This has the stock read-reply framing and checksum; it represents a marker,
not an actual read of the address encoded in that framing. Roland's type3
packetizer generates the following seven little-endian internal words:

```text
34 F0 41 10   34 4E 13 00   34 00 00 00   34 04 0F 05
34 03 04 03   34 05 02 57   35 F7 00 00
```

## Container integrity

The flat Fantom C1A has a 32-byte prefix, with its first u32 equal to file length
minus 48. The CRC word is at file length minus 52 and is `zlib.crc32` of every
preceding byte. The final 48 bytes are an identification footer. Both stock
bmc0 (`28009c` CRC offset, `3538095f` CRC) and bmc1 (`3c563c`, `d86934de`)
independently match. This outer convention does not turn the flat image into
the QSPI directory container handled by `tools/qspi_c1.py`.

The builder recomputes the bmc0 CRC and preserves the prefix, length and footer.
Byte comparisons restrict C1A changes to the 332-byte helper and four-byte CRC.
The patched member SHA256 is
`e387a53a0bfd040f70b380f7f2f7464c1353bdbec1380bc8eda445b1a7f2337e`;
the resulting UPA SHA256 is
`598a1a2be7db21461adadbd37eda4d7411aae480992f6d8f42b24dc097dd03e1`.
The tar is repacked; unchanged member contents do not imply unchanged tar headers.

## Build and checks

Use the repository's pinned Python requirements and installed GNU Arm tools:

```sh
.venv/bin/python tools/build_fantom_core1_marker.py \
  local/fantom-07-onscreen-probe-v108/stock-files/FNTM0_UPA.BIN \
  local/fantom-07-core1-marker-v108
.venv/bin/python -m unittest discover -s tests -p test_fantom_core1_marker.py -v
.venv/bin/python tools/core1_sysex.py \
  local/fantom-07-core1-marker-v108/expected-reply.syx
```

The output directory must not exist. Generated vendor-derived images remain in
ignored `local/`; source, tests and this documentation contain no key or vendor
firmware image. The output includes a manifest, candidate UPA, exact stock UPA
under `restore/`, compiled stub, saved request and expected reply. Keeping stock
bytes is useful for comparison; it does not establish that recovery will work
if the modified BMC fails to boot.

Seven tests passed. Unicorn 2.1.4 with the Cortex-M7 CPU executes the actual stub,
stock packetizer and software enqueue, plus the original service wrapper and
memory-clear routine for the request test. Only task signalling and the full-queue
logger are mocked. Checks cover preserved registers/SP, code read-only access,
SRAM changes confined to stack/scratch/queue regions, empty and wrapped queues,
and full-queue rejection if the logger returns. Poison input pointers include
the candidate ROM address; ROM, DMA, shared-ring, NVIC and other MMIO addresses
are unmapped. This is routine execution testing, not full BMC emulation, a
concurrency proof or evidence of the peer receiving anything.

On this Mac the emulator requires execution outside Codex's restricted sandbox;
inside it, even a minimal CPU-model smoke test exits with SIGILL. A second
instrumentation issue was isolated: `UC_HOOK_MEM_WRITE` makes the stock Thumb
memory-clear IT loop overrun its 256-byte buffer in Unicorn 2.1.4. The same stock
routine clears exactly 256 bytes without that hook. These tests therefore use
memory protection and before/after SRAM comparisons, with a code hook for
registers, stack bounds and calls. They do not trace every transient SRAM write.

OMP/Qwen on the Mac Studio supplied a tool-free review. Its initial alignment
concern and claimed four-byte PUSH/POP sizes were checked against actual emitted
code and rejected: these PUSH/POP instructions are two bytes each, marker data is
at `6102d2f4`, and the literal word is aligned at `6102d308`. The emulator executes
the literal load and actual packetizer call successfully. The model's eventual
no-concrete-defect conclusion adds no hardware validation.

## Controlled request and remaining hardware gates

The offline-tested request is saved as `request.syx`:

```text
F0 41 10 4E 11 00 00 00 00 00 00 00 00 00 F7
```

It specifies an aligned zero offset and **zero read count**. Execution through
stock wrapper `6102d604` reaches the stock helper and exits without MMIO access
or a reply. With the patch, the same wrapper reaches the marker reply. This
avoids requesting a real read if the patch is absent, for the tested bmc0 build.
It does not establish forwarding from an external USB/MIDI port to that wrapper.
Neither the request nor arbitrary internal words have been sent to hardware.

The two-stage procedure, read-only board1 handoff and successful marker flash
are now documented in the [hardware trial](fantom-core1-flash-trial.md).
One zero-count request over external USB MIDI produced two exact marker replies,
proving this patch executes and has a working external path. Recovery after a
failed custom boot is still untested. For other attempts, silence is inconclusive: a wrong image/core,
unforwarded command, disabled output gate or queue pressure can all suppress it.

**This UPA is a BMC/board2 experiment.** It is different from the persistent-SSH
Linux/board1 installer, whose instructions say to reboot before board2. Applying
those SSH-only instructions would not install this BMC change. No Linux updater
or `_DATA_FNTM0` is included here, so this folder alone is not a complete
three-file stock update workflow. Do not mix it casually with the previous SSH
flash-drive contents. Use the complete first-trial kit and its instructions for
the hardware trial; it supplies its own read-only Linux/board1 handoff. No
automatic flashing is performed by either builder.
