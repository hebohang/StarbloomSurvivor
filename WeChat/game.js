import {CanvasUI,hitTest} from '@hengine/web/CanvasUI.js';
import {applyDebugSettings} from '@hengine/wechat/DebugSettings.js';
import {paintHud,mobileControls,title,purchasePrice} from './Hud.js';
import {mobileLayout,MobileTap} from './MobileUI.js';
import {Advertising} from '@hengine/wechat/Advertising.js';
import {FriendLeaderboard} from '@hengine/wechat/FriendLeaderboard.js';
import {readViewport,applyOrientation} from '@hengine/wechat/Viewport.js';
import {WeChatRenderer} from './renderer.js';
import {createPackageAssets} from '@hengine/wechat/PackageAssets.js';
import {CachedOverlay} from '@hengine/wechat/CachedOverlay.js';
import {LoadingScreen} from '@hengine/web/LoadingScreen.js';
import {AnalogStick} from '@hengine/web/Input/AnalogStick.js';
import {PointerDrag} from '@hengine/web/Input/PointerDrag.js';
import {AudioBank} from '@hengine/wechat/AudioBank.js';
import {ManagedGameSession} from '@hengine/web/ManagedGameSession.js';

const root=typeof GameGlobal!=='undefined'?GameGlobal:globalThis;
const config=require('./he-game-config.js');
const ads=new Advertising(wx,config.ads),leaderboard=new FriendLeaderboard(wx,config.leaderboard);let actionBusy=false,leaderboardRectangle=null;
const canvas=wx.createCanvas(),stick=new AnalogStick(),look=new PointerDrag(),metrics={frames:0,errors:[]};
const viewport=()=>readViewport(wx);
const tap=new MobileTap();
let confirmation=null;
function clearInput(){stick.reset();look.reset();tap.reset();}
function refreshUi(){buttons=[];tap.reset();overlay?.invalidate();}
const assets=createPackageAssets(wx,config.files,viewport);
let game,session,snapshot,renderer,overlay,audio,buttons=[],last=Date.now(),tab='home',page=0,hidden=false,previousMode='';
const saveKey='HEngine.StarbloomSurvivor.CSharp.v4';
const persist=()=>session?.persistIfChanged();
function command(name,value=''){
    const previous=snapshot?.mode;snapshot=session.command(name,value);
    if(snapshot.mode!==previous){clearInput();confirmation=null;}
    if(name==='home'){tab='home';page=0;}
    if(name!=='look'){
        refreshUi();audio?.play('ui_click');
        if(snapshot.message&&snapshot.mode==='menu')wx.showToast({title:snapshot.message,icon:'none'});
    }
}
async function hostCommand(action,value=''){
    if(actionBusy||hidden)return;
    if(action==='tab'){tab=value;page=0;refreshUi();return;}
    if(action==='page'){page+=Number(value);refreshUi();return;}
    if(action==='confirmBuy'||action==='confirmPower'){
        const item=action==='confirmBuy'?[...catalog.characters,...catalog.weapons,...catalog.tomes,...catalog.trinkets].find(i=>i.id===value):catalog.metaPowerUps.find(i=>i.id===value);
        const price=action==='confirmBuy'?purchasePrice(catalog,value):item.prices[snapshot.profile.powerUps?.[value]||0];
        const named=action==='confirmPower'?catalog.power_ups?.find(i=>i.id===value):item;
        confirmation={title:action==='confirmBuy'?'购买伙伴 / 装备':'永久成长',message:`${title(named)} · 消耗 ${price} 星币`,action:action==='confirmBuy'?'buy':'power',value};
        clearInput();refreshUi();return;
    }
    if(action==='confirmAbandon'){confirmation={title:'结束本次冒险？',message:'结算当前收益，返回大厅。',action:'abandon',value:''};clearInput();refreshUi();return;}
    if(action==='cancelConfirm'){confirmation=null;refreshUi();return;}
    if(action==='acceptConfirm'){const pending=confirmation;confirmation=null;refreshUi();if(pending)command(pending.action,pending.value);return;}
    if(action==='friends'){actionBusy=true;clearInput();refreshUi();try{updateLeaderboardLayout();await leaderboard.show();}catch(error){console.error('[HE service]',error);wx.showToast({title:'服务暂不可用，请稍后重试',icon:'none'});}finally{actionBusy=false;refreshUi();}return;}
    if(action==='friendsClose'){leaderboard.hide();refreshUi();return;}
    if(action==='friendsPage'){leaderboard.next(Number(value));return;}
    if(action==='start'||action==='watchRevive'){
        actionBusy=true;clearInput();refreshUi();
        try{
            if(action==='start'){await ads.showInterstitial();command('start');if(hidden)command('pause');}
            else{const result=await ads.showRewarded();if(result.completed){command('rewardRevive');if(hidden)command('pause');}else wx.showToast({title:result.status==='closed'?'完整观看后才能复活':'广告暂不可用，请稍后重试',icon:'none'});}
        }finally{actionBusy=false;last=Date.now();refreshUi();}
        return;
    }
    command(action,value);
}
let catalog;
const uiImages=new Map();
function updateLeaderboardLayout(){
    const v=viewport(),layout=mobileLayout(v),width=Math.min(600,layout.width-24),height=layout.height-90;
    leaderboard.setLayout(width,height,Math.min(3,(v.ratio||1)*layout.scale));
    leaderboardRectangle=[layout.left+(layout.width-width)/2*layout.scale,layout.top+10*layout.scale,width*layout.scale,height*layout.scale];
}
function paint(ctx,w,h) {
    const layout=mobileLayout(viewport()),backdrop=layout.fullRect;layout.paint(ctx,()=>{w=layout.width;h=layout.height;buttons=[];
    function label(text,x,y,size=16,color='#ffffff'){ctx.fillStyle=color;ctx.font=`${size}px sans-serif`;ctx.fillText(String(text),x,y);}
    function button(text,x,y,width,action,value=''){const ui=new CanvasUI(ctx);ui.button(text,{x,y,w:width,h:48},{action,value,background:'#304b66',textColor:'#fff'});buttons.push(...ui.targets);}
    const hud=paintHud(ctx,w,h,{snapshot,catalog,images:uiImages,stick,tab,page,confirmation,backdrop});buttons=hud.buttons;page=hud.page;
    if(leaderboard.visible){buttons=[];ctx.fillStyle='rgba(0,0,0,.8)';ctx.fillRect(backdrop.x,backdrop.y,backdrop.width,backdrop.height);updateLeaderboardLayout();const bw=(w-40)/3;button('上一页',12,h-66,bw,'friendsPage','-1');button('下一页',20+bw,h-66,bw,'friendsPage','1');button('关闭',28+bw*2,h-66,bw,'friendsClose');}
    if(actionBusy){buttons=[];label('正在等待服务…',20,h-30,18);}
    });
}
function dispatch(target){
    refreshUi();
    void hostCommand(target.action,target.value).catch(error=>{
        metrics.errors.push(String(error));console.error('[HE command]',error);
        wx.showToast({title:'操作未完成，请稍后重试',icon:'none'});
    });
}
wx.onTouchStart(e=>{
    if(hidden||actionBusy||!game)return;
    const layout=mobileLayout(viewport());
    for(const t of e.changedTouches){
        const px=t.clientX??t.x,py=t.clientY??t.y,{x,y}=layout.point(px,py),b=hitTest(buttons,x,y);
        if(b){
            if(b.action==='jump')dispatch(b);
            else if(b.action)tap.begin(t.identifier,px,py,b,snapshot.mode);
            continue;
        }
        if(!leaderboard.visible&&!confirmation&&snapshot.mode==='playing'){
            const controls=mobileControls(layout.width,layout.height);stick.radius=controls.radius;
            if(x>=0&&y>=0&&x<=layout.width&&y<=layout.height){
                if(controls.isMovement(x,y))stick.begin(t.identifier,x,y);
                else if(controls.isLook(x))look.begin(t.identifier,x,y);
            }
        }
    }
});
wx.onTouchMove(e=>{
    if(hidden||actionBusy)return;
    for(const t of e.changedTouches){
        const px=t.clientX??t.x,py=t.clientY??t.y;tap.move(t.identifier,px,py);
        const point=mobileLayout(viewport()).point(px,py);
        stick.move(t.identifier,point.x,point.y);
        const delta=look.move(t.identifier,point.x,point.y);
        if(delta&&snapshot?.mode==='playing')command('look',JSON.stringify(delta));
    }
});
wx.onTouchEnd(e=>{
    for(const t of e.changedTouches){
        const px=t.clientX??t.x,py=t.clientY??t.y,point=mobileLayout(viewport()).point(px,py);
        const target=tap.end(t.identifier,px,py,hitTest(buttons,point.x,point.y),snapshot?.mode);
        stick.end(t.identifier);look.end(t.identifier);
        if(target&&!hidden&&!actionBusy)dispatch(target);
    }
});
if(wx.onWindowResize)wx.onWindowResize(()=>{clearInput();refreshUi();});
wx.onTouchCancel(()=>{clearInput();});
wx.onHide(()=>{hidden=true;clearInput();confirmation=null;refreshUi();if(snapshot?.mode==='playing')command('pause');persist();audio?.pause();});
wx.onShow(()=>{hidden=false;last=Date.now();refreshUi();audio?.resume();});
async function start(){
    applyDebugSettings(wx,config);
    await applyOrientation(wx,config.orientation);
    renderer=new WeChatRenderer(canvas,assets);overlay=new CachedOverlay(renderer.gl,wx.createCanvas());
    const loading=new LoadingScreen('小树保卫者');
    const showLoading=(message,progress)=>{loading.update(message,progress);renderer.beginFrame([0,1,4],[0,0,0]);const v=viewport();overlay.invalidate();overlay.draw(v.width,v.height,(ctx,w,h)=>loading.paint(ctx,w,h));};
    showLoading('正在下载游戏资源',.02);
    let downloaded=0;
    await Promise.all(config.subpackages.map(name=>new Promise((resolve,reject)=>wx.loadSubpackage({name,success:()=>{showLoading('正在下载游戏资源',.05+.2*++downloaded/config.subpackages.length);resolve();},fail:reject}))));
    loading.background=await assets.loadImage('Assets/UI/Backgrounds/starbloom_loading_bg.png');
    showLoading('正在读取游戏内容',.28);
    catalog=await (await assets.fetch('catalog.json')).json();
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
    root.HEGame={get snapshot(){return snapshot;},get metrics(){return metrics;},get ui(){return {rasterWidth:overlay.canvas.width,rasterHeight:overlay.canvas.height,uploadCount:overlay.uploadCount,uploadBytes:overlay.uploadBytes,leaderboardRectangle,leaderboardSize:leaderboard.context?[leaderboard.context.canvas.width,leaderboard.context.canvas.height]:null,buttons:buttons.map(b=>({...b})),layout:mobileLayout(viewport())};},command,save:()=>session.save(),renderer};
    function frame(){
        try{
            const now=Date.now();
            if(!hidden){
                const before=snapshot.mode;
                snapshot=session.step(Math.min(.05,(now-last)/1000),stick.x,stick.y);
                if(snapshot.mode!==before){clearInput();confirmation=null;refreshUi();}
                renderer.frame(snapshot,now/1000);
                const diagnose=metrics.frames===1||snapshot.mode!==previousMode;
                if(diagnose)overlay.invalidate();
                const v=viewport();
                const hudKey=[snapshot.mode,Math.ceil(snapshot.health),Math.ceil(snapshot.maxHealth),snapshot.level,snapshot.kills,Math.floor(snapshot.elapsed),
                    snapshot.regions.map(r=>r.state).join(','),stick.id,Math.round(stick.originX),Math.round(stick.originY),Math.round(stick.x*40),Math.round(stick.y*40)].join('|');
                overlay.requestUpdate(hudKey);overlay.draw(v.width,v.height,paint);leaderboard.composite(overlay,leaderboardRectangle,v);
                if(diagnose)console.info('[HE render]',JSON.stringify({scene:renderer.diagnostics(),character:snapshot.character,position:[snapshot.x,snapshot.y,snapshot.z]}));
                if(snapshot.mode!==previousMode){
                    audio.setMusic(snapshot.mode==='menu'?'music_menu':'music_gameplay');
                    if(snapshot.mode==='upgrade')audio.play('level_up');
                    if(snapshot.mode==='result')leaderboard.submit(Number(snapshot.profile.career?.bestSurvivalSeconds||snapshot.elapsed));
                    previousMode=snapshot.mode;
                }
                metrics.frames++;
            }
            last=now;requestAnimationFrame(frame);
        }catch(error){fail(error);}
    }
    last=Date.now();requestAnimationFrame(frame);
}
function fail(error){metrics.errors.push(String(error.stack||error));console.error('[HE Survivor]',error);wx.showModal({title:'游戏启动失败',content:'暂时无法加载游戏，请检查网络连接后重新进入。',confirmText:'确定',showCancel:false});}
start().catch(fail);
