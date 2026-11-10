# Transfer spaces: native provenance study

2026-11-09, local Fantom/ZENOLOGY corpus. This study supersedes the broad labels
**tag 2 = IO space** and **tag 4 = coefficient-RAM window** in the earlier packet map.
Those descriptions were too strong. The observed native model contains two distinct
circular data arrays and a third directly indexed, readable/writable double array.
Live `C0xx` coefficient values take a separate pointer path through 0x48-byte records.
No hardware mapping or timing is established by these desktop storage layouts.

## What the tracer proves

`tools/transfer_study.py` reconstructs constructor-written table bytes from actual
ARM64 constants and literal loads, ending at the constructor's first return. It
checks the result against the existing getter's table base/count and recovers records
of `{program-relative field address, simulation-relative memory index}`. Unsupported
register writes invalidate provenance; an unknown store invalidates previous object
bytes instead of leaving stale constants. W/S, X/D and Q accesses have distinct widths.

The native sample-loop tracer starts at the real argument pointers and follows load
and register-copy provenance. An object-field match is accepted only through the
proved `wrapper + 0x28` object path. It tracks address-field use through add/subtract
and masks into indexed floating-point reads/writes. It stops at the first branch,
call or return; it does not pretend to explore every control-flow path. The old textual
lifter matched some fields without checking their base pointer and is not this proof.

Results on the prepared arm64 image:

| Check | Result |
|---|---:|
| Classes with independently reconstructed tables | 73 |
| Reconstructed 8-byte records | 12,789 |
| Indexed native accesses with one resolved table field | 2,388 |
| Ambiguous/unresolved indexed accesses | 1 |
| Classes skipped by bounded reader | 2 |

The skipped classes are `SIM_REV_VP` (unsupported constructor table form) and
`SIM_CHO_CHO` (getter/table layout not resolved). Excluding these is an analysis limit,
not proof that they lack ordinary data memories.

## The spaces are distinct

Let `R = load(load(wrapper + 8) + 0x18)`, the native core/resource object used by these
effect routines. Every resolved access in each group takes the following path:

| Program tag | Native data pointer | Index wrapping | Resolved reads / writes | Classes |
|---|---|---|---:|---:|
| `0xxx` | `load(load(R + 0x10) + 0x18)` | `& 0x7ff` | 1,096 / 924 | 72 |
| `2xxx` | `load(load(R + 0x18) + 0x18)` | `& 0x7ff` | 2 / 2 | 1 |
| `4xxx` | `load(load(R + 0x28) + 0x18)` | No mask in these accesses | 246 / 118 | 32 |

The four tag-2 accesses are in `SIM_MFX_FZ`. Its program operands `2016..2019` map to
simulation-relative indices 0..3 in the second circular array. In many other routines
the corresponding effect inputs/outputs use direct native input/output arguments
instead. Thus the specific MFX input/output role of `2016..2019` remains
useful, while naming the whole tag-2 address space simply “IO” is not justified.

For every class/tag represented above, **program low-12-bit index minus constructor
simulation index is a single constant**. This includes nonzero bases: reverb tag-4
examples use `0x8c`, chorus examples `0x78`, and the observed FZ tag-2 base is `0x16`.
There are no inconsistent deltas among the 2,388 resolved accesses. Comparing the raw
program index directly with the simulation-relative constructor value would wrongly
report mismatches in relocated/shared chorus and reverb spaces.

The native `CSimDSP4_Core::GetMemoryAdrs(DspDataMemoryType, unsigned)` dispatch at
`0x16c3ec` independently returns the same pointer paths for enum values 0, 1 and 2.
Values 0 and 1 subtract their group's base pointer and mask by `0x7ff`; value 2 adds
the index directly to the double-array pointer. This is a native API cross-check,
not an interpretation based solely on numerical proximity of memory tags.

## Tag 4 is not a coefficient-only space

In `CSimDSP4_Core`'s constructor at `0x16bb04`, the member at +0x28 comes from global
object +0x68. The constructor passes that object to the exported
`CBMCDrm::Init(double*, double*)` at `0x2839b0`. That method installs its two array
pointers at +0x18/+0x20 and clears storage. DSP5's corresponding member comes from
global object +0x70. “CBMCDrm-backed direct data space” is a defensible native label;
the expansion of `Drm` and its exact hardware implementation remain unknown.

GATE writes gained audio samples to tag-4 indices 0/1. DJFXLP reads and writes its
tag-4 window as part of effect state calculations. This does not support treating
every `4xxx` field as an immutable coefficient or moving it with coefficient-RAM
relocation rules. Some values in that space may be coefficients or control parameters,
but the space is demonstrably general read/write effect data in this native model.

By contrast, live coefficients are loaded from constructor-established pointers of
the form `base + 0x48 * (parameter_base + slot)`, followed by a **32-bit float** load
at record +0x28 and conversion to double. The data-array accesses above are direct
**64-bit double** reads/writes. These are distinct desktop paths; whether the physical
chip shares any backing storage cannot be settled from this observation alone.

## Limits on coefficient-order alignment

The bounded constructor proof establishes some, not necessarily all, live coefficient
pointer fields in each class. The study observes prefix agreement for 52 of 53 classes
with tracked live-coefficient reads. The remaining MS_EQ case uses conditional
constructor pointer assignments the helper does not fully model. That result is
**incomplete coverage**, not proof of a different execution order.

Therefore first-seen `C0xx` order is a useful alignment check on a covered example,
not a general ISA invariant. Neither sorted object-field order nor unproved pointer
arithmetic should create coefficient slot numbers. The separate gain study deliberately
rejects examples outside its supported pointer model.

## Reproduce

```sh
python3 tools/transfer_study.py
python3 -m unittest discover -s tests -p 'test_transfer_study.py' -v
```

Full method addresses, resolved access provenance and per-class rows go to ignored
`local/transfer_study.json`. No full program, native disassembly or vendor table is
added to the repository. Pure-helper tests run without vendor artifacts; native fixture
tests require Capstone and use study-owned assembly. The corpus check skips when local
inputs are unavailable. Hardware behavior, cycles and physical address-space aliasing
have not been checked.
