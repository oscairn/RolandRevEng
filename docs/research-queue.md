# Offline research queue

Queued 2026-11-10 at Jacob's request. Starting research checkpoint: `80b740b`.
The practical target is a small custom engine running on the BMC render DSPs, with
the i.MX8M handling UI/control. Current emitters produce verified fragments only.

The [mapping-status inventory](bmc-mapping-status.md) distinguishes the 18 exact
DSP profiles and complete FDRV arithmetic reference from structural parsing,
ARM control evidence and unverified hardware. No whole-chip percentage is known.

Latest arithmetic result (2026-11-11): the exact 126-byte cubic quad executes
four independently checked waveshaping curves, matching all five Fantom bodies.
It now composes between the original oscillator/gain and lowpass filter: 510
logical bytes, 512 stored, 39 packets, data extent 150 and the same ten seeds.
Independent scalar and five relocated checks cover the voice through wrap.
Next recover another useful exact producer/control context or an owner-proven
nonempty label/continuation path; retain bounded opcode admission and hardware gates.
Entry, runtime allocation and hardware calibration remain separate requirements.

The latest bounded manager milestone is complete (2026-11-11): [original manager/wait
processing](coefficient-manager-processing-study.md) now executes in owned memory
with controlled task primitives. Forty literal context cases, 12,000 explicit
live ticks and connected EqVg guard cases match the independent model. The raw100
is an update count; counter/state processing and completion bitmaps are checked.
A preposted-flag canary bypasses the live guard in the constructed interleaving;
actual caller ownership and OS/hardware scheduling remain unproved.

The Fantom correspondence milestone is complete (2026-11-11): [bounded ARM32
EqVg/control execution](fantom-eqvg-control-study.md) matches 4,580 coefficient
fields, 2,000 stability decisions, 48 setters, 48 completion cases and 20 literal
cases. Fantom has four active types, a different fallback and float32 rounding.
Its waited driver clears stale completion before arming, so the desktop canary
does not transfer. Stock literal amount100 matches; negative amounts are modeled
statically but excluded from CPU execution pending a Unicorn fixture/IT-path fix.

The [Fantom mode query](fantom-envelope-mode-study.md) is now traced through
four source-bound managers to the MFX controller's per-slot mute nesting counter.
Twenty query cases, 80 counter transitions and 40 original FDRV caller cases
match: count zero enables envelopes, nonzero selects immediate writes. This query
does not inspect task identity. Sample waits use a separate timer byte; bit0 of
the shared completion word belongs to clear completion.

The [parameter-dispatch checkpoint](fantom-parameter-dispatch-study.md) now connects
the original unchanged-algorithm module callback to the concrete FDRV parameter
body, logical live1 fields 2/3, mute query and coefficient math. Ninety-six cases
and 360 writes match. Checked NVIC helpers use unconditional CPSID/CPSIE rather
than preserving an incoming PRIMASK; this is not an exclusion protocol.

The [raw-buffer checkpoint](fantom-parameter-buffer-study.md) now resolves the
embedded capacity-32 FDRV interface: signed-16 snapshot pointer plus element count,
prefix copy and byte-per-field changes. Twenty-four original-buffer cases cover
three capacities; 96 connected raw dispatches match 360 writes without value/flag
callbacks. Short updates retain tail flags, reset retains values, and oversize
updates return unchanged. This is not the external transport or a safe live-call ABI.

The [stock producer/EFCT checkpoint](fantom-parameter-producer-study.md) now
connects task8/IRQ139 through the original descriptor reader to a 22-value FDRV
snapshot and live1 setter. Factory ID85 and descriptor fallback are source-bound;
288 selected route cases match 1,080 writes. ASGN is re-enabled before apply.
The notification, handler body and callback execute in private CPU memory with
hardware effects controlled; real preemption/ownership is still unverified.

The [stream-store checkpoint](fantom-parameter-store-study.md) now executes
generic scalar/block writes and original finalization before the EFCT path.
576 cases match 2,160 writes and 864 notifications. Dirty IDs differ from typed
FDRV IDs; writes retain low16 bits, identical writes still notify, and reserved
notification bits6..12 retain stack contents. External serialization is excluded.

The [assignment-stream checkpoint](fantom-parameter-stream-study.md) now runs
word copying, the real assignment ring, ASGN handler/callback, PRMEdit reassembly
and selector84 into the writer/EFCT path. 576 cases match 2,160 writes through
1,584 incoming words, including ring wrap. This caller passes serialization false;
the separate scalar/UI adapter flag is not assigned that behavior by assumption.

The [host block checkpoint](fantom-host-block-study.md) now verifies original
kind-7 construction/serialization in 108 cases and decodes separate metadata/data
in saved frames. It identifies 37 direct constructor sites and the generic paired
block/range-notification source, without connecting them to CORE1 selector84.

The [host MFX family checkpoint](fantom-host-family-study.md) now compares all 48
generic and 26 FDRV typed descriptor tuples with CORE1, finding a 2,071-ID shift in
these ranges. Registered callbacks, actual getters and paired block/range messages
match 432 cases; physical slot assignment and the missing peer remain unresolved.

The [host scalar-edit checkpoint](fantom-host-write-study.md) now runs original
wrappers, descriptor-clamped writes, destruction and routed notifications in 648
cases, producing 2,268 messages. Identical values still write/notify; an optional
local route4 notification uses converted generic IDs. Receiver/queue consumers and
the missing peer remain outside the replay.

