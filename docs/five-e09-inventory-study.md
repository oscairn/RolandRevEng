# The unresolved 5e09 group: cross-image inventory and the GASS-type 5d52 invariant

2026-11-13. This study resolves the standing unknown from the
[negative-bias work](negative-short-add-study.md): four 5d52 uses under the
unresolved header `5e09`. It enumerates every `5e09` packet across all six
prepared images, classifies the four observed control shapes, and proves
structural invariants per shape. **No opcode, family or interpreter admission
follows**: `5e09` stays outside `header_study.families()`, `5d52` keeps no
global short-add syntax, and the fitted four-operation rule of the
[cross-check study](header-family-crosscheck-study.md) is neither confirmed nor
refuted by these packets.

## What was examined and how

All checks are static. `tools/five_e09_inventory.py` frames every render-list
segment of the pinned ZENOLOGY arm64 image, the two Fantom CORE1 payloads and the
three cross-model QSPI containers with the existing `analyze.core_lists()` /
`qspi_c1.read_c1()` machinery, decodes each segment with the strict
`bmc_dsp.packets()` subset parser, and records every packet whose header is
`5e09`. Any `5e09` packet whose controls are not one of the shapes below is
fatal, because the tool claims complete inventory coverage. Artifacts are
unchanged: desktop SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`, Fantom
CORE1 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`,
JUPITER-X `9368ef3243567cbd639dc990c0bb8ca6d2ee817da2fd8412597ae77d6f0b567b`.

## The complete inventory

Across 2,535 strictly framed segments (a further 135 are counted unframeable,
not fatal) the tool finds exactly 117 `5e09` packets in four
control shapes and no others:

| Image | 5e09 packets | GASS-type `1e50/5d52/4014/0fe6` | SBF325-type | STTMDLY-type | dsp6 diagnostic |
|---|---:|---:|---:|---:|---:|
| ZENOLOGY arm64 | 8 | 2 | 4 | 2 | 0 |
| b0c1a.bin | 17 | 4 | 8 | 4 | 1 |
| b1c1a.bin | 1 | 0 | 0 | 0 | 1 |
| JUPITER-X MI077 | 45 | 11 | 22 | 11 | 1 |
| MC-101 RPG69 | 1 | 0 | 0 | 0 | 1 |
| SH-4d DD013 | 45 | 11 | 22 | 11 | 1 |

Every `5e09` packet has `command_count == 4`, confirming the count formula's
`bit_length(H >> 11)` reading for this header. `families(0x5e09)` still fails
closed: the high byte `0x5e` is outside the implemented four-operation anchor
table and outside every implemented prefix form.

## The four shapes

1. **GASS-type** `5e09 1e50 5d52 4014 0fe6 | 3c00 a400 <r1> <r2>` — the
   negative-bias study's unknown group. The first two payload words decode,
   under the ordinary short-reference syntax, to exactly the admitted
   negative-bias chain constants: `3c00` = `1.75` (the `1e50` reference) and
   `a400` = `-0.25` (the `5d52` reference). The admitted GASSPH/GASSDLY/GAMPSIM
   neighborhoods use the same controls in the admitted `2e07` context with the
   same two constants; here the third control `4014` replaces `3fe4` and the
   transfer is `0fe6` instead of `3fe4`. The two tail words `r1`/`r2` are
   resource words, not literals: they vary across relocated copies of the same
   program (26 distinct ordered pairs over 28 observations) while `3c00/a400`
   stay constant. `0fe6` selects payload offset 6 (`r2`); no known-syntax
   control consumes offset 4 (`r1`), consistent with the fitted rule's
   `(1,1,3,4)` prediction for `0x5e`, whose kind-3 operand syntax is unknown.
   The fitted `(1,1,1,4)` alternative is excluded by the fitted constraint
   itself, not by independent evidence.
2. **SBF325-type** `5e09 2c80 edf4 4010 0fe2 | 0002 <r1> <r2> <r3>` — the
   desktop render stream of `SIM_MFX_SBF325` (list `0xa3f080`, native class
   `CFspMfxSBF325`) carries this shape twice; the Fantom/JUPITER-X/SH-4d
   images carry 22/22/8 more copies across relocations. The `0fe2` transfer
   selects payload offset 2, the same bytes the desktop copies' resource word
   occupies; offset 6 stays constant within one image (`0040`/`2dc0`) while
   offsets 0/2/4 vary.
