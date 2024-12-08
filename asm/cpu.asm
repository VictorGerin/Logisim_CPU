








#subruledef  reg
{
    R0   => 0x01`4
    R1   => 0x02`4
    R2   => 0x03`4
    R3   => 0x04`4
    R4   => 0x05`4
    R5   => 0x06`4
    R6   => 0x07`4
}

#ruledef ; CPU instructions
{
    nop => 0b0000_0000_0000_0000
    ldi {rd: reg}, {val: i8} => val @ rd @ 0b1000
    mv {rd: reg}, {rs: reg} => 0b0000 @ rs @ rd @ 0b0000
    jreli {addr_rel: i16} => (addr_rel - $)`8 @ 0b0000_1001 ; jump to relative address, "$" is the current address
    jrelr {rs: reg} => 0b0000 @ rs @ 0b0000_0001
    jabsr {rs: reg} => 0b0000 @ rs @ 0b0000_0010
    add {rd: reg}, {rs: reg} => 0b0000 @ rs @ rd @ 0b0100
    addc {rd: reg}, {rs: reg} => 0b0001 @ rs @ rd @ 0b0100
    sub {rd: reg}, {rs: reg} => 0b0010 @ rs @ rd @ 0b0100
    subc {rd: reg}, {rs: reg} => 0b0011 @ rs @ rd @ 0b0100
    not {rd: reg} => 0b0100 @ 0b0000 @ rd @ 0b0100
    neg {rd: reg} => 0b0101 @ 0b0000 @ rd @ 0b0100

    shll  {rd: reg} => 0b0110 @ 0b0000 @ rd @ 0b0100
    shlc  {rd: reg} => 0b0111 @ 0b0000 @ rd @ 0b0100
    shrl  {rd: reg} => 0b1000 @ 0b0000 @ rd @ 0b0100
    shrc  {rd: reg} => 0b1001 @ 0b0000 @ rd @ 0b0100
    shra  {rd: reg} => 0b1010 @ 0b0000 @ rd @ 0b0100

    and {rd: reg}, {rs: reg} => 0b1101 @ rs @ rd @ 0b0100
    or {rd: reg}, {rs: reg} => 0b1110 @ rs @ rd @ 0b0100
    xor {rd: reg}, {rs: reg} => 0b1111 @ rs @ rd @ 0b0100
    
    cmp {rd: reg}, {rs: reg} => 0b0010 @ rs @ 0b1 @ rd`3 @ 0b0100
    test {rd: reg}, {rs: reg} => 0b1101 @ rs @ 0b1 @ rd`3 @ 0b0100

    fswap  {rd: reg} => 0b1100 @ 0b0000 @ rd @ 0b0100

}

#ruledef ; CPU instructions Conditions movs
{
    cmv.true {rd: reg}, {rs: reg}  => 0b0000 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.false {rd: reg}, {rs: reg} => 0b0001 @ 0b1 @ rs`3 @ rd @ 0b0100

    cmv.c {rd: reg}, {rs: reg} => 0b0010 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.nc {rd: reg}, {rs: reg} => 0b0011 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.z {rd: reg}, {rs: reg} => 0b0100 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.nz {rd: reg}, {rs: reg} => 0b0101 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.s {rd: reg}, {rs: reg} => 0b0110 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.ns {rd: reg}, {rs: reg} => 0b0111 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.o {rd: reg}, {rs: reg}  => 0b1000 @ 0b1 @ rs`3 @ rd @ 0b0100

    cmv.no {rd: reg}, {rs: reg} => 0b1001 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.eq {rd: reg}, {rs: reg} => 0b0100 @ 0b1 @ rs`3 @ rd @ 0b0100
    cmv.ne {rd: reg}, {rs: reg} => 0b0101 @ 0b1 @ rs`3 @ rd @ 0b0100

    cmv.uge {rd: reg}, {rs: reg} => 0b0010 @ 0b1 @ rs`3 @ rd @ 0b0100 ; unsigned greater or equal
    cmv.ult {rd: reg}, {rs: reg} => 0b0011 @ 0b1 @ rs`3 @ rd @ 0b0100 ; unsigned less than
    cmv.ule {rd: reg}, {rs: reg} => 0b1010 @ 0b1 @ rs`3 @ rd @ 0b0100 ; unsigned less or equal
    cmv.ugt {rd: reg}, {rs: reg} => 0b1011 @ 0b1 @ rs`3 @ rd @ 0b0100 ; unsigned greater than

    cmv.slt {rd: reg}, {rs: reg} => 0b1100 @ 0b1 @ rs`3 @ rd @ 0b0100 ; signed less than
    cmv.sge {rd: reg}, {rs: reg} => 0b1101 @ 0b1 @ rs`3 @ rd @ 0b0100 ; signed greater or equal
    cmv.sle {rd: reg}, {rs: reg} => 0b1110 @ 0b1 @ rs`3 @ rd @ 0b0100 ; signed less or equal
    cmv.sgt {rd: reg}, {rs: reg} => 0b1111 @ 0b1 @ rs`3 @ rd @ 0b0100 ; signed greater than
}

#ruledef ; Derived CPU instructions
{
    cmp {rd: reg} => asm {
        cmp {rd}, {rd}
    }
    
    test {rd: reg} => asm {
        test {rd}, {rd}
    }

    halt => asm {; same as jump to self, "$" is the current address
        jreli $
    }

    zero => asm { ;zero all registers
        ldi R0, 0
        ldi R1, 0
        ldi R2, 0
        ldi R3, 0
        ldi R4, 0
        ldi R5, 0
        ldi R6, 0
        fswap R0
        ldi R0, 0
    }

    reset => asm { ;reset the CPU to the initial program
        ldi R0, 0
        ldi R1, 0
        jabsr R0
    }
}