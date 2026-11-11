# Offline functional fragment emulator

2026-11-10. `tools/bmc_emulator.py` executes logical packet bytes for four checked profiles. Stereo input takes 10 bytes, the dry/wet tail
has 60-byte and 80-byte forms, and the four-stage allpass takes 82 bytes. This is a packet-stepping functional model with memory and
per-packet traces. It is not yet a complete Roland effect or a cycle/bit-accurate
BMC emulator. No vendor plugin or instrument is executed.

## Contract and issue model

```python
from bmc_emulator import execute_fragment
result = execute_fragment(program, data, coefficients, io)
```

`program` is logical `bytes`, not word-reversed storage. The complete stream must
first pass the strict inverse decoder in `bmc_subset.py`; extra wrappers, unknown
controls, altered extensions and partial templates are rejected. The interpreter
then steps the actual packets, rather than returning a whole-template expression.

`data` maps indices `0..0x7ff` to finite real numbers. `coefficients` maps slots
`0..0xfff`. The optional `io` map uses contextual addresses `0x2016/0x2017`
by default. Stereo input and dry/wet profiles also accept the checked
alternate pairs when encoded in their packets.
These are separate explicit dictionaries. Keys must be integers, excluding booleans;
values must be finite integers or floats, excluding booleans. Every supplied entry
is validated, including unused entries. Missing reads fail. No memory is silently
zeroed and no uninitialized functional port reads as zero.

The result contains eight functional `ports`, copied/updated `data`, and `trace`.
Each trace event has logical byte `offset`, `header`, eight-port `before` and
`after` snapshots, and address-to-value `writes`. Unused ports remain `None`.
Ports 0/4 carry the checked main A/B values; this is not a physical register map.
Caller dictionaries remain unchanged on success and failure, and returned snapshots
do not alias each other.

Arithmetic and stores in one packet read its incoming ports. Loads read current
memory and become available in the next packet. Port changes and data writes commit
together at packet end. In particular, an allpass packet stores the incoming stage
while calculating its successor. The final pair of stores receives the same final
value. Co-issued post/master coefficient loads cannot affect the current multiply.

Only the contexts already accepted by the inverse decoder are executable. This
includes indexed transfers with shared operand pools, the two dry/wet MAC forms,
`0403/4503` gains and the alternating `0e0b/22c1`, `0e0b/12c2` allpass forms.
A familiar control word elsewhere is not automatically supported. The
[semantic ledger](opcode-semantics-ledger.md) lists additional research results
that are deliberately outside this executable subset.

## Original audio demonstrations

From the project directory, without vendor artifacts or extra dependencies:

```sh
python3 tools/render_fragment_demo.py local/my-fragment-demo
```

The output directory must be new. The tool writes `allpass-impulse.wav`,
`dry-wet-tones.wav` and a numerical `summary.json`. It refuses clipping/non-finite
PCM conversion and existing output paths. Original signals and host-written history
wiring supply the fragment inputs; the demo does not reconstruct stock LINEDRIVE.
The mix uses explicit host delay lines, and the allpass uses explicit one-sample
history updates between invocations. Neither claims the stock circular-state ABI.

The mono impulse checks energy against a unit-magnitude allpass contract. The stereo
mix checks every frame against an independent channel equation. WAVs use an explicit
software 48 kHz grid and signed 16-bit quantization. These are output choices, not
measurements of BMC sample rate or numerical format. The summary records program
hashes, peaks, RMS, energy and reference errors; generated audio stays local.

## Evidence and limits

[Independent corpus validation](fragment-emulator-validation.md) pins the native
image and four stock byte spans, reruns their native polynomial proofs, and compares
packet traces, coefficient timing and all stores against direct equations. Synthetic
tests separately cover the public API and rejection/aliasing boundaries. Generating
bytes with the emitter and decoding them again is not the sole evidence.

Floating arithmetic uses Python binary64 with explicit operation order. Native FMA,
fixed-point conversions, saturation, rounding, physical registers, issue latency,
clocking, circular indices, reset, routing and call/return state are not inferred.
The interpreter supplies no automatic history allocation, coefficient smoothing,
wrapper execution, device connection or loader. Hardware calibration remains a
separate requirement for fidelity.

The [next-program inventory](emulator-next-program-targets.md) selects LINEDRIVE
for the next complete-effect effort and names every remaining region. A successful
fragment render does not establish that a complete stock engine can yet execute.

## Conditional LINE reference pipeline

Python 3.13+ supplies `math.fma` for the separate
[native shaping oracle](line-prefix-shaping-study.md). A second original-signal
experiment combines that oracle with the checked stereo input packet,
two allpass fragments and the dry/wet fragment with scratch transfers:

