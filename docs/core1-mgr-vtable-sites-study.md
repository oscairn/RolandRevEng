# CBmcDspMgr virtual-call site attribution (flag path A3 closure)

A3 follow-up (entry, return and the mute gate). Run 17
([core1-dsp-flag-study](core1-dsp-flag-study.md)) proved the per-DSP flag path's
manager wrappers — `CBmcDspMgr::SetDspFlag` at vtable byte 0x10 and
`CBmcDspMgr::SetDspFlagBit` at byte 0x14 (address point `0x6117647c`) — have
zero direct callers, listed candidate virtual-call sites, and left the
attribution open: which of those sites dispatch on a real `CBmcDspMgr` object?
This run bounds the attribution and corrects the strict-scan defect that
over-attributed the committed site lists in runs 11 and 17. Static, read-only
file analysis of the pinned bmc0 CORE1 payload (SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`). No
firmware executed, no device access, no key/ciphertext material.

## Result (summary)

- **The manager class is RTTI-pinned:** the vtable address point `0x6117647c`
  is preceded by typeinfo `0x6117177c` (`0x61176478 = 0x6117177c`, byte-pinned),
  whose words are `(base 0x6117c3f8, name 0x61173e6d)` and whose name string
  bytes at `0x61173e6d` are exactly `10CBmcDspMgr`. The repo's
  `tools/core1_rtti.py` independently resolves the same single candidate
  vtable for the encoded name `10CBmcDspMgr`.
- **The manager objects and their construction:** exactly three objects carry
  this vtable, at SRAM cells `0x20084b8c`, `0x20084ba0`, `0x20084bb4`, each
  0x14 bytes, written only by the constructor `0x6100177c` (boot-region ERAM;
  no direct BL/veneer/word callers — the unresolved-entry class of runs
  7/11/15/16). Its pool holds `(base 0x20084b8c, object table 0x61085dec,
  log literal 0x2009be2c, vtable 0x6117647c)`; the body stores the vtable
  address point three times with `adds r4,#0x14` between (byte-pinned at
  `0x610017a0`/`0x610017c0`). Whole-image literal-word census: `0x20084b8c` is
  referenced only at `0x610014e0` (the boot verify routine's pool) and
  `0x61001824` (the constructor's pool); `0x20084ba0`/`0x20084bb4` only at
  `0x610014e4`/`0x610014e8`. No `movw/movt` pairs anywhere produce any of the
  three cells. ITCM/ERAM constructor twins (`0x1127120`, `0x1128974`,
  `0x6102cc68`, `0x61077b6c`) build same-vtable objects at their own runtime
  cells (`0x2009be2c`, `0x2009bbf8` pools etc.), so the class has more
  instances than the three cells — but only the three cells are
  literal-resolvable.
- **The strict scan defect, fixed:** the runs-11/17 scanner counted a site for
  any `ldr rX,[rY,#disp]` within 12 prior halfwords of a `blx rX`, even when
  an intervening instruction rewrote `rX`, double-counting stale loads. The
  corrected scanner (`tools/core1_mgr_vtable_sites_study.py`) requires the
  matched `ldr` to be the last write of the `blx` register. Concrete stale
  members in the committed lists: `0x61030578` was listed under byte 0x18
  (run 11's upload list) but its `blx` at `0x61030578` uses the `#0x10` load
  at `0x61030576` (`0969 8847`, pinned); `0x61030584` was listed under 0x1c
  and 0x10 (runs 11/17) but uses the `#0x1c` load at `0x61030582`; `0x61030594`
  was listed under 0x1c and 0x14 but uses the `#0x20` load at `0x61030592`;
  `0x110e06a` was listed under both 0x14 and 0x10 but its `blx` uses the
  `#0x10` load at `0x110e068`; `0x1128fae`/`0x1128fe8`/`0x1128ff2` (byte-0x10
  list) actually call `#0x04`/`#0x04`/`#0x00` (their own scan matched stale
  `#0x10` loads two/three instructions back); `0x6103bee8` (byte-0x1c list)
  uses the `#0xc` load at `0x6103bee6`. Corrected census (whole image, 27
  anchors pinned): byte 0x10 — 19 sites; byte 0x14 — 11 sites; byte 0x18 —
  12; byte 0x1c — 7; byte 0x20 — 6 (full lists in the JSON below).
- **Attribution bounds.** Among the corrected sites, only the boot verify
  routine's dispatch is literal-provable: its pool words `0x610014e0/e4/e8`
  ARE the three manager cells (byte-pinned), and the boot routine's byte-0x18
  phase-1 / byte-0x1c phase-2 dispatches (`0x61001114..0x61001118`,
  `0x61001154..0x61001158`) load the manager pointer from those cells through
  the `it eq` conditional-pool loads at `0x610010fe/0x61001106/0x6100110e` —
  the runs-11/15 boot walk. No byte-0x10/0x14 site is literal-provable in
  this sense: the other sites load their object from enclosing-context fields
  (`[r4,#0x74]`, `[r4,#0xc]`, `[r4,#0x5c]`, `[r4,#0x4]`, `[r4,#0x78]`) whose
  bases come from callers, or from dispatcher-table cells. What IS bound:
  - the ITCM handlers `0x11021c0`/`0x11021f0`/`0x1102760`/`0x1102794` run in
    event-handler context (they increment byte-0x10/0x14 counters, arm via
    `dsb sy`, and their enclosures match the coefficient-readback event
    handlers' construction of run 11 — the boot routine's pools supply the
    object), and
  - the ERAM lifecycle sites `0x61030560/0x61030578/0x61030584`,
    `0x61034cb8`, `0x6103ce96` load the object from `[r4,#0x74]` — the same
    dispatcher-table cell the runs-16 diagnostic uploader chain uses — and the
    two enclosing functions `0x6103050c`/`0x61034c52` appear in dispatcher rows
  at `0x6117a848`/`0x6117b33c` — each `[0, typeinfo, ctor, fn, three helpers]`
  with `(typeinfo 0x61173414, ctor 0x61030505, fn 0x6103050d, 0x610813c5,
  0x61030613, 0x610813c1)` and `(typeinfo 0x611737e4, ctor 0x61034c39,
  fn 0x61034c53, 0x610813c5, 0x61034d29, 0x610813c1)` — whose typeinfo words
  (`0x61173414`/`0x611737e4`) start typeinfo chains `0x6117c408 → 0x611756ba`,
  the same `10CBmcDspMgr`-adjacent chain as `0x6117c3f8`. These sites'
    vtables come from a dispatcher-table lookup, not from the three literal
    cells, so dispatching on `CBmcDspMgr` for them is inferred (same vtable
    address point, RTTI-adjacent table), not literal-proven.

## Method

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python tools/core1_mgr_vtable_sites_study.py
```

The tool byte-pins 27 anchors (vtable head, typeinfo, RTTI name bytes, ctor
head/stride stores, boot dispatch triple, corrected-site spot anchors, the two
dispatcher rows, boot and ctor pools, the ITCM/ERAM twins' vtable pool words),
re-derives the byte-0x10/0x14/0x18/0x1c/0x20 site lists with the corrected
scan, checks them against the expected lists, and censuses literal word
references to the three manager cells. `ok` requires all of them. Full
report in ignored `local/mgr-sites-report.json` (this worktree's `local/`).

Real tool output (trimmed to the cited fields; exit 0):

```json
{
 "ok": true,
 "anchors_checked": 27,
 "anchor_problems": [],
 "corrected_sites": {
  "0x10": ["0x11021c0", "0x1102760", "0x110e03e", "0x110e06a", "0x110e274",
           "0x1128ca0", "0x1128f20", "0x1128fa4", "0x1128fde", "0x112a666",
           "0x112a848", "0x113126a", "0x6101ef68", "0x6102f648",
           "0x6102fb78", "0x61030578", "0x61030acc", "0x610839e6",
           "0x61083d1e"],
  "0x14": ["0x11021f0", "0x1102794", "0x110e060", "0x1129064", "0x11312b8",
           "0x61030560", "0x61034cb8", "0x6103ce96", "0x611b74c2",
           "0x611b7562", "0x611ca2ca"],
  "0x18": ["0x1102220", "0x11027c8", "0x110ddd8", "0x110e43a", "0x1131306",
           "0x61001118", "0x61013afa", "0x6101ef8c", "0x61026a64",
           "0x6103056c", "0x61034980", "0x61034cf6"],
  "0x1c": ["0x1102250", "0x11027fc", "0x1131336", "0x61001156", "0x61026652",
           "0x61030584", "0x6103bede"],
  "0x20": ["0x1102280", "0x1129a04", "0x1131366", "0x6101efb0", "0x61030594",
           "0x610836f8"]
 },
 "manager_cell_word_refs": {
  "0x20084b8c": ["0x610014e0", "0x61001824"],
  "0x20084ba0": ["0x610014e4"],
  "0x20084bb4": ["0x610014e8"]
 }
}
```

Key disassembly, real recorded output of the commands below:

```sh
PYTHONPATH=tools <venv>/bin/python tools/core1.py <main>/local/b0c1a.bin --address 0x61030560 --size 0x40
```

```text
61030560  8847       blx       r1                      ; [r4+0x74] vtable #0x14
61030562  606f       ldr       r0, [r4, #0x74]
61030564  95ed010a   vldr      s0, [r5, #4]
61030568  0168       ldr       r1, [r0]
6103056a  8969       ldr       r1, [r1, #0x18]
6103056c  8847       blx       r1                      ; #0x18 (upload, not #0x14)
6103056e  606f       ldr       r0, [r4, #0x74]
61030570  95ed020a   vldr      s0, [r5, #8]
61030574  0168       ldr       r1, [r0]
61030576  0969       ldr       r1, [r1, #0x10]
61030578  8847       blx       r1                      ; #0x10 SetDspFlag
6103057a  606f       ldr       r0, [r4, #0x74]
6103057c  95ed030a   vldr      s0, [r5, #0xc]
61030580  0168       ldr       r1, [r0]
61030582  c969       ldr       r1, [r1, #0x1c]
61030584  8847       blx       r1                      ; #0x1c (DRAM-IO, not #0x10)
```

Real output (the flag wrapper bodies reached only through the vtable, from
run 17's pinned disassembly of `0x1131bc6`; shown here for the attribution
argument: `0x1128fa4`'s call shape `ldr r0,[r4,#0xc]; ldr r1,[r0];
ldr r1,[r1,#0x10]; blx r1` is byte-identical to the `#0x10` form):

```text
01128f9e  e068       ldr r0, [r4, #0xc]
01128fa0  0168       ldr r1, [r0]
01128fa2  0969       ldr r1, [r1, #0x10]
01128fa4  8847       blx r1
01128fa6  a061       str r0, [r4, #0x18]
```

## Established

- The flag-path manager wrappers' class is named: vtable `0x6117647c` belongs
  to RTTI class `10CBmcDspMgr` (typeinfo/name bytes pinned; independently
  reproduced by `tools/core1_rtti.py`, single candidate).
- The manager objects are constructed only by `0x6100177c`; exactly three
  (`0x20084b8c/ba0/bb4`, 0x14 stride) are literal-resolvable, and the only
  image consumers of those cells are the boot verify routine (pool
  `0x610014e0..e8`) and the constructor itself. Same-vtable twins are built
  by four more constructors whose cells are runtime-only.
- The committed byte-0x10/0x14/0x18/0x1c/0x20 site lists of runs 11 and 17
  contained stale-register over-attribution; the corrected lists are above
  (19/11/12/7/6 sites; six members removed, one moved: none of the removed
  members is a byte-0x10/0x14 dispatch).
- Only the boot verify routine's manager dispatch is literal-proven to target
  the three cells; every other corrected site's object base comes from
  context. Among them, the ERAM effect-lifecycle sites
  (`0x61030560/0x61030578/0x61030584` in `0x6103050c`, `0x61034cb8` in
  `0x61034c52`) dispatch on `[ctx+0x74]` — the same field the runs-16
  diagnostic uploader chain reads — and their enclosing functions appear in
  dispatcher rows adjacent to the manager's RTTI chain, so their being
  `CBmcDspMgr` dispatches is inferred from the shared vtable address point,
  not literal-proven.
- The flag wrappers themselves (`0x1131bc7`/`0x1131bfd`) appear at no corrected
  site as blx targets — consistent with run 17: they are reached only through
  the vtable words `0x6117648c/0x61176490`.

## Not established

- Which corrected byte-0x10/0x14 sites other than the boot routine's dispatch
  actually target one of the three literal cells at runtime (their object bases
  are context fields; binding `[ctx+0x74]`/`[ctx+0xc]` to a concrete cell needs
  the unit or a runtime capture).
- The dispatcher rows `0x6117a848`/`0x6117b33c`' owner and how the
  `[ctx+0x74]` field is filled (the 0x61173414/0x611737e4 typeinfo chains were
  followed two hops; their class names were not resolved this run).
- Whether the constructor `0x6100177c`'s three objects are the only live
  `CBmcDspMgr` instances (the four twin constructors' cells are runtime-only;
  their bodies' shapes were pinned only via their pool vtable words).
- bmc1 mirrors none of this (untouched, like runs 7/15/16/17).

## Corrections to earlier notes

- `docs/core1-load-route-callers-study.md` (run 11): the upload-slot site
  lists contained `0x61030578` under byte 0x18, `0x61030584` under 0x1c AND
  0x20, `0x61030594` under 0x1c AND 0x20, `0x6103bee8` under 0x1c — the strict
  scanner's stale-load defect. The corrected lists (12/7/6 sites) are pinned
  by this run's tool; the note's prose tables were edited in place and marked.
- `docs/core1-dsp-flag-study.md` (run 17): the byte-0x10/0x14 candidate lists
  in "Not established" contained the same stale members
  (`0x1128fae/0x1128fde/0x1128fe8/0x1128ff2` all under 0x10;
  `0x110e06a/0x6103056c/0x61030594` also under 0x14; `0x611c9e38` under 0x14)
  plus `0x61034f7c` (its `blx` is `#0x08` via `[r4,#0x78]`). The note's list
  was replaced with the corrected census and marked.

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local <venv>/bin/python -m unittest discover -s tests -p test_core1_mgr_vtable_sites_study.py -v
```

With the corpus: pinned-image class runs; without it, the pure scanner-model
tests pass and the pinned class skips cleanly.