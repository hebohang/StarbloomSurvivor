namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    // Same attack phases and catalog tuning as SurvivorAgentBatch / _catalog_archetype.
    private bool PreferredRange(Enemy e)=>e.Behavior is "ranged" or "lobber" or "zone" or "summoner"||(e.Kind=="star_dragon"&&e.BossPhase<3);
    private double AttackRange(Enemy e)=>e.Radius+.42;
    private double Preferred(Enemy e)=>N(mEnemies[e.Kind],"preferredRange",5);
    private bool Charging(Enemy e)=>e.Behavior=="charger"||(e.Boss&&(e.Kind=="star_dragon"?e.BossPhase==3:e.BossPhase==1));
    private void UpdateEnemies(double dt)
    {
        foreach(var e in mAgents.ToArray())
        {
            if(e.Health<=0)continue;e.Timer=Math.Max(0,e.Timer-dt);
            e.SlowRemaining=Math.Max(0,e.SlowRemaining-dt);e.FreezeRemaining=Math.Max(0,e.FreezeRemaining-dt);
            e.ShieldTimer=Math.Max(0,e.ShieldTimer-dt);if(e.ShieldTimer==0)e.EnemyShield=0;
            if(e.Boss)
            {
                e.BossPhase=e.Health/e.MaxHealth<=.33?3:e.Health/e.MaxHealth<=.66?2:1;
                e.BossElapsed+=dt;if(!e.Enraged&&e.BossElapsed>=120){e.Enraged=true;e.Damage*=1.2;e.Speed*=1.1;}
            }
            if(e.FreezeRemaining>0)continue;
            double dx=mX-e.X,dz=mZ-e.Z,distance=Math.Max(.001,Distance(dx,dz));dx/=distance;dz/=distance;e.Yaw=Math.Atan2(dx,dz);
            if(e.AttackPhase==2&&Charging(e))
            {
                double speed=9*(e.Enraged?1.1:1)*(e.SlowRemaining>0?1-e.SlowMagnitude:1);
                e.X+=e.LockedX*speed*dt;e.Z+=e.LockedZ*speed*dt;
                if(!e.AttackCommitted&&Distance(e.X-mX,e.Z-mZ)<=e.Radius+.42){Hurt(e.Damage,e);e.AttackCommitted=true;}
            }
            else if(e.AttackPhase==0)MoveEnemy(e,dt,distance,dx,dz);
            switch(e.AttackPhase)
            {
                case 0:
                    if(e.Timer<=0&&distance<=(PreferredRange(e)?Math.Max(AttackRange(e),Preferred(e)):AttackRange(e))&&Math.Abs(mY-(mTerrain.Height(e.X,e.Z)??0))<=2.25)
                    {
                        e.AttackPhase=1;e.PhaseTimer=Math.Max(e.Boss?.85:.35,N(mEnemies[e.Kind],"telegraph"));e.Windup=e.PhaseTimer;e.LockedX=dx;e.LockedZ=dz;e.AttackCommitted=false;
                        if(e.Behavior=="shield"){e.EnemyShield=Math.Max(e.EnemyShield,60);e.ShieldTimer=2;}
                    }
                    break;
                case 1:
                    e.PhaseTimer-=dt;e.Windup=Math.Max(0,e.PhaseTimer);
                    if(e.PhaseTimer<=0){e.AttackPhase=2;e.PhaseTimer=.12;ActivateEnemy(e,distance);}
                    break;
                case 2:
                    e.PhaseTimer-=dt;if(e.PhaseTimer<=0){e.AttackPhase=3;e.PhaseTimer=e.Boss?.36:.22;}break;
                case 3:
                    e.PhaseTimer-=dt;if(e.PhaseTimer<=0){e.AttackPhase=0;e.Timer=N(mEnemies[e.Kind],"cooldown",1.05)*(e.Enraged?.8:1);e.AttackCommitted=false;}break;
            }
        }
    }
    private void MoveEnemy(Enemy e,double dt,double distance,double dx,double dz)
    {
        double x=dx,z=dz,speed=e.SlowRemaining>0?1-e.SlowMagnitude:1,desired=AttackRange(e),sign=Math.Sin(e.Phase)>=0?1:-1;
        switch(e.Behavior)
        {
            case "flanker":x=dx*.92-dz*.25*sign;z=dz*.92+dx*.25*sign;break;
            case "armored":speed*=.72;break;
            case "bruiser":speed*=.78;break;
            case "ghost":speed*=1.08;x-=dz*.08*sign;z+=dx*.08*sign;break;
            default:
                if(!PreferredRange(e)&&!e.Boss){double weave=Math.Sin(mElapsed*1.7+e.Phase)*.12;x-=dz*weave;z+=dx*weave;}break;
        }
        if(PreferredRange(e))
        {
            desired=Preferred(e);
            if(distance<desired*.75){x=-dx;z=-dz;}
            else if(distance<=desired){if(e.Kind!="star_dragon")return;x=-dz*.25;z=dx*.25;}
        }
        double length=Math.Max(.001,Distance(x,z));x/=length;z/=length;
        double step=e.Speed*speed*dt;if(x*dx+z*dz>0)step=Math.Min(step,Math.Max(0,distance-desired));
        e.X+=x*step;e.Z+=z*step;
    }
    private void EnemyProjectile(Enemy e,double dx,double dz,bool lob=false)
    {
        double length=Math.Max(.001,Distance(dx,dz));dx/=length;dz/=length;
        double life=lob?Math.Max(.001,Distance(mX-e.X,mZ-e.Z)/7.5):2.4;
        mProjectiles.Add(new(){VisualId=++mNextVisualId,X=e.X,Z=e.Z,Vx=dx*7.5,Vz=dz*7.5,Radius=.28,Damage=e.Damage,Hostile=true,Life=life,Behavior=lob?"enemyLob":"enemy",Color=[1,.2,.25,1]});
        if(lob)EnemyZone(e,mX,mZ,life);
    }
    private void EnemyZone(Enemy e,double x,double z,double delay=0,bool suicide=false)
    {
        mAreas.Add(new(){VisualId=++mNextVisualId,Weapon="enemy",X=x,Z=z,Delay=delay,Radius=e.Boss?2.4:1.6,Initial=e.Damage*(suicide?1.5:.75),Tick=e.Damage*.75,Duration=suicide?.12:e.Boss?2.4:2,Interval=.5,VisualCount=16,Hostile=true});
    }
    private void Summon(Enemy e)
    {
        if(!Strings(mEnemies[e.Kind]["attackSet"]).Any(s=>s.Contains("summon")))return;
        for(int i=0;i<4&&mAgents.Count<mEnemyLimit;i++)
        {
            Spawn("green_blob",new System.Text.Json.Nodes.JsonObject());var child=mAgents[^1];double angle=i*Math.PI*.5;
            child.X=e.X+Math.Cos(angle)*1.8;child.Z=e.Z+Math.Sin(angle)*1.8;
        }
    }
    private void ActivateEnemy(Enemy e,double distance)
    {
        if(e.Boss)
        {
            if(e.Kind=="star_dragon"&&e.BossPhase==1)
                for(int i=0;i<8;i++){double angle=Math.Abs(e.Phase)%(Math.PI*2)+Math.PI*2*i/8;EnemyProjectile(e,Math.Cos(angle),Math.Sin(angle));}
            else if(e.Kind=="star_dragon"&&e.BossPhase==2)
                for(int i=0;i<5;i++){double angle=-.62+i*.31,c=Math.Cos(angle),s=Math.Sin(angle);EnemyProjectile(e,e.LockedX*c-e.LockedZ*s,e.LockedX*s+e.LockedZ*c);}
            else if(e.BossPhase==2)EnemyProjectile(e,mX-e.X,mZ-e.Z);
            else if(e.BossPhase==3){EnemyZone(e,mX,mZ);Summon(e);}
            if(Charging(e)&&distance<=e.Radius+.42){Hurt(e.Damage,e);e.AttackCommitted=true;}
            return;
        }
        switch(e.Behavior)
        {
            case "ranged":EnemyProjectile(e,mX-e.X,mZ-e.Z);break;
            case "lobber":EnemyProjectile(e,mX-e.X,mZ-e.Z,true);break;
            case "zone":EnemyZone(e,mX,mZ);break;
            case "summoner":Summon(e);break;
            case "suicide":EnemyZone(e,e.X,e.Z,suicide:true);if(distance<=1.6+.42)Hurt(e.Damage*1.5);mAgents.Remove(e);break;
            default:if(distance<=AttackRange(e)){Hurt(e.Damage,e);e.AttackCommitted=true;}break;
        }
    }
}
