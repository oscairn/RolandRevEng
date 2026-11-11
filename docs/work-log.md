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

## Continued offline pass: startup, lifecycle and oscillator ambiguity

From published checkpoint `5246bce`, independently reviewed and integrated:

- Worker `6308466`, integrated as `5f35157`: both CORE1 reset/scatter/runtime paths
  reach their initializer walkers and service constructors. Exact stack/frame and
  count-width analysis confirms the read-reply discrepancy in both builds.
- Worker `aee4885`, integrated as `efd6869`: generic effect replacement, temporary
  RAMCLR coefficient clearing, DRAM-IO reservation cleanup and DMA wait. Four parent
  numeric effect-entry candidates remain separate from call/timing semantics.
- Worker `86d2698`, integrated as `1553e14`: six independently owned oscillator
  literals match reference fields; two contexts constrain arity uniquely while
  two retain meaningful extension/arity ambiguities. General decoding is unchanged.
- Parent `29e54bf`: five host version-component slots and direct file-backed string
  verification, plus pinned public MC-101 source comparison. Neither establishes
  the missing Fantom stream peer or physical chip identities.

Four bounded no-tool OMP/Qwen analysis requests actually returned through the
authorized Mac Studio endpoint, serialized by a local process lock. Independently
checked useful offsets/slot arithmetic were retained where file evidence agreed;
invented identities, arity assignments, count behavior and reset/fence semantics
were rejected. No generated model code was accepted. Prompts/responses and upstream
source checkouts remain ignored/local. No upstream patcher/probe was executed.

Verification: **111 tests pass, no skips**, with the full existing local corpus.
A fresh tracked-text export passes the same 111 discovered tests with **16 explicit
corpus skips** (95 pass), using Capstone but no vendor artifacts. All new focused
tests and read-only reports were also reproduced during review. Source syntax,
relative documentation links and whitespace checks pass. Logs are under ignored
`local/next-*`. A bounded reproduction script in the host study was executed;
Apple objdump's ignored data-dump address limits were replaced with PT_LOAD reads.

The vault preflight matched saved hashes and found no new-note collisions. Reviewed
file access wrote **10 Markdown notes** (four new, six refreshed), backed up previous
versions and verified all **23 notes** byte for byte. The latest expected hashes are
in `local/obsidian-applied-next-2026-11-10.json`; the earlier manifest/patch is historical.
Only documentation went to Obsidian. Code remains in this project.

The next offline priorities are DRAM-IO clearing semantics, parent entry/return and
issue timing, opaque oscillator-control syntax, and the actual external peer when
an owned image or correlated recording becomes available. No hardware execution,
flashing, device access or shell-payload changes occurred. A runnable custom engine,
complete state reset, physical audio routing and hardware precision remain unverified.

## DRAM-IO, parent control flow and official cross-model firmware

Continued from `ef39d1b` and incorporated Jacob's suggestion to download other
Roland BMC firmware. All comparisons are offline; no updater, target or device ran.

- `0e0a79f`: actual CORE1 wait chunk/final-completion behavior, register arithmetic
  and IRQ/callback path. Bounded scatter-data expansion recovers initial done=1,
  registered=0; an independent decoder reproduced the complete output hash.
- Worker `65b13ea`, integrated as `a54e98a`: 92 owner-matched DRAM-IO records,
  low-23-bit address rewrite and the separate native clear loops' excluded start.
  Hardware clearing coverage remains open.
- Worker `5287ec4`, integrated as `16f5b83`: nested organ Od connects the fifth
  DSP1 context; the native DSP4 routing list has 24 segments, beyond the original
  inventory limit. Shifted `00aN` references and four native IO callbacks constrain
  functional order without admitting call/return timing or a universal stereo ABI.
- Common QSPI reader `26b6bbf`, integrated as `a05ce1a`: bounded two-member C1A
  container inspection, original ranges/hashes and explicit synthetic-view identity.
  No inferred zeros fill an unbacked ITCM gap. Member checksum fields remain
  observed values; a simple additive sum does not validate the SDRAM member.
- MC-101 worker `851ec7a`, integrated as `0cb5a37`: official v1.82 download,
  exact 324-byte Fantom MMIO prefix/epilogue, wait body differing only in three
  BL relocations, and a 44100 scaling constant versus Fantom's 48000.
- JUPITER-X worker `c13945c`, integrated as `efba6ee`: official v3.03 download,
  exact 158-byte RAMCLR and 14-byte rewrite windows, eleven list segments with
  two record spacings instead of Fantom's four. Original-member offsets were
  independently checked. A truncated documentation hash was corrected before merge.

The official ZIPs, tar updates, C1A/C0A components, extracted members, source pages
and local manifests stay under ignored `local/crossmodel/` and worktree scratch.
Their identities and actual shared/different code are recorded in the studies.
Identical crypto header mode/key indices do not establish identical keys.

Two additional no-tool Qwen drafts returned for wait and clearing arithmetic.
Useful mechanical observations were independently reproduced; incorrect overflow,
counter rationale and range arithmetic were rejected. No generated code was
accepted. Exact cross-model comparisons did not require Qwen.

Validation: **132 tests pass with no skips** using the full local artifacts.
A fresh tracked-text checkout discovers the same 132 tests: **111 pass, 21 corpus
checks skip explicitly** with Capstone present and no copied vendor inputs.
Focused checks, report CLIs, original byte-window hashes, syntax, relative links,
tracked-text boundaries and whitespace were reviewed. Logs are ignored under
`local/third-*`; no production Oscairn code or existing shell payload changed.

The vault update checked the latest saved hashes, found no collisions, backed up
changed notes and wrote eight Markdown notes (five new, three refreshed). All
**28 notes** match their staged bytes afterward. The latest hash manifest is
`local/obsidian-applied-third-2026-11-10.json`; earlier manifests/patches remain
historical. No scripts, images or vendor bytes went to the vault.

Next: use the two preserved model images to constrain DRAM-IO counter/source
semantics and render condition/return timing. Full hardware state clearing,
physical routing, permitted manager task entry and the external Fantom peer still
block a runnable engine. Shared code and passing offline checks do not establish
firmware compatibility, a safe live read bound or successful hardware execution.

## Conditions, owner contracts, key provenance and Fantom access

Continued from `788a0f1`. The main checkout reviewed isolated worker commits and
reproduced their focused checks against the retained artifacts:

- Condition/return `60749b5`: four native predicate inputs match exact DSP
  fields; `00f8` has no explicit PC operand in the scoped packets. Hardware
  condition bits, return storage and timing remain unassigned.
- Task context `3f6cbf4`: normal startup registers RXDT/ASGN through software
  IRQs, with actual priorities and queue gates. These are not established OS
  threads or a proven safe custom callback/loader entry.
- Owner/clear interface `1510a1f`: JUPITER-X constructors explain eleven manager
  owners and two layouts. Counter access and global clear are distinct APIs;
  clear units, shared completion synchronization and per-instance safety are open.
- Official SH-4d v2.00 and TR-8S v3.00 `b69b6df`: preserved downloads/manifests,
  another split CORE1 comparison and a package with only encrypted CORE0 and
  initialization data. Shared code does not prove compatible hardware maps.
- Key-provider `33d237a` and material scan `6227df8`: no confirmed key/provider
  in seven readable images; no documented MC-101 ROM copy in 27 scoped objects
  totaling 146,004,684 bytes, including all retained tar components and five
  verified initial-data expansions. Unknown/transformed keys are not ruled out.
- Access audit `3b09159`, writer follow-up `93de9b2`: stock qctest contains a
  login-shell endpoint, but mode 3, effective UID and usable terminal remain
  unproved. One concrete mode writer was identified among recognized references;
  its direct callers pass 0/1/2. This is not an all-writers/unreachability proof.
  The actual mi078 I2C path and MMC boot autodetection correct older assumptions.

Root comparison `7696c65` pins six C0A containers and measures distinct nontrivial
eight-byte blocks inside exact validated payload bounds. Fantom bmc0/bmc1 share
14,335 blocks; each other model shares 8,124–15,985 with bmc0. Under the reported
ECB scheme this supports testing a recovered MC-101 key against Fantom. It is
not key recovery or plaintext validation. The public decryptor depends on an
external ROM dump absent from the retained checkout; its reported B6 table slot
is `012034c0..012034d7`, not a verified Fantom/i.MX read address.

Direct OpenPGP header inspection also confirms the stock update's encoded S2K
count byte is `ff` (65,011,712 input bytes), correcting the old `c8` wording.
No update plaintext, consumer, passphrase or BMC decryption was recovered.
Retained GPL uboot/linux/imxboot tars were hash-checked and preserved locally;
their outer ZIP and exact deployed build equivalence remain unverified.

One bounded no-tool OMP/Qwen review returned for the cross-model checker. Its
mechanical observations were checked against source/tests; its statement that
only synthetic tests exist was rejected. No generated code was accepted.
The installed pyelftools 0.33 dependency is now declared for ELF reproducibility;
no installation or provider configuration change was needed.

Validation: **157 tests pass, no skips**, with full local artifacts. A clean
tracked-text export discovers 157: **129 pass, 28 artifact checks skip explicitly**.
After the bounded writer follow-up, its two affected checks were repeated against
the corpus and clean export (two pass locally; one pass/one skip without the ELF).
Syntax, relative links, tracked-text boundaries and whitespace were checked.
Logs and review outputs remain under ignored `local/fourth-*`.

The vault preflight matched all 28 prior managed notes and the newly managed
passphrase note. Seventeen Markdown notes were written (eight new studies and
nine corrections/refreshes), with prior text backed up and all **37 notes**
verified byte for byte. The current manifest is
`local/obsidian-applied-fourth-2026-11-10.json`; earlier patches/manifests are
historical. Code and all vendor artifacts remain in the project, not the vault.

Next evidence is an applicable BMC ROM/runtime or peer artifact, or a proven
console route, alongside further condition/return and clear-engine semantics.
No live device, target code, updater, shell package, flash writer or exploit was
run or changed. Recovery, secure-boot state, physical routing and render timing/
numerics remain unverified; there is still no runnable custom BMC engine.

## Outbound flow, clear IRQ identity, factory dispatch and stereo tap semantics

Continued from `9ea3262` at Jacob's request. Three isolated workers returned
commits; the main checkout reviewed their code, ran focused tests and inspected
the relevant native/firmware windows independently:

- Factory UI `e6b6270`: 34 initialization copies resolve the intro pointer and
  33 test rows / 28 unique objects. Actual vtable dispatch is connected to the UI
  loop. Modes 0/1/2 clear the intro and select groups; case3 deliberately does
  neither. No enabling mode3 path is recovered. Mode0's additional installed
  daemon side effect is documented, with no activation procedure recommended.
