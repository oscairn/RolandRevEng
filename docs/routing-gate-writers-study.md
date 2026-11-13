# Routing gate writers study

2026-11-13. Static check of who writes the two routing gate floats that run 8
(`docs/routing-2016-owner-study.md`) proved gate the per-pass effect dispatch,
and how the two per-core initializers lay them out. Run 8 left this open: "who
writes these fields" (run 8 log's own next-item list). No execution, no device
access, no key or ciphertext material.

## Question

Run 8 proved, with pinned instruction anchors, that
`CSimDSP4Routing::VSubProc` (0x413d0) skips its whole per-pass effect list when
`[x0+0x678] != 0.0` and runs one effect when `[x0+0x628] != 0.0` (both checked
at 0x41414–0x41424 and 0x41c48–0x41c94). The fields live in the 0x1b40-byte
routing object allocated by ctor 0x410e8. Nothing in run 8 named their writers.
The same study's owner probe showed `CSimDspMgr::WriteDspCoefFloat` (0xfba10)
reaching the same floats through routing vtable slot 4 = 0x41334 — a live
per-pass write path. This run pins the initialization-time writers.

## Method

`tools/routing_gate_writers_study.py` (this run) against the pinned ZENOLOGY
arm64 image (`sha256 b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`,
same image run 8 used). It:

1. byte-checks 102 pinned instruction/quad anchors covering the run 8 chain
   (ctor, core init, VProcSync pair, vtable slots, both VSubProc gate contexts)
   plus this run's new anchors in the two initializer tails;
2. decodes every `str` in each initializer body with capstone and keeps plain
   unsigned-offset stores to the gate offsets, requiring exactly one write per
   gate float per initializer, at pinned addresses;
3. reports per-core gate defaults, record keys, writer addresses and the owner
   chain, exiting nonzero on any mismatch.

Run: `BMC_CORPUS_DIR=<main>/local python tools/routing_gate_writers_study.py --json`.
Checks: `python -m unittest discover -s tests -p test_routing_gate_writers_study.py`.

## What was established

All addresses are ZENOLOGY arm64 image offsets. "DSP4" is the core run 8
studied (CSimDSP4Routing, struct 0x1b40); "DSP5" is its larger sibling
(CSimDSP5Routing, struct 0x46c8).

### The gate floats and their initializing writers (verified)

Both initializers write each gate float exactly once, as a `mov wN, #key` /
`str wN, [x0, #key_offset]` / `str xN, [x0, #value_offset]` triple — a 32-bit
record key at value_offset−8 paired with the 64-bit float at value_offset:

| core | initializer | enable (+0x628) | bypass (+0x678) | record keys |
|------|-------------|-----------------|-----------------|-------------|
| DSP4 | 0x42e14     | `str x9,[x0,#0x628]` at 0x432b8 = 1.0 | `str x8,[x0,#0x678]` at 0x43304 = 0.0 | 0x0000 (+0x620), 0x07c4 (+0x670) |
| DSP5 | 0x34d690    | `str x8,[x0,#0x628]` at 0x34db9c = 1.0 | `str x8,[x0,#0x678]` at 0x34dbd8 = 0.0 | 0x4fce (+0x620), 0x4d02 (+0x670) |

Defaults match the gates' expectations: enable=1.0 (effects run), bypass=0.0
(dispatch not skipped). So after construction the routing dispatch is live and
the run 8 gate reads 1.0/0.0 until something changes the floats.

DSP4's enable key 0x0000 looks odd but is real: 0x432b0 stores w10 (=0) to
[x0,#0x620] right before the 0x628 value store (anchor-pinned `mov w11,#0x134`-
style ladder around it). The 0x50-byte tail-record shape is identical in both
initializers (key at +0, value at +8), matching the transfer-spaces study's
0x48-stride record machinery as a sibling layout.

### The manager's coefficient path reaches the same floats (verified, no trace)