Next bind the local receiver/queue registrations and drain behavior, then seek
readable comparison-peer handling of the precise block/range formats. Independently
supported new DSP encoding contexts remain a separate useful offline direction.
Sample-wait/interrupt ownership and cadence remain open. These control passes add
no DSP opcode coverage; new independently supported instruction contexts remain
a separate useful offline direction. Hardware precision, history setup,
entry/return and safe loading remain open.

The preceding bounded filter milestone is complete (2026-11-11): [EqVgCal](eqvg-filter-generation-study.md)
now has native-checked formulas, Q clamping, consumer permutations and UI scaling.
Original piece setters prove interpolation ordering/wait flags and literal batch
splitting. Both 12,000-frame immediate-update policies match all audio/ring/cache
state during 48 events and 240 original setter writes. No new opcode is admitted.


The preceding bounded filter milestone is complete (2026-11-11): EqFaCal's eight
numbered branches plus bypass fallback are recovered with original native math
checks. Setter reordering and UI indices/scaling are independently checked by
executing the original native UI dispatcher against owned recording callbacks.
Thirty-eight events from 35 UI updates exercise cutoff/type changes in all four
three-coefficient stages. Both native-double and explicitly quantized coefficient
policies match full audio/ring/cache state during 12,000-frame replays. This does
not identify actual Fantom UI routing or physical literal precision.


The preceding bounded control milestone is complete (2026-11-11): native FDRV
descriptors cover all 20 local live slots and 14 literal groups. Drive, wet, level
and slope targets are independently replayed through original native envelope
math. Both 12,000-frame scale pairs match 960,000 envelope fields and 24,696,000
audio/ring/cache values during 13 setter events. Actual Fantom live-slot dispatch
and level-table correspondence are checked, while binary32 VFP target arithmetic
is not treated as identical to desktop binary64/FMA calculations.

The second-effect review independently matches 8,224 FETDRIVE mixed/shaped values
through wrap. Encoded versus native constructor scale changes 3,255 of 4,112 shaped
outputs; the worker's scale-insensitivity claim is rejected. Prefix source/alias
gaps still prevent new opcode admission.

EqFaCal/EqVgCal generation and selected native UI conversions are covered by
the later checkpoints above. Resolve actual runtime with/without-envelope
selection and scheduler cadence next. Physical target precision, history initialization, entry/return and safe
loading remain open. Do not describe the selected live-control replay as complete
parameter support or a hardware envelope measurement.

The preceding bounded milestone is complete (2026-11-11): the final FDRV literal
filter and gain tail complete an offline arithmetic/output reference. Eleven
fragments total 1,692 bytes and 104 packets. Both 12,000-frame scale pairs match
final stereo audio, all 2,048 ring cells and six cache slots/two cursors every
frame. `00f8`, device IO timing, physical precision and safe loading remain open.
Next choose a second complete effect or parameter-update provenance to challenge
the inferred arithmetic policy; hardware entry/return remains a separate gate.

V-STAGE ownership now reaches a RTTI-linked CFspMfxFDRV callback passing the
matching list to vtable slot28. The shared 11,572-byte program has diagnostic
TestEram-associated dispatch; the 51,542-byte program has verified list-selection
dispatch and a 16-byte-row reader, with exact class owner unresolved. Prioritize
semantic leads supported by these callers rather than treating shared test code
as an unidentified synth engine.

The preceding bounded milestone is complete (2026-11-11): two cascaded history
filters extend the independent chain to 1,504 logical/stored bytes and 92 packets.
Distinct nonzero coefficients match 552,000 native values per scale-pair run.
Next recover the final state-variable/auxiliary region and output tail at 4e0;
11 stock packets/172 bytes remain through 58c. Future prefetch values and hardware
numeric/loading behavior remain outside current comparison.

V-STAGE/Fantom comparison now has four exact service-window matches in groups
0 and 1/2, shared candidate DSP contents up to 51,542 bytes, and one relocated
FDRV post-cubic body match. Unseen encoding contexts are catalogued without
semantic claims. Next prove ownership/callers of useful shared contents and
select independently corroborated new contexts; do not transfer host/load rules.

The preceding bounded milestone is complete (2026-11-11): the first post-cubic mix
and gain extend the independent chain to 1,340 logical/stored bytes and 84 packets.
Each scale-pair fixture matches 504,000 native data cutpoints through five wraps.
Next recover the first following filter at 446; 18 stock packets/326 bytes remain
through 58c. The represented next-packet output stores do not admit that full packet.

The parallel V-STAGE inventory found official 1.11 components for bmc0..bmc4,
with three distinct code/content groups. It is now a concrete BMC-family corpus
lead. Its UI/host CPU, physical chip count and loading compatibility remain open;
seek readable processor markings or service/GPL evidence before assuming Linux.

The preceding bounded milestone is complete (2026-11-11): resampling/drive now
connects the filter bank to clipping and cubic shaping in a 1,230-byte packet
chain. Both native-reference drive variants match 456,000 data cutpoints each
through five wraps; all five Fantom bodies retain their distinct 0.0625 scale.
Save/sync this checkpoint and pause broader work. On resumption, begin the first
post-cubic history mix at 3ec; full FDRV has 23 downstream packets/416 stock bytes
remaining through 58c. These byte counts do not estimate effort or full-chip
coverage. ISA/control-flow coverage, numeric/timing calibration and device
loading/ownership remain separate requirements for a complete BMC map.

