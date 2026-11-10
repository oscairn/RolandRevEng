# Effect replacement, coefficient clearing and parent entry references

2026-11-10. Static bytes and Capstone 5.0.7, without target execution or a REA
provider. Addresses apply to bmc0 MI078 C1A v1.08, header-stripped payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.

The effect replacement caller is now partly recovered. It manages a temporary
RAMCLR object, routing-related state, waits, parameter setup and the selected
effect's final `SetAlg` dispatch. RAMCLR explicitly zeroes **coefficient**
reservations and installs a separate DRAM-IO program. This does not establish a
complete per-effect history reset. Four independent parent packets also contain
the corresponding effect entry addresses divided by two beside `00a0/00a2`.
They provide concrete control-flow candidates; neither control has been admitted
as a decoded call instruction.

## Outer object and factory

The constructor at `01128f50`, reached from veneer `6107770c` and the effect-system
constructor at `6102c9dc`, installs address-point vtable `6117b3d8`. Its RTTI name
is `19CEfctPrm_ModuleImpl`. Actual field writes and later reads establish:

| Object offset | Observed role |
|---|---|
| `+4` | Common object, supplied as the constructor's fifth argument |
| `+8` | Current algorithm wrapper returned by the factory |
| `+c` | Factory/type object |
| `+10` | Owner manager/context object |
| `+14` | Instance index |
| `+18` | Current algorithm identifier |
| `+1c` | Transition-state byte, initialized to zero |

The first four instances use factory storage `200a0d8c + index*e0` and managers
`200a0d14 + index*14`. Their descriptors are `610a1674 + index*48`; the constructor
loops over four instances. Addresses and sizes in this paragraph are hexadecimal.

Factory constructor `610847a0` installs `6117be98`, whose RTTI is `8CMfxType`.
Important slots are:

| Factory vtable offset | Body | Static behavior |
|---|---|---|
| `+0` | `6102dc54` | Checks supported identifiers using a bounded TBB table |
| `+4` | `6102dcc4` | Returns/rebuilds the default wrapper in factory storage |
| `+8` | `6102dcda` | TBH dispatch on `algorithm + 1`; constructs algorithm and wrapper |
| `+c` | `6102f2d8` | Bounded algorithm-specific cleanup dispatch |
| `+10` | `61084798` | Returns `-2` |
| `+14` | `6102f632` | Returns `-1` |
| `+18` | `6102f638` | Constructs temporary RAMCLR on stack and calls its `+10` wait query |

The `-1` factory case begins at `6102dda8` and calls RAMCLR constructor
`61056b0a` at `6102ddb0`. It constructs the CFsp object at factory+4 and its
CMfx wrapper at factory+54; the latter's `+74` points back to the CFsp object.
Its wrapper vtable is `611787cc`. Wrapper slot 0, body `61037b36`, loads that
CFsp pointer and tail-calls its vtable+8, resolving to RAMCLR `SetAlg` below.

## Replacement ordering and the transition-state branch

Outer vtable slot `+14` is body `011290ee`. Its inputs preserve the new algorithm
identifier in r7 and parameter-related arguments in r6/r5. This is the observed
flow, retaining branch conditions rather than inventing a universal reset:

1. If the algorithm is unchanged and transition byte `+1c` is zero, take the
   short parameter-update path `011291ba`: initialize/update wrapper+4's
   parameter interface through its slot+4, then invoke wrapper slot+4. There
   is no new RAMCLR stage on this path.
2. If the algorithm changes and `+1c` is zero, call outer slot 0 at `0112910e`.
   Its target `01128ff8` marks `+1c=1`, consults manager-related virtual interfaces,
   XORs one returned selector with 1, updates that selector and another state
   value, and waits with count 1/completion 1.
3. Still inside `01128ff8`, call old wrapper slot+c, factory cleanup slot+c,
   obtain factory's `-1` identifier, construct that algorithm through factory+8,
   and tail-call its wrapper slot 0. The concrete factory and RAMCLR wrapper
   above resolve this last step to `CFspMfxRAMCLR::SetAlg`.
4. Back at `01129110..122`, call outer slot+30 (`011291d6`), which forwards to
   factory+18 with manager/context and instance index. For `CMfxType` this is
   RAMCLR's wait query. Pass the returned count to `011271b8`, completion 1.
