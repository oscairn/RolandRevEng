# Global clear completion: event 0x17 is hardware IRQ80

Follow-ups: [domain labels](memory-domain-labels-and-clear-count-boundary.md) tie
the Boolean banks to explicit software diagnostic names, retaining a control-label
defect and unknown physical/count semantics. [Coefficient envelopes](coefficient-envelope-and-completion-study.md)
use separate IRQ65..70 and shared bit1 in the same flag word, rather than clear bit0.

The Fantom CORE1 completion path is now joined from registration through the vector,
peripheral status acknowledgement, callback and shared waiter flag. Firmware event
`0x17` is a callback-table index; it is **not NVIC IRQ23**. The corresponding vector
selects external IRQ80. This closes the interrupt-delivery gap in
[the previous clear-interface study](dramio-owners-and-clear-interface.md), while
physical IDM/EDM naming, bulk count units and concurrent-use safety remain open.

All findings below are offline observations of the Fantom BMC0 header-stripped
CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
ITCM runtime address `01100000 + offset` is backed directly by the payload; ERAM
`61000000` begins at payload offset `3ffe0`. These addresses are not admitted for
BMC1, JUPITER-X, MC-101 or SH-4d. Capstone disassembly and the existing scatter
decoder were used; the unavailable REA provider was not retried. No target code,
plugin, updater, hardware command or device was executed.

## Registration, initial state and startup order

`0113191e` accepts unsigned event indices below `1f` and stores its r1 callback at
`200a18a4 + 4*r0`. It has no interrupt masking, exclusion, callback chaining or
validation of the pointer. `0113192a` reads the same table and returns zero for an
out-of-range index.

At `0112f496..49a`, the driver initializer loads Thumb pointer `0112f445`, sets
r0=`17`, and calls that registrar. The resulting slot is `200a1900`. Callback
`0112f444..44e` reads `200847f8`, ORs bit0 and writes it back. It does not inspect
the peripheral status, the Boolean domain or an operation identifier.

ARMCC scatter record `6123fce8` zeroes `20084818..200a2d5f` using handler
`610000b4`; that handler explicitly stores zero words. This includes callback slot
`200a1900`, the IRQ bookkeeping and mask shadow. Separately, the compressed record
`6123fc98`, source `0113afc4`, destination `2008008c`, size `478c`, initializes the
completion word `200847f8` to zero. The existing
[initial-data decoder](core1-wait-and-initial-data-study.md) supplies the latter
proof; these are different startup records.

The function with assertion identity `void Bmc_init_DSP() C` starts at `6102d614`:

| Call site | Veneer | Destination | Effect relevant here |
|---|---|---|---|
| `6102d61c` | `61077748` | `0112f450` | Registers driver callbacks, including event17 |
| `6102d8d6` | `61077752` | `01130c3c` | Programs NVIC priority/enables and peripheral event mask |

The registrar call occurs first. The driver initializer ends by branching to
`0112f210`, which initializes a separate listed-memory/DMA facility and IRQ18;
that tail is not the IRQ80 enabling path.

A bounded whole-payload immediate-branch scan found 15 candidate references to
the event registrar. Inspecting their argument setup found event constants
`7,1d,1c,0,2,a,19,6,8,9,a,b,c,d,17`; only the last is 17. This is evidence for the
identified stock installation, not proof against indirect replacement or a later
write to the callback table. No deregistration or lifecycle lock was established.

## Interrupt identity, enable and acknowledgement

| Item | Observed value and source |
|---|---|
| Callback event | `17` hex, registration `0112f498` |
| Vector entry | `01100180` contains `01131621` |
| External NVIC IRQ | `(180/4)-16 = 80` decimal |
| Handler | `01131620` |
| Priority byte | `20` written to `e000e450`, setup `01130d86..8a` |
| NVIC enable | `00010000` written to `e000e108`, setup `01130d8e..92` |
| Peripheral event mask | `old | 3fffffff` written to `41100200`, `01130e0c..18` |
| Mask shadow | Same value stored at `20084808` |

Priority setup initializes r0 to `20` at `01130c40` and retains it through the
IRQ80 byte store. The enable store is ISER2 bit16, agreeing independently with
IRQ80. Mask setup ORs bits0..29, including event23; it preserves the old top two
bits rather than unconditionally writing `3fffffff`. Setter `01130c2c` ORs supplied
bits into the shadow/register; `011318ec` clears supplied bits. These are separate
from driver configuration shadow `200847fc` / register `41100004`; their meanings
must not be collapsed into one mask.

Handler `01131620..0113164e` performs this exact order:

1. Read status `4110035c` and write **zero** to `4110035c`.
2. Save the read word at `200a1714`.
3. Increment the invocation count at `200a1698`.
4. Load callback slot `200a1900`; call it if nonzero.
5. Read `41100000`, store that read value on its stack, execute `DSB`, return.

