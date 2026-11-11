# Coefficient manager processing and waits

The subsequent [Fantom ARM32 check](fantom-eqvg-control-study.md) verifies selected
generator/setter/manager correspondence and differences. In particular, its
waited driver clears stale completion before arming; the desktop preposted-flag
canary below does not establish the same behavior on Fantom. Task exclusion and
physical cadence remain open.

2026-11-11. The earlier [EqVg study](eqvg-filter-generation-study.md) recovered
setter requests. This checkpoint executes their manager/wait processing in
owned buffers and compares it to an independent scalar/event model. It uses
the pinned ZENOLOGY ARM64 image and its simulation role4. It does not establish
Fantom scheduler cadence, hardware precision or a loadable engine.

## Executed source and fixture boundary

`tools/coefficient_manager_study.py` links 19 bounded original bodies, including:

| Native source | Address |
|---|---|
| CSimDspMgr literal interpolation | fbd60..fbfcc, manager slotf8 |
| Live envelope manager forwarding | fcbb4..fcce0, slot178 |
| Descriptor/segment resolution | fc0ac..fc420 |
| DSP4 envelope setup / immediate fallback | 16c468..16c594 / 16c5b0..16c64c |
| DSP4 completion dispatch / wait | 16c684..16c694 / 16c694..16c6dc |
| CBMCEnv control packing, breakpoint, sync, step and interrupt dispatch | 3460cc / 346734 / 3461c0 / 3463d8 / 34611c |
| CBMCEnvSet role4 active scan | 347174..3472e0 |
| CDSPWait request / counter step | 2a5938..2a59c8 / 2a5bc4..2a5c30 |
| Subtask flag set / wait / identity comparison | 36454c / 3645d8 / 364800 |

The complete bounded-region list is `REGIONS` in the tool. Source SHA-256 is
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Manager vtable slots and pthread import identities are checked. Cross-function
branches and constant-page references are relocated into the owned mapping;
excluded assertions, stack-guard failures and other-role interrupt paths trap.
The copied code becomes executable only after writing ends.

Manager, core, descriptors, global-pointer graph, task state, envelope objects,
records and bitmap storage are fixture-owned. The original active-bank scanner
calls the original envelope stepper; completion traverses original interrupt
dispatch and core flag delivery. Literal reads/writes are controlled callbacks
over authored binary64 values, without executing the physical literal codec.

**Primitive boundary:** mutex construction, unique-lock and condition-wait
helpers, pthread lock/unlock/signal and thread identity use controlled callbacks.
The condition-wait callback advances original envelope-bank and CDSPWait counter
processing until the original subtask flag changes, with a bounded progress
budget. No OS worker thread, plugin/application, instrument or hardware driver
is started. This exercises the software protocol under an explicit cooperative
schedule, not real pthread timing, cancellation, spurious wakeups or concurrent
callers. The fixture advances one bank scan and one wait-counter update per tick;
that convention is not a measured audio sample/block cadence.

## Literal interpolation: amount100 is an update count

The method takes a coefficient-symbol pointer list, target-double list,
coefficient count and signed amount. Its observed processing is:

1. Read all baseline values before writes; compute each `target-current` delta.
2. Set step count to `max(abs(amount),1)`. Zero therefore takes the direct-final
   path; negative amounts use their magnitude.
3. For k=1..steps-1, write `FMA(delta,k/steps,baseline)` for nonzero deltas only.
4. After each intermediate sweep, call `WaitXsample(1,true)`.
5. Write every exact target unconditionally at the end, including unchanged
   coefficients. No wait follows that final sweep.

Source anchors include normalization at fbe38, ratio at fbedc, FMA at fbf18,
wait at fbec0 and final writes at fbf6c..fbf88. A zero-length coefficient list
still performs the requested intermediate waits. The research API admits
0..127 coefficients and amount +/-4096; the source count guard is below128.
INT_MIN/huge iteration requests are outside the bounded execution domain.

For five changing coefficients and amount100, there are 99 intermediate sweeps,
99 one-sample wait requests and five final target writes: 500 writes total.
The raw100 is not milliseconds. It is an interpolation subdivision count whose
elapsed progress depends on the wait context and scheduler. Intermediate values
follow native binary64 FMA semantics; physical BMC literal conversion remains
separate. Signed zero, unchanged values, empty/maximal lists and negative/zero
amounts are checked against original execution.

## Sample wait and shared task flag

