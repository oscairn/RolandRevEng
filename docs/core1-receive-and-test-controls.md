# CORE1 receive path, lifecycle and named oscillator controls

Follow-up: [stock task context and host peer](core1-task-context-and-host-peer.md)
connects RXDT/ASGN registration to actual software-triggered NVIC callbacks,
priority bytes and queue gates. These callbacks are not established OS threads;
the external ttyGS0-to-CORE1 conversion remains unresolved.

2026-11-10. Static evidence from bmc0 MI078 C1A v1.08 commit `947de6711`, payload
SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`.
All addresses are CORE1 runtime addresses. No plugin, firmware function or instrument
was executed. These observations extend the [loader map](BMC%20DSP%20packet%20and%20loader%20map.md)
and [command-entry trace](core1-command-entry-study.md).

## What is now concrete

The stock firmware has named sine, impulse, white-noise and DC coefficient controls,
and an actual program transition path using the already identified manager upload
functions. The transition uses small temporary programs and subsequently reloads the
ordinary render programs. The small temporary programs must **not** be mistaken for
the oscillator implementation. Neither finding establishes a callable host upload API
or a hardware-safe custom program slot.

## November 10: incoming ring and routing path

The same bmc0 payload SHA-256 recorded in the loader report contains the following
statically linked receive path. Each edge below is an actual instruction/data reference,
not a relationship inferred from nearby strings:

| Stage | Address and behavior |
|---|---|
| IRQ6 vector | Vector word at `0x01100058` is Thumb pointer `0x01102945` |
| IRQ handler | `0x01102944` calls the hardware/shared-ring reader `0x01125f68`, then passes each returned 32-bit word to `0x0111ed12` |
| Ingress ring reader | `0x01125f68` compares indices at `0xe004300c/0xe0043010`, reads `0xe0043038 + 4*read_index`, advances the read index modulo 64 |
| First software enqueue | `0x0111ed12` calls `0x0111f254`, then schedules task 3 through `0x011020c0` |
| First software ring | Enqueue `0x0111f254` and dequeue `0x0111f2a4` use data at `0x2009570c`, index/counter state at `0x20082024`, and 9-bit indices (512 slots, one empty slot distinguishes full/empty) |
| First router | `0x0111ea24` drains that ring and dispatches on word bits 7:4; its kind-zero path ordinarily calls `0x0110a5a6` |
| Second software enqueue | `0x0110a5a6` passes the pointed-to word to `0x0110a390`, then schedules task 5 |
| Second software ring | Enqueue `0x0110a390` and dequeue `0x0110a438` use data at `0x200876d4`, state at `0x2008044c`, and 11-bit indices (2048 slots, one reserved for full/empty) |
| Second router | `0x0110a65c` drains that ring, dispatches on bits 7:4, and for kind zero ordinarily calls `0x0110bacc` at call site `0x0110a6da` |

The first router's kind-zero path treats byte 1 values `0x07`, `0xc0`, `0xc1` and
`0xfe` separately; the second also handles byte 1 `0x07` separately. The callback's
`0x51/52/54/58/70/74/75/7b` values therefore have a concrete route from this ring, but
that does not make them UART bytes, MIDI SysEx command numbers or a Linux device API.
The low nibble is not checked as a mandatory `1` on this observed kind-zero path.

The first router has other routes, including the `CUMDWRx` SysEx assembly routine at
`0x0111f10c`, which uses low-nibble values 4/5/6/7 and dispatches a completed buffer
through a virtual method. A separate SysEx receiver would need its own provenance and
handler analysis. Decoding this callback does not cover all incoming commands.

The ingress ring's metadata at `0xe0043000` and backing bytes from `0xe0043038` are
also initialized by the recovered CORE1 scatter table. That supplies independent
evidence for these mapped addresses. The producer of the ring is outside this trace;
calling it a direct i.MX8M mailbox or a CORE0 interface would still be an inference.

### Reproduce the new references

`tools/core1_xrefs.py` searches immediate Thumb BL/B candidates and exact contiguous
`MOVW; MOVT; BX` veneers. For example, the driver `SetExeMode` has no observed immediate
call from these image ranges, but the tool finds its far-call veneer at `0x61076aaa`.
Searching that veneer exposes the real ERAM callers. Omitting veneers misses this path.

```sh
python3 tools/core1_xrefs.py local/b0c1a.bin 0x0110bacc
python3 tools/core1_xrefs.py local/b0c1a.bin 0x0111ed12
python3 tools/core1_xrefs.py local/b0c1a.bin 0x01130b6c
python3 tools/core1_xrefs.py local/b0c1a.bin 0x61076aaa
python3 tools/core1.py local/b0c1a.bin --address 0x01102944 --size 0x2c
python3 tools/core1.py local/b0c1a.bin --address 0x01125f68 --size 0x2a
python3 tools/core1.py local/b0c1a.bin --address 0x0111ea64 --size 0x30
python3 tools/core1.py local/b0c1a.bin --address 0x0110a6a4 --size 0x54
python3 -m unittest discover -s tests -p test_core1_xrefs.py -v
```

The reference tool checks every halfword in the two mapped image regions. Data may
look like an instruction, so its results are explicitly **candidates**, not a proved
call graph. The callers described above were inspected in their surrounding functions.
The tool does not find arbitrary indirect calls, conditional branches, other veneer
forms or runtime-generated code, and it never executes firmware.


## Execution-mode calls and cross-core synchronization

The exact veneer at `0x61076aaa` loads Thumb pointer `0x01130b6d` into `ip` and branches
through it. A routine beginning `0x610016b0` calls that veneer at these sites:

| Call site | DSP | Mode | Argument | Event |
|---|---:|---:|---:|---:|
| `610016d8` | 0 | 2 | 0 | 3 |
| `610016e4` | 1 | 0 | 0 | 3 |
| `610016f0` | 2 | 2 | 0 | 3 |
| `610016fc` | 3 | 0 | 0 | 3 |
| `6100170c` (tail branch) | 6/MDSP | 2 | 0 | 3 |

Each tuple follows actual register definitions at the call site and the previously
recovered `SetExeMode` ABI. The differing modes track the voice-side versus other
engines in this build, but **mode 0 = stop and mode 2 = run are not established**.
Treating these values as a safe stop/start recipe would be premature. This bounded
caller search also does not exclude compiler-inlined writes elsewhere.

A function at `0x01101a1a` logs `DSPSync() Step 0/1/2/3`. It writes state 0 through
`0x01126208` (byte `0x617f8001`), waits until `0x01126202` reads 1, clears register
`0x4110003c`, writes state 2, then waits for state 3. Those are real polling and write
operations, not just debug labels. The other participant that advances 0→1 and 2→3 is
outside this trace; CORE0 participation is a plausible inference, not yet proved here.
Its call ordering relative to a new custom-program upload remains unresolved.

## Actual manager call conventions and exclusion flag

The `CBmcDspMgr` vtable address point is `0x6117647c`. Its recovered slots include:

| Vtable byte offset | Thumb target | Meaning established by body/assertion |
|---:|---|---|
| `18` | `01135099` → `01131c4e` with `r2=1` | Write every render-program segment and wait for DMA completion |
| `1c` | `011350a9` → `01131cf4` with `r2=1` | Write DRAM-IO program list and wait |
| `20` | `011350b5` → `01131c4e` with `r2=0` | Write render-program list without the final wait |
| `64` | `011327e7` | `WriteDspCoefFloat(const _CoefSym *, float)` |
| `70` | `01132abf` | `ReadDspCoefFloat(const _CoefSym *)` |

The first three methods still take a **manager object** in `r0` and a list in `r1`.
They are not the static driver ABI whose `r0` is a DSP index.

`WriteDspProgAllImpl` reads byte `0x2008480c`, asserts if it is already nonzero, sets it
to 1, queues each segment, optionally invokes `0x0112f6a4(1)`, then clears the byte.
The coefficient writer uses the same byte around literal writes. The assertion calls
this `DSPMgrWaiSemDspProg`, but the observed operations are a check/set/clear flag;
no blocking acquire or atomic instruction is visible in these function bodies.
This is evidence of shared exclusion requirements, not permission to acquire it from
arbitrary tasks or interrupts. A resident bridge must join the stock task/manager
protocol rather than merely testing that byte and racing it.

## Stock transition and temporary programs

At `0x6102a230`, the firmware follows this observed ordering:

1. Writes four DRAM-IO lists through manager vtable offset `0x1c`.
2. Writes zero through four coefficient handles (`610a352c/353c/354c/355c`) using
   offset `0x64`. Their records target absolute byte 4, width 2, in each DSP's
   prefix program at byte 0.
3. Performs data-memory clearing/writes, then calls a wait helper through veneer
   `0x6107769e` with count 1 and completion flag 1.
4. Loads the four temporary render lists below through vtable offset `0x18`.
5. Writes `2^-14` to those prefix controls, waits with count 2, writes zero to the four
   prefix controls again, then waits with count 1.
6. Calls `0x610293b2`, which reloads ordinary render lists, and finally calls the
   routine at `0x011017fc`, whose logging identifies `EnableDAC` behavior.

The helper behind `0x6107769e` is `0x011271b8`; its wait/event machinery is visible,
but the count's time unit has not been recovered. Do not silently label these waits
milliseconds. The whole transition is more than an upload call, and has not been
executed or established as a general application extension point.

Each temporary list is type 0 and contains exactly one segment:

| DSP | List | Segment metadata | Stored source |
|---:|---|---|---|
| 1 | `610a1f58` | base `20`, length `c6`, capacity `c6` | `610b3c84` |
| 3 | `610a1f60` | base `20`, length `c6`, capacity `c6` | `610b3d5c` |
| 4 | `610a1f68` | base `20`, length `c6`, capacity `c6` | `610b3e34` |
| 5 | `610a1f70` | base `20`, length `c6`, capacity `c6` | `610b3f0c` |

The four logical program images are identical. Their purpose is not assigned an ISA
meaning here; their placement between clears/waits and regular graph restoration
supports a temporary transition role. The actual small-program behavior needs decoding.

The subsequently restored regular lists are `610a1ef8` (DSP1), `610a1f08` (DSP3),
`610a1f18` (DSP4) and `610a1f28` (DSP5). The normal DSP4 primary segment is base `0x20`,
length `0x35b6`, capacity `0x4000`, stored source `0x610a5614`.

## DSPDevelop edits real oscillator coefficients

The exact RTTI `17CEZUtilDSPDevelop` links to vtable group `0x6117ab90`; its event
callback is `0x6107fd9c`. The callback routes direct-value UI choices through
`0x6102372c` and value increments through `0x6102363c`, both ultimately reaching the
setter dispatch at `0x6102301c`. The menu descriptor table at `0x610a04b4` has 12
records, each 28 bytes. Named fields include `TargetMagnitude`, `TestOsc_SineLev`,
`TestOsc_ImpulseLev`, `TestOsc_WhiteLev`, `TestOsc_DCLev`, `TestOsc_LeftSw`,
`TestOsc_RightSw`, `TestOsc_SineFreq`, `TestOsc_ImpulseRate`, and three `StepInfo` fields.
The two channel-switch setters are bare returns in this build.

The following field-to-setter-to-symbol relationships follow real branch and pointer
loads. The symbol records identify literals in the **normal DSP4 primary segment**;
all six ranges fall within packet payloads, not base control words:

| Named field | Setter | `_CoefSym` | Absolute byte | Relative byte | Width |
|---|---|---|---:|---:|---:|
| `TestOsc_SineFreq` | `6102a666` | `610a2114` | `32` | `12` | 4 |
| `TestOsc_SineLev` | `6102a6ba` | `610a2124` | `90` | `70` | 3 |
| `TestOsc_ImpulseRate` | `6102a69a` | `610a20b4` | `54` | `34` | 3 |
| `TestOsc_ImpulseLev` | `6102a6c4` | `610a20a4` | `ac` | `8c` | 3 |
| `TestOsc_WhiteLev` | `6102a6ce` | `610a2154` | `93` | `73` | 3 |
| `TestOsc_DCLev` | `6102a6d8` | `610a2094` | `af` | `8f` | 4 |

Every listed `_CoefSym` has one 12-byte record; that record contains absolute byte
address at +0, segment-relative byte address at +4, literal width at +8 and segment
index at +9. The setters load their manager from object+`0x10` and dispatch through
vtable+`0x64`, independently identified as the literal writer above.

The sine-frequency setter loads `pi_f32` and `48000.0f`, then writes
`2 * F(pi_f32 * frequency / 48000.0f)`, where `F` is the scalar function at
`0x011385f0`, reached through veneer `0x610776da`. Its small-argument path computes
an odd polynomial with coefficients approximately `-1/6`, `1/120` and `-1/5040`,
and its other path performs quadrant reduction with sine/cosine polynomials.
**Inference:** this is a sine approximation and the coefficient is
`2*sin(pi*frequency/48000)`. The decoded initial four-byte DSP literal is
`0.057587904622778296`; the mathematical 440 Hz expression is
`0.05758790473652694`. This is a strong independent oscillator-coefficient anchor,
not a proof of the individual DSP operations or the hardware sample rate in every mode.

The impulse-rate setter directly writes `2 * rate / 48000.0f`. Level setters forward
their float unchanged. UI metadata initial values, `_CoefSym` defaults and stored
program literals must be kept distinct: they need not all reflect the same post-init
state, and the short literal formats have much coarser precision than host floats.

## Reproduction and remaining gap

```sh
python3 tools/core1_rtti.py local/b0c1a.bin 17CEZUtilDSPDevelop
python3 tools/core1_xrefs.py local/b0c1a.bin 0x01130b6c
python3 tools/core1_xrefs.py local/b0c1a.bin 0x61076aaa
python3 tools/core1.py local/b0c1a.bin --address 0x610016b0 --size 0x60
python3 tools/core1.py local/b0c1a.bin --address 0x01101a1a --size 0x56
python3 tools/core1.py local/b0c1a.bin --address 0x6102a230 --size 0x96
python3 tools/core1.py local/b0c1a.bin --address 0x6102a340 --size 0x14a
python3 tools/core1.py local/b0c1a.bin --address 0x6102a666 --size 0x7e
python3 tools/core1.py local/b0c1a.bin --address 0x011386c0 --size 0x32
```

The list and coefficient records can be reproduced without emitting program bytes:

```sh
PYTHONPATH=tools python3 - <<'PY'
import math, struct
from core1 import Core1
from bmc_dsp import literal, swap_words
c = Core1('local/b0c1a.bin')
for a in (0x610a1f18, 0x610a1f58, 0x610a1f60, 0x610a1f68, 0x610a1f70):
    kind, dsp, count, pad, table = struct.unpack_from('<4BI', c.data, c.offset(a))
    print('list', hex(a), 'kind/DSP/count/pad', kind, dsp, count, pad)
    for i in range(count):
        record = struct.unpack_from('<4I', c.data, c.offset(table + 16*i))
        print(' segment base/length/capacity/source', *(hex(v) for v in record))
source = c.offset(0x610a5614)
program = swap_words(c.data[source:source + 0x35b8])[:0x35b6]
for name, a in [('SineFreq', 0x610a2114), ('SineLev', 0x610a2124),
                ('ImpulseRate', 0x610a20b4), ('ImpulseLev', 0x610a20a4),
                ('WhiteLev', 0x610a2154), ('DCLev', 0x610a2094)]:
    table = c.u32(a + 8)
    count = c.data[c.offset(a + 12)]
    assert count == 1
    absolute, relative, width, segment = struct.unpack_from('<IIBB', c.data, c.offset(table))
    assert absolute == 0x20 + relative and segment == 0 and width in (2, 3, 4)
    print(name, hex(absolute), hex(relative), width,
          literal(program[relative:relative + width]))
print('mathematical 440-Hz anchor', 2*math.sin(math.pi*440/48000))
PY
```

The GUI's entry/activation path and the first ingress-ring producer are still unknown.
No arbitrary DSP upload command has been found along this bounded route. There is
also no proved reserved slot, general stop/start sequence, complete device audio ABI,
or hardware timing/numerics model. The new named controls give useful stock programs
and parameters for eventual hardware experiments; they do not remove those blockers.
