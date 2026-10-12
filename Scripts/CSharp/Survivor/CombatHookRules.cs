namespace GameScripts.Survivor;

public static class CombatHookRules
{
    public static double TrinketDamage(string[] trinkets,string[] tags,bool fullHealth,bool boss,bool elite,int velocityLevel)
    {
        double multiplier=1;
        if(trinkets.Contains("popcorn_kernel")&&(tags.Contains("explosion")||tags.Contains("zone")))multiplier*=.92;
        if(trinkets.Contains("glass_star")&&fullHealth)multiplier*=1.40;
        if(trinkets.Contains("boss_bell"))multiplier*=boss||elite?1.28:.95;
        if(trinkets.Contains("comet_tail")&&tags.Contains("projectile"))multiplier*=1+Math.Min(.24,(int)(velocityLevel*.12/.20)*.04);
        return multiplier;
    }
}
