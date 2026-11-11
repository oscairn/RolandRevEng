# FDRV cubic waveshaping and short-add cutpoints

2026-11-10. Static Python/Capstone analysis and explicitly isolated native arm64
execution. Native ZENOLOGY SHA-256:
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom-0 v1.08 CORE1 payload SHA-256:
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
FDRV is a different algorithm from FETDRIVE. No BMC hardware was accessed.

**Result:** four native FDRV waveshaping windows compute
`x * (x*x + (3 - abs(3*x)))`. Their source and destination records are bound to
actual DSP data operands. All five Fantom FDRV placements retain the packet
contexts and relative resource relationships. The reference agrees bit for bit
with an isolated native window on 1,034 inputs, including signed zero and the
smallest positive and negative subnormals.

**2026-11-11 update:** the exact 126-byte `cubic_quad` profile now executes in
the strict emitter/interpreter. A ten-byte authored preload supplies the first
left and incoming second-right samples; the following 116 bytes match stock
FDRV `378..3ec`, including all five Fantom relocations. Independent four-input
vectors and the isolated native curve match bit for bit. The full native callback
also supplies input/output cutpoints for a conditional window comparison; these
captured inputs do not constitute an independent whole-FDRV model. No general
opcode, complete FDRV program or hardware precision policy is admitted.

## Four separate native input/output windows

The call-free native callback is `3050ec..305ea8`. The checker reconstructs its
constructor records independently and uses the existing pointer/index provenance
tracer. Each source load and result store must use the proved data path, a masked
index and an unsigned scaled double access. It also checks the actual d0 load,
the arithmetic instructions and the d0 store, retaining d0 and constant-register
provenance across intervening instructions.

Offsets and cells below are hexadecimal. Source-transfer fields and representative
constructor fields can differ: a constructor may reuse the record for an earlier
store to the same cell. The checker compares both actual field values.

| Source cell | Source-transfer field | Constructor representative | Native source load | Native addition | Result store / field / cell |
|---|---|---|---|---|---|
| `e` | `376` | `36a` | `3059fc` | `305a1c` | `305a30` / `3b2` / `12` |
| `10` | `3a4` | `360` | `305a40` | `305a5c` | `305a70` / `3dc` / `18` |
| `f` | `384` | `374` | `305a80` | `305a9c` | `305ab0` / `3c4` / `13` |
| `11` | `3b4` | `382` | `305ac0` | `305adc` | `305af0` / `3e6` / `1a` |

The native arithmetic forms `3*x`, `x*x` and `-(3*x)` independently, selects the
nonnegative magnitude, subtracts it from three, adds the square, then multiplies
by x. Three is an actual `FMOV` immediate at `305a00`; its register stays intact
until the final window's subtraction. The DSP window contains the exact two-byte
`4300` literals, which decode to three. No FMA is substituted for the separate
native multiplies/additions. The fourth window reuses d1 for the subtraction and
sum; the checker retains that difference.

For the finite stock clipped-input domain `[-1,1]`, the curve is odd, maps zero
to zero and maps ±1 to ±1. At ±.5 the result is ±.875. The reference preserves
negative zero. It rejects nonfinite, boolean and out-of-domain inputs rather than
claiming a general native exception or DSP precision policy.

## What this adds to the short-add investigation

The existing [short-add inventory](short-add-context-candidates.md) found six
short-family `5d46` contexts in FDRV. Four are in state/filter sequences; two
are in the waveshaping window. The latter window interleaves two left and two
right paths in DSP packets even though native code evaluates them in sequence.

The candidate short additions associate as follows:

| Candidate DSP packet / control | Native addition in its containing curve |
|---|---|
| `392` / `1c42` | `305a1c` |
| `3c6` / `1c42` | `305a5c` |
| `39c` / `5d46` | `305a9c` |
| `3d0` / `5d46` | `305adc` |

Thus packet `39c` corresponds to the first right curve, while `3c6` corresponds
to the second left curve. The new exact profile reconstructs their producers
and coissued stores, using incoming ports throughout each packet. The initial
right value is written to its own cell before that packet loads the first right
input; treating the store as observing the new load would corrupt the fourth curve.
The first-right curve finishes before its old port-5 value is stored concurrently
with the next right producers. The final packet stores the second-right curve
and reloads the first pair of shaped values into ports 2/6.

## Exact cubic profile and partial short fields

The original JSON example is `examples/cubic-quad.json`. Its four sources and
four targets are ordered `[left1,left2,right1,right2]`, all eight distinct integer
data indices below `800`. It writes all four curves plus an unchanged copy of
source right2. Final ports are `[left2,C(left2),C(left1),None,
right2,C(right2),C(right1),None]`. Each source must be supplied in the finite
checked `[-1,1]` domain. There are no coefficient reads or implicit zero seeds.

