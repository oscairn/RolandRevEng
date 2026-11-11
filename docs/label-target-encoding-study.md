# CORE1 label targets and reference records

2026-11-10. Static Python/Capstone analysis of Fantom-0 MI078 C1A v1.08,
payload SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
No firmware was run or modified. These are manager/driver semantics, not new
DSP opcode admissions.

**Result:** the implemented label writer explicitly divides an even byte target
by two before sending it to counted literal fields. This independently supports
the halfword scaling previously suggested by parent-program numeric matches.
It does not establish the control that consumes a field, saved return state,
transfer delay, or a runnable entry/exit wrapper.

## Implemented interface

The CORE1 manager vtable at `6117647c` has these slots. Thumb pointers have bit
zero set; the addresses in the table are instruction addresses.

| Slot | Body | Interface |
|---|---|---|
| `a4` | `0113338c` | `ChangeDspLabelAdrs(LabelSym const*, unsigned)` |
| `a8` | `011334d6` | `ChangeDspLabelAdrs(LabelSym const*, LabelSym const*)` |

The first method takes `this` in r0, source symbol in r1, and a byte target in
r2. Count zero returns immediately, before DSP-index or target-parity checks.
For a nonempty list the method checks the signed DSP value is below seven,
requires an even target, and performs a logical right shift by one at
`0113340e`. Negative DSP values are not explicitly rejected by that comparison;
the offline helper does not offer a live driver call.

The LP32 symbol header starts with a representative six-byte record. Its counted
reference-table pointer is at `+8` and its unsigned count byte at `+c`.
Padding is not assumed to be zero. Each reference is six bytes:

| Offset | Type | Use |
|---|---|---|
| `0` | little-endian u16 | absolute byte address fallback |
| `2` | little-endian u16 | relative byte offset within selected reservation |
| `4` | u8 | render-reservation selector |
| `5` | u8 | flags; high nibble skips the entire reference, low nibble is width |

The high-nibble branch at `01133438` goes to `011334c8`, after the raw write and
guard release. Thus a skipped reference is neither resolved nor patched. When
the render-reservation pointer is null, an eligible reference uses its absolute
address. Otherwise the signed reservation count must exceed the selector, and
the selected capacity must exceed the relative **start**. The site is the base
plus relative offset with 32-bit wrap. The firmware does not check that the full
multi-byte field fits, or that the addition did not wrap. A non-null empty
reservation group is different from a null pointer.

For each eligible reference, the code checks program guard byte `2008480c`,
sets it to one, calls the raw driver, and clears it. This covers one write at a
time, with no batch fence. The ordinary check/set sequence does not demonstrate
an atomic mutex or safe coordination with the running graph.

The LabelSym-target overload resolves the target's representative record using
the same absolute/base-plus-relative distinction and start checks. It tailcalls
vtable slot `a4` with that byte address. It does not use the target's reference
count or flags to resolve the representative.

## Raw field encoding and limits

`CBmcDspDrv::WriteLiteralRaw` at `0112f528` receives DSP index in r0, byte site
in r1, width in r2, and halfword target value in r3. The caller supplies true
for the stack alignment argument. The driver accepts widths **2, 3 or 4**:
the unsigned test is `(width - 2) < 3`.

It masks the **site address**, not the target value, to 19 bits. The command is
`(width << 28) | (site & 0x7ffff)`. With alignment enabled, the data register is
`((byte_target >> 1) << (8 * (4 - width))) mod 2^32`. The command and data go
to consecutive per-DSP portal words; the final read of `41100000` is a separate
ordering read, not target storage.

The writer does not check whether the target fits the requested field. For
width two, targets above the 17-bit byte range can lose upper value bits in
alignment. This is an encoding limit of this call, not proof of the entire
DSP program-address range. `label_target_study.py` reports truncation and site
aliasing instead of silently treating either as a safe relocation. Its logical
field bytes describe the inferred stored value; physical readback remains absent.

For example, byte target `4020` becomes halfword value `2010`, with aligned data
register `20100000` for width two. The five previously recorded parent fields
match that same scaling:

| Parent list | Absolute byte field | Relative to primary segment | Candidate byte target | Field word |
|---|---|---|---|---|
| `610a1f18` | `02f0` | `02d0` | `4020` | `2010` |
| `610a1f28` | `1064` | `1044` | `8040` | `4020` |
| `610a1f28` | `178c` | `176c` | `9040` | `4820` |
| `610a1f28` | `1844` | `1824` | `a040` | `5020` |
| `610b88f0` | `10d2` | `00b2` | `3020` | `1810` |

The checker reads each original program list and stored stream before comparing
these words. These are numeric matches, **not counted label ownership proofs**.
The existing even `00aN` pool-index interpretation stays a hypothesis.

## Why this does not yet supply a call wrapper

The actual FETDRIVE label at `610e7b98` has representative absolute `4020`,
relative zero, segment zero and flags one. Owner `610a1674` also resolves it to
`4020`. Its reference count and pointer are both zero. Passing that handle as
the source to the target writer performs no patches. `SetMuteMode` separately
uses the representative to locate the opening `ff70/ff71`; that does not prove
any incoming target-field association.

The bounded aligned-pointer/direct-branch inspection finds the unsigned method
in its manager vtable without an established direct caller. Examination of the
small `LDR.W +a4/+a8` candidate set identifies the LabelSym overload's own tail
dispatch, not an owner-proven counted parent-call handle. Other dispatch forms,
generated metadata and runtime references remain possible. Exact six-byte
segment-zero/width-two patterns for the five sites above also produced no raw
image hits; that narrow negative search does not exclude other descriptors.

In the pinned ZENOLOGY arm64 image, the `CSimDspMgr` unsigned-target implementation
at `fc950` is a validation stub. The native `_CORE1_DSPWriteProgAll` compatibility
body at `a35c` is also a return stub, not an implemented Fantom firmware loader.
Neither implements a hidden hardware return stack. Native compiled graph calls
and the separate MDSP task-control structures do not establish render-DSP PC
semantics. Earlier [return/store provenance](condition-fields-and-implicit-return-study.md)
still constrains any future model: coissued and following stores prevent treating
every `00f8` as an immediate software return without further evidence.

Next steps are an owner-proven nonempty label reference list or an independent
control-flow implementation, then saved continuation and issue-order evidence.
The [resource plans](fantom-voice-resource-plans.md) retain null load/entry/return
addresses, exclude wrappers, and remain `execution_ready: false`.

## Reproduce and review

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/label_target_study.py local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_label_target_study.py' -v
```

The report pins the image, verifies manager slots, the guard pointer and
instruction anchors across all three bodies, and checks the actual symbol and
five parent words. Pure-helper tests use original records to cover skip order,
null versus empty groups, width/parity limits, truncation, wrap and partial
extent checks. No DSP decoder or emitter was expanded.

Qwen's static review returned in 48.6 seconds, but misread branch destinations,
record offsets, register roles, width bounds and guard behavior. Those claims
were rejected against the original instructions. A separate bounded test draft
was reviewed and corrected locally; its generated expectations are not firmware
evidence. No unreviewed worker result is used.


### Mute entry resolution is a distinct interface

The [exact mute checker](kernel-audio-abi-study.md#exact-stock-mute-search-and-its-limits-2026-11-11)
shows that `SetMuteMode` does not perform this writer's reservation-start capacity
check. It searches all following halfwords in the first header's raw low-five-bit
extent, including payloads, and rewrites only the first `ff70..ff73` match.
These differences are tested independently; sharing a LabelSym record does not
make the methods interchangeable or prove safe running-code replacement.
