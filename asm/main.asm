#include "cpu.asm"

ldi r0, 0
ldi r1, 0
ldi r2, 0
ldi r3, 0
ldi r4, 0
ldi r5, 0
ldi r6, 0

; zero
; goToVectorTable:
;     ldi r6, 0
;     add r6, r0
;     add r6, r0
;     add r6, r0
;     add r6, r0
;     add r6, r0
;     add r6, r0
;     ldi16 r2, vectorTable
;     add r2, r6
;     jabsr r2


; testeJumps:
;     nop
;     nop
;     ldi r0, (.jump1 - $) - 2
;     jrelr r0
;     .jump2:
;     nop
;     nop
;     nop
;     jreli .jump3
;     .jump1:
;     nop
;     nop
;     nop
;     nop
;     ldi16 r0, .jump2
;     jabsr r0
;     .jump3:
;     ldi r0, 1
;     ldi16 r2, goToVectorTable
;     jabsr r2

; testeAlu:
;     ldi r0, 2
;     ldi16 r2, goToVectorTable
;     jabsr r2

; testeAlu2:
;     halt


; ;position of the vector table on the end of the memoy
; #addr memorySize - (endVectorTabel - vectorTable)
; vectorTable:
;     ldi16 r0, testeJumps
;     jabsr r0
;     ldi16 r0, testeAlu
;     jabsr r0
;     ldi16 r0, testeAlu2
;     jabsr r0
; endVectorTabel:
