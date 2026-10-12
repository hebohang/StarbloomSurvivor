namespace GameScripts.Survivor;

public sealed class UpgradeDefinition
{
    public string Id { get; set; } = "";
    public int MaxLevel { get; set; } = 1;
    public double RarityWeight { get; set; } = 1;
}
public sealed class UpgradePoolInput
{
    public UpgradeDefinition[] Weapons { get; set; } = Array.Empty<UpgradeDefinition>();
    public UpgradeDefinition[] Tomes { get; set; } = Array.Empty<UpgradeDefinition>();
    public Dictionary<string, string[]> Owned { get; set; } = new();
    public Dictionary<string, string[]> Enabled { get; set; } = new();
    public Dictionary<string, int> WeaponLevels { get; set; } = new();
    public Dictionary<string, int> TomeLevels { get; set; } = new();
    public string[] WeaponSlots { get; set; } = Array.Empty<string>();
    public string[] TomeSlots { get; set; } = Array.Empty<string>();
    public int MaxWeaponSlots { get; set; } = 6;
    public int MaxTomeSlots { get; set; } = 6;
    public long Seed { get; set; } = 1;
    public int Rerolls { get; set; }
    public int Skips { get; set; }
    public int Banishes { get; set; }
    public string[] Sealed { get; set; } = Array.Empty<string>();
    public string[] ExcludedIds { get; set; } = Array.Empty<string>();
    public double HeldWeightMultiplier { get; set; } = 2;
}
public sealed record UpgradeChoice(string Id, string Kind, string Category,
    int CurrentLevel, int NextLevel, bool Unlock, double Weight);
public sealed record UpgradeReceipt(string Status, UpgradeChoice[] Choices);

