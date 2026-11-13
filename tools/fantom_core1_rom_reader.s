.syntax unified
.cpu cortex-m4
.thumb
.equ DMA,       0x40001000
.equ LATCH,     0x6102d330
.equ PATTERN,   0x6102d340
.equ BOUNCE,    0x6102d380
.equ PACKETIZE, 0x0111f0bf

.section .entry,"ax",%progbits
.global reader_entry
.thumb_func
reader_entry:
    movw ip, #:lower16:rom_reader
    movt ip, #:upper16:rom_reader
    bx ip

.section .text,"ax",%progbits
.balign 4
.global rom_reader
.thumb_func
rom_reader:
    push.w {r4-r11, lr}
    sub sp, #116
    mrs r1, primask
    cmp r1, #0
    bne finish
    ldr r1, [r0]
    cmp r1, #10
    bne finish
    ldr r5, [r0, #8]
    lsls r1, r5, #8
    bne finish
    lsrs r5, r5, #24
    cmp r5, #3
    bhi finish
    ldrb r1, [r0, #13]
    cmp r1, #0xf7
    bne finish
    add r1, r0, #4
    movs r2, #9
    movs r3, #0
check_sum:
    ldrb r4, [r1], #1
    cmp r4, #128
    bhs finish
    adds r3, r4
    subs r2, #1
    bne check_sum
    tst r3, #127
    bne finish
    ldr r4, [r0, #4]
    cmp r5, #1
    beq snapshot_check
    cmp r4, #0
    beq address_ok
    ldr r1, =0x40690000
    cmp r4, r1
    bne finish
    cmp r5, #3
    bne finish
address_ok:
    cmp r5, #0
    beq marker
    b init_report
snapshot_check:
    lsls r1, r4, #8
    bne finish
    lsrs r4, r4, #24
    cmp r4, #7
    bhi finish
init_report:
    add r0, sp, #80
    movs r1, #8
    movs r2, #0
clear_report:
    str r2, [r0], #4
    subs r1, #1
    bne clear_report
    cmp r5, #1
    beq snapshot
    ldr r8, =PATTERN
    movs r0, #1
    mov r9, r0
    cmp r5, #2
    beq source_ready
    ldr r8, =0x01200000
    movs r0, #2
    mov r9, r0
    cmp r4, #0
    beq source_ready
    ldr r8, =0x012034c0
    movs r0, #6
    mov r9, r0
source_ready:
    str r8, [sp, #84]
    ldr r0, =0x5244ff00
    str r0, [sp, #80]
    ldr r0, =LATCH
    ldr r1, [r0]
    cmp r1, #0
    bne latched
    ldr r0, =0xe000ed14
    ldr r0, [r0]
    tst r0, #0x10000
    bne cache_on
    ldr r6, =DMA
    ldr r0, [r6]
    tst r0, #0x80000000
    beq disabled
    mrs r10, primask
    cpsid i
    movs r7, #7
find_channel:
    add r6, r7, #1
    lsls r6, #4
    ldr r0, =DMA
    adds r6, r0
    ldm r6, {r0-r3}
    orrs r0, r1
    orrs r0, r2
    orrs r0, r3
    beq channel_ready
    subs r7, #1
    bpl find_channel
    movs r0, #3
    b restore_mask
channel_ready:
    ldr r0, =0x52440000
    orr r0, r0, r7, lsl #8
    str r0, [sp, #80]
    movs r0, #0
    mov r11, r0
next_word:
    ldm r6, {r0-r3}
    orrs r0, r1
    orrs r0, r2
    orrs r0, r3
    bne channel_changed
    ldr r1, =BOUNCE
    ldr r0, =0xa5a5a5a5
    movs r2, #32
fill_bounce:
    str r0, [r1], #4
    subs r2, #1
    bne fill_bounce
    add r0, r8, r11, lsl #2
    str r0, [r6, #8]
    ldr r0, =BOUNCE
    str r0, [r6, #12]
    mov r0, #0x08000000
    str r0, [r6, #4]
    mov r0, #0xa0000000
.global dma_trigger
dma_trigger:
    str r0, [r6]
    dsb sy
    movw r4, #8192
.global dma_poll
dma_poll:
    ldr r0, [r6, #4]
    and r0, r0, #0x70000
    cmp r0, #0
    beq poll_again
    ldr r1, [r6]
    tst r1, #0x80000000
    beq terminal
poll_again:
    subs r4, #1
    bne dma_poll
    ldr r0, [r6]
    bic r0, r0, #0x80000000
    str r0, [r6]
    dsb sy
    movs r0, #5
    b latch_error
terminal:
    cmp r0, #0x50000
    bne dma_error
    ldr r0, [r6, #8]
    add r1, r8, r11, lsl #2
    adds r1, #4
    cmp r0, r1
    bne count_error
    ldr r0, [r6, #12]
    ldr r1, =BOUNCE + 4
    cmp r0, r1
    bne count_error
    ldr r2, =0xa5a5a5a5
    movs r3, #31
guard_loop:
    ldr r0, [r1], #4
    cmp r0, r2
    bne canary_error
    subs r3, #1
    bne guard_loop
    ldr r0, =BOUNCE
    ldr r0, [r0]
    cmp r5, #2
    bne store_result
    ldr r1, =PATTERN
    ldr r1, [r1]
    cmp r0, r1
    bne pattern_error
store_result:
    add r1, sp, #88
    str r0, [r1, r11, lsl #2]
    bl clear_channel
    add r11, #1
    cmp r11, r9
    blo next_word
    movs r0, #1
    b restore_mask
dma_error:
    movs r0, #6
    b terminal_error
count_error:
    movs r0, #9
    b terminal_error
canary_error:
    movs r0, #7
    b terminal_error
pattern_error:
    movs r0, #10
terminal_error:
    mov r4, r0
    bl clear_channel
    mov r0, r4
latch_error:
    ldr r1, =LATCH
    movs r2, #1
    str r2, [r1]
    b restore_mask
channel_changed:
    movs r0, #3
restore_mask:
    msr primask, r10
    b status
latched:
    movs r0, #8
    b status
cache_on:
    movs r0, #4
    b status
disabled:
    movs r0, #2
status:
    ldr r1, [sp, #80]
    orrs r0, r1
    str r0, [sp, #80]
    b send_report
clear_channel:
    movs r1, #0
    str r1, [r6]
    str r1, [r6, #4]
    str r1, [r6, #8]
    str r1, [r6, #12]
    dsb sy
    bx lr
snapshot:
    ldr r0, =0x444d0000
    orrs r0, r4
    str r0, [sp, #80]
    ldr r0, =DMA
    ldr r1, [r0]
    str r1, [sp, #84]
    adds r4, #1
    add r0, r0, r4, lsl #4
    ldm r0, {r1-r4}
    add r0, sp, #88
    stm r0, {r1-r4}
    ldr r0, =0xe000ed00
    ldr r1, [r0]
    str r1, [sp, #104]
    ldr r1, [r0, #20]
    str r1, [sp, #108]
send_report:
    ldr r0, =0x4e1041f0
    str r0, [sp]
    movs r0, #0x13
    str r0, [sp, #4]
    movs r0, #0
    strb r0, [sp, #8]
    add r4, sp, #80
    add r5, sp, #9
    movs r6, #8
    movs r7, #0
word_loop:
    ldr r0, [r4], #4
    movs r1, #8
nibble_loop:
    lsrs r2, r0, #28
    adds r7, r2
    strb r2, [r5], #1
    lsls r0, #4
    subs r1, #1
    bne nibble_loop
    subs r6, #1
    bne word_loop
    rsbs r7, #0
    and r7, #127
    strb r7, [sp, #73]
    movs r0, #0xf7
    strb r0, [sp, #74]
    mov r0, sp
    movs r1, #75
    b packet
marker:
    adr.w r0, marker_data
    movs r1, #19
packet:
    ldr r3, =PACKETIZE
    blx r3
finish:
    add sp, #116
    pop.w {r4-r11, pc}
.balign 4
marker_data:
    .byte 0xf0,0x41,0x10,0x4e,0x13,0,0,0,0,4,15,5,3,4,3,5,2,0x57,0xf7
.balign 4
.ltorg
