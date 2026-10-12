using System.Text.Json.Nodes;
using System.Numerics;
using HEngine;

namespace GameScripts;

public sealed partial class SurvivorNativeGame
{
    private sealed class NativeEffect
    {
        public int Handle = -1;
        public string Path = "";
        public double[] Position = [0,0,0], Forward = [0,0,1];
        public double Scale = 1, Speed = 1, Opacity = 1;
    }
    private readonly Dictionary<string,NativeEffect> mEffects = new();
    private readonly List<NativeEffect> mTransientEffects = new();
    private long mEffectSequence;
    private readonly Dictionary<string, (Entity Entity, string Path)> mProjectileBodies = new();
    private readonly Dictionary<string, Stack<Entity>> mProjectileBodyPool = new();
    private int EffectLimit => Text(mSettings,"ParticleDensity") switch {"low"=>24,"medium"=>48,_=>96};
    private string WeaponEffect(string weapon,string phase) => mCatalog["nativeWeaponVfx"]?[weapon]?[phase+"Vfx"]?.GetValue<string>()??"";
    private string CommonEffect(string name) => mCatalog["nativeCommonVfx"]![name]!.GetValue<string>();
    private static int PlayEffect(NativeEffect effect) => SceneServices.Call<int>("vfx.play",new {path=effect.Path,position=effect.Position,forward=effect.Forward,scale=effect.Scale,speed=effect.Speed,opacity=effect.Opacity});
    private static bool UpdateEffect(NativeEffect effect,bool paused) => SceneServices.Call<bool>("vfx.update",new {handle=effect.Handle,position=effect.Position,forward=effect.Forward,paused,opacity=effect.Opacity});
    private static void StopEffect(NativeEffect effect) { if(effect.Handle>=0)SceneServices.Call<bool>("vfx.stop",new {handle=effect.Handle}); }
    private void ClearNativeEffects()
    {
        foreach(var effect in mEffects.Values.Concat(mTransientEffects))StopEffect(effect);
        mEffects.Clear();mTransientEffects.Clear();
        foreach(var body in mProjectileBodies.Values)body.Entity.Destroy();
        foreach(var pool in mProjectileBodyPool.Values)foreach(var entity in pool)entity.Destroy();
        mProjectileBodies.Clear();mProjectileBodyPool.Clear();
    }
    private void PresentNativeEffects()
    {
        string mode=Text(mSnapshot,"mode");if(mode=="menu"||mode=="result"){ClearNativeEffects();return;}
        bool paused=mode!="playing";var live=new HashSet<string>();
        void Follow(string id,string path,JsonNode item,double height,double scale=1,double speed=1,double dx=0,double dz=1,bool hostile=false)
        {
            if(path.Length==0||live.Count>=EffectLimit)return;
            live.Add(id);
            if(!mEffects.TryGetValue(id,out var effect))mEffects[id]=effect=new(){Path=path,Scale=scale,Speed=speed};
            effect.Position=[Number(item,"x"),Number(item,"y")+height,Number(item,"z")];effect.Forward=[dx,0,dz];
            effect.Opacity=hostile?1:Number(mSettings,"ProjectileOpacity");
            if(effect.Handle<0||!UpdateEffect(effect,paused)){effect.Handle=PlayEffect(effect);if(effect.Handle>=0&&paused)UpdateEffect(effect,true);}
        }
        var liveBodies = new HashSet<string>();
        foreach(var node in mSnapshot["projectiles"]!.AsArray())
        {
            var p=node!;if(p["id"]==null)continue;string weapon=Text(p,"weapon");bool hostile=p["hostile"]?.GetValue<bool>()==true;
            string path=hostile?CommonEffect("enemy-projectile-orange"):WeaponEffect(weapon,"body");
            double dx=Number(p,"vx"),dz=Number(p,"vz");if(dx*dx+dz*dz<.001)dz=1;
            string id="projectile-"+p["id"];
            Follow(id,path,p,.62,weapon=="fireball"?.56:weapon=="moonblade"?.69:.48,1,dx,dz,hostile);
            // Desktop weapons use a mesh core as well as particles in the original presentation.
            string prefab=hostile?"":mCatalog["nativeWeaponVfx"]?[weapon]?["projectilePrefab"]?.GetValue<string>()??"";
            if(prefab.Length==0||liveBodies.Count>=EffectLimit)continue;
            liveBodies.Add(id);
            if(!mProjectileBodies.TryGetValue(id,out var body))
            {
                if(!mProjectileBodyPool.TryGetValue(prefab,out var pool))mProjectileBodyPool[prefab]=pool=new();
                body=(pool.Count>0?pool.Pop():SceneServices.Instantiate(prefab),prefab);
                mProjectileBodies[id]=body;
            }
            var state=body.Entity.State;
            state.Position=new((float)Number(p,"x"),(float)Number(p,"y")+.62f,(float)Number(p,"z"));
            state.Rotation=new(0,(float)Math.Atan2(dx,dz),0);
            state.Scale=new Vector3(weapon switch{"fireball"=>.62f,"moonblade" or "dagger"=>.20f,"bubble"=>.56f,"honeyneedle"=>.18f,"sporecap"=>.50f,"phantombell"=>.48f,"coralanchor"=>.46f,"acornmortar"=>.52f,_=>.48f});
            body.Entity.Apply(state);
        }
        foreach(string id in mProjectileBodies.Keys.Where(id=>!liveBodies.Contains(id)).ToArray())
        {
            var body=mProjectileBodies[id];var state=body.Entity.State;state.Position=new(0,-1000,0);state.Scale=Vector3.Zero;body.Entity.Apply(state);
            mProjectileBodyPool[body.Path].Push(body.Entity);mProjectileBodies.Remove(id);
        }
        foreach(var node in mSnapshot["areas"]!.AsArray())
        {
            var a=node!;bool hostile=a["hostile"]!.GetValue<bool>(),ring=a["ring"]!.GetValue<bool>();
            if(Number(a,"delay")>0&&!hostile)continue;
            string weapon=Text(a,"weapon");
            Follow("area-"+a["id"],hostile?CommonEffect("enemy-zone-telegraph"):WeaponEffect(weapon,"body"),a,.12,Math.Max(.15,Number(a,"radius")/3),ring?1.6:1,hostile:hostile);
        }
        foreach(var node in mSnapshot["enemies"]!.AsArray())
        {
            var enemy=node!;if(Number(enemy,"windup")<=0)continue;
            Follow("warning-"+enemy["id"],CommonEffect(enemy["boss"]!.GetValue<bool>()?"boss-area-telegraph":"enemy-zone-telegraph"),enemy,.08,.7,hostile:true);
        }
        foreach(string id in mEffects.Keys.Where(id=>!live.Contains(id)).ToArray()){StopEffect(mEffects[id]);mEffects.Remove(id);}
        foreach(var effect in mTransientEffects.ToArray())if(!UpdateEffect(effect,paused))mTransientEffects.Remove(effect);
        foreach(var node in mSnapshot["presentationEvents"]!.AsArray())
        {
            var e=node!;long sequence=e["sequence"]!.GetValue<long>();if(sequence<=mEffectSequence)continue;mEffectSequence=sequence;
            string path=WeaponEffect(Text(e,"weapon"),Text(e,"kind"));
            if(path.Length==0||mTransientEffects.Count>=EffectLimit/2)continue;
            var effect=new NativeEffect{Path=path,Position=[Number(e,"x"),Number(e,"y")+.5,Number(e,"z")],Forward=[Number(e,"dx"),0,Number(e,"dz")],Scale=Text(e,"kind")=="cast"?.4:Text(e,"kind")=="body"?.48:.35};
            effect.Handle=PlayEffect(effect);if(effect.Handle>=0){mTransientEffects.Add(effect);if(paused)UpdateEffect(effect,true);}
        }
    }
}
