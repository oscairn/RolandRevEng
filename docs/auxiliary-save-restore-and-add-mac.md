# Native auxiliary saves and a checked add/MAC profile

Follow-up: [stereo state-variable filter](fdrv-state-variable-filter.md) resolves
the first block's preceding producer arithmetic and admits a separate 184-byte
profile with one balanced auxiliary save/restore per port. The 84-byte add/MAC
profile below retains its narrower contract and executes no auxiliary words.

2026-11-10. Native ZENOLOGY arm64 SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Evidence is static Python/Capstone analysis and isolated native execution, with
no BMC hardware access, firmware installation or REA-provider claim.

**Result:** FDRV's auxiliary save/restore round trip preserves the current value
without adding a sample delay. This binds the restored sources in its first
short-add pair and the following multiply-accumulates. A new original 84-byte
`register_add_mac_pair` profile is emitted, inversely decoded and executed by the
strict interpreter. Its 56-byte arithmetic body exactly matches the corresponding
native-paired program and all five recorded Fantom placements. The leading 28
bytes are authored data loads to initialize its six live input ports.

## Native circular banks, not an inferred sample history

The FDRV callback obtains its owner through wrapper+8 then manager+18. Its first
two auxiliary paths use three doubles at owner+`80`/`100`, with cursors at
`98`/`118`. The static checker verifies both paths' exact instructions and retains
the owner, bank-pointer and cursor-register provenance.

For a valid cursor c in `0..2`, the observed operations are:

```text
save:    slots[c] = value; c = (c + 1) mod 3
restore: c = (c - 1) mod 3; value = slots[c]
```

A paired save and restore therefore return the just-saved value and the original
cursor. Repeated restores wrap; the native sequence has no occupancy counter.
This is a native reference model, not a recovered physical BMC stack depth or
overflow policy. The original save stores using the incoming cursor before any
normalization. Invalid native indices are excluded from execution and remain
unverified; the authored helpers reject them.

The matched DSP window has `af60/ef60` at packet `78` and `af61/ef61` at `a4`.
The port-2/port-6 associations are constrained by the preceding typed data loads
and the native saved values. The [TRANSIENT reference](transient-full-reference.md)
independently documents analogous round trips for two native banks. These
contexts support save/restore candidates; they do not license executing every
similar-looking word or every bank in an arbitrary program.

The native DSP4-core constructor at `16bb04` explicitly zeros thirteen equally
spaced cursor fields from `58` through `1d8`. Those stores establish cursor reset,
not zero values for all floating slots or a universal ISA register-bank map.

The primary-program inventory finds 118 candidate words across source-index
candidates `0/2/3/4/6/7`. Counts pair as 59 saves and 59 restores. These are
observations across catalogued primary streams, not proof of dynamic balance,
reachability or a general stack implementation. Two STEPFil short-family
`1f60` controls share the low pattern and are retained as counterexamples.

## First FDRV addition and store cutpoints

The checker binds the port-2/port-6 source loads through constructor records,
the unchanged values saved to the native banks, and the values restored into
native d5. That register remains intact through the additions below. It checks
the intermediate d2 stores, each following native FMA and each final main store.
The native live-coefficient reader independently identifies slot `d` (13) on
both channels.

| Path | Saved source load / cell | Store before short add / cell | Native add | Native MAC | Following main store / cell |
|---|---|---|---|---|---|
| Left | `3051ec` / `29` | `3052ac` / `28` | `3052bc` | `3052c0` | `305398` / `24` |
| Right | `3052d0` / `2c` | `30537c` / `2b` | `305388` | `30539c` | `3053ac` / `25` |

In the containing DSP context, short `1c42/5d46` at `c0` add the restored
port-2/port-6 values to the incoming port-1/port-5 values. The coissued
`9fe0/dfe4` stores retain the **incoming** values, before those additions.
At `de`, long `044b/0000` and `454f/0004` use the sums to update main A/B.
Both possible coefficient ports carry the same coefficient, so port-3 versus
port-7 selection remains indistinguishable. The emitted profile preserves that
equality and does not generalize these words outside the checked context.

The other FDRV state/filter additions and PHONO remain separate follow-ups.
The [cubic windows](fdrv-cubic-waveshaping-study.md) have different producer
sequences and still lack a complete per-packet execution model.

## The original byte-executed profile

The schema is `kind`, ten `sources`, two `targets` and two `coefficient_slots`.
All twelve data indices must be distinct and in `0..7ff`; the coefficient slots
must be distinct and in `0..fff`. The source order is:

```text
[A, W1, S2, B, W5, S6, next_S2, next_S6, next_W1, next_W5]
```

The first coefficient is shared by both accumulations. The second is loaded for
following work. The two target cells capture W1/W5 unchanged. The arithmetic is:

```text
sum1 = W1 + S2
sum5 = W5 + S6
A = fma(sum1, float32(Ccurrent), A)
B = fma(sum5, float32(Ccurrent), B)
```

At completion, ports 1/5 contain next_W1/next_W5, ports 2/6 contain
next_S2/next_S6, and ports 3/7 contain float32(Cfollowing). The four packet offsets
are decimal `0/14/28/58`. Old values feed the arithmetic and stores; coissued
loads supply the next packet. No auxiliary save/restore words are executed by
this profile: the authored prelude supplies the already restored source values.

The numeric policy is explicitly the native binary64 addition/FMA reference,
with binary32 coefficient reads, requiring Python 3.13+. Other profiles retain
their existing policy. BMC precision, flags, physical register hazards and timing
are uncalibrated. The decoder rejects changed controls, extensions, coefficient
duplicates, tags, extra packets and out-of-subset resource assignments.

Fantom list `610e5a94` supplies five independently read body matches at program
bases `4020/8040/9040/a040/3020`. Matching stock bytes and resource substitutions
does not allocate those occupied owners or establish a load address, executable
wrapper, live graph or audio route. No complete FDRV program is emulated.

## Reproduce and verification

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/native_auxiliary_study.py --execute-native
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py assemble examples/register-add-mac-pair.json local/register-add-mac-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py disassemble local/register-add-mac-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_native_auxiliary_study.py' -v
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_register_add_mac_pair.py' -v
```

The 64-byte native cache fixture joins two separately checked original slices
with authored ABI moves and a return. Across 396 cases, all three cursors,
distinct old cache values and every surrounding canary byte agree with the
reference, including signed zero and minimum subnormals. It is a deliberately
isolated operation fixture, not an unchanged native callback.

The 32-byte native arithmetic fixture surrounds the actual adjacent FADD/FMA at
`3052bc..3052c4` with checked ABI moves and a return. All 1,024 asymmetric channel
results from the byte interpreter match this fixture bit for bit. Additional
tests cover every port/trace boundary, old stores versus new sums, five Fantom
body matches, input mutation, malformed resources, missing inputs, truncation,
changed instructions and finite arithmetic limits. No vendor code is committed.

Qwen returned the original circular-helper/test draft in 24.1 seconds. It wrote
two files in the checkout root despite the requested worker path; they were
inspected and moved into ignored worker output. Review retained the circular
copy/update logic, replaced overflow-prone `math.isfinite(huge_int)` validation
with the existing finite-number helper, and installed meaningful unittest and
native-execution checks. The firmware/ISA evidence and new emitter/interpreter
integration were independently derived locally. No unchecked worker claim was used.
