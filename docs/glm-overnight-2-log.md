# glm-overnight-2 run log

## Run 1 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Explain the measured conflict
  between the unit's wire captures (every frame `mi078` writes on
  `/dev/ttyGS0` carries source byte 1 `0x00`) and the static record (some
  constructors store `0x60` there), an open question in
  `bmc-addressing-and-loader-open-questions.md`. The queue's section 1 asks for
  host-side dispatch work with actual call/data references, and this item
  cross-checks the 2026-11-12 measurements against host code without touching
  encryption, keys or device access.
- **Files added:** `docs/host-byte1-study.md`, `tools/host_byte1_study.py`,
  `tests/test_host_byte1_study.py`. Detailed census JSON stays in ignored
  `local/host-byte1-summary.json` (main checkout local; the worktree has no
  `local/`).
- **Verified:** with `tools/host_byte1_study.py` against pinned `mi078`
  (SHA-256 `9051…9bb7`): 391 direct route calls to `00be4270`/`00be4418`; 214
  stamp an immediate into message byte 1, 177 leave the base-initializer
  default 0. Routes exercised by the captures leave it 0: 45 of 46 sites to
  0xEF (one 0x60 stamp at `0x8d58b0`), all 11 to 0x75, and the kind-3
  forwarding path at `00c2c9a0` to 0xE1. The 99 stamping 0xE1 sites use
  0x60/0x62/0x63/0x64 and belong to services those captures did not exercise.
  Send path (`00be1120` → `00be2510` → `00be24e8` → `00bdf988`) copies bytes
  unchanged; nothing rewrites byte 1 between queue and `write`. All four saved
  strace traces re-frame with byte 1 `0x00` in every written frame (196, 176,
  1041, 2505 frames).
- **Tests:** `BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests
  -p test_host_byte1_study.py -v` → 4 passed (34.6 s, pinned image required);
  skips cleanly without the corpus. Existing `test_bmc_ipc.py` (4 tests)
  still passes.
- **Remains unknown:** which subsystems the 0x62-to-0xE1 (76 sites, e.g.
  `0xa573a8`) and 0x60-to-0x0E/0x61 stamps belong to; the CORE1 peer's handling
  of byte 1; whether any stamping site's frames appear under other UI actions
  (captures did not exercise them). The scanner models straight-line blocks
  only; byte-1 stores inside helper routines then routing are counted as
  no-store.
- **Best next item for run 2:** the queue's next section-1 item after dispatch
  mapping: identify where the measured destinations 0xE1/0xEF/0x75 are answered
  on the BMC side — specifically which CORE1 (or CORE0) service receives
  frames routed to 0xEF, using `core1-service-startup-mmio.md` and the
  receiver constructors, or, if that stalls, the section-3 item tracing which
  context owns `2016..2019` routing writes against the measured audio-link
  note. Do not take instruction-semantics items (another series works section
  2).

## Run 2 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Run 1's log pointed at locating
  where the measured 0xE1 traffic is answered; the concrete open item taken is
  the unexplained long kind-9 status frames from 0xE1 (112-byte payload,
  sub-type 9, listed as unknown in `bmc-addressing-and-loader-open-questions.md`
  and absent from the kind-9 service table in
  `host-core1-bridge-followup.md`). This is a static host-side consumer
  cross-check against the saved captures; no keys, encryption or device access.
- **Files added:** `docs/host-status9-study.md`, `tools/host_status9_study.py`,
  `tests/test_host_status9_study.py`.
- **Verified:** all 741 kind-9 frames across the four saved app-stopped
  `.bin` captures are (byte 1, destination, selector) = (0xE1, 0x60, 9) with a
  112-byte payload (181/180/220/160). Statically, the pinned mi078 input worker
  `00be1a50` dispatches kind 9 on byte 3; selector 9 at `0xbe1b18..34` stores
  the payload through `0x6c3070` into a gated two-slot 112-byte ring at
  `0x40a9760`/`0x40a97d0` with a toggle cursor at `0x40a975c` (gate byte
  `0x40a9758`; 11 enable/15 disable direct callers). The consumer checks
  neither source byte 1 nor payload length on this path. All 18 instruction
  anchors checked exactly by `tools/host_status9_study.py`.
