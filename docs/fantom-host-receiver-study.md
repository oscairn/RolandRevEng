# Fantom local range registry, coalescing and drain

2026-11-11. The original route4 receiver now has an executable registry/lookup/
coalescing/drain check. **777 cases consume 2,178 local notifications and produce
1,488 coalesced emitter calls**. Repeated records merge their numeric ID ranges,
retain first-arrival order and reset for reuse. This extends the receiver boundary
from the [host scalar-edit study](fantom-host-write-study.md); the two fixtures do
not run as a continuous Linux application or establish a host-to-CORE1 bridge.

The pinned mi078 SHA-256 remains
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`.
Evidence is file/Capstone analysis and isolated Unicorn CPU execution, not REA
Evidence records or instrument observations. Raw firmware and listings stay
local/ignored. No DSP opcode profile is added.

## Stock activation and registry

Addresses are hexadecimal; counts and parameter IDs below are decimal.

| Original edge | Evidence |
|---|---|
| ELF static activation | `.init_array` contains `00438240` exactly once |
| Registry construction | Static initializer allocates `0x810` bytes and invokes `00c05580` |
| Global binding | `00438278` installs the registry at receiver `0424bb20` |
| Registry geometry | `0x800` bytes of provider pointers, then pending head/tail at `+800/+808` |
| Family6 provider | Registry slot6, vtable `01386030`, RTTI `CIDMinMaxBlock<1,1>` |
| Family7 provider | Registry slot7, vtable `01386090`, RTTI `CIDMinMaxBlock<1,2>` |
| Queue/wake setup | Worker entry `00bfecd0` calls helper `00bfe590` with wake callback `00bfed48` |
| Worker drain | `00bfed3c` invokes drain `00bfe9b8` on receiver `0424bb20` |

The replay executes the complete static initializer and provider constructor:
**78 allocations**, comprising the registry and 77 provider objects. Its private
allocator is bounded to 8 MiB; this is a fixture limit, not a firmware heap size.
The complete constructor exceeded the existing small-fragment instruction budget,
so it has a separate bounded allowance. FP/SIMD execution is enabled in the private
AArch64 CPU for the constructor's original vector initialization stores.
Other family providers are constructed but their semantics are not admitted here.

The two selected providers supply three 24-byte dirty records. Each record holds
u16 minimum ID, maximum ID and family, followed by next/previous pointers at+8/+16.
A clean record has minimum65535, maximum0, family0 and null links. Provider vtable
slot0 finds a record; slot8 recovers its index/context from the record address.
Those original functions execute; lookup is not replaced by an authored table.

The selected provider bounds are significant. Family6 normalizes the checked
nonnegative incoming index/context to0/0. Family7 normalizes a positive index to0,
keeps contexts0/1 and aliases larger context bytes to0. The native tests include
index16383 and contexts2/255 to verify these aliases. These are observed getter
behaviors, not recommended caller values or a physical BMC slot assignment.

## Original coalescing and FIFO drain

The fixture builds each authored kind1 message with original packer `00be40d0`
and constructor `00be2998`, then calls original routing `00be4270` with route4.
The receiver `00bfe640`:

1. Requires kind1, decodes family/index/context and relative ID range.
2. Uses the stock provider's lookup method.
3. Links a clean record at the pending tail, once only.
4. Reduces its minimum ID and increases its maximum ID for subsequent edits.
5. Invokes the installed wake callback after releasing its receiver mutex.

Wake helper `00bfed48` sets worker pending flag+30 to1 and requests a condition
signal. Every checked incoming message wakes, even if it merges into an existing
record. The fixture executes that helper and checks its flag/signal arguments;
pthread effects are intercepted.

Drain `00bfe9b8` pops the head, derives index/context from its actual provider,
resets the record and list links, reconstructs a kind1 range message, and calls
emitter `00bfe7c0`. It requests a 10,000-microsecond delay after each coalesced
record. The delay is recorded, not slept. An additional empty drain must emit
nothing, and all three records plus head/tail are checked clean before reuse.
The worker's infinite wait loop, real condition delivery and timing do not run.

For example, these authored arrivals:

```text
family7/context1: cutoff3505
family6/context0: mode3504
family7/context1: mode3504
```

produce, in order:

```text
family7/index0/context1: 3504..3505
family6/index0/context0: 3504..3504
```

This is numeric min/max coalescing, not a list of changed values. The drain passes
an ID range to its emitter; it does not retain a per-event parameter-value copy.
The emitter's subsequent reads and message construction remain separate evidence.

## Where this queued path leads

The emitter is **intercepted at entry** in this replay. Static tracing identifies
a different output from the family's immediate kind7/8 path:

- `00bfe7c0` calls address/range encoders through the Cff parameter-transfer tables.
- Header helper `00bfedd8` starts with bytes `F0 41` and selects command12 on the
  traced construction path. Other header fields use additional encoding logic.
- After data/tail construction, `00bfe950` wraps the buffer as kind2, and
  `00bfe958/95c` routes it to destination08 through the existing BMC output object.

This is source evidence for a queued SysEx construction route. It does not prove
the full emitted bytes, an external MIDI destination, endpoint transformations,
host-to-CORE1 compatibility or safe DSP loading. In particular a kind2 SysEx
buffer is not the recovered internal selector84 assignment stream merely because
both carry parameter changes. Route0a's separate receiver list also remains outside
this replay.

## Checks and next work

The matrix uses all sequences of length0–3 drawn from six authored notifications,
under three stack canaries. Cases include repeated/overlapping ranges, interleaved
families/contexts and the bounded alias inputs. Original records persist between
cases; the fixture verifies the drain's cleanup rather than resetting dirty records
to hide failures. A second empty drain checks that old work is not replayed.
The inputs cover generic live1 IDs3504/3505; other ranges/families are not tested.

Allocation, memset, cleanup registration, pthread/sem setup, mutex effects,
condition signaling, thread identity and requested delays are controlled. No OS
thread is started, no real cleanup handler is registered, and no device or network
transport opens. The original receiver, provider methods, wake helper and drain
execute; the SysEx emitter and downstream consumers do not.

Qwen's draft returned in 4.6 seconds. Review retained its FIFO/range-union algorithm
and replaced its redundant set and linear search with an insertion-ordered dict.
Independent alias/order tests and the original-code matrix verify the model.

```sh
python3.13 tools/fantom_host_receiver_study.py local/mi078
python3.13 tools/fantom_host_receiver_study.py local/mi078 --execute-arm64
PYTHONPATH=tools:tests python3.13 -m unittest test_fantom_host_receiver_study test_fantom_host_block_study test_bmc_ipc test_core1_sysex -v
```

The queued emitter's complete bytes and route0a consumers remain useful host leads.
Next prioritize an independently supported DSP encoding context, such as the OSC
short-add candidate, while keeping this host control contract available for later
integration. Missing peer/physical slot mapping, silicon precision/history,
interrupt timing, entry/return and safe engine loading remain unresolved. The 18
exact DSP execution profiles are unchanged.
