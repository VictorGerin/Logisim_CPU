class Decoder:
    INPUTS = [
        ("flagsCarry", 1),
        ("flagsZero", 1),
        ("flagsOutSign", 1),
        ("flagsOverFlow", 1),
        ("AluOp", 4),
    ]
    OUTPUTS = [("condMatch", 1)]

    def compute(self, **kwargs):
        flagsCarry = kwargs["flagsCarry"]
        flagsZero = kwargs["flagsZero"]
        flagsOutSign = kwargs["flagsOutSign"]
        flagsOverFlow = kwargs["flagsOverFlow"]
        AluOp = kwargs["AluOp"]

        
        if AluOp >> 1 == 1:
            condMatch = flagsCarry
        elif AluOp >> 1 == 2:
            condMatch = flagsZero
        elif AluOp >> 1 == 3:
            condMatch = flagsOutSign
        elif AluOp >> 1 == 4:
            condMatch = flagsOverFlow
        elif AluOp >> 1 == 5:
            condMatch = flagsZero | ~flagsCarry
        elif AluOp >> 1 == 6:
            condMatch = flagsOutSign ^ flagsOverFlow
        elif AluOp >> 1 == 7:
            condMatch = (flagsOutSign ^ flagsOverFlow) | flagsZero
        else:
            condMatch = 0



        return {"condMatch": condMatch ^ (AluOp & 1)}