- **Tests:** with corpus: 5 passed (38.7 s, `python -m unittest discover -s
  tests -p test_host_status9_study.py -v`); without corpus: 5 skipped cleanly.
  Existing `test_bmc_ipc.py` still passes (4).
- **Remains unknown:** meaning of any of the 112 payload bytes (captures bound
  the varying offsets: 4, 6, 64..70, 92..94, 108..111 under key activity);
  which reader consumes which field (27 references to the gate base not traced);
  the ring object `0x40a9858`'s RTTI; the second gate byte `0x40a9840`'s writer;
  and the BMC-side producer of these frames (measured: they flow with nothing
  sent, app stopped — the producer is beyond the link).
- **Best next item for run 3:** the queue's section-1 continuation: identify
  which service answers frames routed to 0xEF on the BMC side (settings/
  parameter blocks), per run 1's pointer, or decode the selector-9 payload
  fields by tracing the gated reader families' callers against the capture
  offsets above. If either stalls, the section-3 item: which context owns
  `2016..2019` routing writes against `fantom-audio-link-measurements.md`.

## Run 3 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Run 2's log offered decoding the
  selector-9 payload via its gated readers or locating the 0xEF responder; took
  the reader trace because it extends this series' already-verified selector-9
  ring evidence directly against the pinned `mi078` and saved captures (static
  only, no keys/encryption/device access).
- **Files added:** `docs/host-status9-readers-study.md`,
  `tools/host_status9_readers_study.py`,
  `tests/test_host_status9_readers_study.py`.
- **Verified:** the selector-9 ring's readers are a 26-selector jump-table
  dispatcher at `0xb983c0` (table `0x1308c98`, stubs `0xb98430..698`, bound
  `cmp w19, #0x19`); all 26 stub tail branches resolved: selectors 1-3 to pair
  readers `0x6c27f8/0x6c2900/0x6c2988`, 4-7 to `0x6c2a30`, 8-15 to `0x6c2b60`,
  16-17 to `0x6c2d50`, 18-23 to `0x6c2e10`, 24-25 to `0x6c2fb0`, 0 to a
  distinct return path. Each family is gated on `0x40a9758` (direct) or
  `0x40a9758+0xe8=0x40a9840`; the second gate byte's writers are `0x6c2a10`
  (enable) and `0x6c2a20` (disable) with exactly 15/19 direct callers
  (`0x7de324/0x7dd9bc` and eleven more 0x7e/0x7f sites touch only the 0x840
  gate). Every family decodes level = clamp(6*((h>>5 & 31) - 27) +
  table[(h>>5)&31], -60, 0) from the float32[32] table at `0x1214f78`
  (monotonic ramp, ladder -56.31..-0.85 for k=17..26, clamped outside); pair
  readers add `(h1&31)` and halve with rounding, and the zero-level fallback is
  `(h1&31-60)/2`. Capture cross-check: all varying bytes 68,70,92,94,108,109,
  110,111 are inside the readers' reach and decode from -60 (idle captures) to
  -43.97..-7.0 (keys capture); varying bytes 64/66 have no recovered reader
  case.
- **Tests:** `BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests
  -p test_host_status9_readers_study.py -v` → 6 passed (26.2 s); existing
  `test_host_status9_study.py` → 5 passed (39.4 s); `test_bmc_ipc.py` → 4
  passed. Without the corpus the new tests skip cleanly (pinned-image
  guard).
