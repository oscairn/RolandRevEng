# Live coefficient envelopes: selector, dispatch and completion

The later [mode-query checkpoint](fantom-envelope-mode-study.md) traces the
source-bound MFX interface to a per-slot mute nesting count. Its original FDRV
caller enables envelopes only at count zero. This query is not current-task
identity; actual task/IRQ exclusion still needs separate evidence. Timer/sample
wait completion uses byte `200845b4`, separate from the clear/envelope flag word.

The later [Fantom EqVg/control fixture](fantom-eqvg-control-study.md) executes the
selected adapter, generic manager, driver, wait and original completion callback
in private emulated memory. It verifies pre-arm clearing of bit1, preservation of
bit0 and marker release after synthetic completion. This supplements the static
maps below; it does not measure interrupt cadence or prove task exclusion.

The newer [native manager processing checkpoint](coefficient-manager-processing-study.md)
executes role4 envelope registration, active scans, pending-bit transitions and
completion dispatch in owned buffers. It also checks task-flag consumption and
CDSPWait counters with controlled primitive callbacks. This supplements the native
software model; it does not turn the CORE1 mappings below into hardware timing
measurements or prove equivalent completion ownership on Fantom.

2026-11-10. Static follow-up to [kernel/audio ABI](kernel-audio-abi-study.md) and
[clear completion](clear-completion-interrupt-study.md). Pinned inputs:

- Fantom bmc0 stripped CORE1 SHA-256
  `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
- ZENOLOGY prepared arm64 SHA-256
  `b8ba7f41e26bef91e2cc38e99452e7795cd132e9f2a59695a68a77f18b8a2c30`.

This is file/Capstone analysis; no target, plugin, updater or device ran. REA's
known unavailable provider was not retried. These are not runtime measurements.
Addresses and unprefixed code constants are hexadecimal except explicit decimal units.

The time parameter is a **16-value EnvTC selector**, not a duration sent directly
to hardware. The stock manager's final Boolean controls whether it waits on a
shared completion flag. Another dispatch Boolean can choose a without-envelope
path entirely. The native model gives a useful nominal time table but cannot
establish Fantom timing or serve as a hardware-completion oracle.

## Driver and separate live-coefficient memory

Assertion-linked `0113047c` names
`CBmcDspDrv::WriteDspCoefFloatWithEnv(int,unsigned,float,EnvTC,bool,eDSP_EVENT_REF_TYPE)`.
In this hard-float ABI r0 is DSP, r1 coefficient index, s0 target float, r2 EnvTC,
r3 wait/completion Boolean; event-reference selector is on the incoming stack.
PUSH of two registers makes its load `[sp+8]`.

The driver checks signed DSP<6, unsigned index<the selected capacity,
unsigned EnvTC<16, and unsigned event-reference<9. There is no explicit negative
DSP guard in this body. Valid driver indices do not prove that a caller owns a slot.

| DSP | Live bank base | Index capacity, decimal |
|---:|---|---:|
| 0 | `414a0000` | 2048 |
| 1 | `415a0000` | 2048 |
| 2 | `416a0000` | 1024 |
| 3 | `417a0000` | 1024 |
| 4 | `418a0000` | 1024 |
| 5 | `419a0000` | 1024 |

The tables are at `0113aa90/0113aaa8`. Slot pointer is base+index*16. The driver
writes `08000000 | (event_ref<<28) | (wait<<24) | (EnvTC<<20)` at slot+8, then
stores s0 at slot+c. If wait is nonzero, it first clears bit1 in `200847f8`.
This path differs from `_CoefSym` program-literal conversion ports: the manager
requires a **`_DataSym` of kind 6** and resolves its owner-relative word address.
Do not pass a program literal-byte address into this live slot interface.

`IsDspCoefFloatWithEnvOperating` at `01130630` returns the exact predicate
`(slot_control & 0e000000) == 0c000000`. Testing bit31 alone, or merely testing
that one of these bits is nonzero, would not reproduce the stock predicate.
The returned bit pattern is an observed software test, not a proof of hardware
phase meanings, target convergence or audio quiescence.

## Manager ownership, Boolean dispatch and waiting

Direct manager `0113391e` checks `_DataSym` kind 6, resolves its address with
`ParseDspMemoryWordAdrs` at `01131968`, and adds the caller's signed offset.
Kind-6 resolution uses manager descriptor+18, the symbol's segment selector,
relative word address and flag byte at symbol+12. The underlying driver bounds
the final index against the whole bank; this does not establish that arbitrary
extra offsets stay inside the selected owner's reservation.

The manager forces event-reference 2. Only for a waiting call, it checks/sets
byte **`2008480f`**, calls the driver, waits through `0113061c`, then clears that
byte. The name `DSPMgrWaiSemEnv()` is assertion text around a plain check/set;
there is no atomic acquire or blocking mutex in this body. The byte differs from
program-write exclusion `2008480c` and DRAM-IO exclusion `2008480d`. A no-wait
call skips this envelope-byte check/set and returns after the driver invocation.

The generic master callers previously described in the kernel study use vtable
offset **b0**, rather than calling `0113391e` directly. Its actual chain is:

| Slot / target | Observed dispatch |
|---|---|
| b0 → `011350de` | Inserts offset0, forwards caller's EnvTC/wait to b4 |
| b4 → `011350f8` | Incoming r1 nonzero selects c4; zero selects bc |
| bc → `0113391e` | `_DataSym` with-envelope path |
| c4 → `011339ce` | `_DataSym` without-envelope path |

The master callsites obtain that r1 choice through another virtual callback.
Its runtime value was not established here. Therefore a call to b0 with EnvTC10
is **envelope-capable dispatch**, not proof that every stock mode actually ramps.
Open/close still pass target1/0 and wait0/1 respectively; the close call waits in
the with-envelope branch before the later mute change. No universal cross-thread
or interrupt-safe call contract follows from that ordering.

## Six interrupt sources share one completion bit

Initializer `0112f450` installs callback Thumb pointer `0112f439` for events8..d.
The callback at `0112f438` ORs bit1 into `200847f8`. Vectors and handler bodies
independently establish this route for each DSP:

| DSP | Firmware event | NVIC IRQ, decimal | Handler | Read/zero status register |
|---:|---|---:|---|---|
| 0 | 8 | 65 | `01131342` | `41100320` |
| 1 | 9 | 66 | `01131372` | `41100324` |
| 2 | a | 67 | `011313a2` | `41100328` |
| 3 | b | 68 | `011313d2` | `4110032c` |
| 4 | c | 69 | `01131402` | `41100330` |
| 5 | d | 70 | `01131432` | `41100334` |

Each handler snapshots status, increments its invocation counter and calls its
registered slot if nonzero. The callback ignores that status and does not tag
which coefficient/request completed. `0113061c` polls shared bit1, then clears it;
its DSP argument does not select a separate flag. This is distinct from clear's
event17/IRQ80 and bit0, but both bits occupy the same read/modify/write word.
No timeout or per-request identity appears in this wait. Actual event-generation
semantics, interrupt masks, caller exclusion and simultaneous operations remain
unproved. These static shared fields do not by themselves prove a runtime race.

## Native selector table and completion limits

In its envelope branch, named `CSimDSP4_Core::WriteDspCoefFloatWithEnv` (`16c468`) uses
`CBMCEnv::GetCtrlVal` (`3460cc`) to pack the same selector fields, stores that
control word in the selected native coefficient record and invokes `SetBP`
(`346734`) with duration argument -1. The mode2 table branch reaches `346870`.
There it loads current/target floats, calculates float `(target-current)*1000`,
converts to double, divides by `table[EnvTC] * 44100.0`, converts the result to
float and stores the per-update increment. Native coefficient records have a
different stride/layout from the hardware slots above.

The time table at `839df0` has 16 doubles; SHA-256
`7921c8fef9a5176a795ac75f81271637a0407bb5eab8bdb5a5a67cbd27d758b5`.
Selectors0..9 map to nominal1..10 ms; 10..14 map to12/14/16/18/20 ms; 15 maps
to24 ms. Thus the stock **selector10 corresponds to nominal12 ms in this native
calculation**, not a directly encoded10 ms duration. This neither calibrates the
Fantom hardware nor proves its table, update cadence, exact endpoint sample or
finite-precision ramp trajectory. The literal native 44100 differs from the Fantom
wait helper's 48000 scaling; the two mechanisms must not be conflated.

The native core also has an earlier conditional path: when the current-subtask
test is false and the requested wait flag is nonzero, it dispatches through its
without-envelope virtual method instead. Thus these calculations describe the
observed envelope branch, not every call bearing the method name.

Native `CSimDspMgr::IsDspCoefFloatWithEnvOperating` (`fce9c`) validates arguments
but its normal epilogue at `fcee0` returns zero unconditionally. It does not read
the hardware-style predicate above. Native coefficient updates are useful paired
semantic evidence; this manager query cannot independently validate a live BMC
completion or prove that a hardware envelope has stopped.

## Reproduce

```sh
python3 tools/coefficient_env_study.py local/b0c1a.bin > local/coefficient-env-study.json
python3 -m unittest discover -s tests -p test_coefficient_env_study.py -v
```

Use the existing Capstone interpreter. Four tests cover authored control-field
counterexamples, invalid/unknown inputs, the six real interrupt bindings and
source-pinned native table/branch arithmetic. The report emits metadata, not keys,
firmware excerpts or hardware commands. No numerical hardware model, live writer
or executable engine was added.


## FDRV control-path replay (2026-11-11)

The newer [EqVg study](eqvg-filter-generation-study.md) executes original piece
setters against recording callbacks: the live path requests a wait on its first
write when simultaneous interpolation is unsafe; the literal path splits a batch
into 1 then 4 writes. Those calls prove requested sequencing, not completion timing.
Its full-audio replay selects immediate frame-boundary groups and does not claim
to execute those waits or the manager interpolation worker.

The newer [EqFaCal control layer](fdrv-cubic-waveshaping-study.md#three-coefficient-filter-generation-and-ui-dispatch-2026-11-11)
also generates C5/C6/C7 targets from the native UI's input shelf parameters and
compares their envelope evolution during full audio replay. Resampling and post
cascade groups use literal writes instead, applied at explicit fixture frame
boundaries. Group atomicity and real scheduler interleaving remain unverified.

The [FDRV parameter checkpoint](fdrv-cubic-waveshaping-study.md#setter-derived-live-updates-2026-11-11)
now connects checked setter arguments/descriptors to four replayed control
families and compares the original native envelope arithmetic during audio.
Selector 10 remains nominal12 ms; physical timing is still unverified.

The scalar model reproduces original `CBMCEnv::VProcSync()` at `3463d8..346518`,
including binary32 step accumulation, endpoint/control clearing and the one-ULP
escape when addition stalls. A separate owned fixture executes the original
mode2 increment math and VProcSync against explicit records. No manager/event
callbacks are registered; wait is zero and the synchronization flag is zero.
Thus successful trajectories establish the numeric branch under those guards,
not the complete scheduler or hardware completion protocol.

The dynamic FDRV fixture applies one envelope update before each audio frame.
Its independent model and native records match during 13 setter-derived events,
including interrupted ramps and ring wraps. Both 12,000-frame fixed scale pairs
match 960,000 envelope record fields plus complete final audio/ring/cache state.
The actual Fantom setter slots correspond, but their binary32 VFP target math
is not presumed equivalent to the desktop's binary64/FMA calculations. EQ
coefficient generation, UI conversion, runtime branch choice and hardware cadence
remain open; no physical envelope timing or reset behavior is inferred.
