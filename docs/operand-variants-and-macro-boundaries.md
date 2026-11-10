# Operand variants and exceptional-macro boundaries

Follow-up: [oscillator layout candidates](oscillator-layout-candidates.md) explains
all six owned oscillator literal references while retaining two arity ambiguities.
The production decoder and emitter remain unchanged.

2026-11-10. Follow-up to the [MAC/issue study](mac-controls-and-issue-study.md),
[exceptional controls](special-ops-and-exp-study.md), and
[native primitives](native-arithmetic-primitives.md). This uses ordinary Capstone
analysis of the existing local artifacts. REA tools are not exposed in this worker;
the previously unavailable Hopper provider was not retried. No target code, device,
firmware packager or shell update was run.

The arm64 artifact is SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
CORE1 identities remain those in the main packet/loader map. Detailed expressions,
constructor records and disassembly stay ignored under this worktree's `local/`.

## Exact functional comparisons

`tools/operand_variants_study.py` checks three new comparisons. These are bounded
mathematical expressions, with independent symbolic inputs and live coefficients;
they establish neither floating-point equivalence nor hardware precision/timing.

| Program context | Operation | Independently checked result |
|---|---|---|
| CHO_JU106 first three packets, `0x0..0x1a` | `080b / 42c0` at `0xe` | A = input0 × C3 + input1 × C3; stored at DM[0] |
| FETDRIVE three-packet family `0x88..0xa8` | `4e0b / 22c1` at `0x98` | B = DM[8] + (DM[a] − W(7)) × W(5); stored at DM[9] |
| FETDRIVE three-packet family `0x11e..0x13e` | `4e0b / 22c1` at `0x12e` | B = DM[c] + (DM[e] − W(b)) × W(6); stored at DM[d] |

`W(a)` is the actual native value stored at address a before the result. It is an
independent cutpoint, not a claim to understand its earlier computation.

CHO_JU106 loads input0 through `0fe0`, input1 through `4fe2`, and C3 through `3fe4`
in header `3e07`; a pure `0803` long-operation packet follows. The next `0c03/8fe0`
store independently identifies the resulting A value. Both input symbols and the
constructor-proved coefficient record must appear. The native sequence multiplies
one input and then uses FMADD for the other. A single-channel gain, C-slot substitution
or subtraction fails the comparison. Since the same coefficient multiplies both
inputs, this does **not** distinguish `(A+B)×I3` from two separately rounded products,
or identify an ordered three-operand bitfield. It only proves the displayed expression
in this exact context.

The FETDRIVE family is more informative about destination selection. Its precursor
packet contains `bedb`, loads `1fe0/2fe2`, and stores through **`8fe4`**. The operation
packet stores the factor through `bfe2`; the following packet stores its result through
**`cfe0`**. Thus the saved incoming main value is **A**, while the result goes to **B**.
Calling this `B = I1 + (I2 − incoming B) × I3` would confuse destination and source.
Within this family the functional expression is instead consistent with
`B = I1 + (I2 − incoming A) × factor`.

The factor written through `bfe2` is exactly the value multiplying both the positive
I2 term and negative incoming-A term. Its port-3 interpretation agrees with the
already established load/store port convention. This is the first checked use here
of that factor-store control in this context. It does not establish every `bfe*` form
or the behavior of a different co-issued operation.

Crucially, `bedb` remains opaque. These FETDRIVE comparisons prove the **admitted
three-packet family**, rather than a freestanding `4e0b` instruction that can be
scheduled after arbitrary code. Any undocumented precursor/special-state effect
remains a limitation. Neither a general destination-bit decoder nor a new emitter
template is justified by these observations alone.

## Native evidence and field identity

| Context | Native comparison window | Cutpoint stores | Result store |
|---|---|---|---|
| CHO_JU106 | `0xadb68..0xadba0` | Fresh input loads and live C3 load | `0xadba0` |
| FETDRIVE first family | `0x2f7f04..0x2f7f5c` | incoming A `0x2f7f24`, factor `0x2f7f40` | `0x2f7f5c` |
| FETDRIVE second family | `0x2f8034..0x2f808c` | incoming A `0x2f8054`, factor `0x2f8070` | `0x2f808c` |

Each window is completely decoded and has no branch, call or return. Native
register definitions yield the complete two- or three-term polynomial, including
the negative term. Duplicate/equal/late cutpoints and opaque downstream arithmetic
are rejected. Earlier native shaping remains opaque instead of being replaced by
an invented arithmetic operation.

