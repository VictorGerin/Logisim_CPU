#once

 ;System functions for the Stack and dword operations

#ruledef ;mov dword instructions
{
    mov bc, xy => asm { 
        mov b, x
        mov c, y
    }

    mov xy, bc => asm { 
        mov x, b
        mov y, c
    }

    mov m, xy => asm { 
        mov m1, x
        mov m2, y
    }

    mov xy, [{addr: i16}] => asm {
        load a, [{addr} + 0]
        mov y, a
        load a, [{addr} + 1]
        mov x, a
    }

    mov [{addrDest: i16}], xy => asm {
        mov a, y
        store a, [{addrDest} + 0]
        mov a, x
        store a, [{addrDest} + 1]
    }

    mov bc, [{addr: i16}] => asm {
        load b, [{addr} + 0]
        load c, [{addr} + 1]
    }

    mov bc, {val: i16} => asm {
        imm m, {val}
        mov b, m2
        mov c, m1
    }

    mov [{addrDest: i16}], bc => asm {
        store b, [{addrDest} + 0]
        store c, [{addrDest} + 1]
    }

    mov m, [{addr: i16}] => asm {
        load a, [{addr} + 0]
        mov m2, a
        load a, [{addr} + 1]
        mov m1, a
    }

    mov [{addrDest: i16}], m => asm {
        mov a, m2
        store a, [{addrDest} + 0]
        mov a, m1
        store a, [{addrDest} + 1]
    }

    mov [{addrDest: i16}], [{addrOrin: i16}] => asm {
        load a, [{addrOrin} + 0]
        store a, [{addrDest} + 0]
        load a, [{addrOrin} + 1]
        store a, [{addrDest} + 1]
    }
}

#ruledef
{

    push [{addrOrin: i16}] => asm {
        mov [system_trash_var + 0], [{addrOrin}]
        call pushFunc
    }

    push xy => asm {
        mov [system_trash_var + 0], xy
        call pushFunc
    }

    push {val: i16} => asm {
        imm m, {val}
        mov xy, m
        push xy
    }

    pop [{addrDest: i16}] => asm {
        call popFunc
        mov [{addrDest}], [system_trash_var + 0]
    }

    pop xy => asm {
        call popFunc
        mov xy, [system_trash_var + 0]
    }

}

#ruledef ; add16 instru
{
    add16 [{addrDest: i16}], [{addrOrin: i16}] => asm {
        mov [system_trash_var + 0], [{addrDest}]
        mov [system_trash_var + 2], [{addrOrin}]
        call add16BitFast
        mov [{addrDest}], [system_trash_var + 0]
    }

    add16 [{addrDest: i16}], bc => asm {
        mov [system_trash_var + 0], [{addrDest}]
        mov [system_trash_var + 2], bc
        call add16BitFast
        mov [{addrDest}], [system_trash_var + 0]
    }

    add16 bc, [{addrOrin: i16}] => asm {
        mov [system_trash_var + 0], [{addrOrin}]
        call add16BitBc
    }

}

#ruledef ; get and set Var on the stack
{
    getVar [{addrDest: i16}], [{addrOrin: i16}] => asm {
        mov [system_trash_var + 6], bc
        mov [system_trash_var], [{addrOrin}]
        call getVar
        mov [{addrDest}], bc
        mov bc, [system_trash_var + 6]
    }

    getVar bc, [{addrOrin: i16}] => asm {
        mov [system_trash_var], [{addrOrin}]
        call getVar
    }

    setVar [{addrDest: i16}], [{addrOrin: i16}] => asm {
        mov [system_trash_var + 6], bc
        mov [system_trash_var + 2], [{addrDest}]
        mov bc, [{addrOrin}]
        call setVar
        mov bc, [system_trash_var + 6]
    }

    setVar [{addrDest: i16}], bc => asm {
        mov [system_trash_var + 2], [{addrDest}]
        call setVar
    }
}

#addr (0x10000 - (end - systemFuncs))
systemFuncs:
;This section is for system functions that enalbes the Stack

;Trash var is used for temporary storage of data in the system functions
;there is no meaning to the data in the trash var, each function can use it as it wants
;normally (system_trash_var + 0) is used as return.
system_trash_var:
    #res 8

;This section contains contants that are used in the system functions or the user code
const_1:
    #d 1`16
const_neg1:
    #d -1`16
const_neg2:
    #d -2`16
const_neg4:
    #d -4`16
const_neg6:
    #d -6`16
const_neg8:
    #d -8`16


;dword [system_trash_var + 0] is the offset of the stack pointer where the variable is stored
;Reg BC is used as the return value
;Uses system_trash_var 0, 1, 2, 3, 4 and 5
;Change Reg A, B, C, M and XY
getVar:
    mov [system_trash_var + 4], xy

    mov [system_trash_var + 2], [stackPrt + 0]
    call add16BitFast

    mov xy, [system_trash_var + 0]

    mov m, xy
    load b
    inc xy
    mov m, xy
    load c

    mov xy, [system_trash_var + 4]
    ret

