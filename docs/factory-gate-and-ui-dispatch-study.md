# Factory introductory page: dispatch, test groups and the unresolved setting gate

2026-11-10. This follows the [access-route audit](fantom-access-route-audit.md)
using the same stock v1.08 `qctest`: 304912 bytes, SHA-256
`d87316806a54548920773b026f0b4d332b702450e1c1e7c317f5dc46ebfa29a6`.
All addresses are ELF virtual addresses. Evidence is offline ELF/Capstone/source
inspection; REA was unavailable. No binary, updater or instrument was executed,
and no input was sent to a device.

The known transitions leave the introductory version page for test groups 0, 1
or 2. The code for mode 3 takes a different local branch: it leaves
the introductory page selected and performs no group-selection setup. The ordinary
page tables and virtual dispatch do not supply a hidden fourth test group or a
virtual mode setter. This explains the structure of the dormant-looking setting
gate more precisely, but still does not establish an input that enables it or the
source author's intent.

## Introductory page and group selector are separate state

| Address | State / construction |
|---|---|
| `456edc` | Mode value, file initial -1; controls the introductory page's mode-3 gates |
| `5e3f58` | Optional introductory-page object pointer |
| `5e3f60` | `CPageDmyVer` object; its field +8 is a local input-sequence counter |
| `5e3f54` | Indexed test-group selector |
| `5e3f48` | Selected row within a test group |
| `456ea8` | Three pointer/count records describing the groups |

The adjacent `.init_array` entries at `455b58` and `455b60` call `407294` and
`407318`. The former calls the table initializer `406f30`; the latter constructs
the introductory object through `4072d4` → `408270`. The first initializer has
34 straight-line pointer-copy records at `406f58..407284`:

* The first copies the pointer at `456ee0` (`5e3f60`) into `5e3f58`.
* The remaining 33 populate object-pointer slots in the three test-group lists.
* Every copy is a six-instruction ADRP/ADD/LDR/ADRP/ADD/STR sequence, with an
  eight-byte load and store. None of those destination ranges overlaps `456edc`.

The checker summarizes these literal copies against file-backed source values;
it does not execute initialization or prove arbitrary earlier writes to source
globals impossible. The resulting lists contain 28 distinct object addresses,
all between `5e4100` and `5e7b30`. **None is the introductory object `5e3f60`.**

| Group | Base / count | Contents relevant to selection |
|---|---|---|
| 0 | `456c98` / 6 | EVENT, MIDI, EMI, USB HOST, AD, LCD |
| 1 | `456cf8` / 21 | Manufacturing tests from MODEL through MENU; its VERSION row uses object `5e6300`, not `CPageDmyVer` |
| 2 | `456e48` / 6 | ALD, SW/LED, AD, LCD, KEYBOARD, TOUCH |

The third group is an existing group indexed by 2. Mode 3 is not a group index
in the recovered setter's case-3 branch.

## Actual virtual dispatch, not just a vtable candidate

The constructor `408270` installs vtable address point `42f790` in object
`5e3f60`. Manager code first checks `5e3f58`: while nonnull, it invokes that
object; after it is cleared, it resolves the selected object through
`group[5e3f54].rows[5e3f48]`.

| Vtable offset | Introductory method | Manager sites / behavior |
|---:|---|---|
| `+00` | `407bec` | Group initialization loop `406980..406a30`; introductory implementation is a no-op |
| `+08` | `407c00` | Introductory branch `406a50..406aa4`; resets local sequence field +8 at `407d1c` |
| `+10` | `407d2c` | Group row change calls old row through `406794`; introductory implementation is a no-op |
| `+18` | `407d40` | Introductory branch `406b5c..406ba0`; draws version/setting display |
| `+20` | `407e9c` | Introductory branch `406c48..406c8c`; no-op |
| `+28` | `407eb0` | Introductory input dispatch `406d34..406d80` |
| `+30` | `4081b8` | Introductory message callback `406e2c..406e80` |

`40751c`, the mode setter, is absent from these seven slots. The constructed
introductory page's checked dispatch paths therefore invoke its input or message
methods, which in turn contain the already known direct setter calls. This closes
the relevant virtual edge rather than assuming a raw function address is callable
through an unspecified table. It does not exhaust every indirect call in the ELF.

The UI worker `406150` calls `405e0c`; that routine calls introductory setup
through `406a50` at `405ee4`. Its event loop reaches `406d34` at `405f3c` and
`405f88`, and the message callback dispatcher `406e2c` at `405fc4`. The input
dispatcher preserves the event pointer in x1; the message dispatcher supplies
its two saved callback arguments in x1/x2. Thus the handlers are connected to the
startup UI loop, not merely constructed unused objects.

