# Linux application transport: BMC IPC uses ttyGS0

2026-11-10. Read-only static analysis of the existing local ARM64 `mi078` application
and `qctest` diagnostic executable. No target code was executed, device opened,
message sent, boot script changed or update applied.

| Local artifact | SHA-256 | Bytes |
|---|---|---:|
| `local/mi078` | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` | 61181491 |
| `local/qctest` | `d87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6` | 304912 |

The artifacts were preserved from the prior local extraction under
`/private/tmp/fantom-entry-research`; they have not been freshly compared against a new
official download. Vendor binaries and native disassembly remain ignored/local.
This study connects the Linux-side application path to the
[CORE1 loader investigation](BMC%20DSP%20packet%20and%20loader%20map.md), but the peer-side
bridge into the recovered CORE1 ingress ring is still missing.

## Main correction

The earlier vault claim that `/dev/ttyGS0` is spare during normal application operation
is contradicted by a concrete `mi078` startup and dataflow path. The application opens
that device and connects it to classes identified by RTTI as `CBmcIpcIn` and
`CBmcIpcOut`. UART4's diagnostic test is a separate byte-echo test. Neither the UART
label nor USB connector assumptions should override the actual file-descriptor path.

This establishes the application code's intended BMC IPC transport. Static analysis
does not establish which physical connector/USB peer owns the other end, whether every
production boot follows this startup path, or how the other processor forwards these
messages to CORE1. Those points require peer code or runtime evidence.

## ttyGS0 file-descriptor provenance

The following addresses are ELF virtual addresses in this exact `mi078` build:

| Site | Concrete observation |
|---|---|
| `00bdf850` | Loads string pointer `01313f50`, whose contents are `/dev/ttyGS0`, and calls `open` at `00bdf878` with flags `0x102` |
| `00bdf898` | Supplies numeric speed `0x7a12` (31250) to `cfsetspeed`; this is USB serial configuration, not proof of a physical UART baud |
| `00bdf938` | Calls `00bdf850` twice and stores the descriptors at object+0 and object+4 |
| `00bdf230` | Uses global object `04106bb8`, invokes `00bdf938`, polls its input descriptor, and reads up to `0x100` bytes through `00bdf968` |
| `00bdf988` | Loads descriptor at object+4 and calls `write` at `00bdf998` |
| `00be24e8` | Passes the same global object `04106bb8` to `00bdf988` |

Consequently the read descriptor is stored at `0x04106bb8`, the write descriptor at
`0x04106bbc`; both come from the exact device-path opener. This conclusion does not
depend on assuming that a generic `read` or `write` import belongs to BMC traffic.

The application startup sequence at `0x00c081d0/00c081d4/00c081d8` calls the thread
setup `00bdf670`, the input setup `00be1440`, and the output setup `00be26e0` in order.
The thread setup passes entry `00bdf210` to `pthread_create`; that entry invokes its
object's first virtual method, selecting the concrete read loop `00bdf230` for the
constructed object. Thus this is not merely an unused device string or orphan method.
The static initializer at `0x00437540` stores vtable address point `01313f28` into
`04106870 + 0x178 = 041069e8`; the first entry at `01313f28` is `00bdf230`.
This closes the virtual dispatch edge from the thread entry to that concrete read loop.

## Callback and virtual-table links

Input:

1. RTTI name `9CBmcIpcIn` at `01314010` → typeinfo `01314020` → vtable group
   `013140e8`, address point `013140f8`. Its worker method is `00be1a50`.
2. Input construction at `00be1330` installs the nested byte-parser vtable address
   point `01314118` at object+`0x158`. Its first callback is `00be12b0`.
3. Setup `00be1440` registers callback `00be1290` through `00bdf620`, into
   thread object `041069e8` at offset `0xb8`.
4. The read loop invokes exactly that callback at `00bdf2ac`, preserving its byte
   buffer and count arguments. `00be1290` passes them to parser `00be0dd0` on the
   global input object's nested parser.
5. Completed parser messages invoke callback `00be12b0`, which queues the message
   through `00be3800` and wakes the input worker. `00be1a50` handles those messages.

Output:

1. RTTI name `10CBmcIpcOut` at `01314188` → typeinfo `01314198` → vtable group
   `013141d0`, address point `013141e0`. Its worker method is `00be2448`.
2. Constructor `00be25f8` installs its transmit-buffer vtable `01314200` at
   object+`0x158`, and callback `00be24e8` at object+`0x1c0` (buffer+`0x68`).
3. The output worker passes queued messages to serializer `00be1120`. Its virtual
   byte-output method at vtable+`0x10` resolves to `00be2510`, which batches bytes
   in a `0x1000`-byte buffer and invokes the stored callback when flushed.
4. That callback is `00be24e8` → `00bdf988` → `write` on the proven ttyGS0 output fd.

The route function `00be4270` writes its route argument to message byte 2. Several
destination cases, including the high-nibble `0xe0` class, enter the concrete BMC IPC
output object at `041145e0`. For example, `00c2a3c0` constructs a kind-3 message,
sets byte 1 to `0x60`, and routes it with argument `0xe1`. Meanings of every route ID
and chip selection remain unresolved.

## Recovered byte-stream framing

Serializer `00be1120` and parser `00be0dd0` independently agree on the outer frame
boundaries. Reads need not correspond one-for-one to messages: the parser accumulates
partial prefixes and payloads and can process multiple messages from one read.

```text
kind     = byte[0] >> 1
variable = byte[0] & 1

