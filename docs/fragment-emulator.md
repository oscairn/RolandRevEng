# Offline functional fragment emulator

The [mapping-status inventory](bmc-mapping-status.md) separates the 18 executable
profiles, composed FDRV arithmetic and authored voices from a full BMC emulator.
Recent parameter-dispatch checks execute ARM control code, not new DSP opcodes.

The [Fantom ARM32 control fixture](fantom-eqvg-control-study.md) separately checks
the original CPU coefficient producers and selected manager paths. Its fallback,
float32 rounding and pre-arm completion clear differ from desktop assumptions.
This is selected CPU execution; it adds no BMC opcode or hardware calibration.

The [manager processing model](coefficient-manager-processing-study.md) separately
checks parameter interpolation, envelope completion and task flags against owned
original software processing. Its explicit ticks do not calibrate audio/device
cadence or change the admitted packet profiles.

The [EqVg producer layer](eqvg-filter-generation-study.md) adds generated live and
final-filter coefficients without admitting another opcode. The bounded
`native_literals` reference policy also accepts the final output profile, checking
all stereo fields and both occurrences of its first coefficient. Default execution
still decodes literal bytes; actual manager interpolation is separate.

[EqFaCal and UI-driven filter changes](fdrv-cubic-waveshaping-study.md#three-coefficient-filter-generation-and-ui-dispatch-2026-11-11)
now cover the input, resampling and two post-cascade stages. Full-precision
native filter literals can be supplied explicitly for the two checked literal
profiles; every value must encode to the actual serialized stereo fields.
Default interpretation still reads encoded values. Separate 12,000-frame runs
check native-double and explicitly quantized filter coefficients, with matched
audio/ring/cache state under each policy. No new opcode profile is admitted.

[Setter-derived FDRV updates](fdrv-cubic-waveshaping-study.md#setter-derived-live-updates-2026-11-11)
now exercise drive, wet, level and slope through independent native-policy
envelopes while complete audio/ring/cache comparisons remain exact. Physical
control timing and full EQ generation remain unverified.

2026-11-11. `tools/bmc_emulator.py` executes logical packet bytes for eighteen checked profiles. Stereo input takes 10 bytes, the dry/wet tail
has 60-byte and 80-byte forms, and the four-stage allpass takes 82 bytes. This is a packet-stepping functional model with memory and
per-packet traces. A complete FDRV arithmetic reference now composes these profiles;
cycle/bit-accurate BMC execution and device loading remain unverified. Native checks
execute isolated original callbacks in owned buffers, without launching a plugin
or accessing an instrument.

The [complete FDRV arithmetic path](fdrv-cubic-waveshaping-study.md#complete-arithmetic-and-output-milestone-2026-11-11)
adds `fdrv_output_pair` (188 bytes). `fdrv_output_study.execute_frame()` runs the
eleven-fragment, 1,692-byte chain without native/vendor inputs, taking explicit
ring, origin, stereo samples, live coefficients and auxiliary cache state. It
returns new ring/cache state and final audio without mutating its arguments.
Bridge cells 60..63 stay ephemeral. Both 12,000-frame scale-pair fixtures match
all 2,048 ring cells, six cache slots/two cursors and stereo output every frame.
The stock `00f8` and IO-store timing remain outside this arithmetic model.

The [cascaded history filters](fdrv-cubic-waveshaping-study.md#cascaded-history-filter-milestone-2026-11-11)
add a strict 164-byte profile, extending the chain to 1,504 logical/stored bytes.
Nonzero coefficients expose both recurrences; each scale-pair fixture matches
552,000 native memory values through five wraps. Current first/second stores are
checked; the following filter's evolving prefetch values are explicitly excluded.

The [post-cubic mix](fdrv-cubic-waveshaping-study.md#post-cubic-history-mix-milestone-2026-11-11)
adds a strict 110-byte profile and extends the input chain to 1,340 logical/stored
bytes. Raw mixed values are stored before live gain; final values match the next
stock packet's input stores without admitting that packet's other operations.
Both scale-pair variants match 504,000 native data comparisons through five wraps.

The [resampling/drive milestone](fdrv-cubic-waveshaping-study.md#connected-resampling-and-drive-milestone-2026-11-11)
connects the filter bank through clipping and cubic outputs: 1,230 logical bytes,
77 packets, with 456,000 comparisons per drive variant through five wraps. The
122-byte `resample_drive_pair` supports the two recorded fixed drive literals,
exactly representable tap constants and binary32 live gain. ZENOLOGY's native
double differs slightly from its DSP literal; the interpreter's explicit native
policy does not establish silicon precision. Whole-FDRV execution remains open.

The [four-section filter bank](fdrv-state-variable-filter.md#four-section-filter-bank-milestone-2026-11-11)
extends the input chain to 902 packet-executed bytes before resampling arithmetic.
Its separate model ring matches 336,000 values against a shortened native prefix
through five wraps. The new 226-byte recombination-with-output and 202-byte terminal
filter forms retain strict template admission; synthetic bridge stores do not prove
hardware allocation. Earlier first-stage and two-filter tests remain distinct.

The [completed input-to-first-filter stage](fdrv-state-variable-filter.md#completed-input-to-first-filter-stage-2026-11-11)
combines an 86-byte native-policy prefilter and 184-byte filter. A separate packet-only
ring matches 120,000 native callback values through five wraps. This removes the
host-computed input mix from that stage's signal path; the rest of FDRV remains open.

The [80-byte clipped half-sample pair](fdrv-cubic-waveshaping-study.md#stereo-half-sample-interpolation-and-clipping)
adds two average-before-clip results, two direct clipped results and unmodified
current-history stores. Packet traces, isolated native arithmetic and captured
callback cutpoints are checked independently. It is distinct from the existing
80-byte dry/wet scratch profile; only complete exact structures execute.

The [126-byte cubic quad](fdrv-cubic-waveshaping-study.md) executes four
independent bounded curves through eleven packets. Its authored preload plus
116-byte stock body has exact inverse recognition, independent native curve
checks and conditional full-callback cutpoint comparison. Inputs must be finite
and in `[-1,1]`; arbitrary short/miscellaneous forms remain rejected.

The [original filtered voice](original-bmc-filtered-voice.md) now composes four
existing profiles in one ring. All 24,000 channel values match a separately
rendered oscillator voice plus independent scalar filter through five wraps,
and all five relocated bodies match with nonseed canaries. This composition adds
no new opcode admission or hardware precision claim.
Its optional cubic stage now forms a 510-byte, 39-packet voice with the same
ten seeds/eleven coefficients. Independent scalar shaping/filter checks and
relocation canaries cover the composed body; storage padding is applied only
at its end.

The [84-byte add/MAC profile](auxiliary-save-restore-and-add-mac.md) adds two
proved register sums, their following shared-factor MACs, pre-arithmetic
port-1/port-5 stores and next-packet loads. Its binary32 coefficient and
binary64 FMA policy requires Python 3.13+. All 1,024 asymmetric channel results
match isolated native arithmetic execution, separate from pure byte interpretation.
The separate [184-byte state-variable profile](fdrv-state-variable-filter.md)
now includes the first filter block's producers and one balanced save/restore
per port. Other auxiliary contexts and arbitrary stack behavior remain outside
admission. Its state/output values match the independent equations and real
native callback through wrap, with all nine valid cursor pairs checked.

The additional `coefficient_shift4` profile takes 38 logical bytes. Its
numeric policy follows the checked VSOD native prefix, including binary32
coefficient reads and signed64/fixed32 conversion. It uses Python 3.13+
for the native fused input mix.

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
A complete VSOD prefix also executes the exact `0812/1500` half-sum,
`fdd4` coefficient conversion and `ffe0` store.
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

Floating arithmetic uses Python binary64 with explicit operation order. The VSOD
prefix adds the native FMA and fixed32 shift policy described below. Saturation,
rounding, physical registers, issue latency,
clocking, circular indices, reset, routing and call/return state are not inferred.
The interpreter supplies no automatic history allocation, coefficient smoothing,
wrapper execution, device connection or loader. Hardware calibration remains a
separate requirement for fidelity.

## Stored fixed-point coefficient prefix

The exact `coefficient_shift4` profile corresponds to VSOD `004..02a`.
It loads left and right inputs and coefficient C1, computes the native
`fma(left, 0.5, right*0.5)` and converted C1 concurrently, then multiplies
the half-sum by C0 while storing the converted C1 through port 7.
The native stores at `273984` and `2739a8` independently bind the two
results to their actual data records. All five Fantom VSOD placements
reproduce the profile with relocated inputs, coefficient slots and target.

```sh
python3.13 tools/bmc_subset.py assemble examples/coefficient_shift4.json \
  local/coefficient-shift4.bin --stored
python3.13 tools/bmc_subset.py disassemble local/coefficient-shift4.bin \
  --stored --length 38
```

The example assigns C0 to slot 0, C1 to slot 1 and the store to data cell 1.
The executor reads both coefficients as binary32. Conversion truncates
`C1 * 2^32` toward zero, shifts the signed64 integer left by four with
wrap, converts back to binary64 and multiplies by `2^-32`. C1 values
outside the non-overflowing fixed32 conversion range are rejected.
Near zero this differs from multiplying C1 by sixteen. Positive
`2^27` wraps to negative `2^31` under the selected native policy.
BMC conversion precision and exceptions require hardware measurements.

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

## Direct native LINE callback

`native_line_reference.py` executes the pinned ZENOLOGY ARM64 translation
of the complete LINE sample callback at `2df874..2dfd94`. The command
runs as its own macOS ARM64 process and constructs the callback's input,
output, literal, coefficient and circular-memory structures from the
recovered records. It supplies the same original fixture parameters as
the conditional LINE renderer, with a cold zero ring, P=0 and one origin
step per generated frame.

```sh
python3.13 tools/native_line_reference.py local/native-line-reference.wav \
  > local/native-line-reference.json
```

The tool verifies the image hash, exact callback bounds and complete
decoding of the position-independent body. The body contains arithmetic,
memory operations and a final return. Its copied code has no helper call
or external branch. The tool writes its own memory mapping, switches it
to read/execute, invalidates the instruction cache and invokes the exact
callback bytes with pointers to its allocated buffers. These objects stay
alive for the entire invocation loop. It then releases the mapping.
An original two-instruction helper reads the host FPCR before and after
the run. The observed FPCR was zero.

The 12,000-frame native run produced peak `0.09981689821550582`.
11,804 stereo frames agreed exactly with the conditional Python
reference. The maximum absolute sample difference was
`1.3877787807814457e-17`, consistent with the reference interpreter's
separately rounded multiply/add operations in the filter stages.
A separate 2,056-frame subprocess check crosses ring wrap and checks
that an existing output is preserved.

This supplies execution evidence for the native translation with the
declared memory fixture. BMC program-byte execution, native-plugin framework
initialization, parent scheduling and BMC numerical behavior remain
separate requirements. The complete effect's BMC instruction sequence
still contains unresolved controls.

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

## Experimental FETDRIVE first stores

```sh
python3.13 tools/render_fetdrive_window.py local/b0c1a.bin \
  local/fetdrive-first-stores.wav --base 0x4020 > local/fetdrive-first-stores.json
```

The renderer reads the pinned Fantom CORE1 packet sequence, data addresses,
drive scale, two affine literals per channel and post gains. It models the
path from supplied mixed inputs to the first `9fe0` stores using the native
reference's fixed-point conversion, bipolar clamp, fused affine and square.
The first affine literal supplies slope and the second supplies bias. The
two stock values are equal, so exchanging them leaves the prediction equal.

The WAV contains the predicted store values for two sine inputs at a software
rate of 48 kHz and a supplied live drive of 0.5. The JSON records the predicted
values at both signs of the first quantizer bin and immediately below, at and
above both clamp limits. All five stock placements predict the same values
with this fixture. The model stops at the first stores, before the later
filter and mixing stages. Isolated opcode semantics and hardware precision
remain unverified.

## Native FETDRIVE execution fixture

```sh
python tools/native_fetdrive_reference.py local/native-fetdrive-reference.wav \
  --frames 12000 > local/native-fetdrive-reference.json
python -m unittest discover -s tests -p test_native_fetdrive_reference.py -v
```

The pinned desktop ARM64 callback `2f7de4..2f81c4` now executes in an
isolated macOS ARM64 process. The fixture checks the artifact hash,
complete decoding, a conservative instruction allowlist, callback bounds,
the final return and the five live-coefficient pointer fields. Its only
data dependencies are supplied constructor memory, input/output pointers,
live coefficient records and a cold 2,048-double ring. The existing
cutpoint checker independently binds the first shaped stores to cells 3/4.

The fixture retains constructor mono/stereo values `(0,1)`, drive scale
`0.0015476426307448495` and post-rate gain `1`. Its live slots are
master `1`, drive `0.5`, dry `0.5`, wet `0.5` and post `1`. The wrapper
base is zero, and the explicit ring origin advances once per generated
frame. Input tones are left `0.1*sin(220 Hz)` and right `0.08*sin(330 Hz)`
on a software 48 kHz grid.

At every frame, the retained shaped stores are compared bit for bit with
`native_shaped_store()`. All 24,000 values agree in the 12,000-frame run,
including ring wrap. The full native stereo output is finite, with peak
`0.09773264180104757` and RMS `0.06125754092361567`. Three subprocess
tests check wrap, fresh-render determinism and existing-output preservation.

The WAV contains the complete native callback output. The fixture now also
compares every final sample with the full Python reference described below.
Constructor filter coefficients are retained at their defaults while the
test signals use 48 kHz; there is no sample-rate setup or preset calibration.
DSP bytes, parent cadence, instrument routing and hardware precision are
not executed or verified.
Qwen wrote and ran the initial fixture. Local review added the existing
constructor/cutpoint binding checks, then reran the tests and longer render.

## Full Python FETDRIVE reference

```sh
python tools/fetdrive_state_study.py > local/fetdrive-state-study.json
python tools/render_fetdrive_reference.py local/fetdrive-full-reference.wav \
  --frames 12000 > local/fetdrive-full-reference.json
```

The Python model now covers the entire native callback's observable arithmetic
and ring writes under the supplied fixture. It agrees bit for bit at all
24,000 final output samples in a 12,000-frame native comparison. The native
and Python WAV files are byte-identical. Native invocation also checks all
24,000 first shaped stores independently. The test crosses ring wrap at
2,056 frames and validates fresh-render determinism.

For a shaped value `T`, the variable allpass factor is
`k = clamp((2-T)/(T+2), -1, 1)`. With current mixed input `x`, the native
allpass order is `y = previous_input + fma(-x, k, previous_output*k)`.
The later filter computes `y*b + fma(previous_input, a, previous_output*c)`,
using its separate history pair. The constructor doubles are
`b = 0.9996439371675712`, `a = -0.9996439371675712` and
`c = 0.9992878743351423`. The opposite numerator coefficients identify
a DC-blocking stage. The model retains the native multiply, fused multiply-add
and final add order.

The state checker proves the native pointer path, exact constructor-record
identity, DSP operand and double access for each history pair.

| State | Left store / history cell | Right store / history cell |
|---|---|---|
| Allpass input | `7 / 8` | `b / c` |
| Allpass output | `9 / a` | `d / e` |
| DC-block input | `f / 10` | `13 / 14` |
| DC-block output | `11 / 12` | `15 / 16` |

Under the explicit origin step, the previous frame's store and current
history read share the same physical ring index. All eight relationships
are checked across all 2,048 possible origins. This establishes the delay
for the fixture's cadence; the instrument's parent schedule remains open.
The first shaped values use cells `3/4`, factors `5/6`, wet copies `17/18`
and output scratch `19/1a` in hexadecimal.

Counted literal groups explain why both channels use one native representative
for each filter coefficient.

| Coefficient | Native field | DSP fields | Group | Setup call |
|---|---|---|---|---|
| `b` | `8` | `b8 / 14e` | `a50d98` | `32c940` |
| `a` | `18` | `c2 / 158` | `a50db8` | `32c95c` |
| `c` | `28` | `c5 / 15b` | `a50dd8` | `32c980` |

All six DSP fields are width three. The native loads, representative
constructor values, counted group records and slot-`c8` call arguments
are checked independently. Encoded DSP literals differ slightly from their
native double defaults; this model evaluates the native defaults.

The model uses the same explicit fixture parameters as native execution.
It does not step unadmitted DSP words, establish `bedb`'s individual state
effects or provide general opcode execution. It remains a numerical oracle
for further DSP work. It requires the pinned corpus, Capstone and Python
3.13+; rendering the Python reference does not execute vendor machine code.

Qwen's full-model job reached its 600-second limit with an unfinished draft.
Its duplicated quantizer and filter/state equations were not adopted. Local
native def/use checks supplied the corrected model, and actual execution
established exact output agreement. The earlier Qwen native fixture was
retained after review and remains the execution oracle.

## Native TRANSIENT and independent output

The [TRANSIENT fixture](special-ops-and-exp-study.md#native-transient-fixture-and-conditional-envelope-reference)
extends native execution to a callback with three real math imports. It checks
peak/log stores, exp/smoothing stages and the final gain against independent
finite kernels. The [full detector reference](transient-full-reference.md)
now supplies its exp arguments independently. Fifteen detector values per
frame and a separate cold-ring output render match the native callback,
including silence, steps, signed zero and negative live modes. The two
12,000-frame WAVs are byte-identical. No additional DSP control is admitted
by this native reference.

## Original feedback oscillator

The [original allpass oscillator](original-bmc-allpass-oscillator.md) composes
the supported 38-byte coefficient prefix and 82-byte allpass chain into one
static 120-byte fragment. All sample arithmetic goes through the packet
interpreter. Five initialization sine evaluations seed its feedback state;
the host performs no per-sample phase or waveform synthesis. It runs without
vendor artifacts and retains the explicit native-ring cadence assumption.
It still needs hardware data encoding, ownership, wrapper, timing and output
routing before it can serve as an instrument engine.


## Independent FETDRIVE cross-check (2026-11-11)

`tools/fetdrive_crosscheck.py` independently rebuilds the scalar input-mix and
first-shaped-store expressions and executes the complete original FETDRIVE
callback in owned memory. Its 2,056-frame fixture checks **8,224** mixed/shaped
values through wrap, with 1,370 nonzero input-mix cases, asymmetric inputs, six
nonzero drive values and three post gains. These are numeric cutpoint checks,
not a second complete packet effect or new opcode admission.

Qwen's 126.5-second review delivered a report and scalar probe. Independent
checking corrected several errors: packets 3e/d4 loads mixed state, while 66/fc
stores the shaped result; `afe0/bfe2` at 2e are store forms, not incoming loads.
Two-byte BMC literals are not IEEE half precision. Fixed32 truncation followed
by LSL 9 has gain 512 and a nominal post-shift grid 2^-23, not 2^-9. The worker's
asserted one-step/scale-insensitivity conclusion did not follow from its output
mismatches and is rejected.

Using the native constructor scale versus the encoded three-byte DSP value
changes **3,255 of 4,112** checked shaped outputs. These source precisions are not
interchangeable. The independent probe matches original native execution using
constructor precision; it does not settle physical DSP precision. The input-mix
literal alias/control source relation and prefix writeback are still unresolved,
so the worker's candidate contexts were not admitted to the packet interpreter.
No worker code, vendor listings or raw binary data is committed.

```sh
python3.13 tools/fetdrive_crosscheck.py --frames 2056
python3.13 -m unittest discover -s tests -p 'test_fetdrive_crosscheck.py' -v
```
