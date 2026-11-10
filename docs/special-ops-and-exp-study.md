# Exceptional short controls and native exponential cutpoints

2026-11-10. Static follow-up using the same ZENOLOGY arm64 artifact as the header
study. No native or DSP function is executed. This identifies useful reference-function
windows and tightens the decoder's rejection boundary; it does not assign an `EXP`
mnemonic to an isolated BMC opcode.

## What can be established independently

The Mach-O indirect-symbol table identifies native call stub `0x6d886c` as `_exp` and
`0x6d8adc` as `_log`. These names come from `xcrun otool -Iv`, rather than guessing a
function from neighboring strings or its position in a call sequence.

UPLIFT_EXCITER has two direct `_exp` calls. For each, the native D0 argument is also
stored to a proven data-array location before the call, without an intervening write to
D0. The returned D0 is then stored to another proven data-array location, again without
an intervening overlapping floating-register write or call. Fresh constructor recovery
establishes which data-symbol record each access uses. Those records locate particular
address fields within the BMC program, rather than merely matching equal address values.

| Native `_exp` call | Argument also stored at | Argument BMC address-field offset | Return stored at | Return BMC address-field offset | Exceptional short control between fields |
|---|---|---|---|---|---|
| `0x8bbe4` | Data index `0x8`, native store `0x8bbbc`, object field `+0x2ac` | `0x46a` | Data index `0xb`, native store `0x8bbf4`, object field `+0x2bc` | `0x4e2` | `20a0` in packet starting `0x46c` |
| `0x8bc40` | Data index `0x6`, native store `0x8bc3c`, object field `+0x2a4` | `0x4e4` | Data index `0xa`, native store `0x8bc50`, object field `+0x2b4` | `0x55e` | `20a5` in packet starting `0x4e6` |

Thus the native reference value written at `0xb` is `exp(argument also written at 0x8)`;
the value written at `0xa` is `exp(argument also written at 0x6)`. This is stronger than
aligning the first unknown opcode with the first library call: source/destination record
identity and actual D0 def/use delimit both windows independently.

The intervening BMC regions contain long arithmetic and polynomial-looking constants
in addition to the exceptional short control. They are **candidate exponential macro
windows**. The evidence does not separate the short operation from its surrounding
range reduction, polynomial and output operations, nor show that the DSP approximation
is numerically identical to native libm `exp`.

## Why the ordinary literal syntax remains unproved

The relevant observed controls are:

| Short control | ZENOLOGY observations | bmc0 observations | bmc1 observations |
|---|---:|---:|---:|
| `20a0` | 5 | 9 | 1 |
| `20a4` | 3 | 4 | 1 |
| `20a5` | 2 | 0 | 0 |
| `30a0` | 0 | 5 | 0 |
| `30a2` | 8 | 22 | 6 |
| Total | 18 | 40 | 8 |

These totals include repeated/relocated images. `20a0` and `30a0` would read a three-byte
literal starting inside the long extension under the regular six-bit hypothesis. Other
variants accidentally fit by reading a subset of already covered literal bytes. That
fit does not establish their operand roles.

For example, UPLIFT_EXCITER's first window and TRANSIENT's corresponding constant-bearing
packet use the same two explicit four-byte constants, but adding a transfer moves their
payload positions and changes the extension word. A supposed `20a0` literal would then
change solely because the pool was rearranged. The low indices `0`, `2`, `4`, `5` also
vary alongside otherwise closely related polynomial regions. These observations motivate
a register/special-state hypothesis, but do not prove that encoding or a particular
arithmetic operation.

`header_study.layout()` therefore rejects all five observed controls. This removes
46 previously admitted packets, leaving **41,710 structurally admitted observations**.
It does not alter raw byte-preserving packet parsing. The existing single GASSPH
adjacent-symbol ownership conflict also remains explicit and unchanged.

## Reproducible method and limits

`tools/special_ops_study.py` reuses the existing constructor-memory reader and native
pointer-provenance model. It supplies each address field as a distinct record marker;
two equal numeric addresses do not become interchangeable record identities. Stores
must use a 64-bit D0 value and an unsigned 32-bit index scaled by eight, with no added
displacement or writeback. The reference checker requires no overlapping D0/S0/
vector writes between a store and the call. It admits only straight-line prefixes with
the identified pure `_exp`/`_log` imports; another call or control-flow branch ends the
trace. It does not model arbitrary arithmetic as a function with an invented name.

TRANSIENT also contains two `_exp` import calls and analogous exceptional/polynomial
regions. However, its native body reaches a conditional branch at `0x1d6128` before
those calls. The bounded tracer stops there. It reports the imports and exceptional
controls but **no proven cutpoint pairing** for that class. Extending the analysis would
need path-sensitive state merging or a separately justified straight-line entry state.

Run from the project directory with local artifacts, Capstone and Xcode tools available:

```sh
python3 tools/special_ops_study.py
python3 -m unittest discover -s tests -p test_special_ops_study.py -v
```

Detailed source-bound addresses go to ignored `local/special-ops-study.json`. Five tests
cover indirect-symbol parsing, distinct field identities at equal addresses, argument
and return overwrites, overlapping vector writes, a wrong pointer path/index scale, branch/unknown-
call termination and the two local UPLIFT_EXCITER cutpoints. The synthetic instructions
are original authored fixtures, not copied vendor code.

An isolated exceptional-opcode meaning, its destination/special state, the exact BMC
exponential approximation, valid input range, rounding, saturation and timing remain
unresolved. Reusing a stock macro window in a newly scheduled DSP program is not yet
established as safe or correct.
