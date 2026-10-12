using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

public static class EncounterRules
{
    public static int LocalTarget(JsonNode tier,double progress,double difficulty,double challenge,int limit=320)
        =>Math.Min(limit,(int)Math.Round((tier["localAliveStart"]!.GetValue<double>()+(tier["localAliveEnd"]!.GetValue<double>()-tier["localAliveStart"]!.GetValue<double>())*Math.Clamp(progress,0,1))*difficulty*challenge));
    public static double SpawnRate(JsonNode tier,double killsPerSecond,double difficulty,double challenge)
        =>Math.Max(tier["spawnFloor"]!.GetValue<double>()*difficulty*challenge,Math.Min(tier["spawnCap"]!.GetValue<double>()*difficulty*challenge,1.15*killsPerSecond));
    public static double KillRate(double previous,double dt,int kills)=>dt<=0?previous:Math.Max(0,previous+(1-Math.Exp(-dt/5))*(kills/dt-previous));
}
