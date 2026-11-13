# CORE1 receive path and wire byte 1: where 0xEF could be answered

2026-11-13, glm-overnight-2 run 5. Static cross-check of the 2026-11-12 unit
measurements against the pinned bmc0 CORE1 payload, closing the BMC-side half of
run 4's open question ([host-ef-settings-study](host-ef-settings-study.md): "no
host site compares a frame byte against 0xEF — which BMC/CORE service answers
0xEF is unknown"). Inputs: pinned `local/b0c1a.bin`, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` (verified by
`shasum -a 256` and by the tool's digest gate). Every claim below is **verified**
(reproduced by `tools/core1_ef_route_study.py` and
`tests/test_core1_ef_route_study.py`) or **inferred**, and marked. No device
access, no execution of vendor code, no key material touched.

## Question

The unit's host link carries settings frames routed to 0xEF (measured, run 4).
Which code on the BMC side could receive byte 1 = 0xEF? The recovered CORE1
receive route ([core1-receive-and-test-controls](core1-receive-and-test-controls.md),
[core1-task-context-and-host-peer](core1-task-context-and-host-peer.md)) is:
hardware ring (IRQ 6) → RXDT task 3 (first router `0x0111ea24`) → ASGN task 5
(second router `0x0110a65c`) → CUMDWRx dispatcher `0x0110bacc`. This note checks
every byte-1 decision on that route, plus an image-wide census of compare
immediates against the wire byte-1 values.

## The recovered route never tests byte 1 against 0xEF

All instruction anchors below are **verified** by exact byte match in the pinned
image (32/32 anchors match; `tools/core1_ef_route_study.py` `anchors_match`).

First router `0x0111ea24` (RXDT): word bits 7:4 select one of 16 TBB routes
(table at `0x111ea54`, bytes `0847 b3b3 86b3 b3b9 8686 bdb3 8686 86f6`,
**verified**). Route 0 (high nibble 0) is the only route that reads byte 1:

- `0x0111ea64  ldrb.w r0, [sp, #1]` — byte 1 of the stack-copied word.
- `0x0111ea68 cmp r0, #7` / `0x0111ea72 cmp r0, #0xc0` / `0x0111ea76 cmp r0,
  #0xc1` / `0x0111ea7a cmp r0, #0xfe` — four special byte-1 values.
- Everything else (including 0xEF) falls through to `0x0111ea80 bl #0x110a5a6`
  (second-ring enqueue + ASGN signal) plus a call to `0x0112d2e`.
- Route 1 (high nibble 1, SysEx assembly) forwards the whole word to both
  receiver objects without checking byte 1; route 7 enqueues like route 0's
  default; other routes handle kind zero without touching byte 1.

Second router `0x0110a65c` (ASGN): kind zero at `0x0110a6ce` loads byte 1
(`ldrb.w r0, [sp, #0x41]`), compares only `#7` (`0x0110a6d2`), else calls
CUMDWRx `0x0110bacc` at `0x0110a6da` (**verified**).

CUMDWRx `0x0110bacc`: command = `(word >> 8) & 0xff`
(`0x0110bace ubfx r2, r1, #8, #8`); the dispatcher compares only `0x51, 0x52,
0x54, 0x58, 0x70, 0x74, 0x75, 0x7b` (`0x0110bad4`..`0x0110bb02`); every other
command, 0xEF included, hits `0x0110bb04 pop {r4, pc}` — a bare return
(**verified**). This matches the earlier command-entry study's fragment.

So on the recovered route: a ring word with byte 1 = 0xEF reaches CUMDWRx and is
ignored. The same holds for byte 1 = 0xE1/0xE2: no special handling — note the
wire's kind-9 frames (byte 1 = 0xE1, runs 2–3) reach host as *replies*, whose
CORE1-side producer is still the missing peer; nothing here contradicts that.

## Image-wide compare census (candidates, bounded)

`census_immediates` scans both mapped regions for 16-bit-aligned Thumb
format-3 `cmp rN, #imm8` (op bits `01`), excluding halfwords that are the second
half of a 32-bit instruction (preceding halfword `e8xx`/`f0xx..f7xx`/`f8xx..ffff`
prefix). It does **not** prove each survivor is a decoded standalone instruction:
literal-pool data can still match. Results are candidates; only the anchors
above were individually disassembled in context.

