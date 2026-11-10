# Auxiliary-product versus accumulated tap feedback

2026-11-10. Static follow-up to [stereo tap accumulation](stereo-tap-accumulation-study.md).
Prepared ZENOLOGY arm64 SHA-256:
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
`tools/tap_feedback_variation_study.py` requires that exact image. No plugin,
firmware, device, updater or payload is executed or modified. REA remains unavailable;
these are native-byte/Capstone results rather than REA-provider or hardware evidence.

## New exact-context variation

Two later TS808 regions distinguish a scaled auxiliary contribution from the
unchanged main value captured by a store. This extends the earlier `044f/454f`
and `048f/458f` comparison instead of repeating its initial filter.

Let W_L/W_R be independently captured input values, and G/F/H three distinct live
coefficient slots. The native arithmetic independently establishes:

```text
P_L = W_L * G                 P_R = W_R * G
U_L = P_L + old state1_L * F  U_R = P_R + old state1_R * F
V_L = U_L + old state2_L * H  V_R = U_R + old state2_R * H
```

The BMC contexts have the following exact controls:

The stage labels summarize the paired native translation of the whole admitted
context. They do not assign freestanding opcode meanings or causality to an
extension bit in isolation.

| Stage | Base controls / extensions | Supported functional contribution within these contexts |
|---|---|---|
| Auxiliary products | short `2403`, `6507` | Form P_L/P_R while the later main-port stores capture W_L/W_R |
| First accumulation | `044b / 0002`, `454f / 0006` | Form U_L/U_R using P_L/P_R and the first-state products |
| Second accumulation | `044b / 0000`, `454f / 0004` | Form V_L/V_R using U_L/U_R and the next-state products |

For the first long pair, the observed input ports carry state1_L/state1_R through
ports 1/5 and F through ports 3/7. Its co-issued transfers load state2_L/state2_R
through ports 1/5 and H through ports 3/7 for the next long pair. Thus these particular
contexts deliberately use shared F/H labels: both ports 3 and 7 contain the **same
live coefficient slot** at each stage. They cannot independently establish which
of those two ports supplies `044b` or `454f`. No port-3 versus port-7 distinction
or register-bank/source-bit mapping is assigned from those equal inputs.

The generated report explicitly compares the two source-port hypotheses. With
both ports bound to the actual F slot, their full expressions are identical. An
original symbolic counterexample assigns independent live slots to the ports and
shows that the hypotheses then differ. The test uses symbolic record identities,
not coincident numeric defaults. An asymmetric assignment would supply the missing
discriminator; neither actual region provides it.

Importantly, the base words remain `044b/454f` while their extensions change from
`0002/0006` to `0000/0004`. The first accumulated expressions need the G-scaled
contribution; the next expressions retain the already accumulated first-state term.
Treating the first pair as simply W + state1*F drops G. Treating the second as
P + state2*H drops the first-state term. Both hypotheses fail as symbolic expressions,
even if numeric coefficient defaults happen to hide the difference.

## Two independently owned state contexts

| Program region | Live slots G/F/H | Captured W addresses | First-state read/result addresses | Second-state reads |
|---|---|---|---|---|
| `14e..1ba` | C10 / C11 / C12 | b / e | c / f | d / 10 |
| `1cc..236` | C7 / C8 / C9 | 11 / 14 | 12 / 15 | 13 / 16 |

Addresses and program positions are hexadecimal except C-slot numbers, which use
the same decimal convention as the earlier arithmetic studies. All six state/capture
resources within a region must be distinct; the final destinations intentionally
equal the two first-state sources. The primary program entry remains `4020`.

The first auxiliary pair is in packet `160`; its two long pairs start at `176` and
`198`. The second auxiliary pair is at `1de`; its long pairs start at `1f4` and `216`.
Their final state stores are in packets `1a2` and `224`. All packet layouts already
pass the existing decoder. No header, special operation or emitter template is admitted.

Native comparisons match **12 distinct arithmetic definitions and 16 exact state
accesses**, including all intermediate stages and final stores:

| Region / channel | Auxiliary product | W store | First MAC | Second MAC | Result store |
|---|---|---|---|---|---|
| First / left | `2088bc` | `2088dc` | `2088ec` | `2088f0` | `208900` |
| First / right | `208928` | `208948` | `208954` | `208958` | `208968` |
| Second / left | `2089d0` | `2089f0` | `208a00` | `208a04` | `208a14` |
| Second / right | `208a38` | `208a58` | `208a64` | `208a68` | `208a78` |

