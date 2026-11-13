# CORE1 boot-entry chain: how the load route is reached

Closes the gap [core1-load-route-callers-study](core1-load-route-callers-study.md)
left open: that study proved the boot verify routine `0x610010d0` is the stock
image's only end-to-end program-load/verify user but found **no direct caller**.
This study binds the full entry chain statically, and the answer is simpler
than the alternatives run 11 listed: **the chain has no table and no runtime
constructor — it is straight-line code from the reset vector**.

Static, read-only file analysis of the pinned bmc0 CORE1 payload
(SHA-256 `6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154`).
No firmware is executed; no device is contacted; no key or ciphertext material
is read.

## Result (summary)

- **Reset vector `0x1100004` holds `0x01100e55`** (Thumb entry `0x01100e54`).
  The reset entry zeroes r0–r12, clears APSR/CONTROL/BASEPRI/PRIMASK/FAULTMASK,
  copies MSP to PSP, then calls `__rt_entry` (`0x1100ee9`, enables FPU bits in
  `0xe000ed88` CPACR), calls `0x1102ceb`, and finally `bx`es into ERAM code at
  `0x61000001` (the C library runtime entry, which returns to `0x1100ec4`'s
  halt loop if it ever returns).
- **The reset wrapper `0x01100e2a..0x01100e48`** (reached from
  `0x011004de`, which sets SP to `0x1148000` and calls board init `0x1100490`)
  writes `0xf8ff`-masked priority configuration into `0xe000ed0c` (SCB AIRCR
  PRIGROUP), then `bl 0x1102986` — **the boot task** — then parks in a
  `wfi`/`b` halt loop at `0x01100e46`. The boot task has exactly one caller
  image-wide (`0x01100e42`; no veneer, no word reference).
- **The boot task `0x01102986`** divides the boot-state word `0x200800d8` by
  1000 (`mov.w r1,#0x3e8` at `0x0110298c`, `udiv` at `0x01102998`) as a
  milliseconds uptime source, configures and enables SysTick
  (`0xe000e00f` base; LOAD bound `cmp.w r1,#0x1000000`, STRV/VAL/CTRL writes
  at `0x011029a6..0x011029b2`, priority `0xf8` at `0x011029aa`, re-armed at
  `0x01102a32`), logs the `CORE1 Version / Build` banner through the log
  helper `0x1134380` with log block `0x20091280`, sets calibration constants
  from ERAM getter veneers (`0x11033a0` etc.), **arms NVIC interrupt 4**
  (`strb.w r0,[r1,#0x400]` with `r0=0x10`, `r1=0xe000e006` at `0x01102a2a`),
  calls IO init `0x1101a1a`, and then **calls the verify routine through the
  veneer cell `0x0113439e` (`movw ip,#0x10d1; movt ip,#0x6100; bx ip` →
  `0x610010d1`) at `0x01102a3a`** — that BL is the veneer cell's only caller
  image-wide, so the boot task is the verify routine's only caller, exactly as
  run 11's readback census required.
- After the verify call the task calls `0x61001443` (veneer `0x11343a8`, a
  push `{r4,lr}` function at `0x61001442` with no other callers), then gates
  further work on the tick counter: `wfi` until `0x200800d8` advances 20 ticks
  (`adds r0,#0x14` at `0x01102a4a`), i.e. **the boot task waits 20 ticks
  (one SysTick period each) immediately after arming execution modes**, and
  continues with subsystem init and a second 19-tick wait (`adds r0,#0x13`).
- **The state word `0x200800d8` is the SysTick counter.** The interrupt
  handler in vector entry `0x110003c` (Thumb `0x0110292d`, body `0x0110292c`)
  increments it (`ldr r0,[pc] → 0x200800d8; ldr/str r1,[r0] with +1`), runs
  the timer-task poll `0x110284c` and the clock-gate poll `0x110336a`, then
  `dsb sy` and returns. This also explains run 11's unexplained
  `0x200800d8` reads: it is uptime in ticks, not a boot-state flag.
