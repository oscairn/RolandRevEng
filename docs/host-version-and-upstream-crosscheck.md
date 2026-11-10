# Host version identities and public research cross-check

2026-11-10. Offline static follow-up to [the bridge study](host-core1-bridge-followup.md).
Input is the same `local/mi078` ELF, SHA-256
`90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7`.
Addresses in this section are ELF virtual addresses. Apple's `objdump` and direct
ELF PT_LOAD-backed file reads establish these facts; no target was executed.

## Five version slots, not five chip identities

`00cf99c0(object, index)` constructs kind-9, selector-4 requests. Inspecting its
complete branches and the reply handler `00cf9c40` gives:

| Request index | Destination | Request payload byte | Reply slot / object offset | Expected string |
|---:|---:|---:|---|---|
| 0 | `e1` | `01` | 0 / `+00` | `1.08` |
| 1 | `e2` | `01` | 1 / `+05` | `1.08` |
| 2 | `e1` | `04` | 2 / `+0a` | `1.02` |
| 3 | `e2` | `04` | 3 / `+0f` | `1.08` |
| 4 | `e1` | `05` | 4 / `+14` | `1.03` |

All these requests set outer byte 1 to `6f`. In particular, the signed halfword
constants `-0x1e91` and `-0x1d91`, stored at the native message's `+1`, produce
bytes `6f e1` and `6f e2` in little-endian order. They are not payload words.
Reply selection uses **source byte 1**, not destination byte 2. Payload byte 0
selects the component; payload bytes 1–4 become four characters plus a NUL in
the five-byte slot. Component `05` selects slot 4 without checking source here.
The separate resolver `00cfa188` implements the same component/source mapping.
These are component values within service 4, not outer message kinds.

The five pointers at `01686750..01686770` resolve to strings at `01686778`,
`01686778`, `01686780`, `01686778`, `01686788`. Reading those addresses from the
file yields the expected strings above. `00cf9fe0` compares all five slots against
them. It first waits while object+`20` is positive, with at most 50 calls to
`usleep(100000)`, then refreshes a host version slot at `+19` through `00cf9eb0`.
The latter extracts the four-character version from `1.08.00.59` at `010e7438`.
A leading ASCII `0` in that host slot skips its comparison; otherwise it compares
against slot 0. This is version compatibility logic, not a serial/model/MAC table.
The alternate routine `00cfa0e0` uses a caller-supplied index times a 40-byte stride;
the extent of that alternate table is not established here.

Two direct calls to `00cf9fe0` were found in executable PT_LOAD bytes: `00715870`
and `00c3e54c`, both passing global object `0d55e620`. The former tests the result
and branches toward a UI status/error path; the latter discards it. This bounded
search does not cover indirect calls. Neither call supplies a physical BMC identity.

Both available CORE1 images identify themselves as `MI078_C1A VER.1.08 BLD.0059`,
with different commits (`947de6711` and `1413ee942`). Their equal versions cannot
identify which of the two `e1/e2` peers owns which image. The component numbers
`01/04/05` have not been equated to CORE0/CORE1 or content banks. A routing enum,
the peer implementation, or correlated traffic is still needed.

Reproduce the instruction evidence without running the executable:

```sh
/usr/bin/objdump -d --start-address=0xcf99c0 --stop-address=0xcf9d70 local/mi078
/usr/bin/objdump -d --start-address=0xcf9eb0 --stop-address=0xcfa1e4 local/mi078
python3 - <<'PY'
from pathlib import Path
import struct
b = Path('local/mi078').read_bytes()
assert b[:6] == b'\x7fELF\x02\x01'
start = struct.unpack_from('<Q', b, 32)[0]
stride, count = struct.unpack_from('<HH', b, 54)
loads = [struct.unpack_from('<II6Q', b, start+i*stride) for i in range(count)]
def read(va, n):
    for kind, flags, offset, base, physical, size, memory, alignment in loads:
        if kind == 1 and base <= va and va+n <= base+size:
            return b[offset+va-base:offset+va-base+n]
    raise ValueError('Not file-backed')
for i in range(5):
    pointer = int.from_bytes(read(0x1686750+8*i, 8), 'little')
    print(i, hex(pointer), read(pointer, 5).split(b'\0')[0].decode())
assert read(0x10e7438, 11) == b'1.08.00.59\0'
PY
```

Apple's `objdump -s` ignores the address limits used for disassembly in this
environment; the bounded file reads above avoid dumping unrelated sections.

## Public MC-101 work: useful comparison, missing Fantom peer unchanged

Read-only source checkouts are retained under ignored `local/upstream/`, pinned to:

- [edco/mc-101-re, b6607ade](https://github.com/edco/mc-101-re/tree/b6607ade1417e90afd7a0eab51aa371b21d2b3d4).
  Its `src/sysex_hook.s` and `tools/patch_reader_firmware.py` implement an MC-101
  CORE1 hook and reply packetization. The injector has explicit MC-101 hook,
  padding, container and checksum constants. This is a separate patched path;
  it neither contains the Fantom Linux ttyGS0 peer nor proves the Fantom stock
  service is externally reachable. No upstream patcher or probe was executed.
- [soobrosa/mc101-firmware-re, 80024167](https://github.com/soobrosa/mc101-firmware-re/tree/800241673bc0db59b4f67ba9579f3ecf38029b63).
  `REPORT.md` and `analysis/pmb_probe_live.md` discuss external parameter mapping
  and CORE1 UMDW routing. Parameter-address translation and internal-word routing
  are different boundaries. Its MC-101 observations do not establish the Fantom's
  outer envelope transformation or physical chip mapping. The source tree was
  searched for routing/SysEx/MMIO implementations; no missing Fantom peer was found.

Neither source supplies a build-compatible Fantom loader. Statements in upstream
prose about risk-free modification, inaccessible tables or universal memory maps
are not accepted as hardware guarantees for this project.

## Qwen review record

OMP returned an actual bounded no-tool analysis from the configured Mac Studio
Qwen model; prompt and response stay in ignored `local/`. It correctly reproduced
the five reply slots. Independent instruction/file checks rejected its conflation
of source with destination, service/component with kind, its invented description
of the comparison table as model/serial/MAC fields, and its incorrect construction
of an overwritten reply from the request builder. Its proposed runtime table dump
was unnecessary: the ELF already contains the strings. No model-generated code,
unverified claim or self-reported test result was accepted.

The host-side identity question is narrower, but the end-to-end upload boundary
remains unresolved. This pass neither installs a bridge nor demonstrates DSP execution.