```sh
python3.13 tools/render_line_reference.py local/line-reference.wav
```

This tool **does not execute the unknown DSP prefix**. It calls the recovered
native channel equations on the host, then steps the admitted fragment bytes.
It uses explicit unit stereo input mixing and original experimental controls:
drive scale 1/512, drive 1/2, rectified mode, smoothing 3/4, rational scale 1/2,
A=1/B=0 and equal dry/wet gains. These are fixture choices, not an extracted stock
preset or a recovered control mapping for the unresolved input-mix literals.
The later rational parameters have a separately checked
[grouped-write relation](line-prefix-parameter-study.md).

The host supplies a cold zero ring, fixed P=0, no other owner writes, and one
[native origin step](line-state-and-history-study.md) per generated frame. It
retains the pre-rational smoother values at logical3/6 separately from the
current factors27/28, executes the two actual allpass address assignments, and
feeds their current outputs 29/2a into the real tail assignment. The final two
admitted packets write and reload scratch cells 2b/2c. The host reads the
resulting ports for the WAV output.

An independent integration test uses direct five-value delay histories and
unrolled allpass equations instead of circular addressing or packet execution.
All 2,056 stereo frames agree exactly, crossing origin wrap. Separate source/
primitive tests supply the prefix evidence; this integration test alone is not
an independent proof of that prefix's arithmetic. A 12,000-frame render produced
peak 0.0998168982 and maximum factor magnitude 0.0248665508 without PCM clipping.
The WAV path must be new; the numerical summary prints as JSON.

This is a conditional functional reference fixture for further reverse engineering.
It is not a complete stock-program execution or a bit-exact native plugin model:
the prefix uses the declared FMA policy while the fragment interpreter retains its
binary64 operation policy. Actual parent cadence, warm state, hardware numeric/
timing behavior and native-plugin audio equivalence remain unverified. The 48 kHz
WAV grid is still a software output choice.

## LINEDRIVE from the Fantom image

Supply the pinned CORE1 file to render the same conditional fixture with
the original firmware slices:

```sh
python3.13 tools/render_line_reference.py local/fantom-line.wav --core1 local/b0c1a.bin
```

The default owner descriptor is `610a1674`. The `--owner` option selects
one of the other four recorded placements. The context reader checks the
image, owner reservation and packet boundaries. The interpreter consumes
254 logical bytes per placement across the stereo input, both allpass
chains and the mix with scratch transfers. The board image supplies the
actual operand assignments. For example, its right smoother history
reads at enum-0 base plus 6 and writes at plus 5. The desktop fixture
uses 7 and 6. The reader checks the history pairs individually.

The existing host prefix and reference ring model supply values for
the unadmitted packets. The same fixture gives exact output equality
through origin wrap in all five placements. Runtime selection,
on-device state and silicon issue timing remain open.
[Recorded placements and readback](kernel-audio-abi-study.md#offline-line-placement-and-readback-comparison)

`render_reference()` accepts optional `mono` and `stereo` coefficients for the
native-reference input mix. The fixture defaults to `(0, 1)`. The shared term is
computed as `fma(left, mono, right * mono)` and then added by FMA to each input
scaled by `stereo`, matching native `2df890..2df8a4`. These coefficients affect the
wet path only. They do not patch the firmware or resolve how its four fields are
bound. The default 12,000-frame Fantom reference WAV remains byte-identical.

With `--experimental-mix`, the renderer uses all four width-three literals and
the store operands from the stock `00e..038` packet slice. It computes the shared
B candidate and both per-channel candidate sums from those fields. All five
Fantom placements match the native-reference fixture through ring wrap at the
stock `(0, 0, 1, 1)` values. An asymmetric synthetic fixture distinguishes all
four operands. The match at stock defaults cannot establish hardware port state,
precision or behavior under unequal coefficients. The option covers the input
mix and its output samples. Native shaping still supplies the drive stage.

```sh
python tools/render_line_reference.py local/fantom-mix-experiment.wav \
  --core1 local/b0c1a.bin --experimental-mix
```

## Original one-pole kernel

`bmc_one_pole.programs()` assembles two 80-byte variants of the checked
mix and scratch profile. The current sample and previous output form

```text
y = x * (1 - feedback) + previous_y * feedback
```

The scratch packets write the next state. The next call uses the opposite
address pair. `filter_frames(frames, feedback)` initializes the first
pair to zero and alternates variants once per stereo frame. Each channel
has one logical state value and two alternating fixture cells. The test
checks independent channel responses, nonzero state across switches,
and the zero-feedback case. The fixture addresses and host alternation
need an owned reservation and a validated schedule for hardware use.
