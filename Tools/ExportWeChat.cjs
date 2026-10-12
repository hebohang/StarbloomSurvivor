"use strict";
// Project policy only. Packaging and platform adaptation belong to Tools/Build.
const path=require('node:path');
const engineRoot=path.resolve(process.env.HE_ENGINE_ROOT || path.join(__dirname,'../..'));
const {exportWeChatGame}=require(path.join(engineRoot,'Tools/Build/ExportWeChatGame.cjs'));
const config=require('../Config/WeChat.json');
async function main(){
    const [input,managed,output]=process.argv.slice(2);
    if(!input||!managed||!output)throw Error('Usage: ExportWeChat.cjs content-directory managed-framework-directory output-directory');
    const result=await exportWeChatGame({input,managed,output,config,
        entryPoint:path.resolve(__dirname,'../WeChat/game.js'),contentFiles:['catalog.json','rendering.json']});
    console.log(JSON.stringify(result));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