The preceding bounded milestone is complete (2026-11-11): all four stereo filter
sections and both recombinations now execute in a 902-byte input chain, ending
before resampling arithmetic. A separate native prefix matches 336,000 values
through five wraps. The terminal short packet form and synthetic bridge stores
are documented with their allocation limits. Save/sync this checkpoint and pause
broader research as requested. On resumption, recover the resampling/drive producer
and its history/coefficient timing to connect the already checked downstream
clipping/cubic windows. Full FDRV and physical execution remain open.

The preceding bounded milestone is complete (2026-11-11): the second filter and its
recombination now form a 496-byte packet-only chain from the input. A separate
native prefix captures the recombination output before the next filter begins;
192,000 compared values match through five wraps. Save/sync this checkpoint and
pause broader research as requested. Full FDRV and physical execution remain open.

Tonight's bounded input-stage milestone is complete (2026-11-11): the 86-byte
stereo prefilter and 184-byte first filter execute entirely from packet bytes.
The independent persistent model ring matches 120,000 native values through five
wraps. Tests, original example and reproduction command are saved. Pause broader
research after committing/syncing this checkpoint, as Jacob requested; require
resumption before pursuing another block or hardware-loading gap.

Latest emulator result (2026-11-11): exact clipped-half interpolation now executes
80 bytes with verified unclipped history and average-before-clip order. Isolated
native arithmetic, all five stock bodies and 12,000-frame callback cutpoints
match. The earlier drive/resampling producer window remains outside admission;
recover its inputs and stores next to reduce the conditional full-FDRV gap.

Latest execution-path result (2026-11-11): the separate active DMA drain at 0112f508
is now tied to manager slot 48; slot 44 starts queued DMA and can process pending
DRAM-IO state. Queued state 1 and started state 2 require different operations.
The actual Fantom/Jupiter CORE1_DSPEnable calls and global masks differ for DSP 1/3;
no mode-to-halt semantics or custom entry/return rule follows. Next seek an
implemented mode/event consumer or source of saved continuation; preserve these
bounded negatives if hardware observation remains necessary.

Latest loader result (2026-11-11): exact halfword source geometry, edge-before-bulk
ordering and queued-only completion behavior are checked. A 510-byte body reads
512 source bytes but writes 510. Starting without wait and later calling the same
helper with wait does not drain state 2. Planner manifests now retain geometry;
source lifetime, runtime exclusion, entry and continuation remain unproved.
Next trace SetExeMode callers and packed event/mode/start arguments to distinguish
stock scheduler-control sequences from the unproved render CALL/RETURN semantics.

Latest stock-control result (2026-11-11): the mute method's resolver omits capacity
checks and its raw halfword search includes literal payloads. An exact offline
checker covers first-match replacement, all four matching words, compact framing
and all five actual FETDRIVE entries. This constrains future probes but does not
establish halt or safe program replacement. Nonempty label shapes remain unproved.

Latest entry-boundary result: [CORE1 label targets](label-target-encoding-study.md)
proves the halfword scaling and counted record layout, verifies five existing
parent numeric fields, and checks the actual FETDRIVE entry label has no incoming
counted references. Next is an owner-proven nonempty label list or independent
flow implementation, then continuation/issue-order evidence. No wrapper is emitted.

## Research workflow

Read the relevant studies and reuse saved evidence before repeating analysis.
Keep generated reports and supplied vendor inputs in ignored local storage.

- Distinguish observations, hypotheses and hardware-dependent unknowns. Structural
  parsing and numerical coincidence do not establish instruction meaning or timing.
- Preserve vendor inputs. Commit original tools/tests, recovered interfaces,
  aggregate metadata and research prose; exclude binaries, disassembly, extracted
  program/coefficient tables, credentials and personal working notes.
- Fail closed on unsupported forms. New parser, assembler or provenance logic
  needs a focused regression test; retain counterexamples and conflicting evidence.
- Independently review model-assisted work and reproduce its claimed evidence
  and tests. Record which results were accepted and their limitations.
- Keep code in this project; external note vaults receive documentation only.
- Do not access an instrument, package firmware, flash an update or change boot
  scripts as part of an offline study. Normal BMC IPC uses ttyGS0; prepared shell
  packages can contend with that interface.

Local runner configuration and provider profiles are not part of the public
research workflow. Historical execution details remain in the work log.

## 1. Host-to-CORE1 bridge — branch research/transport

Start from [host transport](host-transport-study.md) and
[CORE1 receive path](core1-receive-and-test-controls.md).

Questions, in order:

1. Map the host IPC kinds and route identifiers around `mi078` `00be4270`,
   `00be1a50` and `00be2448`. Establish how a message selects a BMC, subsystem and
   request/reply handler, with actual call/data references.
2. Follow memory/debug, development, coefficient and program-related request paths
   from their constructors to serialization and response handling. Separate ordinary
   MIDI from any actual memory/program service. Trace length, ownership and completion.
3. Identify the stream peer or bound the missing implementation precisely. Compare
   proven embedded words with CORE1's system-command and SysEx handlers. Do not equate
   matching byte shapes with proved forwarding.
4. Determine whether existing firmware exposes a usable loading/readback service,
   or whether a resident CORE1 bridge remains necessary. If the latter, specify its
   minimum ABI and unresolved entry mechanism without pretending it is deployable.

