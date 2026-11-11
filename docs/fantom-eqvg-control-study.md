# Fantom EqVg math and control correspondence

2026-11-11. The Fantom ARM32 generator, setter and selected manager paths now have
an independent scalar reference checked by bounded Thumb execution. This closes
the [desktop correspondence question](coefficient-manager-processing-study.md)
for these paths. It does not establish task exclusion, hardware cadence, BMC
arithmetic precision or a loadable custom engine. No opcode profile is added.

## Evidence and execution boundary

`tools/fantom_eqvg_study.py` checks the stripped Fantom-0 bmc0 CORE1 SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`
before constructing an emulator. Capstone assertions check instructions, constants,
manager slots and descriptors. REA tools remain unavailable; these are direct
file checks and isolated CPU results, not REA Evidence records.

The selected-entry oracle uses pinned Unicorn 2.1.4 with a Cortex-M7 CPU model.
Firmware arithmetic and its original software binary64/libm helpers execute;
there are no host-math replacements. Code is mapped read/execute, private RAM
read/write without execute permission. Writes, unmapped/protected accesses,
assertion entries and a 250,000-instruction budget are checked. Firmware reset,
application initialization, OS tasks and the interrupt controller never run.
The address `414a0000` below is a private Unicorn byte array, with no device or
host-pointer connection. Original IRQ callback delivery is explicitly synthetic.

Unicorn's [official ARM sample](https://github.com/unicorn-engine/unicorn/blob/master/samples/sample_arm.c)
and [release notes](https://github.com/unicorn-engine/unicorn/releases) are the
primary tool references. The macOS JIT needs permitted execution in this session;
the sandbox kills even a synthetic MOV/BX probe with SIGILL. An initial automatic
approval rejection was resolved by documenting the user's existing emulator
authorization and tightening the selected-entry, hash and memory guards. The
approved scope remains private-memory execution only.

## Generator differences from desktop

| Property | Fantom CORE1 | Desktop ZENOLOGY reference |
|---|---|---|
| Main generator | `610732e0` | `20d8f4` |
| Active types in the checked switch | 9 peaking, 13 lowpass, 14 highpass, 16 bandpass | Also 10/11 shelving and 15 allpass |
| Other types 0..16 / cutoff zero | `(0,0,1,0,0)` | `(1,-1,1,0,0)` |
| Sample rate | Fixed 48000.0 | Default 44100, controllable in the fixture |
| Q clamp | 0.25..128 | Same bounds |
| Generator storage | Five binary32 values after software binary64 operations | Binary64 values |
| Four-argument stability test | Non-fused binary32 VFP | Binary64 with desktop FMA positions |
| Stored g offset | Round g to float, then float subtract 1 | Subtract 1 before the live float store |

The raw tuple remains `(g,b,c,d,e)`. The source high-cutoff threshold is
`23760.000228881836`, from `48000 * .5 * 0.9900000095367432`.
The reference preserves separate operation order in `coefficients()`; do not
replace its g/b calculation with a conventional biquad recipe. Gain is bounded
to +/-96 and active cutoffs must be below that threshold in the research API;
these are checked fixture limits, not recovered UI limits. Positive subnormal
binary64 angle ratios and excluded assertion paths are rejected.

The fallback difference matters with existing history. Flag-1 descriptors store
Fantom a=-1, while desktop fallback stores a=0. In the represented state recurrence,
a=-1 freezes the corresponding state update; these fallbacks cannot be assumed
equivalent for arbitrary previous history. Physical history initialization remains
unknown. Even an active lowpass at cutoff 10000, Q=.707 differs after offset rounding:
Fantom a=`-0.06153059005737305`, desktop a rounded to float
`-0.061530597507953644` at rate 48000. This is a rounding-order difference, not a
measurement of the BMC datapath.

The generator helpers start at `61072d58` (LP), `61072eaa` (HP), `61072fe4` (BP)
and `61073124` (peaking); the latter branches over a literal pool before resuming
at `610731b0`. Common g/b math is at `61070548`. The four-argument stability body
is `6107332e..610733bc`. The following six-argument overload is outside this study.

## FDRV callers, descriptors and setter decisions

FDRV `SetFilter` at `61049e86` selects either live piece and inverts the manager
query result into its envelope Boolean at `61049ed0`. Veneer `6107782e` reaches
live setter `0112b7ac`. `SetPostFilter` at `6104a0fa`, index2, instead explicitly
sets that Boolean false at `6104a1a4`; veneer `61077838` reaches output setter
`0112b580`. Therefore its generic interpolation branch exists, but this particular
postfilter callsite selects immediate writes. Real query results and other
callers' modes are not established by the controlled Boolean fixture.

The live setter calls generator veneer `01134ec0` and stability veneer `01134eb6`.
The manager vtable at `6117647c` resolves to:

| Slot | Target | Role |
|---|---|---|
| 64 | `011327e7` | Immediate program literal |
| 70 | `01132abf` | Program coefficient current read |
| 7c | `01132bd3` | Program literal interpolation |
| b8 | `011350cd` | Live envelope adapter, inserts offset0 |
| bc | `0113391f` | Generic live envelope manager |
| c0 | `01135133` | Live immediate adapter |
| c8 | `0113509f` | Live current read |

Targets retain their Thumb bit. Live flag-1 descriptors `610e5c1c/610e5c34` map raw
fields to slots 10/11/12/14/13 and 15/16/17/19/18. Thus consumer order is still
`(g-1,b,c,e,d)`. Output descriptor `610e5c4c` maps `(g-1,b,d,c,e)` in packet order.
Its raw a/b/c/d/e fields have relative program-byte copies:

| Raw field | Relative byte addresses, hexadecimal |
|---|---|
| g-1 | 4ea, 4ed, 536, 539 |
| b | 506, 509 |
| c | 526, 529 |
| d | 512, 515 |
| e | 558, 55b |

Each copy's literal width is3. `_CoefSym` contains float default at+0, table
pointer+8 and record count byte+c; records are 12-byte absolute/relative/width
triples. These are placement-specific addresses, not a new general allocation ABI.

Envelope-enabled setters choose damping b first when `abs(old b)>abs(new b)`.
The four-argument predicate decides whether to wait on that first live write or
split the output interpolation into batches1+4. Other writes retain raw order
`g,b,c,e,d`. **Fantom immediate branches always use g first**, including when b
would lead in the envelope branch. This differs from transferring the desktop
setter's no-envelope ordering. The source literal interpolation amount is100.

## Shared completion bit and ownership marker

The live b8 adapter reaches `0113391e` through slot bc. For wait=true, the generic
manager checks byte `2008480f`, asserts if already set, sets it to1, calls driver
`0113047c`, waits at `0113061c`, then clears that byte to0. Non-waited calls bypass
this marker. The source text calls it a semaphore, but this body is a plain
check/set with an assertion, not an atomic lock or demonstrated OS exclusion.

Driver `011304e4/011304e8` clears **bit1** in shared word `200847f8` before its
control store at `01130504` and target store at `01130506`. Its control value is
`08000000 | (event_ref<<28) | (wait<<24) | (EnvTC<<20)`; the manager forces event_ref2.
Selector10 remains an EnvTC index, not a measured10ms duration. Original callback
`0112f438` sets shared bit1; poll `01130620` consumes and clears it without timeout
or request identity. The six-DSP callback route remains as documented in the
[envelope/IRQ study](coefficient-envelope-and-completion-study.md).

Starting from flags3, a waited fixture writes flags1 before arming, stays pending
with marker1 when no callback is delivered, then produces flag trace `[1,3,1]`
and marker trace `[1,0]` when the original callback is explicitly delivered.
Bit0 is preserved. Non-waited writes leave both flags and marker alone. The
self-check also verifies the clear/control/target store order.

Consequently the desktop preposted-flag counterexample must not be transferred
to Fantom: this path clears the old bit before starting its request. This still
does not prove ownership of the next interrupt. Shared untagged completion,
interrupt masking, competing callers and atomicity of read/modify/write on the
shared flag word remain unresolved. Source caller chains and the marker have
been traced; real task identity/exclusion is not established.

## Program interpolation and emulator limit

Generic `01132bd2` checks program marker byte `2008480c`, sets it, snapshots
baseline/delta arrays at `200a1960/200a1b60`, interpolates, and finally releases
that marker. For amount 100 it requests 99 unit-sample waits per batch and writes
all final targets, including unchanged coefficients. Deltas, step ratios and
VFP VMLA intermediates are binary32 with separate multiply/add rounding. The
current-read callback, program-literal primitive `0112ff4e` and sample-wait
primitive `011271b8` are recorded callbacks in this fixture; their codecs, MMIO
and elapsed time are not executed or calibrated.

Source normalizes amount to `max(abs(amount),1)`; the independent scalar model
covers negative values. Negative-amount execution currently faults near a Thumb
IT path in Unicorn and reaches an unmapped store. The fixture versus engine cause
has not been isolated. Negative amounts are explicitly rejected by
the execution fixture, without patching firmware or relaxing memory guards.
Flushing translation state between calls fixes a separate repeat-call failure;
positive stock amount 100 and amounts0/1/2/3 pass. Upgrade this limit only after
an independently checked fixture/engine fix. No negative-path CPU result is claimed.

## Checks and reproduction

The CLI checks 4,080 regular plus 500 irregular coefficient fields bit for bit,
2,000 stability decisions, 48 setter combinations, 48 live control cases and 20
literal cases. The latter compare 2,160 physical-copy writes and 408 unit wait
requests, including empty, unchanged, one-field and four-field batches.
The generator executes original software math; scalar expected results do not
consume its intermediates. Literal write traces compare binary32 bytes.

```sh
python3.13 -m pip install -r requirements.txt
python3.13 tools/fantom_eqvg_study.py local/b0c1a.bin
python3.13 tools/fantom_eqvg_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_eqvg.py -v
```

This session keeps Unicorn under ignored `local/fantom-python`, so its commands
use `PYTHONPATH=local/fantom-python:tools`. Corpus-free scalar tests need no
Unicorn or vendor payload. CPU tests skip if the dependency or corpus is absent.
Focused and full-regression results are recorded in the work log.

Qwen completed a 43.1-second bounded static review on the Mac Studio. Its bit1
clear and unproved-ownership observations were independently checked. Its nearby
bit2 waiter was not accepted as a bit0 sample-wait mapping; the supplied excerpts
did not establish that mapping. Worker logs and listings remain ignored locally.

Next trace the manager query implementation and task callers that select the
live envelope branch, plus actual sample-wait/interrupt ownership. Physical
precision, completion cadence, history policy, entry/return and safe loading
still require separate evidence. This is ARM control emulation, not full BMC
instruction emulation or a working custom engine on the Fantom.
