# Stock CORE1 task context and the remaining external peer

2026-11-10. The host-to-CORE1 peer remains missing from the readable artifacts.
This pass closes a different, necessary edge: the stock receive and assignment
callbacks are registered to concrete **software-triggered NVIC interrupts**.
They are not established OS threads. Their priority values and queue gates make
the execution context relevant to any future managed engine entry.

These are offline file/disassembly observations using Python 3.13.7, Capstone
5.0.7 and Apple's objdump, not REA Evidence or runtime observations. No firmware,
Linux target executable, patcher, probe or device command was executed.

## Inputs and scope

| Input | SHA-256 |
|---|---|
| Fantom bmc0 stripped CORE1, `local/b0c1a.bin` | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |
| Linux `local/mi078` | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` |
| Retained modified `_DATA_FNTM0` archive, 385,464,320 bytes | `b32d0b363d67ec83ae1d8e47b709419475dfb896050c4c10e2500d43dd09ef0c` |

CORE1 addresses use the existing ITCM/ERAM mapping. Host addresses are ELF virtual
addresses. The retained Linux archive is the existing local shell-modified package,
not a new official stock download or the instrument's complete installed filesystem.
Its executable hashes match the preceding transport study. The modified startup
script is not used as evidence of stock external transport behavior.

## Application setup installs RXDT and ASGN

The [startup study](core1-service-startup-mmio.md) already connects reset, scatter
loading and runtime entry. Continuing that compiled path:

| Call site | Target | Recovered action |
|---|---|---|
| `011004de` | `01100e2a` | Entry after runtime/library initialization |
| `01100e42` | `01102986` | Main application initialization sequence |
| `01102aa6` | `01103304` | Clears queue state and installs stock task callbacks |
| `01103332` | `0110a760` | Registers task 5, named `ASGN` |
| `0110334a` | `0111ece0` | Registers task 3, named `RXDT` |

Earlier synchronization/setup calls must return for this path to reach these
sites. This is compiled startup reachability, not an all-path boot-completion
proof or a runtime snapshot.

`0111ece0` passes task ID 3, name `RXDT`, Thumb callback `0111ea25`, and priority
argument **decimal 10 / hex `0a`** to registrar `01102064` at `0111ecec`.
`0110a760` passes ID 5, name `ASGN`, callback `0110a65d`, and priority argument
**decimal 20 / hex `14`** at `0110a76c`. The callbacks are therefore the two
previously identified word routers, rather than functions guessed from names.

The registrar stores the callback into `20084958 + 4*task_id` at `011020b8`.
Its signed-halfword map at `6108499e` maps ID 3 to external IRQ **231** and ID 5
to IRQ **233**. Signaller `011020c0` reads that map and writes the IRQ number to
the software-trigger register `e000ef00` at `011020d6`.

The vector and indirect-call edges independently agree:

| Task | IRQ | Vector word address | Handler | Callback slot read by handler | Installed Thumb callback |
|---|---:|---|---|---|---|
| RXDT / 3 | 231 | `011003dc` | `0110216c` | `20084964` | `0111ea25` |
| ASGN / 5 | 233 | `011003e4` | `011021cc` | `2008496c` | `0110a65d` |

Each handler obtains the callback table from activity base `200848d8 + 0x80`,
loads its task-indexed slot, tests for zero and calls it with BLX. It also marks
activity, increments an invocation counter, clears activity on return and executes
DSB. Thus these routers execute inside those exception handlers on this stock
path; calling them OS worker threads would misidentify the execution context.

## Priority values and waits

The registrar computes the hardware byte as `(argument & 31) << 3`, using the
LSL-27/LSR-24 sequence at `01102098..9a`. It stores that byte to the mapped NVIC
priority register. The wait-timer setter `01103762` independently shifts its
argument left by three. The wait helper supplies `0x12` at `011271ca`.

| Source | Priority argument, decimal (hex) | Stored byte | Register |
|---|---|---|---|
| Incoming ring IRQ 6 | Direct byte write, rather than this registrar | `10` | `e000e406` |
| RXDT/task 3, IRQ 231 | 10 (`0a`) | `50` | `e000e4e7` |
| Wait timer IRQ 91 | 18 (`12`) | `90` | `e000e45b` |
| ASGN/task 5, IRQ 233 | 20 (`14`) | `a0` | `e000e4e9` |

All stored bytes in that table are hexadecimal. IRQ 6's direct priority write is
at `01102a28..2a`. Entry `01100e2a` clears AIRCR bits 10:8 with mask `f8ff`, sets
them to 3 with OR `300`, supplies the write key and writes AIRCR at `01100e40`.
This records the startup priority-group setting; it does not prove that no later
code changes grouping, priority registers, BASEPRI or interrupt masking.

The raw encoded ordering is IRQ6, RXDT, timer91, ASGN from lower to higher byte.
Effective preemption also depends on implemented priority bits, grouping and
current masks. In particular, the [wait helper](core1-wait-and-initial-data-study.md)
requires its completion callback to run while polling. The observed task/priority
bindings do **not** establish that it is safe to call from arbitrary exceptions,
with interrupts disabled, or while holding the stock manager's exclusion state.
No hardware timing or universal manager-call context is inferred.

## Copies and backpressure belong to the stock path

IRQ 6 (`01102944`) reads hardware-ring words and calls `0111ed12`. That routine
passes the word by value into the first software ring and signals task 3.
RXDT drains the ring into its stack, and its ordinary system-word path passes a
pointer to that stack word to `0110a5a6`.

`0110a5a6` **loads the u32 immediately** at `0110a5c4`, calls enqueue
`0110a390`, then signals task 5. Enqueue stores that value in the assignment ring
at `0110a3b2`. It does not retain the caller's stack pointer. ASGN dequeues a copy
and invokes the system dispatcher at `0110a6da`. This closes the stack-word
lifetime and registered scheduling edges for that path; it does not generalize
to arbitrary variable-buffer ownership.

The firmware also gates producers explicitly:

- IRQ 6 calls `0111f246`, which permits another read only while the first ring's
  free-count field is **greater than 64**. Otherwise `0110295e..68` disables
  IRQ 6 by writing bit `40` to `e000e180` and returns.
- Before copying into the second ring, `0110a478` compares occupancy with
  **`600` hex / 1,536 words**. At or above that high-water mark, `0110a5b0..c2`
  disables task 3's IRQ through `011024c2`, and disables IRQ 6 through ICER bit 6.
- RXDT's drain epilogue `0111ec9a..eca0` re-enables IRQ 6 through ISER bit 6.
  ASGN's drain epilogue `0110a748..756` re-enables task 3 through `01102494`, then
  also re-enables IRQ 6. Do not describe IRQ 6 as staying disabled until ASGN ends.

The ring indices use 9 and 11 bits, giving 512 and 2,048 slots, with one reserved
to distinguish full from empty. The larger ring's high-water threshold leaves
512 slots relative to its physical size. This arithmetic and the gating sites
are consistent with coordinated backlog control, but do not prove every producer
case is lossless. Full-ring error/reset paths also exist. The interrupt-mask
helpers issue CPSID/CPSIE rather than preserving an arbitrary caller's PRIMASK.
A future extension must join this ownership/scheduling design; a raw register
window or a check/set flag is not a general concurrency protocol.

## A bounded Linux routing result, not the missing converter

The Linux route-9 receiver `00c2c998` has a useful concrete boundary. For kind 3
it obtains the four-byte embedded word through `00be2ac0`, masks its first byte
to its low nibble in a **local stack copy** at `00c2c9f8..ca08`, and copies the
outer message separately. Values with low nibble **4, 5, 6 or 7** take the default
branch at `00c2ca34` to `00c2cbbc`. That branch destroys the temporary copy and
returns to `00c2c9bc`, which routes the **original message** to `e1`, local `0a`
and `0d` in order. No embedded-word rewrite occurs on those default branches.

These are the same low-nibble values the CORE1 SysEx assembler uses, but the
host routine does not synthesize CORE1's high-nibble-1 tag on this path. Its
local mask must not be mistaken for a wire-payload transformation. This closes
one host routing/copy question while leaving the e1 peer's interpretation open.
The previous [outer transport/ownership analysis](host-core1-bridge-followup.md)
still applies to the queued copies and ttyGS0 serialization.

## What the available update does and does not contain

All **346 regular members** of the retained `_DATA_FNTM0` archive were scanned
for an ELF header. Exactly four matched:

| Member | Bytes | SHA-256 |
|---|---:|---|
| `_DATA/mi078` | 61,181,491 | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` |
| `_DATA/qctest` | 304,912 | `d87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6` |
| `_DATA/bin/pcm` | 38,824 | `285c18ce51dd473702a74301c31ee000fc3bba413d8973d3ad028baab29b2f56` |
| `_DATA/bin/weston-image` | 608,056 | `a03211d7d0e54c86d910bfb7f8c2bf44153f463b8d186f90e30d9d24a64db609` |

The latter two were checked as possible overlooked plaintext peers. `pcm` imports
the ALSA PCM API and exposes the PCM example's playback/transfer modes;
`weston-image` imports Wayland/Cairo functions and contains `clients/image.c`
and image-viewer usage text. No BMC peer path was established in either. This
bounded classification does not exclude computed paths, loaded libraries, kernel
drivers, non-ELF images or files absent from this update archive. Installed
rootfs/CORE0 peer code remains a missing input, not a proven absence on hardware.

## Reproduction and the minimum missing observation

`tools/core1_task_context_study.py` checks the pinned startup calls, task
registration constants, vector/callback bindings, priority encoding and queue
copy anchors. Its three tests cover NVIC bank boundaries, priority radix,
unsupported-image rejection and the actual local corpus. It does not execute
tasks, provide a live control command or simulate scheduler preemption.

```sh
python3 tools/core1_task_context_study.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_core1_task_context_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x0111ece0 --size 0x14
python3 tools/core1.py local/b0c1a.bin --address 0x0110a760 --size 0x14
python3 tools/core1.py local/b0c1a.bin --address 0x0110216c --size 0x90
/usr/bin/objdump -d --start-address=0xc2c998 --stop-address=0xc2cbc8 local/mi078
```

Until readable peer code is available, a useful passive capture must correlate
the same **ordinary stock action** across boundaries, preserving:

1. Full ttyGS0 outer frame bytes, direction, timestamps, source/destination,
   kind, selector/metadata and payload length; include fragmented stream reads.
2. The peer's corresponding CORE1 ring words and physical-chip/core identity,
   including the actual first-byte high/low nibbles and ordering.
3. Completed CORE1 SysEx bytes/count and output ring words for the same event,
   then their corresponding host-side frame, if any.
4. Observed RXDT/ASGN/timer priorities, masks and callback state for any scheduling
   claim, without changing program ownership to collect the evidence.

This is an evidence specification, not a command sequence or an instruction to
transmit debug/MMIO requests. No such capture exists in this pass. No Qwen draft
was used. The external bridge and a validated custom-engine ABI/loader remain open;
the new result is a concrete stock callback context and queue-ownership model.
