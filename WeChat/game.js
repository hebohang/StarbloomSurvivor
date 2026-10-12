import {CanvasUI,hitTest} from '@hengine/web/CanvasUI.js';
import {applyDebugSettings} from '@hengine/wechat/DebugSettings.js';
import {paintHud} from './Hud.js';
import {touchLayout} from '@hengine/web/Input/TouchLayout.js';
import {Advertising} from '@hengine/wechat/Advertising.js';
import {FriendLeaderboard} from '@hengine/wechat/FriendLeaderboard.js';
import {viewportLayout} from '@hengine/web/ViewportLayout.js';
import {readViewport,applyOrientation} from '@hengine/wechat/Viewport.js';
import {SurvivorRenderer} from '../Web/renderer.js';
import {createPackageAssets} from '@hengine/wechat/PackageAssets.js';
import {CanvasOverlay} from '@hengine/web/CanvasOverlay.js';
import {LoadingScreen} from '@hengine/web/LoadingScreen.js';
import {AnalogStick} from '@hengine/web/Input/AnalogStick.js';
import {PointerDrag} from '@hengine/web/Input/PointerDrag.js';
import {AudioBank} from '@hengine/wechat/AudioBank.js';
import {HuiDocument} from '@hengine/web/HuiDocument.js';
import {ManagedGameSession} from '@hengine/web/ManagedGameSession.js';