- Clear completion `c1a942c`: event17 hex joins callback slot `200a1900` to
  vector `01100180` / IRQ80. Registration precedes priority/enable/mask setup;
  the handler reads/zeros status, snapshots it, increments a counter and invokes
  the installed callback. Raw portal access gives per-element selector evidence,
  not a proof of bulk-clear units or named IDM/EDM Boolean mapping. Integration
  additionally rejects external-vector identities beyond the supported IRQ range.
- Stereo taps `bee7f67`: exact TS808 controls/extensions `044f/0000`, `454f/0004`,
  `048f/0000`, `458f/0004` match six native arithmetic stages with live coefficients
  and exact state-record provenance. Integration corrected one documentation PC
  from `20866c` to the actual D-register load `208668`. No decoder/emitter change,
  global register mapping, numerical or scheduling claim was accepted.

The root outbound study follows the service-reply veneer to type3 packet words,
the 511-usable-word software queue, TXDT task2/IRQ230 and the 63-usable-word shared
ring. Its reported free-count includes the sentinel slot. Failed-attempt counters
are not dropped-message counts; queue-full rejection and four tight full-ring
retry loops prevent treating local completion as a universally lossless protocol.
External conversion, peer identity and safe manager ownership remain missing.

The same pinned MC-101 revision reports different boot-ROM hashes in its README
and ROM study. Both identities are now searched as author-reported candidates;
the scanner explicitly refuses to authenticate either. Rerunning the 27-object /
146,004,684-byte scope still finds no documented ROM copy or actual key candidate.
No decryption or arbitrary key guessing occurred.

One no-tool OMP/Qwen review returned in 98 seconds. It raised useful coverage gaps
in the queue checker; integration added explicit success-counter/peak and complete
free-count instruction anchors, then repeated the affected tests. Its claim that
the prose had already acknowledged those checker gaps was unsupported and was not
accepted. No generated code or unverified model-derived address was used.

Validation: the integrated **174-test suite passes with no skips**. A clean
tracked-text export discovers the same 174: **140 pass, 34 artifact checks skip**.
After the checker-anchor refinement, its three tests passed again locally, with
two pass/one skip in the refreshed clean export. Report CLIs, Python syntax,
relative links, tracked-text boundaries and whitespace were checked. Detailed
logs, native traces, model input/output and reports stay under ignored `local/`.

The vault preflight matched all 37 saved note hashes. Four new studies and ten
refreshed notes were applied as Markdown only, with backups and **41 notes**
verified byte for byte. The current manifest is
`local/obsidian-applied-fifth-2026-11-10.json`. Code and all vendor bytes remain
in the project. Earlier manifests and patches are historical.

Still open: a verified Fantom execution/recovery route, actual CORE0/ROM/peer
evidence, general ISA/register semantics, clear-count/domain rules, owner-safe
state transitions, physical audio routing and hardware timing/precision. No
instrument, plugin, updater, shell package, probe or flash operation was executed
or changed; these findings do not constitute a runnable custom synth engine.

## Envelope selectors, memory naming, feedback variation and a semantics ledger

Continued from `c56b1ed`. The main checkout integrated and reviewed three isolated
worker commits plus an independent coefficient-envelope study:

- Official build `03769cc`: a fresh direct Roland v1.08 ZIP is byte-identical to
  the retained corpus. Its two nested tar inventories and selected member hashes
  close source-to-qctest provenance. Current support HTML says JUL2026; checked
  older detail links returned not-found and supplied no alternate build. The known
  37-record QSPI resource master matches all 29 bmc1 C1C payloads plus eight extras;
  it is not a newly found Linux recovery image. Four existing factory tests passed
  on the fresh extraction. Integration independently checked ZIP/qctest/manifest
  hashes and the actual support text.
- Domain names `988ab16`: the diagnostic's monitor labels join false/IDM and
  true/EDM at software level. Its duplicated control-register read remains visible
  and appears in peer firmware too. Native access/clear stubs and the separate CPU
  ITCM checksum diagnostic do not resolve physical domains or bulk-clear units.
  Integration excludes candidate loads spanning the unmapped ITCM/ERAM gap.
- Feedback variation `cb5fd40`: two later TS808 contexts match 12 native arithmetic
  definitions, 16 state accesses and 12 coefficient loads. Products precede stores
  of unchanged inputs; the two first/second MAC stages keep different contributions.
  Equal coefficients on ports3/7 explicitly leave source selection unresolved.
  Integration found and fixed a retained-source checker edge: a destructive FMUL
  destination could overwrite the supposedly preserved input. The checker now
  includes that instruction in its alias-preservation check, with a counterexample.

Root study `27bc6d8` traces live coefficient envelopes separately from program
literals: bank capacities/stride, kind6 symbols, generic dispatch that can bypass
the envelope, EnvTC's 16 selectors, manager wait/exclusion and six IRQ65..70 paths
sharing completion bit1. Selector10 means nominal12 ms in the native table's
44100-based calculation, not a calibrated Fantom duration. The native manager's
normal operating-query path returns false and cannot validate hardware completion.
The control-semantics ledger consolidates existing exact arithmetic proofs and
unsupported forms without extending the decoder or emitter.

One bounded no-tool OMP/Qwen review returned in 61.3 seconds. Integration checked
its ABI/selector observations and added explicit flag-base/load/store anchors in
response to a real coverage gap. Its assertion that the event-reference2 setup was
absent overlooked existing checked instructions and was rejected. Source table
values were inspected directly; no generated code or model-only hardware claim
was accepted. Prompts and responses remain ignored/local.

Validation: **191 tests pass with no skips** against the full local corpus. A
clean tracked-text export discovers the same 191: **152 pass, 39 artifact checks
skip explicitly**. Focused counterexamples, report CLIs, native windows, syntax,
relative links, tracked-text boundaries and whitespace were reviewed. Detailed
outputs are ignored under `local/sixth-*` and named study reports.

The vault preflight matched all 41 previous hashes. Five new studies/ledger and
eight refreshed notes were applied as Markdown only, with backups and **46 notes**
verified byte for byte. The original ISA note's accumulated status prefaces were
consolidated into a short current index; its historical findings remain. Current
manifest: `local/obsidian-applied-sixth-2026-11-10.json`. Code and all vendor
artifacts remain in the project; prior manifests/patches are historical.

No key, alternate factory activation or readable recovery/CORE0 peer was recovered.
Hardware timing, precision, ownership-safe transitions, bulk-clear units and a
verified live entry/recovery route remain open. No target/plugin/device/update,
flash operation or prepared shell package was executed or modified. This checkpoint
adds reproducible offline semantics and interfaces, not a runnable custom engine.

## Functional fragment emulator checkpoint — 2026-11-10

Continued from `51a92ef` with three isolated workers and local OMP/Qwen support.
The new `bmc_emulator.execute_fragment` steps actual packet bytes for the strict
60-byte dry/wet and 82-byte allpass profiles. It validates complete streams and
all input maps, rejects missing/non-finite values and unknown forms, uses old-port
arithmetic/stores, commits packet writes locally and returns independent snapshots.
Caller maps are preserved on success and failure. No whole-template symbolic
predictor is substituted for packet execution.

Independent tests pin the actual four stock byte spans and full image/program
identities, rerun the native polynomial proofs, compare every eight-port trace
and all stores, and carry the two real LINEDRIVE allpass outputs directly into
its real tail. The corpus tests made 33 fragment calls across asymmetric vectors,
sequential purity checks and adjacent-fragment composition. No plugin/native
sample processing or device was executed.

Original audio demonstration: 12,000 frames each of a mono allpass impulse and
stereo dry/wet tones. Explicit host history/delay wiring supplies inputs; this is
not reconstructed stock state cadence. Float impulse energy is 0.25 and the mix
reference maximum error is zero. WAV headers/payloads and summaries were inspected.
48 kHz and PCM16 are software output choices, not BMC calibration. Outputs stay
ignored in `local/seventh-fragment-demo`; no listening claim is made.

The complete-program inventory verifies all 75 paired render descriptors and
compares five primary streams. LINEDRIVE is the next target, leaving 42 whole
packets outside exact fragment admission plus parameter/history/wrapper contracts.
FETDRIVE has 51 unadmitted packets and unresolved header forms; shorter CHO/GATE
streams are not easier by size alone. Structural decode is not execution coverage.

Qwen returned three bounded drafts/reviews. The initial large implementation
request timed out; a smaller core-only request with per-run thinking disabled
returned code. Review accepted only its useful packet-loop/copy/trace structure
and corrected tag, IO, target-address, extension, store-commit, bytes, uninitialized
and numeric-boundary defects before execution. Independent tests were authored
before acceptance. The oracle review's unsupported same-chain aliases and trace
objections were rejected; its state-boundary suggestion led to the real adjacent
composition test. Target-review range arithmetic was checked, while invented
ranking/flush/scheduling conclusions were rejected. Prompts, outputs and correction
ledgers stay ignored/local; no persistent provider configuration was changed.

Validation: **212 passing tests** with the local corpus: a 207-test full discovery
run plus all five newly integrated corpus tests. A clean tracked-text export
runs all 212: **167 pass and 45 artifact-dependent tests skip explicitly**.
Core/demo tests require no vendor bytes or Capstone. Relative Markdown links,
tracked-text boundaries and whitespace checks pass. No CORE0 key, verified hardware
entry/recovery route, complete stock-effect emulator or hardware engine follows
from this functional milestone. Silicon precision, timing and native-plugin audio
remain untested.


The bounded LINE prefix follow-up checks four width-3 fields at `14/17/24/27`,
with defaults `0/0/1/1`, against eight native records. Only `14/24` have identified
native ownership. Two actual store destinations and native input-mix expressions
are anchored; split-field counterexamples show why equal defaults do not prove
aliases. Outgoing port state, store timing and the two unowned-field relationships
remain unresolved; no extra opcode or fragment was admitted.

Vault preflight matched all 46 previous hashes. Seven Markdown files were written
with backups and atomic per-file concurrent-edit checks; **49 notes** verified
byte for byte. The original ISA status now links the interpreter, validation and
complete-program inventory. Current manifest is
`local/obsidian-applied-seventh-2026-11-10.json`. Code, WAVs, reports and vendor
bytes remain in the project. No live action, updater, flash or prepared shell
package was executed or modified.


## Roland vault organization — 2026-11-10

