using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

public sealed class RegionObjectives
{
    public sealed class Region
    {
        public string Id = "", State = "DORMANT";
        public double X, Z, EnterRadius, HoldRadius, Arming, Assault, Grace, Cooldown;
    }
    public List<Region> Regions { get; } = new();
    public List<string> Completed { get; } = new();
    public string ObjectiveState { get; private set; } = "EXPLORATION";
    public Region? Active { get; private set; }
    private readonly JsonObject mConfig;
    private double mCentralHold, mIntro;
    private double Number(string key) => mConfig[key]!.GetValue<double>();
    public RegionObjectives(JsonObject catalog)
    {
        mConfig = catalog["objective"]!.AsObject();
        foreach(var pair in catalog["regions"]!.AsObject())
        {
            var d=pair.Value!;Regions.Add(new(){Id=pair.Key,X=d["authoredPosition"]![0]!.GetValue<double>(),Z=d["authoredPosition"]![2]!.GetValue<double>(),EnterRadius=d["enterRadius"]!.GetValue<double>(),HoldRadius=d["holdRadius"]!.GetValue<double>()});
        }
    }
    private static bool Inside(Region r,double x,double z,double radius) => (x-r.X)*(x-r.X)+(z-r.Z)*(z-r.Z)<=radius*radius;
    public string? Update(double dt,double x,double z)
    {
        if(!double.IsFinite(dt)||dt<0||!double.IsFinite(x)||!double.IsFinite(z))throw new ArgumentException("Invalid objective update");
        if(dt==0||ObjectiveState is "VICTORY" or "BOSS_ACTIVE")return null;
        if(ObjectiveState=="BOSS_READY")
        {
            double cx=mConfig["centralPosition"]![0]!.GetValue<double>(),cz=mConfig["centralPosition"]![2]!.GetValue<double>();
            mCentralHold=(x-cx)*(x-cx)+(z-cz)*(z-cz)<=Number("centralRadius")*Number("centralRadius")?mCentralHold+dt:0;
            if(mCentralHold>=Number("centralHoldSeconds")){ObjectiveState="BOSS_INTRO";mIntro=0;return "boss_intro_started";}return null;
        }
        if(ObjectiveState=="BOSS_INTRO"){mIntro+=dt;if(mIntro>=Number("bossIntroSeconds")){ObjectiveState="BOSS_ACTIVE";return "boss_spawn_requested";}return null;}
        if(Active is null)
        {
            Active=Regions.FirstOrDefault(r=>r.State=="DORMANT"&&Inside(r,x,z,r.EnterRadius));
            if(Active is null)return null;
            Active.State="ARMING";Active.Arming=0;ObjectiveState="REGION_ASSAULT";
        }
        var state=Active;
        switch(state.State)
        {
            case "ARMING":
                if(!Inside(state,x,z,state.HoldRadius)){state.State="DORMANT";state.Arming=0;Active=null;ObjectiveState="EXPLORATION";return "region_arming_cancelled";}
                state.Arming+=dt;if(state.Arming>=Number("armingSeconds")){state.Arming=Number("armingSeconds");state.State="ASSAULT";state.Grace=0;return "region_assault_started";}break;
            case "ASSAULT":
                if(!Inside(state,x,z,state.HoldRadius)){state.State="OUTSIDE_GRACE";state.Grace=0;return "region_outside_grace_started";}
                state.Assault+=dt;if(state.Assault>=Number("assaultSeconds"))
                {state.Assault=Number("assaultSeconds");state.State="ACTIVATED";Completed.Add(state.Id);Active=null;ObjectiveState=Completed.Count==Regions.Count?"BOSS_READY":"EXPLORATION";return "region_activated:"+state.Id;}break;
            case "OUTSIDE_GRACE":
                if(Inside(state,x,z,state.EnterRadius)){state.State="ASSAULT";state.Grace=0;return "region_assault_resumed";}
                state.Grace+=dt;if(state.Grace>Number("outsideGraceSeconds")){state.State="COOLDOWN";state.Assault=state.Arming=state.Grace=0;state.Cooldown=Number("cooldownSeconds");return "region_failed";}break;
            case "COOLDOWN":
                state.Cooldown=Math.Max(0,state.Cooldown-dt);if(state.Cooldown==0){state.State="DORMANT";Active=null;ObjectiveState="EXPLORATION";return "region_cooldown_finished";}break;
        }
        return null;
    }
    public void Victory(){if(ObjectiveState=="BOSS_ACTIVE")ObjectiveState="VICTORY";}
}
