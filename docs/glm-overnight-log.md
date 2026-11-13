# GLM overnight run log

Unattended run series on worktree branch `research/glm-overnight`. One bounded
item per run; each entry records what was verified, by which command, and what
remains open. Runs do not touch keys, ciphertext, access routes, flashing or
ROM dumping, and stop after committing.

## Run 2 — 2026-11-13: LINE prefix count-1 writers finished and verified

Item chosen: finish the interrupted count-1 single-writer study in the
instruction-semantics lane (the LINE input-mix tied-versus-split question left
open by `line-prefix-global-groups.md`). The worktree already contained
uncommitted drafts of the study note and tool from a prior session; they had a
syntax error, no test file and no recorded run, so nothing in them was yet
evidence. This run fixed, ran, tested and committed them. (No log file
existed before this run; run 1's outcome is unknown — the drafts may be its
uncommitted output.)

Files:

* `tools/line_prefix_single_writer.py` (new): count>=1 descriptor inventory over
  relative fields 14/17/24/27, ADRP+ADD/LDR reference resolution, bounded decode
  of the writer method `1d1ac8..1d1b70`, and the JUPITER-X asymmetric
  4822/1940 instance check (`--jupiter-c1a`).
* `tests/test_line_prefix_single_writer.py` (new): 9 tests — synthetic fixtures
  for `mentions()`/`code_references()` fail-closed behavior plus corpus-pinned
  inventory, references, writer shape and JUPITER-X facts.
* `docs/line-prefix-single-writer-study.md` (new): the study note (from the
  earlier draft, claims below re-checked).

Verified this run (commands and outputs in the transcript):

* Both corpus runs of the tool exit 0:
  `python tools/line_prefix_single_writer.py local/zen_arm64` (13 mentioning
  descriptors, `count2_pair_groups: []`, writer 0x1d1ac8) and the same with
  `--jupiter-c1a .../MI077_C1A_up.bin` (8 sites, all count 1, asymmetric
  literals `[1.0, 0.0]`).
* `count2_pair_groups` is now computed from the scanned rows, not hardcoded;
  the pinned image really has no count>=2 group containing {14,17} or {24,27}.
* The two functions larger than the straight-line reference limit
  (`589000..5af838`, `6b74ec..6d5138`) are now scanned separately inside
  `study()` and must yield no further 17/27 record references or it fails.
* Sibling table claim checked directly: bytes at `0x818d20` unpack as 128
  finite doubles spanning exactly `0.0..0.9998779296875`, as the note states.
* `python -m unittest discover -s tests -p test_line_prefix_single_writer.py`:
  9 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus).
* `python -m unittest discover -s tests -p test_prefix_group_inventory.py`:
  3 tests, OK; the earlier draft diff to that tool was reverted as unused.

Remaining unknown (unchanged from the note): ownership/callers of `1d1ac8`,
runtime-built descriptors, other builds, how the DSP treats the four fields,
any hardware capture. No new opcode or interpreter admission.

Best next item: the queue's standing instruction-semantics lead — prove the
mixed-packet operation families around `5d52` (`1c90`/`0d90`, `ded4`, `9450`,
`d550`/`d554`) against both channel chains, or, if that needs native
execution fixtures beyond an overnight run, extend the fragment emulator's
verified coverage by one more LINEDRIVE/FETDRIVE packet context with the same
fail-closed test style used here.

## Run 4 — 2026-11-13: fitted four-operation header rule cross-checked, no counterexample

Item chosen: the instruction-semantics lane item left as next by run 2 and the
agent handoff — corpus-wide validation of the explicitly hypothesis-only fitted
rule for four-operation header families (rank
`combinations_with_replacement(range(5), 4)` under
`sum(kind<2)<=2 or (sum==3 and last==2)`, indexed by `(header>>8)-0x40`, 57
entries). The handoff fitted it to six anchors with predictions `4b=0124`,
`5a=1122`, `5c=1124`, `62=1224` and forbade expanding `header_study.families()`
from the fit alone; this run tested the fit against the corpora without admitting
anything.