At Jacob's request, moved all 52 Roland research and related planning Markdown
notes from `Projects/Oscairn` into `Projects/Oscairn/Roland`. This includes the
49 previously managed notes, the engine overview and two related planning/draft
notes. All prior managed hashes matched; every source was backed up and all 52
moved files verified unchanged. A no-clobber hard-link/unlink move preserved the
contents and refused destination collisions. No non-Markdown file was moved.

All moved titles are unique across the 553-note vault. The 67 title-based links
to these notes remain resolvable, and no explicit old-path note link required
rewriting. No canvas/base reference to the old note paths was found. Original
research, code, generated audio and vendor bytes remain in the project. Latest
location/manifest: `local/obsidian-location.json` and
`local/obsidian-applied-roland-move-2026-11-10.json`; old sync scripts/manifests
are historical and must not be reapplied to the old folder.

Continued complete-effect work in three independent scopes: LINE parameter
literal ownership/grouped writes, native shaping/quantization, and circular
state/history cadence. Strict interpreter admissions remain unchanged until each
new context has independent evidence.

## Conditional LINE reference and broader firmware check — 2026-11-10

Continued from `18cf845` after the Roland folder move. Three isolated workers
checked parameter groups, native numeric kernels and native state. Root reviewed
the source, integrated the changes and built a conditional original-signal pipeline.

- The native parameter manager updates one first-record representative while the
  firmware loops a descriptor's count with 12-byte records and one saved float.
  Actual SetAlg groups connect EC/F0/118/11C and E6/E9/112/115. The early input
  pairs14/17 and24/27 remain unresolved. A bounded static inventory includes 665
  native and 616 firmware candidates, with known rational positive controls but
  no matching early-prefix group. Runtime/separate writes and other layouts remain
  outside that negative result. Integration corrected literal-call tracing to reject
  intervening branches/returns, with original synthetic regression instructions.
- The native ring is 2048 doubles with physical index `(address+P-O)&7ff`; a separate
  core sync advances O after routing/DRAM-IO. All 46 callback indexed accesses are
  accounted for, including two pre-scaled-index accesses the older tracer missed.
  Twelve prior-write/read relationships hold with fixed P, one step and no overwrite.
  Shared core zeroing is not an instance reset. Prior smoother q at 3/6 must remain
  separate from the post-rational current factors 27/28.
- A pure channel oracle checks native signed64/fixed32 conversion, wrapping shift9,
  strict mode/sign selection, clamp constants, float32 live coefficients, fused
  smoothing and rational arithmetic. Original counterexamples distinguish a changed
  quantizer bin under reassociation, one-ULP fused/unfused results and signed shift
  wrap. It requires Python 3.13+ math.fma and declares an IEEE policy, excluding
  conversion exceptions/unknown FPCR behavior. Review also added destructive-alias
  guards to the synthetic sign/smoothing recognizers. No DSP admission was added.
- `render_line_reference.py` calls that host oracle, executes the two strict allpass
  chains and mix tail, and performs explicit conditional native ring steps. Its
  2056-frame sequence matches separate direct delay equations exactly through wrap.
  The 12000-frame WAV has peak 0.0998168982 and max factor 0.0248665508. Header,
  payload and JSON were checked; independent state review found no issue. The
  unknown prefix/return/mute bytes are not executed. Experimental controls, fixed P,
  cold ring and one step/frame are explicit fixtures, not measured parent cadence.
- Downloaded official AX-Edge 1.11 and JUNO-X 1.12 archives, pinned parent/member
  hashes, checked both C1A CRCs and scanned all 10 tar members within documented
  bounds. JUNO-X has all three exact Fantom comparison windows; AX-Edge has none
  of those exact windows. Their CORE0 payloads share 13659/15780 nontrivial blocks
  with Fantom bmc0. No reported ROM identity, key-table/B6 address literal or key
  candidate was obtained. Unknown compression/ROM revisions and transformed key
  material remain outside this raw scan. No decryption or access-route claim.

Three bounded no-tool Qwen reviews returned through the existing Mac Studio
profile with per-run thinking disabled. Their observations were checked against
source and independent tests. Wrong constants, missing-right-mode claims,
invented alias/grouping and four false ring contradictions were rejected. No
model-only opcode, register identity, state cadence or hardware claim was accepted.
Prompts, reports, raw bytes and audio stay ignored/local.

The current vault update targets `Projects/Oscairn/Roland`. All 52 moved-note hashes
matched, five new studies were added and ten Markdown files written with backups
and concurrent-edit checks. All 57 notes verified byte for byte; new-note creation
also refuses collisions atomically. The keyboard-planning note gained a short
historical-status preface pointing at later access/recovery corrections, preserving
its original text. Current location/manifest is `local/obsidian-location.json` /
`local/obsidian-applied-eighth-2026-11-10.json`. No code or audio went to the vault.


Validation: **243 tests pass with no skips** against the complete local corpus
(65.093 seconds). A clean tracked-text export runs the same 243 tests: **191 pass,
52 artifact-dependent checks skip explicitly**. Pure/reference tests run without
vendor bytes; the FMA oracle requires Python 3.13+. All relative tracked Markdown
links and whitespace checks pass. WAV headers/frame payloads, fixture summaries
and tracked-text/vendor boundaries were inspected. Detailed results are under
`local/eighth-*`; no broader repeat is needed after documentation-only edits.

A complete stock DSP byte stream, arbitrary synth compiler, CORE0 decryption,
verified access/recovery route and silicon timing/precision remain unimplemented
or unverified. No plugin, target, updater, flash, MMIO probe or prepared shell
package was executed or modified.

## Scratch transfers and return placement

The 80-byte dry/wet profile adds the stereo store and reload pair from LINE
and FETDRIVE. Both callbacks reuse the same two native constructor records
for the writes and subsequent reads. The corpus test checks the record and
ring provenance, output expressions and packet results. The conditional LINE
WAV is byte-identical after replacing host scratch writes with the interpreter's
stores. The primary-program inventory now leaves 40 LINE and 49 FETDRIVE
packets. The co-issued output and `00f8` packet remains outside the profile.

The descriptor-checked return inventory found 79 base-word occurrences across
75 primary streams. Two confirmed family-3 placements in JDMLT_B are internal
to its longest segment. Another two internal placements have unresolved
headers. The scan establishes placement. Return destinations, execution of
successors and co-issue behavior require further evidence.

Qwen's bounded review highlighted malformed lengths, aliased indices and
state preservation for tests. Its proposed hardware aliases and bus effects
lacked evidence for this logical-cell model. The synthetic and corpus tests
cover the accepted addresses and reject swapped, duplicated, out-of-range
and trailing operands. Seven Roland vault notes were updated and all 57
hashes verified.

The full local suite passed all 246 tests. Focused emulator and emitter tests
also passed after tightening the scratch profile's input validation.

## JDMLT_B continuation evidence and stereo input

Native JDMLT_B SetAlg and SetSequence connect the render list, the
width-two field at `8018`, and the three calls through the four-entry
native table. The four function bodies load constructor records tied to
transfer operands in distinct DSP regions. The first callee writes the
ring cell named in the packet after the `208` return candidate. The
second writes the cell named by a transfer co-issued with `00f8` at
`332`. The match `43c2 * 2 = 8784` is a separate candidate transfer
from the `0080` packet to the terminal site. The continuation source
and issue order are still unresolved. Qwen incorrectly assigned the
first pool word to a family-1 ALU operand. The checked width-three ALU
operands start at pool offsets 2 and 5.

The emulator now steps the stereo input packet from both observed banks
and the conditional reference WAV remains byte-identical. The bounded
`4822` scan covered 12,365 native render packets and 36,793/12,176
framed CORE1 packets. Its four native and ten bmc0 occurrences all have
literal values `0,0,1,1` across the two adjacent arithmetic packets.
bmc1 has no occurrence in this inventory. Counts include repeated
segments and do not supply independent parameter variations. The
scan is retained locally as `local/tenth-prefix-corpus.py`.

The full local suite passed 250 tests. The focused selector tests also
passed with the final SetAlg and native output-use anchors. Seven Roland
notes were updated and all 57 verified.

## Fantom LINE placements and original one-pole execution

The pinned bmc0 render list provides all five LINE owner placements.
The reader checks program hashes, packet boundaries and the recorded
DM and coefficient reservations. It uses actual transfer operands to
bind input slots, smoother history, allpass state, wet inputs and scratch
stores. In particular the firmware right smoother reads base plus 6
and writes plus 5, unlike the desktop fixture's 7/6 pair. The five
placements match the desktop fixture through wrap. The 12,000-frame
DSP4 render is byte-identical to the previous WAV.

The original one-pole fixture assembles two 80-byte variants. The host
alternates them and each variant reads the previous output and stores
the next. An asymmetric impulse sequence checks the state carried by
the packets. Separately, the stock readback comparator checks one
578-byte logical segment and identifies the opening mute-bit-only case.
The runtime owner and physical capture route still require independent
hardware evidence.

Qwen's review was checked. It confused IO addresses with wet memory,
assumed global relocation arithmetic, and suggested the opposite
history relation. The implementation uses exact half-open slices,
literal operand identities, and read=write+1 in the reference model.
All 255 tests passed with the local corpus. Four Roland Markdown notes
were updated and all 57 verified.

## Asymmetric input-mix literals on JUPITER-X

The expanded scan found two `4822 / 1940` packets with `(1, 0)` literal
pairs. Both belong to the same JUPITER-X list at `61218324`, in relocated
segments. The setup path supplies that list to the DSP manager. This rules
out a universal equality requirement for the encoded pair. The two copies
share one context and do not establish which ports hold the result. The
BITCRUSH native callback gives a separate weighted-sum comparison for
`4812 / 1500` with genuinely different literal values.

The renderer now models the two native mix coefficients explicitly and tests
that they only affect the wet path. Its default Fantom WAV is byte-identical
to the earlier fixture. No new instruction entered the strict interpreter.
All 258 tests passed with the local corpus. A clean export passed 199 tests
with 59 artifact-dependent skips. The ordinary OMP attempt failed DNS. The
network-enabled retry returned a Qwen review, which suggested seeking an
asymmetric context. It overclaimed what literal references and main-port
store ordering establish. Those observations alone do not show that a
referenced literal contributes to the result or that the LINE auxiliary
stores capture an incoming value. No generated code or semantic claim
from the review was used.

## Weighted-mix ports and a LINE prefix candidate

TRECHO provides the independent `4812 / 1500` output store and confirms it uses
the previous A/I1 pair when it co-issues input loads. BITCRUSH's unequal
constructor coefficients fix the native weighted-sum term order. BINHALL
independently ties unequal width-three literals to a port-5 result. BRHL traces
`2424 / 0004` into the next `afe4` store. LINE's `4822 / 1940` shares the nonliteral
bits of the TRECHO form and now has a falsifiable B-port hypothesis. UPLIFT
EXCITER supplies a port-3 store and an independent I1 term for the neighboring
`3464 / 0002` long operation. LINE's paired extensions `0004/0004` give a
candidate shared B addend across both channels. Full LINE prefix state and
silicon execution remain open.

