# Fitted 4b/5c miscellaneous slots: corpus-wide positional cross-check

2026-11-13 (overnight run 11). The review follow-ups and runs 4, 8 and 10 of this
series name one bounded static follow-up: a cross-check of the fitted
four-operation rule's `4b=(0,1,2,4)` and `5c=(1,1,2,4)` predictions, whose kind-2
slots ("miscellaneous") are exactly what run 4 could not decide — it proved only
that such packets fail closed under the admitted strict layout
([header-family-crosscheck-study.md](header-family-crosscheck-study.md)). This
run performs the cross-check the corpus *can* decide statically: a full shape
census of all count-4 fitted packets in six prepared images, plus a positional
invariant on `fe0..fee`-window control words, calibrated on the admitted anchor
syntax and on the count-1 classes `08..0c`. No opcode, family or decoder change;
`header_study` is untouched.

## Method

`tools/four_b_five_c_crosscheck.py` re-uses
`header_family_crosscheck.ranked_choices()` (the fitted ranking, never
re-established here) and the existing `analyze.core_lists()` framing to scan
every framed packet of the six pinned images. For every count-4 packet with a
fitted prediction and every count-1 packet of classes `08..0c` it records
per-slot control vocabularies and window statistics, and raises on any breach of:

- **C1** a `fe0..fee`-window control word in a slot the fitted rule does not
  predict as transfer, except the known `62`/`6fe4` slot-0 trap;
- **C2** for `4b`/`5c` packets specifically, the window-control slot set must be
  `[]` or `[3]` (the fit predicts exactly slot 3 as transfer);
- **C3** `5a` packets (fit `(1,1,2,2)`, no transfer slot) carry no window
  control;
- **C4** count-1 controls of `08`, `09`, `0a`, `0b` never use the window; `0c`
  does.

Calibration of the window: in the admitted anchor syntax a transfer slot's
control word may lie anywhere, but the *proved* transfer field form is the
`fe0..fee` even-address window (`header_study.layout`), and the count-1 classes
give the operand-shape calibration: `0c` controls carry window words (16 distinct
values), `08/09/0a/0b` never do. So "window control" is the strongest static
marker of a transfer-class operation available without admitting new syntax.

## Evidence

Inputs (unmodified): desktop `zen_arm64` SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`; Fantom
`b0c1a.bin` payload `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`;
`b1c1a.bin` `c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd`;
JUPITER-X `MI077` `9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`;
MC-101 `RPG69` `6de1e182e531d672ef9bcc0aabf853dd724f59e70dfd9c9aa34c28a393d62a21`;
SH-4d `DD013` `57466624effa7b78ea6f775487d78a35dbf141d2ec4a979338266b77bdcccadf`
(all re-hashed this run before use).

```sh
BMC_CORPUS_DIR=$PWD/local PYTHONPATH=local/fantom-python:tools \
  python tools/four_b_five_c_crosscheck.py > local/four-b-five-c-run11.json