public sealed class UpgradePool
{
    private readonly Dictionary<string, UpgradeDefinition[]> mCatalog;
    private readonly Dictionary<string, HashSet<string>> mOwned = new();
    private readonly Dictionary<string, HashSet<string>> mEnabled = new();
    public Dictionary<string, Dictionary<string, int>> Levels { get; }
    public Dictionary<string, List<string>> Slots { get; }
    private readonly Dictionary<string, int> mSlotLimits;
    private readonly double mHeldWeightMultiplier;
    private readonly DeterministicRng mRng;
    private readonly HashSet<string> mBanished = new(StringComparer.Ordinal);
    private readonly HashSet<string> mSealed;
    private readonly HashSet<string> mExcluded;
    public int RerollsRemaining { get; private set; }
    public int SkipsRemaining { get; private set; }
    public int BanishesRemaining { get; private set; }
    public long RollSerial { get; private set; }
    public UpgradeChoice[] CurrentChoices { get; private set; } = Array.Empty<UpgradeChoice>();
    private static HashSet<string> IdSet(IEnumerable<string> values)
    {
        var result = new HashSet<string>(StringComparer.Ordinal);
        foreach (string value in values)
        {
            if (string.IsNullOrEmpty(value)) throw new ArgumentException("Content ids must be non-empty.");
            result.Add(value);
        }
        return result;
    }
    public UpgradePool(UpgradePoolInput input)
    {
        mCatalog = new() { ["weapons"] = input.Weapons, ["tomes"] = input.Tomes };
        Levels = new() { ["weapons"] = new(input.WeaponLevels), ["tomes"] = new(input.TomeLevels) };
        Slots = new() { ["weapons"] = new(input.WeaponSlots), ["tomes"] = new(input.TomeSlots) };
        mSlotLimits = new() { ["weapons"] = input.MaxWeaponSlots, ["tomes"] = input.MaxTomeSlots };
        if (input.MaxWeaponSlots < 0 || input.MaxTomeSlots < 0 || input.HeldWeightMultiplier < 1)
            throw new ArgumentException("Invalid slot limits or held weight multiplier.");
        mHeldWeightMultiplier = input.HeldWeightMultiplier;
        mRng = new(input.Seed);
        RerollsRemaining = Math.Max(0, input.Rerolls);
        SkipsRemaining = Math.Max(0, input.Skips);
        BanishesRemaining = Math.Max(0, input.Banishes);
        mSealed = IdSet(input.Sealed);
        mExcluded = IdSet(input.ExcludedIds);
        foreach (string category in new[] { "weapons", "tomes" })
        {
            mOwned[category] = IdSet(input.Owned.TryGetValue(category, out var owned) ? owned : Array.Empty<string>());
            mEnabled[category] = input.Enabled.TryGetValue(category, out var enabled) ? IdSet(enabled) : new(mOwned[category]);
            mEnabled[category].IntersectWith(mOwned[category]);
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var entry in mCatalog[category])
                if (string.IsNullOrEmpty(entry.Id) || !ids.Add(entry.Id)) throw new ArgumentException("Invalid or duplicate catalog id.");
            foreach (var entry in Levels[category])
                if (string.IsNullOrEmpty(entry.Key) || entry.Value < 0) throw new ArgumentException("Invalid level map.");
        }
    }
    public UpgradeChoice[] CandidateSnapshot()
    {
        var result = new List<UpgradeChoice>();
        foreach (string category in new[] { "weapons", "tomes" })
        {
            bool bFull = Slots[category].Count >= mSlotLimits[category];
            foreach (var entry in mCatalog[category])
            {
                string id = entry.Id;
                if (mExcluded.Contains(id) || !mOwned[category].Contains(id) || !mEnabled[category].Contains(id) ||
                    mSealed.Contains(id) || mBanished.Contains(id)) continue;
                int level = Levels[category].TryGetValue(id, out int value) ? value : 0;
                if (level >= entry.MaxLevel || (level <= 0 && bFull)) continue;
                double weight = Math.Max(0, entry.RarityWeight);
                if (level > 0) weight *= mHeldWeightMultiplier;
                if (weight <= 0) continue;
                result.Add(new(id, category == "weapons" ? "weapon" : "tome", category,
                    level, level + 1, level <= 0, weight));
            }
        }
        return result.ToArray();
    }
    public UpgradeChoice[] Roll(int choiceCount = 3)
    {
        if (choiceCount <= 0) throw new ArgumentOutOfRangeException(nameof(choiceCount));
        var available = new List<UpgradeChoice>(CandidateSnapshot());
        var choices = new List<UpgradeChoice>();
        while (available.Count > 0 && choices.Count < choiceCount)
        {
            var weights = new List<double>();
            foreach (var row in available) weights.Add(row.Weight);
            int index = mRng.WeightedIndex(weights);
            choices.Add(available[index]);
            available.RemoveAt(index);
        }
        if (choices.Count == 0)
            foreach (string id in new[] { "snack", "bonus", "spark" })
            {
                if (choices.Count >= choiceCount) break;
                choices.Add(new(id, "fallback", "fallbacks", 0, 0, false, 1));
            }
        CurrentChoices = choices.ToArray();
        ++RollSerial;
        return CurrentChoices;
    }
    public UpgradeReceipt Reroll(int choiceCount = 3)
    {
        if (RerollsRemaining <= 0) return new("unavailable", CurrentChoices);
        --RerollsRemaining;
        return new("rerolled", Roll(choiceCount));
    }
    public UpgradeReceipt Skip()
    {
        if (SkipsRemaining <= 0) return new("unavailable", CurrentChoices);
        --SkipsRemaining;
        CurrentChoices = Array.Empty<UpgradeChoice>();
        return new("skipped", CurrentChoices);
    }
    public UpgradeReceipt Banish(string contentId, int choiceCount = 3)
    {
        if (BanishesRemaining <= 0) return new("unavailable", CurrentChoices);
        bool bFound = false;
        foreach (var choice in CurrentChoices) bFound |= choice.Id == contentId;
        if (!bFound) return new("not_in_choices", CurrentChoices);
        --BanishesRemaining;
        mBanished.Add(contentId);
        return new("banished", Roll(choiceCount));
    }
    public void Seal(string contentId)
    {
        mSealed.Add(contentId);
        var choices = new List<UpgradeChoice>();
        foreach (var choice in CurrentChoices) if (choice.Id != contentId) choices.Add(choice);
        CurrentChoices = choices.ToArray();
    }
    public void Unseal(string contentId) => mSealed.Remove(contentId);
    public void SetEnabled(string category, string contentId, bool bEnabled)
    {
        if (!mEnabled.ContainsKey(category) || !mOwned[category].Contains(contentId))
            throw new ArgumentException("Unknown category or unowned content.");
        if (bEnabled) mEnabled[category].Add(contentId);
        else mEnabled[category].Remove(contentId);
    }
}
