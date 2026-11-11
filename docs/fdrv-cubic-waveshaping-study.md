# FDRV cubic waveshaping, interpolation and clipping

The [post-cubic history mix](#post-cubic-history-mix-milestone-2026-11-11)
now extends the independent chain to 1,340 logical bytes, including live gain and
the paired Fantom/ZENOLOGY post scales. The following filter/output region remains
outside packet admission.

The [connected resampling/drive milestone](#connected-resampling-and-drive-milestone-2026-11-11)
now supplies clipping and cubic inputs from an independent 1,230-byte packet
chain, including the four earlier filter sections. Both recorded drive-literal
variants match checked native-fixture cutpoints; full FDRV remains incomplete.

2026-11-10. Static Python/Capstone analysis and explicitly isolated native arm64
execution. Native ZENOLOGY SHA-256:
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom-0 v1.08 CORE1 payload SHA-256:
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
FDRV is a different algorithm from FETDRIVE. No BMC hardware was accessed.

**Result:** four native FDRV waveshaping windows compute
`x * (x*x + (3 - abs(3*x)))`. Their source and destination records are bound to
actual DSP data operands. All five Fantom FDRV placements retain the packet
contexts and relative resource relationships. The reference agrees bit for bit
with an isolated native window on 1,034 inputs, including signed zero and the
smallest positive and negative subnormals.

**2026-11-11 update:** the exact 126-byte `cubic_quad` profile now executes in
the strict emitter/interpreter. A ten-byte authored preload supplies the first
left and incoming second-right samples; the following 116 bytes match stock
FDRV `378..3ec`, including all five Fantom relocations. Independent four-input
vectors and the isolated native curve match bit for bit. The full native callback
also supplies input/output cutpoints for a conditional window comparison; these
captured inputs do not constitute an independent whole-FDRV model. No general
opcode, complete FDRV program or hardware precision policy is admitted.

## Four separate native input/output windows

The call-free native callback is `3050ec..305ea8`. The checker reconstructs its
constructor records independently and uses the existing pointer/index provenance
tracer. Each source load and result store must use the proved data path, a masked
index and an unsigned scaled double access. It also checks the actual d0 load,
the arithmetic instructions and the d0 store, retaining d0 and constant-register
provenance across intervening instructions.

Offsets and cells below are hexadecimal. Source-transfer fields and representative
constructor fields can differ: a constructor may reuse the record for an earlier
store to the same cell. The checker compares both actual field values.

| Source cell | Source-transfer field | Constructor representative | Native source load | Native addition | Result store / field / cell |
|---|---|---|---|---|---|
| `e` | `376` | `36a` | `3059fc` | `305a1c` | `305a30` / `3b2` / `12` |
| `10` | `3a4` | `360` | `305a40` | `305a5c` | `305a70` / `3dc` / `18` |
| `f` | `384` | `374` | `305a80` | `305a9c` | `305ab0` / `3c4` / `13` |
| `11` | `3b4` | `382` | `305ac0` | `305adc` | `305af0` / `3e6` / `1a` |

The native arithmetic forms `3*x`, `x*x` and `-(3*x)` independently, selects the
nonnegative magnitude, subtracts it from three, adds the square, then multiplies
by x. Three is an actual `FMOV` immediate at `305a00`; its register stays intact
until the final window's subtraction. The DSP window contains the exact two-byte
`4300` literals, which decode to three. No FMA is substituted for the separate
native multiplies/additions. The fourth window reuses d1 for the subtraction and
sum; the checker retains that difference.

For the finite stock clipped-input domain `[-1,1]`, the curve is odd, maps zero
to zero and maps ±1 to ±1. At ±.5 the result is ±.875. The reference preserves
negative zero. It rejects nonfinite, boolean and out-of-domain inputs rather than
claiming a general native exception or DSP precision policy.

## What this adds to the short-add investigation

The existing [short-add inventory](short-add-context-candidates.md) found six
short-family `5d46` contexts in FDRV. Four are in state/filter sequences; two
are in the waveshaping window. The latter window interleaves two left and two
right paths in DSP packets even though native code evaluates them in sequence.

The candidate short additions associate as follows:

| Candidate DSP packet / control | Native addition in its containing curve |
|---|---|
| `392` / `1c42` | `305a1c` |
| `3c6` / `1c42` | `305a5c` |
| `39c` / `5d46` | `305a9c` |
| `3d0` / `5d46` | `305adc` |

Thus packet `39c` corresponds to the first right curve, while `3c6` corresponds
to the second left curve. The new exact profile reconstructs their producers
and coissued stores, using incoming ports throughout each packet. The initial
right value is written to its own cell before that packet loads the first right
input; treating the store as observing the new load would corrupt the fourth curve.
The first-right curve finishes before its old port-5 value is stored concurrently
with the next right producers. The final packet stores the second-right curve
and reloads the first pair of shaped values into ports 2/6.

## Exact cubic profile and partial short fields

The original JSON example is `examples/cubic-quad.json`. Its four sources and
four targets are ordered `[left1,left2,right1,right2]`, all eight distinct integer
data indices below `800`. It writes all four curves plus an unchanged copy of
source right2. Final ports are `[left2,C(left2),C(left1),None,
right2,C(right2),C(right1),None]`. Each source must be supplied in the finite
checked `[-1,1]` domain. There are no coefficient reads or implicit zero seeds.

| Short controls | Functional role in the exact profile |
|---|---|
| `2410 / 6510` | I2 = 3×A; I6 = 3×B, from pool literal zero |
| `1400 / 5504` | I1 = A²; I5 = B² |
| `1440 / 5544` | I1 = I1×A; I5 = I5×B |
| `2e92 / 6f90` | I2/I6 = literal − magnitude of incoming I2/I6 |
| `1c42 / 5d46` | I1 += I2; I5 += I6 |

The first miscellaneous form uses literal pool word one, the second word zero;
both are fixed `4300` (three) here. Magnitude follows the native `>= 0` selection,
including negative zero, rather than replacing its operation order with a fused
expression. The complete profile recognizer protects controls, literal references,
headers, repeated resources and constants. General miscellaneous-header grammar
remains opaque. A familiar word outside this context is still rejected.

Ten admitted short multiplications share destination `(word >> 12) & 7`,
source `(word >> 6) & 7` and six-bit operand reference `word & 63`.
Their masked class `word & 8e00` is `0400`; the two sums normalize to `0c00`.
This is a **partial field map**, not permission to execute arbitrary masked-class
matches. Only ten whitelisted multiplies, the two exact miscellaneous forms and
complete checked profiles execute. Operand references below eight select ports;
`10` selects literal pool word zero in this window. Other references and all
other families remain unadmitted. In the earlier filter, `6547` can now be
represented as I5×I7, but I3/I7 carry equal values there: that context alone does
not independently resolve coefficient-port choice.

The conditional full-callback check sets a nonzero declared input gain (`.75`)
to avoid a silent/default-zero cubic fixture. It captures the four source cells,
executes the actual 126-byte profile, and compares all four output cells with
the callback and scalar curve. The provenance audit rejects a later write to any
captured source/target cell. Counts remain separate from the independently
modeled first filter. Context-level `source_port_binding_verified` and
`per_packet_port_state_verified` flags describe the native cutpoint trace alone;
exact-profile packet execution supplies the additional functional interpretation,
without physical port-state observations.

## Five Fantom placements

Fantom list `610e5a94` contains five 1,420-byte FDRV programs. Its descriptors and
streams, not just copied metadata, are read by the checker. Each source cell is
the data base plus `e/10/f/11`, and each target is base plus `12/18/13/1a`.

| Program base | Data base |
|---|---|
| `4020` | `100` |
| `8040` | `320` |
| `9040` | `3b6` |
| `a040` | `44c` |
| `3020` | `c0` |

These are recorded stock placements, not new allocations or proof that a
particular effect is selected on a running instrument. Numeric equivalence and
timing on the BMC remain unmeasured. The exact cubic profile is available offline; no wrapper, transport or firmware
patch is generated.

## Reproduce and review

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --core1 local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_cubic_study.py --execute-native --native-window-frames 12000
python3.13 tools/bmc_subset.py assemble examples/cubic-quad.json local/cubic-quad.bin --stored
python3.13 tools/bmc_subset.py disassemble local/cubic-quad.bin --stored --length 126
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_fdrv_cubic_study.py' -v
```

The standalone native curve probe extracts only `305a00..305a24`, nine verified register-only
instructions, and appends a return. The resulting 40-byte function takes and
returns one double; it has no memory, calls or external references. The existing
executable-mapping helper handles permissions and instruction-cache invalidation.
The test runs this fixture in a subprocess and compares all bits at ten boundaries
plus 1,024 seeded random inputs. Other tests reject changed controls, literal,
resource aliasing, missing packets, source/result instructions, the native addition
and unknown firmware. Detailed vendor-derived output remains ignored under `local/`.

Qwen's bounded FDRV review hit its 180.2-second deadline and returned no requested
review artifacts. Its exploratory tool output was not accepted as evidence or code.
The equations, aliases and execution checks above were derived and verified locally.

The exact profile has 126 logical bytes, eleven packets and 128 stored bytes.
Append two zero padding bytes before reversing storage words; pass `--length 126`
when decoding. Never insert this storage padding between composed fragments.
Additional tests check every packet state and old-value store, independent asymmetric
inputs, signed zero, native cutpoints, all five stock bodies, mutated literals and
controls, rejected domains/aliases, nonzero padding and output preservation.

A new Qwen read-only attempt reached its 60.2-second limit without the requested
review files. A reduced no-tool review returned in 6.3 seconds, but miscopied the
right-channel inputs and made arithmetic errors. Its conclusions and exploratory
scripts were rejected. The packet model, native checks and tests above were
implemented and verified independently.

At the extended 12,000-frame checkpoint, all 48,000 conditional cubic results
match, with 47,985 distinct captured source values. The independent first-filter
check matches another 96,000 values in the same fixture.


## Stereo half-sample interpolation and clipping

2026-11-11. `tools/fdrv_clip_study.py` now admits an exact **80-byte, six-packet**
`clipped_half_pair` profile. It supplies a 14-byte authored preload, retains the
60 stock bytes at FDRV `33c..378`, and appends a six-byte authored store for the
last direct-right result. The original store is coissued in the following cubic
packet at `378`; the checker binds its actual field at `382` rather than silently
assuming the earlier slice already writes that result.

For current samples L/R and previous samples pL/pR, the checked finite policy is:

```text
averageL = fma(L, 0.5, pL * 0.5)
averageR = fma(R, 0.5, pR * 0.5)
outputs  = [clip(averageL), clip(L), clip(averageR), clip(R)]
clip(x)  = -1 if x < -1 else min(x, 1)
```

Averaging happens **before clipping**, and the current samples are stored
**unclipped** for history. With L=2, pL=-.5, the averaged output is .75; averaging
the already-clipped inputs would incorrectly give .25. Signed zero follows the
native compare/select behavior. NaN, infinity, booleans and missing data are
rejected; finite large inputs are accepted without an overflowing add-before-half.

`examples/clipped-half-pair.json` assigns four sources as
`[currentL,currentR,previousL,previousR]`. Its six targets are
`[saveL,saveR,averageL,directL,averageR,directR]`. All ten indices must be distinct,
below `800` hex, with previousL=saveL+1 and previousR=saveR+1. That adjacency
preserves the checked native-ring history relation; the executor itself neither
allocates a ring nor advances the origin. No coefficients or implicit port seeds
are needed. The authored current inputs use synthetic data cells 100/101 hex,
not a claim that these are available resources in an occupied stock owner.

| Exact controls/extensions | Role in this complete profile |
|---|---|
| `2812 / 2500` | I2 = fma(A,.5,I2*.5) |
| `6912 / 6500` | I6 = fma(B,.5,I6*.5) |
| `8ed8 / aeda / cedc / eede` | Clamp incoming I0/I2/I4/I6 respectively |
| `afe0 / efe0` transfers | Store incoming I2/I6 to checked data cells |

All fixed extension/pool words remain protected. The half coefficients are
established by the actual native arithmetic; decoding an isolated pool halfword
is not a general interpretation of these long forms. No arbitrary limiter word,
header variant, different literal or standalone operation is admitted. General
miscellaneous-header grammar remains opaque. The inverse decoder distinguishes
this six-packet 80-byte profile from the existing eight-packet 80-byte dry/wet
scratch profile by exact structure and reassembly.

Native cutpoints `305930..3059ec` bind both history reads, both raw stores and
all four clipped stores to their constructor records and DSP fields. The checker
rejects later overwrites before using post-callback snapshots. The four clipped
cells feed the already-admitted cubic quad in its native order. The earlier
resampling, drive/gain producers and the remaining effect are still outside this
new profile, so a cutpoint comparison is conditional rather than a full independent
FDRV implementation.

Two register-only native probes test the arithmetic independently: a 24-byte
clip extract and a 40-byte half/clip extract. The latter appends an authored,
decoded FMOV solely to place the result in the native return register, then RET.
The original kernels have no memory, calls or external references. Tests run
these bounded extracts in a subprocess over 1,032 input pairs, including signed
zero, subnormals, maximum finite values, saturation and asymmetric random inputs.
All 2,064 native scalar results match. Separate packet tests check every port
snapshot and old-value store, strict resource/schema/literal boundaries, and the
other 80-byte profile. All five Fantom stock 60-byte bodies and the outside history
and direct-right fields match their recorded relative assignments.

A 12,000-frame full-native-callback run matches 48,000 clipped results and 24,000
raw history-store values using captured current/history cutpoints. This adds
72,000 conditional stored-value checks, separate from the independently modeled
first filter's 96,000 values. It does not establish an independent whole-FDRV
model, physical BMC numeric behavior or sample timing.

```sh
python3.13 tools/fdrv_clip_study.py --execute-native --native-window-frames 12000
python3.13 tools/bmc_subset.py assemble examples/clipped-half-pair.json local/clipped-half.bin --stored
python3.13 -m unittest discover -s tests -p 'test_clipped_half_pair.py' -v
```

This profile is already word aligned, so logical and stored lengths are both 80.
The original example, tools and tests require no firmware patch or live device.
The emitter/interpreter alone need no vendor artifact; the provenance and native
checks require the pinned local corpus and native probes require macOS ARM64.
Qwen's 9.5-second test draft had correct asymmetric arithmetic, but omitted input
values and assumed caller-dictionary mutation. Its code was rejected; actual
API, signed-zero and native execution tests were implemented and run locally.

## Connected resampling and drive milestone (2026-11-11)

The input-to-shaping milestone is complete: an independent packet model now runs
input → prefilter → four stereo filter sections and their recombinations →
three-tap resampling/drive → half-sample clipping → four cubic curves. The eight
fragments take **86/194/226/194/202/122/80/126 bytes**, or **1,230 logical bytes,
1,232 stored bytes and 77 packets**. The model receives only initial ring canaries,
external samples, declared coefficients/constants and its own packet writes.
No captured native intermediate feeds this chain. Earlier conditional clip/cubic
window tests remain separate evidence.

The new `resample_drive_pair` is 122 bytes: ten authored input-load bytes, 102
exact stock bytes at `2d6..33c`, and ten authored output-store bytes. Its seven
sources are raw L, L-history 1/2, raw R, R-history 1/2 and the coissued previous-left
clip prefetch. Six channel/history cells are distinct, each channel's three cells
are consecutive, and the prefetch/output cells are distinct from them. Three
stereo-shared tap constants must be exactly representable by the explicit 24-bit
literal encoder; booleans, nonfinite values, inexact numbers and negative zero
are rejected. Two fixed drive literal variants are admitted, with exact duplicate
fields and all controls/extensions protected by inverse reassembly.

For each channel, using incoming raw x and history cells h1/h2:

```text
z = fma(h2, c, fma(h1, b, x*a))
driven = (z * fixed_drive_scale) * float32(live C0)
```

The raw x is stored at 0/3 before scaling. The mixed z is stored at 1/4 before
drive; the final driven values go to authored bridge 62/63 for the existing clip
profile. All data addresses here are hexadecimal. Under the fixture's origin
increment of one, next frame's h1 reads the preceding raw x, while h2 reads the
preceding mixed z. This is not a proof of physical sample cadence or a general
FIR interpretation. Stock defaults a/b/c = 1/0/0 hide both history terms.

| Packet context | Controls | Functional update in this exact profile |
|---|---|---|
| `b84e`, short | `1428 / 552b` | I1/I5 = incoming A/B × literal a; stores retain raw A/B |
| `470c`, long, extensions `0001/0005` | `1428 / 552b` | I1/I5 = fma(incoming A/B, literal b, incoming I1/I5) |
| `1008`, long, extensions `0001/0005` | `0424 / 4527` | A/B = fma(incoming A/B, literal c, incoming I1/I5) |
| `b80c`, short | `0426 / 4529` | A/B × fixed scale; stores retain pre-drive z and load live C0 |
| `2e05`, short | `0403 / 4503` | A/B × incoming C0; next-packet prefetch cannot affect the gain |

The same base word can have different short/long roles according to its packet
family. These observations do not admit any of these words globally. The actual
native arithmetic, nine data access paths, live C0 load, constructor-literal
records and output lifetimes are checked by `tools/fdrv_resample_study.py`.
The right channel reuses left-channel constructor literal records; paired wire
fields are explicit aliases, not independently established native records.

### Fantom and ZENOLOGY differ at the fixed drive literal

All five pinned Fantom FDRV placements contain duplicated **`100000`** literals
at `32c/32f`, decoding exactly to **0.0625**. ZENOLOGY instead has duplicated
**`0656d2`**, decoding to **0.024762272834777832**. Its constructor double is
**`0x1.95b489f0954cbp-6`**, about **0.02476228209191759**. The difference is below
one encoded-literal quantum, but is enough to break a bitwise native comparison.

The interpreter therefore follows an explicit native-reference policy: `0656d2`
uses the checked constructor double; `100000` uses exactly 0.0625. This is not
evidence that BMC silicon uses the ZENOLOGY double or IEEE binary64 at all. The
Fantom byte test selects its actual literal variant and matches the complete
102-byte body in all five placements; substituting only addresses/slots was
correctly rejected when the different scale was first encountered.

### Independent native comparisons

The owned native fixture executes the original complete callback, while comparing
only packet-covered data cutpoints through the last cubic store at `305af0`.
Later writes to those cutpoints are rejected. Native final audio output is not
compared, and executing its callback does not make the packet model complete FDRV.
For the nondegenerate fixture, constructor slots +48/+58/+68 receive exactly
representable taps **0.5/0.25/-0.125**, live C0 is **8192**, and the fixed drive
double is explicitly set to the selected variant. These are declared local fixture
substitutions, not observed Roland parameter-setter behavior or hardware execution.

Each 12,000-frame run matches **456,000 values** through five wraps, ending at
origin 1760: 26 earlier filter-bank memory values plus 12 resampling/clip/cubic
memory values per frame. The two drive variants therefore supply **912,000
comparisons across two runs**. ZENOLOGY-scale clipping inputs include 47,909
distinct values and 10 exact boundary results; the Fantom-scale run includes
39,151 distinct values and 8,824 boundary results. Both nonsaturated curves and
clipped endpoints are exercised. Three separate 2,056-frame cases cross wrap with
cursors 1/2: stock taps, nonzero taps, and nonzero taps with the Fantom scale.

All **458 tests pass** (69.342 seconds). Pure tests check asymmetric intermediate
ports, stores before gain, next-packet coefficient timing, both scale policies,
binary32 gain, signed zeros and seeded random references. Exact-template tests
reject changed controls, literal duplicates/tags, partial bodies and bad resources.
Native mutation tests reject arithmetic changes, even sub-quantum constructor
scale changes, and later cutpoint overwrites. Qwen supplied eight invalid-input
cases; each fails assembly, but its cross-channel suggestion also breaks adjacency
and aliases an output. A true channel-alias case was added independently. The
seventh prefetch source was added during tracing after Qwen received its baseline.

```sh
python3.13 tools/fdrv_resample_study.py --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_resample.py' -v
python3.13 tools/bmc_subset.py assemble examples/resample-drive-fantom.json local/resample.bin --stored
```

Original JSON assignments are `examples/resample-drive-zenology.json` and
`examples/resample-drive-fantom.json`. Default-tap combined logical hashes:

- ZENOLOGY scale: `457a7ceca95660a4cba18eadb5de872f0603102f3436be7deb46cea5efaaaa26`.
- Fantom scale: `6a3aad1bfe9d00f180f8b07afd1b320df9bb3b861fd804ae96d439c9352601d1`.

Concatenate logical fragments before padding/word reversal. The authored bridge
cells 60/61 and 62/63 require separate allocation proof before on-device use.
Packet execution needs no vendor artifacts; corpus/native checks need the pinned
local inputs, and native execution requires macOS ARM64/Python 3.13+.

Full FDRV still has **23 downstream packets, 416 stock bytes at `3ec..58c`**, to
map and integrate. The first next window mixes shaped samples/history before
later feedback/filter/output stages. State initialization, parameter-update
behavior, hardware numeric/timing calibration, entry/return, allocation and safe
loading remain separate work. Broader research pauses at this saved checkpoint;
no instrument was accessed.

## Post-cubic history mix milestone (2026-11-11)

The independent input chain now reaches the first post-cubic history mix and gain:
**1,340 logical/stored bytes, nine fragments and 84 packets**. Its new
`post_cubic_mix_pair` profile is 110 bytes: ten authored preload bytes, the exact
90 stock bytes at `3ec..446`, and ten explicit output-store bytes. Concatenate
logical fragments first; this complete body needs no final padding.

For each channel, let A be the current averaged/clipped cubic result, D the
current direct/clipped cubic result, and H the previous direct result:

```text
mixed = fma(H, .25, fma(D, .25, A*.5))
output = (mixed * float32(C1)) * fixed_post_scale
```

Sources are 12/18/19 for left and 13/1a/1b for right (hexadecimal data addresses).
The consecutive direct/history relation is checked. Under the fixture's origin
increment of one, the history read recovers the preceding direct cubic store.
Raw mixed values go to 1c/1d **before** C1 multiplication. Final values go to 6/a.
These final stores correspond to native cutpoints from the following stock DSP
packet, whose other arithmetic/prefetches remain outside this new profile. No
additional synthetic bridge cells are required. Existing 60..63 bridge allocation
still needs hardware proof.

| Exact context | Controls | Functional result |
|---|---|---|
| short `5f0a` | `04a4 / 45a7` | main A/B = incoming I2/I6 × .5; coissued loads select current direct values |
| long `470c`, extensions `0000/0004` | `0468 / 456b` | main A/B = fma(incoming I1/I5, .25, incoming A/B); loads select prior direct history |
| long `220a`, extensions `0000/0004` | `2466 / 6569` | I2/I6 = fma(incoming I1/I5, .25, incoming A/B); C1 load is for the next packet |
| short `5f07` | `2483 / 6583` | I2/I6 × incoming I3; coissued stores retain the raw mixed values |
| short `1506` | `24a0 / 65a3` | I2/I6 × fixed post scale |

All admission remains contextual: exact headers, controls, extensions, duplicate
literals, tags and alias relations are protected by inverse reassembly. There is
no general short/long decoder or scheduling claim.

The scale difference found before clipping has a matching post-scale difference.
All five Fantom bodies use duplicated **`500000`** literals, exactly **16.0**.
ZENOLOGY uses duplicated **`628624`**, decoding to **40.3837890625**, while its
constructor double is **`0x1.43126e978d4fep+5`** (40.384). The emulator uses that
explicit native-reference double for the ZENOLOGY variant and 16.0 for Fantom.
This does not establish literal arithmetic or precision on BMC silicon. All five
Fantom 90-byte bodies match with their actual scale/data/coefficient substitutions.

`tools/fdrv_post_cubic_study.py` checks the data paths, arithmetic, live gain,
constructor constants and register preservation through the final stores at
305bd8/305c00. Later overwrites of the four compared cells fail. Both 12,000-frame
scale-pair runs match **504,000 values each** through five wraps, ending at origin
1760: the earlier 38 memory comparisons plus raw mix 1c/1d and final stores 6/a
per frame. C1 is nonzero binary32 0.7313, rather than the earlier fixture's zero.
The complete native callback supplies the oracle; packet coverage and final audio
output remain incomplete. No captured native intermediate feeds the packet model.
Two 2,056-frame subprocess cases cross wrap with cursors 2/1. Pure scalar and
trace tests cover asymmetric terms, signed zeros, zero/nonzero gain, delayed
coefficient visibility, pre-gain stores and both post-scale precision policies.

```sh
python3.13 tools/fdrv_post_cubic_study.py --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_post_cubic.py' -v
python3.13 tools/bmc_subset.py assemble examples/post-cubic-mix-fantom.json local/post-mix.bin --stored
```

Original examples are `examples/post-cubic-mix-zenology.json` and
`examples/post-cubic-mix-fantom.json`. Default-tap composed logical SHA-256:

- ZENOLOGY pair: `f7651e5e2249b90343a720ecf550c0dc32cffb899e3d05a4c21430ead072284c`.
- Fantom pair: `25c5de6b032abab0295be9190871b3bfa9d525c257280399a8278d395be007ef`.

The next unmapped stock region starts at `446`: **18 packets, 326 bytes through
58c**. That boundary includes the stock packet whose final-input stores are
represented by our authored suffix; the full packet still needs mapping. Hardware
calibration, allocation, entry/return and safe loading remain open.
