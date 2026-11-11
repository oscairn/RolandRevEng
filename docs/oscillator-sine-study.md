# OSC sine folding and polynomial

2026-11-10. The first sine window of `SIM_MFX_OSC` now has a checked
native reference. Direct execution agrees bit for bit at 525 input phases,
including fold and sign boundaries. Four Fantom placements retain the matched
DSP packet context. This establishes native CPU behavior and literal ownership.
BMC arithmetic, exceptional state and hardware timing remain unverified.

## Checked state and constants

The fixture copies native `29014..29210`, starting with the
[phase increment and normalization](oscillator-phase-study.md). It appends
a return after the signed sine store. Complete decoding, internal branch
targets, preserved pointers and the pinned native image are checked before
execution. Its explicit memory contains constructor values, zero increment,
supplied phase history and a cold ring. It invokes no plugin framework or
initialization routine.

| Native store | Constructor field | DSP operand field | Native cell | Observed result |
|---|---|---|---|---|
| `290bc` | `1d4` | `022` | 4 | Updated phase |
| `290f8` | `1ec` | `042` | 7 | Sine polarity |
| `291f8` | `1e4` | `094` | 6 | Polynomial before polarity |
| `2920c` | `1b4` | `09a` | 0 | Signed sine |

The sign reload in DSP packet `080` must address the sign target stored by
packet `03c`. Packet `08e` co-issues multiplication `0403` with the store
of the previous main-A polynomial. Packet `096` stores the signed result.
The checker rejects changed controls and a mismatched sign reload.

| Native double field | Native load | DSP literal field | Width | Constructor double |
|---|---|---|---|---|
| `148` | `29180` | `050` | 4 | `0.00012626262626262626` |
| `158` | `29190` | `05e` | 4 | `0.0064102564102564` |
| `168` | `2918c` | `05a` | 4 | `3.0525030525030525e-05` |
| `178` | `291dc` | `08a` | 4 | `0.16666666666667` |
| `188` | `291bc` | `076` | 4 | `0.0083333333333333` |
| `198` | `291b4` | `072` | 4 | `0.0001984126984126984` |
| `1a8` | `291a4` | `068` | 4 | `0.013888888888889` |

Each literal is checked against a fresh constructor record and its actual
native load. The encoded DSP values have their own limited precision. The
native double defaults above are retained for native execution comparisons.

## Fold, scale and evaluation

For the updated phase `p`, the native sign is negative when
`abs(p) - 0.5 > -2^-32` and positive otherwise. The comparison is strict.
It then doubles `p`, applies the same signed32 period-normalization rule
as the phase step, halves the result and multiplies by
`3.1415926218032837`, exactly `0x1.921fb50000000p+1` in binary64.
The reference rejects a doubled phase whose magnitude reaches `2^31`.

This scale is exactly representable by four-byte literal `43243f6a`.
The current nearest-value software encoder gives `43243f6b` for mathematical
pi. These facts do not establish the hardware's coefficient encoding policy.
DSP packet `024` loads port 7 from operand `e037`, and the following packet
contains multiply `1407`. That makes `e037` a fixed-input candidate for the
scale in this context. A general constant-bank mapping remains unproved.

Let `x` be the folded, scaled argument. If the constructor coefficients are
replaced with exact rational values, the native factorization becomes

```text
L = x - x^3/156 + x^5/32760
H = x + x^4*L/7920 - x^3/72
P = x + x^5/120 - x^3/6 - x^6*H/5040
```

Exact rational expansion gives the degree-15 Taylor polynomial
`x - x^3/3! + x^5/5! - x^7/7! + x^9/9! - x^11/11! + x^13/13! - x^15/15!`.
Qwen executed a Fraction calculation for the expansion. An independent local
Fraction calculation asserted all eight coefficients and the absence of
other powers. The worker's generic helper was not adopted.

The executable reference preserves the actual native constants, multiplication
order and fused operations rather than using this ideal expansion. In
particular, native `fmsub` at `291e4` computes addend minus product with one
rounding. The signed output multiplies the polynomial by the saved polarity.
The implementation requires Python 3.13+ `math.fma`.

## Sign boundary observed in the native fixture

The sign threshold and phase fold have slightly different boundaries.
For ordinary phases near the extrema, the resulting native output has the
opposite sign to mathematical `sin(pi*p)` in these intervals

```text
positive phase: (0.5 - 2^-32, 0.5)
negative phase: [-0.5, -0.5 + 2^-32)
```

At `0.5 - 2^-32` the native output is approximately `+1`. The next binary64
value toward `0.5` produces approximately `-1`. At exactly `0.5`, folding
changes the polynomial sign and the output returns to approximately `+1`.
At exactly `-0.5`, the output is approximately `+1`; at
`-0.5 + 2^-32` it is approximately `-1`.

The previous whole-OSC experiment accumulated phase in binary64 and entered
these narrow intervals. This explains its isolated peak sign changes under
that fixture. It does not demonstrate a BMC audio defect. Hardware internal
precision and comparison ties could produce different reachable phases.
An encoded literal format alone does not establish the arithmetic format.

The execution test compares four stored values per phase, including signed
zero, using `float.hex()`. Its 13 boundary inputs and 512 deterministic
random inputs make 2,100 bit-exact stored-value comparisons.

## Fantom placements

The pinned Fantom list at `61112114` contains these contexts. All targets are
logical data cells before any runtime origin/base adjustment.

| Program base | Sine output | Polynomial | Polarity |
|---|---|---|---|
| `4020` | `100` | `106` | `107` |
| `8040` | `320` | `326` | `327` |
| `9040` | `3b6` | `3bc` | `3bd` |
| `a040` | `44c` | `452` | `453` |

The controls and their literal ownership are retained while the data operands
relocate. Placement checks do not execute the Fantom program.

## Reproduce and remaining work

```sh
python tools/oscillator_sine_study.py --execute-native --core1 local/b0c1a.bin \
  > local/oscillator-sine-study.json
python -m unittest discover -s tests -p test_oscillator_sine_study.py -v
```

Native execution requires macOS ARM64, the pinned local corpus and an isolated
subprocess. Vendor code and native disassembly remain ignored local artifacts.

No OSC packet is newly admitted to the strict DSP interpreter. Independent
contexts are still needed for the exceptional phase/fold controls and their
other state effects. Square/impulse/noise paths, output-level calibration and
hardware observations remain separate tasks. A custom Fantom engine still
needs a verified host/CORE1 access path, task entry, state setup and hardware
scheduling in addition to arithmetic semantics.