`WaitXsample` ignores nonpositive requests, a disabled object's byte+c, or calls
outside its current subtask. In the admitted path it **assigns** request+1 to
counter+8, unlocks, and optionally calls the subtask wait. It does not increment
the old counter. `CDSPWait::VProcSync` decrements positive counters and calls
SetFlg exactly when the counter reaches zero.

Thus a fresh `WaitXsample(1,true)` takes two explicit counter updates in this
fixture. That is verified counter behavior, not proof of two physical audio
samples or an off-by-one hardware defect. Outside the admitted subtask context,
the original interpolation writes still occur but no counter wait progresses
fixture time. The thread-identity comparison itself executes original code
against controlled identities.

The original subtask flag state transitions are:

| Operation / prior state | Observed result |
|---|---|
| SetFlg / state3 | state4, posted completion |
| SetFlg / state5 | state3 and condition signal |
| WaiFlg / state4 | state3 and immediate return |
| WaiFlg / state3 | state5, then condition-wait helper |

These names describe observed behavior, not recovered enum declarations. The
completion is shared and untagged by coefficient/request identity. A preposted
flag is consumed without waiting for the newly scheduled operation. Deferred
waits and subsequent counter completion are also compared against the model.

## Live envelope path and completion state

The manager resolves its authored kind6 data descriptor through the original
segment reader, adds the relative slot and calls the core. When wait=true but
the caller is outside the current subtask, the core takes its original immediate
binary32 write path. With an admitted context, it sets the envelope/control
record, registers the active bitmap entry and forwards a wait when requested.
Nonwaiting writes still schedule an envelope outside that subtask.

The original breakpoint math uses the existing selector table and 44100 rate.
Original bank processing advances active records, clears completed active bits,
sets pending bits/counts and dispatches wait completion once. Restarts remove a
slot from pending and reactivate it. Owner sync flags are checked against active
bitmap membership. Tests span slots63/64/65/129 and the final role4 slot1023.
Interrupted ramps, zero increments, equal targets and immediate fallback retain
their actual record/control behavior; completion is not inferred merely from a
counter or target comparison in the harness.

## Connected EqVg sequencing and a preposted-flag canary

The EqVg setter fixture can now forward its original calls into this owned
manager. The independent model uses pure coefficients and the checked descriptor
permutations. Every manager request, wait-driven tick and final state is compared
with bit-preserving float representations. No native intermediate supplies a
model coefficient or model increment.

The example is the previously recovered unsafe simultaneous interpolation:
low-pass 20 Hz/Q.25 to 19000 Hz/Q128 at44100.

| Path / initial task state | Observed fixture result |
|---|---|
| Live / fresh state3 | First damping write waits530 updates; remaining envelopes finish by tick1060; all sampled Jury margins positive |
| Live / preposted state4 | First wait returns without progress; both state coefficients ramp together; minimum sampled Jury margin about -1.159796856 |
| Literal / fresh state3 | Original setter batches1 then4; 198 wait requests, 396 explicit ticks; all sampled margins positive |
| Literal / preposted state4 | First posted flag is consumed; 394 explicit ticks; batch staging still keeps sampled margins positive |

This canary proves the guard depends on completion/flag state in the constructed
interleaving. It does not demonstrate that stock application callers leave a
stale flag or expose a runtime race. Caller ownership, flag initialization and
real scheduling still need evidence. Positive sampled Jury margins are also not
a general stability theorem for arbitrary time-varying filters.

## Validation and next boundary

The standalone native check covers 40 literal context/count cases and 410
wait-driven ticks. A separate 12,000-tick replay with 95 interrupted live writes
matches **960,000 live-record fields**, plus active/pending sets and counts,
owner sync flags, task flag, wait counter, signals and operation traces. Connected
EqVg cases verify both fresh and preposted task states. Full native audio is not
rerendered by this protocol fixture; the preceding FDRV audio checks remain
separate evidence. No packet/opcode profile or byte-emitter rule changed.

```sh
python3.13 tools/coefficient_manager_study.py --execute-native --ticks 12000
python3.13 -m unittest discover -s tests -p test_coefficient_manager.py -v
```

Qwen completed its 111.1-second static pass. Current-subtask gating and the unit
wait calls were independently verified. Its zero-normalization claim and its
swapped coefficient-count/amount interpretation were wrong and rejected. Native
execution supplies the numerical counts above; worker logs and listings stay local.

Next cross-check the corresponding Fantom ARM32 generator/control path and trace
the actual callers' task/flag ownership and sync cadence. Hardware precision,
interrupt delivery, history initialization, entry/return and safe loading remain
unverified. No hardware was accessed or flashed.
