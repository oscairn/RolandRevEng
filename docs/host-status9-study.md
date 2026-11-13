# The measured kind-9 status frames: mi078's selector-9 consumer

2026-11-13. Static cross-check of the 2026-11-12 unit measurements against the
host-side code, answering one open question in
[bmc-addressing-and-loader-open-questions.md](bmc-addressing-and-loader-open-questions.md):
what the unexplained long kind-9 status frames from 0xE1 are. The captures
showed them (measured: about ten a second, 112-byte payload, sub-type 9) with
their contents undecoded. Pinned artifact: `local/mi078`, SHA-256
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`
(61,181,491 bytes). No device access, no execution.

**Result: the app's input worker consumes every kind-9 frame whose service
selector (byte 3) is 9 by storing its 112-byte payload into a gated two-slot
ring at `0x40a9760`, without checking the source byte.** The selector-9
service was the one kind-9 row missing from
[host-core1-bridge-followup.md](host-core1-bridge-followup.md)'s service table.
What the payload fields mean, and what the gated readers do with them, remain
open; the captures bound which bytes ever vary.

## Capture side (measured, reproduced offline)

Re-framing the four saved app-stopped `.bin` captures with
`tools/bmc_ipc.py`'s framing (`tools/host_status9_study.py --captures`) gives:

| Capture | Frames | Kind-9 frames | (byte 1, destination, selector) | Payload lengths |
|---|---:|---:|---|---|
| `gs0-keys-app-stopped.bin` | 425 | 181 | (0xE1, 0x60, 9) | 112 |
| `gs0-local-off.bin` | 480 | 180 | (0xE1, 0x60, 9) | 112 |
| `gs0-local-sent.bin` | 302 | 220 | (0xE1, 0x60, 9) | 112 |
| `gs0-panel-app-stopped.bin` | 160 | 160 | (0xE1, 0x60, 9) | 112 |

741 frames total, every one from 0xE1 to 0x60 with selector 9 and a 112-byte
payload. This matches the measured long kind-9 frames exactly; the four
strace `.raw` logs carry no kind-9 frames on their write side (the app writes
only kinds 3, 6, 7, 8 there).

Payload bytes that vary within each capture (offsets 0-based in the 112-byte
payload, from the same command):

| Capture | Varying offsets |
|---|---|
| `gs0-keys-app-stopped.bin` | 4, 6, 64, 66, 68, 70, 92, 94, 108, 109, 110, 111 |
| `gs0-local-off.bin` | 64, 66, 92, 94, 108, 110 |
| `gs0-local-sent.bin` | none |
| `gs0-panel-app-stopped.bin` | none |

The keys capture varies most (keys held change bytes 4/6 and the pairs around
64..70); the captures without key activity vary least or not at all. The
measured note's varying "header bytes 8 to 11" are the frame prefix metadata
bytes 8..11 (`4c 18` and `d4 0b` in these captures), a different field.

## Static side (verified)

The input worker `00be1a50` (arrival path from the read loop through
`00be12b0` and `00be3800` is the existing
[host transport](host-transport-study.md) evidence) dispatches kind 9 on byte
3 at `0xbe1ae4` (`ldrb w0, [sp, #0x73]`). The selector-9 branch:

```text
0xbe1b18  cmp w0, #9                  ; selector 9
0xbe1b20  add x0, sp, #0x70            ; message
0xbe1b24  bl  00be3688                 ; payload pointer/count getter
0xbe1b2c  adrp x0, #0x40a9000
0xbe1b30  add  x0, x0, #0x858          ; ring object 0x40a9858
0xbe1b34  bl  006c3070                 ; ring store
```

`0x6c3070` is the only direct caller of the payload getter on this path and the
only caller of the ring store (`tools/host_status9_study.py` verifies both
census facts). The store body:

- toggles the cursor at `0x40a975c`: `w3 = 1 - old` (`0x6c308c/90`), so the
  cursor alternates between 0 and 1 and names the most recently written slot;
- copies exactly 112 bytes: seven `ldp`/`stp` pairs of 16 bytes from the payload
  into `0x40a9760 + 112 * new_cursor` — two slots, `0x40a9760` and
  `0x40a97d0`;
- the gate byte at `0x40a9758` gates the readers, not the store.

The gate is written by `0x6c27d8` (`strb #1`, enable) and `0x6c27e8`
(`strb wzr`, disable); the census finds 11 direct enable and 15 direct disable
callers across the application (for example `0x72cd70` and `0x730c38`, each
passing the ring object `0x40a9858`). Reader families:

- `0x6c27fc` gates on `0x40a9758` itself (`0x6c2804`), returns `-60` with the
  gate clear, and reads slot halfwords at `8 + 4*arg` with a caller-supplied
  pair index.
- `0x6c2a50` gates on a separate byte at `0x40a9840` (`0x6c2a58/74`), also
  returns `-60` when clear, reads the same cursor at `0x40a975c` and a slot
  halfword at `+0x54` (`0x6c2a8c`).

Two facts worth recording exactly:

- **The consumer never checks source byte 1.** Between `0xbe1b20` and the
  store, nothing loads the message's byte 1, and `0x6c3070` reads only the
  payload pointer and the hard-coded ring base. The captured frames all say
  0xE1, but the app would file a selector-9 frame from any source the same way.
- The consumer does not check the 112-byte length either; the store copies a
  fixed 112 bytes and the getter's count is not consulted on this path.

## What is established, what is not

- **Verified:** the capture census above (command: `tools/host_status9_study.py
  <mi078> --captures <dir>`; counts and shapes checked by
  `tests/test_host_status9_study.py`).
- **Verified:** the dispatch anchors, the 112-byte copy width, the cursor
  toggle, the gate bytes and the reader gate/return-value instructions, all
  from the pinned image with exact instruction comparisons.
- **Inferred:** the ring is a status/meter store: its readers are gated,
  called from at least 25 sites around the application, and the two captured
  reader shapes touch slot offsets `8 + 4*arg` and `0x54`; the captures show
  activity-dependent variation at offsets 4, 6, 64..70, 92..94 and 108..111.
  Which reader consumes which varying field is not established (27 references
  to the gate base were not all traced).
- **Unknown:** the meaning of any payload field; what writes the second gate
  byte `0x40a9840`; what the ring object `0x40a9858` is (RTTI not recovered);
  whether the BMC side generates these frames unprompted (measured: they keep
  coming with nothing sent, including with the app stopped, so the producer is
  on the BMC side of the link).

## Reproduce

```sh
shasum -a 256 local/mi078
python tools/host_status9_study.py local/mi078 \
  --captures local/fantom-unit-2026-11-12/link-and-panel-captures
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests \
  -p test_host_status9_study.py -v
```

The tool needs Python 3.13+, Capstone 5 and pyelftools (pinned in
requirements.txt). It reads only the pinned ELF and the saved capture files and
prints JSON to stdout. Without `--captures` it prints the static report only.