Deliver a new follow-up study, an evidence-backed route/command table, and only the
offline inspection tools needed to reproduce it. Explicitly identify any dependency
on encrypted CORE0 or missing runtime capture. Never guess a key or send a probe.

## 2. Instruction semantics — branch research/isa

Start from [MAC/issue study](mac-controls-and-issue-study.md),
[exceptional controls](special-ops-and-exp-study.md) and
[native primitives](native-arithmetic-primitives.md).

Questions, in order:

1. Recover additional source/destination fields and exact arithmetic variants around
   already matched gain, MAC and allpass sequences. Prefer asymmetric symbolic values
   and independent native store/load boundaries over frequency correlations.
2. Investigate `20a*`/`30a*` macro windows, saturation/wrap, shifts and breakpoint
   flags. Isolate what can be proved about a single operation versus a whole macro.
3. Use named DSP4 sine/impulse/noise/DC coefficient anchors to identify useful program
   regions, but require independent semantics before assigning oscillator opcodes.
4. Extend the supported decoder/emitter only for proved forms. Keep unresolved
   register syntax, precision and simultaneous issue explicitly unsupported.

Deliver exact-context opcode/operand mappings, reproducible native comparisons and
regressions. If no new opcode can be established, deliver the concrete negative
results and smallest missing proof, rather than expanding speculative tables.

## 3. Kernel and audio ABI — branch research/kernel-abi

Start from [supported code generation](supported-code-generation.md),
[loader map](BMC%20DSP%20packet%20and%20loader%20map.md) and
[receive/lifecycle study](core1-receive-and-test-controls.md).

Questions, in order:

1. Trace stock entry/exit/framing controls (`ff71`, `ff75`, `00f8`), IO-slot setup,
   state initialization and per-instance relocation. Locate which context owns
   `2016..2019`; do not label them physical TDM channels without evidence.
2. Recover program/data ownership, capacity checks, manager task context and actual
   transition ordering. Distinguish a check/set flag from a general-purpose lock,
   and execution modes from unproved stop/run names.
3. Establish the smallest complete stock context that could host a muted zero,
   pass-through, gain or stateful-filter probe. Record every still-unproved wrapper,
   scheduling and routing requirement.
4. Turn proved requirements into a reproducible offline probe design and, where
   justified, extend code generation and reference checks. Do not emit a purported
   standalone engine by copying unexplained controls around a fragment.

Deliver a concrete kernel ABI/resource map and a hardware validation recipe with
expected observations, readback checks and stop conditions. Hardware execution,
recovery and device-specific calibration stay unperformed until a unit is available.

## Integration and completion

The integration task waits for all three `local/HANDOFF.md` files and completed
worker commits, then:

1. Reviews evidence and changes, rejects unproved claims, and resolves any conflicts.
2. Integrates accepted commits into the main research checkout without force-pushing.
3. Runs checks appropriate to merged changes. Baseline is 78 passing tests with the
   local corpus; clean checkouts skip dependency/corpus checks explicitly.
4. Updates README, the main report and work log around the final findings. Rebuilds
   and verifies the Obsidian patch against saved originals; does not overwrite newer
   vault changes or attempt writes outside writable roots.
5. Reports what moved closer to a runnable engine, what remains blocked, and exactly
   which hardware/artifact evidence is needed next. No claim of hardware success from
   static comparisons.

The queue can advance offline analysis using the prepared artifacts. Agent execution
still requires an available Mac and service connection. Losing that execution context
is not evidence that a queued task completed.

## Reviewed offline checkpoint

All three workers completed clean, committed handoffs and were idle before integration.
The main checkout independently reviewed and reproduced their results:

| Work | Accepted worker commit | Result / remaining boundary |
|---|---|---|
| Host/CORE1 bridge | `8e42a7e` | Actual CORE-local MMIO service and host route/service map; external peer, safe manager coordination and read-reply stack discrepancy remain unresolved. |
| Instruction semantics | `6c4678c` | Three exact native expression comparisons and oscillator/macro bounds; no general decoder/emitter expansion. |
| Kernel/audio ABI | `0ecc0fe` | Stock mute/routing/reservations and an offline stock-context probe design; task entry, complete state initialization and hardware behavior remain unresolved. |

Integration tightened saved read-reply decoding to reject unaligned offsets even
when their checksum is valid. Qwen returned no work in any worker; no Qwen draft
was accepted. The OMP/network diagnosis is recorded separately, with the earlier
messaging-approval pause explicitly historical. Tests and final document-patch
validation are recorded in the [work log](work-log.md). No hardware/target execution,
shell-payload edit, vault write or push occurred. The next evidence requirements
are in the three follow-up studies; this checkpoint completes the queued offline
passes, not a runnable engine or hardware validation.

## Continued offline pass: startup, lifecycle and oscillator layouts

Starting checkpoint `5246bce`. Three independent collaboration workers used new
isolated worktrees; the parent separately traced host version identities and
compared pinned public MC-101 source. The prior TUI messaging-approval restriction
above is historical; these workers returned local commits through collaboration.

- [Service startup](core1-service-startup-mmio.md): both compiled startup loops
  visit the receiver constructors. Exact reply-frame geometry confirms the local
  buffer discrepancy in both supplied builds. External ingress remains unknown.
- [Effect lifecycle](effect-lifecycle-and-parent-entry-study.md): generic factory
  replacement, temporary RAMCLR, coefficient writes, DRAM-IO cleanup and DMA wait.
  Four numeric parent-entry candidates; complete history reset remains unknown.
