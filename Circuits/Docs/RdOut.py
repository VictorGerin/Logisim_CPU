class Decoder:
    INPUTS = [
        ("Imm", 4),
        ("RamData", 4),
        ("Rd", 4),
        ("RamOpe", 1),
        ("Op2IsImm", 1),
    ]
    OUTPUTS = [("RdOut", 4)]

    def compute(self, **kwargs):
        Imm = kwargs["Imm"]
        RamData = kwargs["RamData"]
        Rd = kwargs["Rd"]

        
        RamOpe = kwargs["RamOpe"]
        Op2IsImm = kwargs["Op2IsImm"]

        RdOut = 0

        if Op2IsImm == 0:
            RdOut = Rd
        elif RamOpe == 1:
            RdOut = RamData
        else:
            RdOut = Imm


        return {"RdOut": RdOut}