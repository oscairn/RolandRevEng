# Fantom original host scalar edits and routed notifications

2026-11-11. Two original host edit wrappers now execute through transaction
construction, descriptor-bound scalar writes, destruction, registered MFX
callbacks and routed messages. **648 cases match 2,268 captured messages**.
**72 identical-value edits still write and notify**. This extends the
[family callback replay](fantom-host-family-study.md) upstream from a prepared
store to an actual scalar edit. It does not recover the host-to-CORE1 peer.

Inputs retain the pinned mi078 and stripped CORE1 identities checked by the
[host block](fantom-host-block-study.md) and
[CORE1 stream-store](fantom-parameter-store-study.md) tools. Evidence is file and
Capstone analysis plus private Unicorn CPU execution, not REA Evidence records,
live Linux execution or instrument traffic. Raw listings and vendor artifacts
remain local/ignored. No DSP opcode profile is added.

## Recovered wrapper and transaction path

Addresses are hexadecimal; parameter IDs and values below are decimal.

| Original code | Checked behavior |
|---|---|
| `00478d60` / `00478dd8` | Family6/7 wrappers; take a context object, scalar value and parameter ID |
| `00c1c6f0` | Construct a transaction, bind global `0424be78`, family, index0 and context; acquire its parameter scope |
| Wrapper after construction | OR bit1 into transaction byte3, enabling the family's block/range send path |
| `00c1c810` → `00c1b028` | Write the requested scalar using its descriptor; record dirty minimum/maximum ID and modified flag |
| `00c1c728` | Finalize on destruction, dispatch local notification and registered family callback; optionally notify route4; release the scope |

The context byte comes from wrapper-object+8. The replay selects family6/context0
and family7/contexts0 and1, using the three previously bound stores. The actual
wrapper fixes index0. This is not a complete UI event or a physical store-to-CORE1
slot assignment. Multi-write transactions, type replacement, read-only fields and
other families are outside this replay.

The initial transaction has dirty minimum65535, maximum0, modified0 and byte3=8.
The wrapper changes byte3 to10. A successful live1 write marks the exact supplied
ID and modified1. An identical value still traverses the original halfword store
and produces the same notification path. A write guard admits only that selected
two-byte cell; all 84 bytes of all three stores are checked afterward.

## Host clamp differs from the CORE1 stream writer

The shared host writer checks the descriptor's read-only flag, then compares the
signed32 source against minimum and maximum, choosing the nearest bound before
calling the family initializer and storing. The four checked descriptors are
writable halfwords. The generic IDs have bounds -20000..20000; the typed FDRV mode
and cutoff have bounds 0..2 and 20..16000 respectively.

| Authored edit | Host stored value |
|---|---:|
| Generic mode3504, value65537 | 20000 |
| Generic cutoff3505, value65537 | 20000 |
| Typed mode4917, value65537 | 2 |
| Typed cutoff4918, value65537 | 16000 |

These are observed original-code results. The previously checked CORE1 stream
writer instead stores low16 bits: its mode65537 becomes1 before the later typed
reader. Reusing the same visible scalar at different layers can therefore produce
different state. Generic host writes can also exceed typed FDRV bounds; subsequent
typed-reader defaults are a separate step. This fixture does not forward host
messages to CORE1 or run its coefficient producer.

The small clamp model came from a Qwen draft returned in 6.5 seconds. Review
confirmed exact integer/signed32 validation and boundary choices; independent
source checks and original-code comparisons establish its use here. The worker's
asserts were supplemented by independent type, descriptor and CPU tests.

## Ordered local and BMC-output messages

With the optional flag zero, each checked edit routes:

1. **Kind1 to local route0a**, using the originally supplied parameter ID range.
2. **Kind7 to destinationef**, selector6/7, containing the two changed store bytes
   and the descriptor-derived native byte offset.
3. **Kind8 to destinationef**, containing the original selected ID range.

The kind1 and kind8 payload packing agrees in these cases, while their envelope
kinds and destinations are distinct. The original constructors, seven-byte inline
cap, registered family callback and route selector execute. The local route0a
receiver list and BMC output queue are intercepted at their entries.

Destructor `00c1c77c` reads byte `04db0438`. With this byte seeded to128, a fourth
message appears: **kind1 to local route4**, using the generic IDs converted by the
family callback. The flag's actual runtime value, owner and activation conditions
remain unproved. Its address is unrelated to CORE1's separate serialization flag.
The additional route4 message is not evidence of an external transmission.

For typed mode4917 the first local/BMC range identifies4917; the optional local
route4 range identifies3504. Generic3504 remains3504 in both. The existing
[family study](fantom-host-family-study.md) describes the packed relative-ID format
and why equal block bytes do not imply equal range payloads.

The nested parameter scopes produce two intercepted mutex-lock calls and one
unlock call, with the software nesting counter restored to zero. Their pthread
effects are excluded. This does not prove live mutex semantics, listener behavior,
thread scheduling, queue ownership or peer acknowledgement.

## Checks and remaining requirements

The matrix spans three placements, four generic/typed live1 IDs, nine values per
descriptor, two optional-flag seeds and three stack canaries. Values include each
bound and its outside neighbor, an unchanged value, signed32 extrema,65535 and
65537. The initial stores use authored defaults, algorithm85, mode1 and cutoff1000.
Exactly one original halfword write is checked per edit, including the 72 unchanged
stores. The matrix produces 1,296 BMC-output messages, 648 local route0a messages
and 324 optional local route4 messages.

The first store guard compared Unicorn's full reported STRH source register with
an expected halfword and rejected a valid negative write. The guard now compares
the low16 stored bits and independently checks final memory. This was a fixture
comparison error, not a firmware or instruction-emulation defect.

Captured native messages are copied at receiver/queue boundaries, then restored
for original serialization after the original temporaries expire. The wrapper,
writer and destructor execute continuously; receiver/queue consumers do not.
Memory copies and mutex effects remain controlled as in the preceding fixtures.
No physical device, firmware update, kernel call or live transport is involved.

```sh
python3.13 tools/fantom_host_write_study.py local/mi078 local/b0c1a.bin
python3.13 tools/fantom_host_write_study.py local/mi078 local/b0c1a.bin --execute-arm64
PYTHONPATH=tools:tests python3.13 -m unittest test_fantom_host_write_study test_fantom_host_family_study test_fantom_host_block_study test_bmc_ipc test_core1_sysex -v
```

Next bind the local receiver/queue registrations and drain behavior, and seek a
readable peer or saved traffic for the host-to-CORE1 conversion. Independent new
DSP encoding contexts remain useful offline work. Physical slot mapping, silicon
precision/history, interrupt timing, entry/return and safe engine loading remain
unresolved; the 18 exact DSP execution profiles are unchanged.
