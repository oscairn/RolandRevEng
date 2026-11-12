# Fantom stream writes, dirty IDs and local finalization

Follow-up: the [assignment-stream study](fantom-parameter-stream-study.md)
now executes the original assignment queue, ASGN callback, PRMEdit reassembler
and selector84 dispatcher before this writer. The incoming case hardcodes
serialization false; the separate scalar/UI adapter flag remains unproved.

2026-11-11. Original scalar/block stream writers and their finalizer now run
before the [EFCT/FDRV producer](fantom-parameter-producer-study.md). The fixture
no longer supplies the final store bytes or constructs its own EFCT notification:
original routines write the requested cells, track dirty IDs and emit the local
notification before the handler/producer/setter path executes.

This is a CORE1-local control path. The incoming transport caller, optional
outbound serialization, physical IRQ delivery/exclusion and custom-engine
loading remain unproved. No DSP execution profile is added.

## Checked source and the two descriptor domains

The source remains the pinned stripped CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
`tools/fantom_parameter_store_study.py` checks RTTI, vtables, descriptor records
and source anchors before CPU execution. REA is unavailable; evidence comes
from files, Capstone and bounded Unicorn 2.1.4 execution.

| Routine | Address | Observed role |
|---|---|---|
| `CMUSE_PrmStmSF` address-point vtable | `6117958c` | Generic range getters and object/store size |
| Stream constructor | `61004ff8` | Part-store pointer, part index, flags and initial dirty range |
| Scalar wrapper/base | `610050b6` / `610040aa` | Raw value store plus dirty-ID tracking |
| Block wrapper/base | `610050ca` / `61004104` | Relative start ID, descriptor-sized copies, dirty-ID tracking |
| Finalizer | `61005034` | Local notification(s), with optional external serialization |
| Local notification veneer | `61076c44` | Resolves to `01126d2e`, the checked EFCT notifier |

Addresses, IDs and object offsets below are hexadecimal unless marked decimal.
The stream range is `587..5b6`; generic halfword fields begin at `597`.
Its part store is 84 decimal bytes, at the previously recovered
`614012d4 + 84*part` for parts 0..2. These map to MFX slots 1..3.

The generic and algorithm-specific descriptors refer to the same cells:

| Live1 field, decimal | Generic stream ID | FDRV typed ID | Store offset |
|---|---|---|---|
| 2, mode | `599` | `b1e` (2846 decimal) | `14` |
| 3, cutoff | `59a` | `b1f` (2847 decimal) | `16` |

Generic descriptors describe signed halfwords with nominal range -20000..20000
and default 0. The original writer does not enforce that range. FDRV's later
reader uses its own specialized range/defaults at those same offsets, including
mode 0..2 and cutoff 20..16000 with default 3740.

## Scalar and block write contracts

The scalar writer receives object in r0, raw value in r1 and generic parameter
ID in r2. It uses descriptor width/offset to select the store instruction.
For these halfword fields it keeps the **low 16 bits**, without comparing the
old value or checking a value range. The object's signed-halfword dirty minimum
at +10 and maximum at +12 expand using the **parameter ID**, not the value.
The constructor initializes those markers to 32767 and 0 decimal.

The block starts with a little-endian u16 **ID offset from stream base587**,
then complete field bytes. It is neither a byte offset into the parameter store
nor the logical FDRV field index. For example, the authored payload
`12 00 01 00 e8 03` writes logical mode1 and cutoff1000: start ID `587+12=599`,
then two little-endian halfwords. The original decoder checks each ID against
the virtual stream range and advances by descriptor width.

The bounded copy loop tests remaining count before each field, but does not
establish that a complete descriptor-width value remains. The fixture encoder
admits only complete, consecutive live1 halfwords and rejects unknown fields,
reordered/duplicate block fields and malformed values before CPU access. It does
not claim that the firmware rejects every truncated input. Scalar tests also
admit repeated writes to the same checked field.

