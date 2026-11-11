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
smallest positive and negative subnormals. No individual BMC control or complete
FDRV program is admitted to execution by this cubic pass. The subsequent
[auxiliary/add-MAC study](auxiliary-save-restore-and-add-mac.md) admits a separate
exact context from the earlier state/filter sequence; the cubic producer window
remains outside the strict interpreter.

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

Thus packet `39c` does not simply correspond to the second native curve in
listing order. The source/result field bindings constrain the whole window.
They do not separately prove the values entering the short operation's ports.
The miscellaneous `2e92/6f90` controls and preceding producers still matter.
The numerical sum alone cannot establish their individual effects, issue order,
or all live port state. In particular, the two-byte word `5d46` remains a bounded
short-add candidate, not a general executable `I5 += I6` definition.

The four earlier `5d46` contexts have coissued data stores and longer filter/state
producer sequences. They are not treated as four additional cubic curves or
silently folded into this reference. Their state/auxiliary-port relations and
the corresponding PHONO sequences remain useful next comparisons.

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
timing on the BMC remain unmeasured. This cubic reference adds no strict
interpreter or emitter profile; no wrapper, transport or firmware patch is generated.

## Reproduce and review

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --core1 local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --execute-native
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_fdrv_cubic_study.py' -v
```

Native execution extracts only `305a00..305a24`, nine verified register-only
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
