# GASSDLY 6209: the 6fe4 literal trap and its shared ownership group

2026-11-13. This study resolves the trap the [handoff](agent-handoff.md) records for
the fitted four-operation `62` reading: GASSDLY's `6209` packet
(`6fe4 9450 ded4 8fe2`) has a `6fe4` low-six reference that selects relative
field `23c`, but the native constructor representative for the 1.414 value names
relative `22b`. It proves the missing pieces the handoff required before any
binding: there is no second native representative, and both fields are written by
one stock grouped-write operation, so their values are always equal.
**No DSP opcode, port semantics or interpreter admission follows.**

## What was examined and how

All checks are static, on the pinned ZENOLOGY arm64 image
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`, with
`tools/gassdly_62_trap.py` reusing the checked descriptor ABI from
[line-prefix-single-writer](line-prefix-single-writer-study.md), the constructor
reconstruction from `parse.parse_ctor`/`transfer_study.constructor_memory`, the
straight-line ADRP/ADD reference scan, and `header_study.reference`/`bmc_dsp.literal`.

## The trap, exactly

`SIM_MFX_GASSDLY` has one render segment at base `4020` (peer `8000`), logical
length `570`. The `6209` packet at `22e` has four controls and pool
`0000 0013 369f be00`. `6fe4` low six bits `0x24` decode through the ordinary
reference syntax to pool offset 4, width 3 — absolute field `23c`, stored bytes
`369fbe`, value `1.4139995574951172`.

The only native constructor pair naming `22b` sits at object+`b0`/+`b8`:
`mov w8, #0x22b; str w8, [x0, #0xb0]` and the immediate
`mov x8, #0xb439; movk x8, #0x76c8, lsl 16; movk x8, #0x9fbe, lsl 32;
movk x8, #0x3ff6, lsl 48` = `1.414` stored through `str x8, [x0, #0xb8]`, inside
constructor `2fa9a0..2fb5d4`. The native callback loads that double twice:
`2fa1c4: ldr d16, [x8, #0xb8]` (`fmul d4, d16, d4`) and
`2fa1f0: ldr d17, [x8, #0xb8]` (`fsub d17, d17, d4`). The remaining constructor
double loads in the callback name `218` (+0x168, −1.0), `228` (+0x408,
0.019785341483477367) and `274` (+0x2d8, 0.46875) — **none names `23c`**, and no
`[x8, #0xc0]` load exists. So the native read side binds the 1.414 value to
field `22b` only; the constructor has 123 pairs and none names `23c`.

Field `22b` itself is consumed by the preceding `5a09` packet at `21c`
(controls `422, 75e5, 1c90, cedc`, pool `a40005 10a636 9fbe`): control `75e5`
low six bits `0x25` select pool offset 5, width 3 = field `22b`. Both fields
store identical bytes `369fbe`; the stored literal differs from the native double
by `4.4250488e-07`, below the field's `2^-32` quantum, the precision-aware
binding the [short-add inventory](short-add-context-candidates.md) already uses.

## Ownership: one count-2 group and one writer

The count>=1 descriptor scan over relative fields `22b`/`23c` finds exactly six
mentions and exactly one count>=2 group:

| Symbol | Count | Records (absolute / relative / width) | Sole reference | Writer |
|---|---:|---|---|---|
| `9dfa50` | 2 | `424b / 22b / 3`, `425c / 23c / 3` | `cbf98` | `CFspMfxGASSDLY::SetDLY(bool, int, int)` |
| `a1f9a0` | 1 | `424b / 22b / 3` | `1d1e4c` | `CFspMfxSPACED::SetEQHigh(int)` |
| `a41d00` | 1 | `425c / 23c / 3` | `2b0244` | `CFspMfxGasSChoFlg::SetAmpGain(int)` |
| `a43840` | 1 | `425c / 23c / 3` | `2c2618` | `CFspMfxRVSDLY::SetAlg()` |
| `a43860` | 1 | `424b / 22b / 3` | `2c2638` | `CFspMfxRVSDLY::SetAlg()` |
| `9cc8c0` | 1 | `922b / 22b / 3` | `1adb0` | `CFspRevBINHALL::SetAlg()` |

