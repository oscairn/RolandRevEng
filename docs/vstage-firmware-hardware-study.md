# V-STAGE firmware: five named BMC targets

2026-11-11. Read-only analysis of Roland's official V-STAGE System Program 1.11.
This advances the earlier [stage-keyboard screening](stage-keyboard-oscairn-targets.md):
BMC-family update targets are now directly evidenced, while the UI/host processor
and physical chip count remain unverified. No firmware, updater or device code
was executed.

The [CORE1 and DSP comparison](#core1-and-candidate-dsp-comparison-2026-11-11)
now finds exact Fantom service windows, shared candidate DSP segments and a
relocated FDRV post-cubic body in V-STAGE. It also records unseen packet contexts
without assigning new opcode meanings.

The [caller/ownership study](#shared-program-callers-and-ownership-2026-11-11)
now links the matching FDRV list to a RTTI-backed class callback and separates
diagnostic/test reuse from larger bootstrap-list references.

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

## CORE1 and candidate DSP comparison (2026-11-11)

`tools/vstage_core1_comparison.py` compares one representative from each pinned
group (0, 1/2, 3/4) with the Fantom CORE1 payload
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
The update identity remains the 1.11 UPA hash above. No vendor code is executed.

### Exact service windows

Each search stays within a single mapped ITCM or ERAM region. The pattern hashes
and every hit's C1A source offset are retained in the local report. C1A offsets
include the 32-byte prefix and are distinct from outer-tar offsets.

| Fantom window | Bytes | V-STAGE bmc0 runtime / C1A offset | bmc1/2 runtime / C1A offset | bmc3/4 |
|---|---:|---|---|---|
| MMIO-read prefix at `6102d2e6` | 324 | `61030172` / `70172` | `61037bce` / `77bce` | No exact hit |
| RAMCLR body at `61056b14` | 158 | No exact hit | No exact hit | No exact hit |
| DRAM-IO low23 rewrite at `0113383c` | 14 | `0113470c` / `3472c` | `01133cc4` / `33ce4` | No exact hit |

These are four byte-identical bounded windows. They do not prove whole-function
equality, common external message routing or loading compatibility. A negative
exact search does not establish that an equivalent service is absent.

### Candidate DSP programs and unseen contexts

The existing `core_lists()` scanner is a structural heuristic. Segments are
deduplicated by source offset/length, zero-length candidates are excluded, reads
must stay within one mapping, and only successfully framed/roundtripped logical
streams enter the hash/context comparisons. No class or caller ownership is
inferred from a successful frame.

| Image | Candidate lists | Unique nonempty segments | Framed / failures | Distinct framed contents | Whole-content hashes shared with Fantom | Contexts absent from Fantom baseline |
|---|---:|---:|---|---:|---:|---:|
| Fantom baseline | 103 | 377 | 377 / 0 | 353 | — | — |
| V-STAGE bmc0 | 116 | 619 | 619 / 0 | 572 | 5 | 1,221 |
| V-STAGE bmc1/2 | 93 | 579 | 578 / 1 | 560 | 3 | 1,336 |
| V-STAGE bmc3/4 | 73 | 81 | 81 / 0 | 75 | 1 | 1,904 |

The five shared bmc0 contents have lengths **6, 198, 806, 11,572 and 51,542
bytes**. Bmc1/2 share the 6-, 198- and 11,572-byte contents; bmc3/4 share only the
6-byte content in this scan. The two large bmc0 matches frame as 845 and 6,790
packets. These are meaningful reuse leads, while the six-byte match alone is
weak evidence. Actual engine/kernel ownership remains unproved.

The baseline has 5,089 distinct context keys. A key retains header, ordered base
controls, classified long extensions and transfer tags, while excluding numeric
literal values and resource indices. Unsupported layouts are explicitly grouped
as unclassified header/base-control tuples. Thus the unseen counts are encoding
contexts relative to this one Fantom payload, **not counts of new instructions**
or proof that other Roland/native corpora lack them. For example, bmc0 contains
an unseen `0803` / `080b` / long-extension `42c0` context; its meaning is not
admitted by the interpreter. The report retains source/packet offsets and eight
examples per group for later provenance work.

The bmc1/2 failure is a 68-byte structural candidate at payload offset `ff318`,
starting with unsupported header `0000`. Its hash is excluded from the content
and context totals. It is not a new opcode discovery or proof of bad firmware.

### A relocated FDRV match and worker corrections

The comparison uses all five actual Fantom post-cubic bodies at `3ec..446`,
including their real resource/coefficient relocations. Each 90-byte pattern has
a positive packet-boundary witness in the Fantom baseline. The pattern from
Fantom segment base **8040** has one exact packet-boundary match in the bmc1/2
candidate inventory. The other four patterns have no exact V-STAGE hit here.
This establishes one shared body, without identifying the V-STAGE candidate's
owner or proving the entire FDRV program is equivalent.

Qwen's 110-second offline pass produced three scripts and JSON findings, but no
final narrative before its limit. Its initial optional search used unrelocated
and partly raw-storage bytes and missed the match. It also included a failed
candidate's hash in one distinct-content count. Those results were corrected by
an independent compact comparator using the repository's tested mapping/scanner
helpers. The independent report also distinguishes region offsets from original
C1A file offsets. No worker script was adopted directly.

Four new tests check context invariance under numeric/resource substitutions,
sensitivity to long extensions/tags, both ends of packet-boundary matches, all
pinned corpus counts and exact hit bytes/source offsets. They also check the
five Fantom positive controls, the real V-STAGE match and altered-input rejection.
The structural scanner imports native-image helpers only when needed, so this
comparison requires the two firmware inputs but no ZENOLOGY image.

```sh
python3.13 tools/vstage_core1_comparison.py local/vstage-worker/VSTAGE_UPA.BIN local/b0c1a.bin --out local/vstage-core1-comparison.json
python3.13 -m unittest discover -s tests -p 'test_vstage_core1_comparison.py' -v
```

Next useful work is caller/class ownership for the shared DSP contents, and
independent semantic evidence for selected unseen contexts. Exact host CPU,
physical package count, available capacity and safe device loading remain open.


## Shared program callers and ownership (2026-11-11)

`tools/vstage_program_ownership.py` extends the pinned comparison into descriptor
and caller provenance. It checks actual list/table rows, full framed-segment
hashes, mapped source offsets, PC-relative literal loads and bounded Thumb
instruction shapes. Both ITCM and ERAM code are considered. V-STAGE bmc1 and
bmc2 have identical images, so their shared representative is sufficient here.

### FDRV class callback and dispatch

| Evidence | Fantom | V-STAGE bmc1/2 |
|---|---|---|
| Containing program list | `610e5a94` | `611008a8` |
| List DSP / row index | 1 / 1 | 4 / 0 |
| Render base / length / capacity | `8040` / 1420 / 4096 | `7000` / 1420 / 1792 |
| Source runtime | `610e6440` | `61100cc8` |
| List-pointer literal pool | `6104a248` | `610542ec` |
| Literal load / indirect call | `61049e72` / `61049e74` | `61053f26` / `61053f28` |
| Callback entry | `61049e68` | `61053f1c` |
| RTTI typeinfo | `61171a58` | `611c75a0` |
| Vtable address point | `61176adc` | `611cc3ec` |

The exact RTTI name `11CFspMfxFDRV` links through typeinfo/vtable records to
callback slot +8. Its checked prologue obtains the object at +4, reads that
object's vtable slot **+28**, loads the program-list pointer into **r1**, then
calls through r2. This is direct static caller evidence for the list containing
the previously verified 90-byte relocated body, beyond a numeric/string match.
The indirect target still depends on runtime object identity; no loader is run.
The two complete 1,420-byte contents have different hashes, so this does not
assert complete program identity or host/loading compatibility.

### Large shared programs have different roles

| Shared bytes | Fantom list / DSP | V-STAGE bmc0 list / DSP | V-STAGE bmc1/2 list / DSP |
|---|---|---|---|
| 11,572 | `610c59c8` / 4 | `610ed280` / 4 | `610d4458` / 5 |
| 51,542 | `61085de4` / 6 | `610982f4` / 6 | No match in the comparison |

The 11,572-byte list is passed through object vtable slot **+18**. Loads/calls
are Fantom `6103f4f0/6103f4f2`, bmc0 `61044b20/61044b22`, and bmc1/2
`61049844/61049846`. Nearby checked literal readers reference the assertion
`CFspDspTest::EResult CFspDspTest::TestEram()`. The method name is inferred from
that assertion and the nearby dispatch, rather than recovered from a symbol
table. This is diagnostic/test-associated reuse, not evidence for an additional
unidentified synthesizer engine.

The 51,542-byte list has two checked references in both images. Fantom
`610010f6` and V-STAGE bmc0 `61001926` load it into r1 on a selected-list path
that subsequently calls object slot +18. A separate reader at `61001178` /
`610019a8` loads the list into r6, reads count at +2 and table at +4, and walks
16-byte segment records. These establish actual code use of the structural
list. Exact class/function ownership and the interpretation of its DSP6 code
remain unresolved; bootstrap/list-selection context alone does not name it.

Qwen's 230.2-second pass produced local intermediate scripts and records but
left its report at the initial status. Its list/row and pointer locations were
checked independently. The worker's ITCM-only literal scan missed the ERAM
callers, and some listings decoded literal pools as if they were code. None of
those listings establishes ownership. The committed tool instead requires the
RTTI chain/exact FDRV caller shape, exact diagnostic dispatch shape and explicit
large-list row-reader instructions. No worker script or vendor listing is
committed. Three tests cover narrow/wide/negative Thumb literal references,
changed-target/shape rejection, the pinned real caller chains and altered-input
rejection.

```sh
python3.13 tools/vstage_program_ownership.py local/vstage-worker/VSTAGE_UPA.BIN local/b0c1a.bin --out local/vstage-program-ownership.json
python3.13 -m unittest discover -s tests -p 'test_vstage_program_ownership.py' -v
```

Next trace the runtime dispatch target/object and the remaining large program's
owner before transferring loading rules or engine-capacity assumptions. Physical
package count, UI host, device execution and new ISA meanings remain unverified.
