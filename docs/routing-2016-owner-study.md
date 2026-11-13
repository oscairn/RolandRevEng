# Routing `2016..2019` owner: the native context behind the writes

2026-11-13, run 8 of the glm-overnight-2 series. Static analysis of the
pinned ZENOLOGY arm64 image (SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`), extending
[the kernel/audio ABI study](kernel-audio-abi-study.md) and
[the transfer-space study](transfer-spaces-study.md). No execution, no device
access, no encryption material. The tool is
`tools/routing_2016_owner_study.py`; 62 byte-exact instruction anchors and
3 data anchors are checked by `tests/test_routing_2016_owner_study.py`.

## Question

The kernel study established that `CSimDSP4Routing::VSubProc` (`0x000413d0`,
exported) writes shared routing storage and passes input/output pointer arrays
to the selected effect. It left open which context calls it and under which
condition. The queue's section-3 item asks which context owns the
`2016..2019` writes, against the measured audio link, where the i.MX drives
three stereo pairs into the BMCs over SAI1 and nothing is yet known about the
rendered slot graph on the BMC side.

## Result: the full construction and call chain

Every edge below is a checked instruction anchor; all 65 anchors are byte-exact
in the pinned image.

1. **`CEfctPrm::EfctLoadFixedAlg` (`0x165fd8`, exported `0x165fd0` as start-1
   alias; the function body is `0x165fd8..0x1661a0`)** is the construction
   context. It calls `CSimDSP4_Core::Init` (`0x16bc68`, anchor `0x165ff4 bl
   #0x16bc68`) and `CSimDSP5_Core::Init` (`0x292220`, anchor `0x165ffc bl
   #0x292220`), then loops six times (counter at `0x166168..174`, limit
   `#0x30` bytes = six 8-byte records over `x19+0x740..0x860`) allocating a
   0x30-byte object and calling `SIM_MFX_COMP::Init` (`0x3b1cd8`, anchor
   `0x16614c`). This is a fixed-algorithm load: six `SIM_MFX_COMP` effect
   instances plus one DSP4 core and one DSP5 core are constructed here.
2. **`CSimDSP4_Core::Init` (`0x16bc68..0x16bce8`)** allocates `0xa0` bytes
   (`0x16bca8 mov w0, #0xa0`), takes the manager pointer from wrapper+8+0x40
   (`0x16bcb8 ldr x1, [x8, #0x40]`) and the `SGlobalObj` stored by the core
   constructor at core+0x220 (`0x16bcbc ldr x2, [x19, #0x220]`), calls the
   exported `CSimDSP4Routing::CSimDSP4Routing(CFspDspMgr*, SGlobalObj*)`
   (`0x41288`, anchor `0x16bcc0`), and **stores the result at core+0x230**
   (`0x16bcc4 str x20, [x19, #0x230]`). `CSimDSP5_Core::Init` does the same
   with `CSimDSP5Routing::CSimDSP5Routing` (`0x34c0f8`, anchors `0x292278`/
   `0x29227c`).
3. **The routing constructor (`0x410e8..0x41288`)** installs the vtable at
   +0 (`0x41104/0x41110`, vtable `0x9cfdc8`, the exported `vtable for
   CSimDSP4Routing` at `0x9cfd68` whose first function entry is `0x9cfdc8`),
   copies six `_CoefSym`-table pointers (the `ldrsb/cmp #1/ldr/str` ladder at
   `0x41124..0x41224`), stores the `(CFspDspMgr*, SGlobalObj*)` pair at +0x28
   (`0x41220 str x19, [x21, #0x28]` — the pair is `(x1, x2)` from the ctor
   arguments), and allocates the 0x1b40-byte working structure whose address
   lands at routing+0x38 (`0x41234 mov w0, #0x1b40`, `0x41248 bl #0x42e14`,
   `0x4124c str x0, [x19, #0x38]`). That 0x42e14 initializer is the same
   function `transfer-spaces-study.md` reaches as `load(load(R + 0x18) +
   0x18)` source: it initializes the two circular arrays (words at +8/+0x10
   hold 0x3db/0x316/0x33e/0x1d7/0x1558 group sizes, checked at
   `0x42e14..0x42e50`).
