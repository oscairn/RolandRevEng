# Unattended research checkpoint

2026-11-09, continuing into the overnight session. User-selected remote:
`https://github.com/jbschooley/RolandRevEng.git`.

## Repository and publication

The local repository is initialized on `main` in the existing project directory
`bmc-research/`, with `origin` set to the user-provided URL. The remote repository was
created by the user. This environment could not resolve `github.com`; `gh` also could
not connect to `api.github.com`. Therefore remote contents, default branch and private
visibility could not be verified, and no successful upload is claimed.

The GitHub connector was found but is unconnected. The browser access host was
unavailable, and Computer Use approval denied Firefox access without giving a reason.
No authentication or permission settings were changed and no sign-in prompt was left
for the sleeping user.

Before a later push, verify the requested private visibility and fetch any existing
remote history. Do not overwrite a remote initial commit or force-push by assumption.

Tracked files contain analysis tools, original synthetic tests, research prose,
aggregate checks and recovered interface metadata. Vendor binaries, exports, native
disassembly, extracted program/coefficient tables, dumps and personal vault working
copies remain local and are excluded from Git.

## Research delivered

- Independent gain-chain verification against native ARM64 register/pointer def/use.
- An exact dry/wet MAC family compared as complete symbolic output expressions.
- Further header-family and coefficient-reference decoding, with unsupported forms
  retained as explicit limits rather than coerced into a successful parse.
- Fresh constructor-table reconstruction and native memory provenance, correcting the
  previous global tag-2/tag-4 labels.
- A CORE1 RTTI-to-callback trace that distinguishes real dispatch from log formatting;
  it does not supply a demonstrated external upload entrypoint.

Each study document records its exact scope and reproduction command. The original
61,334-packet structural corpus check remains available through `tools/analyze.py`.

No plugin or firmware was executed, no instrument was accessed and no update was
flashed. Arithmetic rounding, timing, physical memory aliasing, host entry and flash
recovery still require evidence before claiming a working custom BMC synth engine.

## Local document state

The Obsidian vault is readable but outside this session's writable roots. Its three
original notes remain unchanged. Updated Markdown and a validated unified patch are
staged under ignored `docs/obsidian/` and `docs/obsidian-update.patch`. Code is entirely
inside the project directory.

## Analysis environment

Final verification: all 42 tests pass with the prepared local corpus. A fresh export
of only staged repository files also passes: 37 tests run and five corpus checks skip
with Capstone installed; without Capstone, dependency-specific checks skip as expected
(25 run, 17 skipped). The index was inspected for binary artifacts, credential patterns,
unexpected file modes, source syntax and broken relative document links. The updated
nine-note Obsidian patch was applied to temporary copies and compared byte for byte.

The local Capstone installation used for full checks belongs to Python 3.13.7.
Depending on shell working directory, unqualified `python3` selected Homebrew Python
3.14 without Capstone. This was a dependency/interpreter mismatch, not a corpus failure.
`requirements.txt` now records the existing dependency; dependency-free tests and
artifact-dependent tests are separated so a clean checkout reports skips correctly.

## November 10 continuation

The next pass moves beyond framing into narrowly supported arithmetic and code emission:

- LFCOMP's `1280/5280` MAC pair now matches complete independent native expressions.
- Two LINEDRIVE four-stage allpass chains match all twelve native stores, including
  subtraction signs. Exact packet contexts remain part of each recovered meaning.
- Mixed-packet stores in these examples capture incoming main values, while arithmetic
  produces new values. The symbolic gain model was corrected and regressions added;
  the previous twelve gain-chain comparisons still match.
- `bmc_subset.py` emits/inversely decodes the exact mix/gain and allpass fragment
  templates. Original JSON examples need no vendor artifact. Corpus checks recreate
  four independently checked stock regions byte for byte. Entry/exit, state/resource
  ownership, audio routing and scheduling are not provided.
- An explicit-policy 2/3/4-byte literal encoder rejects overflow and non-finite values;
  every two-byte encoding preserves its numerical value through decode/encode/decode.
  Its nearest/ties-to-even policy is not attributed to hardware conversion.
