namespace GameScripts.Survivor;

public sealed class EvolutionRecipe
{
    public string Id { get; set; } = "";
    public string WeaponId { get; set; } = "";
    public string TomeId { get; set; } = "";
    public int ChestTier { get; set; } = 1;
    public int RequiredWeaponLevel { get; set; } = 10;
    public int RequiredTomeLevel { get; set; } = 5;
}
public sealed class EvolutionInput
{
    public EvolutionRecipe[] Recipes { get; set; } = Array.Empty<EvolutionRecipe>();
    public Dictionary<string, int> WeaponLevels { get; set; } = new();
    public Dictionary<string, int> TomeLevels { get; set; } = new();
    public string[] WeaponSlots { get; set; } = Array.Empty<string>();
    public string[] Discovered { get; set; } = Array.Empty<string>();
}
public sealed record EvolutionReceipt(string Status, string[] Evolutions, string[] NewlyDiscovered,
    string[] WeaponSlots, Dictionary<string, int> WeaponLevels, string[] Discovered);

public sealed class EvolutionResolver
{
    private readonly EvolutionRecipe[] mRecipes;
    private readonly Dictionary<string, int> mWeaponLevels;
    private readonly Dictionary<string, int> mTomeLevels;
    private readonly List<string> mWeaponSlots;
    private readonly List<string> mDiscovered = new();
    private readonly HashSet<string> mDiscoveredSet = new(StringComparer.Ordinal);
    private readonly HashSet<string> mResolved = new(StringComparer.Ordinal);
    public EvolutionResolver(EvolutionInput input)
    {
        mRecipes = input.Recipes;
        mWeaponLevels = new(input.WeaponLevels);
        mTomeLevels = new(input.TomeLevels);
        mWeaponSlots = new(input.WeaponSlots);
        foreach (var levels in new[] { mWeaponLevels, mTomeLevels })
            foreach (var entry in levels)
                if (string.IsNullOrEmpty(entry.Key) || entry.Value < 0) throw new ArgumentException("Invalid evolution level map.");
        foreach (string id in input.Discovered) if (mDiscoveredSet.Add(id)) mDiscovered.Add(id);
        foreach (var recipe in mRecipes)
            if (mWeaponSlots.Contains(recipe.Id) || Level(mWeaponLevels, recipe.Id) > 0) mResolved.Add(recipe.Id);
    }
    private static int Level(Dictionary<string, int> levels, string id) => levels.TryGetValue(id, out int level) ? level : 0;
    public EvolutionReceipt ResolveChest(int chestTier)
    {
        if (chestTier < 0 || chestTier > 3) throw new ArgumentOutOfRangeException(nameof(chestTier));
        int limit = chestTier == 3 ? 2 : 1;
        var resolved = new List<string>();
        var newlyDiscovered = new List<string>();
        foreach (var recipe in mRecipes)
        {
            if (resolved.Count >= limit) break;
            if (mResolved.Contains(recipe.Id) || !mWeaponSlots.Contains(recipe.WeaponId) ||
                chestTier < recipe.ChestTier || Level(mWeaponLevels, recipe.WeaponId) < recipe.RequiredWeaponLevel ||
                Level(mTomeLevels, recipe.TomeId) < recipe.RequiredTomeLevel) continue;
            mWeaponSlots[mWeaponSlots.IndexOf(recipe.WeaponId)] = recipe.Id;
            mWeaponLevels[recipe.WeaponId] = 0;
            mWeaponLevels[recipe.Id] = 1;
            mResolved.Add(recipe.Id);
            resolved.Add(recipe.Id);
            if (mDiscoveredSet.Add(recipe.Id)) { mDiscovered.Add(recipe.Id); newlyDiscovered.Add(recipe.Id); }
        }
        return new(resolved.Count > 0 ? "evolved" : "no_evolution", resolved.ToArray(), newlyDiscovered.ToArray(),
            mWeaponSlots.ToArray(), new(mWeaponLevels), mDiscovered.ToArray());
    }
}