- [Oscillator layouts](oscillator-layout-candidates.md): four exact contexts and
  six owned anchors constrain arities, with two ambiguities retained. The general
  decoder/emitter is unchanged.
- [Host versions](host-version-and-upstream-crosscheck.md): five component slots
  and actual expected strings. Peer-to-physical-chip identity remains unproved.

Four bounded OMP/Qwen requests actually returned on the authorized Mac Studio.
Each response was independently checked. They contained substantive errors;
no generated code or unverified semantic assignments were accepted. Prompts and
responses remain ignored/local. All published conclusions follow file evidence.

The next useful offline questions, in order:

1. Decode the separate four-segment RAMCLR **DRAM-IO** program sufficiently to
   identify every state range it writes and relate its returned `1900` wait value
   to actual completion. The coefficient loop alone cannot settle history reset.
2. Compare `00a0/00a2` parent contexts with native callback/routing boundaries and
   placeholders. Prove the entry operand, return/condition state and issue timing
   before emitting a wrapper; resolve the fifth DSP1 parent separately.
3. Recover opaque controls around the four oscillator packets. Obtain independent
   arity evidence for `3074` and extension ownership for `2d64/0c3b`; a header-rank
   fit or a matching coefficient alone is insufficient.
4. The end-to-end loader still needs the actual ttyGS0 peer implementation or
   correlated existing two-way traffic. Neither public MC-101 code nor startup
   activation fills that missing edge. Continue other offline work until that
   artifact or hardware evidence is available; do not invent a host upload command.

## Further pass: clearing, parent controls and other factory firmware

From `ef39d1b`, continued the first three questions above and added Jacob's request
to inspect other Roland BMC products. The official MC-101 v1.82 and JUPITER-X
v3.03 archives were downloaded, identified and compared offline. Original files,
download pages, manifests and extracted members remain ignored/local.

- [DRAM-IO/native state](dramio-clear-records-and-native-state.md): 92 owner-matched
  Fantom records, an actual low-23-bit rewrite path and three separate native
  zero loops. Native start indices are excluded; exact hardware coverage is open.
- [Parent controls](parent-control-and-nested-organ-study.md): fifth DSP1 context
  connects through nested organ Od, desktop DSP4 has a previously omitted 24-record
  list, and shifted `00aN` candidates match native callback IO. No call/return timing
  or universal stereo ABI is admitted.
- [Wait/initial data](core1-wait-and-initial-data-study.md): initial flags recovered
  from bounded compressed scatter data; pending completion, chunking, final polling
  and 32-bit scale arithmetic reproduced and independently reviewed.
- [MC-101](mc101-v182-core1-comparison.md): exact 324-byte MMIO read prefix and
  relocated wait body; scaled-wait multiplier 44100 differs from Fantom 48000.
- [JUPITER-X](jupiter-crossmodel-c1-study.md): exact RAMCLR/rewrite windows, but
  eleven segments with two record spacings. Shared code does not establish a shared
  firmware ABI, physical routing or safe Fantom transport.

Two additional bounded Qwen drafts returned for arithmetic/dataflow review; errors
were rejected against the instructions and direct calculations. Cross-model work
used exact bytes/ranges and no model-generated code. One common read-only QSPI
reader serves both comparisons; the Fantom mapper and production ISA admission
remain unchanged. Member checksum fields are preserved, with their semantics open.

Next useful questions:

1. Explain the two JUPITER-X DRAM-IO strides through actual owner/counter/source
   semantics, then test the resulting model against Fantom's four contexts. A
   repeated record pattern alone is insufficient for a clear-coverage proof.
2. Decode the condition/control words associated with shifted `00aN` references
   and the actual return state/timing. Retain the four-output native callback
   counterexample when specifying an engine ABI.
3. Extend cross-model program/owner comparisons using these preserved official
   inputs before downloading more near-duplicate models. Keep product addresses,
   clock assumptions and capacities build-specific.
4. The encrypted/external peer and recoverable host entry remain dependencies for
   an end-to-end Fantom loader. Neither downloaded factory image closes that edge.

## Current pass: owner contracts, task context, keys and access

Continued from `788a0f1`. The owner/condition/task questions above received bounded
follow-ups; the general emitter remains unchanged:

- [Owner/clear contracts](dramio-owners-and-clear-interface.md) explain the two
  JUPITER-X layouts through actual constructor selection and separate counter
  apertures. The global clear driver has different bounds and shared completion;
  its units, synchronization and safe per-instance use remain unproved.
- [Conditions/returns](condition-fields-and-implicit-return-study.md) anchor four
  predicate inputs but do not identify hardware condition flags or return state.
- [Task context](core1-task-context-and-host-peer.md) closes software-IRQ startup,
  priorities and queue gates. Safe custom manager entry/preemption is still open.
- Official [SH-4d/TR-8S updates](sh4d-and-tr8s-firmware-study.md) extend comparison
  to another readable CORE1 and an encrypted-only component set.
- [Ciphertext/key location](core0-ciphertext-and-key-location.md),
  [material scan](embedded-rom-key-material-scan.md) and
  [provider references](core0-rom-provider-reference-study.md) distinguish a
  reported MC-101 ROM entry from an actual recovered key. None was recovered.
- [Access audit](fantom-access-route-audit.md) identifies a gated stock factory
  shell endpoint and corrects the removable-SD, USB-console and recovery claims.

