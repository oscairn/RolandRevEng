# Native arithmetic and voice-notification primitives

2026-11-10. Static inspection of the exported `CBMCDsp` helpers in the locally prepared
ZENOLOGY arm64 image, SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
These are **native reference semantics**, not newly assigned render-DSP opcodes and
not measurements of silicon precision. The helpers are useful targets when correlating
unknown operations with native translations.

## Finite-input functions

Addresses are virtual/file offsets in the prepared arm64 image. Ranges stop before
the next helper. The expressions below exclude NaNs/infinities and conversion overflow.

| Helper | Range | Observed finite-input behavior |
|---|---|---|
| `abs(double)` | `36dca8..36dcb8` | Negate when `x < 0`, otherwise retain x |
| `sgn(double)` | `36dcb8..36dcd0` | -1 for negative x, +1 for positive x, retain signed zero |
| `sat(double)` | `36dd7c..36dda4` | Clamp to the **inclusive** interval [-1, +1] |
| `saw(double)` | `36dc44..36dca8` | Bipolar wrap-like operation with the endpoint behavior below |
| `tri(double)` | `36dcd0..36dd34` | At most one phase adjustment, then a piecewise triangle fold |
| `lfs(double)` | `36dd34..36dd7c` | Fixed-point conversion followed by a feedback shift and rescaling |

For `saw`, within the range where its signed 32-bit conversion and additions do not
overflow, let `even(n) = (n + 1) & ~1` for nonnegative integer n:

```text
x < -1:  x + even(trunc(-x))
x >= 1:  x - even(trunc(x))
otherwise: x
```

This is not unconditionally interchangeable with a modulo expression returning
[-1, 1). In particular, +1 maps to -1, -1 stays -1, but -3 maps to **+1**. The
strict negative-side comparison and integer rounding create that endpoint distinction.
Large finite inputs can reach signed-integer saturation/wrapping cases; no general
large-input formula or hardware overflow behavior is assigned here.

For `tri`, first set y to x+2 if x<-1, x-2 if x>1, otherwise x. It then returns:

```text
y < -0.5:  -2 * (y + 1)
y >  0.5:   2 * (1 - y)
otherwise:  2 * y
```

The first adjustment happens only once. It must not be replaced by arbitrary periodic
phase reduction without a caller-side input bound. This is a phase-shaping primitive,
not evidence of a complete oscillator, its frequency accumulator or waveform routing.

## Feedback shift

`lfs` begins with signed fixed-point conversion `FCVTZS W8,D0,#31`. For finite x in
[-1, 1), q is the 32-bit representation of trunc(x * 2^31). Comparisons and shifts
then operate on its **unsigned bit pattern**:

```text
if q < 8:
    return 2^-28
r = (q >> 1) & 0x7ffffff8
if q & 8:
    r = r XOR 0xea0a0598
return signed32(r) * 2^-31
```

Thus negative inputs do not take the small-seed branch. Both the unsigned comparison
and the final signed interpretation matter. This describes one native feedback step;
the DSP opcode, initial state, polynomial interpretation, period, distribution and
hardware representation have not been established.

## Envelope/breakpoint state

The following helpers share a double at object offset `+0x148`:

| Helper | Range | Observed finite-input effect |
|---|---|---|
| `enve(x,y)` | `36dda4..36ddc4` | Save y at +148; return `(x + 0.0) + y/16` |
| `bpchk(x,y)` | `36ddc4..36dde0` | Return max(x,y) when saved value <0; otherwise min(x,y) |
| `bpchk_flg(out,x,y)` | `36dde0..36de18` | With saved value <0, select x iff x>y; otherwise select x iff x<y. Store the selected x/y through out; return 0 if x was selected, **512** otherwise |

The strict comparisons mean an equality returns the 512 flag. `enve` is not by itself
an ADSR generator. Its stored y supplies direction/state for later breakpoint checking.
The exposed flag value also must not be normalized to boolean 0/1 when comparing a
native translation against candidate DSP arithmetic.

## Constant-source path

`ccf(int)` at `36dbf8..36dc44` uses its selector in W1, with a hidden object argument
in X0. Its static double table starts at `83fe50`:

- Selector 0 returns zero. Selectors 1..42 contain `2^(selector-33)`, from 2^-32
  through 512. This path can provide 512 even though the largest literal encoding is
  slightly below 512.
- Selectors 48..62 contain common logarithmic and circle constants. This establishes
  a native constant-source mechanism; it does not assign these numbers to six-bit ALU
  reference selectors or prove any associated DSP operation.
- Selector 64 takes a dynamic object/resource path. It loads a 32-bit word at
  `load(load(object)+0xa0) + 4*signed32(object[8]) + 0x1f0`, then converts its unsigned
  integer bit pattern to double. The `LDR S0` does **not** mean that the loaded bits are
  interpreted as a float: the following unsigned conversion operates on the bits.
- Other selectors return zero except the code's entire 48..63 block is table-indexed.
  Slot 63 falls into adjacent type-name bytes in this image, rather than an identified
  numeric constant. Do not invent a valid constant or supported selector from that read.

The identity of the dynamic word, and its mapping to actual DSP special registers,
remain open. The static constant table itself is kept local rather than copied into
the repository.

## Voice-end bridge

`DspInt(int,int)` at `36de18` accepts an unsigned selector in W1 and argument in W2.
Selectors 0..3 dispatch through a four-byte jump table at `83fe48` to these exported
native functions:

| Selector | Target | Native symbol |
|---:|---|---|
| 0 | `000d00ac` | `CBMCVoiceEnd::IsrDSPVoiceEndNotify0(unsigned int)` |
| 1 | `000d018c` | `CBMCVoiceEnd::IsrDSPVoiceEndNotify1(unsigned int)` |
| 2 | `000d027c` | `CBMCVoiceEnd::IsrDSPVoiceEndNotify2(unsigned int)` |
| 3 | `000d036c` | `CBMCVoiceEnd::IsrDSPVoiceEndNotify3(unsigned int)` |

The object passed to each callback is reached through the global object at +108 and
then the subobject at +540b8; W2 becomes the callback's notification argument.
Selectors above 3 return. The final callback branch is at `36de9c`; later static
initializers inside the broader function-start range are not part of this dispatcher.

This establishes a native bridge from simulated DSP notifications into voice-end
management. It does not establish the hardware interrupt opcode, register/bit meaning,
or notification protocol. A custom voice engine will eventually need to satisfy that
ownership/lifetime contract rather than merely producing audio samples.

## Reproduce

Use the prepared artifact described in the README. Existing `lib.py` already resolves
exports and image ranges; for example, from the repository root:

```sh
PYTHONPATH=tools python3 - <<'PY'
import lib
exports = lib.load_exports()
for name in ('CBMCDsp::sat(double)', 'CBMCDsp::saw(double)',
             'CBMCDsp::lfs(double)', 'CBMCDsp::DspInt(int, int)'):
    start, end = lib.func(exports[name])
    print(name, hex(start), hex(end))
    for instruction in lib.md().disasm(lib.Z[start:end], start):
        print(hex(instruction.address), instruction.mnemonic, instruction.op_str)
PY
```

These conclusions come from branches, constants, structured instructions and matching
exported target addresses. No helper was executed. Direct calls to these exported
helpers were not found in the 75 paired `VSubProc` bodies scanned in this pass, so
call-count alignment does not supply an opcode map; equivalent operations can be
inlined. Remaining arithmetic correlation must establish actual value provenance.
