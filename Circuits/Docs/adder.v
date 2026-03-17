module adder (
    input  [2:0] A,
    input  [2:0] B,
    output [3:0] S
);
    assign S = A + B;
endmodule
