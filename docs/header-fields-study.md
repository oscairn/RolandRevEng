# Six-bit operands and bounded header-family decoding

Follow-up: [oscillator layout candidates](oscillator-layout-candidates.md) explains
all six owned oscillator literal references while retaining two arity ambiguities.
The production decoder and emitter remain unchanged.

Offline follow-up, 2026-11-09, extended 2026-11-10. This study uses the same local ZENOLOGY arm64 and
Fantom-0 v1.08 inputs as the packet/loader report. It adds operand-layout information;
it does not execute Roland code or establish hardware arithmetic or timing.

## Useful result

Several arithmetic operation families use a **six-bit operand reference**:

```text
selector = (reference >> 4) & 3
index    = reference & 15

selector 0: register/input index; no literal field
selector 1: 2-byte literal at common payload byte offset index
selector 2: 3-byte literal at common payload byte offset index
selector 3: 4-byte literal at common payload byte offset index
```

The four low bits are a **byte offset**, not an operand ordinal. Three-byte literals
can consequently start at odd positions. Two operations can reference the same literal;
allocating a new literal sequentially for each operation is incorrect.

For a regular short arithmetic operation, the reference is `control & 0x3f`.
For a regular long operation there are three references:

```text
operand 0 = base_control & 0x3f
operand 1 = (extension_word >> 6) & 0x3f
operand 2 = extension_word & 0x3f
```

For example, a six-bit value `0x25` selects a three-byte literal at payload byte
offset 5. A value `0x28` selects one at offset 8. The upper four bits of a long
extension word are outside these two operand fields and are not decoded here.

The implementation calls the selector-0 case `register`; exact DSP register names
and the meanings of all register indices remain unresolved. The arithmetic opcode,
destination, precision, clipping and pipeline effects are separate questions.

## Base opcodes and extensions are separate areas

The existing packet formula gives the number of **base opcode words**. Long arithmetic
operations additionally have an extension word in the shared payload. Thus the formula
does not mean every decoded operation consists of one 16-bit control word.

All base opcode words still precede the common payload, so the prior indexed `NFEk`
transfer rule remains useful. It indexes the common pool that includes extension words,
literal bytes and address operands. Moving each extension adjacent to its base opcode
would break the actual field positions.

The bounded layouts implemented by `tools/header_study.py` are:

| Header family (high byte) | Base operation families | Implemented layout |
|---|---|---|
| `08`, `09`, `0c` | one long, one short, or one transfer | The respective reference/extension or address syntax |
| `10`, `11`, `14`, `15`, `18`, `1e` | `00`, `01`, `04`, `11`, `14`, `44` | Two base operations, sharing one payload |
| `22`, `25`, `2b`, `2e`, `34`, `3e` | `004`, `014`, `044`, `114`, `144`, `444` | Three base operations, sharing one payload |
| `47`, `4e`, `58`, `5f`, `69`, `78` | `0044`, `0144`, `0444`, `1144`, `1444`, `4444` | Four base operations, sharing one payload |
| `8f` | `00` followed by transfers | Five through eight base operations observed |
| `9c` | `01` followed by transfers | Five or six base operations observed |
| `ab` | `0` followed by transfers | Five or six base operations observed |
| `b8` | `11` followed by transfers | Five through eight base operations observed |
| `c7` | `1` followed by transfers | Five or six base operations observed |
| `e4` | all transfers | Five or six base operations observed |

Digits in this table are operation-family numbers: `0` long arithmetic, `1` short
arithmetic, `4` transfer. They are not DSP input indices or arithmetic opcode values.
All long-operation extensions occupy the first successive 16-bit words of the common
payload; the remaining literal and indexed-address positions come from their references.
The packet's count formula controls how many transfer slots follow the prefix in the
extended-count forms. The low two count bits are independent of the high-byte family.

Only the known compact single-word forms are additionally accepted. Miscellaneous
families, flow controls, the exceptional short forms below and unproved transfer-window
modes raise `UnsupportedLayout`. The helper never fills an unknown input with zero.

The broader `families()` helper records candidate classifications for neighboring
research, including a constrained rank for three-operation headers. It is **not** a
complete header grammar. The complete operand decoder admits only the narrower table
above. This follow-up adds observed mixed forms, rather than asserting an unrestricted
multiset rank for larger headers. Extrapolating the two-operation lexicographic pattern to all larger packets was
tested and rejected: unconstrained three-operation ranking would place three transfer
operations at the wrong code. Remaining header composition and issue-slot meaning are
still open.

## Validation and independent anchors

`layout()` resolves references and then checks:

- Every extension, indexed address and literal reference fits the packet payload.
- A literal does not overlap a long-operation extension word.
- The references account for every payload byte except at most one final padding byte.
- Shared literal references are permitted; appended-byte accounting is not assumed.

Results on the complete local inventories:

| Artifact | All observed packets | Packets admitted by the bounded layout | Layout counterexamples |
|---|---:|---:|---:|
| ZENOLOGY arm64 | 12,365 | 8,970 | 0 |
| bmc0 CORE1 | 36,793 | 25,864 | 0 |
| bmc1 CORE1 | 12,176 | 6,876 | 0 |
| Total | 61,334 | 41,710 | 0 |

These totals include repeated and relocated observations. They are not counts of
independent algorithms. Unsupported packets are counted separately rather than consumed
as invented data. The admitted layouts contain 30,834 literal-reference observations,
19,855 extension words and 50,433 address-reference observations. The first pass admitted
21,178 packets; the added 20,532 observations exercise mixed long/short/transfer layouts.
Structural fit is necessary but not sufficient to prove an individual opcode subtype's
operand meaning. Newly identified exceptional subtypes are excluded even when a guessed
reference can alias bytes already explained by another operation.

