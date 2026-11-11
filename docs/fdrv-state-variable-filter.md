# A byte-executed stereo state-variable filter

2026-11-10. Native ZENOLOGY arm64 SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
Fantom CORE1 payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Evidence is static Python/Capstone analysis and execution of the pinned native
callback in owned fixture memory. No BMC hardware or updater was accessed.

**Result:** the first stereo FDRV filter block now has an independent state/output
reference, a strict 184-byte assembler/inverse-decoder profile and packet execution.
All 146 arithmetic-body bytes match the native-paired program and all five Fantom
placements. The remaining 38 bytes are authored input/coefficient loads. This is
a reusable filter component for an original engine, not complete FDRV emulation,
a standalone executable wrapper or a general instruction decoder.

## Native recurrence and the subtraction sign

For each channel, y is the input, s/t are two incoming states, and a/b/c/d/e are
five binary32 live coefficients. The recovered operation order is:

```text
Tnew = fma(s, a, s) + t
X = fma(s, b, -Tnew) + y
preliminary = fma(y, c, X * e)
Snew = fma(X, a, X) + s
output = fma(Snew + s, d, preliminary)
```

The nonfused additions and multiplication stay separate. Signals and states are
binary64 in the native reference; only coefficient records are rounded to
binary32. Both the helper and interpreter reject nonfinite intermediates.

The native `FNMSUB` at `305250` computes **s*b − Tnew** in this dataflow.
Direct native probing and the complete callback comparison confirm the sign.
Rewriting it as Tnew−s*b gives the wrong filter. Signed-zero behavior also
prevents casually replacing an instruction with a post-negated expression.

The checker verifies source/state/output records, register identities, coefficient
pointer provenance and intervening register preservation. The
[auxiliary study](auxiliary-save-restore-and-add-mac.md) supplies the matched
save/restore and final add/MAC cutpoints. Native producer anchors include:

| Operation | Left | Right |
|---|---|---|
| Tnew fused term / addition | `305214/305218` | `3052f4/3052f8` |
| X subtraction / input addition | `305250/305254` | `305328/30532c` |
| X*e | `305264` | `305338` |
| Preliminary / Snew fused term / addition | `30528c/305290/305294` | `30535c/305360/305364` |
| Extra s addition / output MAC | `3052bc/3052c0` | `305388/30539c` |

Both channels use coefficient slots `a..e` (hexadecimal), corresponding to
decimal `10..14`. No physical coefficient-port distinction is inferred where
the observed ports carry the same record.

## State-variable interpretation and ideal stability

Define g=1+a and q=−b. Ignoring finite arithmetic rounding, the state update is:

```text
Tnew = t + g*s
X = y - q*s - Tnew
Snew = s + g*X
```

This is a state-variable recurrence with X as a highpass term, Tnew as an
integrated term and Snew as the other state. The state matrix has trace
`2 − g*q − g*g` and determinant `1 − g*q`. The strict ideal Jury conditions
reduce to `g*q > 0` and `g*g + 2*g*q < 4`. Positive g/q designs are a useful
subset; negative g and negative q can also satisfy the mathematical criterion.
The helper compares these conditions with independently calculated poles in tests.
This is an ideal linear-model check, not a hardware or finite-precision guarantee.

The output coefficients mix input, X and Snew+s. For example, c=0/e=1/d=0
selects X; c=e=0/d=.5 selects the average of the old and new s states. In exact
arithmetic, c=1, d=−q/2 and e=q*g/2−1 select Tnew. Serializing d/e to binary32
can perturb that last identity. No cutoff, resonance or sample-rate calibration
on a BMC is claimed.

## State addresses and the conditional ring convention

The native first block reads s/t from `29/2a` and `2c/2d`, writes Tnew at
`29/2c`, and Snew at `28/2b`. The native scalar index convention is
`(address + wrapper_base - origin) & 7ff`. Advancing origin by one makes the
next reads recover the Snew/Tnew pair just written. This is a checked software
convention, not an observed BMC frame cadence.

The profile's ten sources are ordered:

```text
[yL, tL, sL, yR, tR, sR, next_sL, next_sR, next_tL, next_tR]
```

The four targets must be `[sL, sR, sL-1, sR-1]`, with tL=sL+1 and tR=sR+1.
All ten sources plus the two lower state targets must be distinct and in
`0..7ff`; all five coefficient slots must be distinct and in `0..fff`.
These explicit aliases retain the proved write/read dependency. The extra next
sources feed final port loads and do not change this block's current output.

The ten packet offsets are decimal `0/14/28/38/56/86/100/118/128/158`. Stores
capture incoming values and coissued loads feed the following packet. In the
exact window, auxiliary saves at offset 56 preserve old ports 2/6; restores at
offset 100 provide those old states after their temporary products have fed the
preceding arithmetic. The trace records the live saved values and requires a
balanced pair at completion.

This model tracks one live save per port. It does not retain inactive physical
cache slots, arbitrary initial depths or overflow behavior. The native circular
banks can retain changed slot contents after restoring their cursors. Balanced
logical saves therefore do not establish that every physical DSP resource is
unchanged or available to another graph.

Fantom list `610e5a94` supplies the same body at program bases
`4020/8040/9040/a040/3020`. Their data bases are `100/320/3b6/44c/c0` and
coefficient bases `190/1f4/208/21c/e`. Typed substitutions reproduce every body
byte. These are occupied stock placements, not new resource allocations. Live
ownership, auxiliary-resource coordination, loader access, entry/return and
physical precision/timing remain unresolved.

## Reproduce and execution checks

```sh
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/fdrv_filter_study.py --execute-native --frames 12000
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py assemble examples/state-variable-pair.json local/state-variable-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python tools/bmc_subset.py disassemble local/state-variable-pair.bin --stored
/Users/jacob/.pyenv/versions/3.13.7/bin/python -m unittest discover -s tests -p 'test_fdrv_filter_study.py' -v
```

The fixture runs the unmodified native callback `3050ec..305ea8`, 879 instructions,
after checking contiguous code, its final return and a call-free, position-independent
instruction whitelist. It supplies its own constructor image, twenty live
coefficient records, stereo input/output buffers, 2,048-double ring and owner.
The five filter coefficients are explicitly chosen fixture values that require
binary32 rounding, not recovered factory tuning. Other processing in the callback executes, but its full effect
output is not covered by this component comparison.

The tests compare both the byte interpreter and independent equations with native
prefix, state and first-filter output stores. Nine cursor pairs run 128 frames,
one pair runs 12,000 frames through five ring wraps, and two one-frame cases check
signed zeros and large/precise binary64 states. All 105,232 checked native values
and 78,924 byte-emulated filter values agree bit for bit. Cursor pairs return
unchanged and the long render ends at origin 1760. A nonzero indexed background
and distinct auxiliary canaries avoid relying on a cold-zero coincidence.

Qwen returned a small equation/stability draft in 70.4 seconds. Its equations were
retained after independent sign checking, but it incorrectly rounded y/s/t to
binary32 and rejected valid binary64 states. Review corrected that validation
with existing numeric helpers and expanded the requested positive-g/q stability
check to both valid sign orientations, with explicit precision and pole tests.
Native/firmware evidence, the emitter/interpreter and
execution fixtures were derived and verified locally. Generated vendor artifacts
remain under ignored `local/`; no binary is committed or installed.
