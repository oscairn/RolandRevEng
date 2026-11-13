# LINE prefix count-1 literal writers and the JUPITER-X asymmetric 4822/1940

2026-11-13. This study extends the [count>=2 static group scan](line-prefix-global-groups.md)
down to count-1 descriptors and follows their code references. It binds the two
prefix fields without a native constructor representative — relative `17` and
relative `27` of program base `4020` — to one stock straight-line writer that
stores the same computed double into both. It also re-encodes the asymmetric
JUPITER-X `4822 / 1940` instance as static descriptor facts. **No new opcode,
grouped-write rule or interpreter admission follows.** Ownership of the writer
method, runtime-built descriptors and other builds remain outside the inventory.

## Why this targets the standing gap

The [scoped parameter study](line-prefix-parameter-study.md) proved native
constructor representatives for prefix fields `14` (record `+50`, double `+58`)
and `24` (record `+70`, double `+78`) and found no record for `17` or `27`.
The [global-group scan](line-prefix-global-groups.md) found no count>=2 descriptor
containing `14/17` or `24/27` in either pinned image, leaving the tied-versus-split
input-mix question open. This pass asks the complementary count-1 question:
**who writes fields 17 and 27 at all, and do they ever receive different values?**

Method: `tools/line_prefix_single_writer.py` reuses the observed descriptor ABI
(pointer at `2*pointer_size`, count byte at `3*pointer_size`, contiguous 12-byte
records with width byte 2/3/4) with `min_count=1`, then resolves every ADRP-page
reference to each record symbol through checked straight-line windows. Artifacts
and digests are unchanged:

* Native ZENOLOGY arm64: `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
* Fantom CORE1 payload: `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
* JUPITER-X C1A container: `9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`.

## ZENOLOGY count-1 inventory is complete for the prefix fields

Thirteen aligned descriptors mention relative fields `14/17/24/27`; every count-1
member parses through the existing narrow `descriptor()` reader. All thirteen:

| Symbol | Count | Records (absolute / relative / width) | Referencing instruction |
|---|---:|---|---|
| `9d4e30` | 1 | `9024 / 24 / 3` | `7f9b4`, `7fc18` |
| `9ff988` | 2 | `4044 / 24 / 4`, `4048 / 28 / 4` | `120154` |
| `a1f7b0` | 1 | `4037 / 17 / 3` | `1d1b3c` |
| `a1f7d0` | 1 | `4047 / 27 / 3` | `1d1b58` |
| `a2e778` | 1 | `9024 / 24 / 4` | `21440c` |
| `a3f560` | 1 | `4034 / 14 / 3` | `29a9dc` |
| `a3f580` | 1 | `4037 / 17 / 3` | `29a9fc`, `29aa58` |
| `a519f0` | 2 | `4044 / 24 / 4`, `4048 / 28 / 4` | `334314` |
| `a51e08` | 1 | `4034 / 14 / 3` | `334d84` |
| `a51e28` | 1 | `4037 / 17 / 3` | `334da0` |
| `a52c30` | 1 | `4034 / 14 / 4` | `349a1c` |
| `a54ee8` | 1 | `9024 / 24 / 3` | `3546b8`, `35485c` |
| `a70a28` | 1 | `4034 / 14 / 4` | `3b1724` |

`4037 - 17 = 4034 - 14 = 4044 - 24 = 4048 - 28 = 4020`, so all `40xx` records
target the LINE program base; `9024 - 24 = 9000` names a second program. **No
count>=2 group contains `14/17` or `24/27`, and no count-1 record for relative
`27` exists except `a1f7d0`.** The only static references to `a1f7b0`/`a1f7d0`
are at `1d1b3c`/`1d1b58`, both inside the method `1d1ac8..1d1b70`. The reference
scan covers every function under 60000 bytes plus the two larger functions
(`589000..5af838`, `6b74ec..6d5138`) scanned separately; it requires the ADD/LDR
resolving the ADRP page with the same register and no intervening clobber or
branch, so adrp-only or GOT-indirect references are not excluded.

## One writer stores the same computed double into relative 17 and 27

`tools/line_prefix_single_writer.py` checks the 42-instruction method at
`1d1ac8..1d1b70` instruction by instruction:

1. Clamps the `w1` argument to `0..127` (`csel lo` / `csel gt`).
2. Loads `table[clamp]` from `81b678` and an int32 `44100` from `b78af0`
   (`scvtf` converts it to double).
3. Computes `table[clamp] * 44100.0 / 32000.0 * 0.25`. The divisor is the
   64-bit immediate built by `mov x8, #0x400000000000` + `movk x8, #0x40df, lsl 48`
   (`40df400000000000` = `32000.0`); the post-scale `0.25` is a `fmov` immediate.