An additional check uses candidate `_CoefSym` records from the bounded adjacent-data
scan in `analyze.coefficient_widths()`. Its 2,234 candidate width-and-position anchors
inside supported packets produce **2,233 matches and one conflict**, described below.
The original narrower pass found 387 matches and no conflicts. Neither field position
nor width is selected by trying different fits to the native numeric value, but
**adjacency and an equal relative address do not prove table ownership**. These are
therefore matching metadata candidates, not 2,234 independently owner-proven symbols.
The legacy JSON key `independent_symbols` remains for compatibility; the study retains
the conflict with both predicted and candidate widths instead of silently excluding it.

That is structural evidence for operand encoding. It does not show that an arithmetic
opcode computes a multiply or that the operation can safely issue next to another one.

## Negative cases retained

Five distinct firmware short-operation words violate the naive rule that every apparent
six-bit literal selector in family `09` owns a payload literal:

```text
4091, 0094, 2091, 3092, 1090
```

They appear without the predicted payload, in 37 observations in each CORE1 artifact.
They are explicitly unsupported, not interpreted as literals and not converted to zero.
Their operand syntax or opcode subfamily needs separate recovery.

Sixty-six additional mixed-packet observations use short controls `20a0`, `20a4`,
`20a5`, `30a0` or `30a2`. For `20a0`/`30a0`, the regular six-bit interpretation makes
its supposed literal overlap a preceding long-operation extension. The other observed
variants merely alias bytes already covered by known literals, so complete byte coverage
cannot independently justify treating them as ordinary literal references. All five
controls now remain unsupported, including 46 observations that initially passed the
broader structural check. They occur in `11` and `25` header families and are not
generalized to every word with the same low byte. Native `_exp` cutpoints give a better
research target, described in [the exceptional-operation study](special-ops-and-exp-study.md),
but do not prove the individual controls' arithmetic or operand syntax.

## A neighboring symbol table can impersonate a coefficient width

The expanded layout exposes the previous GASSPH default mismatch at relative `0x2a8`:

- The primary GASSPH packet starts at `0x29e`, in long-plus-transfer family `14`.
  Its base's six-bit reference predicts a three-byte literal at `0x2a8`; its extension
  predicts a second three-byte literal at `0x2ab`.
- Decoding the first predicted literal at width three yields `0.998046875`, exactly
  the native constructor default. This is a consequence of the reference encoding;
  the decoder does not choose a width by minimizing the numerical error.
- The old adjacent scan found candidate `_CoefSym` at plugin offset `0x827cac`, with
  `(absolute=0x42c8, relative=0x2a8, width=4)`. Width four consumes the first byte of
  the next predicted literal and produces the previously reported 175-LSB error.
- That candidate lies immediately before the **MS_COMP** program at `0x827cdc`.
  MS_COMP's native default at the same relative `0x2a8` is zero, and its own packet
  predicts a four-byte zero at that position. The candidate's sole image-backed
  64-bit pointer occurrence is at `0xa463e0` in the neighboring descriptor area.
- GASSPH's exported `SetAlg()` instead references its earlier structures at
  `0x826f98`, `0x826fb8`, `0x827068`, `0x827088`, `0x8271c8` and data descriptors in
  the `0xa446xx` area. For example descriptor pointer field `0xa44680` points to
  `0x8271a8`; subsequent descriptors point to symbols near `0x8271e8..0x827234`.

This makes a foreign adjacent-table hit the strong explanation for the mismatch.
The pointer occurrence and position do not by themselves establish the complete
MS_COMP descriptor ownership graph. The bounded result is a conflict in the old
symbol-association heuristic, not proof that GASSPH uses four-byte precision here.
Actual symbol-to-driver ownership needs to be recovered before using such records as
unqualified independent anchors. The corpus test pins this single conflict explicitly
so a future ownership fix or a new discrepancy cannot silently change the count.

## Other negative cases

The indexed-transfer proof covers only `FE0`, `FE2`, ..., `FEE`. Other `Fx` windows,
including firmware `FF0` examples, remain unsupported. In particular, ten `4709`
firmware observations use an unproved transfer window and are excluded. The 100 ZENOLOGY
`4709` observations and the indexed firmware examples fit the two-extension/two-transfer
layout. Across all observed `47xx` sizes, all 410 ZENOLOGY observations fit it.

The first allocation hypothesis also failed: putting all extension/address words before
all coefficients misparsed two-byte literal fields that sit earlier in the common pool.
Using encoded byte references handles those positions and aliases directly. This failed
hypothesis is not retained as a fallback decoder.

## Reproduce

From the repository directory, using the Capstone-capable environment from the README:

```sh
python3 tools/header_study.py
python3 -m unittest discover -s tests -p test_header_study.py -v
```

The script writes aggregate results and counterexample locations to ignored
`local/header-study.json`; it does not publish full program bytes or native disassembly.
The nine tests cover synthetic register/literal references, odd packed literals,
literal aliases, mixed long/short/transfer pools, extended operation counts, paired long
extensions, rejection behavior and the optional local corpus plus its explicit metadata
conflict. The pure checks require no local firmware; corpus tests skip when local
artifacts or Capstone are absent.

Arithmetic and timing remain unverified on hardware. Miscellaneous-family payloads,
unrestricted higher-arity header ranking, exceptional short operations and other transfer
windows remain unresolved.
