# RAMCLR DRAM-IO records and the separate native state-clear loops

2026-11-10. Offline follow-up to [effect replacement and RAMCLR](effect-lifecycle-and-parent-entry-study.md).
This pass recovers a rewriteable address field and four owner-matched record sets
in the hardware DRAM-IO program. The desktop implementation separately has explicit
state-zeroing loops with an excluded endpoint. Neither result establishes the
hardware program's exact time-dependent clear coverage.

Analysis used ordinary file reads, Python 3.13.7 and Capstone 5.0.7. No REA provider,
target execution, device access, request encoding or flashing was involved.

| Artifact | SHA-256 |
|---|---|
| Header-stripped bmc0 CORE1 `local/b0c1a.bin` | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |
| ZENOLOGY arm64 `local/zen_arm64` | `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30` |

Firmware addresses are CORE1 runtime addresses; native addresses are Mach-O virtual
addresses. The new checker rejects different artifact digests before applying them.

## Hardware record shape and placement

The kind-1 list at `61115b14` has header DSP 5, four segments and a 16-byte-stride
table at `61115e3c`. Each segment has `b8` bytes, capacity `160`, and **23 repeated
two-u32 records**. These are literal little-endian u32 words, with no render-packet
word swapping or 16-bit header grammar applied. Calling these records does not
establish a universal 64-bit DRAM-IO instruction size.

The owner descriptor's DRAM-IO selector at `+10` chooses one segment; its `+11`
count is one in each of these four contexts. Descriptor `+c` points to a
`{base,capacity}` reservation that agrees with the selected segment.

| Owner / DSP | Index | Program base | Source | Enum-11 base / length | Enum-2 base |
|---|---:|---:|---|---|---:|
| `610a1674` / 4 | 0 | `0` | `61115b1c` | `420000 / 23000` | `a` |
| `610a16bc` / 5 | 1 | `0` | `61115c14` | `520000 / 23000` | `0` |
| `610a1704` / 5 | 2 | `160` | `61115ccc` | `543000 / 23000` | `22` |
| `610a174c` / 5 | 3 | `2c0` | `61115d84` | `566000 / 23000` | `44` |

All numbers in this section are hexadecimal. For record index i=`0..22` decimal:

- `word0 = 80000000 | (enum11_base + i*1900)`.
- `word1 = enum2_base << 20`; its low 20 bits are zero.

This accounts for all **92 records** without inferring waveform, clearing, transfer
direction or pipeline semantics. The header's DSP 5 is not every owner's destination.
The fifth effect context is outside this four-segment check.

## Independently recovered address field

`CBmcDspMgr::ChangeDramIO_RW_Adrs` at `0113353c` checks both symbols' memory enum
against 11. On the DRAM-IO-symbol path, `0113382c..3854` reads eight bytes through
`0112fa52`, takes the first u32 from stack+8, clears **bits 22:0** with
`BFC r0,#0,#23`, ORs the bounded new address, and writes the eight bytes back through
`0112f964`. The second u32 is preserved. The getter side `01133642..644` extracts
that same 23-bit field using UBFX. This establishes the field used by this stock
address-rewrite path; it does not name the upper nine bits or decode word1.

The read/write helpers use the separate DRAM-IO program aperture on the bool-0 path.
Their mapping is independent of the render DSP program apertures. The segment and
symbol selection/capacity checks in the caller remain part of the contract.

The enum-2/high-12 match is a strong source-slot candidate, independently repeated
across all four owners. There is no complete hardware operand decoder here, so the
helper exposes it as `companion_high12`, not a proven source register or channel.

## Native zeroing is an explicit replacement implementation

Desktop `CFspMfxRAMCLR::SetAlg()` at `00234420` first zeroes coefficients and invokes
the manager's DRAM-IO upload slot. Unlike the hardware-side body, it then performs
three explicit CPU-side zero loops. Their descriptor pointer/count fields are:

| Native descriptor group | Loop pair load | Ring mask | Observed backing path from manager |
|---|---|---|---|
| `+80 / +88`, enum 11 | `0023456c` | `3fffff` | `+28 → +8 → +18 → +20` |
| `+40 / +48`, enum 0 | `0023460c` | `7ff` | `+28 → +8 → +18 → +10` |
| `+50 / +58`, enum 1 | `002346a8` | `7ff` | `+28 → +8 → +18 → +18` |

These group/enum associations are corroborated by the native symbol-address
resolver at `000fc0ac`: its table at `00769f50` sends enums 0, 1 and 11 to
`000fc0e8`, `000fc168`, `000fc368`, which load groups `40`, `50`, `80` respectively.
Native reservation records have a 12-byte stride, distinct from CORE1's 8-byte records.
The enum-11 backing object also receives a `2000000`-byte allocation in
`CSimDSP4_Core` construction at `0016bc08..620`, matching 4,194,304 doubles.

For each reservation pair `{base,length}`, origin O and mask M, the actual loop is:

```text
start = (base - O) & M
current = (base + length - 1 - O) & M
while current != start:
    backing[current] = 0
    current = (current - 1) & M
```

Stores use `STR XZR` at an index scaled by eight. The start index is **excluded**.
The exact store count is `(length-1)&M`, including 32-bit wrap before masking:
length 1 produces zero stores; length 2 produces one; length 0 produces M stores,
not an empty operation. No input validation in these three loop windows changes
that result. This is bounded static reference behavior, not a claim that a
zero-length reservation actually reaches the stock program or should be used.
It prevents interpreting the routine name as a promise to zero every reserved element.

`CFspMfxRAMCLR::GetWaitSample()` at `00234808` returns **1**. Its
`SIM_MFX_RAMCLR::VSubProc()` at `0036cbac` is a single RET. `CSimDSP4_Core::DramioProc()`
at `0016c1e8` processes explicitly queued write/read/mute records and moves doubles;
it is not a fetch/decode interpreter for the firmware's raw DRAM-IO words. Thus the
native CPU clear loops are separate implementation evidence, not an observed
execution of the four hardware record sets.

## Coverage proof still missing

Firmware `GetWaitSample` returns `1900` by subtracting adjacent word0 values.
That is a numeric stride/counter in this build, distinct from the native return of 1.
It cannot simply be multiplied by the record count and called a proved byte sweep:

- `23 * 1900 = 23f00`, whereas the declared enum-11 length is `23000`.
- Last record's starting field is `base + 22600`; the distance from there to the
  reservation's exclusive end is `a00`, not `1900`.

Address unit, counter progression and direction, per-record action/width, repeated
execution, end handling and the source value still need independent evidence.
Without them even the sign/origin of a time-dependent sweep is unproved. No
full-history reset, out-of-range hardware write, or last-record truncation is asserted.

## Reproduce and review

```sh
python3 tools/dramio_clear_study.py
python3 -m unittest discover -s tests -p test_dramio_clear_study.py -v
python3 tools/core1.py local/b0c1a.bin --address 0x113382c --size 0x2e
python3 tools/core1.py local/b0c1a.bin --address 0x1133630 --size 0x1a
```

Use the existing Capstone-capable interpreter. The first command writes only ignored
`local/dramio-clear-study.json`. Five tests cover authored two-word records and field
boundaries, bad shapes, native endpoint/zero-length/wrap behavior against the literal
loop, unknown firmware rejection, all four real owner mappings, the three native
loop anchors and the distinct native wait/sample bodies. Four run without artifacts.

OMP/Qwen returned a bounded no-tool arithmetic/scope review. Its broad separation of
native and hardware paths agreed with the checks above. Its calculated division,
last-chunk size (`1200`), number of unnamed upper bits, and one zero-length formula
were incorrect; those were rejected using direct arithmetic and the loop model.
It also criticized exact-coverage claims that the prompt explicitly disclaimed.
No model-generated code or unverified opcode semantics was accepted.
