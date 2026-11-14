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
* `tests/test_five_e09_inventory.py` (new): 9 tests — synthetic fail-closed
  shape/framing/literal checks plus corpus-pinned totals, per-image counts,
  b0c1a stride `0x5f0`, dsp6 diagnostic payload/offset floor and byte-exact
  GASS anchor payload (count corrected from 8 by the run 12 review).
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
* `python -m unittest discover -s tests -p test_five_e09_inventory.py`: 9
  tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus; count corrected
  from the originally recorded 8 by the run 12 review — the committed file
  had 9 `test_` methods from the start, and run 11's log already recorded
  "test_five_e09_inventory.py 9 OK"). Neighboring suites unchanged:
  `test_header_family_crosscheck.py` 7 OK, `test_header_study.py` 9 OK.

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
## Run 12 — 2026-11-13: review pass; three most recent notes re-verified, run 10 log test count corrected

Item chosen: item C, the every-fourth-run review pass. The three most recent
study notes on this branch are `docs/four-b-five-c-slot-crosscheck-study.md`
(run 11), `docs/five-e09-inventory-study.md` (run 10) and
`docs/rvsdly-60-71-pair-crosscheck-study.md` (run 8). Every stated command in
each note was re-run in this worktree with the pinned interpreter
`/Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python`, and
every address/offset in each note was re-checked against the tools' fresh JSON
and the tests' anchors. No note's analytical content changed; one earlier log
entry's test count was corrected.

Verified this run (all commands and outputs in the transcript):

* Run 11 tool re-run:
  `BMC_CORPUS_DIR="$PWD/local" PYTHONPATH=local/fantom-python:tools python
  tools/four_b_five_c_crosscheck.py` — exit 0; the fresh JSON's `totals`
  match the note's pasted block field for field (38,441 fitted / 27,138
  decoded / 11,303 unsupported / 276 `5a` / 306 `62` / 28 slot-0-trap /
  2,257 `4b5c` = 1,520 + 737 / calibration 43,939 with 7,579 window, all
  class `0c`), and the per-image `4b`/`5c` counts 152, 316, 61, 801, 117,
  810 match the note's prose. `python -c` field-by-field comparison against
  `local/four-b-five-c-run11.json`: 0 differing fields.
* Run 10 tool re-run: `python tools/five_e09_inventory.py` — exit 0; fresh
  JSON identical to `local/five-e09-inventory.json` (0 differing fields):
  totals 117 `5e09` / 2,535 framed / 135 unframeable / shapes 28/56/28/5 /
  26 distinct GASS pairs; per-image shapes match the note's table (zen 8 =
  2/4/2/0, b0c1a 17 = 4/8/4/1, b1c1a 1 = 0/0/0/1, MI077 45 = 11/22/11/1,
  RPG69 1, DD013 45); the five dsp6 diagnostic offsets `0x1964/0x1776/0x16e0/
  0x1324/0x1788` re-read from the fresh JSON equal the note's record.
* Run 8 tool re-run:
  `python tools/rvsdly_60_71_pair_crosscheck.py local/zen_arm64` — exit 0;
  every address in the note matches the fresh JSON: stored
  `0x60=2ff000`/`0x71=aff800`, double-copy sets `{0x60,0x22b}`/`{0x71,0x23c}`,
  constructor pairs object `0x1b0`/`0x1a0` with doubles `0.99609375`/
  `-0.998046875` at `+0x1b8`/`+0x1a8`, groups `0xa438c0`/`0xa438a0` count 1
  with records `0x4080`/`0x4091`, SetAlg ADDs `0x2c268c`/`0x2c2670`, calls
  `0x2c2694` (`d0, d10`)/`0x2c2678` (`d0, d9`), peer groups `0xa43860`/
  `0xa43840` at calls `0x2c2640`/`0x2c2620`, strict controls packet `0x56`
  header `0x2e07` `0x34e2` and packet `0x64` header `0x1408` `0xc24`, and
  the GASSDLY contrast `3fe28f`/`080c64`. `header_study.families(0x2e07)` =
  `(1,1,4)` and `families(0x1408)` = `(0,4)` re-confirmed directly.