4. **Per render pass, `VSubProc` runs virtually.** `VProcSync(double**)`
   (`0x1662a0`) reaches `CSimDSP4_Core::VProcSync(double**, int, int)`
   (`0x16c2e4`, anchor `0x1662b4`), which dispatches through core+0x230
   (`0x16c35c mov x2, #0` after `0x16c350 ldr x0, [x19, #0x230]`... the
   vtable slot +0x20 call at `0x16c364 blr x8`). The routing `VSubProc` body
   (`0x413d0..0x42e14`, 6,724 bytes) is reached only through its vtable slot
   (see below); there is **no direct BL to it anywhere in the image** (full
   image scan of BL encodings: zero hits, run in this study's exploration and
   re-checkable with `tools/core1_xrefs.py`-style encodings on arm64).

## The writes themselves (unconditional) and the call (conditional)

Inside `VSubProc`, with `x8` = routing+0x38 (the 0x1b40 structure) and the
second circular array pointer resolved through the R path
(`0x41bc0 ldr x9, [x19, #8]` → +0x18 → +0x18 → +0x18, base index at +0x20):

- Main scaled outputs land at absolute indices **0xf0/0x100** (`0x41c34 mov
  w12, #0xf0` … `0x41c50 str d0, [x10, w12, uxtw #3]`).
- **The four routing slots are written unconditionally**:
  - `0x41c54 mov w12, #0x18` … `0x41c64 str d1, [x12]` (absolute 0x18),
  - `0x41c68 mov w13, #0x19` … `0x41c78 str d0, [x13]` (absolute 0x19),
  - `0x41c84 mov w14, #0x16` … `0x41c94 str d1, [x14]` (absolute 0x16),
  - `0x41c98 mov w15, #0x17` … `0x41ca8 str d0, [x15]` (absolute 0x17).
  Each effective index is `(absolute − base) & 0x7ff` (`0x41c58/0x41c5c` etc.).
  With the FZ tag-2 base 0x16 recovered by the transfer-space study, absolute
  0x16..0x19 are exactly program operands `2016..2019`.
- The values stored are the scaled, summed results; the scale is a live
  coefficient read through the 0x48-stride record at +0x28 (`0x41bf4 ldr x12,
  [x8, #0x1ac0]`, `0x41bf8 ldr s4, [x12, #0x28]`, `0x41bfc fcvt d4, s4`,
  `0x41c7c/0x41c80 fmul`), and the sums use coefficient-backed gains at
  x8+0x688/0x698 (`0x41be4/0x41bec`) — the same +0x28-record path the
  transfer-space study proved.
- **The effect call is conditional**: the condition word comes from two floats
  in the 0x1b40 structure. `0x41c14 ldr d3, [x8, #0x678]`; `0x41c18 fcmp
  d3, #0.0`; if zero, `0x41c30 mov w8, #0`; else `0x41c20 ldr d3, [x8,
  #0x628]` and `0x41c28 cset w8, ne`. Then `0x41cac tbz w8, #0, #0x41ce0`
  skips the call. So the effect's virtual method runs only when
  `[x8+0x678] != 0` **and** `[x8+0x628] != 0`.
- The call itself takes the effect object from the stored pair: `0x41cb8 ldr
  x8, [x19, #0x28]` (the `CFspDspMgr*` stored at ctor `0x41220`) → +8 →
  +0x50 → +0x28 (`0x41cbc/0x41cc0/0x41cc4`), then `0x41cc8 ldr x8, [x0]` /
  `0x41ccc ldr x8, [x8, #0x20]` / `0x41cd8 blr x8` — **vtable byte offset
  0x20, i.e. slot 4**.
- After the conditional call, output slot 0x18 is re-read (`0x41da8 mov w11,
  #0x18` … `0x41db8 ldr d0, [x8, x11]`), confirming the fallback/preseed
  ordering the kernel study described.

The bypass path (`0x41ce0..0x41d90`) instead zeroes one slot in each of three
arrays (`0x41cf4/0x41d00/0x41d1c str xzr, ...`) and clears the effect's own
state blocks (`0x41d2c..0x41d90`, ten 32-byte zero stores each), so a bypassed
DSP still writes routing state every pass.

