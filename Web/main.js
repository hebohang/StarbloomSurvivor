import { dotnet } from './_framework/dotnet.js';
import { SurvivorRenderer } from './renderer.js';
import { VirtualJoystick } from './engine/Input/VirtualJoystick.js';
import { BrowserInput } from './engine/Input/BrowserInput.js';
import { bindBrowserLifecycle,toggleFullscreen } from './engine/BrowserLifecycle.js';
import { createBrowserRenderer,recoverBrowserRenderer } from './engine/BrowserRenderer.js';
import { AudioBank } from './engine/AudioBank.js';
import { HuiDom } from './engine/HuiDom.js';
import { ManagedGameSession } from './engine/ManagedGameSession.js';
const loading=document.getElementById('loading'),progress=document.getElementById('progress'),ui=document.getElementById('ui'),toast=document.getElementById('toast');
const catalog=await fetch('./catalog.json').then(r=>{if(!r.ok)throw Error('游戏内容未导出');return r.json();});
const audio=new AudioBank(catalog.audio);
const pauseResponse=await fetch(catalog.sharedUi.pause);
if(!pauseResponse.ok)throw Error('Shared pause UI is missing');
const pauseUi=new HuiDom(await pauseResponse.json(),element=>command(element));
const rendererPreference=new URLSearchParams(location.search).get('renderer')||'auto';
let renderer=await createBrowserRenderer(SurvivorRenderer,document.getElementById('game'),{backend:rendererPreference});
try{await renderer.initialize(catalog,text=>progress.textContent=text);}
catch(error){if(!renderer.graphics||rendererPreference!=='auto')throw error;renderer=await recoverBrowserRenderer(SurvivorRenderer,renderer,r=>r.initialize(catalog,text=>progress.textContent=text),error);}
progress.textContent='正在启动 C# 游戏运行时…';
const runtime=await dotnet.create(),exports=await runtime.getAssemblyExports(runtime.getConfig().mainAssemblyName),game=exports.Program;
const saveKey='HEngine.StarbloomSurvivor.CSharp.v4';
const session=new ManagedGameSession(game,{get:key=>localStorage.getItem(key),set:(key,value)=>localStorage.setItem(key,value)},saveKey);
let joystick;
let snapshot,tab='characters',previousMode='',last=performance.now(),lastUi=0,lastMessage='',lastHtml='',running=true;
let input;let touchX=0,touchZ=0;
snapshot=session.initialize(catalog);
if(session.restoredFromBackup)toast.textContent='已从备份恢复存档';
snapshot=session.command('configureInterestRadius',String(renderer.interest.enabled?renderer.interest.radius+renderer.interest.padding:0));
const byId=new Map([...catalog.characters,...catalog.weapons,...catalog.tomes,...catalog.trinkets,...catalog.evolutions].map(x=>[x.id,x]));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const name=item=>item?.name?.zh_cn||item?.title?.zh_cn||item?.id||'';
const icon=id=>{const i=byId.get(id);return i?.icon?`<img src="${esc(i.icon)}" alt="">`:'';};
function persist(){session.persist();}
function resetInput(){input?.reset();touchX=touchZ=0;joystick?.reset();}
function command(action,value=''){audio.unlock().then(()=>audio.play('ui_click')).catch(console.error);try{snapshot=session.command(action,value);renderUi(true);}catch(error){toast.textContent=error.message;console.error(error);}}
function renderUi(force=false){
    if(!force&&performance.now()-lastUi<150)return;lastUi=performance.now();
    if(snapshot.mode!==previousMode)resetInput();
    let html='';
    pauseUi.show(snapshot.mode==='paused');
    const s=snapshot,menu=s.mode==='menu';document.body.classList.toggle('menu',menu);
    const touchControls=s.mode==='playing'&&matchMedia('(any-pointer:coarse)').matches;
    document.getElementById('joystick').hidden=!touchControls;document.getElementById('jump').hidden=!touchControls;
    if(menu){
        let body='';
        if(tab==='characters')body=`<div class="cards character-cards">${catalog.characters.map(c=>{const owned=s.profile.owned.characters.includes(c.id);return `<button data-action="${owned?'selectCharacter':'buy'}" data-value="${esc(c.id)}" class="${s.character===c.id?'selected':''}">${icon(c.id)}${esc(name(c))}<small>${owned?'已拥有':`${c.price} 金币 · 解锁后购买`}</small></button>`;}).join('')}</div>`;
        if(tab==='equipment')body=`<p class="hint">已拥有的武器与绘本将进入升级候选池。</p><div class="cards">${[...catalog.weapons,...catalog.tomes,...catalog.trinkets].map(c=>{const group=catalog.weapons.includes(c)?'weapons':catalog.tomes.includes(c)?'tomes':'trinkets',owned=s.profile.owned[group].includes(c.id);return `<button data-action="${owned?'togglePool':'buy'}" data-value="${esc(c.id)}">${icon(c.id)}${esc(name(c))}<small>${owned?(s.profile.poolDisabled[group].includes(c.id)?'已停用 · 点击启用':'已启用 · 点击停用'):'解锁后购买'}</small></button>`;}).join('')}</div>`;
        if(tab==='powers')body=catalog.metaPowerUps.map(p=>{const level=s.profile.powerUps[p.id]||0;const entry=catalog.power_ups.find(x=>x.id===p.id);return `<div class="list-row"><div class="copy">${esc(name(entry)||p.id)}<p>等级 ${level} / ${p.maxLevel}</p></div><button data-action="power" data-value="${esc(p.id)}" ${level>=p.maxLevel?'disabled':''}>${p.prices[level]??'已满级'} 金币</button></div>`;}).join('');
        if(tab==='quests')body=catalog.quests.filter(q=>!q.hiddenUntil||s.profile.completedQuests.includes(q.hiddenUntil)).map(q=>`<div class="list-row"><div class="copy">${esc(name(q))}<p>${s.profile.completedQuests.includes(q.id)?'✓ 已完成':`${Math.floor(s.profile.questProgress[q.id]||0)} / ${q.target}`} · 奖励 ${q.rewardGold} 金币</p></div></div>`).join('');
        if(tab==='settings')body=`<p>冒险难度</p><select id="difficulty">${catalog.difficulties.map(d=>`<option value="${esc(d.id)}" ${s.profile.selectedDifficulty===d.id?'selected':''}>${esc(d.id)}</option>`).join('')}</select><p>武器槽数量</p><select id="weaponSlots">${[3,4,5,6].map(n=>`<option value="${n}" ${s.profile.selectedWeaponSlotLimit===n?'selected':''} ${n>3+(s.profile.powerUps.meta_weapon_slots||0)?'disabled':''}>${n} 个武器槽${n>3+(s.profile.powerUps.meta_weapon_slots||0)?'（未解锁）':''}</option>`).join('')}</select><p>挑战</p><div class="cards">${catalog.challenges.map(c=>`<button data-action="challenge" data-value="${esc(c.id)}" class="${s.profile.selectedChallenges.includes(c.id)?'selected':''}">${esc(name(c)||c.id)}</button>`).join('')}</div><p class="hint">存档保存在此浏览器中。</p>`;
        html=`<section class="menu-panel"><div class="eyebrow">小树保卫者</div><h1>小树保卫者</h1><div class="wallet"><span>✦ ${Math.floor(s.profile.walletGold)} 金币</span><span>冒险 ${s.profile.career.runs} 次</span></div><nav class="tabs">${[['characters','角色'],['equipment','装备'],['powers','强化'],['quests','任务'],['settings','设置']].map(([id,label])=>`<button data-tab="${id}" class="${tab===id?'selected':''}">${label}</button>`).join('')}</nav><div class="scroll">${body}</div><div class="actions"><button class="primary" data-action="start">开始冒险 →</button></div><p class="hint">WASD / 方向键移动 · 右键拖动视角 · 空格跳跃 · Esc 暂停<br>触屏：左侧摇杆移动 · 右侧滑动视角 · 跳跃按钮</p></section>`;
    }else{
        const minutes=Math.floor(s.elapsed/60),seconds=Math.floor(s.elapsed%60).toString().padStart(2,'0');
        html=`<div class="hud"><div class="stats">生命 ${Math.ceil(s.health)} / ${Math.ceil(s.maxHealth)}<div class="meter"><i style="width:${Math.max(0,s.health/s.maxHealth*100)}%"></i></div>等级 ${s.level}<div class="meter xp"><i style="width:${Math.min(100,s.xp/s.xpRequired*100)}%"></i></div></div><div class="clock">${minutes}:${seconds}<small>击败 ${s.kills}</small></div><button data-action="pause">暂停 Ⅱ</button></div><div class="loadout">${Object.entries(s.weapons).filter(([id,l])=>l>0).map(([id,l])=>`<span>${icon(id)}<b>Lv.${l}</b></span>`).join('')}</div>`;
        const regionNames={star:'北方 · 星光裂隙',thunder:'西方 · 雷鸣圣坛',water:'南方 · 水域花园',wind:'东方 · 风之高地'};
        html+=`<section class="objectives stats"><b>${s.objective==='BOSS_READY'?'返回中央星台':s.objective==='BOSS_ACTIVE'?'击败星龙':'激活四个区域'}</b>${s.regions.map(r=>`<div>${r.state==='ACTIVATED'?'✓':'◇'} ${regionNames[r.id]}<small>${r.state==='ASSAULT'?`${Math.floor(r.assault)} / 60 秒`:r.state==='OUTSIDE_GRACE'?'立即返回区域':r.state==='COOLDOWN'?`冷却 ${Math.ceil(r.cooldown)} 秒`:r.state==='ACTIVATED'?'已激活':`${Math.round(Math.hypot(r.x-s.x,r.z-s.z))} m`}</small></div>`).join('')}</section>`;
        if(s.mode==='upgrade')html+=`<div class="overlay"><div class="dialog upgrade"><div class="eyebrow">LEVEL ${s.level}</div><h2>选择你的星光力量</h2><div class="cards">${s.choices.map(c=>`<button data-action="upgrade" data-value="${esc(c.id)}">${icon(c.id)}${esc(name(byId.get(c.id))||({snack:'恢复生命',bonus:'金币奖励',spark:'星光冲击'}[c.id]))}<small>${c.nextLevel?'Lv.'+c.nextLevel:'即时奖励'}</small></button>`).join('')}</div><div class="actions"><button data-action="reroll" ${s.rerolls<=0?'disabled':''}>重抽 (${s.rerolls})</button><button data-action="skip" ${s.skips<=0?'disabled':''}>跳过 (${s.skips})</button></div></div></div>`;
        if(s.mode==='result')html+=`<div class="overlay"><div class="dialog"><h2>${esc(s.message)}</h2><p>存活 ${minutes} 分 ${seconds} 秒 · 等级 ${s.level} · 击败 ${s.kills}</p><p>金币 ${Math.floor(s.profile.walletGold)}</p><button class="primary" data-action="home">返回大厅</button></div></div>`;
    }
    if(lastHtml!==html){ui.innerHTML=html;lastHtml=html;}
    if(s.message&&s.message!==lastMessage){toast.textContent=s.message;lastMessage=s.message;setTimeout(()=>{if(toast.textContent===s.message)toast.textContent='';},4000);}
    if(s.mode!==previousMode){audio.setMusic(menu?'music_menu':'music_gameplay').catch(console.error);if(s.mode==='upgrade')audio.play('level_up').catch(console.error);}
    previousMode=s.mode;
}
ui.addEventListener('click',e=>{const button=e.target.closest('button');if(!button)return;if(button.dataset.tab){tab=button.dataset.tab;renderUi(true);}else if(button.dataset.action)command(button.dataset.action,button.dataset.value||'');});
ui.addEventListener('change',e=>{if(e.target.id==='difficulty')command('difficulty',e.target.value);if(e.target.id==='weaponSlots')command('weaponSlots',e.target.value);});
ui.addEventListener('pointerdown',()=>audio.unlock().then(()=>audio.setMusic(snapshot.mode==='menu'?'music_menu':'music_gameplay')).catch(console.error),{once:true});
input=new BrowserInput({
    preventKeys:['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '],
    onKeyDown:e=>{if(e.key===' '&&!e.repeat&&snapshot.mode==='playing')command('jump');if(e.key==='Escape'&&!e.repeat){if(snapshot.mode==='playing')command('pause');else if(snapshot.mode==='paused')command('resume');}},
    canDrag:()=>snapshot.mode==='playing',
    canStartDrag:e=>snapshot.mode==='playing'&&(e.pointerType!=='touch'||e.clientX>innerWidth/2),
    onDrag:delta=>{snapshot=session.command('look',JSON.stringify(delta));}
});
const disposeLifecycle=bindBrowserLifecycle({resetInput,
    onSuspend:()=>{if(snapshot.mode==='playing')command('pause');},
    onHidden:()=>{audio.pause();persist();},onPageHide:persist});