`424b − 0x22b = 425c − 0x23c = 4020`, so the group's records target GASSDLY's
program base. The only slot-`c8` literal call in `SetDLY` (`cbe54..cc0d4`) is
at `cbf98` with descriptor `9dfa50`. Per the checked firmware ABI
([parameter study](line-prefix-parameter-study.md)),
`CBmcDspMgr::WriteDspCoefFloat` saves the input float once and writes the same
value through every record of the declared group, so **one SetDLY call writes
fields `22b` and `23c` with one value**.

The written value is selected at `cbf78..cbf90`: `d0 = |old_delay − d8|`,
`d1 = 0.10000000149011612` (`3fb99999a0000000`), and
`d0 = (d0 >= d1) ? 1.0 : 1.4140000343322754` (`3ff69fbe80000000`; the 1.0 is
`fmov d9, #1.0` at `cbf8c`, fcsel `mi`). The delay itself (`d8`, seconds from
either the tempo path `table[w21]*60.0/sync_divisor` or `w22/1000.0`) is stored
to member+`18` after the group write. So both fields always hold one common
value drawn from {1.0, 1.4140000343} on this checked path.

The sibling count-1 writers show the same constructor asymmetry in other classes:
`SIM_MFX_SPACED` has a `22b` pair (object+`40`, 0.0) and no `23c` pair;
`SIM_MFX_RVSDLY` has both a `23c` pair (−0.998046875) and a `22b` pair
(0.99609375), i.e. field `23c` is program-relative and means different values in
different programs. GASSDLY's getter `2f9c34..2f9c80` scans 123 entries of
stride `0x10` at object+`28` comparing the record's absolute byte, so a `23c`
record would have matched had a pair existed.

## What is established

Established (every claim re-checked by the tool and pinned in tests):

* The `6fe4` low-six reading of the `6209` packet selects field `23c`
  (`1.4139995574951172`); the native callback's 1.414 double comes from the
  object+`b8` pair naming field `22b`, loaded at `2fa1c4` and `2fa1f0`.
* No constructor pair names `23c` in GASSDLY; there is no second native
  representative, and no other constructor double load could alias it.
* Fields `22b` and `23c` are declared together in exactly one count-2 group and
  written by exactly one slot-`c8` call in `SetDLY` with one saved float; within
  the checked ABI writers their values are always equal.
* The stored bytes of both fields are identical (`369fbe`), and field `22b` is
  itself referenced by `75e5` in the preceding `5a09` packet.

Consequence for the standing trap: a grouped-write relation is now **proved** for
the `22b`/`23c` pair in GASSDLY, so the handoff's condition — prove the
shared-representative/ownership-update group before binding — is satisfied for
this pair. A `6fe4`-consumes-`23c` reading is therefore consistent with the
native 1.414 evidence, not contradicted by it.

## What is not established

* That the DSP actually executes `6fe4` as an operation consuming field `23c`;
  the fitted `62 = (1,2,2,4)` family and the roles of `9450`, `ded4`, `8fe2`
  remain unresolved (run 4's zero-counterexample result is unchanged).
* That `SetDLY` is the only writer: runtime-built descriptors, raw writes,
  external paths and other builds are not excluded.
* Any DSP observation of grouped writes: the equality follows from the checked
  manager/firmware ABI, not from a hardware trace.
* Any extension of `header_study.families()`, the strict decoder or the
  fragment interpreter; the executable subset is unchanged.

## Reproduce

```sh
PYTHONPATH=local/fantom-python:tools BMC_CORPUS_DIR="$PWD/local" \
  python tools/gassdly_62_trap.py local/zen_arm64
PYTHONPATH=local/fantom-python:tools:tests BMC_CORPUS_DIR="$PWD/local" \
  python -m unittest discover -s tests -p test_gassdly_62_trap.py -v
```

The tool exits nonzero on any changed packet, record, reference, getter shape,
selection constant or image identity. Tests pin the synthetic fail-closed
behavior and the corpus facts above.