variable == 0:
    total length       = 12 bytes
    inline payload     = bytes[4 : 4 + n]
    n                  = byte[11] (setter caps inline data to 7 bytes)

variable == 1:
    fixed wire prefix  = 12 bytes
    payload length N   = little-endian u32 at bytes[12:16]
    payload            = bytes[16 : 16 + N]
    total length       = 16 + N bytes
```

The serializer explicitly emits variable messages as object bytes 0–7, object bytes
16–19, a four-byte length, then the referenced payload. An in-memory pointer in object
bytes 8–15 is **not** transmitted. Copying an entire native message object would be
incorrect. Unused inline bytes and the opaque prefix fields are not assigned meanings.

The parser rejects kinds above 9 in its observed path. The stream framing has no
observed delimiter, magic or checksum in these routines; other layers may add checks.
The four-byte variable length is copied/loaded without byte reversal in this
little-endian ARM64 ELF. This is independent of the render DSP's reversed storage words.

Kind 3 has a useful narrow interpretation: constructor `00be2a60` calls the inline
payload setter `00be3450` with kind 3 and length 4; getter `00be2ac0` copies those four
bytes back. Native callers construct familiar four-byte MIDI/UMDW-style words, such as
the control-change form at `00c2a3c0`. The received kind-3 worker path also obtains that
four-byte value via the getter. For a recorded payload, its numerical word is
`int.from_bytes(payload, 'little')`; no swap is performed by those helpers.

The CORE1 callback receives a four-byte word with a low-byte routing/CIN-like field,
command in byte 1 and argument in bytes 2–3. That structure is compatible with the
application's embedded four-byte values. **The intervening peer-side handler has not
been recovered**, so byte-for-byte forwarding from a selected outer frame into the
CORE1 ring is still an inference. In particular, kind-3 MIDI messages are not proof of
an arbitrary memory/program upload command.

`tools/bmc_ipc.py` inspects only existing capture files using this bounded layout. It
rejects truncated and unsupported forms without resynchronization, reports opaque
prefix bytes, and decodes a little-endian word for four-byte kind-3 payloads. It neither
constructs commands nor opens any live endpoint. Its three tests use original synthetic
frames, not captured/vendor traffic. No real traffic capture was available for a
runtime comparison.

## UART4 diagnostic is an echo test

In `qctest`, function `0041597c` opens `/dev/ttymxc3` (string `004319d0`) with flags
`0x902`, asks `cfsetspeed` for numeric 1000000, and sends the ten bytes `0123456789`
from `004319c0` individually. For each byte it attempts a one-byte write, attempts a
one-byte read, and compares the returned byte with the sent byte. It restores saved
terminal settings and closes the fd. The retry counters start at 300; no wall-clock
timeout is inferred from those instruction counts.

This establishes a diagnostic byte-echo test under the “BMC SOM UART” label, not the
normal application's command protocol or a parser for CORE1 words. The `mi078`
artifact has no literal `/dev/ttymxc3` path in the searched sections. That bounded
negative result does not exclude computed paths, libraries or other processes.

## Existing shell payload conflict

Read-only inspection found both local modified `_DATA_FNTM0` archives contain
`_DATA/go.sh` line 33 starting a background interactive shell with stdin/stdout/stderr
on `/dev/ttyGS0` before the application's launch. The `fantom-07-update-shell` package
also has a similar loop at `update_fntm0` line 9. These payloads were **not edited**.

Given the concrete application IPC path, a concurrently running shell can consume IPC
input and inject shell text into the same stream. The earlier “spare gadget” rationale
does not justify this design. Whether a recovery-only stage uses the same peer or runs
the application concurrently remains separately unresolved; the normal-application
background-shell case is the concrete collision identified here.

## Reproduce without target execution

The installed `/usr/bin/objdump` supports the ARM64 ELF inputs:

```sh
shasum -a 256 local/mi078 local/qctest
/usr/bin/objdump -d --start-address=0xbdf850 --stop-address=0xbdf9a4 local/mi078
/usr/bin/objdump -d --start-address=0xbdf230 --stop-address=0xbdf2b4 local/mi078
/usr/bin/objdump -d --start-address=0xbe25f8 --stop-address=0xbe266c local/mi078
/usr/bin/objdump -d --start-address=0xbe1120 --stop-address=0xbe11c4 local/mi078
/usr/bin/objdump -d --start-address=0xbe0dd0 --stop-address=0xbe111c local/mi078
/usr/bin/objdump -d --start-address=0xc081c8 --stop-address=0xc081ec local/mi078
/usr/bin/objdump -d --start-address=0x41597c --stop-address=0x415bb4 local/qctest
python3 -m unittest discover -s tests -p test_bmc_ipc.py -v
# If an owned capture has subsequently been recorded:
python3 tools/bmc_ipc.py path/to/capture.bin
```

No arbitrary DSP upload operation, live USB topology, complete route-ID map, peer-side
forwarding implementation or hardware recovery has been established. The practical
next bridge target is the peer of this IPC stream, rather than sending the UART echo
pattern or bare CORE1 callback command numbers to an instrument.

The [host/CORE1 bridge follow-up](host-core1-bridge-followup.md) maps the outer route
dispatcher, service clients and payload ownership, and recovers a CORE-local SysEx
MMIO handler. It retains the missing peer boundary and identifies a read-reply
stack-size discrepancy; it does not establish a usable host loader.