* All six image hashes re-hashed with `shasum -a 256`; all equal the run 11
  note's pinned values (zen `b8ba7…c30`, b0c1a `6d954…3154`, b1c1a
  `c8d150…68bd`, MI077 `9368e…567b`, RPG69 `6de1e…2a21`, DD013
  `57466…cadf`).
* Suites re-run (`BMC_CORPUS_DIR="$PWD/local"
  PYTHONPATH=local/fantom-python:tools:tests python -m unittest discover -s
  tests -p <name>`): `test_four_b_five_c_crosscheck.py` 13 tests OK,
  `test_five_e09_inventory.py` 9 tests OK, `test_rvsdly_60_71_pair_crosscheck.py`
  10 tests OK, `test_rvsdly_22b_23c_crosscheck.py` 7 tests OK,
  `test_gassdly_62_trap.py` 7 tests OK, `test_header_family_crosscheck.py`
  7 tests OK, `test_header_study.py` 9 tests OK.
* One correction made: run 10's log entry said its new suite had "8 tests";
  the committed `tests/test_five_e09_inventory.py` has contained 9 `test_`
  methods since commit `496cb5c`, and this run's fresh execution ran 9. Run
  11's log entry already recorded "test_five_e09_inventory.py 9 OK", so the
  8 was a transcription slip in run 10's log text only; both log lines now say
  9. No study note needed a change: no address, offset, count or hash in the
  three notes failed re-verification.

Remaining unknown: unchanged — nothing in this pass produces new semantic
evidence; the review's job was to confirm that existing evidence still
reproduces from the committed tools and pinned corpus. The one process note
from the run: the RVSDLY suites fail with import errors when `tests` is
omitted from `PYTHONPATH`; the notes' reproduce blocks already include it.

Best next item: unchanged from runs 8/10/11 — the native `5d52` cutpoint
binding (GASSDLY/GASSPH/GAMPSIM chains or the `6209` packet's `9450/ded4/8fe2`
roles) through `native_callback_fixture`; if native execution exceeds one run,
the next static fallback is profiling the `b9b3`-class controls' co-occurrence
contexts to bound what the fitted miscellaneous slot can be doing.

## Run 13 — 2026-11-13: program-RAM read path mapped; ReadDspProg exists but has no static caller

Item chosen: lane A1, the load route — the first open item in the owner's
2026-11-13 feasibility order ("load a foreign program and read it back"). The
instruction-semantics lane's preferred next step (the native `5d52` cutpoint
binding, first choice of runs 8/10/11/12) needs native-execution fixtures, which
this run's static-only rules exclude, and runs 2-12 already covered that lane.
The write half of the load route was already mapped (`program_write_study.py`,
`kernel-audio-abi-study.md`); this run mapped the read half and its coupling.

Files:

* `tools/program_read_study.py` (new): models `CBmcDspDrv::ReadDspProg`
  (0x0112f74c) — raw_head/full_word_tail/bulk step order, shared DMA list,
  4095-word descriptors, synchronous completion wait — and `ReadLiteralRaw`
  (0x0112f6e8) widths 2/3/4 with the alignment shift; pins 10 function entries,
  27 instruction anchors, the aperture table (0x113a954), the raw/fixed/float
  port tables (0x113aa74/58/3c), the data-memory kind table (0x113aac0) and the
  capacity pointer table (0x113aaf0), and the four direct `ReadLiteralRaw` call
  sites; `--dsp/--address/--count` emit a sample geometry. Zero decoder changes.
* `tests/test_program_read_study.py` (new): 10 tests — synthetic fail-closed
  geometry (odd/unaligned/oversize inputs, bulk-at-word+2 rejection, threshold
  after edges, widths 0/1/5 rejected via the unsigned comparison) plus
  corpus-pinned anchors, shared aperture table, exactly-four call sites, the
  `ReadDspProg` no-caller negative and a one-bit-flip fail-closed check.
* `docs/program-read-path-study.md` (new): the study note, with the trimmed tool
  output pasted verbatim (owner direction of 2026-11-13).

Verified this run (commands and outputs in the transcript):

