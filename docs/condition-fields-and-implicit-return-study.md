# Tested condition fields and implicit-return limits

2026-11-10. Static bytes and Capstone 5.0.7; no target execution or REA-provider
evidence. Native arm64 artifact SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.
This extends the [parent control study](parent-control-and-nested-organ-study.md).

**New result:** the native values governing four conditional callbacks now connect
to exact width-2 DSP operand fields and their particular producer controls. The
three `28bb` contexts all test the same finite magnitude boundary despite using
different producer controls. This identifies the values a correct condition decoder
must select. It still does not identify a numbered BMC register, condition bitfield,
saved return register/stack, or transfer delay.

## Constructor, native load and DSP field agree independently

Native routing objects load their constructor-built parameter table through
`wrapper+38`. `GetCoefAdrs` searches its 16-byte records by the program-relative
field at record+0 and returns the double at record+8:

- DSP4 getter `41334..37c`: record count `ce`.
- DSP5 getter `34c1a8..1f0`: record count `a9`.

The new checker reconstructs actual constructor-written memory, using the existing
`constructor_memory` reader. It then follows the native predicate inputs, rather
than choosing an equal-valued zero elsewhere in the table:

| Context / candidate control word | Native tested load | Constructor record | Program-relative field | Actual DSP packet / producer | Width-2 pool reference |
|---|---|---|---|---|---|
| DSP4 / `0bc3` | `41c14`: table+`678` | `+670`, default 0 | `7c4` | `7d4` / `1052` | pool+2, absolute `7e4` |
| DSP5 first / `28bb` | `34c2c4`: table+`8d8` | `+8d0`, default 0 | `3eb4` | `3ec2` / `ae54` | pool+4, absolute `3ed4` |
| DSP5 second / `28bb` | `34c74c`: table+`88` | `+80`, default 0 | `43a4` | `43ba` / `7050` | pool+0, absolute `43c4` |
| DSP5 third / `28bb` | `34c9f8`: table+`868` | `+860`, default 0 | `445c` | `446c` / `fe50` | pool+0, absolute `447c` |

All sizes/addresses are hexadecimal. Program absolute byte = relative field +
primary entry `20`. Constructor bodies are `42e14..4439c` and
`34d690..3518b8`, bounded by the Mach-O function-start table.

For each producer, the familiar low-six-bit reference syntax independently lands
on the constructor's exact field: codes `12/14/10/10` denote width 2 and byte
offsets `2/4/0/0` in the shared pool. This is a **field-syntax anchor** in these
previously unresolved header contexts. It does not admit the whole header or
assign arithmetic semantics to `1052/ae54/7050/fe50`.

The native pointer/definition checks include:

- DSP4 `41400` establishes x19 from the wrapper argument; `41b38` loads its table
  pointer into x8. No intervening instruction overwrites x8 before `41c14`.
- DSP5 `34c268/2a4/2a8/2ac/2b0` establish x19 as the wrapper, x22 as wrapper+8,
  x21 as wrapper+38, and x9 as its table pointer. The first condition loads d1
  from this table; no scalar/vector alias overwrites it before the compare.
- Later DSP5 loads first fetch the table pointer through x21, then d0 at `+88`
  or `+868`; x21 stays unchanged and neither tested d0 is overwritten before
  its comparison. Register preservation checks include W/X and scalar/vector aliases.

The def-use statements concern explicit native instructions and ordinary native
calling conventions; they are not BMC pipeline observations. Default doubles and
stored DSP constants can differ until stock parameter initialization patches them.
Equal initial zero values are not used to establish record ownership.

## Exact native predicates

The checker recognizes three bounded branch kernels and rejects other forms.
It reads comparison constants from actual MOV immediates, including their sign,
then validates FCMP/FCCMP conditions and destinations. Native instruction/flag
interpretation follows Arm's [instruction reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
and [floating-point condition-code explanation](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/condition-codes-4-floating-point-comparisons-using-vfp).