5. At `01129126..144`, call intermediate wrapper slot+c and factory cleanup,
   save the new identifier, and check factory support. A nonzero transition
   byte skips steps 2–4 and joins here; it does not prove clearing has completed
   independently of the owning object's protocol.
6. Supported case: construct the new algorithm through factory+8, initialize
   its parameter interface (`0112915e..172`), call wrapper slot 0 and slot+4,
   call outer slot+4 (`0112908c`), then tail-call wrapper slot+8 at `01129198`.
   Unsupported case takes the separate default-wrapper path `0112919a..1b8`.

`0112908c` checks the transition byte, changes the same manager-related state
through its virtual interface, waits count 1/completion 1, calls another
manager-related virtual method with the instance index, then clears `+1c`.
The exact meaning of those selector/state operations remains unresolved. This
is observed coordination, not evidence that any new thread can call these
methods independently or that the byte is a general synchronization primitive.

For this RAMCLR CMfx wrapper, slot+c forwards to CFsp slot+c (`61037b40` →
`61056bb2`), which calls manager+54. That manager slot resolves to `011324fc`,
identified by its assertion as `CBmcDspMgr::FillDramIOProgNopSegment()`. It walks
the owner DRAM-IO reservations, invokes `0112fcee` with each base/capacity and
final bool 0, and waits for DMA through `0112f6a4(1)` before clearing its
flags (`01132586..5c6`). Thus RAMCLR cleanup replaces the temporary DRAM-IO
program; omitting it would leave more than a stale wrapper object.
The driver assertion at `0112fcee` names `StackFillDramIOProgNop`; its direct
store path writes zero words, while the bool selects between two address tables.

## Exactly what RAMCLR clears

RAMCLR address point `611781d4`, RTTI `13CFspMfxRAMCLR`, has SetAlg at vtable+8
(`61056b14`). It obtains the owner descriptor via manager slot 0. The loop:

- Reads signed count at descriptor+`1c` and reservation pointer at `18`, exactly
  the **enum 6** group identified in `kernel_abi.py`.
- For each `{base,length}` record, copies a seven-word `_DataSym` template from
  `61115bd4` and replaces its absolute base, count and inclusive end fields.
  Template bytes at `+10` identify enum 6. It loops index `0 .. length-1`.
- Calls manager slot+bc with that symbol, the element index, float **0**, `EnvTC`
  numeric value **3**, and final bool **0** (`61056b70..b90`).
- Tail-calls manager slot+2c with DRAM-IO list `61115b14` after all coefficient
  records are processed (`61056b9c..bb0`).

Manager+bc resolves to `0113391e`, whose assertion identifies
`CBmcDspMgr::WriteDspCoefFloatWithEnv(const _DataSym *, int, float, EnvTC, bool)`.
It explicitly requires enum 6 and resolves the symbol through `01131968`.
The nonwaiting bool-0 path does not acquire/wait/release the envelope flag in
this body; it forwards the element address and envelope arguments to `0113047c`.
This is coefficient zeroing through the stock envelope mechanism, not a bytewise
zero of enum 0 history memory. The hardware timing/numerical meaning of EnvTC 3
is not assigned.

| Owner descriptor | DSP | Enum 6 range zeroed by this loop | Separate enum 0 reservation |
|---|---:|---|---|
| `610a1674` | 4 | `190..1a3` | `100`, length `96` |
| `610a16bc` | 5 | `1f4..207` | `320`, length `96` |
| `610a1704` | 5 | `208..21b` | `3b6`, length `96` |
| `610a174c` | 5 | `21c..22f` | `44c`, length `96` |
| `610a1d14` | 1 | `e..21` | `c0`, length `c0` |

RAMCLR's wait-query body `61056bba` requires a DRAM-IO reservation, DSP <6,
signed segment count <=4, and its first reservation capacity >=`b8`. It returns
the difference between the first and third u32 words at `61115b1c`: `1900`.
These words are two DRAM-IO instruction words `80420000` and `80421900`, separated
by another word. This is the returned numeric counter, not a measured duration.
The list `61115b14` has kind 1, header DSP 5 and four segments; its table at
`61115e3c` selects sources `61115b1c/5c14/5ccc/5d84`, each length `b8` bytes.
Do not treat header DSP 5 as every segmented manager's destination.

