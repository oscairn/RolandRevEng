# CORE1 per-DSP flag register path (`CBmcDspDrv::SetDspFlag`)

A3 follow-up (entry, return and the mute gate): run 16's log pointed at the
BMC-side per-sample start/return contract and named the mode programmer
`SetExeMode 0x1130b6d` as the next open edge. This run censuses the sibling
driver that no earlier note traced: the per-DSP flag writer
`CBmcDspDrv::SetDspFlag`, its two manager wrappers, the global mask helpers and
the callers of each. Static, read-only file analysis of the pinned bmc0 CORE1
payload (SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`).
No firmware executed, no device access, no key/ciphertext material.

## Result (summary)

- **The driver `CBmcDspDrv::SetDspFlag(int dsp, unsigned char flag,
  eDSP_EVENT_REF_TYPE event) at 0x112f4ba` is the image's only writer of the
  per-DSP flag register table `0x4110{4..9}318` (+ MDSP entry `0x41102318`).**
  The body (assertion string `void CBmcDspDrv::SetDspFlag(int, unsigned char,
  eDSP_EVENT_REF_TYPE)` at `0x610b8cfc`) bounds dsp < 7 (`cmp r0,#7; blt` at
  `0x112f4c2..c4`, assertion line 0xd0), flag <= 0x7f (`bics r0,r5,#0x7f` at
  `0x112f4f8`, line 0xd1) and event < 9 (`cmp r4,#9; blo` at `0x112f4e4..e6`,
  line 0xd2), then packs `event<<28 | (flag & 0x7f)` (`orr.w r0,r0,r4,lsl #28`
  at `0x112f4fc`) and stores it through the per-DSP port table literal
  `0x113a9d0` (`ldr.w r1,[r1,r6,lsl #2]; str r0,[r1]` at `0x112f500..504`).
- **The port table words, verified exactly** (tool, below):
  `0x41104318, 0x41105318, 0x41106318, 0x41107318, 0x41108318, 0x41109318,
  0x41102318` — DSP0..DSP5 then MDSP, stride 0x1000, the `0x4110X318` form run
  13 named ("SetDspFlag `0x0113a9d0` = `0x4110{2..9}318`") but had not decoded
  as a list. (Run 13's prose `0x4110{2..9}318` is right only if `{2..9}` means
  the *digit* X = 4..9 for DSP0..5 plus X = 2 for MDSP; the sixth entry is
  `0x41102318`, not a 7th DSP port.)
- **Two manager wrappers reach the driver, both only through manager vtable
  slots** (address point `0x6117647c`): byte 0x10 = `0x1131bc7`
  (`CBmcDspMgr::SetDspFlag(unsigned char, bool)`, string at `0x610b99e5`) and
  byte 0x14 = `0x1131bfd` (`CBmcDspMgr::SetDspFlagBit(unsigned char, bool,
  bool)`, string at `0x610b9a16`). Neither has any direct BL, veneer or raw word
  caller image-wide — exactly the same virtual-only shape run 11 proved for
  `SetExeMode` (vtable byte 0x18 wrapper `0x1135099`) and the upload slots.
  `SetDspFlag` keeps a shadow byte at manager+0xc (`strb r1,[r0,#0xc]` at
  `0x1131bec`, flag OR'd/BIC'd at `0x1131c26..c38` for the Bit variant) and
  passes event 2 (bool true) or event 8 (bool false) to the driver
  (`ite ne; movne r2,#2; moveq r2,#8` at `0x1131bf0..f4`, `uxtb` at
  `0x1131c42`).
