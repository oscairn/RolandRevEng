# BMC mapping status

2026-11-11. The research supports a constrained functional DSP subset and
substantial ARM control/loader metadata. It is **not a complete BMC chip map**,
a general DSP compiler or a cycle/bit-accurate emulator. No custom engine from
this project has run on a physical Fantom BMC.

There is no defensible whole-chip percentage. We do not know the complete
instruction/context population, and packet parsing, arithmetic semantics,
control firmware and hardware behavior have different evidence requirements.
Dividing a recognizer count by 65536, or treating a byte-parse rate as instruction
coverage, would produce a misleading percentage.

| Area | What is mapped/documented | What remains |
|---|---|---|
| Packet/container structure | Deterministic parsing, control/payload split, sized literals/extensions; the original three-image corpus has 61,334 packets | Other contexts do not gain execution semantics from successful parsing |
| Executable DSP subset | 18 exact sequence profiles, with constrained operands/resources and strict rejection of unsupported forms | General ALU/operand/extension decoding, branches/calls/returns, broader engines |
| FDRV arithmetic | 11 fragments, 1,692 composed bytes, 104 packets; native-policy stereo audio/ring/cache checks through wrap | Stock end/IO controls, silicon arithmetic/timing and a loadable wrapper |
| Authored voices | Oscillator, stereo gain, filter and cubic shaping; shaped filtered voice 510 logical bytes, 39 packets | Hardware scheduling, voice allocation, physical state/routing and launch |
| Placement/resource plans | Five Fantom placements and explicit owner/data/coefficient substitutions | General runtime allocator and safe whole-graph integration |
| Parameter control | Coefficient producers, envelope/mute state, snapshot/change bytes, stock FDRV descriptor reads and source-proved EFCT callback route | Full field effects, upstream parameter-store writes, external panel/MIDI routing, real task/IRQ exclusion |
| Memory/loading interfaces | Build-pinned render/DRAM-IO loaders, descriptors/reservations, DMA ordering, completion/IRQ paths and label encoding | Validated external entry, safe replacement/halt/return contract and recovery |
| Host/boot access | Readable CORE1 receive/transmit routes, comparison firmware, bounded key/provider searches | Readable installed CORE0/host peer, any required key, verified external protocol |
| Physical BMC behavior | No silicon execution/calibration in this research | Precision, saturation/rounding, pipeline latency, timing, aliases and real interrupt delivery |

The 18 profiles are exact **instruction sequences**, not 18 universally decoded
opcodes. Their arithmetic includes checked mix/MAC, allpass feedback,
state-variable/history filters, clipping, cubic shaping and selected coefficient
transfers. Context matters: identical control words can compute different results
under different headers/extensions. Recognition is deliberately narrow.
The 1,692-byte figure is the composed arithmetic reference, including authored
bridges/preloads; it is not the size of the whole firmware or a standalone loader
image. Other effects have useful partial DSP evidence or full native/scalar
references; that does not make their BMC packet programs fully emulated.

The five Fantom layouts are relocations/owner placements of checked material.
They are not five complete BMC maps or five independently emulated synth engines.
The recent coefficient/mute/parameter checkpoints deepen ARM control coverage;
they do not increase the 18 DSP execution profiles.

## Evidence to start from

- [Packet/loader map](BMC%20DSP%20packet%20and%20loader%20map.md): structural corpus and build-specific interfaces.
- [Supported code generation](supported-code-generation.md) and [semantics ledger](opcode-semantics-ledger.md): exact admitted forms and limits.
- [Fragment emulator](fragment-emulator.md): functional execution boundary.
- [Complete FDRV arithmetic](fdrv-cubic-waveshaping-study.md#complete-arithmetic-and-output-milestone-2026-11-11): comparison scope and preserved state.
- [Authored filtered/shaped voice](original-bmc-filtered-voice.md): reusable components and explicit hardware gates.
- [Fantom resource plans](fantom-voice-resource-plans.md): meaning of five placements.
- [Fantom ARM32 math/control](fantom-eqvg-control-study.md), [mute nesting](fantom-envelope-mode-study.md), [parameter dispatch](fantom-parameter-dispatch-study.md) and [raw parameter buffers](fantom-parameter-buffer-study.md): CPU evidence distinct from DSP ISA coverage.
- [Stock FDRV producer and EFCT callback](fantom-parameter-producer-study.md): factory ID85, 22-field snapshot, descriptor defaults and registered source path; no live scheduling claim.
- [Task contexts](core1-task-context-and-host-peer.md), [host bridge](host-core1-bridge-followup.md) and [CORE0/key limits](core0-ciphertext-and-key-location.md): access and ownership gaps.

## What separates this from the two intended outcomes

For a small custom engine using the supported components, the central remaining
steps are a verified external control/entry route, owner-correct memory/history
and audio scheduling, a valid launch/return wrapper, and hardware calibration.
The existing emitter and offline voices are starting material, not runnable
Fantom plugins. More parameter-source work alone does not close these gates.

For an emulator that runs arbitrary stock BMC engines, broader instruction and
control-flow semantics, precise numeric/pipeline behavior, memory/peripheral
models and boot/runtime inputs are still needed. Completing one arithmetic chain
is useful evidence but does not imply most stock firmware can execute.

Useful offline work can still recover new instruction contexts, upstream parameter
producers and registered caller paths. Hardware will make precision, timing,
entry/return and real transport questions much easier to test. Firmware-only
agreement with a desktop reference cannot settle those silicon properties.
