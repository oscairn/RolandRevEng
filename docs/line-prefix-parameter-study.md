# LINE prefix parameters: counted literal groups and the remaining alias gap

2026-11-10. **Grouped literal writes are real, but the inspected LINE setter
descriptors do not connect prefix fields `14/17` or `24/27`.** The new checker
separates a declared group from two adjacent records and follows the native and
firmware write mechanisms. No new DSP arithmetic/control semantics or interpreter
fragment is admitted.

This extends the [prefix ownership finding](emulator-next-program-targets.md).
Addresses and unprefixed offsets are hexadecimal; descriptor counts are decimal.
Evidence is offline bytes/Capstone, without REA, plugin/firmware execution, device
access or payload modification. Pinned inputs:

| Artifact | SHA-256 |
|---|---|
| Prepared ZENOLOGY arm64 | `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30` |
| Fantom bmc0 header-stripped CORE1 | `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154` |

## Actual native LINE literal-call inventory

The checker scans the contiguous `CFspMfxLINEDRIVE` method bodies
`17ca58..17d2ec` for loads of manager virtual slot `c8`, then follows the loaded
target and the symbol argument through the bounded straight-line ADRP/ADD path
to its call. It rejects a clobbered target/argument or intervening branch/call.
The three resulting sites are:

| Method / slot load / call | `_CoefSym` | Declared count | Relative literal fields / width |
|---|---|---:|---|
| `SetAlg`, `17cafc` → `17cb08` | `a16df8` | 4 | `ec,f0,118,11c`, each width 4 |
| `SetAlg`, `17cb4c` → `17cb58` | `a16e18` | 4 | `e6,e9,112,115`, each width 3 |
| `SetType`, `17d120` → `17d13c` | `a17248` | 1 | `45`, width 3 |

The first two descriptor arrays begin at `7b4c8c` and `7b4cbc`; the last begins
at `7b4ec0`. These are program-literal descriptors, distinct from the live
`_DataSym`/envelope interface used by other LINE parameter paths. Neither counting
nearby data nor searching setter names supplies a fourth literal call.

This is an inventory of the **direct slot-c8 operations in those bodies**. It is
not an exhaustive traversal of every external interface, constructed descriptor,
raw writer or indirect call reachable elsewhere in the application. The direct
call at `17ceb8`, for example, is the exported `CDSPWait::WaitXsample` at `2a5938`;
it must not be confused with a program-literal write merely because it occurs in
`SetAlg`. No virtual slot per individual literal is implied by this inventory.

## Why one native representative can model a declared group

In this LP64 image, the observed `_CoefSym` pointer at symbol+`10` selects an
array of 12-byte records; byte symbol+`18` is its count. The records in this study
contain an absolute program-byte field, relative program-byte field and
width/segment metadata. The checker supports only the observed segment-0 widths
2/3/4 and fails closed for other metadata; it is not a general `_CoefSym` decoder.

Native `CSimDspMgr::WriteDspCoefFloat` at `fba10` checks the count is nonzero,
obtains its simulator object and makes **one** virtual getter call at `fba68`.
When the result is nonnull, `fba70` stores one saved double through that pointer.
The manager vtable at `9e53f8` selects this implementation at slot `c8`.

The LINE simulator vtable at `a49620` selects `GetCoefAdrs` (`2df728`) at slot
`10`. That getter loads the descriptor array from symbol+`10`, reads **its first
record's** relative field, compares it against eight constructor records and
returns the matching double. It does not independently visit all descriptor entries.
Independent reconstruction of constructor `2dfe04..2e0248` yields:

| Declared group | Representative relative field | Native double field |
|---|---|---|
| Four width-4 fields | `ec` | `+8` |
| Four width-3 fields | `e6` | `+18` |
| Type field | `45` | `+28` |

These are concrete positive controls for the representative mechanism: a declared
four-record parameter operation reaches one native double selected by its first
record. In particular, they establish the grouped parameter relation for the later
rational-shaping duplicates: `ec/f0/118/11c` share the first declared operation,
and `e6/e9/112/115` share the second. The extra program literal fields need not
each have a separate native record for that operation. This does not establish that arbitrary equal defaults,
adjacent fields or the particular prefix pairs share a parameter.