- CORE1 incoming queues, a far-call execution-mode veneer, synchronization handshake,
  manager exclusion requirements and stock program transitions have concrete traces.
  Six named test-oscillator controls identify literals in ordinary DSP4 code. Temporary
  transition programs are not misidentified as oscillator kernels.
- Normal `mi078` startup creates `/dev/ttyGS0` BMC IPC input/output workers. The UART4
  factory echo test did not prove this gadget was spare. Existing prepared shell
  packages also open it and can contend for the byte stream; no package was changed
  or installed. The host transport study records the trace and topology limits.
- Exported native arithmetic helpers provide finite-input shaping, feedback, breakpoint
  and voice-notification reference semantics. They have not been assigned new DSP opcodes.
- The bounded operand decoder now admits 41,710 observations, up from 21,178. A wider
  candidate initially admitted 46 extra observations whose exceptional short controls
  merely aliased existing literal bytes; those were removed. UPLIFT_EXCITER's two
  exponential argument/return windows now have native cut points, without claiming
  individual `20a*` instruction semantics or tracing through TRANSIENT's branch.
- The expanded operand layouts expose a weak old metadata association: GASSPH relative
  `0x2a8` predicts a three-byte literal matching its native default, while the prior
  width-four candidate appears to belong to neighboring MS_COMP metadata. Adjacency
  is now labeled as unproved ownership throughout the output, rather than calling the
  numerical discrepancy a firmware revision difference.

The GitHub API connection was retried once in this continuation and still failed.
No push or verification of private visibility is claimed. The Obsidian vault remains
outside the writable roots; updated documents and its patch stay staged locally.

The remaining practical blockers are a Fantom-specific externally callable loader,
resource/audio ownership, more of the ISA and its numerical/timing contract, plus
eventual hardware execution/readback and recovery validation. These findings do not
make an arbitrary existing C++ synth executable on the BMC render DSPs.

Final checks for this continuation: **78 tests pass** with all local artifacts. A
checkout containing only indexed text files also passes all available checks: with
Capstone, 69 run and nine corpus checks skip; without Capstone, 49 run and 29
dependency/corpus checks skip. Syntax, relative documentation links, whitespace and
the staged text/artifact boundaries were inspected. The 16-note Obsidian patch was
applied to temporary originals and compared byte for byte; all four original vault
notes were rehashed and remain unchanged. Vendor artifacts and detailed generated
evidence are still excluded from Git.

## Reviewed three-worker queue checkpoint

2026-11-10. All three workers delivered committed, clean file handoffs and were
confirmed idle before their branches were merged into main. The accepted worker
commits are transport `8e42a7e`, ISA `6c4678c` and kernel/audio ABI `0ecc0fe`.
Integration preserved those commits with three ordinary merges; no conflicts or
history rewriting were needed.

- [Host/CORE1 bridge](host-core1-bridge-followup.md) maps actual outer routes,
  service-specific replies, payload retention and CORE1 SysEx callbacks. CORE1 has
  raw MMIO read/write bodies whose window overlaps the DSP program apertures.
  This corrects any broad claim that there is no memory service. The host peer,
  physical endpoint mapping and safe managed loading remain unproved. The read
  helper's `0x50`-byte stack reservation can be exceeded by its permitted reply
  sizes; the 64-byte count clamp is not a safe-read guarantee.
- [Operand variants](operand-variants-and-macro-boundaries.md) independently match
  CHO_JU106's mono sum and two FETDRIVE cross-destination allpass expressions.
  Incoming A and result B are distinct. Exact operand-record provenance, two
  independent cutpoints and straight-line native windows are required. No general
  decoder/emitter expansion was accepted. TRANSIENT modifies both exponential
  returns before storing them, and six named oscillator literals occupy four
  unsupported packet headers.
- [Kernel/audio ABI](kernel-audio-abi-study.md) traces mutable `ff70/ff71` mute
  controls, shared relocated IO, five actual owner reservations, and effect lifecycle
  order. All-program loading ignores capacity; segmented methods check owner
  capacities and differ in destination rules. A full stock instance/parent graph,
  with live parameter changes in verified finite state, is the smallest supported
  probe design. No standalone executable wrapper is emitted.