OMP/Qwen returned a bounded review. It correctly flagged the opaque BITCRUSH
interval. Its generic call for a BITCRUSH trace was narrowed to a JUPITER-X
observation of the exact target form with unequal literals. The symbolic
comparisons were checked directly and no generated code was used.

## Executable stock-mix prediction and quantizer boundaries

The stock JUPITER-X probe reads both relocated copies and predicts `0.25` at
the following B store for unequal inputs `(0.25, -0.125)`. The experimental
Fantom render uses the original four stock literals. All five bank outputs
match the native-mix reference through ring wrap. The 12,000-frame WAV is
byte-identical. No hardware trace entered the comparison.

The LINEDRIVE quantizer study checks both packet windows and separates the
transfer-family `b9b2` from the exceptional `ac99`. BITCRUSH contains two `ac8e`
packets and 16 native fixed32 conversions, which prevents a one-to-one match.
FETDRIVE uses the same native fixed shift by nine with `9c59/9ed9` in its
corresponding DSP windows, providing another encoding to compare.
Qwen reviewed the argument and proposed an asymmetric capture. Its claim
that the native mix treats the two inputs independently is contradicted by
the native shared term at `2df898`. No generated code was used.

## FETDRIVE through the first shaped store

Native source-field binding and register preservation connect each FETDRIVE
mixed-input reload to the first post-quantizer T store. The native clamp,
distinct affine constants, square and post gain are checked end to end.
The Fantom's five relocated copies have a drive scale of `1/256` and stored
post gain `0.9187498092651367`. Desktop DSP literals use approximately
`0.00154763` and `1`, respectively. The operand brackets still leave the
two exceptional controls and their state effects unresolved.
Native `SetAlg` independently writes `44100 / rate` to both post-gain fields.
The Fantom's stored post gain agrees with a 48 kHz divisor within one literal step.

Qwen reproduced the native order but overstated what the correspondence
establishes about the DSP pipeline. The retained conclusions are from the
checked byte and native dataflow evidence. The hardware plan now uses the
Fantom-07 as the sole physical target.

## VMCP and RING limiter evidence

VMCP's standalone `9ed9` is bracketed by native stores around a bipolar clamp
with independent pre-scale and post-bias literals. RING independently brackets
the same native clamp across a co-issued `9ed9` context. VMCP's later native
shifts use distinct packets associated with `bc12` and `bcd4`. This narrows the
FETDRIVE conversion candidate to the preceding `9c59` while preserving the
strict interpreter boundary.

The four Fantom VMCP placements retain the checked controls. The Thumb
threshold setter writes the width-three field at `4a` and its 128-entry
float table matches the native threshold values exactly. Qwen overassigned
both scaling and clipping to the standalone control. The evidence binds
the scale to a separate literal and leaves register and issue effects open.

## Live coefficient fixed-point shifts

The VSODDSAW and VSODDSTW native callbacks independently transform C1 with a
four-bit shift after binary32 conversion. The DSP load before `bcd4` is port 3
in both cases. Base VSOD uses `fdd4` after a port-7 C1 load and stores the
converted value through `ffe0` while a separate port-3 path uses C0. FORMANT's
`bcd2` window traces a different C2 record to a shift by two. GASSPH adds the
`fdd2` counterpart with a computed input and a port-7 store. The exact
contexts are checked offline across the native artifacts and 13 stock
Fantom VSOD placements. Strict DSP admission remains unchanged.

Qwen reviewed the comparison and correctly cautioned against reading the
bit-8 difference as an established operand rule. The checked report derives
its port and value paths from the artifacts.

## FETDRIVE short gain path and first-store renderer

The TRANSIENT short-gain pair `1406/5506` independently anchors A and B
as input sources and ports 1 and 5 at the following stores. Together with
the FETDRIVE C1 load and matched native scaled product, this supports
port 1 as the incoming operand for `9c59`. The pair `9c59/9ed9` still
lacks an independently observed intermediate, so its exact writeback
remains open. Qwen reviewed the path. The retained port claims follow
the packet transfers and matched native constructor records.

`render_fetdrive_window.py` predicts the first stereo stores from a
pinned stock placement and the native numeric policy. With the stock
drive scale and supplied C1 of 0.5, mixed input `±2^-24` quantizes to
zero and `±2^-23` reaches the first nonzero bin. Probes immediately beyond
each clip limit saturate at the corresponding sign. All five placements
give the same predicted output for the test fixture. The WAV covers
only the first stores and uses software-generated input.

## Stock search for an intermediate `9c59` result

The framed control-slot search covered 241,742 packets in ZENOLOGY and
the recovered Fantom, JUPITER-X, MC-101 and SH-4d CORE1 lists. All 58 hits
reproduce the FETDRIVE gain, conversion candidate and clamp candidate
in three consecutive packets. The nearby GATE `8ed9` variant appears in a
three-control bundle. Its native clamp interval also contains a conditional
selection, leaving it insufficient for an isolated port assignment.

## Stored fixed-point conversion and LINE source trace

The VSOD prefix at logical `004..02a` now has a 38-byte emitter,
strict inverse decoder and packet execution profile. Native store
`273984` anchors the converted C1 value to port 7 and store `2739a8`
anchors the half-sum times C0 to main A. Five Fantom placements match
the profile with their actual assignments. Boundary checks exercise
binary32 reads, fixed32 truncation, signed64 wrapping and co-issued
store order.

LINE source records and native multiply uses strengthen the port-2
input candidate for `ac99`. The field pattern agrees with six other
checked shift controls. LINE's first observable store still follows
other nonlinear operations and smoothing.

GATE's later clamp and store at `313fa8` bind to the next packet's
main-A store at operand `ba`. That narrows the earlier GATE comparison
to an observed bundle output while retaining its co-issue ambiguity.

All 284 tests passed. A separate focused pass checks the later GATE store.
Qwen reviewed the prefix implementation. Its proposed scale mismatch
misread hexadecimal `0x20` and the verified `2^-32` constant, and its
store objection extended past the fragment boundary. The checked byte
slice, native instructions and numeric boundary tests resolve those claims.

## Oscillator control reuse and short literal stores

Qwen drafted the control-slot inventory extension. Its scanner logic
was retained with readable field names. Its synthetic packet lengths
were corrected and its mocked family decoder was replaced with the
actual decoder. The synthetic check now distinguishes a family-1
control, an unresolved header and a payload-only occurrence.

The six-artifact scan finds 119 family-1 `3074` occurrences and 17
under unresolved headers. Exact `2d64/0c3b` occurrences remain
confined to the ambiguous Fantom oscillator packet. The FREQ_SHIFTER
comparison independently binds two owned short literal records to
following port-3/port-7 stores. It supports the oscillator's short
`3074` interpretation under the stated fixed-arity assumption.

## Native LINE execution fixture

The pinned ARM64 LINE callback is position-independent and has no helper
calls or external branches. It now runs in a separate macOS ARM64 command
with an explicit pointer graph, reconstructed constructor data, supplied
live coefficients and cold circular state. This is the first direct
native callback execution in this research.

The 12,000-frame render has 11,804 exactly matching frames against the
conditional Python reference. Its maximum sample difference is
`1.3877787807814457e-17`. The isolated test crosses ring wrap at
2,056 frames. Host FPCR was zero. Exact BMC program execution,
hardware scheduling and silicon precision remain unverified.

All 287 tests passed. Qwen's optional Python-only review of the native
fixture timed out at 180 seconds. The callback execution, memory-lifetime
checks and numeric comparisons were verified locally.

## OSC phase boundary and frequency ownership

The MFX OSC phase interval now has a native instruction/constructor
checker, a bounded numeric reference and a subprocess execution comparison.
All 272 native probes agree, including the asymmetric negative-odd
boundary and signed32 normalizer wrapping near the conversion limit.
Four Fantom placements retain the checked packet sequence. Their
stored increments support the existing 48 kHz rate hypothesis.

Qwen drafted the phase rule and tests. Its duplicated validator was
replaced with the existing finite-number helper and its positive-odd
expected values were corrected. Direct native probes then supported
extension through the non-overflowing signed32 conversion domain.
The executable-memory lifetime helper is shared with the LINE fixture.

An ignored whole-OSC native experiment, `local/native-osc-errors.py`,
exhibited sign changes at some waveform extrema under its chosen
constructor overrides. Later waveform folding and parameter calibration
need further analysis before that experiment becomes an audio reference.
USB registry inspection found no Roland/Fantom-named device in the
current host view. Instrument loading and calibration remain pending.

All 292 tests passed. The remaining offline work includes later OSC
waveform folding, a complete native FETDRIVE fixture and independent
contexts for the phase controls' other state effects.

## Native OSC sine fold and stored waveform

The sine window now binds seven owned literals, the native pi scale,
the sign store, the unsigned polynomial store and the signed output store.
The four Fantom placements retain the checked controls and relocated
targets. The native polynomial is a factored degree-15 sine approximation.
The reference preserves its constructor doubles and fused operation order.

All 525 native probes agree bit for bit at four stored values per phase.
The checked boundary behavior explains the earlier binary64 experiment's
isolated peak sign changes. Reachability under BMC arithmetic remains open.
Operand `e037` is a candidate for this context's pi input; a global constant
bank assignment is not established. No strict DSP profile was added.

Early tool-free Qwen drafts misread coefficients and fused arithmetic.
They were rejected. Tool-enabled Qwen then executed exact rational algebra;
its returned coefficient table was independently asserted locally. Worker
code still receives review before adoption. Ring pointer/buffer setup is
shared across the native LINE, phase and sine fixtures. Iterable phase
inputs and mismatched sine packet contexts have regression coverage.

All 297 tests passed. A scoped tool-enabled Qwen job is preparing the
complete native FETDRIVE fixture in ignored scratch files.

## Native FETDRIVE fixture and first-store verification

Tool-enabled Qwen produced and tested the complete native callback fixture.
Review retained its implementation and reused the existing cutpoint checker
to bind the two shaped stores to their constructor records and DSP operands.
The native body has no helper calls or branches. All five live-coefficient
records and the explicit ring graph remain alive across invocation.

The locally repeated tests cover ring wrap, deterministic fresh renders,
stereo output and overwrite refusal. A separate 12,000-frame run matches
all 24,000 first shaped-store values bit for bit. The complete callback
output is finite. Its later filters have no independent comparison yet;
constructor filter defaults and software 48 kHz input are kept explicit.

