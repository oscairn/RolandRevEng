# Offline functional fragment emulator

2026-11-10. `tools/bmc_emulator.py` executes logical packet bytes for the two
independently proved fragment families: the 60-byte dry/wet tail and 82-byte
four-stage allpass. This is a packet-stepping functional model with memory and
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
`0..0xfff`; optional `io` uses the full contextual addresses `0x2016/0x2017`.
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
