using System.Diagnostics;
using System.Text.Json.Nodes;
namespace GameScripts.Survivor;
public sealed partial class WebGameSession
{
    public void FixtureCrowd(int count,int projectiles,bool clump=false)
    {
        Start();mAgents.Clear();mProjectiles.Clear();mWeaponSlots.Clear();mSpawnTimer=1e9;mHealth=mMaxHealth=1e9;
        for(int i=0;i<count;i++){Spawn("green_blob",new JsonObject());var e=mAgents[^1];e.X=clump?0:(i%20-10)*2;e.Z=clump?0:(i/20-8)*2;e.Health=e.MaxHealth=1e9;e.AttackPhase=0;}
        for(int i=0;i<projectiles;i++)mProjectiles.Add(new(){X=(i%20-10)*2+.3,Z=(i/20-5)*2+.2,Radius=.3,Life=1e9,Pierce=100,Damage=.1,Weapon="comet",Behavior="projectile"});
#if !BASELINE
        RebuildEnemyIndex();
#endif
    }
    public object FixtureBenchmark()
    {
        double Measure(Action action,int count){for(int i=0;i<10;i++)action();var timer=Stopwatch.StartNew();long before=GC.GetAllocatedBytesForCurrentThread();for(int i=0;i<count;i++)action();timer.Stop();return timer.Elapsed.TotalMilliseconds/count;}
        double projectiles=Measure(()=>{foreach(var p in mProjectiles){p.Hit.Clear();p.Pierce=100;}UpdateProjectiles(0);},150);
        double nearest=Measure(()=>{for(int i=0;i<100;i++)Nearest(i%13-6,i%17-8,12);},50);
        double density=Measure(()=>{CastAreaWeapon("acornmortar","lob_zone",1,4,1,1,mAgents[0]);mAreas.Clear();},15);
        mProjectiles.Clear();double step=Measure(()=>Step(1.0/30,0,0),60);
        var snapshot=JsonNode.Parse(Snapshot())!;int bytes=System.Text.Encoding.UTF8.GetByteCount(Snapshot());
        return new{projectileMs=projectiles,nearest100Ms=nearest,densityMs=density,fullStepMs=step,snapshotBytes=bytes,enemies=mAgents.Count};
    }
#if !BASELINE
    public void FixtureRegionBurst()
    {
        Start();mAgents.Clear();var region=mObjectives.Regions[0];
        for(int i=0;i<40&&region.State!="ASSAULT";i++)mObjectives.Update(.05,region.X,region.Z);
        UpdateEncounters(1.0/30);int first=mAgents.Count;
        mObjectives.Update(1.0/30,region.X,region.Z);UpdateEncounters(1.0/30);
        if(first!=8||mAgents.Count!=first)throw new Exception("Assault opening burst repeated across frames");
    }
    public void FixtureMobileLimit()
    {
        FixtureCrowd(239,0);mEnemyLimit=240;var region=mObjectives.Regions[0];
        for(int i=0;i<40&&region.State!="ASSAULT";i++)mObjectives.Update(.05,region.X,region.Z);
        UpdateEncounters(1.0/30);if(mAgents.Count!=240)throw new Exception("Mobile crowd cap failed");
        Spawn("star_dragon",new JsonObject());if(mAgents.Count!=241||!mAgents[^1].Boss)throw new Exception("Crowd cap blocked objective boss");
    }
    public void FixtureCheckQueries()
    {
        var rng=new Random(25);
        for(int i=0;i<500;i++){
            double x=rng.NextDouble()*80-40,z=rng.NextDouble()*80-40,range=rng.NextDouble()*20+.1;
            var expected=mAgents.Where(e=>e.Health>0&&Distance(e.X-x,e.Z-z)<range).OrderBy(e=>Distance(e.X-x,e.Z-z)).FirstOrDefault();
            if(Nearest(x,z,range)?.Id!=expected?.Id)throw new Exception("Nearest query changed target");
            var p=new Projectile{X=x,Z=z,Radius=range/10};ProjectileCandidates(p);
            var actual=mProjectileCandidates.Where(e=>DistanceSquared(e.X-x,e.Z-z)<=(p.Radius+e.Radius)*(p.Radius+e.Radius)).Select(e=>e.Id);
            var hits=mAgents.Where(e=>Distance(e.X-x,e.Z-z)<=p.Radius+e.Radius).Select(e=>e.Id);
            if(!actual.SequenceEqual(hits))throw new Exception("Projectile candidates lost/reordered hits");
        }
        foreach(double radius in new[]{.2,2,5,20}){
            var expected=mAgents.OrderByDescending(e=>mAgents.Count(n=>Distance(n.X-e.X,n.Z-e.Z)<=radius)).ThenBy(e=>Distance(e.X-mX,e.Z-mZ)).First();
            if(DensestEnemy(radius)!=expected)throw new Exception("Density target changed");
        }
    }
    public string FixtureSeparate()
    {
        for(int tick=0;tick<120;tick++){
            var before=mAgents.Select(e=>(e.X,e.Z)).ToArray();SeparateEnemies(1.0/30);
            for(int i=0;i<mAgents.Count;i++)if(Distance(mAgents[i].X-before[i].X,mAgents[i].Z-before[i].Z)>2.4*.05+1e-9)throw new Exception("Separation teleported actor");
        }
        double spread=mAgents.Average(e=>e.X*e.X+e.Z*e.Z);
        if(spread<1||mAgents.Any(e=>!double.IsFinite(e.X)||!double.IsFinite(e.Z)))throw new Exception("Crowd did not disperse");
        var frozen=mAgents[0];frozen.FreezeRemaining=10;var fixedPosition=(frozen.X,frozen.Z);SeparateEnemies(.05);
        if((frozen.X,frozen.Z)!=fixedPosition)throw new Exception("Frozen enemy moved");
        return string.Join(";",mAgents.Select(e=>$"{e.X:R},{e.Z:R}"));
    }
    public (int Visuals,double Health) FixtureVisuals(int budget)
    {
        mFriendlyVisualBudget=budget;mAreas.Clear();
        for(int i=0;i<100;i++)mAreas.Add(new(){Weapon="comet",Radius=4,Initial=1,Duration=1,VisualCount=24});
        for(int i=0;i<3;i++)mAreas.Add(new(){Weapon="enemy",Radius=4,Hostile=true,Duration=1,VisualCount=16});
        int count=AreaVisuals().Count();UpdateAreas(.03);return(count,mAgents.Sum(e=>e.Health));
    }
#endif
}