3. **STTMDLY-type** `5e09 0cc8 5074 4010 8fe2 | 0002 <r1> 6879 e080` — the
   desktop render stream of `SIM_MFX_STTMDLY` (list `0xa20200`, native class
   `CFspMfxSTTMDLY`) carries this shape twice; the other images carry 26 more.
   `8fe2` is the established main-A store form; the transfer store selects
   payload offset 2, again a varying resource word, while offset 6 (`e080`) is
   constant and offsets 0/4 vary per placement.
4. **dsp6 diagnostic** `5e09 4050 1052 0094 0fe6 | 0004 d000 002d e000` — one
   packet per image at a large offset (at least `0x1324`) in the shared `0x0`
   diagnostic segment, including one in the `b1c1a.bin` and MC-101 images,
   where no other `5e09` occurs. Its third control is `0094`, one of the
   five known special-short words
   ([header fields study](header-fields-study.md)) that appear without the
   predicted payload literal; its payload words are constant across images.

## The GASS-type invariant, proved

For every GASS-type `5e09` packet in every image, the tool checks:

* gain literal `3c00` decodes to `1.75` and bias literal `a400` to `-0.25`;
* exactly two resource offsets `[4, 6]`, both even and inside the payload;
* the resource pairs are distinct across relocated copies (26 pairs over 28
  packets), so the two words are placement-dependent, not fixed constants.

This upgrades the negative-bias study's finding: the `-0.25` short-literal use
under `5e09` is not a fourth isolated observation but one of 28 structurally
identical uses across four independent images. The desktop GASS-type anchor
is the unpaired render list `0xa41220` (segment program base `0x4020`, length
`0x5ec`, stored source offset `0x817988`; its own second copy at base `0x8000`,
source `0x817f74` carries resource words `01d0` instead of `0040`, so the two
desktop copies already vary),
whose neighborhood

```text
0258: b04b 0424 75c7 1c90 cedc 2925 7fe2 a400 003d 0510 a600
026e: b08d 6586 3066 9450 ded4 2916 8fe2 6fe4 0000 0013 003e 0000 0000
0288: 5e09 1e50 5d52 4014 0fe6 3c00 a400 0003 0040
029a: 2308 7dc8 2442 d552 3034 0000 6800 3040
```

matches the JUPITER-X/SH-4d neighborhood shape (`b04b ... b08d ... 5e09 ...
2308 ... 2508`) packet for packet with 9450/ded4/8fe2/6fe4/1c90/cedc controls
in place, with different resource words. The four b0c1a placements (bases
`4020/8040/9040/a040`, source stride exactly `0x5f0`) show the same
neighborhood with resource pairs `(0xd,0x13f) (3,0x35f) (0x25,0x3f5)
(0x47,0x48b)` — four placements, four distinct pairs. No desktop SIM class
in `pairs.json` owns list `0xa41220` and no desktop class's primary stream is
packet-structure-identical to the GASS-type streams (verified same-position
header counts against the `0xa41220` stream: GASSDLY `0x9de948` 3 of 80; the
best other 80-packet stream, `0xa2cc28`, 5 of 80), so the GASS-type `5e09`
program's desktop identity remains open; the desktop `0xa41220` stream is the
only native-side anchor.

## What is established

* Complete `5e09` coverage: 117 packets, four shapes, no unknown control
  combination, in six images.
* The count-formula reading and the 9-word length of the GASS-type packet are
  pinned; `families(0x5e09)` still fails closed.
* The GASS-type invariants above, checked per packet and per image.
* The `5d52` control coexists with `1e50` selecting `1.75` in the same packet,
  exactly as in the admitted `2e07` negative-bias chains — across 28 uses.
* The three other shapes attach to named desktop classes `SIM_MFX_SBF325` and
  `SIM_MFX_STTMDLY` (via their render-list identity), plus a shared dsp6
  diagnostic packet.

## What is not established

