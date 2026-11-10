# LINEDRIVE native ring state and history cadence

The native reference supplies a concrete LINEDRIVE state interface: a shared
2,048-double ring, explicit wrapper base P and ring origin O, and data element
index **`(address + P - O) & 7ff`**. The callback does not advance O. A separate
native DSP4 sync path advances that ring's origin after routing and DRAM-IO.
With fixed P and one such step between callbacks, twelve actual prior-write /
next-read pairs alias the same physical element, including origin wrap.

This is a checked desktop reference interface, not a recovered BMC circular
addressing rule or hardware sample clock. Callback count per core sync, arbitrary
caller rebasing, intervening writers and hardware execution remain separate.
The findings let an offline harness replace an invented delay cadence with an
explicit, conditional native context step. They do not implement the full effect.

All addresses below belong to the pinned ZENOLOGY arm64 artifact SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Only offline Capstone and read-only Mach-O inspection were used. No target,
plugin, firmware, updater or device was executed.

## Callback address contract

For callback `SIM_MFX_LINEDRIVE::VSubProc` at `2df874..2dfd90`:

| Input / state | Native source |
|---|---|
| Simulator record object | `wrapper[28]` |
| Core/resource context R | `load(load(wrapper+8)+18)` |
| Ring descriptor D | `load(R+10)` |
| Ring double-array pointer | `load(D+18)` |
| Wrapper base P | unsigned word `wrapper[10]`, loaded at `2df8a8` |
| Ring origin O | unsigned word `D[20]`, loaded at `2df8b4` |
| Relative address | Constructor/getter-established record word in simulator object |
| Physical element | `(relative_address + P - O) & 7ff`, then scale by eight |

Offsets are hexadecimal. W-register additions/subtractions wrap at 32 bits;
the final 11-bit mask makes the pure index expression above equivalent. The
first store forms address+P−O explicitly at `2df8b8..2df8c4`. At `2df8cc`, w10
becomes P−O and is retained for the rest of the callback. There are no calls,
branches or origin updates within this fully decoded straight-line callback.
The producer and permissible later changes of wrapper P are not newly proved
here; a harness must supply it explicitly rather than silently assume zero.

The checker independently reconstructs all 159 constructor/getter address
records and verifies their equality with the older reader. That metadata count
is **not the ring size or the number of history cells**. It joins every actual
accessed record to its logical program operand in the pinned `242`-byte program,
SHA-256 `a7306c45ee503e60061261f9fa0fde3f8dfc708e6c245b3868e917e6a7d3ea02`.

There are 46 indexed double accesses to this array per callback: 24 reads and
22 writes, using 32 distinct logical addresses. Existing `native_accesses()`
resolves 44. The remaining two are not discarded: `2dfa64..2dfa70` loads
record+`fc` (address27), adds P−O, masks7ff, and **then** shifts left3 into x13.
`2dfa74` reads through `[x9,x13]`; `2dfab4` writes through the same index, with
no intervening x13/w13 writer. These are ordinary scaled element accesses,
expressed as a pre-scaled byte index, rather than a different address domain.

## Actual ring object and context step

`CGlobalObj::CreateObjs` at `2ac16c..2ac190` allocates a descriptor, installs
vtable address point `a40d40`, initializes descriptor+20 to zero and saves it
at global+40. Its RTTI name is `18CDSPRingDTTemplateIdLi2048EE`, identifying the
double/2048 template. Vtable slot0 points to `2ac570`, which performs exactly:

```text
D.origin = (D.origin + 1) & 7ff
```

`CSimDSP4_Core` construction loads global+40 at `16bb1c` and installs that
descriptor at core+10 at `16bb7c`. It assigns its array pointer, sets origin0,
and calls `_bzero` with size4000 at `16bbbc..16bbc8`: 2048 native doubles. The
import name at stub `6d87c4` was checked with `xcrun otool -Iv` on the pinned
artifact. This is initialization of a shared native core backing array.

The double-input `CSimDSP4_Core::VProcSync` path calls its routing callback at
`16c364` (or `16c390` for the no-input case), calls `DramioProc` at `16c398`,
then invokes core+10's descriptor slot0 at `16c39c..16c3a8`. Thus the origin step
is in a **context sync**, after routing, rather than in LINEDRIVE's callback.
The float-input variant has the same final sequence at `16c18c..16c1a0`.

