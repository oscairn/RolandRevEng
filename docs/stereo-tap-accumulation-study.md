# Live-coefficient stereo tap accumulation

Follow-up: [tap-feedback variations](tap-feedback-variation-study.md) distinguish
auxiliary products from unchanged main values and later accumulated feedback in
two further contexts. Equal source-port coefficients preserve an explicit ambiguity.

2026-11-10. Static follow-up to the [MAC/issue study](mac-controls-and-issue-study.md)
and [operand variants](operand-variants-and-macro-boundaries.md). Source artifact:
prepared ZENOLOGY arm64 SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
`tools/stereo_tap_study.py` requires that exact identity. No plugin, firmware,
updater or device was executed or modified. REA remains unavailable; these are
Capstone/native-byte findings, not REA-provider results or hardware observations.

## New bounded arithmetic meaning

The exact five-packet TS808 context at logical program offsets `0x1e..0x76`
contains a stereo gain followed by two live-coefficient tap accumulations. Its
packet headers already have supported layouts; this study adds no header family.

| Packet | Controls / extensions | Supported functional update in this context |
|---|---|---|
| `0x28`, header `b88d` | `0407`, `4507` | A = incoming A × I7; B = incoming B × I7 |
| `0x42`, header `8f0b` | `044f / 0000`, `454f / 0004` | A = incoming A + I1 × I7; B = incoming B + I5 × I7 |
| `0x58`, header `1005` | `048f / 0000`, `458f / 0004` | A = incoming A + I2 × I7; B = incoming B + I6 × I7 |

A/B and input ports are functional labels from the existing transfer studies.
The new result concerns the four long control/extension pairs, including the
separate first/second tap sources and preserved incoming value. This is more than
an equal-coefficient or matching-final-gain observation: all intermediate arithmetic
expressions and both final state writes match independently.

The leading packet at `0x1e` loads C4 into port 7. Packet `0x28` consumes C4 and
loads C5 for the next packet. Packet `0x42` consumes C5 and loads C6 for packet
`0x58`. Concurrent loads and stores are interpreted only within this observed
context and the already established incoming-state store behavior.

## Independent expression anchors

Let W5 and W8 be the actual native values written to DM[5] and DM[8] before the
three arithmetic stages. Earlier gain/constant shaping remains opaque and is not
assigned an invented interpretation. The four state reads and three live coefficients
are independent symbolic inputs. The complete state results are:

```text
DM[6] = W5 × C4 + old DM[6] × C5 + old DM[7] × C6
DM[9] = W8 × C4 + old DM[9] × C5 + old DM[a] × C6
```

Fresh coefficient loads use constructor-proved pointers to separate 0x48-byte
coefficient records, followed by float loads at record+0x28 and conversion to double.
Their identities are not inferred from numeric defaults or field rank alone:

| Live slot | Program coefficient address field | Native object pointer field | Native float load |
|---|---|---|---|
| C4 | `0x26` | `+548` | `0x208628` |
| C5 | `0x40` | `+550` | `0x208690` |
| C6 | `0x56` | `+558` | `0x2086c4` |

The incoming main-value stores are at `0x208678` and `0x208688`. Six distinct native
arithmetic definitions then match, not merely the final output:

| Channel | Initial gain | After first tap | After second tap | State write |
|---|---|---|---|---|
| Left | `208698` | `2086cc` | `2086d4` | `2086e8` |
| Right | `2086ac` | `2086d0` | `2086d8` | `2086f8` |

The stage expressions contain one, two and three monomials respectively. A swapped
coefficient, swapped channel/state, missing feedback term, negative tap, reordered
stage or duplicate match fails. In particular, consuming the newly loaded C6 in
packet `0x42` would select the wrong coefficient for its first-state term.

The comparison window `0x208628..0x2086f8` is fully decoded, contiguous and free
of branch/call/return/interrupt instructions. Proven input values never become
invented coefficients when their native provenance is unresolved.

## Exact record provenance and an explicit alias

The checker reconstructs constructor-written memory independently of the preserved
getter parser and requires their tables to agree. A separate native pointer/index
trace connects each required access to the actual constructor record. All eight
accesses use the established wrapper/resource/data-array path, mask `0x7ff`, and a
64-bit D-register load/store with unsigned index scaled by eight, no displacement
or writeback. Different arrays, scales, widths, masks and ambiguous records fail.

| Program-relative field | Native object address field | Access / native instruction |
|---|---|---|
| `38` | `+94` | read DM[6] at `208654` |
| `3a` | `+ac` | read DM[9] at `208668` |
| `3c` | `+8c` | write incoming A to DM[5] at `208678` |
| `3e` | `+a4` | write incoming B to DM[8] at `208688` |
| `52` | `+9c` | read DM[7] at `2086a8` |
| `54` | `+b4` | read DM[a] at `2086bc` |
| `6c`, alias of `38` | `+94` | write result to DM[6] at `2086e8` |
| `6e`, alias of `3a` | `+ac` | write result to DM[9] at `2086f8` |

The final two rows deliberately distinguish a wire address field from constructor
record ownership. The native compiler reuses the first-state address records for
those writes. There are **no separately established records owning wire fields
6c/6e**. The matcher instead proves that each final wire destination equals its
particular earlier state source, and the pointer tracer proves that native read and
write use that same earlier record. An unrelated equal-address record is rejected.

All positions are logical bytes within the primary TS808 segment; its entry is
`0x4020`. They are not standalone CORE1 runtime addresses or globally allocated
DSP data addresses. The chosen six main/state resources must be distinct except
for the two explicit read/write aliases; C4/C5/C6 must also be distinct.

## What remains unproved

This does not establish a general register-bit decoder, arbitrary destination
selection or the global meaning of long reference codes `0`, `4` or `0f`. In
particular, the different A/B extension values do not prove whether a low-six-bit
field selects feedback or whether that feedback is implicit in another control
field. That requires an independently varied encoding with the other choices held
fixed. Other occurrences of these base words outside this exact packet context
remain unsupported by this semantic checker.

The checker does not compile or emit the family. It does not prove arbitrary
resource relocation, newly scheduled programs, saturation, rounding, accumulator
width, hidden flags, cycle timing or DSP pipeline hazards. Formal polynomial
equality ignores finite-precision reassociation and is not a numeric silicon model.
The earlier constant/shaping calculation and the later literal gain are outside
the meaning assigned here. Production decoder/emitter coverage is unchanged.

## Reproduce

Use the existing prepared corpus and Capstone environment:

```sh
PY=python3
$PY tools/stereo_tap_study.py
$PY -m unittest discover -s tests -p test_stereo_tap_study.py -v
```

The report goes to ignored `local/stereo-tap-study.json`. Eight tests include
original authored packet/resource fixtures, asymmetric expression counterexamples,
cut-point/path failures, and the source-pinned native stage/record comparison.
The corpus test explicitly skips when inputs or Capstone are unavailable. No vendor
program image, native disassembly or extracted parameter table is committed.
