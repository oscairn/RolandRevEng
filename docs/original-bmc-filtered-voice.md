# Original oscillator, gain and lowpass voice

2026-11-11. `tools/bmc_filtered_voice.py` composes the original oscillator voice, an optional cubic waveshaper
and the checked state-variable filter in one shared ring. All per-frame signal
arithmetic executes through BMC packet bytes. The host initializes seeds and
coefficients, supplies the ring view and advances the explicit native origin.

**Result:** a fixed 384-byte, 28-packet voice body with eleven coefficients and
ten required initial data values. Typed relocation reproduces the model across
all five recorded Fantom layouts with nonzero background canaries. These are
original offline engine bodies, not load-ready firmware or a deployable plugin.
Load/entry/return addresses, output routing, live ownership, state conversion,
physical precision and scheduling remain unverified.

## Composition and shared resources

| Block | Bytes | Packets | Purpose |
|---|---:|---:|---|
| `coefficient_shift4` | 38 | 3 | Refresh the original oscillator factor |
| `allpass4` | 82 | 7 | Generate the feedback oscillator |
| `dry_wet_tail_with_scratch` | 80 | 8 | Apply gain and store the two current samples |
| `state_variable_pair` | 184 | 10 | Filter those samples with two state pairs |
| Total | 384 | 28 | Same body bytes every frame |

The first 200 bytes remain exactly the
[original stereo voice](original-bmc-stereo-voice.md). Data cells `90/91` in hex
feed the filter and retain the pre-filter samples; they are not final filtered
output buffers. Filter results are taken from functional main ports A/B.
Each profile initializes the ports it consumes. No hidden register seed is
assumed between interpreter calls. All four blocks share one origin advance
after the full frame, rather than advancing separately for each fragment.

The filter retains its proved state relation: s/t at `29/2a` and `2c/2d`, with
Snew at `28/2b` and Tnew at `29/2c`. These cells are distinct from the oscillator's
current state reads/writes. Its final otherwise-unused port prefetches read
`20/30/40/50`, which the oscillator already writes. This avoids introducing
additional initial reads without changing the current filter result.

Coefficient slots `0..5` retain the original voice assignments. Slots `6..a`
hold the five filter coefficients a/b/c/d/e. The named data set contains 21
indices, with extent 146; coefficient extent is eleven. The five stock owner
descriptors each have twenty coefficient slots and at least 150 data elements,
so this body fits their recorded numerical capacities. Those occupied stock
instances are not available custom allocations, and a space fit is not an
established real-time issue budget or auxiliary-resource reservation.

The model's required first-frame seeds are exactly:

```text
21, 29, 2a, 2c, 2d, 31, 41, 51, 61, 71   (hexadecimal)
```

Six retain the original oscillator values; four explicitly initialize the
filter states to zero. Current oscillator outputs, factor, scratch samples and
the borrowed prefetch cells are written before read. Read-before-write checks
reject a missing seed. Finite nonseed canaries can replace the zero background
without changing the output. This establishes a model dependency, not safe live
initialization or permission to clear an owner's memory.

## Original lowpass coefficient design

The authored helper uses nominal cutoff f and damping q0 at the explicit 48 kHz
software rate. It constructs:

```text
g0 = 2*sin(pi*f/48000)
a = float32(g0 - 1)
b = float32(-q0)
g = 1+a; q = -b
c = 1
d = float32(-q/2)
e = float32(q*g/2 - 1)
```

The existing [filter recurrence and ideal stability check](fdrv-state-variable-filter.md)
must pass with positive g/q after rounding. Nonfinite, zero-g, zero-damping and
unstable designs are rejected. Not every cutoff below Nyquist is stable for
every damping value. The default nominal cutoff is 1000 and damping sqrt(2).
Nominal cutoff is a coefficient-design parameter, not a measured hardware cutoff.
Binary32 d/e rounding also perturbs the exact ideal lowpass identity.

For the default design, actual coefficients are
`[-.8691937327384949, -1.4142135381698608, 1, -.7071067690849304, -.907505989074707]`.
The ideal matrix has trace `1.797901726406426` and determinant
`.8150120059613144`. Independent tests check unity DC response and relative
stopband attenuation. The original renderer uses no per-sample host sine or
filter calculation: five initialization sine evaluations seed the oscillator,
and one more designs the filter.

## Render and export

```sh
python3 tools/bmc_filtered_voice.py local/filtered-voice.wav \
  --frequency 440 --gain .5 --cutoff 1000 --frames 12000
python3 tools/fantom_voice_plan.py local/b0c1a.bin \
  local/filtered-plan-dsp4 --owner 0x610a1674 --cutoff 1000 --frames 12000
python3 -m unittest discover -s tests -p 'test_bmc_filtered_voice.py' -v
```

