import {CanvasUI} from '@hengine/web/CanvasUI.js';
import {touchLayout} from '@hengine/web/Input/TouchLayout.js';

const title=item=>item?.name?.zh_cn||item?.title?.zh_cn||'未知内容';
const ink='#29394d',mint='#a8efd6',gold='#ffe4a0';
// Presentation only: catalog/save/commands stay owned by the shared C# game.
export function paintHud(ctx,w,h,{snapshot:s,catalog,images,stick,tab,page,backdrop={x:0,y:0,width:w,height:h}}) {
    const ui=new CanvasUI(ctx),buttons=ui.targets;
    const panel=(x,y,width,height,color,r=12)=>ui.panel(x,y,width,height,color,r);
    const text=(value,x,y,size=16,color=ink,maxWidth)=>ui.text(value,x,y,{size,color,maxWidth});
    const button=(label,x,y,width,action,value='',color=mint,height=38,hitBounds=null)=>
        ui.button(label,{x,y,w:width,h:height},{action,value,hitBounds:hitBounds||{x,y,w:width,h:height},background:color,radius:12,textColor:ink});
    const icon=(path,x,y,size)=>{const image=images.get(path);if(image)ctx.drawImage(image,x,y,size,size);return !!image;};
    if(s.mode==='menu') {
        const bg=images.get('Assets/UI/Backgrounds/starbloom_title_bg.png');
        ui.imageCover(bg,backdrop);
        panel(backdrop.x,backdrop.y,backdrop.width,backdrop.height,'rgba(13,25,43,.72)',0);
        text('小树保卫者',24,46,28,gold);text('星币 '+s.profile.walletGold,w-160,43,16,gold,140);
        const tabs=[['伙伴','characters'],['军械','weapons'],['成长','powers'],['任务','quests'],['设置','settings']];
        const contentX=16,contentW=w-32;
        tabs.forEach(([label,id],i)=>button(label,16+i*(contentW+8)/5,74,(contentW-32)/5,'tab',id,tab===id?mint:'#c1cddd'));
        const top=128,bottom=h-132;
        const items=tab==='powers'?catalog.metaPowerUps.map(p=>({...p,...catalog.power_ups?.find(v=>v.id===p.id)})):tab==='quests'?catalog.quests:tab==='weapons'?[...catalog.weapons,...catalog.tomes,...catalog.trinkets]:tab==='settings'?[...catalog.difficulties.map(d=>({...d,action:'difficulty'})),...[3,4,5,6].map(n=>({id:String(n),name:{zh_cn:n+' 个武器槽'},action:'weaponSlots'})),...catalog.challenges.map(c=>({...c,action:'challenge'}))]:catalog[tab];
        const columns=Math.max(1,Math.floor(contentW/340)),rows=Math.max(1,Math.floor((bottom-top)/66)),count=rows*columns,pages=Math.max(1,Math.ceil(items.length/count));
        page=Math.max(0,Math.min(page,pages-1));const cellW=(contentW+8)/columns,rowH=(bottom-top)/rows;
        items.slice(page*count,(page+1)*count).forEach((item,i)=>{
            const x=contentX+(i%columns)*cellW,y=top+Math.floor(i/columns)*rowH,width=cellW-8;
            panel(x,y,width,rowH-8,'#edf1f3');const cy=y+(rowH-8)/2,hasIcon=icon(item.icon,x+8,cy-20,40);
            text(title(item),x+(hasIcon?56:12),cy+5,15,ink,width-(hasIcon?160:116));
            const bx=x+width-100,by=cy-19;
            if(tab==='characters'){const owned=s.profile.owned.characters.includes(item.id);button(s.character===item.id?'已选择':owned?'选择':'购买',bx,by,90,owned?'selectCharacter':'buy',item.id);}
            else if(tab==='weapons'){const group=catalog.weapons.includes(item)?'weapons':catalog.tomes.includes(item)?'tomes':'trinkets',owned=s.profile.owned[group].includes(item.id);button(owned?(s.profile.poolDisabled[group].includes(item.id)?'已停用':'已启用'):'购买',bx,by,90,owned?'togglePool':'buy',item.id);}
            else if(tab==='powers')button('强化',bx,by,90,'power',item.id);
            else if(tab==='quests')text(`${Math.floor(s.profile.questProgress[item.id]||0)} / ${item.target}`,bx,cy+5,13,ink,90);
            else {const selected=item.action==='difficulty'?s.profile.selectedDifficulty===item.id:item.action==='weaponSlots'?s.profile.selectedWeaponSlotLimit===Number(item.id):s.profile.selectedChallenges.includes(item.id);button(selected?'已选择':'选择',bx,by,90,item.action,item.id);}
        });
        button('上一页',contentX,h-116,100,'page','-1','#c1cddd');text(`${page+1} / ${pages}`,contentX+116,h-91,14,'#ffffff');button('下一页',w-116,h-116,100,'page','1','#c1cddd');
        button('开始冒险',contentX,h-62,Math.max(120,contentW-140),'start','',mint,46);button('好友榜',w-136,h-62,120,'friends','',gold,46);
    } else {
        text('小树保卫者',w*.5-40,15,12,gold);
        const controls=touchLayout(w,h),hudW=Math.min(240,w*.45);
        panel(12,10,hudW,76,'rgba(245,247,249,.94)');text(`生命 ${Math.ceil(s.health)} / ${Math.ceil(s.maxHealth)}`,24,32,14);
        panel(24,41,hudW-24,9,'#d9dfe6',4);if(s.health>0)panel(24,41,(hudW-24)*Math.min(1,s.health/Math.max(1,s.maxHealth)),9,'#ee8b9c',4);
        text(`等级 ${s.level}   击败 ${s.kills}`,24,72,14);
        text(`${Math.floor(s.elapsed/60).toString().padStart(2,'0')}:${Math.floor(s.elapsed%60).toString().padStart(2,'0')}`,w*.5-28,38,22,gold);
        panel(12,96,hudW,34,'rgba(245,247,249,.9)');text('四域净化 '+s.regions.filter(r=>r.state==='ACTIVATED').length+' / 4',24,119,14);
        if(s.mode==='playing') {
            const {pause,jump,radius}=controls;
            button('暂停',pause.x-pause.radius,pause.y-pause.radius,pause.radius*2,'pause','',gold,pause.radius*2);
            const sx=stick.id===null?controls.stick.x:stick.originX,sy=stick.id===null?controls.stick.y:stick.originY;
            ctx.strokeStyle='#ffffff99';ctx.lineWidth=2;ctx.beginPath();ctx.arc(sx,sy,radius,0,Math.PI*2);ctx.stroke();
            ctx.fillStyle='#a8efd6bb';ctx.beginPath();ctx.arc(sx+stick.x*radius*.65,sy+stick.y*radius*.65,radius*.32,0,Math.PI*2);ctx.fill();
            button('跳跃',jump.x-jump.radius,jump.y-jump.radius,jump.radius*2,'jump','',mint,jump.radius*2);
        } else if(s.mode!=='paused') {
            panel(backdrop.x,backdrop.y,backdrop.width,backdrop.height,'rgba(10,20,35,.65)',0);
            const width=s.mode==='upgrade'?w-32:Math.min(w-32,900),height=s.mode==='upgrade'?Math.min(h-32,440):340,x=(w-width)/2,y=(h-height)/2;
            panel(x,y,width,height,'#f0f3f5');text('小树保卫者',x+width-135,y+43,14,ink,110);text(s.mode==='upgrade'?'选择星光力量':s.mode==='paused'?'冒险暂停':s.mode==='revive'?'再试一次':'本次冒险结束',x+24,y+43,24);
            if(s.mode==='upgrade') {
                const count=Math.max(1,s.choices.length),cw=(width-40)/count,cardHeight=height-146,iconSize=Math.min(96,cardHeight-80,cw-32);
                s.choices.forEach((c,i)=>{const item=[...catalog.weapons,...catalog.tomes].find(v=>v.id===c.id),cx=x+20+i*cw;panel(cx,y+68,cw-8,cardHeight,'#ffffff');icon(item?.icon,cx+(cw-8-iconSize)/2,y+82+(cardHeight-80-iconSize)/2,iconSize);button(title(item),cx+8,y+68+cardHeight-60,cw-24,'upgrade',c.id,mint,48,{x:cx,y:y+68,w:cw-8,h:cardHeight});});
                button('重抽',x+24,y+height-58,(width-60)/2,'reroll','',gold);button('跳过',x+36+(width-60)/2,y+height-58,(width-60)/2,'skip','','#d9e2ec');
            }
            if(s.mode==='paused'){button('继续冒险',x+24,y+100,width-48,'resume');button('结算并离开',x+24,y+158,width-48,'abandon','','#d9e2ec');}
            if(s.mode==='revive'){text('完整观看视频，恢复一半生命',x+24,y+90,15,ink,width-48);button('观看广告复活',x+24,y+120,width-48,'watchRevive');button('结束本次冒险',x+24,y+178,width-48,'declineRevive','','#d9e2ec');}
            if(s.mode==='result'){text(s.message,x+24,y+96,15,ink,width-48);button('返回大厅',x+24,y+150,width-48,'home');}
        }
    }
    return {buttons,page};
}