- **Remains unknown:** meaning of bytes 4, 6 and 64, 66 (64/66 unreached by any
  recovered reader; 4/6 sit in pair word s=1 whose arithmetic is verified but
  whose UI binding is not); the ring object `0x40a9858`'s RTTI name (runtime
  vtable pointer at `0x40a9de0` is `.bss`; the `.rodata` vtable `0x1308d40`
  holding `0xb983c0` at slot 0 and typeinfo `0x5adb88` was recovered but its
  name string not resolved); which UI surfaces the 0x7de/0x7e/0x7f 0x840-gate
  callers belong to; the BMC-side producer of the frames.
- **Best next item for run 4:** locate which service answers frames routed to
  0xEF on the BMC side (run 1's still-open pointer), or, if the peer evidence
  is too thin, trace the 0x7de/0x7e/0x7f 0x840-gate caller families to identify
  the meter surfaces and bind bytes 92..95/108..111 to named UI fields.

## Run 4 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Run 3's log pointed at the 0xEF
  responder; took the host half of that question because it reuses this
  series' proved scanner machinery against the pinned `mi078` and the saved
  strace captures, and closes with a verifiable negative (no host receive
  path tests a frame source of 0xEF) rather than depending on the missing
  ttyGS0 peer. Static only; no keys, encryption or device access.
- **Files added:** `docs/host-ef-settings-study.md`,
  `tools/host_ef_study.py`, `tests/test_host_ef_study.py`. Full census JSON
  in ignored `local/host-ef-report.json` (main-checkout local; this worktree
  has no corpus).
- **Verified:** all 391 direct `00be4270` route calls carry the route
  immediate in w0; 46 go to 0xEF across 25 functions. Exactly two
  functions construct both the kind-7 parameter block and its kind-8
  companion (`0xc01ec0`, `0xc02010`); `0xc170a0` sends a kind-9 selector-0x0E
  service envelope to 0xEF. Capture cross-check: slider trace = 388 kind-7
  selector-0x0E blocks + 388 kind-8 companions to 0xEF (byte-exact,
  companion pairing holds with unrelated frames interleaved between the two
  writes in 10 cases); Local Switch trace = 37 selector-1/parameter-cf pairs;
  every written frame has byte 1 = 0x00. The `cmp #0xe1/#0xe2/#0xef`
  census (8/6/8 sites) classifies every site; the only received-source-byte
  checks are the three 0xE1 reply handlers (`0xbe9fdc`, `0xc0f610`,
  `0xc0fe58`, all `ldrb w0,[sp,#0x29]`) and the version client's 0xE1/0xE2
  destination checks; **no site anywhere compares against 0xEF**, and no
  capture ever read a frame sourced 0xEF or 0xE2. So a 0xEF reply would
  match no recovered host receiver — settings traffic is fire-and-forget at
  the application layer (inferred from the negative).
- **Tests:** `BMC_CORPUS_DIR=<main>/local python -m unittest discover -s
  tests -p test_host_ef_study.py -v` → 8 passed (67.3 s); without the corpus
  7 skip cleanly, 1 pure parser test still runs. Existing
  `test_bmc_ipc.py` (4), `test_host_byte1_study.py` (4, 38.0 s) and
  `test_host_status9*.py` (11, 60.8 s) all still pass.
- **Remains unknown:** which BMC/CORE service answers 0xEF on the wire (the
  peer side; unchanged missing edge); what the BMC does with kind-7 blocks
  selector 0x0E/0x01 (parameter 0x07 in block 0x0E still unbound); whether a
  0xEF-sourced reply would be silently dropped or hit an unrecovered input
 -worker path; meaning of kind-8 companion payload bytes 2..5; the two
  senders' UI surfaces (the functions exist, the menu items behind them are
  not bound).
- **Best next item for run 5:** the BMC-side half: search bmc0 CORE1
  (`b0c1a.bin`) for consumers of 0xEF-addressed work (the first router's
  non-zero byte-1 routes and the service startup MMIO note are the entry
  points), or, if the peer evidence stays thin, take the kernel-ABI item
  run 3 flagged: locate which context owns the `2016..2019` routing writes
  against `fantom-audio-link-measurements.md` (section 3, not section 2).