## Known transitions from the initial mode

The mode setter at `40751c` stores its incoming integer to `456edc`, then uses
explicit comparisons for 0, 1, 2 and 3. Cases 0, 1 and 2 call `406610`, passing
that same integer. At `40661c..406634`, that helper clears `5e3f58` and writes
the group selector `5e3f54`. Its queued flag causes group initialization and row
setup through `405ffc..406020`. In contrast, case 3 branches to `407614`, a NOP
followed by a branch to the setter's return path. It does not clear the intro
pointer or select group 3.

| Known setter input | Local transition / side effect |
|---:|---|
| 0 | Clears intro, selects group 0; also forks and execs `/home/root/bin/tsd` with argument `1`, directing child stdout/stderr to `/dev/null` (`407588..4075f0`). This executable is absent only from the inspected app archive; its installed behavior is unknown. |
| 1 | Clears intro and selects group 1 (`407608..407610`) |
| 2 | Clears intro and selects group 2; calls `414248` (`4075f8..407600`) |
| 3 | Preserves intro, with no group setup (`407574..407578`, `407614..407618`); no identified caller supplies 3 |

The input handler uses the **object's +8 field** to recognize a sequence, not to
write the global mode. EXIT resets that field to 0 (`40810c..408110`); ZONE4,
STEP06 and STEP09 conditionally increment it at `40801c..40809c`. Other keys can
set it to 5 at `40812c..408134`. A separate SHIFT flag is written at `5e4010`
on its press/release paths. When sequence state is 4 and that flag is nonzero,
SPLIT selects mode 0 at `4080d0`, or WRITE selects mode 1 at `408104`. These
conditions do not select mode 3. This is static transition analysis, not a tested
panel sequence or recommended procedure; mode 0 has the additional unknown daemon
side effect described above.

The message method's known transition is mode 2 at `408230..408238`. It requires
the byte returned by `407384` to equal 1, then requires matcher `414158` to accept
the pointed data at offset +8. That matcher compares against fixed tables at
`431030` and `431060`. A preceding comparison to `0x70` at `4081d8` has no
conditional branch before another compare overwrites its condition flags; it must
not be described as a proven `0x70` message-type filter. This callback supplies 2,
not 3. No live message recipe or packet injection was attempted.

The ordinary row-selection function `40664c` clamps a negative index to zero and
an index at/above the selected group's count to count−1 (`406670..406700`). The
navigation wrappers at `413d00`/`413d68` perform further row bounds checks.
These are row transitions; they do not convert an extra row into a fourth mode.

## Indexed-address and command-line boundaries

All 23 recognized `456ea8 + group*16` address constructions were followed through
their first memory use. Eighteen load the row-table pointer at offset 0 and five
load the count at offset 8; none performs a store through that computed group-table
address. Subsequent code indexes the loaded row table to obtain an object pointer
or display name. The initializer and the constructed intro object establish the
specific ownership described above; they do not turn arbitrary group/row values
or arbitrary object-method writes into safe/known operations. The checker validates
these 23 exact six-instruction constructions, not a general alias analysis.

Main's only explicit argument check (`402d0c..402d60`) requires argc 2 and checks
the first two characters of argv[1] for `-c`; it writes a separate flag `45a2c4`.
It does not parse a mode number or require a terminating NUL after those two
characters. Intro setup/display read that flag at `407c10` and `407d58` to choose
configuration/display behavior. Main passes a saved argc/argv pair to worker
`406150`, but that worker only saves the pointer at `406158` and does not read it
before returning. The inspected startup path supplies no argument-to-mode-3 edge.

The dynamic symbol table has no `getenv`, `secure_getenv`, `getopt` or
`getopt_long` import. That is a scoped import observation, not proof that libraries
or other file/configuration paths cannot depend on the environment. No environment
setting that enables mode 3 was recovered.

## Reproduction and remaining proof

```sh
python tools/factory_gate_study.py local/qctest
BMC_CORPUS_DIR="$PWD/local" python -m unittest discover -s tests -p test_factory_gate_study.py -v
```

Use installed Python 3.13.7, Capstone 5.0.7 and pyelftools 0.33. The two tests
verify actual initializer/dispatch results and reject a pointer-copy window changed
to a four-byte store. No dependency or hardware interface was added.

The result remains `mode3_activation_proven=false` and
`all_aliases_resolved=false`. A real mode-3 writer/indirect call, matching source
showing an omitted entry, or a controlled observation of the actual state is still
needed. Arbitrary spilled/computed aliases, bulk-copy destinations, every other
object method and another installed build were not exhaustively resolved. No
claim of universal absence, runtime root access or usable terminal follows from
the structural explanation in this pass.
