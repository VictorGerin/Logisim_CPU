#!/usr/bin/env node

const stream = require('stream');
const fs = require("fs");


const options = require('command-line-args')([
    { name: 'map', alias: 'm', type: String, multiple: true },
    { name: 'negate', alias: 'n', type: Boolean },
    { name: 'stdin', type: Boolean },
    { name: 'input', alias: 'i', type: String },

])


async function main()
{
    
    let map = options.map.map((a) => `${a} `)
    let file = options.stdin ? 0 : options.input;


    let fileContent = fs.readFileSync(file , "utf-8")
    .split(/\r?\n/g)
    .filter((line) => line.length)
    .map(line => line.split(' ')[0].split(''))
    .map(line => {

        let firstHasprinted = false;
        for(let i = 0; i < line.length; i++) {
            let hasValue = false;
            if(line[i] === '1') {
                hasValue = true;
                line[i] = `${options.negate ? '/' : ' '}${map[i]}`;
            } else if (line[i] === '0'){
                hasValue = true;
                line[i] = `${options.negate ? ' ' : '/'}${map[i]}`;
            } else {
                line[i] = ' '.repeat(map[i].length + 2);
            }

            if(hasValue && firstHasprinted) {
                line[i] = `*${line[i]}`;
            }
            if(hasValue) {
                firstHasprinted = true;
            }
        }

        return line.filter(obj => obj).join('');
    }).join('+\n');

    console.log(fileContent)

}

main();