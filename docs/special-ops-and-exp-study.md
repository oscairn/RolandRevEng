# Exceptional short controls and native exponential cutpoints

2026-11-10. Static follow-up using the same ZENOLOGY arm64 artifact as the header
study. No native or DSP function is executed. This identifies useful reference-function
windows and tightens the decoder's rejection boundary; it does not assign an `EXP`
mnemonic to an isolated BMC opcode.

## What can be established independently

The Mach-O indirect-symbol table identifies native call stub `0x6d886c` as `_exp` and
`0x6d8adc` as `_log`. These names come from `xcrun otool -Iv`, rather than guessing a
function from neighboring strings or its position in a call sequence.

UPLIFT_EXCITER has two direct `_exp` calls. For each, the native D0 argument is also
stored to a proven data-array location before the call, without an intervening write to
D0. The returned D0 is then stored to another proven data-array location, again without
an intervening overlapping floating-register write or call. Fresh constructor recovery
establishes which data-symbol record each access uses. Those records locate particular
address fields within the BMC program, rather than merely matching equal address values.

| Native `_exp` call | Argument also stored at | Argument BMC address-field offset | Return stored at | Return BMC address-field offset | Exceptional short control between fields |
|---|---|---|---|---|---|
| `0x8bbe4` | Data index `0x8`, native store `0x8bbbc`, object field `+0x2ac` | `0x46a` | Data index `0xb`, native store `0x8bbf4`, object field `+0x2bc` | `0x4e2` | `20a0` in packet starting `0x46c` |
| `0x8bc40` | Data index `0x6`, native store `0x8bc3c`, object field `+0x2a4` | `0x4e4` | Data index `0xa`, native store `0x8bc50`, object field `+0x2b4` | `0x55e` | `20a5` in packet starting `0x4e6` |

Thus the native reference value written at `0xb` is `exp(argument also written at 0x8)`;
the value written at `0xa` is `exp(argument also written at 0x6)`. This is stronger than
aligning the first unknown opcode with the first library call: source/destination record
identity and actual D0 def/use delimit both windows independently.

The intervening BMC regions contain long arithmetic and polynomial-looking constants
in addition to the exceptional short control. They are **candidate exponential macro
windows**. The evidence does not separate the short operation from its surrounding
range reduction, polynomial and output operations, nor show that the DSP approximation
is numerically identical to native libm `exp`.

## Why the ordinary literal syntax remains unproved

The relevant observed controls are:

| Short control | ZENOLOGY observations | bmc0 observations | bmc1 observations |
|---|---:|---:|---:|
| `20a0` | 5 | 9 | 1 |
| `20a4` | 3 | 4 | 1 |
| `20a5` | 2 | 0 | 0 |
| `30a0` | 0 | 5 | 0 |
| `30a2` | 8 | 22 | 6 |
| Total | 18 | 40 | 8 |

These totals include repeated/relocated images. `20a0` and `30a0` would read a three-byte
literal starting inside the long extension under the regular six-bit hypothesis. Other
variants accidentally fit by reading a subset of already covered literal bytes. That
fit does not establish their operand roles.

For example, UPLIFT_EXCITER's first window and TRANSIENT's corresponding constant-bearing
packet use the same two explicit four-byte constants, but adding a transfer moves their
payload positions and changes the extension word. A supposed `20a0` literal would then
change solely because the pool was rearranged. The low indices `0`, `2`, `4`, `5` also
vary alongside otherwise closely related polynomial regions. These observations motivate
a register/special-state hypothesis, but do not prove that encoding or a particular
arithmetic operation.

`header_study.layout()` therefore rejects all five observed controls. This removes
46 previously admitted packets, leaving **41,710 structurally admitted observations**.
It does not alter raw byte-preserving packet parsing. The existing single GASSPH
adjacent-symbol ownership conflict also remains explicit and unchanged.

## Reproducible method and limits

`tools/special_ops_study.py` reuses the existing constructor-memory reader and native
pointer-provenance model. It supplies each address field as a distinct record marker;
two equal numeric addresses do not become interchangeable record identities. Stores
must use a 64-bit D0 value and an unsigned 32-bit index scaled by eight, with no added
displacement or writeback. The reference checker requires no overlapping D0/S0/
vector writes between a store and the call. It admits only straight-line prefixes with
the identified pure `_exp`/`_log` imports; another call or control-flow branch ends the
trace. It does not model arbitrary arithmetic as a function with an invented name.

