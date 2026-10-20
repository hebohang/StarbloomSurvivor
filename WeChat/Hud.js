import {CanvasUI} from '@hengine/web/CanvasUI.js';

export const title=item=>item?.name?.zh_cn||item?.title?.zh_cn||'未知内容';
export const purchasePrice=(catalog,id)=>catalog.products.find(p=>p.contentId===id)?.price;
const ink='#29394d',mint='#a8efd6',gold='#ffe4a0',muted='#c1cddd';
const has=(values,id)=>(values||[]).includes(id);

export function mobileControls(w,h) {
    const radius=Math.max(32,Math.min(54,Math.min(w,h)*.14));
    return {
        radius,stick:{x:Math.max(radius+16,w*.16),y:h-radius-24},
        jump:{x:w-58,y:h-64,radius:30},
        pause:{x:w-34,y:28,radius:24},
        isMovement:(x,y)=>x<w*.42&&y>h*.4,
        isLook:x=>x>=w*.42
    };
}

// The shared C# session owns combat, unlocks, prices and saves.
export function paintHud(ctx,w,h,{snapshot:s,catalog,images,stick,tab='home',page=0,confirmation=null,backdrop={x:0,y:0,width:w,height:h}}) {
    const ui=new CanvasUI(ctx),buttons=ui.targets;
    const panel=(x,y,width,height,color,r=12)=>ui.panel(x,y,width,height,color,r);
    const text=(value,x,y,size=16,color=ink,maxWidth)=>ui.text(value,x,y,{size,color,maxWidth});
    const button=(label,x,y,width,action,value='',color=mint,height=48,hitBounds=null)=>
        ui.button(label,{x,y,w:width,h:height},{action,value,hitBounds:hitBounds||{x,y,w:width,h:height},background:action?color:muted,radius:12,textColor:ink,fontSize:17});
    const icon=(path,x,y,size)=>{const image=images.get(path);if(image&&size>0)ctx.drawImage(image,x,y,size,size);return !!image;};
    if(s.mode==='menu') {
        ui.imageCover(images.get('Assets/UI/Backgrounds/starbloom_title_bg.png'),backdrop);
        panel(backdrop.x,backdrop.y,backdrop.width,backdrop.height,'rgba(13,25,43,.72)',0);
        text('小树保卫者',16,32,w<500?18:24,gold,w-250);
        text('星币 '+s.profile.walletGold,w-226,30,16,gold,126);
        button(tab==='settings'?'返回':'设置',w-92,4,80,'tab',tab==='settings'?'home':'settings',muted,44);
        const tabs=[['冒险','home'],['伙伴','characters'],['军械','weapons'],['成长','powers'],['任务','quests']];
        const gap=6,margin=12,contentW=w-margin*2;
        const navW=(contentW-gap*4)/5;
        tabs.forEach(([label,id],i)=>button(label,margin+i*(navW+gap),h-56,navW,'tab',id,tab===id?mint:muted,48));
        if(tab==='home') {
            const character=catalog.characters.find(c=>c.id===s.character);
            const wide=w>=600,cardW=wide?Math.min(420,w*.52):contentW;
            const compact=h<340,x=wide?24:margin,cardH=Math.min(140,h-(compact?192:216));
            panel(x,58,cardW,cardH,'rgba(245,247,249,.95)');
            const size=Math.min(84,cardH-16);
            icon(character?.icon,x+12,66,size);
            text(title(character),x+size+24,86,22,ink,cardW-size-36);
            text('自动攻击 · 摇杆移动',x+size+24,114,16,ink,cardW-size-36);
            if(cardH>=112)text('右侧滑动转向 · 点击跳跃',x+size+24,140,14,ink,cardW-size-36);
            if(wide){text('守护小树，点亮四域',x+cardW+24,90,22,gold,w-cardW-72);text('随时暂停，安心冒险',x+cardW+24,122,16,'#fff',w-cardW-72);}
            const difficulty=catalog.difficulties.find(d=>d.id===s.profile.selectedDifficulty);
            if(!compact)text(`难度：${title(difficulty)}  ·  武器槽：${s.profile.selectedWeaponSlotLimit||3}`,margin,h-132,16,'#fff',contentW);
            button(compact?`开始冒险 · ${title(difficulty)}`:'开始冒险',margin,h-118,contentW-112,'start','',mint,52);
            button('好友榜',w-112,h-118,100,'friends','',gold,52);
        } else {
            const items=tab==='powers'?catalog.metaPowerUps.map(p=>({...catalog.power_ups?.find(v=>v.id===p.id),...p})):
                tab==='quests'?catalog.quests:tab==='weapons'?[...catalog.weapons,...catalog.tomes,...catalog.trinkets]:
                tab==='settings'?[...catalog.difficulties.map(d=>({...d,action:'difficulty'})),
                    ...[3,4,5,6].map(n=>({id:String(n),name:{zh_cn:n+' 个武器槽'},action:'weaponSlots'})),
                    ...catalog.challenges.map(c=>({...c,action:'challenge'}))]:catalog.characters;
            const top=58,bottom=h-114,columns=Math.max(1,Math.floor(contentW/330));
            const rows=Math.max(1,Math.floor((bottom-top)/72)),count=rows*columns,pages=Math.max(1,Math.ceil(items.length/count));
            page=Math.max(0,Math.min(page,pages-1));
            const cellW=(contentW+8)/columns,rowH=(bottom-top)/rows;
            items.slice(page*count,(page+1)*count).forEach((item,i)=>{
                const x=margin+(i%columns)*cellW,y=top+Math.floor(i/columns)*rowH,width=cellW-8,height=rowH-8;
                panel(x,y,width,height,'#edf1f3');
                const cy=y+height/2,hasIcon=icon(item.icon,x+8,cy-22,44);
                const tx=x+(hasIcon?60:12),tw=width-(hasIcon?188:140);
                text(title(item),tx,cy-3,17,ink,tw);
                let label='',action=null,value=item.id,detail='';
                if(tab==='characters'||tab==='weapons') {
                    const group=tab==='characters'?'characters':catalog.weapons.includes(item)?'weapons':catalog.tomes.includes(item)?'tomes':'trinkets';
                    const owned=has(s.profile.owned[group],item.id),eligible=has(s.profile.eligible?.[group],item.id);
                    if(owned){label=tab==='characters'?(s.character===item.id?'已出战':'出战'):(has(s.profile.poolDisabled?.[group],item.id)?'已封印':'已启用');action=tab==='characters'?'selectCharacter':'togglePool';}
                    else {const price=purchasePrice(catalog,item.id);label=eligible?(s.profile.walletGold>=price?'购买':'星币不足'):'未解锁';detail=eligible?`${price} 星币`:'完成任务解锁';action=eligible&&s.profile.walletGold>=price?'confirmBuy':null;}
                } else if(tab==='powers') {
                    const level=s.profile.powerUps?.[item.id]||0,price=item.prices[level];
                    const prerequisite=item.levelPrerequisites?.[level];
                    const unlocked=(!item.unlockId||has(s.profile.completedQuests,item.unlockId))&&(!prerequisite||s.profile.difficultyClears?.[prerequisite]);
                    detail=`等级 ${level} / ${item.maxLevel}`;
                    label=level>=item.maxLevel?'已满级':!unlocked?'未解锁':s.profile.walletGold<price?'星币不足':`${price} 星币`;
                    action=level<item.maxLevel&&unlocked&&s.profile.walletGold>=price?'confirmPower':null;
                } else if(tab==='quests') {
                    detail=`${Math.floor(s.profile.questProgress[item.id]||0)} / ${item.target}`;
                    const complete=has(s.profile.completedQuests,item.id);
                    label=complete?'已完成':has(s.profile.trackedQuests,item.id)?'取消追踪':'追踪';action=complete?null:'trackQuest';
                } else {
                    const selected=item.action==='difficulty'?s.profile.selectedDifficulty===item.id:item.action==='weaponSlots'?s.profile.selectedWeaponSlotLimit===Number(item.id):has(s.profile.selectedChallenges,item.id);
                    const unlocked=item.action==='difficulty'?(!item.unlockId||has(s.profile.completedQuests,item.unlockId)):item.action==='weaponSlots'?Number(item.id)<=Math.min(6,3+(s.profile.powerUps?.meta_weapon_slots||0)):true;
                    label=!unlocked?'未解锁':selected?'已选择':'选择';action=unlocked?item.action:null;
                }
                if(detail)text(detail,tx,cy+19,13,ink,tw);
                button(label,x+width-120,cy-24,112,action,value,mint,48,{x,y,w:width,h:height});
            });
            button('上一页',margin,h-108,100,page>0?'page':null,'-1',muted,44);
            text(`${page+1} / ${pages}`,w/2-24,h-80,16,'#fff');
            button('下一页',w-112,h-108,100,page+1<pages?'page':null,'1',muted,44);
        }
    } else {
        const controls=mobileControls(w,h),hudW=Math.min(210,w*.48);
        panel(8,4,hudW,64,'rgba(245,247,249,.94)');
        text(`生命 ${Math.ceil(s.health)} / ${Math.ceil(s.maxHealth)}`,20,26,15);
        panel(20,34,hudW-24,8,'#d9dfe6',4);
        if(s.health>0)panel(20,34,(hudW-24)*Math.min(1,s.health/Math.max(1,s.maxHealth)),8,'#ee8b9c',4);
        text(`等级 ${s.level}   击败 ${s.kills}`,20,60,14);
        text(`${Math.floor(s.elapsed/60).toString().padStart(2,'0')}:${Math.floor(s.elapsed%60).toString().padStart(2,'0')}`,w*.62-28,30,22,gold);
        text('四域净化 '+s.regions.filter(r=>r.state==='ACTIVATED').length+' / 4',12,90,15,gold);
        if(s.mode==='playing') {
            const {pause,jump,radius}=controls;
            button('暂停',pause.x-pause.radius,pause.y-pause.radius,pause.radius*2,'pause','',gold,pause.radius*2);
            const sx=stick.id==null?controls.stick.x:stick.originX,sy=stick.id==null?controls.stick.y:stick.originY;
            ctx.strokeStyle='#ffffff99';ctx.lineWidth=2;ctx.beginPath();ctx.arc(sx,sy,radius,0,Math.PI*2);ctx.stroke();
            ctx.fillStyle='#a8efd6bb';ctx.beginPath();ctx.arc(sx+(stick.x||0)*radius*.65,sy+(stick.y||0)*radius*.65,radius*.32,0,Math.PI*2);ctx.fill();
            button('跳跃',jump.x-jump.radius,jump.y-jump.radius,jump.radius*2,'jump','',mint,jump.radius*2);
        } else {
            panel(backdrop.x,backdrop.y,backdrop.width,backdrop.height,'rgba(10,20,35,.72)',0);
            const upgrade=s.mode==='upgrade',width=upgrade?w-24:Math.min(w-24,480),height=Math.min(h-16,upgrade?440:294),x=(w-width)/2,y=(h-height)/2;
            panel(x,y,width,height,'#f0f3f5');
            text(upgrade?'选择星光力量':s.mode==='paused'?'冒险暂停':s.mode==='revive'?'再试一次':'本次冒险结束',x+20,y+36,24);
            if(upgrade) {
                const vertical=w<500,count=Math.max(1,s.choices.length),areaH=height-120;
                s.choices.forEach((c,i)=>{
                    const item=[...catalog.weapons,...catalog.tomes].find(v=>v.id===c.id);
                    const cw=vertical?width-32:(width-32-8*(count-1))/count,ch=vertical?(areaH-8*(count-1))/count:areaH;
                    const cx=x+16+(vertical?0:i*(cw+8)),cy=y+52+(vertical?i*(ch+8):0),size=Math.max(0,Math.min(72,vertical?ch-12:ch-84));
                    panel(cx,cy,cw,ch,'#fff');buttons.push({x:cx,y:cy,w:cw,h:ch,action:'upgrade',value:c.id});
                    icon(item?.icon,vertical?cx+8:cx+(cw-size)/2,cy+8,size);
                    const tx=vertical?cx+size+20:cx+10,tw=vertical?cw-size-30:cw-20;
                    text(title(item),tx,vertical?cy+ch/2-5:cy+ch-40,17,ink,tw);
                    text(c.currentLevel>0?`等级 ${c.currentLevel} → ${c.nextLevel}`:`解锁 · 等级 ${c.nextLevel||1}`,tx,vertical?cy+ch/2+18:cy+ch-16,14,ink,tw);
                    if(!vertical&&ch>=200){
                        const description=item?.description?.zh_cn||'',lineLength=Math.max(1,Math.floor((cw-24)/14));
                        for(let line=0;line<2;line++)text(description.slice(line*lineLength,(line+1)*lineLength),cx+12,cy+110+line*22,14,ink,cw-24);
                    }
                });
                button(`重抽 (${s.rerolls||0})`,x+16,y+height-56,(width-40)/2,s.rerolls>0?'reroll':null,'',gold);
                button(`跳过 (${s.skips||0})`,x+24+(width-40)/2,y+height-56,(width-40)/2,s.skips>0?'skip':null,'',muted);
            } else {
                const body=s.mode==='paused'?'左手摇杆移动，右侧滑动转向':s.mode==='revive'?'完整观看视频，恢复一半生命':`生存 ${Math.floor(s.elapsed)} 秒 · 击败 ${s.kills}`;
                text(body,x+20,y+70,16,ink,width-40);
                const by=y+height-120;
                if(s.mode==='paused'){button('继续冒险',x+20,by,width-40,'resume');button('结算并返回大厅',x+20,by+58,width-40,'confirmAbandon','',muted);}
                if(s.mode==='revive'){button('观看广告复活',x+20,by,width-40,'watchRevive');button('结束本次冒险',x+20,by+58,width-40,'declineRevive','',muted);}
                if(s.mode==='result'){text(s.message||'',x+20,y+100,15,ink,width-40);button('返回大厅',x+20,by+58,width-40,'home');}
            }
        }
    }
    if(confirmation) {
        buttons.length=0;
        panel(backdrop.x,backdrop.y,backdrop.width,backdrop.height,'rgba(10,20,35,.8)',0);
        const width=Math.min(w-24,440),height=Math.min(h-16,220),x=(w-width)/2,y=(h-height)/2;
        panel(x,y,width,height,'#f0f3f5');
        text(confirmation.title,x+20,y+40,23,ink,width-40);
        text(confirmation.message,x+20,y+82,16,ink,width-40);
        button('取消',x+16,y+height-64,(width-40)/2,'cancelConfirm','',muted);
        button('确认',x+24+(width-40)/2,y+height-64,(width-40)/2,'acceptConfirm','',mint);
    }
    return {buttons,page};
}
