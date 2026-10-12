namespace GameScripts.Survivor;

// Port of SurvivorRules.py. Keep arithmetic order stable for Python parity.
public static class CombatRules
{
    public const double PlayerHurtIframe = 0.45;
    public const double RegularAttackWindup = 0.35;
    public const double BossAttackWindup = 0.85;
    public const double MaxDamageReduction = 0.55;
    public const double MaxEvasion = 0.35;

    public static DefenseResult ResolveDefense(double rawDamage, double evasionRoll,
        double evasion, double armor, double reduction, double shield)
    {
        rawDamage = Math.Max(0, rawDamage);
        evasion = Math.Clamp(evasion, 0, MaxEvasion);
        if (rawDamage <= 0 || evasionRoll < evasion)
            return new(0, rawDamage > 0, 0, 0, 0, Math.Max(0, shield));
        double afterArmor = Math.Max(1, rawDamage - Math.Max(0, armor));
        double armorPrevented = Math.Max(0, rawDamage - afterArmor);
        reduction = Math.Clamp(reduction, 0, MaxDamageReduction);
        double afterReduction = afterArmor * (1 - reduction);
        shield = Math.Max(0, shield);
        double shieldAbsorbed = Math.Min(shield, afterReduction);
        return new(afterReduction - shieldAbsorbed, false, armorPrevented,
            afterArmor - afterReduction, shieldAbsorbed, shield - shieldAbsorbed);
    }

    public static string[] DueWeaponIds(IEnumerable<string> weaponOrder,
        IReadOnlyDictionary<string, int> levels, IReadOnlyDictionary<string, double> timers)
    {
        var result = new List<string>();
        foreach (string id in weaponOrder)
            if (levels.TryGetValue(id, out int level) && level > 0 &&
                (!timers.TryGetValue(id, out double timer) || timer <= 0)) result.Add(id);
        return result.ToArray();
    }

    public static int ExperienceRequirement(int level) => level <= 1 ? 5 :
        level <= 20 ? level * 10 - 5 : level <= 40 ? 195 + (level - 20) * 13 :
        455 + (level - 40) * 16;
}

public readonly record struct DefenseResult(double Damage, bool Evaded,
    double ArmorPrevented, double ReductionPrevented, double ShieldAbsorbed,
    double ShieldRemaining);

public sealed class DeterministicRng
{
    public uint State { get; private set; }
    public DeterministicRng(long seed) => State = unchecked((uint)seed);
    public uint NextU32() => State = unchecked(1664525u * State + 1013904223u);
    public double Unit() => NextU32() / 4294967296.0;
    public int WeightedIndex(IReadOnlyList<double> weights)
    {
        double total = 0;
        foreach (double weight in weights) total += Math.Max(0, weight);
        if (total <= 0) throw new ArgumentException("Weighted selection requires a positive weight.");
        double roll = Unit() * total;
        double cumulative = 0;
        for (int index = 0; index < weights.Count; ++index)
        {
            cumulative += Math.Max(0, weights[index]);
            if (roll < cumulative) return index;
        }
        return weights.Count - 1;
    }
}

public sealed class ProjectileBudget
{
    public int GameplayLimit { get; }
    public int VisualLimit { get; }
    public int GameplayActive { get; private set; }
    public int VisualActive { get; private set; }
    public long RetryCount { get; private set; }
    public long VisualDegradeCount { get; private set; }
    public long RejectedCount { get; private set; }
    public long Generation { get; private set; } = 1;

    public ProjectileBudget(int gameplayLimit, int visualLimit)
    {
        if (gameplayLimit <= 0 || visualLimit < 0) throw new ArgumentOutOfRangeException(nameof(gameplayLimit));
        GameplayLimit = gameplayLimit;
        VisualLimit = visualLimit;
    }
    public string Reserve(bool bCritical = true)
    {
        if (GameplayActive >= GameplayLimit)
        {
            if (bCritical) { ++RetryCount; return "retry"; }
            ++RejectedCount;
            return "reject";
        }
        ++GameplayActive;
        if (VisualActive < VisualLimit) { ++VisualActive; return "full"; }
        ++VisualDegradeCount;
        return "core_fallback";
    }
    public void Release(bool bHadVisual = true)
    {
        GameplayActive = Math.Max(0, GameplayActive - 1);
        if (bHadVisual) VisualActive = Math.Max(0, VisualActive - 1);
    }
    public void Reset()
    {
        GameplayActive = VisualActive = 0;
        RetryCount = VisualDegradeCount = RejectedCount = 0;
        ++Generation;
    }
}
