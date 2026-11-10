# AX-Edge and JUNO-X firmware comparison

2026-11-10. Two additional official updates supply readable CORE1 images and
more CORE0 ciphertext for comparison. They did not supply a confirmed boot ROM,
key or new Fantom access path. Everything below is offline inspection; no update,
plugin, native sample processing or device was executed.

## Official source and identities

Downloaded directly from the update links on Roland's
[AX-Edge v1.11 page](https://www.roland.com/global/support/by_product/ax-edge/updates_drivers/5e5f0e36-6fc5-4f35-a648-d2d024b66dfc/)
and [JUNO-X v1.12 page](https://www.roland.com/global/support/by_product/juno-x/updates_drivers/495fe8ca-a253-4a72-90e2-512e250e839b/).
The respective archives are
[ax_edge_sys_v111.zip](https://static.roland.com/assets/media/zip/ax_edge_sys_v111.zip)
and [junox_sys_v112.zip](https://static.roland.com/assets/media/zip/junox_sys_v112.zip).

| Object | Bytes | SHA-256 |
|---|---:|---|
| AX-Edge ZIP | 126,347,046 | `92b9c6f68b5ffa50715d85390d6f00d07602cacb322b1f4fccfef3106f86c771` |
| `KY022_UPA_up.bin` | 152,453,120 | `a9d0e103d7a16619b4a84045cd55c56312fd291411f4dd66ff5d2ea9fa815a60` |
| JUNO-X ZIP | 5,518,868 | `c4dd51453ba7e15bda9e2c3e079a72ef18bdb9857b1be3f8c75a95fb0ef05857` |
| `JUNOX_UPA_up.bin` | 24,801,280 | `83516fc8a459879a976033fd68fe551b350bbd084e4ec78704885208142fbc5e` |

Each ZIP contains one update tar inside its product directory. Each tar has five
regular members under `./_tmp/`. AX-Edge supplies C1A/C1C/C0A/C0C plus a
134,217,728-byte wave object; JUNO-X supplies C1A/C1C/C0A/C0C plus a 21,200-byte SUB
image. Member hashes and full scan metadata stay in the ignored local report.
The checker validates the parent update hash, bounds members, refuses duplicate
basenames/unsafe paths/nonregular entries and reads members without extracting
their archive paths. No binary or generated dump is tracked or copied to the vault.

## Readable CORE1 comparison

Both C1A files pass the existing strict two-member QSPI parser and outer CRC32
check. The mapped regions are separate `idm1.bin` and `sdram1.bin` payloads. The
concatenated analysis view omits the hardware gap; it is synthetic, not a flashable
image. File-backed matching is restricted to each actual region separately.

The three exact Fantom reference windows are the 324-byte MMIO-read prefix,
158-byte RAMCLR body and 14-byte DRAM-IO low-23-bit rewrite, as described in the
[SH-4d/TR-8S study](sh4d-and-tr8s-firmware-study.md).

| Window | JUNO-X unique runtime match / original container offset | AX-Edge exact match |
|---|---|---|
| MMIO-read prefix | `6102f15e` / `6e17e` | None |
| RAMCLR body | `610608b8` / `9f8d8` | None |
| DRAM-IO rewrite | `011335e4` / `34604` | None |

JUNO-X therefore provides another byte-identical code comparison in those bounded
windows. This does not establish its external service peer, factory activation,
whole-function equivalence or compatibility with a Fantom hardware probe.
AX-Edge's lack of these exact windows means its bytes differ; it does not show
that the corresponding features are absent. No speculative replacement addresses
or AX-Edge opcode semantics are admitted.

## CORE0 and bounded key-material scan

Both C0A images have the already observed `b6020001` crypto control. Payload blocks
are counted only inside the validated declared payload, deduplicated and compared
as aligned eight-byte values, excluding all-zero/all-FF blocks. Headers and trailers
are excluded. The reference Fantom bmc0 image is pinned independently.

| Image | Declared encrypted payload bytes | Distinct nontrivial blocks shared with Fantom bmc0 |
|---|---:|---:|
| AX-Edge | 1,454,240 | 13,659 |
| JUNO-X | 7,991,072 | 15,780 |

These overlaps extend the [earlier six-image comparison](core0-ciphertext-and-key-location.md).
They support testing applicable recovered key material across the images, but they
are not a key, proof of identical mask ROM or a decryption result.

The existing bounded [material scanner](embedded-rom-key-material-scan.md) ran on
all ten complete tar members, including AX-Edge's wave object and JUNO-X's SUB
image. No reported MC-101 ROM identity/vector-prefix candidate was found, and no
literal reference to the reported key-table base `012023b0` or selected B6 entry
`012034c0` appeared. Raw occurrences of `01200000` do appear and are not treated
as ROM ownership or a key. The crypto-control value occurs in the C0A headers.
No key bytes are emitted by the report.

This negative scan covers the two conflicting reported ROM identities and known
vector/address anchors in the inspected bytes. Unknown ROM revisions, other
compression, transformed/derived constants and unrecognized embedded formats remain
outside that boundary. No new compression algorithm or arbitrary code was run.
Readable CORE0 runtime/ROM and a proven BMC-side access route remain missing.

## Reproduce

With the two official update tars retained under ignored
`local/crossmodel/ax-edge` and `local/crossmodel/juno-x`, plus the existing pinned
Fantom inputs:

```sh
python3 tools/edge_juno_firmware_study.py --out local/edge-juno-firmware-study.json
python3 -m unittest discover -s tests -p test_edge_juno_firmware_study.py -v
```

The four tests cover archive trust boundaries and the actual pinned comparisons.
The corpus-dependent test skips explicitly in a clean checkout without artifacts;
the three synthetic archive tests need only Python's standard library.
