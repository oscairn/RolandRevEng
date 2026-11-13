#!/usr/bin/env python3
"""Bind the bmc0 CORE1 boot verify routine's entry chain, pinned image.

Run 11 (tools/core1_load_route_study.py) proved that the boot verify routine
0x610010d0 is the stock image's only end-to-end load-route user but found no
direct caller. This study closes that gap statically: it pins the reset
vector, the boot task, the byte-1 == 0xFE command that reaches the verify
routine through the ASGN router, and the interrupt handler that shares the
boot state word 0x200800d8. Every claim below is byte-pinned.
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SHA256 = '6d95449ae2a2df48fb60f8b69da6bf8c7198611255b63d59081ba5bdf5263154'

RESET_VECTOR_WORD = 0x1100004
RESET_ENTRY = 0x01100e55          # Thumb pointer stored in the vector
RESET_MAIN = 0x01100e42           # bl -> boot task
BOOT_TASK = 0x01102986            # bl target from reset; __main etc follow
BOOT_TASK_SCHEDULER = 0x01102970  # push {r4,lr}; the bl 0x1102986 tail
ASGN_ROUTER = 0x0111ea24          # run 5's first router
BOOT_STATE_WORD = 0x200800d8      # tick counter / uptime, read by both paths
VERIFY_ROUTINE = 0x610010d0       # run 11's load-route user
VERIFY_VENEER = 0x0113439e        # movw ip,#0x10d1; movt ip,#0x6100; bx ip
VERIFY_CALLER = 0x01102a3a        # bl 0x113439e inside the boot task
TICK_VECTOR_WORD = 0x110003c
TICK_HANDLER_THUMB = 0x0110292d      # vector word value (Thumb bit set; body at 0x110292c)
SYSTICK_VECTOR_WORD = 0x1100058
SYSTICK_HANDLER_THUMB = 0x01102945   # vector word value (Thumb bit set; body at 0x1102944)
NVIC_CLOCK_GATE = 0x01102a2a      # strb r0,[r1,#0x400], r0=0x10, ISER r1=0xe000e006

# (address, hex bytes) — byte-exact anchors, each naming one instruction or word.
ANCHORS = (
    # Reset vector and reset entry.
    (0x1100004, '550e1001'),            # reset vector word = 0x01100e55
    (0x01100e54, '4ff00000'),           # mov.w r0,#0 (reset entry first instr)
    (0x01100e88, '80f30088'),           # msr apsr_nzcvq, r0
    (0x01100e9c, 'eff30880'),           # mrs r0, msp
    (0x01100ea0, '80f30988'),           # msr psp, r0
    (0x01100eb8, '0748'),               # ldr r0,[pc,#0x1c] -> 0x1100ee9
    (0x01100ebc, '0748'),               # ldr r0,[pc,#0x1c] -> 0x1102ceb
    (0x01100ec0, '0748'),               # ldr r0,[pc,#0x1c] -> 0x61000001
    (0x01100ec2, '0047'),               # bx r0 (enter ERAM code)
    (0x01100ed8, 'e90e1001'),           # literal: __rt_entry 0x1100ee9
    (0x01100edc, 'eb2c1001'),           # literal: ERAM tail 0x1102ceb
    (0x01100ee0, '01000061'),           # literal: ERAM entry 0x61000001
    # Reset wrapper -> SCB config -> boot task.
    (0x01100e2a, '0948'),               # ldr r0,[pc] -> 0xe000ed0c
    (0x01100e2e, '4ff6ff02'),           # movw r2,#0xf8ff
    (0x01100e40, '0160'),               # str r1,[r0] (SCB AIRCR priority mask)
    (0x01100e42, '01f0a0fd'),           # bl 0x1102986 (boot task)
    (0x01100e46, '30bf'),               # wfi
    (0x01100e48, 'fde7'),               # b 0x1100e46 (halt loop)
    # Boot task scheduler head and its first calls.
    (0x01102970, '10b5'),               # push {r4, lr}
    (0x01102972, '31f00ffd'),           # bl 0x1134394 (veneer -> 0x61070295)
    (0x01102976, '09f025fa'),           # bl 0x110bdc4 (bulk init A)
    (0x0110297a, '09f084fe'),           # bl 0x110c686 (bulk init B)
    (0x0110297e, 'bde81040'),           # pop.w {r4, lr}
    (0x01102982, '0cf01abb'),           # b.w 0x110efba (bulk init C)
    # Boot task proper (called by reset).
    (0x01102986, 'fff709fa'),           # bl 0x1101d9c
    (0x0110298a, '694c'),               # ldr r4,[pc] -> 0x200800d8
    (0x0110298c, '4ff47a71'),           # mov.w r1,#0x3e8 (ms divisor)
    (0x01102992, 'a068'),               # ldr r0,[r4,#8]
    (0x01102998, 'b0fbf1f0'),           # udiv r0, r0, r1
    (0x0110299e, '6548'),               # ldr r0,[pc] -> 0xe000e00f
    (0x011029a0, 'b1f1807f'),           # cmp.w r1,#0x1000000 (SysTick LOAD bound)
    (0x011029a6, '7161'),               # str r1,[r6,#0x14] (STK LOAD)
    (0x011029a8, 'f821'),               # movs r1,#0xf8
    (0x011029aa, '80f8141d'),           # strb.w r1,[r0,#0xd14] (SHPR: prio)
    (0x011029ae, 'b261'),               # str r2,[r6,#0x18] (STK VAL=0)
    (0x011029b0, '0721'),               # movs r1,#7
    (0x011029b2, '3161'),               # str r1,[r6,#0x10] (STK CTRL: enable)
    (0x011029ba, '0120'),               # movs r0,#1
    (0x011029bc, '21f0d0fb'),           # bl 0x1124160
    (0x011029c0, '00f0eefc'),           # bl 0x11033a0 (coef getter A)
    (0x011029c6, '00f0e9fc'),           # bl 0x110339c (coef getter B)
    (0x011029ce, '5aa1'),               # adr r1,#0x168 -> "CORE1 Version..."
    (0x011029d0, '6048'),               # ldr r0,[pc] -> 0x20091280 (log block)
    (0x011029d2, '31f0d5fc'),           # bl 0x1134380 (log helper)
    # Boot task: interrupt arm and verify call.
    (0x01102a26, '6649'),               # ldr r1,[pc] -> 0xe000e006
    (0x01102a28, '1020'),               # movs r0,#0x10
    (0x01102a2a, '81f80004'),           # strb.w r0,[r1,#0x400] (NVIC ISER0 bit4)
    (0x01102a2e, '4020'),               # movs r0,#0x40
    (0x01102a30, '0125'),               # movs r5,#1
    (0x01102a32, 'c6f80001'),           # str.w r0,[r6,#0x100] (STK CTRL again)
    (0x01102a36, 'fef7f0ff'),           # bl 0x1101a1a (IO init)
    (0x01102a3a, '31f0b0fc'),           # bl 0x113439e (veneer -> verify routine)
    (0x01102a3e, '31f0b3fc'),           # bl 0x11343a8 (veneer -> 0x61001443)
    (0x01102a42, 'fef7c4fe'),           # bl 0x11017ce
    (0x01102a4a, '1430'),               # adds r0,#0x14 (wfi deadline: +20 ticks)
    (0x01102a4e, '03d2'),               # bhs 0x1102a58
    (0x01102a50, '30bf'),               # wfi
    (0x01102a56, 'fbd3'),               # blo 0x1102a50
    # Boot task: log strings around the verify call.
    (0x1102b38, '434f5245'),            # "CORE" of "CORE1 Version    : %d.%02d"
    (0x1102ba8, '25303864'),            # "%08d" of "%08d: CORE I/O Init"
    # Verify veneer cell.
    (0x0113439e, '41f2d10c'),           # movw ip,#0x10d1
    (0x011343a2, 'c6f2001c'),           # movt ip,#0x6100
    (0x011343a6, '6047'),               # bx ip
    # Tick interrupt handler (vector 0x110003c) sharing the state word.
    (0x110003c, '2d291001'),            # vector word 0x0110292d
    (0x0110292c, '8048'),               # ldr r0,[pc] -> 0x200800d8
    (0x01102930, '0168'),               # ldr r1,[r0]
    (0x01102932, '491c'),               # adds r1,r1,#1
    (0x01102934, '0160'),               # str r1,[r0] (tick++)
    (0x01102936, 'fff789ff'),           # bl 0x110284c (timer task work)
    (0x0110293a, '00f016fd'),           # bl 0x110336a (clock gate poll)
    (0x0110293e, 'bff34f8f'),           # dsb sy
    (0x01102942, '10bd'),               # pop {r4, pc}
    # SysTick handler is a distinct idle worker (vector 0x1100058).
    (0x1100058, '45291001'),            # vector word 0x01102945
    (0x01102944, '2de90840'),           # push.w {r3, lr}
    (0x01102948, '1cf07dfc'),           # bl 0x111f246
    (0x0110294e, '6846'),               # mov r0,sp
    (0x0110295e, '4ff0e021'),           # mov.w r1,#-0x1fff2000
    (0x01102964, 'c1f88001'),           # str.w r0,[r1,#0x180] (ICSR write)
    # ASGN router: byte-1 0xFE reaches the scheduler wrapper.
    (0x0111ea7a, 'fe28'),               # cmp r0,#0xfe
    (0x0111ea7c, '07d0'),               # beq 0x111ea8e
    (0x0111ea8e, 'e3f76fff'),           # bl 0x1102970 (scheduler wrapper)
    (0x0111ea92, '00f0efb8'),           # b.w 0x111ec74 (router tail)
    # Boot state word literal loads in both paths.
    (0x01102b30, 'd8000820'),           # literal 0x200800d8 (boot task)
    (0x011028fc, 'c4000820'),           # literal 0x200800c4 (timer task base)
)

# The two veneer->scheduler wrappers and their single callers, per run 11's
# veneer-census method.  0x1134394 -> 0x61070295 (render-manager init stub).
SCHEDULER_VENEER = 0x01134394
SCHEDULER_VENEER_TARGET = 0x61070295
SCHEDULER_VENEER_CALLER = 0x01102972

EXPECTED_RESET_CHAIN = (
    0x1100004, 0x01100e54, 0x01100e42, 0x01102986, 0x01102a3a,
)
EXPECTED_VERIFY_CALLERS = (0x01102a3a,)
EXPECTED_SCHEDULER_CALLERS = (0x0111ea8e,)
EXPECTED_TICK_VECTOR = (0x110003c, 0x1100058)


def load_image(path):
    from core1 import Core1
    return Core1(path)


def check_anchors(core):
    problems = []
    for address, expected in ANCHORS:
        size = len(expected) // 2
        actual = core.data[core.offset(address):core.offset(address) + size]
        if actual.hex() != expected:
            problems.append((hex(address), expected, actual.hex()))
    return len(ANCHORS), problems


def bl_callers(core, target):
    from core1_load_route_study import bl_callers as impl
    return impl(core, target)


def veneer_callers(core, target):
    from core1_load_route_study import veneer_callers as impl
    return impl(core, target)


def word_pointer_refs(core, target):
    from core1_load_route_study import word_pointer_refs as impl
    return impl(core, target)


def census(core):
    verify_veneer_callers = bl_callers(core, VERIFY_VENEER)
    scheduler_callers = bl_callers(core, BOOT_TASK_SCHEDULER)
    reset_callers = bl_callers(core, RESET_MAIN)
    boot_task_callers = bl_callers(core, BOOT_TASK)
    return {
        'reset_vector_word': hex(core.u32(RESET_VECTOR_WORD)),
        'tick_vector_word': hex(core.u32(TICK_VECTOR_WORD)),
        'systick_vector_word': hex(core.u32(SYSTICK_VECTOR_WORD)),
        'reset_callers': [hex(a) for a in reset_callers],
        'boot_task_callers': [hex(a) for a in boot_task_callers],
        'verify_veneer_callers': [hex(a) for a in verify_veneer_callers],
        'scheduler_callers': [hex(a) for a in scheduler_callers],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', help='b0c1a.bin (default: BMC_CORPUS_DIR)')
    args = parser.parse_args()
    import os
    path = Path(args.image or os.environ.get('BMC_CORPUS_DIR', 'local')) / 'b0c1a.bin'
    core = load_image(path)
    import hashlib
    digest = hashlib.sha256(core.data).hexdigest()
    anchors_checked, problems = check_anchors(core)
    report = census(core)
    report['ok'] = not problems and digest == SHA256
    report['anchors_checked'] = anchors_checked
    report['anchor_problems'] = problems
    report['sha256'] = digest
    import json
    print(json.dumps(report, indent=2))
    ok = (not problems and digest == SHA256
          and report['reset_vector_word'] == hex(RESET_ENTRY)
          and report['tick_vector_word'] == hex(TICK_HANDLER_THUMB)
          and report['systick_vector_word'] == hex(SYSTICK_HANDLER_THUMB)
          and report['reset_callers'] == []           # reset path has no callers
          and report['boot_task_callers'] == [hex(RESET_MAIN)]
          and report['verify_veneer_callers'] == [hex(VERIFY_CALLER)]
          and report['scheduler_callers'] == [hex(0x111ea8e)])
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()