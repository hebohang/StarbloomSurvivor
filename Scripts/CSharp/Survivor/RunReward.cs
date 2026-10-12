namespace GameScripts.Survivor;

public sealed class RunRewardInput
{
    public double SurvivalSeconds { get; set; }
    public long Kills { get; set; }
    public long EliteKills { get; set; }
    public long BossKills { get; set; }
    public long Level { get; set; }
    public bool Victory { get; set; }
    public long RevivesUsed { get; set; }
    public long QuestGold { get; set; }
    public long BonusGold { get; set; }
    public double GreedTomeBonus { get; set; }
    public double HoneybunBonus { get; set; }
    public double GlobalGreedBonus { get; set; }
    public double DifficultyReward { get; set; } = 1;
    public double ChallengeReward { get; set; } = 1;
    public string EndReason { get; set; } = "death";
    public double[]? ChallengeRewards { get; set; }
    public int WeaponSlotLimit { get; set; } = 6;
}

// Port of SurvivorEconomy.compute_run_reward; persistence is owned by the host.
public static class RunReward
{
    public const long MaxWalletGold = 2_000_000_000;
    public const long MaxRunCounter = 9_000_000_000;
    public const long MaxRewardComponent = 2_000_000_000;
    private static double Bounded(double value, double maximum)
    {
        if (!double.IsFinite(value)) throw new ArgumentException("Reward values must be finite.");
        return Math.Clamp(value, 0, maximum);
    }
    private static long RewardFloor(double value) => (long)Math.Min(MaxRewardComponent, Math.Floor(value));
    public static double WeaponSlotRewardFactor(int slots) => slots switch
    {
        3 => 1.20, 4 => 1.10, 5 => 1.05, 6 => 1.0,
        _ => throw new ArgumentOutOfRangeException(nameof(slots))
    };
    public static double CombineChallengeRewards(IEnumerable<double>? rewards)
    {
        double result = 1;
        if (rewards is null) return result;
        foreach (double reward in rewards)
        {
            result *= Bounded(reward, 4);
            if (result >= 4) return 4;
        }
        return Math.Min(4, result);
    }
    public static Dictionary<string, double> Compute(RunRewardInput input)
    {
        if (string.IsNullOrEmpty(input.EndReason)) throw new ArgumentException("End reason must be non-empty.");
        double seconds = Bounded(input.SurvivalSeconds, 86_400);
        long kills = Math.Clamp(input.Kills, 0, MaxRunCounter);
        long elites = Math.Clamp(input.EliteKills, 0, MaxRunCounter);
        long bosses = Math.Clamp(input.BossKills, 0, MaxRunCounter);
        long level = Math.Clamp(input.Level, 0, MaxRunCounter);
        long revives = Math.Clamp(input.RevivesUsed, 0, MaxRunCounter);
        long quest = Math.Clamp(input.QuestGold, 0, MaxRewardComponent);
        long bonus = Math.Clamp(input.BonusGold, 0, MaxRewardComponent);
        double slotFactor = WeaponSlotRewardFactor(input.WeaponSlotLimit);
        bool bAbandon = input.EndReason is "abandon" or "restart" or "return_hub";
        bool bVictory = input.Victory && !bAbandon;
        long timeGold = Math.Min(60, (long)Math.Floor(seconds / 15));
        long killGold = Math.Min(75, kills / 40);
        if (bAbandon && seconds < 60) timeGold = killGold = 0;
        long eliteGold = Math.Min(MaxRewardComponent, elites * 4);
        long bossGold = Math.Min(MaxRewardComponent, bosses * 15);
        long levelGold = Math.Min(40, level);
        long clearGold = bVictory ? 80 : 0;
        long noReviveGold = bVictory && revives == 0 ? 20 : 0;
        long subTotal = Math.Min(MaxRewardComponent,
            timeGold + killGold + eliteGold + bossGold + levelGold + clearGold + noReviveGold);
        double bonuses = Bounded(input.GreedTomeBonus, 1) + Bounded(input.HoneybunBonus, 1) + Bounded(input.GlobalGreedBonus, 1);
        double economyFactor = Math.Min(3, 1 + bonuses);
        double challengeFactor = input.ChallengeRewards is null ? Bounded(input.ChallengeReward, 4) : CombineChallengeRewards(input.ChallengeRewards);
        double difficultyFactor = Math.Min(4, Bounded(input.DifficultyReward, 4) * challengeFactor);
        double abandonFactor = bAbandon ? 0.5 : 1;
        long multipliedWithoutSlots = RewardFloor(subTotal * economyFactor * difficultyFactor);
        long multiplied = RewardFloor(subTotal * economyFactor * difficultyFactor * slotFactor);
        long settledBase = (long)Math.Floor(multiplied * abandonFactor);
        long settledWithoutSlots = (long)Math.Floor(multipliedWithoutSlots * abandonFactor);
        long settledBonus = RewardFloor(bonus * slotFactor);
        long nonquest = Math.Min(MaxRewardComponent, settledBase + settledBonus);
        long nonquestWithoutSlots = Math.Min(MaxRewardComponent, settledWithoutSlots + bonus);
        return new()
        {
            ["timeGold"] = timeGold, ["killGold"] = killGold, ["eliteGold"] = eliteGold,
            ["bossGold"] = bossGold, ["levelGold"] = levelGold, ["clearGold"] = clearGold,
            ["noReviveGold"] = noReviveGold, ["subTotal"] = subTotal,
            ["economyFactor"] = economyFactor, ["challengeFactor"] = challengeFactor,
            ["difficultyFactor"] = difficultyFactor, ["weaponSlotFactor"] = slotFactor,
            ["weaponSlotBonusGold"] = Math.Max(0, nonquest - nonquestWithoutSlots),
            ["abandonFactor"] = abandonFactor, ["questGold"] = quest, ["bonusGold"] = bonus,
            ["earnedGold"] = Math.Min(MaxRewardComponent, nonquest + quest)
        };
    }
}
