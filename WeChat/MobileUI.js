import {viewportLayout} from '@hengine/web/ViewportLayout.js';

// Keep at least one screen point per UI unit on small phones.
export function mobileLayout(viewport) {
    const height=Math.max(1,viewport.height-(viewport.top||0)-(viewport.bottom||0));
    const width=Math.max(1,viewport.width-(viewport.left||0)-(viewport.right||0));
    return viewportLayout(viewport,{landscapeHeight:Math.min(390,height),portraitWidth:Math.min(390,width)});
}

// A tap commits on release inside the same target.
export class MobileTap {
    constructor(){this.reset();}
    reset(){this.pending=null;}
    begin(id,x,y,target,mode){
        if(!this.pending)this.pending={id,x,y,target,mode};
    }
    move(id,x,y){
        if(this.pending?.id===id&&Math.hypot(x-this.pending.x,y-this.pending.y)>12)this.reset();
    }
    end(id,x,y,target,mode){
        const p=this.pending;
        if(p?.id!==id)return null;
        this.reset();
        return p.mode===mode&&Math.hypot(x-p.x,y-p.y)<=12&&target?.action===p.target.action&&target?.value===p.target.value?p.target:null;
    }
}