The checker also independently reconstructs constructor memory using
`transfer_study.constructor_memory()`. The reconstructed tables must agree with the
existing getter extraction. A separate pointer/index provenance trace must connect
each required read/write to its **exact program operand-field offset**, rather than
just an equal numeric data address:

| Family | Program field → native object field → native access |
|---|---|
| CHO result | `0x18 → +0x174 → 0xadba0` |
| FET first I1 | `0x92 → +0x4fc → 0x2f7f04` |
| FET first I2 | `0x94 → +0x504 → 0x2f7f14` |
| FET first incoming A | `0x96 → +0xac → 0x2f7f24` |
| FET first factor | `0xa0 → +0x9c → 0x2f7f40` |
| FET first result B | `0xa6 → +0xb4 → 0x2f7f5c` |
| FET second I1/I2 | `0x128/+0x50c/0x2f8034`, `0x12a/+0x514/0x2f8044` |
| FET second incoming/factor/result | `0x12c/+0xbc/0x2f8054`, `0x136/+0xa4/0x2f8070`, `0x13c/+0xc4/0x2f808c` |

All these accesses use the established native data-array path
`wrapper → +8 → +0x18 → +0x10 → +0x18`, index mask `0x7ff`, and a double load/store
with `UXTW #3`, no displacement or writeback. Wrong paths, scales, widths, masks,
ambiguous records and equal-address records with different field identities fail.
Constructor coefficient pointers are independently checked through the existing
0x48-byte coefficient-record path. None of these desktop layouts assigns a physical
DSP register, bus or silicon storage width.

## Shaping and shifts: whole regions versus individual operations

Direct inspection of the same FETDRIVE native body gives a useful reference boundary
for its opaque precursor. Let T be the native value already written at DM[3] or DM[4]:

| Channel | T store / program field | Rational calculation | Clamp / factor store / program field |
|---|---|---|---|
| First | `0x2f7ee4 / 0x6a` | `0x2f7ee8..0x2f7ef4` | `0x2f7f28..0x2f7f30`, `0x2f7f40 / 0xa0` |
| Second | `0x2f8018 / 0x100` | `0x2f801c..0x2f8024` | `0x2f8058..0x2f8060`, `0x2f8070 / 0x136` |

For finite, nonsingular arithmetic, the native reference factor is
`clamp((2−T)/(2+T), −1, +1)`. The first channel forms numerator/denominator with
FSUB/FADD and FDIV, then FMIN with +1 and FCMP/FCSEL with −1. The second channel
does the same with different live registers. This bounds the **whole DSP region
between the recorded T and factor fields**, including several short controls and
`bedb`. It does not identify which control implements division, clamp, reciprocal
refinement or a special-state transfer. No rounding, singular-input or NaN behavior
is assigned to DSP `bedb` from the native function.

Before those regions, native `0x2f7e74..0x2f7e88` and
`0x2f7fe0..0x2f7fec` contain a signed fixed-point conversion with 32 fractional bits,
a **64-bit left shift by 9**, signed integer-to-double conversion, and multiplication
by `2^-32`. The scalar input to the conversion is independently formed by the prior
native multiply. In the range where the conversion and shift do not overflow, this
is mathematically `512 × trunc(x×2^32) × 2^-32`, subject to native conversion rounding.
It is not an ordinary smooth gain for arbitrarily small asymmetric x: truncation is
toward zero. Outside that range the 64-bit shift discards high bits; no unbounded
`512*x` identity is valid. This is native sequence evidence, **not** a recovered
DSP shift encoding or proof of the render DSP's accumulator width.

## Exceptional macros: a stronger negative result for TRANSIENT

The existing UPLIFT_EXCITER cutpoints reproduce unchanged: two independent native
argument/result stores delimit the `20a0` and `20a5` candidate exponential windows.
All five observed `20a*`/`30a*` forms remain rejected by the operand-layout decoder.
There is still no isolated-opcode or special-state proof.

TRANSIENT needs more than simply lifting the old tracer's branch barrier at
`0x1d6128`. Its `_exp` returns are **modified before the next result store**:

- Call `0x1d647c`: D0 is first modified by `FSUB` at `0x1d6490`, then passes
  coefficient-selected FMADD/FCSEL operations before the store at `0x1d64dc`.
