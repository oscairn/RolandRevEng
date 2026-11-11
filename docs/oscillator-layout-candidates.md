# Six oscillator literals: references recovered, arity still partly ambiguous

2026-11-10. Follow-up to [the oscillator anchors](operand-variants-and-macro-boundaries.md#named-oscillator-anchors-expose-the-next-layout-gap).
This uses the existing bmc0 CORE1 artifact, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`,
and ordinary static Python/Capstone analysis. No REA provider was available in this
worker; these are reproducible local byte observations, not REA Evidence records.
No target code, device access, upload, firmware packaging or flashing occurred.

The six owner-proven named coefficient records can all be explained by the existing
six-bit reference encoding. Two packet contexts constrain the ordinary arithmetic
arity uniquely. The other two retain a real ambiguity, which prevents a justified
decoder expansion.

A later [cross-context comparison](#cross-context-reuse-of-3074) finds
`3074` in ordinary short-operation slots and binds its FREQ_SHIFTER
literal to a following port-3 store. This favors the short interpretation
for the test oscillator while retaining the unknown bundled controls.

## Exact fields

All offsets below are bytes relative to the normal DSP4 primary segment, base `0x20`,
stored source `0x610a5614`, list `0x610a1f18`. A reference's low nibble is a **byte**
offset in the common pool. Width is encoded by its upper two bits, independently of
the literal's numeric value. These results reuse the owner records and source checks
in `oscillator_regions_study.study()`; no symbol association by adjacency is added.

| Packet / header | Named literal | Encoded reference | Field / width |
|---|---|---|---|
| `0x0 / bd4b` | SineFreq | `3074 & 3f = 34`, pool+4 | `0x12 / 4` |
| `0x2a / 5c07` | ImpulseRate | `4d20 & 3f = 20`, pool+0 | `0x34 / 3` |
| `0x5e / a50c` | SineLev | `28a6 & 3f = 26`, pool+6 | `0x70 / 3` |
| same | WhiteLev | extension `6a40`, bits 11:6 = `29`, pool+9 | `0x73 / 3` |
| `0x7e / 4d0d` | ImpulseLev | `2d64 & 3f = 24`, pool+4 | `0x8c / 3` |
| same | DCLev | extension `2037`, bits 5:0 = `37`, pool+7 | `0x8f / 4` |

The `4d0d` context also has a four-byte reference from `0c3b` at relative `0x93`.
This extra reference is structurally useful; it has no newly assigned parameter name.

## Which ordinary arities survive?

`tools/oscillator_layout_study.py` checks only the four exact observed header/control
contexts. It preserves miscellaneous slots as **unknown**, removes them from a
temporary analysis packet, and projects the remaining arithmetic and transfer slots
into the existing bounded `header_study.layout()` checker. The common pool is preserved
byte for byte. Returned offsets and operation indices are restored to their original
packet positions. No firmware or runnable packet is emitted.

Every long/short assignment to the arithmetic slots is tested. Literal bounds,
extension ordering, literal/extension separation and full pool coverage are checked
by the existing helper. All surviving candidates must independently match all six
named width/position anchors. The temporary projection assumes no extra pool fields
for the opaque slots; it does **not** prove they lack hidden references, aliases,
state changes, flags or scheduling effects.

`0` below means an ordinary long operation, `1` an ordinary short operation. Numbers
identify the original control slots, starting at zero; they are not DSP registers.

| Context | Arithmetic controls tested | Surviving arities | What is ruled out within this model |
|---|---|---|---|
| `bd4b` | slot 0: `3074` | `[0]` and `[1]` | Neither arity is eliminated by the named literal or pool coverage |
| `5c07` | slots 0,1: `08c1`, `4d20` | `[1,1]` | Every ordinary long assignment overlaps the rate literal with an extension |
| `a50c` | slot 0: `28a6` | `[0]` | A short form leaves pool bytes unexplained and cannot explain the WhiteLev reference |
| `4d0d` | slots 0,1: `2d64`, `0c3b` | `[0,1]` and `[1,0]` | Two short forms leave bytes unexplained; two long forms overlap a literal with an extension |

The `bd4b` ambiguity is easy to miss. Its first pool word is `000c`. Interpreting it
as a long extension yields only register references 0 and 12, while a transfer also
references that same word as an address. The existing decoder permits an extension
and address to alias. A short interpretation requires no extension; its known
literal and transfer fields already cover the pool. Rejecting the long form solely
to obtain a unique answer would add an unproved no-alias rule.

In `4d0d`, assigning extension `2037` to either arithmetic slot explains the same
named literal bytes. DCLev is therefore tied to the extension's low-six-bit reference,
but its owning arithmetic operation is not independently identified by these anchors.
Assuming the usual long-before-short ordering selects `[0,1]`; ordering itself is
part of the missing header proof and is not used to discard `[1,0]` here.

The opaque slots are `ff75`, `ef75`, `00d7` in `bd4b`; `eef6` in `5c07`;
`8ed8`, `00d5` in `a50c`; and `1220` in `4d0d`. They remain opaque in the report.
No waveform generation, recurrence, breakpoint, LFSR, mute, branch or arithmetic
meaning follows from the parameter names or these structural fits.

## Smallest remaining proof

For `bd4b`, establish the ordinary operation family of slot 0 from an independent
header decoder or a matched native dataflow requiring its extra operands. For
`4d0d`, identify which arithmetic operation owns `2037` using equivalent independent
evidence. A constrained lexicographic family ranking can suggest an ordering but
does not supply that evidence. The next missing layer is the miscellaneous controls'
syntax and state effects, followed by oscillator recurrence and scheduling.

A bounded no-tools Qwen draft was requested through OMP on the Mac Studio and reviewed.
Its proposed `3074` long assignment, count-five slot list and rank argument were
rejected: the first skipped the alias ambiguity, the second had six slots, and the
third dropped families 2/3 from the supplied alphabet before claiming no intervening
multisets existed. No Qwen code or asserted family mapping was accepted.

## Cross-context reuse of `3074`

The control-slot inventory covers the same 241,742 framed packets as
the conversion-control search. The table counts occurrences across
render-list segments, including repeated banks and placements.

| Artifact | `3074` classified short | `3074` under an unresolved header | `2d64` / `0c3b` |
|---|---:|---:|---|
| ZENOLOGY | 9 | 0 | absent |
| Fantom BMC0 CORE1 | 16 | 1 | one each, unresolved |
| Fantom BMC1 CORE1 | 2 | 0 | absent |
| JUPITER-X CORE1 | 45 | 0 | absent |
| MC-101 CORE1 | 2 | 16 | absent |
| SH-4d CORE1 | 45 | 0 | absent |

All 119 classified `3074` occurrences occupy family 1, under headers
`3408`, `5f0b` or `2d08`. The unresolved Fantom occurrence is the
`bd4b` test-oscillator packet. MC-101's unresolved occurrences use
`af8c`. The inventory preserves unresolved classifications as null.
It searches base control slots, excluding coincident words in payloads.

The desktop programs give an additional independent binding.
FREQ_SHIFTER packet `0` has header `5f0b` with `3074/7078`,
two indexed input loads, and width-four literals at `e/12`.
Fresh native constructor records bind the doubles at `108/118`
to those two fields. Native loads at `455cc/455e0` carry their
values unchanged into stores at `45600/45614`. The matched
constructor data records bind these stores to fields `28/2a`,
cells `0/d`. In the next DSP packet those are the `bfe4/ffe6`
stores, from functional ports 3 and 7. The check follows register
preservation and record identity independently of equal defaults.

BPMLP and DJFXLP give ordinary `3408` contexts. Their `3074`
literal fields at `ca/182` also have owned native constructor records.
Taken together, these observations support `3074` as a short literal
operation in the oscillator. Applying a fixed arity across these
contexts selects the short candidate from the earlier pool-only
projection. The oscillator's opaque controls and recurrence remain open.
The raw projection continues to retain its two candidates so that this
additional assumption is visible.

```sh
python tools/oscillator_literal_study.py > local/oscillator-literal-study.json
python tools/oscillator_control_inventory.py \
  --core1 local/b0c1a.bin --core1 local/b1c1a.bin \
  --qspi local/crossmodel/jupiter-x/MI077_C1A_up.bin \
  --qspi local/crossmodel/mc101/RPG69_C1A_up.bin \
  --qspi local/crossmodel/sh-4d/DD013_C1A_up.bin \
  > local/oscillator-control-inventory.json
```

## Reproduce the original pool projection

```sh
python3 tools/oscillator_layout_study.py
python3 -m unittest discover -s tests -p test_oscillator_layout_study.py -v
```

Use the existing Capstone-capable Python environment. The report is written to ignored
`local/oscillator-layout-study.json`; it contains fields, candidates and explicit
unknowns, not complete vendor programs. Five tests cover extension/address aliasing,
extension-owner ambiguity, the uniquely constrained short/long contexts, malformed
or changed control contexts, unchanged production-decoder rejection and the optional
six owner-proven corpus anchors. Four tests run without the vendor corpus or Capstone.

The production layout decoder and emitter are unchanged. A complete engine, hardware
precision/timing, safe loading and physical audio routing remain unverified.

The separate [MFX OSC phase study](oscillator-phase-study.md) binds a
stored phase step, its owned frequency field and four Fantom placements.
