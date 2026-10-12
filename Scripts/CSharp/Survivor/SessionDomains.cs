namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private readonly Dictionary<string,double> mDomains=new();
    private double mDomainSpacing;
    private void ResetDomains(){mDomains.Clear();mDomainSpacing=0;}
    private void GrantDomain(string region)
    {
        string id="domain_"+region;mDomains[id]=0;mThreatTime=0;
        if(mCatalog["domainPowers"]?[id] is not { } config)return;
        // Activation overcharge is once per completed region and never consumes a weapon slot.
        foreach(var enemy in mAgents.Where(e=>e.Region==region).ToArray())
        {
            double fraction=N(config["overcharge"],enemy.Boss?"bossHealthFractionDamage":enemy.Elite?"eliteHealthFractionDamage":"ordinaryHealthFractionDamage");
            if(fraction>0)Hit(enemy,enemy.MaxHealth*fraction,id,false);
        }
        CastDomain(id,true);mDomains[id]=N(config,"cooldown");
    }
    private void UpdateDomains(double dt)
    {
        foreach(var enemy in mAgents)enemy.VulnerabilityTimer=Math.Max(0,enemy.VulnerabilityTimer-dt);
        foreach(string id in mDomains.Keys.ToArray())mDomains[id]=Math.Max(0,mDomains[id]-dt);
        mDomainSpacing=Math.Max(0,mDomainSpacing-dt);if(mDomainSpacing>0)return;
        foreach(string id in mDomains.Keys.ToArray())if(mDomains[id]<=0)
        {
            if(CastDomain(id)){mDomains[id]=N(mCatalog["domainPowers"]![id],"cooldown");mDomainSpacing=1.1;break;}
            mDomains[id]=.2;
        }
    }
    private bool CastDomain(string id,bool overcharge=false)
    {
        if(mCatalog["domainPowers"]?[id] is not { } config)return false;
        var candidates=mAgents.Where(e=>e.Health>0&&Distance(e.X-mX,e.Z-mZ)<=N(config,"searchRadius",id=="domain_thunder"?13:id=="domain_wind"?15:14)).ToArray();if(candidates.Length==0)return false;
        double scale=(1+(mLevel-1)*.035)*(1+mDomains.Count*.08),damage=(N(config,"baseDamage")+(mLevel-1)*N(config,"damagePerPlayerLevel"))*scale*(overcharge?2.2:1),radius=N(config,"radius");
        var target=id=="domain_star"||id=="domain_thunder"?candidates.OrderByDescending(e=>e.Boss).ThenByDescending(e=>e.Health).ThenBy(e=>e.Id).First():candidates.OrderByDescending(e=>candidates.Count(n=>Distance(n.X-e.X,n.Z-e.Z)<=radius)).ThenBy(e=>e.Id).First();
        if(id=="domain_thunder")
        {
            damage=(N(config,"baseDamage")+(mLevel-1)*N(config,"damagePerPlayerLevel"))*scale*(overcharge?2:1);
            foreach(var enemy in candidates.OrderByDescending(e=>e.Boss).ThenByDescending(e=>e.Health).ThenBy(e=>e.Id).Take(4+Math.Min(2,mDomains.Count/2)))
            {Hit(enemy,damage,id,false);mProjectiles.Add(new(){VisualId=++mNextVisualId,X=enemy.X,Z=enemy.Z,Radius=.3,Life=.22,Behavior="visual",Color=[1,.95,.3,1]});}
        }
        else if(id=="domain_wind")
        {
            damage=(N(config,"baseTickDamage")+(mLevel-1)*N(config,"tickDamagePerPlayerLevel"))*scale*(overcharge?2:1);
            QueueArea(id,target.X,target.Z,0,radius,damage,damage,overcharge?.8:N(config,"duration"),N(config,"tickInterval"),visuals:20);
        }
        else
        {
            if(id=="domain_water"&&mWeaponSlots.Any(w=>WeaponTag(w,"water")))radius*=1.15;
            QueueArea(id,target.X,target.Z,id=="domain_star"&&!overcharge?N(config,"warningSeconds"):0,radius,damage,visuals:20);
        }
        return true;
    }
    private void DomainHit(Enemy enemy,string id)
    {
        if(mCatalog["domainPowers"]?[id] is not { } config)return;
        if(id=="domain_star"){enemy.Vulnerability=N(config,"vulnerability");enemy.VulnerabilityTimer=N(config,"vulnerabilitySeconds");}
        else if(id=="domain_thunder")
        {
            if(enemy.Boss)enemy.Timer+=N(config,"bossActionDelaySeconds",.18);
            else {enemy.AttackPhase=0;enemy.Windup=0;enemy.Timer=Math.Max(enemy.Timer,N(config,"interruptSeconds",.35));}
        }
        else if(id is "domain_water" or "domain_wind")
        {
            double duration=id=="domain_water"?N(config,"slowSeconds"):N(config,"tickInterval")*1.1;
            enemy.SlowRemaining=Math.Max(enemy.SlowRemaining,duration*(1-N(mEnemies[enemy.Kind]["resistances"],"slow")));
            enemy.SlowMagnitude=Math.Max(enemy.SlowMagnitude,id=="domain_water"?N(config,"slowStrength"):N(config,"bossSlowStrength"));
        }
    }
}
