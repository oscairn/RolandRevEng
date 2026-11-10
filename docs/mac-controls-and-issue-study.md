# More MAC controls and same-packet store ordering

Follow-up: [stereo tap accumulation](stereo-tap-accumulation-study.md) verifies four
more long-control/extension pairs through six native stages, fresh live coefficients
and exact state-record aliases. No global register decoder or new emitter is admitted.

2026-11-10. Offline follow-up using the artifact identities in the main packet/loader
map. This extends the earlier gain and dry/wet MAC studies with independently matched
long controls and a correction to the symbolic model's transfer ordering. No plugin,
firmware or hardware code was executed.

## Results

The following meanings hold in the **exact packet families admitted by
`tools/mac_controls_study.py`**. `A` and `B` below are the incoming main values;
`I1`, `I2`, `I3` and `I5` name input ports established by the surrounding indexed
transfers. They are functional names, not a complete physical register map.

| Base and extension | Supported functional expression |
|---|---|
| `080b / 1280` | new A = A × I3 + I1 × I2 |
| `490b / 5280` | new B = B × I3 + I5 × I2 |
| `0e0b / 22c1` | new A = I1 + (I2 − A) × I3 |
| `0e0b / 12c2` | new A = I2 + (I1 − A) × I3 |

These are mathematical expressions. The evidence does not identify hardware rounding,
internal widths, fused versus unfused evaluation or latency. In particular, subtraction
signs were checked against native ARM64 definitions: ARM `FMSUB` computes
addend minus product, whereas `FNMSUB` computes product minus addend. This ordering is
specified in Arm's [Instruction Set Reference Guide](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
and independently checked with original authored ARM64 fixtures. Reversing those
instructions' signs would yield the wrong recovered filter.

## LFCOMP: a second coefficient source for mixing

The earlier dry/wet study admitted `13c0/53c0` but deliberately left LFCOMP's
`1280/5280` pair unresolved. The new four-packet selection starts at logical program
offset `0x338`; the two operations themselves start at `0x370` and `0x37e`.

The stock sequence loads coefficient C2 into port 3 and C1 into port 2. It loads
DM[0]/DM[1] into ports 1/5. Independent native expressions are:

```text
new A = W(0x13) × C2 + DM[0] × C1
new B = W(0x18) × C2 + DM[1] × C1
```

`W(a)` is the value the native function writes to that address immediately before
mixing. These two actual store values are explicit independent cut points. Earlier
filter calculations remain opaque; the study does not claim to decode them. C1/C2
come from independently proved constructor coefficient-record pointers, not from their
current numeric defaults. Source memory addresses use the previously established
wrapper/resource/data-array pointer path.

The cut-point stores occur at native `0x3713ac` and `0x3713c0`. The two complete
expressions match uniquely at native `0x3713c4` and `0x3713ec`. Swapping coefficient
roles, using another native data-array path or merging the two cut points fails the
comparison. The comparison window `0x371348..0x3713ec` is completely decoded and has
no branch or call.

This does not decode the extension bitfields globally. Other `080b` extensions,
including `42c0`, `43c0` and `52c0`, remain outside this semantic selection.

## LINEDRIVE: two four-stage allpass chains

Two exact seven-packet sequences start at logical offsets `0x13e` and `0x190`.
Each alternates `22c1`, `12c2`, `22c1`, `12c2`, loading a new state input between
operations. The same port-3 coefficient is held throughout one chain. Let incoming
A be x, incoming I1/I2 be a/b, subsequent loaded state inputs be c/d/e, and I3 be k:

```text
u0 = a + (b − x)  × k
u1 = b + (c − u0) × k
u2 = c + (d − u1) × k
u3 = d + (e − u2) × k
```

Each chain uses seven distinct source addresses and six further distinct store
addresses. The first chain uses coefficient data at DM[`0x27`], the second at
DM[`0x28`]. Those are independent symbolic memory values, not assumed coefficient
numbers or known default constants.

All **12 native stores** match: incoming x, u0, u1, u2, and two copies of u3 in each
chain. Their expanded polynomials have 1, 3, 5, 7, 9 and 9 terms. Complete expressions
must agree, including every negative term; a matching final gain or numerical
coincidence is insufficient. The native comparison blocks are branch-free and
completely decoded: `0x2dfad8..0x2dfbc8` and `0x2dfbd8..0x2dfcc8`.

The recognizer admits only the observed headers, control words and extension pairs,
and rejects aliased source/store resources. The evidence does not assign these
meanings to unrelated header contexts or every `0e0b` operation. It does not yet solve
`0e0b/12c0`, `4e0b/22c1` or arbitrary source/destination selectors.

## Correction: stores can read the incoming arithmetic state

The parser's base-word order is **not** an execution-order specification. In the
selected mixed packets, indexed stores from the main ports capture the value entering
the packet while arithmetic produces the next main value. Likewise a newly loaded
coefficient is consumed by the following arithmetic packet.

Two independent observations establish the relevant behavior:

- LFCOMP packet `0x370` contains a MAC and stores to DM[`0x13`]/DM[`0x18`]. Native
  dataflow stores the incoming wet values, then computes the new mixed values.
- LFCOMP packet `0x408` contains the C3 gain, a C0 load and stores to
  DM[`0x22`]/DM[`0x26`]. Complete native outputs equal each stored value × C3 × C0.
  If the same-packet stores captured the post-C3 result, that formula would have one
  C3 factor too many. The actual stores are at `0x3714e0`/`0x3714f4`; the independently
  checked native comparison block is `0x3714bc..0x37150c`.

The allpass stage stores further corroborate this: packets computing u1/u2/u3 store
u0/u1/u2 respectively. `dsp_gain_tail()` now snapshots incoming main values for stores
rather than treating base controls as sequential instructions. Both newly loaded
coefficient consumption and pre-gain stores have regressions. All 12 previously
selected native gain chains still match after the correction.

This is evidence about the admitted packet families, not a complete pipeline model.
It does not establish cycle counts, forwarding, arbitrary same-register write conflicts,
memory read/write arbitration or behavior when an unsupported operation is present.
Unknown arithmetic still invalidates the modeled state.

## Reproduce

With the existing local artifacts and Capstone environment:

```sh
python3 tools/mac_controls_study.py
python3 -m unittest discover -s tests -p 'test*mac*' -v
python3 -m unittest discover -s tests -p test_alu_study.py -v
```

Detailed expressions and native addresses are written to ignored
`local/mac_controls_study.json`; no vendor binary or disassembly is added to Git.
The trace reader records actual floating-register definitions and proven-path stores.
The new studies additionally require a contiguous native comparison window without
branches, calls, returns or interrupts. This remains static symbolic evidence, not
hardware execution or a general ARM64 interpreter.
