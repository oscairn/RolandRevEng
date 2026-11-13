# RVSDLY 22b/23c: the GASSDLY grouped-write reading survives a second program

2026-11-13. Run 6 ([GASSDLY trap study](gassdly-62-trap-study.md)) proved that in
`SIM_MFX_GASSDLY` the relative program fields `0x22b` and `0x23c` always hold one
common value: both are declared in the single count-2 group `9dfa50`, written by
one slot-c8 call in `CFspMfxGASSDLY::SetDLY`. That proof rested on grouped
equality, so a critic can object that the two fields are one storage by
construction and the `6fe4`-consumes-`23c` reading is vacuous there. This study
cross-checks the same fields in `SIM_MFX_RVSDLY`, the independent program run 6
already listed as a sibling writer: there the two fields are owned by two
separate count-1 groups written with two different computed doubles, so the
equality shortcut is unavailable and each field must stand on its own evidence.
**No DSP opcode, port semantics, fitted-family role or interpreter admission
follows.**

## What was examined and how

All checks are static, on the pinned ZENOLOGY arm64 image
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`, with
`tools/rvsdly_22b_23c_crosscheck.py` reusing `parse.parse_ctor`, the strict
`header_study.layout` decoder, the count>=1 descriptor ABI from
[line-prefix-single-writer](line-prefix-single-writer-study.md) and the
Capstone disassembly of `CFspMfxRVSDLY::SetAlg()`.

## Established facts

Established (every claim re-checked by the tool and pinned in
`tests/test_rvsdly_22b_23c_crosscheck.py`):

* `SIM_MFX_RVSDLY` has one render segment at base `0x4020` (peer `0x8000`),
  logical length `0x484`.
* The reconstructed constructor declares exactly one pair per field: object
  offset `0x150` holds a record pointer naming relative `0x22b` with the double
  `0.99609375` at object `0x158`, and object offset `0x140` names relative
  `0x23c` with the double `-0.998046875` at object `0x148` (44 pairs total).
  The stored program bytes decode exactly to those doubles: `0x22b` = `2ff000`
  = `0.99609375`, `0x23c` = `aff800` = `-0.998046875` — exactly, unlike
  GASSDLY's `4.4250488e-07` near-miss. The two values are `-1+2^-9` and a
  dyadic rational, not round decimals.
* The count>=1 descriptor inventory over both fields is exactly
  `9cc8c0, 9dfa50, a1f9a0, a41d00, a43840, a43860`. The RVSDLY groups
  `a43860` (`424b/22b/3`) and `a43840` (`425c/23c/3`) each have count 1 with
  one record, referenced from `CFspMfxRVSDLY::SetAlg()` at `0x2c2638` and
  `0x2c2618`. `9dfa50` remains the only count>=2 group mentioning the fields,
  unchanged from run 6.
* `SetAlg` (`0x2c2508..0x2c2740`) contains exactly six slot-c8 literal calls
  with descriptors `0xa430840, 0xa430860, 0xa430880, 0xa4308a0, 0xa4308c0,
  0xa4308e0` and arguments `d9, d10, d8, d9, d10, #1.0`. The first two write
  the two fields: call `0x2c2620` (descriptor `a43840`, field `0x23c`) passes
  `d0 = d9 = -d8`, and call `0x2c2640` (descriptor `a43860`, field `0x22b`)
  passes `d0 = d10 = d8*d10+d11` with `d8 = 86.30125969547748`,
  `d10 = 2.0 - x`, `d11 = -1.0` from the preceding `fmov/fneg/fmadd` chain.
  The two fields therefore receive **different values by construction**.
* Under the strict decoder (`header_study.layout`), exactly one control in the
  whole program exactly selects each field, and both literals decode exactly to
  their field's constructor double:
  - packet `0x22e`, header `0x2b09`, families `[0,4,4]`: the long operation's
    literal (extension `5fe2`, low-six `0x26` -> offset 6, width 3) selects
    absolute field `0x23c`, value `-0.998046875`.
  - packet `0x21e`, header `0x2e08`, families `[1,1,4]`: short control `0x34e5`
    (low-six `0x25` -> offset 5, width 3) selects absolute field `0x22b`, value
    `0.99609375`.
* `0.99609375` also occurs at field `0x60` (same bytes `2ff000`), and
  `-0.998046875` at field `0x71`; neither of those fields is selected by any
  strict-decoder control, and field `0x60` is covered by other groups
  (`a52a08`, `a578e0`), so the discrimination rests on exact field offsets and
  constructor pairs, not on values alone.

## What this establishes for the lane

The GASSDLY grouped-write reading is not an artifact of grouped equality: in a
second program the same two relative fields are independently owned, written
with different computed values, and each is selected by exactly one
strict-decodable control whose literal equals that field's own constructor
default. The reference syntax (short low-six and long-extension low-six literal
forms) behaves identically in both programs. This is cross-program consistency
evidence for the reference reading, not new opcode semantics: the arithmetic
roles of `0xca6`/`0x5fe2`, `0x34e5` and the GASSDLY `6209` words remain
unproved, and the fitted `62 = (1,2,2,4)` family of run 4 is untouched.

## What is not established

* That the DSP executes these controls as loads of the named fields; the
  constructor/stored-literal/strict-decoder agreement is static evidence only.
* That `SetAlg` is the only writer: runtime-built descriptors, raw writes,
  external paths and other builds are not excluded.
* Any claim about fields `0x60`/`0x71` beyond their stored bytes and owning
  groups; their consumers are not analyzed here.
* No extension of `header_study.families()`, the strict decoder or the fragment
  interpreter; the executable subset is unchanged.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /path/to/venv/bin/python tools/rvsdly_22b_23c_crosscheck.py local/zen_arm64
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  /path/to/venv/bin/python -m unittest discover -s tests \
  -p test_rvsdly_22b_23c_crosscheck.py -v
```

The tool exits nonzero on any changed segment base, stored triple, constructor
pair, descriptor record, `SetAlg` call shape, packet reference or image
identity. Tests pin the synthetic fail-closed behavior and the corpus facts
above.