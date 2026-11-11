# Complete independent TRANSIENT arithmetic reference

2026-11-10. The Python reference now computes TRANSIENT's entire detector,
both exponential-envelope arguments, their state updates and the stereo
output. It reads no native intermediate values. Every output float matches
the complete pinned ARM64 callback over 12,000 frames, and the resulting WAV
files are byte-identical. This closes the upstream-detector dependency in the
[earlier conditional reference](special-ops-and-exp-study.md#native-transient-fixture-and-conditional-envelope-reference).

This is a native arithmetic reference, not a TRANSIENT BMC interpreter.
The strict DSP decoder/emitter gains no speculative instructions. Hardware
precision, flags, timing, actual warm state and preset initialization remain
unverified. The reference uses the existing explicit cold 2,048-double ring,
wrapper base zero, one origin step per frame and software 48 kHz inputs.

## Checked state and defaults

`transient_state_study.py` pins native SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`,
checks constructor/program operand records, the preserved context/ring/origin
roots, key arithmetic/branch anchors and the two distinct log constants.
The native callback remains `1d5fd0..1d66c4` with the checked log/exp bridge.

**Logical cell numbers below are decimal.** Native object fields and code
addresses are hexadecimal. These ten record pairs become one-frame histories
under the explicitly selected origin convention:

| Current store | Next-frame read | State |
|---:|---:|---|
| 17 | 18 | Held log maximum |
| 19 | 20 | Phase/counter |
| 21 | 22 | First saved peak-window value |
| 23 | 24 | Second saved value |
| 25 | 26 | Third saved value |
| 29 | 30 | First decay path |
| 31 | 32 | Second decay path |
| 34 | 35 | Smoothed rising path |
| 38 | 39 | First exponential envelope |
| 40 | 41 | Second exponential envelope |

Defaults come from the actual reconstructed constructor. Its peak
normalization is `0.02476228209191759`; its phase increment is
`0.009070294784580499`. No hardware time unit is assigned to that increment.
The first decay increment is `-0.0004233471397304735`, rising-path rate
`0.0014237438457114227`, and second-decay increments are
`-0.000195798052125344` / `-0.000783192208501376`.

The native held-log floor at object+8 is
`-0x1.ba18a998fffa1p+2`. A separately synthesized release-floor literal is
`-0x1.ba18a998fffa0p+2`, **one binary64 step higher**. The model preserves both.
The normalized peak's zero-log replacement is a third constant,
`-22.18070977791825`, equal to `log(2^-32)`.

Only the normalization's serialized literal binding is admitted by this
study. Other defaults include unresolved mixed packet layouts, such as family
`b409`; the strict reader still rejects them. Native constructor doubles and
truncated BMC literals remain distinct representations, not bit-identical values.

## Detector transitions

`transient_detector_reference.detector_step` consumes the two input samples,
eight old history cells and the native defaults, returning fifteen retained
logical writes plus the selected branches. All arithmetic is finite binary64;
the existing bounded signed32 phase normalizer and explicit `math.fma` retain
the native operation order.

1. Form normalized maximum magnitude, store peak at 0 and log at 1. The
   native magnitude selections retain negative zero and choose the right input
   on an equal-magnitude tie. Zero peak selects the explicit zero-log floor.
2. Build the held maximum from current log, constructor floor and old cell 18.
   If `current_log-old18 >= 2^-32`, reset the counter to -1 and retain guard -2.
   Otherwise add the increment to old cell 20 and normalize for store 19.
3. The later window decision uses **unwrapped sum minus 1**, not normalized
   phase minus 1. A guard at/below `-2^-32` rolls old 24/26 into stores 23/25,
   old 22 into 21, and includes old 26 in the window maximum. Above that
   threshold it copies old 22/24 into 23/25, the held maximum into 21, and
   replaces held store 17 with the current log. The resulting maximum is
   duplicated into stores 27 and 2.
4. First decay store 29 is the greater of `old30+first_decay_increment` and
   current log clamped to the separate release floor. If `new29-release_floor`
   is strictly below `2^-32`, the second decay uses object+`e8`; otherwise
   object+`d8`. Store 31 is the greater of that decayed old 32 and clamped log.
5. Store 33 copies the current window maximum. Compute
   `smooth=fma(window-old35,rising_rate,old35)` and store the lesser of the
   window and smooth at 34. The exp arguments are **34−33** at 36 and
   **29−31** at 37. Live C1/C3 quantization selects envelope rates downstream;
   it does not multiply either argument.

The owner+`100` cache writes the current log, advances its cursor modulo
three, then decrements that cursor before reading. It therefore reads the
just-written entry and restores the starting cursor. The owner+`a0` cache
does the same for the current `a-a*b` term in the final gain. Neither introduces
an extra frame delay in this callback. Native comparisons with initial cursors
0, 1 and 2 confirm this round trip; the model needs no separate cache history.

## Independent render and native comparisons

`render_transient_reference.py` initializes its own ring and applies detector
writes, the existing `envelope_step` kernels and `tail_reference`. It uses
constructor rates and four binary32 live coefficients. Its only vendor inputs
are the statically checked constants and address records; it executes no vendor
code and consumes no native output or intermediate state.

`native_transient_reference.py` now checks all fifteen detector writes after
each real callback invocation, using histories captured before that call.
It uses the independently computed arguments for its envelope/tail checks,
then compares the entire output with a separate cold-ring reference render.
The report sets `upstream_arguments_from_native=false` and
`full_output_reference_verified=true`; `bmc_instructions_executed` stays false.

The 12,000-frame baseline checks 180,000 detector values, 60,000
envelope/gain/output values and 24,000 output values from the fully independent
render. These checks overlap; they are not counts of distinct measurements.
Peak remains `0.14596584013287234`, RMS `0.07554220759649252`.
The detector selects 129 resets and 11,979 window-roll branches.

Additional isolated native tests cover 17,000 silent frames (684 selections of
the faster second-decay rate), stepped inputs, signed zero, negative C1/C3 modes,
binary32-rounded master gain and both alternate valid cache cursors. Pure kernel
tests distinguish positive reset epsilon, negative window epsilon, the release
epsilon boundary and phase wrap with its unwrapped guard. They reject missing
state, non-finite input and phase conversion outside the checked signed32 domain.

```sh
python3 tools/render_transient_reference.py local/transient-full-model.wav \
  --frames 12000 > local/transient-full-model.json
python3 tools/native_transient_reference.py local/native-transient-full-model.wav \
  --frames 12000 > local/native-transient-full-model.json
python3 -m unittest discover -s tests -p '*transient*' -v
```

Use the existing Capstone-capable Python 3.13+ interpreter. Native comparison
also requires macOS ARM64. Both CLIs refuse existing WAV paths. New model code
and tests are tracked; vendor bytes, disassembly, worker drafts and generated
audio remain ignored/local. All 341 repository tests passed, with the expanded
native cache-cursor cases additionally rerun after their addition.

## Reviewed Qwen draft and remaining DSP work

Qwen returned a draft in 188.1 seconds, honestly retaining a frame-1 mismatch.
Review found incorrect log constants, phase source/guard handling, reversed
window copies, invented coefficient multipliers on the exp arguments, and a
replacement of the native normalization with a truncated serialized value.
Its claim that earlier native stores already matched was unsupported by its
checker. No worker model code was accepted; the corrected reference above was
derived from the instruction listing and independently executed comparisons.

The next ISA work can now compare actual TRANSIENT packet windows against
known detector and envelope transitions. It still needs exact operand/port
selection, literal ownership in unresolved mixed layouts, precision/flag
semantics, and entry/return execution. Full native output agreement alone does
not establish any of those DSP behaviors or hardware readiness.