document.getElementById('jump').addEventListener('pointerdown',e=>{e.preventDefault();if(snapshot.mode==='playing')command('jump');});
document.getElementById('fullscreen').addEventListener('click',async()=>{try{await toggleFullscreen();}catch{toast.textContent='当前浏览器暂不支持全屏';}});
joystick=new VirtualJoystick(document.getElementById('joystick'),{autoRadius:true,deadZone:.12,onChange:(x,y)=>{touchX=x;touchZ=y;}});
function frame(now){if(!running)return;try{const dt=Math.min(.05,(now-last)/1000);last=now;
    const x=Number(input.keys.has('d')||input.keys.has('arrowright'))-Number(input.keys.has('a')||input.keys.has('arrowleft'))+touchX;
    const z=Number(input.keys.has('s')||input.keys.has('arrowdown'))-Number(input.keys.has('w')||input.keys.has('arrowup'))+touchZ;
    snapshot=session.step(dt,x,z);renderer.frame(snapshot,now/1000);renderUi(snapshot.mode!==previousMode);
    requestAnimationFrame(frame);
}catch(error){
    if(error.renderBackendFailure&&renderer.graphics){
        resetInput();if(snapshot.mode==='playing')command('pause');toast.textContent='正在恢复画面…';
        recoverBrowserRenderer(SurvivorRenderer,renderer,r=>r.initialize(catalog),error).then(replacement=>{renderer=replacement;last=performance.now();toast.textContent='画面已恢复';requestAnimationFrame(frame);}).catch(failFrame);return;
    }
    failFrame(error);
}}
function failFrame(error){running=false;input.dispose();joystick.dispose();disposeLifecycle();toast.textContent='运行错误：'+error.message;console.error(error);globalThis.HEGame.error=String(error);}
globalThis.HEGame={get snapshot(){return snapshot;},get renderer(){return renderer;},get running(){return running;},command,
    advance(seconds,x=0,z=0){for(let elapsed=0;elapsed<seconds&&snapshot.mode==='playing';elapsed+=.05)snapshot=session.step(Math.min(.05,seconds-elapsed),x,z);renderUi(true);return snapshot;},save:()=>session.save()};
loading.hidden=true;loading.style.display='none';ui.hidden=false;renderUi(true);persist();requestAnimationFrame(frame);