One bounded no-tool Qwen review returned for the cross-model checker. Its code
observations were checked against source and focused tests; its statement that
tests cover only synthetic inputs was rejected because actual-corpus tests exist.
No model-generated code or unverified semantic assignment was accepted.

The next concrete work, ordered by what it unlocks:

1. Trace any indirect/aliased writer enabling qctest mode 3. A shell call alone
   does not supply its UI activation, effective UID or a usable terminal. Keep
   physical console/security questions separate from source configuration.
2. Obtain an owned BMC boot-ROM/runtime or applicable peer artifact through a
   proven access path. Reported MC-101 B6 entry `012034c0..012034d7` is a candidate
   only. Validate any actual candidate with the documented packing and multiple
   plaintext structures before claiming Fantom decryption. More identical update
   headers or arbitrary 24-byte guesses do not resolve this dependency.
3. Continue native/DSP alignment for condition flags, implicit return state and
   unresolved oscillator/macro fields. Require independent cutpoints before
   admitting new opcodes; retain the current four-output callback counterexample.
4. Establish the clear engine's units, completion sharing and ownership against
   existing code/captures. Source bounds alone do not prove hardware history reset.
5. Once entry and recovery are established, correlate existing bidirectional
   host/peer traffic and stock RAM/state before designing a tiny muted probe.
   Timing, numerical precision, audio routing and a complete executable ABI still
   require hardware validation. No live probe or flashing is queued automatically.

## Next checkpoint: transmit, clear interrupt and stereo taps

Continued from `9ea3262` with three isolated workers and an independent outbound
queue study. New evidence is in [factory UI dispatch](factory-gate-and-ui-dispatch-study.md),
[clear completion](clear-completion-interrupt-study.md),
[stereo taps](stereo-tap-accumulation-study.md) and
[transmit/backpressure](core1-transmit-and-backpressure-study.md).

- The factory intro page is connected to actual dispatch and separate from all
  33 test rows. Mode 3 preserves it while 0/1/2 select test groups. No enabling
  mode-3 caller was recovered; more literal scans of the same build are unlikely
  to resolve arbitrary aliases. Another build/source or controlled state evidence
  would discriminate dormant code from an omitted activation path.
- Clear event17 maps to IRQ80. Registration, zero state, priority/enable/mask and
  status/callback flow are now joined. Bulk-clear units/domain naming, ownership
  and hardware event generation remain open.
- Four exact long-control/extension pairs implement stereo tap accumulation in
  one TS808 context. Six independent native stages, live coefficient records and
  explicit read/write aliases agree. General register syntax, numerics, other
  occurrences and new scheduling are not admitted.
- The MMIO reply reaches type-3 word packetization and TXDT/shared-ring enqueue.
  Rings reserve a slot; shared free-count includes it; software full paths can
  reject words and TXDT can spin on shared-ring fullness. No remote acknowledgement
  or universally lossless/reentrant interface follows.
- The pinned MC-101 README and ROM study disagree on the dump hash. Both are now
  searched as author-reported candidates; neither is authenticated. The bounded
  corpus still supplies no actual ROM/key candidate or decrypted CORE0.

Next useful work is independent variation of tap/control fields or another native
primitive with complete input/state provenance; bulk-clear count/domain semantics
through named allocation/access callers; and an owned applicable peer/ROM artifact
or verified access route. Preserve the separation between queue acceptance,
peer receipt, hardware clear/DMA completion and DSP execution in any future ABI.
No flash, shell activation or live MMIO probe is scheduled by this queue.

## Current checkpoint: envelope API and independently varied feedback

Continued from `c56b1ed`. The [control-semantics ledger](opcode-semantics-ledger.md)
now consolidates the exact arithmetic forms, scope and unsupported controls.

- [Tap-feedback variation](tap-feedback-variation-study.md) checks two later
  contexts, including compiler-hoisted products, exact distinct read/write
  records and auxiliary versus accumulated contributions. Equal coefficients on
  ports3/7 leave source selection underdetermined; isolated bit causality is not
  admitted. Integration rejects destructive multiply destinations in the retained
  source proof, with a new counterexample in the existing regression.
- [Coefficient envelopes](coefficient-envelope-and-completion-study.md) recover
  selector packing, bank capacities, manager dispatch/wait behavior and shared
  completion bit1 through IRQ65..70. EnvTC is a selector; native nominal timing
  is not Fantom calibration. The native manager's operating query returns false
  on its normal path and cannot validate live hardware completion.
- [Memory-domain names](memory-domain-labels-and-clear-count-boundary.md) join
  false/IDM and true/EDM at software-diagnostic level. A retained control-label
  defect and native no-op stubs leave physical and bulk-count claims unresolved.
- [Official build check](fantom-official-build-provenance.md) downloaded v1.08
  directly from Roland and verified equality to the retained archive. Checked
  older links supplied no alternate qctest/recovery consumer. The QSPI resource
  master was corroborated as the known37-record superset, not a Linux image.

The next discriminating evidence for register syntax is a context with different
source-port coefficients while other controls stay fixed, or an authoritative
assembler/interpreter. Further aliases of equal values cannot settle the bits.
Bulk-clear units still need an actual count-to-indexed-range relation. Usable
entry/recovery, a readable peer/ROM artifact and hardware state/timing observations
remain dependencies for an executable engine, not tasks solved by passing offline tests.