The separate DRAM-IO program may perform additional clearing. Its instruction
semantics and the relationship to every history reservation have not been
recovered here. Consequently neither this name nor the coefficient loop proves
all filter/delay state is reset before arbitrary replacement code.

## Four parent entry-reference candidates

The normal DSP4/5 parent streams each contain an adjacent `00a0/00a2` pair in
the **control region**. The second shared-pool halfword in these four packets
is exactly the corresponding reserved entry byte address divided by two:

| Parent list / DSP | Absolute packet byte | Pool value | Reserved entry byte | Owner descriptor |
|---|---|---|---|---|
| `610a1f18` / 4 | `2e0` | `2010` | `4020` | `610a1674` |
| `610a1f28` / 5 | `1056` | `4020` | `8040` | `610a16bc` |
| `610a1f28` / 5 | `177a` | `4820` | `9040` | `610a1704` |
| `610a1f28` / 5 | `1832` | `5020` | `a040` | `610a174c` |

The surrounding indexed transfers independently corroborate the instance mapping:
DSP5's `1056` packet contains input slots `2005/2006`, while the `1072` packet
reads `2007/2008`; the preceding `1042` packet seeds those outputs. At `177a`
and `1832`, output slots `200b/200c` and `200f/2010` occur in the same packet as
the candidate entry, while subsequent packets write input slots `2009/200a`
and `200d/200e`, then read the outputs. DSP4 similarly writes inputs `2000/2001`
in packet `2f8`, **after** candidate packet `2e0`, and reads outputs at `308`.

**Inference:** the cross-instance scale/address agreement plus IO ownership and
the six-byte `00f8` placeholder programs strongly support an effect-entry
control-flow role. The relative order also warns that pipeline/control-transfer
delay matters. The observations do not isolate which of `00a0/00a2` selects an
address, which controls conditions/link state, or when execution transfers.
No call/return or delay-slot semantics are added to the decoder/emitter.

The normal DSP1 parent list `610a1ef8` has another pair at `17e`, with pool value
`0810`, consistent with its **different** `1020` placeholder. This bounded search
does not connect descriptor `610a1d14`'s `3020` effect entry to that normal parent.
The fifth context's parent/control path remains open.

## Available implementation does not prove selection

The prior FETDRIVE study establishes its implementation bytes, program lists,
owner-compatible layouts and virtual callback identity. This pass found **no**
direct BL/B caller, recognized MOVW/MOVT/BX veneer, or raw absolute pointer to
its constructor `6104a314`/Thumb pointer `6104a315`, across this supplied image.
The `CMfxType` factory above uses a bounded 92-entry `algorithm+1` dispatch;
its RAMCLR case is reachable statically, while FETDRIVE selection through this
factory is not established. The negative search does not prove the constructor
can never be reached by computed addressing or another unrecognized path.
Do not label FETDRIVE as an observed running/selected Fantom effect. Prefer an
actually selected owner/algorithm when hardware evidence becomes available.

## Reproduce

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/effect_lifecycle_study.py local/b0c1a.bin > local/effect-lifecycle.json
$PY -m unittest discover -s tests -p test_effect_lifecycle_study.py -v
$PY tools/core1.py local/b0c1a.bin --address 0x011290ee --size 0xf4
$PY tools/core1.py local/b0c1a.bin --address 0x61056b14 --size 0x10a
$PY tools/core1.py local/b0c1a.bin --address 0x0113391e --size 0xb0
$PY tools/core1.py local/b0c1a.bin --address 0x6102dcda --size 0x12
$PY tools/core1_xrefs.py local/b0c1a.bin 0x6104a314
```

The new read-only helper pins the image hash, reuses the existing bounded
list/descriptor readers, checks controls separately from payload, and reports
numeric candidates with `execution_ready: false`. Tests cover owner-DSP mismatch,
payload-only false positives, reservation mismatch, the four actual parent
matches, all five coefficient ranges and refusal of a different image.
It emits no target commands or executable code.

A bounded OMP/Qwen draft was independently checked against these windows. Its
suggestions of a complete reset, delay-history ping-pong, a generic zero-valued
coefficient call at `011290a8`, and a batch fence at manager+2c were rejected:
those identities/effects do not follow from the supplied dataflow. No generated
Qwen code was accepted. The range/role conclusions above come from the actual
descriptor, assertion, vtable and loop reads.
