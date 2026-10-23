'use strict';
// Run the actual exported game and C# Wasm with a strict package-path WX host.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process');
const engine=process.env.HE_ENGINE_ROOT;
if(!engine)throw Error('Set HE_ENGINE_ROOT to the selected engine checkout.');
const esbuild=require(path.join(engine,'Tools/Scripting/node_modules/esbuild')),{chromium}=require('playwright');
async function main(){
    const root=path.resolve(__dirname,'..'),pkg=path.resolve(process.argv[2]||path.join(root,'Dist/WeChat')),out=path.join(engine,'out/agent/starbloom-wechat-mobile-test');fs.mkdirSync(out,{recursive:true});
    const bundled=esbuild.buildSync({entryPoints:[path.join(pkg,'game.js')],bundle:true,platform:'browser',write:false}).outputFiles[0].text;
    const server=spawn(process.execPath,[path.join(engine,'Tools/Build/ServeWeb.cjs'),pkg,'0'],{windowsHide:true,stdio:['ignore','pipe','pipe']});let browser;
    try{
        const url=await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{const m=String(b).match(/http:\/\/127\.0\.0\.1:\d+\//);if(m)resolve(m[0]);});server.on('error',reject);});
        browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
        const page=await browser.newPage({viewport:{width:960,height:540}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
        await page.route('**/__test',r=>r.fulfill({contentType:'text/html',body:'<style>body{margin:0}canvas{display:block;width:100vw;height:100vh}</style>'}));await page.goto(url+'__test');
        await page.evaluate(()=>{
            window.GameGlobal=window;
            // Reproduce a host that advertises WebGL 2 but cannot use the new instanced path.
            for(const name of ['drawElementsInstanced','drawArraysInstanced','vertexAttribDivisor'])
                WebGL2RenderingContext.prototype[name]=()=>{throw Error('Unsupported phone instancing: '+name);};
            const buffers=new Map(),events={},storage=new Map();let mainCanvas;
            window.fixture={events,storage,modals:[],toasts:[],size:{width:960,height:540},loadedPackages:new Set(),packageAttempts:[],activeDownloads:0,peakDownloads:0,nativeInstantiations:0,nativeModules:0,imagesAtNativeStart:null,loadingReads:0,loadingReadBytes:0};
            fixture.tableGrowth=[];fixture.zeroArityExports=0;
            const grow=WebAssembly.Table.prototype.grow;
            WebAssembly.Table.prototype.grow=function(delta,...args){fixture.tableGrowth.push(delta);if(fixture.rejectJitTables&&delta>64){fixture.tableFailure=true;throw Error('Simulated iOS Jiterpreter Table.grow failure');}return grow.call(this,delta,...args);};
            const bytes=async file=>{if(!fixture.loadedPackages.has(file.split('/')[0]))throw Error('Read before subpackage ready: '+file);if(!buffers.has(file)){const response=await fetch(file);if(!response.ok)throw Error('Missing '+file);buffers.set(file,await response.arrayBuffer());}return buffers.get(file);};
            const filePath=file=>{if(typeof file!=='string'||!file.endsWith('.wasm'))throw Error('WX Wasm requires a package path');};
            window.WXWebAssembly={Memory:WebAssembly.Memory,Table:WebAssembly.Table,Global:WebAssembly.Global,RuntimeError:WebAssembly.RuntimeError,
                Module:function(file){fixture.nativeModules++;if(!fixture.baseline)throw Error('Unexpected redundant synchronous native Wasm compile');filePath(file);return new WebAssembly.Module(buffers.get(file));},
                instantiate:async(file,imports)=>{
                    filePath(file);if(!file.includes('/feature-')){fixture.nativeInstantiations++;fixture.imagesAtNativeStart=fixture.imageCount||0;if(fixture.pauseNative)await new Promise(resolve=>{fixture.resumeNative=resolve;});}
                    const result=await WebAssembly.instantiate(await bytes(file),imports);if(result.instance?.exports.memory)fixture.wasmMemory=result.instance.exports.memory;
                    if(fixture.zeroArity&&!file.includes('/feature-')){
                        const exports={};for(const [name,value] of Object.entries(result.instance.exports)){exports[name]=typeof value==='function'?(...args)=>value(...args):value;if(typeof value==='function')fixture.zeroArityExports++;}
                        return {instance:{exports},module:result.module};
                    }return result;
                }};
            const shared=document.createElement('canvas');shared.width=720;shared.height=640;fixture.sharedCanvas=shared;fixture.boardMessages=[];
            const originalDrawImage=CanvasRenderingContext2D.prototype.drawImage;
            const originalGetImageData=CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData=function(...args){const result=originalGetImageData.apply(this,args);if(!window.HEGame){fixture.loadingReads++;fixture.loadingReadBytes+=result.data.byteLength;}return result;};
            CanvasRenderingContext2D.prototype.drawImage=function(source,...args){if(source===shared)throw Error('Restricted shared canvas cannot enter a 2D HUD');return originalDrawImage.call(this,source,...args);};
            window.wx={getWindowInfo:()=>({windowWidth:fixture.size.width,windowHeight:fixture.size.height,pixelRatio:3,safeArea:{left:12,top:0,right:fixture.size.width-12,bottom:fixture.size.height-10}}),
                getMenuButtonBoundingClientRect:()=>({bottom:40}),
                setEnableDebug:({enableDebug})=>{fixture.debug=enableDebug;},
                setDeviceOrientation:({value,complete})=>{fixture.orientation=value;complete();},
                createCanvas:()=>{const c=document.createElement('canvas');if(!mainCanvas){mainCanvas=c;document.body.appendChild(c);}return c;},createImage:()=>{fixture.imageCount=(fixture.imageCount||0)+1;return new Image();},
                getFileSystemManager:()=>({readFile:({filePath,encoding,success,fail})=>bytes(filePath).then(data=>success({data:encoding==='utf8'?new TextDecoder().decode(data):data})).catch(fail),readFileSync:file=>new TextDecoder().decode(buffers.get(file))}),
                loadSubpackage:({name,success,fail})=>{
                    fixture.packageAttempts.push(name);fixture.peakDownloads=Math.max(fixture.peakDownloads,++fixture.activeDownloads);let report=()=>{};
                    setTimeout(()=>{report({progress:50,totalBytesWritten:500,totalBytesExpectedToWrite:1000});fixture.activeDownloads--;
                        if(name==='managed'&&(fixture.failPackages||fixture.packageAttempts.filter(n=>n===name).length===1)){fail({errMsg:'fixture network failure',errCode:1001});return;}
                        fixture.loadedPackages.add(name==='managed'?'runtime':name);success();},5);
                    return {onProgressUpdate:callback=>{report=callback;}};
                },getStorageSync:key=>storage.get(key),setStorageSync:(key,value)=>storage.set(key,value),
                createInnerAudioContext:()=>({onError(){},play(){},pause(){},stop(){},destroy(){}}),
                showModal:options=>{fixture.modals.push(options);if(options.title==='上次加载未完成')setTimeout(()=>options.success({confirm:true}),1);},showToast:options=>fixture.toasts.push(options),
                authorize:({success,fail})=>fixture.authorizeError?fail(fixture.authorizeError):success(),getOpenDataContext:()=>({canvas:shared,postMessage:message=>{fixture.boardMessages.push(message);fixture.openDataMessage(message);}})};
            for(const name of ['TouchStart','TouchMove','TouchEnd','TouchCancel','Hide','Show','WindowResize','MemoryWarning'])wx['on'+name]=fn=>events[name]=fn;
            fixture.tap=(x,y)=>{events.TouchStart({changedTouches:[{identifier:1,clientX:x,clientY:y}]});events.TouchEnd({changedTouches:[{identifier:1,clientX:x,clientY:y}]});};
        });
        await page.evaluate(source=>{
            const host={getSharedCanvas:()=>fixture.sharedCanvas,onMessage:fn=>fixture.openDataMessage=fn,
                getFriendCloudStorage:({keyList,success})=>success({data:Array.from({length:18},(_,i)=>({nickname:'好友 '+(i+1),KVDataList:[{key:keyList[0],value:String(900-i*20)}]}))}),
                getUserCloudStorage:({success})=>success({KVDataList:[]}),setUserCloudStorage:({success})=>success({})};
            new Function('wx',source)(host);
        },fs.readFileSync(path.join(pkg,'open-data/index.js'),'utf8'));
        // Test-only save fixture in the simulated host; no device/user storage is touched.
        const catalog=require('../Config/GameplayCatalog.json'),profile=structuredClone(catalog.defaultProfile);
        profile.walletGold=1000;profile.eligible.characters=['peachy'];profile.completedQuests.push('quest_character_peachy');
        await page.evaluate(save=>fixture.storage.set('HEngine.StarbloomSurvivor.CSharp.v4',save),JSON.stringify(profile));
        if(process.argv.includes('--baseline'))await page.evaluate(()=>{fixture.baseline=true;});
        if(process.argv.includes('--previous-startup'))await page.evaluate(()=>fixture.storage.set('HEngine.StarbloomSurvivor.WeChat.diagnostic',{phase:'wasm:native-instantiate',time:123}));
        if(process.argv.includes('--loading-capture'))await page.evaluate(()=>{fixture.pauseNative=true;});
        if(process.argv.includes('--ios-interop'))await page.evaluate(()=>{fixture.rejectJitTables=true;fixture.zeroArity=true;});
        if(process.argv.includes('--expect-table-failure'))await page.evaluate(()=>{fixture.expectTableFailure=true;});
        if(process.argv.includes('--package-failure'))await page.evaluate(()=>{fixture.failPackages=true;});
        await page.addScriptTag({content:bundled});
        if(process.argv.includes('--loading-capture')){await page.waitForFunction(()=>fixture.resumeNative);await page.screenshot({path:path.join(out,'ios-startup-loading.png')});await page.evaluate(()=>fixture.resumeNative());}
        await page.waitForFunction(()=>window.HEGame?.metrics.frames>0||fixture.modals.some(m=>m.title!=='上次加载未完成')||(fixture.expectTableFailure&&fixture.tableFailure),null,{timeout:90000});
        if(process.argv.includes('--expect-table-failure')){
            const failure=await page.evaluate(()=>({tableFailure:fixture.tableFailure,growth:fixture.tableGrowth,diagnostic:fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic'),ready:!!window.HEGame}));
            assert.equal(failure.tableFailure,true);assert.equal(failure.ready,false);assert.ok(failure.growth.some(n=>n>64));
            fs.writeFileSync(path.join(out,'ios-table-negative-control.json'),JSON.stringify(failure,null,2));
            console.log('test-layer PASS (expected old-package failure): '+JSON.stringify({growth:failure.growth,phase:failure.diagnostic.phase}));return;
        }
        if(process.argv.includes('--package-failure')){
            const failure=await page.evaluate(()=>({modal:fixture.modals[0],attempts:fixture.packageAttempts,diagnostic:fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic')}));
            assert.equal(failure.attempts.length,3);assert.equal(failure.modal.title,'资源下载未完成');
            assert.match(failure.modal.content,/managed.*fixture network failure.*1001/);
            assert.equal(failure.diagnostic.phase,'failed:packages');assert.equal(failure.diagnostic.download.code,1001);
            fs.writeFileSync(path.join(out,'package-failure.json'),JSON.stringify(failure,null,2));
            console.log('test-layer PASS: permanent package failure retries exactly three times; modal and persisted diagnostic retain package/native error/code');return;
        }
        assert.deepEqual(await page.evaluate(()=>fixture.modals.filter(m=>m.title!=='上次加载未完成')),[]);assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'menu');
        if(!process.argv.includes('--baseline')){
            assert.equal(await page.evaluate(()=>fixture.nativeModules),0);assert.equal(await page.evaluate(()=>fixture.nativeInstantiations),1);assert.equal(await page.evaluate(()=>fixture.imagesAtNativeStart),0,'Wasm compilation precedes image decoding');
            assert.ok(await page.evaluate(()=>HEGame.metrics.loading.pixels<=640*360),'loading raster has its own low-memory budget');
        }
        if(process.argv.includes('--previous-startup')){
            assert.match(await page.evaluate(()=>fixture.modals[0].content),/wasm:native-instantiate/);
            assert.equal(await page.evaluate(()=>fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic.previous').phase),'wasm:native-instantiate');
            assert.equal(await page.evaluate(()=>fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic').phase),'ready');
        }
        if(process.argv.includes('--ios-interop')){assert.deepEqual(await page.evaluate(()=>fixture.tableGrowth),[]);assert.ok(await page.evaluate(()=>fixture.zeroArityExports>100));}
        const startup=await page.evaluate(async()=>{
            const r=HEGame.renderer,buffers=new Set();
            for(const mesh of await Promise.all([...r.meshes.values()]))for(const part of mesh.parts)for(const name of ['position','normal','joints','weights'])
                if(part[name]?.buffer)buffers.add(part[name].buffer);
            return {loadedMeshes:r.meshes.size,loadedSceneItems:r.scene.filter(item=>item.mesh).length,textures:r.textures.size,
                retainedGeometryBytes:[...buffers].reduce((total,b)=>total+b.byteLength,0),wasmMemoryBytes:fixture.wasmMemory?.buffer.byteLength,
                framebuffer:r.diagnostics().size,hudBytesPerUpload:HEGame.ui.rasterWidth*HEGame.ui.rasterHeight*4,context:r.gl.getContextAttributes(),loading:HEGame.metrics.loading,
                loadingReads:fixture.loadingReads,loadingReadBytes:fixture.loadingReadBytes,nativeModules:fixture.nativeModules,nativeInstantiations:fixture.nativeInstantiations,imagesAtNativeStart:fixture.imagesAtNativeStart,tableGrowth:fixture.tableGrowth,zeroArityExports:fixture.zeroArityExports};
        });
        fs.writeFileSync(path.join(out,'startup-'+path.basename(pkg)+'.json'),JSON.stringify(startup,null,2));
        console.log('Startup resource census (not total process memory): '+JSON.stringify(startup));
        if(process.argv.includes('--startup-only'))return;
        const packageConfig=require(path.join(pkg,'he-game-config.js'));
        const startupDownloads=await page.evaluate(()=>({loaded:[...fixture.loadedPackages],attempts:fixture.packageAttempts,peak:fixture.peakDownloads}));
        assert.equal(startupDownloads.peak,1);assert.equal(startupDownloads.attempts.filter(name=>name==='managed').length,2,'transient failure retries without restarting startup');
        assert.deepEqual(startupDownloads.loaded.map(name=>name==='runtime'?'managed':name).sort(),[...packageConfig.subpackages].sort(),'all packages are downloaded before the menu');
        assert.equal(await page.evaluate(()=>fixture.orientation),'landscape');
        assert.equal(await page.evaluate(()=>fixture.debug),false);
        assert.deepEqual(await page.evaluate(()=>HEGame.renderer.diagnostics().size),[1280,720]);
        assert.deepEqual(await page.evaluate(()=>({width:HEGame.ui.rasterWidth,height:HEGame.ui.rasterHeight})),{width:1280,height:720});
        const contextAttributes=await page.evaluate(()=>HEGame.renderer.gl.getContextAttributes());
        assert.equal(contextAttributes.antialias,false);assert.equal(contextAttributes.preserveDrawingBuffer,false);
        assert.equal(await page.evaluate(()=>HEGame.renderer.scene.filter(item=>item.mesh).length),0,'menu does not allocate battle geometry before first frame');
        await page.waitForTimeout(150);
        const idleUploads=await page.evaluate(()=>HEGame.ui.uploadCount);
        await page.waitForTimeout(250);
        assert.equal(await page.evaluate(()=>HEGame.ui.uploadCount),idleUploads,'static lobby does not re-upload HUD');
        assert.equal(await page.evaluate(()=>HEGame.renderer.diagnostics().instancing),false);
        const tapAction=async action=>{await page.waitForFunction(a=>HEGame.ui.buttons.some(b=>b.action===a),action);await page.evaluate(a=>{const {buttons,layout}=HEGame.ui,b=buttons.find(b=>b.action===a);fixture.tap(layout.left+(b.x+b.w/2)*layout.scale,layout.top+(b.y+b.h/2)*layout.scale);},action);};
        const tapValue=async(action,value)=>{await page.waitForFunction(({action,value})=>HEGame.ui.buttons.some(b=>b.action===action&&b.value===value),{action,value});await page.evaluate(({action,value})=>{const {buttons,layout}=HEGame.ui,b=buttons.find(b=>b.action===action&&b.value===value);fixture.tap(layout.left+(b.x+b.w/2)*layout.scale,layout.top+(b.y+b.h/2)*layout.scale);},{action,value});};
        if(process.argv.includes('--leaderboard-failure')){
            await page.evaluate(()=>{fixture.authorizeError={errMsg:'authorize:fail fixture privacy declaration missing',errCode:103};});
            await tapAction('friends');await page.waitForFunction(()=>fixture.modals.some(m=>m.title==='好友榜未能打开'));
            const failure=await page.evaluate(()=>({modal:fixture.modals.find(m=>m.title==='好友榜未能打开'),error:HEGame.metrics.serviceError,stored:fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic').serviceError}));
            assert.match(failure.modal.content,/privacy declaration missing/);assert.match(failure.modal.content,/103/);assert.equal(failure.error.stage,'authorize');assert.deepEqual(failure.error,failure.stored);
            await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='start'));
            await page.evaluate(()=>{fixture.authorizeError=null;});await tapAction('friends');
            await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='friendsClose'));assert.equal(await page.evaluate(()=>HEGame.metrics.serviceError),null);
            assert.deepEqual(errors,[]);assert.deepEqual(await page.evaluate(()=>HEGame.metrics.errors),[]);
            fs.writeFileSync(path.join(out,'leaderboard-authorization-failure.json'),JSON.stringify(failure,null,2));
            console.log('test-layer PASS: leaderboard native authorization error/code shown and persisted, menu restored, later authorization success opens the real open-data renderer');return;
        }
        await page.screenshot({path:path.join(out,'landscape-menu.png')});
        await page.evaluate(()=>{
            const {buttons,layout}=HEGame.ui,b=buttons.find(b=>b.action==='start'),clientX=layout.left+(b.x+b.w/2)*layout.scale,clientY=layout.top+(b.y+b.h/2)*layout.scale;
            fixture.events.TouchStart({changedTouches:[{identifier:11,clientX,clientY}]});
        });
        assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'menu','press alone does not start');
        await page.evaluate(()=>fixture.events.TouchCancel());
        await tapValue('tab','characters');
        await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='selectCharacter'));
        await page.screenshot({path:path.join(out,'landscape-characters.png')});
        const wallet=await page.evaluate(()=>HEGame.snapshot.profile.walletGold);
        await tapValue('confirmBuy','peachy');await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='acceptConfirm'));
        assert.equal(await page.evaluate(()=>HEGame.snapshot.profile.walletGold),wallet,'confirmation does not spend');
        await tapAction('cancelConfirm');assert.equal(await page.evaluate(()=>HEGame.snapshot.profile.walletGold),wallet,'cancel does not spend');
        await tapValue('confirmBuy','peachy');await tapAction('acceptConfirm');
        await page.waitForFunction(()=>HEGame.snapshot.profile.owned.characters.includes('peachy'));
        assert.equal(await page.evaluate(()=>HEGame.snapshot.profile.walletGold),wallet-catalog.products.find(p=>p.contentId==='peachy').price,'actual C# purchase price');
        await tapValue('tab','powers');await tapValue('confirmPower','meta_might');await tapAction('acceptConfirm');
        await page.waitForFunction(()=>HEGame.snapshot.profile.powerUps.meta_might===1);
        await tapValue('tab','settings');
        await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='difficulty'));
        assert.ok(await page.evaluate(()=>HEGame.ui.buttons.filter(b=>b.action==='weaponSlots').every(b=>b.value==='3')));
        await tapValue('tab','home');
        await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='start'));
        await tapAction('friends');await page.waitForTimeout(100);await page.screenshot({path:path.join(out,'landscape-friends.png')});
        const board=await page.evaluate(()=>({size:HEGame.ui.leaderboardSize,rect:HEGame.ui.leaderboardRectangle,message:fixture.boardMessages.at(-1)}));
        assert.ok(Math.abs(board.size[0]/board.size[1]-board.rect[2]/board.rect[3])<.005,'leaderboard pixels match displayed aspect ratio');
        await tapValue('friendsPage','1');await page.waitForTimeout(100);
        assert.equal(await page.evaluate(()=>fixture.boardMessages.at(-1).page),1);
        await tapAction('friendsClose');await page.waitForTimeout(60);
        await page.evaluate(()=>HEGame.command('seed','7'));
        await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='start'));
        await page.evaluate(()=>{
            const {buttons,layout}=HEGame.ui,b=buttons.find(b=>b.action==='start');
            fixture.tap(layout.left+(b.x+b.w/2)*layout.scale,layout.top+(b.y+b.h/2)*layout.scale);
            // The async start service completes after the host has gone to background.
            fixture.events.Hide();
        });
        await page.waitForFunction(()=>HEGame.snapshot.mode==='paused');
        await page.evaluate(()=>fixture.events.Show());await tapAction('resume');
        await page.waitForFunction(()=>HEGame.snapshot.mode==='playing');
        assert.equal(await page.evaluate(()=>fixture.packageAttempts.length),startupDownloads.attempts.length,'Start does not trigger another package download');
        await page.waitForTimeout(1000);await page.screenshot({path:path.join(out,'landscape-game.png')});
        const before=await page.evaluate(()=>({x:HEGame.snapshot.x,z:HEGame.snapshot.z}));
        await page.evaluate(()=>{fixture.events.TouchStart({changedTouches:[{identifier:2,clientX:80,clientY:440}]});fixture.events.TouchMove({changedTouches:[{identifier:2,clientX:125,clientY:440}]});});await page.waitForTimeout(600);
        await page.evaluate(()=>fixture.events.TouchEnd({changedTouches:[{identifier:2}]}));
        assert.ok(await page.evaluate(p=>Math.hypot(HEGame.snapshot.x-p.x,HEGame.snapshot.z-p.z)>.5,before));
        const yaw=await page.evaluate(()=>HEGame.snapshot.cameraYaw);
        await page.evaluate(()=>{
            const e=fixture.events;
            e.TouchStart({changedTouches:[{identifier:3,clientX:90,clientY:430},{identifier:4,clientX:650,clientY:260}]});
            e.TouchMove({changedTouches:[{identifier:3,clientX:130,clientY:430},{identifier:4,clientX:720,clientY:260}]});
        });
        assert.notEqual(await page.evaluate(()=>HEGame.snapshot.cameraYaw),yaw);
        await tapAction('jump');
        await page.waitForTimeout(60);assert.ok(await page.evaluate(()=>HEGame.snapshot.y>0),'jump while moving and looking');
        await page.evaluate(()=>fixture.events.TouchCancel());
        await tapAction('pause');await page.waitForFunction(()=>HEGame.snapshot.mode==='paused');
        await page.screenshot({path:path.join(out,'landscape-paused.png')});
        await tapAction('resume');await page.waitForFunction(()=>HEGame.snapshot.mode==='playing');
        await page.evaluate(()=>fixture.events.Hide());assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'paused');
        await page.evaluate(()=>fixture.events.Show());
        assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'paused','foreground requires explicit resume');
        await tapAction('confirmAbandon');await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='cancelConfirm'));
        assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'paused');
        await tapAction('cancelConfirm');await tapAction('resume');
        await page.evaluate(()=>fixture.events.TouchStart({changedTouches:[{identifier:55,clientX:90,clientY:430}]}));
        console.log('mobile interaction checks passed; waiting for a natural combat upgrade');
        await page.waitForFunction(()=>HEGame.snapshot.mode!=='playing',null,{timeout:90000});
        assert.equal(await page.evaluate(()=>HEGame.snapshot.mode),'upgrade','automatic combat reaches a real upgrade');
        await page.waitForFunction(()=>HEGame.ui.buttons.some(b=>b.action==='upgrade'));
        await page.screenshot({path:path.join(out,'landscape-upgrade.png')});
        await tapAction('upgrade');await page.waitForFunction(()=>HEGame.snapshot.mode==='playing');
        await page.evaluate(()=>fixture.events.TouchMove({changedTouches:[{identifier:55,clientX:160,clientY:430}]}));
        await page.waitForTimeout(120);
        assert.equal(await page.evaluate(()=>HEGame.snapshot.moving),false,'pre-upgrade finger cannot resume stale movement');
        await page.evaluate(()=>fixture.events.TouchEnd({changedTouches:[{identifier:55}]}));
        const roi=await page.evaluate(async()=>{
            const r=HEGame.renderer;r.cullView=false;await r.ensureModel('green_blob');const state={...HEGame.snapshot,enemies:Array.from({length:200},(_,i)=>({kind:'green_blob',x:500+i,z:500,yaw:0})),pickups:[],projectiles:[]};
            r.frame(state,10);const filtered=r.drawCalls;r.interest.enabled=false;r.frame(state,10);const full=r.drawCalls;r.interest.enabled=true;r.cullView=true;return {filtered,full};
        });assert.ok(roi.full-roi.filtered>=200);
        await page.addScriptTag({content:esbuild.buildSync({entryPoints:[path.join(engine,'Engine/Source/Runtime/Platform/Web/SceneRenderer.js')],bundle:true,write:false,format:'iife',globalName:'RendererBaseline'}).outputFiles[0].text});
        const seams=await page.evaluate(()=>{
            const r=HEGame.renderer,gl=r.gl,base=RendererBaseline.SceneRenderer.prototype,bias=r.depthBiasForMesh;
            const mesh={parts:[{...r.upload(new Float32Array([-20,0,-20,20,0,-20,20,0,20,-20,0,20]),new Float32Array([0,1,0,0,1,0,0,1,0,0,1,0]),new Float32Array(8),new Uint16Array([0,2,1,0,3,2])),color:[1,1,1,1],texture:r.white}]};
            const floor=RendererBaseline.trs([0,0,0],[0,0,0,1],[1,1,1]),road=RendererBaseline.trs([0,0,0],[0,0,0,1],[1,1,1]);
            const run=optimized=>{
                let wrong=0,total=0;
                for(let i=0;i<8;i++){
                    r.sortOpaque=optimized;r.depthBiasForMesh=optimized?bias:()=>0;
                    (optimized?r.beginFrame:base.beginFrame).call(r,[i*.013,20,100],[0,0,0]);
                    r.draw({...mesh,path:''},floor,[.1,.9,.1,1]);r.draw({...mesh,path:'Assets/Models/VerdantRift/DirtPaths.hmesh'},road,[.9,.1,.1,1]);r.endFrame();
                    const pixels=new Uint8Array(64*16*4);gl.readPixels(Math.floor(r.canvas.width/2)-32,Math.floor(r.canvas.height/2)-8,64,16,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
                    for(let p=0;p<pixels.length;p+=4){total++;if(pixels[p+1]>pixels[p])wrong++;}
                }
                return {wrong,total};
            };
            const before=run(false),after=run(true);r.sortOpaque=true;r.depthBiasForMesh=bias;
            return {gapMetres:0,before,after};
        });
        assert.ok(seams.before.wrong>0,'reproduce ambiguous same-depth ground/overlay ordering');
        assert.equal(seams.after.wrong,0,'road remains above ground across slight camera motion');
        fs.writeFileSync(path.join(out,'depth-seams.json'),JSON.stringify(seams,null,2));
        console.log('Ground depth regression (synthetic coplanar overlap): '+JSON.stringify(seams));
        const visibility=await page.evaluate(async()=>{
            const r=HEGame.renderer;await r.ensureModel('green_blob');
            const state={...HEGame.snapshot,mode:'playing',enemies:[],pickups:[],projectiles:[]};
            const pixels=()=>{const result=new Uint8Array(r.canvas.width*r.canvas.height*4);r.gl.readPixels(0,0,r.canvas.width,r.canvas.height,r.gl.RGBA,r.gl.UNSIGNED_BYTE,result);return result;};
            r.frame(state,10);const sceneCalls=r.drawCalls,scene=pixels();
            state.enemies=Array.from({length:300},(_,i)=>({kind:'green_blob',x:state.x+(i%20-10)*.7,z:state.z+(Math.floor(i/20)-7)*.7,yaw:i*.4}));
            r.frame(state,10);const crowdCalls=r.drawCalls,crowd=pixels();let changedPixels=0;
            for(let i=0;i<scene.length;i+=4)if(Math.abs(scene[i]-crowd[i])+Math.abs(scene[i+1]-crowd[i+1])+Math.abs(scene[i+2]-crowd[i+2])>15)changedPixels++;
            // Isolate player rasterization from both scenery and projectiles.
            const scenery=r.scene;r.scene=[];
            r.frame({...state,enemies:[]},10);const player=pixels();r.scene=scenery;
            const background=Array.from(player.slice(0,3));let playerPixels=0;
            for(let i=0;i<player.length;i+=4)if(Math.abs(player[i]-background[0])+Math.abs(player[i+1]-background[1])+Math.abs(player[i+2]-background[2])>15)playerPixels++;
            return {sceneCalls,crowdCalls,changedPixels,playerPixels,instancing:r.diagnostics().instancing,cullLeaked:r.gl.isEnabled(r.gl.CULL_FACE),glError:r.gl.getError()};
        });
        assert.ok(visibility.sceneCalls>10,'scenery submitted through compatible draw path');
        assert.ok(visibility.crowdCalls>=visibility.sceneCalls+300,'crowd uses ordinary draws');
        assert.ok(visibility.changedPixels>1000,'crowd is visible in actual framebuffer');
        assert.ok(visibility.playerPixels>100,'player is visible without UI or projectiles');
        assert.equal(visibility.glError,0);assert.equal(visibility.cullLeaked,false,'ground culling does not leak into actors/UI');
        fs.writeFileSync(path.join(out,'compatible-visibility.json'),JSON.stringify(visibility,null,2));
        console.log('Compatible renderer visibility (instancing APIs reject calls): '+JSON.stringify(visibility));
        const performanceCases=await page.evaluate(async()=>{
            const r=HEGame.renderer;await r.ensureModel('green_blob');
            const results=[];
            for(const spacing of [.7,3.8]){
                const state={...HEGame.snapshot,mode:'playing',enemies:Array.from({length:300},(_,i)=>({kind:'green_blob',x:HEGame.snapshot.x+(i%20-10)*spacing,z:HEGame.snapshot.z+(Math.floor(i/20)-7)*spacing,yaw:i*.4})),pickups:[],projectiles:[]};
                const run=optimized=>{
                    r.sortOpaque=optimized;r.cullView=optimized;
                    for(let i=0;i<3;i++)r.frame(state,10+i*.05);
                    const samples=[];for(let i=0;i<12;i++){const start=performance.now();r.frame(state,10+i*.05);r.gl.finish();samples.push(performance.now()-start);}
                    samples.sort((a,b)=>a-b);
                    const pixels=new Uint8Array(r.canvas.width*r.canvas.height*4);r.gl.readPixels(0,0,r.canvas.width,r.canvas.height,r.gl.RGBA,r.gl.UNSIGNED_BYTE,pixels);
                    return {draws:r.drawCalls,binds:r.materialBinds,medianMs:samples[6],p95Ms:samples[11],culledActors:r.culledActors,pixels};
                };
                const before=run(false),after=run(true);let error=0;
                for(let i=0;i<before.pixels.length;i++)error+=Math.abs(before.pixels[i]-after.pixels[i]);
                results.push({spacing,before:{draws:before.draws,binds:before.binds,medianMs:before.medianMs,p95Ms:before.p95Ms},after:{draws:after.draws,binds:after.binds,medianMs:after.medianMs,p95Ms:after.p95Ms,culledActors:after.culledActors},meanPixelError:error/before.pixels.length});
            }
            return results;
        });
        for(const result of performanceCases){
            assert.ok(result.after.binds<result.before.binds*.35,'ordinary draw path cuts repeated material binding');
            assert.ok(result.meanPixelError<1,'conservative culling and material sorting preserve visible pixels');
        }
        fs.writeFileSync(path.join(out,'ordinary-render-performance.json'),JSON.stringify(performanceCases,null,2));
        console.log('Ordinary draw performance (instancing disabled): '+JSON.stringify(performanceCases));
        await page.evaluate(async()=>{
            fixture.events.Hide();const r=HEGame.renderer;
            await Promise.all(r.scene.map(async item=>{if(!item.mesh)item.mesh=await r.loadMesh(item.path);r.updateSceneBounds(item);}));
        });
        const groundNames={star:'NorthRidgeUpper',thunder:'WestShrine',water:'Foundation',wind:'EastBasin'},regionResults=[];
        for(const [id,region] of Object.entries(catalog.regions)){
            const result=await page.evaluate(({position,ground})=>{
                const r=HEGame.renderer,[x,y,z]=position;
                const state={...HEGame.snapshot,mode:'playing',x,y,z,enemies:[],pickups:[],projectiles:[]};
                const views=[];
                for(const yaw of [0,Math.PI/2,Math.PI,Math.PI*1.5]){
                    r.frame({...state,cameraYaw:yaw},10);
                    views.push({yaw,foundation:r.visibleScenePaths.some(p=>p.endsWith('/TerrainPlate_Foundation.hmesh')),ground:r.visibleScenePaths.some(p=>p.endsWith('/TerrainPlate_'+ground+'.hmesh')),draws:r.drawCalls});
                }
                const length=Math.hypot(x,z),boundary=[];
                for(const d of [54.8,55,55.2]){r.frame({...state,x:x/length*d,z:z/length*d,cameraYaw:0},10);boundary.push(r.visibleScenePaths.some(p=>p.endsWith('/TerrainPlate_Foundation.hmesh')));}
                r.frame({...state,cameraYaw:0},10);
                return {views,boundary,glError:r.gl.getError()};
            },{position:region.authoredPosition,ground:groundNames[id]});
            assert.ok(result.views.every(v=>v.foundation&&v.ground),'region ground survives all view directions: '+id);
            assert.ok(result.boundary.every(Boolean),'ground does not pop across the old 55 m boundary: '+id);
            assert.equal(result.glError,0);
            regionResults.push({id,...result});
            await page.screenshot({path:path.join(out,'region-'+id+'.png')});
        }
        fs.writeFileSync(path.join(out,'region-visibility.json'),JSON.stringify(regionResults,null,2));
        console.log('Four-region visibility PASS: all ground retained from four camera directions and across the old origin-radius boundary');
        await page.evaluate(()=>fixture.events.Show());await tapAction('resume');
        await page.evaluate(()=>{fixture.size={width:390,height:844};fixture.events.WindowResize();});await page.setViewportSize({width:390,height:844});await page.waitForTimeout(100);await page.screenshot({path:path.join(out,'portrait-game.png')});
        await tapAction('pause');await tapAction('confirmAbandon');await tapAction('acceptConfirm');
        await page.waitForFunction(()=>HEGame.snapshot.mode==='result');
        await page.screenshot({path:path.join(out,'portrait-result.png')});
        await tapAction('home');await page.waitForFunction(()=>HEGame.snapshot.mode==='menu');
        await page.screenshot({path:path.join(out,'portrait-menu.png')});
        const saved=await page.evaluate(()=>({value:HEGame.save(),stored:fixture.storage.get('HEngine.StarbloomSurvivor.CSharp.v4')}));
        assert.equal(saved.value,saved.stored,'settlement persisted');
        for(const [width,height] of [[568,320],[667,375],[844,390]]){
            await page.evaluate(({width,height})=>{fixture.size={width,height};fixture.events.WindowResize();},{width,height});
            await page.setViewportSize({width,height});await page.waitForTimeout(120);
            assert.ok(await page.evaluate(()=>{const {buttons,layout}=HEGame.ui;return buttons.filter(b=>b.action).every(b=>b.w*layout.scale>=44&&b.h*layout.scale>=44&&b.x>=0&&b.y>=0&&b.x+b.w<=layout.width+.01&&b.y+b.h<=layout.height+.01);}),'phone touch targets remain large and safe');
            await page.screenshot({path:path.join(out,`menu-${width}x${height}.png`)});
        }
        await page.evaluate(()=>fixture.events.MemoryWarning({level:10}));await page.waitForTimeout(120);
        const memory=await page.evaluate(()=>({warnings:HEGame.metrics.memoryWarnings,phase:fixture.storage.get('HEngine.StarbloomSurvivor.WeChat.diagnostic').phase,
            scene:HEGame.renderer.diagnostics().size,hud:[HEGame.ui.rasterWidth,HEGame.ui.rasterHeight],cachedRequests:HEGame.renderer.requests.size,glError:HEGame.renderer.gl.getError()}));
        assert.equal(memory.warnings,1);assert.equal(memory.phase,'playing');assert.ok(memory.scene[0]*memory.scene[1]<=960*540);
        assert.ok(memory.hud[0]*memory.hud[1]<=960*540);assert.equal(memory.cachedRequests,0);assert.equal(memory.glError,0);
        fs.writeFileSync(path.join(out,'memory-pressure.json'),JSON.stringify(memory,null,2));
        assert.deepEqual(await page.evaluate(()=>HEGame.metrics.errors),[]);
        assert.deepEqual(errors,[]);assert.deepEqual(await page.evaluate(()=>fixture.modals.filter(m=>m.title!=='上次加载未完成')),[]);
        console.log('test-layer PASS: actual exported C# game in simulated WX browser host; mobile lobby/characters/purchase cancel+confirm/growth/settings/release/friends/stick/multi-touch look/jump/pause/resume/background/abandon confirmation/settlement/save/natural combat upgrade + stale finger reset + background start, small phone layouts and portrait resize, strict WX Module path; distant-actor draw comparison '+JSON.stringify(roi));
    }finally{if(browser)await browser.close();server.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
