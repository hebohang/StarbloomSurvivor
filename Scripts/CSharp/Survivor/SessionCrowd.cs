namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private readonly SpatialGrid<Enemy> mEnemyGrid=new();
    private readonly List<Enemy> mNearestCandidates=new(),mProjectileCandidates=new(),mSplashCandidates=new(),mDensityCandidates=new(),mSeparationCandidates=new();
    private readonly List<(Enemy Enemy,double X,double Z)> mSeparationMoves=new();
    private double mLargestEnemyRadius;
    private int mCrowdTick;
    private double mSeparationTime;
    private void RebuildEnemyIndex(){mEnemyGrid.Clear();mLargestEnemyRadius=0;foreach(var e in mAgents)if(e.Health>0){mEnemyGrid.Add(e,e.X,e.Z);mLargestEnemyRadius=Math.Max(mLargestEnemyRadius,e.Radius);}}
    private static double DistanceSquared(double x,double z)=>x*x+z*z;
    private void OrderCandidates(List<Enemy> candidates)
    {
        // A fully packed cell cannot prune well. Reuse the original ordered
        // list rather than paying a sort for almost the entire crowd.
        if(candidates.Count>mAgents.Count/2){candidates.Clear();candidates.AddRange(mAgents);}
        else candidates.Sort((a,b)=>a.Id.CompareTo(b.Id));
    }
    private void ProjectileCandidates(Projectile p){mEnemyGrid.Query(p.X,p.Z,p.Radius+mLargestEnemyRadius,mProjectileCandidates);OrderCandidates(mProjectileCandidates);}
    private Enemy DensestEnemy(double radius)
    {
        Enemy? best=null;int bestCount=-1;double bestDistance=double.PositiveInfinity;
        foreach(var e in mAgents){
            if(e.Health<=0)continue;mEnemyGrid.Query(e.X,e.Z,radius,mDensityCandidates);int count=0;
            foreach(var other in mDensityCandidates)if(other.Health>0&&DistanceSquared(other.X-e.X,other.Z-e.Z)<=radius*radius)count++;
            double distance=DistanceSquared(e.X-mX,e.Z-mZ);
            if(count>bestCount||count==bestCount&&distance<bestDistance){best=e;bestCount=count;bestDistance=distance;}
        }
        return best!;
    }
    private void SeparateEnemies(double dt)
    {
        mSeparationTime+=dt;if(mSeparationTime+1e-9<.05)return;
        mSeparationTime=Math.Max(0,mSeparationTime-.05);dt=.05;
        RebuildEnemyIndex();mSeparationMoves.Clear();mCrowdTick++;
        foreach(var e in mAgents){
            if(e.Health<=0||e.Boss||e.FreezeRemaining>0||Charging(e)&&e.AttackPhase is 1 or 2)continue;
            // Bound dense-cell work and rotate the sampled neighbors each tick.
            mEnemyGrid.Query(e.X,e.Z,e.Radius+mLargestEnemyRadius,mSeparationCandidates,32,e.Id+mCrowdTick);
            double pushX=0,pushZ=0;int overlaps=0;
            foreach(var other in mSeparationCandidates){
                if(other==e||other.Health<=0)continue;
                double dx=e.X-other.X,dz=e.Z-other.Z,spacing=(e.Radius+other.Radius)*.8,d2=dx*dx+dz*dz;
                if(d2>=spacing*spacing)continue;
                double distance=Math.Sqrt(d2);
                if(distance<1e-6){int low=Math.Min(e.Id,other.Id),high=Math.Max(e.Id,other.Id);double angle=((low*31^high*17)&15)*Math.PI/8,sign=e.Id<other.Id?1:-1;dx=Math.Cos(angle)*sign;dz=Math.Sin(angle)*sign;distance=1;}
                double strength=Math.Max(.05,spacing-Math.Sqrt(d2));pushX+=dx/distance*strength;pushZ+=dz/distance*strength;overlaps++;
            }
            if(overlaps==0)continue;
            double length=Math.Sqrt(pushX*pushX+pushZ*pushZ);if(length<1e-8)continue;
            double step=Math.Min(length/Math.Sqrt(overlaps),2.4*dt),x=e.X+pushX/length*step,z=e.Z+pushZ/length*step;
            var height=mTerrain.Height(x,z);if(height.HasValue&&Math.Abs(height.Value-(mTerrain.Height(e.X,e.Z)??height.Value))<=.4)mSeparationMoves.Add((e,x,z));
        }
        foreach(var move in mSeparationMoves){move.Enemy.X=move.X;move.Enemy.Z=move.Z;}
    }
}