The comparison windows are contiguous and branch/call/return/interrupt-free:
`208898..208968` and `2089ac..208a78`. Each stage's entire polynomial must match:
one term for P, two for U, three for V. Earlier shaping/mixing is opaque at W;
the later gain applied alongside the final stores is outside this expression.

## A product can precede its input's cut-point store

The compiler computes each auxiliary product **before** storing its unchanged input.
The checker does not relax the previous late-cut rejection by expression equality
alone. For each channel it additionally verifies:

1. The actual multiply source register is the later store's D-register source.
   The multiply's destination must not overwrite that retained source either.
2. Every intervening native instruction is decoded, with no address gap.
3. No intervening instruction overwrites that source or any scalar/vector alias.
4. The W store precedes both MACs and the result store follows them.

The actual retained sources are native D0/D1; the auxiliary products use different
native registers. D0/D1 here are **ARM registers**, not a claimed BMC register map.
Original authored fixtures reject scalar/vector clobbers, another store source,
missing instructions and reversed ordering. The entire comparison window separately
rejects control transfers.

## Constructor and operand identity

Fresh constructor-memory reconstruction must agree with getter extraction. Native
pointer/index provenance must connect each access to one exact record, the established
wrapper/resource/data-array path, mask `7ff`, and a 64-bit double access with UXTW #3,
no displacement or writeback. Equal numeric addresses never substitute for record identity.

The reused state values have **different records for reads and result writes** here:

| Region | Read wire field / native object field / read PC | Write wire field / native object field / write PC |
|---|---|---|
| First left, DM[c] | `16e / +4cc / 2088ac` | `1ae / +4d4 / 208900` |
| First right, DM[f] | `172 / +4e4 / 20891c` | `1b0 / +4ec / 208968` |
| Second left, DM[12] | `1ec / +4fc / 2089c0` | `230 / +504 / 208a14` |
| Second right, DM[15] | `1f0 / +514 / 208a28` | `232 / +51c / 208a78` |

Unlike the earlier TS808 initial-filter result aliases, these writes do not reuse
one constructor field. Substituting the earlier equal-address read record for the
write record fails. The report also records the exact second-state and W-store
bindings rather than matching addresses in aggregate.

Each live slot has two separately traced float loads through a constructor-proved
0x48-byte coefficient record at record+0x28, followed by conversion to double. The
first region checks slots 10/11/12; the second checks 7/8/9. All 12 loads are source-bound.
Their current numeric defaults are not used to establish arithmetic or identity.
The symbolic comparison assigns one value per live slot; interleaved parameter
updates between its repeated loads are not modeled or ruled out on hardware.

## Limits and the smallest remaining discriminator

This recovers the exact contexts' functional source/destination roles. It does not
prove that extension code 2 means a particular physical auxiliary register, code 0
means a particular accumulator, or that one bit alone selects that behavior.
The paired stock observations also vary preceding short controls, co-issued transfers
and header context. Pipeline forwarding/delayed writeback could affect the internal
explanation of why the two values remain distinct. None is guessed here.

The next discriminator would hold the other choices fixed while independently varying
a long extension and exposing both the auxiliary and unchanged main values, or recover
an authoritative emulator/assembler implementation. These results constrain that
experiment; they do not replace it with a global bitfield interpretation.

Formal polynomial equality does not establish hardware precision, rounding, saturation,
hidden flags, cycle timing or arbitrary relocation/scheduling. No new code generator,
DSP wrapper or runnable synth engine is claimed. Existing decoder/emitter interfaces
are unchanged.

## Reproduce

With the prepared local corpus and installed Capstone:

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/tap_feedback_variation_study.py
$PY -m unittest discover -s tests -p test_tap_feedback_variation.py -v
```

The detailed source-pinned report is ignored `local/tap-feedback-variation.json`.
Ten tests cover both exact shapes, source identities, full stage expressions,
retained-source proof, altered encodings, record/resource distinction and explicit
countermodels. Pure tests run without vendor data; native tests skip explicitly when
Capstone or the prepared artifact is missing. No vendor image or native disassembly
is committed.
