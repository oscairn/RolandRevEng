# Routing gate writer callers study

Follow-up to [run 9's gate-writer study](routing-gate-writers-study.md), which
proved that the DSP4/DSP5 routing dispatch gate floats (structure+0x628 enable,
+0x678 bypass) are written at construction time as value slots of 0x50-stride
tail records with 32-bit record keys, and that the runtime coefficient
transfer path `CSimDspMgr::WriteDspCoefFloat` (`0x0fba10`) resolves records
through the same record storage. This run answers run 9's open question: does
the stock application ever call that write path at runtime, and with which
keys — in particular, can the bypass gate (+0x678) be flipped nonzero after
construction?

Static, read-only file analysis of the pinned ZENOLOGY arm64 image,
SHA-256 `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
No firmware, plugin or instrument is executed; no device is contacted.

## Result (summary)

`WriteDspCoefFloat` (0xfba10) has **no direct BL callers** in the pinned image
(whole-image scan of every 4-byte-aligned BL encoding: 0 hits for 0xfba10 and
0xfba11; the only reference anywhere is an aligned 64-bit pointer quad at
`0x9e54d0`, inside the consecutive manager-function-pointer table starting at
`0x9e53f8`, and no adrp+add pair computes either address). The write path is
therefore entered **virtually**: the manager vtable slot at byte offset 0xc8
holds it, and a strict whole-image virtual-call scan (LDR xS,[xR]; LDR
xT,[xS,#0xc8]; BLR xT, with xS loaded from a pointer load in the preceding four
instructions) finds 162 sites, of which **5 load the manager global 0x9c8480**
within 40 instructions — all five inside one function at `0x354184`
(`0x354388`, `0x3543a0`, `0x3543b8`, `0x3543d0`, `0x3543e8`). So the stock
image does contain a runtime caller of the coefficient write path; whether it
ever writes the bypass key needs runtime values (see limits).

## Method

Run the committed checker:

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/routing_gate_callers_study.py --json
```

The checker (76 byte-exact anchors) verifies the write/lookup ABI end to end,
then censuses callers:

1. Write ABI (byte-pinned at `0x0fba10..0x0fba7c`): `WriteDspCoefFloat(x0 =
   manager, x1 = symbol descriptor, d0 = value)`. It checks the gate/entry byte
   `symbol+0x18` (zero → return without writing), loads the routing object
   `x0 = [manager+0x28]`, calls `vtable byte 0x10` with `(routing, symbol)`,
   and, if the returned record pointer is nonzero, stores the value with
   `str d8, [x0]`. Real instructions:
   `0x0fba54 ldr x0,[x0,#0x28]; 0x0fba60 ldr x8,[x0]; 0x0fba64 ldr
   x8,[x8,#0x10]; 0x0fba68 blr x8; 0x0fba6c cbz x0,#0xfba74; 0x0fba70 str
   d8,[x0]`.
2. Both record-lookup helpers, byte-pinned: vtable byte 0x10 = `0x41334`
   (16-byte-stride key scan, 0xce entries over `[routing+0x38]`, wanted key
   `u32[[symbol+0x10]+4]`, returns `record+8`) and vtable byte 0x18 = `0x41380`
   (8-byte-stride key scan, 0x1ba entries over `[routing+0x38]+0xce0`, returns
   `record+4`). The DSP5 routing object has its own pair at its vtable byte
   0x10 = `0x34c1a8` (0xa9 entries) and byte 0x18 = `0x34c1f4` (0x4bb entries,
   table at `[routing+0x38]+0xa90`).
3. Vtable geometry (byte-pinned quads): DSP4 routing vtable at `0x9cfd78`:
   slot bytes 0x0/0x8/0x10/0x18/0x20 = `0x412c4/0x412fc/0x41334/0x41380/
   0x413d0` (so `0x41334` is the slot at byte 0x10 and VSubProc 0x413d0 the
   slot at byte 0x20, matching run 8's dispatch anchor). DSP4 ctor `0x41288`
   tail stores it: `0x041224 adrp x8,#0x9cf000; 0x041228 add x8,x8,#0xd78;
   0x04122c str x8,[x19]`. DSP5 ctor `0x34bf7c` tail stores its own:
   `0x34c0b8 adrp x8,#0xa52000; 0x34c0bc add x8,x8,#0xe98; 0x34c0c0 str
   x8,[x19]` — vtable at `0xa52e98` (quads `0xa52e98..0xa52eb8` byte-pinned,
   byte 0x20 = `0x34c244` = DSP5 VSubProc).
4. Caller census: whole-image BL decode (both 0xfba10/0xfba11), aligned quad
   scan, adrp+add scan, then the strict virtual-call pattern scan at every
   4-byte offset and manager-global (`adrp x, 0x9c8000; ldr x,[x,#0x480]`)
   attribution within 40 instructions.

## Evidence

Real tool output (pinned image, command above), trimmed to the relevant keys:

```json
{
  "anchors_checked": 76,
  "anchor_problems": [],
  "adrp_add_candidates": [],
  "direct_bl_callers": 0,
  "direct_bl_sites": [],
  "aligned_pointer_quads": ["0x9e54d0"],
  "manager_global_call_sites": ["0x354388", "0x3543a0", "0x3543b8", "0x3543d0", "0x3543e8"],
  "manager_pointer_table_quad": "0x9e54d0",
  "virtual_call_sites_slot_c8": 162,
  "ok": true
}
```

The five manager-global call sites sit in the function at `0x354184`, which
loads the manager global in its prologue (`0x3541a4 adrp x8,#0x9c8000; 0x3541a8
ldr x8,[x8,#0x480]; 0x3541ac ldr x8,[x8]`), takes an object with a parameter
descriptor at `[x0+8]`/`[x0]`, and applies a list of (symbol, value) pairs,
calling the write path per pair:

```text
0x354394  ldp  x0, x8, [x19]      ; x0 = manager-derived object, x8 = symbol
0x354398  ldr  x1, [x8, #0x10]   ; symbol fields used by the lookup helper
0x35439c  ldr  d0, [sp, #8]      ; the value
0x3543a0  ldr  x8, [x0]
0x3543a4  ldr  x8, [x8, #0xc8]   ; vtable byte 0xc8 = WriteDspCoefFloat
0x3543a8  blr  x8
```

(x8+0x10/+0x18/+0x20/+0x28 symbol-field offsets across the five sites, values
from `[sp]`..`[sp, #0x20]`.) This function shape matches a parameter-apply
entry: the caller supplies the object and per-parameter symbols/values.

## Established

- `WriteDspCoefFloat` is **runtime-reachable stock code**: five virtual call
  sites through the manager vtable byte 0xc8 in the parameter-apply function
  `0x354184`, plus the function-pointer entry at `0x9e54d0` (table reference;
  whether that table is also used for calls is unchecked).
- The write path's record keys come from symbol descriptors (`x1`), not from
  immediates at the call sites, so the four gate record keys run 9 decoded
  (`0x0000`, `0x07c4`, `0x4fce`, `0x4d02`) are *writable* through this path;
  which symbols the stock parameter stream carries is a runtime question.
- The bypass gate (+0x678, keys `0x07c4`/`0x4d02`) is therefore runtime-writable
  through the stock coefficient path — the gate is not frozen at construction.

## Not established

- Whether the stock application ever flips the bypass gate nonzero during
  normal operation: the five call sites prove reachability and call shape, not
  which symbols flow through them at runtime (needs the unit or a runtime
  capture; a full provenance trace into the parameter/UI layer was out of
  scope for this run).
- What the manager function-pointer table at `0x9e53f8..` is used for beyond
  holding `0xfba10` at `0x9e54d0` (its references were not recovered; the
  adrp+add scan found none, so loads through other bases are possible).
- Whether any of the other 157 strict slot-0xc8 call sites also reach
  `WriteDspCoefFloat` (they call *some* object's vtable byte 0xc8; only the
  five loading the manager global are attributed here).
- The symbol-descriptor key space: `u32[[symbol+0x10]+4]` was not decoded for
  the runtime symbols (that requires the runtime parameter stream).

## Corrections to earlier notes

Run 9's note `docs/routing-gate-writers-study.md` said the write path reaches
the lookup helpers through "routing vtable slot 4 = 0x41334". The vtable byte
offsets are 0x10 (0x41334) and 0x18 (0x41380); slot numbering by 8-byte index
makes 0x41334 "slot 2", and run 9's "slot 5 = 0x41380" is slot 3. That note
also called 0x41334 "slot 4" while its own quad anchor at `0x9cfd88` sits at
vtable byte 0x10 — the anchor bytes were right, the slot names were wrong. This
run also found the DSP5 routing vtable pointer is `0xa52e98` (ctor bytes at
`0x34c0b8..0x34c0c0`), not `0xa520e98` as run 9's prose said; the anchor bytes
there were right too. Both prose errors are corrected in that note.

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/routing_gate_callers_study.py --json
/path/to/.venv/bin/python -m unittest discover -s tests -p test_routing_gate_callers_study.py -v
```

The tool exits 0 only when all 76 anchors match, the manager global call sites
are exactly the five expected, and no direct BL callers exist. Tests: with the
corpus the pinned-image class runs (anchors, no-direct-callers, table quad,
call-site equality, clean report); without the corpus 3 pass and the
pinned-image class skips cleanly.

## Best next item

Trace the parameter-apply function `0x354184`'s callers to name the stock
entry that drives coefficient writes (purely static), or decode the
symbol-descriptor key field `u32[[symbol+0x10]+4]` for the symbols the
parameter stream carries, binding the gate keys `0x0000/0x07c4/0x4fce/0x4d02`
to named stock parameters.