TRANSIENT also contains two `_exp` import calls and analogous exceptional/polynomial
regions. However, its native body reaches a conditional branch at `0x1d6128` before
those calls. The bounded tracer stops there. It reports the imports and exceptional
controls but **no proven cutpoint pairing** for that class. Extending the analysis would
need path-sensitive state merging or a separately justified straight-line entry state.

Run from the project directory with local artifacts, Capstone and Xcode tools available:

```sh
python3 tools/special_ops_study.py
python3 -m unittest discover -s tests -p test_special_ops_study.py -v
```

Detailed source-bound addresses go to ignored `local/special-ops-study.json`. Five tests
cover indirect-symbol parsing, distinct field identities at equal addresses, argument
and return overwrites, overlapping vector writes, a wrong pointer path/index scale, branch/unknown-
call termination and the two local UPLIFT_EXCITER cutpoints. The synthetic instructions
are original authored fixtures, not copied vendor code.

An isolated exceptional-opcode meaning, its destination/special state, the exact BMC
exponential approximation, valid input range, rounding, saturation and timing remain
unresolved. Reusing a stock macro window in a newly scheduled DSP program is not yet
established as safe or correct.

## TRANSIENT callback execution boundary

The complete pinned native `SIM_MFX_TRANSIENT` callback is now inventoried
for a separate execution fixture. It spans `1d5fd0..1d66c4`, with 445
contiguous ARM64 instructions and one final return. There are eight internal
forward branches, no `ADR/ADRP`, and no indirect calls or branches. The
three external calls resolve through the actual Mach-O import table.

| Native call | Target stub | Imported function |
|---|---|---|
| `1d606c` | `6d8adc` | `_log` |
| `1d647c` | `6d886c` | `_exp` |
| `1d6518` | `6d886c` | `_exp` |

These are the complete call set in the checked span. Unconditional `b`
instructions are internal jumps. Capstone also labels ARM64 `bl` as both
CALL and JUMP, so classification must handle calls before ordinary jumps.

Fresh constructor extraction initializes bytes through object offset `65f`.
The four live-coefficient pointer fields are `660/668/670/678`, slots
`0/1/2/3`. An explicit context therefore needs at least `680` bytes.
The primary DSP segment is 808 bytes. Initial native pointer loads follow
the established wrapper/context/ring graph. These bounds informed the
execution fixture below; metadata alone did not establish its memory setup.

This callback cannot be copied using the call-free LINE/FETDRIVE procedure
unchanged. Its three external `bl` instructions require deliberate host-math
resolution. Internal relative branches must retain their destinations, and
the callee-saved register/stack contract must remain intact. The fixture below
resolves these dependencies explicitly.

Tool-enabled Qwen produced the initial metadata. Local review corrected its
three internal jumps misclassified as unknown calls, its conditional-branch
count, and FP loads included in a purported GPR list. Independent extraction
asserted the callback bounds, complete decoding, import identities, branch
targets and constructor layout. Raw and reviewed JSON remain ignored under
`local/transient-metadata-worker/`. This metadata-only pass did not execute
the callback. The subsequent execution work is recorded below.

## Native TRANSIENT fixture and conditional envelope reference

`native_transient_reference.py` now executes the complete pinned callback
in a separate macOS ARM64 process. The new `native_math_bridge.py` validates
the entire instruction stream, checks the exact three original call targets,
and rewrites their `bl` instructions to two local process-libm trampolines.
Internal branches keep their destinations. Each trampoline uses caller-saved
X16 and preserves the original call's return address. Its host pointer is
literal data and is excluded from instruction decoding and report metadata.

The relocation helper rejects unexpected calls, external/indirect branches,
ADR/ADRP, PC-relative literal accesses, interrupts and early/unusual returns.
It validates relocation rather than arbitrary machine-code safety; the
fixture separately pins the source image and callback bounds. Authored ABI
snippets test single `log`/`exp` calls and a two-call composition in isolated
processes before any vendor callback execution. The helper checks signed BL
range; tests cover nonzero source bases, shared trampolines and malformed streams.

