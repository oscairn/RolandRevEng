# CORE1 stock program reservations: which per-DSP slots exist and which are free

A2 item from the owner's feasibility order (program reservations: which program
slots/contexts exist, who owns each, whether any is unused in the stock image),
queued as next by run 13's log ("a census of all seven per-DSP list-slot
objects to say which slots are free in the stock image") after run 13 pinned
the five stock upload objects. The sibling series' run 14 closed lane A1 to
its static limit and pointed here.

Static, read-only file analysis of the pinned bmc0 CORE1 payload
(SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`),
reusing the boot-verify anchors of runs 11–13.. No firmware executed as a
program, no device access, no key/ciphertext material.

## Result (summary)

- **Seven reservation slots exist, indexed r4 = 0..6 (DSP0..DSP5, MDSP = 6).**
  The boot verify routine `0x610010d0` walks `cmp r4,#7; bhs` exit
  (`0x610010de`) and loops `adds r4,#1; cmp r4,#6; bls` at `0x6100111a..1e`
  (the bound run 11 pinned). Each index has TWO phases: phase 0 = program
  lists (TBB `0x610010e2`, table bytes at `0x610010e6`:
  `04 1a 06 1a 1a 1a 08 00`) and phase 1 = DRAM-IO lists (TBB `0x61001128`,
  bytes `02 16 04 00`, run 13).
- **Only slots DSP0, DSP2 and MDSP carry a static reservation entry.** The
  phase-1 TBB sends r4 = 0/2/6 to load objects `0x61085dc4`/`0x61085dd4`/
  `0x61085de4` from literal pools `0x610014d4/d8/dc`; r4 = 1/3/4/5 fall
  through to the shared skip `0x6100111a`. Phase 2 likewise uploads only
  `0x61085dcc` (DSP0) and `0x61085ddc` (DSP2) plus the SRAM pointer
  `0x20084bb4` for MDSP (pools `0x610014ec/f0/e8`).
- **Entry format (all five pinned):** an 8-byte record pair — header u32 =
  `(count << 16) | (dsp << 8) | phase` (count is the byte at +2, read by the
  walk as `ldrb r0,[r6,#2]` at `0x6100117e` and gated `cmp r0,#0; ble` —
  count 0 would mean an empty slot), then the list pointer at +4. Each
  16-byte list record is (word0 = aperture offset, word1 = length,
  word2 = length repeat, word3 = compare source), exactly the compare-walk
  semantics run 13 established.
- **The five stock entries** (all count 1, all record word0 = 0):
  DSP0 program, list `0x61085db4`, length `0x13e4` (5092 bytes), source
  `0x610849d0`; DSP0 DRAM-IO, list `0x61085ed4`, 16-byte stub
  (`0x807fffff`/`0x00000000` pairs, run 13); DSP2 program, list
  `0x61086bcc`, length `0xce6` (3302); DSP2 DRAM-IO, list `0x61086bec`,
  16-byte stub; MDSP program, list `0x61093554`, length `0xc956` (51542).
  No sixth entry follows: the 18 words `0x61085dec..0x61085e33` are all zero
  in the image.
- **Stock occupancy in program RAM** (via `GetDspProgAdrs`' 7-word aperture
  table at `0x0113a954` = `0x41480000 + dsp*0x100000` plus final
  `0x41260000`, and the bank-0 DRAM-IO aperture `0x41440000 + dsp*0x100000`
  from run 13's closed form):
  - DSP0 program `[0x41480000, 0x414813e4)`; DSP0 DRAM-IO
    `[0x41440000, 0x41440010)` (stub).
  - DSP2 program `[0x41680000, 0x41680ce6)`; DSP2 DRAM-IO
    `[0x41640000, 0x41640010)` (stub).
  - MDSP program `[0x41260000, 0x4126c956)`.
  - **DSP1, DSP3, DSP4, DSP5 are completely untouched by the boot load
    route** — no reservation entry, skipped by both TBBs, so their program
    apertures (`0x41580000`, `0x41780000`, `0x41880000`, `0x41980000`)
    and DRAM-IO apertures (`0x41540000`, `0x41740000`, `0x41840000`,
    `0x41940000`) hold nothing the boot route wrote. A foreign program
    can be loaded into any of them without overwriting a stock boot
    program; note the boot route itself is not the only writer (run 11
    found runtime upload callers through the same manager vtable, and the
    stride-1 MiB layout bounds each slot's capacity but was not measured
    against hardware).
- **Who owns each**: the boot verify routine is the only static consumer of
  the five objects — a whole-image word census finds each object's 32-bit
  value exactly once, in the verify routine's literal pools, and nowhere
  else. Runtime re-writes go through the manager upload wrappers (run 11's
  vtable bytes 0x18/0x1c sites: the effect-lifecycle callers
  `0x61013aa0`, `0x6101ef2e`, `0x6103050c`, `0x61034954`, `0x61034c52`,
  `0x610835d0` and the ITCM walkers), which take the list argument from
  their caller, not from this table.
- **The manager cells are runtime-constructed.** The dispatch loads a
  per-DSP manager object pointer from `0x20084b8c`/`0x20084ba0`/`0x20084bb4`
  (IT-block `ldreq` from pools `0x610014e0/e4/e8` at `0x610010fc..0x61001110`,
  phase 2 likewise at `0x61001138..4e`), skips the upload if zero
  (`cbz r0`), and calls `[vtable+0x18]` (phase 1) / `[vtable+0x1c]`
  (phase 2). All three cells are **zero in both scatter records** of the
  image, so the objects exist only after runtime construction. A
  constructor at `0x6100177c` writes the manager vtable address point
  `0x6117647c` into all three (0x14-stride objects at `0x20084b8c`,
  `0x20084ba0`, `0x20084bb4`, each with `[+4] = 0x2009be2c`, `[+8] =
  0x61085dec/0x61085e34/0x61085e7c`, `[+0x10] = 0`, then helper calls
  through veneers `0x61076ab4` → `0x1131bb7` and `0x61076abe` →
  `0x112ca7d`) — but that constructor itself has **no direct BL, veneer or
  aligned word reference anywhere in the image**: its entry, like the verify
  routine's and bmc1's ASGN task (runs 11/12/7), is built at runtime or in an
  unrecovered table. Whether it runs before the boot task's verify call is
  inferred from the verify routine's `cbz` guards, not proved.
- **Whole-image header census** (14 candidate words
  `0x00010000 | (dsp<<8) | phase` followed by a plausible list pointer): the
  five boot entries plus 113 other occurrences, all outside the boot array —
  most are single incidental `0x00010000`-valued words (the constant is
  common in program code), but two structured clusters use the same 8-byte
  header shape: the MDSP program's own DRAM-IO region records at
  `0x61093578..0x61093650` and a separately consumed run of same-shape
  (header, list) pairs at `0x610a1ef8..0x610a1f78` (16 pairs; end corrected
  run 16 — the last pair is `0x610a1f70..0x610a1f78`) — including
  `0x610a1f08` header `0x00010300` list `0x610a556c` and
  `0x610a1f58/f60/f68/f70` with DSP1/3/4/5 class headers, pool-referenced at
  `0x6102956c`/`0x6102a750..c`; some neighbors there carry count bytes of 2
  and 5 (e.g. `0x00050301` at `0x610a1f00`, list `0x610a5350`), which this
  run's count-1 census did not scan. Those lookalikes are consumed by other
  code paths not traced here; none of them is consumed by the boot verify walk.

## Method

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python tools/core1_reservations_study.py <main>/local/b0c1a.bin --json
```

The tool byte-pins 24 anchors: the phase-1 TBB bytes, the three object pools,
the manager-cell IT-block pools, the walk bounds, the count-byte load, the
record-walk head, the `GetDspProgAdrs` veneer BL, both loop tails, the phase-2
TBB bytes, the five entry headers and list pointers as stored, and the
constructor prologue with its pool words and both 0x14 strides. It then:
decodes the five entries against pinned expectations; checks the zero tail;
decodes the phase-1 TBB (base `insn+4`, byte entries ×2, the encoding run 13
proved with Unicorn); checks the program-aperture table against the closed
form; verifies the manager cells are zero in both scatter records; scans the
whole image for other header-form words; and computes the occupancy ranges.
`ok` requires all of them.

Real tool output (command above, fields this note cites):

```json
{
 "ok": true,
 "sha256": "6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154",
 "anchors_checked": 24,
 "anchor_problems": [],
 "phase1_tbb_targets": ["0x610010ee", "0x6100111a", "0x610010f2",
  "0x6100111a", "0x6100111a", "0x6100111a", "0x610010f6", "0x610010e6"],
 "entries": [
  {"address": "0x61085dc4", "header": "0x10000", "count": 1, "dsp": 0,
   "phase": 0, "high_byte": 0, "list": "0x61085db4", "records": [
   {"word0": 0, "length": 5092, "length_repeat": 5092,
    "word3": 1627933136}]},
  {"address": "0x61085dcc", "header": "0x10001", "count": 1, "dsp": 0,
   "phase": 1, "high_byte": 0, "list": "0x61085ed4", "records": [
   {"word0": 0, "length": 16, "length_repeat": 16, "word3": 1627938500}]},
  {"address": "0x61085dd4", "header": "0x10200", "count": 1, "dsp": 2,
   "phase": 0, "high_byte": 0, "list": "0x61086bcc", "records": [
   {"word0": 0, "length": 3302, "length_repeat": 3302,
    "word3": 1627938532}]},
  {"address": "0x61085ddc", "header": "0x10201", "count": 1, "dsp": 2,
   "phase": 1, "high_byte": 0, "list": "0x61086bec", "records": [
   {"word0": 0, "length": 16, "length_repeat": 16, "word3": 1627941852}]},
  {"address": "0x61085de4", "header": "0x10600", "count": 1, "dsp": 6,
   "phase": 0, "high_byte": 0, "list": "0x61093554", "records": [
   {"word0": 0, "length": 51542, "length_repeat": 51542,
    "word3": 1627941884]})}
 ],
 "entries_match_expectations": true,
 "zero_tail_after_mdsp_entry": ["0x0", "0x0", "0x0", "0x0", "0x0", "0x0",
  "0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0",
  "0x0", "0x0"],
 "program_aperture_table": ["0x41480000", "0x41580000", "0x41680000",
  "0x41780000", "0x41880000", "0x41980000", "0x41260000"],
 "program_aperture_matches_closed_form": true,
 "object_references": {"0x61085dc4": ["0x610014d4"],
  "0x61085dcc": ["0x610014ec"], "0x61085dd4": ["0x610014d8"],
  "0x61085ddc": ["0x610014f0"], "0x61085de4": ["0x610014dc"]},
 "manager_cells_in_image": {"0x20084b8c": "0x0", "0x20084ba0": "0x0",
  "0x20084bb4": "0x0"},
 "manager_ctor_pools": {"0x61001824": "0x20084b8c",
  "0x61001830": "0x6117647c", "0x61001828": "0x61085dec",
  "0x6100183c": "0x61085e34", "0x61001840": "0x61085e7c",
  "0x6100182c": "0x2009be2c"},
 "stock_occupancy": [
  {"dsp": 0, "phase": 0, "start": "0x41480000", "end": "0x414813e4",
   "length": 5092},
  {"dsp": 0, "phase": 1, "start": "0x41440000", "end": "0x41440010",
   "length": 16},
  {"dsp": 2, "phase": 0, "start": "0x41680000", "end": "0x41680ce6",
   "length": 3302},
  {"dsp": 2, "phase": 1, "start": "0x41640000", "end": "0x41640010",
   "length": 16},
  {"dsp": 6, "phase": 0, "start": "0x41260000", "end": "0x4126c956",
   "length": 51542}
 ]
}
```

(`exit=0`; `word3` decimals are `0x610849d0`, `0x61085ec4`, `0x61085ee4`,
`0x61086bdc`, `0x61086bfc`; the `header_form_hits_elsewhere` list has 118
rows, the five boot entries plus the lookalikes named above.)

Key disassembly, real recorded output of the commands below:

```sh
PYTHONPATH=tools <venv>/bin/python - <<'EOF'
from core1 import Core1
from pathlib import Path
core = Core1('<main>/local/b0c1a.bin')
for a, n in ((0x610010d0, 0x10), (0x610010e6, 0x30), (0x610010fa, 0x24),
             (0x6100117e, 0x20), (0x6100177c, 0x28)):
    for line in core.disasm(a, n):
        print(line)
    print('---')
EOF
```

Real output:

```text
610010d0  2de9f05f   push.w    {r4, r5, r6, r7, r8, sb, sl, fp, ip, lr}
610010d4  fe4d       ldr       r5, [pc, #0x3f8] ; [0x610014d0] = 0x200800d8
610010d6  2868       ldr       r0, [r5]
610010d8  0024       movs      r4, #0
610010da  2746       mov       r7, r4
610010dc  07e0       b         #0x610010ee
610010de  072c       cmp       r4, #7
---
610010e6  041a       subs      r4, r0, r0        ; TBB table: 04 1a 06 1a 1a 1a 08 00
610010e8  061a       subs      r6, r0, r0
610010ea  1a1a       subs      r2, r3, r0
610010ec  0800       movs      r0, r1
610010ee  f949       ldr       r1, [pc, #0x3e4] ; [0x610014d4] = 0x61085dc4
610010f0  02e0       b         #0x610010f8
610010f2  f949       ldr       r1, [pc, #0x3e4] ; [0x610014d8] = 0x61085dd4
610010f4  00e0       b         #0x610010f8
610010f6  f949       ldr       r1, [pc, #0x3e4] ; [0x610014dc] = 0x61085de4
610010f8  79b1       cbz       r1, #0x6100111a
610010fa  2000       movs      r0, r4
610010fc  08bf       it        eq
610010fe  f848       ldreq     r0, [pc, #0x3e0]   ; pool 0x610014e0 = 0x20084b8c
61001100  07d0       beq       #0x61001112
61001102  0228       cmp       r0, #2
61001104  08bf       it        eq
61001106  f748       ldreq     r0, [pc, #0x3dc]   ; pool 0x610014e4 = 0x20084ba0
61001108  03d0       beq       #0x61001112
6100110a  062c       cmp       r4, #6
6100110c  08bf       it        eq
6100110e  f648       ldreq     r0, [pc, #0x3d8]   ; pool 0x610014e8 = 0x20084bb4
61001110  03d1       bne       #0x6100111a
61001112  10b1       cbz       r0, #0x6100111a
61001114  0268       ldr       r2, [r0]
61001116  9269       ldr       r2, [r2, #0x18]
61001118  9047       blx       r2
---
6100117e  b078       ldrb      r0, [r6, #2]       ; count byte of the entry
61001180  0025       movs      r5, #0
61001182  0028       cmp       r0, #0
61001184  78dd       ble       #0x61001278
61001186  7068       ldr       r0, [r6, #4]       ; list pointer
61001188  10eb0518   adds.w    r8, r0, r5, lsl #4 ; record = list + i*16
6100118c  70d0       beq       #0x61001270
6100118e  2046       mov       r0, r4
61001190  d8f80010   ldr.w     r1, [r8]           ; record word0 = aperture offset
61001194  75f075fc   bl        #0x61076a82        ; veneer -> GetDspProgAdrs
61001198  d8f80410   ldr.w     r1, [r8, #4]       ; record word1 = length
---
6100177c  70b5       push      {r4, r5, r6, lr}
6100177e  294c       ldr       r4, [pc, #0xa4] ; [0x61001824] = 0x20084b8c
61001780  2b4d       ldr       r5, [pc, #0xac] ; [0x61001830] = 0x6117647c
61001782  0022       movs      r2, #0
61001784  2560       str       r5, [r4]              ; [cell] = vtable address point
61001786  2849       ldr       r1, [pc, #0xa0] ; [0x61001828] = 0x61085dec
61001788  2261       str       r2, [r4, #0x10]
6100178a  2848       ldr       r0, [pc, #0xa0] ; [0x6100182c] = 0x2009be2c
6100178c  a160       str       r1, [r4, #8]
6100178e  6060       str       r0, [r4, #4]
61001790  2046       mov       r0, r4
61001792  75f08ff9   bl        #0x61076ab4           ; veneer -> 0x1131bb7
```

(`0x61076ab4` = `movw ip,#0x1bb7; movt ip,#0x113; bx ip` → `0x1131bb7`,
which zeroes `[r0,#0xc]`; `0x61076abe` → `0x112ca7d`, body not analyzed.)

## Established

- The boot load route's reservation model: 7 slots × 2 phases, per-slot
  reservation list object with a count byte and 16-byte (offset, length,
  length repeat, source) records; count 0 or a zero object pointer means the
  slot is skipped.
- Stock occupancy: DSP0 program 5092 bytes at `0x41480000`, DSP2 program
  3302 bytes at `0x41680000`, MDSP program 51542 bytes at `0x41260000`,
  16-byte DRAM-IO stubs on DSP0/DSP2 only. DSP1/3/4/5 have no entry, no
  upload and no readback in the boot route — the free slots in the stock
  image, bounded by this route's own evidence.
- The five reservation objects have exactly one image-wide word reference
  each (the verify routine's pools), so nothing else consumes the stock
  table.
- The manager cells the dispatch dereferences are runtime-constructed (zero
  in both scatter records); the constructor's shape is pinned, its caller is
  not.

## Not established

- Whether DSP1/3/4/5 stay free at runtime: run 11's upload-site census shows
  other callers of the same manager upload bytes, and the lookalike headers
  at `0x610a1f58/f60/f68/f70` (DSP1/3/4/5 class) belong to a second consumer —
  bound run 16 (`core1-lookalike-consumers-study.md`): a diagnostic
  (`CFspDspTest::TestEram`) path, so they stay free outside qctest/diagnostic
  operation as far as static evidence goes; ordinary-operation freedom still
  needs the unit to confirm.
- The constructor `0x6100177c`'s caller (no BL/veneer/word reference found;
  same unresolved-entry class as the verify routine and bmc1's ASGN task).
- The bodies of the constructor's helper callees `0x1131bb7` (only its
  `strb r1,[r0,#0xc]` zero-store was read) and `0x112ca7d`.
- Whether the boot verify walk's manager objects are the same objects the
  run-11 runtime upload sites use (both go through vtable address point
  `0x6117647c`, so they share the vtable — the object identity behind each
  cell is inferred, not proved).
- What the lookalike structure at `0x610a1ef8..0x610a1f78` is and who consumes
  it (resolved run 16: a second reservation table covering DSP1/3/4/5, consumed
  by `0x610293b2`/`0x6102a608` behind `CFspDspTest::TestEram` — see
  core1-lookalike-consumers-study.md).
- Per-slot capacity: the 1 MiB stride of the aperture tables bounds the slot
  layout, but no capacity check was found in the upload dispatch (the count
  byte and lengths are the only bounds the walk reads); actual silicon
  capacity is unknown.
- bmc1 mirrors none of this (untouched, like the run-7 boundary).

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python -m unittest discover -s tests -p test_core1_reservations_study.py -v
```