## Run 5 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane. Run 4's log pointed at the BMC-side
  half of the 0xEF question; took it because it reuses this series' verified
  router evidence directly against the pinned `b0c1a.bin` and closes with a
  checkable negative (nothing on the recovered CORE1 receive route tests byte 1
  against 0xEF). Static only; no keys, encryption or device access.
- **Files added:** `docs/core1-ef-route-study.md`, `tools/core1_ef_route_study.py`,
  `tests/test_core1_ef_route_study.py`.
- **Verified:** 32/32 instruction anchors byte-exact in the pinned payload
  (SHA-256 `6d954…263154`). First router `0x0111ea24`: only route 0 (TBB table at
  `0x111ea54`, 16 bytes pinned) reads byte 1 (`ldrb.w r0,[sp,#1]` at `0x0111ea64`)
  and compares only 0x07/0xc0/0xc1/0xfe; every other byte 1, 0xEF included, falls
  through to second-ring enqueue (`0x0111ea80 bl #0x110a5a6`). ASGN router
  `0x0110a65c` compares byte 1 only against 0x07, else calls CUMDWRx
  `0x0110bacc`, which dispatches only commands 0x51/0x52/0x54/0x58/0x70/0x74/
  0x75/0x7b (ubfx bits 15:8 at `0x0110bace`) and returns bare (`0x0110bb04`) for
  everything else, 0xEF included. Image-wide census of 16-bit-aligned
  `cmp #imm8` candidates (32-bit-instruction interiors excluded): 0xEF=16, 0xE1=4,
  0xE2=1506; no 0xEF candidate lies inside the recovered router/CUMDWRx ranges
  (`0x0111ea24..0x0111ed25`, `0x0110a65c..0x0110a760`, `0x0110bacc..0x0110bb10`).
  The two ITCM 0xEF compares belong to other dispatchers: `0x0110045e` (debug
  service reply chain, reached from `0x0112c8b8`; 0xEF → `0x0112d6de`, a 3-bit
  hex-digit repack of an 8-byte value) and `0x0110ddb0` (byte-stream parser at
  `0x0110d980`; 0xEF → `0x0110e1f2`; no BL/veneer/aligned-word reference to
  `0x0110d981` found, entry reachability unresolved).
- **Tests:** with corpus: 9 passed (0.7 s, `BMC_CORPUS_DIR=<main>/local python -m
  unittest discover -s tests -p test_core1_ef_route_study.py -v`); without corpus
  4 pass, 5 skip cleanly. Existing `test_bmc_ipc.py` (4) and the `test_core1_*`
  family (36, 9 skipped) still pass.
- **Remains unknown:** which service actually answers 0xEF on the wire — the
  recovered route would ignore a 0xEF ring word, so the answerer (if any) sits
  behind the missing ttyGS0 peer, the unrecovered parser `0x0110d980`, CORE0
  (encrypted, out of scope), or nowhere; what the route-0 fallthrough helper
  `0x0112d2e` checks deeper; whether bmc1 mirrors the route; which UI surfaces
  the run-4 senders belong to.
- **Best next item for run 6:** trace the route-0 fallthrough helper `0x0112d2e`
  and the parser `0x0110d980` ingress to bound where a 0xEF-byte-1 word could
  still be consumed, or, if that stays thin, take the section-3 item run 3
  flagged: locate which context owns the `2016..2019` routing writes against
  `fantom-audio-link-measurements.md`. Do not take instruction-semantics items
  (another series works section 2).

## Run 6 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane, the continuation run 5 queued
  first: trace the route-0 fallthrough helper and the byte-stream parser's
  ingress to bound where a byte-1 = 0xEF ring word could still be consumed on
  bmc0 CORE1. Reuses run 5's verified router anchors directly against the
  pinned `b0c1a.bin`; static only, no keys/encryption/device access.
