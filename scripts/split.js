#!/usr/bin/env node

const stream = require('stream');
const fs = require("fs");

let replase_dash_to_x = true;

async function main()
{
    let file = process.argv[2];
    let varIndex = process.argv[3];


    if((!file || !varIndex) && (!Number.isInteger(parseInt(file)) || varIndex)) {
        console.log("Usage: node separate_espresso_var.js <file> <index>");
        console.log("Usage: node separate_espresso_var.js <index>");
        return;
    }

    if(!varIndex) {
        varIndex = file;
        file = undefined;
    }

    if(file && !fs.existsSync(file)) {
        console.log("File not found");
        return;
    }
    

    let fileContent = fs.readFileSync(file || 0, "utf-8")
    .split(/\r?\n/g)
    .filter((line) => line.length && line.indexOf('.'))
    .map(line => {
        let [input, output] = line.split(' ');
        output = output.charAt(varIndex);
        return [input, output];
    })
    .filter((line) => line[1] === '1')
    .map((line) => {
        line = line.join(' ');
        if(replase_dash_to_x) {
            line = line.replaceAll(/-/g, 'x');
        }
        return line;
    })
    .join('\n');

    console.log(fileContent)

}

main();