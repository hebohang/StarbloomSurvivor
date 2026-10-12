using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

// The same versioned profile contract on every host. Storage and backup policy belong to hosts.
public static class ProfileRules
{
    private const long Counter = RunReward.MaxRunCounter;
    private static readonly string[] sRetired = ["thunder", "starfall", "tornado"];
    private static ArgumentException Invalid(string key) => new("Invalid profile field: " + key);
    private static JsonNode? Get(JsonObject obj, string key, JsonNode? fallback = null) => obj.ContainsKey(key) ? obj[key] : fallback;
    private static JsonObject Obj(JsonNode? value, string key) => value as JsonObject ?? throw Invalid(key);
    private static string Str(JsonNode? value, string key)
    {
        if (value is not JsonValue v || !v.TryGetValue<string>(out var s) || s.Length == 0 || s.EnumerateRunes().Count() > 128) throw Invalid(key);
        return s;
    }
    private static double Num(JsonNode? value, string key, double maximum = Counter, double minimum = 0, bool integer = false)
    {
        string raw = value?.ToJsonString() ?? "null";
        if ((integer && (raw.Contains('.') || raw.Contains('e') || raw.Contains('E'))) || !double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out double n) || !double.IsFinite(n)) throw Invalid(key);
        return Math.Clamp(n, minimum, maximum);
    }
    private static bool Bool(JsonNode? value, string key, bool allowInteger = false)
    {
        if (value is JsonValue v && v.TryGetValue<bool>(out bool b)) return b;
        if (allowInteger) return Num(value, key, double.MaxValue, -double.MaxValue, true) != 0;
        throw Invalid(key);
    }
    private static JsonArray List(JsonNode? value, string key, int maximum = 4096, Func<string, bool>? filter = null)
    {
        if (value is not JsonArray array) throw Invalid(key);
        var seen = new HashSet<string>(); var result = new JsonArray();
        foreach (var item in array)
        {
            string s = Str(item, key);
            if (seen.Add(s) && (filter == null || filter(s))) result.Add(s);
            if (seen.Count >= maximum) break;
        }
        return result;
    }
    private static JsonObject Map(JsonNode? value, string key, bool boolean = false, bool integer = true, double maximum = Counter, Func<string, bool>? filter = null)
    {
        var result = new JsonObject();
        foreach (var pair in Obj(value, key))
        {
            Str(JsonValue.Create(pair.Key), key);
            JsonNode entry = boolean ? JsonValue.Create(Bool(pair.Value, key, true))! : JsonValue.Create(Num(pair.Value, key, maximum, integer: integer))!;
            if (filter == null || filter(pair.Key)) result[pair.Key] = entry;
        }
        return result;
    }
    private static bool Contains(JsonNode? array, string value) => ((JsonArray)array!).Any(n => n!.GetValue<string>() == value);
    public static JsonObject Normalize(JsonObject source, JsonObject catalog)
    {
        var result = catalog["defaultProfile"]!.DeepClone().AsObject();
        int version;
        if (source["version"] == null && new[] { "total_kills", "best_survival", "best_level", "boss_kills", "selected_character" }.Any(source.ContainsKey)) version = 1;
        else version = (int)Num(source["version"], "version", int.MaxValue, int.MinValue, true);
        if (version < 1 || version > 4) throw Invalid("unsupported version " + version);
        if (version == 1) return Legacy(source, result);
        result["walletGold"] = Num(Get(source, "walletGold", result["walletGold"]), "walletGold", RunReward.MaxWalletGold, integer: true);
        var career = Obj(Get(source, "career", result["career"]), "career"); var target = result["career"]!.AsObject();
        foreach (string key in new[] { "runs", "wins", "totalKills", "totalElites", "totalBossKills", "totalGoldEarned", "bestLevel" })
            target[key] = Num(Get(career, key, target[key]), "career." + key, minimum: key == "bestLevel" ? 1 : 0, integer: true);
        target["bestSurvivalSeconds"] = Num(Get(career, "bestSurvivalSeconds", target["bestSurvivalSeconds"]), "bestSurvivalSeconds", 86400);
        target["highestDifficulty"] = Str(Get(career, "highestDifficulty", target["highestDifficulty"]), "highestDifficulty");
        var owned = Obj(Get(source, "owned", result["owned"]), "owned"); var eligible = Obj(Get(source, "eligible", result["eligible"]), "eligible");
        foreach (string group in new[] { "characters", "weapons", "tomes", "trinkets" })
        {
            var entries = List(Get(owned, group, result["owned"]![group]), "owned." + group);
            if (group == "weapons")
            {
                if (version <= 3) result["walletGold"] = Math.Min(RunReward.MaxWalletGold, result["walletGold"]!.GetValue<double>() + (Contains(entries, "starfall") ? 120 : 0) + (Contains(entries, "tornado") ? 100 : 0));
                entries = List(entries, group, filter: s => !sRetired.Contains(s));
            }
            result["owned"]![group] = entries;
            result["eligible"]![group] = List(Get(eligible, group, new JsonArray()), "eligible." + group, filter: s => !Contains(entries, s) && (group != "weapons" || !sRetired.Contains(s)));
        }
        if (!Contains(result["owned"]!["characters"], "starpaw")) result["owned"]!["characters"]!.AsArray().Insert(0, JsonValue.Create("starpaw"));
        string character = Str(Get(source, "selectedCharacter", result["selectedCharacter"]), "selectedCharacter");
        result["selectedCharacter"] = Contains(result["owned"]!["characters"], character) ? character : "starpaw";
        result["selectedDifficulty"] = Str(Get(source, "selectedDifficulty", result["selectedDifficulty"]), "selectedDifficulty");
        var challengeIds = catalog["challenges"]!.AsArray().Select(n => n!["id"]!.GetValue<string>()).ToArray();
        void Challenges(JsonObject from, JsonObject to, string plural, string singular)
        {
            JsonArray entries = from.ContainsKey(plural) ? List(from[plural], plural, challengeIds.Length) : new JsonArray(Str(Get(from, singular, JsonValue.Create("none")), singular));
            var normalized = new JsonArray();
            foreach (string id in ChallengeRules.NormalizeIds(entries.Select(n => n!.GetValue<string>()), challengeIds)) normalized.Add(id);
            to[plural] = normalized; to[singular] = normalized.FirstOrDefault()?.DeepClone() ?? JsonValue.Create("none");
        }
        Challenges(source, result, "selectedChallenges", "selectedChallenge");
        var powers = Obj(Get(source, "powerUps", new JsonObject()), "powerUps"); var enabled = Obj(Get(source, "powerUpsEnabled", new JsonObject()), "powerUpsEnabled");
        foreach (var definition in catalog["metaPowerUps"]!.AsArray())
        {
            string id = definition!["id"]!.GetValue<string>(); int level = (int)Num(Get(powers, id, JsonValue.Create(0)), id, definition["prices"]!.AsArray().Count, integer: true);
            if (level <= 0) continue;
            result["powerUps"]![id] = level;
            bool active = Bool(Get(enabled, id, JsonValue.Create(true)), id);
            result["powerUpsEnabled"]![id] = definition["toggleable"]?.GetValue<bool>() == false || active;
        }
        int slots = Math.Min(6, 3 + (result["powerUps"]!["meta_weapon_slots"]?.GetValue<int>() ?? 0));
        result["selectedWeaponSlotLimit"] = Num(Get(source, "selectedWeaponSlotLimit", JsonValue.Create(3)), "selectedWeaponSlotLimit", slots, 3, true);
        foreach (string key in new[] { "characterTraining", "characterMasteryXp", "questProgress", "characterTrainingEnabled", "difficultyClears", "challengeClears" })
            result[key] = Map(Get(source, key, new JsonObject()), key, boolean: key.EndsWith("Enabled") || key.EndsWith("Clears"), integer: key != "questProgress", maximum: key == "characterTraining" ? 5 : Counter,
                filter: key == "questProgress" ? s => !sRetired.Any(r => s == "quest_weapon_" + r) : null);
        foreach (string key in new[] { "completedQuests", "trackedQuests", "discoveredEvolutions", "discoveredDomains" })
            result[key] = List(Get(source, key, new JsonArray()), key, key == "trackedQuests" ? 3 : 4096,
                filter: s => (key != "trackedQuests" || !sRetired.Any(r => s == "quest_weapon_" + r)) && (key != "discoveredEvolutions" || s != "storybooktempest"));
        var disabled = Obj(Get(source, "poolDisabled", result["poolDisabled"]), "poolDisabled");
        foreach (string key in new[] { "weapons", "tomes", "trinkets" }) result["poolDisabled"]![key] = List(Get(disabled, key, new JsonArray()), key, filter: s => Contains(result["owned"]![key], s));
        if (source["lastRun"] != null)
        {
            var last = Obj(source["lastRun"], "lastRun").DeepClone().AsObject();
            last["runId"] = Str(last["runId"], "lastRun.runId"); last["rewardCommitted"] = Bool(Get(last, "rewardCommitted", JsonValue.Create(false)), "rewardCommitted");
            Challenges(last, last, "challengeIds", "challengeId");
            last["weaponSlotLimit"] = Num(Get(last, "weaponSlotLimit", version <= 2 ? JsonValue.Create(6) : result["selectedWeaponSlotLimit"]), "weaponSlotLimit", 6, 3, true);
            result["lastRun"] = last;
        }
        return result;
    }
    private static JsonObject Legacy(JsonObject source, JsonObject result)
    {
        double LegacyNumber(string key, double fallback, bool integer, double minimum = 0)
        {
            var value = Get(source, key, JsonValue.Create(fallback));
            string raw = value is JsonValue v && v.TryGetValue<string>(out var s) ? s.Trim() : value?.ToJsonString() ?? "null";
            if (!double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out double n) || !double.IsFinite(n)) throw Invalid(key);
            if (integer && value is JsonValue str && str.TryGetValue<string>(out _) && (raw.Contains('.') || raw.Contains('e') || raw.Contains('E'))) throw Invalid(key);
            return Math.Clamp(integer ? Math.Truncate(n) : n, minimum, integer ? Counter : 86400);
        }
        double kills = LegacyNumber("total_kills", 0, true), seconds = LegacyNumber("best_survival", 0, false), level = LegacyNumber("best_level", 1, true, 1), bosses = LegacyNumber("boss_kills", 0, true);
        var career = result["career"]!; career["totalKills"] = kills; career["bestSurvivalSeconds"] = seconds; career["bestLevel"] = level; career["totalBossKills"] = bosses;
        var characters = result["owned"]!["characters"]!.AsArray();
        if (seconds >= 120) characters.Add("peachy"); if (kills >= 750) characters.Add("mossling"); if (bosses >= 1) characters.Add("snowbean"); if (level >= 20) characters.Add("azura");
        result["owned"]!["weapons"] = new JsonArray("ring", "fireball", "moonblade", "bubble", "aura", "dagger", "starwheel", "petalstorm", "comet");
        result["owned"]!["tomes"] = new JsonArray("magnet", "vitality", "guard", "might", "haste", "reach", "fortune", "growth", "quantity", "velocity", "duration");
        if (source["selected_character"] is JsonValue selected && selected.TryGetValue<string>(out var id) && Contains(characters, id)) result["selectedCharacter"] = id;
        return result;
    }
}
