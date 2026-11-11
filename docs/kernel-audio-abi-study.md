# Kernel context, routing and program ownership

Follow-up: [effect lifecycle and parent entries](effect-lifecycle-and-parent-entry-study.md)
traces the generic replacement caller, RAMCLR coefficient zeroing and DRAM-IO cleanup,
and four parent entry-reference candidates. It also bounds the evidence for FETDRIVE
selection: available implementation bytes do not prove stock activation.

The [label-target study](label-target-encoding-study.md) checks the implemented
manager reference writer: six-byte records, even-byte targets shifted right once,
per-reference guard scope, and width/address truncation. FETDRIVE's actual entry
label has zero counted references; this does not bind a parent call or reveal
return state. The original voice plans retain no executable wrapper or load address.

2026-11-10, branch `research/kernel-abi`. Static file/Capstone 5.0.7 analysis,
not REA-provider or runtime evidence. CORE1 addresses below apply only to bmc0
MI078 C1A v1.08, payload SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
Native comparison: ZENOLOGY arm64 SHA-256
`b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.

**Result:** a concrete stock effect context is recoverable, including manager-owned
reservations, shared routing slots and an actual mute-control update. This supports
an offline inspection tool and a staged stock-context probe design. It does not
establish a complete standalone DSP kernel, safe injection point or cycle budget.

**Transport constraint:** normal BMC IPC uses `/dev/ttyGS0`; prepared shell update
packages can contend with it. This study changes neither package nor payload. A
future probe cannot assume that gadget is an unused debug channel.

## Evidence anchors and question status

| Question | Result and evidence boundary |
|---|---|
| `ff71` / `ff70` | Stock `SetMuteMode` reads and patches this control family; lifecycle callers distinguish opening and muting. Actual silicon skip/clear behavior remains unobserved. |
| `ff75`, `00f8` | Exact stock contexts and counterexamples recovered; execution meaning remains unknown. |
| IO ownership | Native DSP4 routing writes/reads shared effect slots; the addresses relocate between instances and differ in Fantom. No physical TDM mapping. |
| Program/data ownership | CORE1 `SDSPSegmentInfo` fields and five effect reservations mapped from constructors and manager bodies. |
| State initialization | Native core clears and stock global transition clearing are observed; effect `SetAlg` itself does not prove a complete state reset. |
| Manager context/order | Concrete manager objects, vtable paths and effect mute/load ordering recovered; safe arbitrary task entry remains unresolved. |
| Minimal probe | Retain the stock graph/instance and use its mute plus live gain controls first; new fragment execution remains gated on wrapper/routing/timing evidence. |

## The first control is mutable mute state

The CORE1 `CBmcDspMgr` address point is `0x6117647c`. Vtable slot `+0xe0`
contains Thumb pointer `0x01133b39`. Its target has the assertion signature
`void CBmcDspMgr::SetMuteMode(const LabelSym *, bool)`.

The body at `0x01133b38`:

1. Takes the shared program check/set flag at `0x2008480c`.
2. Resolves the label's absolute u16 address, or manager render base plus the
   label's relative u16 address and segment byte at `+4`.
3. Reads the first 16-bit word through `ReadLiteralRaw` (`0x0112f6e8`) and takes
   its low five bits as the halfword count to scan.
4. For following halfwords, compares `(word >> 2) & 0x3fff` with `0x3fdc`
   (`0x01133bde..be4`), equivalent to `word & 0xfffc == 0xff70`.
5. Writes `0xff70 | saved_bool` as a width-2 raw value and releases the flag
   (`0x01133be6..3c00`). A failed search asserts; it does not invent a wrapper.

For FETDRIVE, label `0x610e7b98` has absolute `0x4020`, relative 0, segment 0.
The first packet is `0a02 ff71`; the scan finds its single control at base+2.
The actual lifecycle uses bool 0 for opening and bool 1 for muting. Thus `ff71`
is not an immutable generic entry opcode. The hardware consequence of mute mode
(skip, suppress stores, clear, or another action) is still unknown; do not infer
that it writes numerical zero to every output or clears filter history.

This scan excludes `ff75` (`ff75 & fffc == ff74`). Voice-side `ff75` is not a
drop-in substitute for this effect gate. In the small FETDRIVE image `00f8`
appears in the output-store packet at relative `0x1ba`, followed by a distinct
`0a02 ff70` packet at `0x1c6`. It is not the final packet. An empty DSP4 effect
stub from `0x610a8bcc` is six bytes: a packet containing `00f8`, then compact
`0001`; it has neither the opening `ff71` nor trailing `ff70`. FZ also has no
initial `ff71` in its `0x37e`-byte implementation. These are counterexamples to
making an executable wrapper from a universal `ff71/body/00f8` recipe.

## Exact stock mute search and its limits (2026-11-11)

`tools/mute_mode_study.py` now checks the actual CORE1 resolver/search instructions
and the first FETDRIVE packet in each of the five recorded effect placements.
This is a static/file analysis and original pure-Python model; no instrument,
firmware routine or plugin is executed.

The label resolver at `01133b7a..ba6` differs from the counted label-target writer.
With a null render pointer it uses the representative absolute u16. Otherwise it
checks only the signed reservation count against the unsigned segment selector,
loads the selected base and adds the relative u16 with 32-bit wrap. **It never
loads or compares the reservation capacity**, and checks no entry parity. The
offline helper must not reuse the stricter `label_target_study.resolve` behavior.
This models firmware behavior; it is not validation of a safe entry address.

After the first width-two raw read, `01133bb8` takes **header & 31**. The loop
starts at word one and continues while index < that count. Its byte address is
entry + 2×index. At `01133bde..be4`, `(word >> 2) & 3fff == 3fdc` means
`word & fffc == ff70`. There is no operation-family or control/payload check.
A matching literal payload can therefore be selected. The **first** match is
written and the function returns; later matches are not changed.

The replacement at `01133be6..bfc` is exactly `ff70 | bool`, width two with raw
alignment enabled. Both `ff72` and `ff73` qualify, and either is rewritten to
`ff70` or `ff71`; bit one is not preserved. This is a host-manager mutation
rule, not evidence for the silicon meaning of these four words. `ff75` does
not qualify. Neither standalone `00f8` nor the coissued return/output packet
supplies a match. The real FETDRIVE entries `4020/8040/9040/a040/3020` all have
opening `ff71` at entry+2 and produce the expected bool-false plan.

The firmware loop does not implement the generic framer's compact-`001f` rule:
it would request 30 following halfwords. The offline checker rejects that
compact first-packet form rather than silently limiting the scan to zero reads.
It also requires one complete supported packet and a true Python boolean; these
are explicit offline input restrictions, not extra firmware checks.

The guard is set before resolving the label. Its invalid-segment error path
restores the stack and tailbranches to the assertion handler without clearing
the guard in this body. Search failure calls the assertion handler and has a
subsequent guard clear if that call returns. This is not a mutex, a scheduler
fence, a proof of halt, or a demonstrated way to replace running program bytes.
Recovery from firmware assertions and actual mute effects remain unobserved.

```sh
python3.13 tools/mute_mode_study.py local/b0c1a.bin
python3.13 -m unittest discover -s tests -p 'test_mute_mode_study.py' -v
```

Seven tests check actual instruction anchors and five stock packets, first-match
order, all four matching words, payload collisions, excluded return/ff75 forms,
compact-framing disagreement, missing matches, wrap and unchecked capacity,
strict offline inputs and mutated evidence. Qwen's supplied-trace review returned
in 3.0 seconds. It correctly identified first-match replacement, but confused
header/control/payload roles and called the 14-bit extraction 20 bits. Those
claims were corrected against the instructions; no worker code was adopted.

The exploratory nonempty-label scan remains ignored under `local/`: shape-only
candidates do not establish LabelSym type or ownership, and none is admitted as
an incoming parent-call handle. No CALL/RETURN, continuation or loading gate is
closed by either investigation.

## `2016..2019` belong to a shared routing context

In native `CSimDSP4Routing::VSubProc` (`0x000413d0`), the path at
`0x00041bc0..bd0` resolves the core's **second** circular data array and its
base pointer. It then:

- Stores fallback output values at indices `0x18/0x19` (`0x00041c54..c78`).
- Stores scaled input values at `0x16/0x17` (`0x00041c84..ca8`). Each effective
  array index is `(absolute_index - array_base) & 0x7ff`.
- When its condition is enabled, passes pointers to `0x16/0x17` as the input
  pointer array and `0x18/0x19` as the output pointer array to the selected
  effect's virtual method at `0x00041cd8`.
- Reads slot `0x18` again at `0x00041da8..db8`, after that conditional call.

This explains the agreement between direct native arguments in FETDRIVE and
tag-2 memory accesses in FZ. It establishes shared routing storage, including
preseeded outputs when the effect call is bypassed. It does not establish
peripheral channels, codec pins, TDM slots, or an independent audio callback ABI.

The addresses are not fixed even within the desktop corpus. FETDRIVE and
LINEDRIVE's second image uses inputs `2459/245a` and outputs `245b/245c` where
the first uses `2016..2019`. The corresponding Fantom render lists use:

| List segment | DSP selected by manager | Program base / capacity (bytes) | Input operands | Output operands |
|---:|---:|---|---|---|
| 0 | 4 | `4020 / 1000` | `2000/2001` | `2002/2003` |
| 1 | 5 | `8040 / 1000` | `2005/2006` | `2007/2008` |
| 2 | 5 | `9040 / 1000` | `2009/200a` | `200b/200c` |
| 3 | 5 | `a040 / 1000` | `200d/200e` | `200f/2010` |
| 4 | 1 | `3020 / 1800` | `20ee/20ef` | `20f0/20f1` |

FETDRIVE list `0x610e7b88` and LINEDRIVE list `0x611084fc` both have five
segments and **header DSP byte 1**. Their lengths are `0x1ca` and `0x242` per
segment. Header DSP 1 is not the destination of every segment: the segmented
manager path selects both DSP and segment subset from its descriptor.

Independent firmware corroboration: normal DSP4 list `0x610a1f18`, primary
base `0x20`, source `0x610a5614`, contains indexed transfers targeting `2000/2001`
at absolute program byte `0x2f8`, and loads `2002/2003` at `0x308`. The earlier
transfers at `0x2ce/0x2e0` also target `2002/2003`. Port E/F arithmetic semantics
are not assigned here; this establishes actual operand use in the surrounding
graph, not a recovered schedule of its calls into effect segments.

## CORE1 resource descriptor and placement rules

Manager objects constructed at `0x6102c924` use vtable `0x6117647c`, common
object pointer `0x2009be2c` at manager+4, the descriptor at manager+8, and an
instance-related pointer at manager+`0x10`. The manager is 20 bytes in these
constructors. The `0x10` pointer varies; copying only the descriptor into an
invented manager object loses context.

| `SDSPSegmentInfo` offset | Observed field / evidence |
|---|---|
| `00` | u32 DSP index |
| `04` | Render reservation pointer, `{u32 byte_base, u32 byte_capacity}` stride 8 |
| `08`, `09` | First program-list segment byte, signed count byte |
| `0c` | DRAM-IO reservation pointer; separate program format |
| `10`, `11` | First DRAM-IO segment byte, signed count byte |
| `14` | Additional reference pointer; not decoded as a render reservation |
| `18`, `1c` | Memory enum 6 reservation pointer and count |
| `20`, `24` | Enum 0 reservation pointer and count |
| `28`, `2c` | Enum 1 reservation pointer and count |
| `30`, `34` | Enum 2 reservation pointer and count |
| `38`, `3c` | Enum 5 reservation pointer and count |
| `40`, `44` | Enum 11 reservation pointer and count |

Memory records are `{u32 base, u32 length}` stride 8. `ParseDspMemoryWordAdrs`
at `0x01131968` selects the listed groups by the `_DataSym` enum byte at
`+0x10`. When a group exists it checks the symbol segment, relative index less
than length, and relocation flag at symbol+`0x12`, then adds the reservation's
base. Without a group it returns the symbol's absolute value. Enum numbers are
not converted here into guessed physical RAM names.

The five descriptors selecting the effect images above are:

| Descriptor | DSP / first / count | Enum 0 base,length | Enum 1 base,length | Enum 6 base,length |
|---|---|---|---|---|
| `610a1674` | 4 / 0 / 1 | `100,96` | `47e,0` | `190,14` |
| `610a16bc` | 5 / 1 / 1 | `320,96` | `44c,0` | `1f4,14` |
| `610a1704` | 5 / 2 / 1 | `3b6,96` | `44c,0` | `208,14` |
| `610a174c` | 5 / 3 / 1 | `44c,96` | `44c,0` | `21c,14` |
| `610a1d14` | 1 / 4 / 1 | `c0,c0` | `70,0` | `e,14` |

All values in these tables are hexadecimal except DSP/first/count. Enum 1 has
zero private length in these descriptors despite real shared tag-2 IO accesses
in their programs. Its base is not a private allocation of `2016..2019`.

The manager methods are materially different:

| Path | Actual checks and destination |
|---|---|
| All-program `01131c4e` | Manager DSP <7, equals list DSP, list type 0; walks every list segment and writes its base/length. Does **not** load the segment capacity field. |
| Segmented `01131e70` | Requires manager reservations; checks first+count <= list count and each selected length <= owner capacity. Writes **list base**, not owner base. No list-DSP equality check in this body. |
| Unique segmented `0113214e` | Checks owner count <= list count and lengths <= owner capacities. Takes source segments starting at 0, writes **owner base**, ignoring their list bases. |

The latter two do not themselves relocate internal memory operands, labels or
coefficients. Replacing a list's base cannot relocate a complete effect. The
non-unique path checks length but trusts destination base: the new offline
inspector additionally requires it to match the owner reservation. This stricter
policy is explicit; it is not an undocumented firmware guarantee.

## Render-write source extent and completion state (2026-11-11)

`tools/program_write_study.py` checks the pinned CORE1 `StackWriteDspProg`
(`0112f582`), listed-copy builder (`0112f290`), completion helper (`0112f6a4`)
and callback (`0112f42c`). These are static instruction/byte checks and an
original offline geometry/state model; no firmware routine or instrument runs.

### Halfword edges precede the bulk copy

The writer requires an even destination/count. It adds the selected program
aperture, then handles a destination at word+2 by reading **LE16[source]**, writing
that value through the width-two raw port with alignment true, subtracting two
bytes, advancing destination by two and source by **four**. Thus this source is
not an arbitrary tightly packed halfword stream.

If the remaining count has bit one set, the writer next reads a **full source
word** at index `((remaining+3)>>2)-1`, clears its low sixteen bits, and writes
it to destination + (remaining & ~3) with raw alignment false. It subtracts two
more bytes. Only then does it copy the remaining aligned bulk bytes unchanged.
Bulk below 64 bytes uses the CPU loop; bulk of at least 64 is queued for DMA.
The threshold is evaluated **after** removing both edges. These are write-order
facts; no atomic program replacement or live exclusion follows from them.

For the original shaped voice at recorded base `4020`:

| Step, in actual call order | Destination | Written bytes | Source read |
|---|---|---:|---|
| Raw tail | `421c` | 2 | Full word at source+508, high half retained |
| Queued bulk | `4020` | 508 | Source bytes 0..507 |
| Total | `4020..421d` | **510** | Backing source extent **512** |

Addresses are hexadecimal; sizes and source offsets in this table are decimal.
The final two source padding bytes are read in the last word but discarded from
the raw value. They are not written when the caller supplies count 510. Passing
the stored size 512 as the count instead requests two additional destination bytes.
The raw tail can be updated before any queued bulk starts; a source-buffer hash
or completed function call by itself does not establish an atomic replacement.

For a destination at word+2, encode the source by adding **two logical prefix
bytes before reversing four-byte storage words**, then pad at the end. Four
requested destination bytes need an eight-byte backing buffer: the leading read
uses source+0..1, and the trailing read uses source+4..7. For a two-byte-only write,
the convenient stored buffer still has four bytes but the actual read extent is
two. The checker reports both values instead of treating every source byte as a
destination write. All current recorded owner bases are word aligned, so exported
voice bodies require no leading prefix. The planner now records their exact
`recorded_base_write_geometry`, retaining null load/entry/return addresses.

The listed-copy builder uses at most 4095 words per sixteen-byte DMA descriptor.
The shared list limit is 32 descriptors, including those already queued. The
geometry helper assumes an otherwise empty list, rejects writes exceeding it,
and rejects literal-port aliases, 19-bit window crossings and aperture/end wrap. These are declared offline restrictions; the
checker does not assert that the hardware program RAM is that large or available.
DMA retains source addresses, so source and descriptor storage must remain valid
until actual completion. Nothing here supplies those lifetimes on a running unit.

### This completion helper is not an active-transfer drain

| Initial state byte at `200847f0` | Wait false | Wait true |
|---|---|---|
| 0 | Immediate return | Immediate return |
| 1, queued | Clear event 4, set state 2, start list, return | Same start, then wait for a new event 4, clear it and set state 0 |
| 2, started | Immediate return | **Immediate return** |

`0112f6ac..6b0` tests state 1 and returns before inspecting the wait argument.
The callback at `0112f42c` only ORs 4 into the event word at state+8; it does
not reset the state byte. Therefore **start(false), then call this helper(true)
is not a drain**, even after the callback has set its event bit. A waiting
state 1 path clears a stale event before starting, so its successful return needs
a subsequent completion event under the declared no-other-writer model. These
paths do not establish DMA visibility, source cache handling, task ownership,
bounded completion time or a safe external calling context.

The stack writer also asserts on state 2 before its zero-count early return.
Its later large-copy branch contains a state 2 wait/reset path if that earlier
assertion returns. The checker does not treat an assertion path as an authorized
synchronization method. The program guard and this queue state remain distinct.

```sh
python3.13 tools/program_write_study.py local/b0c1a.bin
python3.13 -m unittest discover -s tests -p 'test_program_write_study.py' -v
```

Tests independently replay asymmetric stored bytes into canary-surrounded logical
memory for both destination alignments and every even count 0..130. They check
the real 510-byte voice, full-word tail read, discarded source padding, CPU/DMA
thresholds, 4095-word splitting, shared-list bounds, all completion-state paths
and modified firmware anchors. Voice-plan tests verify the new geometry across
all five recorded assignments. Numerical program capacity again uses logical
write length 510; the previous512-byte requirement was a conservative policy,
now distinguished from the proved 512-byte source footprint.

Qwen's no-tool review returned in 4.1 seconds but confused source read extent,
source halves and the state 2 early return. Those claims were rejected against
the instructions and independent replay; no worker code was used.

### Separate active DMA drain and manager wrappers

Follow-up on 2026-11-11: the missing active drain is implemented at **`0112f508`**.
It checks the same global state byte for **2**, returns for states 0/1, polls
event 4 without clearing it first, clears that bit and resets the state to 0.
It does not start an unstarted queue. An already-set event satisfies the poll;
source lifetime still depends on the stock event/ownership protocol.

The manager address point `6117647c` supplies two distinct wrappers:

| Slot | Body | Checked behavior |
|---|---|---|
| `44` | `01132472` | Takes this in r0 and wait in r1, forwards wait to `0112f6a4`, then handles a possible pending DRAM-IO update |
| `48` | `011324a2` | Tailbranches to `0112f508`; the drain uses global state rather than a per-manager DMA queue |

The extra slot 44 path reads a per-DSP pending byte from `20084810`, clears it
if set, then dispatches manager slot 5c with descriptor+`c` and r2=1. It is not
safe to pretend slot 44 is a render-only fence when that state is pending.
The checker retains this side path rather than offering a blind live call.

The all-program nonwaiting manager path skips `0112f6a4` entirely. Thus queuing
without its final wait can leave state 1, with DMA not yet started. Calling the
active drain then returns immediately. Correct offline state distinctions are:

- **Queued state 1:** the start helper can initiate it, optionally waiting during that start.
- **Started state 2:** the separate active drain can wait for its event and reset the state.
- **Idle state 0:** both helpers return without initiating work.

These are recovered firmware operations, not a tested upload sequence or a halt
protocol. The active-drain model and actual vtable/body anchors now have regression
coverage, including preexisting event bits and unstarted queues. No routine was run.

## Stock effect lifecycle and state boundaries

The exact RTTI `15CFspMfxFETDRIVE` points to vtable group `0x6117a0fc`, whose
address point is `0x6117a104`. Its `SetAlg` callback is `0x6104a35a`. Actual
branches and arguments give this sequence:

1. Manager vtable `+0x28` writes the manager-selected render segment from
   `0x610e7b88`, with final DMA wait enabled (`011350ae` → `01131e70`).
2. Manager `+0x2c` writes the selected DRAM-IO list `0x610e7b90` with wait enabled.
   The DRAM-IO page machinery is distinct from render-program loading.
3. Calls wait helper `0x011271b8` through `0x6107769e`, count 1, completion 1.
4. Calls its own level setter with 127 (`0x6104a380..388`).
5. Calls `SetMuteMode(label=610e7b98, false)`, then passes the master symbol
   `0x610e7ba8`, float 1, envelope argument 10 and final flag 0 through manager
   `+0xb0` (`0x6104a38a..3be`).

The separate open routine at `0x6104a31e` performs step 5. The close routine at
`0x6104a3c4` first requests the master target zero through envelope-capable dispatch (float constant at
`0x6104a514`) with final flag 1, then sets the mute label true, then waits count
3/completion 1. The native exported `MuteOff`/`MuteOn` methods independently
have that order. The [envelope follow-up](coefficient-envelope-and-completion-study.md)
now identifies argument 10 as an EnvTC selector and the final flag as wait/no-wait
on the with-envelope path. Another dispatch Boolean can select a without-envelope
method. Native selector10 corresponds to nominal12 ms in its 44100-based formula;
the actual Fantom ramp timing and runtime dispatch choice remain unverified.

The wait helper operates a completion flag at `0x200845b4`, installs an IRQ
callback, and arms a counter through `0x01103772` at MMIO `0x40059000`. The
neighbor at `0x0112721a` multiplies its argument by 48000 and divides by 1000
before using the same mechanism. **Inference:** the first API counts units
related to a 48 kHz timebase. That does not prove timer calibration or elapsed
sample boundaries on a unit; the transition counts remain counts here.

Neither this `SetAlg` body nor `SetMuteMode` clears all effect data history.
Native `SIM_MFX_FETDRIVE::Init` allocates constructor/default/symbol storage;
its `EndProc` frees it. Those allocations are not a hardware state reset.
Native `CSimDSP4_Core` constructor zeroes two circular arrays and initializes
its CBMCDrm arrays (`0x0016bbb0..bc04`), at a larger ownership boundary.
The [global transition study](core1-receive-and-test-controls.md) separately
records clears, waits, temporary programs and normal graph restoration before
DAC enable. Preserve both distinctions: per-effect parameter setup versus whole
graph state initialization.

The program and coefficient methods use a check/set/clear byte, not a demonstrated
blocking or atomic lock. DRAM-IO uses its neighboring byte. Nonwaiting uploads
can release the program flag with DMA work still pending. A new IRQ/worker must
not treat a zero flag as sufficient synchronization. Joining the actual stock
task, maintaining object lifetimes, completing queued DMA and bounding waits
remain requirements; a universally safe new entry context has not been found.

## Minimal probe design and hardware gates

The smallest supported design retains **one complete stock effect instance and
its parent routing graph**. Keep all program bytes, DRAM-IO setup, labels,
reservations and state initialization intact. Initially vary the already matched
dry/wet and live gain parameters. No standalone executable is emitted.

For FETDRIVE segment 0 the independently matched tail is at relative `0x16a`:
wet data `0117/0118`, dry/wet/post/master coefficient operands
`c192/c193/c194/c190`. The corresponding `_DataSym` handles are
`610e7be0` (dry), `610e7bfc` (wet), `610e7c18` (post), `610e7ba8` (master).
Their enum is 6; their relative indices are 2,3,4,0 in the manager's reservation.
The handle's relocation records refer to the matching program operands.
The [native MAC proof](dry-wet-mac-study.md) establishes the formal output:

```text
outL = (inL * dry + W(0x117) * wet) * post * master
outR = (inR * dry + W(0x118) * wet) * post * master
```

The firmware and native FETDRIVE/LINEDRIVE packet headers, controls and offsets
match completely, independently checked by the new corpus regression. Their
operand values and some literals differ. In particular, LINEDRIVE's tag-0
native-to-firmware deltas are not globally constant; copying the desktop's state
layout or coefficients is not justified. No new arithmetic meanings are assigned.

| Stage | Proposed settings in verified, finite stock state | Expected observation / required readback |
|---|---|---|
| Baseline | Stock graph/parameters and externally attenuated capture | Save exact selected program, label controls, data/reservations and coefficient values; establish known channel routing. |
| Zero-output calculation | dry=1, wet=0, post=1, master=0 | Formal tail outputs zero for finite operands. Verify coefficients and both output slots; this is stronger than assuming gate mute clears them. |
| Pass-through | Same values, master=1 | Output slots follow asymmetric low-level left/right inputs; physical output still depends on parent graph. |
| Gain | Same values, master=1/4, then 1/2 | Corresponding output-slot gain ratios; compare settled intervals after stock ramps. |
| Stateful reference | Restore stock LINEDRIVE with complete state/default initialization | Record impulse/history and both native-matched allpass chains before considering any fragment replacement. |

These are proposed measurements, not measured results. A live parameter operation
must use the owner manager's actual method and handle, with its stock ramp/context;
`_CoefSym` program-literal methods and `_DataSym` live-memory methods are different
ABIs. No tool in this change calls either. Zero wet gain does not make unknown,
uninitialized or non-finite upstream state safe by itself.

Before any execution, a unit-specific entry mechanism, recovery procedure, verified
manager identity/task, quiescence point, readback path and routing capture are needed.
The firmware driver has `ReadDspProg` at `0x0112f74c` and `ReadLiteralRaw` at
`0x0112f6e8`; their presence does not establish a host command that invokes them.
Normalize readback byte order and halfword edges, compare only uploaded logical
bytes, and retain neighboring program guards. Require the selected reservation,
coefficient values and changed mute bit to read back as intended before proceeding.

Stop on a build/owner/hash mismatch, reservation violation, unexpected neighbor
change, missing completion, unknown route, clipped/non-finite output, or loss of
ordinary IPC. Remain externally muted and restore through the verified stock
lifecycle/recovery route; do not improvise SetExeMode values or blind MMIO writes.
DSP4/5's rejection of mode 2 still rules out a generic `mode 2 = run` recipe.
Cycle limits, numerical precision, gate behavior and timing remain hardware gates.

## Reproduce offline

Use the existing interpreter with Capstone; Homebrew's default Python in this
session lacked it. No dependency installation or provider repair was needed.

```sh
PY=/Users/jacob/.pyenv/versions/3.13.7/bin/python3
$PY tools/kernel_abi.py local/b0c1a.bin --list 0x610e7b88 --segment-info 0x610a1674 > local/kernel-fetdrive.json
$PY tools/kernel_abi.py local/b0c1a.bin --list 0x611084fc --segment-info 0x610a1d14 > local/kernel-linedrive.json
$PY -m unittest discover -s tests -p test_kernel_abi.py -v
$PY tools/core1_rtti.py local/b0c1a.bin 15CFspMfxFETDRIVE
$PY tools/core1.py local/b0c1a.bin --address 0x01133b38 --size 0xee
$PY tools/core1.py local/b0c1a.bin --address 0x6104a31e --size 0xf2
$PY tools/core1.py local/b0c1a.bin --address 0x01131e70 --size 0x122
$PY tools/core1.py local/b0c1a.bin --address 0x0113214e --size 0x112
$PY tools/core1.py local/b0c1a.bin --address 0x6102c998 --size 0x2a
$PY tools/core1.py local/b0c1a.bin --address 0x6102cd26 --size 0x34
```

For the native routing and core initialization anchors, still without execution:

```sh
PYTHONPATH=tools $PY - <<'PY'
import lib
for address, size in [(0x41bc0, 0x200), (0x16bbb0, 0x58)]:
    for ins in lib.md().disasm(lib.Z[address:address+size], address):
        print(f'{ins.address:08x} {ins.mnemonic} {ins.op_str}')
