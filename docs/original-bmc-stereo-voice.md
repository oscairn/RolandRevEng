# Original BMC oscillator voice with stereo gain/output

Follow-up: the [original filtered voice](original-bmc-filtered-voice.md) retains
this entire 200-byte body and appends the checked stereo lowpass component.
It adds four state seeds and five coefficient slots while retaining data extent
146. The original unfiltered behavior below remains independently verified.

2026-11-10. `tools/bmc_allpass_voice.py` composes the original feedback
oscillator with the supported stereo gain and scratch-output profile. All
per-frame signal arithmetic runs through packet bytes. The host computes five
initial sine values and advances the explicit native ring after each full frame.
It does not multiply or duplicate the oscillator samples to construct the output.

This is a **200-byte voice body**, not load-ready firmware or a deployable plugin.
The entry/return wrapper, live ownership, resource relocation, real output routing,
state initialization, hardware precision and cadence remain unverified. It has
constant gain; live envelopes, note events and polyphony are not implemented here.

## Static program and resources

| Block | Logical bytes | Packets | Purpose |
|---|---:|---:|---|
| `coefficient_shift4` | 38 | 3 | Refresh the quantized allpass factor |
| `allpass4` | 82 | 7 | Generate the feedback oscillator |
| `dry_wet_tail_with_scratch` | 80 | 8 | Apply stereo gain, store and reload outputs |
| Total | 200 | 18 | Same bytes every frame |

Logical program SHA-256:
`0c53752b429210af9d5f7e29bbcaf468e218518979b4d7fdf62b6fa0a175cb15`.
Concatenate all three logical slices before converting LE32 storage words.
The 38-byte boundary is not word-aligned; independently padding/switching
the slices changes the program. `storage_program()` converts the whole body.

The original oscillator's store/read pairs and six seeds are unchanged.
Its output and duplicate are current-frame logical cells `60/70` in hex.
The tail reads both, stores its two results at `90/91`, and reloads those
actual results into functional main outputs A/B. All three blocks share one
2,048-element ring and one origin; the origin advances only after the tail.
Each strict profile initializes the ports it consumes, so no undocumented
port state is carried between interpreter calls.

| Coefficient slot | Value/role |
|---:|---|
| 0 | Zero for the oscillator prefix's unused external-input mix |
| 1 | Original frequency factor divided by 16 |
| 2 | Zero dry contribution in the output tail |
| 3 | Requested output gain rounded to CPU binary32 |
| 4 | Post gain 1 |
| 5 | Master gain 1 |

Gain is finite in 0..1; the manifest records requested and rounded gain.
The functional output is the original oscillator value times rounded gain,
on both channels. That equation is the independent test oracle. The renderer
itself takes both results from the executed tail's ports.

The body retains the default software input pair `2016/2017` with zero dry
contribution. The [recorded stock owners](kernel-audio-abi-study.md) have other
input/output assignments. A capacity fit does not rewrite those addresses or
establish which physical audio channels a wrapper will select.

## Static capacity comparison with Fantom owners

`tools/voice_owner_fit_study.py` derives the body's footprint from its three
decoded profile specifications, then reads the five actual stock descriptors
from the pinned Fantom BMC0 CORE1 payload. The requirements are 200 program bytes,
15 referenced data indices spanning **146 relative positions**, and six consecutive
coefficient slots. Program framing and any wrapper resources are excluded.

| Descriptor | DSP | Program base / capacity, hex bytes | Enum-0 base / length, hex elements | Enum-6 base / length, hex elements |
|---|---:|---|---|---|
| `610a1674` | 4 | `4020 / 1000` | `100 / 96` | `190 / 14` |
| `610a16bc` | 5 | `8040 / 1000` | `320 / 96` | `1f4 / 14` |
| `610a1704` | 5 | `9040 / 1000` | `3b6 / 96` | `208 / 14` |
| `610a174c` | 5 | `a040 / 1000` | `44c / 96` | `21c / 14` |
| `610a1d14` | 1 | `3020 / 1800` | `c0 / c0` | `e / 14` |

The body fits all five recorded capacities under the checked index ranges.
The first four data reservations have only four positions beyond this body's
extent. Additional wrapper state may change that result. These are occupied
stock reservations, **not available allocations for a custom voice**. The
checker emits no relocated program and marks ownership/execution unverified.
Equal numeric indices in enum 0 and enum 6 remain different resources.

The [resource planner](fantom-voice-resource-plans.md) now generates and
verifies explicit data/coefficient/IO substitutions for all five layouts.
Each relocated body matches the original model through wrap with canaries
outside its six seed cells. Its entry/return wrapper and load address remain
unassigned. Actual replacement still needs the
[typed state-write/readback gates](state-initialization-and-float-writers.md)
and a verified control/transport path on the Fantom.

## Verification and reproduction

At requested 440 Hz, default amplitude .25 and gain .5, a 12,000-frame render
has peak `0.12499999999623529` and RMS `0.08838832781982624`. Actual modeled
pitch remains `440.000197628852` Hz. Tests compare every output value against
the earlier mono oscillator times rounded gain at 440 and 9600 Hz through
ring wrap, plus zero/unity gain, nonzero external inputs, exact program shape,
five initialization-only sine calls and existing-output preservation.

The shared `initialize` extraction retains the earlier mono renderer's samples
and metadata exactly; this was independently checked against the previous
committed implementation at both frequencies. Native detector/source-rounding
regressions also remain covered by the repository suite.

```sh
python3 tools/bmc_allpass_voice.py local/bmc-allpass-voice.wav \
  --frequency 440 --gain .5 --frames 12000 > local/bmc-allpass-voice.json
python3 tools/voice_owner_fit_study.py local/b0c1a.bin > local/voice-owner-fit.json
python3 -m unittest discover -s tests -p 'test_bmc_allpass*' -v
python3 -m unittest discover -s tests -p test_voice_owner_fit_study.py -v
```

Rendering needs Python 3.13+ `math.fma` and no vendor artifacts. Capacity analysis
needs the existing pinned firmware and Capstone. Audio and original binary exports
remain ignored/local. Both live-hardware flags stay false. All 352 tests passed.

Qwen returned a working voice draft in 126.1 seconds. Review retained its shared
state/three-block design, removed the scratch import loader and duplicate
coefficient maps, moved validation into shared initialization, and reduced the
tests to the meaningful contracts above. Local verification reproduced output
gain, resource shape, mono compatibility and the full suite. No new DSP opcode,
instruction scheduler or hardware loader was introduced.
