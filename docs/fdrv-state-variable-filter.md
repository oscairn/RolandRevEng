# A byte-executed stereo state-variable filter

The [second-filter extension](#second-filter-and-recombination-milestone-2026-11-11)
now forms a 496-byte packet-executed input/two-filter/recombination chain, checked
against an explicitly bounded native prefix. The earlier 270-byte stage remains
covered by its original full-callback comparison.

The [original filtered voice](original-bmc-filtered-voice.md) now composes this
component with the packet-executed oscillator/gain body and verifies shared
state, ten seeds, eleven coefficients and all five recorded owner layouts.

2026-11-10. Native ZENOLOGY arm64 SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Evidence is static Python/Capstone analysis and execution of the pinned native
callback in owned fixture memory. No BMC hardware or updater was accessed.

**Result:** the first stereo FDRV filter block now has an independent state/output
reference, a strict 184-byte assembler/inverse-decoder profile and packet execution.
All 146 arithmetic-body bytes match the native-paired program and all five Fantom
placements. The remaining 38 bytes are authored input/coefficient loads. This is
a reusable filter component for an original engine, not complete FDRV emulation,
a standalone executable wrapper or a general instruction decoder.

## Native recurrence and the subtraction sign

For each channel, y is the input, s/t are two incoming states, and a/b/c/d/e are
five binary32 live coefficients. The recovered operation order is:

```text
Tnew = fma(s, a, s) + t
X = fma(s, b, -Tnew) + y
preliminary = fma(y, c, X * e)
Snew = fma(X, a, X) + s
output = fma(Snew + s, d, preliminary)
```

The nonfused additions and multiplication stay separate. Signals and states are
binary64 in the native reference; only coefficient records are rounded to
binary32. Both the helper and interpreter reject nonfinite intermediates.

The native `FNMSUB` at `305250` computes **s*b − Tnew** in this dataflow.
Direct native probing and the complete callback comparison confirm the sign.
Rewriting it as Tnew−s*b gives the wrong filter. Signed-zero behavior also
prevents casually replacing an instruction with a post-negated expression.

The checker verifies source/state/output records, register identities, coefficient
pointer provenance and intervening register preservation. The
[auxiliary study](auxiliary-save-restore-and-add-mac.md) supplies the matched
save/restore and final add/MAC cutpoints. Native producer anchors include:

| Operation | Left | Right |
|---|---|---|
| Tnew fused term / addition | `305214/305218` | `3052f4/3052f8` |
| X subtraction / input addition | `305250/305254` | `305328/30532c` |
| X*e | `305264` | `305338` |
| Preliminary / Snew fused term / addition | `30528c/305290/305294` | `30535c/305360/305364` |
| Extra s addition / output MAC | `3052bc/3052c0` | `305388/30539c` |

Both channels use coefficient slots `a..e` (hexadecimal), corresponding to
decimal `10..14`. No physical coefficient-port distinction is inferred where
the observed ports carry the same record.

## State-variable interpretation and ideal stability

Define g=1+a and q=−b. Ignoring finite arithmetic rounding, the state update is:

```text
Tnew = t + g*s
X = y - q*s - Tnew
Snew = s + g*X
```

This is a state-variable recurrence with X as a highpass term, Tnew as an
integrated term and Snew as the other state. The state matrix has trace
`2 − g*q − g*g` and determinant `1 − g*q`. The strict ideal Jury conditions
reduce to `g*q > 0` and `g*g + 2*g*q < 4`. Positive g/q designs are a useful
subset; negative g and negative q can also satisfy the mathematical criterion.
The helper compares these conditions with independently calculated poles in tests.
This is an ideal linear-model check, not a hardware or finite-precision guarantee.

The output coefficients mix input, X and Snew+s. For example, c=0/e=1/d=0
selects X; c=e=0/d=.5 selects the average of the old and new s states. In exact
arithmetic, c=1, d=−q/2 and e=q*g/2−1 select Tnew. Serializing d/e to binary32
can perturb that last identity. No cutoff, resonance or sample-rate calibration
on a BMC is claimed.

## State addresses and the conditional ring convention

The native first block reads s/t from `29/2a` and `2c/2d`, writes Tnew at
`29/2c`, and Snew at `28/2b`. The native scalar index convention is
`(address + wrapper_base - origin) & 7ff`. Advancing origin by one makes the
next reads recover the Snew/Tnew pair just written. This is a checked software
convention, not an observed BMC frame cadence.

The profile's ten sources are ordered:

```text
[yL, tL, sL, yR, tR, sR, next_sL, next_sR, next_tL, next_tR]
```

The four targets must be `[sL, sR, sL-1, sR-1]`, with tL=sL+1 and tR=sR+1.
All ten sources plus the two lower state targets must be distinct and in
`0..7ff`; all five coefficient slots must be distinct and in `0..fff`.
These explicit aliases retain the proved write/read dependency. The extra next
sources feed final port loads and do not change this block's current output.

The ten packet offsets are decimal `0/14/28/38/56/86/100/118/128/158`. Stores
capture incoming values and coissued loads feed the following packet. In the
exact window, auxiliary saves at offset 56 preserve old ports 2/6; restores at
offset 100 provide those old states after their temporary products have fed the
preceding arithmetic. The trace records the live saved values and requires a
balanced pair at completion.

This model tracks one live save per port. It does not retain inactive physical
cache slots, arbitrary initial depths or overflow behavior. The native circular
banks can retain changed slot contents after restoring their cursors. Balanced
logical saves therefore do not establish that every physical DSP resource is
unchanged or available to another graph.

Fantom list `610e5a94` supplies the same body at program bases
`4020/8040/9040/a040/3020`. Their data bases are `100/320/3b6/44c/c0` and
coefficient bases `190/1f4/208/21c/e`. Typed substitutions reproduce every body
byte. These are occupied stock placements, not new resource allocations. Live
ownership, auxiliary-resource coordination, loader access, entry/return and
physical precision/timing remain unresolved.

## Reproduce and execution checks

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_filter_study.py --execute-native --frames 12000
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py assemble examples/state-variable-pair.json local/state-variable-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py disassemble local/state-variable-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_fdrv_filter_study.py' -v
```

The fixture runs the unmodified native callback `3050ec..305ea8`, 879 instructions,
after checking contiguous code, its final return and a call-free, position-independent
instruction whitelist. It supplies its own constructor image, twenty live
coefficient records, stereo input/output buffers, 2,048-double ring and owner.
The five filter coefficients are explicitly chosen fixture values that require
binary32 rounding, not recovered factory tuning. Other processing in the callback executes, but its full effect
output is not covered by this component comparison.

The tests compare both the byte interpreter and independent equations with native
prefix, state and first-filter output stores. Nine cursor pairs run 128 frames,
one pair runs 12,000 frames through five ring wraps, and two one-frame cases check
signed zeros and large/precise binary64 states. All 105,232 checked native values
and 78,924 byte-emulated filter values agree bit for bit. Cursor pairs return
unchanged and the long render ends at origin 1760. A nonzero indexed background
and distinct auxiliary canaries avoid relying on a cold-zero coincidence.

Qwen returned a small equation/stability draft in 70.4 seconds. Its equations were
retained after independent sign checking, but it incorrectly rounded y/s/t to
binary32 and rejected valid binary64 states. Review corrected that validation
with existing numeric helpers and expanded the requested positive-g/q stability
check to both valid sign orientations, with explicit precision and pole tests.
Native/firmware evidence, the emitter/interpreter and
execution fixtures were derived and verified locally. Generated vendor artifacts
remain under ignored `local/`; no binary is committed or installed.


## Completed input-to-first-filter stage (2026-11-11)

Tonight's bounded milestone is a **270-byte packet-executed stereo stage**:
86-byte `stereo_prefilter` followed by the existing 184-byte state-variable filter.
The signal path uses packet arithmetic throughout; host code supplies external
input samples, declared initial state and one native-model ring-origin step.

The prefilter computes each channel in the observed operation order:

```text
mixed = fma(old2, C7, fma(old1, C6, input * C5))
```

Live coefficients are read as binary32, while signals/state retain the native
binary64/FMA policy. Its first 76 bytes match the stock FDRV input packets exactly;
ten authored bytes store the two mixed results. `examples/stereo-prefilter.json`
names the checked input pair, three coefficient slots, six source cells and four
stores. Sources are `[Lold1,Lold2,Rold1,Rold2,nextSleft,nextSright]`; targets are
`[rawLeft,rawRight,mixedLeft,mixedRight]`. The last two sources are coissued
prefetches and do not affect the current outputs, but must be provided explicitly.

For each channel, old1=raw+1, old2=raw+2 and mixed is stored at old1. The two
channels and prefetches retain the exact distinctness restrictions. Advancing the
native ring origin makes the following invocation read the previous raw and mixed
values; this is not a general three-tap FIR contract. Raw stores use incoming
ports before coissued arithmetic/loads. Coefficient changes become available in
the next packet. All five Fantom input spans match after their actual data,
coefficient and IO assignments, and asymmetric vectors execute identically.

Constructor aliases are material: native mixed stores reuse the earlier source
representatives at relative 1e/24 rather than new records for the later store
operands at 5a/5c. The checker now verifies the real representatives and both stock
store words. Native load/store paths, six arithmetic instructions and three live
coefficient reads are independently anchored. Changed arithmetic, aliases,
resources, headers and extensions are rejected.

The combined checker uses a **separate persistent model ring** initialized from
the declared fixture state. Only packet writes update it; no native intermediate
sample is fed into its prefilter or filter. Parallel scalar/native checks remain
validation oracles. A 12,000-frame run matches all 120,000 compared raw/mixed/state/
output values against the native callback, crosses five origin wraps and ends at
origin 1760. A separate 2,056-frame regression uses auxiliary cursors 1/2 and crosses
a wrap. The original prefilter vectors produce left -1.875/right 5.625, with the raw
inputs 4/-5 retained separately. Binary32 rounding and every packet state are tested.

```sh
python3.13 tools/fdrv_filter_study.py --input-stage --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_stereo_prefilter.py' -v
python3.13 tools/bmc_subset.py assemble examples/stereo-prefilter.json local/prefilter.bin --stored
```

The prefilter alone is 86 logical/88 stored bytes. Concatenate logical fragments
before padding/conversion: the combined stage is 270 logical/272 stored bytes.
Its unrelocated logical hash is
`9912f101df3714156894a3b9bb7feb3c6225c468e33e3179fc68ebcd783637bb`.
Do not insert the prefilter's standalone padding before the filter fragment.

This completes the input-to-first-filter milestone, not a complete FDRV effect or
on-device engine. Outputs are functional A/B, with no entry/return wrapper or
hardware output routing. BMC precision, cadence, live loading and ownership remain
unverified. Qwen checked the asymmetric numbers; its loose state/rounding language
was corrected against the actual packet trace and native callback.


## Second filter and recombination milestone (2026-11-11)

The next bounded milestone is complete: input → prefilter → first stereo filter
→ second stereo filter → recombination executes through **496 logical bytes**.
The three profiles are 86-byte `stereo_prefilter`, 194-byte
`state_variable_pair_with_output`, and 216-byte `state_variable_recombine_pair`.
The composed body is word aligned; do not concatenate individually padded forms.
Its logical SHA-256 is
`2501fa7b8c39b306d190478fdd6ede532ddf2689ba967f6d02813e235b738dd9`.

The 194-byte form appends two main-port data stores to the existing 184-byte filter,
preserving its original state operations. Those stores supply the first result
at 24/25 for the next independently initialized fragment. The 216-byte profile
contains 38 authored preload bytes and the exact 178 stock bytes at FDRV f8..1aa.
That body includes input writebacks, the second filter, its complement products,
recombination and next-section prefetches. All five pinned Fantom bodies match
with their actual data/coefficient substitutions. Duplicate unchanged input stores
in the composed functional body are not a claim of stock cycle timing.

The second filter uses the same a/b/c/d/e slots 10..14, state pairs 2f/30 and 32/33,
and next-state stores at 2e/2f and 31/32. Its following g slot is 8. The exact new
arithmetic contexts are:

| Controls | Role in the complete 216-byte profile |
|---|---|
| `1bc1 / 5bc5` | I1/I5 = fma(-incoming I1/I5, incoming I7, incoming I1/I5) |
| `09c1 / 49c5` | A/B = fma(incoming A/B, incoming I7, incoming I1/I5) |

Thus the recombination is `fma(wet,g,fma(-dry,g,dry))`, with g read as binary32
and signal arithmetic binary64. **FMSUB supplies dry − dry×g**, unlike the
FNMSUB sign in the filter recurrence. The actual register-only native probe
returns 2.75 for dry 2/wet 5/g .25, 2 for g 0 and 5 for g 1. Signed-zero and random
cases are compared by bit pattern rather than replacing the FMAs with an
algebraically rearranged expression. The final coissued coefficient load selects
slot 15 for a later section and must not affect this packet's g multiplication.
All constants, resource relations, duplicate fields and tags remain protected;
none of these words is admitted outside complete recognized profiles.

The extended native oracle is explicitly a **prefix fixture**, not the complete
sample callback: original instructions 3050ec..30553c followed by the original
output-store/epilogue instructions 305e90..305ea8. Checks bind the prologue and
restores, verify that the output-pointer register x2 survives, and reject any
additional stack-pointer write. The existing callback whitelist and owned buffer
graph remain in force. The appended epilogue records the current recombined d1/d0
before the next filter begins. No firmware or plugin is loaded as a whole.

The separate persistent packet ring receives only declared initial state, external
test inputs and packet writes. In 12,000 frames, 120,000 earlier-stage values plus
72,000 second-state/recombined values match the native prefix: **192,000 total**,
five wraps, final origin 1760. A 2,056-frame subprocess with cursors 2/1 crosses wrap.
A separate native FMSUB/FMADD probe matches 1,029 boundary/random triples. Pure
reference tests independently check second-filter states, both final products,
old-port timing and the harmlessness of changing the coissued future coefficient.

```sh
python3.13 tools/fdrv_second_stage_study.py --execute-native --frames 12000
python3.13 -m unittest discover -s tests -p 'test_fdrv_second_stage.py' -v
```

Original JSON assignments are `examples/state-variable-with-output.json` and
`examples/state-variable-recombine-pair.json`. The emitter/interpreter can use
them without vendor artifacts; corpus proofs and native probes need the pinned
local inputs, with native execution restricted to macOS ARM64. Tests reject
altered arithmetic, output ABI, clobbered output pointers, resource/literal changes
and incompatible requests to check later clipping with this shortened fixture.

Qwen's 6.3-second recombination review made arithmetic/sign mistakes and was
rejected. The accepted signs and values come from actual native execution and
independent references. This milestone stops before the next filter section;
full FDRV, silicon precision, live loading and entry/return remain open. Broader
research pauses after saving this checkpoint, as requested.
