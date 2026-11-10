# Narrow gain-control semantics

2026-11-09. Offline follow-up to [the packet and loader map](BMC%20DSP%20packet%20and%20loader%20map.md).
The source is the local ZENOLOGY arm64 image identified in that report. No plugin or
firmware was executed. No hardware was accessed.

Follow-up, 2026-11-10: [the MAC controls and issue study](mac-controls-and-issue-study.md)
establishes that main-port stores in the selected mixed packets capture incoming
values, before same-packet arithmetic. The gain model now uses that ordering; all
12 native tail matches still pass. Base-word order must not be used as issue order.

## Result

A bounded model of gain controls and indexed transfers matches the terminal gain
chains in **12 effect classes**, on both output channels: **24 channel chains and
48 gain applications**. Each chain has two distinct live-coefficient operands in
program order. This is stronger evidence for the previously tentative multiply
interpretation; it is not a complete arithmetic decoder or hardware validation.

The verified subset is:

| Control | Functional interpretation in these examples | Observed selector |
|---|---|---|
| `0401` / `4501` | Multiply main result A / B by input port 1 | EH tail |
| `0403` / `4503` | Multiply main result A / B by input port 3 | All 12 tails |
| `4507` | Multiply main result B by input port 7 | RVSDLY and STTMDLY asymmetric tails |
| `3FE(2i)` | Load input port 3 from indexed payload operand i | Live coefficient reads feeding the shared gains |
| `7FE(2i)` | Load input port 7 from indexed payload operand i | Separately controlled right-channel gain |
| `1FE(2i)` | Load input port 1 from indexed payload operand i | EH loads a live coefficient through this port |
| `8FE(2i)` / `CFE(2i)` | Store main result A / B through indexed payload operand i | Final DM stores and output destinations |
| `0FE(2i)` / `4FE(2i)` | Load the two main paths through indexed operand i | FETDRIVE/LINEDRIVE output-state reloads |

`0407` is modeled as the corresponding A-path multiply, consistent with the earlier
TS808 opening-chain inspection. This **terminal-tail experiment does not independently
exercise it**. Likewise the low-three-bit source-selector interpretation is directly
tested only for selectors 1, 3 and 7; selectors 0, 2, 4, 5 and 6 remain open.

Port names above are functional labels. They do not establish physical register names,
accumulator precision or instruction latency. Port 1 holding a coefficient in EH also
shows why calling ports 3/7 the only "coefficient registers" would be premature.
The mappings are header-family dependent: the study interprets gain words only in
family 1 within the exact `1503`, `2e05`, `b809` and `5f07` packet contexts, and indexed
transfers only in family 4, using `header_study.families()`.
The same 16-bit base word in a different header family is not assigned that meaning.
Unknown header families discard the model's current arithmetic/input/memory state.
The two asymmetric examples additionally rely on the independently checked `4709`
family `(0,0,4,4)` to locate their preceding coefficient transfers. This is not a global
arithmetic interpretation of those base words or of all family-1 operations.

## Independent native checks

`tools/alu_study.py` reads Capstone's structured ARM64 operands, rather than comparing
strings emitted by the earlier `lift.py` heuristic. It tracks:

1. The native object's actual provenance from the wrapper argument and output-pointer
   provenance from the output argument. Output channel identity does not assume `d0`
   always means left or `d1` always means right.
2. The constructor's resource-base load, dynamic coefficient-base index, stride `0x48`,
   integer index offsets and pointer stores. Thus a field is recognized as
   `resource_base + 0x48 * (parameter_base + slot)`. Slot numbers are not inferred merely
   from the rank of the field offset.
3. Live float loads from those proven coefficient-record pointers at record offset
   `0x28`, followed by their conversion to double.
4. Floating multiply def/use and DM store/reload aliases, preserving the coefficient
   identity through the final output writes. Integer aliases and overlapping S/D and
   W/X register writes are invalidated when overwritten.

Constructor inspection stops at its first return. Apple's `LC_FUNCTION_STARTS` range
can contain subsequent static-initializer procedures; scanning past that return is
not valid evidence for a constructor's field assignments.

The DSP model implements only the six listed multiply controls, the narrow main/port
transfers and observed framing/output controls. An unsupported arithmetic control
discards current arithmetic, input-port and modeled-memory state. An unknown value
never becomes an invented coefficient. Unknown indexed stores invalidate their
destination aliases. Native calls discard modeled memory/output aliases as well as
caller-saved register provenance. Unsupported vector writes invalidate overlapping
scalar-register provenance. Targeted synthetic fixtures cover those cases.

The output compares the ordered *outer coefficient-factor chain*, not numerical
samples. Compiler scheduling may move loads, but the final native value still depends
on the same two coefficient records. Both factors must agree independently for each
output channel.

## Matched classes

Slot numbers below are relative to the native constructor's coefficient-base parameter.
They match the live coefficient indices in the selected program image; they are not
global coefficient-RAM addresses or named patch parameters.

| Effect class | Left factors, in order | Right factors, in order |
|---|---|---|
| EH | 3, 0 | 3, 0 |
| FETDRIVE | 4, 0 | 4, 0 |
| ISOLATE | 7, 6 | 7, 6 |
| LFCOMP | 3, 0 | 3, 0 |
| LINEDRIVE | 5, 0 | 5, 0 |
| PH90 | 5, 0 | 5, 0 |
| RVSDLY | 8, 0 | 9, 0 |
| STPS | 2, 3 | 2, 3 |
| STTMDLY | 0, 2 | 1, 2 |
| SUST | 0, 1 | 0, 1 |
| TS808 | 2, 3 | 2, 3 |
| VMCP | 2, 0 | 2, 0 |

The asymmetric RVSDLY/STTMDLY cases are particularly useful: replacing `4507` with
the `4503` hypothesis selects the wrong first right-channel coefficient. A model
that simply labels every final gain "master volume" would miss this distinction.

EH adds an independent selector check: the earlier gain uses `0401/4501` after a
port-1 transfer, then the final `0403/4503` pair uses port 3. The native result has
coefficient factors 3 then 0 on both channels.

## Reproduction

With the local corpus prepared as described in the project README:

```sh
python3 tools/alu_study.py
python3 -m unittest discover -s tests -p test_alu_study.py -v
```

The study writes its detailed summary, class function ranges and unresolved cases to
ignored `local/alu_study.json`. Unit tests include original, synthetic ARM64 fixtures
authored for this study; they are not copied firmware or plugin instructions.
They verify pointer provenance, a relative slot 7 stored in the first/only field,
rejection of a wrong stride, termination at return, unsupported-control invalidation,
asymmetric gain selection and transfer bounds. The corpus-dependent test skips when
local vendor artifacts are absent.

## Limits and next useful experiment

Selection is explicit: these classes end with a pure `0403/4503` pair. Other opcode
families and earlier filter/distortion stages were not treated as solved. The native
reader performs bounded static def/use, not path-sensitive execution of arbitrary
ARM64 branches or a complete interpretation of the translated effects.

Multiplication identity does not establish hardware rounding, saturation/wrap,
pipeline latency, side effects or the semantics of a newly scheduled program. The
native model's double precision must not be projected onto the silicon.

A useful next offline step is to extend the same expression comparison to the paired
dry/wet MAC stage immediately before the gains, where asymmetric coefficient inputs
can distinguish operand order. A useful eventual hardware check is a muted, owned
two-gain kernel with nonidentical left/right coefficient values and stock API readback.
Neither test has been performed on hardware here.