Run 8's owner probe is byte-checked again: vtable byte 0x10 = 0x41334 (slot 2
by 8-byte index), reached from `CSimDspMgr::WriteDspCoefFloat` 0xfba10 through
`CSimDSP4Routing`'s vtable (0x9cfd78 region: byte 0x8 = 0x412fc, byte 0x10 =
0x41334, byte 0x18 = 0x41380, byte 0x20 = 0x413d0 — anchors 0x9cfd70/0x9cfd88/
0x9cfd90). Both helper slots are verified record lookups: byte 0x18 (0x41380)
loads the routing object's record-table base `[x0+0x38]+0xce0` and linearly
scans 0x1ba 8-byte key entries for the requested key, returning a pointer into
the table; byte 0x10 (0x41334) scans 0xce 16-byte entries over `[x0+0x38]` and
returns entry+8. These are the manager-side views of the same 0x50-stride
records the initializer wrote. This closes the loop run 8 opened:
`WriteDspCoefFloat` resolves a coefficient key through one of these helpers and
writes the value slot the VSubProc gate reads. (Correction 2026-11-13, run 10:
this section originally called 0x41334 "slot 4" and 0x41380 "slot 5"; the quad
anchors were right but the slot names were wrong — byte 0x10 is slot 2 and
byte 0x18 slot 3 by 8-byte index. The caller census is in
[routing-gate-callers-study.md](routing-gate-callers-study.md).)

### DSP5 control analog (verified instructions, inferred semantics)

`CSimDSP5Routing::VSubProc` 0x34c244 loads the manager from global 0x9c8480
(`adrp x8,#0x9c8000; ldr x8,[x8,#0x480]` at 0x34c26c, byte-pinned; the global
itself is 0 in the image — filled at load), then reads both gate records
through the manager per pass: 0x34c2b8 `ldr x10,[x9,#0x3300]; ldr s0,
[x10,#0x28]` (the +0x628 record) and the #0x8d8 variant for +0x678's. Unlike
DSP4's hard-coded dispatch gate, DSP5's VSubProc takes no [x0+0x678] != 0
branch in its head — the skip decision lives in its caller or in the effect
objects. That asymmetry is **inferred** from the disassembled prologue only;
the full DSP5 pass body was not walked this run. (Correction 2026-11-13,
run 10: this section's prose gave the DSP5 routing vtable pointer as
0xa520e98; the ctor bytes at 0x34c0b8..0x34c0c0 compute 0xa52000+0xe98 =
0xa52e98. The anchors were right, the arithmetic in the prose was wrong.)

### DSP5 initializer scale (verified)

0x34d690 spans 0x34d690–0x351808 (0x41f78 bytes, ~4.1 MB of stores in the
image) writing the 0x46c8-byte struct: a giant ladder of `add wN,w20,#k;
umaddl xN,wN,w25,xN` address computations and paired `str` pairs, ending
`ldp x29,x30,[sp,#0x130]; add sp,sp,#0x140; ret` at 0x3517e8–0x351804
(byte-pinned). The 0x42e14 DSP4 initializer spans 0x42e14–0x4439c (0x1588
bytes) for the 0x1b40 struct. Both tails write the gate records last before
their epilogue — the gate floats are the final fields initialized.

## Reproduce

```
BMC_CORPUS_DIR=<main>/local python tools/routing_gate_writers_study.py --json
BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests -p test_routing_gate_writers_study.py -v
```

The tool exits 0 only when all 102 anchors match and both initializers write
each gate float exactly once at the pinned addresses. Tests: 5 pass with the
corpus (2 skip without); run 8's routing suite (9), the core1 family (57, 1
skipped) and test_bmc_ipc (4) still pass.

## What is not established

- Whether the stock application ever flips bypass (+0x678) to nonzero through
  WriteDspCoefFloat, muting the effect list — needs runtime capture or a
  caller census of 0xfba10 with bypass-key arguments (not done).
- The 0x50-byte tail records' full key space: only the two gate keys per core
  were decoded; the rest of the ladder (hundreds of records) is unchecked.
- DSP5's VSubProc full body: the skip-gate asymmetry is inferred from the
  prologue, not proved over the whole function.
- The global 0x9c8480's loader: image-rest value 0, filled at load; which
  startup path writes it is unknown (same situation as run 7's bmc1 RXDT
  router note).
- No live or runtime evidence: everything here is static on the pinned image.

## Best next item

Census callers of `CSimDspMgr::WriteDspCoefFloat` 0xfba10 (and its DSP5
sibling if any) and classify which record keys they write — this would answer
whether the application can flip the bypass gate at runtime, purely static.