PY
```

`kernel_abi.py` reads exact supplied list/descriptor addresses, bounds every read
to a single mapped image region, rejects unsupported record forms and reports
`execution_ready: false`. It reports framing controls and indexed transfers
without interpreting payload literals as addresses. `--unique` models the different
source-selection/destination rule only; it performs no operand relocation. It never
writes vendor input or emits a deployable program. Build-specific addresses are
caller-selected and the output includes the image hash; verify that identity.
Detailed generated JSON/disassembly stay in ignored `local/`.

Next concrete offline lead: trace the effect-system caller that clears/initializes
an instance before `SetAlg`, and resolve scheduling from the parent routing program
to its render reservations. Next hardware experiment, once its gates are met: retain
the complete graph and measure the master-zero/pass/gain sequence above, including
program/parameter readback and adjacent-instance isolation.

## Offline LINE placement and readback comparison

The context reader uses the pinned `b0c1a.bin` to join the LINEDRIVE
list at `611084fc` to its five recorded owner descriptors. For the default
DSP4 placement it reports the expected 578 logical program bytes at
`4020`, their hash, the memory reservations, input pair `2000/2001`
and output operand candidates `2002/2003`. Allpass data, scratch, and
coefficient operands are checked against the relevant reservations.
The reported destination describes a stock placement available in the
image. Active selection must be established from the instrument.

```sh
python3 tools/fantom_line_context.py local/b0c1a.bin --owner 0x610a1674
```

The same command can compare an independently acquired, normalized
logical-byte capture with `--readback path`. It expects exactly one
578-byte LINE segment for the selected owner. It reports exact matches,
offsets of differences, and the special case where the opening
`ff71` differs only by the observed mute bit. Other changes are reported
as differences, including potential live parameter edits. The tool
has no connection to the instrument. The first hardware evidence needed
is a capture whose build, active effect, owner and DSP destination are
independently identified. [Host peer evidence](core1-task-context-and-host-peer.md)

Hardware validation is scoped to the Fantom-07. Use an independently identified
stock LINE placement to establish the active owner and audio path. Compare the
stock program bytes before interpreting sample or state observations. Once the
execution and audio paths are verified, the existing original one-pole kernel
is the first custom program candidate. JUPITER-X firmware contributes offline
operand comparisons. Its store prediction is optional corroboration and does
not gate the Fantom-07 work.
[Original one-pole kernel](fragment-emulator.md#original-one-pole-kernel)
