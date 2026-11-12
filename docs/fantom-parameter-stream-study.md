# Fantom assignment words to original parameter editing

The [host family study](fantom-host-family-study.md) matches 48 generic and 26 typed descriptor tuples, with different host IDs, and replays paired host messages. It does not establish their translation into this internal stream or assign host stores to CORE1 slots.

Follow-up: [host block construction](fantom-host-block-study.md) now has 108 original constructor/serializer replay cases. Its outer structured metadata is distinct from this internal CORE1 format; the missing peer is still unproved.

2026-11-11. The recovered control path now begins before the stream writer:
original assignment-word copying, ring enqueue/dequeue, ASGN handler/callback,
`CUMDWRxPRMEdit` reassembly and selector84 dispatch feed the
[store/finalize/EFCT/FDRV path](fantom-parameter-store-study.md).
This identifies a concrete incoming CORE1 parameter-edit route, without
establishing its host/CORE0 transport or a safe custom-engine entry.

The source is still the pinned stripped CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
`tools/fantom_parameter_stream_study.py` checks RTTI, task bindings, switch
targets, vtables and instruction anchors. REA is unavailable; the evidence is
file/Capstone analysis and bounded Unicorn 2.1.4 execution. No DSP profile is added.

## Source bindings

Addresses, offsets, selectors and tags below are hexadecimal; counts, part/slot
indices, task IDs and IRQ numbers are decimal.

| Edge | Source |
|---|---|
| RXDT kind3 branch | Its TBB target is `0111ebba`; `0111ebc8` calls `0110a5a6` after any required initializer returns |
| Assignment input | `0110a5a6` immediately loads the caller's word, enqueues via `0110a390`, then requests task5 |
| Main assignment ring | State `2008044c`, data `200876d4`, 2,048 slots with 11-bit index wrapping |
| Registered ASGN | Task5 / IRQ233; vector `011003e4` → handler `011021cc` → callback slot `2008496c` → `0110a65c` |
| Kind3 dispatch | `0110a6c8` passes object `20089ad4` and the word to `0110ac78` |
| Receiver | RTTI `CUMDWRxPRMEdit`, address-point vtable `61179ae8`; slot0 reassembles, slot4 invokes `0110ad92` |
| Receiver initialization | `0110bbc8` initializes the edit object and adjacent receiver, installing their concrete vtables |
| Selector84 case | TBB target `0110aef6`; constructs `CMUSE_PrmStmSF`, calls its block writer, then finalizes with argument0 |

The RXDT edge is source-checked, not executed as a complete RXDT/ingress-IRQ
fixture. The tested path starts at assignment input and initializes its private
queue/receiver state explicitly. No all-path boot or initializer-completion claim
follows from the table.

## Internal word and payload format

ASGN selects this receiver for words whose first byte has high nibble3. The
receiver uses the low nibble as follows:

| First byte | Data bytes appended | Effect |
|---|---:|---|
| `34` | 3 | Continue, without dispatching |
| `35` | 1 | Finish and dispatch |
| `36` | 2 | Finish and dispatch |
| `37` | 3 | Finish and dispatch |

On a new sequence the count resets; a preceding continuation retains it. The
object has prior-tag state at+4, byte storage at+8 and a u16 count at+208.
Terminal tags invoke its slot4 with the assembled buffer and count. The source
also has capacity/error guards; this checkpoint exercises complete short records
of **5, 7 and 9 bytes**, not arbitrary malformed or maximum-size streams.

For the checked MFX case the authored assembled payload is:

```text
84  part  00  [little-endian generic-ID offset] [complete field bytes]
```

Part0..2 maps to MFX slot1..3. The third header byte is consumed but not used by
this selected case. The dispatcher removes all three header bytes before calling
the existing block writer. Generic IDs and descriptor-sized field bytes retain
the contracts from the store study; no new field schema is inferred.

For example, part0, logical mode1 and cutoff1000 produce these authored
little-endian assignment words:

```text
00008434  01001234  03e80037
```

The final full group uses37; another empty terminal is not appended. One-field
and empty-write records exercise35 and36 respectively. Data octets can have
their high bit set; this is not a 7-bit MIDI/SysEx encoding. These words are
CORE1 assignment inputs, **not ttyGS0 host frames or device commands**. Their
translation through the missing peer remains open.

## Serialization and object lifetime

The selector84 receive case sets r1=0 at `0110af0c` before finalization. It does
not use the global serialization flag at `20081980`. The fixture sets that byte
to80 and still observes argument0 and no optional external serialization.

The separate scalar adapters are associated with RTTI `CEZSNDTonePrmSFSub`,
vtable `6117b010`: slot1c → `61080abc` writes; slot14 → `61080ac4` finalizes
using the signed global byte. That RTTI binding is checked, but its higher UI
caller, the flag's runtime value/meaning and an external route are not proved.

The receive dispatcher constructs its stream object on its stack. Its dirty
range is therefore captured at the original finalizer entry; the fixture does
not read an expired object after the handler returns. Existing store checks still
verify the finalizer's dirty-marker behavior separately.

Assignment input copies its u32 into the ring. The fixture overwrites the caller's
temporary word with `deadbeef` before ASGN consumes the queue; reconstruction and
coefficient results still match. This verifies local word-copy lifetime, not the
ownership of an external host message or interleaved fragment sequences.

## Executed checks and boundaries

**576 cases match 2,160 coefficient writes**, consuming **1,584 assignment words**
and producing **864 local notifications**. Cases span all three checked slots,
two mute counts, both enable flags, three modes, two cutoffs and four changed
sets, at empty-ring cursors0 and2047. The latter crosses the ring boundary.
An additional all-ones cutoff case traverses the receiver and reads default3740.

The fixture executes original ring initialization, receiver construction,
assignment copy/enqueue, ASGN handler body/callback, dequeue, reassembly,
selector dispatch and the existing store/finalizer/EFCT/FDRV bodies. It checks
ring head/tail/occupancy, ASGN invocation/activity, exact assembled bytes,
constructor/store binding, writer arguments and dirty ranges. Auxiliary queues
start empty; full-ring/backpressure behavior is outside this replay.

Task signaling, ASGN's IRQ reenables, coefficient I/O, slope effects and post-apply
hardware routing are recorded or intercepted. EFCT is run explicitly after ASGN
returns. No actual exception arrival, preemption, OS startup, physical NVIC/BMC
peripheral or instrument execution occurs. The initial run exposed a fixture
resume-address bug at an intercepted NVIC store; preserving the Thumb bit fixed
it, after which the focused source/CPU checks passed.

Qwen returned an encoder draft in46.0 seconds. Review retained its chunk/tag
algorithm, replaced the permissive integer-subclass check with an exact part
type check, and removed extensive commentary/unreachable branches. Its incomplete
tests were replaced with independent exact-word/all-terminal checks and the
original receiver/queue comparisons. No model claim establishes host compatibility.

```sh
python3.13 tools/fantom_parameter_stream_study.py local/b0c1a.bin
python3.13 tools/fantom_parameter_stream_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_parameter_stream.py -v
```

Next bind this CORE1 stream format to the readable host's structured-block
constructors/serializer, preserving the missing CORE0 peer boundary. Live queue
ownership, IRQ priorities/masks, completion cadence, silicon precision/history,
entry/return and safe custom-engine loading remain separate requirements.