All 300 tests passed. A second Qwen job is deriving the full Python state
reference for comparison against the now-executable native callback.

## Complete native FETDRIVE arithmetic reference

The full Python reference now reproduces the drive, variable allpass,
DC-blocking filter, dry/wet mix and scratch round trip. It agrees bit for
bit with native execution at all 24,000 final samples in 12,000 frames.
Its WAV is byte-identical to the native fixture's WAV. Native invocation
now enforces that full-output comparison alongside the first-store oracle.

The new state checker follows all eight history pairs through constructor
records and actual DSP operand fields. Every origin value satisfies the
unit-delay relation under the explicit fixture step. Three counted groups
bind the two filter-literal copies per coefficient to their native
representatives and actual setup calls. Native double precision and DSP
encoded literal precision remain separate policies.

The second Qwen job timed out at 600 seconds with an unfinished model.
Its extra quantizer and incorrect filter/state equations were rejected.
The retained implementation follows the native instructions and existing
checked quantizer. No new strict DSP profile or hardware execution is claimed.

All 303 tests passed. A smaller Qwen inventory job is searching the existing
six-artifact corpus for `3086/7086/bebe/bedb` contexts using the already
checked framed control-slot scanner.

The Qwen inventory completed. Local assertions verify 241,742 framed packets,
174 family-1 `3086` hits, 58 `bebe` hits, 230 `bedb` hits and zero `7086` hits.
All `3086` hits reproduce the same repeated triples. Qwen's final family
summary was imprecise; the recorded JSON and local counts supply the table.

Local class mapping identifies STPS and TVPS as simpler `bedb` candidates.
Their following port-3 stores correspond to explicit native clamp tails.
The prefix tracer stops earlier at phase branches, leaving full late-window
record/input provenance as the next step. No opcode semantics were inferred
from inventory adjacency alone. The 303-test code checkpoint is unchanged.

## Phaser late-store provenance and finite clamp execution

The STPS and TVPS late windows now have checked provenance for both the
pre-clamp port-2 store and the following clamped port-3 store. A bounded
forward-join check proves all six phase branches enter the window with
unchanged constructor/ring pointers and base index. Only those proved
roots cross the projected pointer trace; the general tracer is unchanged.

All 526 finite probes of STPS's actual native three-instruction clamp agree
bit for bit. The test includes signed zero, subnormals and boundary neighbors.
Twelve matching STPS-form contexts appear in two pinned Fantom lists.
Exact BMC source selection and flags remain unresolved, so no strict DSP
profile is added. Full phaser audio and instrument behavior are unverified.

Qwen's counted-group lookup timed out at 180 seconds. An independent local
scan of all 665 candidate descriptors confirms no width-three static group
for either duplicated `1.4` pair. The result remains a bounded negative,
with runtime groups and separate writes open. All 309 tests passed.

The next Qwen task is a bounded TRANSIENT metadata extraction for the
post-branch math track. It is limited to callback/constructor identities,
import-call names and initial pointer loads; no machine-code execution.

The bounded metadata job returned. Qwen misclassified three internal jumps
as unknown calls and included FP loads in its GPR list. Independent review
asserts 445 contiguous instructions, eight internal forward branches, a
single return, no ADR/ADRP/indirect control flow and exactly three named
math calls: one log and two exp. Constructor bytes end at `65f`, followed
by four live-pointer fields through `678`. Reviewed metadata is saved
separately. A native TRANSIENT fixture can now target these concrete
dependencies; it has not yet been executed. Code and the 309-test checkpoint
are unchanged by this metadata-only follow-up.

## Native TRANSIENT execution and conditional envelopes

The complete callback runs with three rewritten math calls, explicit context,
four binary32 coefficients and two owner caches. The source image, call set,
branches, return and constructor bounds are checked before execution.
Authored ABI snippets exercise the math bridge before vendor-code invocation.

Qwen's bridge draft timed out with relocation-base/range and code/data errors.
The corrected implementation rejects nonlocal or indirect branches and does
not decode embedded host pointers as code. Its misplaced test draft was moved
into ignored worker output. The source and tests were reviewed and run locally.

The owner allocation now includes both caches through `118`; LINE/FETDRIVE
and earlier native fixtures pass their regressions. A 12,000-frame run matches
24,000 peak/log values and 60,000 envelope/gain/output values exactly. The
upstream detector arguments still come from native execution. No complete
TRANSIENT DSP interpretation or hardware calibration is claimed.

The repeated OSC/TRANSIENT/FETDRIVE native scales supply an amplitude-convention
candidate; physical full scale remains unverified. All 319 tests passed at
this checkpoint, including math-bridge, native-execution and finite-kernel tests.

## Original packet-driven allpass oscillator

Qwen produced and tested an original oscillator from the supported coefficient
prefix and allpass chain. Review retained its static packet/state loop,
reused existing finite-number and PCM helpers, fixed output creation and
exported the original 120 logical bytes under ignored local output. The
manifest includes six seed slots, two live coefficient values and the byte
format. No vendor binary or native call supplies this waveform.

All per-frame signal arithmetic executes packet bytes. Only five sine values
are computed at initialization. The explicit native ring convention supplies
the one-frame feedback path. At requested 440 Hz, the quantized factor gives
440.000197628852 Hz and a maximum 12,000-frame error of
3.1290942059669646e-14. The worker's smaller error claim was replaced with
local measurements. Tests cover external-input independence, two ring wraps,
vendor-corpus-free operation and existing-output preservation.

All 327 tests passed. This is a synthesis-core candidate, with hardware data
encoding, owned resources, task wrapper, output routing and calibration
still pending. The complete-program and general ISA goals remain open.

## Typed state initialization and native enum-0 identity

The native core's checked vtable/dispatch identifies the packet fixture's
double ring as memory enum 0. Fantom's actual manager and driver expose a
binary32 write path for that enum, with 2048 exposed elements per DSP and
separate typed apertures. The checker preserves the important counterexample:
all three stock per-DSP read methods explicitly reject enums 0 and 1.
No join to the global IDM/EDM portal or safe original-engine owner is claimed.

The source-buffer helper reports CPU binary32 rounding, including signed zero,
without labeling those bytes raw DSP state. Two original packet-oscillator
experiments use rounded seeds through ring wrap. Across 12,000 frames their
maximum differences from the binary64-seeded reference are 6.7324744390528934e-9
(440 Hz) and 5.929301521989672e-9 (9600 Hz). Hardware conversion is not modeled.

Qwen returned a portal review in 92.2 seconds. Independent review accepted its
ABI, element-stride and float-transfer observations, rejected a wrong timer
literal, an assumed vtable terminator and a broken no-call result, then derived
and tested the native/per-DSP join locally. Worker outputs stay ignored/local.
All 331 tests passed. Hardware placement, cadence, conversion, entry/return and
actual host loader access still prevent a deployable engine.

## Independent TRANSIENT detector and complete output reference

The upstream detector now has a finite Python model: normalized log peak,
held/window state, reset and unwrapped phase guard, both decay paths and the
rising smoother. It preserves the one-ULP difference between constructor
held-log floor and the separately synthesized release floor. Ten constructor/
program history pairs are checked. Unsupported literal layouts remain rejected.

The native fixture checks all fifteen retained detector writes, uses independently
computed exp arguments, and compares its final output to a separate cold-ring
render. Over 12,000 frames all 24,000 output floats and both WAV files agree
exactly; 180,000 detector values and 60,000 envelope/tail values also agree.
Report flags now mark the full output reference verified and native-sourced
upstream arguments false. These checks do not execute BMC packet arithmetic.

Native tests additionally cover 17,000 silent frames reaching the faster decay
branch, stepped inputs, signed zero, negative live modes and cache cursors 1/2.
The signed-zero comparison exposed and corrected the earlier peak-check oracle's
use of Python abs, which differed from native conditional selections at -0.
Every cache cursor round trip reads the just-written entry and restores its
initial value. No extra delay is added to the independent model.

Qwen returned a bounded draft in 188.1 seconds with a recorded frame-1 mismatch.
Its constants, phase/window state and exp argument equations were incorrect;
no draft model code was accepted. The reviewed implementation was independently
derived from the listing and verified against real callback execution.
All 341 tests passed; the expanded native cache cases were also rerun afterward.
Full DSP interpretation, physical precision/timing and hardware deployment stay open.

## Short-add operand binding and original stereo voice body

The masked-control inventory finds 15 short contexts in nine primary native
programs, plus 23 long, one miscellaneous and nine unclassified contexts.
TRANSIENT short5d72 selects the four-byte field104, whose constructor record
and native load/add are now checked. Native and serialized values differ by
less than one literal quantum; this is expected precision separation. Same-word
long/misc forms and the nondiscriminating PH100 zero remain explicit. Four
other immediate additions are checked without claiming source-port recovery.

Qwen returned the initial study in 89.8 seconds, but narrowed the requested
catalogue to TRANSIENT and misdecoded constants. Those conclusions were rejected.
The correct inventory and field binding were independently reproduced locally.

A second bounded Qwen draft returned the original stereo voice in 126.1 seconds.
Review retained its three-block/shared-ring design, removed scratch import
machinery and duplicate coefficient maps, validated shared initialization and
checked old/new mono samples and metadata against the prior committed source.
The 200-byte/18-packet body applies gain and obtains both output channels through
the existing interpreter; only five initialization sine calls remain.

The 12,000-frame .5-gain voice peaks at .12499999999623529, RMS .08838832781982624.
Its derived footprint is 146 relative data positions and six coefficients; all
five pinned stock descriptors fit the body numerically. Four data positions
remain beyond the extent in the four 150-element owners. These occupied stock
owners are not custom allocations, wrappers are excluded, and no relocated or
deployable engine is emitted. All 352 tests passed, with the final expanded
native-immediate checks also run separately. Hardware gates remain open.

## Original voice resource plans and six-seed dependency

The new planner uses the pinned stock LINE context to obtain each known owner,
DSP, reservations and IO assignments, then reassembles the original three
voice profiles with explicit data/coefficients/input substitutions. A separate
byte-level walk of only proved family-4 transfers verifies all thirty operand
words and protects the remaining 140 bytes. The miscellaneous prefix packet's
general layout stays rejected; no arithmetic/flow decoder was weakened.

The model requires exactly six initial data values. The factor and scratch
cells are written before read. Verification seeds those six cells in an
otherwise nonzero, index-dependent canary ring. All five relocated bodies match
all 120,000 original channel values across 12,000 frames per layout, with
origin1760 after five wraps. Logical/stored original bodies and manifests are
exported only under ignored local output, with typed CPU binary32 source rows
and raw DSP encoding still unverified.

