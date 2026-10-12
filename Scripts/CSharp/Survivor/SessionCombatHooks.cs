using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private sealed class Echo { public string Weapon="";public double Delay; }
    private readonly List<string> mTrinkets=new();
    private readonly List<Echo> mEchoes=new();
    private double mWalked,mSnowCooldown,mBooletCooldown,mPrevented,mMarshmallowTimer,mMagnetTimer;
    private int mCastCounter,mMagnetStacks,mLuckySecond=-1,mLuckyAwards;
    private bool bEchoReady,bMarshmallowReady;
    private bool WeaponTag(string id,string tag)=>mWeapons.TryGetValue(id.Split(':')[0],out var weapon)&&Strings(weapon["tags"]).Contains(tag);
    private double WeaponDamage(double damage)=>damage*N(mCharacterStats,"weapon_damage_multiplier",1)*(1+.08*Tome("might"))*(1+.04*mAzuraStacks);
    private void ResetCombatHooks()
    {
        mTrinkets.Clear();mEchoes.Clear();ResetEvolutions();mWalked=mSnowCooldown=mBooletCooldown=mPrevented=mMarshmallowTimer=mMagnetTimer=0;
        mCastCounter=mMagnetStacks=mLuckyAwards=0;mLuckySecond=-1;bEchoReady=bMarshmallowReady=false;
    }
    private void UpdateCombatHooks(double dt,double walked)
    {
        mSnowCooldown=Math.Max(0,mSnowCooldown-dt);mBooletCooldown=Math.Max(0,mBooletCooldown-dt);
        if(mCharacter=="mossling"){mWalked+=walked;if(mWalked>=18){mWalked%=18;bEchoReady=true;}}
        if(mTrinkets.Contains("marshmallow_shield")&&!bMarshmallowReady){mMarshmallowTimer+=dt;if(mMarshmallowTimer>=45){mMarshmallowTimer=0;bMarshmallowReady=true;}}
        if(mTrinkets.Contains("tiny_magnet")){mMagnetTimer+=dt;if(mMagnetTimer>=2&&mMagnetStacks>0){mMagnetStacks=Math.Max(0,mMagnetStacks-((int)((mMagnetTimer-2)/.5)+1)*2);mMagnetTimer=2;}}
    }
    private void Heal(double amount)
    {
        amount=Math.Max(0,amount);double healed=Math.Min(mMaxHealth-mHealth,amount);mHealth+=healed;
        mHealing+=healed;
        if(healed>0)RecordQuest("healing",healed);
        if(mCharacter=="peachy")mShield=Math.Min(mMaxHealth*.20,mShield+Math.Max(0,amount-healed));
    }
    private void OnWeaponCast(string weapon,bool echo)
    {
        EmitPresentation("cast",weapon,mX,mZ);
        RecordCombat("casts",1,weapon);
        EvolutionCast(weapon);
        if(echo)return;
        ++mCastCounter;
        if(mTrinkets.Contains("echo_shell")&&mCastCounter%7==0)mEchoes.Add(new(){Weapon=weapon,Delay=.22});
        if(bEchoReady){bEchoReady=false;mEchoes.Add(new(){Weapon=weapon,Delay=.18});}
    }
    private double TrinketDamage(string weapon,Enemy target)
    {
        string[] tags=mWeapons.TryGetValue(weapon.Split(':')[0],out var definition)?Strings(definition["tags"]):[];
        return CombatHookRules.TrinketDamage(mTrinkets.ToArray(),tags,mHealth>=mMaxHealth-.001,target.Boss,target.Elite,Tome("velocity"));
    }
    private void Status(Enemy target,string status,double magnitude,double duration)
    {
        duration*=1+.1*Tome("status");
        duration*=1-Math.Clamp(N(mEnemies[target.Kind]["resistances"],status),0,1);
        if(duration<=0)return;
        if(status=="freeze")target.FreezeRemaining=Math.Max(target.FreezeRemaining,duration);
        else {target.SlowRemaining=Math.Max(target.SlowRemaining,duration);target.SlowMagnitude=Math.Max(target.SlowMagnitude,magnitude);}
        mQuests.Record("status_applied",1,new(){["status"]=status});if(mQuests.Flush())++mSaveRevision;
    }
    private void OnWeaponHit(Enemy target,double damage,string weapon,bool critical)
    {
        string baseWeapon=weapon.Split(':')[0];
        EvolutionHit(target,damage,weapon,critical);
        RecordCombat("hits",1,weapon);RecordCombat("damage",damage,weapon);
        if(WeaponTag(weapon,"projectile"))RecordCombat("projectile_hits",1,weapon);
        if(critical)RecordCombat("critical_hits",1,weapon);
        if(baseWeapon=="bubble")RecordCombat("bounce_hits",1,weapon);
        if(mWeapons.TryGetValue(baseWeapon,out var definition)&&N(definition,"pierce")>0)RecordCombat("pierce_hits",1,weapon);
        if(mTrinkets.Contains("sticky_honey"))Status(target,"slow",.12,1.4);
        if(mTrinkets.Contains("prism_lens")&&!weapon.Contains(":split")&&mRng.Unit()<.16)
            foreach(var nearby in mAgents.Where(e=>e!=target&&e.Health>0&&Distance(e.X-target.X,e.Z-target.Z)<=2.8).OrderBy(e=>Distance(e.X-target.X,e.Z-target.Z)).Take(2).ToArray())Hit(nearby,damage*.35,baseWeapon+":split",false);
        if(baseWeapon=="frostorb"&&mRng.Unit()<(mWeaponLevels.GetValueOrDefault(baseWeapon)>=5?.25:.15))Status(target,"freeze",1,mWeaponLevels.GetValueOrDefault(baseWeapon)>=5?1.1:.8);
        else if(baseWeapon=="honeyneedle"&&mWeaponLevels.GetValueOrDefault(baseWeapon)>=5)Status(target,"slow",.20,1.4);
        if(mCharacter=="honeybun"&&weapon=="honeyneedle")
        {
            if(++target.HoneyMarks>=3){target.HoneyMarks=0;foreach(var nearby in mAgents.Where(e=>e!=target&&e.Health>0&&Distance(e.X-target.X,e.Z-target.Z)<=2.2).ToArray())Hit(nearby,Math.Max(1,damage*.25),"honeyneedle",false);}
        }
        if(baseWeapon=="sporecap"&&target.PoisonGeneration==0)target.PoisonRemaining=Math.Max(target.PoisonRemaining,WeaponDamage(4)*6);
    }
    private void OnEnemyKilled(Enemy target,bool critical)
    {
        if(critical)
        {
            RecordQuest("critical_kills",1);int second=(int)mElapsed;if(mLuckySecond!=second){mLuckySecond=second;mLuckyAwards=0;}
            if(mTrinkets.Contains("lucky_ribbon")&&mLuckyAwards<3&&mRng.Unit()<.08){mLuckyAwards++;mRunGold++;}
        }
        if(mCharacter=="mushmellow"&&target.PoisonGeneration==0&&target.PoisonRemaining>0)
        {
            foreach(var nearby in mAgents.Where(e=>e!=target&&e.Health>0&&Distance(e.X-target.X,e.Z-target.Z)<=2.2).OrderBy(e=>Distance(e.X-target.X,e.Z-target.Z)).Take(4).ToArray())
            {
                nearby.PoisonRemaining=target.PoisonRemaining*.5;nearby.PoisonGeneration=1;
                QueueArea("sporecap",nearby.X,nearby.Z,0,.48,nearby.PoisonRemaining/6,nearby.PoisonRemaining/6,3,.5,limit:1);
            }
        }
    }
    private void OnDefense(DefenseResult hit,Enemy? source)
    {
        double prevented=hit.ArmorPrevented+hit.ReductionPrevented+hit.ShieldAbsorbed;
        if(prevented>0)RecordQuest("damage_prevented",prevented);
        if(mCharacter=="crabble")
        {
            mPrevented+=prevented;if(mPrevented>=60){mPrevented%=60;QueueArea("coralanchor",mX,mZ,.60,Reach(3),WeaponDamage(42),visuals:12);}
        }
        if(hit.Evaded&&mCharacter=="boolet"&&mBooletCooldown<=0)
        {mBooletCooldown=1.2;QueueArea("phantombell",mX,mZ,0,Reach(2.6),WeaponDamage(24)*.40,visuals:12);}
        if(hit.Damage<=0)return;
        if(mCharacter=="snowbean"&&mSnowCooldown<=0)
        {mSnowCooldown=12;foreach(var enemy in mAgents.Where(e=>Distance(e.X-mX,e.Z-mZ)<=3.2).ToArray())Status(enemy,"freeze",1,1.1);}
        double thorns=N(mCharacterStats,"thorns")+6*Tome("thorns");if(source!=null&&thorns>0){Hit(source,thorns,"thorns",false);RecordQuest("thorns_prevented",thorns);}
    }
    private void RecordCombat(string metric,double amount,string weapon)
    {
        string id=weapon.Split(':')[0];
        var context=new JsonObject{["weapon"]=id,["path"]=WeaponTag(id,"return")?"return":"outbound",["tags"]=mWeapons.TryGetValue(id,out var definition)?definition["tags"]?.DeepClone():new JsonArray()};
        mQuests.Record(metric,amount,context);if(mQuests.Flush())++mSaveRevision;
    }
    private void WeaponMetric(string weapon,string metric,double amount)
    {
        string id=weapon.Split(':')[0];if(!mWeapons.ContainsKey(id))return;
        if(!mWeaponStats.TryGetValue(id,out var stats))mWeaponStats[id]=stats=new();stats[metric]=stats.GetValueOrDefault(metric)+amount;
    }
    private bool TryEquipTrinket()
    {
        if(mChallenges.DisableTrinkets||mTrinkets.Count>=4)return false;
        var available=mCatalog["trinkets"]!.AsArray().Select(n=>S(n,"id")).Where(id=>Contains(Array(Object(mProfile,"owned"),"trinkets"),id)&&!Contains(Array(Object(mProfile,"poolDisabled"),"trinkets"),id)&&!mTrinkets.Contains(id)).ToArray();
        if(available.Length==0)return false;
        string item=available[(int)(mRng.Unit()*available.Length)];mTrinkets.Add(item);
        if(item=="glass_star"){double fraction=mHealth/Math.Max(1,mMaxHealth);mBaseHealth*=.8;mMaxHealth=mBaseHealth*(1+.08*Tome("vitality"));mHealth=mMaxHealth*fraction;}
        if(item=="marshmallow_shield"){mMarshmallowTimer=0;bMarshmallowReady=true;}
        mMessage="宝箱饰品："+(mCatalog["trinkets"]!.AsArray().First(n=>S(n,"id")==item)?["name"]?["zh_cn"]?.GetValue<string>()??"未知饰品");RecordQuest("chests_opened",1);return true;
    }
}
