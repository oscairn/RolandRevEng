# Render program indexed-transfer census: which memory spaces stock programs address

2026-11-13, run 21. Lane A5 scoping step named by run 19: a census of which
memory spaces render programs address through the admitted indexed-transfer
control form, over all six prepared corpus images. Inventory only: no
instruction semantics, no opcode admission, no hardware claim.

## What was examined

Every framed render program segment in six hash-pinned images:

| Image | SHA-256 (first 16) | framed segments | framed packets |
|---|---|---:|---:|
| `zen_arm64` (desktop) | `b8ba7f41e26bef91` | 177 | 12,365 |
| `b0c1a.bin` | `6d95449ae2a2df48` | 377 | 36,793 |
| `b1c1a.bin` | `c8d150b9cfe13d8e` | 1,632 | 132,135 |
| JUPITER-X `MI077` | `9368ef3243567cbd` | 979 | 86,857 |
| MC-101 `RPG69` | `6de1e182e531d672` | 1,561 | 125,927 |
| SH-4d `DD013` | `57466624effa7b78` | 909 | 79,912 |

The control form is the fragment emulator's admitted indexed transfer
(`tools/bmc_emulator.py` line 110, `tools/alu_study.py` line 35): a control
word with bits 4..11 equal `0xfe0` and bit 0 clear. Its low nibble halves to a
shared-pool halfword index; its top nibble is the port. The direction
convention is the emulator's: ports 0..7 load, 8..15 store. The 16-bit pool
word's top nibble is reported as the address tag.

## Method

`tools/render_transfer_census.py` frames every segment
(`program_slot_census.frame_lists` for the CORE1 payloads and the QSPI
cross-model images, `local/zenology_inventory.json` lists for the desktop
image — the framings runs 4/11/19 already accepted), decodes each segment's
stored bytes with the admitted packet subset, and classifies every control
word. Unknown shapes are counted, never guessed: segments whose stored bytes
do not packet-decode are counted `unframeable_segments`; a transfer whose pool
index exceeds the packet's pool is counted `pool_index_overflow`; the odd
bit-0 form is counted `odd_form_controls`. Every access to a rare tag
(`1`, `3`, `f`) is recorded verbatim with its packet words, so rare-syntax
questions stay inspectable without a rerun.

## Exact evidence (this run's command, trimmed output)

```sh
cd "/Users/jacob/Projects/Open Synth Platform/bmc-research/local/worktrees/glm-overnight"
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  tools/render_transfer_census.py > local/render-transfer-census.json
# exit=0
```

```json
"transfer_controls": 529931, "framed_segments": 5635,
"framed_packets": 473989, "unframeable_segments": 136,
"odd_form_controls": 88, "pool_index_overflow": 0,
"observed_tags": ["0","1","2","3","4","6","8","a","c","e","f"],
"absent_tags": ["5","7","9","b","d"],
"native_provenanced_tags": ["0","2","4","c"]
```

Accesses by tag (all six images):

| tag | accesses | loads | stores | distinct low-12 addresses | programs | native provenance |
|---|---:|---:|---:|---:|---:|---|
| 0 | 381,028 | 205,159 | 175,869 | 1,843 (RPG69) | 45 (RPG69) | yes (transfer-spaces-study.md) |
| 2 | 40,997 | 23,141 | 17,856 | 1,302 (RPG69) | 46 (RPG69) | yes (transfer-spaces-study.md) |
| 4 | 33,066 | 25,015 | 8,051 | 656 (RPG69) | 40 (RPG69) | yes (transfer-spaces-study.md) |
| c | 55,850 | 55,850 | 0 | 869 (RPG69) | 43 (RPG69) | yes (transfer-spaces-study.md) |
| a | 8,107 | 3,160 | 4,947 | 811 (RPG69) | 36 (RPG69) | no |
| e | 8,474 | 8,474 | 0 | 40 (DD013) | 37 (MI077) | no |
| 8 | 1,299 | 982 | 317 | 346 (RPG69) | 8 (RPG69) | no |
| 6 | 725 | 370 | 355 | 176 (b0c1a) | 4 (b0c1a) | no |
| 1 | 134 | 134 | 0 | 1 (`0x999` low 12 of `1999`) | — | no |
| 3 | 134 | 134 | 0 | 1 (`0x69f` low 12 of `369f`) | — | no |
| f | 117 | 24 | 93 | 2 (`f000`, `f801`) | — | no (run-11 6fe4/62 trap lives here) |

