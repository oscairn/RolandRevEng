# Negative literal adds: paired native chains and unresolved DSP routing

2026-11-11. This pass corrects an ambiguity in the
[short-add inventory](short-add-context-candidates.md): GASSPH, GAMPSIM and
GASSDLY each contain **two** native adds of the same `-.25` constant. The old
inventory listed only the first. A matching constant and adjacent `FADD` do not
uniquely bind short `5d52` to that instruction.

The new checker verifies both native dependency chains, including the reused
constant across compiler interleaving. Its numerical reference matches 8,430
original ARM64 cutpoints. The Fantom image has 13 matching packet neighborhoods
and four additional uses under an unresolved header. These results add no DSP
execution profile; the subset remains at 19 exact sequences.

## The corrected native candidates

`tools/negative_short_add_study.py` pins desktop image SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
It independently reconstructs the stream and native callback for each class.

| Class | Known short packet / literal field | Earlier literal context / field | Native constant definition | Both native adds |
|---|---|---|---|---|
| GASSPH | `25c / 266` | `236 / 240`, control `1c90` | `14a62c`, D16 | `14a630`, `14a680` |
| GASSDLY | `240 / 24a` | `21c / 226`, control `1c90` | `2fa1b0`, D7 | `2fa1b4`, `2fa200` |
| GAMPSIM | `2a4 / 2ae` | `27e / 28a`, control `0d90` | `324f84`, D18 | `324f88`, `324fe8` |

The short packet has family ordering `(1,1,4)`, controls
`1e50,5d52,3fe4` or `0e10,5d52,3fe4`, and pool words
`3c00,a400,<resource>`. The ordinary short reference in `5d52` selects the two
bytes at pool offset 2: `a400 = -.25`.

Each earlier context also contains `a400`, but its header remains unresolved.
The checker verifies its location and the presence of `1c90`/`0d90`; it does
**not** assign that word short syntax or claim that it consumes that literal.
Likewise, `ded4`, `9450`, `d550`/`d554` and their side effects remain unresolved.

There is a plausible two-channel alignment: the earlier context produces the
first magnitude/bias path and `ded4` produces the later path consumed by short
`5d52`. The native compiler interleaves these operations. That alignment still
needs independent DSP source/port proof; neither native register numbering nor
the order of native instructions supplies it. Both add addresses remain explicit
candidates in the machine-readable inventory.

## What the native arithmetic does prove

Both chains compute, in this order:

```text
clipped   = clip(input, -1, 1)
magnitude = clipped if clipped >= 0 else -clipped
biased    = magnitude + (-.25)
floor     = max(biased, 0)
gain      = 1.75 - floor
```

This is the gain curve used by the surrounding waveshaping arithmetic. It is
1.75 through the central quarter and falls to 1 at either clipped endpoint.
The magnitude selection deliberately preserves negative zero, matching native
`FCMP/FCSEL`. The checker does not replace it with a library absolute-value call.
Full channel multiplication, upstream production, following mixes and memory
effects are outside this probe.

For all six chains, the checker verifies the actual `FMIN/FCMP/FCSEL`,
`FNEG/FCMP/FCSEL`, `FADD`, `FMAXNM` and `FSUB` operands. It checks that constants
and intermediate registers survive every omitted instruction between dependent
uses in the original callback. In particular, each second add reuses the original
`-.25` definition; it does not introduce a second immediate definition.

The execution fixture copies these checked register-only dependency slices into
private memory, with checked `FMOV` argument/result bridges and a return. It runs
five cutpoints per chain on 281 inputs: 256 deterministic random values and 25
boundary entries, including both signed zeros, subnormals, neighbors of the
quarter and clip thresholds, and maximum finite magnitudes. All **8,430** results
match the independent scalar reference bit for bit under the native binary64
policy. This is a dependency-slice test, not execution of a whole native callback,
DSP packet stream or physical BMC.

## Fantom correspondence

The pinned Fantom CORE1 image is
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
A framed scan examines 377 render segments / 36,793 packets and finds 17 base
control uses of `5d52`:

| Neighborhood | Descriptor | Placements |
|---|---|---:|
| GAMPSIM | `610eb860` | 5 |
| GASSDLY | `610f53b4` | 4 |
| GASSPH | `610f9bec` | 4 |
| Unresolved `5e09` packet | `610f09c4` | 4 |

The 13 known matches preserve the entire preceding, selected and following
packet after substitution of explicitly named resource words. They represent
three contexts repeated at different placements, not 13 independent algorithms.
This comparison does not assign ownership of the fourth descriptor or give its
`5d52` short syntax. Its header and neighboring controls differ, so it stays in a
separate unresolved list. These are the catalogued render segments in this one
image; other BMC cores and firmware versions are outside this scan.

## Reproduce and next discriminating evidence

```sh
PYTHONPATH=local/fantom-python:tools python3.13 tools/negative_short_add_study.py --core1 local/b0c1a.bin --execute-native > local/negative-short-add/report-native.json
PYTHONPATH=local/fantom-python:tools:tests python3.13 -m unittest test_negative_short_add_study test_short_add_context_study -v
```

Capstone and the local pinned corpus are needed for static checks. Native
execution requires macOS ARM64 and executable private-memory permission. Two
pure tests run without vendor artifacts. Tests also reject changed controls,
truncated neighborhoods, the unresolved-header collision, changed image identity
and a clobber of the reused native constant. Detailed output and vendor data stay
under ignored `local/`.

Qwen returned an evidence review in 25.5 seconds. It incorrectly required native
temporaries to be stored to memory before they could represent functional DSP
ports, confused CPU registers with those ports, and misquoted an immediate
`FMOV` as a load. Those conclusions and its suggested opcode assignment were
rejected. The paired arithmetic and ambiguity above were independently checked.

The next useful proof is the exact operation-family/operand layout of the earlier
`5a`/`b1` packets and the `ded4`/maximum producer effects. It must establish which
clipped input reaches which functional port and account for coissued operations.
The second native add is a stronger lead, not an admitted `P5 += literal` opcode.
Silicon precision, latency, safe loading and engine entry/return remain separate
hardware requirements.
