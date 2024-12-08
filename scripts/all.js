#!/usr/bin/env node

const { execFile } = require("child_process");
const stream = require('stream');
const fs = require("fs");

const options = require('command-line-args')([
    { name: 'input', alias: 'i', type: String },
    { name: 'negate', alias: 'n', type: Boolean },
    { name: 'out', type: String, defaultValue: 'gal' },
    { name: 'folder_out', type: String, defaultValue: '' },

])


async function execFileAsync(command, input, args = []) {
    return new Promise((resolve, reject) => {
        let child = execFile(command, args, (err, stdout, stderr) => {
            if(err) {
                reject(err);
                return;
            }

            resolve(stdout);
        });

        let stdinStream = new stream.Readable();
        stdinStream.push(input);  // Add data to the internal queue for users of the stream to consume
        stdinStream.push(null);   // Signals the end of the stream (EOF)
        stdinStream.pipe(child.stdin);

    });
}

function getHeader(originalFileData) {

    let fileContent = originalFileData
    .split(/\r?\n/g)
    .map(line => line.indexOf('#') !== -1 ? line = line.slice(0, line.indexOf('#')) : line) //Remove os comentarios
    .filter((line, index) => line.length && line.indexOf('~'))
    .map(line => line.split(/\|/))[0]
    .map(header => {
        return header.trim().split(/ +/).map(variable => {

            let match = variable.match(/(?<name>\w+)(\[(?<msb>\d+)\.\.(?<lsb>\d+)\])?/);

            if(!match.groups.msb) {
                return [match.groups.name]
            }

            let arr = []
            for(let i = match.groups.msb; i >= match.groups.lsb; i--) {
                arr.push(`${match.groups.name}_${i}`)
            }

            return arr;
        }).flat()
    })

    return fileContent
}

async function outputGal(otimmazed_data, input, output)
{

    let bigestOutputName = output.reduce(function (a, b) {
        return a.length > b.length ? a : b;
    });

    let eq_sing = " = ";
    let padding = (bigestOutputName + eq_sing).length;

    for(let i = 0; i < output.length; i++) {

        let splited = await execFileAsync(`./scripts/split.js`, otimmazed_data, [ i ]);

        let gen_eq_args = ['--stdin', '--map', ...input];
        if(options.negate) {
            gen_eq_args.push('--negate')
        }

        let eq = (await execFileAsync(`./scripts/gen_eq.js`, splited, gen_eq_args))
            .split('\n')
            .map(line => ''.padStart(padding) + line) //adiciona a cada linha um padding
            .join('\n')
            .substring(padding); //remove da primeira linha o padding pois o noma da variavel ja esta la
        
        console.log(`${output[i]} termo de protudo qtd: ${eq.split('\n').length - 1}`);
        console.log(`${`${output[i]}${eq_sing}`.padEnd(padding)}${eq}`);
    }
}

async function outputLogisimPLA(otimmazed_data, input, output) {

    for(let i = 0; i < output.length; i++) {
        let splited = await execFileAsync(`./scripts/split.js`, otimmazed_data, [ i ]);

        if(options.folder_out) {
            fs.writeFileSync(`${options.folder_out}/${output[i]}.txt`, splited);
        } else {
            console.log(output[i]);
            console.log(splited);
        }
    }
}

async function outputLogisimPLA2(otimmazed_data, input, output)
{
//     let arrAnd = []
//     let arrOr = []

//     let offetY = 0;
//     let outputPrint = () => {
//         let outputString = `
// <comp lib="10" loc="(0,${offetY += 60})" name="PlaRom">
//     <a name="Contents" val="${arrAnd.join(' ') + " " + arrOr.join(' ')}"/>
//     <a name="and" val="${arrAnd.length}"/>
//     <a name="inputs" val="${input.length}"/>
//     <a name="outputs" val="${output.length}"/>
// </comp>`.trimStart()
                
//         console.log(outputString)

//         arrAnd = []
//         arrOr = []
//     }

    let arrAnd = []
    for(let i = 0; i < output.length; i++) {
        let splited = await execFileAsync(`./scripts/split.js`, otimmazed_data, [ i ]);

        let dictTranslate = {
            'x': '0',
            '0': '1',
            '1': '2'
        }

        let inputLines = splited.split(/\r?\n/g)
        .filter((line) => line.length)
        .map(line => line.split(' ')[0]
                        .split('')
                        .map(char => dictTranslate[char])
                        .join(' ')
        )

        arrAnd.push({
            inputs: inputLines,
            output: output[i]
        })

    }
    

    let groupBySize = arrAnd.reduce(
        (acc, current) => {
            let qtd = acc[acc.length - 1].reduce((sumQtd, output) => {
                return sumQtd + output.inputs.length;
            }, 0)

            if(qtd + current.inputs.length > 32) {
                acc.push([]);
            }

            acc[acc.length - 1].push(current);
            return acc;
        }, [ [] ]
    )

    let offetY = 0;
    for (const pla_group of groupBySize) {

        
        let arrAndFinal = pla_group.map((g) => g.inputs).flat()

        
        // arrOr.push(...Array(arrAndFinal.length).fill(outputPartten))
        let arrOr = pla_group.map((g, i) => {
            let outputPartten = ('0 '.repeat(i) + '1 ' + '0 '.repeat(pla_group.length - i - 1)).trimEnd();
            return Array(g.inputs.length).fill(outputPartten)
        }).flat();
        

        let outputString = `
<comp lib="10" loc="(0,${offetY += 60})" name="PlaRom">
    <a name="Contents" val="${arrAndFinal.join(' ') + " " + arrOr.join(' ')}"/>
    <a name="and" val="${arrAndFinal.length}"/>
    <a name="inputs" val="${input.length}"/>
    <a name="outputs" val="${pla_group.length}"/>
</comp>`.trimStart()

        console.log(outputString)
        
    }

    

    // outputPrint();
}

async function main()
{
    let fileData = fs.readFileSync(options.input, "utf-8")
    
    let [input, output] = getHeader(fileData);
    let otimmazed_data = await execFileAsync(`./scripts/log_espresso.js`, fileData);

    if(options.out === "gal") {
        await outputGal(otimmazed_data, input, output);
    } else if(options.out === "logisim_pla") {
        await outputLogisimPLA(otimmazed_data, input, output)
    } else if(options.out === "teste")
    {
        await outputLogisimPLA2(otimmazed_data, input, output)
    }

}

main();