The stock placement remains a stock578-byte LINE identity, separate from the
custom200-byte body. Body load/entry/return addresses remain null, and no
output-IO write, wrapper, live allocation or hardware success is claimed.
Exports refuse existing directories and fail on byte/hash inconsistencies.

Qwen's 240.2-second draft timed out with transfer-offset, coefficient-tag and
default-IO errors. The typed remapping design was independently implemented;
no unchecked draft was adopted. All 359 tests passed, followed by the seven
planner tests after adding strict owner-address type rejection. Remaining work
includes task entry/return, actual owner coordination, safe typed initialization,
readback, routing and physical calibration, alongside the unresolved ISA work.

## CORE1 label-target encoding and counted references

The implemented manager methods at0113338c/011334d6 establish six-byte LP32
records and an explicit logical target right shift by one. The raw driver at
0112f528 accepts widths2/3/4, masks the site to19bits, and can truncate a target
that exceeds its field width. High-nibble flags skip the entire reference before
resolution. Reservation validation covers the start only; the ordinary program
check/set byte covers one eligible patch, not a batch or demonstrated atomic lock.

The new source-pinned report checks instruction/vtable/guard anchors, the real
FETDRIVE symbol and five parent numeric target fields. The actual FETDRIVE label
has zero incoming counted references. Its representative resolves to4020, but
this does not bind a parent target field. The native unsigned-target manager and
_CORE1_DSPWriteProgAll compatibility bodies are stubs; separate MDSP task controls
do not establish render-DSP continuation state. No CALL/RETURN decoder, wrapper
or hardware write was added.

Qwen's static review returned in48.6seconds with wrong record offsets, branch
destinations, register roles, width bounds and guard behavior; its semantic
claims were rejected. A separate test-only draft returned in45.0seconds. Review
retained its helper checks, corrected the installed import path, added an actual
32-bit wrap, nonzero width3/4 cases, mixed skipping, count bounds and the real
firmware corpus check. All368tests passed in32.337seconds. Next evidence needed
is owner-proven nonempty label references or an independent control-flow
implementation; saved return state, issue order and physical deployment remain open.

## Four FDRV cubic windows and five Fantom placements

The next short-add pass binds four FDRV native input/result windows to actual
constructor records and serialized data fields, retaining the earlier-store
representative aliases rather than equating record offsets with read sites.
Their arithmetic is x*(x*x+(3-abs(3*x))) with separate native operations. The
constant register, input/result registers and intervening preservation are
checked. The two cubic5d46 candidates are at39c/3d0 and correspond to the third
and fourth native curves, rather than listing order across interleaved channels.

An isolated40-byte native function matches all bits for1,034 boundary/random
inputs, including signedzero and minimum subnormals. The same cubic contexts
and resource relations are checked in all five Fantom FDRV programs under list
610e5a94. These are whole-window source/result constraints, not complete port
state or isolated short-opcode admission. The strict interpreter/emitter remain
unchanged. The four earlier FDRV state/filter short-add contexts and the separate
PHONO comparison remain next targets.

Qwen's bounded FDRV review timed out at180.2seconds without the requested review
files. No exploratory result or code was accepted. The finished study was derived
locally and checked by six focused tests. All374tests passed in31.504seconds.
No hardware, firmware installation or BMC execution was performed.

## Native auxiliary round trips and executable add/MAC profile

FDRV's first native save/restore paths preserve their current inputs and rewind
their cursors. The new checker pins both bank paths, pointer/cursor provenance,
thirteen constructor cursor-zero stores and the first stereo additive cutpoints.
The 118 candidate-word inventory retains two short 1f60 low-pattern collisions.
The native three-slot model is not a claimed physical hardware depth or proof
of arbitrary program balance. Invalid native cursors were not executed.

The restored inputs are bound through the port 2/6 source records to native d5,
then through the pre-add stores, additions and following main MAC/store results.
The exact first context now supports an original 84-byte register_add_mac_pair
profile. Its 56-byte arithmetic body matches the native-paired program and every
one of the five Fantom placements. The remaining 28 bytes are original input-load
setup. The constrained emitter, inverse decoder and interpreter preserve old
stores, next-packet loads, shared coefficient constraints and native FMA/binary32
policy. The arithmetic result matches 1,024 directly executed native channel cases.
The 64-byte native circular fixture also matches 396 cases with distinct cache and
surrounding canaries. The full FDRV program, auxiliary words, arbitrary variants
and hardware scheduling/precision remain outside execution admission.

Qwen returned a circular-helper/test draft in 24.1 seconds, with bare paths that
wrote into the checkout root. Those original files were inspected and moved into
ignored worker output. Review retained the circular copy/update logic, replaced
overflow-prone numeric validation with the existing finite helper, and installed
meaningful unit and native-execution checks. Native/firmware proof and emitter
integration were independently derived locally. Stored example CLI roundtrip
passes, and all 386 tests passed in 32.305 seconds after the final arithmetic-limit
checks. No vendor binary, device operation or live allocation was added.

## Complete first FDRV state-variable filter component

The first stereo filter's producers now have a checked recurrence, source/state
records, coefficient readers and native register-preservation anchors. Direct
native execution established the FNMSUB sign as s*b minus Tnew. The paired state
update is Tnew=t+(1+a)*s, X=y+b*s-Tnew, Snew=s+(1+a)*X in ideal arithmetic;
the model retains actual native FMA and separate addition order. Its state matrix
and strict ideal Jury conditions are derived, with both valid sign orientations
and independent pole checks. This is not a hardware stability guarantee.

The new 184-byte state_variable_pair profile includes all first-block producer
arithmetic, one balanced auxiliary save/restore per port, explicit history aliases
and following loads. Its 146-byte arithmetic body matches the native-paired
stream and all five Fantom placements; the leading 38 bytes are authored loads.
The inverse decoder protects the exact context without changing the general
header grammar. Inactive physical cache slots, arbitrary depths and flags remain
outside the model. The separate cubic producer window stays unadmitted.

The owned fixture executes the unchanged 879-instruction native FDRV callback,
checking the prefix and first block rather than claiming complete effect-output
agreement. Nine cursor pairs, a 12,000-frame wrap run, signed-zero and large/
precise binary64 states produce 105,232 exact native values and 78,924 matching
byte-emulated filter values. Non-dyadic source coefficients force actual binary32
conversion in all three comparisons. Stored-example CLI roundtrip passes, and
all 393 tests passed in 37.550 seconds after the precision cases.

Qwen returned an equation/reference draft in 70.4 seconds. Its unwanted binary32
rounding of y/s/t and rejection of valid wide signals were corrected. Review
retained the equations, reused the existing numeric helpers and expanded the
requested positive-g/q stability subset to both mathematical sign orientations.
Native/firmware evidence, byte backend and execution fixtures were derived locally.
Next is a filtered original oscillator voice with verified shared resources and
seeds across the five owners; entry, ownership and hardware calibration stay open.

## Original filtered voice and owner plans (2026-11-11)

The oscillator/gain body now composes with the admitted lowpass filter into
384 static bytes and 28 packets. Filter inputs use the existing 90/91 scratch
samples; its four state seeds occupy separate cells. Final unused prefetches
borrow current oscillator stores at 20/30/40/50, keeping exactly ten required
initial values. Data extent remains 146 and coefficient extent becomes eleven,
within each recorded owner's numerical capacities. Each profile initializes
the ports it consumes; all four share one ring and one origin advance per frame.

The authored lowpass helper supplies rounded a/b/c/d/e values and rejects
nonfinite, zero-g and unstable positive-g/q designs. Its cutoff is nominal and
the software clock is explicit. A separately rendered original voice plus scalar
filter matches all 24,000 channel values through 12,000 frames. The renderer uses
five oscillator-seed sine calls and one filter-design sine call at initialization,
with no per-sample host waveform or filter calculation outside packet execution.

The existing planner's default 200-byte mode remains tested. Optional cutoff mode
relocates all 58 transfer fields while protecting 268 other bytes, including mixed
header contexts whose general grammar remains opaque. All five 12,000-frame
canary runs match 120,000 output values and end at origin 1760. Exported original
body bytes/manifests verify against their hashes, and a new stereo WAV is generated
under ignored local output. Ten CPU data-source rows and eleven coefficient-source
rows retain the source-buffer versus raw-DSP-format distinction.

Qwen returned the bounded design draft in 23.1 seconds. Review retained the math,
fixed coefficient labels and the rate-derived bound, replaced a weak absolute
stopband assertion with a relative response check, and verified returned values
are already binary32. Composition, dataflow, byte protection, relocation and
independent renders were implemented and checked locally. All 403 tests passed in
45.987 seconds. Load/entry/return remain null, ownership/output routing and physical
timing/precision remain unverified, and no firmware package or device write is made.

## Cubic packet execution and original shaped/filter voice (2026-11-11)

The FDRV cubic producer window is now an exact 126-byte/eleven-packet profile:
10 authored preload bytes plus the stock 116-byte body at 378..3ec. Four
independent sources feed four x*(x*x+(3-abs(3*x))) results, preserving old-port
stores, shared literals and final reloads. All five Fantom FDRV bodies match.
Six additional short multiplies and two literal-minus-magnitude forms execute
only inside the strict checked profile. Destination/source/operand fields and
masked multiplication/add classes are recorded as partial maps; arbitrary class
matches and miscellaneous header grammar remain outside admission. The earlier
6547 coefficient-port ambiguity is retained because its candidate values coincide.

Every packet is checked with four asymmetric inputs. Native curve comparisons
cover 1,032 independent values, including signed zero and minimum subnormals.
A separate 12,000-frame full-callback fixture with declared .75 input gain supplies
four cubic input/result cutpoints: all 48,000 conditional results match, with
47,985 distinct input values. A provenance audit excludes later overwrites. These
captured inputs are not a new independent complete-FDRV reference. The existing
first-filter check independently matches another 96,000 values in that fixture.

The original filtered voice now has optional cubic shaping between gain and
lowpass. The five profiles occupy 510 logical bytes and 39 packets, stored as
512 bytes with padding only at the full body's end. Data extent 150 fits the
smallest recorded reservation exactly; ten initial data values and eleven
coefficients are unchanged. Amplitude is bounded to 0..0.5 for headroom and
actual shaper reads retain the checked [-1,1] domain. No sample-rate arithmetic
is performed on the host outside the packet interpreter.

