# Official Fantom-0 build check and fresh archive provenance

2026-11-10. A fresh official download supplies **the same v1.08 bytes already
analyzed**, not another factory-test build. The current
[Roland Fantom-07 update page](https://www.roland.com/global/support/by_product/fantom-07/updates_drivers/a0df616e-3d37-41d2-9464-d04a43c53193/)
lists the shared FANTOM-06/07/08 package as version 1.08, dated July 2026. Its raw
HTML download handler links directly to
[fantom060708_sys_v108.zip](https://static.roland.com/assets/media/zip/fantom060708_sys_v108.zip).
The page and archive both returned HTTP 200 during this pass.

This closes the provenance gap between the retained app binaries and the current
manufacturer download. It does not change the unresolved
[factory mode-3 gate](factory-gate-and-ui-dispatch-study.md) or establish Linux
recovery access. No target binary, updater or script was executed, and no device
was opened or flashed. Only official Roland domains were used for source discovery
and retrieval; no software was installed.

## Download identity and exact archive boundary

The downloaded ZIP is 274624040 bytes, SHA-256
`2edf37f2543ece10319079a8626edce93d6062511143a959ff3a961dbfdff939`.
That matches the retained `sys_v108.zip` used by the earlier studies. One archive
was downloaded, subject to a 600000000-byte limit; no other version was downloaded.

The ZIP has four entries: one directory and these three regular files. Paths and
entry types were inspected before selected extraction; hashes were calculated by
reading the actual members, including ZIP CRC verification by the standard reader.

| Member | Bytes | SHA-256 |
|---|---:|---|
| `FNTM0_UPA.BIN` | 22200320 | `44993228fc0b407a6b198d8ef3da953f861393d929f47cce08ce1a79fc108f75` |
| `update_fntm0` | 1607 | `ef69453ca9dfa7af7cff043e43bcbc5598fc07fe4e445e55e13e03d812103013` |
| `_DATA_FNTM0` | 385464320 | `cfbf9bf1134746096ba26561e2d0f32528b251f9b59ae5e574523fcdfd11643a` |

`FNTM0_UPA.BIN` is directly readable as a tar archive containing exactly six
regular members: bmc0 and bmc1 versions of `MI078_C0A_up.bin`,
`MI078_C1A_up.bin` and `MI078_C1C_up.bin`. There is no separately named Linux
rootfs, recovery image, bootloader or Linux update consumer in that tar.

`_DATA_FNTM0` is a tar with 440 entries: 346 regular files and 94 directories.
Every entry passed the path/type inventory; no symlinks or special files were
accepted. Its app components match the retained analysis inputs:

| Nested member | Bytes | SHA-256 |
|---|---:|---|
| `_DATA/qctest` | 304912 | `d87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6` |
| `_DATA/mi078` | 61181491 | `90515931ab039e926fea9cd1b237e341d4097002dcb119674eed7df00f3d9bb7` |
| `_DATA/go.sh` | 1547 | `e51155f468927d69792cd9612d8bc676f8b2ee41901d769112c134c83b126964` |
| `_DATA/fsl-imx8mm-mi078.dtb` | 40714 | `ffe1b637abf981b1e0adae2684b25cd47f952925e14b66a2e5a35ccaf725904a` |

The remaining tree is application utilities/assets, factory sound/sequence content
and the resource directory below. No installed `/etc` tree, `net.sh`, `tsd`,
login configuration or Linux recovery executable was added in this download.
That is a member-inventory result, not a claim about the instrument's installed
filesystem or the contents of every opaque/encrypted byte range. The encrypted
`update_fntm0` is unchanged; no readable replacement consumer was found.

`_DATA/bin/fact.sh` is a 372-byte factory-content script. Its text removes and
recreates user rhythm/sequence directories and copies factory sequence/backup
content under `/home/ROLAND/FANTOM`; it is not a Linux rootfs restore script.
It was read, never run.

## QSPIImage is the previously identified resource superset

The nested `_DATA/bin/QSPIImage.BIN` is 8388608 bytes, SHA-256
`318d26901fe05e0a7148941ceca65817553121c608a8b8f2db01d23d68feec96`.
The original `BMC DSP ISA.md` note already identified it as the 37-record master
resource directory. A fresh structural comparison corroborates that identification:

* Its raw header is `QSPI`, followed by u32 values `(32,32,37)`.
* The fresh bmc1 C1C component has `(32,32,29)` after its 32-byte update wrapper.
* All 29 shared stored-name records have byte-identical payload SHA-256 values.
* Eight extra stored-name prefixes cover the documented PCM-EX/SNAC tone and
  instrument/kit resources.

The comparison reads 32-byte directory records and their bounded payload ranges.
It does not treat this as a new Linux image or run any resource loader. The existing
`qspi_c1.py` parser is specifically for two-member C1A containers; its constraints
must not be silently generalized to accept this raw 37-record resource image.

## Older official links were stale, not a retrieved alternate build

A targeted official-domain search for the v1.07/v1.06 package and older update
pages found cached v1.07 results with page identifier
`98537fa5-85bf-4a85-8e70-066ceca8cc97`. The specific
[Latin America detail URL](https://www.roland.com/latinamerica/support/by_product/fantom-08/updates_drivers/98537fa5-85bf-4a85-8e70-066ceca8cc97/)
and [French Canada detail URL](https://www.roland.com/fr-ca/support/by_product/fantom-08/updates_drivers/98537fa5-85bf-4a85-8e70-066ceca8cc97/)
each returned HTTP 302 to a regional not-found route, then HTTP 404. Their old
search text is not evidence of a currently downloadable archive.

The [Dutch Fantom-06 index](https://www.roland.com/nl/support/by_product/fantom-06/updates_drivers/)
also appeared as v1.07 in a cached web view, but its freshly retrieved HTTP-200
HTML links to **v1.08**, using the same current page identifier as above. Current
global Fantom-06/08 index views likewise name the common v1.08 package.
No older archive URL was recovered from the checked live pages, and no archive
filename/URL was guessed. This bounded pass therefore has no alternate `qctest`
to compare. It does not prove that all historic official packages have disappeared
or that no unpublished/service build exists.

## Retained evidence and verification

Originals and detailed evidence remain ignored under
`local/crossmodel/fantom-0/` in the main project checkout:

* `fantom060708_sys_v108.zip`: unchanged fresh manufacturer download.
* `download-manifest.json`: source URLs, HTTP status chains, response-capture
  hashes, size limit and selected-extraction record.
* `v108-inventory.json`: all ZIP/tar members and regular-member hashes, including
  the six UPA members.
* `qspi-resource-directory.json`: both resource inventories and payload hashes.
* `support-20261110/`: original HTML/HTTP captures and concise evidence notes.
* `v108-selected/qctest` and `QSPIImage.BIN`: selected bytes copied after inventory.

Both existing qctest studies were tested against the **freshly extracted** qctest
using Python 3.13.7, Capstone 5.0.7 and pyelftools 0.33. All four tests passed,
without skips. The same shell endpoint, mode initial −1, direct setter values
0/1/2 and introductory-page/group structure remain in force. No new reusable parser
or dependency was needed for this provenance-only pass.

The remaining access gap is unchanged: a proven mode-3 activation edge or readable
installed recovery/rootfs/update-consumer evidence. The public current package does
not supply a new build that resolves it.
