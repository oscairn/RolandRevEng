# JUPITER-X v3.03: shared RAMCLR code, different DRAM-IO program layout

2026-11-10. Read-only comparison of the official JUPITER-X update with Fantom-0
v1.08 bmc0 CORE1. This pass establishes two exact byte windows and a significant
RAMCLR table difference. It does not establish interchangeable firmware or an
end-to-end Fantom loader. No update, target executable, device or probe was run.

## Official source and file identity

Download source: Roland's [JUPITER-X update page](https://www.roland.com/global/support/by_product/jupiter-x/updates_drivers/8eb3b467-b455-4588-85b1-c8b62c4458b2/)
and its [v3.03 ZIP](https://static.roland.com/assets/media/zip/jupiterx_sys_v303.zip).
The original ZIP, tar update, component files and download manifest remain ignored
under `local/crossmodel/jupiter-x/`; no vendor bytes are repository deliverables.

| Original artifact | Bytes | SHA-256 |
|---|---:|---|
| `jupiterx_sys_v303.zip` | 5,889,845 | `c82a5a683ec87fc9319bbd565d815c217d580d107f95f7e24f5daab0684a5581` |
| `MI077_UPA_up.bin` | 24,985,600 | `ddfff1b91aa39f2388a1e0f531f37880242e62a01e57a0da2e44447bd1b0d336` |
| `MI077_C1A_up.bin` | 4,194,144 | `9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b` |
| `MI077_C0A_up.bin` | 8,176,816 | `56d7382ad6b642e2213e417311ab49c89ba6359e34339115316521346a66fbb1` |

The C1A outer IEEE CRC32 matches `62546290`, covering bytes before the final
52-byte CRC/identification trailer. Its footer is
`Roland MI077_C1AVER.3.03-BLD.09124 1219 12 09 06`.
C0A's outer CRC32 similarly matches `7fbcd752`. CRC agreement is an integrity
observation, not a cryptographic signature or an execution result.

## Split QSPI members and runtime mapping

C1A is a QSPI container, unlike Fantom's directly combined CORE1 payload. Its
header specifies two 32-byte TOC entries. Each member begins with 32 zero bytes:

| Member | Container offset | Size | SHA-256 including its prefix |
|---|---:|---:|---|
| `idm1.bin` | `1000` | `3dd2c` | `a3927ca6605f0b845f2b85483fce0da7342c82754c7bfadbf006a10dcf4cbdb4` |
| `sdram1.bin` | `3f000` | `35fe10` | `77f390b8f62865fa76b6eedbe07d2bc44fad7780184e1f270ca358dcf685b743` |

Offsets and addresses below are hexadecimal unless explicitly labeled decimal.
The raw TOC checksum fields are `6feb` and `0558`. Summing little-endian u16s
matches `idm1`'s `6feb`, but gives `e559` for `sdram1`, **not** `0558`. The member
checksum algorithm is therefore not claimed verified for both files. The complete
outer CRC still matches; a naive additive mismatch is not treated as proof of a
corrupt official download or silently discarded.

Stripping each member's prefix yields these file-backed mappings:

- `idm1` member offset `20` → runtime `01100000`, length `3dd0c`.
- `sdram1` member offset `20` → runtime `61000000`, length `35fdf0`.

The reset vector is `01100e25`. The reset path at `01100e90..e92` loads
`61000001` and branches there. The ERAM scatter bootstrap resolves ten records.
This corroborates the split addresses rather than assigning them solely by name.
The unbacked ITCM gap after `0113dd0c` is rejected, not filled with inferred zeros.

The common `qspi_c1.py` reader validates the outer CRC, observed header/TOC layout,
exact names, ranges, overlap and zero prefixes. It returns original member hashes
and original source offsets plus a **synthetic analysis view** formed by concatenating
the stripped members. That view is explicitly marked nonoriginal and has SHA-256
`9cb7fdce212675611bbec0592c1dd4c56e43c1a12854e2bd5723debb12a7c7ee`. It is neither a vendor image
nor a deployable update. Existing `Core1` mapping code is reused unchanged on a
temporary local view; the wrapper checks its inferred boundary against the explicit
member split and verifies compared bytes against the original container ranges.

## Two exact code windows

Fantom comparison input: `local/b0c1a.bin`, SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
JUPITER-X RTTI name `13CFspMfxRAMCLR` resolves to typeinfo `61275ee4`, vtable
`6127c778`, and SetAlg Thumb pointer `61064c51`. Thus this RAMCLR body is linked
by actual RTTI/vtable data rather than a same-named logging string.

| Window | Fantom runtime | JUPITER-X runtime | JUPITER member / member offset | Exact bytes |
|---|---:|---:|---|---:|
| RAMCLR SetAlg body | `61056b14` | `61064c50` | `sdram1 / 64c70` | 158 decimal |
| DRAM-IO low-23-bit rewrite | `0113383c` | `011334c0` | `idm1 / 334e0` | 14 decimal |

The respective byte-window hashes are
`5fc550c53a449a074b8955389d3728b768cfda5b9700442f1c881092f404f6ec`
and `ea6ec2d6a64786562c75b6fda29642320ee2e08da733bfb553e32a8e6022e158`.
Container offsets are `a3c70` and `344e0`; they differ from member offsets.

The shared SetAlg body walks enum-6 coefficient reservations and zero-writes them
through manager+`bc`, then dispatches a separate DRAM-IO list through manager+`2c`.
Its referenced literal pool and list live outside the compared body and have different
addresses/data. Exact instruction bytes do not make those dependencies equivalent.

The rewrite window includes the same `BFC r0,#0,#23` / OR / store sequence on the
first u32 of an eight-byte buffer. In JUPITER-X it is inside the assertion-linked
`ChangeDramIO_RW_Adrs` path (assertion reference `01133556` → string `610d40bf`).
It corroborates the address-field encoding already recovered in Fantom. It does not
identify every DRAM-IO opcode or expose an external memory-write route.

## Eleven RAMCLR segments, with two record families

JUPITER-X SetAlg's list at `6118ab70` has type 1, header DSP 5, **11 segments** and
table `6118b390`. Fantom's corresponding list has four segments. These different
counts also appear in GetWaitSample: JUPITER-X checks `r0 <= 11` at `61064d2a`,
while Fantom checks `r0 <= 4` at `61056bee`.

| List indices | Records per source | Source byte length | First-word address stride | First-word starts |
|---|---:|---:|---:|---|
| 0–8 | 23 | `b8` | `1900` | `400000,423000,446000,469000,48c000,4af000,4d2000,4f5000,518000` |
| 9–10 | 22 | `b0` | `2100` | `700000,72d000` |

All observed first words have upper bits `80000000` and a varying low-23-bit field;
companion words have zero low 20 bits and a constant high-12 value within a source.
The table's program bases, capacities and companion values are retained by the
read-only report. JUPITER-X owner-descriptor assignment and physical routing have
not been recovered here; a list-header DSP byte alone does not settle them.

GetWaitSample at `61064cf6` still returns `1900` using adjacent first words from
source `6118ab78`. That return is not independently derived from the last two
sources' `2100` stride. This is evidence against treating a uniform stride or fixed
four-instance layout as a universal BMC contract. Actual execution cadence, clearing
coverage, source semantics and completion timing remain unresolved.

## Encrypted CORE0 comparison remains bounded

The existing C0A header inspector reports payload offset `60`, load destination
`60000000`, crypto control `b6020001`, enabled 1, mode 2, key index `b6` for this
JUPITER-X component. These match Fantom's header fields. Identical mode/index values
do not prove identical keys or make encrypted peer code readable. No decryption,
key extraction/guessing or CORE0 execution was attempted.

## Reproduce and limits

```sh
python3 tools/jupiter_c1_study.py local/crossmodel/jupiter-x/MI077_C1A_up.bin local/b0c1a.bin > local/jupiter-c1-study.json
python3 -m unittest discover -s tests -p 'test_*c1*.py' -v
python3 tools/c0_header.py local/crossmodel/jupiter-x/MI077_C0A_up.bin
```

Use the existing Capstone 5.0.7 interpreter. The wrapper's three tests cover original
span boundaries/unbacked gaps, unknown-image rejection, both actual exact byte windows
and the differing 11-segment layout. The common reader adds two synthetic boundary/CRC
tests. All five pass with the official/local artifacts; without Capstone, four pass
and the corpus comparison skips explicitly. No Qwen draft was needed for these direct
byte/range comparisons. Root independently reproduced the exact matches from raw members.

Cross-model evidence narrows the address-field and shared-manager questions, but
safe loading, task ownership, state initialization, render control-flow timing and
hardware precision remain unverified. No new render opcode or executable wrapper was emitted.


## CORE1 enable masks and mode differences (2026-11-11)

The comparison now checks a third exact byte window: the 14-byte global-mask
OR writer at Fantom `0112f4a6` and Jupiter `0112f126`. Jupiter's original member
is idm1, offset `2f146` (container `30146`). Its PC-relative dependencies differ:
Fantom stores a shadow at `200847fc`, Jupiter at `200850f4`; both OR the argument
into that shadow and write the resulting value to MMIO `41100004`. Common code
bytes do not establish that the two machines have interchangeable masks.

The actual callers contain the format `%08d: CORE1_DSPEnable` and pass their
constant mask through verified MOVW/MOVT/BX veneers to these writers. Five later
calls go through separate verified veneers to the assertion-named SetExeMode.
A bounded MOV/register tracker invalidates volatile arguments after every call,
checks all four new arguments and permits a nonreturning branch only at the end.
Unknown sources, omitted definitions, extra operations and early tail branches
are rejected. It does not infer dataflow from equal numeric constants elsewhere.

| Image | Enable routine | SetExeMode | Global OR mask | Modes for DSP 0,1,2,3,6 |
|---|---|---|---|---|
| Fantom-0 v1.08 | `610016b0` | `01130b6c` | `45c5` | 2,0,2,0,2 |
| Jupiter-X v3.03 | `610029c8` | `011307ec` | `4fcf` | 2,2,2,2,2 |

All ten calls supply argument 0 and event 3. Mask bits 6:0 and 14:8 independently
equal the set of indices receiving mode 2: `45` versus `4f`. Bit 7 is set in both
observed masks. The model checks this **two-image correlation**, not a complete
register field specification. It does not establish the purpose of bit 7, the
meaning of mode 0/2, or whether a particular DSP subsequently executes samples.
A function named enable can configure several engines differently; its name
alone cannot turn one enum value into a safe halt command.

SetExeMode's Fantom body packs event<<28, mode<<24 and the unscaled even 16-bit
argument, writes one register and returns. Its separate getter reads only mode
bits 25:24. These interfaces expose no PC, return stack, issue fence or proof of
execution completion. Argument 0 in every observed call cannot resolve argument
units or establish where a custom fragment would begin.

The [separate active DMA drain](kernel-audio-abi-study.md#separate-active-dma-drain-and-manager-wrappers)
closes a different offline interface gap: manager slots 44/48 distinguish starting
queued DMA from draining already-started DMA. DMA completion does not prove DSP
halt, cache coherency, safe code replacement or the custom body's continuation.

The checker reads the original Jupiter container, validates its identity/mapping,
and compares the exact window back to its original member bytes. Added corpus
tests cover both actual call tuples and reject stale/unproved register sources,
missing producers and an early nonreturning branch. No Jupiter hardware is needed
or accessed; this is a firmware comparison supporting the Fantom-07 investigation.