| Short controls | Functional role in the exact profile |
|---|---|
| `2410 / 6510` | I2 = 3×A; I6 = 3×B, from pool literal zero |
| `1400 / 5504` | I1 = A²; I5 = B² |
| `1440 / 5544` | I1 = I1×A; I5 = I5×B |
| `2e92 / 6f90` | I2/I6 = literal − magnitude of incoming I2/I6 |
| `1c42 / 5d46` | I1 += I2; I5 += I6 |

The first miscellaneous form uses literal pool word one, the second word zero;
both are fixed `4300` (three) here. Magnitude follows the native `>= 0` selection,
including negative zero, rather than replacing its operation order with a fused
expression. The complete profile recognizer protects controls, literal references,
headers, repeated resources and constants. General miscellaneous-header grammar
remains opaque. A familiar word outside this context is still rejected.

Ten admitted short multiplications share destination `(word >> 12) & 7`,
source `(word >> 6) & 7` and six-bit operand reference `word & 63`.
Their masked class `word & 8e00` is `0400`; the two sums normalize to `0c00`.
This is a **partial field map**, not permission to execute arbitrary masked-class
matches. Only ten whitelisted multiplies, the two exact miscellaneous forms and
complete checked profiles execute. Operand references below eight select ports;
`10` selects literal pool word zero in this window. Other references and all
other families remain unadmitted. In the earlier filter, `6547` can now be
represented as I5×I7, but I3/I7 carry equal values there: that context alone does
not independently resolve coefficient-port choice.

The conditional full-callback check sets a nonzero declared input gain (`.75`)
to avoid a silent/default-zero cubic fixture. It captures the four source cells,
executes the actual 126-byte profile, and compares all four output cells with
the callback and scalar curve. The provenance audit rejects a later write to any
captured source/target cell. Counts remain separate from the independently
modeled first filter. Context-level `source_port_binding_verified` and
`per_packet_port_state_verified` flags describe the native cutpoint trace alone;
exact-profile packet execution supplies the additional functional interpretation,
without physical port-state observations.

## Five Fantom placements

Fantom list `610e5a94` contains five 1,420-byte FDRV programs. Its descriptors and
streams, not just copied metadata, are read by the checker. Each source cell is
the data base plus `e/10/f/11`, and each target is base plus `12/18/13/1a`.

| Program base | Data base |
|---|---|
| `4020` | `100` |
| `8040` | `320` |
| `9040` | `3b6` |
| `a040` | `44c` |
| `3020` | `c0` |

These are recorded stock placements, not new allocations or proof that a
particular effect is selected on a running instrument. Numeric equivalence and
timing on the BMC remain unmeasured. The exact cubic profile is available offline; no wrapper, transport or firmware
patch is generated.

## Reproduce and review

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --core1 local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --execute-native --native-window-frames 12000
python3.13 tools/bmc_subset.py assemble examples/cubic-quad.json local/cubic-quad.bin --stored
python3.13 tools/bmc_subset.py disassemble local/cubic-quad.bin --stored --length 126
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_fdrv_cubic_study.py' -v
```

The standalone native curve probe extracts only `305a00..305a24`, nine verified register-only
instructions, and appends a return. The resulting 40-byte function takes and
returns one double; it has no memory, calls or external references. The existing
executable-mapping helper handles permissions and instruction-cache invalidation.
The test runs this fixture in a subprocess and compares all bits at ten boundaries
plus 1,024 seeded random inputs. Other tests reject changed controls, literal,
resource aliasing, missing packets, source/result instructions, the native addition
and unknown firmware. Detailed vendor-derived output remains ignored under `local/`.

Qwen's bounded FDRV review hit its 180.2-second deadline and returned no requested
review artifacts. Its exploratory tool output was not accepted as evidence or code.
The equations, aliases and execution checks above were derived and verified locally.

The exact profile has 126 logical bytes, eleven packets and 128 stored bytes.
Append two zero padding bytes before reversing storage words; pass `--length 126`
when decoding. Never insert this storage padding between composed fragments.
Additional tests check every packet state and old-value store, independent asymmetric
inputs, signed zero, native cutpoints, all five stock bodies, mutated literals and
controls, rejected domains/aliases, nonzero padding and output preservation.

A new Qwen read-only attempt reached its 60.2-second limit without the requested
review files. A reduced no-tool review returned in 6.3 seconds, but miscopied the
right-channel inputs and made arithmetic errors. Its conclusions and exploratory
scripts were rejected. The packet model, native checks and tests above were
implemented and verified independently.

At the extended 12,000-frame checkpoint, all 48,000 conditional cubic results
match, with 47,985 distinct captured source values. The independent first-filter
check matches another 96,000 values in the same fixture.