echo exit=$?
```

Observed: exit 0, zero invariant breaches. Pasted (trimmed) output, from
`local/four-b-five-c-run11.json`, key `totals`:

```json
{
 "count4_fitted": 38441,
 "decoded_packets": 27138,
 "unsupported_packets": 11303,
 "code5a_packets": 276,
 "code62_packets": 306,
 "code62_slot0_fe": 28,
 "packets_4b5c": 2257,
 "fe3_packets": 1520,
 "no_fe_packets": 737,
 "count1": {"08": 10433, "09": 9815, "0a": 8548, "0b": 4176, "0c": 10967},
 "count1_fe_window": {"08": 0, "09": 0, "0a": 0, "0b": 0, "0c": 7579},
 "calibration": {
  "08": {"occurrences": 10433, "distinct": 194, "fe_window_occurrences": 0, "fe_window_distinct": 0},
  "09": {"occurrences": 9815, "distinct": 269, "fe_window_occurrences": 0, "fe_window_distinct": 0},
  "0a": {"occurrences": 8548, "distinct": 128, "fe_window_occurrences": 0, "fe_window_distinct": 0},
  "0b": {"occurrences": 4176, "distinct": 51, "fe_window_occurrences": 0, "fe_window_distinct": 0},
  "0c": {"occurrences": 10967, "distinct": 188, "fe_window_occurrences": 7579, "fe_window_distinct": 16}
 },
 "vocab_crosscheck": {
  "long8_distinct": 194, "short9_distinct": 269, "overlap": 6,
  "4b_slot0": {"distinct": 28, "long8_inside": 4, "short9_inside": 0, "outside_both": 24},
  "5c_slot01": {"distinct": 98, "long8_inside": 5, "short9_inside": 22, "outside_both": 72}
 }
}
```

Per-image counts (same file): fitted count-4 packets `zen_arm64` 2,266,
`b0c1a.bin` 5,204, `b1c1a.bin` 1,253, `MI077` 14,923, `RPG69` 2,116, `DD013`
12,679 — identical to run 4's totals, so the scan base is unchanged. `4b`+`5c`
packets per image: 152, 316, 61, 801, 117, 810 (2,257 total); of those, 1,520
have exactly one window control in slot 3 and 737 have none (1,520 + 737 =
2,257, no third case). The one C1 exception corpus-wide is the known trap: all
28 `62` packets with a window control in slot 0 are the 9-word GASSDLY shape
`6209 6fe4 9450 ded4 8fe2` (zen desktop segment offset `0x22e`, b0c1a GASSDLY
`0x22e` with the same controls, plus further placements in MI077 and DD013);
every other fitted count-4 packet keeps every window
control in a transfer-predicted slot.

A second, independent vocabulary check (recorded, not asserted —
`vocab_crosscheck` above): the count-1 long (`08`) and short (`09`) control
vocabularies overlap in only 6 of 194/269 words, so mostly class-exclusive words
discriminate. The 28 distinct controls in `4b` slot 0 include 4 of the
long-only words and **zero** of the 269 short-only words; the 98 distinct
controls in `5c` slots 0..1 include 22 of the short-only words and 5 of the
long-only ones. Under the fitted assignment (4b slot 0 long, 5c slots 0..1
short) both directions go the right way; under the swapped assignment they would
both go the wrong way. This is positional evidence the fitted rule did not
predict and the corpus did not have to supply.

The non-window `4b`/`5c` slot-3 controls (737 occurrences, 16 distinct values,
`b9b3` 368, `c9b3` 149, `99b1` 90, `99b2` 36, `d9b2` 24, the rest rarer) never
appear as any count-1 `08..0c` control, consistent with their belonging to a
operation class the count-1 calibration does not cover — the same class the fit
calls miscellaneous.

## What is established, and what is not

Verified (commands above; test `tests/test_four_b_five_c_crosscheck.py`, 13
tests, `OK` with the prepared corpus):

- All 38,441 fitted count-4 packets in six images satisfy C1 (window control in
  a transfer-predicted slot) except the 28 pinned `6209`/`6fe4` slot-0
  occurrences; all 2,257 `4b`/`5c` packets satisfy C2; all 276 `5a` packets
  satisfy C3. The count-1 calibration totals 43,939 controls (10,433 + 9,815
  + 8,548 + 4,176 + 10,967, the pinned per-class counts above), of which 7,579
  use the window and all 7,579 belong to class `0c`.
- The long/short vocabulary discrimination of `4b` slot 0 and `5c` slots 0..1
  goes the fitted rule's way in both directions.
- Fail-closed synthetic checks: a window control moved into an anchor's
  long/short slot raises; a second window control in a one-transfer anchor
  raises; a window control in a `5a` packet raises; a `4b` window control in
  slot 2 raises; count-1 calibration changes raise.

Inferred (from consistency and calibration, not from execution):

- The fitted rule's *slot ordering* — not just its multiset — is now consistent
  with every transfer-marker statistic the corpus exposes, which run 4 could not
  say: nothing in six images puts a transfer-looking control outside a
  transfer-predicted slot, and the two leading-slot vocabularies match their
  predicted long/short classes.
- The single C1 exception mildly tensions with the fit: `6fe4` in `6209` looks
  transfer-like, but the fit puts slot 0 of `62` in the short class. Either the
  window marker does not extend to the unadmitted `62` syntax, or the fitted
  `62` ordering is wrong. This sharpens, but does not resolve, the standing
  GASSDLY `62` trap; runs 6 and 7 proved field ownership, not slot roles.
- The 737 non-window `4b`/`5c` slot-3 controls (`b9b3` class) belong to no
  count-1 class; if the fit's kind-2 label is meaningful they are its natural
  occupants, and the same words plausibly fill `5a`'s predicted-miscellaneous
  slots. Not proved.

Unknown: what `4b`/`5c` slot 2 (the fit's other miscellaneous slot) and the
`b9b3` class actually do; whether the window marker is causal or accidental
across unadmitted syntaxes; `5a`/`62` slot semantics; other builds. No
opcode, family or interpreter admission; `header_study.families()` still fails
closed for every non-anchor count-4 code.

## Reproduction

```sh
BMC_CORPUS_DIR=$PWD/local PYTHONPATH=local/fantom-python:tools \
  python -m unittest discover -s tests -p test_four_b_five_c_crosscheck.py
BMC_CORPUS_DIR=$PWD/local PYTHONPATH=local/fantom-python:tools \
  python tools/four_b_five_c_crosscheck.py
```

The tool writes nothing except stdout; regenerate `local/four-b-five-c-run11.json`
with the redirect above if wanted (that file is ignored local storage).