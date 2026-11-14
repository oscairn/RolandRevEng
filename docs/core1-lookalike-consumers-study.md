# CORE1 runtime consumers of the DSP1/3/4/5 program-reservation lookalikes

A2 follow-up queued by run 15's log ("trace the `0x610a1ef8..` lookalike run's
consumers (`0x6102956c`/`0x6102a750..c` pools) to say whether DSP1/3/4/5 receive
runtime program loads through it"). Static, read-only file analysis of the pinned
bmc0 CORE1 payload (SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`),
reusing the boot-route anchors of runs 11–15. No firmware executed, no device
access, no key/ciphertext material.

## Result (summary)

- **The run-15 lookalikes are a real second reservation table, and its consumers
  are now bound.** The 16 same-shape (header, list) pairs spanning
  `0x610a1ef8..0x610a1f78` (the cluster run 15 named, including the
  `0x610a1f58/f60/f68/f70` DSP1/3/4/5 pairs and the count-2/5/11 neighbors run
  15's count-1 scan did not decode) are consumed by two ERAM functions inside
  the manager upload region:
  - **Seed consumer `0x610293b2`** uploads the four phase-0 "seed" lists
    (entries `0x610a1ef8`, `0x610a1f08`, `0x610a1f18`, `0x610a1f28`) through
    manager vtable byte 0x18, after a 0x3a00 wait call through vtable byte 0x8.
  - **Load/verify consumer `0x6102a608`** uploads the DSP1/3/4/5 stub pairs
    (`0x610a1f38`..`0x610a1f50`) through vtable byte 0x18 and the four phase-1
    coefficient lists (`0x610a1f00`, `0x610a1f10`, `0x610a1f20`, `0x610a1f30`)
    through vtable byte 0x1c, then tail-calls `0x610293b2` (at `0x6102a662`).
- **Both consumers are driven from the diagnostic dispatcher `0x1126a6c`**
  (the function whose queue-poll helper `0x11269ba` has no static entry — the
  same unresolved-entry class as runs 7/11/15):
  - `0x1126bba bl 0x1134c7c` (veneer `movw ip,#0xf4b3; movt ip,#0x6103; bx ip`
    → `0x6103f4b3`) calls **`CFspDspTest::TestEram 0x6103f4b2`** — the string
    `CFspDspTest::EResult CFspDspTest::TestEram()` at `0x610c59e8` is logged by
    its error path `0x6103f4ca`. This is the "diagnostic TestEram-associated
    dispatch" the queue's V-STAGE note mentions.
  - `0x1126d1e b.w 0x1134cea` (veneer → `0x6102a609`) calls the load/verify
    consumer `0x6102a608` directly.
  - TestEram is in turn called by the qctest state machine `0x61080fe0..`
    (`0x6108104e bl 0x6103f4b2`, `0x61081062 bl 0x6103f49c`); the state machine
    has no direct BL/veneer caller, only the pointer-table word `0x6117b0f0 =
    0x61080fe1` (analogous to run 11's ITCM pointer tables).
- **The lookalike table is static image data; its runtime uploader is
  `0x6102a230`.** The 16 pairs sit literal in ERAM data (verified: `0x610a1ef8`
  = `0x00030100,0x610a52e8` … `0x610a1f70` = `0x00010500,0x610b3fd4`).
  `0x6102a230` (code, entered only by `0x6102a48c b 0x6102a230`) is the runtime
  uploader that selects manager vtable byte 0x1c (the same DRAM-IO-phase upload
  byte the boot route's phase 2 uses) for the four phase-1 lists and byte 0x18
  for the phase-0 stubs/programs.
- **Yes, DSP1/3/4/5 receive program loads outside the boot route** (verified call
  structure; the argument values are pinned below). The program lists:
  DSP1 3 records (634-byte program at `0x41580020` + two 6-byte records),
  DSP3 1 record (390 bytes at `0x41780020`), DSP4 5 records (13,750-byte
  program at `0x41880020` + four 6-byte), DSP5 11 records (13,678-byte program
  at `0x41980020` + ten 6-byte). The phase-1 lists are DRAM-IO (bank-0
  apertures `0x41540000/0x41740000/0x41840000/0x41940000`). Whether these loads
  actually run at runtime depends on the dispatcher reaching those call sites
  (see Not established).
- **The dispatcher is behind `CFspDspTest::TestEram`, i.e. a diagnostic, not the
  normal boot path.** The boot verify routine (runs 11–15) remains the only
  boot-time user of the stock reservation table `0x61085dc4..`; this second table
  belongs to the qctest/diagnostic machinery. DSP1/3/4/5 staying free during
  ordinary operation is therefore still plausible but now bounded by this
  diagnostic path rather than unbounded.

## Method

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python tools/core1_lookalike_consumers_study.py <main>/local/b0c1a.bin
```

The tool byte-pins 48 anchors: the 16 lookalike entry pairs, the first
consumer's head and four list loads, the second consumer's twelve list loads,
its tail call and the constructor entry, the dispatcher/TestEram/veneer chain,
and both upload wrappers; it decodes all 16 entries plus the four seed entries,
maps every record onto the run-13/15 aperture closed forms, re-runs the
capstone branch scan, the committed veneer scanner and the aligned word scan
over the whole image for every chain function, and reads the manager cells and
the EFCT context word through the scatter records. `ok` requires all of them.

Real tool output (command above, trimmed to the cited fields):

```json
{
 "ok": true,
 "sha256": "6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154",
 "anchors_checked": 48,
 "anchor_problems": [],
 "table2_matches": true,
 "table1_matches": true,
 "efct_context_word_0x2009bbf8": "0xf0629942",
 "manager_cells": {"0x20084b8c": "0x0", "0x20084ba0": "0x0", "0x20084bb4": "0x0"},
 "table2_apertures[0..1]": [
  {"entry": "0x610a1ef8", "dsp": 1, "phase": 0, "base": "0x41580000",
   "ranges": [{"start": "0x41580020", "length": 634},
               {"start": "0x41581020", "length": 6},
               {"start": "0x41586020", "length": 6}]},
  {"entry": "0x610a1f00", "dsp": 1, "phase": 1, "base": "0x41540000",
   "ranges": [{"start": "0x41540000", "length": 0},
               {"start": "0x41540080", "length": 8},
               {"start": "0x415405a8", "length": 16}]},
 ...
 },
 "call_chains": {
  "0x1126a6d": {"branches": [], "veneers": [], "words": []},
  "0x11269bb": {"branches": [], "veneers": [], "words": []},
  "0x1126cec": {"branches": [["0x110332e", "bl"]], "veneers": [], "words": []},
  "0x1134c7c": {"branches": [["0x1126bba", "bl"]], "veneers": [], "words": []},
  "0x1134cea": {"branches": [["0x1126d1e", "b.w"]], "veneers": [], "words": []},
  "0x6103f4b2": {"branches": [["0x6108104e", "bl"]],
                 "veneers": ["0x1134c7c"], "words": []},
  "0x61080fe1": {"branches": [], "veneers": [], "words": ["0x6117b0f0"]},
  "0x610293b2": {"branches": [["0x6102a478", "bl"], ["0x6102a662", "b.w"]],
                 "veneers": [], "words": []},
  "0x6102a230": {"branches": [["0x6102a48c", "b"]], "veneers": [], "words": []},
  "0x6102a608": {"branches": [], "veneers": ["0x1134cea"], "words": []},
  "0x1135099": {"branches": [], "veneers": [], "words": ["0x61176494"]},
  "0x11350a9": {"branches": [], "veneers": [], "words": ["0x61176498"]}
 }
}
```

(`exit=0`; the full 16-entry decode follows.)

Full decoded lookalike table (real tool-side decode, command above):

```text
0x610a1ef8 header 0x30100 count 3 dsp 1 phase 0 list 0x610a52e8: (w0 0x20, len 0x27a, rep 0x1000, src 0x610a505c); (w0 0x1020, len 0x6, rep 0x5000, src 0x610a52d8); (w0 0x6020, len 0x6, rep 0x5000, src 0x610a52e0)
0x610a1f00 header 0x50101 count 5 dsp 1 phase 1 list 0x610a5350: (w0 0x0, len 0x0, rep 0x80, src 0x610a5318); (w0 0x80, len 0x8, rep 0x528, src 0x610a5320); (w0 0x5a8, len 0x10, rep 0x10, src 0x610a5328); (w0 0x2400, len 0x8, rep 0x800, src 0x610a5338); (w0 0x2c00, len 0x10, rep 0x400, src 0x610a5340)
0x610a1f08 header 0x10300 count 1 dsp 3 phase 0 list 0x610a556c: (w0 0x20, len 0x186, rep 0x1000, src 0x610a53e4)
0x610a1f10 header 0x50301 count 5 dsp 3 phase 1 list 0x610a55b4: (w0 0x0, len 0x0, rep 0x0, src 0x610a557c); (w0 0x0, len 0x8, rep 0x800, src 0x610a5584); (w0 0x800, len 0x10, rep 0x10, src 0x610a558c); (w0 0x2400, len 0x8, rep 0x800, src 0x610a559c); (w0 0x2c00, len 0x10, rep 0x400, src 0x610a55a4)
0x610a1f18 header 0x50400 count 5 dsp 4 phase 0 list 0x610a8bec: (w0 0x20, len 0x35b6, rep 0x4000, src 0x610a5614); (w0 0x4020, len 0x6, rep 0x1000, src 0x610a8bcc); (w0 0x5020, len 0x6, rep 0x1000, src 0x610a8bd4); (w0 0x6020, len 0x6, rep 0x400, src 0x610a8bdc); (w0 0x6420, len 0x6, rep 0x1000, src 0x610a8be4)
0x610a1f20 header 0x50401 count 5 dsp 4 phase 1 list 0x610a8c74: (w0 0x0, len 0x0, rep 0x0, src 0x610a8c3c); (w0 0x0, len 0x8, rep 0x900, src 0x610a8c44); (w0 0x900, len 0x10, rep 0x10, src 0x610a8c4c); (w0 0x2400, len 0x8, rep 0x800, src 0x610a8c5c); (w0 0x2c00, len 0x10, rep 0x400, src 0x610a8c64)
0x610a1f28 header 0xb0500 count 11 dsp 5 phase 0 list 0x610b0cb0: (w0 0x20, len 0x356e, rep 0x8000, src 0x610ad6f0); (w0 0x8040, len 0x6, rep 0x1000, src 0x610b0c60); (w0 0x9040, len 0x6, rep 0x1000, src 0x610b0c68); (w0 0xa040, len 0x6, rep 0x1000, src 0x610b0c70); (w0 0xb040, len 0x6, rep 0x1000, src 0x610b0c78); (w0 0xc040, len 0x6, rep 0x1000, src 0x610b0c80); (w0 0xd040, len 0x6, rep 0x400, src 0x610b0c88); (w0 0xd440, len 0x6, rep 0x400, src 0x610b0c90); (w0 0xd840, len 0x6, rep 0x1000, src 0x610b0c98); (w0 0xe840, len 0x6, rep 0x1400, src 0x610b0ca0); (w0 0xfc40, len 0x6, rep 0x2c0, src 0x610b0ca8)
0x610a1f30 header 0x50501 count 5 dsp 5 phase 1 list 0x610b0d98: (w0 0x0, len 0x0, rep 0x0, src 0x610b0d60); (w0 0x0, len 0x8, rep 0x13a0, src 0x610b0d68); (w0 0x13a0, len 0x10, rep 0x10, src 0x610b0d70); (w0 0x2400, len 0x8, rep 0x800, src 0x610b0d80); (w0 0x2c00, len 0x10, rep 0x400, src 0x610b0d88)
0x610a1f38 header 0x20100 count 2 dsp 1 phase 0 list 0x610b3b8c: (w0 0x0, len 0x12, rep 0x20, src 0x610b3b74); (w0 0x20, len 0x0, rep 0x0, src 0x610b3b88)
0x610a1f40 header 0x20300 count 2 dsp 3 phase 0 list 0x610b3bd0: (w0 0x0, len 0x12, rep 0x20, src 0x610b3bb8); (w0 0x20, len 0x0, rep 0x0, src 0x610b3bcc)
0x610a1f48 header 0x20400 count 2 dsp 4 phase 0 list 0x610b3c14: (w0 0x0, len 0x12, rep 0x20, src 0x610b3bfc); (w0 0x20, len 0x0, rep 0x0, src 0x610b3c10)
0x610a1f50 header 0x20500 count 2 dsp 5 phase 0 list 0x610b3c58: (w0 0x0, len 0x12, rep 0x20, src 0x610b3c40); (w0 0x20, len 0x0, rep 0x0, src 0x610b3c54)
0x610a1f58 header 0x10100 count 1 dsp 1 phase 0 list 0x610b3d4c: (w0 0x20, len 0xc6, rep 0xc6, src 0x610b3c84)
0x610a1f60 header 0x10300 count 1 dsp 3 phase 0 list 0x610b3e24: (w0 0x20, len 0xc6, rep 0xc6, src 0x610b3d5c)
0x610a1f68 header 0x10400 count 1 dsp 4 phase 0 list 0x610b3efc: (w0 0x20, len 0xc6, rep 0xc6, src 0x610b3e34)
0x610a1f70 header 0x10500 count 1 dsp 5 phase 0 list 0x610b3fd4: (w0 0x20, len 0xc6, rep 0xc6, src 0x610b3f0c)
```

Key disassembly, real recorded output of the commands below:

```sh
PYTHONPATH=tools <venv>/bin/python - <<'EOF'
from core1 import Core1
core = Core1('<main>/local/b0c1a.bin')
for line in core.disasm(0x610293b2, 0x40): print(line)
for line in core.disasm(0x6102a608, 0x14): print(line)
for line in core.disasm(0x6102a230, 0x20): print(line)
EOF
```

Real output:

```text
610293b2  2de9f04f   push.w    {r4, r5, r6, r7, r8, sb, sl, fp, lr}
610293b6  0446       mov       r4, r0
610293b8  2ded068b   vpush     {d8, d9, d10}
610293bc  81b0       sub       sp, #4
610293be  0069       ldr       r0, [r0, #0x10]
610293c0  0168       ldr       r1, [r0]
610293c2  8a68       ldr       r2, [r1, #8]
610293c4  4ff46851   mov.w     r1, #0x3a00
610293c8  9047       blx       r2
610293ca  6068       ldr       r0, [r4, #4]
610293cc  0168       ldr       r1, [r0]
610293ce  8a69       ldr       r2, [r1, #0x18]
610293d0  6549       ldr       r1, [pc, #0x194] ; [0x61029568] = 0x610a1ef8
610293d2  9047       blx       r2
610293d4  e068       ldr       r0, [r4, #0xc]
610293d6  0168       ldr       r1, [r0]
610293d8  8a69       ldr       r2, [r1, #0x18]
610293da  6449       ldr       r1, [pc, #0x190] ; [0x6102956c] = 0x610a1f08
610293dc  9047       blx       r2
610293de  2069       ldr       r0, [r4, #0x10]
610293e0  0168       ldr       r1, [r0]
610293e2  8a69       ldr       r2, [r1, #0x18]
610293e4  6249       ldr       r1, [pc, #0x188] ; [0x61029570] = 0x610a1f18
610293e6  9047       blx       r2
610293e8  6069       ldr       r0, [r4, #0x14]
610293ea  0168       ldr       r1, [r0]
610293ec  8a69       ldr       r2, [r1, #0x18]
610293ee  6149       ldr       r1, [pc, #0x184] ; [0x61029574] = 0x610a1f28
610293f0  9047       blx       r2
---
6102a608  10b5       push      {r4, lr}
6102a60a  0446       mov       r4, r0
6102a60c  4068       ldr       r0, [r0, #4]
6102a60e  0168       ldr       r1, [r0]
6102a610  8a69       ldr       r2, [r1, #0x18]
6102a612  6549       ldr       r1, [pc, #0x194] ; [0x6102a7a8] = 0x610a1f38
6102a614  9047       blx       r2
6102a616  e068       ldr       r0, [r4, #0xc]
6102a618  0168       ldr       r1, [r0]
6102a61a  8a69       ldr       r2, [r1, #0x18]
---
6102a230  70b5       push      {r4, r5, r6, lr}
6102a232  0126       movs      r6, #1
6102a234  2ded028b   vpush     {d8}
6102a238  82b0       sub       sp, #8
6102a23a  0446       mov       r4, r0
6102a23c  0676       strb      r6, [r0, #0x18]
6102a23e  4068       ldr       r0, [r0, #4]
6102a240  0168       ldr       r1, [r0]
6102a242  ca69       ldr       r2, [r1, #0x1c]
6102a244  3549       ldr       r1, [pc, #0xd4] ; [0x6102a31c] = 0x610a1f00
6102a246  9047       blx       r2
6102a248  e068       ldr       r0, [r4, #0xc]
6102a24a  0168       ldr       r1, [r0]
6102a24c  ca69       ldr       r2, [r1, #0x1c]
6102a24e  3449       ldr       r1, [pc, #0xd0] ; [0x6102a320] = 0x610a1f10
```

Wait-for-DMA helper at `0x61029392` (seed consumer's loop helper, called from
`0x6102939c`/`0x610293a6` 4x each) and its `TestEram` string:

```text
610c59e8  43464653 70447370 3a745370 3a724545 ... 'CFspDspTest::EResult CFspDspTest::TestEram()'
```

## Established

- The run-15 lookalike run is a complete second reservation table in the boot
  entry format (header `(count<<16)|(dsp<<8)|phase`, list pointer, 16-byte
  records), covering DSP1/3/4/5 in both phases — the four slots the boot route
  leaves static-reservation-empty.
- Its consumers are `0x610293b2` (seeds, manager vtable byte 0x18 after a 0x3a00
  wait through byte 0x8) and `0x6102a608` (stub pairs through byte 0x18, phase-1
  coefficient lists through byte 0x1c, tail-calling `0x610293b2`), both driven
  from the diagnostic dispatcher `0x1126a6c` through the veneers `0x1134c7c`
  (→ `CFspDspTest::TestEram 0x6103f4b2`) and `0x1134cea` (→ `0x6102a609`).
- `TestEram` is the diagnostic the V-STAGE note called "diagnostic
  TestEram-associated dispatch"; the qctest state machine `0x61080fe0..` calls it
  at `0x6108104e`/`0x61081062` and is reached only through pointer-table word
  `0x6117b0f0`.
- The second table is runtime-constructed by `0x6102a230` (entered only by
  `0x6102a48c b 0x6102a230`); the manager cells it works through
  (`0x20084b8c/ba0/bb4`) are still zero in the stock image (scatter-verified),
  consistent with run 15.

## Not established

- Whether the diagnostic dispatcher `0x1126a6c` ever runs on the instrument
  during normal operation (no static entry for it or its poll helper
  `0x11269ba`; qctest is entered via `0x11340e8`/`0x113410c`/`0x1134130`
  diagnostic paths with no direct callers either — the qctest activation question
  from the queue's earlier passes remains open, and its resolution needs the unit
  or a stronger model).
- Whether the uploads actually execute/verify successfully on hardware (the call
  structure and argument values are pinned; the NG paths and the 0x3a00 wait's
  units are not measured).
- The semantics of the seed lists' `rep` word (word2) and the `src` word
  (word3) beyond their pinned values; run 15's record interpretation for the
  boot table (word0/length/length/source) is reused here without independent
  proof that the diagnostic path reads them identically.
- The 6-byte and 0xc6-byte small records' meaning (they look like stubs/markers;
  their consumers' bodies are not analyzed).
- bmc1 mirrors none of this (untouched, like the run-7/15 boundary).

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python -m unittest discover -s tests -p test_core1_lookalike_consumers_study.py -v
```