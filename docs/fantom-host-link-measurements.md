# Fantom-07 host link measurements

2026-11-12. What the i.MX's USB serial link to the BMC side (`/dev/ttyGS0`, the `g_serial`
gadget on `usbotg2`) carried on the owner's FANTOM-07, with Roland's app (`mi078`) running and
stopped. Each claim is marked **measured** (seen on the unit), **GPL source** (read from Roland's
published kernel source), **static** (read from Roland's programs as files, without running them)
or **inferred**.

> **Not pure stock firmware.** During these measurements one BMC ran a modified diagnostic CORE1
> build (see [the CORE1 diagnostics note](fantom-core0-key-recovery.md)). Everything below was
> seen with that build in place. Repeat any result that matters on stock firmware before relying
> on it.

The captures and `strace` traces behind this note stay local and unpublished
(`local/fantom-unit-2026-11-12/`). Byte strings below are short frame headers and payloads, not
extracts of Roland's programs.

## How it was observed

- **App stopped:** `systemctl stop weston-term`, then `/dev/ttyGS0` opened raw with echo off and
  only read (`cat` into a file), while the owner played. Three captures: keys with Local Switch on
  (18 s, 26,096 bytes), keys with Local Switch off (480 frames), and keys after Linux sent Local
  Switch off (302 frames).
- **App running:** `strace` attached to `mi078`, recording its reads and writes on the two
  descriptors it holds on `/dev/ttyGS0`: at rest (5 s), while the owner moved one slider, and
  while the owner switched Local Switch off and on in Roland's menu (about 45 s).
- The link was never opened a second time while Roland's app held it.

## Frame forms

- **Confirmed on the unit** (measured): every byte of every capture parsed as the frames
  [host-transport-study.md](host-transport-study.md) describes (static): a short frame of 12
  bytes (byte 0 the kind times two, byte 1 the source, byte 2 the destination, byte 3 a sub-type,
  bytes 4 to 10 payload, byte 11 its length), and a long frame with bit 0 of byte 0 set (16 header
  bytes, the payload length as 32 bits little-endian at bytes 12 to 15, then the payload). No
  capture of the app-stopped link had a byte left over.
- **Stale bytes past the count** (measured): short frames often carry leftover bytes after the
  counted payload, for example the note number repeated after a 4-byte MIDI word. Readers must
  honor byte 11.
- **Roland's app writes with source byte 0x00** (measured, every written frame in the three
  traces). The static reading had it sending as 0x60; on the wire the byte was 0x00.

## Addresses seen

| Address | Role | Basis |
|---|---|---|
| 0x02 | the keyboard (sub-processor scanning the keys) | measured as a source; role static |
| 0x60 | Linux-side destination of the keys' own frames and of the sound engine's status frames | measured |
| 0x61 | Linux-side destination of the zones' MIDI words for the keys | measured |
| 0xE1 | the sound engine: receives MIDI clock and forwarded panel words, sends status | measured |
| 0xEF | settings: receives system and level parameter messages | measured |
| 0x75 | the panel's lamps (kind-6 lamp words) | measured as a destination; role static |
| 0xA1 | one of the app's MIDI inputs (static); sent kind-2 frames to 0x60 | measured |

Static readings also name 0x63 and 0x64 as key destinations; the unit used 0x61 throughout.
0xE2 never appeared (see [the open questions](bmc-addressing-and-loader-open-questions.md)).

## Key events, in two forms

- **The key's own frame** (measured): kind 6 from 0x02 to 0x60, panel word `88 nn 00 vv` for
  note on and `87 nn 00 vv` for note off (nn the note, vv the velocity, release velocity on
  off). The third byte was always 0. One per key event, whatever the zones or Local Switch.
- **The zones' MIDI words** (measured): kind 3 from 0x02 to 0x61, a USB-MIDI-style word whose
  first byte is 0x29 for on and 0x28 for off (port 2 in the high nibble), then status, note,
  velocity. With one active zone there was one (status 0x91); in the Local Switch trace with
  three active zones there were three per key event (0x90, 0x91, 0x92, the same note and
  velocity).
- **Local Switch changes only the second form** (measured): with Local Switch off, only the
  kind-6 frames came (300 key frames, no kind-3 words, in one capture). Inferred: the kind-6 frame
  is the key itself and the MIDI words echo what Roland's engine plays from it.
- In the 18-second app-stopped capture with Local Switch on, the 122 kind-3 words and 122 kind-6
  frames agreed key for key (measured).

## The Local Switch setting message