The renderer needs Python 3.13+ but no vendor artifact, plugin or instrument.
It writes a new stereo WAV and prints metadata. The planner additionally needs
the pinned CORE1 artifact for descriptor evidence. Its default without `--cutoff`
retains the old 200-byte voice. A damping option without a filter is rejected.
Frequency, amplitude, gain, cutoff and damping change seeds or coefficients,
not the fixed body bytes.

The planner emits only original logical/stored bodies and a manifest into a new
directory. It independently verifies **58 two-byte transfer fields**, preserving
the remaining **268 bytes**. The optional exact-filter recognizer gates its
transfer-only walk through mixed packets; general miscellaneous header layouts
remain rejected. All fragments are concatenated before stored-word conversion.
The ten CPU binary32 data-source rows and eleven coefficient-source rows are
source buffers, not a recovered raw DSP storage format. Entry/return addresses
stay null and `execution_ready` stays false.

## Verification checkpoint

The shared-ring renderer agrees bit for bit with a separately rendered original
voice followed by the independent scalar filter for all 24,000 channel values
in 12,000 frames. Five relocated canary-ring runs match another 120,000 output
values, each ending at origin 1760 after five wraps. The default unrelocated body
hash is `e3c09a822f1962ed7e7b2e4dc0ac6618c8d7c9baad0236395fa3e14ffbf502c1`;
the DSP4-layout body hash is
`7376365cd0b7ae2252dfdce42c652d735904016e46fbd290f67e62559abcad20`.
The default render peaks at `.1210436562504144`, RMS `.08557454541306107`.
These are offline reference values, not BMC measurements.

Qwen returned the bounded design/helper draft in 23.1 seconds. Review retained
the coefficient equations, corrected coefficient labels and the fixed-rate bound,
replaced its weak absolute stopband assertion with a relative response test,
and checked that returned coefficients themselves are binary32 values. Shared
resources, seed analysis, byte protection, relocation and render comparisons
were independently implemented and verified locally. All 403 tests passed.

## Optional cubic waveshaping before the filter

`--waveshape` adds the [exact cubic quad](fdrv-cubic-waveshaping-study.md)
between the gain/scratch and state-variable profiles. It produces a static
**510-byte, 39-packet** body, stored as **512 bytes** after two final zeros.
The four inputs are raw oscillator cells `60/70` and gained samples `90/91`,
ordered `[60,90,70,91]`; four shaped results occupy `92/93/94/95` (hex).
The filter consumes `93/95`, the gained then shaped pair. Raw-channel shaped
results are retained as scratch because the exact quad profile includes them.
Functional main A/B still carry the final filtered result.

All five profiles initialize their consumed ports. Every per-sample multiply,
magnitude, addition and filter update goes through the packet interpreter.
The host performs no per-sample waveshaping. Initial seeds and coefficients
remain ten and eleven; cubic inputs and outputs are already written before
read. The named data set becomes 25 cells with extent **150**, exactly the
smallest recorded enum-0 reservation. This leaves no spare numerical data
extent in those owners and establishes no live allocation or issue budget.

The authored composed fixture restricts amplitude to `0..0.5` for input
headroom; gain remains `0..1`. Actual cubic reads are checked every frame
against the proved finite `[-1,1]` domain. Other amplitude ranges retain the
unshaped renderer's contract and are not silently clamped for waveshaping.
The planner rejects `--waveshape` without `--cutoff` and accepts no implicit
truth-value conversion for the API flag.

```sh
python3.13 tools/bmc_filtered_voice.py local/waveshaped.wav --waveshape --frames 12000
python3.13 tools/fantom_voice_plan.py local/b0c1a.bin local/shaped-plan-dsp4 \
  --cutoff 1000 --waveshape --frames 12000
python3.13 -m unittest discover -s tests -p 'test_waveshaped_voice.py' -v
```

Independent relocation verifies **70 two-byte address fields**, protecting
**370 other logical bytes**. Only exact cubic/filter recognizers admit the
transfer walk through mixed packets. All fragments are joined before the
single final storage padding/conversion; inserting two padding bytes after
the cubic would shift and corrupt the following filter. Export manifests
record both logical and stored lengths/hashes. The [render-write study](kernel-audio-abi-study.md#render-write-source-extent-and-completion-state-2026-11-11)
now distinguishes the 512-byte backing source from the exact 510-byte destination
write. Numerical program capacity uses the logical write length; planner manifests
include the recorded-base geometry without selecting a live load address.

The 12,000-frame original render matches a separately rendered oscillator
voice followed by independent scalar cubic and filter references for all
24,000 channel values, crossing five ring wraps. The default model body hash
is `c75803f83d50e0d89ae35c9f24ab06b4065f0b008639cea7d7355acfea2d1b0a`; its peak is `0.3223646047275704`, 0.2305023653442409 `0.2305023653442409`. Five relocated canary-ring
renders match another 120,000 channel values. These are software results,
with the same hardware and entry/ownership gates as the unshaped body.

The complete suite passes 415 tests at this checkpoint (57.989 seconds); the
new shape/composition tests retain all default and hardware-boundary checks.
