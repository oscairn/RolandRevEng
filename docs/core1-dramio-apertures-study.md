# CORE1 DRAM-IO aperture tables and the verify-phase upload dispatch

Follow-up to [core1-load-route-callers-study](core1-load-route-callers-study.md)
(run 11) and [core1-boot-entry-chain-study](core1-boot-entry-chain-study.md)
(run 12), which named but did not decode the DRAM-IO aperture tables
`0x0113a970`/`0x0113a988`. This study decodes them, binds every bank's
consumers, recovers the boot verify routine's per-DSP DRAM-IO upload dispatch
in detail, and records the page-copy contract `CopyDramIOProgPage` — the
pieces a resident loader's own DRAM-IO verify could reuse.

Static, read-only file analysis of the pinned bmc0 CORE1 payload
(SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`).
No firmware is executed as a program; the Unicorn single-step cross-checks
below execute only single TBB instructions against the pinned bytes. No
device access, no key or ciphertext material.

## Result (summary)

- **The two named tables are one contiguous 24-word array at `0x0113a970`,
  not two separate tables.** Layout, closed form and every word
  byte-verified: bank `b` (0..3), DSP `d` (0..5) aperture =
  `0x41440000 + b*0x40000 + d*0x100000`. So bank 0 = `0x41440000`-based
  (DSP0 `0x41440000` … DSP5 `0x41940000`), bank 1 = `+0x40000`
  (`0x41444000` …), bank 2 = `+0x80000`, bank 3 = `+0xc0000`.
- **`GetDramIOProgAdrs 0x0112fb75`** (signature at `0x610b8eea`) requires
  `dsp < 6` (`cmp r0,#6; blt` at `0x0112fb76`), 8-byte-aligned offset
  (`tst.w r1,#7` at `0x0112fb8c`), then selects the sub-table with `r2`:
  `r2 == 0` loads the bank-0 half at `0x0112fbb0` (pool
  `0x112fc88 → 0x113a970`), `r2 != 0` the bank-1 half at `0x0112fba6`
  (pool `0x112fc8c → 0x113a988`), and returns `table[dsp] + offset`.
  This is the r2 bank selector run 11 reported; its two "tables" are the
  two halves of the 24-word array.
- **Who consumes which bank** (literal-pool census over the whole image,
  every site checked against its pool word):
  - bank 0 (`0x113a970`): `StackWriteDramIOProg` `0x112f9ca` (the
    `r2==0` branch of its bank ITE), `ReadDramIOProg` `0x112fa9c`
    (`r2==0`), `GetDramIOProgAdrs` `0x112fbb0`, and
    `StackFillDramIOProgNop` `0x112fd4a` (`r8==0`).
  - bank 1 (`0x113a988`): the `r2/r8 != 0` branches of the same three
    (`0x112f9cc`, `0x112fa9e`, `0x112fd48`) plus `GetDramIOProgAdrs`
    `0x112fba6` and `GetDramIOMuteCounter` `0x11307ea`.
  - bank 2 (`0x113a9a0`): only the mute-counter pair —
    `SetDramIOMuteCounter` `0x113078e` and `GetDramIOMuteCounter`
    `0x11307f8`.
  - bank 3 (`0x113a9b8`): only `SetDramIOMuteCounter` `0x113077e`.
    The mute counters therefore live in the bank-3 apertures with the
    counter offset computed as `4 + (counter>>3)*8` (`mov.w ip,#4;
    lsrs r1,r1,#3; add.w r1,ip,r1,lsl #3` at `0x01130772..0x01130778`),
    read back as bits 19..0 (`ubfx r0,r0,#0,#0x14` at `0x011307f2`).
- The aperture array is followed by four 7-word per-DSP literal port
  tables (verified word by word): exec control `0x0113a9ec` =
  `0x4110{2..9}310` (SetExeMode packs the mode/event word at `0x1130bd4`
  and stores it through the table at `0x1130bdc..e2`; the dead reader
  `GetExeMode` (run 11) loads the same table at `0x1130bfe`),
  SetDspFlag `0x0113a9d0` = `0x4110{2..9}318` (written at `0x112f4f6`),
  CopyDramIOProgPage command `0x0113aa08` = `0x4110{2..9}300`, its
  +0x100 sibling `0x0113aa24` = `0x4110{2..9}200`, and a raw/fixed
  region `0x0113aa3c` = `0x4110{2..9}400` (seventh entry `0x41104600`,
  eighth `0x41105600`, ...). Each table's sixth entry is the
  MDSP (index 6) port, e.g. exec `0x41102310`. The render-path program
  table `GetDspProgAdrs` loads is separate and shorter: 7 words at
  `0x0113a954` (`0x41480000 + dsp*0x100000`, plus a final `0x41260000`
  entry), loaded at `0x112f95a`.
- **Boot verify DRAM-IO phase dispatch, fully decoded.** In the verify
  routine `0x610010d0`, after the DSP-walk `cmp r4,#6` loop (program phase,
  run 11), the second walk `0x61001120..0x6100115e` (bound `cmp r4,#5`,
  i.e. DSP 0..5) dispatches `r4 == 0` through the TBB at `0x61001128`
  (table bytes at `0x6100112c`: `02 16 04 00`, i.e. targets `0x61001130`
  for DSP0, `0x61001158` = skip for DSP1, `0x61001134` for DSP2,
  `0x6100112c` re-entry path for r4==0's fall-in), loads a per-DSP object
  (`DSP0: pool 0x610014ec → 0x61085dcc`, `DSP2: pool 0x610014f0 →
  0x61085ddc`, `DSP6/MDSP: pool 0x610014f8 → 0x20084bb4`, SRAM pointer,
  reached via the `cmp r4,#6` IT-block at `0x61001148..0x6100114e`) and
  calls the upload through manager **vtable byte 0x1c**
  (`ldr r2,[r0]; ldr r2,[r2,#0x1c]; blx r2` at `0x61001152..56`) —
  exactly the byte run 11 pinned. The DSP1/3/4/5 targets fall through
  to the shared skip `0x61001158`, so **no DRAM-IO upload happens for
  DSP1/3/4/5 in the stock boot image**.
- **Unicorn cross-check of both dispatches.** Single-stepping the TBB
  at `0x610010e2` (phase 1, program lists) for r4 = 0..7 gives targets
  `0x610010ee/0x6100111a/0x610010f2/0x6100111a×3/0x610010f6/0x610010e6`
  and the TBB at `0x61001128` (phase 2) gives
  `0x61001130/0x61001158/0x61001134/0x6100112c`, agreeing with the static
  decode. The static decoder must scale each table byte by two
  (halfword TBB) and use the *unaligned* base `insn+4` — with the aligned
  `(insn+4)&~3` and byte-scale form the decode is wrong; the tool's first
  draft had that bug and the Unicorn run exposed it.
- **Per-DSP stock upload objects** (headers `(tag:u32, count:u8 at +2,
  list:u32 at +4)`, each with exactly one 16-byte record, all verified;
  record semantics confirmed from the compare-walk loads in both phases
  (`0x6100118e..0x6100119c` phase 1, `0x610012a6..0x610012bc` phase 2:
  word0 → `Get{,DramIO}ProgAdrs(dsp, word0)` as the aperture offset,
  word1 = length into the compare loop, word3 → `r3` as the compare
  source pointer):
  - phase 1: DSP0 `0x61085dc4` tag `0x10000`, list `0x61085db4`, length
    `0x13e4`, word3 `0x610849d0`; DSP2 `0x61085dd4` tag `0x10200`, length
    `0xce6`, word3 `0x61085ee4`; MDSP `0x61085de4` tag `0x10600`, length
    `0xc956`, word3 `0x61086bfc`.
  - phase 2 (DRAM-IO): DSP0 `0x61085dcc` tag `0x10001`, list `0x61085ed4`,
    length **16**, word3 `0x61085ec4`; DSP2 `0x61085ddc` tag `0x10201`,
    length 16, word3 `0x61086bdc`. Both 16-byte DRAM-IO stubs hold the
    repeated halfwords `ffff 7f80 0000 0000 ffff 7f80 0000 0000`
    (`0x807fffff`/`0x00000000` pairs — the stock DRAM-IO program for DSP0
    and DSP2 is a 16-byte stub, not a real program).
  - The phase-2 readback-compare calls `GetDramIOProgAdrs` with bank 0
    (`movs r2,#0` at `0x610012a6`, `bl` at `0x610012ae`), i.e. it verifies
    the bank-0 aperture the upload wrote (run 11's `vtable byte 0x1c` at
    `0x61001156` is this phase's upload; the compare loop follows).
- **`CopyDramIOProgPage 0x0112fdc0`** (signature `0x610b8fcd`, five assert
  paths with ids `0x215..0x21a` through the assert helper `0x1134ef2`):
  requires `dsp < 6`, offset low 10 bits == 0 (`ubfx ip,r1,#0,#0xa`),
  offset+span ≤ `0x3000`, source low 10 bits == 0 (`ubfx ip,r3,...`),
  span low 10 bits == 0 — a page-granular (1 KiB) copy of at most
  12 KiB. It then walks `span>>10` pages: per page it writes through the
  per-DSP port table at `0x113aa08` (pool `0x1130114 → 0x113aa08`, loaded
  once at `0x112fe60`) — first `port[0] = offset_page | 0x10000` (bit 16
  set = command word), then `port[1] = source_page | 0x10000`, then spins
  on `[port[2]+8]` bit 31 (`ldr r4,[ip,#8; cmp r4,#0; bne` at
  `0x0112fe8c..0x0112fe92`) — busy-wait per page, not per batch. The
  sibling function at `0x0112fe9e` (`SetDramIOProgPage`, signature
  `0x610b9020`) bounds both offset and span at `0x3000` and writes
  `[table_0x113aa24[dsp] + (offset>>10)*4] = value | 0x80000000`
  (`orr r2,r2,#0x80000000` at `0x0112ff04`) — the same aperture+8
  status/aperture words the busy-wait polls, so **a resident loader can
  reuse exactly this port-protocol shape for its own DRAM-IO writes**:
  write command pair, wait bit 31 of the status word.

## Method

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_dramio_apertures_study.py <main>/local/b0c1a.bin --json
```

The tool byte-pins 26 anchors: the full `GetDramIOProgAdrs` body including
both bank-select tails, the render-path `GetDspProgAdrs` table load, the bank
ITE branches of `StackWriteDramIOProg`/`ReadDramIOProg`/
`StackFillDramIOProgNop`, both mute-counter bodies, the
`CopyDramIOProgPage` head (all five bounds checks) and its page loop with the
bit-24 command pairs and busy-wait, the `SetExeMode`/`GetExeMode` port-table
accesses, the `SetDspFlag` port write, and the boot verify phase-2 region
(bypass entry, TBB, object literal loads, vtable byte 0x1c dispatch, the
bank-0 readback call and loop bound, and the `VerifyDrProg` log string).
It then: checks all 24 aperture words against the closed form; decodes both
TBB dispatches statically; cross-checks them with Unicorn single-steps
(`unicorn_tbb_targets`); resolves which functions load which aperture/port
literal (pc-relative literal scan with value check); and decodes the five
stock upload objects and their 16-byte records. `ok` requires all of: zero
anchor problems, the closed-form word match, and the pinned TBB targets.

Real tool output (command above, trimmed to the fields this note cites):

```json
{
 "ok": true,
 "anchors_checked": 26,
 "anchor_problems": [],
 "aperture_words_match_closed_form": true,
 "aperture_words": [
  "0x41440000", "0x41540000", "0x41640000", "0x41740000",
  "0x41840000", "0x41940000", "0x41444000", "0x41544000",
  "0x41644000", "0x41744000", "0x41844000", "0x41944000",
  "0x41448000", "0x41548000", "0x41648000", "0x41748000",
  "0x41848000", "0x41948000", "0x4144c000", "0x4154c000",
  "0x4164c000", "0x4174c000", "0x4184c000", "0x4194c000"],
 "phase2_tbb_targets": [
  "0x61001130", "0x61001158", "0x61001134", "0x6100112c"],
 "phase1_tbb_targets": [
  "0x610010ee", "0x6100111a", "0x610010f2", "0x6100111a",
  "0x6100111a", "0x6100111a", "0x610010f6", "0x610010e6"],
 "unicorn_phase2_tbb": {"0": "0x61001130", "1": "0x61001158",
  "2": "0x61001134", "3": "0x6100112c"},
 "unicorn_phase1_tbb": {"0": "0x610010ee", "1": "0x6100111a",
  "2": "0x610010f2", "3": "0x6100111a", "4": "0x6100111a",
  "5": "0x6100111a", "6": "0x610010f6", "7": "0x610010e6"},
 "aperture_users": {
  "bank0": ["0x112f9ca", "0x112fa9c", "0x112fbb0", "0x112fd4a"],
  "bank1": ["0x112f9cc", "0x112fa9e", "0x112fba6", "0x112fd48",
            "0x11307ea"],
  "bank2": ["0x113078e", "0x11307f8"],
  "bank3": ["0x113077e"],
  "exec_ports": ["0x1130bdc", "0x1130bfe"],
  "flag_ports": ["0x112f4f6"],
  "copy_ports_300": ["0x112fe60"],
  "copy_ports_200": ["0x112ff00", "0x112ff32"],
  "copy_ports_400": ["0x112ff82", "0x1130032"]},
 "verify_objects": [
  {"object": "0x61085dc4", "tag": "0x10000", "count": 1,
   "list": "0x61085db4",
   "records": [{"word0": 0, "length": 5092, "length_repeat": 5092,
                "word3": 1627933136}]},
  {"object": "0x61085dcc", "tag": "0x10001", "count": 1,
   "list": "0x61085ed4",
   "records": [{"word0": 0, "length": 16, "length_repeat": 16,
                "word3": 1627938500}]},
  {"object": "0x61085dd4", "tag": "0x10200", "count": 1,
   "list": "0x61086bcc",
   "records": [{"word0": 0, "length": 3302, "length_repeat": 3302,
                "word3": 1627938532}]},
  {"object": "0x61085ddc", "tag": "0x10201", "count": 1,
   "list": "0x61086bec",
   "records": [{"word0": 0, "length": 16, "length_repeat": 16,
                "word3": 1627941852}]},
  {"object": "0x61085de4", "tag": "0x10600", "count": 1,
   "list": "0x61093554",
   "records": [{"word0": 0, "length": 51542, "length_repeat": 51542,
                "word3": 1627941884]}]}
}
```

(`exit=0`; `word3` decimal values are `0x610849d0`, `0x61085ec4`,
`0x61085ee4`, `0x61086bdc`, `0x61086bfc`.)

Key disassembly, real recorded output of the command below (run against the
pinned image with `tools/core1.py` disasm; each line's bytes are pinned by
the 26 anchors). Command:

```sh
PYTHONPATH=tools /path/to/.venv/bin/python - <<'EOF'
from core1 import Core1
core = Core1('<main>/local/b0c1a.bin')
for a, n in ((0x0112fba4, 0x14), (0x61001120, 0x40),
             (0x0112fe58, 0x44), (0x01130772, 0x18)):
    for line in core.disasm(a, n):
        print(line)
EOF
```

Real output:

```text
0112fba4  22b1       cbz       r2, #0x112fbb0
0112fba6  394a       ldr       r2, [pc, #0xe4] ; [0x112fc8c] = 0x113a988
0112fba8  52f82000   ldr.w     r0, [r2, r0, lsl #2]
0112fbac  0844       add       r0, r1
0112fbae  10bd       pop       {r4, pc}
0112fbb0  354a       ldr       r2, [pc, #0xd4] ; [0x112fc88] = 0x113a970
61001120  0024       movs      r4, #0
61001122  05e0       b         #0x61001130
61001124  032c       cmp       r4, #3
61001126  17d2       bhs       #0x61001158
61001128  dfe804f0   tbb       [pc, r4]
6100112c  0216       asrs      r2, r0, #0x18
6100112e  0400       movs      r4, r0
61001130  ee49       ldr       r1, [pc, #0x3b8] ; [0x610014ec] = 0x61085dcc
61001132  00e0       b         #0x61001136
61001134  ee49       ldr       r1, [pc, #0x3b8] ; [0x610014f0] = 0x61085ddc
61001136  79b1       cbz       r1, #0x61001158
61001138  2000       movs      r0, r4
6100113a  08bf       it        eq
6100113c  e848       ldreq     r0, [pc, #0x3a0]
6100113e  07d0       beq       #0x61001150
61001140  0228       cmp       r0, #2
61001142  08bf       it        eq
61001144  e748       ldreq     r0, [pc, #0x39c]
61001146  03d0       beq       #0x61001150
61001148  062c       cmp       r4, #6
6100114a  08bf       it        eq
6100114c  e648       ldreq     r0, [pc, #0x398]
6100114e  03d1       bne       #0x61001158
61001150  10b1       cbz       r0, #0x61001158
61001152  0268       ldr       r2, [r0]
61001154  d269       ldr       r2, [r2, #0x1c]
61001156  9047       blx       r2
61001158  641c       adds      r4, r4, #1
6100115a  052c       cmp       r4, #5
6100115c  e2d9       bls       #0x61001124
0112fe58  960a       lsrs      r6, r2, #0xa
0112fe5a  0022       movs      r2, #0
0112fe5c  002e       cmp       r6, #0
0112fe5e  cebf       itee      gt
0112fe60  ac4d       ldrgt     r5, [pc, #0x2b0] ; pool 0x1130114 = 0x113aa08
0112fe68  55f82040   ldr.w     r4, [r5, r0, lsl #2]
0112fe6c  01eb822c   add.w     ip, r1, r2, lsl #10
0112fe70  4cf4803c   orr       ip, ip, #0x10000
0112fe74  c4f800c0   str.w     ip, [r4]
0112fe78  55f82040   ldr.w     r4, [r5, r0, lsl #2]
0112fe7c  03eb822c   add.w     ip, r3, r2, lsl #10
0112fe80  4cf4803c   orr       ip, ip, #0x10000
0112fe84  c4f804c0   str.w     ip, [r4, #4]
0112fe88  55f820c0   ldr.w     ip, [r5, r0, lsl #2]
0112fe8c  dcf80840   ldr.w     r4, [ip, #8]
0112fe90  002c       cmp       r4, #0
0112fe92  fbd1       bne       #0x112fe8c
0112fe94  521c       adds      r2, r2, #1
0112fe96  b242       cmp       r2, r6
0112fe98  e6db       blt       #0x112fe68
0112fe9a  f0bc       pop       {r4, r5, r6, r7}
0112fe9c  7047       bx        lr
01130772  4ff0040c   mov.w     ip, #4
01130776  c908       lsrs      r1, r1, #3
01130778  0cebc101   add.w     r1, ip, r1, lsl #3
0113077c  3bb1       cbz       r3, #0x113078e
0113077e  9e4b       ldr       r3, [pc, #0x278] ; [0x11309f8] = 0x113a9b8
01130780  53f82000   ldr.w     r0, [r3, r0, lsl #2]
01130784  0844       add       r0, r1
01130786  0260       str       r2, [r0]
```

## Established

- The DRAM-IO addressing hardware is exposed as four aperture banks per DSP
  with the closed form `0x41440000 + b*0x40000 + d*0x100000`; upload/read
  paths use banks 0/1, the mute counters use banks 3/2. A loader that
  wants a fresh DRAM-IO region should prefer a bank the stock consumers do
  not use (bank 2 is consumed only by the mute-counter getter).
- The boot verify routine uploads DRAM-IO content for DSP0, DSP2 and MDSP
  only, each a 16-byte stub (`ffff 7f80 0000 0000` repeated) — the stock
  image does not boot any real DRAM-IO program on those DSPs; the other
  DSPs get no DRAM-IO upload at all. This answers what "DRAM-IO" holds at
  boot: nothing but 16-byte stubs on three DSPs. The phase-2 walk's loop
  tail (`adds r4,#1; cmp r4,#5; bls` at `0x61001390..0x61001394`) and the
  `"DSP%c VerifyDrProg() = "` string at `0x61001518` bound the phase's
  extent.
- The per-DSP upload objects and their 16-byte record layout are pinned, so
  a resident loader can construct compatible objects (tag/count/list) and
  drive the same manager vtable byte 0x1c path.
- The page-copy port protocol (command word with bit 16, per-page busy-wait
  on `[aperture+8]` bit 31) is fully pinned; it is the reusable primitive
  for loader-initiated DRAM-IO transfers and their completion detection.
- The stock DRAM-IO verify compares against bank-0 apertures only (the
  `movs r2,#0` call at `0x610012ae`), consistent with uploads landing in
  bank 0.

## Not established

- The meaning of the aperture base addresses themselves (the
  `0x41440000`-based window): which physical DRAM-IO region each maps to,
  and how `GetDramIOProgAdrs`'s result is consumed by the DMA hardware.
- What the stub bytes `0x807fffff/0x00000000` mean to the DRAM-IO hardware
  (their shape is pinned; their effect is not).
- The `0x4110..00`-family port register semantics beyond the three
  operations recovered here (command/status/mute); the `copy_ports_400`
  region's consumers (`0x112ff82`, `0x1130032`) were pinned as users but
  their bodies were not analyzed.
- Whether any runtime path ever writes a real DRAM-IO program (all
  recovered upload users are boot-time or the assert-guarded wrappers; no
  non-stub length appears in any recovered object).
- bmc1 (`b1c1a.bin`) mirrors none of this; untouched.

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_dramio_apertures_study.py <main>/local/b0c1a.bin --json
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python -m unittest discover -s tests -p test_core1_dramio_apertures_study.py -v
```

The tool exits 0 only when all 26 anchors match, the SHA-256 matches, the 24
aperture words equal the closed form, and both TBB decodes equal the pinned
targets. Tests: with the corpus 9 pass; without the corpus 3 model tests
pass and the pinned-image tests skip cleanly.

## Best next item

A2 (program reservations): the boot walk's per-DSP bound `cmp r4,#6` gives 7
list slots per DSP, and this study pinned the occupied stock objects
(phase-1: one program each on DSP0/DSP2/MDSP) — the next step is a census of
all seven per-DSP list-slot objects to say which slots are free in the stock
image, which bounds where a foreign program can be loaded without disturbing
stock state. Static. Alternative: A5 (wave memory and interpolation), the
least mapped and most important for the first sample-playback target, but a
bigger bite.