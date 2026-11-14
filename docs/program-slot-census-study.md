# Program slot census and boot-stub ownership

2026-11-13. GLM overnight run 19. Lane A2 of the feasibility order: which
render program slots the two pinned CORE1 images declare and fill at the
list level, which slots receive only the six-byte boot stub, and what backs
those stub slots in the image. Static file analysis of `local/b0c1a.bin`
and `local/b1c1a.bin` with the repo's own Python tools; no device IO, no
firmware execution, no hardware claim.

## What was examined

`tools/program_slot_census.py` (this run, from an uncommitted draft found in
the worktree) frames every render program list with the `analyze.core_lists()`
predicates relaxed to `count <= 64` (the pinned images frame identically at 16
and 64), classifies every framed segment's stored bytes as `stub`, `packet`
or `data`, and answers three questions:

1. How many (dsp, base) slots exist, and which receive only the boot stub?
2. Is every framed list referenced by exactly one stored u32 word (framing
   liveness), and do referenced words form runs?
3. What backs each stub-only slot in the image?

The boot stub is a stored eight-byte record the writer splits into a leading
word and the high half of a second word; its logical six-byte stream is the
constant program `0b0200f80001`. Both constants are pinned in the tool:

```
$ PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  tools/program_slot_census.py b0c1a
{
  "lists": 103,
  "classification": {"counts": {"stub": 16, "packet": 361, "data": 0},
                     "data_segments": []},
  "slots": 32,
  "stub_only": [[4, "0x4020", ["0x1000"]], [4, "0x5020", ["0x1000"]],
                 [4, "0x6020", ["0x400"]], [4, "0x6420", ["0x1000"]],
                 [5, "0xe840", ["0x1400"]], [5, "0xfc40", ["0x2c0"]]],
  "stub_records": [{"base": "0x4020", "capacity": "0x1000",
                    "record": "0x610a8bfc", "source": "0x610a8bcc"},
                   {"base": "0x5020", "capacity": "0x1000",
                    "record": "0x610a8c0c", "source": "0x610a8bd4"},
                   {"base": "0x6020", "capacity": "0x400",
                    "record": "0x610a8c1c", "source": "0x610a8bdc"},
                   {"base": "0x6420", "capacity": "0x1000",
                    "record": "0x610a8c2c", "source": "0x610a8be4"},
                   {"base": "0xe840", "capacity": "0x1400",
                    "record": "0x610b0d40", "source": "0x610b0ca0"},
                   {"base": "0xfc40", "capacity": "0x2c0",
                    "record": "0x610b0d50", "source": "0x610b0ca8"}],
  "pointer_runs": [{"start": "0x610014d4", "length": 3},
                   {"start": "0x61029568", "length": 4},
                   {"start": "0x6102a750", "length": 4}],
  "descriptor_crosscheck": [
    {"dsp": 4, "base": "0x4020", "capacity": "0x1000",
     "stub_segments": 1, "packet_segments": 76},
    {"dsp": 5, "base": "0x8040", "capacity": "0x1000",
     "stub_segments": 1, "packet_segments": 76},
    {"dsp": 5, "base": "0x9040", "capacity": "0x1000",
     "stub_segments": 1, "packet_segments": 76},
    {"dsp": 5, "base": "0xa040", "capacity": "0x1000",
     "stub_segments": 1, "packet_segments": 76},
    {"dsp": 1, "base": "0x3020", "capacity": "0x1800",
     "stub_segments": 0, "packet_segments": 12}]
}
```

