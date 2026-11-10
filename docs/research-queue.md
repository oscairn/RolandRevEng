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

The integration task waits for all three handoffs, then:

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