- **Files added:** `docs/core1-ef-319-consumers-study.md`,
  `tools/core1_ef_319_consumers_study.py`,
  `tests/test_core1_ef_319_consumers_study.py`; run tool JSON sample in ignored
  `local/core1-ef319-report.json`. Corrected two addresses in run 5's note
  `docs/core1-ef-route-study.md` (fallthrough helper is `0x01126d2e`, not
  `0x0112d2e`; the parser is entered at `0x0110d962`, not `0x0110d980`).
- **Verified (all exact byte matches in the pinned payload, SHA-256
  `6d954…263154`, 105/105 anchors):** the route-0 fallthrough helper
  `0x01126d2e` tests byte-0 high nibble == 2, then consumes byte 1 in
  {0x80..0x85 (TBB at 0x1126d52, table bytes `03f05b5d2a1c`), 0x8e, 0x8f,
  0xbc, 0xbd, 0xbe} and ignores everything else including 0xEF (shared tail
  `0x01126e1a; movs r0,#8; b 0x11020c0`). The parser's ingress is recovered:
  the ASGN router's byte-0-high-nibble switch (0/3/7/0xb special) calls it at
  **`0x0110a6ba bl #0x110d962`** — run 5's xref search missed it by probing
  `0x0110d980/0x0110d981`. Parser `0x0110d962` dispatches on word low nibble
  (TBB at 0x0110d972, 15 entries, nibble 15 rejects); its shared bodies
  re-dispatch on byte 1 through binary-search chains that consume
  0x76/0x77/0x7c/0x80/0x88/0x8c/0x8d/0x99/0xa5/0xa6..0xad/0xb3..0xb7/
  0xbc..0xbe/**0xee**/**0xef** and reject the rest (`0x0110ddb6 b.w #0x110e2b6`).
  The **0xEF body `0x0110e1f2`** requires payload bit 15 (bytes 2..3 &
  0x8000), then the singleton getter `0x110e9f0` (returns `0x614020c8`),
  tests flag byte +0xa (zero, else a cleanup call `0x110f522` runs first),
  then walks a 16-entry table at `0x20084d88` (stride 0x148) calling each
  entry's vtable slots +0x10 and +0x20(+0x20, twice) and `0x1104e34` per
  entry. 0xEE is a distinct single-shot command, not an alias. So a 0xEF
  byte-1 ring word IS consumed on the recovered route, gated on payload bit 15
  and the flag byte — the first recovered place on bmc0 CORE1 where 0xEF does
  work. The remaining 0xEF consumers are exactly: this parser body (consumes),
  the helper (ignores), CUMDWRx (ignores, run 5).
- **Tests:** with corpus: 8 passed (0.03 s, `BMC_CORPUS_DIR=<main>/local
  python -m unittest discover -s tests -p test_core1_ef_319_consumers_study.py
  -v`); without corpus 3 pass, 5 skip cleanly. Sibling suites still pass:
  `test_core1_*.py` 44 (1 skipped), `test_bmc_ipc.py` 4.
- **Remains unknown:** whether the wire settings frames (host→0xEF, run 4) are
  the same stream this parser consumes — the parser reads two/three-byte
  records (low nibble + byte-1 command + 16-bit payload), not 12-byte short
  frames, so a repackaging peer would be required and that peer is still the
  missing ttyGS0 edge; what the 16 walked vtable callees do (call structure
  verified, body semantics inferred); the `0x110f522` cleanup body; whether
  bmc1 (`b1c1a.bin`) mirrors the route (untouched); the parser's producer side.
