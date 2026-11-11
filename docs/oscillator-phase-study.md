# OSC phase state and frequency field

2026-11-10. The desktop `SIM_MFX_OSC` native translation and four Fantom
MFX OSC placements share a checked phase-add/wrap window. The Python
reference agrees with 272 direct native-execution probes. The native
frequency setter owns the increment field and computes
`2 * frequency / sample_rate`. BMC execution and timing remain unverified.

## Stored phase boundary

All program offsets in the native comparison belong to the 806-byte
desktop MFX OSC segment.

| DSP packet | Checked context |
|---|---|
| `000`, `0c03 / 0fe0` | Load phase history from data cell 5 |
| `006`, `0904 / 0c30` | Width-four increment literal at field `00a` |
| `00e`, `1604 / 1410 / 8ee0` | Constant `2` and exceptional control in the phase window |
| `016`, `6f07 / 3c10 / 8ee1 / 8fe2 / b9b1` | Phase store to cell 4, operand field `022` |

Fresh constructor records bind the source to object field `1dc` and
the target to field `1d4`. Native read `29040` supplies the old phase,
load `29044` reads its owned increment double at object+`a8`,
and `29048` adds them. Both normalization paths join at `290ac`.
Store `290bc` writes the normalized value through the matched
target record. The checker verifies instruction uses, preserved
pointers, branch targets and complete decoding.

The native fixture copies only `29014..290c0` and appends an original
return instruction at the stored-state boundary. All branches stay
inside the copied interval. The subprocess supplies explicit memory
and pointer structures. Its output checks the stored phase against the
Python rule. The test covers both sides of `±1`, increment carry,
negative odd integers, signed32 normalization wrap and 256 deterministic
random phase/increment pairs.

## Native numeric rule

The reference first computes the binary64 sum of phase and increment.
It accepts finite sums with magnitude below `2^31`, where the positive
integer conversion is in range.

For a sum in `[-1,1)`, it retains the sum. Otherwise it truncates the
sum's absolute value to an integer, adds one and clears the low bit.
It interprets that result as signed32. A negative sum adds this
normalizer and a positive sum subtracts it.

| Input sum | Stored native result |
|---:|---:|
| `-5` | `+1` |
| `-3` | `+1` |
| `-1` | `-1` |
| `+1` | `-1` |
| `+3` | `-1` |
| `0.99 + 0.03` | approximately `-0.98` |
| `2^31 - 1` | `2^32 - 1` |

The negative odd boundary differs from canonical modulo normalization.
At the upper integer limit the signed normalizer wraps. The returned
value can then exceed the conversion domain. A following out-of-domain
step is rejected by this reference. Conversion-overflow exception
behavior and BMC numerical representation remain open.

## Owned frequency write

The checked `CFspMfxOSC` constructor installs the oscillator symbol
table at `a4d578`. Its first entry points to `a4d760`, which declares
one width-four record at relative field `a`.
`CFspPiece_Oscillators::SetSineFrequency(double)` at `293900`
doubles the requested frequency, divides by the current signed sample
rate and passes that symbol to manager slot `c8`. The native
constructor record at `a0` owns the same field.

The Fantom list at `61112114` contains four placements with the
checked phase controls.

| Program base | Phase history | Stored phase |
|---|---|---|
| `4020` | `105` | `104` |
| `8040` | `325` | `324` |
| `9040` | `3bb` | `3ba` |
| `a040` | `451` | `450` |

Each placement stores increment `0.018333333311602473`. It differs
from `2 * 440 / 48000` by less than one encoded step. This supports
the 48 kHz rate hypothesis alongside the earlier post-gain evidence.
Actual selection, live parameter writes, parent cadence and output
frequency require instrument observations.

## Reproduce

```sh
python tools/oscillator_phase_study.py --core1 local/b0c1a.bin
python tools/oscillator_phase_study.py --execute-native --core1 local/b0c1a.bin \
  > local/oscillator-phase-study.json
python -m unittest discover -s tests -p test_oscillator_phase_study.py -v
```

The direct execution check requires macOS ARM64 and the pinned native
corpus. The numeric function runs without vendor artifacts.
The phase equation binds the complete checked window. Individual
exceptional controls, their flags and their other port effects remain
outside the strict packet interpreter.
