namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private readonly Dictionary<string,string> mActiveEvolutions=new();
    private readonly Dictionary<int,int> mHiveEdges=new();
    private bool bRoyalBubbleShield;
    private int mEncoreNotes;
    private (double X,double Z)? mNebulaLastHit;
    private bool Evolved(string weapon,string evolution)=>mActiveEvolutions.GetValueOrDefault(weapon)==evolution;
    private void ResetEvolutions()
    {
        mActiveEvolutions.Clear();mHiveEdges.Clear();bRoyalBubbleShield=false;mEncoreNotes=0;mNebulaLastHit=null;
    }
    private void EvolutionCast(string weapon)
    {
        if(Evolved(weapon,"royalbubblecade"))bRoyalBubbleShield=true;
        if(Evolved(weapon,"tidalfortress"))mShield=Math.Min(mMaxHealth*.30,mShield+24);
        if(Evolved(weapon,"galaxygarden"))for(int i=0;i<5;i++)
        {
            double angle=Math.PI*2*i/5;
            QueueArea(weapon,mX+Math.Cos(angle)*Reach(6),mZ+Math.Sin(angle)*Reach(6),1.1,Reach(1.1),WeaponDamage(32));
        }
    }
    private void EvolutionHit(Enemy target,double damage,string weapon,bool critical)
    {
        if(weapon=="comet"&&Evolved(weapon,"supernovachoir"))
            foreach(var nearby in mAgents.Where(e=>e!=target&&e.Health>0&&Distance(e.X-target.X,e.Z-target.Z)<=2.5).Take(4).ToArray())Hit(nearby,damage*.28,"comet:evolved",false);
        if(weapon=="dagger"&&Evolved(weapon,"nebulanetwork"))
        {
            if(mNebulaLastHit is { } previous)QueueArea("dagger:evolved",(previous.X+target.X)*.5,(previous.Z+target.Z)*.5,0,Reach(.65),damage*.35,duration:.8,interval:.4);
            mNebulaLastHit=(target.X,target.Z);
        }
        if(weapon=="honeyneedle"&&Evolved(weapon,"royalbeehive"))
        {
            int edges=mHiveEdges.GetValueOrDefault(target.Id)+1;
            if(edges>=6){edges=0;QueueArea("honeyneedle:evolved",target.X,target.Z,0,Reach(2),damage*1.8);}
            mHiveEdges[target.Id]=edges;
        }
        if(weapon.Split(':')[0]=="phantombell"&&critical&&Evolved("phantombell","midnightencore"))
        {
            if(++mEncoreNotes>=8){mEncoreNotes=0;QueueArea("phantombell:evolved",mX,mZ,0,Reach(4.2),WeaponDamage(52));}
        }
        if(weapon.Split(':')[0]=="prismorbit"&&Evolved("prismorbit","friendshipspectrum"))
        {
            // Poison is a timed status; it must not recurse through prism hit hooks.
            if(mRng.Unit()<.5)Status(target,"slow",.18,1.2);
            else {target.PoisonRemaining=Math.Max(target.PoisonRemaining,.18*1.2);mQuests.Record("status_applied",1,new(){["status"]="poison"});}
        }
    }
}
