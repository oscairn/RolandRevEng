# Fantom host MFX families and paired range notifications

Follow-up: [original host scalar edits](fantom-host-write-study.md) now execute two edit wrappers through the writer, destructor and these callbacks. The 648 cases distinguish descriptor clamping, identical-value notifications and an optional local route4 notification.

2026-11-11. Host families 6 and 7 now have source-bound store getters and registered
callback replays. **432 matrix cases produce 216 block/range pairs and 8,928 block
data bytes**, with another three force-full cases checked separately. All 48
generic MFX and 26 FDRV typed descriptors match their CORE1 counterparts in the
five fields compared. This narrows the host parameter model; the missing peer's
translation into [CORE1 selector84](fantom-parameter-stream-study.md) remains open.

This uses the pinned mi078 and stripped CORE1 images from the
[host block study](fantom-host-block-study.md) and
[stream-store study](fantom-parameter-store-study.md). Both source identities are
checked before execution. Evidence is file/Capstone analysis and isolated Unicorn
CPU execution, not REA Evidence records or instrument observations. Vendor bytes,
listings and scratch traces stay local/ignored.

## Descriptor correspondence

Parameter IDs below are decimal; addresses and explicitly prefixed values are
hexadecimal. Host descriptors at `0138b3d0` have 16-byte stride. CORE1 descriptors
at `611616b8` have 20-byte stride. Every compared tuple consists of default,
minimum, maximum, store byte offset and native value width. The host's other
encoding flags are not claimed equal to the CORE1 record.

| Domain | Host IDs | CORE1 IDs | Records compared |
|---|---:|---:|---:|
| Generic MFX range | 3486–3533 | 1415–1462 (`0x587–0x5b6`) | 48 |
| Algorithm85/FDRV typed range | 4911–4936 | 2840–2865 | 26 |
| Checked live1 mode, generic | 3504 | 1433 (`0x599`) | Included above |
| Checked live1 cutoff, generic | 3505 | 1434 (`0x59a`) | Included above |
| Checked live1 mode, typed | 4917 | 2846 | Included above |
| Checked live1 cutoff, typed | 4918 | 2847 | Included above |

The host IDs exceed the corresponding CORE1 IDs by **2,071** in these two ranges.
That observed shift is not a universal parameter-ID conversion rule. The original
host algorithm85 table at `01613b40 + 4*85` supplies typed bounds 4911–4936.
The checked generic/typed live1 cells have offsets20/22 decimal (`0x14/0x16`).

The generic descriptors cover 80 bytes of an 84-byte store: the final generic
halfword ends at byte80. A full generic callback sends those 80 bytes; it does not
serialize the four trailing bytes merely because the allocation stride is84.

## Actual registrations and store selection

The host's table at `013844c8` binds its descriptor, range and family tables.
Startup `00c07f64` calls constructor `00c1aa60`, which copies that 64-byte binding
into global `0424be78`. The replay executes that constructor directly; the wider
startup and thread launch are outside this fixture.

| Host family/context | Registered getter | Store selected | Registered callback |
|---|---|---|---|
| 6 / checked context0 | `00c00538` | `0424ce9c` | `00c08858` |
| 7 / context0 | `00c00548` | `0424cef0` | `00c08a68` |
| 7 / context1 | `00c00548` | `0424cf44` | `00c08a68` |

These three selected stores are contiguous with 84-byte stride. Family6's getter
returns a fixed address; family7's getter uses its low-eight-bit context with that
stride. The latter has no context-bound check in the getter. This replay's three
placements do not establish a physical BMC identity, a complete permitted context
range or which CORE1 slot each host store controls.

The callbacks read the store's algorithm through the original Cff parameter scope,
convert generic/typed ranges, update their status record, and optionally invoke
the generic block/range sender `00c02010`. Original scope bookkeeping increments
and restores its nesting counter. Mutex operations are intercepted; this is not
proof of exclusion or correct scheduling in a live process.

## Callback flags and paired output

