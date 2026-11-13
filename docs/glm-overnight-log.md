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