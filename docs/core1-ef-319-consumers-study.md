# CORE1 byte-1 consumers beyond the run-5 route: where 0xEF still gets through

2026-11-13, glm-overnight-2 run 6. Static cross-check continuing run 5
([core1-ef-route-study](core1-ef-route-study.md)). Run 5 left two receiving
edges open: the first router's route-0 fallthrough helper, called at
`0x0111ea86` and written in run 5's note as `0x0112d2e` (wrong; the encoded
`bl` targets `0x01126d2e`), and the byte-stream command parser entered at
`0x0110d980`/`0x0110d980+1`, whose ingress run 5 could not find. This note
pins both. Inputs: pinned `local/b0c1a.bin`, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`. Every
instruction claim below is **verified** (exact byte match via
`tools/core1_ef_319_consumers_study.py` and `tests/test_core1_ef_319_consumers_study.py`);
reachability and semantics claims are marked **verified** (decoded branch/table
structure) or **inferred**. No device access, no execution of vendor code, no
key material touched.

## First correction: the parser is reachable, from the ASGN router

Run 5 searched direct BL/veneer/word references to `0x0110d980`/`0x0110d981`
and found none. The parser's real entry is `0x0110d962` (two instructions
earlier), and it is called directly from the ASGN router
`0x0110a65c` at **`0x0110a6ba  bl #0x110d962`** (**verified**): the router's
byte-0-high-nibble switch (`0x0110a6a4 ldrb.w r0,[sp,#0x40]`,
`lsrs #4`, `beq`/`cmp #3`/`cmp #7`/`cmp #0xb`) takes every high nibble other
than 0/3/7/0xb into the parser, then continues at `0x0110a6be` (kind-zero-style
state polling). The kind-zero path (`0x0110a6ce`) still goes to byte-1 `0x07`
and CUMDWRx `0x0110bacc` as run 5 established.

The parser's own dispatch (**verified**): entry `0x0110d962 push.w {r3..lr}`;
ldrb r1,[r0]; and r7,r1,#0xf; cmp #0xf; bhs reject` — word low nibble selects,
15 rejects (`0x0110d972 tbb`, table base `0x110d974`, bytes
`07f0f4f38ef4f2f1f0ef0829eeb5f4`, **verified**). The TBB targets low nibbles 0→`0x110d982`, 10→`0x110d984`,
11→`0x110d9c6`, 4→`0x110da90`, 13→`0x110dade`, and 1..3/5..9/12/14→ a shared
fallthrough region `0x110db50..b5c` whose bodies re-dispatch on **byte 1**
(`0x0110db60 ldrb r1,[r0,#1]` etc.). So the run-5 census missed the call
because it probed the entry two instructions late.

Byte order note (from the parser bodies): the parser reads bytes 2..3 as a
halfword `ldrh r0,[r0,#2]` and byte 1 at `[r0,#1]`, so a parser word carries
wire byte 1 at bits 15:8 — the same convention run 5 proved for the routers.

## Edge 1: route-0 fallthrough helper `0x01126d2e` never tests 0xEF

Called from first-router route 0 at `0x0111ea86` (`mov r0,sp; bl
#0x1126d2e`, **verified**), after the second-ring enqueue at `0x0111ea80`.
The helper (**verified**):

- `0x01126d30 ldrb r1,[r0]; movs r2,#2; cmp.w r2,r1,lsr #4; bne 0x1126e14` —
  only words whose **byte 0 high nibble is 2** reach the byte-1 switch; other
  byte-0 values go to `0x01126e14` (`ldr r0,[r0]; bl 0x1126974`).
- Byte 1 (`0x01126d3a ldrb r3,[r0,#1]`) is compared against `0x8e`
  (`strb #1,[0x20083e74+3]`), `0x8f` (`+4`), `0xbc`, `0xbd`, `0xbe`, and the
  TBB at `0x1126d52` whose table (base `0x1126d54`, bytes `03f05b5d2a1c`,
  **verified**) covers `0x80..0x85` — six mask/state bodies on the object at
  `0x20083e74` (`+8/+0xc/+0x10/+0x14/+0x18/+0x1c/+0x20` word masks and the
  `+1/+2` byte states).
- Everything else — `0xEF`, `0xE1`, `0xE2`, all wire byte-1 values — falls
  through to the shared tail `0x01126e1a pop.w; movs r0,#8; b 0x11020c0`
  (**verified**): no state is written for them.

So route 0's fallthrough helper consumes byte-1 values `0x80..0x85, 0x8e,
0x8f, 0xbc, 0xbd, 0xbe` and ignores 0xEF. The helper is a remote-state/flag
setter over the object at `0x20083e74`; calling it "the byte-1 dispatch
`0x0112d2e`" (run 5's note) pointed one digit off.

## Edge 2: the parser consumes 0xEF — with a flag guard

Inside the parser's shared fallthrough region, byte 1 is dispatched by two
binary-search chains (**verified**): `0x0110dd22..dd66` (`0x76/0x77/0x7c/
0x80/0x88/0x8c/0x8d/0x99/0xa5`, then TBB `0x110dd66` on `r1-0x9d` for
`0x9d..0xa4`, then `0xa6..0xad` via TBB `0x110dd82`, then `0xb3..0xb7` and
`0xb4..0xb6`) and `0x0110dd94..ddb6` (`0xb7`, `0xb4`, `0xb5/0xb6`, **`0xee`**,
**`0xef`**). Everything else reaches `0x0110ddb6 b.w #0x110e2b6` (reject).

