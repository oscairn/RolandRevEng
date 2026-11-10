# MC-101 v1.82 CORE1 comparison with Fantom-0

2026-11-10. The official MC-101 image contains the same MMIO read/reply builder
previously traced in Fantom-0, including its stack-size discrepancy. Its ordinary
wait function also matches except for relocated calls, while its scaled-wait
multiplier differs: **44,100** versus **48,000**. These are byte/instruction
comparisons of factory updates, rather than similarities inferred from strings.

This is offline analysis with Python 3.13.7 and Capstone 5.0.7. No firmware was
executed, device opened, request generated, update repackaged or target flashed.
The comparison does not establish the MC-101's external service route or provide
a custom-engine loader.

## Official source and identities

The [Roland MC-101 support page](https://www.roland.com/global/support/by_product/mc-101/updates_drivers/c6fc66b8-d5d0-4b3b-a6d0-db156217129f/)
identifies System Program Ver.1.82 and links its download button to
[mc101_sys_v182.zip](https://static.roland.com/assets/media/zip/mc101_sys_v182.zip).
Both page and archive were fetched on 2026-11-10. The ZIP contains one tar-format
file, `mc101_sys_v182/MC101_UPA_up.bin`; its four regular members are the
`RPG69_C0A`, `C0C`, `C1A` and `C1C` update containers. Only C1A was analyzed.

| Input | Bytes | SHA-256 |
|---|---:|---|
| `mc101_sys_v182.zip` | 5,094,049 | `5062dbf08fc4ba6a18f3e1fd4b7ab79c407939b8f497891e4ad0beee76b50a4d` |
| `MC101_UPA_up.bin` | 20,285,440 | `14bfb011aea0f492c6c55fcb1abf4bfce89913c84330586f79d1d76d7b6997e8` |
| `RPG69_C1A_up.bin` | 4,194,144 | `6de1e182e531d672ef9bcc0aabf853dd724f59e70dfd9c9aa34c28a393d62a21` |
| Fantom bmc0 stripped C1A payload | — | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |

The C1A footer identifies `RPG69_C1A`, version 1.82, build 14423, timestamp
`0517 22 49 32`. Its stored CRC32 `81796451` matches the bytes before the final
52-byte CRC/identification trailer. The archive contains unmodified factory
code; none of the separate community project's patched dumps or probe results
were used as the comparison input.
The directory's per-member checksum fields are recorded, without claiming a
verified checksum algorithm; the simple 16-bit additive sum does not match SDRAM.

The QSPI layout was first located using read-only inspection of
[edco/mc-101-re](https://github.com/edco/mc-101-re), revision
`b6607ade1417e90afd7a0eab51aa371b21d2b3d4`, particularly its unpacker, format
notes and mapping comments. The actual downloaded bytes, bounds, CRC and code
anchors were then checked independently. No community patcher, probe, client or
decryptor was executed, and no key material was needed.

## Split CORE1 mapping

This C1A is a QSPI directory with two members. Each begins with 32 zero bytes;
remove that prefix before assigning its runtime base. Keeping it would place the
reset and ERAM bootstrap instructions at the wrong addresses.

| Member | Container offset | File bytes | Raw member SHA-256 | Runtime base after stripping 32 bytes |
|---|---:|---:|---|---|
| `idm1.bin` | `1000` | 241,796 | `80f062ac8d050fbffcaa71c91500f2e2b71749d7103d158312325e20d8747578` | `01100000` |
| `sdram1.bin` | `3d000` | 3,709,724 | `e532f514f64f31813aca13263a68a27d71e353efb156f8a659d02354572835ba` | `61000000` |

For an ITCM address A, the member-file offset is `A-01100000+20`; for an ERAM
address it is `A-61000000+20`. Add the member's directory offset to locate it
inside C1A. All addresses in this report use this mapping.

Independent anchors:

- The stripped vector table contains initial SP `200a91c8` and reset pointer
  `01100de5`. The code at `01100de4` begins the expected core-register setup.
- Reset's literal at `01100e70` selects `61000001`; the branch is at `01100e52`.
- The stripped SDRAM member starts at `61000000` with the ARMCC bootstrap calling
  the scatter loader at `61000008`, rather than with 32 bytes of zero instructions.

This checks the compiled address map; it is not an observation of a live boot.
The existing Fantom `Core1` mapping was not loosened to guess other layouts.

## Shared MMIO reply builder

Fantom helper `6102d2e6` and MC-101 helper **`6103205a`** have **324 consecutive
identical bytes**, from PUSH through outgoing-call argument construction.
That sequence occurs once across the two MC-101 code members. Its SHA-256 is
`454f8fe6b80521c5738b5649133668dbdf4ccda7f08ca2dcec076cc411855246`.
The subsequent output BL differs: MC-101 calls `6107df12` at `6103219e`;
Fantom calls `6107773e` at `6102d42a`. The four-byte add-SP/pop epilogue is identical.

Consequently the detailed [Fantom frame analysis](core1-service-startup-mmio.md)
also applies to this MC-101 reply builder:

| Property | Both supplied builds |
|---|---|
| Local frame after saving r4/lr | 80 bytes, reply starts at SP+0 |
| MMIO read address | `41100000` + masked 25-bit, four-byte-aligned offset |
| Decoded read count | Four seven-bit groups, clamped to 64; complete words only |
| Reply | `F0 41 10 4E 13`, encoded address, eight nibbles per word, checksum, F7 |
| Emitted size | `11 + 8*floor(min(count,64)/4)` for count>=4 |
| Counts 32..35 | 75 emitted bytes |
| Counts 36..39 | 83 bytes: three bytes of saved r4 overwritten if loads complete |
| Count 40 | 91 bytes: saved r4/lr and three caller bytes overwritten if loads complete |
| Count 64 | 139 bytes; exceeds the local reservation by 59 |

The shared prefix **`F0 41 10 4E` is present in both factory firmware models**.
It therefore cannot be treated as evidence that a record uniquely identifies
Fantom-0. This does not establish universal Roland compatibility, public MIDI
reachability or a safe live-read bound.

The MC-101 caller is also concrete rather than just a matching detached body.
Handler `61032220` checks the header and dispatches read command `11` to
`61032330`. That path prepares its scratch object and tail-branches from
`6103237a` to `6103205a`. Wrapper `6103237c` supplies object `200a5c20` and
branches to `61032220`. The read path's minimum length is 15 bytes.
Its inline write body at `610322b8..3232c` uses the same `41100000` base,
25-bit offset mask, four-byte alignment check and `<01000000` store window.
This report does not trace that wrapper back to a physical transport or prove
its receiver activation on a running MC-101.

## Wait comparison and a model-specific scaling constant

The **98-byte** MC-101 function `01124c5c` equals Fantom `011271b8` after
ignoring only the immediate fields of its three BL instructions. Their target
relocations are:

| Role | Fantom target | MC-101 target |
|---|---|---|
| Priority setup | `01103762` | `0110285a` |
| Callback registration | `0110376c` | `01102864` |
| Arm timer | `01103772` | `0110286a` |

The initial flag load uses a literal outside the compared function; that literal
changes from Fantom `200845b4` to MC-101 `2008390c`. The callback pointer changes
to `01124c51`. The code structure is shared: drain any pending global completion,
schedule unsigned chunks up to `fffe`, wait for every intermediate chunk, and
skip polling the final chunk only when the completion argument is zero.
An amount of zero still performs the initial drain but does not arm a new chunk.

MC-101 driver `0110286a` implements the same clamp and raw 32-bit target formula
`current_counter + min(chunk,fffe) + 1`, writing to `40059020`, then enabling
bit 0 at `40059000`. It reads the current value from `4005900c`. Its cap path uses
a branch at `0110288e` and rejoins at `01102890`, whereas Fantom uses conditional
MOVW. This instruction selection difference does not change that arithmetic.
Neither path establishes the hardware reason for `+1`, a timer width or a timeout.

The scaled neighbor differs materially:

| Build | Routine | MOVW multiplier | Following calculation |
|---|---|---:|---|
| Fantom | `0112721a` | 48,000 (`bb80`) at `0112721e` | Low 32-bit multiply, signed division by 1,000 |
| MC-101 | `01124cbe` | 44,100 (`ac44`) at `01124cc2` | Low 32-bit multiply, signed division by 1,000 |

This is evidence for a model-specific software scaling constant. It does not
measure the timer or audio clock, prove wall-clock duration, or justify replacing
every 48,000 constant in a custom engine. The same wrapped multiplication and
signed-division caveats from the [wait study](core1-wait-and-initial-data-study.md) apply.

## Reproduction and remaining limits

The comparison tool is pinned to the two hashes above. It uses the bounded common
QSPI reader and checks the reset-map anchors, shared MMIO prefix/epilogue,
relocated wait body and MC-101 scaling instruction. It emits metadata only.
Vendor files and detailed scratch disassembly stay under ignored `local/`.

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 tools/mc101_core1_compare.py \
  local/crossmodel/mc101/RPG69_C1A_up.bin local/b0c1a.bin
/Users/jacob/.pyenv/versions/3.13.7/bin/python3 -m unittest discover -s tests -p test_mc101_core1_compare.py -v
```

No additional Qwen draft was used in this comparison; byte equality and direct
instruction review supplied the evidence. MC-707, encrypted CORE0, DSP program
opcodes and loader/DRAM-IO ownership were not investigated in this focused pass.
The new result supports a shared CORE1 code family and identifies a scaling
difference; it does not close the external host bridge, runtime scheduling,
verified custom-engine ABI or safe installation gaps.