const root=typeof GameGlobal!=='undefined'?GameGlobal:globalThis;
const config=require('./he-game-config.js');
const ads=new Advertising(wx,config.ads),leaderboard=new FriendLeaderboard(wx,config.leaderboard);let actionBusy=false,leaderboardRectangle=null;
const canvas=wx.createCanvas(),stick=new AnalogStick(),look=new PointerDrag(),metrics={frames:0,errors:[]};
const viewport=()=>readViewport(wx);
const assets=createPackageAssets(wx,config.files,viewport);
let game,session,snapshot,renderer,overlay,audio,buttons=[],last=Date.now(),tab='characters',page=0,hidden=false,previousMode='';
const saveKey='HEngine.StarbloomSurvivor.CSharp.v4';
const persist=()=>session?.persistIfChanged();
function command(name,value=''){const previous=snapshot?.mode;snapshot=session.command(name,value);if(snapshot.mode!==previous){buttons=[];stick.reset();look.reset();overlay?.invalidate();}if(name!=='look')audio?.play('ui_click');}
async function hostCommand(action,value=''){
    if(actionBusy)return;
    if(action==='friends'){actionBusy=true;try{await leaderboard.show();}catch(error){console.error('[HE service]',error);wx.showToast({title:'服务暂不可用，请稍后重试',icon:'none'});}finally{actionBusy=false;}return;}
    if(action==='friendsClose'){leaderboard.hide();return;}
    if(action==='friendsPage'){leaderboard.next(Number(value));return;}
    if(action==='start'||action==='watchRevive'){
        actionBusy=true;stick.reset();look.reset();
        try{
            if(action==='start'){await ads.showInterstitial();command('start');}
            else{const result=await ads.showRewarded();if(result.completed)command('rewardRevive');else wx.showToast({title:result.status==='closed'?'完整观看后才能复活':'广告暂不可用，请稍后重试',icon:'none'});}
        }finally{actionBusy=false;last=Date.now();}
        return;
    }
    command(action,value);
}
let catalog,pauseUi;
const uiImages=new Map();
function paint(ctx,w,h) {
    const layout=viewportLayout(viewport()),backdrop=layout.fullRect;layout.paint(ctx,()=>{w=layout.width;h=layout.height;buttons=[];
    function label(text,x,y,size=16,color='#ffffff'){ctx.fillStyle=color;ctx.font=`${size}px sans-serif`;ctx.fillText(String(text),x,y);}
    function button(text,x,y,width,action,value=''){const ui=new CanvasUI(ctx);ui.button(text,{x,y,w:width,h:38},{action,value,background:'#304b66',textColor:'#fff'});buttons.push(...ui.targets);}
    const hud=paintHud(ctx,w,h,{snapshot,catalog,images:uiImages,stick,tab,page,backdrop});buttons=hud.buttons;page=hud.page;
    if(snapshot.mode==='paused')buttons=pauseUi.paint(ctx,w,h,{backdrop});
    if(leaderboard.visible){buttons=[];ctx.fillStyle='rgba(0,0,0,.8)';ctx.fillRect(backdrop.x,backdrop.y,backdrop.width,backdrop.height);const boardWidth=Math.min(600,layout.width-24);leaderboardRectangle=[layout.left+(layout.width-boardWidth)/2*layout.scale,layout.top+10*layout.scale,boardWidth*layout.scale,(h-90)*layout.scale];button('上一页',20,h-66,100,'friendsPage','-1');button('下一页',130,h-66,100,'friendsPage','1');button('关闭',layout.width-120,h-66,100,'friendsClose');}
    if(actionBusy){buttons=[];label('正在等待服务…',20,h-30,18);}
    if(snapshot.message)label(snapshot.message.slice(0,26),16,h-12,12,'#ffe09c');});
}
wx.onTouchStart(e=>{const layout=viewportLayout(viewport()),h=layout.height;for(const t of e.changedTouches){const px=t.clientX??t.x,py=t.clientY??t.y,point=layout.point(px,py),x=point.x,y=point.y;const b=hitTest(buttons,x,y);if(b){if(!b.action)continue;if(b.action==='tab'){tab=b.value;page=0;}else if(b.action==='page')page+=Number(b.value);else if(game)try{void hostCommand(b.action,b.value).catch(error=>{console.error('[HE command]',error);wx.showToast({title:'操作未完成，请稍后重试',icon:'none'});});}catch(error){metrics.errors.push(String(error));console.error('[HE command]',error);wx.showToast({title:'操作未完成，请稍后重试',icon:'none'});}continue;}if(!actionBusy&&!leaderboard.visible&&snapshot?.mode==='playing'){const controls=touchLayout(layout.width,h);stick.radius=controls.radius;if(controls.isMovement(x,y))stick.begin(t.identifier,x,y);else if(controls.isLook(x))look.begin(t.identifier,x,y);}}});
wx.onTouchMove(e=>{for(const t of e.changedTouches){const x=t.clientX??t.x,y=t.clientY??t.y;const point=viewportLayout(viewport()).point(x,y);stick.move(t.identifier,point.x,point.y);const delta=look.move(t.identifier,point.x,point.y);if(delta&&snapshot?.mode==='playing')command('look',JSON.stringify(delta));}});
wx.onTouchEnd(e=>{for(const t of e.changedTouches){stick.end(t.identifier);look.end(t.identifier);}});
if(wx.onWindowResize)wx.onWindowResize(()=>{stick.reset();look.reset();buttons=[];});
wx.onTouchCancel(()=>{stick.reset();look.reset();});
wx.onHide(()=>{hidden=true;stick.reset();look.reset();if(snapshot?.mode==='playing')command('pause');persist();audio?.pause();});
wx.onShow(()=>{hidden=false;last=Date.now();audio?.resume();});
async function start(){
    applyDebugSettings(wx,config);
    await applyOrientation(wx,config.orientation);
    renderer=new SurvivorRenderer(canvas,assets);overlay=new CanvasOverlay(renderer.gl,wx.createCanvas(),{pixelUpload:true,maxUpdateHz:30});
    const loading=new LoadingScreen('小树保卫者');
    const showLoading=(message,progress)=>{loading.update(message,progress);renderer.beginFrame([0,1,4],[0,0,0]);const v=viewport();overlay.draw(v.width,v.height,(ctx,w,h)=>loading.paint(ctx,w,h));};
    showLoading('正在下载游戏资源',.02);
    let downloaded=0;
    await Promise.all(config.subpackages.map(name=>new Promise((resolve,reject)=>wx.loadSubpackage({name,success:()=>{showLoading('正在下载游戏资源',.05+.2*++downloaded/config.subpackages.length);resolve();},fail:reject}))));
    loading.background=await assets.loadImage('Assets/UI/Backgrounds/starbloom_loading_bg.png');
    showLoading('正在读取游戏内容',.28);
    catalog=await (await assets.fetch('catalog.json')).json();
    pauseUi=new HuiDocument(await (await assets.fetch(catalog.sharedUi.pause)).json(),catalog.sharedUi.pause);
    await pauseUi.loadAssets(assets.loadImage);
    audio=new AudioBank(wx,catalog.audio,assets.pathFor);
    let loaded=0;
    await renderer.initialize(catalog,message=>showLoading(message,Math.min(.8,.3+ ++loaded*.007)));
    showLoading('正在加载界面贴图',.82);
    for(const path of new Set([...catalog.characters,...catalog.weapons,...catalog.tomes,...catalog.trinkets,...catalog.metaPowerUps,...(catalog.power_ups||[])].map(item=>item.icon).filter(Boolean)))
        uiImages.set(path,await assets.loadImage(path));
    uiImages.set('Assets/UI/Backgrounds/starbloom_title_bg.png',await assets.loadImage('Assets/UI/Backgrounds/starbloom_title_bg.png'));
    showLoading('正在启动游戏逻辑',.92);
    const runtime=await require('./wechat-runtime.js').createManagedRuntime(require('./runtime-config.js'));
    game=(await runtime.getAssemblyExports(runtime.getConfig().mainAssemblyName)).Program;
    session=new ManagedGameSession(game,{get:key=>wx.getStorageSync(key),set:(key,value)=>wx.setStorageSync(key,value)},saveKey);
    snapshot=session.initialize(catalog,{backupBeforeInitialize:true});command('configureAdRevive',String(ads.canReward));command('configureInterestRadius',String(renderer.interest.enabled?renderer.interest.radius+renderer.interest.padding:0));
    showLoading('加载完成',1);
    root.HEGame={get snapshot(){return snapshot;},get metrics(){return metrics;},get ui(){return {rasterWidth:overlay.canvas.width,rasterHeight:overlay.canvas.height,buttons:buttons.map(b=>({...b})),layout:viewportLayout(viewport())};},command,save:()=>session.save(),renderer};
    function frame(){try{const now=Date.now();if(!hidden){snapshot=session.step(Math.min(.05,(now-last)/1000),stick.x,stick.y);renderer.frame(snapshot,now/1000);const diagnose=metrics.frames===1||snapshot.mode!==previousMode;const scene=diagnose?renderer.diagnostics():null;if(diagnose)overlay.invalidate();const v=viewport();overlay.draw(v.width,v.height,paint);leaderboard.composite(overlay,leaderboardRectangle,v);if(diagnose)console.info('[HE render]',JSON.stringify({scene,composite:renderer.diagnostics(),character:snapshot.character,position:[snapshot.x,snapshot.y,snapshot.z]}));if(snapshot.mode!==previousMode){audio.setMusic(snapshot.mode==='menu'?'music_menu':'music_gameplay');if(snapshot.mode==='upgrade')audio.play('level_up');if(snapshot.mode==='result')leaderboard.submit(Number(snapshot.profile.career?.bestSurvivalSeconds||snapshot.elapsed));previousMode=snapshot.mode;}metrics.frames++;}last=now;requestAnimationFrame(frame);}catch(error){fail(error);}}
    last=Date.now();requestAnimationFrame(frame);
}
function fail(error){metrics.errors.push(String(error.stack||error));console.error('[HE Survivor]',error);wx.showModal({title:'游戏启动失败',content:'暂时无法加载游戏，请检查网络连接后重新进入。',confirmText:'确定',showCancel:false});}
start().catch(fail);
