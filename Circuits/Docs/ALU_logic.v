module ALU_logic (
    input  [3:0] A,
    input  [3:0] B,
    input  [3:0] L,
    output [3:0] Z
);
    // For each bit i, {A[i], B[i]} is the 2-bit address into L.
    // Z[i] = L[{A[i], B[i]}]  (4:1 mux per bit, L as truth table)
    genvar i;
    generate
        for (i = 0; i < 4; i = i + 1) begin : bit_mux
            assign Z[i] = L[{B[i], A[i]}];
        end
    endgenerate
endmodule
