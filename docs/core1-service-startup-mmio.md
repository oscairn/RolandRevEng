# CORE1 service initialization and MMIO reply frame

Follow-up: [transmit/backpressure](core1-transmit-and-backpressure-study.md) follows
the reply's far call into type-3 word packetization, TXDT and its shared-ring
writer. This closes a CORE1-local edge, not the Linux bridge or safe request bounds.

2026-11-10. Offline follow-up to [the host/CORE1 bridge study](host-core1-bridge-followup.md).
The two bmc0 SysEx receivers are installed by an initializer actually visited by
the reset/startup table walker. The previous relative-pointer candidate is now
connected to that compiled startup path. The MMIO read-reply size discrepancy is
also confirmed against the exact stack offsets and loop stores. The corresponding
bmc1 receiver pair is initialized the same way, and its reply builder has the same
frame problem.

These are static observations from Python 3.13.7 and Capstone 5.0.7, not REA
Evidence records or observations of a running keyboard. No Roland executable or
firmware was executed, device opened, request generated or message sent.

## Inputs and address scope

All addresses are CORE1 runtime addresses under `tools/core1.py`'s ITCM/ERAM mapping.
The inputs are header-stripped payloads; the audit also accepts their recognized
container form, hashing the stripped payload before using build-specific addresses.

| Payload | SHA-256 |
|---|---|
| bmc0 `local/b0c1a.bin` | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |
| bmc1 `local/b1c1a.bin` | `c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd` |

## Startup reaches the initializer table

The bmc0 reset vector at `01100004` contains Thumb pointer `01100e55`.
The routine at `01100e54` performs core setup, calls two setup routines and at
`01100ec0..ec2` loads/branches to `61000001`. The ERAM bootstrap at `61000000`
calls the scatter loader at `61000008`. At completion the scatter loop calls
`61076a64` from `6100001a`; the instruction after the bootstrap call,
`61000004`, targets that same veneer. Its MOVW/MOVT/BX sequence selects
Thumb pointer `011004d7`.

`011004d6` establishes the runtime stack and calls `01100490` at `011004da`.
The latter does runtime/library setup, then calls the initializer walker
`0112ce90` at `011004be`. Thus this is an actual startup call edge, rather than
an inference from nearby data. It precedes the subsequent call at `011004de`.

The table bounds follow directly from the walker's literal loads and ADD-PC
instructions:

| Quantity | Calculation | Value |
|---|---|---|
| Start | PC `0112ce98` + literal `60112fcc` | `6123fe64` |
| Exclusive end | PC `0112ce9c` + literal `6011312c` | `6123ffc8` |
| Count | `(end-start)/4` | 89 |

The loop first compares the start pointer with the end, then for each slot:
loads a u32 at `[r4]` (`0112ce9c`), adds the **slot address** (`0112ce9e`), calls
that resulting pointer with BLX (`0112cea0`), advances `r4` by four
(`0112cea2`), compares with the exclusive end and repeats. There is no per-entry
enable flag or filtering in this walker. Arithmetic is 32-bit PREL32-style
resolution, retaining the Thumb bit.

Slot **67** (zero-based), `6123ff70`, is inside these bounds. Its word
`9fededb5` resolves to `0111ed25`. Therefore the receiver constructor at
`0111ed24` is one of the functions this startup loop calls. This establishes
compiled startup activation assuming normal completion of preceding startup
calls; it does not establish a runtime vtable snapshot or prove every earlier
initializer returns under every hardware condition.

## Installed receiver state

`0111ed24` loads object `20094ee4`, temporarily installs the common base vtable
`6117bca4`, and calls `0111f100`. That helper sets object+4 to `0x10` and clears
the halfword at object+`208`, then returns. The constructor installs the concrete
vtable, advances by `20c`, and repeats for the second object.

| Object | Final vtable | Completed-buffer callback (Thumb pointer) |
|---|---|---|
| `20094ee4` | `6117bf3c` | `01135de1` |
| `200950f0` | `61177dac` | `011351a1` |

The stores are at `0111ed34` and `0111ed44`. The virtual callback is at vtable+4.
These match the two objects called by the existing high-nibble-1 router path at
`0111eae2`. The constructor sets each object's initial state rather than leaving
the dispatch path dependent on an uninitialized vtable candidate.

The old host-bridge uncertainty remains: this closes the initializer-table edge
inside CORE1, not the missing ttyGS0 peer or a physical external ingress route.

## Exact MMIO read/reply frame

In bmc0 helper `6102d2e6`, PUSH saves `{r4,lr}` and `6102d2fa` subtracts `0x50`
from SP. Let **S** be that resulting SP. There is no later local allocation or
buffer-base adjustment:

| Region | Half-open offsets relative to S |
|---|---|
| Local reservation / reply start | `[0,80)` |
| Saved r4 | `[80,84)` |
| Saved lr | `[84,88)` |
| Caller-owned stack above entry SP | `[88,...)` |

`6102d342` assigns r0=S. Fixed header and command stores fill offsets 0..4;
the re-encoded address fills offsets 5..8. `6102d384` advances r0 by nine.
The data loop at `6102d39c..3e4` loads one u32, subtracts four from the remaining
byte count, and performs exactly eight byte stores with r0 postincremented by
one each time. It repeats only while the remaining count is at least four.
Thus nonmultiple-of-four remainder bytes are ignored.