Integration reviewed every changed source/test/prose file and independently read
the relevant raw host/native/Thumb instructions and data records. Checks reproduced
the three expression matches, six oscillator anchors, five effect placements,
native/firmware control schedules, mute/load ordering, both SysEx callback pointers,
program-aperture overlap and the reply-size arithmetic. A fresh bounded scan again
found zero direct BL calls to seven named helpers across 75 render-class bodies
through their first return. That negative result does not exclude inlining or
indirect calls.

The new saved-reply decoder initially accepted an unaligned offset with a valid
checksum, despite the observed read helper's alignment check. Integration added the
two-line rejection and a regression for offsets 1, 2 and 3. This is an offline parser
correction; no vendor firmware or handler was modified. Existing decoder/emitter
callers and the IPC exact-row test were checked; no unrelated interfaces changed.

Qwen returned no work to any worker: no draft or self-reported test was accepted.
The documented OMP smoke timeout and command-network EPERM/DNS/TCP restrictions
remain the exact blockers. The earlier cross-task-message approval pause was cleared;
workers then completed offline with Codex and local handoffs. REA provider setup was
not retried, and ordinary Capstone/file observations are not described as REA Evidence.
No approval/input request remains pending.

Final verification in main:

- **98 tests pass, no skips**, using the existing Python 3.13.7/Capstone 5.0.7
  environment and local corpus. All 61,334 packets in 588 nonempty segment
  observations reproduce with zero structural failures; tracked aggregate output
  is unchanged, including the known adjacent-symbol ownership conflict.
- A fresh export of indexed text files discovers the same 98 tests: with Capstone,
  85 pass and 13 corpus checks skip; without Capstone, 64 pass and 34 dependency/
  corpus checks skip. No artifacts or local symlinks were copied into that checkout.
- Source syntax, relative documentation links, whitespace, tracked file modes,
  credential patterns and text/artifact boundaries were inspected. All new binary
  fixtures are original authored instructions/records; vendor inputs/dumps stay local.
- The rebuilt **19-note Obsidian patch** applies with zero fuzz to temporary saved
  originals and reproduces every staged note byte for byte. Its filenames with
  spaces retain tab-separated patch timestamps. All four current vault originals
  still match saved SHA-256 values. No vault write was attempted in this pass.

Reproduction logs, independent disassembly and review records are ignored under
`local/integration-*`; the main README/report and queue status link the final studies.
No Roland target code, hardware, updater, shell payload or production Oscairn code
was executed or changed. GitHub private visibility and remote history remain
unverified because of the recorded command-network restriction; no push was attempted.

The next required evidence is an owned decrypted peer image or an existing
bidirectional stream/ring capture, a unit-specific recoverable entry/readback route,
the permitted manager task and complete state/scheduling context, physical routing,
and hardware measurements of gate behavior, precision and timing. The MMIO reply
size discrepancy must be resolved before treating that service as safe. Normal
ttyGS0 IPC still conflicts with prepared shell payloads. These are explicit blockers
to a runnable engine, not completed hardware experiments.

## Network and local-model verification after reopening

Jacob applied the network config patch and reopened Codex. Ordinary command networking
is still restricted, while the new automatic-review execution path permits bounded
approved network calls. GitHub DNS/HTTP succeeds through that path, and the configured
Mac Studio returns an actual authenticated `BMC_RUNNER_OK` through OMP with tools
disabled. No code or research finding was produced by this smoke test. Qwen can now
be used for bounded drafts followed by independent evidence/code review and tests.

The requested GitHub repository was verified private and its remote refs were empty.
The reviewed checkpoint contains only tracked text tools/tests/research; vendor inputs,
raw dumps, credentials and working vault copies remain excluded. Publication uses an
ordinary non-forced push, with a remote-commit comparison after upload.

The first push succeeded, and remote `main` was independently compared with local
commit `e5bc5a6`. The repository remains private. Reviewed filesystem access also
allowed the previously staged Obsidian update: all four originals still matched their
saved hashes, all 19 Markdown notes were written atomically per file, and every note
was verified byte for byte afterward. Original backups and the validated patch remain
local/ignored. No code, vendor artifact or firmware was written to the vault.