For the checked status record, byte3 bit0 requests the full generic range, and
byte3 bit1 enables sending. A separate bit0 at status+0 also forces the full range.
All four byte3 combinations are tested; no-send cases still compute the reported
range. Typed live1 IDs4917/4918 convert to generic IDs3504/3505 in the status record.
The sender still receives the selected original IDs for the specific-range case.
An initial model reversed the conditional-select interpretation of bit0; a register
trace identified that mistake before the successful matrix. No firmware change
or emulator-instruction defect was inferred.

When enabled, the original helper constructs and routes two messages in order:

1. **Kind7 block**, selector6 or7, destination `ef`: metadata u16 is the caller's
   index, metadata byte2 is context, metadata byte3 is the first descriptor's
   native byte offset. Data is the complete descriptor-derived byte range.
2. **Kind8 range notification**, destination `ef`: seven inline bytes produced by
   `00be3f30` and wrapper `00be2bf8`. The wrapper's eight-byte request is capped to
   seven by the original inline setter.

The seven notification payload bytes are:

```text
u32 little endian: family[9:0] | index[13:0]<<10 | context[7:0]<<24
byte4:             (first_ID - family_base) >> 4, low 8 bits
byte5:             (last_ID  - family_base) >> 4, low 8 bits
byte6:             first_relative low nibble | last_relative low nibble << 4
```

For both checked families the base is3486. The block retains all 16 index bits;
the notification retains only14. This is observed truncation, not an inferred
valid caller-index range. Header source/selector fields initialized to zero are
not assigned a universal transport meaning.

For family7, index65535, context1, the authored specific ranges yield:

| Input IDs | Kind7 metadata offset/data bytes | Kind8 payload hex |
|---|---|---|
| Generic3504–3505 | Offset20, `01 00 e8 03` | `07 fc ff 01 01 01 32` |
| Typed4917–4918 | Offset20, `01 00 e8 03` | `07 fc ff 01 59 59 87` |

The same underlying bytes therefore do **not** imply identical notification IDs.
These examples come from synthetic fixture state; they are not captures or commands
sent to a Fantom. CORE1's received generic-ID-relative prefix and internal local
notifications remain distinct formats. A peer must perform actual translations;
this study does not replace that missing code with guessed arithmetic.

## Executed scope, checks and remaining work

The matrix spans the three placements, indices0/65535, three stack canaries, six
specific generic/typed ranges and all four byte3 flags. The store is prepared with
authored descriptor defaults, algorithm85, mode1 and cutoff1000. The original host
scalar writer and upstream UI/MIDI event are not executed. Three separate cases
force a full update through status+0.

Original code executes the global binding constructor, registered callbacks,
parameter scopes/readers, family getters, typed-to-generic conversion, block and
range constructors, retaining message wrapper, route selection, temporary message
destructors and serializer. At the output-queue entry the fixture saves the native
message and copied payload. Original temporaries are then destroyed and released;
private snapshots are restored later for original serialization. This is a bounded
queue boundary, not continuous execution of the output worker or proof of queue
retention/concurrent ownership.

Allocation, reference-count helpers, free, memcpy, pthread mutex effects and the
output queue are controlled/intercepted. The fixture poisons freed private storage
and checks allocations, releases, store invariance, nesting counter restoration,
message order and both decoded payloads. No target process, external device,
physical interrupt or host-to-CORE1 transport executes.

```sh
python3.13 tools/fantom_host_family_study.py local/mi078 local/b0c1a.bin
python3.13 tools/fantom_host_family_study.py local/mi078 local/b0c1a.bin --execute-arm64
PYTHONPATH=tools:tests python3.13 -m unittest test_fantom_host_family_study test_fantom_host_block_study test_bmc_ipc test_core1_sysex -v
```

Qwen returned a no-tool draft in14.3 seconds. Its nibble layout was corroborated;
its header lost the family and misplaced index bits, and its validation accepted
booleans. That draft was rejected. The independent model and exact-byte tests were
checked against the original paired route and serialization.

Next trace an original host scalar-write transaction into these registered
callbacks, and search readable comparison-peer implementations for this exact
block-plus-notification format. Live endpoint transformations and host-store to
CORE1-slot assignment remain unresolved. No DSP opcode profile is added; silicon
precision/history, physical scheduling, entry/return and safe loading remain open.