Files:

* `tools/header_family_crosscheck.py` (new): rebuilds the ranking from the
  constraint, asserts size 57 and the six anchor families, then scans
  render-list segments of any number of `--core1`/`--qspi` images with the
  existing `analyze.core_lists()` framing, comparing every count-4 packet against
  the rule (code range, strict-decode families, must-fail-closed for
  miscellaneous predictions). Zero decoder changes.
* `tests/test_header_family_crosscheck.py` (new): 7 tests — ranking/anchor
  agreement pinned against `header_study.families`, only-anchors-strictly-decode
  partition, synthetic strict-decode and out-of-range counterexample detection,
  and corpus-pinned zero-counterexample plus exact packet/code counts.
* `docs/header-family-crosscheck-study.md` (new): the study note.

Verified this run (commands and outputs in the transcript):

* The tool exits 0 with zero counterexamples over six images
  (zen_arm64, b0c1a.bin, b1c1a.bin, JUPITER-X MI077, MC-101 RPG69, SH-4d DD013):
  38,441 count-4 packets, every code inside `40..78`, all strict decodes are the
  six anchors (zen 1,703; b0 3,697; b1 631; JUPITER-X 11,285; MC-101 837;
  SH-4d 8,985), zero non-anchor strict decodes, zero rejected decodes.
* GASSDLY's `6209` (`6fe4 9450 ded4 8fe2`, segment offset `022e`) and `6207` fail
  closed as the fitted `62=(1,2,2,4)` miscellaneous prediction requires; the
  `6fe4` trap stays unresolved, unchanged.
* `python -m unittest discover -s tests -p test_header_family_crosscheck.py`:
  7 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus).
* `python -m unittest discover -s tests -p test_header_study.py`: 9 tests,
  OK (1 skipped without context) — decoder unchanged.
* Full `python -m unittest discover -s tests` with the corpus: no failures.

Established: the fit is consistent with all six prepared images; no non-anchor
count-4 code strictly decodes anywhere, so no discriminating evidence for the
predicted tuples exists. Unknown: the actual operand syntax of the 45 observed
non-anchor codes; whether the ranking constraint has a causal basis; other builds.
No opcode or interpreter admission.

Best next item: the smallest independent proof is still the earlier-`5a`/`62`
context — bind `1c90`/`0d90`/`ded4`/`9450`/`d550`/`d554` effects to native
cutpoints through both channel chains (native execution fixtures), or, if that
exceeds one run, a native window over a `4b`/`5c` miscellaneous slot as an
alternative discriminator.

## Run 6 — 2026-11-13: GASSDLY 6209 6fe4 trap resolved to a proved shared ownership group

Item chosen: the instruction-semantics trap the handoff and run 4 left standing —
GASSDLY's `6209` packet (`6fe4 9450 ded4 8fe2`), whose `6fe4` low-six reference
selects relative field `23c` while the native constructor representative for the
1.414 value names relative `22b`. The handoff required proving the
shared-representative/ownership-update group before any binding; this run proved
it with the count-1/count-N descriptor machinery run 2 built.

Files:

* `tools/gassdly_62_trap.py` (new): pins the constructor pair (object+`b0`/`b8`
  = relative `22b`, double `1.414`), proves no constructor pair names `23c`,
  maps the `6fe4` and `75e5` low-six references to fields `23c`/`22b`, and
  recovers the unique count-2 group `9dfa50` (`424b/22b`, `425c/23c`) written by
  the single slot-`c8` call at `cbf98` inside `CFspMfxGASSDLY::SetDLY`.
* `tests/test_gassdly_62_trap.py` (new): 7 tests — synthetic fail-closed checks
  for the mov/movk immediate rebuild and low-six reference rejection, plus
  corpus-pinned representative, trap, ownership and stored-bytes facts.
