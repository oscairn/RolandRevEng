# Host byte 1 on the ttyGS0 wire: caller data, not a send-path rewrite

2026-11-13. Static cross-check of the 2026-11-12 unit measurements against the
host-side code, answering the open question in
[bmc-addressing-and-loader-open-questions.md](bmc-addressing-and-loader-open-questions.md):
why Roland's app writes every frame with source byte (byte 1) `0x00` on
`/dev/ttyGS0` while [host-transport-study.md](host-transport-study.md) recorded
constructors setting byte 1 to `0x60`. Pinned artifact:
`local/mi078`, SHA-256
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`
(61,181,491 bytes). No device access, no execution, no capture.

**Result: both observations are correct and compatible.** Message byte 1 is
call-site data. Of the 391 direct calls to the outer route dispatchers, 214
stamp an immediate into message byte 1 before routing, and 177 leave it at the
base-initializer default 0. The frames the unit measurements observed on the
wire (MIDI clock, panel forwards, lamp words, parameter blocks and companions)
come from call sites that leave byte 1 at 0; the stamping sites belong to other
services whose frames those captures did not exercise. Nothing in the send path
rewrites or clears byte 1.

## Method

`tools/host_byte1_study.py` disassembles the pinned `.text` with Capstone and,
for every direct call of the route dispatchers `00be4270` (explicit route
argument) and `00be4418` (existing message byte 2), walks back over the
straight-line block since the previous branch/call boundary and records:

- the route immediate (last `mov`/`movz w0, #imm`, `00be4270` only);
- whether the block stored an immediate into message byte 1, recognized as
  `strb wN, [xM, #1]` where `xM` is the message base register resolved from
  `add x1, xM, #off` / `mov x1, xM`, and the stored immediate.

`tests/test_host_byte1_study.py` checks the totals, the per-route stamp sets
and the exact instruction anchors of the cited sites against the pinned image.

Boundaries: the scanner models straight-line blocks only (up to 140 instructions
back to the previous `bl`/branch/return boundary); it does not follow flows into
helper routines, so a caller that sets byte 1 inside a helper and then routes is
counted as no-store here. The measured `strace` traces record `write` buffers,
not the native message objects; the wire prefix is recovered by re-framing those
buffers, which `tools/bmc_ipc.py` bounds exactly as documented.

## Wire observation (measured, reproduced offline)

Re-framing the saved `strace` write buffers from the unit session (files under
the ignored `local/fantom-unit-2026-11-12/link-and-panel-captures/`) with
`tools/bmc_ipc.py`'s framing shows byte 1 `0x00` in every written frame:

```text
rest.trace.raw      frames:  196  byte1 values: 0x0  kinds: 3, 6
slider.trace.raw    frames:  176  byte1 values: 0x0  kinds: 3, 6, 7, 8
local.trace.raw     frames: 1041  byte1 values: 0x0  kinds: 3, 6
local2.trace.raw    frames: 2505  byte1 values: 0x0  kinds: 3, 6, 7, 8
```

One example of each form written while the slider moved (prefix hex from the
trace, decoded by `bmc_ipc.py` semantics):

| Wire prefix | Kind | Byte 1 | Destination | Selector | Payload |
|---|---:|---|---|---|---|
| `06 00 e1 00` | 3 | 0x00 | 0xE1 | 0x00 | `0f f8 …` (MIDI clock) |
| `0c 00 e1 00` | 6 | 0x00 | 0xE1 | 0x00 | `84 09 00 vv` (slider word) |
| `0c 00 75 00` | 6 | 0x00 | 0x75 | 0x00 | `85 01 …` (lamp word) |
| `0e 00 ef 0e` | 7 | 0x00 | 0xEF | 0x0E | level parameter block |
| `10 00 ef 00` | 8 | 0x00 | 0xEF | 0x00 | companion frame |

Command: re-frame the four `.raw` traces (byte-exact counts above), and run
`tools/host_byte1_study.py local/mi078` for the static census below.

## Static census (verified)

`00be3120` is the message base initializer: `str wzr, [x0]` at `0xbe3120`
followed by `strb wzr, [x0, #0xb]` at `0xbe3124`. It zeroes bytes 0–3, so any
message constructed through the kind constructors begins with byte 1 = 0.
Constructors then set only byte 0 (kind) and byte 3 (sub-type argument);
`00be3450` sets byte 0 bits 1–7 and byte 11; `00be3e70` stores the kind-7
sub-type byte at offset 3. No kind constructor stores byte 1.

The census over all 391 direct route calls (full JSON in the ignored
`local/host-byte1-summary.json`):

