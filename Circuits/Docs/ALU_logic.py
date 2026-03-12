class Decoder:
    INPUTS = [
        ("A", 4),
        ("B", 4),
        ("L", 4)
    ]
    OUTPUTS = [("Z", 4)]

    def compute(self, **kwargs):
        A = kwargs["A"]
        B = kwargs["B"]
        L = kwargs["L"]
        Z = None

        if L == 0:
            Z = 0
        elif L == 1:
            Z = ~(A | B)
        elif L == 2:
            Z = ~A & B
        elif L == 3:
            Z = ~A
        elif L == 4:
            Z = A & ~B
        elif L == 5:
            Z = ~B
        elif L == 6:
            Z = A ^ B
        elif L == 7:
            Z = ~(A & B)
        elif L == 8:
            Z = A & B
        elif L == 9:
            Z = ~(A ^ B)
        elif L == 10:
            Z = B
        elif L == 11:
            Z = ~A | B
        elif L == 12:
            Z = A
        elif L == 13:
            Z = A | ~B
        elif L == 14:
            Z = A | B
        elif L == 15:
            Z = 15

        return {"Z": Z}