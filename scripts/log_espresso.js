#!/usr/bin/env node

const { execFile } = require("child_process");

const stream = require('stream');
const fs = require("fs");

async function execFileAsync(command, input) {
    return new Promise((resolve, reject) => {
        let child = execFile(command, [], (err, stdout, stderr) => {
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

async function execEspresso(data) {
    return execFileAsync(`./Progs/espresso-logic/bin/espresso`, data);
}

async function metodo1(file) {

    let fileContent = fs.readFileSync(0, "utf-8")
        .split(/\r?\n/g)
        .map(line => line.indexOf('#') !== -1 ? line = line.slice(0, line.indexOf('#')) : line) //Remove os comentarios
        .filter((line) => line.length && line.indexOf('~'))
        .filter((_, index) => index) //Remove a primeira linha
        .map(line => line.replaceAll(' ', '')) //remove os espaços
        .map(line => line.split(/\|/))
        
    
    let countInput = fileContent[0][0].length;
    let countOutput = fileContent[0][1].length;

    fileContent = fileContent.map(line => line.join(' ')).join('\n');

    fileContent =
`.i ${countInput}
.o ${countOutput}
${fileContent}`

    return await execEspresso(fileContent);
}

async function main()
{
    let file = process.argv[2];

    console.log(await metodo1(file))
}

main();