- **A global-mask pair sits next to the driver**: OR-set helper `0x112f4a6`
  (`ldr r2,[r1,#0xc]; orrs r0,r2; str r0,[r1,#0xc]` into `0x200847f0+0xc`, then
  `str r0,[0x41100004]`) and reader `0x112f4b4` (`ldr r0,[r0,#0xc]; bx lr`).
  They are reached only through manager vtable bytes 0x8/0xc (`0x1131bbd`/
  `0x1131bc3`, thunks at `0x1131bbe`/`0x1131bc2`) and one veneer cell
  `0x61076aa0` whose exactly four direct BL callers are
  `0x610016c2` (the boot verify routine, immediately before its five
  `SetExeMode` calls, with `movw r0,#0x45c5`) and three call sites in the
  debug/verify helper family `0x6102d2e6` (`0x6102d708`, `0x6102d762`,
  `0x6102d8a0`, passing `0x04000000`, `0x02000000`, `0x01000000` — single
  event-nibble bits). The reader has exactly one direct BL caller
  (`0x1131bc2`, the byte-0xc thunk); nothing else in the image reads
  `0x200847f0+0xc` through this function.
- **Boot connection, verified:** the boot verify routine (runs 11–12) calls the
  global setter at `0x610016be..c2` with `r0 = 0x45c5` — mask bits 0, 6, 7, 10,
  14 (0x45c5 = `0100 0101 1100 0101`) — right after its `0x61015b76` log call
  and before the five `SetExeMode` tuples. The initial value of
  `0x200847f0+0xc` is 0 (scatter initial-data expansion, tool-checked), so the
  stock boot leaves the mask at exactly `0x45c5` after the first pass — until
  the debug family's three single-bit passes run (their order/occurrence is not
  bound; see Not established).
- **Comparison with `SetExeMode 0x1130b6c` (same driver family, already
  censused in run 11):** `SetExeMode` writes `event<<28 | mode<<24 | argument`
  into the exec table `0x4110{4..9}310` (literal `0x113a9ec`, verified again
  this run) with argument asserted to 0/1 (`bfc ip,#1,#0xf` at `0x1130b9c`
  clears bits 15:1, then `cmp.w ip,#0` — DSP5 and DSP4-mode-2 take assertion
  line 0x5ce unconditionally). `SetDspFlag` is the same register-write shape
  with a 7-bit payload and no DSP4/5 restriction. Neither driver has a
  readback path except the dead `GetExeMode 0x1130be6` (run 11) — there is no
  "GetDspFlag" anywhere in the image (whole-image scan, below).