- **Roland's app sends** (measured, `strace` while the owner toggled Local Switch in MENU >
  SYSTEM > MIDI): a kind-7 short frame to 0xEF, sub-type 1,
  `0e 00 ef 01 | 00 00 00 cf vv 00 00 | 05`, with vv 0 for off and 1 for on: system parameter
  0xCF. Each is followed by a kind-8 companion frame `10 00 ef 00 | 01 00 00 00 0c 0c ff | 07`.
  19 off and 18 on pairs were seen in the trace.
- **It works from Linux with the app stopped** (measured): on a fresh boot with Local Switch on,
  after Roland's app was stopped, writing those two frames (off) to `/dev/ttyGS0`, raw with echo
  off, turned Local Switch off: in the 12 seconds of playing after, the link carried only the
  keys' own frames and the instrument stayed silent.
- **It does not survive a power cycle** (measured): Local Switch was on again after one, and
  Roland's sound with it. The engine keeps the setting while it stays powered, including after
  Roland's app stops (measured: set off in Roland's menu, then app stopped, the instrument stayed
  silent while the owner played).
- Inferred: the companion frame's first payload byte echoes the parameter message's sub-type (1
  here, 0x0E for the level messages below), so it may close or commit a parameter block. Not
  tested.

## Traffic at rest, with Roland's app running

- **A MIDI clock to the sound engine** (measured): kind-3 frames to 0xE1 holding the word
  `0f f8` (code index 0xF, a single-byte message: 0xF8, timing clock). About 48 a second over the
  45-second trace (120 BPM at 24 per quarter note) and about 36 a second in the 5-second rest trace.
  Whether the difference is the tempo setting or tracing overhead was not checked. Inferred: this
  is how the app's sequencer clock (Roland's `tickgen` module) reaches the engine.
- **TEMPO lamp traffic** (measured): kind-6 frames to 0x75 with lamp word `85 01 ...`
  alternating between two values: lamp 1, which the test tool's lamp table names TEMPO (static).
  Inferred: the tempo blink. During the Local Switch trace, words for lamps 66, 67, 74 and 75
  (ZONE 1 and 2 in their two colors, static) also went to 0x75.
- **Status frames from the engine** (measured): long kind-9 frames from 0xE1 to 0x60, sub-type 9,
  112-byte payload, about ten a second, with the app running and stopped, at rest too. Header
  bytes 8 to 11 vary (`10 16 2d 00`, `00 02 00 00` and a few others). Their contents were not
  decoded; whether they carry meters or other status is a guess.

## Slider forwarding and level parameters

While the owner moved slider 1 with the app running (measured):

- **The panel word is forwarded to the engine:** kind-6 frames to 0xE1 holding the panel word as
  read from `/dev/i2c-slave-2`, `84 09 00 vv` (analog ID 9, slider 1, value vv). 49 in the trace.
  This agrees with the static reading that the app's "Thread Sw Ad" passes analog and switch words
  to 0xE1.
- **And a level parameter goes to settings:** kind-7 frames to 0xEF, sub-type 0x0E,
  `0e 00 ef 0e | 00 00 00 07 vv 00 0a | 05`, the value following the slider, each followed by a
  kind-8 companion `10 00 ef 00 | 0e 00 00 00 00 00 77 | 07`. 47 and 46 in the trace. Inferred:
  the part level the slider is assigned to; which parameter 0x07 in block 0x0E is was not
  determined.
- During the Local Switch trace, 31 analog words with ID 0 (`84 00 00 vv`) were also forwarded
  to 0xE1; which control sent them is not established (the panel map names no analog ID 0).

## A MIDI input

During the slider trace the app read two kind-2 frames from 0xA1 to 0x60 (measured): a short one
whose payload was `f0 f7` and a long one with a 32-byte payload. 0xA1 is one of the addresses the
app treats as a MIDI input (static); kind 2 was not read statically. Inferred: SysEx from one of
the MIDI ports. Which physical port 0xA1 is remains unknown.

## When nothing drains the link

- **It backs up** (measured): with a program reading the app-stopped link, Roland's engine kept
  playing the keys; when reading stopped, the last notes stayed on (stuck), and when reading
  resumed the queued frames came out in a burst (15 kB in 6 seconds). Whoever opens the link
  has to read it without pause and expect stale events at open.
- **Restarting Roland's app needs a power cycle** (measured): started again after being stopped,
  without a power cycle, it showed "program version error" and did nothing, with nothing else
  holding the link.

## What this does not establish

- Which BMC answers as 0xE1, or 0xEF, or passes lamp words on as 0x75.
- What the status frames say, and whether anything must be sent regularly to keep the engine
  talking (the keys arrived with nothing sent, so nothing is needed for that).
- Whether any of this differs with both BMCs on stock firmware.
