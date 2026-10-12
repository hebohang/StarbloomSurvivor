namespace GameScripts.Survivor;

public sealed class ChallengeDefinition
{
    public string Id { get; set; } = "";
    public double EnemyCount { get; set; } = 1;
    public double SpawnPerMinute { get; set; }
    public double EnemyHealth { get; set; } = 1;
    public double HealthPerMinute { get; set; }
    public double EnemyDamage { get; set; } = 1;
    public double DamagePerMinute { get; set; }
    public double EnemySpeed { get; set; } = 1;
    public double EnemyScale { get; set; } = 1;
    public double Clock { get; set; } = 1;
    public double Xp { get; set; } = 1;
    public double Gold { get; set; } = 1;
    public double? PlayerMaxHealth { get; set; }
    public bool DisableTrinkets { get; set; }
}

public sealed class ChallengeModifiers
{
    public List<string> Ids { get; } = new();
    public double EnemyCount { get; set; } = 1;
    public double EnemyHealth { get; set; } = 1;
    public double EnemyDamage { get; set; } = 1;
    public double EnemySpeed { get; set; } = 1;
    public double EnemyScale { get; set; } = 1;
    public double Clock { get; set; } = 1;
    public double Xp { get; set; } = 1;
    public double Gold { get; set; } = 1;
    public double? PlayerMaxHealth { get; set; }
    public bool DisableTrinkets { get; set; }
}

public static class ChallengeRules
{
    public static string[] NormalizeIds(IEnumerable<string>? values, IEnumerable<string>? catalogOrder = null)
    {
        var selected = new HashSet<string>(StringComparer.Ordinal);
        var ordered = new List<string>();
        if (values is not null)
            foreach (string id in values)
            {
                if (string.IsNullOrEmpty(id)) throw new ArgumentException("Challenge ids must be non-empty.");
                if (id != "none" && selected.Add(id)) ordered.Add(id);
            }
        if (catalogOrder is null) return ordered.ToArray();
        ordered.Clear();
        foreach (string id in catalogOrder) if (selected.Contains(id)) ordered.Add(id);
        return ordered.ToArray();
    }
    public static string[] ToggleId(IEnumerable<string> selectedIds, string id, string[] catalogOrder)
    {
        if (Array.IndexOf(catalogOrder, id) < 0) throw new ArgumentException("Unknown challenge id: " + id);
        var selected = new HashSet<string>(NormalizeIds(selectedIds, catalogOrder), StringComparer.Ordinal);
        if (!selected.Remove(id)) selected.Add(id);
        return NormalizeIds(selected, catalogOrder);
    }
    private static double Multiplier(double value)
    {
        if (!double.IsFinite(value) || value < 0) throw new ArgumentException("Challenge multiplier must be finite and non-negative.");
        return value;
    }
    public static ChallengeModifiers Combine(IEnumerable<ChallengeDefinition> challenges, int minute = 0)
    {
        minute = Math.Clamp(minute, 0, 15);
        var result = new ChallengeModifiers();
        foreach (var challenge in challenges)
        {
            if (challenge.Id.Length > 0) result.Ids.Add(challenge.Id);
            result.EnemyCount *= Multiplier(challenge.EnemyCount);
            result.EnemyCount *= 1 + Multiplier(challenge.SpawnPerMinute) * minute;
            result.EnemyHealth *= Multiplier(challenge.EnemyHealth);
            result.EnemyHealth *= 1 + Multiplier(challenge.HealthPerMinute) * minute;
            result.EnemyDamage *= Multiplier(challenge.EnemyDamage);
            result.EnemyDamage *= 1 + Multiplier(challenge.DamagePerMinute) * minute;
            result.EnemySpeed *= Multiplier(challenge.EnemySpeed);
            result.EnemyScale *= Multiplier(challenge.EnemyScale);
            result.Clock *= Multiplier(challenge.Clock);
            result.Xp *= Multiplier(challenge.Xp);
            result.Gold *= Multiplier(challenge.Gold);
            if (challenge.PlayerMaxHealth is double maximum)
            {
                maximum = Multiplier(maximum);
                result.PlayerMaxHealth = result.PlayerMaxHealth is double previous ? Math.Min(previous, maximum) : maximum;
            }
            result.DisableTrinkets |= challenge.DisableTrinkets;
        }
        result.EnemyCount = Math.Min(3, result.EnemyCount);
        result.EnemyHealth = Math.Min(4, result.EnemyHealth);
        result.EnemyDamage = Math.Min(3, result.EnemyDamage);
        result.EnemySpeed = Math.Min(2, result.EnemySpeed);
        result.EnemyScale = Math.Min(2, result.EnemyScale);
        result.Clock = Math.Min(2, result.Clock);
        result.Xp = Math.Min(3, result.Xp);
        result.Gold = Math.Min(4, result.Gold);
        return result;
    }
}
