# Parent control references and the nested organ effect graph

Follow-up: [condition fields and implicit returns](condition-fields-and-implicit-return-study.md)
connects four native predicate inputs to exact DSP literal fields and bounds the
return packet's payload. It does not assign a saved-PC source or transfer timing.

2026-11-10. Static Capstone/file analysis; no REA provider or target execution.
CORE1 payload SHA-256:
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
ZENOLOGY arm64 SHA-256:
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.

This pass connects the fifth DSP1 effect reservation to a nested organ graph,
finds the desktop DSP4 routing list missed by the existing inventory limit, and
cross-checks four desktop call sites against their actual native IO pointers.
It also finds shifted `00a6/00a8` variants. These constrain the shared-pool operand
hypothesis, but do not establish call timing, link state or `00f8` return semantics.
The production decoder, emitter and inventory counts remain unchanged.

## The fifth context sits inside the organ effect graph

The normal DSP1 routing list `610a1ef8`, primary entry `20`, has the already
recorded `00a0/00a2` candidate at program byte `17e`, pool value `0810`.
Its doubled value is the nested entry **`1020`**. The stock placeholder at that
entry is replaced by a distinct aggregate render list:

| Aggregate list | Segment entry | Length / capacity | Source |
|---|---|---|---|
| `610b88f0` | `1020` | `14a / 1000` | `610b89c4` |
| same | `6020` | `14a / 1000` | `610b8b10` |

All addresses and sizes are hexadecimal. Its loader at `01128762` calls owner
manager+28 with this render list and owner+2c with DRAM-IO list `610b88f8`.
The literal loads are `0112876c/776`; the loader is a real code reference, rather
than merely a list-shaped byte candidate.

In aggregate segment 0:

| Absolute program byte | Candidate control | Indexed pool value | Doubled candidate entry |
|---|---|---|---|
| `1026` | `00a0` | `1010` | `2020` |
| `10c8` | `00a0` | `1810` | **`3020`** |
| `1110` | `00a0` | `2410` | `4820` |

At `10c8`, the same packet stores shared output slots `20f0/20f1`; the next
packet at `10d8` stores input slots **`20ee/20ef`**. Packet `10ec` reads `20f0`
again. These are exactly the fifth effect context's IO operands and entry in
descriptor `610a1d14`, independently recovered in the earlier kernel study.

The CORE1 management object path supplies a second ownership cross-check. Aggregate
constructor `01128730`, reached through veneer `61077734`, installs three
subinterfaces at object+8/+c/+10:

| Subinterface | Address-point vtable | Exact RTTI name |
|---|---|---|
| `+8` | `6117c430` | `N19CFspOrgnEFX_COMPLEX16CMyDSPSysOrgnChoE` |
| `+c` | `6117c418` | `N19CFspOrgnEFX_COMPLEX15CMyDSPSysOrgnOdE` |
| `+10` | `6117c448` | `N19CFspOrgnEFX_COMPLEX16CMyDSPSysOrgnRotE` |

The existing manager constructor at `6102cd26..338` installs descriptor
`610a1d14` and instance-related pointer **aggregate object+c**. Thus this fifth
manager is bound to the nested organ **Od** interface. This closes the structural
connection missed when searching only the normal parent primary stream.
It still does not prove which specific algorithm is selected/running on a unit.
The second aggregate segment has analogous numeric entries `7020/8020/9820`
and different IO slots; they are not substituted for descriptor `610a1d14`.

## Desktop DSP4 has a 24-segment list

The selected LP64 list header at **`9faed0`** is kind 0, DSP 4, count **24**,
table `9fc3e8`. Its primary segment is byte entry `20`, length/capacity `1766`,
source `77d494`. Existing `extract_zenology.program_lists()` deliberately admits
at most 16 segments, so this list was absent from `zenology_inventory.json`.
This is a bounded scanner omission, not evidence the artifact lacked a DSP4 graph.

The primary stream contains the paired candidate at byte **`82e`**:
controls `00a0/00a2`, referenced pool words `0bc3/2010`. The second word doubled
is **`4020`**, a six-byte placeholder entry in this same list. Native
`CSimDSP4Routing::VSubProc` callback `41cd8` uses shared input indices `16/17`
and output indices `18/19`, matching program operands `2016..2019` in the
surrounding primary packets. Firmware's corresponding first effect context uses
different program offsets/IO indices, so the desktop and Fantom parents are not
claimed byte-identical.

The list's segment at entry `1786`, length `44`, starts with `0000` and fails the
current render packet grammar. Other entries include zero-length reservations.
The new helper frames only the primary stream and six-byte placeholders; it
does not turn every record into an admitted render program. No old corpus
observation total is increased by this study.

## `00aN` references move with the shared pool

The desktop DSP5 routing list is `9faee0`, count 8, table `9fc628`; primary
entry `20`, length `519a`, source `77ece0`. Its observed controls support this
specific hypothesis: **the low nibble is a byte offset into the shared pool**,
as for the existing indexed-transfer family. It is not a fixed identity split
in which `00a0` always means one operation and `00a2` always means another.