- **Best next item for run 7:** the section-3 item runs 3/5 flagged twice:
  locate which context owns the `2016..2019` routing writes against
  `fantom-audio-link-measurements.md` (kernel/audio ABI lane, not section 2),
  or, if the native side is too thin offline, cross-check the parser's producer
  requirements against `core1-transmit-and-backpressure-study.md` to bound what
  a resident loader would have to format into the second ring.

## Run 7 — 2026-11-13

- **Item chosen:** host-to-CORE1 bridge lane, the question runs 5/6 left
  explicitly untouched: whether bmc1 (`b1c1a.bin`) mirrors the recovered
  receive route. This closes the last open peer-mirroring edge of the
  route work and bounds the measurements' 0xE1/0xE2 addressing question with
  the same verified machinery; static only, no keys/encryption/device access.
- **Files added:** `docs/core1-b1-route-study.md`,
  `tools/core1_b1_route_study.py`, `tests/test_core1_b1_route_study.py`.
- **Verified (75/75 exact byte anchors in pinned bmc1, SHA-256 `c8d150…268bd`):**
  bmc1 mirrors the route's structure at every recovered decision with different
  addresses and sets — ASGN-analog task `0x0110a9e2` (nibble switch 0/3/7/0xb,
  else parser `0x0110f70c`; nibble 0 reads byte 1 at `0x0110aa54`, compares only
  0x07, else CUMDWRx `0x0110b7da`); CUMDWRx extracts `(word>>8)&0xff` and
  consumes nine commands — bmc1 adds 0x53 to bmc0's eight; remote-state helper
  `0x0112a1ce` (byte-0 high nibble 2 gate, shared tail `movs r0,#8`) consumes
  byte 1 in {0x80..0x88 TBB (`efeecfbf9ded14aedf`), 0x89, 0x8a, 0x8e, 0x8f,
  0x9f} — different from bmc0's {0x80..0x85, 0x8e, 0x8f, 0xbc..0xbe}; parser
  consumes 0xEF exactly like bmc0's: payload bit 15 gate, singleton getter
  `0x01110cfc` → `0x61402164`, flag byte +8, cleanup `0x11118a4`, 16-entry
  pointer walk at `0x20084d28` (bmc1 stride 0x2ac). Nothing on the recovered
  bmc1 chain tests byte 1 against 0xE1/0xE2 — the addressing question stays
  open on both images. Paired census (same committed scanner): 0xEF 16→47,
  0xE1 4→14, 0xE2 1506→6121. Also: run 6's prose stride 0x148 was wrong —
  bmc0's own instruction bytes compute 496 (0x1f0); committed anchors
  unaffected.
- **Tests:** with corpus: 13 passed (0.65 s, `BMC_CORPUS_DIR=<main>/local
  python -m unittest discover -s tests -p test_core1_b1_route_study.py -v`);
  without corpus 5 pass, 8 skip cleanly. Siblings: `test_core1_ef*.py` 17
  passed; `test_core1_*.py` 57 (1 skipped); `test_bmc_ipc.py` 4.
- **Remains unknown:** the bmc1 first-router (RXDT) analog and the ASGN task's
  entry path (no direct BL, word-ref or MOVW/MOVT/BX reference to `0x0110a9e2`
  anywhere in the image — entry is built at runtime or in an unrecovered
  table); whether a 0xE2-addressed frame would ever reach this route; the
  parser's producer on bmc1; the ERAM cmp#0xef/#0xe1 classifier contexts
  (stride-0x440 families at 0x610e722c/0x611cf8e4, not disassembled).
- **Best next item for run 8:** the section-3 item runs 3/5/6 flagged three
  times, still untouched: locate which context owns the `2016..2019` routing
  writes against `fantom-audio-link-measurements.md` (kernel/audio ABI lane,
  not section 2), or, if that stalls, cross-check the parser's producer
  requirements against `core1-transmit-and-backpressure-study.md` to bound
  what a resident loader must format into the second ring.

## Run 8 — 2026-11-13

