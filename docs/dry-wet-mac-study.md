# Dry/wet MAC pair

2026-11-09. This extends [the gain-control study](alu-controls-study.md) by comparing
the preceding dry/wet stage with native expressions. It uses the same locally prepared
ZENOLOGY arm64 artifact. No plugin or hardware code is executed.

## Result and exact scope

The following **control/extension pairs in the observed header contexts** match the
functional dry/wet equations in FETDRIVE and LINEDRIVE:

| Form | Supported functional interpretation |
|---|---|
| Base `080b`, extension `13c0` | Main A = input port 0 × port 3 + port 1 × port 7 |
| Base `490b`, extension `53c0` | Main B = input port 4 × port 3 + port 5 × port 7 |

The header assigns those base words to family 0. Each extension is the first word of
the common operand pool in these particular packets; other memory transfers in the
packet index subsequent pool words. `command_count()` still counts base control words,
not extension words. The interpretation is **not** assigned to every occurrence of
the same base word, different extensions, or different header families.

The experiment compares the entire dry/wet expression followed by the two final gains,
not only a matching master-volume factor. It finds two supported class examples and
one explicitly unsupported variant among the three classes containing both base words.

## Expressions that matched

Let `L/R` be the current audio inputs; `W(a)` the prior computed wet result loaded from
data-memory address a; and `Ck` the live coefficient at slot k relative to the native
constructor's coefficient-base parameter.

| Class | Left output | Right output |
|---|---|---|
| FETDRIVE | `(L*C2 + W(0x17)*C3) * C4 * C0` | `(R*C2 + W(0x18)*C3) * C4 * C0` |
| LINEDRIVE | `(L*C3 + W(0x29)*C4) * C5 * C0` | `(R*C3 + W(0x2a)*C4) * C5 * C0` |

FETDRIVE's selected packet sequence starts at relative `0x16a`; LINEDRIVE's at `0x1e2`.
These are offsets within the logical primary program image, not CORE1 runtime addresses.

The dataflow is sufficiently asymmetric to distinguish the dry and wet coefficient
roles: replacing the dry coefficient with the wet coefficient changes the symbolic
polynomial, even if their current numerical values happen to match. Left/right signal
identity is derived from the native input/output argument pointer paths rather than
assuming a fixed floating-register assignment.

## How it is checked

`tools/mac_study.py` first recognizes a tightly bounded six-packet family:

1. Load left input and dry coefficient into ports 0 and 3.
2. Load left wet state and wet coefficient into ports 1 and 7.
3. The `080b/13c0` operation, followed by right input/state loads into ports 4 and 5.
4. The `490b/53c0` operation, followed by loading the post-effect gain into port 3.
5. A shared port-3 gain pair, then load the final master coefficient into port 3.
6. Another shared port-3 gain pair.

Headers, control ordering, extension values, input slots and operand tags must match
this observed family. The two wet addresses must differ and all four coefficient
indices must differ. This restriction supplies independent symbolic variables instead
of inferring semantics from coincident numerical defaults. It is intentionally not a
general MAC decoder.

The native side reuses the gain study's direct Capstone register/pointer provenance
reader. Constructor calculations independently prove the coefficient-record pointers.
For this experiment it additionally preserves the expression trees for floating add
and multiply-add and labels audio input reads.

The two wet-state addresses are explicit **cut points**: reads through the observed
data-array path are independent `W(a)` variables. This avoids assuming that the earlier
distortion/filter implementation has been decoded. A matching integer address loaded
through an unrelated pointer path does not qualify. Other unresolved reads or
arithmetic remain opaque and cause the comparison to stay unresolved.

Both output expressions are normalized to bounded polynomials of those independent
signal/coefficient variables. Their complete terms must agree: each output has two
terms, one dry and one wet, with the correct three coefficient factors. No search over
coefficient assignments or arithmetic formulas is performed.

## Counterexamples and remaining work

LFCOMP contains the same two base words but extensions `1280` and `5280`, and a different
surrounding operand pattern. Its result is **unsupported encoding family**, not
"matched" and not a contradiction of the narrower `13c0/53c0` interpretation.
SPACED contains repeated `080b` forms with `43c0` and no paired `490b` form; it falls
outside this paired-family selection. Extension/register bitfields still need decoding.

Formal polynomial equality ignores finite-precision rounding and fused versus
unfused arithmetic. It does not establish whether silicon computes a single FMA,
multiple multiplies/adds, a particular accumulator width, or a particular issue schedule.
The shared model remains bounded static def/use rather than a path-sensitive ARM64
interpreter. Hardware timing, saturation, wrapping and side effects remain unknown.

## Reproduce

From the project directory with local artifacts and Capstone prepared:

```sh
python3 tools/mac_study.py
python3 -m unittest discover -s tests -p test_mac_study.py -v
```

The detailed expressions and function ranges go to ignored `local/mac_study.json`.
Seven tests cover exact-family recognition, rejection of another extension, swapped
coefficient roles, algebraic load-order independence, original synthetic ARM64 FMUL/FMA
provenance, rejection of an unresolved wet-state anchor, and the local paired classes.
The native and corpus-dependent checks skip cleanly without their dependencies.