## Method

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python tools/core1_dsp_flag_study.py
```

The tool byte-pins 40 anchors (driver body bounds and packing, both manager
wrappers, the global helpers, the veneer cell, the boot call site and the five
boot `SetExeMode` tuples, the three debug-family call sites, the literal pools,
the three assertion signature strings, `SetExeMode`'s argument-bound check, and
the manager vtable word for the global-set thunk), verifies both port tables
word by word against their closed forms,
censuses direct BL/veneer/raw-word callers of every entry point against pinned
expectations, expands the scatter record's compressed initial data to check
`0x200847f0+0xc` starts at 0, and re-checks the pure packing model.
`ok` requires all of them.

Real tool output (command above, trimmed to the cited fields; full JSON in
ignored `local/core1-dsp-flag-report.json`):

```json
{
 "ok": true,
 "anchors_checked": 40,
 "anchor_problems": [],
 "flag_ports": {
  "0x41104318": "0x41104318",
  "0x41204318": "0x41105318",
  "0x41304318": "0x41106318",
  "0x41404318": "0x41107318",
  "0x41504318": "0x41108318",
  "0x41604318": "0x41109318",
  "0x41102318": "0x41102318"
 },
 "callers": {
  "driver": {"target": "0x112f4bb", "bl": ["0x1131bf8", "0x1131c4a"],
              "veneers": [], "words": []},
  "global_set": {"target": "0x112f4a7", "bl": ["0x1131bbe"],
                 "veneers": ["0x61076aa0"], "words": []},
  "global_read": {"target": "0x112f4b5", "bl": ["0x1131bc2"],
                  "veneers": [], "words": []},
  "mgr_set": {"target": "0x1131bc7", "bl": [], "veneers": [],
              "words": ["0x6117648c"]},
  "mgr_set_bit": {"target": "0x1131bfd", "bl": [], "veneers": [],
                  "words": ["0x61176490"]},
  "veneer_global_set": {"target": "0x61076aa1",
   "bl": ["0x610016c2", "0x6102d708", "0x6102d762", "0x6102d8a0"]}
 },
 "initial_dma_state_plus_c": "0x0",
 "model_checks": {"pack_flag_event2_flag2": "0x20000002",
  "pack_flag_event8_flag8": "0x80000008",
  "pack_exe_mode_dsp0_mode2": "0x32000000",
  "flag_bit_or_bit1": 2, "flag_bit_bic_bit3": 247}
}
```

(`exit=0`.)

Key disassembly, real recorded output of the commands below:

```sh
PYTHONPATH=tools <venv>/bin/python tools/core1.py <main>/local/b0c1a.bin --address 0x112f4ba --size 0x54
PYTHONPATH=tools <venv>/bin/python tools/core1.py <main>/local/b0c1a.bin --address 0x1131bc6 --size 0x8a
```

Real output (driver head, bounds and store; manager wrappers):

```text
0112f4ba  70b5       push      {r4, r5, r6, lr}
0112f4bc  1446       mov       r4, r2
0112f4be  0d46       mov       r5, r1
0112f4c0  0646       mov       r6, r0
0112f4c2  0728       cmp       r0, #7
0112f4c4  06db       blt       #0x112f4d4
0112f4c6  bde87040   pop.w     {r4, r5, r6, lr}
0112f4ca  dba2       adr       r2, #0x36c
0112f4cc  d021       movs      r1, #0xd0
0112f4ce  db48       ldr       r0, [pc, #0x36c] ; [0x112f83c] = 0x610b8cfc void CBmcDspDrv::SetDspFlag(int, unsigned char, eDSP_EVENT_REF_TYPE)
0112f4d0  05f00fbd   b.w       #0x1134ef2
0112f4d4  35f07f00   bics      r0, r5, #0x7f
0112f4d8  04d0       beq       #0x112f4e4
0112f4da  d7a2       adr       r2, #0x35c
0112f4dc  d121       movs      r1, #0xd1
0112f4de  d748       ldr       r0, [pc, #0x35c] ; [0x112f83c] = 0x610b8cfc void CBmcDspDrv::SetDspFlag(int, unsigned char, eDSP_EVENT_REF_TYPE)
0112f4e0  05f007fd   bl        #0x1134ef2
0112f4e4  092c       cmp       r4, #9
0112f4e6  06d3       blo       #0x112f4f6
0112f4e8  bde87040   pop.w     {r4, r5, r6, lr}
0112f4ec  d2a2       adr       r2, #0x348
0112f4ee  d221       movs      r1, #0xd2
0112f4f0  d248       ldr       r0, [pc, #0x348] ; [0x112f83c] = 0x610b8cfc void CBmcDspDrv::SetDspFlag(int, unsigned char, eDSP_EVENT_REF_TYPE)
0112f4f2  05f0febc   b.w       #0x1134ef2
0112f4f6  d249       ldr       r1, [pc, #0x348] ; [0x112f840] = 0x113a9d0
0112f4f8  05f07f00   and       r0, r5, #0x7f
0112f4fc  40ea0470   orr.w     r0, r0, r4, lsl #28
0112f500  51f82610   ldr.w     r1, [r1, r6, lsl #2]
0112f504  0860       str       r0, [r1]
0112f506  70bd       pop       {r4, r5, r6, pc}
---
01131bc6  8368       ldr       r3, [r0, #8]
01131bc8  d3f800c0   ldr.w     ip, [r3]
01131bcc  bcf1070f   cmp.w     ip, #7
01131bd0  04db       blt       #0x1131bdc
01131bd2  74a2       adr       r2, #0x1d0
01131bd4  8a21       movs      r1, #0x8a
01131bd6  7548       ldr       r0, [pc, #0x1d4] ; [0x1131dac] = 0x610b99e5 void CBmcDspMgr::SetDspFlag(unsigned char, bool)
01131bd8  03f08bb9   b.w       #0x1134ef2
01131bdc  31f07f0c   bics      ip, r1, #0x7f
01131be0  04d0       beq       #0x1131bec
01131be2  70a2       adr       r2, #0x1c0
01131be4  8b21       movs      r1, #0x8b
01131be6  7148       ldr       r0, [pc, #0x1c4] ; [0x1131dac] = 0x610b99e5 void CBmcDspMgr::SetDspFlag(unsigned char, bool)
01131be8  03f083b9   b.w       #0x1134ef2
01131bec  0173       strb      r1, [r0, #0xc]
01131bee  002a       cmp       r2, #0
01131bf0  14bf       ite       ne
01131bf2  0222       movne     r2, #2
01131bf4  0822       moveq     r2, #8
01131bf6  1868       ldr       r0, [r3]
01131bf8  fdf75fbc   b.w       #0x112f4ba
01131bfc  30b4       push      {r4, r5}
01131bfe  d0f808c0   ldr.w     ip, [r0, #8]
01131c02  dcf80040   ldr.w     r4, [ip]
01131c06  072c       cmp       r4, #7
01131c08  05db       blt       #0x1131c16
01131c0a  30bc       pop       {r4, r5}
01131c0c  65a2       adr       r2, #0x194
01131c0e  9421       movs      r1, #0x94
01131c10  6748       ldr       r0, [pc, #0x19c] ; [0x1131db0] = 0x610b9a16 void CBmcDspMgr::SetDspFlagBit(unsigned char, bool, bool)
01131c12  03f06eb9   b.w       #0x1134ef2
01131c16  0729       cmp       r1, #7
01131c18  05d3       blo       #0x1131c26
01131c1a  30bc       pop       {r4, r5}
01131c1c  61a2       adr       r2, #0x184
01131c1e  9521       movs      r1, #0x95
01131c20  6348       ldr       r0, [pc, #0x18c] ; [0x1131db0] = 0x610b9a16 void CBmcDspMgr::SetDspFlagBit(unsigned char, bool, bool)
01131c22  03f066b9   b.w       #0x1134ef2
01131c26  0124       movs      r4, #1
01131c28  04fa01f1   lsl.w     r1, r4, r1
01131c2c  002a       cmp       r2, #0
01131c2e  027b       ldrb      r2, [r0, #0xc]
01131c30  14bf       ite       ne
01131c32  1143       orrne     r1, r2
01131c34  22ea0101   biceq.w   r1, r2, r1
01131c38  0173       strb      r1, [r0, #0xc]
01131c3a  002b       cmp       r3, #0
01131c3c  14bf       ite       ne
01131c3e  0222       movne     r2, #2
01131c40  0822       moveq     r2, #8
01131c42  c9b2       uxtb      r1, r1
01131c44  dcf80000   ldr.w     r0, [ip]
01131c48  30bc       pop       {r4, r5}
01131c4a  fdf736bc   b.w       #0x112f4ba
```

Manager vtable words around the address point (tool-verified):

```text
0x6117647c 0x1135095   (+0x00)
0x61176480 0x1135189   (+0x04)
0x61176484 0x1131bbd   (+0x08  global-set thunk)
0x61176488 0x1131bc3   (+0x0c  global-read thunk)
0x6117648c 0x1131bc7   (+0x10  CBmcDspMgr::SetDspFlag)
0x61176490 0x1131bfd   (+0x14  CBmcDspMgr::SetDspFlagBit)
0x61176494 0x1135099   (+0x18  upload wrapper, run 11)
0x61176498 0x11350a9   (+0x1c  DRAM-IO wrapper, run 11)
```

## Established

- The per-DSP flag register path is bound end to end at the call-structure
  level: manager wrappers (vtable bytes 0x10/0x14) → driver `0x112f4ba` →
  packed word `event<<28 | flag&0x7f` → per-DSP ports `0x4110{4..9}318` +
  MDSP `0x41102318`. The event argument reaching the driver from the wrappers
  is 2 (bool true) or 8 (bool false).
- The manager wrappers have exactly zero direct callers; a resident loader that
  wants to raise or clear these flags must do it through the manager object's
  vtable (bytes 0x10/0x14) or by calling the driver directly, the same constraint
  run 11 proved for uploads and `SetExeMode`.
- The global mask word `0x200847f0+0xc` is written by the global setter (through
  manager vtable byte 0x8 or the veneer `0x61076aa0`) and read by the manager
  reader (byte 0xc). Its boot-time value after the boot verify routine is
  `0x45c5`; its initial value is 0. The three debug-family call sites each pass
  one event-nibble bit (`0x01000000`/`0x02000000`/`0x04000000`), so they are
  per-event enables, not value payloads.
- The `0x4110X318` port form of run 13 is now decoded as a complete 7-entry
  table; the exec sibling `0x4110{4..9}310` + `0x41102310` is verified beside it.
- `SetDspFlag` has no readback anywhere (no getter; the whole-image literal and
  caller scans in the tool found no reader of the table other than the writer's
  own pool).

## Not established

- What the flag register contents *do* on silicon (which event nibble gates what
  on the DSP side) — hardware behavior, needs the unit.
- Who calls the manager vtable bytes 0x10/0x14 at runtime: the strict
  virtual-call scan (this tool plus `core1_load_route_study.virtual_slot_sites`)
  finds sites at `+0x10`: `0x11021c0, 0x1102760, 0x110e03e, 0x110e06a,
  0x110e274, 0x1128ca0, 0x1128f20, 0x1128fa4, 0x1128fae, 0x1128fde, 0x1128fe8,
  0x1128ff2, 0x112a666, 0x112a848, 0x113126a, 0x6101ef68, 0x6102f648,
  0x6102fb78, 0x61030578, 0x61030584, 0x61030acc, 0x61034f7c, 0x610839e6,
  0x61083d1e` and at `+0x14`: `0x11021f0, 0x1102794, 0x110e060, 0x110e06a,
  0x1129064, 0x11312b8, 0x61030560, 0x6103056c, 0x61034cb8, 0x6103ce96,
  0x611b74c2, 0x611b7562, 0x611c9e38, 0x611ca2ca` — but byte-0x10/0x14 loads
  are a generic vtable layout shared by many classes (the byte-0x8 scan alone
  hits 3,268 sites), so which of these sites actually dispatch on the
  `CBmcDspMgr` object is NOT proven; attributing them needs the enclosing
  objects' vtables traced (deferred; the boot call sites are the proven ones).
- The three debug-family callers' enclosing context (the function
  `0x6102d2e6` family has no static entry — same unresolved-entry class as runs
  7/11/15/16; only `0x6102d602 b 0x6102d2e6` reaches it) and when they run.
- Whether the boot routine's `0x45c5` mask is later modified during ordinary
  operation (no other static caller was found; a computed write could exist).
- bmc1 mirrors none of this (untouched, like the run-7/15/16 boundary).
- The exact semantics of manager+0xc's shadow byte (the wrappers rewrite it
  wholesale in `SetDspFlag` and OR/BIC single bits in `SetDspFlagBit`; no reader
  of the shadow byte other than the global reader thunk and `SetDspFlagBit`
  itself was recovered).

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python -m unittest discover -s tests -p test_core1_dsp_flag_study.py -v
```

With the corpus: 8 passed (3.7 s). Without: 4 pass, 4 skip cleanly
(pinned-image guard).