;setVar
;dword [system_trash_var + 2] is the offset of the stack pointer where the variable is stored
;dword [system_trash_var + 4] is the value to be stored on the stack
;Uses system_trash_var 0, 1, 2, 3, 4 and 5
;Change Reg A, B, C, M and XY
setVar:
    mov [system_trash_var + 4], xy

    ;xy = [stackPrt] + [trash_var + 2]
    mov [system_trash_var + 0], [stackPrt + 0]
    call add16BitFast

    mov m, [system_trash_var + 0]
    mov xy, m
    store b

    inc xy

    mov m, xy
    store c


    mov xy, [system_trash_var + 4]
    ret

;dword [system_trash_var + 0] first operand to be added
;dword [system_trash_var + 2] secoond operand to be added
;dword [system_trash_var + 0] is used as the return value
;reg A return if carry
;Uses system_trash_var 0, 1, 2, 3
;Change Reg A, M and XY
add16Bit:
    store b, [.localStore + 0]
    store c, [.localStore + 1]
    store d, [.localStore + 2]

    load b, [system_trash_var + 1]
    load c, [system_trash_var + 3]

    add a 
    mov d, a; d = lsb

    ;get carry flag set on Reg B
    jc .carry
    imm b, 0
    jmp .continue
    .carry:
    imm b, 1
    .continue:

    load c, [system_trash_var + 0]
    add b ; add carry
    
    jc .carry2
    imm a, 0
    jmp .continue2
    .carry2:
    imm a, 1
    .continue2:

    load c, [system_trash_var + 2]
    add b ; b = msb

    store d, [system_trash_var + 1] ;store lsb
    store b, [system_trash_var + 0] ;store msb

    load b, [.localStore + 0]
    load c, [.localStore + 1]
    load d, [.localStore + 2]

    jc .setCarry
    jmp .return
    .setCarry:
    imm a, 1
    .return:
    ret
    ;As this function is heavily used is good preserve the registers B, and C
    .localStore:
        #res 3

add16BitFast:
    store b, [.localStore + 0]
    store c, [.localStore + 1]

    load b, [system_trash_var + 1]
    load c, [system_trash_var + 3]

    add a ; d = lsb

    ;get carry flag set on Reg B
    jc .carry
    imm b, 0
    jmp .continue
    .carry:
    imm b, 1
    .continue:

    load c, [system_trash_var + 0]
    add b ; add carry

    load c, [system_trash_var + 2]
    add b ; b = msb

    store a, [system_trash_var + 1] ;store lsb
    store b, [system_trash_var + 0] ;store msb

    load b, [.localStore + 0]
    load c, [.localStore + 1]

    ret
    ;As this function is heavily used is good preserve the registers B, and C
    .localStore:
        #res 2

;dword bc fisrt operand to be added
;dword [system_trash_var + 0] is the second operand to be added
add16BitBc:
    store d, [.localStore + 0]
    mov d, b

    load b, [system_trash_var + 1]
    add a; d = lsb

    jc .carry
    imm b, 0
    jmp .continue
    .carry:
    imm b, 1
    .continue:
    
    load c, [system_trash_var + 0]
    add b ; add carry

    mov c, d
    add b ; b = msb
    mov c, a; c = lsb

    ret
    .localStore:
        #res 1
;dword [system_trash_var + 0] is used as the return value
;Uses system_trash_var 0, 1, 2, 3, 4 and 5
;Change Reg A, M and XY
popFunc:
    mov [system_trash_var + 4], xy

    mov [system_trash_var + 0], [stackPrt]
    mov [system_trash_var + 2], [const_neg2]
    call add16BitFast

    mov [stackPrt], [system_trash_var]
    mov xy, [system_trash_var]
    
    mov m, xy
    load a
    store a, [system_trash_var + 0]
    inc xy
    mov m, xy
    load a
    store a, [system_trash_var + 1]

    mov xy, [system_trash_var + 4]
    ret

;dword [system_trash_var + 0] is the value to be pushed on the stack
;Uses system_trash_var 0, 1, 2, 3, 4 and 5
;Change Reg A, M and XY
pushFunc:
    mov [system_trash_var + 4], xy

    ;bc = xy = [stackPrt]
    mov xy, [stackPrt]

    load a, [system_trash_var + 0]
    mov m, xy
    store a

    inc xy
    load a, [system_trash_var + 1]
    mov m, xy
    store a

    ;xy = [stackPrt] + 1
    inc xy

    mov [stackPrt], xy

    mov xy, [system_trash_var + 4]
    ret



;This is the stack pointer
;it's points to the next free byte on the stack
;it's also use as reference on getVar and setVar
stackPrt:
    #d Stack`16
;The is the Stack it self where the variávels is std
Stack:
    #res 1024
end: