class Decoder:
    INPUTS = [
        ("a", 3),
        ("b", 3)
    ]
    OUTPUTS = [("c", 5)]

    def compute(self, **kwargs):
        a = kwargs["a"]
        b = kwargs["b"]
        return {"c": a + b + 2}