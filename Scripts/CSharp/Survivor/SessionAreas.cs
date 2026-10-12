namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    // Timed damage is independent of the visual budget on all three hosts.
    private sealed class Area
    {
        public long VisualId;
        public string Weapon="";
        public double X,Z,Delay,Radius,Initial,Tick,Duration,Interval=.5,Age,Timer;
        public bool Follow,Ring,Hostile;
        public int Limit,VisualCount;
        public readonly HashSet<int> Hits=new();
    }
    private sealed class Beam
    {
        public long VisualId;
        public string Weapon="";
        public double Delay=.55,X,Z,Dx,Dz,Length,Damage;
        public int[] Targets=[];
    }
    private readonly List<Area> mAreas=new();
    private readonly List<Beam> mBeams=new();
    private double Reach(double radius)=>radius*N(mCharacterStats,"weapon_reach_multiplier",1)*(1+.07*Tome("reach"));
    private void QueueArea(string id,double x,double z,double delay,double radius,double damage,double tick=0,double duration=0,double interval=.5,bool follow=false,int limit=0,int visuals=0)
    {
        if(mTrinkets.Contains("bloom_battery")&&(WeaponTag(id,"zone")||WeaponTag(id,"tick"))){interval*=.82;duration*=.90;}
        mAreas.Add(new(){VisualId=++mNextVisualId,Weapon=id,X=x,Z=z,Delay=delay,Radius=radius,Initial=damage,Tick=tick,Duration=duration,Interval=interval,Follow=follow,Limit=limit,VisualCount=visuals});
    }
    private bool CastAreaWeapon(string id,string behavior,double damage,double radius,double duration,int amount,Enemy target)
    {
        switch(behavior)
        {
            case "expanding_ring":
                if(Distance(target.X-mX,target.Z-mZ)>radius+1){mCooldowns[id]=.12;return true;}
                mAreas.Add(new(){VisualId=++mNextVisualId,Weapon=id,X=mX,Z=mZ,Radius=radius,Initial=damage,Ring=true,Duration=70.0/(60*1.6),VisualCount=16});return true;
            case "echo_ring":
                QueueArea(id,mX,mZ,0,radius,damage,visuals:12);
                for(int i=0;i<(mWeaponLevels[id]>=7?2:1);i++)QueueArea(id,mX,mZ,.65*(i+1),radius,damage*(mWeaponLevels[id]>=5?.75:.55),visuals:12);
                return true;
            case "orbit_contact":
                if(!mAreas.Any(a=>a.Weapon==id))QueueArea(id,mX,mZ,0,Reach(2.2),damage,damage,999,.55,true,visuals:amount);
                mCooldowns[id]=.5;return true;
            case "orbit_beam":
                QueueArea(id,mX,mZ,0,Reach(6),damage,damage,duration,.20,true,amount,amount);return true;
            case "lob_zone":
            case "lob_split":
                var center=mAgents.OrderByDescending(e=>mAgents.Count(n=>Distance(n.X-e.X,n.Z-e.Z)<=radius)).ThenBy(e=>Distance(e.X-mX,e.Z-mZ)).First();
                double travel=behavior=="lob_zone"?.58:.62;
                mProjectiles.Add(new(){VisualId=++mNextVisualId,Weapon=id,X=mX,Z=mZ,Vx=(center.X-mX)/travel,Vz=(center.Z-mZ)/travel,Radius=.35,Life=travel,Behavior="travelVisual",Color=[.65,.9,.3,1]});
                if(behavior=="lob_zone")QueueArea(id,center.X,center.Z,travel,radius,damage,4*N(mCharacterStats,"weapon_damage_multiplier",1)*(1+.08*Tome("might")),duration,visuals:8);
                else
                {
                    QueueArea(id,center.X,center.Z,travel,radius,damage,visuals:12);
                    int children=mWeaponLevels[id]>=10?7:3+(mWeaponLevels[id]>=3?1:0);
                    for(int i=0;i<children;i++){double angle=Math.PI*2*i/children;QueueArea(id,center.X+Math.Cos(angle)*radius*.72,center.Z+Math.Sin(angle)*radius*.72,travel+.14,radius*.36,damage/3,visuals:4);}
                }
                return true;
            case "telegraphed_beam":
                int[] best=[];double dx=0,dz=1,length=Reach(12);
                for(int i=0;i<16;i++)
                {
                    double sx=Math.Sin(Math.PI*2*i/16),sz=Math.Cos(Math.PI*2*i/16);
                    var targets=mAgents.Where(e=>{double x=e.X-mX,z=e.Z-mZ,t=x*sx+z*sz;return t>=0&&t<=length&&Math.Abs(x*sz-z*sx)<=radius+e.Radius;}).Select(e=>e.Id).ToArray();
                    if(targets.Length>best.Length){best=targets;dx=sx;dz=sz;}
                }
                if(best.Length==0){mCooldowns[id]=.1;return true;}
                mBeams.Add(new(){VisualId=++mNextVisualId,Weapon=id,X=mX,Z=mZ,Dx=dx,Dz=dz,Length=length,Damage=damage,Targets=best});return true;
            default:return false;
        }
    }
    private void UpdateAreas(double dt)
    {
        foreach(var area in mAreas.ToArray())
        {
            area.Delay-=dt;if(area.Delay>0)continue;
            if(area.Follow){area.X=mX;area.Z=mZ;}
            double previous=area.Age;area.Age+=dt;area.Timer-=dt;
            if(area.Ring)
            {
                double inner=area.Radius*Math.Min(1,previous/area.Duration),outer=area.Radius*Math.Min(1,area.Age/area.Duration);
                foreach(var enemy in mAgents.ToArray())
                {double distance=Distance(enemy.X-area.X,enemy.Z-area.Z);if(!area.Hits.Contains(enemy.Id)&&distance+enemy.Radius>=inner-.42&&distance-enemy.Radius<=outer+.42){area.Hits.Add(enemy.Id);Hit(enemy,area.Initial,area.Weapon);}}
            }
            else if(area.Timer<=0)
            {
                area.Timer+=area.Interval;double damage=previous==0?area.Initial:area.Tick;
                if(area.Hostile){if(Distance(mX-area.X,mZ-area.Z)<=area.Radius+.42)Hurt(damage);}
                else if(damage>0)
                {
                    var targets=mAgents.Where(e=>Distance(e.X-area.X,e.Z-area.Z)<=area.Radius+e.Radius).OrderBy(e=>Distance(e.X-area.X,e.Z-area.Z));
                    foreach(var enemy in targets.Take(area.Limit>0?area.Limit:int.MaxValue).ToArray())Hit(enemy,damage,area.Weapon);
                }
            }
            if(area.Duration<900&&area.Age>=Math.Max(area.Duration,.12))mAreas.Remove(area);
        }
        foreach(var beam in mBeams.ToArray())
        {
            beam.Delay-=dt;if(beam.Delay>0)continue;
            EmitPresentation("body",beam.Weapon,beam.X,beam.Z,dx:beam.Dx,dz:beam.Dz);
            foreach(int id in beam.Targets){var enemy=mAgents.FirstOrDefault(e=>e.Id==id);if(enemy!=null)Hit(enemy,beam.Damage,beam.Weapon);}
            mBeams.Remove(beam);
        }
    }
    private IEnumerable<object> AreaVisuals()
    {
        foreach(var area in mAreas.Where(a=>a.Delay<=0))for(int i=0;i<Math.Min(24,area.VisualCount);i++)
        {
            double radius=area.Ring?area.Radius*Math.Min(1,area.Age/area.Duration):area.Follow?Math.Clamp(area.Radius*.38,.8,2.4):area.Radius;
            double angle=area.Age*2.4+Math.PI*2*i/Math.Max(1,area.VisualCount),x=area.X+Math.Cos(angle)*radius,z=area.Z+Math.Sin(angle)*radius;
            yield return new{X=x,y=mTerrain.Height(x,z)??0,Z=z,Radius=.16,Color=area.Hostile?new[]{1,.25,.15,.85}:new[]{.45,.75,1,.8}};
        }
        foreach(var beam in mBeams)for(int i=0;i<20;i++)
        {double x=beam.X+beam.Dx*beam.Length*i/20,z=beam.Z+beam.Dz*beam.Length*i/20;yield return new{X=x,y=mTerrain.Height(x,z)??0,Z=z,Radius=.12,Color=new[]{1.0,.4,.3,.65}};}
    }
}
