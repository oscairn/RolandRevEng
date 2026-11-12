# Host routes, CORE1 SysEx and the remaining bridge

The [local range-receiver study](fantom-host-receiver-study.md) now executes stock provider registration, coalescing and drain for families6/7. Its queued emitter statically constructs kind2 SysEx routed to08, distinct from immediate kind7/8 blocks; the external peer remains unproved.

The [host family follow-up](fantom-host-family-study.md) now executes registered family6/7 callbacks, original store getters and paired block/range routing. The descriptor match narrows the parameter domains without proving the missing peer.

The bounded [host block replay](fantom-host-block-study.md) now executes the original kind-7 constructor/serializer across 108 cases and exposes metadata in saved captures. Padding retains seeded memory. Host-to-CORE1 translation remains unresolved.

Follow-up: [service initialization and reply frames](core1-service-startup-mmio.md)
closes the startup-table activation edge below for both supplied builds. It also
refines the exact count/remainder and saved-register bounds; the external bridge
remains unproved. [Host version identities](host-version-and-upstream-crosscheck.md)
recovers five component slots and their actual version strings without assigning
unproved physical chip identities. The original bounded investigation follows.

2026-11-10. Follow-up to [host transport](host-transport-study.md) and
[CORE1 receive path](core1-receive-and-test-controls.md). This is offline static
analysis with Apple's `objdump`, Python and Capstone 5.0.7. REA's native provider
was unavailable in the preceding investigation; these are ordinary file-tool
observations, **not REA Evidence records or runtime observations**. No Roland
executable or firmware was run, no device opened and no message transmitted.

The substantive new finding is a CORE1 SysEx handler that reads and writes an
MMIO offset window based at `0x41100000`. That window includes the known DSP
program apertures. It is more than a debug label, but it is not yet a usable
host loader: the ttyGS0 peer is missing, the handler bypasses the DSP manager,
and its read-reply construction has a concrete stack-size discrepancy.
A managed resident bridge remains a possible design, not a demonstrated necessity
for every raw transfer and not a deployable artifact.

**Existing shell conflict remains:** the prepared update shells use `/dev/ttyGS0`,
which the normal application opens for BMC IPC. Concurrent shells can consume IPC
bytes and inject shell text. The packages were not changed. Nothing in this study
establishes a spare serial port or makes those payloads suitable for normal operation.

## Artifact and address scope

