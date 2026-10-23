import {SurvivorRenderer} from '../Web/renderer.js';
import {withWeChatDepth} from '@hengine/wechat/CompatibleRenderer.js';
import {trs,quaternion} from '@hengine/web/SceneRenderer.js';
import {meshBounds,geometryBounds,transformBounds,nearBounds,visibleBounds} from '@hengine/wechat/Visibility.js';

export class WeChatRenderer extends withWeChatDepth(SurvivorRenderer) {
    constructor(canvas,host){
        const budget={pixels:1280*720,ratio:1.5};
        const viewport=()=>{const v=host.viewport();return {...v,ratio:Math.min(v.ratio||1,budget.ratio,Math.sqrt(budget.pixels/(v.width*v.height)))};};
        super(canvas,{...host,viewport,maxPixelRatio:1.5,deferSceneMeshes:true});
        this.renderBudget=budget;this.cullView=true;this.localBounds=new Map();this.sceneLoads=0;
    }
    async initialize(catalog,progress){
        await super.initialize(catalog,progress);
        const paths=new Set(this.scene.map(item=>item.path));
        for(const definition of this.modelDefinitions.values())paths.add(definition.mesh);
        for(const path of paths)this.localBounds.set(path,meshBounds(await this.json(path))||this.localBounds.get(path)||null);
        for(const item of this.scene)this.updateSceneBounds(item);
    }
    async prepareScene(x=0,z=0){
        // Large terrain meshes contain world-space vertices with a zero object
        // origin. Stream and retain them using their extents, never their origin.
        // Defer scenery until Start: the menu and managed runtime no longer
        // initialize alongside all battle textures and buffers.
        for(const item of this.scene)if(!item.mesh&&nearBounds(item.bounds,x,z,this.interest.radius+this.interest.padding)){item.mesh=await this.loadMesh(item.path);this.updateSceneBounds(item);}
    }
    updateSceneBounds(item){
        let local=this.localBounds.get(item.path);
        if(!local&&item.mesh){local=geometryBounds(item.mesh);this.localBounds.set(item.path,local);}
        item.bounds=transformBounds(local,item.matrix);
    }
    async ensureModel(id){
        const model=await super.ensureModel(id);
        if(model&&!this.localBounds.get(model.mesh.path))this.localBounds.set(model.mesh.path,geometryBounds(model.mesh));
        return model;
    }
    streamScene(x,z){
        if(this.streamError)throw this.streamError;
        for(const item of this.scene){
            if(this.sceneLoads>=2)break;
            if(item.mesh||item.pending||!nearBounds(item.bounds,x,z,this.interest.radius+this.interest.padding))continue;
            item.pending=true;this.sceneLoads++;
            this.loadMesh(item.path).then(mesh=>{item.mesh=mesh;this.updateSceneBounds(item);}).catch(error=>{this.streamError=error;})
                .finally(()=>{item.pending=false;this.sceneLoads--;});
        }
    }
    reduceMemory(){
        this.renderBudget.pixels=Math.min(this.renderBudget.pixels,960*540);this.renderBudget.ratio=Math.min(this.renderBudget.ratio,1);
        // Parsed metadata can be read again if needed. Live models retain their
        // animation objects, and live geometry remains intact.
        this.requests.clear();
    }
    frame(state,seconds){
        const menu=state.mode==='menu',px=menu?0:state.x,pz=menu?0:state.z,yaw=state.cameraYaw||0,elevation=state.cameraElevation??Math.atan2(14,17),distance=Math.hypot(14,17),horizontal=distance*Math.cos(elevation);
        const eye=menu?[0,1.8,4.8]:[px+Math.sin(yaw)*horizontal,(state.y||0)+Math.sin(elevation)*distance,pz+Math.cos(yaw)*horizontal],target=menu?[0,.65,0]:[px,state.y||0,pz];
        this.beginFrame(eye,target);if(!menu)this.streamScene(px,pz);
        this.visibleScenePaths=[];this.culledActors=0;this.culledScene=0;
        if(!menu)for(const item of this.scene){
            if(!item.mesh)continue;
            if((this.interest.enabled&&!nearBounds(item.bounds,px,pz,this.interest.radius))||(this.cullView&&!visibleBounds(item.bounds,this.viewPlanes))){this.culledScene++;continue;}
            this.draw(item.mesh,item.matrix);this.visibleScenePaths.push(item.path);
        }
        const animationTime=this.interest.animationTime(seconds),posed=this.poseCache;
        const character=(id,x,z,yaw,moving,y=0)=>{
            if(!this.interest.contains(x,z,px,pz))return;
            const model=this.models.get(id);
            if(!model){this.ensureModel(id).catch(error=>{this.streamError=error;});this.draw(this.primitive,trs([x,y+.4,z],[0,0,0,1],[.3,.5,.3]),[.6,.8,1,1]);return;}
            const matrix=trs([x,y,z],quaternion(model.upright,yaw,0),[model.scale,model.scale,model.scale]),local=this.localBounds.get(model.mesh.path);
            // Animated limbs may extend beyond the authored bind pose.
            const padding=Math.max(.75,local?(local.max[1]-local.min[1])*model.scale*.5:0);
            if(this.cullView&&!visibleBounds(transformBounds(local,matrix,padding),this.viewPlanes)){this.culledActors++;return;}
            const key=id+':'+moving;
            if(posed.get(key)?.time!==animationTime)posed.set(key,{time:animationTime,bones:this.bones(moving?model.run:model.idle,animationTime)});
            this.draw(model.mesh,matrix,null,posed.get(key).bones);
        };
        character(state.character,px,pz,menu?Math.sin(seconds*.3)*.4:state.yaw,state.moving,state.y||0);
        if(!menu){
            for(const enemy of state.enemies)character(enemy.kind,enemy.x,enemy.z,enemy.yaw,true,enemy.y||0);
            for(const gem of state.pickups)if(this.interest.contains(gem.x,gem.z,px,pz))this.draw(this.primitive,trs([gem.x,(gem.y||0)+.35,gem.z],quaternion(0,seconds,0),[.16,.24,.16]),[.3,1,.75,1],null,.4);
            for(const p of state.projectiles)if(this.interest.contains(p.x,p.z,px,pz))this.draw(this.primitive,trs([p.x,(p.y||0)+.7,p.z],quaternion(0,seconds*4,0),[p.radius,p.radius,p.radius]),p.color||[1,.75,.2,.9],null,.6);
        }
        this.endFrame();
    }
    depthBiasForMesh(mesh){
        // Road/ring surfaces are authored only millimetres above the terrain.
        // Separate those coplanar layers in depth without changing gameplay heights.
        if(mesh.path?.endsWith('/DirtPaths.hmesh'))return -2;
        if(mesh.path?.includes('/EventRing_'))return -4;
        return 0;
    }
    cullBackFacesForMesh(mesh){
        // These authored, non-mirrored ground meshes have CCW upper surfaces.
        // Do not draw inverted road slivers or plate bottoms over supporting ground.
        return /\/(?:TerrainPlate_|TerrainRamp_|DirtPaths\.hmesh)/.test(mesh.path||'');
    }
}
