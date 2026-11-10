# Next complete-program emulator target

2026-11-10. **Select the primary LINEDRIVE program next**, with FETDRIVE as the
shared-prefix comparison and TS808 as a later alternative. This is an engineering
priority among five inspected native/DSP pairs, not a statement that any complete
stock effect can currently execute. No complete program was justified in this pass.

The two strict interpreter milestones being developed separately cover exact
60-byte dry/wet and 82-byte allpass fragments. Here an admitted region means the
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
| `SIM_MFX_FETDRIVE` | 458 / `8372f4` | `2f7de4..2f81c4` | Dry/wet `16a..1a6` |
| `SIM_MFX_LINEDRIVE` | 578 / `7b47f4` | `2df874..2dfd94` | Allpass `13e..190`, `190..1e2`; dry/wet `1e2..21e` |
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

The complete remaining regions are `000..13e` and `21e..242`: **42 packets**.
All of each remaining packet, including its shared pool, stays unadmitted. The
local JSON lists each packet's start/end, header, base controls, structural family
or explicit layout failure, and pool byte range. No hole is skipped as zero, NOP,
an immediate or an address merely because its encoding resembles a familiar form.

| Remaining LINEDRIVE region / requirement | Concrete gap |
|---|---|
| Opening `000..004` | `ff71` is a stock mutable mute gate; its execution/skip/store consequences are unproved |
| Input/prefix `004..13e` | Mixed long/short arithmetic, extensions, special controls and transfers are not fully decoded. Examples include `4822`, `2424/3467`, `2485`, `fe10`, `b9b2`, `ac99`, `aed2/1e10`, `aeda`, `0e8b`, `5424/643e`, `5464/647e`, `ceae`, `4086`, `0044/1044`; these names are inventory, not opcode assignments |
| Pool roles throughout that prefix | Literal width/reference selection, extension consumption, auxiliary store sources and interactions with special/condition state need exact contextual proofs |
| Suffix `21e..242` | Stores to scratch, reloads, co-issued output stores with `00f8`, and trailing `ff70` must all execute under a proved entry/return contract |
| History/factor inputs to the allpass chains | Caller must supply real prior state and the factors produced before `13e`; using zero or arbitrary external factors would create a different program |
| Cross-invocation memory | Ring base/current index, wrap, retained history and initialization must be modeled explicitly; the fixed fragment's stores do not supply an allocator or reset protocol |
| Parameter binding | Eight constructor default records and six live coefficient-pointer fields have different roles; literal patching, parameter-base offsets and live float reads cannot be collapsed into a single coefficient array without proof |
| Numeric policy | Prefix native fixed-point conversions, integer shifts and nonlinear selection cannot be replaced by unconstrained floating arithmetic; BMC precision, saturation and issue timing remain a separate silicon-validation gap |

The suffix is 36 bytes/four packets in both LINEDRIVE and FETDRIVE. Seeing a native
return after output writes does not identify `00f8`'s saved PC, transfer latency or
the meaning of the following `ff70`. The six-byte stock placeholder
`00f8`/NOP is likewise not a justified complete trivial target: its implicit return
state remains unknown. The [condition/return study](condition-fields-and-implicit-return-study.md)
states that precise boundary.

## Alternatives and reasons to defer them

**Second: FETDRIVE.** Its smaller image and branch-free native body are useful for
checking shared mixing/shaping hypotheses. The strict dry/wet region leaves
`000..16a` and `1a6..1ca` unadmitted: **51 packets**. Header `7308` is unresolved
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
all 40 packets remain outside those two interpreter admissions.

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