The independent original-voice + scalar-cubic/filter render matches all 24,000
channel samples through 12,000 frames. Five owner-specific canary-ring renders
match another 120,000 values. The planner verifies 70 two-byte address fields,
protects 370 other bytes, exports distinct logical/stored sizes and hashes, and
includes storage alignment in the capacity check. Default 200-byte unfiltered
and 384-byte filtered behavior remain tested. Original local WAV and five plans
were generated and their exported sizes and hashes verified.

Qwen's read-only attempt hit its 60.2-second bound without review artifacts.
A smaller no-tool review completed in 6.3 seconds but miscopied right inputs and
made arithmetic errors; none of its code or conclusions were accepted. The
implementation, provenance and native/scalar checks were completed locally.
All 415 tests passed in 57.989 seconds. Twelve new tests cover actual byte windows,
packet timing, native/independent comparisons, strict boundaries, relocation,
padding, capacities, initialization and output preservation. Physical precision,
issue budget, live ownership, entry/return, output routing and usable transport
remain unverified. No device was accessed and no firmware package was built.

## Exact stock mute resolver/search limits (2026-11-11)

Focused on an execution gate rather than another audio block. The implemented
CORE1 SetMuteMode body at01133b38 and slot+e0 now has an offline checker with
instruction anchors and five actual FETDRIVE first-packet comparisons. Its label
resolution checks segment count but never reads capacity or verifies parity;
base+relative follows uint32 wrap. This differs from the counted label writer,
so the stricter resolver cannot be reused as a firmware behavior model.

The actual raw scan uses header&31, starts at following word one, and selects
the first word masked byfffc equaltoff70. It scans controls and payloads alike,
and replaces ff70/71/72/73 with ff70|bool, clearing bitone. FF75 and the return
forms do not supply a gate. Generic compact001f framing disagrees with the
firmware's 30 subsequent raw reads, so the offline checker rejects that input.
The invalid-segment assertion tailpath has no guard clear in this body; search
failure has a clear only if its assertion call returns. None of this proves
hardware halt, atomic exclusion, actual mute effects or safe live code replacement.

A bounded exploratory nonempty-label scan returned shape-only candidates without
label-type/caller ownership. Those remain local and unadmitted; no parent target
or continuation inference was accepted. Qwen's no-tool trace review returned in
3.0 seconds, correctly noting first-match replacement but confusing the header
and payload roles and the 14-bit extraction width. Actual instructions supplied
all accepted conclusions; no worker code was adopted.

Seven new tests cover the actual five entries, instruction mutations, all four
masked words, first-match order, payload collisions, excluded forms, missing
matches, compact framing, unchecked capacity, wrap and strict offline types.
All422 tests passed in58.036 seconds. Updated existing studies and queue; no new
opcode admission, firmware mutation or device access. Next useful evidence remains
an owner-proven incoming label/flow implementation or a controlled Fantom PC/state
observation, retaining the separately documented access/recovery prerequisites.

## Exact render-write geometry and queued-only completion (2026-11-11)

The pinned StackWriteDspProg and listed-copy bodies now have a pure offline
geometry checker. Destination word+2 uses the source word's low half and advances
the source by four bytes; a trailing halfword uses a full-word read with low bits
cleared. Both raw edges occur before the aligned bulk copy, whose post-edge
64-byte threshold selects CPU versus DMA. Descriptor lengths are bounded to4095
words, with32 shared slots including already queued descriptors.

For the original shaped voice, logical count510 reads a512-byte backing source,
writes the tail at421c first, then queues508 bytes at4020. Source padding is not
written. Passing count512 writes two additional bytes instead. A word+2 start
needs a two-byte logical source prefix before stored-word reversal; a four-byte
payload then requires eight source bytes. The two-byte-only edge reads only two
bytes despite a convenient four-byte stored buffer. Tests replay both alignments
and every even count0..130 with independent asymmetric bytes and neighbour canaries.

The completion helper at0112f6a4 returns immediately unless its initial state is1,
before examining wait. State1 clears event4, sets state2 and starts the list;
wait=true then polls a new event, clears it and resets state0. The callback only
sets event4. Thus a nonwaiting start followed by helper(true) is not an active
DMA drain, even with completion already signaled. The initial state2 assertion
in StackWriteDspProg is not treated as a synchronization API. No live exclusion,
source-cache policy, source lifetime or real-time completion was established.

Voice-plan manifests now include recorded-base write geometry and retain null
load/entry/return addresses and execution_ready=false. Program capacity uses
logical destination length again; the previous512-byte requirement was an
explicit conservative policy before this exact510-byte write was proved. A fresh
DSP4 export retains the prior logical/stored hashes and includes the new geometry.
The five relocation/canary checks pass with the metadata integration.

Qwen returned its supplied-trace review in4.1 seconds but confused source read
extent and halves, the state2 early return and the padded-count counterexample.
Those claims were rejected; actual instruction anchors and independent byte
replay supply accepted evidence. All429 tests passed in57.339 seconds. After
adding the explicit literal-address-window alias guard, all seven focused tests
passed again. This helper assumes an otherwise empty shared DMA list, restricts
nonwrapping/no-alias geometry, provides no live caller and performs no device IO.
Next trace SetExeMode callers and packed stock event/mode/start values, keeping
scheduler control separate from still-unproved render CALL/RETURN semantics.

## Active DMA drain and two-model execution enable (2026-11-11)

The separate active DMA drain at 0112f508 is now checked against instructions and
manager slot 48 (011324a2 tailbranch). It waits only from global state 2, accepts
an already-set completion bit, clears bit 4 and resets state 0. It does not start
state 1. Manager slot 44 (01132472) forwards its r1 wait argument to the queued
start helper, then may apply a per-DSP pending DRAM-IO update through slot 5c.
This side path and the global queue scope are retained explicitly. The all-program
nonwaiting upload skips the start helper entirely; a subsequent active drain
cannot complete a merely queued transfer. No manager routine was actually called.

The Jupiter comparison now reads the actual CORE1_DSPEnable suffix in both images,
validates both veneer chains and tracks all four fresh MOV-defined arguments.
Fantom calls DSP0/1/2/3/6 with modes 2/0/2/0/2; Jupiter uses mode 2 for all five.
Every call has argument 0 and event 3. Global masks 45c5 and 4fcf are passed to a
third exact shared code window: the 14-byte shadow-OR/MMIO writer. Its real shadow
addresses differ, while the port is 41100004. The mask's low seven bits and bits
14:8 both correlate with the mode-2 index set (45 versus 4f). This is a bounded
cross-image observation, not an admitted complete register specification, halt
operation or sample-execution proof. Argument zero cannot resolve entry units.

The MOV tracker rejects unknown/stale sources, missing producers, unrecognized
operations and a tail branch before the final call. An initially incorrect tail
position in that guard was fixed, the corpus checks rerun and exact rejection
messages added to the mutation regression. All 431 tests pass in 57.337 seconds;
the strengthened focused checks also pass. The shared window is compared back
to the original Jupiter member at 2f146, container 30146, with hash
4af08510153d36b624d4d5afe6c050b8a25c3621ed714b842ba2b1e29afb7d02.

Qwen's small supplied-contract boundary draft returned in 4.4 seconds. Seven
vectors were consistent; the final DSP6/mode2/event3 expected word omitted the
mode bits (30000000 instead of 32000000), which was corrected independently.
No worker hardware interpretation was accepted. The firmware comparisons and
active-drain implementation were completed locally. Existing Roland notes are
updated; no executable wrapper, on-device upload, hardware halt or saved-return
semantics is claimed. Next useful evidence remains an implemented event/mode
consumer or actual continuation/PC observation, subject to the access/recovery
requirements already documented.

## Exact half-sample interpolation and clipping (2026-11-11)

The strict emitter/interpreter now admits an 80-byte, six-packet clipped_half_pair:
14 authored preload bytes, 60 exact FDRV bytes at33c..378 and a six-byte final
store. It preserves unclipped current-history stores, averages before clipping,
and produces the four bounded samples feeding the existing cubic quad. The
following original cubic packet supplies the direct-right store provenance.
Two half/FMA forms, four exact self-limiters and data stores from ports2/6 execute
only inside complete checked profiles. The other 80-byte scratch-tail profile
retains its original exact structure. No general miscellaneous grammar is admitted.

Independent packet snapshots distinguish unclipped history and average-before-clip
order. Two register-only native extracts (24/40 bytes) match all 2,064 results over
1,032 input pairs, including signed zero, subnormals, maximum finite inputs and
random saturation cases. All five pinned Fantom 60-byte bodies and the outside
history/direct-right fields match. A 12,000-frame callback fixture matches 48,000
clipped results and 24,000 raw history values using conditional cutpoints, separate
from the first filter's 96,000 independently modeled values. Earlier resampling/
drive producers and a complete FDRV byte-execution path remain unresolved.

All436 tests passed in58.147 seconds. Focused tests passed again after adding
pinned-Fantom identity and changed-native-clamp rejection checks. The original JSON
example round-trips through the CLI as80 logical/stored bytes. Qwen's9.5-second
draft calculated the asymmetric example correctly but omitted inputs and assumed
caller-map mutation; its code was rejected and working tests implemented locally.
Updated the semantic ledger's stale cubic-admission statements and existing Roland
notes. No firmware package, live device, output wrapper or silicon-precision claim.

## Completed tonight's input-to-first-filter milestone (2026-11-11)

Resumed only the bounded stage after Jacob explicitly requested continuation.
The saved draft's failed binding was corrected to the actual constructor aliases:
right history uses relative24, raw stores22/26, and mixed stores reuse1e/24.
The physical mixed-store operands at5a/5c are also checked; validation was not
weakened. The86-byte stereo_prefilter now matches all76 stock input bytes and
adds ten authored mixed stores. Three binary32 coefficients, six explicit data
reads and exact raw/mixed history aliases preserve the checked operation order.

Combined with the184-byte state-variable profile, the270-byte signal path runs
entirely through packet execution. Its separate persistent ring receives only
external input samples and packet writes, never native intermediate samples or
host-calculated mixed samples. The declared initial ring matches the fixture's
nonzero background; independent scalar equations remain validation only.
All120,000 raw/mixed/state/output comparisons match the native callback over
12,000 frames and five wraps, ending at origin1760. A2056-frame subprocess test
with auxiliary cursors1/2 independently crosses wrap. All five actual Fantom
input spans execute the asymmetric vector identically. Qwen's checked expected
outputs -1.875/5.625 agree, while its loose state/rounding claims were not used.

Five new tests cover every packet state/write, coefficient timing and binary32
rounding, exact fields/constants/resources, changed native arithmetic and aliases,
all five pinned Fantom spans, and independent native execution through wrap.
All441 tests pass in59.088 seconds; the focused suite passes again after refining
platform/corpus skip guards. The original example and reproducible command are
saved. Local270-byte logical/272-byte stored bodies have logical hash
9912f101df3714156894a3b9bb7feb3c6225c468e33e3179fc68ebcd783637bb.