## Active emulator milestone

The [functional interpreter](fragment-emulator.md) now executes the exact 60-byte
dry/wet and 82-byte allpass families. Its first audio demonstrations use original
signals and explicit host state wiring. [Independent corpus checks](fragment-emulator-validation.md)
compare every packet and store and compose the two actual LINEDRIVE chains into
its real tail; this does not supply the unproved stock prefix or circular cadence.

The [five-program inventory](emulator-next-program-targets.md) selects LINEDRIVE
as the next complete-effect target: 42 remaining packets, prefix numeric/state
behavior, coefficient bindings and entry/return wrappers still need proof. The
shorter CHO/GATE files have more unresolved structure and control flow. Prioritize
the LINE input-mix/store window `004..038` against native `2df884..2df8d8`, retaining
constructor-field identity and independent L/R expressions; equal defaults cannot
settle duplicated literal fields. Then recover quantized shaping and history.
No automatic unknown-as-zero, whole-effect substitution or guessed return semantics
is authorized by a successful fragment render. Hardware access/recovery and numeric
calibration remain separate dependencies for deployment.


## Continued LINE reference and state checkpoint

The native prefix now has [checked numerical kernels](line-prefix-shaping-study.md),
including exact signed shift wrap, strict sign-mode boundary, binary32 live
coefficients and explicit FMA evaluation. The [ring/context study](line-state-and-history-study.md)
checks one origin step after native routing, twelve conditional prior-write/read
relationships and all 46 indexed accesses. Pre-rational history3/6 must stay
separate from the current allpass factors27/28. Warm initialization and actual
callback count/P assignment are still not supplied by a fresh effect record.

