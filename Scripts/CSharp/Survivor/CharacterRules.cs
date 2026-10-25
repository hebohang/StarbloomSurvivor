namespace GameScripts.Survivor;

public sealed class CharacterDefinition
{
    public string Weapon { get; set; } = "";
    public Dictionary<string, double> Modifiers { get; set; } = new();
    public string[] Hooks { get; set; } = Array.Empty<string>();
}

public static class CharacterRules
{
    public const double BaseMoveSpeed = 5.1;
    public static double StarpawMight(int level) => Math.Min(.40, (level / 10) * .08);
    public static double HoneyGold(int level) => 1 + Math.Min(40, level) * .0075;
    private static readonly HashSet<string> sModifierKeys = new(StringComparer.Ordinal)
    {
        "max_health_add", "crit_chance_add", "move_speed_mul", "magnet_range_mul",
        "weapon_damage_mul", "weapon_cooldown_mul", "weapon_reach_mul", "projectile_add",
        "projectile_speed_mul", "armor_add", "thorns_add", "evasion_add", "luck_add",
        "xp_gain_mul", "gold_gain_mul", "difficulty_mul"
    };
    public static Dictionary<string, object> CompileStartState(string characterId,
        CharacterDefinition definition, int trainingLevel = 0)
    {
        foreach (string key in definition.Modifiers.Keys)
            if (!sModifierKeys.Contains(key)) throw new ArgumentException("Unknown character modifier: " + key);
        if (trainingLevel < 0 || trainingLevel > 5) throw new ArgumentOutOfRangeException(nameof(trainingLevel));
        double Value(string name, double fallback) => definition.Modifiers.TryGetValue(name, out double value) ? value : fallback;
        return new()
        {
            ["character_id"] = characterId, ["starter_weapon"] = definition.Weapon,
            ["max_health"] = 100 + Value("max_health_add", 0),
            ["crit_chance"] = 0.08 + Value("crit_chance_add", 0),
            ["move_speed"] = BaseMoveSpeed * Value("move_speed_mul", 1),
            ["magnet_range"] = 4.2 * Value("magnet_range_mul", 1),
            ["weapon_damage_multiplier"] = Value("weapon_damage_mul", 1) * (1 + trainingLevel * 0.02),
            ["weapon_cooldown_multiplier"] = Value("weapon_cooldown_mul", 1),
            ["weapon_reach_multiplier"] = Value("weapon_reach_mul", 1),
            ["projectile_bonus"] = (int)Value("projectile_add", 0),
            ["projectile_speed_multiplier"] = Value("projectile_speed_mul", 1),
            ["armor"] = Value("armor_add", 0), ["thorns"] = Value("thorns_add", 0),
            ["evasion"] = Math.Min(CombatRules.MaxEvasion, Value("evasion_add", 0)),
            ["luck"] = Value("luck_add", 0), ["xp_gain_multiplier"] = Value("xp_gain_mul", 1),
            ["gold_gain_multiplier"] = Value("gold_gain_mul", 1),
            ["difficulty_multiplier"] = Value("difficulty_mul", 1), ["hooks"] = (string[])definition.Hooks.Clone()
        };
    }
}
