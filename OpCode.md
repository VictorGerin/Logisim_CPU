        OpCode					15    bits      0

00 |    nop				|	-------- --000000


Because my implementation overlaps imm values with rd addr
4 differents structions is used to generate the upper 2bits of RD register

01 |    ldi0 rd, imm			|	iiiiiiii dd000001
44 |    ldi1 rd, imm			|	iiiiiiii dd010111
45 |    ldi2 rd, imm			|	iiiiiiii dd011000
46 |    ldi3 rd, imm			|	iiiiiiii dd011001

02 |    mv rd, rs			|	--ssssdd dd000010
03 |    jreli +imm			|	iiiiiiii --000011
04 |    jrelr rs			|	--ssss-- --000100
05 |    jabsr rs16			|	--ssss-- --000101

06 |    add rd, rs			|	--ssssdd dd000110
07 |    addc rd, rs			|	--ssssdd dd000111
08 |    sub rd, rs			|	--ssssdd dd001000
09 |    subc rd, rs			|	--ssssdd dd001001
10 |    not rd				|	------dd dd001010
11 |    neg rd				|	------dd dd001011
12 |    shll rd				|	------dd dd001100
13 |    shlc rd				|	------dd dd001101
14 |    shrl rd				|	------dd dd001110
15 |    shrc rd				|	------dd dd001111
16 |    shra rd				|	------dd dd010000
17 |    and rd, rs			|	--ssssdd dd010001
18 |    or rd, rs			|	--ssssdd dd010010
19 |    xor rd, rs			|	--ssssdd dd010011

20 |    cmp rd, rs			|	--ssssdd dd010100
21 |    test rd, rs			|	--ssssdd dd010101

22 |    fswap rd			|	------dd dd010110

24 |    cmv.true rd, rs 	        |	--ssssdd dd100000
25 |    cmv.false rd, rs	        |	--ssssdd dd100001

26 |    cmv.c rd, rs    	        |	--ssssdd dd100010
27 |    cmv.nc rd, rs    	        |	--ssssdd dd100011
28 |    cmv.z rd, rs    	        |	--ssssdd dd100100
29 |    cmv.nz rd, rs    	        |	--ssssdd dd100101
30 |    cmv.s rd, rs    	        |	--ssssdd dd100110
31 |    cmv.ns rd, rs    	        |	--ssssdd dd100111
32 |    cmv.o rd, rs    	        |	--ssssdd dd101000
33 |    cmv.no rd, rs    	        |	--ssssdd dd101001

34 |    cmv.eq rd, rs    	        |	--ssssdd dd100100
35 |    cmv.ne rd, rs    	        |	--ssssdd dd100101

36 |    cmv.uge rd, rs    	        |	--ssssdd dd100010
37 |    cmv.ult rd, rs    	        |	--ssssdd dd100011
38 |    cmv.ule rd, rs    	        |	--ssssdd dd101010
39 |    cmv.ugt rd, rs    	        |	--ssssdd dd101011

40 |    cmv.sge rd, rs    	        |	--ssssdd dd101101
41 |    cmv.slt rd, rs    	        |	--ssssdd dd101100
42 |    cmv.sle rd, rs    	        |	--ssssdd dd101110
43 |    cmv.sgt rd, rs    	        |	--ssssdd dd101111
