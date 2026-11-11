# EqVg generation and interpolation policy

2026-11-11. This recovers the ZENOLOGY native EqVg generator and the stock setter
decisions used by FDRV. It adds coefficient producers to the existing packet
model; it does not admit another opcode profile or establish physical BMC
arithmetic, scheduling or loading.

## Generator and numeric boundaries

`tools/eqvg_study.py` maps `CDSPCtrlEq::EqVgCal` at `20d8f4..20defc` and its
tail-called shelving helpers. The owned execution region is `20cee8..20defc`,
pinned to native SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
The eight halfword records at `7c663c` are checked against actual branch targets;
filter names are independently checked against assertion-linked strings.

| EqType | Branch |
|---:|---|
| 0 | Bypass fallback |
| 9 | EqVgPeakingCal |
| 10 | EqVgLowShelvingCalNew |
| 11 | EqVgHighShelvingCalNew |
| 12 | Bypass fallback |
| 13 | EqVgLowPassCal |
| 14 | EqVgHighPassCal |
| 15 | EqVgAllPassCal |
| 16 | EqVgBandPassCal |

The source's other out-of-switch types also take fallback; the API admits only
0 and 9..16. Cutoff zero returns `(1,-1,1,0,0)` for every admitted type. The raw
structure is **(g,b,c,d,e)**, not five conventional biquad numerator/denominator
coefficients. The damping-related coefficient b is normally negative. Q clamps
to **0.25..128**, including finite inputs outside that interval. Gain branches
use `10^(gain/20)` and, for shelving, its square root. Shelving uses tangent;
the other active branches use combined sine/cosine with the original division
order and FMA positions. See `coefficients()` for the explicit scalar formulas.

The default native rate is 44100; controlled tests also use 48000. Active types
reject cutoff at or above `rate*0.5*0.9900000095367432`, preserving the source
guard without executing assertion/logging paths. The API additionally bounds
finite gain to +/-96, requires nonnegative finite cutoff and positive signed32
rate, and rejects positive cutoff/rate ratios outside the normal binary64 domain
to exclude subnormal-angle arithmetic failures.
These are checked research API bounds, not recovered global UI ranges. Literal
encoding can impose a narrower representable range.

The owned native oracle copies original arithmetic/control flow and its required
constant pages, supplies an explicit rate, relocates math imports to host libm,
and traps excluded assertion calls. No plugin, manager, event loop or instrument
is initialized. The imports are verified using Mach-O indirect symbols:
`___sincos_stret`, `_pow`, `_tan`.

An irregular high-pass case exposed a one-ULP difference between Darwin's
combined sine/cosine operation and separate `math.sin`/`math.cos` calls. The
model uses the same combined host-libm operation on Darwin, preserving that
import's semantics without consuming native generator intermediates. Elsewhere
it falls back to separate standard-library calls; cross-platform bit identity
is not established. The regular CLI matrix matches **5,400 native coefficient
values**. Separate tests check irregular inputs and Q boundaries at both rates.

## Consumer order and coefficient offsets

FDRV's piece descriptors have flag byte 1, causing **g-1** to be stored. Copying
the raw generator tuple directly into the existing packet model is incorrect.

| Consumer | Existing model order | Native evidence |
|---|---|---|
| First live filter | `(g-1,b,c,e,d)` at C10..C14 | Descriptor `9e32a0`: raw field slots 10/11/12/14/13 |
| Second live filter | Same at C15..C19 | Descriptor `9e32d0`: 15/16/17/19/18 |
| Final literal filter | `(g-1,b,d,c,e)` | Descriptor `9e3300`, fields e8/108/f8/118/d8 in model order |

`live_coefficients()` and `output_coefficients()` make these permutations
explicit. Descriptor bytes, symbol pointers and live slots are source checked.
Live values are binary32; final-filter constructor values are binary64 before
literal conversion. For byte emission, explicitly call the existing
`encoded_taps()` codec, then the strict exact-input assembler. The assembler's
rejection policy remains unchanged.

## Interpolation stability and original setter recording

`IsStateVariableFilterInterpolationStable(double,double,double,double)` at
`20defc..20df8c` takes old/new g and b. Its pure replica matches original leaf
execution over 20,000 irregular cases plus degenerate branches. It tests the
interior minimum of the linear interpolation path after taking absolute values.
With G=abs(g), B=abs(b), the relevant Jury margin is `4-2*G*B-G*G`.
The endpoint checks are a separate requirement: equal-g/equal-b shortcuts return
true even for invalid endpoints. This predicate is not a universal certificate
for arbitrary coefficients or a guarantee for switched time-varying filters.