```
$ ... tools/program_slot_census.py b1c1a
{
  "lists": 104,
  "classification": {"counts": {"stub": 26, "packet": 1606, "data": 1},
                     "data_segments": [{"list_offset": 941364, "dsp": 4,
                                        "base": "0x1bda", "length": 64}]},
  "slots": 51,
  "stub_only": [[4, "0x4020", ["0x700"]], [4, "0x4720", ["0x700"]],
                 [4, "0x4e20", ["0x700"]], [4, "0x5520", ["0x700"]],
                 [4, "0x5c20", ["0x700"]], [4, "0x6320", ["0x700"]],
                 [4, "0x6a20", ["0x700"]], [4, "0x7120", ["0x700"]],
                 [4, "0x7820", ["0x700"]], [4, "0x7f20", ["0x700"]],
                 [4, "0x8620", ["0x700"]], [4, "0x8d20", ["0x700"]],
                 [4, "0x9420", ["0x700"]], [4, "0x9b20", ["0x700"]],
                 [4, "0xa220", ["0x700"]], [4, "0xa920", ["0x700"]],
                 [4, "0xb120", ["0x1000"]], [5, "0xe000", ["0x800"]],
                 [5, "0xe800", ["0x1000"]]],
  "stub_records": [{"base": "0x4020", ..., "record": "0x610a9000",
                    "source": "0x610a8f58"},
                   ... 17 dsp-4 records at 0x610a9000..0x610a9100 stride 16,
                   then {"base": "0xe000", "record": "0x610afcec",
                         "source": "0x610afc5c"},
                        {"base": "0xe800", "record": "0x610afcfc",
                         "source": "0x610afc64"}],
  "pointer_runs": [{"start": "0x610029b4", "length": 5},
                   {"start": "0x61024348", "length": 2},
                   {"start": "0x61024800", "length": 2}],
  "b1c1a_reservation_table": [[0x4020, 0x700], [0x4720, 0x700],
    [0x4e20, 0x700], [0x5520, 0x700], [0x5c20, 0x700], [0x6320, 0x700],
    [0x6a20, 0x700], [0x7120, 0x700], [0x7820, 0x700], [0x7f20, 0x700],
    [0x8620, 0x700], [0x8d20, 0x700], [0x9420, 0x700], [0x9b20, 0x700],
    [0xa220, 0x700], [0xa920, 0x700], [0xa000, 0x700], [0xa700, 0x700],
    [0xae00, 0x700], [0xb500, 0x700]]
}
```

## Method

* Framing reuses the proven `analyze.core_lists()` predicates; the only
  relaxation is the count bound, and `frame_lists` was checked to produce the
  identical list set at bound 16 on both images (the draft's shortcut comment
  records this; the committed tool raises only above 64).
* `classify_segment` calls the admitted packet subset `bmc_dsp.packets()` and
  fails closed: a segment whose stored bytes are shorter than its padded
  length raises rather than silently classifying.
* The stub-record invariant is checked, not assumed: for every stub-only
  slot the census locates every stored `{base, 6, capacity}` triple in the
  image, requires exactly one, requires its fourth word to point at stored
  bytes equal to the pinned record, and requires the record's source to hold
  `f800020b00000100`.

## Verified evidence

All commands run in this worktree with the pinned interpreter
`/Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python`,
`PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local"`.

1. Both payloads re-hash to the run 14 pins before use (`b0c1a`
   `6d95449a…3154`, `b1c1a` `c8d150b9…68bd`); the tool exits 0 on both.
2. Stub-only slots: b0c1a has 32 (dsp, base) slots, 6 stub-only; b1c1a has
   51 slots, 19 stub-only. All four FETDRIVE-family reservations (dsp4
   `0x4020/0x1000`, dsp5 `0x8040/0x9040/0xa040` at `0x1000`) are ALSO
   boot-stubbed; the LINEDRIVE reservation (dsp1 `0x3020/0x1800`) receives
   12 packet segments with no stub. This matches the five reservations the
   kernel-audio-abi study maps from constructors.
