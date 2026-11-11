# LINE native quantization and shaping prefix

2026-11-10. Static follow-up to the [next-program target study](emulator-next-program-targets.md)
and [native primitives](native-arithmetic-primitives.md). Source: prepared ZENOLOGY
arm64 SHA-256 `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
`tools/line_shaping_study.py` checks that identity before analysis. No vendor function,
plugin, device or updater is executed. REA remains unavailable.

The result is a **pure native-reference channel kernel**, with source-checked numeric
and state anchors. It is not a new DSP instruction interpretation or a complete LINE
program. Remaining prefix controls and entry/return behavior stay unadmitted.

## Reference API and numerical policy

```python
native_channel_reference(mixed, *, drive_scale, drive, mode, history,
                         smoothing, rational_scale, a, b)
```

All arguments are explicit finite numbers. `drive` and `smoothing` are rounded to
IEEE binary32 before their conversion to binary64, matching native float-record loads;
constructor-backed arguments remain binary64. The result contains `smoothed` and
`factor` separately, plus effective coefficients and intermediate diagnostics.

The oracle requires **Python 3.13+ `math.fma`** for the observed fused operations.
It uses an explicit default IEEE reference policy; native FPCR rounding, exception,
flush-to-zero behavior and BMC silicon numerics have not been measured. There is no
unfused fallback, clipping beyond the observed stage, reset, memory allocation, ring
advance or hidden initial state. Invalid/nonfinite results and a zero rational
denominator raise `ValueError`.

With G=`drive_scale*drive`, the native order first computes G, then x=`mixed*G`.
Reassociation can change a quantizer bin. An original test vector gives fixed integer
1359712 in that order and 1359711 for `(mixed*drive_scale)*drive`.

## Fixed-point conversion and signed shift

Native windows `2df904..2df910` and `2df9e4..2df9f0` contain exactly:

```text
FCVTZS Xn, Dm, #32
LSL    Xn, Xn, #9
SCVTF  Dm, Xn
```

The following multiply by `2^-32` occurs at `2df91c`/`2df9f0`. FCVTZS uses signed
fixed-point conversion rounded toward zero, as specified in Arm's
[instruction reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab).
The GP scalar form is also specified in Arm's
[compiler guide, section 7.18](https://documentation-service.arm.com/static/5f3fa899428f7a6b3328fd44).
The bounded oracle implements:

```text
q = trunc(x * 2^32)
s = signed64((q << 9) mod 2^64)
z = binary64(s) * 2^-32
```

It accepts **-2^31 <= x < 2^31**, excluding signed64 conversion overflow and its
FP exception/saturation policy. The subsequent integer shift deliberately wraps;
it is not an unbounded multiply. At x=2^22, z is **-2^31**. At x=-2^31, z is zero.
Even without shift overflow, values smaller in magnitude than `2^-32` truncate to
zero; a smooth `512*x` replacement is wrong. Tests independently vary integer width,
fraction bits, shift count and signed versus unsigned conversion.

## Exact constants and the shared mode gate

| Constant | Native materialization | IEEE binary64 bits | Value |
|---|---|---|---:|
| Epsilon | `2df914..2df91c` | `3df0000000000000` | 2^-32 |
| Shaping gain | `2df940..2df954` | `3ff2d0e560418937` | 1.176 |
| Final scale | `2df97c..2df988` | `3feb333333333333` | 0.85 |
| Negative cap | `2df994..2df9a0` | `bfeb333333333333` | -0.85 |

Mode comes from object double `+28`, constructor record `+20`, owned literal field
`45`. The left kernel at `2df920..2df940` retains z when **mode < 2^-32 or z >= 0**;
otherwise it negates z. Equality at the mode threshold therefore selects rectification
for negative z. The right kernel at `2df9f4..2dfa0c` uses the same mode Boolean
carried in W13; it does not need another mode compare. Preservation checks reject
writes through W/X and scalar/vector aliases.

After that selection, t=`z_selected*1.176`. Native FMIN caps t at +1, multiplies
by 0.85, and selects -0.85 when the original t is **strictly below -1**. These
operations are checked separately from constant decoding. Neither the threshold
nor the 1.176 multiplier may be replaced by 1/32 or 0.85.

The shared native drive product D0, epsilon D3, mode flag W13, shaping gain D2,
clamp constants and C1 pointer remain live across the first channel into the second.
The checker verifies those actual definitions/uses rather than assuming that a reused
register retains its earlier meaning.

## History blend and rational factor

Let u be the shaped value, h the supplied prior history, and C1 the effective float32
smoothing coefficient. Native `2df9a4..2df9b0` and `2dfa38..2dfa44` compute:

```text
p = h * C1
q = u + fma(-u, C1, p)
```

The multiply and outer add remain separate roundings. An original test fixture
makes the fused result `-0x1.fe74a1637292ap-2`, while the unfused rewrite produces
`-0x1.fe74a1637292bp-2`. A formal polynomial identity alone would miss that difference.
Nonzero history is required; it is not silently replaced by zero.

Native q is stored to **27 and 3** on the left, **28 and 6** on the right. The
subsequent rational stage overwrites only 27/28 with the factor used by the allpass
chains. Thus q and factor are different state roles. The oracle returns both and
does not choose a ring-advance rule or supply history automatically.

For each channel, z=`q*rational_scale`. Native roles at `2dfaa0/aa4/aa8` and
`2dfaac/ab0/ab8` establish:

```text
factor = fma(z, a, b) / fma(z, b, a)
```

A/B come from object doubles `+18`/`+8`; channel scales come from `+38`/`+48`.
The oracle preserves the fused numerator/denominator and the preceding separate
scale multiply. It rejects a zero denominator before dividing. For one original
finite fixture q≈0.18735 but factor≈0.21614409, so feeding factor back as q is incorrect.

## Provenance and admission boundary

Fresh constructor-memory reconstruction agrees with getter records. The checker
connects six owned literal fields to actual native double loads: D=`42`, mode=`45`,
channel scales=`d6/d9`, a=`e6`, b=`ec`. It uses positions and register definitions,
not equal default values. Grouped descriptor relations for other DSP literal copies
are separate evidence; this study does not invent constructor aliases for them.

Eight native data accesses have exact record, pointer-path, mask and scaled-double
checks. Channel inputs are data[1]/data[2]; prior histories are data[4]/data[7]. Their
history operand fields are **70/b2**, not the preceding literal words 6e/b0. The q
writes use fields 80/82 and c2/c4. The established circular path and `&7ff` identify
within-call dependencies; cross-invocation advancement is a separate state proof.

C2 is loaded as a float at `2df8e0`; C1 at `2df974` and `2dfa24`, followed by the
checked conversions to double. The C1 pointer and shared C2-derived gain are
preserved across channels. The later direct X13-scaled rational memory bridge is
handled by the separate state study, not silently inferred by this checker.

These native equations do **not** assign meanings to `2485`, `fe10`, `b9b2`,
`ac99`, `aed2`, `aeda`, `0e8b`, `ceae`, `4086` or the remaining controls. No decoder,
emitter or strict fragment-interpreter admission changed. Even a native-reference
composition using the proven allpass/mix fragments remains distinct from running
the complete stock BMC byte stream.

## DSP quantizer window and BITCRUSH comparison

`dsp_quantizer_windows()` checks the repeated left and right packet shapes at
logical `48..66` and `8a..a8`. The existing header classification keeps the
operations separate:

| Relative to each channel start | Controls | Header-classified families |
|---|---|---|
| `0` | `2485`, `fe10`, `b9b2` | Short arithmetic, family 2, transfer family |
| `a` | `ac99` | Family 2 |
| `e` | `aed2`, `1e10` | Families 2 and 3 |
| `14` | `2490` with its literal | Short arithmetic |
| `1a` | `aeda` | Family 2 |

`b9b2` has a transfer slot in the LINE header and in 41 classified occurrences
across the local ZENOLOGY render segments. Another 150 occurrences have an
unclassified header. Its transfer address, side effects and connection to
exceptional state remain unknown. In particular, the family assignment supplies
no basis for labeling it the native left shift.

BITCRUSH has related-looking `ac8e` at only two logical packet starts, `128` and
`278`, while its native callback has 16 signed fixed32 conversions with variable
shift logic. It cannot provide a one-occurrence-per-conversion alignment for that
control. LINE's isolated `ac99` is a candidate immediate shift or shift-state
operation. A second exact-context case with another fixed shift count, or a capture
of the input and output around that packet, could distinguish those roles. Neither
the control's low nibble nor the matching native shift-by-nine is sufficient alone.

A scan of framed CORE1 render segments, deduplicated by stored source within
each image, found 10 `ac99` occurrences in Fantom bmc0, 22 in JUPITER-X and
22 in SH-4d. All have the same preceding `3105` packet and following `1a03`
packet shown above. Fantom bmc1 and MC-101 have zero in this scan. Relocated
copies therefore add coverage across builds and still leave one local encoding
context for the exact `ac99` control.

FETDRIVE has the same native fixed32 conversion, shift by nine, and signed
conversion back at `2f7e74..2f7e80` and `2f7fe0..2f7fec`, with half-open
ranges. Its matching DSP quantizer windows use `9c59` followed by `9ed9`
at `48/4c` and `de/e2`. The primary FETDRIVE segment contains no `ac99`.
This gives two different DSP contexts for the same native numeric primitive.
`9c59`, `9ed9`, and `ac99` all have low six bits `19`. VMCP also has an exact
standalone `9ed9` at `4e`, while its native callback's two signed64/fixed32
conversion windows use shifts of 2 and 4. The checked VMCP inventory supplies no
one-to-one relationship between its `9ed9` and either native conversion. These
comparisons leave the role of the shared low bits and any special state open.

The [FETDRIVE cutpoint study](operand-variants-and-macro-boundaries.md#fetdrive-mixed-input-through-the-first-shaped-store)
now follows both mixed-input reloads through the native clamp and affine square
to T. It reads the drive and post-gain literal values separately in all five
Fantom placements. No intermediate readback establishes the two standalone
operations' individual effects.

## VMCP and RING separate `9ed9` from fixed-point conversion

The best current interpretation of `9ed9` is a bipolar limiter in the checked
contexts. VMCP has an isolated `9ed9` at `4e`, after `1460`'s scale literal
and before `1c64`'s bias literal. Native records tie the state read at
`39da78` to field `3c`, the held-value store at `39da90` to field `44`, and
the detector store at `39dac8` to field `6a`. The native interval is
straight-line and computes the following:

```text
detector = clamp((held * state) * threshold_scale, -1, +1) + bias
```

Both literal operands are checked by constructor-field identity, including the
bias `-0.010009765625` at `5e`. The native clamp is at `39daa4..39dab0`, with
no integer conversion in this interval. The matching DSP stores are `9fe0`
at `3e` and `62`. This places the clamp between two matched stores, with
`9ed9` the sole family-2 control between them.

RING provides a second store-bracketed case. Its `8fe2` store at `fa` matches
native `277dcc`, and `9fe0` at `110` targets the cell written at `277e00`.
The latter uses the constructor record associated with field `e4`; the DSP
store field `11e` independently carries that same cell address (`7`). The
native interval forms a new value with FMADD and clamps it to `[-1,+1]` at
`277de0..277de8`. DSP `9ed9` co-issues with `0410` and a coefficient-slot-7
load at `104`. The native coefficient load feeds a separate scaled term.
This corroborates the limiter interpretation while leaving exceptional
register selection and issue timing open.

VMCP's native fixed-point conversions occur in later, distinct windows:

| DSP context | Native boundary |
|---|---|
| `bc12` co-issued with `8fe0` at `e2` | Native `39dba8` stores the value before the shift-by-2 conversion at `39dbac`. Its rescaled result feeds both channel multiplies. |
| `bcd4` at `108`, after loading coefficient slot 1 | Native `39dc08` reads the live float, and `39dc10` starts its shift-by-4 conversion. Its rescaled result multiplies both channels before stores at `39dc30/39dc44`, tied to fields `118/11a`. |

These contexts support shift-2 and shift-4 hypotheses for `bc12` and `bcd4`
without defining their individual state effects. In FETDRIVE, `9c59` precedes
`9ed9`, and the native order is shift-by-nine followed by a clamp. The two new
cases favor assigning the clamp to `9ed9` and make `9c59` the next conversion
candidate. LINE's `ac99` still needs an independent binding. No strict DSP
interpreter profile was added.

The Fantom VMCP list at `6113d2b8` retains the checked sequence in all four
placements. Literal `4a` is zero in the stored bytes. The desktop
`SetThreshold(int)` and Fantom callback `610641da` both write that exact
width-three field from a 128-entry table. The Fantom's manager dispatch is
slot `64` at the receiver's vtable. Its table matches all desktop entries after
exact conversion of the native doubles to float32. The endpoints are
`0.630950927734375` and `0.010009765625`. This verifies a parameter-write path
in the image. Active VMCP selection, threshold settings, hardware numeric
behavior and actual execution timing remain unverified.

```sh
python tools/limit_control_study.py --core1 local/b0c1a.bin > local/limit-control-study.json
python -m unittest discover -s tests -p test_limit_control_study.py -v
```

## Fixed-point shifts in VMCP, VSOD, FORMANT and GASSPH

`coefficient_shift_study.py` follows independently identified binary32 live
coefficient records into the native signed64 fixed32 conversion, wrapping
left shift, signed conversion back, and multiplication by `2^-32`.

| DSP context | Live operand | Checked native use |
|---|---|---|
| VMCP `108`, `bcd4` | C1 through `3fe0`, port 3 | Shift by four at `39dc10`. The converted coefficient supplies both following `0403/4503` gains, which use port 3. |
| VSODDSAW `1ac`, `bcd4` | C1 through `3fe4`, port 3 | Shift by four at `1791d4`; `179268` selects the converted value or unity. Both incoming native pointer paths load the same C1 record. |
| VSODDSTW `1c4`, `bcd4` | C1 through `3fe6`, port 3 | Shift by four at `2813bc`; `28143c` selects the converted value or unity. Native input is in `d7` and the signed conversion back goes to `d4`. |
| Base VSOD `12`, `fdd4` | C1 through `7fe4`, port 7 | Shift by four at `27394c`. Native `273984` writes the converted coefficient to field `28`, the exact operand of the next `ffe0` port-7 store. |
| FORMANT `6a`, `bcd2` | C2 through `3fe4`, port 3 | Shift by two at `3cdb34`. At `3cdb54` its result multiplies the independently owned literal at field `80` from the following packet. |
| GASSPH `28a`, `fdd2` | Computed value `0.25 - d3²` in the native reference | Shift by two begins at `14a6f8`; the result reaches the `14a730` store. The `ffe2` port-7 store in the next DSP packet targets the same data cell (`46`) through field `2a6`. |

In base VSOD, the `fdd4` packet also loads C0 into port 3, and the next packet
combines the port-7 store with a known port-3 gain. The independently traced
native C0 path is separate from the C1 value stored at `273984`. This anchors
the port-7 result and supports the in-place port-3 reading of VMCP's `bcd4`
counterpart. The two VSOD variants independently agree on the port-3 input,
conversion, and native selection rule `-2^-32 < mode_delta < 2^-32`.

`bcd2` and `bcd4` differ only in their low nibble, and the FORMANT and VMCP
windows use shifts of two and four. `fdd2` and `fdd4` likewise differ only in
the low nibble and both lead to a port-7 store. In GASSPH, the native record
at field `a2` and the DSP operand at `2a6` independently name cell `46`. The
native source is computed arithmetic, so the shift operation is also used
outside a live-coefficient load context. Comparing `fdd4` with `bcd4` changes
bits beyond the high nibble. These comparisons support the shift counts and
port roles in the checked contexts.
The remaining encoding bits, exceptional state, rounding on silicon and
co-issue effects are still open. The strict interpreter has no new profile.

The Fantom bmc0 lists retain the same controls and operand roles in all five
base VSOD placements and all four placements of each VSOD variant. The
checker reads the relocated coefficient operands and the base VSOD store
addresses separately. No active effect or hardware execution was observed.

```sh
python tools/coefficient_shift_study.py --core1 local/b0c1a.bin > local/coefficient-shift-study.json
python -m unittest discover -s tests -p test_coefficient_shift_study.py -v
```

## Reproduce and Qwen review

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/line_shaping_study.py
$PY -m unittest discover -s tests -p test_line_shaping_study.py -v
```

The report is ignored `local/line-shaping-study.json`. Fifteen tests cover native
anchors, original synthetic ARM64 kernels, finite domains, mode/shift boundaries,
binary32 coefficients, reassociation/FMA counterexamples and nonzero history.

A serialized no-tool Qwen mechanical review was obtained through the existing
MacStudio profile with per-run thinking disabled. Its correct broad reminders about
duplicate stores, FMSUB and the rational form were independently checked. Its claimed
1/32 epsilon, 0.85 shaping multiplier, absent right-channel mode gate and several
addresses/register writes were wrong and rejected. Complete prompt, output and the
review ledger remain local. No model claim was used as native or DSP evidence.
