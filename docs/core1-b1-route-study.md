# bmc1 CORE1 receive route: does the second chip mirror bmc0?

2026-11-13, glm-overnight-2 run 7. Static cross-check closing the runs-5/6 open
question — "whether bmc1 (`b1c1a.bin`) mirrors the route" was explicitly
untouched in both [core1-ef-route-study](core1-ef-route-study.md) and
[core1-ef-319-consumers-study](core1-ef-319-consumers-study.md). Inputs: pinned
`local/b1c1a.bin`, SHA-256
`c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd` (matches the
value recorded in [core1-service-startup-mmio](core1-service-startup-mmio.md);
verified by `shasum -a 256` and the tool's digest gate), plus pinned bmc0
`local/b0c1a.bin` SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`
for the census comparison. Every instruction claim below is **verified** (exact
byte match via `tools/core1_b1_route_study.py` and
`tests/test_core1_b1_route_study.py`); structural and role claims are marked
**verified** (decoded branch/table structure) or **inferred**. No device access,
no execution of vendor code, no key material touched.

## Answer

**Verified: bmc1 mirrors the bmc0 receive route's structure and byte-1
semantics at every recovered decision, with different addresses, different
consumed byte-1 sets on the helper and parser, and one added system command.**
The recovered bmc1 chain is: second-ring enqueue `0x0110a714` → ASGN-analog
task `0x0110a9e2` → (byte-0 high nibble 0) byte-1 `0x07` else CUMDWRx
`0x0110b7da`; (high nibble 3/7) direct bodies; (high nibble 0xb and all others)
byte-stream parser `0x0110f70c`; plus the route-0-fallthrough-style remote-state
helper `0x0112a1ce`. Nothing on this chain compares byte 1 against 0xE1, 0xE2 or
0xEF except the parser, which consumes 0xEF exactly as bmc0's does. A wire
frame addressed 0xE1 or 0xE2 is not distinguished by any recovered bmc1 byte-1
decision — the addressing question from
[bmc-addressing-and-loader-open-questions](bmc-addressing-and-loader-open-questions.md)
stays open on both images: the recovered receive routes do not test byte 1 for
0xE1/0xE2 at all.

## The bmc1 ASGN-analog task 0x0110a9e2

Entry `0x0110a9e2 push {r4, r5, lr}` (**verified**). The task reads a work word
to `sp+0x40`, then dispatches on the word's byte-0 high nibble
(`0x0110aa2a ldrb.w r0,[sp,#0x40]; lsrs #4`): 0 → `0x0110aa54`, 3 →
`0x0110aa4a`, 7 → `0x0110aa6e`, 0xb → `0x0110aa76`, everything else → parser
call `0x0110aa40 bl #0x110f70c` (**verified**). This is the same four-special
+ parser structure as bmc0's `0x0110a65c`, at different addresses.

Nibble 0 path: `0x0110aa54 ldrb.w r0,[sp,#0x41]` (byte 1), `0x0110aa58 cmp
r0, #7`, special → `0x0110aa66` → `0x0111cdfc`; otherwise CUMDWRx
`0x0110aa60 bl #0x110b7da` (**verified**). Identical semantics to bmc0's
byte-1-vs-0x07 test.

The ingress into this task differs from bmc0's recovered one: the second-ring
enqueue analog `0x0110a714` (a 2048-slot ring at `0x200804d8`/`0x20087cf4`
with counters at +8/+0xc and an almost-full gate at `0x0110a7fc`, threshold
0x600 — **verified** instruction bytes) has exactly two BL callers,
`0x0110a94a` (inside helper `0x0110a92a`) and `0x0110a9a2` (inside task
`0x0110a960`) (**verified**). Neither is a 16-route TBB dispatcher matching
bmc0's first-router `0x0111ea24` shape, and the ASGN task itself has no
direct BL caller, no aligned Thumb-pointer word reference and no MOVW/MOVT/BX
construction anywhere in the image (**verified** by `tools/core1_xrefs.py`-style
scans inline in this run and by the tool's value-set checks). Its task-table
entry is therefore built at runtime or in a form this run did not recover —
the bmc1 first-router analog (RXDT) is **not recovered** and is the note's
main unrecovered edge.

## CUMDWRx 0x0110b7da: bmc1 adds command 0x53

Command extraction is identical: `0x0110b7dc ubfx r2, r1, #8, #8` (**verified**).
The dispatcher consumes **nine** commands — 0x51, 0x52, **0x53** (new: body
`0x0110b860 pop.w {r4, lr}; b.w #0x11341a0`), 0x54, 0x58, 0x70, 0x74, 0x75,
0x7b — and pops bare for everything else (`0x0110b812 pop {r4, pc}`)
(**verified**). bmc0 consumed eight (no 0x53). The 0x58 body reads bits 23:16
(`0x0110b830 ubfx r0, r1, #0x10, #8`) in both images; bmc0 tails to
`0x0110c5a4`, bmc1 to `0x0110daf8`.

## Remote-state helper 0x0112a1ce: different consumed set

Same gate: `0x0112a1d4 cmp.w r2, r1, lsr #4` with `r2 = 2` — only words whose
byte-0 high nibble is 2 reach the byte-1 switch (**verified**). But the bmc1
consumed byte-1 set is **0x80..0x88 (TBB at `0x0112a1f2`, table bytes
`efeecfbf9ded14aedf`), 0x89, 0x8a, 0x8e, 0x8f, 0x9f** — bmc0's helper consumed
0x80..0x85, 0x8e, 0x8f, 0xbc, 0xbd, 0xbe. Nothing is consumed for 0xEF, 0xE1,
0xE2: bhs to `0x0112a21e` and the 0x89/0x8a/0x9f compares reject everything
else (**verified**). The shared tail is `0x0112a46c pop.w {r4, lr}; movs r0,
#8; b.w #0x11011dc` (**verified**) — bmc0's tail branched to `0x11020c0`, a
different (bmc0) task-epilogue helper; bmc1's goes to its own `0x11011dc`.
The bodies write flag/mask words on the object at `0x200844f4` (byte states
+1/+2, word masks at +8..+0x3c; **verified** at the `0x112a3d6..a42c` body
samples) — the bmc0 analog wrote on `0x20083e74`. Different objects, same shape
(**inferred** role: remote-state setter).

## Parser 0x0110f70c: same 0xEF semantics, different neighbors

Entry and nibble TBB match bmc0's structure: low nibble of byte 0 selects,
15 rejects (`0x0110f720 bhs.w #0x111022e`; TBB at `0x0110f724`, table bytes
`f8f7a3f8f6f5f4f30835f2c7f8f9f0`, **verified**). The shared bodies re-dispatch
on byte 1 through binary-search chains (`0x0110fadc..fb94`, **verified** at
the 0x76/0x77/0x7c/0x80/0x88/0x8c/0x8d/0x99/0xa6/0xb3..0xb7 compares and both
sub-TBBs), consuming 0x76, 0x77, 0x7c, 0x80, 0x88, 0x8c, 0x8d, 0x99, 0xa5,
0xa6, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, **0xee**, **0xef** — a different set from
bmc0's (bmc0 additionally had 0xa5..0xad, 0xbc..0xbe ranges; bmc1's chain has
its own, this run pinned only the skeleton above).

The **0xEF body `0x1110176`** is semantically the bmc0 analog (**verified**):
payload bytes 2..3 must have bit 15 set (`0x01110178 tst.w r0, #0x8000`),
else reject; singleton getter `0x01110cfc` returns `0x61402164` (pool at
`0x011110dc`, **verified**); flag byte at object +8 (bmc0 used +0xa) gates an
optional cleanup call `0x11118a4` (bmc0: `0x110f522`); then a 16-entry
pointer-table walk (`0x011101d6 cmp r5, #0x10`) over the pointer array at
`0x20084d28` (bmc0: `0x20084d88`), calling each entry's vtable slot +0x10 and
slot +0x20 twice, then `0x1104022` (bmc0: `0x1104e34`) per entry
(**verified** at the call sites; per-entry semantics **inferred** as in run 6).
The bmc1 per-entry stride computes to 0x2ac bytes (`smulbb r0, r5, #0xab`
then ×4); while re-deriving this the run also recomputed bmc0's stride from
its own instruction bytes (`rsb/add/add` chain) as 496 = 0x1f0, not the 0x148
printed in run 6's note — a stray value in the earlier prose, not reproduced
by `tools/core1_ef_319_consumers_study.py`'s anchors (the note's table text
is wrong; the committed anchors are unaffected).

The **0xEE body `0x1110160`** is also the analog of bmc0's single-shot: byte 2
& 0x3f, getter `0x01110cf8` (returns `0x61401280`), then `0x110f364`
(bmc0: `0x110d594`).

## Compare census: the two images differ an order of magnitude

The committed bmc0 scanner (`tools/core1_ef_route_study.py` as of commit
`18de324`, byte-identical today) and the new bmc1 tool run the same algorithm:

| Immediate | bmc0 (verified, committed tool) | bmc1 (verified, new tool) |
|---|---:|---:|
| 0x02 | 736 | 829 |
| 0x07 | 788 | 3146 |
| 0x60 | 84 | 80 |
| 0x61 | 20 | 18 |
| 0x62 | 62 | 88 |
| 0x63 | 46 | 59 |
| 0x64 | 191 | 245 |
| 0x75 | 11 | 9 |
| 0xE0 | 1077 | 3629 |
| 0xE1 | 4 | 14 |
| 0xE2 | 1506 | 6121 |
| 0xEF | 16 | 47 |

Caveats: candidates, not proven standalone instructions (literal-pool data can
match). Two provenance notes. First, run 5's note printed a slightly
different bmc0 table (772/806/90/22/47/192/12); the committed tool and its
committed tests both reproduce the 736/788/84/20/46/191/11 numbers above, and
only the 0xEF=16 and 0xE2=1506 values are pinned by tests, so this note carries
the committed tool's numbers as ground truth. Second, bmc1's 47 `cmp #0xef`
candidates fall into: the two recovered chain sites `0x0110045e` (debug chain,
same as bmc0) and `0x0110fb8e` (the parser chain, this time found at its own
chain address); a 21-site stride-0x440 family at `0x610e722c..0x610eac10`
(contexts not disassembled; the sample at `0x610e722c` sits inside computed
`subs/cmp` classifier chains like bmc0's ERAM value matchers); a 13-site
stride-0x440 family at `0x611cf8e4..0x611d49a4` (same shape, one disassembled
sample); and 11 scattered sites (`0x611cf8e4` family excluded, `0x61215bf0`,
`0x612ba864`, `0x612bfa2c`, `0x612df0e6`, `0x612fce94`, …) — none of these is a
proven wire-byte-1 compare, and none lies on the recovered receive chain.

The 14 bmc1 `cmp #0xe1` candidates: five in ITCM around the parser region
(`0x0110c4ac`, `0x0110c50a`, `0x0110c512` — a 0xE1/0xE2/0xE5/0xFF/0x100 range
classifier over signed fields at object +0xc/+0xe of the per-port records,
with a `orr r3, #4` flag bit — **verified** instructions, role **inferred**;
these test port-record fields, not wire byte 1) and nine in ERAM (sample
`0x610eca24`; not disassembled). None is a wire-byte-1 compare.

## What is established and what is not

Established (static, verified): the bmc1 ASGN-analog/CUMDWRx/helper/parser
anchors and both TBB tables; the byte-1 decision semantics at every recovered
decision (identical structure, different consumed sets on helper and parser);
the added CUMDWRx command 0x53; the 0xEF body's flag-gated 16-entry walk with
its bmc1-specific getter/cleanup/table addresses; the paired census numbers.

Inferred: the helper is a remote-state setter over `0x200844f4`; the 0xEF walk
drives per-port hook objects; the ERAM `cmp #0xef/#0xe1` candidates are value
classifiers.

Not established: the bmc1 first-router (RXDT) analog and how the ASGN task is
entered (no static reference found — the main unrecovered edge); whether the
wire peer addresses bmc1 via byte 1 = 0xE2 through this route at all (nothing
on the recovered chain tests byte 1 against 0xE1 or 0xE2, so if 0xE2 frames
exist they are either consumed by an unrecovered ingress or by CORE0/CORE1
code this run did not reach); what the parser's producer formats into the
second ring on bmc1; whether bmc1's larger parser/helper command sets
correspond to services the host sends only to the second chip.

## Reproduce

```sh
shasum -a 256 local/b1c1a.bin
PYTHONPATH=tools python3 tools/core1_b1_route_study.py local/b1c1a.bin --b0 local/b0c1a.bin
python3 -m unittest discover -s tests -p test_core1_b1_route_study.py -v
```

The tool pins the bmc1 payload digest and exits nonzero on any other image or
anchor mismatch. All 75 anchors, both TBB tables, the walker bound and the
getter's literal pool are checked by the tests; without the corpus 8 of 13
tests skip cleanly (5 run pure).