| DSP5 parent byte | Controls | Pool offsets / values | Matching listed entry |
|---|---|---|---|
| `3f02` | `00a0`, `00a2` | `0:28bb`, `2:4000` | `8000` |
| `43f8` | `00a6`, `00a8` | `6:28bb`, `8:5800` | `b000` |
| `44b6` | `00a6`, `00a8` | `6:28bb`, `8:4800` | `9000` |
| `49ce` | single `00a0` | `0:6600` | `cc00` |

The `43f8/44b6` packets have additional long-operation/extension material before
these words. Reusing a fixed second-pool-word rule would select `2800`, not their
actual listed entries. Conversely the single-control context uses its first word
as the candidate entry. Operation-family/header distinctions remain essential.

**Inference:** paired forms carry a condition/control word plus a target word;
single forms can carry just a target. This fits the observed pool displacement,
listed entries, native conditional callbacks and surrounding IO. It does not
prove each base word is an independent instruction, assign a condition bitfield,
or generalize to unobserved headers/odd-index forms. The helper reports the raw
references and numeric entry matches under this hypothesis, never decoded calls.

## Native callbacks constrain functional order, not DSP issue timing

The following native call sites have direct pointer provenance from the core's
second circular array, using `(index - array_base) & 7ff`, double elements:

| Native callback | Object selection path after `this+28 → +8` | Inputs | Persistent outputs | Matching desktop parent |
|---|---|---|---|---|
| DSP4 `41cd8` | `+50 → +28 → vtable+20` | `16/17` | `18/19` | `82e → 4020` |
| DSP5 `34c374` | `+68 → +28 → vtable+20` | `459/45a` | `45b/45c` | `3f02 → 8000` |
| DSP5 `34c8b0` | `+60 → +28 → vtable+20` | `462/463` | `464/465` | `43f8 → b000` |
| DSP5 `34cb60` | `+58 → +28 → vtable+20` | `467/468` | `469/46a` | `44b6 → 9000` |

Each input/output pointer array is built on the native stack before the actual
`BLR`; output loads occur after it. DSP4/DSP5's first context seed outputs with
fallback values, while DSP5's later contexts zero the persistent outputs before
the condition. The three DSP5 native conditions use the finite-value boundary
`abs(control) >= 2^-32`; the DSP4 condition combines two nonzero-value tests.
Those are native predicates, not decoded meanings of `28bb` or `0bc3`.

The last native call has **four output pointers**: its first two point to stack
double temporaries (`sp+10`, `sp+8`); the next two point to shared `469/46a`.
Do not impose a universal two-output callback ABI from the simpler MFX context.
These desktop calls also select different interfaces/effect contexts; the table
does not identify all three DSP5 calls as interchangeable MFX instances.

When their conditions bypass the call, the native methods execute explicit zero
stores into several core-owned arrays. Those branches are separate from the
effect callback and the earlier RAMCLR coefficient loop. Their existence does
not establish a hardware reset operation or allow arbitrary state to be omitted.

The actual DSP source order prevents an eager sequential interpretation:

- Desktop DSP4 issues the pair at `82e`, writes input slots in `846`, then reads
  outputs starting `85a`.
- Firmware DSP4 issues its pair at `2e0`, writes inputs at `2f8`, then reads
  outputs at `308`.
- Firmware DSP1's nested candidate is `10c8`, input stores are `10d8`, and output
  use starts `10ec`.

A working model must explain why the callee consumes the intended inputs and
returns before the caller uses its outputs. The native callback proves that
functional dependency. It cannot distinguish delayed control transfer from
transfer-port latency, special packet scheduling, link-update timing or a
combination. No delay-slot count, saved PC or nesting limit is inferred here.

## `00f8` remains a return candidate

Every six-byte desktop DSP4/5 placeholder inspected here contains `00f8` as the
sole control of its first packet, followed by compact `0001`. The desktop DSP5
primary also contains `00f8` at bytes `5198` and `51b4`; the DSP4 primary contains
none and ends with compact `001f`, then `0001`. Earlier effect contexts place
`00f8` before additional scheduled stores/mute controls.

This supports a return/control-transfer role in callable fragments, while
contradicting treating it as a universal whole-program terminator. No execution
trace identifies its return address source, delay or fall-through behavior.
`0001` is still the independently established NOP; its position after `00f8`
does not by itself prove a mandatory one-packet delay slot.

## Reproduce and remaining gates

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/parent_control_study.py local/b0c1a.bin --native-bin local/zen_arm64 > local/parent-controls.json
$PY -m unittest discover -s tests -p test_parent_control_study.py -v
$PY tools/core1.py local/b0c1a.bin --address 0x01128730 --size 0x64
$PY tools/core1.py local/b0c1a.bin --address 0x6102cd26 --size 0x16
```

Three tests cover shifted references, payload/control separation, truncated pool
references, selected native-list bounds, the 24-record list, four DSP5 numeric
matches, nested DSP1 entry `3020`, and exact placeholder `00f8` observations.
Both artifact hashes are pinned. Native disassemblies/generated data stay in
ignored `local/`; no Qwen result or generated code was used in this pass.

Remaining execution gates: condition encoding, operation/header arity, saved
return state, nested-call capacity, transfer and return timing, hardware numeric
behavior and an owned stock task/manager entry. This study supplies no runnable
wrapper, firmware command, deployment tool or new production opcode admission.
