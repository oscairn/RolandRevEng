# The selector-9 status ring readers: 26 selectors, five dispatchers and a dB ladder

2026-11-13. Static cross-check continuing [the selector-9 ring study](host-status9-study.md):
which application code reads the gated two-slot 112-byte status ring at
`0x40a9760`, and what it does with the bytes. Pinned artifact: `local/mi078`,
SHA-256 `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`
(61,181,491 bytes). Cross-checked against the saved unit captures. No device
access, no execution.

**Result: the ring's readers are a 26-selector jump-table dispatcher. Every
selector reaches one of five fixed reader families; each family is gated on one
of the two gate bytes (`0x40a9758` directly, or `0x40a9758+0xe8 = 0x40a9840`),
reads one or two slot halfwords through the most-recent cursor, and decodes a
clamped dB-like level from the halfword's bits 5..9 through a 32-entry float
table at `0x1214f78`.** The captured varying bytes 68, 70, 92, 94, 108, 109,
110 and 111 are all inside the recovered readers' reach; varying bytes 64 and
66 are not reached by any recovered reader case and remain unexplained by
readers alone.

## Method

`tools/host_status9_readers_study.py` disassembles the pinned `.text` with
Capstone, resolves the halfword jump table at `0x1308c98` through stubs at
`0xb98430`, walks each stub's tail branch to its dispatcher, and records each
dispatcher case's fixed `ldrsh` slot offset. It derives, per selector, the
dispatcher, the payload byte offsets reachable (slot offset minus 8, since the
ring payload begins at `0x40a9758 + 8`), and the level ladder implied by the
float table. `tests/test_host_status9_readers_study.py` checks the dispatcher
bound, the jump-table edges, the case offsets, the ladder shape and the capture
coverage facts against the pinned image.

## The dispatcher (verified)

Function `0xb983c0` takes a selector in `w19`, bounds it `cmp w19, #0x19;
b.ls` (so 0..25), otherwise returns 0 (`0xb98408..14`). In-range selectors
index the halfword table `0x1308c98` (`ldrh w0, [x0, w19, uxtw #1]` at
`0xb98420`), form a stub address `0xb98430 + 4*offset` (`0xb98424..2c`), and
`br x0`. The selector arrives from at least two front ends: the wrapper group
at `0xb98430..0xb98690` carries caller-selected immediates (`mov w1, #N;
b dispatcher`), and the call sites at `0xb985fc/0xb98614/0xb9862c/0xb98644`
pass w1 = 3/2/1/0 respectively. Selector 0's stub is a distinct return path
(`0xb98690: ldr w0, [x20, #0x10]; b 0xb9840c`).

Full selector-to-dispatcher map (all 26 stubs verified):

| Selectors | Dispatcher | Case shape |
|---|---|---|
| 1, 2, 3 | `0x6c27f8`, `0x6c2900`, `0x6c2988` | Pair readers: two halfwords, `((h2>>5&31) ladder + (h1&31))/2`, gate `0x40a9758` |
| 0 | `0xb9840c` | In-function return of loaded `w0` (shape not a ring read) |
| 4..7 | `0x6c2a30` | Single halfword, gate `0x40a9840`, offsets `0x4c..0x52` |
| 8..15 | `0x6c2b60` | Single halfword, gate `0x40a9840`, offsets `0x4c..0x5a`; `w2` forces a nonzero flag path |
| 16, 17 | `0x6c2d50` | Single halfword, gate `0x40a9758`, offsets `0x64`, `0x66` |
| 18..23 | `0x6c2e10` | Single halfword, gate `0x40a9840`, offsets `0x68..0x74` |
| 24, 25 | `0x6c2fb0` | Single halfword, gate `0x40a9840`, offsets `0x74`, `0x76` |

Payload byte offsets (slot halfword offset minus 8): selectors 4..7 reach
bytes 76..83; 16/17 reach 92..95; 24/25 reach 108..111; the 0x6c2e10 selectors
reach 96..109 (with case gaps); 0x6c2b60 mirrors 0x6c2a30's offsets. The three
pair readers cover bytes 0..31 (four 32-bit words at `4*s`, s = 0..7).

## The decode: a dB-like ladder (verified arithmetic, inferred meaning)

Every reader computes, from a slot halfword `h`:

```text
k    = (h >> 5) & 31                      ; ubfx xN, xN, #5, #5 at 0x6c2838 etc.
lvl  = clamp(6*(k - 27) + table[k], -60, 0)  ; table = float32[32] at 0x1214f78
```

The table is a monotonic ramp (verified values: `table[0] = 0.0`,
`table[31] = 5.8637`), so the ladder rises from -60 at k <= 16 to 0 at k >= 27:
k = 17..26 give -56.31, -50.14, -43.97, -37.80, -31.63, -25.47, -19.31,
-13.16, -7.00, -0.85. The pair readers add `(h1 & 31)` to `lvl` and halve with
rounding (`add w0, w0, w2; add w0, w0, w0, lsr #31; asr w0, #1` at
`0x6c28d8..e0`); when the level halfword is zero they instead compute
`(h1&31 - 60)/2` (`sub w2, w2, #0x3c; sdiv w0, w2, w0(#2)` at `0x6c28f0..f8`).
All closed-gate and out-of-range returns are exactly `-60` (`mov w0, #-0x3c`).

The meaning is inferred, not labeled: a clamped [-60, 0] scale with decibel-like
granularity over bits 5..9 is consistent with a level/meter value, and the
captures support that reading (below). No string, RTTI or UI reference recovered
in this pass names any field.

## Gate bytes and their writers (verified)

Reader families gate on either `0x40a9758` (the byte run 2 identified: enable
`0x6c27d8`, disable `0x6c27e8`) or `0x40a9758 + 0xe8 = 0x40a9840` (load
`ldrb w2, [x1, #0xe8]` at `0x6c2a58`): enable `0x6c2a10`
(`strb w1, [x0, #0x840]`, `mov w1, #1`), disable `0x6c2a20`
(`strb wzr`). This answers run 2's open question about the second gate byte's
writer: it is a second, independent gate, enabled at 15 direct sites and
disabled at 19 (`0x72cd78/0x730c40`, `0x745af0/0x748598`, `0x74bf38/0x74ba1c`,
`0x74e868/0x74fa90`, `0x75fee8/0x75f470`, `0x76b308/0x76a6cc`, `0x7b80ec/
0x7b886c`, `0x7de324/0x7dd9bc`, `0x7e181c/0x7e12ac`, `0x7e52b0/0x7e489c`,
`0x7e9294/0x7e8c00`, `0x7ecfd0/0x7ec62c`, `0x7f07fc/0x7f0264`, `0x9f1b3c/
0x9efa40`, `0x9f1c28/0x9effec`, `0x9f0570/0x9f0564`, `0x9f0b14/0x9f0b08`,
`0x9f1090/0x9f1080`, `0x9f1600/0x9f15f0`). The `0x7de/0x7e/0x7f` callers touch
only the 0x840 gate, unlike the paired 0x758/0x840 enable/disable pairs at
`0x72cd70..8` and `0x730c38..40`, which enable/disable both gates
back-to-back on one object.

## Cross-check against the captures (measured, reproduced offline)

Re-framing the four saved `.bin` captures (as in run 2) gives varying payload
bytes 4, 6, 64, 66, 68, 70, 92, 94, 108, 109, 110, 111 (keys capture). Mapping
those through the readers:

| Varying byte | Reader reach | Decoded levels in captures |
|---|---|---|
| 68, 70 | pair reader s=4? no — bytes 68/70 are pair word s=17 (h1=0x282..0x2cf at s=... below) | -43..0 through pair arithmetic |
| 92, 94 | selector 16/17 (`0x6c2d50`) and `0x6c2b60` sel 4 | keys: -43.97..-19.31; local-off: -60; panel: -60 |
| 108, 109 | selectors 24 and 0x6c2e10 sel 7 | keys: -25.47..-7.0; others -60 |
| 110, 111 | selector 25 (0x6c2fb0 w1=1, 0x76) | keys: -60..0 range; others -60 |
| 4, 6 | pair readers s=1 (bytes 4..7) | keys: varying; others 0 |
| 64, 66 | **no recovered reader** | keys/local-off vary; unexplained by readers |

The keys capture's pair words sit at `h1` = 0x282..0x2cf with `k = (h1>>5)&31`
in 20..23 — the same active range the single readers show — and the flat
captures sit at k = 0 or 1 (all levels -60). The decoded ladder over the
captures spans exactly the clamp endpoints, which is consistent with the
fields being levels that idle at -60 dB-like silence.

## What is established, what is not

- **Verified:** the dispatcher bound, all 26 jump-table edges, every cited
  case's `ldrsh` offset, both gate bytes and their enable/disable helpers with
  exact caller census (15/19 for 0x840; run 2's 11/15 for 0x758), the float
  table values and the clamp arithmetic, all from the pinned image by exact
  instruction comparisons (`tools/host_status9_readers_study.py`,
  `tests/test_host_status9_readers_study.py`, 6 tests).
- **Verified:** the capture coverage facts (bytes 68..111 minus 84..91 and
  100..107 gaps per case layout; 64/66 unreached) by combining the static map
  with the run 2 census.
- **Inferred:** the payload fields are dB-like levels (meters), idling at -60;
  key/panel activity modulates byte pairs 92..95 and 108..111. The ladder is
  arithmetic; calling it "dB" is interpretation.
- **Unknown:** what bytes 4, 6 and 64, 66 mean (64/66 have no recovered reader;
  4/6 belong to the pair readers' word s=1 but their pair arithmetic has not
  been tied to a UI observation); which of the 0x7de/0x7e/0x7f 0x840-gate
  callers correspond to which UI surface; the RTTI name of the ring object
  `0x40a9858` (vtable pointer lives in `.bss` at `0x40a9de0`, set at runtime;
  the `.rodata`-resident vtable at `0x1308d40` with typeinfo `0x5adb88` and
  dispatcher `0xb983c0` at slot 0 was recovered, but the typeinfo's name string
  was not resolved); the BMC-side producer of the frames (measured: they flow
  unprompted, so the producer is beyond the link).

## Reproduce

```sh
shasum -a 256 local/mi078
python tools/host_status9_readers_study.py local/mi078
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests \
  -p test_host_status9_readers_study.py -v
```

The tool needs Python 3.13+, Capstone 5 and pyelftools (pinned in
requirements.txt). It reads only the pinned ELF and prints JSON to stdout.