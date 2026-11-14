# CORE1 program-load route callers and readback users

Follow-up to the loader map's section 6
([BMC DSP packet and loader map](BMC%20DSP%20packet%20and%20loader%20map.md))
and [kernel-audio-abi](kernel-audio-abi-study.md), which recover the driver
routines (`StackWriteDspProg`, the literal ports, `WriteDspProgAllImpl`) and
the manager vtable slots. Those notes name the functions but not their
callers: nothing so far binds *which stock code actually drives the load
route*, whether any code *reads program or coefficient state back*, and what
the exclusion flag's scope is. This run censuses callers of every recovered
entry point and finds the one stock routine that both uploads and verifies.

Static, read-only file analysis of the pinned bmc0 CORE1 payload
(SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`).
No firmware is executed; no device is contacted; no key or ciphertext material
is read.

## Result (summary)

The whole-image caller census (74 byte-exact anchors; tool exits 0) shows:

- **One routine drives the whole route end to end**: the boot verify routine at
  `0x610010d0` walks per-DSP program lists, resolves destinations through
  `GetDspProgAdrs` (its **only** caller image-wide, via veneer cell
  `0x61076a82` → single `bl` at `0x61001194`), uploads through manager vtable
  byte 0x18, then **readback-compares** every written byte against the stored
  list. A second phase does the same for DRAM-IO lists through
  `GetDramIOProgAdrs` (`0x0112fb75`) and vtable byte 0x1c.
- **No other code uploads programs.** The strict virtual-call scan finds
  exactly 13 sites through vtable byte 0x18, 9 through byte 0x1c and 6 through
  byte 0x20 image-wide; outside the boot routine, all belong to a handful of
  manager/effect-lifecycle functions (list in the evidence section).
- **Coefficient readback exists but is event-driven**: the coefficient-read
  manager slots (vtable bytes 0x70 `0x01132abf` / 0x74 `0x01132b89`) have
  **exactly one virtual call site each** (`0x01131734` / `0x01131764`), inside
  two tiny hardware-event handlers at `0x01131710` / `0x01131740` that read
  registers `0x41100370` / `0x41100374` and are themselves reached only through
  an ITCM pointer table (`0x01100194`, `0x01100244`, `0x01100248`) — stock
  coefficient readback is wired to a register event, not called in-line.
- **`GetExeMode` has zero callers** anywhere (no BL, no veneer, no word
  reference): nothing in the stock image reads back execution state.

## Method

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_load_route_study.py
```

The tool byte-pins 74 anchors across the recovered bodies (assertion
signature strings, the exclusion-flag byte `0x2008480c` handling, the
even-address checks, the 19-bit port command encoding `ubfx r1,r1,#0,#0x13`,
the aperture table `0x0113a954`, the manager vtable quads, the boot routine's
log strings), then scans both image regions (ITCM `0x01100000..`, ERAM
`0x61000000..`) for:

1. direct BL/B.W encodings to each recovered entry point (Thumb targets),
2. MOVW/MOVT/BX veneer cells, and the BL callers of each veneer cell,
3. aligned word-pointer references,
4. strict virtual-call pairs (`ldr rX,[rY,#disp]` within 12 prior halfword
   instructions, then `blx rX`) at the manager vtable program-upload bytes
   0x18/0x1c/0x20 and coefficient bytes 0x64/0x68/0x6c/0x70/0x74.

Enclosing-function names below come from the assertion signature strings in
each function's prologue (the repo's established naming method).

## Evidence

Real tool output (command above), trimmed to the relevant keys:

```json
{
  "ok": true,
  "anchors_checked": 74,
  "anchor_problems": [],
  "upload18": ["0x1102220", "0x11027c8", "0x110ddd8", "0x110e43a",
               "0x1131306", "0x61001118", "0x61013afa", "0x6101ef8c",
               "0x61026a64", "0x6103056c", "0x61034980",
               "0x61034cf6"],
  "upload1c": ["0x1102250", "0x11027fc", "0x1131336", "0x61001156",
               "0x61026652", "0x61030584", "0x6103bede"],
  "upload20": ["0x1102280", "0x1129a04", "0x1131366", "0x6101efb0",
               "0x61030594", "0x610836f8"],
  "coef70": ["0x1131734"],
  "coef74": ["0x1131764"]
}
```

