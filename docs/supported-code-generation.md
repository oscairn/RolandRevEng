# First supported code-generation subset

2026-11-10. `tools/bmc_subset.py` turns a named dry/wet or four-stage allpass operation
and explicitly assigned indices into exact packet sequences independently matched
against native FETDRIVE and LINEDRIVE expressions. This is a constrained semantic code emitter and
inverse decoder, not a general DSP assembler, scheduler or standalone engine.

## Dry/wet functional contract

With contextual stock MFX inputs `L/R` at `2016/2017`, data-array values `W(a/b)`
already computed, and coefficient-record slots `d/w/p/m`, the resulting main paths are:

```text
A = (L * Cd + W(a) * Cw) * Cp * Cm
B = (R * Cd + W(b) * Cw) * Cp * Cm
```

The dry/wet and gain comparisons in [the MAC study](dry-wet-mac-study.md) establish
these formal expressions. Finite-precision rounding, fused arithmetic and silicon
timing remain untested. Resource indices are assignments, not allocations or ownership
checks. The emitter preserves the observed packet ordering rather than attempting to
schedule operations from algebra alone.

The dry/wet fragment is 60 logical bytes, with packet starts at relative offsets
`0, 10, 20, 34, 44, 54`. The two wet indices must be distinct and in `0..0x7ff`, avoiding
aliases from the native circular-data mask. The four coefficient indices must be
distinct and in `0..0xfff`. Distinctness retains the independently checked subset;
it is not a claim that hardware prohibits shared sources. Coefficients use tag C,
and the contextual input addresses stay fixed. Unknown controls, extension variants,
tags, extra packets and schema fields are rejected.

Entry/exit instructions, output stores, routing, data initialization, coefficients'
values, program placement and stop/start management are intentionally absent. A
fragment cannot be loaded as a complete program. The [kernel ABI follow-up](kernel-audio-abi-study.md)
recovers the stock `ff70/ff71` mute-mode update, manager reservations and shared routing.
It does not establish a safe executable wrapper or the meaning of `00f8`. The fixed
`2016/2017` inputs above are one desktop instance; other instances and firmware use
different operands. This template performs no resource or routing relocation.

## Use without vendor artifacts

From the repository root:

```sh
mkdir -p local
python3 tools/bmc_subset.py assemble examples/dry-wet-tail.json local/my-tail.bin --stored
python3 tools/bmc_subset.py disassemble local/my-tail.bin --stored
python3 tools/bmc_dsp.py local/my-tail.bin --stored
```

Omit `--stored` for logical big-endian packet bytes. The template length is already
divisible by four, so storage conversion needs no extra padding. The command refuses
to overwrite an existing output. It never opens a device or modifies a firmware image.
The example indices are original synthetic assignments, not a reserved hardware slot.

The integration check generates both stock tails from their extracted assignments
and compares all 60 bytes with their independently matched program regions. Structural
round trip alone is not the semantic evidence: that comes from the separate native
expression comparison. Synthetic tests also exercise schema/bounds rejection, unknown
encodings, storage byte order and the command-line round trip.

## Four-stage allpass contract

The second template, `allpass4`, reproduces both independently checked LINEDRIVE
four-stage filter chains. Its seven source data indices represent the main input x,
state values s1/s2, factor k, and subsequent states s3/s4/s5, in that order. It computes:

```text
y0 = s1 + (s2 - x)  * k
y1 = s2 + (s3 - y0) * k
y2 = s3 + (s4 - y1) * k
y3 = s4 + (s5 - y2) * k
```

Its six target data indices receive `x, y0, y1, y2, y3, y3`, respectively. The names
describe dataflow, not automatic filter-state allocation: callers must arrange the
history and factor before each invocation. All thirteen source/target indices must
be distinct and in `0..0x7ff`, retaining the tested subset. The same-packet stores
capture the **incoming** arithmetic value while the arithmetic computes the next
stage; a sequential store-after-compute model produces the wrong state.

The [MAC/store study](mac-controls-and-issue-study.md) compares all twelve stores across the
two native chains as signed symbolic polynomials. The emitter also reproduces both
82-byte regions byte for byte. It does not prove stability for arbitrary factors or
history, hardware precision, or safe rescheduling.

```sh
python3 tools/bmc_subset.py assemble examples/allpass4.json local/my-allpass.bin --stored
python3 tools/bmc_subset.py disassemble local/my-allpass.bin --stored --length 82
python3 tools/bmc_dsp.py local/my-allpass.bin --stored --length 82
```

The allpass fragment has 82 logical bytes and 84 stored bytes. The final two zero
padding bytes are included **before** reversing storage words. `--length 82` is
explicit when decoding the stored fragment; arbitrary trailing bytes cannot be hidden
as padding. Neither template constitutes an executable program on its own.

## Literal encoder

`bmc_dsp.encode_literal(value, width)` now complements the existing decoder. Width is
explicitly 2, 3 or 4 bytes. It selects the representable value with the smallest absolute
error; half-way cases use nearest/ties-to-even, and equal-error exponent choices use
the finest quantum. Zero has a canonical positive encoding. Non-finite numbers and
values outside the selected width's finite range are rejected rather than clipped.

This is an explicit **software assembler policy**. The actual CORE1 float-write port's
rounding is still unknown. A caller can compare `literal(encoded)` with its requested
value before accepting quantization. All 65,536 two-byte encodings preserve their
numeric values through decode/encode/decode, including alternate representations;
tests also check width-specific limits and quantization ties.

## Next extension

Recover each additional instruction's input/output and simultaneous-issue behavior
before adding it. Especially avoid interpreting a packet's written control order as
a sequential execution schedule. A useful eventual tiny-engine backend needs proven
entry/exit behavior, resource allocation, state initialization and cycle constraints in
addition to emitting these bytes.


The [offline interpreter](fragment-emulator.md) can now execute these exact
logical-byte fragments with explicit memory/coefficient/input dictionaries and
per-packet traces. It retains all emitter restrictions and supplies no wrapper or
resource allocator. Original WAV demonstrations and independent stock-byte tests
are documented there.
