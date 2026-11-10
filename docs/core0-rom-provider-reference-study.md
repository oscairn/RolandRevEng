# CORE0 key-provider references in readable updates

2026-11-10. **No CORE0 firmware-decryption key or confirmed ROM key-provider call
was recovered in this bounded reference study.** The community MC-101 decryptor
expects a separate silicon boot-ROM dump; its source does not embed the key.
No separately identified boot-ROM dump was present among the inspected inputs.
This is not a claim that every downloaded byte, encrypted component, ROM revision
or installed file has been proved key-free.

This work used offline file reads and Capstone 5.0.7 under Python 3.13.7. No target
code, updater, device, probe, exploit or decryption attempt was run. No key bytes
or vendor ROM bytes are emitted by the new reproducer or committed to the repo.
The root investigation separately examines exact key candidates and ciphertext
relationships; the evidence here concerns readable-code provider references.

## What the public decryptor actually needs

The inspected source is [edco/mc-101-re, revision b6607ade](https://github.com/edco/mc-101-re/tree/b6607ade1417e90afd7a0eab51aa371b21d2b3d4),
particularly `tools/decrypt_c0a.py`, `docs/boot_rom_analysis.md` and
`docs/core0_boot_and_memory_architecture.md`. The local decryptor file's SHA-256
is `1e5e312d3d60183e86db09dac63d08abf763e654db8462257fda1a1751e7b1de`.
Its default `vendor/mc101_sys_v182/dumps/bootrom_full_16k.bin` is absent from the
retained checkout, including ignored files.

`derive_3des_key` reads 24 bytes from that external ROM file at
`23b0 + key_index*24`. For index B6, the documented address is:

`012023b0 + b6*18 = 012034c0` (all numbers in this expression are hexadecimal).

Those are **addresses and an entry size**, not key bytes. The function rearranges
six words for the hardware bus/cipher ordering and returns the resulting key;
it raises an error if the ROM input is unavailable. Reading this Python source
therefore does not itself make a B6 key available.

The upstream ROM/body descriptions supplied these search anchors:

| Documented object | Address |
|---|---|
| MC-101 silicon ROM | `01200000..01203fff` |
| Key table base | `012023b0` |
| B5 / B6 entry | `012034a8` / `012034c0` |
| Cipher setup body / Thumb pointer | `01202604` / `01202605` |
| Buffer cipher body / Thumb pointer | `0120283a` / `0120283b` |
| Decrypted flash-read body / Thumb pointer | `01202c94` / `01202c95` |
| Setup / buffer export slots | `01203f64` / `01203f68` |
| ESC2 input/output FIFOs | `40020000` / `40020200` |
| ESC2 six key registers | `40020400..40020414` |
| ESC2 cipher control / described bit-band alias | `40020420` / `42408400` |

These meanings are reported by the community's MC-101 ROM study. We do not have
that ROM or App0 in this pass to independently validate its table/key ordering,
and do not assume the same provider addresses or keys exist on every model.
In particular, a container's `b6020001` control word identifies the declared
mode/index, rather than containing 24 bytes of key material.

## Exact readable inputs and mappings

| Input | SHA-256 |
|---|---|
| Fantom bmc0 stripped C1A | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |
| Fantom bmc1 stripped C1A | `c8d150b9cfe13d8e091ed5f3d79786d084bdb7a6ae6d360582f32d5d223268bd` |
| MC-101 v1.82 `RPG69_C1A_up.bin` | `6de1e182e531d672ef9bcc0aabf853dd724f59e70dfd9c9aa34c28a393d62a21` |
| JUPITER-X v3.03 `MI077_C1A_up.bin` | `9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b` |
| SH-4d v2.00 `DD013_C1A_up.bin` | `57466624effa7b78ea6f775487d78a35dbf141d2ec4a979338266b77bdcccadf` |
| JUPITER-X `MI077_SUB_up.bin`, 24,096 bytes | `718abc6885cb3c0a45ba0da7a50d1abb0b775f5d48dbeaac1f71025511749558` |
| SH-4d `DD013_SUB_up.bin`, 21,073 bytes | `f9ab7a9e845907afe0cdad7d336961cc1467bc37d91a80f173a2d5491c798fca` |

The official source/archive identities are preserved in the existing
[MC-101](mc101-v182-core1-comparison.md), [JUPITER-X](jupiter-crossmodel-c1-study.md)
and [SH-4d/TR-8S](sh4d-and-tr8s-firmware-study.md) studies. The inspected MC-101
update has no SUB component; the inspected TR-8S update has no readable C1A.

Fantom uses the existing `Core1` map. The three QSPI C1As use the CRC/bounds-checked
split-member reader: strip each member's 32-zero-byte prefix, map ITCM at
`01100000` and SDRAM at `61000000`, and keep their actual spans separate.
No search window is allowed to cross the unmapped gap.

Each SUB has a four-byte prefix followed by plausible ARM vectors: JUPITER-X SP
`20001780`, reset `08000149`; SH-4d SP `20001ef0`, reset `080001a1`. Stripping
four bytes and mapping at `08000000` places the reset routine at its expected
LDR/BLX/LDR/BX startup sequence. The prefix format was not fully decoded.
This mapping check does not identify the SUB MCU as an ESC2/BMC chip.

## Search boundary and results

The reproducer searches each actual region independently for:

- Four-byte-aligned little-endian values in the broad ROM candidate range
  `01200000..0120ffff`, or the described cipher range `40020000..40020424` and
  alias `42408400`; the named provider anchors above are reported separately.
- Thumb PC-relative word-load candidates whose pool value lands in those ranges.
- Immediate Thumb B/B.W/BL or MOV candidates that construct such a value.
- Contiguous MOVW/MOVT pairs targeting the same register.

It scans every halfword for these instruction forms, so matches can lie in data
or the second half of real 32-bit instructions. Results are explicitly candidates,
not a proved call graph or an extraction of key material.

| Input | Exact named provider words | Instruction-shaped candidates | Accepted provider/key evidence |
|---|---:|---:|---|
| Fantom bmc0 C1A | 0 | 9 | None |
| Fantom bmc1 C1A | 0 | 7 | None |
| MC-101 C1A | 0 | 12 | None |
| JUPITER-X C1A | 0 | 8 | None |
| SH-4d C1A | 0 | 12 | None |
| JUPITER-X SUB | 0 | 45 | None |
| SH-4d SUB | 0 | 10 | None |

No contiguous MOVW/MOVT pair or immediate MOV in this scope constructed a value
in the searched ROM/cipher ranges. No exact aligned reference to the documented
table, B5/B6 entries, cipher bodies or export slots was found.

### Rejected branch and data leads

All 17 BL-shaped ROM candidates in the C1A files overlap a four-byte arithmetic
decode beginning two bytes earlier. For example, the apparent BL at Fantom
`011122d0` is inside the SDIV at `011122ce`; the next real instruction starts at
`011122d2`. Fantom `01105ea6` similarly overlaps SMULBB at `01105ea4`.
The corresponding MC-101/JUPITER/SH sites have the same arithmetic-pattern issue.
No such candidate was accepted as an actual call into ROM.

The remaining C1A candidates are literal-load-shaped patterns in packed data,
without a demonstrated reachable ARM key-provisioning sequence. For example,
Fantom `610e3094` happens to decode as a load of `01200000` and `6121b82c` as a
load of `012001b0`; their surrounding packed words do not establish a ROM reader.
Eight SH-4d patterns load `400200fd` from repeated packed regions. These are not
evidence of six successive key-register writes or a firmware-decrypt caller.

### SUB numeric address overlap is not peripheral identity

The SUB matches are real loads of addresses including `40020008`, `4002001c`,
`40020030`, `40020044`, `40020058`, `4002006c` and `40020408`. Their code context
differs from the documented ESC2 cipher setup. JUPITER-X routine `08001274` and
SH-4d routine `080014a8` distinguish controller bases around `40020008` and
`40020408`, derive a per-instance/channel index with a **20-byte stride**, cache
control fields and configure those instances. This is consistent with a separate
MCU's DMA-controller/channel setup, an inference from the code structure.
It is not a confirmed ESC2 DES key-loader and yields no CORE0 key bytes.

Using the same numeric peripheral range in a different MCU image must not be
turned into a shared-memory-map or key-provisioning claim.

## Reproduce and interpret the limit

`tools/core0_provider_refs.py` accepts only the seven input hashes above, maps
their actual spans, and emits addresses, instruction metadata and hashes.
Its three tests use original synthetic literal/MOVW/MOVT/branch fixtures,
region-boundary rejection and unsupported-image rejection. They do not contain
keys or vendor ROM data. The full seven-file scan was also run once and its
candidate records retained under ignored `local/provider-reference-results.json`.

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/core0_provider_refs.py local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/core0_provider_refs.py local/crossmodel/mc101/RPG69_C1A_up.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 -m unittest discover -s tests -p test_core0_provider_refs.py -v
```

The scan does not cover noncontiguous constant construction, computed or indirect
ROM calls, encrypted contents, every possible provider revision, or arbitrary
key bytes lacking a code reference. It therefore does not prove global absence.
No firmware-key candidate reached plaintext validation in this pass because no
actual key bytes were recovered. A future candidate still needs verification
against the exact encrypted payload and its startup/scatter/checksum structure;
an address, an index, a string, or a few plausible Thumb instructions is insufficient.

No additional Qwen draft was used. No wave, license or signing-key material was
reclassified as a CORE0 firmware key.