A [conditional original-signal pipeline](fragment-emulator.md#conditional-line-reference-pipeline)
now composes the host oracle and supported bytes. Its circular implementation
matches direct delay equations through origin wrap. This is a useful numerical
fixture, not complete DSP byte execution or native-plugin/hardware audio validation.

The [parameter study](line-prefix-parameter-study.md) establishes real rational
count-4 operations and the one-representative native mechanism. A checked
[global inventory](line-prefix-global-groups.md) has no matching static count-2+
group for14/17 or24/27; separate/runtime writers and other layouts remain open.
The next discriminating evidence is the rule governing those fields and full
outgoing DSP port/store state, followed by contextual instruction comparisons
against the new numerical kernels. Implicit return/mute execution, parent cadence,
resource transitions and hardware calibration remain independent gaps.

Two [new official firmware packages](ax-edge-and-juno-x-firmware-study.md) add
readable CORE1/ciphertext comparisons but no applicable ROM/key candidate or
access/recovery route. Repeating unchanged code windows and literal-address
scans is unlikely to resolve the missing peer or silicon state. Future vault
updates go to `Projects/Oscairn/Roland`; code and generated audio stay in the project.

## Stereo scratch transfer checkpoint

The dry/wet profile now covers the store and reload pair in both LINEDRIVE
and FETDRIVE. The conditional LINE render obtains scratch values from those
packets. The primary-program gap inventory leaves 40 and 49 packets respectively,
including the two final packets in each program. The next suffix proof needs
the return state consumed by `00f8` and the fate of its co-issued output stores.
[Scratch profile and evidence](supported-code-generation.md#drywet-tail-with-scratch-transfers)

## JDMLT_B sequence and LINE input checkpoint

The JDMLT_B native selector now ties the stock sequence setter, dispatch
table and four callee regions together. Two constructor records bind native
writes to transfers beside the internal `00f8` sites. The next control-flow
proof needs to resolve the DSP selector dispatch and saved continuation.
The `0080` packet's remaining word matches the terminal address under
the existing doubled-address hypothesis.
[JDMLT_B selector and return evidence](condition-fields-and-implicit-return-study.md#jdmlt_b-sequence-selector-and-store-provenance)

The checked stereo input packet runs in the conditional LINE renderer.
LINEDRIVE and FETDRIVE have 39 and 48 primary packets left respectively.
The alternate-bank comparison keeps the duplicated input-mix literals
equal, so resolving their independent roles and the auxiliary store
sources still needs a discriminating case.
[Stereo input and bank comparison](emulator-next-program-targets.md#input-packet-and-bank-comparison)

## Fantom LINE placements and original stateful kernel

The conditional renderer now executes original input, allpass and
mix/scratch slices from all five pinned Fantom LINE placements. Each
matches the desktop fixture through ring wrap. A separate original
one-pole fixture carries its previous outputs through DSP stores and
alternates two preassembled variants on the host.
[Offline render and kernel](fragment-emulator.md#linedrive-from-the-fantom-image)

For the hardware track, the first missing observation is normalized
program readback from a verified active owner. The offline comparator
can now distinguish an exact match, the recorded opening mute-bit
difference and other differences. Prefix arithmetic and return
continuation remain open on the DSP track.
[Placement and readback comparison](kernel-audio-abi-study.md#offline-line-placement-and-readback-comparison)

## Native arithmetic execution checkpoint

The native LINE callback runs in an explicit isolated fixture and agrees
with the conditional reference through ring wrap. MFX OSC now has a
checked phase step, owned frequency write, sine factorization, seven owned
polynomial literals and direct boundary execution. The
[sine study](oscillator-sine-study.md) records the narrow native sign/fold
intervals and four Fantom placements. These do not establish DSP precision
or exceptional-state effects.

The complete native FETDRIVE fixture has now passed review, local execution
and per-frame comparison of both first shaped stores. A full Python state
reference also matches every output sample in 12,000 frames. Eight native
history pairs and three paired coefficient groups are independently checked.
Qwen's native fixture was retained; its later unfinished full-model draft
required local correction from native instructions. Independent contexts
for exceptional arithmetic, strict byte-execution admission and further
OSC waveforms remain queued. Qwen's exact rational sine expansion has been
checked independently.

The next discriminating clamp comparison is now STPS `bedb` at packet `18a`
and TVPS at `178`. Both have a following port-3 store, separate from the
FETDRIVE reciprocal sequence. Their native tails perform explicit bipolar
clamps. The late-store checker now accounts for the earlier phase branches
by proving invariant address roots and forward joins. It verifies both native
store pairs and twelve Fantom contexts. The six-artifact inventory found all 174
`3086` hits in the same 58 repeated triples, with no independent result.
[Inventory and phaser candidates](operand-variants-and-macro-boundaries.md#reciprocal-control-context-inventory)

The remaining phaser comparison needs the exact source of `bedb`, beyond
its now-proved port-3 result. No counted static group binds the duplicated
`1.4` producer literals. The pointer-preserving late-window method also
provides a concrete approach for revisiting TRANSIENT's post-branch math
cutpoints, without weakening the ordinary prefix tracer.

TRANSIENT's complete native callback is `1d5fd0..1d66c4`. Its only external
calls are one `_log` and two `_exp` imports; all eight ordinary branches
stay internal. No `ADR/ADRP` appears. Constructor data and four live-pointer
fields require a context of at least `680` bytes. The next execution step
is a checked host-math call bridge and explicit memory fixture, followed
by arithmetic/state comparisons. Qwen's initial metadata was reviewed and
corrected before the execution work recorded below.
[TRANSIENT execution boundary](special-ops-and-exp-study.md#transient-callback-execution-boundary)

The TRANSIENT callback now executes through a checked three-call libm bridge.
The [full independent reference](transient-full-reference.md) closes the
upstream detector gap and matches all stereo output values across 12,000
frames. Fifteen retained detector writes per frame are also checked. Constructor
rates, native owner caches and explicit clock assumptions are documented in the
[execution fixture](special-ops-and-exp-study.md#native-transient-fixture-and-conditional-envelope-reference).

An [original 120-byte feedback oscillator](original-bmc-allpass-oscillator.md)
now executes its sample arithmetic entirely through supported packet profiles.
It has a reproducible coefficient/seed manifest and no per-sample host phase
calculation. The [200-byte stereo voice](original-bmc-stereo-voice.md) now adds
packet-executed gain and scratch output. Its resource extents fit five recorded
stock owners. [Explicit resource plans](fantom-voice-resource-plans.md) now
substitute data/coefficient/IO fields for all five recorded layouts and match
the original model with nonseed canaries. Next are actual owner coordination,
initialization, envelope/routing integration and entry/return validation.
Hardware precision/cadence and actual loader access remain required. The
exact phaser input selection, TRANSIENT packet semantics and broader ISA gaps
remain open alongside this original-core track.

The [typed state-writer study](state-initialization-and-float-writers.md)
joins the native oscillator ring to enum 0 and checks its per-DSP firmware
binary32 write apertures. All three stock per-DSP readers reject enum 0/1;
the global IDM/EDM portal has no proved address join to this ring. The six-seed
CPU-rounding experiment passes through ring wrap, but hardware conversion,
owned initialization and readback remain open. Qwen's bounded portal analysis
was reviewed; incorrect literal and call-search conclusions were rejected.

The [short-add candidate study](short-add-context-candidates.md) inventories
fifteen short contexts across nine classes and verifies TRANSIENT's constructor
decay-default binding to its short operand. Same-word long/misc contexts and
PH100's zero literal are retained counterexamples. Four native immediate adds
are checked, but exact port source/destination and side effects remain open.
The [FDRV cubic study](fdrv-cubic-waveshaping-study.md) now checks four independent
source/result cutpoints, direct native arithmetic and all five Fantom placements.
The [auxiliary/add-MAC study](auxiliary-save-restore-and-add-mac.md) now closes
the first stereo pair's source/store relation and admits an exact 84-byte profile.
Next are the remaining state/filter producer arithmetic and PHONO, with actual
owner/entry/return and hardware gates still required. Qwen's initial
single-class/numeric rejection was independently corrected.

The [state-variable filter pass](fdrv-state-variable-filter.md) now resolves the
first complete stereo block and adds a 184-byte byte-executed template. Its
native sign, state aliases, shared coefficients and one-level auxiliary lifetime
are checked. The [original filtered voice](original-bmc-filtered-voice.md) now
completes that composition: 384 bytes, ten seeds and eleven coefficients, with
all five layouts verified through wrap and nonseed canaries. Next are nonlinear
waveform producers and remaining arithmetic/control semantics, alongside live
ownership, routing, initialization and entry/return requirements.

The resource planner exports original logical/stored bodies and manifests only.
It verifies all thirty transfer operands while protecting every other byte,
and derives exactly six read-before-write data seeds. Across five 12,000-frame
renders, all 120,000 channel values match the original body. This clears the
offline resource-substitution step, with body load address and all entry/exit
and hardware claims still unassigned. Qwen's timed-out draft was corrected
through independent typed transfer-field checks rather than a grammar expansion.