* The operand syntax of `4014`/`4010` (the presumed kind-3 slot): that they
  consume offset 4 is consistent with byte accounting but is not a proof; no
  kind-3 semantics are admitted.
* That `5d52` performs an add in these contexts, or that the packet's `1.75`
  and `-0.25` words are consumed by the DSP the way the admitted native chains
  use them. No native cutpoint or DSP execution evidence exists for any
  `5e09` packet.
* The fitted `(1,1,3,4)` prediction for `0x5e`: these packets show the shape
  is consistent with it but cannot discriminate it from other unknown-syntax
  decompositions.
* Other builds, runtime-built descriptors, and writers outside the render
  lists scanned.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  python tools/five_e09_inventory.py > local/five-e09-inventory.json
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  python -m unittest discover -s tests -p test_five_e09_inventory.py -v
```

The tool exits nonzero on any unknown `5e09` control shape, changed count or
length, changed gain/bias literal, or changed image framing counts. The tests
pin the synthetic fail-closed behavior and the corpus totals above.

## Verification transcript (run 10, 2026-11-13)

Real commands and their real output (relevant lines) on this worktree,
interpreter `<repo>/.venv/bin/python`:

`PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" python tools/five_e09_inventory.py > local/five-e09-run10.json` — exit 0; `totals`:

```json
{
 "five_e_packets": 117,
 "framed_packets": 241742,
 "framed_segments": 2535,
 "shape_0cc8": 28,
 "shape_1e50": 28,
 "shape_2c80": 56,
 "shape_4050": 5,
 "unframeable_segments": 135,
 "distinct_gass_resource_pairs": 26
}
```

Per-image `five_e_packets`: zen_arm64 8, b0c1a.bin 17, b1c1a.bin 1,
MI077 45, RPG69 1, DD013 45; shapes per image match the table above.

Anchor dump (list `0xa41220`, zen segment base `0x4020`, length `0x5ec`,
source `0x817988`), via `packets(swap_words(...))`:

```text
0x258: b04b 0424 75c7 1c90 cedc 2925 7fe2 a400 003d 0510 a600
0x26e: b08d 6586 3066 9450 ded4 2916 8fe2 6fe4 0000 0013 003e 0000 0000
0x288: 5e09 1e50 5d52 4014 0fe6 3c00 a400 0003 0040
0x29a: 2308 7dc8 2442 d552 3034 0000 6800 3040
```

JUPITER-X MI077 first GASS placement (base `0x2020`, source `0x17621c`,
offset `0x28c`, payload `3c00a4000003003f`), same segment window:

```text
0x25c: b04b 0424 75c7 1c90 cedc 2925 7fe2 a400 003c 0cc8 c000
0x272: b08d 6586 3066 9450 ded4 2916 8fe2 6fe4 0000 0013 003d 0000 0000
0x28c: 5e09 1e50 5d52 4014 0fe6 3c00 a400 0003 003f
0x29e: 2308 7dc8 2442 d552 3034 0000 703c f040
```

Controls identical; resource/tail words differ as claimed.

b0c1a GASS records (tool output): bases `0x4020/0x8040/0x9040/0xa040`,
sources `0x1334c8/0x133ab8/0x1340a8/0x134698` (stride `0x5f0`), all at packet
offset `0x28c`, resources `(0xd,0x13f) (3,0x35f) (0x25,0x3f5) (0x47,0x48b)`.

dsp6 diagnostic records: one per image in b0c1a/b1c1a/MI077/RPG69/DD013, base
`0x0`, payload `0004d000002de000` in all five, offsets `0x1964/0x1776/0x16e0/
0x1324/0x1788` — minimum `0x1324` (MC-101), and b1c1a/RPG69 have no other
`5e09`.

`header_study.families(0x5e09)` raises `UnsupportedLayout: Unresolved header
family 5e09`; `families(0x4709)` returns `(0, 0, 4, 4)` as the anchor control.

Desktop identity negatives: `6698528` (`0xa41220`) absent from
`local/pairs.json` keys and from `labels`; same-position 80-packet header
comparison against the anchor stream: GASSDLY `0x9de948` 3/80, next best
`0xa2cc28` 5/80, anchor-vs-anchor 80/80.