(Run 18's `docs/core1-mgr-vtable-sites-study.md` corrected this JSON: the
original scan here double-counted `0x61030578` under 0x18 and
`0x61030594`/`0x6103bee8` under 0x1c — its strict scanner accepted stale
register loads; `0x61030578`'s actual load is `#0x10` (a flag dispatch) and
`0x61030594`'s is `#0x20`.)

### The boot verify routine (`0x610010d0`)

It reads a state word at `0x200800d8`, walks per-DSP list slots (loop bound
`cmp r4,#6; bls` at `0x6100111c` — indices 0..6, with per-index list-object
selection), and for each list record (`stride 16`: `[r8+0]` destination byte
address, `[r8+4]` length, `[r8+0xc]` stored-source pointer):

1. `0x61001190 ldr.w r1,[r8]; 0x61001194 bl #0x61076a82` — the veneer
   `movw ip,#0xf92b; movt ip,#0x112; bx ip` → `GetDspProgAdrs(dsp, address)`.
   This veneer cell has **exactly one direct BL caller image-wide**
   (`0x61001194`), and `GetDspProgAdrs` itself has **no direct BL callers** —
   every program-RAM destination resolution in the stock image goes through
   this one call.
2. `0x61001114 ldr r2,[r0]; 0x61001116 ldr r2,[r2,#0x18]; 0x61001118 blx r2`
   — manager vtable byte 0x18 (the "write every render-program segment and
   wait" wrapper `0x01135099` → `WriteDspProgAllImpl` with `r2=1`).
3. A three-stage compare loop (halfword edges at `0x610011ae..c6`, then word
   bulk at `0x61001200..0x210`) comparing the aperture at the `GetDspProgAdrs`
   return against the stored-source bytes, counting matching length in `r2`.
4. On mismatch it logs `"DSP%c VerifyProg() = "` (`0x610014f4`) with a `NG`
   count (`" NG(%d)\n"` at `0x6100150f`) through `0x61015b76`, the assert/log
   helper taking `0x20091280`.

Phase 2 (`0x61001290..`) repeats the pattern for DRAM-IO: object table
`0x61085ddc`/`0x61085de4`, veneer cell `0x61076a8c` →
`GetDramIOProgAdrs` (`0x0112fb75`, DSP<6, 8-byte-aligned check, aperture
tables `0x0113a988`/`0x0113a970`), upload through vtable byte 0x1c at
`0x61001156`, the same compare loop, and the `"DSP%c VerifyDrProg() = "`
string (`0x61001518`).

The five `SetExeMode` call sites (`0x610016d8/6e4/6f0/6fc/70c`, all through
veneer cell `0x61076aaa` — the only callers of that veneer) sit in the same
routine's continuation: the exact tuples the kernel study recorded
(DSP0 mode 2 event 3, DSP1 mode 0, DSP2 mode 2, DSP3 mode 0, MDSP mode 2).
So the stock image's only execution-mode programmer is the boot verify
routine itself, immediately after its upload+verify passes.

### Upload-slot call sites outside the boot routine

| Site | Enclosing function (assertion string) |
|---|---|
| `0x1102220/0x1102250/0x1102280` | unnamed ITCM trio (a DSP0/2/6 walk like the boot routine's, one blx per slot) |
| `0x11027c8/0x11027fc` | unnamed ITCM pair |
| `0x110ddd8` | the byte-stream parser `0x0110d962` family (run 6's parser body) |
| `0x110e43a` | parser sibling `0x0110e400` |
| `0x1131306/0x1131336/0x1131366` | manager-side function `0x011312c4` (one call per upload slot) |
| `0x61013afa` | effect-lifecycle writer `0x61013aa0` (per-instance loop, list count from `[r5,#0x10]`) |
| `0x6101ef8c/0x6101efb0` | `0x6101ef2e` (both a 0x18 and a 0x20 call) |
| `0x61026a64` / `0x61026652` | `0x61026612` (event-style, guarded by `[r6,r4,lsl#2]` object slots and `0x411003xx` register writes) |
| `0x6103056c/0x61030578/0x61030584/0x61030594` | `0x6103050c` — calls slot 0x14 once, then 0x18, then 0x10 (flag), then 0x1c, then 0x20 (the only function calling three different upload slots plus the flag byte) |
| `0x61034980/0x61034cf6` | `0x61034954` / `0x61034c52` |
| `0x610836f8` | inside `0x610835d0` (boot-region helper; the old note's `0x610836f0` is the `ldr r1,[r1,#0x20]` right before the `blx`, not a function start) |
| `0x1129a04` | inside `0x0112999e` (effect replacement region; the old note's `0x01129a00` is the instruction right before the `blx`, not a function start) |

### Direct-caller census of the drivers

| Function | Direct BL callers |
|---|---|
| `StackWriteDspProg` `0x0112f582` | `0x01131cd4`, `0x01131f6c`, `0x01132240` — all three are inside the manager program writers (`WriteDspProgAllImpl`, segmented `0x01131e70`, unique-segmented `0x0113214e`) |
| `StackFillDspProgNop` `0x0112fbba` | `0x011324c2` (inside the manager vtable byte-0x44 wrapper `0x01132473`) |
| `DSP_listed_memcpy` `0x0112f290` | `0x0112f662`, `0x0112f8aa`, `0x0112fa10`, `0x0112faf4` — all inside `StackWriteDspProg` itself |
| `DMA completion helper` `0x0112f6a4` | 12, all inside manager writers/wrappers plus the mute search tail |
| `Active DMA drain` `0x0112f508` | `0x011324a2` (manager vtable byte 0x48 wrapper only) |
| `WriteLiteralRaw` `0x0112f528` | 9: `StackWriteDspProg` edges (2), `StackFillDspProgNop` (2), `WriteDspCoefRaw 0x011329ce`, `ChangeDspMemoryAdrs 0x011330ae` (2), `ChangeDspLabelAdrs 0x0113338c`, `ChangeDramIO_RW_Adrs 0x0113353c`, `SetMuteMode 0x01133b38` |
| `WriteLiteralFloat` `0x0112ff4e` | 5: `WriteDspCoefFloat 0x011327e6`, `WriteDspCoefFloatWithInterpolation 0x01132bd2` (2), `ChangeDspMemoryAdrs`, `ChangeDramIO_RW_Adrs` |
| `ReadLiteralRaw` `0x0112f6e8` | 5: `ReadDspCoefRaw 0x01132b88`, `ChangeDspMemoryAdrs`, `ChangeDramIO_RW_Adrs`, `SetMuteMode` (2 — the scan and the write-back are one function) |
| `GetDspProgAdrs` `0x0112f92a` | 0 direct; 1 veneer cell with exactly 1 caller (boot verify) |
| `WriteDspProgAllImpl` `0x01131c4e` | `0x0113509a` (slot 0x18 wrapper), `0x011350b6` (slot 0x20 wrapper) |
| `WriteDramIOProg` `0x01131cf4` | `0x011350aa` (slot 0x1c wrapper), `0x011350c2` (slot 0x24 wrapper) |
| `SetExeMode` `0x01130b6c` | 0 direct; 1 veneer cell with exactly the five boot call sites |
| `GetExeMode` `0x01130be6` | 0 of every kind |

### Manager vtable quads (byte-pinned)

`0x6117647c` address point; quads `0x61176490..0x611764f0`:

| Quad | Value | Meaning |
|---|---|---|
| `0x61176490` | `0x01131bfd` | byte 0x14 |
| `0x61176494` | `0x01135099` | byte 0x18 — write all render segments, wait |
| `0x61176498` | `0x011350a9` | byte 0x1c — write DRAM-IO list, wait |
| `0x6117649c` | `0x011350b5` | byte 0x20 — write render segments, no wait |
| `0x611764e0` | `0x011327e7` | byte 0x64 — `WriteDspCoefFloat` |
| `0x611764ec` | `0x01132abf` | byte 0x70 — `ReadDspCoefFloat` |

### Coefficient readback is event-driven

The only virtual callers of the coefficient-read slots are:

```text
0x01131710  push {r3, r4, r5, lr}
0x01131712  ldr  r4, [pc, #0x1cc]   ; 0x41100000
0x01131714  ldr.w r0, [r4, #0x370]  ; hardware event register
0x01131718  movs r1, #0
0x0113171a  str.w r1, [r4, #0x370]  ; ack by zeroing
0x0113171e  ldr  r1, [pc, #0x1c4]   ; 0x200a16b8 (stats block)
0x01131720  str  r0, [r1, #0x70]
...
0x01131732  it   ne
0x01131734  blxne r1                ; manager vtable byte 0x70 = ReadDspCoefFloat
0x01131736  ldr  r0, [r4]
0x0113173a  dsb  sy
```

and its twin at `0x01131740` for byte 0x74 (`ReadDspCoefRaw`). The handlers are
reached only through ITCM pointer-table words `0x01100194` (handler 5 of the
`0x01100180..` table), `0x01100244` and `0x01100248` — a dispatch table, not
call sites. `ReadDspCoefFloat`'s and `ReadDspCoefRaw`'s results land in the
stats block at `0x200a16b8` (+0x70/+0x74), i.e. the stock image's coefficient
*readback users* are diagnostics, not the audio path.

## Established

- The stock load route is **boot-verify-driven**: one routine (`0x610010d0`)
  resolves every destination through `GetDspProgAdrs`, uploads through the
  manager vtable bytes 0x18/0x1c, and verifies the written bytes against the
  stored list before arming execution modes. This is the image's only
  end-to-end user of the load route.
- Program-RAM **readback** in the stock image is this compare loop reading the
  aperture directly (`GetDspProgAdrs` + word/halfword loads) — no function
  called "read program" exists; coefficient/data readback exists as manager
  methods whose only users are event handlers and the mute search.
- `GetExeMode` is dead stock code in this build; nothing reads execution
  state back.
- The exclusion flag `0x2008480c` is taken by exactly the writers the kernel
  study named (`WriteDspProgAllImpl`, coefficient writers) and released in the
  same bodies; no other image code touches it (all ten image-wide literal-pool
  occurrences of `0x2008480c` lie inside the manager writer region
  `0x1131dbc..0x113517c`; the flag loads pinned at `0x01131c96`, released at
  `0x01132ab2`/`0x01132ab6`).
- Outside the boot routine, the upload slots' users are a bounded set of 12
  additional functions (13/9/6 sites), listed above — a resident loader must
  share with these, not with unknown code.

## Not established

- What triggers the boot verify routine and when it runs (no direct BL callers
  of `0x610010d0` were found; its entry is built at runtime or in an
  unrecovered table, like bmc1's ASGN task in run 7).
- The semantics of the unnamed ITCM walkers (`0x011021fc`, `0x011027b4`,
  `0x0110e400`) and the effect-lifecycle callers (`0x61013aa0`,
  `0x6101ef2e`, `0x6103050c`, `0x61034954`, `0x61034c52`,
  `0x610836f0`): call structure verified, bodies not decoded.
- Whether the verify compare loop ever reports a mismatch in practice (needs
  the unit; the `NG` log path exists but firing it is a runtime question).
- The `0x41100370/0x41100374` event registers' meaning and interrupt vectoring
  (the ITCM pointer table at `0x01100180..` resembles a handler table; its
  consumer was not traced).
- bmc1 (`b1c1a.bin`) mirrors none of this census; untouched.

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_load_route_study.py
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python -m unittest discover -s tests -p test_core1_load_route_study.py -v
```

The tool exits 0 only when all 74 anchors match, the three upload-slot site
lists equal the expected sets, and the vtable quads hold the recovered
wrappers. Tests: with the corpus the pinned-image class runs (anchors,
SHA-256, upload-site equality, vtable quads, direct-caller counts, veneer
single-caller proofs); without the corpus the 3 model tests pass and the
7 pinned-image tests skip cleanly.

## Best next item

Trace the boot verify routine's entry (who builds `0x610010d0` into a
dispatch table) to bind when the load route runs, or decode the DRAM-IO verify
phase's aperture tables (`0x0113a970`/`0x0113a988`) to bound what a resident
loader's own verify could reuse. Both are static.