- **Item chosen:** kernel/audio ABI lane, the section-3 item runs 3/5/6/7
  flagged four times and no run had taken: locate which context owns the
  `2016..2019` routing writes against `fantom-audio-link-measurements.md`.
  Took it because the native image gives a concrete, fully static handle —
  the exported `CSimDSP4Routing::VSubProc` — and the queue explicitly
  forbids labelling `2016..2019` physical TDM channels without evidence, so
  naming the writer and its call condition closes a named gap. No keys,
  encryption or device access.
- **Files added:** `docs/routing-2016-owner-study.md`,
  `tools/routing_2016_owner_study.py`,
  `tests/test_routing_2016_owner_study.py`.
- **Verified (65/65 byte-exact anchors in pinned `zen_arm64`, SHA-256
  `b8ba7…c30`, via `tools/routing_2016_owner_study.py`):** the owner chain is
  `CEfctPrm::EfctLoadFixedAlg` (`0x165fd8`) → `CSimDSP4_Core::Init`
  (`0x16bc68`) → routing ctor `0x41288` with `(CFspDspMgr*, SGlobalObj*)` →
  stored at core+0x230 (`0x16bcc4 str x20, [x19, #0x230]`); per pass
  `VProcSync` dispatches through it and `VSubProc` (`0x413d0`) writes the
  four routing slots (absolute 0x16..0x19 = program operands `2016..2019`
  under the FZ tag-2 base 0x16) **unconditionally** (`0x41c54..0x41ca8`),
  while the effect's virtual call is gated on two floats in the 0x1b40
  structure: `[x8+0x678] == 0` forces bypass (`0x41c14/0x41c18/0x41c30`),
  else `[x8+0x628] != 0` enables (`0x41c20/0x41c28`), dispatch at `0x41cac
  tbz` → vtable byte 0x20 = **slot 4** (`0x41ccc`), confirmed by
  `SIM_MFX_FZ::VSubProc 0x3e480c` sitting at `0xa76210` = slot 4 of the
  vtable starting `0xa761f0` (typeinfo chain names `9CMDSPTask`). The bypass
  path still writes slots and zeroes ten 32-byte effect-state blocks
  (`0x41d2c..0x41d90`). `CSimDSP5Routing::VSubProc` (`0x34c244`) mirrors the
  shape with absolute slots 0x460..0x465 and zeroed fallback outputs.
  Nothing in this chain references a TDM/SAI slot number — the writes are
  core-internal routing storage, corroborating the queue's warning.
- **Tests:** with corpus: 9 passed (0.05 s, `BMC_CORPUS_DIR=<main>/local
  python -m unittest discover -s tests -p test_routing_2016_owner_study.py
  -v`); without corpus 5 pass, 4 skip cleanly (pinned-image guard).
  Siblings still pass: `test_core1_*.py` 57 (1 skipped), `test_bmc_ipc.py`
  4, `test_transfer_study.py` 6 (1 skipped).
- **Remains unknown:** which BMC/DSP/TDM slot each native routing instance
  maps to on the instrument (native study cannot bound it; the kernel study's
  five recorded effect placements stay the Fantom-side evidence); which
  coefficient symbols feed the gate floats at structure+0x678/+0x628 (writers
  untraced); whether DSP5's 0x460..0x465 matches the kernel study's per-
  instance DSP5 tag-2 bases (DSP5 ctor tables not reconstructed); the role of
  the six `SIM_MFX_COMP::Init` instances at `EfctLoadFixedAlg`'s tail.
- **Best next item for run 9:** trace the writers of the gate floats
  (structure+0x678/+0x628) to name the stock mute/enable controls that gate
  the routing dispatch — they are the natural counterpart of CORE1's
  `ff70/ff71` mute state — or, if that stalls, reconstruct the DSP5 routing
  ctor tables (`0x34c0f8`) to bind `0x460..0x465` to the kernel study's DSP5
  list operands. Both are static, native-side, and reuse this run's tool.
