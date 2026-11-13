# RVSDLY 0x60/0x71: a second owned field pair inside the program run 7 checked

2026-11-13. Run 7 ([RVSDLY cross-check](rvsdly-22b-23c-crosscheck-study.md)) proved
that in `SIM_MFX_RVSDLY` the relative program fields `0x22b`/`0x23c` are
independently owned, written with different computed doubles by
`CFspMfxRVSDLY::SetAlg()`, and each is selected by exactly one strict-decodable
control whose literal equals that field's own constructor default. Its note also
recorded that the same two doubles sit at relative fields `0x60`/`0x71` and
asserted — without a test — that neither of those fields is selected by any
strict-decoder control. This run re-examined that aside and found it wrong: the
fields are a second, structurally identical owned pair in the same program, each
with its own constructor pair, count-1 SetAlg write call and unique
strict-decoder control. **No DSP opcode, port semantics, fitted-family role or
interpreter admission follows.**

## What was examined and how

All checks are static, on the pinned ZENOLOGY arm64 image
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`, with
`tools/rvsdly_60_71_pair_crosscheck.py` reusing run 7's `packet_references`,
`mentions`, `setalg_calls` and constants, `parse.parse_ctor`, the strict
`header_study.layout` decoder and `line_prefix_single_writer.code_references`.

## Established facts

Established (every claim re-checked by the tool and pinned in
`tests/test_rvsdly_60_71_pair_crosscheck.py`):

* The stored program triples decode exactly to the run 7 doubles: `0x60` =
  `2ff000` = `0.99609375`, `0x71` = `aff800` = `-0.998046875`. The complete set
  of 3-byte windows in the whole `0x484`-byte program decoding to each double is
  exactly `{0x60, 0x22b}` / `{0x71, 0x23c}` — no third copy exists.
* The reconstructed constructor (44 pairs total, unchanged from run 7) declares
  exactly one pair per field: object `0x1b0` names relative `0x60` with the
  double `0.99609375` at object `0x1b8`, and object `0x1a0` names relative
  `0x71` with the double `-0.998046875` at object `0x1a8`.
* The count-1 width-3 descriptor groups `0xa438c0` (record `0x4080/0x60/3`,
  table `0x821808`) and `0xa438a0` (record `0x4091/0x71/3`, table `0x8217fc`)
  each hold one record, and each has exactly one code reference: the SetAlg
  descriptor ADD at `0x2c268c` / `0x2c2670` (page `0xa43000`, offsets
  `#0x8c0`/`#0x8a0`). The two oversized functions `0x589000..0x5af838` and
  `0x6b74ec..0x6d5138`, which `code_references` skips, contain no ADRP into the
  `0xa43000` descriptor page, so the sole-reference claim is not a scan-limit
  artifact.
* Inside `SetAlg` (`0x2c2508..0x2c2740`), call `0x2c2694` passes `d0 = d10` to
  the `0x60` group and call `0x2c2678` passes `d0 = d9` to the `0x71` group —
  the same registers passed to the `0x22b` call (`0x2c2640`, `d0 = d10`, the
  `fmadd` result computed once at `0x2c2628`) and the `0x23c` call
  (`0x2c2620`, `d0 = d9 = fneg(d8)` computed once at `0x2c2608`). `d8..d15`
  are callee-saved under AAPCS64, so the intervening slot-c8 callees cannot
  clobber them; the four calls therefore pass two distinct computed values,
  each twice.
* Under the strict decoder, exactly one control in the whole program selects
  each field, and both literals decode exactly to their field's constructor
  double:
  - packet `0x56`, header `0x2e07`, families `[1, 1, 4]`: control `0x34e2`
    selects absolute field `0x60`, value `0.99609375`.
  - packet `0x64`, header `0x1408`, families `[0, 4]`: control `0xc24` selects
    absolute field `0x71`, value `-0.998046875`.
  These are new instances of the same two reference syntax shapes run 7 proved
  for `0x22b`/`0x23c` (short `0x34e*` low-six and long-op literal), with
  different packets and controls.
* Cross-program contrast: in `SIM_MFX_GASSDLY` the same relative fields hold
  other values (`0x60` = `3fe28f` = `1.992812156677246`, `0x71` = `080c64` =
  `0.03143906593322754`), no constructor pair names `0x60` or `0x71`, and no
  strict-decoder control selects either field. The duplicated-pair structure
  is therefore program-local to RVSDLY, not a universal constant layout.
* Fail-closed negatives (each a one-bit image mutation, re-hashing so the
  identity check does not pre-empt the deeper checks): mutating a stored triple
  byte (`0x820e38+0x60`, `+0x71`), a control literal byte (packet `0x64`
  literal, and packet `0x56`), a group record byte (`0x821808`, `0x8217fc`,
  width byte included) or a SetAlg ADD immediate (`0x2c268c+3`) makes the tool
  raise `ValueError`.

## What this establishes for the lane

Run 7's second-program cross-check is corroborated by a second, independent
field pair inside the same program: same ownership shape (count-1 single-record
groups with a sole SetAlg reference), same write mechanism (slot-c8 calls
passing one computed double per pair), same exact constructor/stored-literal/
strict-control agreement, through both reference syntax forms. Run 7's aside is
corrected: `0x60`/`0x71` are selected by strict-decoder controls of their own;
the discrimination between the two same-valued copies rests on exact field
offsets and constructor pairs, not on values — unchanged in substance.

## What is not established

* That the DSP executes these controls as loads of the named fields; the
  constructor/stored-literal/strict-decoder agreement is static evidence only.
* Why the program keeps two copies of each parameter: the consumers of
  `0x60`/`0x71` versus `0x22b`/`0x23c` (channel split, stage split or
  otherwise) are not analyzed.
* That `SetAlg` is the only writer: fields `0x60`/`0x71` are also declared by
  other count>=1 groups (widths 2 and 4, e.g. `0x9d6660`, `0x9d6c80`,
  `0xa52a08`, `0xa578e0`, `0xa71d48` for `0x60`; `0xa2cdb0` count 5,
  `0xa337e0`, `0xb3c148` for `0x71`) whose writer functions were bounded but
  not named; runtime-built descriptors, raw writes and other builds are not
  excluded.
* The arithmetic roles of `0x34e2`, `0xc24`, `0x34e5`, `0xca6` and the fitted
  `62` family of run 4 remain unproved. No opcode, family or interpreter
  admission.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /path/to/venv/bin/python tools/rvsdly_60_71_pair_crosscheck.py local/zen_arm64
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  /path/to/venv/bin/python -m unittest discover -s tests \
  -p test_rvsdly_60_71_pair_crosscheck.py -v
```

The tool exits nonzero on any changed segment base, stored triple, double-copy
set, constructor pair, descriptor record, SetAlg call shape, packet reference,
GASSDLY contrast or image identity. Tests pin the synthetic fail-closed
behavior and the corpus facts above.