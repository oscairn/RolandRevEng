# RolandRevEng

Independent Roland BMC interoperability research, starting with Fantom-0 v1.08 and
the installed ZENOLOGY plugin. Remote: `https://github.com/jbschooley/RolandRevEng.git`.
Private visibility was verified on 2026-11-10; keep it private as requested. This is not an official Roland project.

Read [the packet and loader map](docs/BMC%20DSP%20packet%20and%20loader%20map.md) for findings,
confidence, build-specific addresses and the remaining requirements for custom engines.
The [queued research](docs/research-queue.md) prioritizes the host bridge, instruction
semantics and kernel/audio ABI. Follow-up passes are reviewed below.
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
- [CORE1 service startup](docs/core1-service-startup-mmio.md): normal initializer-table activation in both builds and exact MMIO reply-frame bounds.
- [Host version identities](docs/host-version-and-upstream-crosscheck.md): five component slots, checked version strings and bounded public-source comparisons.
- [Supported code generation](docs/supported-code-generation.md): mix/gain and four-stage allpass fragments, with original examples.
- [Kernel and audio ABI](docs/kernel-audio-abi-study.md): stock mute controls, manager reservations, shared routing and a gated probe design.
- [Effect lifecycle and parent entries](docs/effect-lifecycle-and-parent-entry-study.md): factory replacement ordering, coefficient clearing and four effect-entry candidates.
- [DRAM-IO records and native clearing](docs/dramio-clear-records-and-native-state.md): owner-matched address fields and exact native clear-loop bounds.
- [Wait completion and initial data](docs/core1-wait-and-initial-data-study.md): timer chunking, initial flag recovery and explicit completion limits.
- [Parent controls and the organ graph](docs/parent-control-and-nested-organ-study.md): nested DSP1 ownership, shifted pool references and native callback IO.
- [Official MC-101 comparison](docs/mc101-v182-core1-comparison.md): shared MMIO/wait code and a different software scaling constant.
- [Official JUPITER-X comparison](docs/jupiter-crossmodel-c1-study.md): shared routine windows and eleven RAMCLR segments with two record spacings.
- [Condition fields and implicit returns](docs/condition-fields-and-implicit-return-study.md): exact native predicate inputs and payload limits on `00f8` interpretations.
- [Owners and clear interfaces](docs/dramio-owners-and-clear-interface.md): constructor-selected ownership, counter aliases and actual global clear callers.
- [CORE1 task context](docs/core1-task-context-and-host-peer.md): software IRQ registration, priorities, queue ownership and the remaining host peer.
- [SH-4d and TR-8S updates](docs/sh4d-and-tr8s-firmware-study.md): another readable shared-code case and an encrypted-only package boundary.
- [CORE0 ciphertext and key location](docs/core0-ciphertext-and-key-location.md): six-image block comparison and the reported MC-101 ROM slot, with Fantom validation still missing.
- [Embedded ROM/key-material scan](docs/embedded-rom-key-material-scan.md): 27 scoped objects, including all retained update components and verified initial-data expansions.
- [Readable key-provider references](docs/core0-rom-provider-reference-study.md): bounded instruction/literal candidates and rejected cross-MCU address matches.
- [Fantom access-route audit](docs/fantom-access-route-audit.md): a gated stock factory-shell endpoint, MMC boot autodetection and corrected console/recovery claims.
- [Native arithmetic primitives](docs/native-arithmetic-primitives.md): bounded native shaping, feedback and voice-end reference semantics.
- [Operand variants and macro boundaries](docs/operand-variants-and-macro-boundaries.md): exact mono-sum and cross-destination allpass comparisons, with oscillator-layout and exceptional-macro limits.
- [Oscillator layout candidates](docs/oscillator-layout-candidates.md): competing arities consistent with six independently owned coefficient anchors.

This directory contains offline tools and derived research. It does not contain
a working custom synth engine, general assembler, flasher or hardware driver. A constrained
emitter reproduces two verified fragment families; it does not schedule arbitrary operations. Nothing
here opens a device or executes Roland's plugin. Production Oscairn code was not changed.

## Reproduce

Python 3, Capstone 5.0.7 and pyelftools 0.33 support the analysis; `requirements.txt` records
these dependencies. Preparing exports also uses Xcode's `dyld_info` and
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
The initial 19-note update was applied to the vault on 2026-11-10 through reviewed file access.
Subsequent passes add nine studies, for 28 verified notes, including the official
MC-101/JUPITER-X firmware comparisons. Firmware downloads remain local/ignored.
Saved hashes were checked before each update; every note was verified byte for byte.
Original backups, the initial validated patch and the applied hash manifests remain
ignored/local. The patch records the initial original-to-updated change;
do not reapply it to the already updated vault. Check for newer edits before future
updates. No code or vendor artifact was written there.