| Destination route | Calls | Byte-1 immediate stamped | Stamps observed |
|---|---:|---:|---|
| 0xE1 (engine) | 123 | 99 | 0x60 (19), 0x62 (76), 0x63 (2), 0x64 (2) |
| 0xEF (settings) | 46 | 1 | 0x60 (1, at 0x8d58b0) |
| 0x61 (zones MIDI) | 56 | 45 | 0x60 (39), 0x62 (6) |
| 0x0E | 41 | 41 | 0x60 (41) |
| 0x08 | 41 | 15 | 0x60 (14), 0x62 (1) |
| 0x75 (lamps) | 11 | 0 | none |
| all others / existing byte 2 | 73 | 13 | 0x60/0x62/0x66/0x67 etc. |

The dominant forms the captures exercised:

- **Kind-7 parameter blocks and kind-8 companions to 0xEF:** 45 of 46 call sites
  leave byte 1 at the constructor default 0. The single stamp (0x60 at
  `0x8d58b0`) belongs to a different subsystem.
- **Kind-6 lamp words to 0x75:** all 11 call sites leave byte 1 at 0. The lamp
  path (`00be2b30` constructor around `0xcf3ae8`) stores the lamp word bytes at
  offsets 3–5 and never touches offset 1.
- **Kind-3 MIDI clock / panel forwards to 0xE1:** the forwarding path at
  `00c2c998`/`00c2c9a0` routes an already-built message with `00be4270` and
  stores nothing into byte 1 (`0xc2c9bc..c4`); the message's byte 1 is whatever
  its original constructor caller left, and the observed frames show 0.

The stamping sites are real but belong to other services. The clearest
example is the control-change constructor `00c2a3c0` cited by the earlier study:
`mov w2, #0x60` at `0xc2a400`, `strb w2, [sp, #0x29]` at `0xc2a408` (message
base `sp+0x28`, offset 1), then `mov w0, #0xe1` and `bl 00be4270` at
`0xc2a40c`. Its frames (status `0xb0|ch`, controller `0x2b`) did not appear in
the unit captures, which exercised transport MIDI (clock `0f f8`) and panel
words instead. The 76 sites stamping `0x62` to 0xE1 (e.g. `0xa573a8`,
`mov w2, #0x62; strb w2, [sp, #0x29]; mov w0, #0xe1; bl 00be4270`) are a
separate, unidentified subsystem.

Byte 1 therefore behaves like a source/endpoint field that each caller sets or
leaves zero, consistent with the reciprocal-use inference in
[host-core1-bridge-followup.md](host-core1-bridge-followup.md) (reply handlers
compare it to `0xe1`/`0xe2`). The wire evidence now bounds it further: on this
unit's traffic, the app's own transmitted frames carry 0, `0x6f` appears only in
the version client (`0xcf9a30..44`, which queues through `00be26a8` directly and
is not part of the `00be4270` census), and the 0x60/0x62 stamps are host-side
service data whose frames were not captured.

## What is established, what is not

- **Verified:** send path has no byte-1 rewrite. `00be1120` (serializer) emits
  object bytes 0–7 for variable messages and 12 inline bytes otherwise;
  `00be2510` (batcher) and `00be24e8`→`00bdf988` (`write` on the output fd,
  `00bdf994` loading `write`'s fd argument from `[x0, #4]`) copy/transmit bytes
  unchanged. The queued copy `00be31e8` copies all 24 native object bytes
  including byte 1. Nothing between queueing and `write` modifies byte 1.
- **Verified:** the census counts and stamp values above come from the pinned
  image and are checked by tests.
- **Verified:** all measured write-side frames had byte 1 = 0, by re-framing the
  saved strace buffers.
- **Inferred:** byte 1 is caller-selected source/endpoint data. The measured
  frames came from call sites that leave it 0; the stamping sites' frames were
  not in the captures.
- **Unknown:** which services the 0x62-to-0xE1 and 0x60-to-0x0E/0x61 stamps
  belong to, and what the CORE1 peer does with byte 1. The 0xEF/0x75/0xE1 wire
  frames are consistent with these sites simply never having been exercised;
  whether any stamping site's frames would appear under other UI actions is not
  checked. The peer's handling remains open (missing implementation,
  host-core1-bridge-followup.md section 4).

## Reproduce

```sh
shasum -a 256 local/mi078
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests \
  -p test_host_byte1_study.py -v
python tools/host_byte1_study.py local/mi078          # census summary JSON
python tools/host_byte1_study.py local/mi078 --sites  # every call site
```

The scanner needs Python 3.13+, Capstone 5 and pyelftools (pinned in
requirements.txt). It reads only the pinned file and prints to stdout; the
detailed JSON dump stays in ignored local storage.