using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

public sealed class QuestTracker
{
    private readonly JsonObject mProfile;
    private readonly Dictionary<string,List<JsonObject>> mByMetric = new();
    private readonly Dictionary<string,double> mRunValues = new();
    private readonly Queue<(string Metric,double Amount,JsonObject Context,bool Set)> mBuffer = new();
    public List<string> CompletedThisRun { get; } = new();
    public long RunQuestGold { get; private set; }
    private static readonly JsonObject sEmptyContext=new();
    private static double Number(JsonNode? value)
    {
        if(value is null)return 0;
        if(value is JsonValue number){if(number.TryGetValue<double>(out var d))return d;if(number.TryGetValue<long>(out var l))return l;if(number.TryGetValue<int>(out var i))return i;}
        return double.Parse(value.ToJsonString(),System.Globalization.CultureInfo.InvariantCulture);
    }
    public QuestTracker(JsonObject profile,JsonArray quests)
    {
        mProfile=profile;
        foreach(var quest in quests){string metric=quest!["metric"]!.GetValue<string>();if(!mByMetric.TryGetValue(metric,out var list))mByMetric[metric]=list=new();list.Add(quest.AsObject());}
    }
    public void ResetRun(){mRunValues.Clear();mBuffer.Clear();CompletedThisRun.Clear();RunQuestGold=0;}
    public void Record(string metric,double amount=1,JsonObject? context=null,bool bSet=false)
    {
        if(mByMetric.ContainsKey(metric))mBuffer.Enqueue((metric,amount,context?.DeepClone().AsObject()??sEmptyContext,bSet));
    }
    private static bool Has(JsonArray list,string id)=>list.Any(n=>n!.GetValue<string>()==id);
    private static bool Matches(JsonObject filters,JsonObject context)
    {
        foreach(var filter in filters)
        {
            var actual=context[filter.Key];
            if(filter.Key=="tags")
            {if(actual is not JsonArray tags||!filter.Value!.AsArray().Any(expected=>tags.Any(t=>JsonNode.DeepEquals(t,expected))))return false;}
            else if(filter.Value is JsonArray choices){if(!choices.Any(c=>JsonNode.DeepEquals(c,actual)))return false;}
            else if(!JsonNode.DeepEquals(filter.Value,actual))return false;
        }
        return true;
    }
    public bool Flush()
    {
        bool bChanged=false;var completed=mProfile["completedQuests"]!.AsArray();
        while(mBuffer.TryDequeue(out var record))
        foreach(var quest in mByMetric[record.Metric])
        {
            string id=quest["id"]!.GetValue<string>();if(Has(completed,id))continue;
            if(quest["prerequisiteIds"]!.AsArray().Any(n=>!Has(completed,n!.GetValue<string>())))continue;
            string hidden=quest["hiddenUntil"]!.GetValue<string>();
            if(hidden.StartsWith("meta_weapon_slots:")&&(!int.TryParse(hidden.Split(':')[1],out int required)||Number(mProfile["powerUps"]?["meta_weapon_slots"])<required))continue;
            if(!Matches(quest["filters"]!.AsObject(),record.Context))continue;
            bool bRun=quest["progressMode"]!.GetValue<string>()=="run";var progress=mProfile["questProgress"]!.AsObject();
            double previous=bRun?mRunValues.GetValueOrDefault(id):Number(progress[id]),value=record.Set?Math.Max(previous,record.Amount):previous+record.Amount;
            if(bRun)mRunValues[id]=value;else progress[id]=value;
            if(value<Number(quest["target"]))continue;
            completed.Add(id);CompletedThisRun.Add(id);RunQuestGold+=(long)Number(quest["rewardGold"]);bChanged=true;
            string type=quest["unlockType"]!.GetValue<string>(),unlock=quest["unlockId"]!.GetValue<string>();
            if(type is "character" or "weapon" or "tome" or "trinket" && unlock.Length>0)
            {
                string category=type=="character"?"characters":type+"s";var eligible=mProfile["eligible"]![category]!.AsArray();
                if(!Has(eligible,unlock)&&!Has(mProfile["owned"]![category]!.AsArray(),unlock))eligible.Add(unlock);
            }
            Record("quests_completed",completed.Count,new(){["questId"]=id},true);
        }
        return bChanged;
    }
}
