"use strict";
// Project policy only. Packaging and platform adaptation belong to Tools/Build.
const path=require('node:path'),fs=require('node:fs');
const engineRoot=path.resolve(process.env.HE_ENGINE_ROOT || path.join(__dirname,'../..'));
const {exportWeChatGame}=require(path.join(engineRoot,'Tools/Build/ExportWeChatGame.cjs'));
const {resolveWeChatConfig}=require('./WeChatConfig.cjs');
async function main(){
    const [input,managed,output]=process.argv.slice(2);
    if(!input||!managed||!output)throw Error('Usage: ExportWeChat.cjs content-directory managed-framework-directory output-directory');
    const config=resolveWeChatConfig(path.resolve(__dirname,'..'));
    const catalog=JSON.parse(fs.readFileSync(path.join(input,'catalog.json'))),manifest=JSON.parse(fs.readFileSync(path.join(input,'content-manifest.json')));
    const names=Object.keys(manifest.assets),startup=new Set(['catalog.json','rendering.json','content-manifest.json',catalog.scenePath]);
    // Bounds lookup needs metadata, not every mesh's vertex buffer or animation.
    for(const name of names)if(name.endsWith('.hmesh'))startup.add(name);
    const pending=new Set(['Assets/UI/Backgrounds/starbloom_loading_bg.png','Assets/UI/Backgrounds/starbloom_title_bg.png',catalog.audio.music_menu,catalog.audio.ui_click]);
    for(const item of [...catalog.characters,...catalog.weapons,...catalog.tomes,...catalog.trinkets,...catalog.metaPowerUps,...(catalog.power_ups||[])])if(item.icon)pending.add(item.icon);
    const first=catalog.characters[0],folder=first.mesh.slice(0,first.mesh.lastIndexOf('/')+1),animations=names.filter(name=>name.startsWith(folder)&&name.endsWith('.hanim'));
    pending.add(first.mesh);pending.add(first.idle||animations.find(name=>/idle/i.test(name)));pending.add(animations.find(name=>/run|walk/i.test(name)));
    const visited=new Set();
    function collect(value){
        if(typeof value==='string'&&Object.hasOwn(manifest.assets,value.replaceAll('\\','/')))pending.add(value.replaceAll('\\','/'));
        else if(value&&typeof value==='object')for(const child of Object.values(value))collect(child);
    }
    while(pending.size){
        const name=pending.values().next().value;pending.delete(name);if(!name||visited.has(name))continue;
        if(!Object.hasOwn(manifest.assets,name))throw Error('Missing startup asset: '+name);
        visited.add(name);startup.add(name);
        if(/\.(hmesh|hmat|hskel|hanim|hanimctrl)$/.test(name))collect(JSON.parse(fs.readFileSync(path.join(input,name))));
    }
    const result=await exportWeChatGame({input,managed,output,config,
        entryPoint:path.resolve(__dirname,'../WeChat/game.js'),contentFiles:['catalog.json','rendering.json'],startupFiles:[...startup]});
    console.log(JSON.stringify(result));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
