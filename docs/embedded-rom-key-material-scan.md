# Embedded ROM/key-material search in the retained firmware

2026-11-10. This bounded offline search found **no copy of the documented MC-101
16 KiB Boot ROM and no confirmed key-material candidate** in the scoped objects.
That is not proof that every downloaded byte is free of unknown, transformed or
compressed key material. No candidate key was guessed, printed or tested, and no
firmware, hardware probe or upstream dumper/decryptor CLI was executed.

This answers a narrower question than cipher compatibility. See
[the separate ciphertext/key-location study](core0-ciphertext-and-key-location.md)
for aligned CORE0 block comparisons and the distinction between common container
settings, common key use and actual recovery of a key.

## What would count as a located ROM

The pinned public [MC-101 Boot ROM study](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/docs/boot_rom_analysis.md)
reports a 16,384-byte ROM at `01200000`, SHA-256
`742b1dd61d07509d8c72a1c7bcf3a44b9707e72d31543e3256415eb4307e60d5`,
with initial vector values SP=`01060000`, reset=`012000d1`.
Those two u32 values form the search anchor. A hit is not accepted as the documented
ROM unless the complete following `4000`-byte window has that exact hash. A whole
16 KiB artifact also receives the identity check independently of the vector anchor.
The scan does not hash every possible unanchored 16 KiB window of larger files.

The public [decryptor](https://github.com/edco/mc-101-re/blob/b6607ade1417e90afd7a0eab51aa371b21d2b3d4/tools/decrypt_c0a.py)
reads a caller-supplied ROM file. Its table base `012023b0` and index `b6` imply an
entry at `012034c0`, ROM offset `34c0`, length 24 bytes. Those addresses and the
container index are **not the key bytes**. That source does not include the ROM in
its tracked tree. Its CLI prints the derived key, so that CLI was deliberately not
invoked. The candidate detection/reporting code never emits a ROM/table slice.

These are MC-101 source assumptions, not an independently supplied ROM dump or
proof that the Fantom uses identical ROM contents. No authentic ROM copy was
available locally to validate the public identity itself.

## Exact local scope

`tools/key_material_scan.py` read the following fixed local inputs and reports a
SHA-256 for every distinct scanned object. It neither recursively searches the
user's home directory nor inspects provider credentials or unrelated secrets.

| Category | Unique objects | Bytes scanned |
|---|---:|---:|
| Fantom bmc0/bmc1 C1A payloads and C0A containers, Linux `mi078`, `qctest` | 6 | 71,093,411 |
| Every regular component member of retained official MC-101/JUPITER-X/SH-4d/TR-8S update tar archives | 16 | 74,811,409 |
| Recognized CORE1 initial-data expansions | 5 | 99,864 |
| Total | **27** | **146,004,684** |

The archive component coverage includes:

- MC-101: C0A, C0C, C1A, C1C.
- JUPITER-X: C0A, C0C, C1A, C1C, SUB.
- SH-4d: C0A, C0C, C1A, C1C, SUB.
- TR-8S: encrypted M0C0A and the init-parameter file.

The scanner reads members directly with `tarfile`, subject to fixed member-count
and size limits; it does not extract untrusted paths to disk. Container bytes,
including opaque ciphertext and raw resource data, are searched as stored. QSPI
C1A parsing reuses the bounded split-member reader for interpreting scatter data;
no search hit is manufactured by joining the unmapped ITCM gap to ERAM.
Download URLs, archive identities and component layout remain in the existing
[JUPITER-X](jupiter-crossmodel-c1-study.md), [MC-101](mc101-v182-core1-comparison.md)
and [SH-4d/TR-8S inventory](sh4d-and-tr8s-firmware-study.md) studies and
ignored local manifests. Detailed per-object hashes and offset samples are retained
in ignored `local/key-material-scan.json` and can be reproduced from these inputs.

## Initial-data handling is explicit and limited

The reference Fantom bmc0 payload is pinned to SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
The scanner compares each candidate scatter handler's complete 90-byte window with
that build's already verified handler at `6100003c`. Only exact byte matches are
expanded with the existing bounded `expand_initial_data()` helper. This is file-data
reconstruction, not execution of target code.

All five recognized expansions target `2008008c`:

| Image | Expanded bytes | Compressed bytes consumed |
|---|---:|---:|
| Fantom bmc0 | 18,316 | 8,003 |
| Fantom bmc1 | 18,192 | 7,239 |
| MC-101 | 23,344 | 10,359 |
| JUPITER-X | 20,612 | 8,880 |
| SH-4d | 19,400 | 7,937 |

Other handlers and other compression formats were not interpreted. A raw byte scan
cannot establish the absence of a ROM hidden by an unrecognized transform. Original
input files were preserved, and no expanded byte array or synthetic mapped view was
committed or labeled as original vendor firmware.

## Observations and limits

Across the 27 objects:

- The documented eight-byte MC-101 vector prefix has **zero occurrences**. Thus no
  complete vector-anchored window with the documented ROM hash was recovered.
- Little-endian literal words `012023b0`, `012034c0` and `40020400` each have zero
  occurrences. This is only a literal-byte result. MOVW/MOVT construction, relative
  arithmetic, indirect calls and references to a different ROM revision are separate
  code-analysis questions; absence of these literals cannot prove absence of keys.
- The word `01200000` occurs 690 times, including many occurrences in PCM/resource
  containers. Numeric equality therefore does not authenticate a ROM pointer or
  identify an embedded table.
- `b6020001` occurs in the six scanned C0A headers. Those mode/index settings do not
  supply the selected 24-byte entry. No random neighboring bytes were promoted to a
  candidate key, and no entropy or arbitrary 24-byte search was used.

The positive criterion is deliberately strict: locating a documented ROM copy would
identify a concrete table location for subsequent build-specific validation; it
would still not prove that its selected key decrypts every other model. With no
actual candidate identified here, no 3DES trial or plaintext-structure claim is made.
Unknown standalone key bytes have no universal recognizable signature, so this search
cannot answer their absence with certainty.

## Reproduce and verify

```sh
BMC_CORPUS_DIR='/Users/jacob/Projects/Open Synth Platform/bmc-research/local' \
  /Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/key_material_scan.py
BMC_CORPUS_DIR='/Users/jacob/Projects/Open Synth Platform/bmc-research/local' \
  /Users/jacob/.pyenv/versions/3.13.7/bin/python3 -m unittest discover -s tests -p test_key_material_scan.py -v
```

The report contains identities, provenance, counts, offset samples and window hashes;
it contains no key bytes or firmware excerpts. Five tests cover authored complete and
truncated vector windows, exact-hash gating, metadata-only reporting, literal-address
counterexamples, bounded offset samples and the actual scoped corpus. All five pass
with the prepared inputs; four pure tests run without artifacts or Capstone.
No Qwen draft was needed for this deterministic search.
