# Stage keyboard targets for Oscairn

Research snapshot: 2026-11-11. This is an initial evidence-based screening, not a
tested port or purchase recommendation. Oscairn's current host and device-profile
work is described in the sibling project's README and OS documentation. An
internal port needs compatible CPU/OS, sufficient working RAM, boot/recovery
access, audio/display/panel drivers and measured realtime performance. Putting a
DSP algorithm on a coprocessor is separate from running the CLAP/LV2 host there.

Update: the [V-STAGE firmware inventory](vstage-firmware-hardware-study.md) now
verifies five named BMC update targets, bmc0..bmc4, in the official 1.11 package.
Targets 1/2 and 3/4 share identical images. The UI/host CPU and physical package
count remain unverified; no Linux/i.MX8 assumption follows from those filenames.

## What physical Fantom hardware would add

Firmware and paired native code let us recover used instruction contexts,
constructor resources, arithmetic expressions and host/DSP message paths. They
do not by themselves establish silicon precision, rounding, saturation, timing,
hazards or unexercised instructions. A Fantom-07 would permit direct measurement
and comparisons against the offline model. The biggest improvement comes once
we have a safe way to submit controlled DSP programs and capture results; simply
owning the instrument does not establish that access or a recovery path.

A reliable custom engine does not require every chip feature to be mapped first.
Prioritize safe loading/recovery, a calibrated useful instruction subset and the
actual audio/control path. A complete chip map remains a larger undertaking.
Stock audio or MIDI observations alone cannot uniquely prove every DSP opcode.

## Candidate comparison

Confidence labels refer to the cited evidence, not all production revisions.
Unknown silicon is intentionally left unknown rather than inferred from engine
brands or similar keyboards.

