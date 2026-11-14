# Program RAM read path: ReadDspProg and the raw/float/fixed literal readers

2026-11-13. Static Capstone analysis of the pinned bmc0 CORE1 payload
`local/b0c1a.bin`, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
This study answers one part of the load-route question (feasibility-assessment
item A1, "read it back"): the stock firmware does contain a program-RAM *read*
path, and this note maps its geometry, its DMA coupling and its callers. Nothing
executed; no instrument was contacted.

## Method

The loader map's write-path study (`kernel-audio-abi-study.md`) established the
aperture table at `0x113a954` and the DMA state byte at `0x200847f0`. This run
disassembled the two driver functions that read through the same aperture table
and the literal-read functions beside them, then bounded their callers. New tool
`tools/program_read_study.py` pins the image, asserts the disassembly anchors
below, checks the port tables word for word, and models the read geometry.

Command producing the evidence below:

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  <repo>/.venv/bin/python \
  tools/program_read_study.py local/b0c1a.bin --dsp 4 --address 0x4020 --count 510
```

Pasted tool output (trimmed to the structure fields; addresses shown in hex here,
the JSON prints decimal):

```json
{
  "payload_sha256": "6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154",
  "functions": {"ReadLiteralRaw": 18020072, "ReadDspProg": 18020172,
    "ReadLiteralFloat": 18022382, "ReadLiteralFixed": 18022490,
    "ReadDspMemoryFloat": 18023008, "ReadDspMemoryFixed": 18023252,
    "GetDspProgAdrs": 18020650},
  "port_tables": {"float": 18065980, "fixed": 18066008, "raw": 18066036,
    "memory_float_kinds": 18066112, "capacities": 18066160},
  "sample_read": {"dsp": 4, "byte_address": 16416, "byte_count": 510,
    "aperture": 1099431936, "port_command": 536887328,
    "words_returned": 128,
    "steps": [
      {"kind": "full_word_tail", "source": 16924, "source_read_bytes": 4,
       "words_returned": 1, "shift_bits": 0, "bytes_beyond_count": 2},
      {"kind": "dma_queue", "source": 16416, "source_read_bytes": 508,
       "words_returned": 127}],
    "descriptors": [{"word_count": 127}]},
  "sample_literal": {"dsp": 4, "byte_address": 16417, "width": 2,
    "port_command": 536887329, "alignment_shift_bits": 0}
}
```

(Decimal: ReadLiteralRaw 0x0112f6e8, ReadDspProg 0x0112f74c,
ReadLiteralFloat 0x0112ffee, ReadLiteralFixed 0x0113005a,
ReadDspMemoryFloat 0x01130260, ReadDspMemoryFixed 0x01130354,
GetDspProgAdrs 0x0112f92a; tables 0x113aa3c/0x113aa58/0x113aa74/0x113aac0/
0x113aaf0; sample aperture 0x41880000, command 0x20004020, sources 0x422c and
0x4020.)

## ReadDspProg (0x0112f74c): `void (int dsp, uint byte_adrs, uint byte_count, uint *out)`

Entry checks and gates (Capstone, from `tools/core1.py`):

```
0112f74c  2de9f041  push.w  {r4, r5, r6, r7, r8, lr}
0112f752  0728      cmp     r0, #7          ; dsp < 7
0112f766  41ea0203  orr.w   r3, r1, r2
0112f76a  13f0010f  tst.w   r3, #1          ; address|count even
0112f780  b8f1000f  cmp.w   r8, #0          ; output pointer nonzero
0112f786  002a      cmp     r2, #0          ; count nonzero
0112f78e  314b      ldr     r3, [pc, #0xc4] ; 0x113a954 (aperture table)
```

The function shares `GetDspProgAdrs`'s aperture table: `r3 = table[dsp]`,
`r6 = r3 + r1` is the byte window, `r2 = 0x113aa74` is the raw literal port
table, and `r8 = out`. Both the address and the count must be even; the output
pointer and count must be nonzero. There is no capacity or window-bound check in
this body beyond the even checks; the 19-bit address masking happens per command.

### Read ordering: tail halfword first, then the bulk

At `0112f7a0` the firmware tests `r6 & 2` — whether the **byte address** is
word+2, not whether the count is odd-halfwords (that test, `r5 & 2`, comes later
at `0112f7da`). For a word+2 address it issues one width-2 raw read of the first
two bytes and advances. This mirrors the write path's leading raw edge, but with
the port command assembled at `0112f7aa..b6` as
`(byte_adrs & 0x7ffff) | 0x20000000` — bit 29 set, where the write path's raw
writer uses `0x30000000`-style width encoding. The busy-wait on
`0x41100008 & 0x80000000` and the port+4 data fetch match `ReadLiteralRaw`
exactly; the returned halfword is stored through `str r1, [r8], #4`.

The count's own low-bit test follows at `0112f7da`: if the remaining count still
has bit 1 set, the tail block (`0112f7e0..872`) reads one **full 32-bit word** at
`cursor + (remaining & ~3)` and stores it **unshifted** at output slot
`((remaining+3)>>2)-1` (`str r0, [r8, r4, lsl #2]`; there is no shift in this
path — the `lsr` at `0112f7ce` belongs to the leading-halfword path). For the
510-byte sample the tail source is `4020+508 = 422c` and the slot is 127, so the
read returns the complete stored word there, including whatever the hardware
holds in the two bytes past the count. This is the read-side twin of the write
path's trailing raw edge, reversed: the write clears the loaded word's low
sixteen bits (`bfc r3, #0, #0x10` at `0112f620`) so it never disturbs bytes past
the count, while the read returns the whole word unchanged.

For the FETDRIVE-shaped sample (DSP 4, address 0x4020 word-aligned, count 510):

| Step, in actual order | Source bytes | Returned words |
|---|---|---|
| Full trailing word (count bit 1) | `4020+508..511` = `422c..422f` | 1, the complete stored word, unshifted |
| Bulk 508 bytes, word-aligned | `4020..4227` | 127 words |

The bulk path at `0112f878` (`cmp r5, #0x40`) reaches the shared DMA list when
the remainder after the edges is at least 64: it enters the same `0112f290`
listed-memcpy builder and the same `0x200847f0` state machine as the write path
(`0112f87c..f26`), with the same 4095-word descriptor cap and completion callback
`0x0112f42d`. Unlike the write path, the read bulk copy is byte-count-preserving:
508 requested bytes copy 508 source bytes (`0112f8a4` passes `r2=r5, r1=r6` with
no edge trimming). The builder requires all three arguments 4-aligned
(`tst r3, #3` at `0112f298`), and the read's source is the window cursor, so a
bulk-sized read from a word+2 address would take the builder's assertion path;
the model rejects that combination. Sub-64 remainders take the CPU word loop at
`0112f8ea..f26`, which copies words sequentially (one prologue word for odd word
counts, then two words per iteration) through unaligned-tolerant LDR/STR.

Completion: after queueing, the reader polls `state == 2` and then event bit 4
at `0112f8d6..da` before resetting state to 0 at `0112f8e4`. So a queued read
does not return until the DMA completion IRQ has fired — synchronous, like the
write path's wait-enabled variant. State 0 (idle) takes the `0112f89c` start
branch, sets state 1, starts the list through `0x0112f3ba`, and then also waits.
State 2 (already started by another writer) polls the same event without
restarting; the read then waits for that earlier transfer's completion, which is
correct only under the stock single-owner discipline.

## ReadLiteralRaw (0x0112f6e8): `uint (int dsp, uint byte_adrs, uint width, bool align_right)`

Entry gates: `dsp < 7` and `(width - 2) < 3` unsigned — widths 2, 3, 4. The
command is `(width << 28) | (byte_adrs & 0x7ffff)` (at `0112f71a..726`,
`ubfx r1, r1, #0, #0x13; orr.w r1, r1, r2, lsl #28`), written to `port[dsp]+0`.
The busy-wait and `port+4` data load follow. When the `align_right` argument
is false the function returns the loaded word unshifted (`cmp r3, #0; it eq;
popeq` at `0112f73c..740`, for every width); when true it shifts right by
`(4-width) << 3` (`rsb.w r1, r2, #4; lsls r1, r1, #3; lsrs r0, r1` at
`0112f742..748`) — 8 bits for width 3, zero for width 4, and 16 bits for
width 2, so a right-justified halfword lands in the low half. `ReadDspProg`'s
leading-halfword path shifts by the same 16 bits unconditionally.

Literal port tables verified word for word this run:

| Table | Address | DSP 0..6 values |
|---|---|---|
| float read | `0x113aa3c` | `41104400 41105400 41106400 41107400 41108400 41109400 41102400` |
| fixed read | `0x113aa58` | `41104600 41105600 41106600 41107600 41108600 41109600 41102600` |
| raw read | `0x113aa74` | `41104700 41105700 41106700 41107700 41108700 41109700 41102700` |

These are the same ports the write path uses (`BMC DSP packet and loader map.md`
section 6): float `+400`, fixed `+600`, raw `+700` per DSP base. Reads return
through the same port+4 data register, so a literal read costs the same command
word as a literal write, with bit 29 of the command apparently serving as the
read direction flag for the program-aperture window. The write path's `WriteDspCoefFloatWithEnv` at `0113047c` writes slot commands
with bit 29 clear plus wait/EnvTC fields, so bit 29 is specific to the
program-window literal ports, not a universal read flag — that generalization
is bounded to the two port families compared here.

`ReadLiteralFloat` (0x0112ffee) and `ReadLiteralFixed` (0x0113005a) share the
same command assembly with their own tables and return `vldr s0, [r0, #4]` /
`ldr r0, [r0, #4]` respectively; the float variant returns through `s0`, so its
ABI is hard-float like the writers.

## Data-memory (windowed) readers

`ReadDspMemoryFloat` (0x01130260) takes `(int dsp, DspDataMemoryType kind,
uint index)` and dispatches through the kind table at `0x113aac0`:

| Kind | Port table | DSP 0..6 bases | Capacity pointer | Capacities |
|---|---|---|---|---|
| 0 | `0x113acb8` | `41400000 41500000 41600000 41700000 41800000 41900000 41200000` | `0x113acd4` | 2048 ×7 |
| 1 | `0x113ad60` | `41410000 41510000 41610000 41710000 41810000 41910000 41210000` | `0x113ad7c` | 2048 ×7 |
| 2 | `0x113ae08` | `41420000 41520000 41620000 41720000 41820000 41920000 41102400*` | `0x113ae24` | 1536 ×6 |
| 3 | `0x113ae40` | `4113c000` (all) | `0x113ae5c` | 256 ×6 |
| 4 | `0x113abe0` | `411d0000 411d8000 41430000 41530000 41630000 41730000 41102400*` | `0x113abf8` | 512 ×6 |
| 5 | `0x113ac10` | `41114000 41118000 4111c000 41120000 41124000 41128000 41110000` | `0x113ac2c` | 1024 ×7 |

(*) The table's last entries for kinds 2/4 read `0` in my dump for DSP6 and one
spare slot; the DSP6 row of kind 2 is `0` in the table and the dispatch checks
`cmp r3, #0` before using it, so kind 2/4 reads on DSP 6 (MDSP) would fail the
zero check and take the assertion path — DSP 6 has no kind-2/kind-4 window per
this table. Kinds 0/1/5 have DSP 6 entries.

The capacity pointer table at `0x113aaf0` holds one pointer per kind; the
kind-4 pointer is `0x113abf8`, whose table reads 512 ×6 followed by two
float-bit-pattern words (my dump reads those two words as capacities, which they
are not — the bound check only ever indexes the six DSP rows). The verified
read bound: at `011302c8` the firmware compares the index against the selected
capacity and raises via the assertion helper when it exceeds it, before
computing the port fetch at `011302d0` (`addhi r0, r3, r2, lsl #2`). The kind-2
1536 and kind-3 256 capacities are the circular/direct data windows; kinds 0/1
hold 2048 per DSP here while `coefficient-envelope-and-completion-study.md`
gives the live coefficient banks as 2048/2048/1024/1024/1024/1024 — the read
driver bounds every DSP against a single fixed 2048 rather than a per-DSP table,
and I did not reconcile that with the envelope study's per-DSP sizes; the driver
bound is therefore conservative, not proof of bank size.

Kinds 0 and 1 branch earlier at `011302a2..a8` (`cmp r1, #0 / cmpne r1, #1`)
into a dedicated path at `011302ea` before the general table dispatch — the
circular data path and the direct/window path are distinguished inside the
driver, consistent with `transfer-spaces-study.md`. The `ReadDspMemoryFixed`
variant at 0x01130354 mirrors the float one with the fixed tables.

## Callers and the read-back route

`ReadLiteralRaw` has exactly four direct BL callers in the mapped low region
(found by scanning every halfword with `core1.md`, matching
`core1_xrefs.py`'s BL decoder):

| Site | Enclosing function | Purpose |
|---|---|---|
| `0x01133bb4` | `SetMuteMode` 0x01133b38 | First-packet halfword (the mute scan's header read) |
| `0x01133bda` | `SetMuteMode` | Each scanned halfword |
| `0x01133220` | program-literal `ChangeDspMemoryAdrs` caller, start 0x011330ae; reads through `GetDspProgByteAdrs` (assertion at `0x610b98f3`) | Reads the current program-literal value |
| `0x01133698` | DRAM-IO address-change method, start 0x0113353c; its other branch asserts `ChangeDramIO_RW_Adrs` (`0x610ba163`) and its helper names `GetDramioProgByteAdrs` (`0x610b9943`) | Reads the current DRAM-IO address |

`ReadDspProg` itself has **no direct BL, no immediate B/BL and no
MOVW/MOVT/BX veneer anywhere in the image** — `tools/core1_xrefs.py
local/b0c1a.bin 0x0112f74c` returns all three candidate lists empty, and a
halfword scan for the Thumb pointer `0x0112f74d` also returns nothing. So the
only established invocations are through vtable/computed references, i.e. the
function exists and is sound, but this image does not statically name a caller.
The mute manager (`SetMuteMode`) already demonstrates the pattern: it reads
program RAM through `ReadLiteralRaw` in its scan loop (`01133bcc..be4`), so
**in-the-manager program-RAM reads are exercised stock behavior**, but a
whole-program readback call site is not identified in this pass.

`ReadLiteralRaw`'s mute-scan use is the strongest existing evidence that reads
through the literal port return live program-RAM content: `SetMuteMode` scans
the loaded FETDRIVE program's first packet through it and muting works on the
unit per the earlier studies (static chain; the hardware act of muting was not
measured by this project).

## What this establishes for item A1

- Program RAM is readable through the same aperture/ports used for writing, by
  the stock driver: the bulk path is synchronous (it waits for the DMA
  completion event before returning), shares the write path's listed-memcpy
  builder, state machine and 4095-word cap, and requires a word-aligned start
  for bulk-sized reads. Edge reads cover the word+2 start and the final odd
  halfword, with the trailing edge returning the complete final stored word.
- Literal reads return widths 2/3/4 through the same ports the writers use, with
  bit 29 set in the command; float/fixed variants return through s0/r0.
- The windowed data-memory readers exist per kind with per-kind port and
  capacity tables; kinds 2/4 have no DSP-6 row in their tables.
- The completeness gap for "load a foreign program and read it back" is now
  narrower: the driver-level read primitive exists (`ReadDspProg`), and
  `SetMuteMode` proves program-window reads return loaded program content. What is still missing is the manager- or service-level call that invokes
  `ReadDspProg` (no static caller found), and the host route to request it (the
  missing external peer from `host-core1-bridge-followup.md`).

## What is not established

- No hardware observation: that the BMC silicon actually drives these ports as
  modeled, and that a read returns the just-written bytes, needs the unit.
- No caller of `ReadDspProg` was found in this image; whether any stock path
  ever reads a whole program is unknown.
- The bit-29 read direction flag is established only for the program-window
  literal ports compared here; `WriteDspCoefFloatWithEnv`'s live-slot commands
  clear bit 29, so it is not a universal flag across all DSP MMIO.
- The kind-0/1 2048-word driver bound versus the envelope study's per-DSP
  1024-word bank sizes for DSP 2..5 is unreconciled; the driver bound is a
  single fixed number, not a per-DSP table, and this note does not guess which
  reading reflects the silicon.
- Whether any stock caller reads with width 3 and `align_right` true (the 8-bit
  shift) is unverified.
- The kind-4 capacity table's trailing words (my dump shows two float-bit-pattern
  words after the six 512 entries) are not capacities; how many entries each
  capacity table really has is unpinned here.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  python tools/program_read_study.py local/b0c1a.bin --dsp 4 --address 0x4020 --count 510
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  python -m unittest discover -s tests -p test_program_read_study.py -v
```