| Scalar input, decimal | Stored halfword interpretation | Later FDRV read |
|---:|---:|---:|
| Mode 65537 | 1 | 1 |
| Mode 65539 | 3 | 2, descriptor default |
| Cutoff 66536 | 1000 | 1000 |
| Cutoff 65535 | -1 as a signed halfword | 3740, unsigned typed-read default |

Writing the type header ID587 instead sets a separate flag that requests the
transition path at finalization. The live1 fixture excludes that ID, type changes,
replacement and RAMCLR; this study is not a mechanism for installing an engine.

## Finalization and notification details

The original finalizer always emits a local `21 84` part notification, including
an empty transaction. If dirty minimum equals dirty maximum, it first emits
`21 9f` followed by that single generic ID as a little-endian u16. An identical
value write still dirties its ID and emits the notifications; later buffer
comparison can correctly produce **zero coefficient writes**. The destination
consumer/meaning of the single-ID notification is not generalized here.

The part word's low six bits carry the part index; bits13/14 are cleared and
bit15 reflects the type-change flag. **Bits6..12 are not initialized by this
routine.** The fixture seeds the finalizer's prior stack bytes with `5a` and
verifies that mask `1fc0` survives. The earlier authored `21 84 part 00` input
is one accepted shape, not a claim that stock reserved bits are always zero.
The checked notifier uses the low part bits and transition flag, so those
reserved bits do not change the selected producer in these cases.

Dirty min/max markers remain after finalization. The checked transactions create
and initialize a stream object for each operation; no assumption that a flush
resets a reusable object is made. The finalizer's **second argument** controls
the optional call to `6100447a`. Tests pass zero and explicitly reject entering
that serialization path; no external host packet is generated or transmitted.

## Execution, scope and reproduction

The connected fixture executes the original stream constructor, scalar or block
writer, finalizer, local notifier and existing EFCT handler/descriptor/FDRV path.
Guest writes to parameter RAM are allowed only in the requested field bytes;
the complete part-store image and dirty range are checked against an independent
low16-bit model. Other field effects remain inactive.

**576 cases match 2,160 coefficient writes and 864 local notifications**, spanning
three slots, two mute counts, both enable flags, both writer forms, three modes,
two cutoffs and four changed sets. Eight additional cases verify low16-bit
boundaries/defaults. Repeated identical scalar writes emit two notifications
while producing no coefficient writes. A finalizer with no writes also notifies.

Task signaling, NVIC helpers, coefficient I/O, slope effects and post-apply
hardware routing retain the preceding fixture's controlled boundaries. The
command ring is empty and the handler is invoked as a CPU routine. Real
exception delivery, scheduling, factory lifetime, physical peripherals and
instrument startup do not execute. Reserved stack bits are tracked as observed
data, not used to invent a universal wire format.

Qwen returned a no-tool review in 19.6 seconds. Store truncation and the absence
of value validation were independently confirmed. Its conflation of dirty IDs
with values, null-store/descriptor interpretation, zero-reserved-bit assumption,
argument numbering and merged-neighbor serialization claims were rejected.
No worker code was accepted; listings and detailed outputs stay local.

```sh
python3.13 tools/fantom_parameter_store_study.py local/b0c1a.bin
python3.13 tools/fantom_parameter_store_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_parameter_store.py -v
```

Next identify the incoming caller that chooses the stream object and supplies
the scalar IDs or block payload. Joining that caller to a host frame remains
separate from the local write/finalize/EFCT proof, as do real exclusion,
completion cadence, BMC precision/history, entry/return and safe loading.

Concrete next leads are block/finalizer veneers `01134574/0113457e` and the
scalar/finalizer adapters `61080abc/61080ac4`. The latter add4 to their receiver;
the finalizer adapter loads its second argument as a signed byte from `20081980`.
The follow-up binds the scalar adapters to RTTI `CEZSNDTonePrmSFSub` and identifies
the incoming selector84 block caller. The higher scalar/UI caller and that
serialization flag's runtime value remain open. No external command follows.
