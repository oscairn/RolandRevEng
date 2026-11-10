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
