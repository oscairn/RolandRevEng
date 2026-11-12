# OSC bias/add and signed32 fold: exact executable profile

2026-11-11. `osc_bias_wrap` adds one constrained profile to the offline emitter and
interpreter, bringing the subset to **19 exact sequence profiles**. Its 52 logical/
stored bytes comprise a 10-byte authored preload and 42 stock bytes at OSC
`264..28e`. The body matches the desktop program and all four checked Fantom OSC
placements. **8,460 native cutpoint comparisons pass**, including whole-ring
write checks. This is functional software evidence, not BMC silicon execution or
a complete oscillator/engine.

The [earlier short-add inventory](short-add-context-candidates.md) located the
`.203125` literal and native FADD but left its port context unresolved. This study
binds its preceding producer, isolated add cutpoint, following fold and stored
outputs. Header family, extension, packet order and resources remain part of the
admission. The same `5d50` word in JDMLT's miscellaneous family remains unsupported.

## Sources and the hoisted constant

Native SHA-256 is
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom CORE1 retains its existing pinned identity. `tools/osc_bias_wrap_study.py`
checks both sources, constructor data records, exact native instructions and
packet bytes. Evidence is file/Capstone analysis and private macOS ARM64 native
execution, not REA Evidence records. Vendor bytes/listings stay ignored/local.

The native arithmetic immediately before the add looks like:

```text
29744: multiply the first loaded value by 3
29748: FMA(second loaded value, retained d0, scaled first)
2974c: define .203125
29750: add .203125
```

The multiplier `.25` is defined earlier at `29590`. Register-preservation checks
prove d0 retains it through `29748`. Treating d0 as another input signal obscures
the correspondence with long packet `272`; the native compiler has hoisted the
literal. Constants3, .25 and .203125 are exactly representable in the packet fields.

## Admitted packet sequence and ports

Addresses and words below are hexadecimal. P0..P7 are functional ports under the
existing model, not independently identified physical registers.

| Packet | Exact control context | Checked effect |
|---|---|---|
| Authored preload | `1e05 / 4fe0 / 2fe2` | Load P4 from first source and P2 from an explicit marker source |
| Stock264 | `3407 / 5510 / afe2 / 4fe4`, literal `4300` | P5=3×old P4; store old P2; load future P4 from second source |
| Stock272 | `0804 / 5512 / 0005 / 2400` | P5=FMA(P4,.25,P5) |
| Stock27a | `0903 / 5d50 / 2340` | P5=P5+.203125 |
| Stock280 | `0a02 / dee5` | Apply the checked native signed32 normalization to P5 |
| Stock284 | `1e05 / dfe0 / dfe2` | Store folded P5 into two distinct output cells |

All six source/target addresses must be distinct and below `0x800`. The sources
are first input, second input and marker; targets are saved marker and two folded
outputs. Literal/control changes, different headers/extensions and resource
aliases fail closed. The emitter does not offer arbitrary bias/scale parameters
or admit these control words outside the complete sequence. The generic layout
checker still rejects miscellaneous-operation syntax.

For the desktop body, constructor fields bind:

| Native context field | Program field | Data cell | Native access |
|---|---|---:|---|
| `1fc` | `262` | 9 | Read at2972c |
| `204` | `270` | a | Read at2973c |
| `1c4` | `26e` | 2 | Marker store at2971c |
| `1cc` | `28a` | 3 | Output store at297b4 |
| `1f4` | `28c` | 8 | Output store at297c4 |

The marker source in the authored preload is synthetic. In the stock callback,
that register holds a value produced earlier. The native fixture supplies its
incoming value explicitly and uses asymmetric markers to distinguish its store
from the arithmetic result. This does not execute or admit the earlier oscillator
control packets. Four Fantom body matches provide additional address placements;
the existing five FDRV resource layouts are a separate count.

## Numeric contract and edge behavior

Under the explicit binary64/native-FMA reference policy:

```text
scaled = 3 * first
mixed  = fma(second, .25, scaled)
biased = mixed + .203125
output = normalize_phase_sum(biased)
```

Each intermediate must be finite, and `abs(biased) < 2**31`. The final function is
the [previously checked native signed32 fold](oscillator-phase-study.md), not an
unqualified mathematical modulo operation. It preserves -1, maps positive odd
integers to -1, and maps negative odd integers below -1 to+1. Near the signed32
limit its integer-normalizer wrap can produce values outside the bipolar range:
`2**31-1` produces `2**32-1`, with the corresponding negative case too. Those
quirks are retained and tested rather than silently replaced by an ideal wrap.

This policy does not establish BMC accumulator width, rounding, saturation, FMA
fusion, execution latency or physical coissue timing. Non-finite inputs, overflow
and out-of-domain normalization are rejected. Caller dictionaries are not mutated.
The unchanged FDRV arithmetic/reference chain retains its own literal policies.

## Independent native and rejection checks

There are 141 input triples: 128 deterministic asymmetric random cases and 13 exact
boundary constructions. Qwen's boundary-input draft returned in 4.8 seconds; its
construction/equality filter was reviewed and retained, with sorted deterministic
output. Cases whose subtraction/addition did not exactly reconstruct the intended
boundary were not mislabeled as boundary tests.

For each input, five resource assignments (desktop plus four Fantom placements)
and origins0,1,2047 are checked at four native endpoints: scaled first, FMA sum,
biased sum and final fold/stores. The pinned branch-free native interval is copied
into private executable memory with its checked original pointer setup and literal
loads. Two decoded register-copy bridges supply the marker and return the first
cutpoint. No external call, branch or arbitrary program bytes enter that interval.
Every native call also compares all 2,048 ring cells, catching unintended writes.

The interpreter's packet cutpoints, old-value marker store and both outputs match
that independent reference. Negative tests alter headers, controls, extensions and
literals; reject aliasing and invalid addresses; preserve the JDMLT family collision;
and exercise invalid/overflowing numeric input. A different source image fails its
hash gate before native execution.

```sh
python3.13 tools/osc_bias_wrap_study.py --core1 local/b0c1a.bin --execute-native
python3.13 tools/bmc_subset.py assemble examples/osc-bias-wrap.json local/osc-bias-wrap.bin --stored
python3.13 tools/bmc_subset.py disassemble local/osc-bias-wrap.bin --stored
PYTHONPATH=tools:tests python3.13 -m unittest test_osc_bias_wrap test_bmc_subset test_bmc_emulator test_fragment_emulator_corpus test_oscillator_phase_study test_short_add_context_study -v
```

The example's marker cell2047 is an offline assignment, not evidence that this
cell is free or safe to borrow on the instrument. No whole-graph allocator, voice
planner integration, entry/return wrapper or hardware loader is supplied here.
General `5d4x`/`5512` semantics and arbitrary `dee5` contexts remain unproved.
Next seek independent negative-literal short-add/source-port contexts or another
self-contained OSC arithmetic window; preserve these exact-context boundaries.