The immediate milestone is complete. Broader research pauses after this verified
commit and note sync, per Jacob's requested stopping point. No full-FDRV,
physical-precision, live-loading or entry/return claim is made, and no device
was accessed. Saved earlier WIP is historical and is superseded by this checkpoint.

## Completed second-filter/recombination milestone (2026-11-11)

Extended the input chain through the second stereo state-variable filter and its
recombination, stopping before the following filter. The composed496-byte body
uses86/194/216-byte exact profiles. The194-byte first-filter form supplies explicit
main-port data stores; the216-byte second form retains all178 stock bytes at
f8..1aa after authored preloads. All five pinned Fantom body substitutions match.
Four new arithmetic words execute only in the complete recombination profile.

Original native FMSUB/FMADD execution establishes fma(wet,g,fma(-dry,g,dry)), with
g read as binary32. Its dry2/wet5/g.25 result is2.75, and numerical endpoint
results are2/5. The future coefficient load cannot affect the current packet.
Pure tests compare independent filter states, recombination, incoming-port timing
and changed future coefficients. Qwen's6.3-second review got the arithmetic and
signs wrong; its conclusions were rejected against actual execution.

The extended native oracle is deliberately a prefix fixture:276 original sample
instructions through30553c plus the six original output/epilogue instructions.
Checks preserve x2 and the stack-pointer lifetime and bind the callee-save ABI;
no third-filter or later effect arithmetic executes. A mutation-test instruction
initially lacked Capstone detail metadata; that fixture was corrected, and both
output-pointer and stack clobber rejection are now exercised before execution.

The separate persistent packet ring matches192,000 native-prefix state/output
values over12,000 frames and five wraps, ending at origin1760. A2056-frame test
uses cursors2/1;1,029 native register-only boundary/random probes match the scalar
reference. All446 tests pass in59.860 seconds. Original JSON examples, reproduction
commands and local496-byte logical/stored bodies are saved. Body hash:
2501fa7b8c39b306d190478fdd6ede532ddf2689ba967f6d02813e235b738dd9.

This bounded milestone is complete. Broader research pauses after the verified
commit and Obsidian sync. Full FDRV, hardware precision, entry/return, ownership
and safe live loading remain unresolved; no instrument was accessed.

## Completed four-section filter-bank milestone (2026-11-11)

Extended the packet-only input chain through the third and fourth stereo filter
sections and their recombination, stopping before resampling arithmetic. The five
86/194/226/194/202-byte fragments compose 902 logical/904 stored bytes and 53
packets. The third 146-byte and terminal 154-byte stock bodies match the pinned
native-paired image and all five Fantom relocations. New exact profiles add
recombination output stores and the terminal short-packet context, reusing existing
arithmetic. Shared resource checks preserve strict alias/type/range validation.

Synthetic bridge cells 60/61 hexadecimal connect the independently initialized
second/third fragments; their stores are authored and excluded from native state
comparisons. They are not evidence of available on-device allocation. The raw
final 0/3 stores do match native history writes. The owned native fixture executes
494 original prefix instructions through 3058a4, plus the six original output and
epilogue instructions. Some next-packet loads/stores execute, but the first
resampling multiply is excluded. Pointer, stack and output lifetime checks remain
enforced. The complete original callback is not executed by this fixture.

The independent persistent packet ring matches 336,000 native-prefix values over
12,000 frames and five wraps, ending at origin 1760. Nonzero C8/C9 and distinct
nonzero C15..C19 prevent degenerate section/recombination coverage. A separate
2,056-frame subprocess checks 57,568 values with auxiliary cursors 1/2. Pure
terminal tests cover scalar recurrence/recombination, signed zeros, endpoints and
seeded random signals; strict decoder and native mutation tests reject altered
fields, arithmetic and provenance. One output-lifetime mutation initially targeted
d0 before its final assignment; the test was corrected to clobber the live d1
result, then extended to check d0 after its final assignment as well.

Qwen supplied six invalid-input mutations. All are rejected by the assembler,
but its intended T/S-adjacency case only repeats target mismatch. The actual
adjacency mutation was added independently. No Qwen arithmetic was needed.
All 452 tests pass in 62.903 seconds; tightened tag/duplicate-field and output
mutation assertions are also checked in the focused suite. Three original JSON
assignments and reproduction commands are saved. Local logical body SHA-256:
35975c7fd5f68ee68078e35812931dbef7b625d8a6a47d5dfa1b10fac69e0398.

This bounded milestone is complete. Save/push the verified checkpoint and sync
the Roland Markdown notes, then pause broader work as requested. Resampling/drive
and remaining full-FDRV integration, silicon precision/cadence, allocation,
entry/return and safe live loading remain open. No instrument was accessed.

## Completed connected resampling/drive milestone (2026-11-11)

Recovered the 102-byte stock FDRV window at 2d6..33c, including raw-history
writebacks, three-tap accumulation, mixed-history stores, fixed drive scaling,
binary32 live C0 gain and a real coissued clip-history prefetch. The strict
122-byte profile adds authored input/output transfers. Its short/long contexts
reuse 1428/552b with different roles; long 0424/4527 accumulates the third term,
and short 0426/4529 applies the fixed scale. All three tap coefficients must be
exactly representable by the 24-bit encoder; no general opcode admission is added.

The first Fantom comparison correctly failed: all five placements use duplicated
100000 literals (0.0625), while ZENOLOGY uses 0656d2. Both exact variants are now
supported and checked against their real bytes. ZENOLOGY's constructor double
0x1.95b489f0954cbp-6 differs slightly from the decoded DSP literal; the interpreter
uses that explicit native-reference constant, without claiming silicon precision.
Right-channel literal loads reuse left-channel constructor records, with wire
aliases retained rather than inventing independent records.

The eight-fragment chain reaches clipping and cubic outputs from external samples
and its own persistent packet ring: 1,230 logical/1,232 stored bytes, 77 packets.
Synthetic bridge cells 60/61 and 62/63 have no on-device allocation proof. Native
comparison runs the original complete callback in owned fixture memory but checks
only 38 packet-covered data values per frame through the last cubic store. Later
cutpoint writes fail provenance checks; native final output is not compared.

Stock 1/0/0 tap defaults would hide history arithmetic. Declared nonzero fixture
taps 0.5/0.25/-0.125, C0=8192 and each selected fixed scale match 456,000 data
values over 12,000 frames/five wraps, ending at origin 1760. The two runs supply
912,000 comparisons, with both varied nonsaturated values and clipped endpoints.
Separate stock/nonzero/Fantom-scale cases cross wrap over 2,056 frames with
cursors 1/2. These constructor substitutions are fixture inputs, not evidence of
Roland parameter setters or physical Fantom execution.

Qwen returned eight invalid-input suggestions in 4.0 seconds. Each is rejected,
but its cross-channel suggestion instead breaks adjacency and aliases an output;
an actual channel-alias case was added independently. A seventh source was needed
for the traced prefetch after the worker received its six-source baseline.
Pure tests cover the packet trace, pre-gain stores, delayed loads, both fixed
scales, independent scalar FMA order, signed zeros and seeded random signals.
Native mutations reject changed arithmetic, sub-quantum scale changes and later
cutpoint overwrites. All 458 tests pass in 69.342 seconds.

Default-tap logical hashes:
ZENOLOGY 457a7ceca95660a4cba18eadb5de872f0603102f3436be7deb46cea5efaaaa26;
Fantom 6a3aad1bfe9d00f180f8b07afd1b320df9bb3b861fd804ae96d439c9352601d1.
Original JSON examples, reproduction commands and local evidence are saved.
Pause broader research after the private commit and note sync. Full FDRV still
has 23 downstream packets/416 stock bytes at 3ec..58c. Broader ISA/control-flow
mapping, parameter behavior, numeric/timing calibration, entry/return, allocation
and safe loading remain unresolved. No instrument was accessed.

## Post-cubic mix and V-STAGE hardware inventory (2026-11-11)

Completed the two requested bounded tasks. The strict 110-byte post-cubic profile
retains 90 exact stock bytes at 3ec..446, mixing current averaged/direct cubic
values and preceding direct history with .5/.25/.25 weights. Raw mixed stores
precede binary32 live C1 gain and the fixed post scale. Explicit final stores at
6/a match cutpoints from the following stock packet without admitting that
packet's other operations. No new synthetic bridge cells are needed.

Fantom's five bodies use the exact 500000/16.0 scale; ZENOLOGY uses 628624 with
native constructor double 40.384 rather than decoded 40.3837890625. Both complete
input-chain fixtures match 504,000 data comparisons over 12,000 frames and five
wraps, ending at origin 1760. The chain is 1,340 logical/stored bytes and 84
packets. Two wrap-crossing subprocess cases use cursors 2/1; pure reference and
packet-trace tests retain signed-zero, gain/timing/store and resource checks.
There are now 18 stock packets/326 bytes remaining from 446 through 58c.

Qwen's 90.1-second V-STAGE pass found official update 1.11 and retained its ZIP
and UPA payload, but timed out with an interim report and unbounded-looking string
output. Its strings were not accepted as chip identification. Independently
retrieved the linked official page and ZIP, verified the same hashes, and parsed
the archive with the existing bounded member reader. ZIP hash:
8e883fa00fd083926716d2fd0f0cac6744eebda7f50fb905dc04ca4844ae6572.
UPA hash:145262c536dec1928c4652bec6c5c84318374445219832c34e864760377644a8.

The update has 15 components addressing bmc0..bmc4. Three distinct image groups
exist:0,1/2,3/4; all C0A/C1A/C1C images match within each paired group. The existing
CORE1 mapper accepts all three distinct vector/scatter layouts. C0A encrypted
header key-index b6 is not a recovered key. No separately named host/Linux image
identifies the UI processor; opaque CORE0 content remains unresolved. Roland's
engineering photograph was retrieved and inspected, but its obscured/unreadable
markings cannot verify exact chips or a physical five-package count.

Added a pinned read-only V-STAGE inventory tool and three tests for actual target
groups, hash-first rejection, missing members and changed footers. All 467 tests
pass in 77.501 seconds. No vendor images, photographs or raw listings are committed;
no firmware/updater was executed. The comparative keyboard note is updated to
distinguish verified BMC target names from unresolved physical/host identity.
Save the private checkpoint and sync Roland notes plus the separate cross-vendor
Obsidian note. Full FDRV, host/load compatibility, allocation and silicon behavior
remain open; no instrument was accessed.
