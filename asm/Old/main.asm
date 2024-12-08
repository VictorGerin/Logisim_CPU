#include "cpu.asm"
#include "cpu_system.asm"

#addr 0x0
jmp main

trash_var:
    #res 10

;Set Zero flag of Status register if dword[trash_var] is One
isOne:
    mov a, b
    imm b, -1
    add b
    mov b, a
    jz .zero ;if not zero return
        ret
    .zero:
    mov d, c
    imm c, 0
    add A
    mov c, d
    
    ret

;Set Zero flag of Status register if dword[trash_var] is Zero
isZero:
    mov a, b

    imm b, 0
    add b
    mov b, a
    jz .zero ;if not zero return
        ret
    .zero:
    mov d, c
    imm c, 0
    add A
    mov c, d
    
    ret

;bc = fibo(dword n)
;n = dword [stack - 6]
fibo:
    push xy; return val
    push xy; return val

    getVar bc, [const_neg6]

    ;[trash_var + 0] = [const_neg4 + 0]
    call isZero
    jnz .notZero
    imm b, 1
    imm c, 0
    jmp .finish ;if(isZero([trash_var + 0])) return 1
.notZero:
    ;[trash_var + 0] = [const_neg4 + 0]
    call isOne
    jnz .notOne
    imm b, 1
    imm c, 0
    jmp .finish ;if(isOne([trash_var + 0])) return 1
.notOne:

    add16 bc, [const_neg1]
    
    push [trash_var]
    call fibo
    pop xy; discart passed variable
    mov [trash_var], bc

    setVar [const_neg2], [trash_var]
    ;sum = fibo([trash_var + 0] - 1)

    getVar bc, [const_neg6]
    add16 bc, [const_neg2]

    push [trash_var]
    call fibo
    pop xy; discart passed variable
    ; mov [trash_var], bc
    
    getVar [trash_var + 2], [const_neg2]

    add16 bc, [trash_var + 2]

.finish:
    pop xy
    pop xy
    ret

var1:
    #d 0x0000
var2:
    #d 0x0100
main:

    ; mov bc, 0x00ff
    ; add16 bc, [var2]
    ; mov [trash_var], bc
    ; push 2
    ; call fibo
    ; pop xy; discart passed variable

    ; imm M, 0x1234
    ; mov xy, m
    ; mov [trash_var], xy
    ; imm M, 0x4321

    ; mov xy, m
    ; mov [trash_var + 2], xy
    ; add16 [trash_var], [trash_var + 2]

    imm M, trash_var
    halt



