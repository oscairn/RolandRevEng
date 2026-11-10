# CORE1 wait completion and initial-data recovery

2026-11-10. Offline static follow-up to the [effect lifecycle study](effect-lifecycle-and-parent-entry-study.md).
Input: header-stripped bmc0 CORE1 payload, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Addresses are CORE1 runtime addresses. Python/Capstone file analysis and bounded
initial-data expansion are not execution of the firmware or hardware observations.

## Completion is a shared timer flag

`011271b8` preserves input r1 as an unsigned remaining count and r2 as a completion
argument. It uses bytes at `200845b4` (done) and `200845b5` (callback registered).
On first use it sets the registered byte, calls `01103762(12)` and registers
Thumb callback `011271ad` through `0110376c`. The latter stores the pointer at
`20084c38`. The numeric `12` here is hexadecimal; `01103762` shifts it left three
and writes byte `90` at `e000e45b`.

The vector-table word at `011001ac` is `01103471`, the IRQ91 slot under the
Cortex-M vector layout. Handler `01103470` clears bit 0 at `40059000`, loads
the callback from `20084c38`, calls it when nonzero, increments the counter at
`20084c78`, and executes DSB before returning. Callback `011271ac` writes 1 to
the done byte. This connects the wait flag to an actual compiled interrupt path;
it does not measure interrupt latency or establish a peripheral clock frequency.

The wait routine's exact sequence is:

1. Wait for any previous operation's done byte. This initial wait uses WFI and
   reloads the flag. It happens even when the new count is zero.
2. For nonzero remaining count, choose `min(remaining,fffe)`, subtract it, clear
   the done byte and call timer driver `01103772` with that chunk.
3. Poll the done byte when either remaining count or the completion argument is
   nonzero. These subsequent waits busy-poll; they do not use WFI.
4. Repeat until remaining is zero. Completion 0 skips polling the final chunk.

| Count | Completion | New arms | Waits after those arms |
|---:|---:|---|---|
| 0 | either | none | none, but previous completion is still drained |
| 1 | 0 | `1` | final wait omitted |
| `ffff` | 0 | `fffe`, `1` | first required, final omitted |
| `ffff` | 1 | `fffe`, `1` | both required |

Omitting the final wait does not guarantee that the interrupt has not already
completed by return. It means this call does not require that final observation.
Another count-zero call can wait for the pending operation, assuming no competing
caller or callback replacement. There is no mutex, interrupt masking or timeout
in these traced wait/driver/callback bodies. Coordination elsewhere remains open.
This API is not proof of a DSP program, envelope, DMA or audio-graph fence.

## Driver arithmetic and scale conversion

Driver `01103772` first clears bit 0 at `40059000` while it remains set, then
executes DMB. It clamps its argument to `fffe`, reads a u32 at `4005900c`, and
stores `counter + clamped_argument + 1` to `40059020`, with ordinary 32-bit wrap.
It sets bit 0 at `40059000` afterward. The code does not truncate the stored sum
to 16 bits. The peripheral comparison width and reason for the `+1` remain unknown.
Counter reads, stores and the interrupt path alone cannot establish elapsed time.

Neighbor `0112721a` first computes the low 32 bits of `r1 * 48000`, interprets that
product as signed for SDIV by 1000, and truncates the quotient toward zero. It then
uses the same unsigned chunking logic. This supports a milliseconds-to-48-kHz-domain
interpretation for ordinary small positive arguments, not a hardware calibration.
It is not unlimited mathematical multiplication: argument 44739 yields 2147472;
44740 wraps the signed product and yields register bits representing `-2147447`.
Those bits are a large unsigned count in the chunk loop. No new live-call recipe
or general timer service is supplied.

## The first call starts with done = 1

The initial flag is recovered from the actual scatter record rather than assumed.
The record at `6123fc98` expands source `0113afc4` into destination `2008008c`,
length `478c`, using handler `6100003c`. The handler's token rules are:

- Low three bits give literal count plus one; zero selects a following count byte.
- High nibble gives run count; zero selects a following count byte after the
  literal-count extension, before any literal bytes.
- It copies literal count minus one bytes.
- If token bit 3 is clear, it emits run-count zero bytes.
- Otherwise it consumes a one-byte backward distance and copies run-count plus
  two bytes sequentially, allowing source/destination overlap.

The bounded offline expansion consumes `1f43` bytes (one byte before the next
aligned source boundary) and produces exactly `478c` bytes. Output SHA-256 is
`9a35747f56872b1f2f81bd375c17a57fd2f17a4b00b4ed6cdcd460f2b067bca8`.
At output offset `4528`, corresponding to `200845b4`, the first two bytes are
**01 00**: done starts true and callback registration starts false.
This closes the initial-flag question for this supplied build after normal scatter
completion; it is not a snapshot after application startup or later runtime writes.
The reader rejects malformed counts, truncated input, out-of-output backward
references and declared-size overflow. It neither patches nor repackages firmware.

## Reproduce and review

```sh
python3 tools/core1_wait_study.py local/b0c1a.bin
python3 -m unittest discover -s tests -p test_core1_wait_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x11271ac --size 0xde
python3 tools/core1.py local/b0c1a.bin --address 0x1103470 --size 0x24
python3 tools/core1.py local/b0c1a.bin --address 0x1103762 --size 0x4c
python3 tools/core1.py local/b0c1a.bin --address 0x6100003c --size 0x5a
```

Use the existing Capstone-capable interpreter for corpus checks. Five tests cover
chunk boundaries and final polling, register wrap and signed scaling, authored
compressed tokens including overlapping copies, malformed input, and the complete
pinned initial-data output digest/flags/vector. Four run without vendor inputs.

An independent worker reproduced the expansion and register/control-flow results.
A bounded no-tool Qwen draft correctly summarized chunking and final polling;
its rationale for `+1`, undefined-overflow claim, invented MULS errata distinction
and description of the callback as one-shot initialization were rejected. The
callback is in the supplied listing, and low-product bits/wrap are deterministic.
No generated Qwen code was accepted.
