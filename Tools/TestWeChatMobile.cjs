'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),engine=process.env.HE_ENGINE_ROOT;
if(!engine)throw Error('Set HE_ENGINE_ROOT to the selected engine checkout.');
const esbuild=require(path.join(engine,'Tools/Scripting/node_modules/esbuild'));
const {engineAliases}=require(path.join(engine,'Tools/Build/EngineImports.cjs'));
function load(file){
    const code=esbuild.buildSync({entryPoints:[path.join(root,'WeChat',file)],bundle:true,write:false,format:'iife',globalName:'Module',alias:engineAliases(engine)}).outputFiles[0].text;
    const scope={};vm.runInNewContext(code,scope);return scope.Module;
}
const {paintHud,purchasePrice}=load('Hud.js'),{mobileLayout,MobileTap}=load('MobileUI.js');
const catalog=require('../Config/GameplayCatalog.json');
const profile={walletGold:10000,owned:{characters:['starpaw'],weapons:[],tomes:[],trinkets:[]},eligible:{characters:catalog.characters.map(c=>c.id),weapons:[],tomes:[],trinkets:[]},
    selectedDifficulty:'adventure',selectedWeaponSlotLimit:3,completedQuests:['quest_start'],powerUps:{},poolDisabled:{},questProgress:{},trackedQuests:[],selectedChallenges:[]};
const state={mode:'menu',character:'starpaw',profile,choices:catalog.weapons.slice(0,3).map(c=>({id:c.id})),health:100,maxHealth:100,level:1,kills:0,elapsed:0,regions:[]};
const ctx={save(){},restore(){},rect(){},clip(){},beginPath(){},moveTo(){},arcTo(){},arc(){},stroke(){},fill(){},fillText(){},drawImage(){}};
let checked=0;
for(const [width,height,left,top,bottom] of [[568,320,0,44,10],[667,375,0,44,10],[844,390,44,44,21],[960,540,12,44,10],[1280,720,0,44,0],[320,568,0,44,10],[390,844,0,44,34]]){
    const layout=mobileLayout({width,height,left,right:left,top,bottom}),w=layout.width,h=layout.height;
    for(const mode of ['menu','playing','paused','upgrade','revive','result']){
        state.mode=mode;
        for(const tab of mode==='menu'?['home','characters','weapons','powers','quests','settings']:['home']){
            for(const confirmation of [null,{title:'确认',message:'消耗星币'}]){
                const hud=paintHud(ctx,w,h,{snapshot:state,catalog,images:new Map(),stick:{id:null},tab,page:0,confirmation,backdrop:layout.fullRect});
                for(const b of hud.buttons){
                    assert.ok(b.x>=0&&b.y>=0&&b.x+b.w<=w+.01&&b.y+b.h<=h+.01,`${width}x${height} ${mode}/${tab}: safe bounds ${JSON.stringify(b)}`);
                    if(b.action)assert.ok(b.w*layout.scale>=44&&b.h*layout.scale>=44,`${mode}/${tab} finger target: ${JSON.stringify(b)}`);
                }
                for(let i=0;i<hud.buttons.length;i++)for(let j=i+1;j<hud.buttons.length;j++){
                    const a=hud.buttons[i],b=hud.buttons[j];
                    assert.ok(Math.min(a.x+a.w,b.x+b.w)<=Math.max(a.x,b.x)||Math.min(a.y+a.h,b.y+b.h)<=Math.max(a.y,b.y),`${mode}/${tab}: overlapping targets`);
                }
                if(confirmation)assert.equal(hud.buttons.length,2,'modal isolates commands');
                checked++;
            }
        }
    }
}
const product=catalog.products.find(p=>p.category==='characters');
assert.equal(purchasePrice(catalog,product.contentId),product.price);
state.mode='menu';
let hud=paintHud(ctx,700,350,{snapshot:state,catalog,images:new Map(),stick:{},tab:'settings',page:0});
assert.ok(hud.buttons.filter(b=>b.action==='weaponSlots').every(b=>b.value==='3'),'unpurchased weapon slots unavailable');
const tap=new MobileTap(),target={action:'start',value:''};
tap.begin(1,10,10,target,'menu');assert.equal(tap.end(2,10,10,target,'menu'),null,'second finger cannot confirm');
assert.equal(tap.end(1,10,10,{...target},'menu'),target,'repaint preserves target identity by action/value');
tap.begin(1,10,10,target,'menu');tap.move(1,40,10);assert.equal(tap.end(1,10,10,target,'menu'),null,'drag away and back cancels');
tap.begin(1,10,10,target,'menu');assert.equal(tap.end(1,10,10,target,'playing'),null,'mode change cancels');
tap.begin(1,10,10,target,'menu');tap.reset();assert.equal(tap.end(1,10,10,target,'menu'),null,'cancel clears pending touch');
console.log(`unit-test PASS: ${checked} phone layouts; >=44 point targets, safe bounds, no overlaps, confirmation isolation, catalog prices, unlock gating, release/drag/cancel/multitouch`);
