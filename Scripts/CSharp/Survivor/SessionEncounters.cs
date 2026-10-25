using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private double mRegionCredit,mRegionBurstTimer,mKillRate,mThreatTime;
    private int mPreviousKills,mEncounterOrder;
    private string mEncounterRegion="";
    private readonly HashSet<int> mEliteWaves=new();
    private readonly Dictionary<string,double> mRegionXp=new();
    private void ResetEncounters()
    {mRegionCredit=mRegionBurstTimer=mKillRate=mThreatTime=0;mPreviousKills=mEncounterOrder=0;mEncounterRegion="";mEliteWaves.Clear();mRegionXp.Clear();ResetDomains();}
    private int WorldTarget(double progress,JsonNode wave)
    {
        if(mCatalog["globalThreatBands"] is not JsonArray bands)return (int)Math.Min(320,(N(wave,"countStart")+(N(wave,"countEnd")-N(wave,"countStart"))*progress)*N(mDifficulty,"spawn",1)*mChallenges.EnemyCount);
        if(mObjectives.ObjectiveState is "BOSS_READY" or "BOSS_INTRO")return 35;
        if(mObjectives.ObjectiveState=="BOSS_ACTIVE")return mAgents.FirstOrDefault(e=>e.Kind=="star_dragon")?.BossPhase switch{2=>70,3=>100,_=>40};
        var band=bands[mObjectives.Completed.Count]!;return (int)Math.Round(band[0]!.GetValue<double>()+(band[1]!.GetValue<double>()-band[0]!.GetValue<double>())*Math.Min(1,mThreatTime/45));
    }
    private void UpdateEncounters(double dt)
    {
        mThreatTime+=dt;mKillRate=EncounterRules.KillRate(mKillRate,dt,mKills-mPreviousKills);mPreviousKills=mKills;
        var active=mObjectives.Active;
        if(active?.State!="ASSAULT"||mCatalog["encounterTiers"] is not JsonArray tiers){if(active is null||active.State is "ARMING" or "COOLDOWN")mEncounterRegion="";return;}
        // Initialize once per assault, not on both of its first two frames.
        if(mEncounterRegion!=active.Id)
        {mEncounterRegion=active.Id;mEncounterOrder=mObjectives.Completed.Count+1;mRegionCredit=mRegionBurstTimer=0;mEliteWaves.Clear();if(!mRegionXp.ContainsKey(active.Id))mRegionXp[active.Id]=0;}
        var tier=tiers[Math.Clamp(mEncounterOrder-1,0,3)]!;double difficulty=N(mCatalog["encounterDifficulty"],S(mDifficulty,"id"),1);
        int local=mAgents.Count(e=>e.Region==active.Id&&Distance(e.X-active.X,e.Z-active.Z)<=24);
        int target=EncounterRules.LocalTarget(tier,active.Assault/N(mCatalog["objective"],"assaultSeconds",60),difficulty,mChallenges.EnemyCount);
        mRegionCredit+=EncounterRules.SpawnRate(tier,mKillRate,difficulty,mChallenges.EnemyCount)*dt;
        int count=Math.Min((int)mRegionCredit,Math.Max(0,target-local));mRegionCredit-=(int)mRegionCredit;
        mRegionBurstTimer=Math.Max(0,mRegionBurstTimer-dt);
        if(mRegionBurstTimer==0&&local<target*.75){count+=Math.Min((int)N(tier,"burstCap"),Math.Max(0,target-local-count));mRegionBurstTimer=5;}
        for(int i=0;i<count&&mAgents.Count<mEnemyLimit;i++)SpawnRegion(active,tier,false);
        int[][] eliteCounts=[[1,0,1],[1,1,1],[1,1,2],[1,2,2]];double[] times=[18,34,50];
        for(int i=0;i<3;i++)if(active.Assault>=times[i]&&mEliteWaves.Add(i))for(int n=0;n<eliteCounts[Math.Clamp(mEncounterOrder-1,0,3)][i]&&mAgents.Count<mEnemyLimit;n++)SpawnRegion(active,tier,true);
    }
    private void SpawnRegion(RegionObjectives.Region region,JsonNode tier,bool elite)
    {
        var config=mCatalog["regions"]![region.Id]!;var fodder=Strings(config["fodder"]);var specialists=Strings(config["specialists"]).Take(Math.Min(3,1+(int)(Math.Min(59.999,region.Assault)/15))).ToArray();
        var pool=mRng.Unit()<.62&&!elite?fodder:specialists;string kind=pool[(int)(mRng.Unit()*pool.Length)];
        Spawn(kind,new JsonObject{["healthMultiplier"]=N(tier,"healthMultiplier",1),["damageMultiplier"]=N(tier,"damageMultiplier",1),["eliteRate"]=elite?1:0});
        // Golden-angle sequence avoids repeatedly stacking a burst on 8 points.
        var enemy=mAgents[^1];double angle=mNextId*2.399963229728653,radius=region.HoldRadius+3+(mNextId%5)*.55;
        enemy.X=region.X+Math.Cos(angle)*radius;enemy.Z=region.Z+Math.Sin(angle)*radius;enemy.Region=region.Id;
    }
    private double EnemyExperience(Enemy enemy)
    {
        if(enemy.Region.Length==0||mCatalog["encounterTiers"] is not JsonArray tiers)return enemy.Xp;
        double budget=N(tiers[Math.Clamp(mEncounterOrder-1,0,3)],"xpBudget"),used=mRegionXp.GetValueOrDefault(enemy.Region),value=Math.Min(enemy.Xp*.5,Math.Max(0,budget-used));mRegionXp[enemy.Region]=used+value;return value;
    }
}