Tags 5, 7, 9, b, d never occur. Ports 0..15 all occur corpus-wide
(port 11 only in corpus images, never in an admitted fragment profile).

## What is established (verified)

* Every indexed transfer in every framed stock render program resolves to a
  pool word inside its own packet: `pool_index_overflow` is 0 across all
  529,931 transfers (tool run above). This extends `analyze.py`'s per-image
  operand-boundary assertions to the whole census.
* The address space is sparse: of 16 possible top-nibble tags, 11 occur; 4 of
  the 11 carry 510,941 of 529,931 transfers (96.4%) (0/2/4/c), and those four
  are exactly the tags the transfer-spaces study proved natively. The other
  18,990 accesses (3.6%) use tags without native provenance.
* Tags 1 and 3 are corpus singletons: each hits exactly one address
  (`0x1999` and `0x369f`), 134 load-only accesses each, and every occurrence
  is a pool word of the GASS-type `5e09`-family neighborhoods run 10 mapped —
  tag 3 (`0x369f`) is consumed by the `6209` packet itself (offsets `0x22e`/
  `0x29c`, the run-6/11 `6fe4` trap and its `2508` companion) and tag 1
  (`0x1999`) by the `2e08` packets at offsets `0x1a`/`0x5e`, all in dsp4/dsp5
  programs (dsp0 for the desktop image).
* Tag f is the rare-tag home of the run-11 `6fe4` slot-0 trap: 117 accesses,
  addresses only `f000`/`f801`, 93 of them stores.
* The odd bit-0 form (`0xfe1`-class) occurs 88 times corpus-wide and was never
  admitted; the census counts it instead of guessing.
* All six image hashes re-pinned before use; the tool fails closed on any hash
  or inventory-pin change (one-bit flip → `SystemExit: Unexpected b0c1a
  SHA-256 40fdbbf2…`).

## What is not established

* No instruction semantics: a tag census does not say what loads/stores mean
  on silicon, nor that the port direction convention holds on the chip.
* No wave-memory answer yet: this run bounds *which* spaces exist and their
  use counts; identifying which instructions read DRAM-IO/wave apertures
  (the `0x411/0x412/0x414/0x415` ports of the program-read study) and whether
  any tag here is the wave path remains open — none of the six images' render
  programs reference an address whose tag could be wave memory under the
  current (unproved) assumptions.
* Native provenance for tags 1/3/6/8/a/e/f: `transfer-spaces-study.md` proved
  only tags 0/2/4/c in the desktop model. The singleton tags 1/3 are fully
  enumerated above, which makes them the cheapest next native-provenance
  targets.
* 136 unframeable segments (128 desktop, 6 MC-101, 1 b1c1a data segment, 1
  SH-4d) are counted, not decoded; their contents are not in the census.
* b1c1a framing uses run 19's count<=64 relaxation; b1c1a framed segment count
  differs from `analyze.core_lists` (1,632 vs 34) because the latter caps
  count at 16 and drops b1c1a's long dsp0..3 base-0 lists. This is the same
  accepted framing run 19 pinned, not a new one.

Reproduce the pinned numbers:

```sh
BMC_CORPUS_DIR="$PWD/local" PYTHONPATH=local/fantom-python:tools:tests \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  -m unittest discover -s tests -p test_render_transfer_census.py -v
# Ran 18 tests in 25.6s — OK (8 corpus-pinned, 10 pure)
```