A concrete counterexample uses low-pass `(20 Hz,Q=.25)` and `(19000 Hz,Q=128)`
at 44100. Both endpoint recurrences satisfy the strict Jury conditions, but their
simultaneous linear interpolation crosses an unstable region. Original setter
execution returns false for that path and records a damping-first update.

`tools/eqvg_setter_study.py` executes the original bounded setters against owned
recording manager callbacks. It calls the original recovered generator and
stability function, supplies descriptor/current-value buffers, relocates the
output setter's stack guard, and never starts manager processing.

| Path | Observed decision |
|---|---|
| EqVGenv `19b8ec..19bbd4`, enveloped | Manager slot178, EnvTC selector10; unsafe path sets wait on first write only |
| EqVGenv, immediate | Manager slot188; no envelope/wait arguments |
| EqVG `354184..354490`, immediate | Manager slotc8, five literal writes |
| EqVG, interpolated | Manager slotf8, raw time argument100; safe path batches5, unsafe path batches1 then4 |

If abs(new b) is smaller than abs(current b), b is first; otherwise g-1 is
first. The remaining raw-field order is c/e/d. Tests execute both envelope
choices, both offset flags and both order branches against the original code.
The batch split and wait flag show the caller's sequencing request. Completion
timing, raw argument100's runtime interpretation and the real manager's grouped
write scheduling have not been executed or calibrated here.

FDRV SetFilter indices0/1 tail-call EqVGenv. The wrapper derives its envelope
argument by XOR1 of the manager query result (`e7550`); actual runtime selection
remains unverified. SetPostFilter index2 tail-calls EqVG with envelope=false
(`e77b8`). It is distinct from the two three-coefficient post cascades.

## Native UI dispatch and dynamic fixture

The existing `eqfa_ui_study.py` fixture now also records the EqVg subset of the
original `CMfxFDRVPrm::VUpdatePrm`. Defaults for the earlier EqFa API are retained.

| Native UI fields | Recovered filter call |
|---|---|
| 2 mode, 3 cutoff | Live1: bypass when mode0, otherwise type13; gain0, Q=0.7070000171661377 |
| 14 type, 15 cutoff, 16 gain, 17 Q | Output: lookup **0/13/14/16/9** at `83d000` |

Cutoff converts directly from signed integer to double. Gain and Q each convert
to binary32, divide by10 in binary32, then promote to double; raw Q71 becomes
7.099999904632568. Changing field2 also invokes a slope setter with mode-1;
the recorder checks that companion call. The research UI wrapper admits mode
0..2; it does not infer the complete source UI range. No live0 control route is
proved in this dispatcher. These indices are internal native-class fields,
not Fantom front-panel, MIDI or SysEx mappings.

`examples/fdrv-eqvg-events.json` contains **48 filter events**: 32 calls from
16 original UI snapshots and 16 explicit live0 setter inputs. The audio fixture
uses immediate frame-boundary updates, retains filter history and checks source
generator values before applying original setter writes to owned native state.
The independent packet model uses pure generated coefficients and checked
consumer permutations. Native live-slot routing is read independently from the
artifact's descriptors. Companion UI slope changes are not applied in this
filter-only replay; the preexisting fixture's drive/wet/level/slope values and
ZENOLOGY fixed scales stay fixed.

Both 12,000-frame runs match **24,696,000 audio/ring/cache values each**, through
five wraps, ending at origin1760. Each checks 240 generator coefficients and 240
original setter writes. Thirty-eight generated output literals differ from their
encoded values; maximum absolute error is 7.599686759895974e-6. These immediate
runs do not step coefficient envelopes.

Native-double and explicitly encoded final-filter policies are tested
separately. Output native overrides must encode to every actual stereo field,
including both occurrences of the first coefficient. Default packet evaluation
continues to use encoded values. Neither passing policy establishes physical
literal precision, and their audio is not claimed identical.

```sh
python3.13 tools/eqvg_study.py --execute-native
python3.13 tools/eqvg_study.py --execute-native --events examples/fdrv-eqvg-events.json --frames 12000 --literal-policy native
python3.13 tools/eqvg_study.py --execute-native --events examples/fdrv-eqvg-events.json --frames 12000 --literal-policy encoded
python3.13 -m unittest discover -s tests -p test_eqvg.py -v
```

The Qwen pass saved a static report but reached its 220-second limit. Several
claims labelled proved were incorrect, including selector1 returning without
writes, ten rather than five writes, and the coefficient permutation. Those
claims were rejected; native fixtures and descriptor reads establish the
results above. Worker logs/listings and vendor data remain ignored locally.

Still open: actual manager wait/interpolation processing, the separate
six-argument stability overload and its callers, cross-checking this generator
against Fantom ARM32 code, physical precision, entry/return, scheduler cadence,
history initialization and safe loading. No hardware was accessed or flashed.
