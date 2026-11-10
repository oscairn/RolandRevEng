# Six-bit operands and bounded header-family decoding

Offline follow-up, 2026-11-09. This study uses the same local ZENOLOGY arm64 and
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
| `08` | one long arithmetic operation | One extension word and its three operand references |
| `09` | one short arithmetic operation | One operand reference, excluding known special operations |
| `15` | two short arithmetic operations | Two references into the same payload |
| `0c`, `1e`, `3e`, `78`, selected `e4` forms | transfer operations | Indexed `FE0..FEE` fields or direct forms without added fields |
| `47` | two long operations and two transfers | Two extension words first in the common payload; both sets of arithmetic references and transfer fields |

Only the known compact single-word forms are additionally accepted. Other mixed
families, miscellaneous operations, flow controls and unproved transfer-window modes
raise `UnsupportedLayout`. The helper never fills an unknown input with zero.

The broader `families()` helper records candidate classifications for neighboring
research, including a constrained rank for three-operation headers. It is **not** a
complete header grammar. The complete operand decoder admits only the narrower table
above. Extrapolating the two-operation lexicographic pattern to all larger packets was
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
| ZENOLOGY arm64 | 12,365 | 3,047 | 0 |
| bmc0 CORE1 | 36,793 | 13,739 | 0 |
| bmc1 CORE1 | 12,176 | 4,392 | 0 |
| Total | 61,334 | 21,178 | 0 |

These totals include repeated and relocated observations. They are not counts of
independent algorithms. Unsupported packets are counted separately rather than consumed
as invented data. The admitted layouts contain 7,778 literal-reference observations,
4,859 extension words and 14,817 address-reference observations.

The stronger independent check uses `_CoefSym` records from the adjacent symbol tables,
whose explicit widths were previously matched against native coefficient defaults.
Across the supported primary paired images, **all 387 symbol width-and-position anchors
match the six-bit field prediction exactly**. This includes 75 anchors in the short
single/dual forms and a further 312 in long and paired-long forms. Neither field position
nor width is selected by trying different fits to the native numeric value.

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
The seven tests cover synthetic register/literal references, odd packed literals,
literal aliases, paired long extensions, transfers, rejection behavior and the optional
local corpus. The pure checks require no local firmware; corpus tests skip when local
artifacts or Capstone are absent.

Arithmetic and timing remain unverified on hardware. Higher-arity header ranking,
special short operations and other transfer windows were left unresolved.
