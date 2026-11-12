# Fantom EFCT callback and stock FDRV parameter producer

2026-11-11. A concrete registered **EFCT** callback now connects an internal
change notification to FDRV's descriptor reader, 22-value snapshot, original
buffer change detection and coefficient setter. This extends the
[raw-buffer study](fantom-parameter-buffer-study.md). The route is source-proved
and its selected bodies execute in isolated CPU memory; no physical interrupt
arrival, preemption, external panel/MIDI protocol or safe custom-engine entry
has been demonstrated. No DSP execution profile is added.

## Registered source path

All addresses/offsets below are hexadecimal, except decimal task IDs, IRQ
numbers, counts and parameter field indices. The stripped Fantom CORE1 payload
is pinned to SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
`tools/fantom_parameter_producer_study.py` checks source anchors, metadata and
the existing RTTI/hash gates. REA remains unavailable; these are file/Capstone
and Unicorn 2.1.4 results, not REA Evidence records.

| Edge | Checked source |
|---|---|
| Application initialization | `0110332e` calls `01126cec` |
| Task registration | `01126cf8` calls registrar `01102064`, with task 8, name `EFCT`, callback `01126a6d`, priority argument decimal 28 |
| IRQ binding | Task-map entry `610849ae` is decimal 139; vector word `0110026c` points to `0110225d` |
| Handler body | `0110225c` reads callback slot `20084978`, calls it, counts invocation and clears activity on return |
| Deferred dirty masks | Callback `01126a6c` consumes `20083e7c/80`, clears them between CPSID/CPSIE, then calls `01134c86` at `01126c0e` |
| Adapter | Veneer → `6102c8c4` → producer `610835d0` |
| Producer | Fills owner+144, then calls veneer `61077b12` → module update `011290ee` |
| Parameter application | Original embedded buffer, FDRV parameter callback, mute query and live coefficient producer |

The registered priority byte is `e0`, distinct from ASGN/task 5's `a0` and
timer91's `90`. Encoded values do not establish live preemption: grouping,
implemented bits, PRIMASK/BASEPRI, nesting and later configuration remain relevant.
The nearby task 6 named DEMO is not this effect callback.

Internal notifier `01126d2e` accepts a high-nibble-2 word and selects the MFX
dirty masks for operation byte84. Its low-six-bit part selector sets a pending
bit; bit15 additionally requests a transition/begin mask. It signals task8
through `011020c0`. The fixture uses `21 84 part 00` for parts0..2 and executes
the original notifier. This is a CORE1-local notification format, not a recovered
ttyGS0/SysEx/MIDI command. Actual upstream parameter-store writes are still open.

## Factory identity and the stock snapshot

Factory `6102dcda` branches through its TBH using `algorithm + 1`. The entry for
**decimal algorithm85** selects `6102f18a`, the checked FDRV constructor/wrapper
branch. This gives a real FDRV identity; the earlier equality-only fixtures used
an opaque marker42 to isolate the unchanged-algorithm path.

The source parameter constructor `61004ff8` calls `0110ea00` through a veneer.
For local part p in 0..2, it obtains the parameter store at
`614012d4 + 84*p`, reads its type byte, and selects the type's range from
`61093780`. For FDRV that range is decimal2840..2865. Four header parameters
are excluded from the snapshot: count is `end - start - 3`, or **22**, and the
snapshot reads IDs2844..2865 in ordinary order.

These three local parts map to owner module slots **1..3**, at
`owner + 54 + 20*p`. Slot0 follows a different producer and is excluded here.
The common scratch snapshot is `owner + 144`; on the checked sequential path,
the module copies it into the capacity-32 embedded buffer before the next loop
iteration reuses that scratch. The prior 32-element test snapshots established
capacity/ABI behavior, not that stock FDRV supplies 32 logical parameters.

## Original descriptor reads and defaults

`61004040` looks up a 20-byte descriptor through `6106f7bc` and reads from the
selected part store. FDRV's 22 descriptors use halfwords at offsets10..3a.
A negative descriptor minimum chooses signed-halfword loading; otherwise the
reader loads unsigned. Values outside the descriptor range become its default,
**not the nearest boundary**.

| Logical field | Source parameter ID, decimal | Store offset | Range | Default |
|---|---:|---|---|---:|
| 2: live1 mode | 2846 | 14 | 0..2 | 2 |
| 3: live1 cutoff | 2847 | 16 | 20..16000 | 3740 |

For example, mode3 becomes2; cutoff19000 becomes3740. A stored halfword `ffff`
in either unsigned field also falls back. Signed gain fields instead preserve
in-range negative values. These are this build's descriptor rules, not a general
BMC numeric limit or a direct panel-label mapping. Earlier direct-setter tests
above16000 remain tests of that lower-level API, not this stock UI producer.

## Mask and state boundaries

For the steady-state fixture, owner byte+2 is1, incoming transition mask is0,
and the type remains85. A pending part bit selects the update. With that byte0,
the producer can refresh parts without a pending bit and can enter replacement/
RAMCLR coordination; those paths are not executed here.

The observed per-part order is **disable task5 → read descriptors/fill snapshot
→ enable task5 → module apply → route selection**. The enable call is at
`610836d0`, before module apply at `610836e4`. ASGN masking therefore does not
enclose parameter application. It is not a proof of exclusive access, a DSP halt
or safe calling from an arbitrary context. The callback's global CPSID/CPSIE
around dirty-word clearing is likewise separate from the later apply.

## Execution checks and exclusions

The fixture executes the original notifier, IRQ-handler body, EFCT callback,
adapter, producer, parameter-store address calculation, descriptor lookup/read,
buffer copy/getters, FDRV/mute query and coefficient math. It supplies typed
part-store memory and an already-created unchanged-algorithm object graph.
Factory allocation and its lifetime are checked statically, not executed.

Across three slots, two mute counts, both enable flags, three modes, two valid
cutoffs and four changed sets, **288 cases match 1,080 coefficient writes**.
Four additional cases verify default fallback for out-of-range mode/cutoff.
Invocation/activity counters and dirty-mask consumption also match. Only fields
2/3 change; other parameter groups remain inactive.

The command ring is controlled empty. Task signaling, NVIC mask helpers and
post-apply hardware routing are recording callbacks. Coefficient I/O and slope
effects retain the previous fixture's controls. The handler is invoked as a CPU
routine; no actual exception arrival, OS startup, scheduling, preemption, live
NVIC, BMC peripheral or physical instrument executes.

Qwen returned a no-tool review in 23.1 seconds. Its scratch/source/count
observations were checked independently. It misidentified an early replacement
veneer, reversed the enable/apply order and inferred a task5 consumer; those
claims were rejected against the source route and event-order checks. No worker
code was accepted. Listings, worker text and detailed reports stay local.

```sh
python3.13 tools/fantom_parameter_producer_study.py local/b0c1a.bin
python3.13 tools/fantom_parameter_producer_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_parameter_producer.py -v
```

Next recover the write/notification producer for the typed parameter stores and
its host/CORE0 boundary. Real priority/mask state, object ownership, completion
cadence, hardware precision, history, entry/return and safe loading remain open.
