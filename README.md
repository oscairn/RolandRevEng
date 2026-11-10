# RolandRevEng

Independent Roland BMC interoperability research, starting with Fantom-0 v1.08 and
the installed ZENOLOGY plugin. Intended remote: `https://github.com/jbschooley/RolandRevEng.git`.
Keep the repository private as requested. This is not an official Roland project.

Read [the packet and loader map](docs/BMC%20DSP%20packet%20and%20loader%20map.md) for findings,
confidence, build-specific addresses and the remaining requirements for custom engines.
The [queued research](docs/research-queue.md) prioritizes the host bridge, instruction
semantics and kernel/audio ABI. All three offline passes are now reviewed and integrated.
CORE1 has a raw MMIO SysEx handler overlapping DSP program RAM, and stock effect
ownership/mute controls are mapped. The external peer, safe task entry, state setup
and hardware timing still block a runnable custom engine. The MMIO read-reply builder
also has a static stack-size discrepancy; it is not a demonstrated safe loader.

Independent follow-up studies:

- [Gain controls](docs/alu-controls-study.md): native def/use comparison of selected gain chains.
- [Dry/wet MAC controls](docs/dry-wet-mac-study.md): symbolic mixing expressions for the established subset.
- [MAC, allpass and store timing](docs/mac-controls-and-issue-study.md): additional exact arithmetic forms and pre-arithmetic stores.
- [Transfer spaces](docs/transfer-spaces-study.md): pointer provenance and the contextual meaning of address tags.
- [Header fields](docs/header-fields-study.md): bounded operation-family and payload-layout findings.
- [Exceptional operations](docs/special-ops-and-exp-study.md): exponential reference windows and deliberately unsupported short controls.
- [CORE1 command entry](docs/core1-command-entry-study.md): actual callbacks versus logging strings.
- [Receive path and test controls](docs/core1-receive-and-test-controls.md): CORE-local queues, boot modes and stock diagnostic controls.
- [Host transport](docs/host-transport-study.md): the normal application's gadget-serial IPC and correction to the older spare-port assumption.
- [Host/CORE1 bridge](docs/host-core1-bridge-followup.md): routes, service replies, CORE-local MMIO and the precise missing peer boundary.
- [Supported code generation](docs/supported-code-generation.md): mix/gain and four-stage allpass fragments, with original examples.
- [Kernel and audio ABI](docs/kernel-audio-abi-study.md): stock mute controls, manager reservations, shared routing and a gated probe design.
- [Native arithmetic primitives](docs/native-arithmetic-primitives.md): bounded native shaping, feedback and voice-end reference semantics.
- [Operand variants and macro boundaries](docs/operand-variants-and-macro-boundaries.md): exact mono-sum and cross-destination allpass comparisons, with oscillator-layout and exceptional-macro limits.

This directory contains offline tools and derived research. It does not contain
a working custom synth engine, general assembler, flasher or hardware driver. A constrained
emitter reproduces two verified fragment families; it does not schedule arbitrary operations. Nothing
here opens a device or executes Roland's plugin. Production Oscairn code was not changed.

## Reproduce

Python 3 and Capstone 5.0.7 are sufficient for the analysis; `requirements.txt` records
the existing analysis dependency. Preparing exports also uses Xcode's `dyld_info` and
`c++filt`; the exceptional-operation study uses `xcrun otool` to identify import stubs.
Use an interpreter with Capstone installed. To prepare a fresh environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
. .venv/bin/activate
```

From this directory, with that environment active:

```sh
python3 tools/prepare_zenology.py '/Library/Audio/Plug-Ins/VST3/Roland/ZENOLOGY.vst3/Contents/MacOS/ZENOLOGY' --out local
python3 tools/extract_zenology.py
python3 tools/analyze.py
python3 -m unittest discover -s tests -v
```

The first two commands regenerate the effect metadata without the old scratchpad or its
pickle files. `analyze.py` additionally expects `local/b0c1a.bin` and `local/b1c1a.bin`:
the respective `bmc*_MI078_C1A_up.bin` files with their first 32 container bytes removed.
These inputs are already prepared locally for this investigation. The unmodified files
are inside `FNTM0_UPA.BIN` in the user's v1.08 update. Artifact SHA-256 identities are
recorded in `evidence/analysis.json`; other plugin versions require a fresh analysis.

`local/`, detailed generated evidence and working vault copies are ignored. Keep vendor
images, generated exports, disassembly and extracted coefficient/program data local.
Only aggregate results, artifact identities and recovered interfaces are tracked.
The existing `parse.py`, `lift.py` and `coeftab.py` were preserved from Jacob's earlier
scratchpad and adapted for durable paths and the corrected segment layout. Their ARM
readers are bounded heuristics, not general interpreters. Native operand dumps remain
supporting evidence rather than a semantic proof.

## Inspect

```sh
# Native DSP0 program in the header-stripped bmc0 CORE1 payload:
python3 tools/bmc_dsp.py local/b0c1a.bin --stored --offset 0xc49b0 --length 0x13e4

# Recover a CORE1 scatter map, or inspect the DSP upload function:
python3 tools/core1.py local/b0c1a.bin
python3 tools/core1.py local/b0c1a.bin --address 0x112f582 --size 0x122
python3 tools/core1.py local/b0c1a.bin --find 'CBmcDspDrv::GetDspProgAdrs('

# Inspect a complete CORE0 container header without decrypting it:
python3 tools/c0_header.py local/bmc0_MI078_C0A_up.bin
```

Packet output is `offset: header | base control words | operand pool as words`.
The pool can contain operation extension words as well as addresses and literals.
`bmc_dsp.assemble()` reconstructs raw packets and checks lengths. The separate
`bmc_subset.py` emits the two supported named fragment templates. The decoder rejects unobserved header bit 5 and unknown
compact forms instead of skipping bytes to manufacture a successful parse.

The locally generated `evidence/analysis.json` contains packet inventories, complete scatter records and the
firmware program-list candidates. `coefficient_widths.json` records exact symbol offsets
and the adjacent-symbol width conflict explained in the header study. Candidate
symbol adjacency does not prove ownership by a program class.
`core1_bmc0_api.json` and `core1_bmc0_functions.txt` retain the build-specific load path.

Local documentation prepared for the existing vault is under ignored `docs/obsidian/`;
code stays here. These working copies are not part of the GitHub repository.
The vault is outside the writable roots. Its four saved original notes were rehashed
and remain unchanged. The local 19-note `docs/obsidian-update.patch` was applied to
temporary copies with zero fuzz and compared byte for byte with the staged documents.
Check for newer vault changes before applying it from a writable session:

```sh
cd /Users/jacob/Documents/ObsidianVault/Projects/Oscairn
patch -p1 < '/Users/jacob/Projects/Open Synth Platform/bmc-research/docs/obsidian-update.patch'
```