| Immediate | Candidates |
|---|---:|
| 0x02 | 772 |
| 0x07 | 806 |
| 0x60 | 90 |
| 0x61 | 22 |
| 0x62 | 62 |
| 0x63 | 47 |
| 0x64 | 192 |
| 0x75 | 12 |
| 0xE0 | 1077 |
| 0xE1 | 4 |
| 0xE2 | 1506 |
| 0xEF | 16 |

The 16 `cmp #0xef` candidates (**verified as exact halfwords; context classified
by hand**): the two ITCM ones are `0x0110045e` — the debug/service command chain
reached from the reply-state machine at `0x0112c8b8` (caller `0x0112ca0a`; the
0xEF branch at `0x01100460` targets `0x0112d6de`, a 3-bit hex-digit repack of an
8-byte value into `r0+0x24`, the same builder family as the debug reply helpers
`0x0112c6a4`/`0x0112d4ca` — **verified anchors, inferred role**) — and
`0x0110ddb0`, inside a byte-stream command parser entered at `0x0110d980` whose
0xEF branch (`0x0110ddb2 → 0x0110e1f2`) tests a flag bit and calls `0x110e9f0`
(the same receive-helper called at the first router's entry) — **verified
anchors, reachability of this parser's entry from the recovered route not
established** (no direct BL/veneer/aligned-word reference to `0x0110d981` was
found by `tools/core1_xrefs.py` and a full-image word scan).

The other 14 are ERAM compare/classifier contexts: `0x610a047c` sits in a long
`cmp rN, #imm / str r2, [r0, #0x10]` matcher chain (sibling bounds 0xad, 0xbb,
0xc7, 0xd5, 0xe1, 0xed — a value matcher, not a wire check); `0x610ae988`,
`0x610aeaa0`, `0x610aecc0`, `0x610d352c`, `0x610d3838`, `0x610d3b44`,
`0x610d3e50`, `0x611169d0`, `0x61116e10`, `0x61117250`, `0x61117690`,
`0x61177d00` all follow `subs r7, #0xe4`-style computed values (range
classifiers like the host binary's); `0x61129f8c` decodes against an
unrelocated literal-pool-looking area and may be data. **None of the 16 is a
proven wire-byte-1 compare on the recovered receive route.**

The four `cmp #0xe1` candidates: `0x6102d862` (inside the documented MMIO
debug/read helper family `0x6102d2e6`, comparing a value before `blt`),
`0x610a0474` (same matcher chain as above), `0x610aa6a4` and `0x61130598`
(contexts not disassembled in this run). The E1 comparisons that *do* matter on
the wire — the reply-source checks — exist on the **host** side (run 4); CORE1
shows no equivalent in the recovered route.

## What is established and what is not

Established (static, verified): the router/CUMDWRx instruction anchors and TBB
table bytes; that route 0 is the only first-router route reading byte 1 and it
compares only 0x07/0xc0/0xc1/0xfe; that ASGN compares byte 1 only against 0x07;
that CUMDWRx handles only the eight commands 0x51/0x52/0x54/0x58/0x70/0x74/
0x75/0x7b and returns for everything else; the bounded census numbers above.

Inferred: the `0x0110045e` chain serves the debug/service reply path; the
`0x0110d980` parser is a command dispatcher whose ingress is outside the
recovered route (entry reachability unresolved).

Not established: which service actually answers 0xEF on the wire. The
recovered route would *ignore* a 0xEF-byte-1 ring word, so either the answerer
lives behind an ingress this study has not recovered (the ttyGS0 peer remains
missing — [host-core1-bridge-followup](host-core1-bridge-followup.md) section
4), behind the unrecovered parser `0x0110d980`, in CORE0 (encrypted, out of
scope for this series), or nothing answers and the settings traffic is
fire-and-forget end to end. Also unknown: whether the second byte-1 dispatch
(`0x0112d2e`, called from route 0's fallthrough) checks byte 1 deeper (not
traced this run); whether bmc1 (`b1c1a.bin`) mirrors this route (untouched).

## Reproduce

```sh
shasum -a 256 local/b0c1a.bin
PYTHONPATH=tools python3 tools/core1_ef_route_study.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_core1_ef_route_study.py -v
```

The tool pins the payload digest and exits nonzero on any other image. The 32
anchors, the TBB bytes and the census numbers are checked by the tests; without
the corpus the five pinned-image tests skip cleanly.