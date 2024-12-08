#!/usr/bin/env python3



qtdOutputBits = 12
qtdInputBits = 8

def sliceToInt(slice, qtdBits):
    outputVal = 0
    for i in range(qtdBits):
        outputVal |= slice[i] << i
    return outputVal

def intToSlice(input, qtdBits):
    i = []
    for index in range(qtdBits):
        i.append((input >> index) & 1)
    return i

def process(input):
    # i = intToSlice(input, qtdOutputBits)

    centena = input // 100
    input = input % 100
    dezena = input // 10
    input = input % 10
    unidade = input // 1

    centena = [x for x in (intToSlice(centena, 4))]
    dezena = [x for x in (intToSlice(dezena, 4))]
    unidade = [x for x in (intToSlice(unidade, 4))]


    unidade.extend(dezena)
    unidade.extend(centena)


    return sliceToInt(unidade, qtdOutputBits)

def printTable(input, output):

    for i in range(2**qtdInputBits):
        print("{:>08b} | {:>012b}".format(int(input[i]), int(output[i])))

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