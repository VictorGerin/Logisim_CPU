#once

#subruledef  register
{
    A => 0x000`3
    B => 0x001`3
    C => 0x002`3
    D => 0x003`3
    M1 => 0x004`3
    M2 => 0x005`3
    X => 0x006`3
    Y => 0x007`3
}

#subruledef  AluOut
{
    A => 0x0`1
    B => 0x1`1
}

#subruledef  MemRegs
{
    A => 0x0`2
    B => 0x1`2
    C => 0x2`2
    D => 0x3`2
}

#subruledef  Move16Dest
{
    XY => 0x0`1
    PC => 0x1`1
}
#subruledef  Move16Source
{
    M   => 0x0`2
    XY  => 0x1`2
    J   => 0x2`2
}

#ruledef ;ALU
{
    add {d: AluOut} => 0b1000 @ d @ 0b000
    inc {d: AluOut} => 0b1000 @ d @ 0b001
    and {d: AluOut} => 0b1000 @ d @ 0b010
    or {d: AluOut} => 0b1000 @ d @ 0b011
    xor {d: AluOut} => 0b1000 @ d @ 0b100
    not {d: AluOut} => 0b1000 @ d @ 0b101
    shl {d: AluOut} => 0b1000 @ d @ 0b110
}

#ruledef ;Memory
{
    load {d: MemRegs} => 0b100100 @ d
    store {d: MemRegs} => 0b100110 @ d


    load {d: MemRegs}, [{add: i16}] => asm {
        imm M, {add}
        load {d}
    }

    store {d: MemRegs}, [{add: i16}] => asm {
        imm M, {add}
        store {d}
    }
}

#ruledef ;branch
{
    jmp {addr: i16} => 0b11100110 @ addr`16
    call {addr: i16} => 0b11100111 @ addr`16
    ret => asm { mov PC, XY }
    jn {addr: i16}  => 0b111_10000 @ addr`16
    jc {addr: i16}  => 0b111_01000 @ addr`16
    jz {addr: i16}  => 0b111_00100 @ addr`16
    jnz {addr: i16} => 0b111_00010 @ addr`16
}

#ruledef
{
    halt => 0b10101110
    mov {d: register}, {s: register} => 0b00 @ d @ s
    mov {d: Move16Dest}, {s: Move16Source} => 0b1010 @ d @ s @ 0b0
    imm {d: AluOut}, {s: i5} => 0b01 @ d @ s
    imm {d: register}, {val: i5} => 0b01 @ 0b0 @ val @ asm { mov {d}, a }
    imm M, {val: i16} => 0b11000000 @ val`16
    inc XY => 0b10110000
}