4. Calls the checked generic literal driver twice through the member object at
   `+8`, its vtable slot `c8` (`fba10`, the same slot the manager vtable exposes,
   per the [scoped study](line-prefix-parameter-study.md)), first with descriptor
   `a1f7b0` (relative `17`) and then `a1f7d0` (relative `27`).
5. Both calls pass the same `d8` (`fmov d0, d8` at `1d1b40` and `1d1b5c`). The
   driver preserves `d8` (callee-saved: `stp d9, d8, [sp, #-0x20]!` /
   `ldp d9, d8, [sp], #0x20` at `fba10/fba78`), so both fields receive one value.
6. There is no branch between the two writes.

The lookup table's 128 doubles span `0.0`..`0.775390625`, all finite. A sibling
method `334d40..334db8` has the same shape with table `818d20` (span
`0.0..0.9998779296875`) and writes the count-1 records `a51e08`/`a51e28`
(relative `14` and `17`) with the same computed double. A third method
`29a9b8..29aafc` writes four count-1 records of the same program with constants
selected by a halfword member test: when nonzero, fields `14` (`a3f560`), `17`
(`a3f580`), `2e` (`a3f5a0`) and `31` (`a3f5c0`) receive `1.0`, `0.0`, `0.0`,
`1.0`; when zero, all four receive `0.5`. So the `14/17` sibling writers
demonstrate both equal-computed and constant-different relations; field `14` and
field `17` are not uniformly tied by these writers.

The tool pins the writer constants (`44100`, `32000.0`, `0.25`, table bounds) so
any rebuild drift fails closed. **The method's owning class is unresolved**: the
vtable slot containing `1d1ac8` sits in `a1f4f0`-based storage (slot 6), the
constructor storing that vtable is the five-instruction `1d14e0`, and neither has
a direct BL caller or export in the prepared image. The known JUPITER-X/SH-4d
comparison point predicts `0.25` in the following store for literals `(0.25,
-0.125)`; this writer computes from a 128-entry table instead, which is a
different parameter source and does not confirm or refute that prediction.

## What this establishes for the tied-versus-split question

Established (checked by the tool against the pinned image):

* Fields `17` and `27` of program `4020` are each declared exactly once (count 1)
  and both are written by one branch-free method with one computed double.
* Within this image there is no static descriptor group or second writer that
  could give them different values. Any tied/split distinction the hardware
  makes between the two fields therefore has no observed stock driver.
* Fields `14` and `17` have two same-shaped sibling writers (`334d40` with equal
  computed values, `29a9c8` with different constants), so field `14` and field
  `17` are demonstrably not uniformly tied by these writers.

Not established:

* That `1d1ac8` executes on the stock LINE parameter path (class ownership,
  callers and construction are unresolved); that no runtime-built descriptors or
  raw writes exist; other builds.
* How the DSP itself treats the four fields; the LINE native window reads only
  the two constructor representatives (`+58`, `+78`) per the prior study, which
  remains consistent with a tied model but does not prove it.
* Any new interpreter admission; the strict profile set is unchanged.

## JUPITER-X asymmetric instance: static facts only

`tools/line_prefix_single_writer.py --jupiter-c1a ...` re-encodes the [known
asymmetric instance](emulator-next-program-targets.md#jupiter-x-carries-an-asymmetric-instance-of-4822--1940)
at list `61218324` (segment bases `2020`/`7020`, unequal literals `(1, 0)`):

* Eight aligned ARM32 descriptors mention relative `d0`/`d3`; **all eight have
  count 1**; there is no count>=2 group containing both fields.
* The two sites adjacent to the list descriptor — `61218334` (record
  `20f0 / d0 / 3`, first word `3f800000` = `1.0`) and `61218364` (record
  `20f3 / d3 / 3`, first word `0`) — are the two unequal fields. `20f0 -
  0xd0 = 0x2020` and `20f3 - 0xd3 = 0x2020`, so both target segment base
  `2020`. The unequal stored literals are therefore also separate count-1
  declarations, not members of a declared group.
* The sibling base `7020` copies (`611660dc`/`611660ec`, records `20f0`/`20f3`)
  and a width-4 `d0` record at `611bf6f0` exist; none is a group.

This gives the asymmetric instance the same static shape as LINE's equal-literal
prefix: independent count-1 fields. The distinction between the two hypotheses
therefore cannot be resolved by descriptor shape in either program; it needs a
capture of the JUPITER-X store or an ownership proof. No DSP trace, native
cutpoint or hardware observation was made.

## Reproduce

```sh
python tools/line_prefix_single_writer.py local/zen_arm64 \
  --jupiter-c1a local/crossmodel/jupiter-x/MI077_C1A_up.bin
python -m unittest discover -s tests -p test_line_prefix_single_writer.py -v
```

Corpus paths follow `BMC_CORPUS_DIR`. The corpus-free tests construct fixtures
for the inventory/reference logic; the corpus tests pin the thirteen native
mentions, the reference sets, the writer shape and the eight JUPITER-X sites.