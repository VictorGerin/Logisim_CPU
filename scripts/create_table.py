



qtdOutputBits = 5
qtdInputBits = 12


def process(input):
    i = []
    for index in range(qtdInputBits):
        i.append((input >> index) & 1)

    outputBits = [0 for x in range(qtdOutputBits)]

    outputBits[0] = (i[0] & i[1] & i[2] & i[3]) & 1

    outputBits[1] = (i[3] & i[4] & i[8] | \
                     i[2] &~i[4] & i[8] | \
                     i[1] & i[4] &~i[8] | \
                     i[0] &~i[4] &~i[8]) & 1

    outputBits[2] = (i[3] & i[5] & i[9] | \
                     i[2] &~i[5] & i[9] | \
                     i[1] & i[5] &~i[9] | \
                     i[0] &~i[5] &~i[9]) & 1

    outputBits[3] = (i[3] & i[6] & i[10] | \
                     i[2] &~i[6] & i[10] | \
                     i[1] & i[6] &~i[10] | \
                     i[0] &~i[6] &~i[10]) & 1

    outputBits[4] = (i[3] & i[7] & i[11] | \
                     i[2] &~i[7] & i[11] | \
                     i[1] & i[7] &~i[11] | \
                     i[0] &~i[7] &~i[11]) & 1

    outputVal = 0
    for i in range(qtdOutputBits):
        outputVal |= outputBits[i] << i

    return outputVal

def printTable(input, output):

    for i in range(2**qtdInputBits):
        print("{:>012b} | {:>05b}".format(input[i], output[i]))

    pass

def main():
    input = []
    for i in range(2**qtdInputBits):
        input.append(i)

    output = [process(i) for i in input]

    printTable(input, output)
    pass

if __name__ == '__main__':
    main()