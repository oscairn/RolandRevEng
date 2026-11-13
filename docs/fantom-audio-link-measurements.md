# Fantom-07 audio link measurements

2026-11-12. The i.MX's SAI1 TDM link to the BMC side (ALSA `hw:1,0`), tried on the owner's
FANTOM-07 with Roland's app stopped. Each claim is marked **measured** (seen or heard on the
unit), **GPL source** (Roland's published device tree for this board), **static** (read from
Roland's programs as files) or **inferred**.

> **Not pure stock firmware.** One BMC ran a modified diagnostic CORE1 build during these
> measurements (see [the CORE1 diagnostics note](fantom-core0-key-recovery.md)).

## The link as the device tree describes it (GPL source)

From `arch/arm64/boot/dts/freescale/fsl-imx8mm-mi078.dts` (the `sound-bmc` node and `&sai1`):

- `simple-audio-card` named "nocodec", `left_j`, `dai-tdm-slot-num` 16, `dai-tdm-slot-width` 32,
  with a dummy codec (`codec_bmc`, `linux,snd-soc-dummy`) as **bit clock and frame master**: the
  BMC side clocks the link.
- SAI1's pin group muxes four pads: RX bit clock, RX frame sync, RX data 0 and TX data 0. The
  MCLK pad is commented out. So: **one data line each way**, carrying 16 slots of 32 bits.
  `fsl,dataline` enables all eight lanes in the controller, but only lane 0 has a pad.
- `fsl,sai-synchronous-rx`: receive runs synchronous to transmit.
- The running unit's device tree matches the source on all of this (measured, from the survey's
  device-tree dump).

## Measured with Roland's app stopped

- **The link runs and clocks without Roland's app.** `aplay -D hw:1,0` played a 6-channel S32_LE
  48 kHz file to its end, and the link's DMA interrupts kept their rate throughout.
- **Six playback channels are three stereo pairs.** A tone on each channel in turn, heard on
  PHONES: channels 0, 2 and 4 in the left ear and 1, 3 and 5 in the right, so 0/1, 2/3 and 4/5
  are stereo pairs, even left and odd right.
- **All three pairs reach PHONES by default,** with nothing sent to the BMC side (no routing or
  level message). A quiet sine (about -30 dBFS) on 2/3, then 4/5, then 0/1 was heard each time.
- **Nothing reaches SUB OUT by default.** The same tones, about 12 dB louder, were silent on SUB
  OUT. Roland's own sound did not come out of SUB OUT either.
- **Oscairn's engine ran on it** at 48 kHz with 128-frame blocks: `oscairn-engine
  --output-device hw:1,0 --device-channels 6 --sample-rate 48000 --audio-outputs 0,1
  --buffer-frames 128` opened the device, and notes sent to it were heard. Its deadline-miss and
  underrun counters stayed at 0 in that first run; later runs at 128 frames had two deadline
  misses and no underruns. Load figures are in
  [the kernel and timing note](fantom-kernel-and-timing-measurements.md).

## Static, for comparison

- Roland's app opens six channels each way, S32_LE, 48 kHz, plays its sample players on channels
  2 to 5 and leaves 0 and 1 silent, and records from its first two input channels (static, from
  Oscairn's reading of `mi078`). Inferred: slots 0 to 5, since NXP's SAI driver enables the first
  *n* slots for *n* channels.
- Roland's `thru.sh` opens all 16 channels both ways (static).

## Not measured

- MAIN OUT (no cable was connected), the pairs' levels against each other, capture, and opening
  all 16 channels.
- Whether the link clocks and passes audio if Roland's app has **never** run since power-on. In
  every test the app had run and then been stopped.
- Which BMC drives the link, whether both BMCs' outputs share it, and where on the BMC side the
  six channels enter the mix (whether they pass through any effect).
