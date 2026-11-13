# Fitted four-operation header rule: corpus-wide consistency cross-check

2026-11-13 (overnight run 4). The agent handoff records a fitted rule for
four-operation header families as explicitly hypothesis only: rank
`combinations_with_replacement(range(5), 4)` filtered by
`sum(kind < 2) <= 2 or (sum(kind < 2) == 3 and last == 2)` (57 entries) and index
that list by `(header >> 8) - 0x40`. It matches the six recorded anchors
(`47=0044`, `4e=0144`, `58=0444`, `5f=1144`, `69=1444`, `78=4444`) and predicts
`4b=0124`, `5a=1122`, `5c=1124`, `62=1224`. The handoff forbids expanding
`header_study.families()` from that fit alone. This study does not expand it; it
cross-checks the rule against every render-list packet in six prepared images and
records the exact consistency boundaries.

## Method

`tools/header_family_crosscheck.py` rebuilds the ranking from the constraint
alone, asserts the 57-entry size and the six anchor families, and then scans the
render-list segments of each image with the existing `analyze.core_lists()`
framing. For every framed packet with `command_count == 4` and no bit-5 flag it
compares three things against the rule:

1. The header code must lie in the fitted range `40..78`. Any count-4 packet
   outside it would be a counterexample, because the ranking assigns no family
   there.
2. If `header_study.layout()` strictly decodes the packet, its families must
   equal the rule's prediction for that code.
3. A code the rule predicts as containing a miscellaneous (family 2) operation
   must fail closed in `layout()` with `UnsupportedLayout`; a strict decode of
   such a packet would contradict the rule.

Nothing is admitted into `header_study.py`; the decoder is unchanged.

## Evidence

Prepared inputs (unmodified, read in place): desktop `zen_arm64` SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`; Fantom
`b0c1a.bin` payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`; JUPITER-X
container SHA-256
`9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`.

```sh
BMC_CORPUS_DIR=<prepared local> PYTHONPATH=local/fantom-python:tools \
  python tools/header_family_crosscheck.py \
  --core1 local/b0c1a.bin --core1 local/b1c1a.bin \
  --qspi local/crossmodel/jupiter-x/MI077_C1A_up.bin \
  --qspi local/crossmodel/mc101/RPG69_C1A_up.bin \
  --qspi local/crossmodel/sh-4d/DD013_C1A_up.bin
```

Observed output (exit 0, 2026-11-13): **zero counterexamples** in all six images.

| Image | Packets framed | Count-4 packets | Distinct count-4 codes | Code range | Strictly decoded | All decoded are anchors | Nonanchor strict decodes |
|---|---:|---:|---:|---|---:|---:|---:|
| zen_arm64 | 12,365 | 2,266 | 37 | `40..78` | 1,703 | yes | 0 |
| b0c1a.bin | 36,793 | 5,204 | 40 | `40..78` | 3,697 | yes | 0 |
| b1c1a.bin | 12,176 | 1,253 | 32 | `46..78` | 631 | yes | 0 |
| MI077 (JUPITER-X) | 86,857 | 14,923 | 41 | `40..78` | 11,285 | yes | 0 |
| RPG69 (MC-101) | 13,639 | 2,116 | 36 | `42..78` | 837 | yes | 0 |
| DD013 (SH-4d) | 79,912 | 12,679 | 42 | `40..78` | 8,985 | yes | 0 |

Total: 38,441 count-4 packets. Every count-4 header in all six images lies
inside the fitted range, and the only codes that strictly decode are exactly the
six anchors. That is the strongest statement static evidence here supports: the
ranking is *consistent with* the corpus, and no non-anchor count-4 code admits
the current strict layout, which is what the rule's miscellaneous predictions
require. Framing failures are counted, never decoded: 6 segments in RPG69 and 1
in DD013, matching the exclusion counts the [earlier
scan](emulator-next-program-targets.md) reported for the same images; no
conclusion rests on them.

Two bounded spot checks connect the result to the named trap in the handoff:

* GASSDLY `62` packets exist (the exact handoff-trap neighborhood `6209` with
  controls `6fe4 9450 ded4 8fe2` at b0c1a GASSDLY segment offset `022e`, plus
  `6207` at `024e`). Under the fitted rule `62=(1,2,2,4)`, slot 0 is a short
  arithmetic operation and slots 1..2 are miscellaneous, so `6fe4` is not forced
  into a short-arithmetic slot by the rule itself; but the rule's fit gives no
  independent evidence for that slot assignment. Unchanged.
* The four predicted codes `4b`, `5a`, `5c`, `62` all occur in the corpus (for
  example 138 `4b` packets and 39 `5a` packets in b0c1a) and all fail closed with
  `UnsupportedLayout`, as a miscellaneous-containing prediction requires.

## What is established, and what is not

Verified (commands above; test `tests/test_header_family_crosscheck.py`, 7 tests,
`OK` with the prepared corpus):

* The rebuilt ranking has 57 entries and agrees with all six `header_study`
  anchor families; those families are pinned by the existing
  `tests/test_header_study.py` assertions, which still pass.
* All 38,441 count-4 packets across six images have codes in `40..78`; zero
  strict decodes disagree with the ranking; zero non-anchor codes strictly decode
  in any image; zero segments failed strict framing (`unframeable_segments` is 6
  in RPG69 and 1 in DD013, both counted, not decoded; these are the same counts
  the earlier `line_mix_variation` scan reported for the same images).
* Across the six images, 45 of the 57 fitted codes occur at least once; the 12
  never observed are `49, 4c, 4f, 50, 52, 55, 56, 60, 66, 6a, 6b, 70`. Unobserved
  codes carry no evidence in either direction.
* Predicted-miscellaneous codes fail closed, checked with synthetic packets in the
  tests and observed in the corpus counts.

Inferred (from the consistency direction only):

* The rule remains unfalsified by the corpus. This is consistency, not proof of
  the fitted semantics: every count-4 code in `40..78` is *allowed* by the fit, so
  the fit excludes nothing and the corpus provides no discriminating evidence for
  the predicted `4b/5a/5c/62` tuples beyond their failure to decode strictly.
* Unknown: whether non-anchor count-4 packets decode under some other operand
  syntax (as the known `1c90`/`0d90`/`ded4`/`9450`/`d550`/`d554` ambiguity shows
  they must); whether other builds or BMC cores use count-4 codes outside
  `40..78`; whether the ranking constraint itself has any causal basis.
* No opcode, decoder or emitter change. `header_study.families()` still fails
  closed for every non-anchor count-4 code. The `62=1224` GASSDLY `6fe4` trap
  stands exactly as the handoff recorded it.

## Next discriminating step

The smallest next proof is unchanged from the handoff and the negative-bias
study: bind one earlier-`5a`/`62` context's `1c90`/`0d90`/`ded4`/`9450`/
`d550`/`d554` effects to native cutpoints through both channel chains, which
would give the first independent (non-anchor) evidence about the four-operation
family layout. A second independent route is a native window over a
`4b`/`5c` context, whose predicted miscellaneous slots should correspond to
non-arithmetic control behavior.