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
