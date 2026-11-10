# Next complete-program emulator target

2026-11-10. **Select the primary LINEDRIVE program next**, with FETDRIVE as the
shared-prefix comparison and TS808 as a later alternative. This is an engineering
priority among five inspected native/DSP pairs, not a statement that any complete
stock effect can currently execute. No complete program was justified in this pass.

The strict interpreter executes a stereo input packet, exact dry/wet tails, with an optional checked
scratch round trip, and 82-byte allpass fragments in the offline reference model. Here an admitted region means the
specific class/offset context already independently compared with native dataflow
and reproduced by `bmc_subset.py`. Equal control words, a successful packet parse,
or a known header family do not admit other contexts. See the
[semantic ledger](opcode-semantics-ledger.md) for those boundaries.

## Artifact and selection boundary

The existing prepared ZENOLOGY arm64 image is SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
`emulator_target_study.py` cross-checks all 75 paired render-list descriptors and
their segment records against this image, then reads **five** primary streams and
their exported native sample callbacks. Generated pairings retain the earlier
constructor/export-reader limitations; descriptor self-consistency is not proof of
Fantom factory selection or deployment. No new download, plugin/vendor execution,
device action or firmware modification was performed. REA remains unavailable.

By largest logical segment length alone, the seven shortest paired render classes
are CHO (312), GATE (332), FETDRIVE (458), BPMLP (468), DJFXLP (470), VMCP (470)
and RING (498 bytes). These are **size observations**, not semantic rankings. The
last four were not expanded into new opcode studies. Every paired class has one
render list in this recorded metadata; no extra render list was silently discarded.

| Inspected primary | Logical bytes / source | Native sample callback | Exact strict-fragment contexts already proved |
|---|---|---|---|
| `SIM_CHO_CHO` | 312 / `7c5080` | `a9084..a9620` | None |
| `SIM_MFX_GATE` | 332 / `833318` | `313dd0..3140b8` | None |
| `SIM_MFX_FETDRIVE` | 458 / `8372f4` | `2f7de4..2f81c4` | Input `004..00e`; dry/wet plus scratch `16a..1ba` |
| `SIM_MFX_LINEDRIVE` | 578 / `7b47f4` | `2df874..2dfd94` | Input `004..00e`; allpass `13e..190`, `190..1e2`; dry/wet plus scratch `1e2..232` |
| `SIM_MFX_TS808` | 588 / `8403fc` | `2085f0..208ab0` | Additional bounded tap/feedback evidence, but neither strict template |

Ranges are half-open hexadecimal byte offsets. Sources and native addresses are
file/virtual offsets in the prepared image. CHO's program base is `b000`; the other
four primary bases are `4020`. CHO has one render segment; the MFX candidates have
two relocated segments each. Existing proofs here concern the primary bank, not
automatic admission of every relocated operand, parameter binding or parent route.
Native list header DSP values are not a physical Fantom destination map.

## Why LINEDRIVE comes first

LINEDRIVE's two allpass chains are complete *fragment* proofs: all twelve state
stores, their incoming-value ordering and the signed polynomial expressions were
checked independently. Its dry/wet tail has the same six-packet family as FETDRIVE.
Its native sample body has no branch or helper call, and every packet header has
an existing structural family interpretation. The remaining arithmetic, payload
roles and wrapper semantics are still unresolved; the header observation removes
one source of structural ambiguity without conferring execution semantics.

The complete remaining regions are `000..004`, `00e..13e` and `232..242`: **39 packets**.
All of each remaining packet, including its shared pool, stays unadmitted. The
local JSON lists each packet's start/end, header, base controls, structural family
or explicit layout failure, and pool byte range. No hole is skipped as zero, NOP,
an immediate or an address merely because its encoding resembles a familiar form.