| Native kernel | Finite-input callback predicate |
|---|---|
| `41c14..c34`, Boolean carried to `41cac` | table[`678`] != 0 **and** table[`628`] != 0 |
| `34c330..34c34c`, FCCMP form | abs(table[`8d8`]) >= `2^-32` |
| `34c7bc..34c7dc`, two-branch form | abs(table[`88`]) >= `2^-32` |
| `34ca60..34ca80`, two-branch form | abs(table[`868`]) >= `2^-32` |

The boundary is inclusive: both `+2^-32` and `-2^-32` take the callback, while
signed zero and values strictly inside that interval bypass it. The finite
reference rejects NaN/infinity; this study does not model FPCR exception/trap
settings or infer BMC exceptional-value handling from the desktop branches.

DSP4 has a material additional input: table+`628` is constructor record `+620`,
whose program position is **zero**, default **1**. It is the second native mode
gate in the conjunction. This does not give it ownership of program byte zero or
an encoded literal there. No separate wire operand is assigned to it. Consequently
`0bc3 = simple nonzero test of one literal` is an incomplete interpretation even
though one of the two inputs now has an exact DSP field anchor.

For DSP5, `28bb` remains constant while the field-producing controls change from
`ae54` to `7050` to `fe50`, and its referring base controls shift from `00a0/00a2`
to `00a6/00a8`. The reference offsets have a concrete explanation; a numbered
condition register and comparison-selector decomposition still lack one. These
four anchors constrain future hypotheses without manufacturing a bit decoder.
The Fantom words `1acb/1aa7/012d` likewise retain their previous candidate status.

## What `00f8` can require from the packet

The DSP4 placeholder at native source `77ec44`, entry `4020`, begins with
`0b02 00f8`, followed by compact NOP `0001`. Header-family decoding yields one
family-3 operation and **zero payload bytes**. Therefore this observed standalone
form carries no explicit program address or link/stack operand in its packet.
If its role is return, its destination must come from implicit architectural
state or surrounding context; this does not identify where that state lives.

An independent co-issued example is native FETDRIVE source `8372f4`, relative
packet `1ba`: `3d06 00f8 8fe0 cfe2 2018 2019`. The header's families are
`(3,4,4)`. All four payload bytes are accounted for by the two indexed-transfer
address fields. Thus this example also needs no dedicated return operand bytes.
It does not prove that an opaque operation can never inspect shared packet data.

Neither example proves that `00f8` writes or reads a particular saved PC, how
calls nest, whether a return stack exists, or when the next instruction executes.
The following NOP does not establish a one-packet return delay. The inspected
native branch kernels expose no BMC PC/link-state implementation.

## Minimal missing proof

The remaining gap is specific: identify which architectural value/flags the
paired condition word selects, demonstrate its comparison bits independently of
the surrounding native translation, and observe or recover the saved-control-flow
state used by `00f8`. A changed condition producer with known same register, an
assembler/disassembler implementation, a DSP interpreter, or a controlled PC/state
trace could discriminate these possibilities. More copies of the same translated
graph do not by themselves determine the encoding.

No such runtime or implementation evidence is supplied here. The checked native
predicates are useful future probe oracles, not permission to emit an unproved
conditional call/return wrapper. No device, plugin binary, firmware loader or
program was executed or modified.

## Reproduce

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/condition_return_study.py local/zen_arm64 > local/condition-proof.json
$PY -m unittest discover -s tests -p test_condition_return_study.py -v
```

Three tests cover the actual constructor/field/predicate bridges, a changed native
branch condition, scalar/vector alias clobbers, the inclusive finite boundary,
equal values at wrong field positions, explicit extra return payload and the two
real return-packet shapes. Detailed generated records remain ignored under `local/`.
No Qwen draft/code was used, and production decoder/emitter coverage is unchanged.