- **The router-reached path run 11 could not attribute is a warm-restart
  scheduler entry, not a second verifier.** The ASGN router `0x0111ea24`
  (run 5) dispatches byte-1 `0xFE` (`cmp r0,#0xfe; beq` at `0x0111ea7c`) to
  `bl 0x1102970` at `0x0111ea8e` — the **scheduler wrapper** `push {r4,lr}`
  at `0x01102970`, which calls veneer `0x1134394` → `0x61070295` (a render
  manager stub, `bx lr` immediately at the pinned entry), bulk inits
  `0x110bdc4` and `0x110c686`, tail-calls `0x110efba`, and whose tail at
  `0x01102986..0x01102982` **falls into the same boot task** (`bl 0x1102986`
  from `0x01102976/0x0110297a/0x01102982` then `b.w 0x110efba` from
  `0x01102982`). So `0x1102986` is reached exactly twice: once from reset and
  once from the `0xFE` command path; both paths converge on one boot task,
  which alone drives the load route. (`0x1102970` has exactly one caller:
  `0x111ea8e`.)
- The SysTick exception vector `0x1100058` (Thumb `0x01102945`, body
  `0x01102944`) is a **distinct idle worker** (`bl 0x111f246`, ICSR write
  `0xe000ef00+0x180` on exit), not the tick incrementer.

## Method

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_boot_entry_study.py
```

The tool byte-pins 84 anchors (the reset vector word, both handler vector
words, the reset entry's register clears and SCB/CPACR writes, the ERAM
literals, the boot task's SysTick configuration and log strings, the verify
veneer cell's three halfwords, the tick handler's increment sequence, the
SysTick handler body, the ASGN router's `0xFE` dispatch and scheduler call,
and both state-word literal loads), then scans for direct BL callers of the
boot task, the scheduler wrapper and the veneer cell. All scanner machinery is
reused from run 11's `tools/core1_load_route_study.py`.

Real tool output (command above):

```json
{
  "reset_vector_word": "0x1100e55",
  "tick_vector_word": "0x110292d",
  "systick_vector_word": "0x1102945",
  "reset_callers": [],
  "boot_task_callers": [
    "0x1100e42"
  ],
  "verify_veneer_callers": [
    "0x1102a3a"
  ],
  "scheduler_callers": [
    "0x111ea8e"
  ],
  "ok": true,
  "anchors_checked": 84,
  "anchor_problems": [],
  "sha256": "6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154"
}
```

(`exit=0`. `reset_callers` is empty because nothing calls the reset entry —
it is hardware vectored; the census records that as the expected negative.)

Key disassembly, real recorded output of the command below (run against the
pinned image with `tools/core1.py` disasm; each line verified byte-exact by
the anchors above). Command:

```sh
BMC_CORPUS_DIR=<main>/local PYTHONPATH=tools /path/to/.venv/bin/python - <<'EOF'
from core1 import Core1
from pathlib import Path
core = Core1(Path('<main>/local/b0c1a.bin'))
for a, n in ((0x01100e2a, 0x24), (0x0110298a, 0x30), (0x01102a26, 0x20),
             (0x01102a3a, 0x10), (0x01102a4a, 0x8), (0x0110292c, 0xc),
             (0x0111ea7a, 0x18), (0x01102976, 0x10)):
    for line in core.disasm(a, n):
        print(line)
