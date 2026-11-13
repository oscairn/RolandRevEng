# BMC accelerator feasibility

2026-11-12. This assessment asks whether the two Roland BMC sound chips in the FANTOM-07
could serve Oscairn as accelerators. Oscairn now runs on the instrument's i.MX8M Mini (four
Cortex-A53 cores, 992 MiB as the kernel sees it). It draws only on existing research notes and
tonight's measurements. No firmware was examined, no tool was run and no device was contacted.
"The research" means `bmc-research/docs/` and the Roland notes in the Obsidian vault. Each claim
names its note and says how firmly that note established it: **measured** (seen on the unit),
**static** (read from firmware or Roland's programs as files), **inferred**, or **guessed**.

## Short answer

Not yet, for anything that runs Oscairn code on the chips. The research has mapped a narrow but
carefully checked slice of the DSP instruction set and much of the loading machinery. Still
missing are a proven way to put code on the chips, a way to read it back, a recovery path, the
meaning of a program's entry and return, and any measurement of the silicon's arithmetic or
timing. The research says so itself (`bmc-mapping-status.md`). The near-term options use
Roland's stock engine and stock effects as they are, over the message link Oscairn already
reads. Both need one piece of evidence first: a record of what Roland's app sends during
ordinary actions. Neither needs anything loaded onto the chips. All of this ranks below making
the A53 path solid: real-time tuning, the start script and the display.

## 1. What is established about the chips

**Topology (static, with parts inferred).** Each BMC has three kinds of processor
(`BMC chips.md`, `BMC DSP packet and loader map.md`):

- **CORE0**, whose firmware image ships encrypted. The research names it as a plausible home for
  the bridge between the Linux link and CORE1, but has not mapped what it does
  (`host-core1-bridge-followup.md`, inferred). The vault's newer checkpoint says both CORE0
  images can now be read in plaintext (`bmc-mapping-status.md` in the vault). No note maps their
  contents yet.
- **CORE1**, an ARM Cortex-M-class core with a floating-point unit, running unencrypted
  firmware. It handles voice allocation, MIDI, the DSP driver and manager, coefficient updates
  and the receive queues (static). The vault checkpoint reports that custom diagnostic code
  for bmc0's CORE1 has run on the owner's unit and answered over USB MIDI (measured by the
  other session, per `bmc-mapping-status.md` in the vault).
- **A DSP array** of six render DSPs plus one "system" DSP, with paired I/O blocks, cross-mix
  buses between DSPs, DMA, and separate "DRAM-IO" processors that use a different instruction
  format and serve external-memory delay lines and clearing (static, from firmware strings and
  program lists).

**Division of labor between the two chips (inferred).** Both run complete voice allocation.
bmc0 carries the behavior-modeling, organ, VTW and piano content. bmc1 carries the ZEN-Core
PCM and drum engine, the wave ROM and the expansion manager (`BMC chips.md`). How the two
outputs merge onto one audio link, and which chip is clock master, are open questions there.

**Memory.**

- *Program RAM*: one window per DSP, written by CORE1 (static). Stock effect slots reserve 4 to
  6 KB per placement. The large base programs on DSP4 and DSP5 exceed that, and an earlier
  "2 KB per DSP" limit was wrong (`BMC DSP packet and loader map.md`, `kernel-audio-abi-study.md`).
  No total program-RAM size or per-sample instruction budget is known. The loader map says
  plainly that stored program size is not a cycle count.
- *Coefficient and data memory*: live coefficient banks written through per-DSP conversion
  ports; short circular data arrays for state and history; a separate direct/windowed data path;
  and external RAM reached through the DRAM-IO path. Reservations are tracked per effect
  instance by type (static: `kernel-audio-abi-study.md`, `transfer-spaces-study.md`). The
  research warns that its memory "tags" are contextual findings, not a hardware memory map
  (`opcode-semantics-ledger.md`).
- *Wave memory*: factory samples sit in parallel NOR flash on a dedicated wave bus, and updates
  never touch it. `BMC chips.md` gives "4× MT28EW01G" with bmc0's firmware showing two wave banks
  and bmc1's four. The bank names are static; the wiring is inferred, and the board-level source
  for the chip count is not in the notes read here.

**Reconciling 256 MB and 4 × 1 Gbit.** These are two different memories, and the notes leave
both partly open. Four 1-Gbit NOR chips hold 512 MiB of read-only factory waves. `BMC chips.md`
lists that row as "64 MB", which is an arithmetic slip: 4 Gbit is 512 MiB. The 256 MB "user
sample" figure on the settings screen has to be writable memory. The research does not say where
it lives. What it does show:

- Linux talks to a "user wave" service on the sound engine that reads and writes 128 KiB blocks
  (static, from Roland's app: `host-core1-bridge-followup.md`). That fits user wave data being
  moved into memory on the BMC side, but the destination is not established.
- bmc1 has an expansion manager with its own wave-block tables (static, medium confidence:
  `BMC chips.md`).
- Roland's app was 11 MB resident with 104 MB swapped during the survey (`fantom-0.md`, measured).
  That argues against the i.MX holding 256 MB of samples in RAM. So the 256 MB is more likely
  BMC-side RAM or a flash quota (inferred, weak).

**How DSP programs are loaded (static).** The programs are not separate files. They are lists
built into CORE1's firmware, and CORE1 boots from the BMC's own flash; nothing on the i.MX loads
it (`BMC chips.md`). At start-up and on each effect change, CORE1's DSP manager walks a list and
copies each *segment* (a DSP, base, length and capacity) into that DSP's program RAM, by CPU loop
or DMA. It writes coefficients by symbol through conversion ports (`BMC DSP packet and loader map.md`).
The loader copies bytes unchanged, so the decoded packets are exactly what runs. One of the
three loading paths does not check segment capacity (`kernel-audio-abi-study.md`). The effect
lifecycle is a fixed sequence: load the program, load the DRAM-IO program, wait, set levels,
open a mute gate, ramp the master level. No step in it is shown to clear all history
(`kernel-audio-abi-study.md`, `effect-lifecycle-and-parent-entry-study.md`).

**Voices and effects (static, partly inferred).** There are 16 parts with voice reservations.
Effect instances are placed by descriptors that name a DSP and reserve program, data and
coefficient ranges; five such placements are recorded (`kernel-audio-abi-study.md`,
`fantom-voice-resource-plans.md`). Polyphony is not established. A firmware stress string
mentions 564 voices, retailers claim 256, and the Jupiter-X Base Engine is documented at 256
partials (`BMC chips.md`).

**Audio paths.**

- A 16-slot, 32-bit TDM link at 48 kHz, with the BMCs as clock master (device tree, plus
  `fantom-0.md`, measured). Roland's app uses 6 channels each way.
- It plays its pad sampler into channels 2 to 5 and reads capture channels 0 and 1 for sampling
  (static from the app; the slot mapping is inferred: `fantom-0.md`).
- With the app stopped, audio sent on any of pairs 0/1, 2/3 and 4/5 was heard, and the link kept
  clocking (`fantom-0.md`, measured).
- The firmware names no per-slot routing; the path is set by register initialization alone
  (`BMC chips.md`, a negative static result). The research never ties the DSPs' internal effect
  I/O to physical TDM slots (`kernel-audio-abi-study.md`).
- USB audio and MIDI to a computer, DIN MIDI, the keyboard scanner and the panel lamps all go
  through the BMC side (`fantom-0.md`, inferred strongly).

**The host link.** Linux reaches the chips through a USB serial gadget carrying addressed
frames. The framing is static (`host-transport-study.md`) and was confirmed tonight on 26 KB of
real traffic (`fantom-0.md`, measured). What the link can do, as far as the notes show:

- MIDI words, panel words, typed parameter blocks, and request/reply services: version queries,
  expansion install and delete, user-wave block transfers (static: `host-core1-bridge-followup.md`).
- Inside CORE1, a SysEx handler reads and writes a hardware register window that overlaps
  program RAM (static). It bypasses the DSP manager, and its read reply can overrun its stack
  buffer at allowed sizes (static size discrepancy, not tested).

What the notes do not show:

- The component that turns host frames into CORE1 queue words has not been recovered. "No
  external host-to-CORE1 path is proven" is the research's own repeated conclusion
  (`core1-task-context-and-host-peer.md`, `host-core1-bridge-followup.md`).
- No program upload, program readback or acknowledged write over the link is demonstrated.

## 2. How much of the DSP instruction set is understood

The research declines to give a percentage, on purpose. It does not know the full population of
instruction contexts. The same control word can compute different things under different packet
headers. Dividing a recognizer count by 65,536 would mislead (`bmc-mapping-status.md`). What it
does count:

- **Structure (static, strong).** All 588 program segments in the corpus (61,334 packets across
  two Fantom CORE1 images and the ZENOLOGY plugin) split deterministically, consume exactly their
  length and round-trip byte for byte. Packet length, control-word count and literal widths are
  understood (`BMC DSP packet and loader map.md`, `header-fields-study.md`). This is grammar,
  not meaning.
- **Semantics (static, narrow).** 19 exact instruction *sequences* have checked meanings. Each
  is admitted only in its full context. Together they cover gain and mixing, multiply-accumulate,
  four-stage allpass, state-variable and history filters, clipping, cubic waveshaping, an
  oscillator fold and some coefficient transfers (`opcode-semantics-ledger.md`,
  `supported-code-generation.md`). For scale: in LINEDRIVE, the effect chosen as the next whole
  program, 39 packets remain outside admission; FETDRIVE leaves 48
  (`emulator-next-program-targets.md`). No complete stock effect executes yet.
- **The emulator.** It is a functional packet-stepper for those 19 profiles, with memory and
  per-packet traces (`fragment-emulator.md`). Validation compares its output with equations
  derived *independently* from Roland's native desktop code (ZENOLOGY), on real stock fragments,
  every intermediate port value and store included (`fragment-emulator-validation.md`). One
  effect's full arithmetic chain, 1,692 bytes, matches the native callback's audio and state
  over 12,000 frames. Original voices (oscillator, gain, filter, shaper) run in the model and
  relocate into five real Fantom placements (`original-bmc-filtered-voice.md`,
  `fantom-voice-resource-plans.md`). All of this is software against software, as the notes
  stress.
- **Unknown.** Nothing has run on BMC silicon in this research, so the following are all open:
  - arithmetic precision, rounding, saturation and accumulator width;
  - pipeline latency, hazards and the per-sample cycle budget;
  - control flow (call, return and the end-of-program forms);
  - the execution meaning of the mute gate, which CORE1 is seen patching;
  - condition bits, the exponential and other special operations, most oscillator forms;
  - the DRAM-IO instruction format;
  - how work is scheduled across DSPs, and real interrupt delivery

  (`opcode-semantics-ledger.md`, `condition-fields-and-implicit-return-study.md`,
  `special-ops-and-exp-study.md`, `bmc-mapping-status.md`).

## 3. What "using them as accelerators" could mean

### a. Roland's stock engine as a sound source beside Oscairn

Roland's engine already plays the keys with its app stopped, under Oscairn's own sound
(`fantom-0.md`, measured). Driving it on purpose means writing to the link, which Oscairn so far
only reads.

- **Evidence for a message layer.** Roland's app sends MIDI words to the sound engine (static).
  It also builds typed parameter blocks and scalar parameter edits; 74 descriptor tuples on
  the host side match the descriptors CORE1 holds (static, executed in isolation:
  `fantom-host-family-study.md`, `fantom-host-write-study.md`). Inside CORE1, the
  parameter-edit receiver, the store and the coefficient producers are traced down to live
  coefficient writes (`fantom-parameter-stream-study.md`, `fantom-parameter-store-study.md`).
  ZENOLOGY carries the same voice-parameter namespace (`Roland sound engines 6.md`).
- **What is missing.** How host messages become CORE1 words (the missing bridge), how tones are
  selected, and a correlated record of real traffic.
- **What could go wrong.** A malformed frame could stall or confuse the engine. That costs a
  power cycle, which restarting Roland's app needs anyway (`fantom-0.md`). Some services change
  persistent state, such as expansion install and delete and user-wave writes; those must stay
  untouched.
- **What it buys.** Roland's full engine at no A53 cost. But its audio goes straight to the
  outputs, outside Oscairn's graph. Under RFC 0004 that is "external MIDI control plus physical
  audio return", not an in-graph backend, unless the engine's output can be brought back over
  capture with known latency (`0004-hardware-services.md`).
- **The cheapest useful case** is one write: Roland's Local Switch, so the stock engine stops
  doubling the keys (`fantom-0.md`, read from the app, untried).

### b. Stock effects as a processor for audio Oscairn sends

- **What is missing.** Whether audio arriving on any TDM slot passes through Roland's MFX,
  chorus or reverb is not established anywhere. The firmware names no slot routing
  (`BMC chips.md`), and the research never ties effect I/O to TDM slots
  (`kernel-audio-abi-study.md`). Roland's app feeds its pad sampler into the BMC mix at two
  places (inferred, `fantom-0.md`); whether pads get effects in the stock design is not in the
  notes. Control would need option a's parameter layer. Getting processed audio back into
  Oscairn would need capture routing, which tonight left unchecked.
- **What could go wrong.** Very little, as long as it is only listened to. Once controlled, the
  same risks as option a apply.
- **What it buys.** Roland's reverbs at no A53 cost. But the result would be a hardware-required
  sound mode by RFC 0004's rules, and it adds latency that cannot be compensated until capture
  is mapped.

### c. Oscairn-authored DSP programs under Roland's control firmware

The research describes this case, but nothing below proposes doing it. Before anyone tries,
all of the following must hold (`kernel-audio-abi-study.md`, `host-core1-bridge-followup.md`,
`BMC DSP packet and loader map.md`):

- a proven route that writes and **reads back** program and coefficient memory through the
  stock manager, in its own task context, with its exclusion honored;
- an owned, unused reservation, rather than one occupied by a stock effect;
- known meanings for program entry, return and the mute gate;
- a quiescence point;
- a mapping from DSP output to TDM slots;
- a tested recovery to stock behavior that needs no reflashing.

The research's own probe design keeps a whole stock effect in place. It only varies
already-understood gains, and requires every gate above before executing anything
(`kernel-audio-abi-study.md`). The largest unknowns are the loading route, the cycle budget,
and silicon precision and timing. One more: the only register-window path found bypasses the
manager and has an unresolved stack overrun. **Readiness: thinkable as research, not as a
product path.** It is also unclear what it would buy. Tonight the A53 ran Oscairn's startup
synth, sequencer and delay at about 25% load (`fantom-0.md`), and the render DSPs' capacity is
unmeasured.

### d. Replacing the control firmware

Nothing here proposes this either. The control firmware does far more than run DSPs. The notes
put the following on the BMC side: the audio clock and DAC, the wave bus, USB to a computer, DIN
MIDI, the key scanner's path to Linux, and the lamps (`BMC chips.md`, `fantom-0.md`). Replacing
it means reimplementing all of that, or losing keys and sound. It would also require proven
update acceptance and a recovery path that survives a bad image. `bmc-mapping-status.md` lists
recovery as unresolved, and this assessment did not open the flashing notes. **Readiness: not
thinkable yet.** The largest unknowns are recovery, CORE0's role, and every peripheral the
firmware runs.

### Summary

| Option | Requires (not yet existing) | Risk | Payoff | Readiness |
|---|---|---|---|---|
| a. Stock engine as a sound source | Correlated capture of the app's link traffic; frame-to-engine translation; tone selection; writing to the link | Low to moderate (power cycle on a bad frame; avoid persistent-state services) | Roland's engine at no A53 cost, but outside Oscairn's graph | Closest; one capture away from a first write (Local Switch) |
| b. Stock effects on Oscairn audio | Whether any TDM input reaches effects; option a's control; a capture return path | Low while listening | Free reverb and chorus; hardware-required sounds, uncompensated latency | Unknown; one listening test decides whether to continue |
| c. Oscairn DSP code under stock firmware | Proven load and readback via the manager, owned reservation, entry and return semantics, routing, recovery, silicon calibration | High (corrupt graph, hangs; flashing if a resident bridge is needed) | Unmeasured DSP capacity; the A53 is not yet the bottleneck | Research stage |
| d. Replace control firmware | Everything in c, plus clock, DAC, wave bus, USB, MIDI, keys, lamps, CORE0, recovery | Very high (loss of keys and audio) | Full control | Not thinkable yet |

## 4. Sample memory and polyphony

Factory waves live in read-only NOR on the wave bus. A BMC sample voice reads from the wave bus
or from BMC-side memory, never from Linux storage (`BMC chips.md`, static and inferred). User
waves appear to be copied in from Linux in 128 KiB blocks (`host-core1-bridge-followup.md`,
static). Roland's own pad sampler, though, runs on the i.MX: eight player threads mix into TDM
channels 2 to 5, with the app holding its sample files open (`fantom-0.md`, static and measured).
Roland itself, in other words, keeps the streaming-style sampler on the Linux side and leaves
keyboard multisamples to the engine (`Roland sound engines 6.md` notes the same split from
Roland's documentation).

So a sampler hosted on the chips would be bound by BMC-side memory: at most the 256 MB user area,
wherever that turns out to be. It would be loaded over a serial-class link whose throughput is
unmeasured, and it would need option c's whole stack before playing a note. An A53 sampler can
stream from 25 GB of free eMMC. It has about 416 MB of RAM free with the engine running
(`fantom-0.md`) for preloaded attack segments, and RFC 0025 already models a sample cache as
opportunistic memory. **Keep the sampler on the A53.** Polyphony there should be measured, not
borrowed from the BMC's unconfirmed 256-voice figure.

## 5. Recommendation

**Order of work.**

1. Real-time tuning of the A53 path.
2. The start script. It carries a BMC question that comes first: if `mi078` never runs after
   power-on, do the BMCs still clock the link and pass Linux audio? Tonight the app had run
   before it was stopped, and `fantom-0.md` lists this as unknown.
3. The display.
4. Option a and option b, as the low-risk steps below.
5. Option c, only after the research closes its own gates. Option d stays off the roadmap.

**First concrete, low-risk steps.**

- For option b: with Roland's app stopped, play a dry impulse on each output pair and record
  MAIN OUT, listening for any tail. In the same session, record `hw:1,0` capture (step 8 in
  `fantom-0.md`). This sends nothing to the chips.
- For option a: record the stock app's link traffic during a short script of ordinary actions:
  select a tone, move a slider, toggle Local Switch, change the reverb level. Observe the app's
  own reads and writes rather than opening the link a second time, which would steal its bytes
  (`host-core1-bridge-followup.md`). This is the "minimum missing observation" the research
  names (`core1-task-context-and-host-peer.md`). Only then try one write, Local Switch, the way
  `fantom-0.md` already plans its single lamp write.

**Do not attempt yet:**

- any write through CORE1's register-window SysEx handler;
- any program, coefficient, execution-mode or segment write;
- expansion or user-wave service messages;
- flashing BMC firmware for accelerator purposes;
- a second reader on the link while Roland's app runs.

## Notes on sources

**Read:**

- `bmc-research`: `README.md`, `bmc-mapping-status.md`, `BMC DSP packet and loader map.md`
  (all but its CORE0 section), `opcode-semantics-ledger.md`, `fragment-emulator.md`,
  `fragment-emulator-validation.md`, `fantom-voice-resource-plans.md`,
  `core1-task-context-and-host-peer.md`, `host-transport-study.md`,
  `host-core1-bridge-followup.md`, `kernel-audio-abi-study.md`, `emulator-next-program-targets.md`
  and `research-queue.md`.
- The openings of `original-bmc-filtered-voice.md`, `coefficient-envelope-and-completion-study.md`,
  the parameter store, stream and dispatch studies, `core1-receive-and-test-controls.md`,
  `effect-lifecycle-and-parent-entry-study.md` and `supported-code-generation.md`.
- Vault: `BMC chips.md`, `bmc-mapping-status.md`, `BMC DSP ISA.md` (checkpoint notes), the
  relevant sections of `Roland sound engines 6.md` (the latest of seven versions) and
  `Stage Keyboard Targets.md`.
- Oscairn: `fantom-0.md`, RFC 0004, and RFC 0025's progress and open questions.

**Skipped on purpose:** notes on keys, ciphertext, passphrases, update decryption, access routes,
shells, SSH packages, ROM dumping and BMC flashing.
