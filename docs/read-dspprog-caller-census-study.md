# ReadDspProg caller census: the program-read twin exists in both CORE1 images and no static reference names it

2026-11-13. Static Capstone analysis of the two pinned, header-stripped Fantom-0
CORE1 payloads `local/b0c1a.bin` (SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`) and
`local/b1c1a.bin` (SHA-256
`c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd`). This study
closes the one gap `program-read-path-study.md` (overnight run 13) left in the
load-route item A1: whether the stock image names any caller of
`CBmcDspDrv::ReadDspProg`. Nothing executed; no instrument was contacted.

## Method

Run 13 proved `ReadDspProg` has no direct BL/B, no MOVW/MOVT/BX veneer and no
stored Thumb pointer *word in the mapped code*, and named initializer/scatter
tables as the remaining computed-call paths. This run added the three missing
reference forms and exhausted all of them in both images:

1. **MOVW/MOVT constructor pairs** — a RAM vtable built at runtime by two
   immediate-forming instructions (the veneer scan only finds the triple with a
   following BX, and the stored-word scan only finds an already-materialized
   pointer, so a vtable constructor is visible to neither).
2. **PC-relative ADR** — `add{.w}/addw rX, pc, #imm` computing the address in
   place (an image could reference the function without any pool word).
3. **The *expanded* compressed initial-data image** — run 13 and the run-13
   xref only scanned stored payload bytes; RAM vtables live in the
   scatter-decompressed image at `0x2008008c..0x20084818`, which the verified
   handler `0x6100003c` expands (handler byte-identity and expansion model
   reused unchanged from `core1_wait_study.py`).

Plus, for completeness in both images: every stored word (anywhere in the
payload, code or ERAM) equal to the function address or its Thumb pointer, the
Cortex-M vector table, and literal-pool words (subsumed by the stored-word
scan). The tool also *locates* the function by a build-independent prologue
shape instead of pinning one address, so the b1c1a twin is found, not assumed.

Command producing the evidence below:

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open\ Synth\ Platform/bmc-research/.venv/bin/python \
  tools/read_dspprog_caller_census.py b0c1a
```

Pasted tool output (trimmed: the `read_dspprog`/table fields print decimal in
the JSON; hex equivalents in the prose below):

```json
{
  "payload_sha256": "6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154",
  "read_dspprog": 18020172,
  "aperture_table": 18065748,
  "raw_ports": 18066036,
  "dma_state_byte": 537413616,
  "aligned_thumb_pointer_candidates": [],
  "direct_branch_candidates": [],
  "movw_movt_bx_candidates": [],
  "movw_movt_constructor_pairs": [],
  "adr_references": [],
  "stored_word_hits": [],
  "expanded_ram_word_hits": [],
  "expanded_bytes": 18316,
  "compressed_bytes_used": 8003,
  "callers_found": false,
  "execution_ready": false
}
```

(Decimal: ReadDspProg `0x0112f74c`, aperture table `0x113a954`, raw ports
`0x113aa74`, DMA state byte `0x200847f0` — all equal to run 13's pins.)

The b1c1a run:

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open\ Synth\ Platform/bmc-research/.venv/bin/python \
  tools/read_dspprog_caller_census.py b1c1a
```

```json
{
  "payload_sha256": "c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd",
  "read_dspprog": 18019220,
  "aperture_table": 18067892,
  "raw_ports": 18068180,
  "dma_state_byte": 537413492,
  "aligned_thumb_pointer_candidates": [],
  "direct_branch_candidates": [],
  "movw_movt_bx_candidates": [],
  "movw_movt_constructor_pairs": [],
  "adr_references": [],
  "stored_word_hits": [],
  "expanded_ram_word_hits": [],
  "expanded_bytes": 18192,
  "compressed_bytes_used": 7239,
  "callers_found": false,
  "execution_ready": false
}
```

(Decimal: ReadDspProg `0x0112f394`, aperture table `0x113b1b4`, raw ports
`0x113b2d4`, DMA state byte `0x20084774`.)

## What was verified, per claim

- **The b1c1a twin is `ReadDspProg`, not a coincidental match.** The locator
  requires the full prologue shape — `push.w {r4,r5,r6,r7,r8,lr}` (bytes
  `2de9f041`), `mov r8, r3`, `cmp r0, #7`, then `orr.w r3, r1, r2` and
  `tst.w r3, #1` inside the next twelve instructions. Dumped from the image
  this run (`tools/core1.py local/b0c1a.bin --address 0x112f74c --size 0x30`
  in the run-13 note; re-dumped identically here), b0c1a yields exactly
  `0x0112f74c`; b1c1a yields exactly `0x0112f394`; each image yields exactly
  one candidate (asserted by the tool, exit 2 otherwise).
- **Both twins share one aperture/port design.** The tool asserts the seven
  aperture words and seven raw-port words byte-for-byte in each image against
  the constants run 13 pinned for b0c1a:
  apertures `41480000 41580000 41680000 41780000 41880000 41980000 41260000`,
  raw ports `41104700 41105700 41106700 41107700 41108700 41109700 41102700`.
  Both images pass the same assertion at their own table addresses
  (`0x113a954`/`0x113aa74` in b0c1a; `0x113b1b4`/`0x113b2d4` in b1c1a). Each
  twin loads its DMA state byte's address from its own literal pool, and the
  tool asserts that pool word: `0x112fc74` = `0x200847f0` in b0c1a,
  `0x112f8bc` = `0x20084774` in b1c1a. In each image that same state byte is
  referenced by 18 literal-pool loads spanning the DMA driver family around
  the twins (`0x0112f42c..0x0112fbf6` plus later driver bodies in b0c1a, the
  mirrored range `0x0112f074..0x0112f974` in b1c1a); for b0c1a the write path
  is inside that referenced range (run 13's write study), and the b1c1a range
  mirrors it positionally, but this run did not name each b1c1a referencing
  function individually.
- **Every enumerable reference form is empty in both images.** Seven scanner
  families return `[]` in the outputs above: direct branches, MOVW/MOVT/BX
  veneers, aligned Thumb pointer words (stored anywhere), MOVW/MOVT constructor
  pairs, PC-relative ADR forms, stored words equal to the target or target|1,
  and words inside the expanded initial-data image. The expanded image is not
  assumed: the tool decompresses the scatter record
  (`destination 0x2008008c`, verified handler `0x6100003c`) and pins its size
  and consumed source bytes (`0x478c`/`0x1f43` b0c1a; `0x4710`/`0x1c47` b1c1a),
  matching the run that introduced the expansion model.
- **An empty scanner proves liveness, not death.** The ADR scanner initially
  returned `[]` on all inputs because Capstone names the PC-relative T3 form
  `addw`, not `add.w`; the first tool version missed the form. The committed
  tool asserts two per-image liveness anchors — real instructions in each image
  that the scanners must resolve or the tool exits 2: b0c1a `add.w r6, pc,
  #0x204` at `0x112e74e` (sum `0x0112e954`) and the MOVW/MOVT pair at
  `0x1134380` (materializing `0x61015b77`); b1c1a `addw` at `0x110165e` (sum
  `0x01101a14`) and the pair at `0x1133ffc` (materializing `0x61070181`). Both
  images pass, so the all-empty result was produced by scanners proven to fire
  on this image.
- **Fail-closed negatives.** The synthetic tests plant a pointer word in
  stored and expanded regions and assert `census()` finds both; they plant real
  instruction bytes (taken from these images this run) for the MOVW/MOVT, ADR
  and prologue scanners and assert exact hits, then one-bit mutations produce
  no hits; `report()` raises on any nonempty reference list, on a digest
  mismatch (tested by flipping one image bit) and on a locator miss.

## What this establishes for item A1

The stock bmc0 and bmc1 CORE1 images contain a complete, sound program-RAM read
primitive — `ReadDspProg`, geometry mapped by run 13 — and in **neither** image
does any enumerable static reference name it: no branch, no veneer, no
constructor pair, no ADR, no stored or decompressed pointer word. The run-13
statement "no static caller found" is now strengthened to "no *reference of any
scannable kind* exists in either image, with scanner liveness proven per image
and per form". For loading a foreign program and reading it back, the remaining
unknowns are exactly: (1) how execution would ever reach `ReadDspProg` (only a
computed call whose address is assembled by arithmetic on data this census
cannot enumerate — e.g. base + index*4 — could invoke it), and (2) the missing
external peer that would carry a readback request from the host. This makes
readback-for-verification in the first custom-voice milestone dependent on
either a resident CORE1 bridge calling the driver directly, or hardware
observation; the *write* route alone is fully mapped.

## What is not established

- No hardware observation: that silicon returns just-written program bytes on a
  literal read is still untested (run 13's caveat, unchanged).
- "No reference" is exhaustive only over the enumerated forms. A reference
  built by runtime arithmetic on another pointer (for example
  `table_base + 4*k` where `table_base` comes from a relocation) is invisible
  to every scanner here; no such table entry was found pointing at the twin,
  but a dynamically computed *derived* address cannot be excluded by static
  scanning in general.
- The b1c1a twin is proven identical by prologue shape plus value-identical
  aperture/port tables plus its own pool's state byte; a byte-level diff of the
  two function bodies was not performed, and per-build addresses differ, so
  "same function" is a structural, not byte-exact, identity.
- Whether the stock scheduler ever reads a whole program at runtime (through a
  call path outside this image, or on other builds) remains unknown.
- Other builds (JUPITER-X, MC-101, SH-4d) were not scanned for twins or
  callers; this census is bounded to the two pinned Fantom payloads.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  python tools/read_dspprog_caller_census.py b0c1a
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  python tools/read_dspprog_caller_census.py b1c1a
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  python -m unittest discover -s tests -p test_read_dspprog_caller_census.py -v
```