| Remaining LINEDRIVE region / requirement | Concrete gap |
|---|---|
| Opening `000..004` | `ff71` is a stock mutable mute gate; its execution/skip/store consequences are unproved |
| Input mix/prefix `00e..13e` | Mixed long/short arithmetic, extensions, special controls and transfers are not fully decoded. Examples include `4822`, `2424/3467`, `2485`, `fe10`, `b9b2`, `ac99`, `aed2/1e10`, `aeda`, `0e8b`, `5424/643e`, `5464/647e`, `ceae`, `4086`, `0044/1044`; these names are inventory, not opcode assignments |
| Pool roles throughout that prefix | Literal width/reference selection, extension consumption, auxiliary store sources and interactions with special/condition state need exact contextual proofs |
| Suffix `232..242` | Co-issued output stores with `00f8` and trailing `ff70` must execute under a proved entry/return contract |
| History/factor inputs to the allpass chains | Caller must supply real prior state and the factors produced before `13e`; using zero or arbitrary external factors would create a different program |
| Cross-invocation memory | Ring base/current index, wrap, retained history and initialization must be modeled explicitly; the fixed fragment's stores do not supply an allocator or reset protocol |
| Parameter binding | Eight constructor default records and six live coefficient-pointer fields have different roles; literal patching, parameter-base offsets and live float reads cannot be collapsed into a single coefficient array without proof |
| Numeric policy | Prefix native fixed-point conversions, integer shifts and nonlinear selection cannot be replaced by unconstrained floating arithmetic; BMC precision, saturation and issue timing remain a separate silicon-validation gap |

