# V-STAGE firmware: five named BMC targets

2026-11-11. Read-only analysis of Roland's official V-STAGE System Program 1.11.
This advances the earlier [stage-keyboard screening](stage-keyboard-oscairn-targets.md):
BMC-family update targets are now directly evidenced, while the UI/host processor
and physical chip count remain unverified. No firmware, updater or device code
was executed.

## Source and identity

- [Official update page](https://www.roland.com/global/support/by_product/v-stage_88/updates_drivers/d33f4b4f-4ca5-4a6a-9703-8fb3ef3a3354/).
- [Official ZIP](https://static.roland.com/assets/media/zip/vstage_sys_v111.zip),
  13,066,431 bytes, SHA-256
  `8e883fa00fd083926716d2fd0f0cac6744eebda7f50fb905dc04ca4844ae6572`.
- Its sole ZIP member, `VSTAGE_UPA.BIN`, is a 52,008,960-byte tar archive,
  SHA-256 `145262c536dec1928c4652bec6c5c84318374445219832c34e864760377644a8`.

Qwen located the public download, retained the ZIP/payload and made preliminary
string observations, but reached its 90-second limit with only an interim report.
Its raw string dump is not accepted as hardware identification. An independent
HTTP retrieval verified the same archive hash and its link on the official page.
The page, HTTP metadata and read-only inventory report are retained locally.
Some search-cached product pages still listed 1.10; the directly retrieved update
page linked the inspected 1.11 ZIP. This is the inspected release, not a promise
about later availability.

## Direct archive observations

There are exactly **15 regular components**: for each target `bmc0` through
`bmc4`, one `MI087_C0A`, one `MI087_C1A` and one `MI087_C1C` update. Their footers
identify MI087 version 1.11, build 0098. Names and independently computed hashes
establish five named BMC firmware targets, without relying on synthesis brands
or the earlier forum claim.

| Targets | C0A bytes | C1A bytes | C1C bytes | Sharing |
|---|---:|---:|---:|---|
| bmc0 | 5,218,400 | 3,108,960 | 8,388,704 | Distinct |
| bmc1, bmc2 | 1,161,232 each | 2,431,040 each | 8,388,448 each | All three components match byte for byte within the pair |
| bmc3, bmc4 | 848,976 each | 1,660,704 each | 3,145,824 each | All three components match byte for byte within the pair |

There are therefore three distinct code/content groups: **0; 1/2; 3/4**. The
duplication does not establish which group runs which engine, how work is shared,
or how much processing capacity is available for custom code.

The existing CORE1 mapper accepts all three distinct C1A groups: 32-byte prefixes,
Thumb reset entries, the familiar address/scatter-loader structure, and an ERAM
analysis offset of `3ffe0`. Scatter record counts are 10, 12 and 8 respectively.
Readable initialization symbols also refer to BMC setup and peripheral services.
This supports reuse of some analysis tools and the BMC-family interpretation.
It does **not** identify an exact CPU part, prove every ISA encoding is compatible,
or validate a Fantom host protocol on V-STAGE.

C0A components have the recognized `App1_Main` encrypted-payload header. Their
control field is `b6020001`: enabled byte 1, mode field 2, key index `b6`.
That index is not a recovered encryption key. No decryption was attempted, and
the opaque CORE0 contents cannot be used to infer the host OS or UI processor.

## Hardware evidence and limits

Roland's own [engineering interview](https://articles.roland.com/roland-engineering-v-stage/)
discusses an increase in CPU/DSP systems during development and supplies an
internal photograph. It does not name processors or give a numerical chip count.
The retrieved 1024×768 photo has obscured/unreadable chip markings and does not
independently establish the five-chip claim.

The correct current conclusion is **five named BMC update targets**, consistent
with a five-instance design. A physical five-package count is still an inference.
The archive contains no separately named host/Linux image, which establishes
neither that no other processor exists nor that no host payload is embedded in
an opaque component. In particular, it does not establish an i.MX8 host or a
Linux environment capable of running Oscairn. This is the main remaining platform
question before ranking V-STAGE as a whole-host port target.

## Reproduction and next evidence

`tools/vstage_firmware_study.py` hashes before parsing, reuses the bounded regular
member reader, checks the exact 15-member set, footers and sharing groups, then
uses temporary nonflashable files solely for the existing CORE1 mapper. It never
extracts archive paths to the filesystem. Reports contain identities/metadata,
not firmware bytes. Three tests cover the real pinned archive, digest rejection
before archive parsing, missing components and changed identification footers.

```sh
python3.13 tools/vstage_firmware_study.py local/vstage-worker/VSTAGE_UPA.BIN --out local/vstage-study.json
python3.13 -m unittest discover -s tests -p 'test_vstage_firmware_study.py' -v
```

Next useful evidence is readable exact-revision processor markings or service/GPL
documentation identifying the UI/host, followed by static comparison of relevant
CORE1 services/DSP programs against Fantom. Loading, boot/recovery, allocation,
audio routing and hardware numeric behavior remain separate requirements. All
vendor archives and photographs stay in ignored local storage.
