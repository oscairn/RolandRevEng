.syntax unified
.cpu cortex-m4
.thumb
.section .text
.balign 4
/* Link two bytes before the original halfword-aligned entry. */
.hword 0xbf00
.global marker_reply
.thumb_func
marker_reply:
    push {r4, lr}
    adr.w r0, marker_data
    movs r1, #19
    ldr r3, packetizer
    blx r3
    pop {r4, pc}
.balign 4
marker_data:
    .byte 0xf0, 0x41, 0x10, 0x4e, 0x13, 0, 0, 0, 0
    .byte 4, 15, 5, 3, 4, 3, 5, 2, 0x57, 0xf7
.balign 4
packetizer:
    .word 0x0111f0bf
