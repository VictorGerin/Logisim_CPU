#!/usr/bin/env node

const fs = require("fs");
const commandLineArgs = require('command-line-args')

const options = commandLineArgs([
    { name: 'file', alias: 'f', type: String, defaultValue: fs.openSync("/dev/stdin", "r")},
    { name: 'test_chip', alias: 'c', type: Number, defaultValue: null},
    { name: 'truth_table', alias: 't', type: Number, defaultValue: null }
])


String.prototype.replaceAt = function(index, replacement) {
    return this.substring(0, index) + replacement + this.substring(index + replacement.length);
}

function toJson(vec)
{
    let str = "";
    let i = 0;
    for (const vector of vec) {
        str += `<vector id="${(i++).toString().padStart(5,'0')}"> ${vector.split('').join(' ')} </vector>\n`;
    }
    return str
    // return JSON.stringify({
    //     ics: [
    //         {
    //             name: "teste",
    //             pins: 24,
    //             vcc: 5,
    //             vectors: vec
    //         }
    //     ]
    // }, null, 4);
}

mapTruthTable = [
    'STATE4', 'STATE3', 'STATE2', 'STATE1', 'STATE0',
    'Instru7', 'Instru6', 'Instru5', 'Instru4', 'Instru3', 'Instru2', 'Instru1', 'Instru0',
    'STATUS2', 'STATUS1', 'STATUS0',
]

mapGal = `
Instru7 Instru6 Instru5 Instru4 Instru3 Instru2  Instru1  Instru0 STATUS2 STATUS1 STATUS0 GND
STATE4  STATE3  STATE2  STATE1  STATE0  SelAdr2  SelAdr2b SelAdr0 Func2   Func1   Func0   VCC
`.split(/[ \n]{1,}/).filter(line => line)


async function metodo1(file, filterColumn) {

    let fileContent = fs.readFileSync(file, "utf-8")
        .split(/\r?\n/g)
        .map(line => line.indexOf('#') !== -1 ? line = line.slice(0, line.indexOf('#')) : line)
        .filter((line) => line.length && line.indexOf('~')).filter((_, index) => index)
        .map(line => line.replaceAll(' ', ''))
        .map(line => line.split(/\|/))
        
    return fileContent.map(line => {
        [input, output] = line;
        return [input, output[filterColumn]]
    })
}

async function main()
{
    // let file = process.argv[2] || fs.openSync("/dev/stdin", "r");
    // let file = './Circuits/Docs/Truth\ table_Complete.txt'
    // let outputIndex = 9
    // let galIndex = 17

    let file = options.file;
    let galIndex = options.test_chip;
    let outputIndex = options.truth_table;
    console.log(galIndex, outputIndex, file)

    let fullTable = []

    for (const caso of await metodo1(file, outputIndex)) {
        qtdVars = caso[0].split('').filter(a => a === '-').length;
        for (let i = 0; i < Math.pow(2, qtdVars); i++) {
            let num = i.toString(2).padStart(qtdVars, '0')

            let count = 0;
            let casoCopy = caso[0];
            
            for (const key in casoCopy) {
                if(casoCopy[key] !== '-') continue;
                
                
                casoCopy = casoCopy.replaceAt(parseInt(key), num[count++]);
                
            }
            fullTable.push([casoCopy, caso[1]])
        }
    }
    

    fullTable = fullTable.map(line => {
        let [input, val] = line;

        switch(val) {
            case '0': val = 'L'; break;
            case '1': val = 'H'; break;
            case '-': val = 'X'; break;
            default: val = 'X'; break;
        }

        let vector = 'X'.repeat(mapGal.length);

        for (let key = 0; key < input.length; key++) {
            galIndex = mapGal.indexOf(mapTruthTable[key])
            vector = vector.replaceAt(galIndex, input[key])
        }

        galIndex = mapGal.indexOf('GND')
        vector = vector.replaceAt(galIndex, 'G')

        galIndex = mapGal.indexOf('VCC')
        vector = vector.replaceAt(galIndex, 'V')
        
        vector = vector.replaceAt(galIndex, val)

        return vector;
    })

    console.log(toJson(fullTable))
    
}

main();
//console.log(mapGal.length)