The checksum loop starts at S+5 (`6102d3e6`) and ends at the current output
pointer, excluding the fixed five-byte header/command. `6102d41a` appends the
checksum; `6102d420` appends F7. There is no alignment padding between data,
checksum and terminator. `6102d424..428` passes r0=S and r1=output_end-S to the
send call at `6102d42a`. These stores have already happened before that call.
The epilogue adds 80 to SP and pops `{r4,pc}` at `6102d42e..430`.

For decoded count c>=4, n=`floor(min(c,64)/4)`:

- Data occupies `[9,9+8*n)`.
- Checksum is at `9+8*n`; F7 is at `10+8*n`.
- Total emitted bytes are `11+8*n`.

| Decoded count | Words | Emitted bytes | Exact frame overlap |
|---:|---:|---:|---|
| 32..35 | 8 | 75 | Within the local reservation, with five bytes unused |
| 36..39 | 9 | 83 | Last data nibble at +80, checksum +81, F7 +82; three bytes of saved r4 |
| 40..43 | 10 | 91 | All saved r4 and lr bytes, plus caller bytes +88..90 |
| 64 and larger | 16 | 139 | All saved registers and caller bytes +88..138 |

Counts below four return without emitting a reply. This table describes static
frame geometry; it is not a verified safe request bound. A faulting MMIO load or
other runtime condition could prevent later stores. For a path whose loads
complete, the permitted larger counts write past the reservation before sending.
No corruption experiment or exploit was constructed.

### Count and address fields are separate

The four count loads at `6102d31a..32a` are unsigned bytes. The BFI chain first
clears bits 7..31 of the first group, then shifts that accumulated value by seven
into the next group's bits 7..31, retaining each next byte's low seven bits.
The resulting widths are **7, 14, 21, 28 bits**. The count is therefore
`g0*2^21 + g1*2^14 + g2*2^7 + g3`, with every g masked to seven bits. Its sign bit
cannot be set, even if any input byte has bit 7 set. The signed GT clamp to 64
and signed LT lower guard therefore operate on a nonnegative 28-bit count.

The earlier signed address loads and `bic`/alignment test at `6102d2e8..314`
operate on a **different value**. Those operations mask an MMIO offset to
25 bits and reject misalignment; they do not align or mask the count. The reply
address is extracted back into four seven-bit groups from the assembled address
value. For canonical input that reproduces its encoded address; malformed-input
behavior should not be described as blindly copying the four original bytes.

## bmc1 comparison

The corresponding reset routine starts at `01100e14`. The scatter-completion
veneer `6107750c` reaches the same runtime entry `011004d6`. Runtime setup
`01100490` calls walker `0112cad8` at the same callsite `011004be`.
Its ADD-PC calculations yield `613854a0..6138560c`, **91** entries. Slot **70**
at `613855b8` resolves to `011258b1`.

| bmc1 object | Final vtable | Completed-buffer callback (Thumb pointer) |
|---|---|---|
| `200993a8` | `612c090c` | `011362b1` |
| `200995b4` | `612bc1b4` | `01134a09` |

Constructor `011258b0` calls base initializer `01125c54`, which performs the
same +4/+208 state writes. Callback `011362b0` ends by calling veneer
`0113475e`; this selects `61028b70`, which supplies scratch object `200a1f5c`
and branches to MMIO handler `61028a0c`. Its read branch at `61028b68..6e`
tail-calls helper `61028846`.

The first **324 bytes** of bmc1 helper `61028846` are identical to bmc0
`6102d2e6`, through the outgoing-call argument construction. The BL target
differs (`610781b4` versus `6107773e`); the following add-SP/pop epilogue is
identical. This proves the same count logic, stores, checksum and stack geometry
for these two supplied builds. It does not prove common physical reply routing.

bmc1 also has an additional two-object initializer at `0110b87e`, table slot 6
(`613854b8`), objects `2008a0f4/2008a300`, with different concrete callbacks.
That pair was not traced further. There are at least two analogous pairs in that
image; counting the main service pair must not be generalized to all receivers.

## Reproduction and worker review

`tools/core1_service_audit.py` is an offline, digest-pinned check of the startup
anchors, walker instructions, receiver initializer and MMIO frame instructions.
It reports resolved metadata and frame occupancy. Unsupported digests fail
closed; it is not a general startup analyzer, emulator, request encoder or loader.
The six tests include synthetic negative PREL32 displacement/Thumb-bit checks,
bad bounds, count-width examples, exact frame intersections, unknown-build
rejection and both local corpus builds.

```sh
python3 tools/core1_service_audit.py local/b0c1a.bin
python3 tools/core1_service_audit.py local/b1c1a.bin
python3 -m unittest discover -s tests -p test_core1_service_audit.py -v
```

One actual OMP/Qwen draft reviewed a bounded read-helper disassembly using
`MacStudio/Qwen3.8-Flash-Next-Uncensored-oQ6e-mtp`, with all tools, context files
and sessions disabled. Access was serialized with `local/omp-qwen.lock`.
The raw prompt/reply stay under ignored `local/`; no Qwen-generated code was used.
Its buffer start, saved-register offsets, byte totals and checksum-scope statements
were independently confirmed. Its claims that the count can set bit 31, that the
alignment test applies to the count, that every count >32 overflows, and its
description of partial lr corruption at count 40 were **rejected**. The direct
instruction dataflow and tests above take precedence over the worker draft.

Still missing: a runtime vtable/reply observation, the external transport bridge,
manager ownership/timing for DSP writes, and a validated custom-engine ABI/loader.
Initializing the stock debug service does not supply those missing parts.