The status address also agrees with `41100300 + 4*event23`. No status-bit test
qualifies the callback in this handler: a nonzero callback is invoked regardless
of the captured status value. It receives the captured word in r0, but the clear
callback ignores r0. The write-zero is the stock status-acknowledgement operation;
there is no evidence here that writing one is an equivalent acknowledgement.
The later `c0000000` write by the waiting clear driver is a **different write to
the selected bank control**, after its flag has been observed and cleared.

## What the completion contract does and does not guarantee

The previous study's `01130814` driver behavior is unchanged: it waits for the
selected bank's control bit31 to clear, optionally clears the shared completion
flag, writes start and `c0000000 | count | (completion<<28)`, then, for completion
true, polls shared flag bit0 and acknowledges the selected control with
`c0000000`. The final flag loop does not poll bank busy. Neither start nor count
has an explicit bounds/alignment guard or field mask in this body.

The new interrupt trace establishes the stock producer of that flag. It does not
turn the flag into a fence for unrelated DSP owners. Both Boolean banks use the
same callback and one flag; the callback has no bank or request discrimination.
The registrar, clear body and IRQ handler contain no mutex, exclusive-access
loop, PRIMASK/BASEPRI save/restore or timeout. The selected-bank busy test does
not serialize operations in the other bank. This is a bounded body-level finding,
not proof that every caller lacks a higher-level exclusion rule.

For a completion wait to finish through this path, the callback must remain
installed and IRQ80 delivery must be possible in the caller's context. IRQ80's
configured priority byte `20` differs from timer IRQ91's `90`, RXDT's `50` and
ASGN's `a0` in [the task-context study](core1-task-context-and-host-peer.md).
Those bytes alone do not prove current mask state, permissible calling contexts
or scheduler serialization. The pre-command busy-delay path also depends on the
separate timer wait `011271b8`; it is not a clear-completion event. Safe use from
arbitrary callbacks/interrupts, with interrupt masks raised, or by simultaneous
callers has not been established. No deadlock was observed or claimed.

## Independent address-unit evidence and its boundary

The named firmware assertion in `01130b00..b6a` identifies
`CBmcDspDrv::ReadIdmEdmMemoryRaw(bool,unsigned,unsigned,unsigned*)`. Its loop sets
the same start registers used by clear:

| Boolean | Start selector | Read command/control | Raw data portal |
|---:|---|---|---|
| true | `41100040 = start+i` | `41100044 = a0000000` | `41158008` |
| false | `41100050 = start+i` | `41100054 = a0000000` | `41158018` |

It waits for selected control bit31 to clear, reads one 32-bit portal word and
stores it at CPU output pointer `+4*i`; i advances by one until i reaches count.
The adjacent float (`01130a1a`) and fixed (`01130a94`) readers use the same start
sequence with float/fixed portal offsets. The float writer `01130892` likewise
uses `start+i` and CPU input pointer `+4*i`.

**Observation:** one start-selector increment corresponds to one exposed 32-bit
CPU element for these access operations, rather than a four-byte-scaled hardware
selector increment. The clear driver writes its start unchanged into the very
same selected register. **Inference:** this is useful evidence for a logical
element address at that portal. It does not prove the physical stored width,
alias/wrap behavior, bulk-clear count unit or range inclusivity. Bulk count may
have a different interpretation from the per-element access selector; no such
equivalence has been admitted. Neither portal's Boolean branch has yet been
independently tied to a named IDM versus EDM backing resource.

There are also direct startup operations before interrupt enabling: at
`6102d732..746`, start0 and control `c0020000` are written to the false bank; at
`6102d748..75c`, start0 and `c0800000` to the true bank. Both busy-poll bit31 and
neither sets bit28. These corroborate separate bank initialization and a polling
mode; `20000` versus `800000` are raw low-field constants, not byte capacities
or proof of domain names. They are distinct from the later manager calls
documented previously.

## Reproduce and outstanding proof

```sh
python3 tools/clear_completion_study.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_clear_completion_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x1131620 --size 0x30
python3 tools/core1.py local/b0c1a.bin --address 0x1130c3c --size 0x1e4
python3 tools/core1.py local/b0c1a.bin --address 0x1130b00 --size 0x6c
```

Use the existing Capstone-capable interpreter. The checker pins the full build,
verifies instruction/literal anchors, independently joins vector arithmetic and
callback indexing, checks initial flag/table allocation, and reports source
offsets and SHA-256 for six relevant spans. It emits metadata only. Three tests
cover event/vector separation, invalid vector/Thumb inputs, unknown-build
rejection and the actual local corpus join. They do not emulate a peripheral.

Answered: clear callback event→vector identity, stock priority/enable/mask setup,
status acknowledgement order, initial flag/table state, startup registration
order, and per-element portal address progression. Partially answered:
registration lifetime/exclusion, because direct installation is known but all
indirect mutation/caller contexts are not. Still unknown: physical IDM/EDM bool
mapping, bulk-count units, hardware IRQ-generation semantics, selective owner
clear bounds, time-index behavior and safe transition sequencing. This pass
adds no executable opcode or hardware-clear command to the admitted subset.