Memory is explicit: a `680`-byte coefficient/address context, four live
coefficient records with binary32 slots `(1, 0.5, 0.25, 0.125)`, a cold
2,048-double sample ring, and an owner buffer covering `120` bytes.
TRANSIENT uses two additional three-double caches at owner+`a0` and
owner+`100`, with cursors at `b8/118`. The common fixture allocation now
covers both. Their cursors begin and end at zero under this experiment.
Constructor defaults are retained. The host supplies zero wrapper base,
one origin step per generated frame, and 48 kHz software input tones.

The first native peak store at `1d6064` is the larger absolute channel input
times the owned normalization default `0.02476228209191759`. The following
log store at `1d609c` uses native `log`, replacing its zero-input result with
the explicit constant `-22.18070977791825`, equal to `log(2^-32)`.
The fixture checks both retained stores bit for bit on every frame.

Two independently evaluated kernels then check the exponential envelopes
and output gain. Let `a/b` be the new envelopes. Their arguments come from
native cells `24/25` in hexadecimal; previous states are read before invocation
from `27/29`. Current envelope stores use `26/28`. The native D0 argument
to the first exp is unchanged after its saved store; the second uses D8,
whose low 64 bits are also preserved by the libm ABI.

```text
delta = exp(argument) - previous
next = fma(delta, above_rate if delta > -2^-32 else below_rate, previous)
product = a * b
gain = fma(a - product, C3, 1 + fma(1 - a, C1, product * C2))
output = (input * gain) * C0
```

The finite reference preserves the native operation order. The four live
values are read as binary32. For the supplied positive C1/C3, the selected
constructor rates are

| Envelope | Rate above the delta threshold | Rate at/below the threshold |
|---|---:|---:|
| First | `0.0028454592029794057` | `0.13258300293690084` |
| Second | `0.02809113921598716` | `0.0028454592029794057` |

The negative-epsilon threshold is strict, so small negative deltas can select
the above-threshold rate. Separate tests distinguish the exact boundary and
its neighboring binary64 value. The gain store is cell `10` in hexadecimal.
The owner cache round trip supplies the current `a-product` term in this fixture.

A 12,000-frame run matches 24,000 peak/log values and 60,000 envelope/gain/output
values bit for bit. Peak stereo output is `0.14596584013287234`; RMS is
`0.07554220759649252`. Subprocess tests cross sample-ring wrap at 2,056 frames,
check fresh-render determinism and preserve existing output files.

This is a conditional output reference: upstream detector arguments remain
native-computed. The JSON keeps `full_output_reference_verified=false` and
`upstream_arguments_from_native=true`. No BMC instructions run in this native
fixture. Its hardware precision, parent cadence, warm state, sample-rate
initialization and preset calibration remain unverified.

```sh
python tools/native_transient_reference.py local/native-transient-reference.wav \
  --frames 12000 > local/native-transient-reference.json
python -m unittest discover -s tests -p 'test_*transient*reference.py' -v
python -m unittest discover -s tests -p test_native_math_bridge.py -v
```

Qwen's bridge draft had relocation-base, branch-range and code/data decoding
errors and reached its time limit. The retained helper was corrected locally
and verified with authored snippets before running the pinned callback. A
misplaced worker test draft was preserved under ignored worker output.
Unfinished bridge drafts and vendor bytes remain local; reviewed code is tracked.

## Paired native amplitude-scale candidates

TRANSIENT's peak normalization is the binary64 reciprocal of the OSC default
gain `40.384`. FETDRIVE's drive-scale default is that normalization divided
by sixteen. These numerical relationships and native uses are observed
directly in the pinned artifact.

| Native class | Native load | Object double field | Representative DSP field | Native default |
|---|---|---|---|---|
| OSC | `29820` | `98` | `2cc` | `40.384` |
| TRANSIENT | `1d6040` | `28` | `12` | `0.02476228209191759` |
| FETDRIVE | `2f7e58` | `58` | `3a` | `0.0015476426307448495` |

The latter two have independently decoded owned width-three literals.
OSC's containing mixed packet remains outside the ordinary layout decoder;
its row describes a native constructor record and use, without new layout
admission. These paired scales suggest a shared native amplitude convention.
They do not establish a universal PCM full scale or the physical BMC data
representation. Audio-boundary tracing and hardware calibration remain required.
