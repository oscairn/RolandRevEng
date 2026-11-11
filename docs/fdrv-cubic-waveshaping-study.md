# FDRV cubic waveshaping, interpolation and clipping

The [parameter-control checkpoint](#setter-derived-live-updates-2026-11-11) now
traces live/literal descriptors and replays drive, wet, level and slope changes
through native coefficient envelopes. Complete audio/state comparisons remain
exact during interrupted ramps. Full EQ generation and hardware timing remain open.

The [complete arithmetic/output milestone](#complete-arithmetic-and-output-milestone-2026-11-11)
now matches final stereo audio and all persistent ring/cache state against native
callbacks through five wraps. Its 1,692-byte composed packet reference excludes
the unresolved DSP return/control contract and hardware loading.

The [cascaded history filters](#cascaded-history-filter-milestone-2026-11-11)
extend the chain to 1,504 logical/stored bytes and 92 packets. Both nondegenerate
scale-pair fixtures match 552,000 native values. The final state-variable filter
and output region remain outside packet execution.

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

## Cascaded history filter milestone (2026-11-11)

The next post-shaping window is now executed as `cascaded_history_pair`: **164
bytes, eight packets**, comprising ten authored input-load bytes and the exact
154 stock bytes at `446..4e0`. The complete ten-fragment chain is **1,504
logical/stored bytes and 92 packets**, without end padding. All five pinned
Fantom bodies match with their actual data substitutions.

For one channel, x is the current post-mix/gain input and h1/h2/h3 are incoming
history cells. The native operation order is:

```text
first  = fma(h2, c, fma(h1, b, x*a))
second = fma(h3, f, fma(h2, e, first*d))
```

The left source cells are 6/7/8/9, right a/b/c/d (all addresses hexadecimal).
Raw x is stored at 6/a, first at 7/b, and second at 8/c. Under the fixture's
origin increment, next frame's h1 reads the preceding x, h2 the preceding first,
and h3 the preceding second. In particular, h2 is reused by both equations; it
is not an independently invented third raw-input delay. Both cascaded sections
have feedback for the nonzero fixture, without claiming physical sample cadence.

| Exact context | Controls | Functional role |
|---|---|---|
| short `b84e` | `14a8 / 55ab` | I1/I5 = incoming I2/I6 × a; raw input stores retain incoming I2/I6 |
| long `470c`, extensions `0001/0005` | `1428 / 552b` | I1/I5 = fma(incoming A/B, the encoded coefficient, incoming I1/I5) |
| long `1008`, extensions `0001/0005` | `1424 / 5527` | Same accumulated form, selecting c at a different literal-pool offset |
| short `5f0a` | `1464 / 5567` | I1/I5 × d; coissued first-history stores retain the pre-multiply first result |
| transfer `7809` | `9fe0 / dfe2` plus loads | Store second at 8/c; preload next-filter T values |

The repeated long form selects b, e and f in distinct packets. Resource indices,
six stereo-duplicated 24-bit coefficients, adjacency, aliases, headers and
extension values are protected by exact inverse assembly. Coefficients must be
exactly representable; inexact values, nonfinite values, booleans and negative
zero are rejected. Only this complete profile is admitted, not arbitrary uses
of these control words or a general filter scheduler.

Stock a/b/c/d/e/f are **1/0/0/1/0/0**, which hide all history arithmetic. The owned
native fixture instead patches its six constructor doubles at +78/+88/+98/+a8/
+b8/+c8 to distinct exactly representable values **.5/.25/-.125/.75/-.1875/.0625**.
These are explicit test substitutions, not observed Roland parameter-setter
behavior. The earlier nonzero drive, post gain and both fixed scale pairs remain
in force. Native defaults are also tested separately.

Each 12,000-frame run matches **552,000 memory values** through five wraps, ending
at origin 1760: the preceding 42 comparisons plus four first/second result stores
per frame. Both scale-pair runs supply **1,104,000 comparisons total**. The oracle
executes the complete original callback; the packet model receives no captured
native intermediate. Whole-FDRV and final audio-output comparison remain open.
Three 2,056-frame subprocess cases cross wrap with cursors 1/2: stock cascade,
nonzero cascade, and nonzero cascade with the Fantom scale pair.

The profile retains following S/T prefetches at 41/44 and 42/45. Static native
data paths are checked, but these ports' evolving values are **not** compared
against the full callback: the following filter's state writes are not modeled
yet. Pure tests change all four prefetch values and show that the current first/
second stores stay identical. Only current outputs/history are claimed by this
milestone. No additional scratch bridge cells are allocated.

Pure tests check explicit asymmetric packet traces, incoming-port stores,
FMA order, signed zeros, random inputs and nonbinary representable coefficients.
Native mutation tests reject changed arithmetic, even sub-quantum changes to the
exact default constructor constants, and later state overwrites. Original JSON
assignments are `examples/cascaded-history-default.json` and
`examples/cascaded-history-nonzero.json`.

```sh
python3.13 tools/fdrv_cascade_study.py --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_cascade.py' -v
python3.13 tools/bmc_subset.py assemble examples/cascaded-history-nonzero.json local/cascade.bin --stored
```

Default-coefficient composed logical SHA-256:

- ZENOLOGY scale pair: `1a1bc3fa5fd188a4729bba7f3cf189409e5521c9ff5b413050c33af2d097c623`.
- Fantom scale pair: `38cefe2683622577e9784f650d33430f367fead8bf07f19dd4447fb81954469e`.

Next is `4e0..58c`: **11 stock packets, 172 bytes**, containing the final
state-variable/auxiliary section and output tail. Hardware precision, allocation,
entry/return and safe loading remain unverified. No instrument was accessed.


## Complete arithmetic and output milestone (2026-11-11)

The remaining arithmetic now runs as `fdrv_output_pair`: **188 bytes, twelve
packets**, including 28 authored preload bytes, 154 exact stock bytes at
`4e0..57a`, and a six-byte authored final multiply. All five Fantom placements
match the stock body with their actual data/live-coefficient relocations.
The eleven-fragment chain is **1,692 logical/stored bytes and 104 packets**.

The final filter uses incoming y at 8/c, S at 41/44 and T at 42/45. With five
fixed literal coefficients a/b/c/d/e, the checked native operation order is:

```text
nextT       = fma(S, a, S) + T
high        = fma(S, b, -nextT) + y
preliminary = fma(y, d, high*c)
nextS       = fma(high, a, high) + S
filtered    = fma(nextS + S, e, preliminary)
output      = fma(dry, float32(C2), filtered*float32(C3)) * float32(C4)
```

Store nextT at 41/44 and nextS at 40/43. Under the existing fixture's origin
increment, these become next frame's T/S inputs. Dry values come from 0/3, whose
producer-side native records point at `2e6/2ea`; final DSP operands at `56a/56e`
name the same cells. Earlier cascade S/T prefetches are now covered through the
complete state comparison.

The exact `420a` packet is significant: controls `1464/5567` fuse y*d with
incoming I2/I6 (high*c) while auxiliary restores replace those ports for the
following packet. Under the earlier cascade's `5f0a`, the same controls perform
plain products. Treating the control word alone as a universal multiply would
produce the wrong FMA order. Other admitted contexts cover literal accumulation,
pre-add state stores, live wet/dry/master gains and final main-port outputs.

Stock a/b/c/d/e are **0/0/0/1/0**. The owned native fixture patches constructor
doubles +e8/+108/+f8/+118/+d8 to **.125/-.25/.5/.75/-.1875**. Earlier resampling
and cascade coefficients remain nonzero. Live C2/C3/C4 use binary32 versions of
.4137/.7313/.8279. These substitutions expose hidden arithmetic; they are not
claims about Roland's parameter setters. Pure tests also exercise zero wet,
zero dry, zero master, asymmetric/random inputs, signed zeros and stock defaults.

`tools/fdrv_output_study.py:execute_frame()` is a packet-only, nonmutating frame
runner. It needs assembled supported fragments, an explicit 2,048-cell ring,
origin, live coefficients, stereo samples and two three-slot/cursor auxiliary
banks. It returns new ring/cache state and stereo audio. Fragment resources and
order must match the checked chain. The caller advances origin using the
existing fixture convention; physical sample cadence is still unverified.

All four authored bridge cells **60..63** are frame-local software temporaries.
They are no longer written into the persistent ring in this complete reference.
This matters because a rotating ring containing synthetic bridge histories would
fail a full-state comparison even when selected stock cutpoints matched. Cache
push/pop state is reconstructed from the packet controls and interpreter traces,
using only the model's own values. No captured native intermediate seeds it.

Each 12,000-frame scale-pair run matches, bit for bit, **two final audio values,
all 2,048 ring cells, six auxiliary slots and two cursors every frame**. That is
24,696,000 scalar comparisons per variant, ending at origin 1760 through five
wraps. One variant uses ZENOLOGY constructor precision; the other patches the
owned callback to the Fantom fixed drive/post scale pair. Three 2,056-frame tests
cross wrap with cursor pairs 0/1, 1/2 and 2/0, covering stock and nonzero final
filter coefficients. Both original JSON examples roundtrip as 188 stored bytes.

This completes the recovered **arithmetic/output reference**, not a DSP control
emulator. Stock `57a` includes `00f8` alongside the final multiplies; our authored
packet retains only the arithmetic. Stock `582` transfers main ports to
`2018/2019`; the offline runner returns their final stereo values to its caller.
It does not invent return-PC storage, pipeline drain or external IO timing.
The source callback's two output stores are independently checked and executed
in owned memory. Hardware numeric precision, allocation, entry/return and safe
loading remain separate requirements. No instrument was accessed.

```sh
python3.13 tools/fdrv_output_study.py --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_output.py' -v
python3.13 tools/bmc_subset.py assemble examples/fdrv-output-nonzero.json local/fdrv-output.bin --stored
```

Default-coefficient composed logical SHA-256:

- ZENOLOGY scale pair: `d9e40b0e93ca42f8d8326f53b473bcd1081d74c951209d91589e2bb0827a9e3f`.
- Fantom scale pair: `29ea7bfcccab4836d8f2663ee0f5bc3c3c2c5ad9a35c812c839771d6c59cbd62`.


## Setter-derived live updates (2026-11-11)

`tools/fdrv_parameter_study.py` replaces ad hoc changes to four live-control
families with source-checked setter target calculations and envelope trajectories.
This is a bounded desktop control-path reference. It maps the other filter
coefficient groups statically; it does not yet implement every EQ generator or
UI parameter conversion.

### Live and literal ownership

| Native setter/piece | Local live slots | Checked path |
|---|---|---|
| SetDrive(db0, db1) | C0, C1 | dB2Gain, cubic normalization, manager slot 160 |
| SetDriveWetRatio(ratio, db) | C2 dry, C3 wet | clamp ratio, dB2Gain, manager slot 160 |
| SetLevel(integer) | C4 | clamp 0..127, pinned 128-double table, manager slot 160 |
| SetFilter(index 2, ...) | C5, C6, C7 | EqFaCal stack results, manager slot 160 |
| SetFilterSlope(index 0/1, slope) | C8, C9 | zero/nonzero selection, manager slot 160 |
| First state-filter piece | C10..C14 | descriptor order10,11,12,14,13 |
| Second state-filter piece | C15..C19 | descriptor order15,16,17,19,18 |

The direct live calls pass **EnvTC selector 10 and wait=false**. They are
with/without-envelope-capable dispatches; replay explicitly chooses the
with-envelope branch. The runtime dispatch choice is not inferred from the name.
Native descriptors are checked as kind6, with the expected local slot fields.

Fourteen literal groups map to the constructor-double representatives used by
the packet arithmetic: three resampling taps, six cascade coefficients and five
final-filter coefficients. Native direct literal setters use manager slot c8.
The three taps come from SetPreFilter index 0; SetPostFilter indices 0/1 write the
three coefficients of each cascaded section. Its index 2 delegates to the final
EQ piece. The final filter's a descriptor at `9e3598` declares **four** width3
records: `4ea,4ed,536,539`, proving the repeated a fields belong to one declared
write. The other groups each declare two width3 records. The native manager
updates one representative double; firmware's previously checked writer walks
the declared count. This does not establish atomic application or silicon rounding.

For the replayed setters, let g0=10^(db0/20), g1=10^(db1/20), and
v=min(g0*g1,1). SetDrive sends C0=g0 and C1=g1/(3v-3v²+v³), evaluated in the
actual multiplication/FMA order. SetDriveWetRatio sends C2=1-clamp(ratio,0,1)
and C3=clamp(ratio,0,1)*10^(db/20). The Mach-O indirect-symbol table independently
identifies dB2Gain's tail target `6d8c98` as `_pow`. Original owned native math
slices check the normalization and wet arithmetic; host libm supplies pow inputs.
Level's native table at `818d20` has SHA-256
`a4218b6632614d7d49d228d1b6e7db535bd3dadcb3b016fa97799fee6c87a9e4`.

### Native envelope behavior and dynamic comparison

The reference preserves binary32 subtraction, multiplication, accumulation and
stored target/current values. Selector 10 selects nominal12 ms in the pinned
16-entry table. Mode2 increment preparation computes float32(target-current),
multiplies by 1000 in float32, divides in binary64 by time_ms*44100, then converts
the increment to float32. The original VProcSync code clamps at the endpoint and
clears its active control fields. When a float32 addition stalls despite a
nonzero increment, it advances one representable float toward the target.
A generic double-precision linear ramp would miss that behavior.

Owned native increment/VProcSync buffers and an independent scalar model match
all selectors, rising/falling ramps, signed-zero cases and one-ULP stall escape.
The fixture keeps wait/event processing disabled and the synchronization-owner
flag zero; it does not register native scheduler callbacks or touch hardware.
One VProcSync update occurs before each fixture audio frame by explicit policy.
That convention and the native 44100 constant do not calibrate Fantom cadence.

The original event example contains **13** drive/wet/level/slope changes, with
multiple events at frame 0, updates near 2048-cell wraps and retargeting before a
ramp finishes. The selected controls update 7 distinct live slots. Both
12,000-frame fixed scale-pair variants match **960,000 envelope fields** plus
**24,696,000 final audio/ring/cache values each**, ending at origin 1760 through
five wraps. The model receives no native current coefficient, audio or ring
intermediate. An owned adapter copies native envelope current values into the
native callback's coefficient records; the model advances its own envelopes.
No history reset is inserted into this fixture.

### Fantom correspondence and remaining boundaries

The actual Fantom RTTI-linked FDRV callbacks independently confirm local
C0/C1 drive, C2/C3 wet, C4 level and C8/C9 slope descriptors, dispatched through
manager slot b0. Drive loads occur at `6104a0d2/6104a0e8`; wet at
`6104a21c/6104a232`; level at `6104a2e8`; slope dispatch is `61049fb4`.
The level table at `610bc584` equals the native table after binary32 conversion.

Fantom's setter target arithmetic uses binary32 VFP instructions, including
VMUL/VMLS/VMLA/VDIV in drive normalization; the desktop uses binary64 and FMA.
Their computed targets are **not assumed bit-identical**. The Fantom-scale replay
still executes the desktop callback with fixed scale substitutions. It is not
execution of ARM32 setters or a hardware envelope measurement.

Still open: EqFaCal/EqVgCal coefficient generation and interpolation stability,
UI index/unit conversions, actual with/without-envelope selection and scheduler
cadence, SetAlg/history initialization, grouped literal timing, physical
precision and safe loading. The selected setter mapping and dynamic arithmetic
check do not close those requirements.

```sh
python3.13 tools/fdrv_parameter_study.py --core1 local/b0c1a.bin
python3.13 tools/fdrv_parameter_study.py --execute-native --events examples/fdrv-parameter-events.json --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_parameters.py' -v
```

The event example is original research input, not a Roland parameter dump. Detailed static/dynamic reports remain local.