The two unresolved suffix packets occupy 16 bytes in both LINEDRIVE and FETDRIVE.
The [scratch round trip](supported-code-generation.md#drywet-tail-with-scratch-transfers)
now accounts for the preceding 20 bytes. Seeing a native
return after output writes does not identify `00f8`'s saved PC, transfer latency or
the meaning of the following `ff70`. The six-byte stock placeholder
`00f8`/NOP is likewise not a justified complete trivial target: its implicit return
state remains unknown. The [condition/return study](condition-fields-and-implicit-return-study.md)
states that precise boundary.

## Alternatives and reasons to defer them

**Second: FETDRIVE.** Its smaller image and branch-free native body are useful for
checking shared mixing/shaping hypotheses. The strict dry/wet region leaves
`000..004`, `00e..16a` and `1ba..1ca` unadmitted: **48 packets**. Header `7308` is unresolved
at `88` and `11e`; the whole prefix also needs its nonlinear/quantization, filter,
special-state and auxiliary-transfer semantics. The two
[cross-destination allpass comparisons](operand-variants-and-macro-boundaries.md)
prove results relative to actual native cutpoint stores, but explicitly leave
`bedb` opaque. They must not be promoted to complete interpreter-ready families.
Wrapper, parameter and history requirements are shared with LINEDRIVE. Availability
of this implementation is not proof that Fantom's normal factory activates it.

**Third: TS808**, after the stricter LINE/FET gaps. Its straight-line native body
and contextual tap/feedback proofs offer useful later regression cases, but its
nonlinear blocks and four unresolved-layout packets (`4b09` and `8a0c`, each twice)
remain. The feedback proof cannot distinguish source port 3 from 7 where both hold
equal factors. That is an outstanding semantic ambiguity, not permission to select
either one arbitrarily. Neither existing strict template covers this complete image;
all 40 packets remain outside the interpreter admissions.

**The shortest counterexamples:** CHO has eight unresolved header forms and a
native callback with branches and two helper calls, plus modulation/history memory
requirements. GATE has three unresolved forms (`de4c`, `6508`, `bf07`) and a native
conditional branch, plus envelope/threshold/state semantics without a strict admitted
fragment. Their shorter files do not make them lower-risk complete targets. No
general chorus/gate implementation, missing helper or condition was substituted.

## Native harness requirements for the chosen target

LINEDRIVE's exported `Init()` at `2df6e0` allocates `5a8` bytes, passes its manager
context to constructor `2dfe04`, and saves the returned simulator-record pointer at
wrapper+`28`. `EndProc()` at `2df718` reads that pointer and takes the deallocation
path if nonnull. This concerns simulator records; it does not zero all DSP history.

The sample callback starts at `2df874`. It reads a pair of input pointers from x1,
loads their double samples at `2df888/2df88c`, and eventually writes doubles through
the x2 output-pointer pair at `2dfd84..2dfd8c`. The data-array path is
`wrapper → +8 → +18 → +10 → +18`, with current/base-index participation from that
context and `&7ff` before scaled double accesses. Live coefficient records use the
constructor-proved `48`-byte stride and float at record+`28`, converted to double.
Those offsets are hexadecimal and describe this native reference, not a BMC bus map.

A useful offline harness therefore needs explicit ring/history contents, ring
index/base, literal defaults/patches, live coefficient records and input/output
bindings. It cannot call only the new fragment interpreter and label the result
LINEDRIVE. The complete parent routing/task/return contract remains separate from
the native callback's two input/output sample bindings. Existing getter/default
record counts are symbol-map metadata, not a count of state cells to allocate.

## Smallest next comparison

Start with the **whole input-mix/store context**, DSP `004..038`, against native
`2df884..2df8d8`. The native window loads independent L/R samples, reads constructor
doubles at record-object+`58` and +`78`, forms mixed values and stores both through
the circular path. Recover exact field identity and def/use for both destination
stores, including any duplicated/aliased literal fields; equal defaults are not
enough. Perturb each independent input/coefficient symbol in the formal comparison
and reject swapped channels, shared-field assumptions and late-store variants.

This would admit another bounded fragment only after the mapping succeeds. It is
not yet an assignment of `4822` or any destination bit. Then tackle the remaining
quantized nonlinear prefix with integer conversion/shift boundaries and nonzero
history fixtures. In parallel, implicit call/return state is the smallest global
proof still preventing even the short stock placeholder from becoming a complete
callable program. Extra copies of the same packet sequence cannot supply that state.

## Prefix follow-up: two literal identities remain unresolved

A bounded follow-up checked the proposed `004..038` window, using the existing
`header_study.layout()`, independent `constructor_memory()` reconstruction and
`native_accesses()`/`check_bindings()` provenance checks. It establishes the native
result and two destination fields, but **does not admit a new DSP fragment**.

The four decoded width-3 literal fields are distinct byte ranges:

| Program field | Stored default | Native constructor-owned record / load |
|---|---:|---|
| `14` | 0 | record `+50`, double `+58`, read at `2df890` |
| `17` | 0 | No matching record among the eight reconstructed defaults |
| `24` | 1 | record `+70`, double `+78`, read at `2df89c` |
| `27` | 1 | No matching record among the eight reconstructed defaults |

Both zero fields occur in the `4822` packet; the two unit-valued fields occur in
the `2424/3467` packet. This follows their pool-reference syntax, not an arithmetic
assignment. Getter `2df728..2df824` compares a requested relative field with each
of the eight records and returns its double, or returns null. No additional alias
for `17` or `27` was identified in that getter. An external descriptor/write group
could still constrain the fields together; its absence is not proved here.

With independent input samples L/R, the native sequence at `2df888..2df8a4` reads
the doubles M=`object[58]`, S=`object[78]` and produces the formal expressions
`M*(L+R)+S*L` and `M*(L+R)+S*R`. FMUL/FMADD ordering is preserved in the source
anchors; the polynomial notation does not assert bit-exact fused/rounded behavior.
The two stores have independently checked field identities and circular-data
pointer/mask/scaled-double provenance:

| Program operand → native object field | Native store | Observed target |
|---|---|---|
| `32 → +8c` | `2df8c4` | data index 1 |
| `34 → +94` | `2df8d8` | data index 2 |

These checks connect the actual native stores to the packet's `afe0/bfe2` address
fields. They do not identify their complete DSP source-port state or prove which
incoming versus newly computed port value those stores capture. The same packet
also loads live coefficient C2 through `5fe4`; a result-only macro that discards
that outgoing port state would be incomplete.

Equal defaults cannot establish the missing two identities. For example, a tied
native expression uses one M and one S, whereas a hypothetical split expression
could use `M1*L+M2*R+S1*L` and `M1*L+M2*R+S2*R`. Both give `(1,2)` for L=1,
R=2 and stored defaults M1=M2=0, S1=S2=1. Setting only M2=1 distinguishes
`(3,4)` from tied `(1,2)`; setting only S2=2 distinguishes `(1,4)` from `(1,2)`.
These are checked algebraic counterexamples, **not predictions of mutated DSP
execution**. No program or parameter was changed or executed.

The smallest remaining prefix proof is therefore specific: recover the ownership,
fixed-constant rule or grouped-write relation for fields `17` and `27`, then prove
the full outgoing register/port state and store capture semantics. Merely equating
their defaults with fields `14` and `24` would conceal the unresolved relationship.
The checked diagnostic is retained in ignored `local/line-prefix-ownership.json`;
all three target-selection tests still pass, and the strict admissions are unchanged.

## Reproduce and review

```sh
python tools/emulator_target_study.py --out local/target-study.json
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests -p test_emulator_target_study.py -v
```

Use the existing prepared `zen_arm64`, `pairs.json` and `exports_dem.txt` with
Python 3.13.7/Capstone 5.0.7. The three tests check exact corpus contexts, whole-packet
partition/rejection and refusal to admit a new program merely containing familiar
template words. There is no ISA-completion percentage or base-word execution metric.
Detailed inventory/disassembly and the bounded Qwen draft stay ignored/local;
the final reviewed Qwen outcome is recorded in the handoff. The serialized,
no-tools Qwen pass correctly checked the half-open ranges and 36-byte suffixes.
Its proposed ranking was rejected: it called the 362-byte FET prefix smaller
than LINE's 318 bytes and inferred a complexity difference unsupported by the
supplied straight-line callbacks. Its suggestions that the epilogue might be an
output flush and that BMC scheduling is likely block-based/fixed-point supplied
no evidence. No opcode, timing or numeric claim was admitted from that draft.


## Input packet and bank comparison

Both LINE and FETDRIVE load left and right in the packet at `004`. Native
`2df884..2df890` and `2f7df4..2f7e00` independently load the two samples
through the input pointer pair. The primary and alternate banks use the
same load controls with different input slots. The packet is now admitted.

The four checked banks all store zero in both mono-mix literal fields and
one in both stereo literal fields. FETDRIVE co-issues a coefficient load
in its stereo arithmetic packet and moves the width-three stereo fields
to `28/2b`. In LINE they remain at `24/27`. The bank variation changes
the input addresses, and the class variation changes the packet layout.
The equal stored literals leave the tied-versus-split input-mix behavior
underdetermined. The `afe0/bfe2` store-source identities remain open.

## JUPITER-X carries an asymmetric instance of `4822 / 1940`

`tools/line_mix_variation.py` searches packet boundaries for the exact `0806` header,
`4822` control and `1940` extension. It decodes each literal by reference slot and
reports the following packet separately. CORE1 totals count segment occurrences
from the bounded render-list inventory, including relocated copies.

| Local image | Framed segments | Framed packets | Exact matches | Unequal literal pair |
|---|---:|---:|---:|---:|
| ZENOLOGY arm64 | 177 | 12,365 | 4 | 0 |
| Fantom bmc0 | 377 | 36,793 | 10 | 0 |
| Fantom bmc1 | 34 | 12,176 | 0 | 0 |
| JUPITER-X C1A | 979 | 86,857 | 24 | 2 |
| MC-101 C1A | 59 | 13,639 | 0 | 0 |
| SH-4d C1A | 909 | 79,912 | 22 | 0 |

Six MC-101 and one SH-4d candidate segments did not frame and were excluded. The
QSPI parser checks the container CRC and member bounds. The report maps each stored
source back to its original container member. The JUPITER-X container SHA-256 is
`9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`.

The two unequal matches belong to one JUPITER-X list at `61218324`, with segment
bases `2020` and `7020`. Each segment is `16a6` logical bytes. The original container
source offsets are `2545d0` and `255c78`. A native Thumb call at `6102b4f2` reaches
the setup body at `6107dace`. That body loads this exact list through the literal
at `6107dbc4` and passes it to manager slot `28` at `6107dade`. The caller and list
selection are static observations. The model or user-facing effect name is unknown.

Both segments load through `0fe0/1fe2` immediately before the exact `4822 / 1940`
packet at logical `ca`. The width-three fields at `d0/d3` contain `(1, 0)` in slot
order. The next packet at `d6` has `5824 / 19c0`, a co-issued `cfe2` store to
`200e` or `207e`, and independent width-three fields at `e0/e3` containing `(0, 1)`.
This establishes that a stock instance of the exact first form can encode unequal
literals. Its successor and input transfers differ from LINE's. Both instances
are relocations of one context, and their results have not been observed. Literal
contribution, source/destination port selection, the LINE-specific tie rule and
`afe0/bfe2` capture remain open.

An independent native comparison point is BITCRUSH. Its `4812 / 1500` packets at
`15c`, `1a8` and `1f4` carry width-two pairs `(0.75, 0.25)`, `(0.5, 0.5)` and
`(0.25, 0.75)`. Native instructions at `241b98..241ba4` load constructor fields
`+158/+168` for the first pair and compute `d1 × first + d3 × second`. The
analogous native windows start at `241c6c` and `241d44`. These comparisons provide
different coefficients and a weighted-sum reference for the neighboring form.
They leave the DSP input and output ports of `4822 / 1940` unresolved.

```sh
python tools/line_mix_variation.py \
  --core1 local/b0c1a.bin --core1 local/b1c1a.bin \
  --qspi local/crossmodel/jupiter-x/MI077_C1A_up.bin \
  --qspi local/crossmodel/mc101/RPG69_C1A_up.bin \
  --qspi local/crossmodel/sh-4d/DD013_C1A_up.bin > local/line-mix-variation.json
```
