memorySize = 0x10000

R0 = 0x01`4
R1 = 0x02`4
R2 = 0x03`4
R3 = 0x04`4
R4 = 0x05`4
R5 = 0x06`4
R6 = 0x07`4

r0 = R0
r1 = R1
r2 = R2
r3 = R3
r4 = R4
r5 = R5
r6 = R6

#ruledef ; CPU instructions
{
    nop {val: u8} => val @ 0b0000_0000 ;
    nop => asm {
        nop 0
    }
    
    ;original ldi, losses 2bits of rd for the immediate value
    ;this function can only map the first 4 registers
    ldi {rd: u4}, {val: i8} => {
        assert(rd >=  0)
        assert(rd <=  3)
        
        val @       rd`2@ 0b00_0001
    }
    
    ;this function and the next 2 can map the other registers
    ldi {rd: u4}, {val: i8} => {
        assert(rd >=  4)
        assert(rd <=  7)
        
        val @       rd`2@ 0b01_0111
    }
    
    ldi {rd: u4}, {val: i8} => {
        assert(rd >=  8)
        assert(rd <=  11)
        
        val @       rd`2@ 0b01_1000
    }
    
    ldi {rd: u4}, {val: i8} => {
        assert(rd >=  12)
        assert(rd <=  15)
        
        val @       rd`2@ 0b01_1001
    }

    mv {rd: u4}, {rs: u4} =>        0b00 @ rs  @ rd  @ 0b00_0010
    jreli {val: i8} =>             (val - $)`8 @ 0`2 @ 0b00_0011
    jrelr {rs: u4} =>               0b00 @ rs  @ 0`4 @ 0b00_0100
    jabsr {rs: u4} =>               0b00 @ rs  @ 0`4 @ 0b00_0101

    add {rd: u4}, {rs: u4} =>       0b00 @ rs  @ rd  @ 0b00_0110
    addc {rd: u4}, {rs: u4} =>      0b00 @ rs  @ rd  @ 0b00_0111
    sub {rd: u4}, {rs: u4} =>       0b00 @ rs  @ rd  @ 0b00_1000
    subc {rd: u4}, {rs: u4} =>      0b00 @ rs  @ rd  @ 0b00_1001

    not {rd: u4} =>                 0b00 @ 0`4 @ rd  @ 0b00_1010
    neg {rd: u4} =>                 0b00 @ 0`4 @ rd  @ 0b00_1011
    shll {rd: u4} =>                0b00 @ 0`4 @ rd  @ 0b00_1100
    shlc {rd: u4} =>                0b00 @ 0`4 @ rd  @ 0b00_1101
    shrl {rd: u4} =>                0b00 @ 0`4 @ rd  @ 0b00_1110
    shrc {rd: u4} =>                0b00 @ 0`4 @ rd  @ 0b00_1111
    shra {rd: u4} =>                0b00 @ 0`4 @ rd  @ 0b01_0000
    and {rd: u4}, {rs: u4} =>       0b00 @ rs  @ rd  @ 0b01_0001
    or {rd: u4}, {rs: u4} =>        0b00 @ rs  @ rd  @ 0b01_0010
    xor {rd: u4}, {rs: u4} =>       0b00 @ rs  @ rd  @ 0b01_0011

    cmp {rd: u4}, {rs: u4} =>       0b00 @ rs  @ rd  @ 0b01_0100
    test {rd: u4}, {rs: u4} =>      0b00 @ rs  @ rd  @ 0b01_0101

    fswap {rd: u4} =>               0b00 @ 0`4 @ rd  @ 0b01_0110

    load {rd: u4}, {rs: u4} =>      0b00 @ rs  @ rd  @ 0b01_1110
    store {rd: u4}, {rs: u4} =>     0b00 @ rs  @ rd  @ 0b01_1111

    mvlpc {rd: u4} =>               0b00 @ 0`4 @ rd  @ 0b01_1100
    mvupc {rd: u4} =>               0b00 @ 0`4 @ rd  @ 0b01_1101
}

#ruledef ; CPU instructions Conditions movs
{
    cmv.true {rd: u4}, {rs: u4}  => 0b00 @ rs  @ rd  @ 0b10_0000
    cmv.false {rd: u4}, {rs: u4} => 0b00 @ rs  @ rd  @ 0b10_0001

    cmv.c {rd: u4}, {rs: u4} =>     0b00 @ rs  @ rd  @ 0b10_0010
    cmv.nc {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_0011
    cmv.z {rd: u4}, {rs: u4} =>     0b00 @ rs  @ rd  @ 0b10_0100
    cmv.nz {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_0101
    cmv.s {rd: u4}, {rs: u4} =>     0b00 @ rs  @ rd  @ 0b10_0110
    cmv.ns {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_0111
    cmv.o {rd: u4}, {rs: u4} =>     0b00 @ rs  @ rd  @ 0b10_1000
    cmv.no {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_1001

    cmv.eq {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_0100
    cmv.ne {rd: u4}, {rs: u4} =>    0b00 @ rs  @ rd  @ 0b10_0101

    cmv.uge {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_0010
    cmv.ult {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_0011
    cmv.ule {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1010
    cmv.ugt {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1011

    cmv.sge {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1101
    cmv.slt {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1100
    cmv.sle {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1110
    cmv.sgt {rd: u4}, {rs: u4} =>   0b00 @ rs  @ rd  @ 0b10_1111

}

#ruledef ; Derived CPU instructions
{
    cmp {rd: u4} => asm {
        cmp {rd}, {rd}
    }
    
    test {rd: u4} => asm {
        test {rd}, {rd}
    }

    halt => 0x00 @ 0`2 @ 0b00_0011

    zero => asm { ;zero all registers
        ldi r0, 0
        mv r1, r0
        mv r2, r1
        mv r3, r2
        mv r4, r3
        mv r5, r4
        mv r6, r5
    }

    reset => asm { ;reset the CPU to the initial program
        ldi R0, 0
        ldi R1, 0
        jabsr R0
    }

    ; ldi16 {rd: u4}, {val: i16} => {
    ;     ((val >> 0) & 0xFF)`8 @ ({rd} + 0)`4 @ 0b1000 @
    ;     ((val >> 8) & 0xFF)`8 @ ({rd} + 1)`4 @ 0b1000
    ; }

    ldi16 {rd: u4}, {val: i16} => asm {
        ldi ({rd} + 0), (({val} >> 0) & 0xFF)`8
        ldi ({rd} + 1), (({val} >> 8) & 0xFF)`8
    }

}