This does not establish how many times a particular LINEDRIVE instance is
invoked by arbitrary routing, its parent manager or DSP5. DRAM-IO or another
owner may also write the shared array. The history-value relation below is
conditional on fixed P, one origin step and no intervening overwrite of the
relevant stored values. The separate `CBMCDspRes` 23-bit counters are not used
as substitutes for this ring descriptor's origin.

## Delayed history versus same-callback scratch

For previous callback origin O and next origin `(O+1)&7ff`, with fixed P:

```text
index(written_address, P, O)
    == index(written_address+1, P, (O+1)&7ff)
```

The checker verifies exact constructor-record, program-operand, pointer-path,
mask and scaled-double bindings for these twelve actual pairs. All addresses
in this table are hexadecimal:

| Role | Previous logical writes | Next logical reads |
|---|---|---|
| Pre-rational smoother history, L/R | `3, 6` | `4, 7` |
| Allpass A prior x/u0/u1/u2/u3 | `9, c, f, 12, 15` | `a, d, 10, 13, 16` |
| Allpass B prior x/u0/u1/u2/u3 | `18, 1b, 1e, 21, 24` | `19, 1c, 1f, 22, 25` |

The allpass store equations were independently verified in the existing
[native MAC/store-order study](mac-controls-and-issue-study.md), and their
single-fragment behavior in [emulator validation](fragment-emulator-validation.md).
Each chain still has thirteen distinct logical source/target addresses in one
callback. Their inter-callback alias arises from the explicit native origin
step; it is not a same-callback address alias or an inferred DSP instruction.

Factor/history production must remain separated:

| Native ordering | Logical state |
|---|---|
| `2df96c` / `2dfa20` | Read previous smoother state at4 /7 |
| `2df9bc,2df9cc` / `2dfa50,2dfa60` | Write equal pre-rational values to27+3 /28+6 |
| `2dfab4` / `2dfac8` | Rational stage overwrites27 /28 |
| `2dfb08` / `2dfc08` | Allpass reads current post-rational factors27 /28 |
| `2dfbb8` / `2dfcb8` | Allpass produces current wet outputs29 /2a |
| `2dfce4` / `2dfd08` | Tail reads those same-callback wet outputs |

Consequently, the next smoother input4/7 recovers the prior **pre-rational**
value from3/6 under the stated step conditions. It must not be initialized or
updated from the final allpass factor27/28. This pass records production and
memory order; the separate nonlinear study owns the factor arithmetic.

## Initialization, counterexamples and scope

LINEDRIVE `Init` at `2df6e0` allocates a `5a8`-byte simulator-record object,
calls constructor `2dfe04`, and stores the result at wrapper+28. It does not
itself clear the shared ring. A new record object therefore does not prove
zero history during an effect transition. Native core construction provides
one proved zero-ring startup; warm starts need supplied history. The separate
[RAMCLR loops](dramio-clear-records-and-native-state.md) and effect-replacement
protocol retain their previously documented coverage limits.

For a nonzero wrap counterexample, let P=0 and previous O=7ff. A write to
logical3 lands at physical4. After the descriptor advances to O=0, logical4
reads that **same physical4**. Keeping O unchanged instead reads physical5;
advancing it in the wrong direction reads physical6. An array with only
physical4 set to3/8 distinguishes all three. A zero-filled test alone would
hide the difference. Changing P by one also breaks this particular history
identity, which is why the fixed-base condition is explicit.

Three tests check unsigned bounds/32-bit wrap, all twelve nonzero-history
aliases across origins0/1/7fe/7ff and three P values, wrong/no origin advancement,
changed P, and the pinned native ring/callback/access evidence. All pass without
target execution. The read-only report includes source-span SHA-256 values.

```sh
python3 tools/line_state_study.py
python3 -m unittest discover -s tests -p test_line_state_study.py -v
```

Use the existing Capstone-capable interpreter and local native/pairs/exports
corpus. Pure address tests run without the corpus; its evidence test skips
explicitly when unavailable. A bounded Qwen review returned four purported
contradictions. Source checks and the modulo tests rejected them: they omitted
the updater between callbacks, substituted zero for the distinct written/read
addresses, reversed the observed add→mask→shift order, and confused static
access count with callback count per context sync. No model change was made
to accommodate those incorrect claims.

Still open: complete parent invocation cadence, P assignment/rebasing contract,
intervening owner/DRAM-IO writes, per-instance reset coverage and hardware ring
semantics. This native ABI alone does not make a complete running LINEDRIVE
engine or justify hardware program execution.
