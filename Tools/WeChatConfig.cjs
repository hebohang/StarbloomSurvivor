'use strict';
const fs=require('node:fs'),path=require('node:path');

function resolveWeChatConfig(projectRoot,environment=process.env){
    const shared=JSON.parse(fs.readFileSync(path.join(projectRoot,'Config/WeChat.json'),'utf8'));
    if(shared.appid)throw Error('Keep Config/WeChat.json appid empty; use Config/WeChat.local.json or HE_WECHAT_APPID.');
    let appid=environment.HE_WECHAT_APPID?.trim();
    const local=path.join(projectRoot,'Config/WeChat.local.json');
    if(!appid&&fs.existsSync(local))appid=JSON.parse(fs.readFileSync(local,'utf8')).appid;
    if(typeof appid!=='string'||!/^wx[0-9a-f]{16}$/.test(appid))
        throw Error('Set a valid appid in ignored Config/WeChat.local.json or HE_WECHAT_APPID before exporting.');
    return {...shared,appid};
}
module.exports={resolveWeChatConfig};
