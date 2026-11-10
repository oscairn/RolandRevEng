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
