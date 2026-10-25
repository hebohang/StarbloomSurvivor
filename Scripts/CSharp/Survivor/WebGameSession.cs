using System.Text.Json;
using System.Text.Json.Nodes;
using HEngine;

namespace GameScripts.Survivor;

// Host-neutral session: no browser, files, window, GPU or input device APIs.
public sealed partial class WebGameSession : IGameSession
{
    private static readonly JsonSerializerOptions sJson = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase, IncludeFields = true };
    private readonly JsonObject mCatalog;
    private readonly TerrainSurface mTerrain;
    private JsonObject mProfile;
    private readonly Dictionary<string, JsonObject> mCharacters = new(), mWeapons = new(), mEnemies = new();
    private readonly List<Enemy> mAgents = new();
    private readonly List<Projectile> mProjectiles = new();
    private readonly List<Pickup> mPickups = new();
    private readonly Dictionary<string, int> mWeaponLevels = new(), mTomeLevels = new();
    private readonly Dictionary<string, double> mCooldowns = new();
    private readonly List<string> mWeaponSlots = new(), mTomeSlots = new();
    private readonly HashSet<string> mBanished = new();
    private DeterministicRng mRng = new(7301);
    private UpgradePool? mUpgradePool;
    private JsonObject mCharacterStats = new();
    private JsonObject mDifficulty = new();
    private ChallengeModifiers mChallenges = new();
    private string mMode = "menu", mMessage = "", mCharacter = "starpaw";
    private double mX, mY, mZ, mVerticalSpeed, mYaw, mHealth = 100, mMaxHealth = 100, mElapsed, mSpawnTimer, mHurtTimer, mXp, mShield;
    private int mLevel = 1, mKills, mBossKills, mEliteKills, mNextId, mRerolls, mSkips, mBanishes;
    private int mEnemyLimit=320;
    private long mSaveRevision;
    private long mSeed = 7301;
    private double mBaseDamage, mBaseHealth, mDurationMultiplier = 1;
    private int mRunGold, mRevivesRemaining, mRevivesUsed, mAzuraStacks, mScore;
    private double mDamageTaken,mDamagePrevented,mHealing,mDistanceMoved;
    private readonly Dictionary<string,Dictionary<string,double>> mWeaponStats=new();
    private readonly HEngine.Platform.OrbitCamera mView = new();
    public void ConfigureCamera(double elevation, double sensitivity, double minElevation, double maxElevation, double yaw = 0) =>
        mView.Configure(elevation, sensitivity, minElevation, maxElevation, yaw);
    private readonly HEngine.Platform.InterestRegion mPresentationRegion = new();
    private bool bMoving;
    private bool bAllowAdRevive, bAdReviveUsed;
    private RegionObjectives mObjectives;
    private readonly QuestTracker mQuests;
    private sealed class Enemy
    {
        public int Id; public string Kind = ""; public double X, Z, Yaw, Health, MaxHealth, Speed, Damage, Radius, Timer = 1;
        public double Xp; public bool Boss, Elite; public string Behavior = "",Region=""; public double Windup,Vulnerability,VulnerabilityTimer;
        public double SlowRemaining,SlowMagnitude,FreezeRemaining,PoisonRemaining;public int HoneyMarks,PoisonGeneration;
        public double Phase,PhaseTimer,LockedX,LockedZ,EnemyShield,ShieldTimer,BossElapsed;
        public int AttackPhase,BossPhase=1;public bool AttackCommitted,Enraged;
    }
    private sealed class Projectile
    {
        public long VisualId;
        public double X, Z, Vx, Vz, Radius, Damage, Life, Age; public int Pierce, Bounce; public bool Hostile;
        public string Behavior = "", Weapon = ""; public HashSet<int> Hit = new();
        public double[] Color = new[] { 1.0, .75, .2, .9 };
    }
    private sealed class Pickup { public double X, Z, Xp; public bool Chest; public int Tier; }
    private static double N(JsonNode? node, string key, double fallback = 0)
    {
        if (node?[key] is not JsonValue value) return fallback;
        if (value.TryGetValue<double>(out double number)) return number;
        if (value.TryGetValue<long>(out long integer)) return integer;
        if (value.TryGetValue<int>(out int smallInteger)) return smallInteger;
        return fallback;
    }
    private static string S(JsonNode? node, string key, string fallback = "") => node?[key]?.GetValue<string>() ?? fallback;
    private static bool B(JsonNode? node, string key) => node?[key]?.GetValue<bool>() ?? false;
    private static string[] Strings(JsonNode? value) => value?.AsArray().Select(n => n!.GetValue<string>()).ToArray() ?? System.Array.Empty<string>();
    private static JsonArray Array(JsonObject obj, string key) { if (obj[key] is not JsonArray) obj[key] = new JsonArray(); return obj[key]!.AsArray(); }
    private static JsonObject Object(JsonObject obj, string key) { if (obj[key] is not JsonObject) obj[key] = new JsonObject(); return obj[key]!.AsObject(); }
    private static bool Contains(JsonArray values, string id) => values.Any(n => n?.GetValue<string>() == id);
    private static void AddUnique(JsonArray values, string id) { if (!Contains(values, id)) values.Add(id); }
    private int Tome(string id) => mTomeLevels.GetValueOrDefault(id);
    private int Power(string id) => B(Object(mProfile, "powerUpsEnabled"), id) ? (int)N(Object(mProfile, "powerUps"), id) : 0;

    public WebGameSession(string catalog, string save)
    {
        mCatalog = JsonNode.Parse(catalog)?.AsObject() ?? throw new ArgumentException("Missing catalog");
        mTerrain = new(mCatalog);
        mObjectives = new(mCatalog);
        mProfile = mCatalog["defaultProfile"]!.DeepClone().AsObject();
        if (!string.IsNullOrWhiteSpace(save))
        {
            var loaded = JsonNode.Parse(save)?.AsObject() ?? throw new ArgumentException("Invalid profile");
            // Early portable previews could enter play before Guid.NewGuid failed on hosts
            // without Web Crypto. Repair only that identifiable incomplete receipt.
            if (loaded["lastRun"] is JsonObject receipt && !receipt.ContainsKey("runId")
                && receipt["reward"] is JsonObject && receipt["rewardCommitted"]?.GetValue<bool>() == true)
            {
                receipt["runId"] = "recovered-" + DateTime.UtcNow.Ticks.ToString("x");
                mMessage = "已恢复旧测试版本的结算记录";
                ++mSaveRevision;
            }
            mProfile = ProfileRules.Normalize(loaded, mCatalog);
        }
        foreach (var item in mCatalog["characters"]!.AsArray()) mCharacters[S(item,"id")] = item!.AsObject();
        foreach (var item in mCatalog["weapons"]!.AsArray()) mWeapons[S(item,"id")] = item!.AsObject();
        foreach (var item in mCatalog["enemies"]!.AsArray().Concat(mCatalog["bosses"]!.AsArray())) mEnemies[S(item,"id")] = item!.AsObject();
        mCharacter = S(mProfile, "selectedCharacter", "starpaw");
        if (!mCharacters.ContainsKey(mCharacter)) mCharacter = "starpaw";
        mQuests=new(mProfile,mCatalog["quests"]!.AsArray());
        RecordQuest("profile_created", 1);
    }
    public string Save() => mProfile.ToJsonString();
    public string Snapshot() => JsonSerializer.Serialize(new
    {
        mode = mMode, character = mCharacter, x = mX, y = mY, z = mZ, yaw = mYaw, moving = bMoving,
        health = mHealth, maxHealth = mMaxHealth, shield = mShield, elapsed = mElapsed, level = mLevel,
        xp = mXp, xpRequired = CombatRules.ExperienceRequirement(mLevel), kills = mKills,
        weapons = mWeaponLevels, evolutions = mActiveEvolutions, tomes = mTomeLevels, trinkets=mTrinkets, score=mScore, choices = mUpgradePool?.CurrentChoices,
        telemetry=new{damageTaken=mDamageTaken,damagePrevented=mDamagePrevented,healing=mHealing,distanceMoved=mDistanceMoved,weapons=mWeaponStats},domains=mDomains,
        objective = mObjectives.ObjectiveState, regions = mObjectives.Regions,
        enemies = mAgents.Where(e=>mPresentationRegion.Contains(e.X,e.Z,mX,mZ)).Select(e => new { e.Id, e.Kind, e.X, y = mTerrain.Height(e.X,e.Z)??0, e.Z, e.Yaw, e.Health, e.MaxHealth, e.Boss, e.Elite, e.Windup }),
        projectiles = mProjectiles.Where(p=>mPresentationRegion.Contains(p.X,p.Z,mX,mZ)).Select(p => (object)new { id=p.VisualId, p.Weapon, p.Behavior, p.Hostile, p.Vx, p.Vz, p.Age, p.X, y = mTerrain.Height(p.X,p.Z)??0, p.Z, p.Radius, p.Color }).Concat(AreaVisuals()),
        areas = mAreas.Where(a=>mPresentationRegion.Contains(a.X,a.Z,mX,mZ)).Select(a=>new {id=a.VisualId,a.Weapon,a.X,y=mTerrain.Height(a.X,a.Z)??0,a.Z,a.Radius,a.Age,a.Delay,a.Ring,a.Hostile}),
        beams = mBeams.Where(b=>mPresentationRegion.Contains(b.X,b.Z,mX,mZ)).Select(b=>new {id=b.VisualId,b.Weapon,b.X,y=mTerrain.Height(b.X,b.Z)??0,b.Z,b.Dx,b.Dz,b.Length,b.Delay}),
        presentationEvents = mPresentationEvents,
        pickups = mPickups.Where(p=>mPresentationRegion.Contains(p.X,p.Z,mX,mZ)).Select(p => new { p.X, y = mTerrain.Height(p.X,p.Z)??0, p.Z, p.Chest }),
        profile = mProfile, message = mMessage, saveRevision = mSaveRevision, seed = mSeed,
        cameraYaw = mView.Yaw, cameraElevation = mView.Elevation,
        rerolls = mUpgradePool?.RerollsRemaining ?? mRerolls, skips = mUpgradePool?.SkipsRemaining ?? mSkips,
        banishes = mUpgradePool?.BanishesRemaining ?? mBanishes
    }, sJson);
    public string Command(string name, string value)
    {
        if (name == "shared_restart" && mMode == "paused")
        {
            Command("abandon", "");
            Command("home", "");
            return Command("start", "");
        }
        // Element IDs from the shared Editor-authored pause document. Every host
        // forwards the same event; gameplay commands remain owned by this session.
        name = name switch { "shared_resume" => "resume", "shared_abandon" => "abandon", _ => name };
        if (name == "look")
        {
            var delta = JsonNode.Parse(value)!.AsArray();
            if (mMode == "playing") mView.Drag(delta[0]!.GetValue<double>(), delta[1]!.GetValue<double>());
            return Snapshot();
        }
        mMessage = "";
        switch (name)
        {
            case "configureInterestRadius" when mMode == "menu": mPresentationRegion.Configure(double.Parse(value,System.Globalization.CultureInfo.InvariantCulture));break;
            case "configureVisualBudget" when mMode == "menu": mFriendlyVisualBudget=Math.Clamp(int.Parse(value,System.Globalization.CultureInfo.InvariantCulture),16,512);break;
            case "configureEnemyLimit" when mMode == "menu": mEnemyLimit=Math.Clamp(int.Parse(value,System.Globalization.CultureInfo.InvariantCulture),64,320);break;
            case "configureAdRevive" when mMode == "menu": bAllowAdRevive = value == "true"; break;
            case "rewardRevive" when mMode == "revive" && bAllowAdRevive && !bAdReviveUsed:
                bAdReviveUsed=true;++mRevivesUsed;mHealth=mMaxHealth*.5;mHurtTimer=3;mMode="playing";break;
            case "declineRevive" when mMode == "revive": Finish("death");break;
            case "selectCharacter" when mMode == "menu":
                if (!mCharacters.ContainsKey(value) || !Contains(Array(Object(mProfile,"owned"),"characters"), value)) throw new ArgumentException("Character is not owned");
                mCharacter = value; mProfile["selectedCharacter"] = value; ++mSaveRevision; break;
            case "difficulty" when mMode == "menu":
                var difficulty=mCatalog["difficulties"]!.AsArray().FirstOrDefault(d=>S(d,"id")==value)??throw new ArgumentException("Unknown difficulty");
                if(S(difficulty,"unlockId").Length>0&&!Contains(Array(mProfile,"completedQuests"),S(difficulty,"unlockId")))throw new ArgumentException("Difficulty is locked");
                mProfile["selectedDifficulty"] = value; ++mSaveRevision; break;
            case "challenge" when mMode == "menu":
                var ids = mCatalog["challenges"]!.AsArray().Select(c=>S(c,"id")).ToArray();
                mProfile["selectedChallenges"] = JsonSerializer.SerializeToNode(ChallengeRules.ToggleId(Strings(mProfile["selectedChallenges"]), value, ids)); ++mSaveRevision; break;
            case "start" when mMode == "menu": Start(); break;
            case "jump" when mMode == "playing": if(mY<=(mTerrain.Height(mX,mZ)??0)+.06)mVerticalSpeed=5.8; break;
            case "pause" when mMode == "playing": mMode="paused"; break;
            case "resume" when mMode == "paused": mMode="playing"; break;
            case "abandon" when mMode is "paused" or "playing" or "upgrade": Finish("abandon"); break;
            case "home" when mMode == "result": mMode="menu"; mAgents.Clear(); mProjectiles.Clear(); mPickups.Clear(); break;
            case "upgrade" when mMode == "upgrade": Choose(value); break;
            case "reroll" when mMode == "upgrade": mUpgradePool!.Reroll(); break;
            case "skip" when mMode == "upgrade": if(mUpgradePool!.Skip().Status=="skipped") ResumeUpgrade(); break;
            case "banish" when mMode == "upgrade": if(mUpgradePool!.Banish(value).Status=="banished")mBanished.Add(value); break;
            case "buy" when mMode == "menu": Buy(value); break;
            case "power" when mMode == "menu": BuyPower(value); break;
            case "refundPower" when mMode == "menu": RefundPower(value); break;
            case "refundAllPower" when mMode == "menu": RefundAllPower(); break;
            case "trackQuest" when mMode == "menu": ToggleQuestTracking(value); break;
            case "unsealPool" when mMode == "menu":
                if (value is not ("weapons" or "tomes" or "trinkets")) throw new ArgumentException("Unknown pool");
                Array(Object(mProfile,"poolDisabled"),value).Clear();++mSaveRevision;break;
            case "seed" when mMode == "menu": mSeed = long.Parse(value, System.Globalization.CultureInfo.InvariantCulture); break;
            case "weaponSlots" when mMode == "menu":
                int slots = int.Parse(value, System.Globalization.CultureInfo.InvariantCulture);
                if (slots < 3 || slots > Math.Min(6, 3 + N(Object(mProfile,"powerUps"),"meta_weapon_slots"))) throw new ArgumentException("Weapon slot limit is not purchased");
                mProfile["selectedWeaponSlotLimit"] = slots; ++mSaveRevision; break;
            case "train" when mMode == "menu":
                if (!Contains(Array(Object(mProfile,"owned"),"characters"), value)) throw new ArgumentException("Character is not owned");
                var training = Object(mProfile,"characterTraining"); int rank = (int)N(training,value); int[] costs = [100,200,350,550,800];
                if (rank >= costs.Length) { mMessage="已达最高等级"; break; }
                if (N(mProfile,"walletGold") < costs[rank]) { mMessage="金币不足"; break; }
                mProfile["walletGold"] = N(mProfile,"walletGold") - costs[rank]; training[value] = rank + 1; ++mSaveRevision; break;
            case "toggleTraining" when mMode == "menu":
                if (!mCharacters.ContainsKey(value)) throw new ArgumentException("Unknown character");
                var trainingEnabled = Object(mProfile,"characterTrainingEnabled"); trainingEnabled[value] = !(trainingEnabled[value]?.GetValue<bool>() ?? true); ++mSaveRevision; break;
            case "togglePower" when mMode == "menu":
                var powerDefinition = mCatalog["metaPowerUps"]!.AsArray().FirstOrDefault(p=>S(p,"id")==value) ?? throw new ArgumentException("Unknown power");
                if (powerDefinition["toggleable"]?.GetValue<bool>() == false) throw new ArgumentException("This capability cannot be disabled");
                Object(mProfile,"powerUpsEnabled")[value] = !B(Object(mProfile,"powerUpsEnabled"),value); ++mSaveRevision; break;
            case "togglePool" when mMode == "menu":
                string group = new[]{"weapons","tomes","trinkets"}.FirstOrDefault(g=>Contains(Array(Object(mProfile,"owned"),g),value)) ?? throw new ArgumentException("Item is not owned");
                var disabled = Array(Object(mProfile,"poolDisabled"),group);
                if (!Contains(disabled,value))
                {
                    bool sealing = Contains(Array(mProfile,"completedQuests"),"quest_system_seal") ||
                        new[]{"weapons","tomes","trinkets"}.Any(g=>Array(Object(mProfile,"poolDisabled"),g).Count>0);
                    if (!sealing || (group=="weapons" && value==S(mCharacters[mCharacter],"starterWeapon")) ||
                        Array(Object(mProfile,"owned"),group).Count-disabled.Count <= (group=="trinkets"?4:6))
                    { mMessage="当前内容不能封印";break; }
                }
                if (Contains(disabled,value)) disabled.Remove(disabled.First(n=>n!.GetValue<string>()==value)); else disabled.Add(value);
                ++mSaveRevision; break;
            default: throw new InvalidOperationException("Command not available: " + name);
        }
        return Snapshot();
    }
    private void Start()
    {
        mMode="playing";mElapsed=mX=mZ=mYaw=mXp=mSpawnTimer=mHurtTimer=mShield=0;mLevel=1;mKills=mBossKills=mEliteKills=0;mNextId=0;mObjectives=new(mCatalog);
        mPresentationEvents.Clear();
        mY=mTerrain.Height(0,0)??0;mVerticalSpeed=0;
        mBanished.Clear();
        ResetCombatHooks();
        ResetEncounters();
        mDamageTaken=mDamagePrevented=mHealing=mDistanceMoved=0;mWeaponStats.Clear();
        mQuests.ResetRun();
        mAgents.Clear();mProjectiles.Clear();mPickups.Clear();mAreas.Clear();mBeams.Clear();mWeaponLevels.Clear();mTomeLevels.Clear();mWeaponSlots.Clear();mTomeSlots.Clear();mCooldowns.Clear();mUpgradePool=null;
        mEnemyGrid.Clear();mCrowdTick=0;mSeparationTime=0;
        mRng = new(mSeed);
        var definition=mCatalog["characterDefinitions"]![mCharacter]!.Deserialize<CharacterDefinition>(sJson)!;
        int training=Object(mProfile,"characterTrainingEnabled")[mCharacter]?.GetValue<bool>() == false ? 0 : (int)Math.Clamp(N(Object(mProfile,"characterTraining"),mCharacter),0,5);
        mCharacterStats=JsonSerializer.SerializeToNode(CharacterRules.CompileStartState(mCharacter,definition,training))!.AsObject();
        mBaseDamage=N(mCharacterStats,"weapon_damage_multiplier",1)*(1+.03*Power("meta_might"))*(1+Math.Min(10,(int)N(Object(mProfile,"characterMasteryXp"),mCharacter)/500)*.003);
        mCharacterStats["weapon_damage_multiplier"]=mBaseDamage;
        bAdReviveUsed=false;
        mRunGold=mRevivesUsed=mAzuraStacks=mScore=0;mDurationMultiplier=1;mRevivesRemaining=Power("meta_revive")>0?1:0;
        mDifficulty=mCatalog["difficulties"]!.AsArray().First(d=>S(d,"id")==S(mProfile,"selectedDifficulty","adventure"))!.AsObject();
        var selected=Strings(mProfile["selectedChallenges"]);
        mChallenges=ChallengeRules.Combine(mCatalog["challenges"]!.AsArray().Where(d=>selected.Contains(S(d,"id"))).Select(d=>d!.Deserialize<ChallengeDefinition>(sJson)!));
        mMaxHealth=N(mCharacterStats,"max_health",100)*(1+.05*Power("meta_health"));
        mBaseHealth=mMaxHealth;
        if(mChallenges.PlayerMaxHealth is double cap)mMaxHealth=Math.Min(mMaxHealth,cap);
        mHealth=mMaxHealth;string starter=S(mCharacters[mCharacter],"starterWeapon");mWeaponLevels[starter]=1;mWeaponSlots.Add(starter);
        int QuestBonus(string id)=>Contains(Array(mProfile,"completedQuests"),"quest_system_"+id)?1:0;
        mRerolls=Power("meta_reroll")+QuestBonus("reroll");mSkips=Power("meta_skip")+QuestBonus("skip");mBanishes=Power("meta_banish")+QuestBonus("banish");
        // This is a local idempotency key, not a security token. No host entropy API
        // is needed; monotonic revision disambiguates starts within the same tick.
        mProfile["lastRun"]=new JsonObject { ["runId"]=$"{DateTime.UtcNow.Ticks:x}-{mSaveRevision:x}",["rewardCommitted"]=false,["characterId"]=mCharacter,["difficultyId"]=S(mDifficulty,"id"),["challengeIds"]=mProfile["selectedChallenges"]!.DeepClone(),["weaponSlotLimit"]=mProfile["selectedWeaponSlotLimit"]!.DeepClone() };
        ++mSaveRevision;
    }
    public string Step(double seconds,double inputX,double inputZ)
    {
        if(!double.IsFinite(seconds)||!double.IsFinite(inputX)||!double.IsFinite(inputZ))throw new ArgumentException("Non-finite frame input");
        if(mMode!="playing")return Snapshot();
        double dt=Math.Clamp(seconds,0,.05),length=Math.Sqrt(inputX*inputX+inputZ*inputZ);bMoving=length>.01;
        if(length>1){inputX/=length;inputZ/=length;}
        (inputX,inputZ)=mView.Movement(inputX,inputZ);
        double speed=N(mCharacterStats,"move_speed",CharacterRules.BaseMoveSpeed)*(1+.03*Power("meta_move"));
        double nextX=mX+inputX*speed*dt,nextZ=mZ+inputZ*speed*dt;
        double? nextHeight=mTerrain.Height(nextX,nextZ);
        double walked=0;if(nextHeight.HasValue&&nextHeight.Value<=mY+.4){walked=Distance(nextX-mX,nextZ-mZ);mX=nextX;mZ=nextZ;}
        double floor=mTerrain.Height(mX,mZ)??0;mVerticalSpeed-=9.8*dt;mY+=mVerticalSpeed*dt;
        if(mY<=floor){mY=floor;mVerticalSpeed=0;}if(bMoving)mYaw=Math.Atan2(inputX,inputZ);
        mElapsed+=dt*mChallenges.Clock;mHurtTimer=Math.Max(0,mHurtTimer-dt);
        UpdateCombatHooks(dt,walked);
        mDistanceMoved+=walked;
        Heal(dt*(.2*Tome("recovery")+.05*Power("meta_recovery")));
        UpdateObjectives(dt);UpdateEncounters(dt);SpawnWaves(dt);RebuildEnemyIndex();UpdateDomains(dt);UpdateWeapons(dt);UpdateProjectiles(dt);UpdateAreas(dt);UpdateEnemies(dt);SeparateEnemies(dt);UpdatePickups(dt);
        RecordQuest("survival_seconds",mElapsed,true);RecordQuest("best_level",mLevel,true);
        if(mHealth<=0)
        {
            if(mRevivesRemaining>0){--mRevivesRemaining;++mRevivesUsed;mHealth=mMaxHealth*.5;mHurtTimer=Math.Max(mHurtTimer,1);}
            else if(bAllowAdRevive&&!bAdReviveUsed){mMode="revive";mMessage="观看完整视频可复活一次，恢复一半生命";}
            else Finish("death");
        }
        return Snapshot();
    }
    private void SpawnWaves(double dt)
    {
        mSpawnTimer-=dt;if(mSpawnTimer>0)return;
        var wave=mCatalog["waves"]!.AsArray().LastOrDefault(w=>N(w,"start")<=mElapsed)??mCatalog["waves"]![0]!;
        double progress=Math.Clamp((mElapsed-N(wave,"start"))/Math.Max(1,N(wave,"end")-N(wave,"start")),0,1);
        int target=WorldTarget(progress,wave);
        mSpawnTimer=N(wave,"spawnInterval",.65);
        var pool=wave["pool"]!.AsArray();var weights=pool.Select(p=>p![1]!.GetValue<double>()).ToArray();
        for(int i=0;i<(int)N(wave,"batch",2)&&mAgents.Count(e=>e.Region.Length==0)<target&&mAgents.Count<mEnemyLimit;i++) Spawn(pool[mRng.WeightedIndex(weights)]![0]!.GetValue<string>(),wave);
    }
    private void UpdateObjectives(double dt)
    {
        string? eventName=mObjectives.Update(dt,mX,mZ);
        if(eventName=="boss_spawn_requested") {Spawn("star_dragon",new JsonObject());mMessage="最终目标：星龙降临";}
        else if(eventName?.StartsWith("region_activated:")==true)
        {
            string id=eventName.Split(':')[1];AddUnique(Array(mProfile,"discoveredDomains"),"domain_"+id);
            GrantDomain(id);
            mPickups.Add(new(){X=mX,Z=mZ,Chest=true,Tier=new[]{1,2,2,3}[mObjectives.Completed.Count-1]});
            foreach(var pickup in mPickups)if(!pickup.Chest){pickup.X=mX;pickup.Z=mZ;}
            string regionName=id switch {"star"=>"星之区域","thunder"=>"雷之区域","water"=>"水之区域","wind"=>"风之区域",_=>"未知区域"};
            mMessage=mObjectives.Completed.Count==4?"四个区域已激活，返回中央星台召唤星龙":"区域已激活："+regionName;
            ++mSaveRevision;
        }
        else if(eventName=="region_assault_started")mMessage="守住区域 60 秒";
        else if(eventName=="region_failed")mMessage="离开区域过久，挑战将在冷却后重置";
    }
    private void Spawn(string kind,JsonNode wave)
    {
        if(!mEnemies.TryGetValue(kind,out var d))throw new InvalidOperationException("Missing enemy "+kind);
        double angle=mRng.Unit()*Math.PI*2,distance=14+mRng.Unit()*6;bool boss=B(d,"boss"),elite=!boss&&mRng.Unit()<N(wave,"eliteRate");
        double health=N(d,"health")*N(wave,"healthMultiplier",1)*N(mDifficulty,"health",1)*mChallenges.EnemyHealth*(elite?2.5:1);
        mAgents.Add(new(){Id=++mNextId,Kind=kind,X=mX+Math.Sin(angle)*distance,Z=mZ+Math.Cos(angle)*distance,Health=health,MaxHealth=health,
            Speed=N(d,"speed")*N(wave,"speedMultiplier",1)*N(mDifficulty,"speed",1)*mChallenges.EnemySpeed,
            Damage=N(d,"damage")*N(wave,"damageMultiplier",1)*N(mDifficulty,"damage",1)*mChallenges.EnemyDamage,
            Radius=N(d,"radius",.7),Xp=(int)N(d,"rewardXp",1)*(elite?4:1),Behavior=S(d,"behaviorId"),Boss=boss,Elite=elite,Phase=mRng.Unit()*Math.PI*2,Timer=mRng.Unit()*.3});
    }
    private Enemy? Nearest(double x,double z,double range=30)
    {
        mEnemyGrid.Query(x,z,range,mNearestCandidates);Enemy? best=null;double bestDistance=range*range;
        foreach(var e in mNearestCandidates){if(e.Health<=0)continue;double d=DistanceSquared(e.X-x,e.Z-z);if(d<bestDistance||best!=null&&d==bestDistance&&e.Id<best.Id){best=e;bestDistance=d;}}
        return best;
    }
    private static double Distance(double x,double z)=>Math.Sqrt(x*x+z*z);
    private void UpdateWeapons(double dt)
    {
        foreach(var echo in mEchoes.ToArray())
        {
            echo.Delay-=dt;if(echo.Delay>0)continue;mEchoes.Remove(echo);
            double previous=mCooldowns.GetValueOrDefault(echo.Weapon);CastWeapon(echo.Weapon,.45,true);mCooldowns[echo.Weapon]=previous;
        }
        foreach(string id in mWeaponSlots.ToArray())
        {
            mCooldowns[id]=mCooldowns.GetValueOrDefault(id)-dt;if(mCooldowns[id]>0)continue;
            CastWeapon(id);
        }
    }
    private void CastWeapon(string id,double proc=1,bool echo=false)
    {
            if(!mWeapons.TryGetValue(id,out var w))return;var target=Nearest(mX,mZ);if(target is null)return;
            double damage=N(w,"baseDamage"),cooldown=N(w,"cooldown"),area=N(w,"area"),speed=N(w,"speed"),duration=N(w,"duration");int amount=(int)N(w,"amount",1),pierce=(int)N(w,"pierce"),bounce=(int)N(w,"bounce");
            double damageMul=1,hasteMul=1;foreach(var step in w["levelPlan"]!.AsArray())if(N(step,"level")<=mWeaponLevels[id]){damageMul+=N(step,"damageMultiplierAdd");hasteMul+=N(step,"cooldownMultiplierAdd");amount+=(int)N(step,"amountAdd");pierce+=(int)N(step,"pierceAdd");bounce+=(int)N(step,"bounceAdd");area+=N(step,"areaAdd");duration+=N(step,"durationAdd");}
            damage*=damageMul*N(mCharacterStats,"weapon_damage_multiplier",1)*(1+.08*Tome("might"))*(1+.04*mAzuraStacks)*proc;
            cooldown*=Math.Max(.55,hasteMul)*N(mCharacterStats,"weapon_cooldown_multiplier",1)*Math.Max(.45,1-.05*Tome("haste"));
            area*=N(mCharacterStats,"weapon_reach_multiplier",1)*(1+.07*Tome("reach"));speed*=N(mCharacterStats,"projectile_speed_multiplier",1)*(1+.12*Tome("velocity"));duration*=1+.12*Tome("duration");
            duration*=mDurationMultiplier;
            if(mTrinkets.Contains("friendship_pin")&&mWeaponSlots.OrderBy(w=>mWeaponLevels[w]).ThenBy(w=>w,StringComparer.Ordinal).FirstOrDefault()==id)amount++;
            if(mTrinkets.Contains("popcorn_kernel")&&(WeaponTag(id,"explosion")||WeaponTag(id,"zone")))area*=1.3;
            if(mTrinkets.Contains("bloom_battery")&&(WeaponTag(id,"zone")||WeaponTag(id,"tick")))duration*=.9;
            amount+=(int)N(mCharacterStats,"projectile_bonus")+Math.Min(3,(Tome("quantity")+1)/2);amount=Math.Clamp(amount,1,24);mCooldowns[id]=cooldown;
            string behavior=S(w,"behavior");double angle=Math.Atan2(target.X-mX,target.Z-mZ);
            int areasBefore=mAreas.Count;
            if(CastAreaWeapon(id,behavior,damage,area,duration,amount,target)){if(mCooldowns[id]>.15&&(behavior!="orbit_contact"||mAreas.Count>areasBefore))OnWeaponCast(id,echo);return;}
            for(int i=0;i<amount;i++)
            {
                double a=behavior=="radial_projectile"?i*Math.PI*2/amount:angle+(i-(amount-1)*.5)*.16;
                mProjectiles.Add(new(){VisualId=++mNextVisualId,X=mX,Z=mZ,Vx=Math.Sin(a)*Math.Max(1,speed),Vz=Math.Cos(a)*Math.Max(1,speed),Radius=Math.Min(1,area*.45),Damage=damage,
                    Life=Math.Min(8,Math.Max(.5,duration)),Pierce=pierce,Bounce=bounce,Behavior=behavior,Weapon=id,Color=id is "fireball" or "acornmortar"?new[]{1.0,.4,.12,.9}:new[]{.5,.85,1.0,.9}});
            }
            RecordQuest("projectiles_spawned",amount);
            OnWeaponCast(id,echo);
    }
    private void UpdateProjectiles(double dt)
    {
        foreach(var p in mProjectiles.ToArray())
        {
            p.Age+=dt;p.Life-=dt;if(p.Life<=0){mProjectiles.Remove(p);continue;}if(p.Behavior=="visual")continue;
            if(p.Behavior is "homing_volley" or "lob_homing") {var t=Nearest(p.X,p.Z);if(t is not null){double d=Distance(t.X-p.X,t.Z-p.Z),speed=Distance(p.Vx,p.Vz);if(d>.01){p.Vx=(t.X-p.X)/d*speed;p.Vz=(t.Z-p.Z)/d*speed;}}}
            if(p.Behavior is "returning" or "returning_lob" && p.Age>.5){double d=Distance(mX-p.X,mZ-p.Z),speed=Distance(p.Vx,p.Vz);if(d>.1){p.Vx=(mX-p.X)/d*speed;p.Vz=(mZ-p.Z)/d*speed;}}
            p.X+=p.Vx*dt;p.Z+=p.Vz*dt;
            if(p.Behavior=="travelVisual")continue;
            if(p.Hostile){if(p.Behavior!="enemyLob"&&Distance(p.X-mX,p.Z-mZ)<p.Radius+.4){if(bRoyalBubbleShield)bRoyalBubbleShield=false;else Hurt(p.Damage);mProjectiles.Remove(p);}continue;}
            ProjectileCandidates(p);
            foreach(var e in mProjectileCandidates)
            {
                if(e.Health<=0||p.Hit.Contains(e.Id)||DistanceSquared(e.X-p.X,e.Z-p.Z)>(p.Radius+e.Radius)*(p.Radius+e.Radius))continue;
                p.Hit.Add(e.Id);Hit(e,p.Damage,p.Weapon);
                if(p.Behavior is "lob_homing" or "lob_zone" or "lob_split"){
                    mEnemyGrid.Query(e.X,e.Z,2,mSplashCandidates);OrderCandidates(mSplashCandidates);
                    foreach(var nearby in mSplashCandidates)if(nearby.Id!=e.Id&&DistanceSquared(nearby.X-e.X,nearby.Z-e.Z)<4)Hit(nearby,p.Damage*.65,p.Weapon);
                }
                if(p.Bounce-->0){var next=mAgents.Where(a=>!p.Hit.Contains(a.Id)).OrderBy(a=>Distance(a.X-p.X,a.Z-p.Z)).FirstOrDefault();if(next is not null){double d=Distance(next.X-p.X,next.Z-p.Z),s=Distance(p.Vx,p.Vz);p.Vx=(next.X-p.X)/Math.Max(.01,d)*s;p.Vz=(next.Z-p.Z)/Math.Max(.01,d)*s;}break;}
                if(p.Pierce--<=0){mProjectiles.Remove(p);break;}
            }
        }
    }
    private void Hurt(double damage,Enemy? source=null)
    {
        if(mHurtTimer>0)return;bool block=mTrinkets.Contains("marshmallow_shield")&&bMarshmallowReady;
        var hit=CombatRules.ResolveDefense(damage,mRng.Unit(),N(mCharacterStats,"evasion"),N(mCharacterStats,"armor"),.06*Tome("guard"),mShield+(block?Math.Max(1,damage):0));
        mShield=Math.Max(0,mShield-Math.Max(0,hit.ShieldAbsorbed-(block?Math.Max(1,damage):0)));
        if(block){bMarshmallowReady=false;mMarshmallowTimer=0;}
        mHealth=Math.Max(0,mHealth-hit.Damage);if(hit.Damage>0)mHurtTimer=CombatRules.PlayerHurtIframe;
        mDamageTaken+=hit.Damage;mDamagePrevented+=hit.ArmorPrevented+hit.ReductionPrevented+hit.ShieldAbsorbed;
        OnDefense(hit,source);
    }
    private void Hit(Enemy enemy,double damage,string weapon,bool canCritical=true)
    {
        if(enemy.Health<=0)return;
        bool domain=weapon.StartsWith("domain_",StringComparison.Ordinal);
        if(!domain)damage*=TrinketDamage(weapon,enemy)*(enemy.VulnerabilityTimer>0?1+enemy.Vulnerability:1);
        double crit=Math.Min(.5,N(mCharacterStats,"crit_chance",.08)+.02*Power("meta_luck")+.03*Tome("fortune"));bool critical=!domain&&canCritical&&mRng.Unit()<crit;if(critical)damage*=2+.08*Tome("fortune");
        damage*=1-Math.Clamp(N(mEnemies[enemy.Kind]["resistances"],"damage"),0,1);
        double absorbed=Math.Min(enemy.EnemyShield,damage);enemy.EnemyShield-=absorbed;damage-=absorbed;
        double applied=Math.Min(enemy.Health,damage);enemy.Health-=damage;if(!domain)OnWeaponHit(enemy,applied,weapon,critical);else DomainHit(enemy,weapon);
        EmitPresentation("impact",weapon,enemy.X,enemy.Z,applied,critical);
        if(!domain){WeaponMetric(weapon,"damage",applied);WeaponMetric(weapon,"hits",1);if(critical)WeaponMetric(weapon,"crits",1);}
        if(enemy.Health>0||!mAgents.Contains(enemy))return;
        OnEnemyKilled(enemy,critical);mKills++;if(enemy.Elite)mEliteKills++;if(enemy.Boss)mBossKills++;
        if(!domain)WeaponMetric(weapon,"kills",1);
        double xp=EnemyExperience(enemy);if(xp>0)mPickups.Add(new(){X=enemy.X,Z=enemy.Z,Xp=xp});if(enemy.Boss||enemy.Elite&&enemy.Region.Length==0)mPickups.Add(new(){X=enemy.X+.5,Z=enemy.Z,Chest=true,Tier=enemy.Boss?3:1});
        mAgents.Remove(enemy);RecordQuest("kills",1);if(enemy.Boss)RecordQuest("boss_kills",1);
        if(enemy.Kind=="star_dragon"){mObjectives.Victory();Finish("victory");}
    }
    private void UpdatePickups(double dt)
    {
        double range=N(mCharacterStats,"magnet_range",4.2)*(1+.18*Tome("magnet"))*(1+.125*Power("meta_magnet"))*(1+mMagnetStacks*.05);
        foreach(var p in mPickups.ToArray())
        {
            double d=Distance(p.X-mX,p.Z-mZ);if(d<.85){mPickups.Remove(p);if(p.Chest){OpenChest(p.Tier);continue;}if(mTrinkets.Contains("tiny_magnet")){mMagnetStacks=Math.Min(8,mMagnetStacks+1);mMagnetTimer=0;}mXp+=p.Xp*(1+.07*Tome("growth"))*(1+.03*Power("meta_growth"))*N(mCharacterStats,"xp_gain_multiplier",1)*mChallenges.Xp;}
            else if(d<range&&!p.Chest){p.X+=(mX-p.X)/d*Math.Min(d,dt*12);p.Z+=(mZ-p.Z)/d*Math.Min(d,dt*12);}
        }
        if(mXp>=CombatRules.ExperienceRequirement(mLevel)&&mMode=="playing")
        {
            mXp-=CombatRules.ExperienceRequirement(mLevel);mLevel++;
            if(mCharacter=="starpaw")mCharacterStats["weapon_damage_multiplier"]=mBaseDamage*(1+CharacterRules.StarpawMight(mLevel));
            if(mCharacter=="honeybun")mCharacterStats["gold_gain_multiplier"]=CharacterRules.HoneyGold(mLevel);
            if(mCharacter=="cosmobob"&&mLevel%5==0)
            {
                string key=new[]{"weapon_damage_multiplier","weapon_reach_multiplier","weapon_cooldown_multiplier","move_speed","duration"}[(int)(mRng.Unit()*5)];
                if(key=="duration")mDurationMultiplier*=1.02;
                else mCharacterStats[key]=N(mCharacterStats,key,1)*(key=="weapon_cooldown_multiplier"?.98:1.02);
            }
            var owned=Object(mProfile,"owned");var disabled=Object(mProfile,"poolDisabled");
            mUpgradePool=new(new(){Weapons=mCatalog["weapons"]!.Deserialize<UpgradeDefinition[]>(sJson)!,Tomes=mCatalog["tomes"]!.Deserialize<UpgradeDefinition[]>(sJson)!,
                Owned=new(){["weapons"]=Strings(owned["weapons"]),["tomes"]=Strings(owned["tomes"])},
                Enabled=new(){["weapons"]=Strings(owned["weapons"]).Except(Strings(disabled["weapons"])).ToArray(),["tomes"]=Strings(owned["tomes"]).Except(Strings(disabled["tomes"])).ToArray()},
                WeaponLevels=new(mWeaponLevels),TomeLevels=new(mTomeLevels),WeaponSlots=mWeaponSlots.ToArray(),TomeSlots=mTomeSlots.ToArray(),MaxWeaponSlots=(int)N(mProfile,"selectedWeaponSlotLimit",3),
                Seed=mRng.NextU32(),Rerolls=mRerolls,Skips=mSkips,Banishes=mBanishes,ExcludedIds=mBanished.ToArray()});
            mUpgradePool.Roll();mMode="upgrade";
        }
    }
    private void Choose(string id)
    {
        var choice=mUpgradePool!.CurrentChoices.FirstOrDefault(c=>c.Id==id)??throw new ArgumentException("Invalid upgrade choice");
        if(choice.Category=="weapons"){mWeaponLevels[id]=choice.NextLevel;if(!mWeaponSlots.Contains(id))mWeaponSlots.Add(id);}
        else if(choice.Category=="tomes"){mTomeLevels[id]=choice.NextLevel;if(!mTomeSlots.Contains(id))mTomeSlots.Add(id);if(id=="vitality"){mMaxHealth=mBaseHealth*(1+.08*Tome(id));if(mChallenges.PlayerMaxHealth is double cap)mMaxHealth=Math.Min(mMaxHealth,cap);mHealth=Math.Min(mMaxHealth,mHealth+mMaxHealth*.08);}}
        else if(id=="snack")Heal(mMaxHealth*.35);
        else if(id=="bonus")mScore+=750;
        else if(id=="spark"){mMaxHealth+=12;mHealth=Math.Min(mMaxHealth,mHealth+12);mCharacterStats["crit_chance"]=Math.Min(.5,N(mCharacterStats,"crit_chance")+.01);}
        if(mCharacter=="azura"&&choice.Category is "weapons" or "tomes"&&choice.NextLevel>=(int)N(mCatalog[choice.Category]!.AsArray().First(n=>S(n,"id")==id),"maxLevel",choice.Category=="weapons"?10:5))mAzuraStacks=Math.Min(6,mAzuraStacks+1);
        ResumeUpgrade();
    }
    private void ResumeUpgrade(){mRerolls=mUpgradePool!.RerollsRemaining;mSkips=mUpgradePool.SkipsRemaining;mBanishes=mUpgradePool.BanishesRemaining;mUpgradePool=null;mMode="playing";}
    private void OpenChest(int tier)
    {
        var recipes=mCatalog["evolutions"]!.Deserialize<EvolutionRecipe[]>(sJson)!.Where(r=>!mActiveEvolutions.ContainsKey(r.WeaponId)).ToArray();
        var resolver=new EvolutionResolver(new(){Recipes=recipes,WeaponLevels=new(mWeaponLevels),TomeLevels=new(mTomeLevels),WeaponSlots=mWeaponSlots.ToArray(),Discovered=Strings(mProfile["discoveredEvolutions"])});
        var receipt=resolver.ResolveChest(tier);if(receipt.Status=="evolved")
        {
            // The resolver describes inventory replacement; the Python runtime keeps
            // base weapon levels and activates a separate behavior override.
            foreach(string id in receipt.Evolutions){var recipe=recipes.First(r=>r.Id==id);mActiveEvolutions[recipe.WeaponId]=id;mCooldowns[recipe.WeaponId]=0;}
            RecordQuest("evolutions",receipt.Evolutions.Length);RecordQuest("evolutions_in_run",mActiveEvolutions.Count,true);
            mProfile["discoveredEvolutions"]=JsonSerializer.SerializeToNode(receipt.Discovered);mMessage="武器进化！";
        }
        else if(!TryEquipTrinket())
        {
            var candidates=mWeaponSlots.Where(id=>mWeaponLevels[id]<(int)N(mWeapons[id],"maxLevel",10)).Select(id=>(Level:mWeaponLevels[id],Category:"weapon",Id:id))
                .Concat(mTomeSlots.Where(id=>mTomeLevels[id]<5).Select(id=>(Level:mTomeLevels[id],Category:"tome",Id:id)))
                .OrderBy(c=>c.Level).ThenBy(c=>c.Category,StringComparer.Ordinal).ThenBy(c=>c.Id,StringComparer.Ordinal).ToArray();
            if(candidates.Length>0)
            {
                var choice=candidates[0];if(choice.Category=="weapon")mWeaponLevels[choice.Id]++;else {mTomeLevels[choice.Id]++;if(choice.Id=="vitality"){double fraction=mHealth/Math.Max(1,mMaxHealth);mMaxHealth=mBaseHealth*(1+.08*Tome("vitality"));mHealth=mMaxHealth*fraction;}}
                var item=mCatalog[choice.Category=="weapon"?"weapons":"tomes"]!.AsArray().FirstOrDefault(n=>S(n,"id")==choice.Id);
                mMessage="宝箱升级："+(item?["name"]?["zh_cn"]?.GetValue<string>()??"未知装备");
            }
            else {int gold=12+tier*8;if(mTrinkets.Contains("boss_bell"))gold=(int)(gold*1.2);mRunGold+=gold;mMessage="宝箱："+gold+" 金币";}
        }
        ++mSaveRevision;
    }
    private void Finish(string reason)
    {
        if(mMode=="result")return;var last=Object(mProfile,"lastRun");if(B(last,"rewardCommitted")){mMode="result";return;}
        RecordQuest("runs",1);
        Dictionary<string,double> Reward()=>RunReward.Compute(new(){SurvivalSeconds=mElapsed,Kills=mKills,EliteKills=mEliteKills,BossKills=mBossKills,Level=mLevel,Victory=reason=="victory",EndReason=reason,RevivesUsed=mRevivesUsed,BonusGold=mRunGold,
            QuestGold=mQuests.RunQuestGold,GreedTomeBonus=.08*Tome("greed")+.10*Tome("curse"),HoneybunBonus=Math.Max(0,N(mCharacterStats,"gold_gain_multiplier",1)-1),GlobalGreedBonus=.05*Power("meta_greed"),DifficultyReward=N(mDifficulty,"gold",1),ChallengeRewards=mCatalog["challenges"]!.AsArray().Where(c=>Strings(mProfile["selectedChallenges"]).Contains(S(c,"id"))).Select(c=>N(c,"gold",1)).ToArray(),WeaponSlotLimit=(int)N(last,"weaponSlotLimit",3)});
        var reward=Reward();RecordQuest("gold_earned",reward["earnedGold"]);reward=Reward();
        double before=N(mProfile,"walletGold"),after=Math.Min(RunReward.MaxWalletGold,before+reward["earnedGold"]);
        mProfile["walletGold"]=after;last["walletBefore"]=before;last["walletAfter"]=after;last["creditedGold"]=after-before;
        last["reward"]=JsonSerializer.SerializeToNode(reward);last["rewardCommitted"]=true;last["endReason"]=reason;
        var career=Object(mProfile,"career");
        void Count(string key,double amount)=>career[key]=Math.Min(RunReward.MaxRunCounter,N(career,key)+amount);
        Count("runs",1);Count("totalKills",mKills);Count("totalGoldEarned",reward["earnedGold"]);Count("totalElites",mEliteKills);Count("totalBossKills",mBossKills);
        var mastery=Object(mProfile,"characterMasteryXp");mastery[mCharacter]=Math.Min(RunReward.MaxRunCounter,N(mastery,mCharacter)+(int)mElapsed+mKills/5+mBossKills*100+(reason=="victory"?300:0));
        if(reason=="victory")
        {
            Count("wins",1);string difficulty=S(mDifficulty,"id");Object(mProfile,"difficultyClears")[difficulty]=true;
            foreach(string challenge in Strings(mProfile["selectedChallenges"]))Object(mProfile,"challengeClears")[challenge]=true;
            string[] ranks=["adventure","fierce","nightmare"];if(System.Array.IndexOf(ranks,difficulty)>System.Array.IndexOf(ranks,S(career,"highestDifficulty")))career["highestDifficulty"]=difficulty;
            RecordQuest("difficulty_clear",1);
        }
        career["bestLevel"]=Math.Max(N(career,"bestLevel"),mLevel);career["bestSurvivalSeconds"]=Math.Max(N(career,"bestSurvivalSeconds"),mElapsed);
        mMode="result";mMessage=(reason=="victory"?"冒险胜利":"本次冒险结束")+" · 获得 "+reward["earnedGold"]+" 金币";++mSaveRevision;
    }
    private void Buy(string id)
    {
        foreach(string category in new[]{"characters","weapons","tomes","trinkets"})
        {
            var item=mCatalog[category]!.AsArray().FirstOrDefault(e=>S(e,"id")==id);if(item is null)continue;
            var owned=Array(Object(mProfile,"owned"),category);if(Contains(owned,id)){mMessage="已拥有";return;}
            if(!Contains(Array(Object(mProfile,"eligible"),category),id)){mMessage="请先完成解锁任务";return;}
            var product=mCatalog["products"]!.AsArray().FirstOrDefault(p=>S(p,"category")==category&&S(p,"contentId")==id)??throw new InvalidOperationException("Product price missing");
            double price=N(product,"price"),gold=N(mProfile,"walletGold");if(gold<price){mMessage="金币不足";return;}
            mProfile["walletGold"]=gold-price;owned.Add(id);
            var eligible=Array(Object(mProfile,"eligible"),category);var entry=eligible.FirstOrDefault(n=>n!.GetValue<string>()==id);if(entry!=null)eligible.Remove(entry);
            ++mSaveRevision;mMessage="购买成功";return;
        }
        throw new ArgumentException("Unknown product");
    }
    private void BuyPower(string id)
    {
        var d=mCatalog["metaPowerUps"]!.AsArray().FirstOrDefault(e=>S(e,"id")==id)??throw new ArgumentException("Unknown power");
        var levels=Object(mProfile,"powerUps");int level=(int)N(levels,id);var prices=d["prices"]!.AsArray();if(level>=prices.Count){mMessage="已达最高等级";return;}
        var prerequisites=d["levelPrerequisites"]!.AsArray();if(prerequisites.Count>level&&!B(Object(mProfile,"difficultyClears"),prerequisites[level]!.GetValue<string>())){mMessage="尚未通关所需难度";return;}
        double price=prices[level]!.GetValue<double>(),gold=N(mProfile,"walletGold");if(gold<price){mMessage="金币不足";return;}
        levels[id]=level+1;Object(mProfile,"powerUpsEnabled")[id]=true;mProfile["walletGold"]=gold-price;++mSaveRevision;mMessage="强化成功";
    }
    private void RefundPower(string id)
    {
        var definition=mCatalog["metaPowerUps"]!.AsArray().FirstOrDefault(e=>S(e,"id")==id)??throw new ArgumentException("Unknown power");
        var levels=Object(mProfile,"powerUps");int level=(int)N(levels,id);if(level==0)return;
        double refund=definition["prices"]!.AsArray().Take(level).Sum(p=>p!.GetValue<double>());
        if(N(mProfile,"walletGold")+refund>2_000_000_000){mMessage="星币已达上限";return;}
        mProfile["walletGold"]=N(mProfile,"walletGold")+refund;levels[id]=0;Object(mProfile,"powerUpsEnabled")[id]=false;
        if(id=="meta_weapon_slots")mProfile["selectedWeaponSlotLimit"]=3;
        ++mSaveRevision;mMessage="已退还强化花费";
    }
    private void ToggleQuestTracking(string id)
    {
        if(!mCatalog["quests"]!.AsArray().Any(q=>S(q,"id")==id))throw new ArgumentException("Unknown quest");
        var tracked=Array(mProfile,"trackedQuests");var entry=tracked.FirstOrDefault(n=>n!.GetValue<string>()==id);
        if(entry!=null)tracked.Remove(entry);
        else if(tracked.Count<3)tracked.Add(id);
        else {mMessage="最多追踪三个任务";return;}
        ++mSaveRevision;
    }
    private void RefundAllPower()
    {
        var definitions=mCatalog["metaPowerUps"]!.AsArray();var levels=Object(mProfile,"powerUps");
        double refund=definitions.Sum(d=>d!["prices"]!.AsArray().Take((int)N(levels,S(d,"id"))).Sum(p=>p!.GetValue<double>()));
        if(refund==0)return;
        if(N(mProfile,"walletGold")+refund>2_000_000_000){mMessage="星币已达上限";return;}
        mProfile["walletGold"]=N(mProfile,"walletGold")+refund;
        foreach(var d in definitions){string id=S(d,"id");levels[id]=0;Object(mProfile,"powerUpsEnabled")[id]=false;}
        mProfile["selectedWeaponSlotLimit"]=3;++mSaveRevision;mMessage="已退还全部强化花费";
    }
    private void RecordQuest(string metric,double amount,bool bSet=false)
    {
        mQuests.Record(metric,amount,new(){["difficulty"]=S(mDifficulty,"id",S(mProfile,"selectedDifficulty","adventure"))},bSet);
        if(mQuests.Flush()){mMessage="任务完成";++mSaveRevision;}
    }
}
