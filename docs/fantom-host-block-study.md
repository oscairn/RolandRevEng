# Fantom Linux block construction and serialization

The [scalar-edit follow-up](fantom-host-write-study.md) now begins at original family6/7 edit wrappers and reaches these serialized messages; local receiver and BMC queue consumers remain outside the replay.

Follow-up: [registered host MFX family callbacks](fantom-host-family-study.md) now bind 74 corresponding host/CORE1 descriptor tuples and execute getters, routing and paired block/range notifications. The queue and missing-peer boundaries remain explicit.

2026-11-11. The readable Linux application now has a bounded, executable check of
its kind-7 block constructor and serializer. **108 authored cases match the
independent byte layout**, including copied input lifetime and the inline/variable
boundary. The offline capture decoder exposes the four metadata bytes separately
from block data. This does not connect the host envelope to
[CORE1 selector84 reception](fantom-parameter-stream-study.md).

The input is the existing v1.08 `mi078` ELF, SHA-256
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`.
`tools/fantom_host_block_study.py` rejects other images before parsing/execution.
Evidence is file/Capstone analysis and isolated Unicorn CPU execution, not REA
Evidence records, live Linux operation or device traffic. Raw binaries and
listings remain ignored/local.

## Original constructor and wire layout

Addresses are hexadecimal; sizes below are decimal unless prefixed with `0x`.
The AArch64 function at `00be3e38` takes:

| Register | Checked use |
|---|---|
| x0 | Native message output object |
| w1 | Selector, retained low 8 bits at native byte3 |
| w2 | First metadata field, retained low 16 bits |
| w3 | Metadata byte2, retained low 8 bits |
| w4 | Metadata byte3, retained low 8 bits |
| x5 | Caller data pointer |
| w6 | Data byte count |

The message kind is 7. For **0–3 data bytes**, its four metadata bytes and data
share the seven-byte inline payload. For **4 or more data bytes**, the metadata is
at native object+16 and data is forced into allocated storage. Its allocation is
N+8 bytes: a reference count, a length, then the copied data. Source argument
truncation is observed; the replay's Python boundary requires explicit unsigned32
scalar arguments and at most `0x660` authored data bytes. That replay bound is not
a discovered firmware maximum.

Serializer `00be1120` invokes a byte-output virtual method with these spans:

| Form | Output calls | Wire bytes |
|---|---|---|
| Inline | Native object[0:12] | 12 total; payload length at byte11 is 4+N; metadata at bytes4–7 and data at byte8 |
| Variable | Native object[0:8], object[16:20], u32 N, allocated data | 16+N total; metadata at bytes8–11, length at bytes12–15, data at byte16 |

The variable object's eight-byte pointer is omitted. The final four prefix bytes
are metadata, not a pointer or payload length. Existing `frames()` output retains
its original `payload` field: inline payload includes metadata; variable payload
contains data alone. Kind-7 frames additionally expose:

```text
block.u16    first two metadata bytes, little endian
block.byte2  third metadata byte
block.byte3  fourth metadata byte
block.data   only the block data, hexadecimal
```

These neutral names avoid assigning a universal meaning across all callers.
Inline kind-7 records shorter than four metadata bytes are rejected by the offline
decoder. This is structural validation of saved records, not a reproduction of
all malformed-input behavior in the stock firmware. No encoder or device sender
is added to the capture tool.

## Padding and local ownership

The base initializer at `00be3120` writes zero to native bytes0–3 and byte11.
It does not clear the whole 24-byte object. Canary values 00, 5a and ff show:

- Inline unused bytes after metadata/data and before byte11 retain seeded memory.
- Variable native bytes4–7 retain seeded memory and are serialized in the first span.
- The block payload survives overwriting its caller's source storage after the
  constructor returns, for both storage forms.

Consequently padding is opaque and cannot be assumed zero when comparing saved
messages. These results demonstrate bounded local copy behavior and visible
padding writes/omissions. They do not establish live process memory contents or a
live information disclosure. Queue retention, allocation failure, reference-count
concurrency, POSIX partial writes and peer acknowledgement were not executed.

## Generic host caller and the remaining translation gap

An aligned direct B/BL scan of the complete ELF `.text` finds **37 direct sites**
calling this constructor. The source checker pins that set. Indirect callers and
semantic classification of every site remain outside this scan.

Two generic helpers are `00c01ec0` and `00c02010`. Their source reads a descriptor
pointer from `013844c8` (file value `0138b3d0`). Descriptors have 16-byte stride;
start/end byte offsets come from halfwords at descriptor+12, with the final field
size from the low nibble at descriptor+14. They supply data starting at the first
offset and length `last_offset - first_offset + last_size`, passing the first
offset through the constructor's **8-bit** w4 metadata field. This is a
source observation, not an execution of the generic getter or a validation of
arbitrary descriptor ranges.

After sending the block to route `ef`, these helpers construct a separate packed
range notification at `00be3f30`, wrap it via `00be2bf8`, and route it too. The
wrapper uses kind8 and the seven-byte-capped inline setter. The original earlier
observation that kind8 requests eight input bytes does not imply eight transmitted
payload bytes. This paired notification has not been replayed here.

These host descriptors, kind numbers, widths and notification packing must not be
silently substituted for CORE1's header `84 part 00` and generic-ID-relative block
prefix. The receive study starts with internal high-nibble-3 assignment words;
this study ends with outer host envelopes. A matching selector or authored test
value does not prove forwarding between them. In particular, the replay includes
synthetic selector arguments with high bits to test truncation; they are not
observed stock selector84 requests.

The missing peer still needs to resolve endpoints, convert the structured fields
and notifications into CORE1 records, fragment them and perform the reverse
reply route. No complete bridge, ttyGS0 command, CORE0 decryption or custom-engine
loading method follows from this checkpoint.

## Verification and next work

The 108 cases span N=0,1,2,3,4,5,7,8,9,`0x54`,`0x410`,`0x660`, three scalar-field
patterns and three canaries. They execute the original constructor, metadata
setter, payload setter, getters and serializer. Memory allocation, memcpy,
reference-count helper and output callback are intercepted in private emulated
memory. ELF imports independently bind the intercepted allocation/copy addresses.
The capture decoder is cross-checked against each original serialized result.

```sh
python3.13 tools/fantom_host_block_study.py local/mi078
python3.13 tools/fantom_host_block_study.py local/mi078 --execute-arm64
PYTHONPATH=tools:tests python3.13 -m unittest test_fantom_host_block_study test_bmc_ipc test_core1_sysex -v
```

Qwen returned a no-tool review in 16.6 seconds. Its copy-lifetime observation was
corroborated. Incorrect seven-byte block-data boundary, metadata placements,
register/stack claims and wire-size arithmetic were rejected. No Qwen code or
unsupported protocol claim was accepted.

Next trace a specific host parameter family's descriptor/getter/notification
pair and seek corresponding readable comparison-firmware peer code or saved
traffic. Keep the absent CORE0 transformation explicit. No DSP opcode profile is
added: 18 exact execution profiles remain; silicon calibration, live scheduling,
entry/return and safe loading still require separate evidence.