3. Every stub-only slot is backed by exactly one 6-byte segment record
   `{base, 6, capacity, source}` whose source holds the pinned record:
   * b0c1a: records at `0x610a8bfc/0c/1c/2c` (dsp4 group, stride 16, sources
     `0x610a8bcc..0x610a8be4` inside the 5-record array
     `0x610a8bc4..0x610a8be8`) and `0x610b0d40/d50` (dsp5 `0xe840/0xfc40`,
     sources `0x610b0ca0/0x610b0ca8` inside the 11-record array
     `0x610b0c58..0x610b0cac`).
   * b1c1a: 17 dsp-4 records at `0x610a9000..0x610a9100` (stride 16) plus
     dsp5 `0xe000/0xe800` at `0x610afcec/fc`, sources `0x610a8f58..0x610a8fd8`
     inside the 18-record array `0x610a8f50..0x610a8fdc` and dsp5 sources
     `0x610afc5c/0x610afc64` in a second array near `0x610afc54`.
   The `{base, 6, capacity}` shape is the *framed segment record format
   itself*: the fourth word is the segment's stored source. The b0c1a and
   b1c1a stub-record words were dumped and compared with `STUB_RECORD` byte
   for byte in this run's transcript.
4. Fail-closed negatives (verified by test and by direct mutation):
   duplicating a stub record's base (`0x5020 -> 0x4020`, one bit at
   `0x610a8c0c`) makes `study()` raise `... has 2 {base, 6, capacity}
   segment records, expected exactly one`; removing or corrupting a record's
   source raises in `stub_record_census`; a one-bit change to framing,
   capacity or length predicates is covered by synthetic tests.
* The pinned b1c1a table at `0x610a4f20` holds exactly 20 distinct
   `{base, 0x700}` pairs; 16 of the 20 bases are the stub-only dsp4 slots
   (the 17th, `0xb120` at capacity `0x1000`, is not in the table) and the
   other 4 (`0xa000/0xa700/0xae00/0xb500`) are dsp5 slots carrying both a
   boot stub and real packet content. The table words were compared raw
   with `struct.iter_unpack` in the test.
6. The one b1c1a data segment (dsp4 base `0x1bda`, length 64, source
   `0xe8ef4`) is a 64-byte non-packet tail inside a stub-record array. Its
   stored bytes end `…c0f8fdd1 c0f8020c f800020b` — the last word is the
   boot-stub record's first word — and the stored region continues after
   the segment with `00000100 f800020b f800020b` (the tail of one record
   then two full records). Lead stored bytes `0530000059cf50500400d700…`
   were dumped and are not claimed to be packets.

## What is established

* Both stock images declare their render slot usage purely through framed
  program lists plus boot-stub segment records; no slot in either image lacks
  a backing record.
* The b0c1a MFX render reservations from the kernel-audio-abi study are
  confirmed to be written at list level, four of them also boot-stubbed.
* b1c1a reserves a 20-entry `{base, 0x700}` table beside its boot-stub
  array; 16 of its 20 rows are the dsp4 stub-only slots, and the b0c1a
  5-record/11-record arrays and b1c1a 18-record array bound every stub
  slot's stored program copy.
* No conclusion here is about silicon, execution or loading: it is list- and
  image-level structure only.

## What is not established

* Which manager code owns each slot at runtime (the census names no owner
  function); the pointer runs at `0x610014d4/0x61029568/0x6102a750` (b0c1a)
  and `0x610029b4/0x61024348/0x61024800` (b1c1a) are located but not traced.
* Whether the b1c1a table at `0x610a4f20` is read by code (no xref taken).
* Whether any stub-only slot is *unused* by the stock engine versus
  deliberately stubbed (a stub is a written program; whether it ever runs is
  open).
* The lead bytes of the b1c1a data segment's 64-byte payload (first 60 bytes
  dumped, not decoded); other builds.

## Reproduce

```
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  tools/program_slot_census.py b0c1a
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  tools/program_slot_census.py b1c1a
BMC_CORPUS_DIR="$PWD/local" PYTHONPATH=local/fantom-python:tools:tests \
  /Users/jacob/Projects/Open Synth Platform/bmc-research/.venv/bin/python \
  -m unittest discover -s tests -p test_program_slot_census.py
```