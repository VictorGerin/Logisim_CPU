# Projeto processador

Esse é meu projeto de um processador simples

----------

### Run minipro on Windows WSL

https://learn.microsoft.com/en-us/windows/wsl/connect-usb

https://github.com/dorssel/usbipd-win/releases

No windows rode `usbipd list` para pegar o ID do dispositivo USB
ainda no windows rode `usbipd bind --busid <busid>` para capturar o dispositivo pelo usbipd
depois `usbipd attach --wsl --busid <busid>` para disponilizar para o WSL

### Scripts folder

#### all.js

Principal script que transforma um truthtable do logisim em uma serie de equações para o galasm
usando o mesmo nome de variaveis definidas no logisim

#### generate_boolean_eq.js | gen_eq.js

Cria Galasm equeção de acordo com a variável map e negate
Var map:
    Array que mapeia a coluna para o nome dado no array

Negate:
    Serve para negar todas as entradas (util para quando a entrada está invertida por causa de um pullup)

#### logisim_truth_to_espresso.js | log_espresso.js

Converte logisim truth table numa tabela que o espresso possa executar e executa o mesmo

`cat ./Circuits/Docs/Truth\ table_Complete.txt | node ./scripts/logisim_truth_to_espresso.js`

#### separate_espresso_var.js | split.js

pega o resultado do espresso e separa a variável de saida indicada pelo index

replase_dash_to_x:
    pode ser usado para trocar '-' pelo x util para gerar PLA no logsim

`cat ./Circuits/Docs/Truth\ table_Complete.txt | node ./scripts/logisim_truth_to_espresso.js | node ./scripts/separate_espresso_var.js 0`

### Prog folder

#### xgpro-logic

Programa usado para converter .toml, .json ou .xml em um formato que possa ser importado pelo xgpro para criar vetores de teste, consulte exemplo de como fazer

#### Galasm

Programa usado par a "Compilar" programas pld (gal) para gerar .jed

o resultado .jed é usado diretamente no Xgpro (programador universal)

```pld
GAL22V10 ; modelo do Chip
StateMachine ; Nome do projeto

;Definição dos pinos
;1    2     3     4     5     6     7     8     9     10    11   12
Clock I0    I1    I2    I3    I4    I5    I6    I7    I8    I9   GND
I11   O0    O1    O2    O3    O4    NC    O5    O6    O7    O8   VCC
;13   14    15    16    17    18    19    20    21    22    23   24

;Exemplo basico de circuito combinacional
O1 = I2 + I3


;Clock sempre deve ser o Pino 1
;AR 'Async Reset' para todos os FlipFlop D
AR = I0
;.R Usa esse Pino como um registrador
O0.R = I1


DESCRIPTION
Descrição do projeto text livre
```

Forma de usar
`
galette prog.pld
`

#### Espresso-logic


Usado para simplificar tabelas verdade

Vale notar que cada linha é um conjunto de produtos com o resultado final
sendo a soma de todas as linhas

##### Exemplo:
###### input
.i 4
.o 3
0000  000
0001  001
0010  010
0011  011
0100  001
0101  010
0110  011
0111  100
1000  010
1001  011
1010  100
1011  101
1100  011
1101  100
1110  101
1111  110

###### output

.i 4
.o 3
.p 11
0101 010
1111 010
1-00 010
0-10 010
100- 010
001- 010
-111 100
11-1 100
-1-0 001
-0-1 001
1-1- 100
.e