import {InterestRegion} from './engine/InterestRegion.js';
import { SceneRenderer, trs, quaternion } from './engine/SceneRenderer.js';
export class SurvivorRenderer extends SceneRenderer {
    async initialize(catalog,progress){
        const settings=await this.json('rendering.json');this.interest=new InterestRegion(settings[this.platform]);this.poseCache=new Map();
        return super.initialize({scenePath:catalog.scenePath,models:[...catalog.characters,...catalog.enemies,...catalog.bosses],excludeTags:['Player']},progress);
    }
    frame(state,seconds){
        const menu=state.mode==='menu',px=menu?0:state.x,pz=menu?0:state.z,yaw=state.cameraYaw||0,elevation=state.cameraElevation??Math.atan2(14,17),distance=Math.hypot(14,17),horizontal=distance*Math.cos(elevation),eye=menu?[0,1.8,4.8]:[px+Math.sin(yaw)*horizontal,(state.y||0)+Math.sin(elevation)*distance,pz+Math.cos(yaw)*horizontal],target=menu?[0,.65,0]:[px,state.y||0,pz];
        this.beginFrame(eye,target);this.streamScene(px,pz);
        if(!menu)for(const item of this.scene){const x=item.matrix[12],z=item.matrix[14];if(item.mesh&&this.interest.contains(x,z,px,pz))this.draw(item.mesh,item.matrix);}
        const animationTime=this.interest.animationTime(seconds),posed=this.poseCache;
        const character=(id,x,z,yaw,moving,y=0)=>{
            if(!this.interest.contains(x,z,px,pz))return;
            const model=this.models.get(id);if(!model){this.ensureModel(id).catch(error=>{this.streamError=error;});this.draw(this.primitive,trs([x,y+.4,z],[0,0,0,1],[.3,.5,.3]),[.6,.8,1,1]);return;}const key=id+':'+moving;
            if(posed.get(key)?.time!==animationTime)posed.set(key,{time:animationTime,bones:this.bones(moving?model.run:model.idle,animationTime)});
            this.draw(model.mesh,trs([x,y,z],quaternion(model.upright,yaw,0),[model.scale,model.scale,model.scale]),null,posed.get(key).bones);
        };
        character(state.character,px,pz,menu?Math.sin(seconds*.3)*.4:state.yaw,state.moving,state.y||0);
        if(!menu){
            for(const enemy of state.enemies)character(enemy.kind,enemy.x,enemy.z,enemy.yaw,true,enemy.y||0);
            for(const gem of state.pickups)if(this.interest.contains(gem.x,gem.z,px,pz))this.draw(this.primitive,trs([gem.x,(gem.y||0)+.35,gem.z],quaternion(0,seconds,0),[.16,.24,.16]),[.3,1,.75,1],null,.4);
            for(const p of state.projectiles)if(this.interest.contains(p.x,p.z,px,pz))this.draw(this.primitive,trs([p.x,(p.y||0)+.7,p.z],quaternion(0,seconds*4,0),[p.radius,p.radius,p.radius]),p.color||[1,.75,.2,.9],null,.6);
        }
        this.endFrame();
    }
}
