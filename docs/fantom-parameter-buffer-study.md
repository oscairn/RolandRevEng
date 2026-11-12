# Fantom raw parameter snapshots and changed bytes

Follow-up: the [stock producer/EFCT study](fantom-parameter-producer-study.md)
binds FDRV to factory ID85 and a 22-element stock snapshot, then source-connects
the registered task8 callback to this buffer and its setter. Actual IRQ arrival,
preemption, external transport and parameter-store writes remain unverified.

2026-11-11. The FDRV parameter interface consumes a pointer to signed 16-bit
values and an element count. It copies values into an embedded buffer and
computes byte-per-field change flags; the second argument is not a flag-word
pointer or a byte length. Original buffer routines now connect to the bounded
[FDRV dispatch fixture](fantom-parameter-dispatch-study.md).

This closes the raw snapshot ABI at that module boundary. It does not identify
the upstream message producer, panel/MIDI mapping, registered caller, exclusion
protocol or a hardware-loading entry. No DSP opcode profile is added.

## Identity and source binding

`tools/fantom_parameter_buffer_study.py` reuses the existing CORE1 hash gate:
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
It checks RTTI, vtable entries and instruction anchors before CPU execution.
REA is unavailable in this session; the evidence is file/Capstone analysis and
bounded Unicorn 2.1.4 execution, not a REA Evidence record or a silicon trace.

| Capacity | RTTI | Vtable | Reset | Update | Value / changed getters |
|---|---|---|---|---|---|
| 20 | `CEfctPrmBufferTemplate<20>` | `6117b7e0` | `0113995c` | `01139988` | `01139aa2` / `01139a9a` |
| 24 | `CEfctPrmBufferTemplate<24>` | `6117b7f8` | `011399fc` | `01139a28` | `01139ab4` / `01139aac` |
| 32 | `CEfctPrmBufferTemplate<32>` | `6117b810` | `610848d8` | `61084904` | `6108497e` / `61084976` |

Addresses and object offsets in this document are hexadecimal; capacities and
field indices are decimal. Vtable slots 0/4/8/c are reset/update/value/changed.
The update receives object in r0, source pointer in r1 and signed count in r2.
Value/changed getters receive the field index in r1.

The factory branch `6102f18a..6102f1b2` calls the FDRV constructor `61049e40`,
then selects the RTTI-linked `CMfxFDRVPrm` vtable `61176e20`. At wrapper+8 it
installs the capacity-32 buffer vtable, stores wrapper+8 at wrapper+4, and stores
the FDRV effect pointer at wrapper+74. The selected factory branch is checked
statically; allocation, factory selection and its lifetime are not executed.

The unchanged-algorithm outer callback `011290ee` forwards its incoming r2/r3
as source/count to interface slot4 at `011291c6`. FDRV then obtains signed values
and changed bytes through the same embedded object's slots 8/c.

## Storage and update rules

For capacity N, the buffer has the following layout:

| Offset | Contents |
|---|---|
| 0 | Vtable pointer |
| 4 | Signed last-update element count |
| 8 | N signed 16-bit values, ordinary index order |
| `8 + 2*N` | N changed bytes, returned with signed-byte loads |

For FDRV's N=32 this occupies 104 bytes, with flags at offset48. Reset writes
count 0 and every flag 1. **Reset leaves value storage untouched.** An initial
value array in a fixture is explicit prior storage, not an inferred zero-fill.

Updates behave as follows within the checked nonnegative-count domain:

- A count above capacity returns without changing the object or reading the
  source. A count of zero stores count 0 without reading the source or clearing
  any old values/flags.
- A positive update after count 0 marks every supplied element changed, even
  when its value already equals retained storage.
- Otherwise each supplied element's flag becomes 1 when its signed value
  differs from retained storage, and 0 when equal. The new prefix is copied.
- Values and flags outside that prefix retain their previous contents. Growing
  a nonempty buffer compares newly included fields with retained storage; it
  does not force them changed solely because the previous count was smaller.
- The count is the size of the most recent update. The getters themselves do
  not check capacity or that count before reading a field. A consumer must not
  assume an unvisited tail flag was cleared by a short update.

Both source and destination are visited backwards while preserving ordinary
element order: source starts at `source + 2*count - 2`; the destination offset
is `6 + 2*(count-i)`, equivalent to `8 + 2*(count-1-i)`. The flag offset likewise
uses `47 + (count-i)` for N=32, equivalent to `48 + (count-1-i)`.
Those displaced loop operands do not imply reversed storage or two flag arrays.

The original function compares count as a signed integer and has no lower-bound
check. Negative counts and invalid getter indices are not admitted by the safe
fixture API; this is a research boundary, not a claim that the firmware rejects
them. Source/destination aliasing is also outside these checks.

## Execution and remaining boundary

Twenty-four original-buffer cases span all three capacities, signed extrema,
reset, first/repeated copies, short updates, shrink/grow, zero and oversize.
Canaries check object bounds. Zero and oversize calls use a null source to check
that it is not read. Valid sources are checked for preservation, then overwritten
before calling every original value/changed getter: getters still return the
copied object state. This proves local synchronous copying, not upstream message
ownership or concurrent-call safety.

The connected fixture builds the embedded capacity-32 object, runs its original
reset and baseline copy, then forwards a second 32-element snapshot through the
original outer callback. Values/flags are no longer recording callbacks.
Only fields 2/3 change, so other FDRV parameter groups remain inactive. Across
edge slots 0/3, mute counts 0/2, three mode values, two cutoffs and four changed
sets, **96 cases match 360 coefficient writes** against the independent model.

Coefficient reads/writes and companion slope effects remain controlled as in the
previous fixture. No factory allocation, algorithm replacement, OS/IRQ task,
real MMIO, hardware precision/timing or instrument startup executes. The 18 DSP
sequence profiles and 1,692-byte arithmetic chain are unchanged.

Qwen returned a no-tool review in 37.8 seconds. Its first-copy, zero and oversize
observations were independently checked. Its two-flag-array and reversed-storage
claims were rejected by address algebra and asymmetric CPU cases; a trailing
data word is not treated as an extra source function. No Qwen code was accepted.

## Reproduce

Use the Python environment from the repository README and a prepared local image:

```sh
python3.13 tools/fantom_parameter_buffer_study.py local/b0c1a.bin
python3.13 tools/fantom_parameter_buffer_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_parameter_buffer.py -v
```

The producer follow-up now supplies the source/count caller and registered
callback binding. Next trace the parameter-store write/notification producer,
preserving object lifetime, priority/mask state and the distinction between the
local snapshot ABI and external transport.