## The dispatch target is the effect's `VSubProc` at vtable slot 4

`SIM_MFX_FZ::VSubProc` is exported at `0x3e480c`. Its vtable reference is the
8-byte pointer at `0xa76210`; the vtable's first function entry is `0xa761f0`
(slot 0 = `0x3e4f84`), so `VSubProc` sits at **slot 4 = byte 0x20**, exactly
the `ldr x8, [x8, #0x20]` the dispatch executes. The vtable header at
`0xa761d8` points at typeinfo `0xa504d8`, whose name pointer resolves to
`9CMDSPTask` — the `CMDSPTask` base-class chain, consistent with these being
render-task classes. The tool pins this arithmetic in
`check_slots`/`vtable_slot`.

`CSimDSP5Routing::VSubProc` (`0x34c244..0x34d690`) is the DSP5 analog: same
shape, but its absolute slots are **0x462..0x465** (`0x34c76c mov w11, #0x462`
… `0x34c7a8 mov w14, #0x465`), outputs first with the last two zeroed as
fallbacks (`0x34c7a4/0x34c7b8 str xzr`), inputs `0x460/0x461` (the pair fed by
the earlier `0x34c6ac`-region stores), and the same slot-4 dispatch
(`0x34c8b0 blr x8` after `0x34c888 stp x11, x12, [sp, #0x38]`). This matches
the kernel study's DSP5 list operands (`2005..2010` for the three DSP5
segments come from tag-2 bases per instance, not one global constant).

## What this establishes for the queue item

- **The owner of the `2016..2019` writes is named and chained**: one
  `CSimDSP4Routing` per DSP4 core, constructed by `CSimDSP4_Core::Init` under
  `CEfctPrm::EfctLoadFixedAlg`, stored at core+0x230, executing per pass
  through a vtable slot-4 virtual call, writing the four slots every pass
  whether or not the effect runs.
- The writes are **not** keyed to any external audio input in this context:
  the slots are rewritten from computed values (coefficient-scaled sums) and
  zero fallbacks each pass. Nothing in this chain references an SAI/TDM slot
  number; the measured six-channel SAI1 link of
  [the audio link note](fantom-audio-link-measurements.md) enters the BMC
  somewhere else, and this study adds the negative: **no `0x16..0x19`-region
  code in this native chain touches a TDM/SAI concept** — the tag-2 array is
  core-internal routing storage with per-instance bases, exactly as the
  transfer-space study required.
- The kernel study's "when its condition is enabled" is now decoded exactly:
  **two coefficient-backed floats in the 0x1b40 structure gate the effect
  call** (`0x678` zero forces bypass; otherwise `0x628` nonzero enables), and
  the bypass path still writes the slots and zeroes effect state.

## What is not established

- The hardware correspondence on the Fantom: which BMC, DSP index and TDM slot
  each `CSimDSP4/5Routing` instance maps to is beyond a native-image study;
  the five recorded effect placements of the kernel study remain the Fantom-
  side evidence, and nothing here proves the bmc0 CORE1 side mirrors this
  desktop layout.
- Which coefficient symbols feed `[x8+0x678]/[x8+0x628]` (their writers were
  not traced; the 0x1b40 structure's field ownership is only bounded by the
  constructor at `0x42e14`).
- Whether the DSP5 slot constants `0x460..0x465` correspond to the kernel
  study's DSP5 list operands exactly (their tag-2 bases were per-instance;
  this study did not reconstruct the DSP5 constructor tables).
- The meaning of the six `SIM_MFX_COMP::Init` instances at the
  `EfctLoadFixedAlg` tail (a fixed-algorithm scaffold; its callers and the
  stock activation path remain open, per the kernel study).

## Reproduce

```sh
PYTHONPATH=tools BMC_CORPUS_DIR=<main>/local python tools/routing_2016_owner_study.py --json
BMC_CORPUS_DIR=<main>/local python -m unittest discover -s tests -p test_routing_2016_owner_study.py -v
```

Without the corpus the pure condition/slot tests still run (5 of 9; 1 skipped
class of 4 tests under pytest-style skipping, or the pinned class skipped by
unittest).