| Keyboard | Processor/platform evidence | Stage controls and Oscairn assessment |
|---|---|---|
| Fantom-07 | Existing repository firmware research: i.MX8M Linux host plus Roland BMC DSPs. Safe custom loading and hardware calibration remain open. | Most useful continuation of our existing Roland work; no tested Oscairn port yet. See the access and packet/loader studies. |
| Roland V-STAGE 76/88 | Official 1.11 firmware targets bmc0..bmc4, with three distinct code/content groups. Exact physical chips, UI/host, RAM and boot access remain unverified. | Dedicated engine/effect sections and USB audio/MIDI make its panel worth investigating. The new [archive evidence](vstage-firmware-hardware-study.md) supports BMC-family research, without establishing a whole Oscairn host or Fantom-compatible loading. [Roland product](https://www.roland.com/global/products/v-stage_88/), [connections](https://static.roland.com/manuals/v-stage_reference/en-US/143855755.html). |
| Nord Stage 3 | A firsthand Stage 3 repair identifies AM1705DPTP4; TI documents AM1705 as ARM9. Clavia's May 2023 parts list names an ARM host and SHARC DSPs for NS3; exact DSP model/count not established. | Rich dedicated panel. Physical drawbars are specific to Compact; 88/HP76 have LED/button drawbars. Standard ARM/SHARC documentation helps, but a whole Oscairn host port, boot access and drivers are unproved. [Repair](https://www.reddit.com/r/nordkeyboards/comments/1j6utsx/fixed_my_dead_stage_3_mainboard/), [TI](https://www.ti.com/product/AM1705), [manufacturer parts list mirror](https://device.report/m/0cd5cc22278a8379320e6ecf27ef13cc9397080614ffbb69498135b6195a76fb.pdf), [model differences](https://www.nordkeyboards.com/legacy-products/nord-stage-3/overview/). |
| Nord Stage 4 | Exact CPU/DSP unverified here. A distinct mainboard part number does not identify the chips or prove Stage 3 compatibility. | All models have physical drawbars, dedicated layer faders and extensive synth/effect controls. Its documented CC/NRPN protocol is useful for an external Oscairn adapter; internal loading is a different research problem. [Product](https://www.nordkeyboards.com/products/nord-stage-4/), [manual](https://www.nordkeyboards.com/wt/documents/951/Nord%20Stage%204%20User%20Manual%20v1.6X-Edition-N.pdf). |
| Yamaha CK76 | Exact CK76 silicon unverified. The CK61 service manual names SWX09 tone-generator initialization; that proves a CK61 subsystem, not CK76's board or CPU core. | Real model announced October 21, 2026: 76 semi-weighted FSB keys, 6.7 kg, drawbars, filter/effect controls, speakers and battery operation. Strong portable-panel candidate; no internal general-purpose host path established. [Yamaha release](https://www.yamaha.com/en/news_release/2026/26102101/), [original CK61 service manual mirror](https://www.manualslib.com/manual/4649084/Yamaha-Ck61.html). |
| Original-generation Korg Kronos | Firsthand research identifies Intel D510/x86 Linux/GRUB and a TI AM1806 NKS4 for panel/display/audio over USB, with separate serial keybed. This is evidence for that generation, not every Kronos/Nautilus/Grandstage. | Official controls include nine sliders, eight knobs and 16 switches. Strongest alternative internal-host lead found here, because boot and I/O research already exist. Proprietary interfaces, older CPU limits and modern audio-driver integration still need work. [Owner research](https://marcan.st/2016/06/hacking-and-upgrading-the-korg-kronos/), [Korg guide](https://cdn.korg.com/us/support/download/files/2fd1d54ad1f6f5e32caa8f5cd622e565.pdf). |
| Kurzweil PC4 / PC4-7 family | Exact host/DSP unverified here; VAST/FlashPlay descriptions are not CPU identification. Check the particular model/revision before transferring details. | PC4's official specification lists nine sliders, nine knobs, ten assignable switches and 16-zone MIDI control. Strong control-surface lead; no internal Oscairn execution path established. [PC4](https://kurzweil.com/pc4/). |
| Studiologic Numa Compact X SE | Exact host/DSP and internal boot path unverified. | Officially nine assignable sliders, seven pots, 23 buttons, 88 semi-weighted keys with aftertouch, USB audio/MIDI and 7.1 kg. Attractive lightweight external-control candidate; these controls do not prove that its internal processor can host Oscairn. [Specifications](https://www.studiologic-music.com/products/numacompact_se/specs/). |

Yamaha YC73 and Korg Grandstage X/Nautilus are additional screening candidates,
but this pass did not establish their silicon. Do not infer identical hardware
from shared sample/synthesis names. Grandstage X's stage panel and Nautilus's
controls should be compared directly with the desired density before prioritizing
an internal port. [Grandstage X manual](https://cdn.korg.com/us/support/download/files/7a6d89c8e80cd703ad4a13e316de2470.pdf),
[YC61 family MIDI documentation](https://data.yamaha.com/files/download/other_assets/4/1311174/VCN7200_YC61_owners_manual_En_C0.pdf).

## Research priority and evidence still needed

For the current project, keep Fantom-07 first because of the existing evidence
and intended hardware purchase. Investigate a specifically identified older
Kronos as an alternative internal host; investigate V-STAGE next for its panel
and possible Roland-family reuse, without assuming common silicon. Nord Stage 4,
PC4 and CK76 are good panel candidates, but their porting ranking cannot be
settled without stronger internal evidence. Numa Compact X SE is especially
interesting if using an external Oscairn computer is acceptable.

Before selecting another device for an internal port, obtain exact-revision board
photos or service diagrams, firmware/GPL inventory, boot/recovery evidence, RAM
layout and audio/panel interface documentation. For external control, check
transmission as well as reception, local-off behavior, CC/NRPN/SysEx routing,
split/layer modes and LED/display feedback. A published receive table or a large
panel does not guarantee arbitrary bidirectional control.

## Qwen review

Qwen's bounded 180-second public-web pass ended without a report. Its gathered
material was not promoted to verified fact. A separate short synthesis over
independently checked facts was reviewed manually. It made several mistakes:
it confused Roland BMC DSP mapping with MIDI-controller mapping, invented motor
fader implications, over-ranked Nord Stage 3 based on a Linux-capable CPU without
system-access evidence, and called a Kronos interface USB audio-class without
establishing class compliance. Those claims are rejected. Only the general
distinction between host ports, DSP kernels and external controllers was retained.
Worker logs remain ignored under local/; temporary public downloads are not
committed. No downloaded code was run and
no device was accessed. V-STAGE BMC target names are now verified in the follow-up;
its exact physical chips/host, and Stage 4/CK76 silicon, remain unresolved.
