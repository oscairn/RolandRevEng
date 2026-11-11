# Fantom parameter dispatch and wait-context limits

2026-11-11. The original unchanged-algorithm update path now reaches FDRV's
parameter callback, live-filter setter, mute-counter query and coefficient
producer in a bounded CPU fixture. Logical fields 2/3 select live filter 1's
mode/cutoff. This extends [mode selection](fantom-envelope-mode-study.md);
it does not connect an incoming hardware message or registered IRQ task all the
way to this callback. No BMC opcode profile is added.

## Source chain and independent checks

`tools/fantom_parameter_dispatch_study.py` pins the same stripped CORE1 SHA-256
`6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`
before constructing an emulator. RTTI, vtables, branch anchors and constants are
checked with the existing Capstone helpers. REA remains unavailable; these are
file/Capstone and isolated CPU observations, not REA Evidence records.

| Step | Source |
|---|---|
| Outer module callback | Vtable `6117b3d8`, slot14 → `011290ef` |
| Unchanged algorithm and transition byte 0 | `011290ee` takes branch `011291ba` |
| Parameter-interface update | `011291c6` invokes wrapper+4's interface slot4 with the two incoming arguments |
| Algorithm parameter apply | `011291cc..1d4` invokes wrapper slot4 |
| Concrete wrapper | RTTI `11CMfxFDRVPrm`, vtable `61176e20`, slot4 → `61032e91` |
| CFsp receiver | Loaded from wrapper+74 |
| Live filter 1 update | `61032f44` calls CFsp slot10, resolving to `61049e86` |
| Source mode selection | Actual manager getter and MFX mute-count query, as checked in the preceding study |
| Coefficient calculation | Original live piece `0112b7ac`, EqVg software math and stability predicate |

Offsets and code addresses above are hexadecimal. The equality-only fixture uses
matching opaque algorithm markers; it does not claim those markers identify FDRV
in the factory table. Algorithm replacement, RAMCLR and cleanup are excluded.
The original [replacement ordering](effect-lifecycle-and-parent-entry-study.md)
remains a separate source result.

## Logical fields and what their producer still needs

If either logical field 2 or3 changed, the parameter callback reads both and makes
one live-filter call with filter index1. Field2 zero selects type0, otherwise
it selects type13. Field3 becomes a signed-integer-to-binary32 cutoff. Gain is 0
and Q is the source float `0x3f34fdf4`, or 0.7070000171661377. A field 2 change also
calls the companion slope setter with field 2 minus1; a field 3-only change does
not request that companion update. Slope calls are recorded but not applied.
The fixture admits mode 0..2 and cutoff 0..23000 to stay inside the checked source
paths; these are research API bounds, not recovered global UI ranges.

The parameter interface's value/changed methods are recording callbacks, using
an independent logical snapshot. Its initializer records forwarding of the two
incoming arguments; those buffers are not decoded. Consequently this proves
logical parameter routing and numeric conversions, not raw flag-word layout,
message-buffer lifetime, panel control identity or MIDI/SysEx encoding. Other
parameter groups remain disabled in this fixture. The earlier desktop
`vg_events()` model supplies the expected logical event independently.

The original outer callback, concrete parameter body, FDRV wrapper, mute query,
piece setter, stability test and software math execute. Current coefficient
reads and final writes remain controlled callbacks. Mode/cutoff changes at both
edge slots 0/3, mute counts 0/2, three mode values, two cutoffs and four changed sets
produce 96 cases and 360 coefficient writes. All match the independent plan.
A changed field 2 of zero records slope argument -1, preserving the source's signed
subtraction rather than clamping it by assumption. No changed fields produce no
coefficient or slope writes, while the outer interface-update call still occurs.

Execution reuses pinned Unicorn2.1.4, RX code, nonexecutable private RAM, fixed
entry admission, access/write guards, assertion traps and the 250,000-instruction
limit. No reset, OS task, scheduler, real MMIO or interrupt controller executes.
The existing negative-amount interpolation exclusion is unchanged.

## Mask helpers do not preserve an incoming global mask

The complete bounded bodies at `01102494..011024c2` and `011024c2..011024f0`
contain no PRIMASK read/save/restore sequence. Their NVIC enable/disable stores
are bracketed by these unconditional instructions:

| Helper | CPSID i | CPSIE i |
|---|---|---|
| Enable mapped task IRQ | `011024a0` | `011024be` |
| Disable mapped task IRQ | `011024ce` | `011024ec` |

Arm documents `CPSID i` as setting PRIMASK and `CPSIE i` as clearing it. Thus this
sequence does not restore an arbitrary incoming mask; enabling/disabling one
NVIC line is distinct from preserving a caller's global interrupt state.
See the primary [Arm CMSIS core-register documentation](https://arm-software.github.io/CMSIS_6/main/Core/group__Core__Register__gr.html).
This is instruction semantics plus a source check, not a measured live mask trace.

The [software-IRQ callback bindings](core1-task-context-and-host-peer.md) identify
RXDT and ASGN execution contexts. Their wrappers do not establish an exclusion
lock around this parameter apply callback. An ASGN-to-FDRV setter connection is
still missing here; proximity to a registered task or an effect-related string
cannot supply that edge. The observed task6 registration near the parameter
helpers is named DEMO and must not be relabeled an effect worker.

The timer wait's byte at `200845b5` is a callback-registration indicator, not an
acquire/release lock: the checked helper sets it during registration and does not
clear it on wait completion. Byte `200845b4` is its completion flag. Clear and
envelope completion use bits0/1 of a different word, `200847f8`. A polling wait
whose required callback cannot run has no proved progress path; a blanket claim
that every masked call sleeps forever is unwarranted, including already-complete
or zero-count cases. Runtime priority grouping, BASEPRI, PRIMASK, nesting and the
actual caller's ownership remain necessary evidence.

## Reproduce and review

```sh
python3.13 tools/fantom_parameter_dispatch_study.py local/b0c1a.bin
python3.13 tools/fantom_parameter_dispatch_study.py local/b0c1a.bin --execute-thumb
python3.13 -m unittest discover -s tests -p test_fantom_parameter_dispatch.py -v
```

This session uses ignored `local/fantom-python` for Unicorn and
`PYTHONPATH=local/fantom-python:tools` for CPU commands, within the previously
approved private-RAM JIT scope. The work log records focused/regression results.
Qwen saved a mask review, while its wrapper returned 1 at 60.1 seconds. Parent
checks accept the source CPSID/CPSIE observations; the registration-byte-as-lock
claim, one polling-PC attribution and unconditional WFI/deadlock claims are
rejected or narrowed. Raw listings and worker logs remain ignored locally.

Next recover the actual parameter interface/buffer producer and its route from a
concrete registered callback, preserving masks and object lifetimes. This remains
separate from broader DSP instruction coverage, silicon precision/timing,
history initialization, entry/return and safe custom-engine loading.