* Tool exits 0:
  `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python
  tools/program_read_study.py local/b0c1a.bin --dsp 4 --address 0x4020 --count 510`
  — 510-byte read at 0x4020 = full word at 0x422c first, then 508 queued bytes /
  127 words, 128 words returned; port command 0x20004020; literal sample
  (width 2, no shift) command 0x20004021.
* Read ordering established from the disassembly (`tools/core1.py` listings in
  the transcript): the leading raw halfword fires on the *address* bit 1
  (`tst.w r6, #2` at 0x0112f7a0), the trailing **full** word on the *remaining
  count* bit 1 (`tst.w r5, #2` at 0x0112f7da) and is stored unshifted
  (`str r0, [r8, r4, lsl #2]` at 0x0112f872 — the `lsr` at 0x0112f7ce belongs to
  the leading path); the leading halfword shifts right 16
  (`rsb.w/lsl/lsrs` at 0x0112f7c6..ce). Write-path contrast: `bfc r3, #0, #0x10`
  at 0x0112f620 clears the low half so writes never disturb bytes past the count,
  while reads return the whole final word.
* The bulk path shares the write machinery: threshold `cmp r5, #0x40` at
  0x0112f878 applies to the remainder after the edges; `DSP_listed_memcpy`
  (0x0112f290) requires all three arguments 4-aligned (`tst r3, #3` at
  0x0112f298), so a bulk read from a word+2 address would assert — the model
  rejects it. The copy is byte-count-preserving (0x0112f8a4 passes r2=r5, r1=r6).
  Sub-64 remainders take the sequential CPU word loop at 0x0112f8ea..f26.
* Synchronous completion: after queueing, the reader polls state 2/event bit 4
  (0x0112f8d6..e4) before resetting state 0; idle state 0 also starts the list
  through 0x0112f3ba and waits. Same completion callback 0x0112f42d and state
  byte 0x200847f0 as the write path (pool words 0x112fc74/78).
* `ReadLiteralRaw`: unsigned `(width-2) < 3` at 0x0112f702; command
  `(width<<28)|(addr&0x7ffff)` via `ubfx/orr` at 0x0112f71a..26; busy-wait on
  0x41100008 bit 31; align_right false returns unshifted for every width
  (`cmp r3, #0; it eq; popeq` at 0x0112f73c..40), true shifts by `(4-width)<<3`
  (width 3 = 8 bits). Port tables word-verified: raw 0x113aa74 =
  41104700/.../41102700, fixed 0x113aa58, float 0x113aa3c — the same ports the
  write path uses, so bit 29 distinguishes these read commands from the write
  commands on the same ports; bounded to these two families (live-slot
  `WriteDspCoefFloatWithEnv` commands clear bit 29).
* Data-memory readers mapped: kind table 0x113aac0 = six port tables
  (0x113acb8/d60/e08/e40/be0/c10), bases 414/415/.../412-series with kind 3 =
  0x4113c000; capacity pointers 0x113acd4/ad7c/e24/e5c/bf8/c2c = 2048/2048/1536/
  256/512/1024 per DSP; kinds 2/4 have a 0 DSP-6 row; kind 4's table at
  0x113abf8 reads 512 x6 then two float-bit words (not capacities). Kinds 0/1
  branch before the general dispatch (0x011302a2..a8).
* Exactly four direct BL callers of `ReadLiteralRaw` (halfword scan):
  0x01133bb4/0x01133bda in `SetMuteMode` (0x01133b38), 0x01133220 in the
  program-literal method starting 0x011330ae (assertion
  `CBmcDspMgr::ChangeDspMemoryAdrs` 0x610ba092; helper `GetDspProgByteAdrs`
  0x610b98f3), 0x01133698 in the DRAM-IO address-change method starting
  0x0113353c (assertion `CBmcDspMgr::ChangeDramIO_RW_Adrs` 0x610ba163; helper
  `GetDramioProgByteAdrs` 0x610b9943).
* `ReadDspProg` has no direct BL/B, no MOVW/MOVT/BX veneer and no thumb-pointer
  word anywhere (`tools/core1_xrefs.py local/b0c1a.bin 0x0112f74c` — all three
  candidate lists empty; halfword scan for 0x0112f74d empty).
