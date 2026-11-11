# Fantom envelope mode and mute nesting

The subsequent [parameter-dispatch checkpoint](fantom-parameter-dispatch-study.md)
executes the original unchanged-algorithm callback and logical live1 fields 2/3
through this mode query and setter. Raw buffers and registered-task ownership
remain unresolved.

2026-11-11. The FDRV mode query is now traced through its actual manager binding
and checked by original Thumb execution. For this CORE1 graph it reads a
**per-slot mute nesting counter**, rather than current task identity. A zero
counter enables the live filter's envelope path; a nonzero counter selects
immediate coefficient updates. This closes the mode-selection question from the
[EqVg correspondence checkpoint](fantom-eqvg-control-study.md). Actual caller
exclusion, IRQ delivery and physical timing remain unresolved.

## Concrete manager and interface binding

The pinned stripped CORE1 SHA-256 remains
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
`tools/fantom_envelope_mode_study.py` rejects another payload before any emulator
construction, then checks source instructions, RTTI, vtables and constants.
These are direct Capstone/file observations and isolated CPU results; REA tools
remain unavailable and no REA Evidence record is claimed.

The binding path is compiled source, not an inferred pointer match:

| Edge | Source evidence |
|---|---|
| System object | `2009bbf8`, loaded at `6102c934` |
| Embedded MFX controller | System+28 = `2009bc20`; constructor `6102a512` installs vtable `6117c494` at that offset |
| Concrete controller type | RTTI `N7CFSPSys12CMyDSPSysMfxE` |
| Per-slot managers | `200a0d14 + 20*i`, i=0..3, installed by `6102c924` |
| Manager interface field | `6102c9b2` forms system+28; `6102c9ba` stores it at manager+10 |
| Manager getter | Vtable `6117647c` slot4 → `01135189`; body `01135188` returns manager+10 |
| Interface query | MFX vtable slot4 → `61081de3`; body `61081de2` reads controller+14+4*i and returns whether nonzero |

Addresses and offsets in that table are hexadecimal except the manager stride
20, which is decimal. Four refers to slots in this checked CORE1 graph; it is
not a claim that the whole instrument has only four effects or four BMC chips.
The installer derives each descriptor from `610a1674 + 72*i` (decimal stride).
It passes the slot index and manager into the slot-controller constructor through
`6107770c`. Startup/binding code is inspected statically, not executed.

FDRV itself is separately RTTI-linked as `11CFspMfxFDRV`, vtable `61176adc`, whose
slot10 points to `61049e87`. Its constructor at `61049e40` stores the integer
slot index at effect+8 and manager at effect+4. This is distinct from the nearby
FETDRIVE class and its constructor. The caller `61049e86` gets the interface,
passes the stored slot index to its slot4 query, then XORs the returned Boolean
with1 at `61049ed0`. It forwards that result into the original live piece setter
`0112b7ac`. An extra index argument must not be mistaken for a task pointer.

## Counter ownership and transition behavior

The four counter words are `2009bc34`, `2009bc38`, `2009bc3c`, `2009bc40`.
The system constructor zeros them. The query is simply `counter != 0`; it does
not inspect IPSR, thread identity, the software-task table or completion flags.

`6102bfae` and `6102c064` implement the matching nested mute-on/off operations:

| Operation | Counter before | Counter after | Original helper order |
|---|---:|---:|---|
| Mute on | 0 | 1 | Gate update, then skip/clear update |
| Mute on | Positive | +1 | No boundary helper calls |
| Mute off | Greater than1 | -1 | No boundary helper calls |
| Mute off | 0 or 1 | 0 | Skip/clear update, then gate update |

The source helper entries are `61029296` and `61029332`. The first mute-on
forwards third-register arguments 1 then the incoming Boolean. The final mute-off
uses 1 then0. Recording tuples in the tool retain those arguments; they are not
claims about a physical gain or switch level. Hardware-facing helper bodies are
excluded from execution. Mute-off at zero repeats boundary helper calls rather
than wrapping the counter negative. Ordinary nested on/on/off/off therefore
keeps immediate updates selected until the last release.