* `docs/gassdly-62-trap-study.md` (new): the study note.

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  python tools/gassdly_62_trap.py local/zen_arm64` — representative
  `(22b, 1.414)`, no second `23c` pair among 123, `6fe4` -> field `23c`
  (1.4139995574951172), `75e5` (packet `5a09`) -> field `22b`, stored bytes equal
  (`369fbe`), group `9dfa50` written at `cbf98` inside `cbe54..cc0d4` with
  selection constants 0.1 / 1.4140000343322754 / 1.0.
* `python -m unittest discover -s tests -p test_gassdly_62_trap.py`: 7 tests, OK.
* Neighboring suites unchanged: `test_line_prefix_single_writer.py` 9 OK,
  `test_short_add_context_study.py` 3 OK, `test_line_prefix_study.py` 4 OK,
  `test_prefix_group_inventory.py` 3 OK, `test_header_family_crosscheck.py` 7 OK,
  `test_emulator_target_study.py` 3 OK.

Established: the `22b`/`23c` pair of program `4020` in GASSDLY is declared and
written together by one checked grouped-write operation, always with one common
value; the native read side binds the 1.414 double to field `22b` only. The
handoff's precondition for a `6fe4`-consumes-`23c` binding is therefore satisfied
for this pair. Unknown: actual DSP execution of `6fe4`, the fitted `62` family
roles of `9450`/`ded4`/`8fe2`, runtime-built/raw writers, other builds. No opcode,
family or interpreter admission.

Best next item: with the ownership precondition met, the `5a`/`62` family proof
can proceed — either prove the `ded4`/`9450`/`8fe2` roles of the `6209` packet
statically against both channel chains, or attempt the native cutpoint binding of
the GASSDLY/GASSPH/GAMPSIM `5d52` chains through the now-proved grouped fields.

## Run 7 — 2026-11-13: RVSDLY cross-check removes the grouped-equality objection

Item chosen: the instruction-semantics cross-check run 6 left open — test the
GASSDLY `0x22b`/`0x23c` grouped-ownership and strict-reference reading against a
second independent program. `SIM_MFX_RVSDLY` is the natural discriminator
because run 6's own sibling table shows its two fields owned by separate
count-1 groups, so the grouped-equality shortcut that carried the GASSDLY proof
is unavailable and each field must stand on its own constructor and reference
evidence. Static analysis only; no native execution fixture was needed.

Files:

* `tools/rvsdly_22b_23c_crosscheck.py` (new): pins the RVSDLY segment bases,
  stored field triples, exactly-one constructor pair per field (object `0x150`
  -> relative `0x22b`, 0.99609375; object `0x140` -> relative `0x23c`,
  -0.998046875), the count>=1 descriptor inventory, the two count-1 RVSDLY
  groups and their sole references inside `CFspMfxRVSDLY::SetAlg()`, the exact
  six-call slot-c8 sequence with descriptor/argument registers, and the
  strict-decoder (`header_study.layout`) packet-reference sets for both fields.
* `tests/test_rvsdly_22b_23c_crosscheck.py` (new): 7 tests — synthetic
  fail-closed checks (exact-start literal matching, one-bit mutation,
  unsupported-layout skip, truncated descriptor) plus corpus-pinned report,
  group-record and exact-decode facts.
* `docs/rvsdly-22b-23c-crosscheck-study.md` (new): the study note.

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  python tools/rvsdly_22b_23c_crosscheck.py local/zen_arm64` — stored bytes
  `0x22b=2ff000` (0.99609375), `0x23c=aff800` (-0.998046875), each exactly its
  own constructor double; groups `a43860`/`a43840` count 1 with single records
  `424b/22b/3` and `425c/23c/3`, sole references `0x2c2638`/`0x2c2618` inside
  `SetAlg 0x2c2508..0x2c2740`; `9dfa50` still the only count>=2 group.
* `SetAlg` has exactly six slot-c8 calls (descriptors `0xa430840..0xa4308e0`,
  arguments `d9, d10, d8, d9, d10, #1.0`); the first two write the two fields
  with `d0=-d8` and `d0=d8*d10+d11`, so the fields differ by construction.
* Exactly one strict-decoder control selects each field across the whole
  program: packet `0x22e` header `0x2b09` families `[0,4,4]` long-op literal
  `0xca6/5fe2` -> `0x23c` = -0.998046875; packet `0x21e` header `0x2e08`
  families `[1,1,4]` short control `0x34e5` -> `0x22b` = 0.99609375.
