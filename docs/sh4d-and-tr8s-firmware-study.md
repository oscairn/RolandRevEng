# Additional official firmware: SH-4d and TR-8S

2026-11-10. Offline file/Capstone analysis following Jacob's request to acquire
other BMC firmware when it can resolve engine-loading or ISA questions. These two
updates add a different readable CORE1 image and a concrete encrypted-only limit.
No updater, target program, device or probe was executed.

## Official downloads and original identity

Sources are Roland's [SH-4d v2.00 page](https://www.roland.com/global/support/by_product/sh-4d/updates_drivers/085ae596-6d56-4904-bd9b-e12ecca85391/)
and [TR-8S v3.00 page](https://www.roland.com/global/support/by_product/tr-8s/updates_drivers/84163b50-a2c5-4c3e-be2a-6ccee610d6ff/).
Their page-linked files were downloaded on 2026-11-10:
[SH-4d ZIP](https://static.roland.com/assets/media/zip/sh4d_sys_v200.zip),
[TR-8S ZIP](https://static.roland.com/assets/media/zip/tr8s_sys_v300.zip).

| File | Bytes | SHA-256 |
|---|---:|---|
| `sh4d_sys_v200.zip` | 5,386,409 | `24f65c09661c717b9c91a4cdd27aa55e6f7beb4fb8870426d183d76634eee149` |
| `SH4d_UPA_up.bin` | 25,589,760 | `744584b30b93fd57b1ab271105a64a6c48b609217175b7d5b54b640ae58f9f5e` |
| `tr8s_sys_v300.zip` | 2,723,820 | `c526b7a4d2a9fa160ed88b3f14fcb04aff0a3714284f7831f6d1135c996dfd93` |
| `TR8S_UP.bin` | 3,983,360 | `f1948e2719fef2735f0611848501f1eb3a1a163b5b75aaef20ae3db28489f2ba` |

Both BIN files are tar archives. SH-4d contains `DD013_C1A`, `C1C`, `C0A`, `C0C`
and `SUB` components. TR-8S contains **only** `rpg42_m0c0a_up.bin` and
`rpg42_init_param.bin`. That is a bound on these downloaded packages, not a claim
that the TR-8S hardware lacks another core or that parameter data contains no code.
Original downloads, pages, extracted components and manifests stay under ignored
`local/crossmodel/{sh-4d,tr-8s}/`.

## SH-4d's readable CORE1

`DD013_C1A_up.bin` is 4,194,144 bytes, SHA-256
`57466624effa7b78ea6f775487d78a35dbf141d2ec4a979338266b77bdcccadf`.
The existing common QSPI reader accepts the two-member layout and validates its
outer CRC32. Footer: `Roland DD013_C1AVER.2.00-BLD.062Commit:6e4ad273b`.

| Original member | Container offset | Size including zero prefix | SHA-256 |
|---|---:|---:|---|
| `idm1.bin` | `1000` | 258,972 decimal | `67e6bcea555a5ec4fba80e90cf091d7391627964f2cb57693435724a3a7af359` |
| `sdram1.bin` | `41000` | 3,145,468 decimal | `f7fde1a3f5f09d90e6fbf22efe4fe9cabc39f4d52ed11573391b8134b6ac38b5` |

After stripping each 32-byte zero prefix, runtime bases are `01100000` and
`61000000`. The reset vector is `01100dc5`; the ERAM split is at synthetic-view
offset `3f37c`, consistent with the actual stripped ITCM size. Synthetic analysis
views remain explicitly nonoriginal; the comparison searches each actual member
separately and never bridges a missing ITCM address range.

The following windows each occur once and exactly match Fantom bmc0 payload
SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`:

| Window | Bytes, decimal | Fantom runtime | SH-4d runtime | SH C1A container offset |
|---|---:|---|---|---|
| MMIO read/reply prefix | 324 | `6102d2e6` | `61029baa` | `6abca` |
| RAMCLR body | 158 | `61056b14` | `610593b0` | `9a3d0` |
| Low-23-bit DRAM-IO rewrite | 14 | `0113383c` | `01134f48` | `35f68` |

Their respective hashes are
`454f8fe6b80521c5738b5649133668dbdf4ccda7f08ca2dcec076cc411855246`,
`5fc550c53a449a074b8955389d3728b768cfda5b9700442f1c881092f404f6ec`,
and `ea6ec2d6a64786562c75b6fda29642320ee2e08da733bfb553e32a8e6022e158`.

This provides another independently downloaded source for the shared CORE1 code
family. The MMIO prefix includes the same local-frame/count/store construction
already studied in Fantom and MC-101. It does not prove that an external message
reaches it. The RAMCLR window uses literal pools and manager tables outside the
matched bytes; equal instructions do not imply equal owners or memory capacities.
No complete SH-4d graph or hardware ISA compatibility is asserted.

## TR-8S's inspected update does not supply a readable peer

Its application component is 2,535,520 bytes, SHA-256
`cfdc444c03a9d41655f02d9bf3dd3c28b335c292b09cbede23924aa8ed97620d`.
The parameter component is 1,441,792 bytes, SHA-256
`07c5b2a974a4a0b33489ee663b75c27fc7d65714df19b9cb252f0d5a9830a4eb`.
There is no C1A member to parse under the split CORE1 format in this package.

Both TR-8S's application and SH-4d's `DD013_C0A` have the existing `App1_Main`
header layout: payload offset `60`, load destination `60000000`, crypto control
`b6020001` (enabled 1, mode 2, key index `b6`). The declared payload lengths are
2,535,360 and 8,781,760 bytes respectively. These are header observations, not
successful decryption, identical-key proof or a plaintext host-to-CORE1 bridge.
No key guess or cipher attack was attempted.

## Reproduce and remaining work

```sh
python3 tools/additional_firmware_study.py
python3 -m unittest discover -s tests -p test_additional_firmware_study.py -v
```

Use the existing Capstone-capable interpreter for the corpus check. The helper
pins the two original tar hashes and Fantom reference digest, checks component
inventories, reuses the QSPI/header readers and reports original byte ranges.
Three tests cover overlapping matches, refusal of cross-region matches and bad
bounds, unknown-image rejection, both real archives and the three exact windows.
Two tests run without vendor files. Generated reports are ignored/local.

These images are now available to constrain condition-word, owner and DRAM-IO
interpretations. Their initial inventory and code matches do not settle render
call/return timing, complete hardware state clearing, safe manager entry or the
Fantom Linux transport peer. Further downloads should target a specific missing
counterexample or readable implementation rather than assume another product's
encrypted update will expose the peer.