The independent counter API admits nonnegative signed32 values below overflow
and slot indices0..3, rejecting negative indices and Booleans as integers. The
source routines only show their own upper index guards; they do not establish
safe negative-index behavior. Counter overflow, misuse and concurrent operations
are outside the checked model. These plain loads/stores do not prove atomic
nesting or cross-task exclusion. A mute count is not a lock or a DSP halt fence.

## Original FDRV caller execution

The new oracle reuses the [bounded Thumb fixture](fantom-eqvg-control-study.md),
including pinned Unicorn2.1.4, RX firmware, nonexecutable private RAM, access/write
guards, assertion traps and the 250,000-instruction limit. Its fixed extra entries
are the query, two counter methods and original FDRV setter. No reset, OS task,
application initialization, interrupt controller or physical MMIO executes.

The fixture supplies source-derived managers, interface and piece descriptors.
The original getter, query, FDRV wrapper, piece setter, stability predicate and
software math run. Current coefficient reads and final writes are recording
callbacks. The pure EqVg/control reference supplies the expected five writes.
With count 0 the unstable test change selects b first and requests a wait on the
first envelope write. Nonzero counts select immediate g-first writes. This tests
actual caller selection instead of injecting its envelope Boolean directly.
It does not execute the resulting ramp or demonstrate that a real mute completed.

Counts 0/1/2/127/65535 across all four slots give 20 query cases, 80 counter cases
(two operations and two incoming Boolean values) and 40 original FDRV caller cases
(both live filter pieces). All match the independent model. The source getter
and concrete interface binding are checked in addition to these controlled RAM
instances; no live object-memory snapshot is claimed.

## Three separate completion mechanisms

The [sample-wait study](core1-wait-and-initial-data-study.md),
[clear IRQ study](clear-completion-interrupt-study.md) and
[envelope IRQ study](coefficient-envelope-and-completion-study.md) distinguish:

| Mechanism | Flag | Completion source |
|---|---|---|
| Sample/timer wait `011271b8` | Byte `200845b4` | Callback `011271ac`, timer IRQ91, counter base `40059000` |
| Global clear | Bit0 of word `200847f8` | Callback `0112f444`, event17 hex, IRQ80 decimal |
| Coefficient envelope | Bit1 of word `200847f8` | Callback `0112f438`, six DSP envelope sources |

Bit0 is **clear completion, not sample-wait completion**. The timer helper sets
priority argument18 decimal (`12` hex), registers its callback and drains a prior
pending timer flag before handling the next count, including count 0. It chunks
requests at 65534 and programs counter+chunk+1. These source counts are already
modeled by `core1_wait_study.py`; no new clock calibration follows. The
[registered RXDT/ASGN contexts](core1-task-context-and-host-peer.md) still do not
prove arbitrary wait calls can be made safely from any exception or interrupt mask.

## Reproduce and review boundary

```sh
python3.13 tools/fantom_envelope_mode_study.py local/b0c1a.bin
python3.13 tools/fantom_envelope_mode_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_envelope_mode.py -v
```

This session keeps Unicorn under ignored `local/fantom-python`; its CPU commands
use `PYTHONPATH=local/fantom-python:tools` and the previously approved private-RAM
JIT scope. Tests skip CPU execution without the pinned dependency or local corpus.
Validation results are recorded in the work log. The previous negative-amount
interpolation exclusion remains unchanged.

Qwen timed out at 120.2 seconds with only an in-progress report. Its final partial
text associated a different constructor/vtable with this query; parent RTTI and
source checks reject that claim. No worker interpretation is used as evidence.
Raw listings, worker logs and numerical reports remain ignored under local/.

Next trace the actual setter dispatch/registered task callbacks and their masking
or exclusion, then connect the source event chains to observed hardware timing.
No BMC opcode is added; physical precision, history setup, entry/return and safe
custom-engine loading remain separate requirements.