* Every address in the note re-checked against image bytes before commit:
  10 function entries' bytes, pool words 0x112fc74/78, 0x112f854/4c, 0x1130130/38,
  shift/bfc instruction bytes, kind/capacity pointer words, capacity values,
  port first words, listed-memcpy caps 0xffe/0xfff, bulk threshold 0x40 — all
  verified by the two `python - <<'PY'` sweeps in the transcript.
* `python -m unittest discover -s tests -p test_program_read_study.py`: 10
  tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring suites
  unchanged: `test_program_write_study.py` 8 OK, `test_kernel_abi.py` 5 OK.

Established: the stock driver can read program RAM back through the same
apertures and ports it writes, synchronously, with geometry that mirrors the
write path's edge rules; `SetMuteMode` proves in-the-manager program-window
reads return loaded program content. The route is missing exactly two edges:
no static caller invokes `ReadDspProg` in this image (so no manager/service
readback flow is named), and no host route reaches it (the missing external
peer). Unknown: silicon behavior of the read ports, the real size of the
program-RAM window beyond the modeled 0x80000, the kind-0/1 2048 driver bound
versus the envelope study's per-DSP 1024-word bank sizes (unreconciled, stated
as unreconciled in the note), whether any caller uses width-3 align_right, and
other builds. No opcode, family or interpreter admission.

Best next item: lane A1's remaining gap is now precise — find the
manager/service caller of `ReadDspProg` by xrefing its computed-call paths
(vtable scan of ERAM pools for 0x0112f74d found nothing, so the next step is
scanning the initializer/scatter tables), or advance to A5 (wave memory and
interpolation instructions), the owner's least-mapped and highest-value lane;
A2 (program reservations/unused slots) is also open. The static-analysis
fallback from the instruction-semantics lane remains the `b9b3`-class context
profile.

## Run 14 — 2026-11-13: ReadDspProg caller census exhausted; both CORE1 images carry an unreferenced program-read twin

Item chosen: lane A1 continuation, the precise gap run 13 named — find the
manager/service caller of `ReadDspProg` by scanning the remaining computed-call
paths (initializer/scatter tables). Taken as the only bounded static step left
in the owner's first-priority lane (load route + readback); either outcome was
provable: a found caller names the stock readback flow, an exhausted search is
a verified negative. The instruction-semantics lane's preferred native
`5d52` cutpoint binding still needs native-execution fixtures, excluded by this
series' rules.

Files:

* `tools/read_dspprog_caller_census.py` (new): locates the ReadDspProg twin in
  either pinned CORE1 payload by build-independent prologue shape (push
  {r4-r8,lr} / mov r8,r3 / cmp r0,#7 / orr.w r3,r1,r2 / tst.w r3,#1), asserts
  value-identical aperture and raw-port tables per image, asserts each twin's
  own DMA-state-byte pool word, and exhausts seven static reference forms:
  direct BL/B, MOVW/MOVT/BX veneer, aligned Thumb pointer words, MOVW/MOVT
  constructor pairs, PC-relative ADR (add/add.w/addw/sub/sub.w/subw with pc
  operand), stored words equal to target or target|1 anywhere in the payload,
  and words inside the *expanded* compressed initial-data image (reusing
  `core1_wait_study.expand_initial_data` unchanged). Per-image scanner liveness
  anchors make an empty result meaningful; any hit or anchor failure exits 2.
* `tests/test_read_dspprog_caller_census.py` (new): 10 tests — synthetic
  fail-closed fixtures built from real image bytes this run (prologue bytes
  dumped at 0x0112f74c; MOVW/MOVT pair bytes from 0x1134380; add.w bytes from
  0x112e74e), planted-pointer detection in stored and expanded regions with
  one-bit-mutation negatives, plus corpus-pinned twin location in both images,
  table identity, exhaustively-empty census, report pass/fail-closed and pinned
  expansion sizes.
* `docs/read-dspprog-caller-census-study.md` (new): the study note, with both
  tools' full outputs pasted verbatim (owner direction of 2026-11-13).

Verified this run (commands and outputs in the transcript):

* Tool exits 0 on both images:
  `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  .venv/bin/python tools/read_dspprog_caller_census.py b0c1a` — twin at
  `0x0112f74c` (equals run 13's pin), all seven scanner families `[]`,
  expanded `0x478c` bytes / `0x1f43` consumed; `... b1c1a` — twin at
  `0x0112f394`, all seven `[]`, expanded `0x4710` / `0x1c47`.
* b1c1a twin identity: prologue-identical (disassembled this run), aperture
  words `41480000 41580000 41680000 41780000 41880000 41980000 41260000` and
  raw-port words `41104700 ... 41102700` value-identical to b0c1a's at its own
  addresses `0x113b1b4`/`0x113b2d4`, own pool word `0x112f8bc` =
  `0x20084774`.
* State-byte sharing: in each image exactly one distinct DMA state byte
  (`0x200847f0` b0c1a / `0x20084774` b1c1a) is referenced by 18 literal-pool
  loads spanning the DMA driver family around the twins; for b0c1a the write
  path is inside that referenced range (run 13's write study) and the b1c1a
  range mirrors it positionally, but this run did not name each b1c1a
  referencing function individually.
* Scanner-liveness process note: the first tool version's ADR scanner was
  dead — Capstone names the PC-relative T3 form `addw`, not `add.w` — and its
  MOVW/MOVT pair scanner read the MOVT halfword at +2 instead of +4 (found 0
  candidate pairs; 323 exist in b0c1a's low region). Both bugs were found by
  the synthetic tests, fixed, and the committed tool asserts per-image liveness
  anchors (b0c1a: `add.w r6, pc, #0x204` at `0x112e74e` -> `0x0112e954`; pair
  at `0x1134380` -> `0x61015b77`; b1c1a: `addw` at `0x110165e` ->
  `0x01101a14`; pair at `0x1133ffc` -> `0x61070181`), so the final empty
  results come from proven-live scanners.
* Every address in the note re-checked against live image bytes and the tests'
  anchors before commit (prologue bytes, pool words, anchor instruction bytes
  and sums, reset-entry Thumb bits, xref emptiness): all pass.
* `python -m unittest discover -s tests -p test_read_dspprog_caller_census.py`:
  10 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring
  suites unchanged: `test_program_read_study.py` 10 OK,
  `test_program_write_study.py` 8 OK, `test_core1_wait_study.py` 5 OK. (The
  repo's pinned venv has no pytest; unittest discover per the README.)

Established: the stock bmc0 and bmc1 CORE1 images each contain a sound
program-RAM read primitive and in neither image does any enumerable static
reference name it. Run 13's "no static caller found" is strengthened to "no
reference of any scannable kind, in either image, with scanner liveness proven
per image and per form". For A1's "read it back", the remaining unknowns are
exactly: (1) how execution reaches `ReadDspProg` — only a computed call whose
address is assembled by arithmetic on data (e.g. base + 4*index) could invoke
it, and this census proves no static materialization exists; (2) the missing
external peer to carry a readback request. Readback-for-verification in the
first custom-voice milestone therefore depends on a resident CORE1 bridge
calling the driver directly, or hardware observation; the write route alone is
fully mapped. Unknown: derived-address invocation (not statically
excludable), the byte-level difference between the two twins (structural
identity only — prologue, tables, pool), other builds.

Best next item: lane A1 is now closed to the static limit; per the owner's
order advance to A5 (wave memory and interpolation — which instructions read
sample/wave memory and DRAM-IO, their formats, and how stock sample playback
interpolates), the least-mapped and highest-value lane for the sample-playback
target. If A5 needs a scoping run first, A2 (program reservations: which
program slots/contexts exist, who owns each, whether any is unused in the
stock image) is the next bounded static item. The instruction-semantics
fallback remains the `b9b3`-class context profile.

## Run 19 — 2026-11-13: program-slot census adopted and finished; every stub-only slot backed by exactly one boot-stub segment record

Item chosen: lane A2 (program reservations), the next open item in the
owner's 2026-11-13 feasibility order after run 14 closed A1 — which program
slots/contexts the stock image declares and fills, who owns each at the list
level, and whether any receives only the boot stub. The worktree held
uncommitted drafts of the census tool and two stored JSON outputs but no
test, no note and no recorded run, so nothing in them was yet evidence; this
run verified, extended, tested and committed them (run 2/run 10 pattern).
The instruction-semantics lane's preferred native `5d52` cutpoint binding
still needs native-execution fixtures, excluded by this series' rules.

Files:

* `tools/program_slot_census.py` (new, from the draft): frames every render
  program list with the `analyze.core_lists()` predicates (count bound
  relaxed to 64, checked to frame identically at 16), classifies each framed
  segment's stored bytes as `stub`/`packet`/`data` via the admitted packet
  subset, checks the framing-liveness invariant (exactly one stored u32
  reference per framed list), cross-checks the five pinned b0c1a MFX
  reservations, reads the pinned b1c1a 20-row table at `0x610a4f20`, and
  enforces the new invariant: every stub-only slot's `{base, 6, capacity}`
  segment record appears exactly once and its source holds the pinned
  boot-stub record `f800020b00000100`.
* `tests/test_program_slot_census.py` (new): 14 tests — synthetic fail-closed
  checks (stub record byte pins, classify shapes, framing predicates,
  record-census raise paths, kernel-abi reservation pins) plus corpus-pinned
  censuses for both images, pinned record addresses, table rows, and a
  duplicate-record mutation that must raise.
* `docs/program-slot-census-study.md` (new): the study note, with both
  tools' trimmed outputs pasted verbatim (owner direction of 2026-11-13).

Verified this run (commands and outputs in the transcript):

* Tool exits 0 on both re-hashed payloads
  (`PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  .venv/bin/python tools/program_slot_census.py {b0c1a,b1c1a}`):
  b0c1a 103 lists / 32 slots / stub 16 + packet 361 + data 0 / 6 stub-only
  slots (dsp4 0x4020/0x5020/0x6020/0x6420, dsp5 0xe840/0xfc40); b1c1a 104
  lists / 51 slots / stub 26 + packet 1606 + data 1 / 19 stub-only slots
  (17 dsp4 at 0x700 capacity, dsp5 0xe000/0xe800).
* Every stub-only slot is backed by exactly one 6-byte segment record
  `{base, 6, capacity, source}` whose source holds the pinned record:
  b0c1a records `0x610a8bfc/0c/1c/2c` + `0x610b0d40/d50` with sources in the
  5-record array `0x610a8bc4..0x610a8be8` and the 11-record array
  `0x610b0c58..0x610b0cac`; b1c1a 17 dsp-4 records at
  `0x610a9000..0x610a9100` (stride 16) plus dsp5 `0x610afcec/fc`. All 25
  records re-verified field-for-field against image bytes this run.
* The `{base, 6, capacity}` shape is the framed segment record format itself;
  the fourth word is the segment's stored source.
* b1c1a's pinned 20-row table at `0x610a4f20` was compared raw with
  `struct.iter_unpack`: 20 distinct `{base, 0x700}` pairs; 16 of the 20 bases
  are the stub-only dsp4 slots (the 17th, `0xb120` at `0x1000`, is not in
  the table), the other 4 (`0xa000/0xa700/0xae00/0xb500`) are dsp5 slots with
  both a stub and real packet content.
* The four FETDRIVE-family reservations of the kernel-audio-abi study are
  also boot-stubbed (1 stub + 76 packet segments each); the LINEDRIVE
  reservation dsp1 `0x3020/0x1800` carries 12 packet segments and no stub.
* Fail-closed checks: overwriting the second b0c1a stub record's base
  `0x5020` with `0x4020` (verified one-bit change at `0x610a8c0c`) makes
  `study()` raise `... has 2 {base, 6, capacity} segment records, expected
  exactly one`; record-removal/corruption and framing/capacity/length
  predicate changes are covered by synthetic tests.
* The single b1c1a data segment (dsp4 `0x1bda`, 64 bytes at source `0xe8ef4`)
  sits inside a stub-record array; stored tail ends `...c0f8fdd1 c0f8020c
  f800020b` and the region continues with two full stub records.
* Process note: the draft had an incomplete `stub_only` comprehension that
  only compiled by luck; it was rewritten during adoption. Also, a first
  fail-closed mutation attempt (flipping a bit in a stored record's bytes)
  was measured to produce NO raise across all 64 single-bit flips because the
  census is self-consistent under reclassification; the committed raise
  paths are the record-count and source-bytes invariants.
* `python -m unittest discover -s tests -p test_program_slot_census.py`:
  14 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring
  suites unchanged: `test_read_dspprog_caller_census.py` 10 OK,
  `test_program_read_study.py` 10 OK, `test_program_write_study.py` 8 OK,
  `test_kernel_abi.py` 5 OK.

Established: both stock images declare their render slot usage purely through
framed program lists plus boot-stub segment records, with no slot lacking a
backing record; the b1c1a `0x700` table's composition is pinned. A2's "is
any slot unused" is now bounded to: a stub is a written program, but whether
any stub-only slot ever executes is open. Unknown: runtime owners of the
slots (pointer runs at `0x610014d4/0x61029568/0x6102a750` b0c1a and
`0x610029b4/0x61024348/0x61024800` b1c1a located but not traced), whether
code reads the `0x610a4f20` table (no xref taken), the 60 lead bytes of the
b1c1a data segment, other builds. No opcode, family or interpreter
admission.

Best next item: lane A5 (wave memory and interpolation — which instructions
read sample/wave memory and DRAM-IO, their formats, and how stock sample
playback interpolates), the least-mapped and highest-value lane for the
sample-playback target; a scoping census of which render packets read the
DRAM-IO/wave apertures the read study mapped (0x411/0x412/0x414/0x415 ports)
is the bounded first step. If A5 stalls, trace the b1c1a pointer runs to
name slot owners (A2 completion).

## Run 21 — 2026-11-13: render indexed-transfer census; 529,931 operand reads across six images, tag space bounded to 11 tags

Item chosen: lane A5 (wave memory and interpolation) — specifically the
bounded scoping step run 19 named as the lane's first step: a census of which
render programs address which memory spaces through the admitted
indexed-transfer control form. The instruction-semantics lane's preferred
native `5d52` cutpoint binding still needs native-execution fixtures, excluded
by this series' rules. The worktree held an untracked draft
`tools/render_transfer_census.py` from an earlier session; this run verified,
corrected, finished, tested and committed it (run 2/10/19 adoption pattern).

Item taken and why: A5 scoping, because run 19 left it as the best next item,
it is the owner's least-mapped and highest-value lane, and the draft already
existed. The b1c1a pointer-run trace (A2 completion) is deferred as the
fallback.

Files:

* `tools/render_transfer_census.py` (new, from the draft): fail-closed census
  of every indexed-transfer control in all framed render programs of six
  hash-pinned images (zen_arm64 via `zenology_inventory.json`, b0c1a/b1c1a via
  `program_slot_census.frame_lists`, three cross-model QSPI images via
  `qspi_c1.read_c1` + the same framing); counts unknown shapes instead of
  guessing (`unframeable_segments`, `pool_index_overflow`,
  `odd_form_controls`); records every access to rare tags 1/3/f verbatim;
  reports per-tag accesses/loads/stores/distinct-addresses/programs/DSPs and
  per-port counts; zero decoder changes.
* `tests/test_render_transfer_census.py` (new): 18 tests — 10 pure synthetic
  fail-closed checks (admitted/rejected control forms, load/store counting,
  tag = pool-word top nibble, odd-form counting, pool-index overflow on a
  length-6 packet, unframeable counting, rare-context field capture,
  program/DSP attribution, trap-word form) plus 8 corpus-pinned tests (totals,
  per-tag counts, per-image counts, singleton tags, singleton addresses,
  native-majority share, run-19 framing cross-check).
* `docs/render-transfer-census-study.md` (new): the study note, with this
  run's tool command and trimmed JSON output pasted verbatim (owner direction
  of 2026-11-13).
* `local/render-transfer-census.json` (ignored local storage): this run's full
  tool output, read back by the corpus tests.

Verified this run (commands and outputs in the transcript):

* Tool exits 0: `PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"
  .venv/bin/python tools/render_transfer_census.py` — totals
  `transfer_controls` 529,931 over `framed_segments` 5,635 / `framed_packets`
  473,989; `unframeable_segments` 136 (128 desktop, 6 MC-101, 1 b1c1a data
  segment, 1 SH-4d), `odd_form_controls` 88, `pool_index_overflow` 0.
* Every indexed transfer in every framed stock program resolves inside its own
  packet (0 overflows across 529,931) — the whole-census extension of
  `analyze.py`'s per-image operand-boundary assertions.
* Tag space bounded: 11 of 16 top-nibble tags occur; tags 5/7/9/b/d never do.
  Tags 0/2/4/c carry 510,941 transfers (96.4%) and are exactly the natively
  provenanced tags of `transfer-spaces-study.md`; the other 18,990 (3.6%) use
  unprovenanced tags 1/3/6/8/a/e/f.
* Tags 1 and 3 are corpus singletons: one address each (`0x1999`/`0x369f`),
  134 load-only accesses each, all as pool words of the GASS-type `5e09`
  neighborhoods run 10 mapped — tag 3 by the `6209`/`2508` packets at program
  offsets `0x22e`/`0x29c` (the run-6/11 trap and its companion), tag 1 by the
  `2e08` packets at offsets `0x1a`/`0x5e`, in dsp4/dsp5 programs (dsp0 on the
  desktop image).
* Tag f: 117 accesses at only `f000`/`f801`, 93 stores — the rare-tag home of
  the run-11 `6fe4` slot-0 trap.
* Draft corrections during adoption: the draft used `analyze.core_lists`
  framing, which caps count at 16 and drops b1c1a's long dsp0..3 base-0 lists
  (34 segments vs run 19's accepted 1,633-geometry framing); switched to
  `program_slot_census.frame_lists` and added the desktop inventory path;
  also fixed a draft arithmetic slip (`counts['pool_index_overflow'] =
  counts['pool_index_overflow']` no-op) and dead code in `per_program_rows`
  (removed as unused).
* Every address/offset/count in the note re-checked before commit against the
  fresh JSON and the tests' anchors by a `python - <<PY` sweep (totals table,
  per-image tables, per-tag table incl. load/store sums recomputed
  independently, native share 510,941/18,990 = 96.4%, singleton low-12
  addresses 0x999/0x69f, tag-f 93 stores, hash first-16 prefixes
  `b8ba7f41e26bef91`/`6d95449ae2a2df48`/`c8d150b9cfe13d8e`, singleton offsets
  0x22e/0x29c/0x1a/0x5e): all pass.
* `python -m unittest discover -s tests -p test_render_transfer_census.py`:
  18 tests, OK (with `BMC_CORPUS_DIR` at the prepared corpus). Neighboring
  suites unchanged: `test_program_slot_census.py` 14 OK,
  `test_four_b_five_c_crosscheck.py` 13 OK, `test_program_read_study.py` 10
  OK, `test_header_study.py` 9 OK, `test_transfer_study.py` 6 OK,
  `test_bmc_emulator.py` 13 OK.

Established: the complete A5 scoping map — which memory spaces stock render
programs address through the admitted transfer form, with counts, directions,
and program coverage per image; the transfer-form operand pool is always
in-packet; four tags hold 96.4% of traffic and match the natively provenanced
set; tags 1/3 are fully enumerated singletons inside the already-mapped GASS
`5e09` contexts. Unknown: native provenance of tags 1/3/6/8/a/e/f (1/3 are
the cheapest next native targets — 134 occurrences, one address, all in
already-mapped contexts); which tag/instruction reaches the wave/DRAM-IO
apertures (none of the six images' render programs show a wave-memory-looking
tag under current unproved assumptions — the answer needs either native
provenance for the minority tags or the DRAM-IO instruction study); the 136
unframeable segments' contents. No opcode, family or interpreter admission.

Best next item: lane A5 continues — native provenance of the singleton tags
1/3 is now the smallest bounded step (134 occurrences, one address each, all
inside run 10's mapped `5e09` contexts, so the native tracer of
`transfer_study.py` style can resolve them), or, if native execution exceeds
one run, study which DRAM-IO/wave aperture ports (`0x411/0x412/0x414/0x415`)
appear in the render transfer pool addresses at all (this census shows no tag
above `e`; if wave memory is reached, it is via a non-transfer-form
instruction, which itself would be new evidence). A2 completion (b1c1a pointer
runs) remains the static fallback.