* Negative controls: mutating one stored triple byte or one descriptor record
  byte makes the tool exit 2.
* `python -m unittest discover -s tests -p test_rvsdly_22b_23c_crosscheck.py`:
  7 tests, OK. Neighboring suites unchanged: `test_gassdly_62_trap.py`,
  `test_line_prefix_single_writer.py`, `test_header_family_crosscheck.py`,
  `test_header_study.py`, `test_short_add_context_study.py` each OK.

Established: the GASSDLY grouped-write reading is not an artifact of grouped
equality — in a second program the same relative fields are independently owned,
written with different computed values, and each is selected by exactly one
strict-decodable control whose literal equals that field's own constructor
default. Unknown: DSP execution of these controls (static evidence only), other
writers/builds, the arithmetic roles of `0xca6`/`0x5fe2`/`0x34e5`, the fitted
`62` family roles (run 4 unchanged), and the unexamined neighbor fields
`0x60`/`0x71`. No opcode, family or interpreter admission.

Best next item: run 6+7 remove both structural objections to the `62` family
proof; the smallest remaining step is native — bind the GASSDLY/GASSPH/GAMPSIM
`5d52` chains (or the `6209` packet's `9450/ded4/8fe2` roles) to native cutpoints
through the now twice-corroborated field reading, using the existing
`native_callback_fixture` style; if that exceeds one run, cross-check the
`0x60`/`0x71` RVSDLY fields or a `4b`/`5c` miscellaneous slot instead.

## Run 8 — 2026-11-13: RVSDLY 60/71 second pair corroborates the reference reading; run 7 aside corrected

Item chosen: the instruction-semantics fallback run 7 left as next — cross-check
the unexamined RVSDLY neighbor fields `0x60`/`0x71`, which hold the same doubles
as `0x22b`/`0x23c`, against the same four-part proof shape (constructor pair,
exact stored bytes, count-1 SetAlg ownership, unique strict-decoder control).
The native `5d52` cutpoint binding remains the preferred next item and was left
in place because it needs native-execution fixtures beyond one run.

Files:

* `tools/rvsdly_60_71_pair_crosscheck.py` (new): pins the double-copy field sets
  `{0x60,0x22b}`/`{0x71,0x23c}`, both constructor pairs, the count-1 width-3
  SetAlg groups `0xa438c0`/`0xa438a0` with their sole code references, the
  skipped-oversized-window ADRP sweep, the SetAlg call arguments, the exactly-one
  strict-decoder control per field, and the GASSDLY contrast (other values, no
  constructor pair, no strict control). Zero decoder changes.
* `tests/test_rvsdly_60_71_pair_crosscheck.py` (new): 10 tests — synthetic
  fail-closed checks on the real packet-0x56/0x64 byte shapes, exact-value
  stored-window matching, and corpus-pinned report, ownership, contrast,
  run-7-unchanged and fail-closed constructor facts.
* `docs/rvsdly-60-71-pair-crosscheck-study.md` (new): the study note.
* `docs/rvsdly-22b-23c-crosscheck-study.md`: corrected run 7's untested aside —
  `0x60`/`0x71` ARE selected by strict-decoder controls of their own; the
  by-offsets-not-values discrimination point is unchanged.

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  python tools/rvsdly_60_71_pair_crosscheck.py local/zen_arm64` — stored
  `0x60=2ff000`/`0x71=aff800`, double-copy sets exactly `{0x60,0x22b}`/
  `{0x71,0x23c}`, constructor pairs object `0x1b0`/`0x1a0` with doubles
  `0.99609375`/`-0.998046875` (44 pairs total), groups `0xa438c0`/`0xa438a0`
  count 1 with sole references at SetAlg ADDs `0x2c268c`/`0x2c2670`, calls
  `0x2c2694` (`d0, d10`) and `0x2c2678` (`d0, d9`), exactly one strict control
  each (packet `0x56` `0x34e2` -> `0x60`; packet `0x64` `0xc24` -> `0x71`),
  GASSDLY `0x60`=`3fe28f`/`0x71`=`080c64` with no constructor pair and no
  strict control.
* Fail-closed negatives (one-bit image mutations, hash re-patched so identity
  does not pre-empt): stored triple bytes (`0x820e38+0x60/+0x71`), control
  literal byte (packet `0x64`), group record bytes (`0x821808`, `0x8217fc`,
  width byte included) and a SetAlg ADD immediate (`0x2c268c+3`) each raise
  `ValueError`. The program byte space is word-reversed (`lib.be`), so naive
  file-offset mutations were first off by three bytes and did not fire; corrected.
* `python -m unittest discover -s tests -p test_rvsdly_60_71_pair_crosscheck.py`:
  10 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus).
* Neighboring suites unchanged: `test_rvsdly_22b_23c_crosscheck.py` 7 OK,
  `test_gassdly_62_trap.py` 7 OK, `test_header_family_crosscheck.py` 7 OK,
  `test_line_prefix_single_writer.py` 9 OK, `test_header_study.py` 9 OK.

Established: the reference reading now holds for two independently owned,
differently-valued field pairs in RVSDLY through both strict syntax forms, with
exact constructor/stored/strict-control agreement in each, plus a cross-program
contrast showing the pairing is program-local. Run 7's "neither field selected"
aside is corrected with evidence. Unknown: DSP execution, why the program keeps
two copies, other writer groups for `0x60`/`0x71` (widths 2/4, functions bounded
but unnamed), arithmetic roles of `0x34e2`/`0xc24`, other builds. No opcode,
family or interpreter admission.

Best next item: unchanged from run 7 — the native `5d52` cutpoint binding
(GASSDLY/GASSPH/GAMPSIM chains or the `6209` packet's `9450/ded4/8fe2` roles)
through `native_callback_fixture`; it has now survived two structural
cross-checks. If one run is still too small, the next static fallback is naming
the writers of the other `0x60`/`0x71`/`0x22b`/`0x23c` declaring groups.

## Run 10 — 2026-11-13: adopted and finished the uncommitted 5e09 cross-image inventory; three draft claims corrected

Item chosen: the instruction-semantics lane — the worktree held uncommitted
drafts (`tools/five_e09_inventory.py`, `tests/test_five_e09_inventory.py`,
`docs/five-e09-inventory-study.md`) resolving the standing unknown from
`negative-short-add-study.md`: the four `5d52` uses under unresolved header
`5e09`. Following the run-2 pattern, this run verified, corrected, tested and
committed them rather than starting a new item; the drafts were not yet
evidence because nothing in them had been run or recorded.

Files:

* `tools/five_e09_inventory.py` (new): fail-closed inventory of every `5e09`
  packet across the pinned ZENOLOGY arm64 image, both Fantom CORE1 payloads and
  the three cross-model QSPI containers via the existing `analyze.core_lists()`/
  `qspi_c1.read_c1()` framing; four known control shapes, unknown shapes fatal;
  GASS-type per-packet invariants (gain 1.75, bias -0.25, resource offsets 4/6).
* `tests/test_five_e09_inventory.py` (new): 8 tests — synthetic fail-closed
  shape/framing/literal checks plus corpus-pinned totals, per-image counts,
  b0c1a stride `0x5f0`, dsp6 diagnostic payload/offset floor and byte-exact
  GASS anchor payload.
* `docs/five-e09-inventory-study.md` (new): the study note, with a run-10
  verification transcript pasted verbatim (owner direction of 2026-11-13).

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  python tools/five_e09_inventory.py` — totals 117 `5e09` packets over 2,535
  strictly framed segments (135 more counted unframeable, not fatal): GASS-type
  28, SBF325-type 56, STTMDLY-type 28, dsp6 diagnostic 5; per image zen 8,
  b0c1a 17, b1c1a 1, MI077 45, RPG69 1, DD013 45; 26 distinct GASS resource
  pairs over 28 observations.
* Draft corrections (each re-checked with a fresh command before editing):
  (1) "117 framed scans" — the tool frames 2,535 segments, of which 117 contain
  the packets; note now states 2,535/135. (2) the zen anchor segment was
  described as "segment `0x817988`" — that is the stored source offset; the
  program base is `0x4020` with length `0x5ec`; note now names both. (3) "best
  header-sequence agreement: GASSDLY 45/80" — verified same-position header
  counts are GASSDLY `0x9de948` 3 of 80 and next best `0xa2cc28` 5 of 80, so
  no number near 45/80 exists; note now carries the measured counts.
* Neighborhood claim re-verified: the zen `0xa41220` 4-packet window and the
  JUPITER-X MI077 placement (base `0x2020`, source `0x17621c`) are
  packet-for-packet identical in controls (`b04b ... b08d ... 5e09 ... 2308`)
  with differing resource words, hexdumps pasted into the note.
* b0c1a GASS placements: bases `0x4020/0x8040/0x9040/0xa040`, sources
  `0x1334c8+0x5f0*k`, resources `(0xd,0x13f) (3,0x35f) (0x25,0x3f5) (0x47,0x48b)`
  — the note's stride and pair claims hold.
* dsp6 diagnostic: one packet each in b0c1a/b1c1a/MI077/RPG69/DD013, payload
  `0004d000002de000` constant, offsets `0x1964/0x1776/0x16e0/0x1324/0x1788`;
  b1c1a and MC-101 have no other `5e09` — as the note claims.
* `header_study.families(0x5e09)` raises `UnsupportedLayout`; `families(0x4709)`
  returns `(0,0,4,4)` — decoder unchanged, fail-closed confirmed.
* `6698528` (`0xa41220`) absent from `local/pairs.json` and `labels` — the
  desktop-identity negative holds.
* Fail-closed mutation check: single-bit flips at the stored gain/bias literal
  bytes (`0x817988+0x290/0x291/0x297`) each raise
  `ValueError: 0x288: gain/bias literal ... is not ...`.
* `python -m unittest discover -s tests -p test_five_e09_inventory.py`: 8
  tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring suites
  unchanged: `test_header_family_crosscheck.py` 7 OK, `test_header_study.py`
  9 OK.

Established: complete `5e09` coverage across six images (117 packets, four
shapes, no unknown combination); the GASS-type invariants per packet and image;
the count-formula and 9-word length pinned; the `5d52` control coexists with
`1e50` selecting 1.75 exactly as in the admitted `2e07` chains, across 28 uses
in four independent images. Unknown: the operand syntax of `4014`/`4010`
(presumed kind-3 slot), whether `5d52` adds in these contexts, the fitted
`(1,1,3,4)` prediction for `0x5e` (consistent but not discriminated), the GASS-
type program's desktop identity, other builds. No opcode, family or interpreter
admission.

Best next item: the structural ground for the `62`/`5e` families is now as
complete as static analysis gets without native execution; the next run should
attempt the native `5d52` cutpoint binding (GASSDLY/GASSPH/GAMPSIM chains, or
the `6209` packet's `9450/ded4/8fe2` roles) through the existing
`native_callback_fixture` style, or, if that still exceeds one run, the bounded
4b/5c miscellaneous-slot cross-check named in the review follow-ups.

## Run 11 — 2026-11-13: fitted 4b/5c slot ordering survives the corpus-wide transfer-marker cross-check

Item chosen: the review-follow-up bounded 4b/5c miscellaneous-slot cross-check
(the static fallback runs 4, 8 and 10 left standing; the preferred native
`5d52` cutpoint binding needs native-execution fixtures, which this run's
static-analysis-only rules exclude). Run 4 proved only that `4b`/`5c` fail
closed; this run added the corpus-decidable positional check: a full census of
all 38,441 fitted count-4 packets in six images plus a `fe0..fee`-window
transfer-marker invariant calibrated on the admitted anchor syntax and the
count-1 classes `08..0c`. Taken from the review follow-up B list and run 10's
"best next item"; no earlier item was repeated.

Files:

* `tools/four_b_five_c_crosscheck.py` (new): reuses
  `header_family_crosscheck.ranked_choices()` and the existing
  `analyze.core_lists()` framing; records per-slot control vocabularies and
  window statistics for all fitted count-4 packets and count-1 classes
  `08..0c`; raises on any window control outside a transfer-predicted slot
  (except the pinned `62`/`6fe4` slot-0 trap), on `4b`/`5c` window sets other
  than `[]`/`[3]`, on any `5a` window control, and on count-1 `08..0b` window
  use. Zero decoder changes.
* `tests/test_four_b_five_c_crosscheck.py` (new): 13 tests — synthetic
  fail-closed invariant checks (window into anchor long/short slot, extra window
  control, `5a` window control, `4b` window in slot 2, count-1 calibration
  change, truncated-packet framing) plus corpus-pinned totals, calibration,
  vocab crosscheck and per-image counts.
* `docs/four-b-five-c-slot-crosscheck-study.md` (new): the study note, with the
  trimmed tool output pasted verbatim (owner direction of 2026-11-13).
* `local/four-b-five-c-run11.json` (ignored local storage): the run's tool
  output the tests read back.

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  python tools/four_b_five_c_crosscheck.py` — 38,441 fitted count-4 packets
  (27,138 strictly decoded, 11,303 unsupported, 0 framing-rejected), 2,257
  `4b`/`5c` packets of which 1,520 carry exactly one window control in slot 3
  and 737 none; 276 `5a` packets with zero window controls; the only window
  control outside a transfer-predicted slot corpus-wide is the known
  `6209 6fe4 ...` slot-0 trap (28 occurrences, all one control shape);
  count-1 calibration 43,939 controls with 7,579 window uses, all in class
  `0c` (16 distinct window words), `08/09/0a/0b` zero.
* Long/short vocabulary discrimination: count-1 `08` and `09` control
  vocabularies overlap in only 6 words; `4b` slot 0 contains 4 long-only and 0
  short-only words, `5c` slots 0..1 contain 22 short-only and 5 long-only —
  both directions agree with the fitted assignment.
* The 737 non-window `4b`/`5c` slot-3 controls (`b9b3` class, 16 distinct)
  never appear as any count-1 `08..0c` control.
* All six image hashes re-pinned before use; per-image fitted counts equal run
  4's recorded totals (scan base unchanged).
* `python -m unittest discover -s tests -p test_four_b_five_c_crosscheck.py`:
  13 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring
  suites unchanged: `test_header_family_crosscheck.py` 7 OK,
  `test_header_study.py` 9 OK, `test_five_e09_inventory.py` 9 OK,
  `test_gassdly_62_trap.py` 7 OK, `test_rvsdly_22b_23c_crosscheck.py` 7 OK.
* Every pinned number in the note re-checked against the tool JSON before
  commit; the one arithmetic slip (count-1 total written 43,739, actual 43,939)
  was fixed in the note before commit. No earlier note needed correction.

Established: the fitted rule's slot ordering — not just its multiset — is now
consistent with every transfer-marker statistic the corpus exposes; nothing in
six images puts a transfer-looking control outside a transfer-predicted slot,
and the one exception is the known `62` trap, which now carries a sharpened
statement: `6fe4` looks transfer-like while the fit calls slot 0 of `62` short,
so either the marker does not extend to unadmitted syntax or the fitted `62`
ordering is wrong. Unknown: what `4b`/`5c` slot 2 and the `b9b3` class do,
whether the window marker is causal across unadmitted syntaxes, `5a`/`62` slot
semantics, other builds. No opcode, family or interpreter admission.

Best next item: unchanged — the native `5d52` cutpoint binding
(GASSDLY/GASSPH/GAMPSIM chains or the `6209` packet's `9450/ded4/8fe2` roles)
through `native_callback_fixture`, now with this run's positional evidence in
hand; if native execution exceeds one run again, the next static fallback is
profiling the `b9b3`-class controls' co-occurrence contexts to bound what the
fitted miscellaneous slot can be doing.