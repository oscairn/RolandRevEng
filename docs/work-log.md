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