- Call `0x1d6518`: D0 is modified by `FSUB` at `0x1d651c`, then FMADD/FCSEL operations
  precede the store at `0x1d653c`. The argument was copied from D8 at `0x1d6514`;
  the earlier independent argument store uses D8, not D0, at `0x1d6478`.

Consequently the existing unchanged-D0 argument/result rule cannot produce two new
pure-exponential cutpoint pairs even with the branches removed. The smallest missing
proof includes argument-copy provenance, path-sensitive entry state and the actual
post-exponential smoothing/selection expression. Equating its two import calls with
its two exceptional controls would silently skip all of those operations.

The 75 paired render-class `VSubProc` bodies were also rescanned through each first
return for direct BL calls to exported `sat`, `saw`, `tri`, `lfs`, `enve`, `bpchk` and
`bpchk_flg`: none were found. This is a bounded negative search; inlined forms and
indirect calls remain possible. In particular, native breakpoint equality returning
512 still has no independently paired DSP flag encoding. A boolean substitution or
an oscillator/LFSR assignment based on a nearby helper name is not justified.

## Named oscillator anchors expose the next layout gap

`tools/oscillator_regions_study.py` follows the ordinary DSP4 list and each of the six
previously established owner-proven coefficient records. It checks list/DSP identity,
primary-segment ownership, absolute/relative addresses, supported literal width and
complete field containment in the packet payload. It then asks the existing layout
decoder to explain the packet without extending its grammar:

| Named field | Relative byte / width | Containing packet / header | Current result |
|---|---|---|---|
| SineFreq | `0x12 / 4` | `0x0 / bd4b` | Unsupported header |
| SineLev | `0x70 / 3` | `0x5e / a50c` | Unsupported header |
| ImpulseRate | `0x34 / 3` | `0x2a / 5c07` | Unsupported header |
| ImpulseLev | `0x8c / 3` | `0x7e / 4d0d` | Unsupported header |
| WhiteLev | `0x73 / 3` | `0x5e / a50c` | Unsupported header |
| DCLev | `0x8f / 4` | `0x7e / 4d0d` | Unsupported header |

These six anchors occupy four packets, all before relative `0x98` in the normal
`0x35b6`-byte DSP4 primary segment. Named sine/noise/DC levels sharing a packet do
not prove which base operation generates any waveform. The immediate missing proof
is the operand layout for these four header contexts, followed by independent native
or hardware dataflow for the oscillator state/update. The MFX opcode mappings above
do not supply that missing DSP4 oscillator implementation.

## Reproduce and remaining work

Use the existing Capstone environment (in this session,
`/Users/jacob/.pyenv/versions/3.13.7/bin/python3`):

```sh
python3 tools/operand_variants_study.py
python3 tools/oscillator_regions_study.py
python3 tools/special_ops_study.py
python3 -m unittest discover -s tests -p 'test_*variants*' -v
python3 -m unittest discover -s tests -p 'test_oscillator*' -v
python3 -m unittest discover -s tests -v
```

New JSON reports are `local/operand-variants-study.json` and
`local/oscillator-regions-study.json`. Pure regressions run without vendor inputs;
native/provenance tests skip explicitly without Capstone or the local corpus. The
original inputs and all existing decoder/emitter interfaces are unchanged.

For the manually inspected shaping/TRANSIENT boundaries above, reproduce selected
disassembly with the existing native reader rather than executing it:

```sh
PYTHONPATH=tools python3 - <<'PY'
import parse
for cls, ranges in [('SIM_MFX_FETDRIVE', [(0x2f7e70, 0x2f7f5c), (0x2f7fdc, 0x2f808c)]),
                    ('SIM_MFX_TRANSIENT', [(0x1d643c, 0x1d653c)])]:
    _, _, code = parse.disasm_meth(cls, 'VSubProc(double const**, double**)')
    for ins in code:
        if any(lo <= ins.address <= hi for lo, hi in ranges):
            print(hex(ins.address), ins.mnemonic, ins.op_str)
PY
```

Next useful offline experiments are an isolated native/DSP boundary around `bedb`,
path-sensitive TRANSIENT smoothing expressions, and independently anchored layouts
for the four oscillator packet families. The new family checks deliberately do not
turn opaque precursors into a general arithmetic decoder or emitter. Scheduling,
precision, special flags and a complete runnable engine remain unresolved.

The actual transport conflict also still applies: normal BMC IPC uses **ttyGS0**,
which the prepared shell updates can contend with. Those packages were not changed
or used. Hardware probes, packaging and flashing remain unperformed.