| Input | SHA-256 |
|---|---|
| `local/mi078`, 61,181,491 bytes | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` |
| `local/b0c1a.bin`, header-stripped bmc0 CORE1 | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |
| `local/bmc0_MI078_C0A_up.bin` | `0ecb9c16adf67349c0f1efd6e8c257465972690a3ca1b5e5af29dbb1f2c480c9` |
| `local/bmc1_MI078_C0A_up.bin` | `2929219309206f7f9ac0abab429a6a20e5eff45c6caf7c417af197f2275911f5` |

`00……` addresses below are mi078 ELF virtual addresses, not file offsets.
`011……` and `610……` addresses are bmc0 CORE1 runtime addresses from the mapping
in `tools/core1.py`. Only that CORE1 build was traced; bmc1 equivalence is unproved.
Vendor files are preserved symlinks. Detailed disassembly and scratch searches stay
in this worktree's ignored `local/` directory.

## 1. Outer routing: endpoint, message kind and service are separate

`00be4270(route, message)` writes `route & 255` to message byte 2, except that its
argument `0x0b` means reuse the existing byte 2. The high-nibble and exact-value
comparisons then select one of the destinations below. `00be4418(message)` repeats
the dispatch using existing byte 2. Neither routine converts a route to a DSP index.

| Actual destination byte | Dispatch edge in `00be4270` | Observed receiver |
|---|---|---|
| `e0..ef`, `08`, `0d`, `0e`, `75`, `81`, `91`, `a1`, `b2`, `c8`, `d8` | `00be43a4` → `00be26a8` | BMC output object `041145e0`; queue → serializer → ttyGS0 |
| `03` | `00be43d0` → `00bfe768` | Local object `0424bb20` |
| `04` | `00be42e8` → `00bfe640` | Same local object, different method |
| `09` | `00be43e0` → `00c2c998` | Local MIDI routing object `04db8b90` |
| `0a` | `00be43f0` → `00be4620` | Local registered-receiver list at `0412efe8` |
| `0c` | `00be42c4` → `00c2d3c8` | Local object `04db8c20`, which can subsequently reroute |
| `61` | `00be431c..4380` → `00ce9180` | Kind-3 getter followed by a local sequencer receiver, argument `0x40` |
| All other byte values | return | No receiver in this dispatcher |

For example, `00c2a3c0` constructs a kind-3 four-byte control-change word whose
first byte is `0x2b`, status is `0xb0 | channel`, and last byte is zero. It sets
outer byte 1 to `0x60`, routes the same message to `e1`, then to local `0a`.
This is ordinary MIDI routing, not a memory-write operation. At `00c2c998`,
non-kind-3 messages fan out to `e1`, `0a` and `0d`; kind 3 has additional per-channel
routing/rewrite logic. A queue destination therefore does not identify the eventual
CORE1 word, subsystem or physical chip.

Another concrete counterexample is `00c2ccd8`: it constructs a kind-3 word with
byte 0=`0b`, byte 1=`b0 | channel`, and bytes 2–3=`7b 00`. Here `7b` is in the MIDI
controller position; CORE1's system callback tests **byte 1** for command `7b`.
The shared number does not connect the handlers.

Byte 1 is consistent with a source endpoint: constructors repeatedly set it to
`0x60`, while reply handlers compare it to `e1` or `e2`. That is an **inference from
reciprocal uses**, not a recovered enum. `bmc_ipc.py` calls it `byte1` to preserve
that distinction. Byte 3 is an actual service selector for kind 9, and a different
metadata field for other kinds. No universal meaning is assigned across kinds.

The version client independently distinguishes `e1` and `e2`: service 4 requests
at `00cf99c0..9be0` pair payload byte 1 or 4 with each destination. Reply handler
`00cf9c40` checks selector 4 and source byte 1, stores five-byte result slots, and
decrements an outstanding counter at object+`0x20`. `00cf9fe0` waits on that counter
with a finite retry loop before comparing version strings. This proves distinct
logical peer selectors. Mapping `e1/e2/ef` to physical BMC0/BMC1/broadcast or mapping
all small routes to CORE0/CORE1 is still unresolved; the arithmetic nibble pattern
alone is insufficient. The `0x60` endpoint cannot be called a particular BMC core.

### Message-kind evidence

| Kind (`byte[0] >> 1`) | Constructor/getter or receiver | Bounded interpretation |
|---:|---|---|
| 0 | Base initializer `00be3120` | Default empty/base message; no service meaning recovered |
| 1 | `00be2998`, setter `00be29e8`, getter `00be29f8` | Requests eight bytes through the inline setter, which caps at seven; do not infer an eight-byte wire payload |
| 2 | `00be3d98`; input `00be1b7c..1cfc` | Buffer with byte-3 low-nibble metadata; source `a1` and metadata 1 delivers bytes/count to `00bcef48` |
| 3 | `00be2a60` / `00be2ac0`; input `00be1b3c` | Four-byte MIDI/UMDW-style value; source and embedded high nibble affect handling |
| 4 | No specialized constructor established in this pass | Accepted by outer kind bound; meaning unresolved |
| 5 | `00be2ac8` / `00be2b28`; input `00be1bbc` | Four-byte value passed to `00c111a0`; not established as a program operation |
| 6 | `00be2b30` / `00be2b90` | Four-byte value; generic receive/logging path inspects its low five bits |
| 7 | `00be3e38`, wrapped by `00be2b98` | Structured block: u16 + two u8 metadata bytes and variable data; see below |
| 8 | `00be2bf8` / `00be2c58` | Also requests eight bytes through the seven-byte-capped inline setter; semantics unresolved |
| 9 | `00be2968`, wrapped by `00be2c60`; input `00be1ae4` | Service-selected envelope; selected services have real reply consumers |

Kinds 1 and 8 are useful counterexamples: constructor argument sizes are not proof
of transmitted size. The shared setter `00be3450` makes the seven-byte cap explicit.

## 2. Serialization, ownership and completion

The existing wire layout remains valid: fixed messages are 12 bytes; variable
messages emit native bytes 0–7, native bytes 16–19, a little-endian u32 payload length,
then payload bytes. The native pointer at object+8 is omitted. Thus the variable
wire prefix's last four bytes are metadata, **not the length or a pointer**.

| Evidence | Actual length/ownership behavior |
|---|---|
| `00be3528` | Stores up to seven bytes inline when the force-variable argument is zero; otherwise allocates `N+8`, stores reference count at allocation+0 and length at +4, copies bytes at +8 |
| `00be31e8`, `00be32b8` | Copy variable message fields and retain the allocation via `00bdf9b8`; release prior allocation when replacing it |
| `00be3180` | Releases variable storage; deletion occurs when the shared reference reaches zero |
| `00be3800` / `00be3928` | Queue copies use 24-byte native slots and those retaining assignments; dequeue resets the consumed slot |
| `00be26a8` | Only queues/wakes output while output object's byte `0x150` is nonzero; otherwise returns |
| `00be2448` | Drains queue, calls serializer `00be1120`, then flushes the transmit buffer when drained |
| `00be2510` | Copies serial bytes into a `0x1000`-byte output buffer, invoking callback on a full buffer |
| `00be24e8` → `00bdf988` | Calls `write` on ttyGS0 fd; callback reduces result to sign; this path does not prove full-write retry or peer acknowledgement |

Deleting a temporary native object immediately after routing is consistent with
retained queue ownership. It does not mean delivery is synchronous. Serializer
completion, local queue consumption, successful POSIX write, service reply, DMA
completion and DSP execution are distinct events. No general request ID or ack field
was established in the outer header. Individual services implement their own state.

`00be3e38` makes kind 7's split explicit. For data length <=3 it stores a u16 and two
u8 metadata fields followed by data in the inline payload. For larger data it writes
those four metadata bytes at native object+16 through `00be3758`, and forces variable
storage for the data. Example `00c1f964..9b0` supplies selector `0x14`, caller-derived
u16, two zero metadata bytes and `0x660` data bytes, wraps it and routes to `ef`.
Other callers use selector `0x91` with `0x410` bytes. These are typed parameter/block
transfers; there is no demonstrated DSP program address in these fields and no
recovered manager upload edge. Naming them a coefficient/program loader would exceed
the evidence.

### Service request/reply table

These rows are distinct paths, not a complete application protocol inventory.

| Service / form | Construct and send | Response / completion | What it does and does not prove |
|---|---|---|---|
| kind 9, selector 4 | `00cf99c0..9be0`: one-byte requests to `e1/e2`, outer byte 1=`6f` | `00cf9c40`, result slots and outstanding counter; `00cf9fe0` finite polling | Version-query client; not program readback |
| kind 9, selector 6 | `00be9b08`, `00be9f08`: caller bytes/count, byte 1=`60`, destination `e1` | Registered callback `00be9fa0` requires kind 9/source `e1`/selector 6 and feeds bytes/count through `00be5388` → `00be94c0` → `00be9430` | A byte-stream service with parsing; arbitrary DSP memory meaning not established |
| kind 9, selector `0d` | `00c0f140` / `00c0f260`: three signed-halfword fields; first has bit 7 set/cleared; optional tail at +8; destination `e1` | `00be1c3c` recognizes field low-seven-bit 6/7 and calls `00c0f5d0`; that handler requires source `e1`/selector `0d`, then updates client fields via `00c0f4f8`/`00c0f380` | Expansion operation/status client. The companion command writer `00c0e808` references `CmdExpInstall`, `CmdExpUninstall`, `CmdExpDelete` and `EXEC_TYPE.txt`; not render-code upload |
| kind 9, selector `0e` | `00c0f9d0` / `00c0fb00`: analogous halfword/optional-tail messages, caller-selected destination; `00c17170` supplies command 6 and route `ef` | Registered callback `00c0fe18` requires source `e1`/selector `0e`, calls `00c0fd40`; client status checks remain service-specific | Sample/operation-related transport; complete command semantics remain unresolved |
| kind 9, selector `0f`, command 1 | `00d18590`, send sites `00d18638..688`: seven inline bytes (u32 block index, u16=1, u8=1), byte 1=`60`, route `e1` | Queued responses with metadata command 2 must have exactly `0x20000` bytes; `00d18818..828` copies that many; command 3 handles negative result. Counter and timeout at `00d18708..780` | A real large-block readback client, associated with `CUserWaveIFServ`, not arbitrary CORE1/program addressing |
| kind 9, selector `0f`, commands 4/5 | `00d18dc4..e7c`: command 4 block request, then forced-variable `0x20000` data with metadata command 5 | Same queued client family with command-specific response checks | Large-block writes exist; program-memory destination is not established |
| kind 9, selector `0f`, command 7 | `00d190c8..154`: metadata command 7 and two u32 fields plus optional bytes | Response command 8 returns u32 status at `00d19234..258`; timeout returns -7 | Another bounded service exchange, not a generic function-call ABI |
| kind 3 / ordinary MIDI | `00c2a3c0`, four-byte control-change construction, route `e1`, local `0a` | Input worker gets four bytes via `00be2ac0`; special source cases feed `00c2a128` | No arbitrary program write can be inferred from the four-byte shape |

The selector-`0f` service has independent RTTI/data linkage: name
`15CUserWaveIFServ` at `016899d8` → typeinfo `016899f0` → vtable address point
`01689a18` → callback `00d195b8`. The callback checks kind 9/selector `0f`, gets
command metadata from object+16 for variable messages or payload+4 for inline ones,
and queues most replies at receiver+`0x18`. Registration `00d19340` inserts the
same global receiver at `0db94270` into list `0412efe8`; routing `0a` invokes each
registered receiver's first virtual method through `00be4620`.
That closes the host-side response edge without assuming that all input returns
through the input worker's specialized branches.

## 3. CORE1 SysEx: actual handlers, including raw MMIO

This part is independent of the missing ttyGS0 peer. It begins with an already
received CORE1 ring word; no outer-host frame is assumed to reach it unchanged.

`0111ea24` dispatches on the word's first-byte high nibble. The jump-table byte for
1 selects `0111eae2`. Except low nibble `f` (realtime handling), this path calls both
SysEx assemblers, on objects `200950f0` and `20094ee4`, using `0111f10c`.
The assembler accepts low nibble 4 as a three-byte body and 5/6/7 as final one/two/
three-byte pieces, with a 512-byte buffer and overflow state. Its completed-message
virtual call passes `r1=buffer`, `r2=byte count` to vtable+4.

The constructor/initializer body at `0111ed24` sets up both concrete vtables:

| CORE1 object | Installed vtable | Completed-buffer callback |
|---|---|---|
| `20094ee4` | `6117bf3c` | Thumb pointer `01135de1`, code `01135de0` |
| `200950f0` (`20094ee4 + 20c`) | `61177dac` | Thumb pointer `011351a1`, code `011351a0` |

These are concrete construction and callback references, not proof that every boot
activates the objects. The initializer has a relative-pointer candidate at
`6123ff70` resolving to `0111ed25`; a complete initializer-table/startup walk remains
unperformed. No runtime vtable snapshot is available.

`011351a0` calls validator veneer `01126a48` → `01134c68` → `6102d2bc`, which checks
length >=11 and header `F0 41 10 4E`. On success it repacketizes the same bytes into
high-nibble-1 words and passes each to `01126d2e`. This is a forwarding/output side
within CORE1, not proof that Linux can reach it or that a read reply reaches Linux.

`01135de0` tries these handlers in order:

| Form | Recognition and subsequent dataflow | Recovered scope |
|---|---|---|
| Exactly 9 bytes, `F0 41 60 … F7` | `01126658` reconstructs four bytes from four low-seven-bit bytes plus a four-bit high-bit group; `01135df0` calls `0110a5a6` with the reconstructed word | Internal-word wrapper. High-group bit 3 supplies word byte 0 bit 7, bit 2 supplies byte 1 bit 7, etc. Only high-nibble-zero words subsequently select the system-command path |
| Exactly 8 bytes, `F0 41 50 … F7` | `011266ce` consults table `610a0e9f`, combines two seven-bit value bytes, forms a packed word; caller changes its first-byte high nibble to 1 and calls `0110a5a6` | Table-driven parameter conversion; table values affect scaling. Not decoded by the new offline tool |
| Exactly 8 bytes, device-specific third byte | `01135014` veneer → `6101469c`; requires `F0 41`, third byte from `61014ba0`, trailing `F7`; builds a four-byte control record for `6101460c` | Another stock control path; not automatically a development/program entry |
| `F0 41 10 4E`, command `11` | `01134f1a` veneer → `6102d604` → `6102d4ac`, branch `6102d5b8`, helper `6102d2e6` | Actual MMIO read and encoded reply, detailed below |
| Same header, command `12` | `6102d4ac`, write body `6102d502..5b4` | Actual aligned 32-bit MMIO writes; no manager call in that body |
| Same header, other command byte | `6102d4f4..4fe` | Returns on this path |

The firmware handlers do not validate every seven-bit/high-group field the offline
decoder validates. This decoder intentionally recognizes canonical saved records;
it is not a byte-exact emulator of malformed-input behavior.

### MMIO service boundaries

`6102d4ac` checks minimum length 11, the four header bytes and that the first address
byte's upper nibble is zero. It dispatches on command byte at message+4. For the read
branch it further requires length >=15, copies the tail into global scratch object
`2009f330` (length at +0, bytes at +4, zeroed capacity `0x100`), then calls
`6102d2e6`. The write branch requires length >=12 and uses the same scratch object.
Neither branch checks the final marker/checksum in this body. The enclosing SysEx
assembly is still a separate boundary.

The read helper:

- Combines four seven-bit address groups; masks to `0x01ffffff`; rejects non-four-byte
  alignment. Effective address is `0x41100000 + masked_offset`.
- Decodes a four-group byte count, returns below 4 and caps above 64. It reads complete
  32-bit words, reducing count by 4; a nonmultiple-of-four remainder is not read.
- Builds a reply with the same four-byte prefix, response command `13`, the original
  encoded offset, eight high-to-low nibbles per loaded word, a negated additive
  seven-bit checksum over address/data, then `F7`.
- Sends the constructed buffer/count via `6107773e` → `0111f0be`, which selects
  output route argument 3 in `0111efc2`. The physical destination of that route is
  not established here.

The write body reconstructs one 32-bit value per eight nibble bytes and stores to
`0x41100000 + offset`, incrementing by four. It performs writes only while masked
offset <`0x01000000`; offsets above that threshold consume input without the store.
It checks four-byte alignment for full words. No explicit service acknowledgement,
stock manager exclusion, segment capacity check, DMA wait, rollback or audio mute
appears in this write body. Omitted manager calls are bounded to this traced path;
they do not prove no coordination elsewhere in the system.

The mathematical overlap with the driver is real: program apertures
`41480000..41980000` correspond to offsets `00380000..00880000`, and MDSP
`41260000` to offset `00160000`. These satisfy the write-path window bound. Driver
`0112f92a` independently loads its program-aperture table at `0113a954`.
This establishes address-window overlap, **not a tested loading method, host route,
correct program ownership or safe timing**. It does not provide Cortex-M code
execution or writes to arbitrary SRAM/ERAM where a resident bridge would live.

There is also a concrete read-reply size problem. `6102d2e6` pushes `{r4,lr}` and
reserves `0x50` bytes. It emits `11 + 8*floor(count/4)` bytes. Count 32 gives 75;
36 gives 83; 40 gives 91; the cap of 64 gives 139. Consequently the visible write
sequence reaches beyond the local reservation and into the saved frame for allowed
larger counts. This is a static size discrepancy, not an executed corruption test.
Do not turn the 64-byte clamp into a presumed safe read limit. No live experiment
or command sequence is proposed here.

## 4. Where the external proof stops

The proven host endpoint ends at ttyGS0 `write`; the proven CORE1 endpoint begins
with IRQ6 reading 32-bit ring entries at `e0043038`, using indices `e004300c/10`.
The missing implementation must:

1. Receive/reassemble the 12-byte/variable host envelopes, including metadata and
   payload ownership in its own address width.
2. Resolve outer destinations such as `e1/e2/ef` and kinds 2/3/7/9 to actual cores,
   endpoints and services; perform any UMDW byte/high-nibble rewrites.
3. Produce CORE1 ring words and notify the receiving core, or take another service
   path. Ordinary MIDI may be repacketized; matching four-byte shapes do not prove
   a memcpy into the ring.
4. Bring CORE1 output words/replies back to an outer kind, source/destination and
   selector accepted by the relevant Linux receiver.

None of these four edges was recovered from the available host or CORE1 code.
A fixed SysEx word wrapper makes one CORE-local conversion concrete, but cannot fill
in the peer. In particular the ordinary host example's embedded byte `2b` selects
CORE1 high-nibble 2 if forwarded unchanged; it does not demonstrate the high-nibble-1
SysEx ingress route or high-nibble-zero system-command route.

Encrypted CORE0 is a plausible place for part of the peer. Both supplied C0A
containers declare crypto enabled, mode 2, key index `0xb6`, and destination
`60000000` in the existing [header inventory](../evidence/core0_headers.json).
Their implementation is opaque here. That is a precise missing-artifact dependency,
not proof that CORE0 implements every service or that the serial cable terminates
there. No decryption, key guess, firmware packaging or target probe was attempted.
An owned decrypted peer image or an existing bidirectional traffic/ring capture is
needed to settle this route. Neither was available.

## 5. Loading decision and minimum resident interface

Answered: host routing dispatch, variable storage lifetime, several actual service
clients, two CORE1 SysEx callbacks, an internal-word conversion, and a raw MMIO
read/write handler including address-window overlap. Partially answered: logical
peer selection and request/reply routing. Unresolved: physical chip mapping, the
external peer, safe host-to-DSP loading and the resident entry mechanism.

The evidence does **not** justify saying firmware has no memory service. It has the
CORE-local MMIO handler above and separate Linux block clients. It also does not
justify saying either is a usable end-to-end DSP loader. A resident bridge could
provide missing manager coordination, but it cannot presently be installed through
a proved mechanism. The MMIO window is not a demonstrated ARM-code injection path.

If a managed CORE1 bridge is eventually justified, the minimum proposed ABI is:

| Operation | Required contract; design requirements, not recovered wire opcodes |
|---|---|
| Identify | ABI version, exact firmware identity, BMC/core identity, supported DSPs and owned segment capacities; reject unknown builds |
| Read | DSP + identified program/segment + byte offset/count; explicit byte order, alignment and bounds; chunked data, request ID and terminal status |
| Stage write | Same bounded identifiers, expected current program identity, total length and integrity value; staged bytes stay separate from running program until validation |
| Commit / restore | Execute on the stock manager's permitted task, join its actual exclusion/transition protocol, validate stock context, complete driver DMA and read back before reporting completion; preserve a known restore context |
| Coefficient access | Existing symbol/segment/width form, with the stock manager's conversion and ownership rules; no arbitrary address writer |

All requests need bounded lengths, build-specific capabilities and explicit error/
completion status. A staged request must be discardable without changing the running
graph. An arbitrary function-call service, general memory shell, guessed mode-0/2
stop/run pair and unbounded direct aperture writer are unnecessary for this ABI.
Its implementation still depends on the kernel/audio ABI study for valid scheduling,
transition and mute requirements. No opcode numbers, upload packet generator or
purported standalone resident payload was produced.

The next concrete offline experiment is to obtain the actual peer implementation
or a previously recorded two-way capture and correlate one known stock MIDI event
and one stock version reply through the envelopes. Only after the two directions and
endpoint transformations match should a separate owned-hardware plan consider
CORE1's existing services; the stack discrepancy and manager/lifecycle requirements
must be resolved first. This study provides no speculative upload/probe commands.

## Reproduce and verify

The following commands only read local artifacts. From the worktree, use a Python
interpreter with Capstone 5.0.7 for `core1.py`; the IPC/SysEx decoder tests use only
the standard library.

```sh
shasum -a 256 local/mi078 local/b0c1a.bin local/bmc0_MI078_C0A_up.bin local/bmc1_MI078_C0A_up.bin
/usr/bin/objdump -d --start-address=0xbe4270 --stop-address=0xbe4418 local/mi078
/usr/bin/objdump -d --start-address=0xbe2448 --stop-address=0xbe2510 local/mi078
/usr/bin/objdump -d --start-address=0xbe31e8 --stop-address=0xbe36c0 local/mi078
/usr/bin/objdump -d --start-address=0xbe3e38 --stop-address=0xbe3f30 local/mi078
/usr/bin/objdump -d --start-address=0xcf99c0 --stop-address=0xcf9d84 local/mi078
/usr/bin/objdump -d --start-address=0xd18590 --stop-address=0xd1884c local/mi078
/usr/bin/objdump -d --start-address=0xd19340 --stop-address=0xd19650 local/mi078
python3 tools/core1.py local/b0c1a.bin --address 0x111eae2 --size 0x30
python3 tools/core1.py local/b0c1a.bin --address 0x111ed24 --size 0x24
python3 tools/core1.py local/b0c1a.bin --address 0x111f10c --size 0x11a
python3 tools/core1.py local/b0c1a.bin --address 0x1135de0 --size 0x4c
python3 tools/core1.py local/b0c1a.bin --address 0x1126658 --size 0xf8
python3 tools/core1.py local/b0c1a.bin --address 0x6102d2bc --size 0x176
python3 tools/core1.py local/b0c1a.bin --address 0x6102d4ac --size 0x160
python3 -m unittest discover -s tests -p test_bmc_ipc.py -v
python3 -m unittest discover -s tests -p test_core1_sysex.py -v
python3 -m unittest discover -s tests -v
```

Small data-reference and size checks, without copying firmware/program bytes:

```sh
PYTHONPATH=tools python3 - <<'PY'
from core1 import Core1
c = Core1('local/b0c1a.bin')
assert c.u32(0x6117bf3c + 4) == 0x01135de1
assert c.u32(0x61177dac + 4) == 0x011351a1
relative = c.u32(0x6123ff70)
assert (0x6123ff70 + relative) & 0xffffffff == 0x0111ed25
apertures = [c.u32(0x0113a954 + 4*i) for i in range(7)]
assert apertures == [0x41480000, 0x41580000, 0x41680000, 0x41780000,
                     0x41880000, 0x41980000, 0x41260000]
assert all(0 <= address - 0x41100000 < 0x01000000 for address in apertures)
assert [11 + 8*(n//4) for n in (32, 36, 40, 64)] == [75, 83, 91, 139]
print('Vtables, relative-pointer candidate, aperture overlap and size arithmetic match')
PY
```

`tools/core1_sysex.py` reads **one existing raw SysEx file** and accepts only the
nine-byte internal-word wrapper or command-13 debug read reply. It validates
canonical seven-bit bytes, four-byte-aligned offsets, exact word/nibble boundaries and read-reply checksum;
unsupported forms fail closed. It neither encodes a request nor opens a device.
A decoded reply is not evidence it was captured on real hardware. Tests use original
synthetic records with asymmetric high bits, nibble order, wrong checksums,
truncation, noncanonical values and the 16-word bound. The 8-byte table-dependent
parameter wrapper and incoming write/read requests are deliberately unsupported.

`tools/bmc_ipc.py` now exposes byte 1, destination and selector alongside its original
opaque prefix/payload. Existing frame boundaries and endian behavior are unchanged.
No automatic association between these outer frames and CORE1 SysEx is made.