EOF
```

Real output (trimmed to one line before/after cut ranges):

```text
01100e2a  0948       ldr       r0, [pc, #0x24] ; [0x1100e50] = 0xe000ed0c
01100e2e  4ff6ff02   movw      r2, #0xf8ff
01100e40  0160       str       r1, [r0]
01100e42  01f0a0fd   bl        #0x1102986
01100e46  30bf       wfi
01100e48  fde7       b         #0x1100e46
0110298a  694c       ldr       r4, [pc, #0x1a4] ; [0x1102b30] = 0x200800d8
0110298c  4ff47a71   mov.w     r1, #0x3e8
01102992  a068       ldr       r0, [r4, #8]
01102998  b0fbf1f0   udiv      r0, r0, r1
0110299e  6548       ldr       r0, [pc, #0x194] ; [0x1102b34] = 0xe000e00f
011029a0  b1f1807f   cmp.w     r1, #0x1000000
011029a6  7161       str       r1, [r6, #0x14]
011029aa  80f8141d   strb.w    r1, [r0, #0xd14]
011029b2  3161       str       r1, [r6, #0x10]
01102a26  6649       ldr       r1, [pc, #0x198] ; [0x1102bc0] = 0xe000e006
01102a28  1020       movs      r0, #0x10
01102a2a  81f80004   strb.w    r0, [r1, #0x400]
01102a32  c6f80001   str.w     r0, [r6, #0x100]
01102a36  fef7f0ff   bl        #0x1101a1a
01102a3a  31f0b0fc   bl        #0x113439e
01102a3e  31f0b3fc   bl        #0x11343a8
01102a42  fef7c4fe   bl        #0x11017ce
01102a4a  1430       adds      r0, #0x14
01102a4e  03d2       bhs       #0x1102a58
01102a50  30bf       wfi
0110292c  8048       ldr       r0, [pc, #0x200] ; [0x1102b30] = 0x200800d8
01102930  0168       ldr       r1, [r0]
01102932  491c       adds      r1, r1, #1
01102934  0160       str       r1, [r0]
0111ea7a  fe28       cmp       r0, #0xfe
0111ea7c  07d0       beq       #0x111ea8e
0111ea80  ebf791fd   bl        #0x110a5a6
0111ea8e  e3f76fff   bl        #0x1102970
01102976  09f025fa   bl        #0x110bdc4
0110297a  09f084fe   bl        #0x110c686
01102982  0cf01abb   b.w       #0x110efba
```

## Established

- The load route's trigger is **boot, not a runtime service**: reset →
  `0x01100e2a` → boot task `0x01102986` → veneer `0x0113439e` → verify
  routine `0x610010d0` → `SetExeMode` sequence. Every link is singly-called
  (boot task has one BL caller; the veneer cell has one BL caller), so the
  boot task is provably the image's only driver of the load route.
- `0x200800d8` is the SysTick tick counter, incremented by the handler at
  `0x0110292c` and used as the boot task's millisecond clock and its
  post-verify delay gate (20 and 19 ticks). This resolves the open question
  run 11 listed about that word's role in the verify routine.
- The `0xFE` byte-1 command (run 5's router) is a **scheduler entry** that
  re-enters the same boot task through the wrapper `0x01102970`; it is the
  second and only other path to the boot task. A 0xFE command therefore
  re-runs the full load/verify/mode-arming sequence.
- The SysTick exception handler (`0x1100058`) is distinct from the tick
  interrupt handler (`0x110003c`): the former idles/polls via `0x111f246`,
  the latter increments the counter and runs the timer task.

## Not established

- What interrupt 4 (NVIC ISER0 bit 4, armed at `0x01102a2a` just before the
  verify call) is on this SoC and which peripheral raises it; the handler
  table entry was not traced to a device.
- The bodies of the scheduler wrapper's callees (`0x61070295` is a `bx lr`
  stub at its pinned entry — whether the real work sits behind a later entry
  is unverified), `0x110bdc4`, `0x110c686`, `0x110efba` and the post-verify
  `0x61001442` — call structure verified, semantics inferred.
- Whether a `0xFE` command actually arrives on the recovered route in practice
  (the producer side of the ASGN router is still the missing peer edge).
- Whether the boot task's second half (after the 20-tick wait) can also run on
  the `0xFE` path's second entry, or whether the wrapper's tail-call ordering
  prevents it; the task is straight-line, so a second full pass is the
  natural reading, but the timers and ISR state it assumes are unverified.
- bmc1 (`b1c1a.bin`) mirrors none of this chain; untouched.

## Reproduce

```sh
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python tools/core1_boot_entry_study.py
BMC_CORPUS_DIR=<main>/local /path/to/.venv/bin/python -m unittest discover -s tests -p test_core1_boot_entry_study.py -v
```

The tool exits 0 only when all 84 anchors match, the SHA-256 matches, and the
three caller lists equal the expected single-element sets. Tests: with the
corpus 8 pass; without the corpus 3 model tests pass and the 5 pinned-image
tests skip cleanly.

## Best next item

Decode the DRAM-IO verify phase's aperture tables (`0x0113a970`/`0x0113a988`,
run 11) to bound what a resident loader's own verify could reuse, or take A2
(program reservations): the per-DSP list-slot bound `cmp r4,#6` in the boot
walk already gives 7 slots per DSP — cross-check against the stock lists the
boot task uploads to say which are occupied in the stock image.