Native manager program-load slot `50` resolves to the immediate return at
`fd570`. This native path does not execute/upload the DSP packet bytes and cannot
itself reveal how a hardware instruction treats duplicated literal fields.

## Firmware really walks the declared count

Assertion-linked `CBmcDspMgr::WriteDspCoefFloat` at `011327e6` uses the ARM32
descriptor layout: array pointer at symbol+8 and count byte at symbol+c. It saves
the input float in s16 at `011327f0`, establishes a zero loop index and then:

1. Forms `3*i` at `0113285a` and accesses records using that value scaled by four,
   producing a **12-byte stride**.
2. Resolves the record's absolute/owner-relative program byte address and its
   segment selection. This remains subject to the owner descriptor's bounds.
3. Reloads width byte record+8, copies the same saved s16 into s0 at `011328bc`,
   and calls literal-write driver `0112ff4e` at `011328c8`.
4. Increments the index at `011328ce` and branches back while index<count at
   `011328d2`.

Thus a declared multi-record operation requests the same float for each selected
literal field, while the desktop implementation can update a single representative
double. Different field widths can quantize a requested value differently; this
is not a proof of bit-identical native/hardware values, atomic application across
records, audio timing or completion. Nor does the generic loop prove that these
native pointer values or every native LINE group are the actual Fantom call inputs.

## Prefix pairs still lack that descriptor relation

The prefix has distinct width-3 fields `14` and `17`, both stored as zero, and
`24` and `27`, both stored as one. The native constructor owns representatives
`14 → +58` and `24 → +78`; no matching record for `17` or `27` was identified.
The three inspected LINE literal groups above contain **none of these four
fields**. Therefore the newly recovered count mechanism does not close their
specific ownership/alias relation.

A concrete negative control prevents a common false inference. Elsewhere in the
same native image, adjacent records at `7ed710`/`7ed71c` have relative fields
`14`/`17`, but symbols `a3f560` and `a3f580` each declare **count 1**, pointing to
one record apiece. The same count-1 arrangement occurs at `839050`/`83905c`, via
symbols `a51e08`/`a51e28`. They are not among LINE's three scoped call arguments.
Adjacency is not a count-2 group, and matching relative offsets do not establish
ownership by the LINE program. The synthetic test checks this distinction directly.

The missing representative is not an uninitialized native variable or evidence of
zero state. These are program-relative **byte offsets**, not physical DSP register
addresses; the four stored DSP default values are already known. It is the rule
linking their possible changes that remains unproved. The prior tied-versus-split
coefficient counterexamples still apply: equality at defaults does not distinguish
those models.

The independently checked destination identities remain `32 → object+8c →
2df8c4` and `34 → object+94 → 2df8d8`. They establish native store locations,
not the source-port state/capture timing of DSP `afe0/bfe2`. The co-issued C2 load
also remains part of the outgoing state. No store-order conclusion was added here.

The smallest additional proof is an actual LINE-owned descriptor/grouped-write
path for the missing fields, or a source/generator rule establishing them as fixed
constants or canonical representatives. An instruction/model implementation that
exposes both references independently would also distinguish the hypotheses.
Arbitrary external/raw writers and other configurations are not excluded by this
scoped setter inventory. The prefix and complete program remain unadmitted.

## Verification and Qwen review

```sh
python tools/line_prefix_study.py local/zen_arm64 --core1 local/b0c1a.bin > local/line-prefix-parameters.json
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests -p test_line_prefix_study.py -v
```

All three tests passed with Python 3.13.7/Capstone 5.0.7 and the recorded inputs:
descriptor-count/bounds/unsupported-metadata rejection, actual native groups and
representatives, and the firmware count/stride/saved-float loop. Detailed generated
reports and disassembly remain ignored/local; neither vendor data nor a new payload
is committed.

The serialized no-tools Qwen review completed successfully and supported the
conditional grouped-write explanation and scoped conclusion. Independent review
rejected its statements that missing native records are uninitialized/zero, that
the prefix pairs are already grouped in a native simplified view, and that these
byte offsets should be resolved as hardware register addresses. Its proposed
per-literal virtual-slot reasoning was also unsupported. No model-only alias or
opcode assignment was used.
