# Short-add candidates: field bindings and remaining source ambiguity

Follow-up: [OSC bias/add and fold](osc-bias-wrap-study.md) now binds the hoisted quarter, preceding P5 producer, isolated add cutpoint and folded stores. One exact 52-byte profile is admitted; the inventory and other short-add candidates below retain their original limits.

2026-11-10. The complete TRANSIENT reference exposes a useful constant-add
candidate around `5d72`, but the same 16-bit word is also a long operation
elsewhere. This pass binds the short operand to its actual constructor field,
inventories independent contexts, and retains the missing arithmetic/port proof.
This inventory alone admits no opcode. The later
[auxiliary/add-MAC study](auxiliary-save-restore-and-add-mac.md) binds the first
FDRV state/filter sums and admits one exact composite profile. It does not define
these short words globally; the later exact cubic profile supplies its own
separate producer/port proof.

The [184-byte filter profile](fdrv-state-variable-filter.md) also covers that
first pair's producer arithmetic and balanced auxiliary saves. It verifies the
complete component's state/output recurrence without admitting the other
short-add contexts or a universal instruction definition.

The [FDRV cubic study](fdrv-cubic-waveshaping-study.md) now binds four complete
waveshaping windows to their source/result stores and checks the native curve
directly on 1,034 inputs. It locates the two cubic `5d46` candidates among the
six FDRV observations and admits one exact 126-byte profile; arbitrary
individual-word meanings remain unproved.

`tools/short_add_context_study.py` pins native SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
It examines the catalogued primary render program for each class; 18 entries
without a render program are recorded as skipped. Repeated A/B banks are not
counted as independent algorithms.

## Same word, different operation family

For masked controls `1d40/3d40/5d40/7d40`, the inventory finds:

| Classified operation family | Candidate words |
|---|---:|
| Long arithmetic, family 0 | 23 |
| Short arithmetic, family 1 | 15 |
| Miscellaneous, family 2 | 1 |
| Header family unresolved | 9 |

The 15 short observations span nine classes. FDRV contributes six `5d46`
contexts; PHONO contributes two. ROT has `5d44`; GASSPH, GAMPSIM and GASSDLY
have `5d52`; OSC has `5d50`; PH100 has `1d78`; TRANSIENT has `5d72`.
The regular short reference fields select register index 6 for `5d46`,
register index 4 for `5d44`, two-byte -.25 for `5d52`, two-byte .203125 for
`5d50`, four-byte zero for `1d78`, and the four-byte decay increment below
for short `5d72`. These are operand references, not recovered source-register
semantics for the arithmetic.

Two concrete counterexamples prevent word-only decoding:

- TRANSIENT packet `3e` has long-family `5d72`; packet `fc` has short-family
  `5d72`. Their payload/extension syntax differs.
- OSC packet `27a` has short-family `5d50`, whereas JDMLT packet `c` uses
  exactly `5d50` in miscellaneous family 2. Its operand remains opaque.

PH100's selected literal is zero. A numerical identity there cannot distinguish
addition from several other operations, so this observation is not an independent
arithmetic proof. Unresolved headers never acquire short syntax by resemblance.

## TRANSIENT's native default is actually bound to the program field

Packet `fc` has known family ordering `(1,2)` and controls `5d72 / f510`.
The ordinary short reference in `5d72` selects four bytes at relative `104`.
Those bytes decode to `-0.0004233471117913723`.

The reconstructed constructor record at object+`70` names exactly relative
`104`; its double at +`78` is `-0.0004233471397304735`. Native load `1d62e8`
reads that double. The preceding data access uses constructor field `1d4`,
which binds packet field `fa` to logical cell 30. Native `FADD` at `1d62ec`
therefore computes **old cell 30 plus that constructor default**. The checker
verifies the record, native pointer/index roots and exact instructions.

The two numbers differ by `2.793910120944251e-11`, below the field's `2^-32`
quantum. Exact equality between a native double and truncated serialized literal
is not required for this existing constructor-to-field check. Their different
precision does not disprove the binding and must not be silently erased.

The co-issued miscellaneous `f510` and following `d547` still prevent assignment
of an isolated `P5 += literal` operation. The native sum is not separately stored
before its maximum/clamp combination. Exact source/destination-port identity and
other co-issued effects remain unproved. The complete mixed packet stays outside
`header_study.layout()`; its known short field is reported without pretending the
remaining packet has been decoded.

The independently decoded native clamp constant is
`c01ba18a998fffa0 = -6.907755278982137`. The packet's two-byte `c6e8` decodes
to -6.90625. These are separate from the small four-byte decay increment.

## Additional native addition candidates

The checker also verifies actual native immediate definitions and `FADD`
instructions with the corresponding short literal values. The
[negative-bias follow-up](negative-short-add-study.md) corrects an important
ambiguity: each negative-literal context has two uses of the same immediate.
The first use listed in the original inventory was not a unique opcode binding.

| Class | DSP packet | Native constant definition | Native add candidates | Value |
|---|---|---|---|---:|
| OSC | `27a` | `2974c` | `29750` | .203125 |
| GASSPH | `25c` | `14a62c` | `14a630`, `14a680` | -.25 |
| GAMPSIM | `2a4` | `324f84` | `324f88`, `324fe8` | -.25 |
| GASSDLY | `240` | `2fa1b0` | `2fa1b4`, `2fa200` | -.25 |

These strengthen the additive hypothesis across different values and algorithms.
This inventory does not bind each native input value to a particular DSP
arithmetic port. The OSC follow-up supplies its separate exact-profile proof;
the negative-bias study verifies both native chains and 13 Fantom neighborhoods
without assigning either add uniquely to `5d52`.
The FDRV callback is branch-free. Its four cubic input/result cutpoints are now
bound in the follow-up above. The earlier four `5d46` state/filter sequences
still need their auxiliary-port inputs and coissued-store relations resolved.

## Reproduce and reviewed Qwen result

```sh
python3 tools/short_add_context_study.py > local/short-add-context-study.json
python3 -m unittest discover -s tests -p test_short_add_context_study.py -v
```

Use the existing Capstone-capable interpreter. Three tests cover family collisions,
unknown/truncated input and the real corpus counts/bindings. Detailed inventory
output remains local; no vendor code is repackaged.

Qwen returned in 89.8 seconds but searched TRANSIENT rather than the requested
class catalogue, misassembled the clamp constant and rejected the native/literal
binding because the values were not identical. Independent review rejected those
claims and reproduced the correct catalogue and precision-aware binding above.
No worker analysis code or unsupported arithmetic assignment was accepted.
