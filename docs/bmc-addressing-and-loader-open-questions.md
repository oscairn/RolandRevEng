# BMC addressing and loader open questions

2026-11-12. Questions the night's Fantom-07 measurements raise for the BMC research, and the
owner's direction for where it goes. Sources: [host link](fantom-host-link-measurements.md),
[audio link](fantom-audio-link-measurements.md),
[i.MX interfaces](fantom-imx-interfaces-and-sound-chip-links.md) and
[the accelerator feasibility assessment](bmc-accelerator-feasibility.md).

## The owner's direction (2026-11-12)

- Oscairn is not to drive Roland's stock engines for now.
- In his words: "eventually we'll want to implement open source ports of rolands engines and get
  those running, along with other engines that can use that chip".
- On loading: "once we get the bmc fully mapped, could we build firmware for it that can take
  binaries over that usb connection and then we can load accelerators on and off it as needed?
  ... of course we need to figure out how to address each individual bmc (would also be important
  if we eventaully run this on synths with more or less bmcs)".

## How each BMC is addressed on the link

- Only **0xE1** was seen as the sound engine's address on `/dev/ttyGS0` (measured). 0xEF took
  settings and 0x75 lamp words (measured), but which chip answers to either is unknown.
- **0xE2 is inferred**, not seen: Roland's test tool also commands 0xE2 (static), and the unit
  has two BMCs. No frame to or from 0xE2 appeared in any capture.
- Unknown: whether the chip on the far end of the USB link forwards frames for the other BMC, by
  what path, and whether the address byte or something else selects the chip.
- A loader that serves instruments with more or fewer BMCs needs an addressing scheme that does
  not assume two. Stock firmware's convention (0xE1, 0xE2, ...) is a starting point, not a
  confirmed rule.

## Which chip is on the far end of the USB link

- The device tree gives one USB device port (`usbotg2`) and no per-chip nodes (GPL source). Its
  host enumerates it at boot (measured). Which BMC that is, and whether it is the same chip that
  clocks SAI1, is not established.
- Possible evidence: which BMC's CORE1 firmware holds a USB host stack for the internal port
  (static, not yet looked for), or a diagnostic build that reports its own identity over the link.

## Whether UART3 or UART4 reaches a BMC

- Both are enabled with no consumer and had zero receive counts all evening, including across
  Roland's app starting (measured). The pinmux proves the pads, not the traces.
- Unknown: whether either reaches a BMC (a boot console or recovery path would matter a great deal
  for a loader), the panel processor, or a test header. Board inspection or a passive capture
  across a BMC reset would settle it.

## What a resident loader would need

Taking the owner's direction as the goal (firmware on the BMC that accepts binaries over the USB
link and loads accelerators on and off), the research would need, at least:

- **Addressing:** a confirmed way to name each BMC (above), so a binary reaches the intended chip
  and the loader reports which chip it is.
- **The bridge:** where host frames become CORE1 work. The research has not recovered the
  component that turns host frames into CORE1 queue words (see
  [core1-task-context-and-host-peer.md](core1-task-context-and-host-peer.md) and
  [host-core1-bridge-followup.md](host-core1-bridge-followup.md)). A resident loader either lives
  behind that bridge or replaces it.
- **What the loader keeps running:** the stock control firmware also serves the audio clock and
  link, keys, lamps, MIDI and USB to a computer (inferred, feasibility assessment section 3d).
  A loader that replaces it must keep those or reimplement them; one that runs beside it must
  share CORE1 safely with the stock manager.
- **Program loading and readback:** writes to DSP program, coefficient and data memory that are
  acknowledged and read back, with known entry, return and quiescence (feasibility assessment
  section 3c lists the gates).
- **Recovery:** a tested way back to stock that does not depend on the loader working.
- **Throughput:** the USB link's usable rate for binaries, unmeasured; the link also carries keys
  and status that must keep draining (measured backlog behavior).
- **Silicon facts:** arithmetic precision, cycle budget and timing per DSP, none measured yet.

## Smaller open items from the night

- Whether Roland's app writes with source byte 0x00 by design (measured) where the static reading
  had 0x60.
- What the kind-9, sub-type 9 status frames from 0xE1 contain.
- Whether the measurements hold with both BMCs on stock firmware (one ran a diagnostic CORE1
  build).
