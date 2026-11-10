# Offline research queue

Queued 2026-11-10 at Jacob's request. Starting research checkpoint: `80b740b`.
The practical target is a small custom engine running on the BMC render DSPs, with
the i.MX8M handling UI/control. Current emitters produce verified fragments only.

## Execution and ownership

Three separate Codex tasks work in isolated Git worktrees under ignored
`local/worktrees/`. Each has a research branch, its own generated outputs and symlinks
to the existing vendor inputs. An integration task reviews their commits after they
finish. Worktrees and binaries are not repository deliverables.

Workers read this file, README, the relevant studies and the REA and Ponytail skills.
Read `/Users/jacob/.agents/skills/reverse-engineer-anything/SKILL.md` and
`/Users/jacob/.codex/plugins/cache/ponytail/ponytail/5.3.3/skills/ponytail/SKILL.md`.
Reuse saved evidence. REA's Hopper provider was unavailable in the earlier pass;
ordinary file/Capstone analysis is available and must be labeled as such. Do not
repeat an unchanged failed provider setup or alter client configuration.

### OMP/Qwen delegation and review

Jacob additionally authorized using OMP with Qwen on his Mac Studio to save tokens,
with independent review of the returned work. The installed OMP is 18.18.0 and the
existing model identifier is `MacStudio/Qwen3.8-Flash-Next-Uncensored-oQ6e-mtp`.
Use bounded analysis/coding prompts; Codex remains responsible for validating evidence
and accepting changes.

OMP's ordinary state directory is outside writable roots. Isolated provider profiles
are already prepared at each worktree's `local/omp-agent`, with only the existing
MacStudio provider. The launch environment that reached startup is:

```sh
PI_CONFIG_DIR='Projects/Open Synth Platform/bmc-research/local/omp-root'
PI_CODING_AGENT_DIR="$PWD/local/omp-agent"
```

`PI_CONFIG_DIR` is relative to the existing home directory in this installed OMP;
do not reassign HOME. Pass these variables to the OMP process using `env` or a
structured subprocess environment. Never print provider credentials or commit profiles.
Initially, the no-tool 30-second smoke test started but timed out; a read-only request to the
configured model endpoint failed hostname resolution in this command runner. Model
availability was therefore unverified. Do not claim Qwen was used unless a run
actually returns, and do not spend the research run repeatedly repairing networking.
Use the available Codex path when the local model cannot be reached.
Later diagnostics confirmed direct TCP and DNS sockets are denied with EPERM by the
command sandbox. After Jacob reopened Codex with automatic approval review, an
approved network execution returned an authenticated `BMC_RUNNER_OK` from this exact
OMP/Qwen provider. The ordinary sandbox remained restricted: use the reviewed network
execution path, not a claim that all commands now have unrestricted network access.
See [runner diagnosis](runner-network-diagnosis.md) for the verified invocation.

When using Qwen:

- Serialize requests with a process lock on the main checkout's
  `local/omp-qwen.lock`, using `fcntl.flock`; avoid competing long inference jobs.
- Prefer no-tool drafts with supplied bounded source/evidence, or read-only tools
  `read,grep,glob`. Keep writes, commits and integration under the reviewing worker.
  Disable extra extensions/title generation and use an explicit model and time limit.
  No paid-model fallback, configuration installs or approval bypass flags.
- Save prompts/results under the worker's ignored `local/`. Treat output as a draft,
  including any claimed test results and instruction meanings.
- Review every accepted diff for correct logic, bounds, unknown-state handling,
  unnecessary dependencies/abstractions and unintended file changes. Run the relevant
  tests yourself, including meaningful failure cases; independently reproduce binary
  evidence. Compilation or self-reported tests alone are insufficient.
- State in the handoff which work Qwen actually returned, what was accepted/rejected,
  and which independent checks passed. The integration task reviews it again.

Shared rules:

- Code stays in the project. The Obsidian vault gets documentation only and is
  currently outside writable roots; prepare updated notes/patches locally.
- Use local artifacts without executing Roland's plugin/app/firmware or opening any
  live device. No firmware packaging, flashing, boot-script changes or blind commands.
- Do not change the existing shell update packages. Normal BMC IPC uses ttyGS0;
  the prepared shells can contend with it. Record this actual conflict prominently.
- Preserve vendor inputs. Keep vendor binaries, raw programs, coefficient tables,
  disassembly and detailed dumps ignored/local. Commit original tools/tests, recovered
  interfaces and research prose only. The requested GitHub repository is private;
  do not push until private visibility and existing history can be verified.
- Distinguish observations, hypotheses and hardware-dependent unknowns. Structural
  parsing and numerical coincidence do not establish instruction meaning or timing.
- Fail closed on unsupported forms. Add a small meaningful regression for new parser,
  assembler or provenance logic; retain counterexamples and conflicting evidence.
- Work unattended. Make routine decisions and continue independent work when one
  lead stalls. Do not leave approval/input requests pending. If a question is truly
  unavoidable, first run `/Users/jacob/.codex/bin/prompt-ding`; otherwise record the
  exact missing evidence and continue another lead.
- Each worker owns its branch/worktree. Do not edit another worker's checkout or
  merge into main. Commit coherent findings and write a final handoff with commit IDs,
  reproduction commands, checks, limitations and next concrete experiment.
- Use the worker's ignored `local/HANDOFF.md` for the final handoff, then finish the
  task normally. Do not send cross-task progress messages: the client requested
  approval for those calls in this run. Integration reads the files and branches.

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
