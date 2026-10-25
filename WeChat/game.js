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
import {Subpackages} from '@hengine/wechat/Subpackages.js';
import {StartupDiagnostics} from '@hengine/wechat/StartupDiagnostics.js';
import {LoadingPresenter} from '@hengine/wechat/LoadingPresenter.js';
import {FramePacer} from '@hengine/wechat/FramePacer.js';

const root=typeof GameGlobal!=='undefined'?GameGlobal:globalThis;
const config=require('./he-game-config.js');
const ads=new Advertising(wx,config.ads),leaderboard=new FriendLeaderboard(wx,config.leaderboard);let actionBusy=false,leaderboardRectangle=null;
const canvas=wx.createCanvas(),stick=new AnalogStick(),look=new PointerDrag(),metrics={frames:0,errors:[],memoryWarnings:0,phase:'boot'};
const viewport=()=>readViewport(wx);
const tap=new MobileTap();
let confirmation=null,downloadStatus='',pendingLook=[0,0];
const framePacer=new FramePacer(wx);
function clearInput(){stick.reset();look.reset();tap.reset();pendingLook=[0,0];}
function refreshUi(){buttons=[];tap.reset();overlay?.invalidate();}
const diagnosticKey='HEngine.StarbloomSurvivor.WeChat.diagnostic';
const diagnostics=new StartupDiagnostics(wx,diagnosticKey);
const packages=new Subpackages(wx,{onEvent:event=>{
    const previous=metrics.download;metrics.download=event;
    if(previous?.name!==event.name||previous?.attempt!==event.attempt||previous?.status!==event.status)recordPhase(metrics.phase);
    if(event.status==='failed')console.warn('[HE package]',event);
}});
const assets=createPackageAssets(wx,config.files,viewport,packages);
let game,session,snapshot,renderer,overlay,audio,loadingPresenter,buttons=[],last=Date.now(),tab='home',page=0,hidden=false,previousMode='';
const saveKey='HEngine.StarbloomSurvivor.CSharp.v4';
function recordPhase(phase){
    metrics.phase=phase;
    diagnostics.record(phase,{memoryWarnings:metrics.memoryWarnings,download:metrics.download,runtimeMessage:metrics.runtimeMessage,serviceError:metrics.serviceError,error:metrics.errors[metrics.errors.length-1]});
}
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
    if(action==='friends'){
        actionBusy=true;clearInput();refreshUi();
        try{updateLeaderboardLayout();await leaderboard.show();metrics.serviceError=null;recordPhase(metrics.phase);}
        catch(error){
            metrics.serviceError={service:'friends',stage:error.stage||'unknown',code:error.code,detail:error.detail||String(error.message||error)};recordPhase(metrics.phase);
            console.error('[HE service]',metrics.serviceError);
            const denied=/auth deny|auth denied|user deny|user denied|cancel/i.test(error.detail||'');
            const message=denied?'请在小游戏右上角的设置中允许好友互动后重试。':error.message||'好友排行榜暂时无法打开';
            wx.showModal({title:'好友榜未能打开',content:(message+(error.detail?'\n微信返回：'+error.detail:'')+(error.code!==undefined?'\n错误码：'+error.code:'')).slice(0,350),confirmText:'知道了',showCancel:false});
        }finally{actionBusy=false;refreshUi();}return;
    }
    if(action==='friendsClose'){leaderboard.hide();refreshUi();return;}
    if(action==='friendsPage'){leaderboard.next(Number(value));return;}
    if(action==='start'||action==='watchRevive'){
        actionBusy=true;clearInput();refreshUi();
        try{
            if(action==='start'){
                recordPhase('battle-assets');
                downloadStatus='正在准备场景…';refreshUi();await renderer.prepareScene();await ads.showInterstitial();command('start');recordPhase('playing');if(hidden)command('pause');
            }
            else{const result=await ads.showRewarded();if(result.completed){command('rewardRevive');if(hidden)command('pause');}else wx.showToast({title:result.status==='closed'?'完整观看后才能复活':'广告暂不可用，请稍后重试',icon:'none'});}
        }finally{downloadStatus='';actionBusy=false;last=Date.now();refreshUi();}
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
    if(actionBusy){buttons=[];label(downloadStatus||'正在准备，请稍候…',20,h-30,18);}
    });
}
function dispatch(target){
    refreshUi();
    void hostCommand(target.action,target.value).catch(error=>{
        metrics.errors.push(String(error));recordPhase(metrics.phase);console.error('[HE command]',error);
        if(error.packageName)wx.showModal({title:'资源下载未完成',content:String(error.message).slice(0,300)+'。请检查网络后再次点击开始。',showCancel:false});
        else wx.showToast({title:'操作未完成，请稍后重试',icon:'none'});
    });
}
wx.onTouchStart(e=>{
    if(hidden||actionBusy||!snapshot)return;
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
        if(delta&&snapshot?.mode==='playing'){pendingLook[0]+=delta[0];pendingLook[1]+=delta[1];}
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
if(wx.onMemoryWarning)wx.onMemoryWarning(()=>{
    metrics.memoryWarnings++;renderer?.reduceMemory();
    if(overlay){overlay.maxPixels=Math.min(overlay.maxPixels,960*540);overlay.invalidate();}
    recordPhase(metrics.phase);console.warn('[HE memory warning]',metrics.phase,metrics.memoryWarnings);
});
const recordHostError=(phase,error)=>{metrics.errors.push(String(error?.stack||error?.message||error).slice(0,1200));recordPhase(phase);};
if(wx.onError)wx.onError(error=>recordHostError('host-error',error));
if(wx.onUnhandledRejection)wx.onUnhandledRejection(event=>recordHostError('host-rejection',event.reason));
if(canvas.addEventListener)canvas.addEventListener('webglcontextlost',()=>recordHostError('context-lost','WebGL context lost'));
async function start(){
    const previous=diagnostics.previous;
    if(previous&&/^(graphics|packages|catalog|scene|ui|managed-runtime|wasm:|managed-state|failed:|menu-frame|menu-audio|host-|context-lost)/.test(previous.phase))
        await new Promise(resolve=>wx.showModal({title:'上次加载未完成',content:'上次记录：'+previous.phase+(previous.phase.includes('packages')&&previous.download?.name?' / '+previous.download.name:'')+(previous.runtimeMessage?'\n'+previous.runtimeMessage:'')+'。如果再次退出，请把这条记录截图反馈。',confirmText:'继续加载',showCancel:false,success:resolve,fail:resolve}));
    recordPhase('graphics');
    applyDebugSettings(wx,config);
    await applyOrientation(wx,config.orientation);
    renderer=new WeChatRenderer(canvas,assets);overlay=new CachedOverlay(renderer.gl,wx.createCanvas());
    const normalBudget={...renderer.renderBudget};renderer.renderBudget.pixels=640*360;renderer.renderBudget.ratio=1;overlay.maxPixels=640*360;
    const loading=new LoadingScreen('小树保卫者');
    loadingPresenter=new LoadingPresenter(loading,()=>{if(hidden)return;renderer.beginFrame([0,1,4],[0,0,0]);const v=viewport();overlay.invalidate();overlay.draw(v.width,v.height,(ctx,w,h)=>loading.paint(ctx,w,h));});
    const showLoading=(message,progress)=>loadingPresenter.update(message,progress);
    await loadingPresenter.phase('正在下载游戏资源',.02);
    recordPhase('packages');
    // Download the complete game before showing the menu. Keep geometry/GPU
    // allocation deferred so cached package files do not restore the old peak.
    await packages.loadMany(config.subpackages,state=>{
        showLoading(`正在下载游戏资源 ${state.index+1}/${state.total} · ${Math.floor(state.progress)}%${state.attempt>1?'（重试 '+state.attempt+'/3）':''}`,.02+.68*(state.index+state.progress/100)/state.total);
    });
    await loadingPresenter.phase('正在读取游戏内容',.72);
    recordPhase('catalog');
    catalog=await (await assets.fetch('catalog.json')).json();
    // Compile/initialize Wasm before decoding images or allocating character
    // buffers. The low-resolution loading surface is the only UI allocation.
    recordPhase('managed-runtime');await loadingPresenter.phase('正在启动游戏逻辑',.75);
    const runtime=await require('./wechat-runtime.js').createManagedRuntime(require('./runtime-config.js'),{onStage:(stage,detail)=>{if(detail)metrics.runtimeMessage=detail;recordPhase('wasm:'+stage);}});
    game=(await runtime.getAssemblyExports(runtime.getConfig().mainAssemblyName)).Program;
    recordPhase('scene');await loadingPresenter.phase('正在准备角色',.83);
    loading.background=await assets.loadImage('Assets/UI/Backgrounds/starbloom_loading_bg.png');
    audio=new AudioBank(wx,catalog.audio,assets.pathFor);
    let loaded=0;
    await renderer.initialize(catalog,message=>showLoading(message,Math.min(.87,.84+ ++loaded*.001)));
    recordPhase('ui');await loadingPresenter.phase('正在加载界面贴图',.88);
    let icons=0;
    for(const path of new Set([...catalog.characters,...catalog.weapons,...catalog.tomes,...catalog.trinkets,...catalog.metaPowerUps,...(catalog.power_ups||[])].map(item=>item.icon).filter(Boolean))){
        uiImages.set(path,await assets.loadImage(path));
        if(++icons%16===0){recordPhase('ui:'+icons);await loadingPresenter.phase('正在加载界面贴图 · '+icons,.88+Math.min(.05,icons*.0007));}
    }
    uiImages.set('Assets/UI/Backgrounds/starbloom_title_bg.png',await assets.loadImage('Assets/UI/Backgrounds/starbloom_title_bg.png'));
    recordPhase('managed-state');await loadingPresenter.phase('正在读取游戏进度',.96);
    session=new ManagedGameSession(game,{get:key=>wx.getStorageSync(key),set:(key,value)=>wx.setStorageSync(key,value)},saveKey);
    snapshot=session.initialize(catalog,{backupBeforeInitialize:true});command('configureAdRevive',String(ads.canReward));command('configureInterestRadius',String(renderer.interest.enabled?renderer.interest.radius+renderer.interest.padding:0));
    command('configureVisualBudget','128');
    command('configureEnemyLimit','240');
    await loadingPresenter.phase('加载完成',1);
    metrics.loading={draws:loadingPresenter.draws,uploadBytes:overlay.uploadBytes,pixels:overlay.canvas.width*overlay.canvas.height};
    loadingPresenter.dispose();
    Object.assign(renderer.renderBudget,metrics.memoryWarnings?{pixels:960*540,ratio:1}:normalBudget);
    overlay.maxPixels=metrics.memoryWarnings?960*540:1280*720;recordPhase('menu-frame');
    root.HEGame={get snapshot(){return snapshot;},get metrics(){return metrics;},get ui(){return {rasterWidth:overlay.canvas.width,rasterHeight:overlay.canvas.height,uploadCount:overlay.uploadCount,uploadBytes:overlay.uploadBytes,leaderboardRectangle,leaderboardSize:leaderboard.context?[leaderboard.context.canvas.width,leaderboard.context.canvas.height]:null,buttons:buttons.map(b=>({...b})),layout:mobileLayout(viewport())};},command,save:()=>session.save(),renderer};
    function frame(){
        try{
            const now=Date.now();
            if(!hidden&&!framePacer.due(now,snapshot.mode==='playing')){requestAnimationFrame(frame);return;}
            if(!hidden){
                const before=snapshot.mode;
                if(snapshot.mode==='playing'&&(pendingLook[0]||pendingLook[1])){command('look',JSON.stringify(pendingLook));pendingLook=[0,0];}
                if(snapshot.mode==='playing')snapshot=session.step(Math.min(.05,(now-last)/1000),stick.x,stick.y);
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
                    if(metrics.frames===0)recordPhase('menu-audio');
                    audio.setMusic(snapshot.mode==='menu'?'music_menu':'music_gameplay');
                    if(snapshot.mode==='upgrade')audio.play('level_up');
                    if(snapshot.mode==='result')leaderboard.submit(Number(snapshot.profile.career?.bestSurvivalSeconds||snapshot.elapsed));
                    previousMode=snapshot.mode;
                }
                if(metrics.frames===0)recordPhase('ready');
                metrics.frames++;
            }
            last=now;requestAnimationFrame(frame);
        }catch(error){fail(error);}
    }
    last=Date.now();requestAnimationFrame(frame);
}
function fail(error){loadingPresenter?.dispose();metrics.errors.push(String(error.stack||error));recordPhase('failed:'+metrics.phase);console.error('[HE Survivor]',error);wx.showModal({title:error.packageName?'资源下载未完成':'游戏运行失败',content:error.packageName?String(error.message).slice(0,300)+'。请检查网络后重新进入。':'游戏暂时无法继续，请重新进入。诊断阶段：'+metrics.phase,confirmText:'确定',showCancel:false});}
start().catch(fail);
