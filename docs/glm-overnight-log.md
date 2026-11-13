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