The **0xEF body** at `0x0110e1f2` (**verified**):

1. `0x0110e1f2 ldrh r0,[r0,#2]; tst #0x8000; beq reject` — the word's bytes
   2..3 must have bit 15 set, else the word is ignored.
2. `0x0110e1fa bl #0x110e9f0` — returns the singleton pointer
   `0x614020c8` (**verified**; the helper is a four-instruction getter).
3. `0x0110e1fe ldrb r0,[r0,#0xa]; cmp #0` — the object's flag byte must be 0.
   If set, `0x0110e20a bl #0x110f522` runs first (a bounded
   unregister/cleanup over the `0x20084d88` table; role **inferred** from the
   call shape, not disassembled exhaustively).
4. Then a **16-iteration walk** over the table at `0x20084d88`
   (`0x0110e214 rsb r0,r5,r5,lsl#5; add x2; ldr r0,[r6,r0,lsl#2]`,
   stride 0x148 bytes): for each entry, call slot `+0x10` with the entry, then
   call slot `+0x20` twice with r1=0 (`0x0110e238..e248 cmp r4,#2 blt`),
   and after each entry `0x0110e24a bl #0x1104e34`.
   The loop bound `cmp r5,#0x10` at `0x0110e29e` is **verified**; the loop's
   early exits (`0x0110e22a..e248` region, between the two call sites) were
   partially disassembled, and the per-entry virtual-call semantics are
   **inferred** — this run did not prove what the callees do.

The **0xEE body** for contrast (`0x0110e1dc`, **verified**) is single-shot:
one `ldrb r0,[r0,#2]` masked to 6 bits, one getter, one call to `0x0110d594`.
So 0xEE and 0xEF are distinct commands in this parser, not aliases.

## What the parser is, bounded

The parser is a byte-stream command decoder reading **two/three-byte records**
(word bits 7:0 = low nibble selector, bits 15:8 = byte 1, bits 31:16 = record
payload) with per-command bodies writing the `0x20084d88` per-port table,
the `0x61400d98` byte-stream accumulator (offset `0x200`, guarded by a
state-4 check and a `0x1fc` overflow bound at `0x0110dc28`, **verified**), and
calling per-port vtable slots (`+0x4/+0x8/+0xc/+0x10/+0x18/+0x20/+0x54/+0x58/
+0x90`, **verified** at the call sites). Its ingress on the recovered receive
route is the ASGN router's non-kind-zero high-nibble path (`0x0110a6ba`).

The parser consumes byte-1 values `0x76, 0x77, 0x7c, 0x80, 0x88, 0x8c, 0x8d,
0x99, 0xa5, 0xa6..0xad, 0xb3..0xb7, 0xbc, 0xbd, 0xbe, 0xee, 0xef`
(structure **verified**; the exact body set is the verified cmp/TBB skeleton,
with per-command IO semantics partly **inferred** as above).

## Answer to the run-5 question: bounded remaining 0xEF consumers

A ring word with byte 1 = 0xEF can now be consumed in exactly three recovered
places on bmc0 CORE1:

1. **First-router route 0 → second-ring enqueue → ASGN task 5 → parser**
   via the non-kind-zero path `0x0110a6ba` — **consumed**, gated on payload
   bits 15 and flag byte `0x614020c8+0xa` (above). This is the only recovered
   path where 0xEF does work.
2. **Route-0 fallthrough helper `0x01126d2e`** — **ignored** (falls to the
   shared tail, no state change).
3. **CUMDWRx `0x0110bacc`** (kind-zero path) — **ignored** (bare return, run 5).

The two ITCM `cmp #0xef` candidates run 5 classified are confirmed unrelated to
wire byte 1 on this route: `0x0110045e` (debug service reply chain) and the
parser chain's own `0x0110ddb0` — which run 5 could not reach and this run
reaches from the ASGN router. Nothing else in the image tests byte 1 against
0xEF on a recovered path.

What this does **not** establish: whether the *wire* settings frames (host →
0xEF, run 4) are the same stream this parser consumes. The parser's ingress is
the ASGN router's ring words, whose producer side (which upstream formats ring
words into low-nibble-selector + byte-1-command records) is still the missing
ttyGS0 peer. The parser's record shapes match a byte-stream protocol, not the
12-byte short frame form; a peer that repackages frames into ring words would
fit, but that peer is not recovered. Whether bmc1 mirrors any of this is
untouched (`b1c1a.bin` was not read this run).

## Reproduce

```sh
shasum -a 256 local/b0c1a.bin
PYTHONPATH=tools python3 tools/core1_ef_319_consumers_study.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_core1_ef_319_consumers_study.py -v
```

The tool pins the payload digest and exits nonzero on any other image. All
anchors, the three TBB tables and their target ranges are checked by the tests;
without the corpus the five pinned-image tests skip cleanly.