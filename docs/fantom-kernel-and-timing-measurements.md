# Fantom-07 kernel and timing measurements

2026-11-12. What the i.MX side of the owner's FANTOM-07 offers a real-time audio engine, read and
measured on the unit over SSH. Each claim is marked **measured** (seen on the unit), **GPL
source** or **inferred**. These matter for the BMC research as the baseline any accelerator
would have to beat.

> **Not pure stock firmware.** One BMC ran a modified diagnostic CORE1 build during these
> measurements (see [the CORE1 diagnostics note](fantom-core0-key-recovery.md)). The i.MX-side
> figures below should not depend on it.

## Kernel

- **Linux 4.19.35, `CONFIG_PREEMPT`** (not PREEMPT_RT), aarch64, 250 Hz, high-resolution timers
  (measured: `uname`, `/proc/config.gz`).
- cgroups v1 with cpusets; no RT group scheduling; RT throttling at the default 950 ms of every
  second; no `isolcpus`; no PSI (measured).
- **Real-time priorities are granted** to root processes (measured: the engine and `cyclictest`
  ran at real-time priority).
- **Every device interrupt lands on core 0** (measured, `/proc/interrupts`): the I2C buses, both
  USB controllers, the eMMC, SDMA (inferred to carry the audio link's DMA) and the UARTs count on
  CPU0 only; only the timers are spread.
- **Memory:** the kernel sees 992 MiB (1,015,808 KiB at boot), of which a 320 MiB CMA pool serves
  the GPU and display; `free -m` reports 952 MB, with a 256 MB swap file (measured).
- Four Cortex-A53 cores at 1.2, 1.6 or 1.8 GHz; the stock governor is `ondemand` (measured).

## Scheduling latency

`cyclictest` at priority 80, 2,667 µs interval (one 128-frame block at 48 kHz), 30 seconds, with
Oscairn's engine stopped and the `performance` governor (measured, reported by the session that
ran it; the raw output is not among the files filed with this note):

| Core | Max latency | Average |
|---|---|---|
| 0 | 48 µs | 6 µs |
| 1 | 38 µs | 6 µs |

Core 0 is worse, as expected with every device interrupt on it (inferred).

## Engine load

Oscairn's engine on `hw:1,0` at 48 kHz, its default session (sequencer, synth and delay in their
workers), `cpuLoad` from its status at rest and holding an eight-note chord on the built-in synth
(measured, from Oscairn's `fantom-0.md`):

| Governor | Buffer | At rest | 8 notes | Deadline misses | Underruns | Synth worker block, last / most (µs) |
|---|---|---|---|---|---|---|
| `ondemand` (1.6 GHz) | 128 | 0.23 | about 0.34 | 2 | 0 | 406 / 3,151 |
| `performance` (1.8 GHz) | 128 | 0.20 | about 0.25 | 2 | 0 | 160 / 5,814 |
| `performance` | 256 | 0.13 | about 0.21 | 0 | 0 | 733 / 822 |
| `ondemand` | 256 | 0.17 | about 0.29 | 0 | 0 | 1,076 / 2,118 |

No click was heard in any run. Most of the load is a fixed cost per block, present with nothing
playing; the misses come from the worst worker block, 3 to 6 ms against a 2.67 ms block at 128
frames (inferred from the table). About 416 MB of memory was still available with the engine
running.

No voice-count ramp measured on the unit was found in the sources for this note; polyphony on the
i.MX remains to be measured.
