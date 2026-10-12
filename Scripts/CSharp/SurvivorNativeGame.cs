using System.Globalization;
using System.Numerics;
using System.Text.Json.Nodes;
using HEngine;
using GameScripts.Survivor;

namespace GameScripts;

// Native presentation adapter. The session is the same source compiled for Wasm.
[ScriptType("survivor.game")]
[ScriptDependency("Assets/UI/SurvivorHUD.hui")]
[ScriptDependency("Assets/UI/Cursors/starbloom_cursor.png")]
// The host cooker discovers dependencies using the Windows assembly, including
// resources consumed only by the Android presentation adapter.
[ScriptDependency("Assets/UI/SharedPause.hui")]
[ScriptDependency("Assets/Prefabs/SurvivorMenuPreview.hprefab")]
[ScriptDependency("Assets/Prefabs/SurvivorCometCore.hprefab")]
[ScriptDependency("Assets/Prefabs/ExperienceGem.hprefab")]
[ScriptDependency("Assets/Prefabs/SurvivorBossChest.hprefab")]
public sealed partial class SurvivorNativeGame : ScriptBehaviour
{
    private WebGameSession? mSession;
    private JsonObject mCatalog = new(), mSnapshot = new();
    private readonly Dictionary<string, JsonObject> mModels = new();
    private readonly Dictionary<int, Entity> mEnemies = new();
    private readonly List<Entity> mProjectileVisuals = new(), mGemVisuals = new(), mChestVisuals = new();
    private Entity mPlayer, mCamera;
    private string mDocument = "", mMode = "", mCharacter = "";
#if HE_ANDROID
    private string mPauseDocument = "";
#endif
    private string mMenuPage = "play";
    private string mPreviewCharacter = "starpaw";
    private float mPreviewYaw, mPreviewZoom = 1;
    private bool bPreview;
    private bool bBanishSelection;

    private ulong mUiSequence;
    private bool bJump, bPause;
    private bool bLooking;
    private bool bFollowing;
    private double mPointerX, mPointerY;
    private double mUiTimer;
    private long mSaveRevision = -1;
    private ulong mMusic;
    private string mMusicCue = "";
    private double mPreviousHealth=100;
    private static double Number(JsonNode node, string key) => node[key]?.GetValue<double>() ?? 0;
    private static string Text(JsonNode node, string key) => node[key]?.GetValue<string>() ?? "";
    public override void Initialize()
    {
        using var stream = typeof(SurvivorNativeGame).Assembly.GetManifestResourceStream("Survivor.catalog.json")
            ?? throw new InvalidOperationException("The gameplay catalog was not built.");
        using var reader = new StreamReader(stream);
        string catalog = reader.ReadToEnd();
        mCatalog = JsonNode.Parse(catalog)!.AsObject();
        foreach (string group in new[] { "characters", "enemies", "bosses" })
            foreach (var entry in mCatalog[group]!.AsArray()) mModels[Text(entry!, "id")] = entry!.AsObject();
        // Keep reference Python saves intact during migration acceptance.
        mSession = new(catalog, Engine.Api.ReadSave("survivor-csharp-v4"));
#if !HE_ANDROID
        mSession.EnablePresentationEvents();
        // The original desktop camera starts behind the player's +Z facing direction.
        mSession.ConfigureCamera(20 * Math.PI / 180, .0024, -5 * Math.PI / 180, 75 * Math.PI / 180, Math.PI);
#endif
        mCamera = SceneServices.Camera;
        var originalPlayer = SceneServices.FindTag("Player");
        if (originalPlayer.IsValid) { var state = originalPlayer.State; state.Position.Y = -1000; originalPlayer.Apply(state); }
        mDocument = SceneServices.LoadUi("Assets/UI/SurvivorHUD.hui");
        SceneServices.Call<bool>("ui.cursor", new { document = mDocument, visible = true, path = "Assets/UI/Cursors/starbloom_cursor.png" });
        InitializeSettings();
#if HE_ANDROID
        mPauseDocument = SceneServices.LoadUi("Assets/UI/SharedPause.hui");
        SceneServices.SetUiVisible(mPauseDocument, false);
        SceneServices.SetUiVisible(mDocument, true);
#endif
        SetSnapshot(mSession.Snapshot());
        Engine.Log("[C# Survivor] Native session initialized; Python gameplay is not used by this script.");
    }
    private void SetSnapshot(string json) => mSnapshot = JsonNode.Parse(json)!.AsObject();
    private void Command(string name, string value = "")
    {
        try { SetSnapshot(mSession!.Command(name, value)); }
        catch (Exception error) when (error is ArgumentException or InvalidOperationException) { Engine.Log(error.Message); }
        mUiTimer = 0;
    }
    public override void Update(double seconds)
    {
        string events = Engine.Api.ReadEvent("ui.event", mUiSequence, out mUiSequence);
        if (events.Length > 0)
        {
            var e = JsonNode.Parse(events)!;
            if (Text(e, "type") == "click")
            {
                string source = Text(e, "source");
                if (source is "shared_resume" or "shared_abandon" or "shared_restart") Command(source);
                else HandleClick(source);
            }
        }
        var keys = SceneServices.Call<JsonObject>("input.buttons", new { });
        bool jump = keys["jump"]!.GetValue<bool>(), pause = keys["pause"]!.GetValue<bool>();
        string mode = Text(mSnapshot, "mode");
        bool looking = mode == "playing" && (keys["captured"]!.GetValue<bool>() || keys["right"]!.GetValue<bool>());
        double pointerX=Number(keys,"pointerX"),pointerY=Number(keys,"pointerY");
        if(looking && bLooking)Command("look",$"[{(pointerX-mPointerX).ToString(CultureInfo.InvariantCulture)},{(pointerY-mPointerY).ToString(CultureInfo.InvariantCulture)}]");
        bLooking=looking;mPointerX=pointerX;mPointerY=pointerY;
        if (jump && !bJump && mode == "playing") Command("jump");
        if (pause && !bPause)
        {
            if (bSettingsOpen) { bSettingsOpen = false; UpdateUi(); }
            else if (mode is "playing" or "paused") Command(mode == "playing" ? "pause" : "resume");
        }
        bJump = jump; bPause = pause;
        var input = Engine.Input;
        SetSnapshot(mSession!.Step(seconds, input.Movement.X, -input.Movement.Y));
        Present();
        mUiTimer -= seconds;
        if (mUiTimer <= 0 || mMode != Text(mSnapshot, "mode")) { UpdateUi(); mUiTimer = .1; }
        long revision = mSnapshot["saveRevision"]!.GetValue<long>();
        if (revision != mSaveRevision) { Engine.Api.WriteSave("survivor-csharp-v4", mSession.Save()); mSaveRevision = revision; }
    }
    private void HandleClick(string id)
    {
        PlayAudio("ui_click");
        string mode = Text(mSnapshot, "mode");
        if (HandleSettingsClick(id, mode)) return;
        if (mode == "menu" && HandleHubClick(id)) { UpdateUi(); return; }
        if (mode == "menu")
        {
            if(id=="character_rotate_left"){mPreviewYaw-=.3f;return;}
            if(id=="character_rotate_right"){mPreviewYaw+=.3f;return;}
            if(id=="character_zoom_in"){mPreviewZoom=Math.Min(1.32f,mPreviewZoom+.08f);return;}
            if(id=="character_zoom_out"){mPreviewZoom=Math.Max(.72f,mPreviewZoom-.08f);return;}
            if(id=="character_preview_reset"){mPreviewYaw=0;mPreviewZoom=1;return;}
            if(id is "character_preview_idle" or "character_preview_dance")
            {SceneServices.Call<bool>("animation.set",new{entity=mPlayer.Handle,clip=Text(mModels[mPreviewCharacter],id.EndsWith("dance")?"dance":"idle")});return;}
            if (id.StartsWith("hub_nav_", StringComparison.Ordinal)) { mMenuPage = id[8..]; UpdateUi(); return; }
            if (id == "play_change_character_button") { mMenuPage = "characters"; UpdateUi(); return; }
            if (id.StartsWith("character_",StringComparison.Ordinal)&&mCatalog["characters"]!.AsArray().Any(c=>Text(c!,"id")==id[10..])) { mPreviewCharacter=id[10..];UpdateUi();return; }
            if(id=="character_training_button"){Command("train",mPreviewCharacter);return;}
            if(id=="character_training_toggle_button"){Command("toggleTraining",mPreviewCharacter);return;}
            if(id=="character_purchase_button"){Command("buy",mPreviewCharacter);return;}
            if(id=="character_use_button"){Command("selectCharacter",mPreviewCharacter);mMenuPage="play";UpdateUi();return;}
            if (id.StartsWith("difficulty_", StringComparison.Ordinal)) { Command("difficulty", id[11..]); return; }
            if (id.StartsWith("weapon_limit_", StringComparison.Ordinal)) { Command("weaponSlots", id[13..]); return; }
            if (id.StartsWith("challenge_slot_", StringComparison.Ordinal) && int.TryParse(id[15..], out int challenge) && challenge < mCatalog["challenges"]!.AsArray().Count) { Command("challenge", Text(mCatalog["challenges"]![challenge]!, "id")); return; }
            if (id == "play_seed_button") { Command("seed", Random.Shared.NextInt64(1,int.MaxValue).ToString(CultureInfo.InvariantCulture)); return; }
        }
        if (id == "start_button" && mode == "menu") Command("start");
        else if (id == "resume_button" && mode == "paused") Command("resume");
        else if (id == "pause_home_button" && mode == "paused") Command("abandon");
        else if (id == "pause_restart_button" && mode == "paused") { Command("abandon"); Command("home"); Command("start"); }
        else if (id == "restart_button" && mode == "result") { Command("home"); Command("start"); }
        else if (id == "result_adjust_build_button" && mode == "result") { Command("home");mMenuPage="armory";UpdateUi(); }
        else if (id == "game_over_home_button" && mode == "result") Command("home");
        else if (id == "upgrade_reroll_button" && mode == "upgrade") Command("reroll");
        else if (id == "upgrade_skip_button" && mode == "upgrade") Command("skip");
        else if (id == "upgrade_banish_button" && mode == "upgrade" && Number(mSnapshot,"banishes")>0) { bBanishSelection=!bBanishSelection;mUiTimer=0; }
        else if (id.StartsWith("upgrade_", StringComparison.Ordinal) && mode == "upgrade" && int.TryParse(id[8..], out int index))
        {
            var choices = mSnapshot["choices"]!.AsArray();
            if (index > 0 && index <= choices.Count) { Command(bBanishSelection?"banish":"upgrade", Text(choices[index - 1]!, "id"));bBanishSelection=false; }
        }
    }
    private Entity Spawn(string id)
    {
        var model = mModels[id];
        string prefab = Text(model, "prefab");
        var entity = SceneServices.Instantiate(prefab.Length > 0 ? prefab : "Assets/Prefabs/SurvivorMenuPreview.hprefab");
        SceneServices.Call<bool>("scene.visual", new { entity = entity.Handle, mesh = Text(model, "mesh") });
        if (Text(model, "controller").Length > 0)
            SceneServices.Call<bool>("animation.set", new { entity = entity.Handle, controller = Text(model, "controller") });
        var state = entity.State;
        if (model["scale"] != null) state.Scale = new Vector3((float)Number(model, "scale"));
        if (model["preview"] is JsonNode preview) state.Rotation.X = (float)Number(preview,"upright");
        entity.Apply(state);
        return entity;
    }
    private static void Move(Entity entity, JsonNode state)
    {
        var transform = entity.State;
        transform.Position = new((float)Number(state, "x"), (float)Number(state, "y"), (float)Number(state, "z"));
        transform.Rotation.Y = (float)Number(state, "yaw");
        entity.Apply(transform);
    }
    private void Present()
    {
        bool preview=Text(mSnapshot,"mode")=="menu"&&mMenuPage=="characters";
        string character = preview?mPreviewCharacter:Text(mSnapshot, "character");
        if (mCharacter != character || bPreview != preview)
        {
            if (mPlayer.IsValid) mPlayer.Destroy();
            mPlayer = Spawn(character); mCharacter = character;
            bPreview=preview;
        }
        if(preview)
        {
            var state=mPlayer.State;state.Position=new Vector3(0,1000,0);
            state.Rotation.Y=mPreviewYaw;state.Scale=new Vector3((float)Number(mModels[character],"scale")*mPreviewZoom);
            mPlayer.Apply(state);
        }
        else Move(mPlayer, mSnapshot);
        SceneServices.SetAnimationFloat(mPlayer, "Speed", mSnapshot["moving"]!.GetValue<bool>() ? 1 : 0);
        var live = new HashSet<int>();
        foreach (var enemy in mSnapshot["enemies"]!.AsArray())
        {
            int id = enemy!["id"]!.GetValue<int>(); live.Add(id);
            if (!mEnemies.TryGetValue(id, out var entity)) mEnemies[id] = entity = Spawn(Text(enemy, "kind"));
            Move(entity, enemy);
        }
        foreach (int id in mEnemies.Keys.Where(id => !live.Contains(id)).ToArray()) { mEnemies[id].Destroy(); mEnemies.Remove(id); }
#if HE_ANDROID
        PresentPool(mProjectileVisuals, mSnapshot["projectiles"]!.AsArray(), "Assets/Prefabs/SurvivorCometCore.hprefab", .3f, .7f);
#else
        PresentNativeEffects();
#endif
        PresentPool(mGemVisuals, mSnapshot["pickups"]!.AsArray().Where(p => p!["chest"]!.GetValue<bool>() == false), "Assets/Prefabs/ExperienceGem.hprefab", .5f, .35f);
        PresentPool(mChestVisuals, mSnapshot["pickups"]!.AsArray().Where(p => p!["chest"]!.GetValue<bool>()), "Assets/Prefabs/SurvivorBossChest.hprefab", 1, .2f);
        if (mCamera.IsValid)
        {
            var camera = mCamera.State;
            float yaw=(float)Number(mSnapshot,"cameraYaw"),elevation=(float)Number(mSnapshot,"cameraElevation"),distance=MathF.Sqrt(14*14+17*17),horizontal=distance*MathF.Cos(elevation);
#if !HE_ANDROID
            distance = 12.5f; horizontal = distance * MathF.Cos(elevation);
#endif
            camera.Position = mPlayer.State.Position + new Vector3(MathF.Sin(yaw)*horizontal,MathF.Sin(elevation)*distance,MathF.Cos(yaw)*horizontal);
            camera.Rotation = new Vector3(-elevation, yaw, 0);
            if(preview){camera.Position=new Vector3(0,1001.8f,4.8f);camera.Rotation=new Vector3(-MathF.Atan2(1.15f,4.8f),0,0);}
#if !HE_ANDROID
            bool following = Text(mSnapshot, "mode") != "menu";
            SceneServices.Call<bool>("camera.follow", new { entity = mPlayer.Handle, enabled = following,
                yaw = yaw + MathF.PI, pitch = -elevation, minPitch = -75, maxPitch = 5,
                distance = 12.5f, targetHeight = 1.5f, socketHeight = .25f, lagSpeed = 10, minDistance = .8f,
                reset = following && !bFollowing });
            bFollowing = following;
            if (!following) mCamera.Apply(camera);
#else
            mCamera.Apply(camera);
#endif
        }
    }
    private static void PresentPool(List<Entity> pool, IEnumerable<JsonNode?> items, string prefab, float scale, float height)
    {
        int index = 0;
        foreach (var item in items.Take(HEngine.Platform.BuildFeatures.PresentationParticleLimit))
        {
            if (index == pool.Count) pool.Add(SceneServices.Instantiate(prefab));
            var entity = pool[index++]; var state = entity.State;
            state.Position = new((float)Number(item!, "x"), (float)Number(item!, "y") + height, (float)Number(item!, "z"));
            state.Scale = new Vector3(scale); entity.Apply(state);
        }
        for (int i = index; i < pool.Count; i++) { var state = pool[i].State; state.Scale = Vector3.Zero; pool[i].Apply(state); }
    }
    private void UpdateUi()
    {
        string nextMode=Text(mSnapshot,"mode"),cue=nextMode=="menu"?"music_menu":"music_gameplay";
        if(mMusicCue!=cue){if(mMusic!=0)SceneServices.StopAudio(mMusic);mMusic=PlayAudio(cue,true);mMusicCue=cue;}
        if(nextMode=="upgrade"&&mMode!="upgrade")PlayAudio("level_up");
        double health=Number(mSnapshot,"health");if(health<mPreviousHealth)PlayAudio("player_hit");mPreviousHealth=health;
#if HE_ANDROID
        if ((mMode == "paused") != (nextMode == "paused"))
        {
            SceneServices.SetUiVisible(mPauseDocument, nextMode == "paused");
            if (nextMode != "paused") SceneServices.SetUiVisible(mDocument, true);
        }
#endif
        if (nextMode != mMode) bLooking = false;
        if (nextMode != "paused") bSettingsOpen = false;
        SceneServices.Call<bool>("ui.cursor", new { document = mDocument, visible = nextMode != "playing" });
        mMode = Text(mSnapshot, "mode");
#if HE_ANDROID
        SceneServices.Call<bool>("input.touchControls", new { enabled = mMode == "playing" });
#endif
        SceneServices.SetClass(mDocument,"hud","character_preview_mode",mMode=="menu"&&mMenuPage=="characters");
        SceneServices.SetStyle(mDocument,"character_preview_loading","display","none");
        SceneServices.SetStyle(mDocument, "settings_panel", "display", bSettingsOpen ? "flex" : "none");
        foreach (var pair in new[] { ("start_panel", "menu"), ("pause_panel", "paused"), ("upgrade_panel", "upgrade"), ("game_over_panel", "result") })
            SceneServices.SetStyle(mDocument, pair.Item1, "display", !bSettingsOpen && mMode == pair.Item2 ? "flex" : "none");
#if HE_ANDROID
        SceneServices.SetStyle(mDocument, "pause_panel", "display", "none");
#endif
        void Set(string id, string value) => SceneServices.SetText(mDocument, id, value);
        SceneServices.SetStyle(mDocument, "gameplay_hud", "display", mMode == "menu" ? "none" : "block");
        SceneServices.SetStyle(mDocument, "title_backdrop", "display", mMode == "menu" ? "block" : "none");
        SceneServices.SetStyle(mDocument, "loading_backdrop", "display", "none");
        Set("hp_text", $"{Number(mSnapshot,"health"):0} / {Number(mSnapshot,"maxHealth"):0}");
        Set("timer", TimeSpan.FromSeconds(Number(mSnapshot, "elapsed")).ToString(@"mm\:ss", CultureInfo.InvariantCulture));
        Set("kills", $"击杀 {Number(mSnapshot,"kills"):0}");
        Set("level", $"等级 {Number(mSnapshot,"level"):0}");
        Set("enemy_count", $"附近怪物 {mSnapshot["enemies"]!.AsArray().Count}");
        Set("shard_count", $"星光碎片 {mSnapshot["pickups"]!.AsArray().Count}");
        var regions=mSnapshot["regions"]!.AsArray();
        Set("region_completed_count",regions.Count(r=>Text(r!,"state")=="ACTIVATED")+" / 4");
        var closest=regions.OrderBy(r=>Math.Pow(Number(r!,"x")-Number(mSnapshot,"x"),2)+Math.Pow(Number(r!,"z")-Number(mSnapshot,"z"),2)).First();
        foreach(var region in regions)
        {
            string id=Text(region!,"id"),state=Text(region!,"state"),label=id switch{"star"=>"星之区域","thunder"=>"雷之区域","water"=>"水之区域",_=>"风之区域"};
            string status=state switch{"ACTIVATED"=>"已净化","ASSAULT"=>"守住区域","OUTSIDE_GRACE"=>"立即返回","COOLDOWN"=>"冷却中",_=>"待净化"};
            double distance=Math.Sqrt(Math.Pow(Number(region!,"x")-Number(mSnapshot,"x"),2)+Math.Pow(Number(region!,"z")-Number(mSnapshot,"z"),2));
            Set("region_seal_"+id+"_status",status);Set("region_seal_"+id+"_direction",distance.ToString("0",CultureInfo.InvariantCulture)+" m");
            if(ReferenceEquals(region,closest)){Set("region_current_name",label);Set("region_status_instruction",status);Set("objective_navigation",label+" · "+distance.ToString("0",CultureInfo.InvariantCulture)+" m");Set("region_countdown",Math.Max(0,60-Number(region!,"assault")).ToString("0.0",CultureInfo.InvariantCulture));}
        }
        Set("banner",Text(mSnapshot,"message"));
        SceneServices.SetStyle(mDocument, "hp_fill", "width", (100 * Number(mSnapshot,"health") / Math.Max(1, Number(mSnapshot,"maxHealth"))).ToString(CultureInfo.InvariantCulture) + "%");
        SceneServices.SetStyle(mDocument, "xp_fill", "width", (100 * Number(mSnapshot,"xp") / Math.Max(1, Number(mSnapshot,"xpRequired"))).ToString(CultureInfo.InvariantCulture) + "%");
        var weapons = mSnapshot["weapons"]!.AsObject().Where(p => p.Value!.GetValue<int>() > 0).ToArray();
        for (int i = 0; i < 6; i++)
        {
            string slot = (i + 1).ToString(); bool equipped = i < weapons.Length;
            bool unlocked = i < Number(mSnapshot["profile"]!, "selectedWeaponSlotLimit");
            SceneServices.SetClass(mDocument, "weapon_slot_" + slot, "equipped", equipped);
            SceneServices.SetClass(mDocument, "weapon_slot_" + slot, "empty", !equipped && unlocked);
            SceneServices.SetClass(mDocument, "weapon_slot_" + slot, "locked", !equipped && !unlocked);
            Set("weapon_name_" + slot, equipped ? ItemName(weapons[i].Key) : "");
            Set("weapon_value_" + slot, equipped ? "Lv." + weapons[i].Value : "");
            if (equipped) SceneServices.SetAttribute(mDocument, "weapon_icon_" + slot, "src", Text(Item(weapons[i].Key)!, "icon"));
        }
        var tomes=mSnapshot["tomes"]!.AsObject().ToArray();
        for(int i=0;i<6;i++)
        {
            string slot=(i+1).ToString();bool equipped=i<tomes.Length;
            SceneServices.SetClass(mDocument,"tome_slot_"+slot,"empty",!equipped);
            Set("tome_value_"+slot,equipped?"Lv."+tomes[i].Value:"");
            if(equipped)SceneServices.SetAttribute(mDocument,"tome_icon_"+slot,"src",Text(Item(tomes[i].Key)!,"icon"));
        }
        Set("xp_label", $"经验 {Number(mSnapshot,"xp"):0} / {Number(mSnapshot,"xpRequired"):0}");
        Set("hub_wallet_value", $"{Number(mSnapshot["profile"]!,"walletGold"):0}");
        Set("play_character_name", mModels[mCharacter]["name"]?["zh_cn"]?.GetValue<string>() ?? mCharacter);
        Set("game_over_title", Text(mSnapshot, "message"));
        Set("game_over_subtitle", "奖励已保存");
        if(mMode=="result")UpdateResult();
        SceneServices.SetStyle(mDocument, "result_commit_status", "display", "none");
        if (mMode == "menu") UpdateMenu();
        if (mMode == "upgrade")
        {
            Set("upgrade_reroll_label","重抽 · "+TextNumber(mSnapshot,"rerolls"));Set("upgrade_skip_label","跳过 · "+TextNumber(mSnapshot,"skips"));
            Set("upgrade_banish_label",bBanishSelection?"点击卡牌放逐":"放逐所选 · "+TextNumber(mSnapshot,"banishes"));
            int index = 0;
            foreach (var choice in mSnapshot["choices"]!.AsArray())
            {
                string id = Text(choice!, "id"), slot = (++index).ToString();
                Set("upgrade_kind_"+slot,Text(choice!,"category")=="weapons"?"主动武器":"被动能力");
                Set("upgrade_rank_"+slot,"本局成长");
                Set("upgrade_name_" + slot, ItemName(id)); Set("upgrade_title_" + slot, ItemName(id));
                Set("upgrade_stat_" + slot, "等级 " + TextNumber(choice!, "nextLevel"));
                if (Item(id) is JsonNode item)
                {
                    Set("upgrade_desc_"+slot,item["description"]?["zh_cn"]?.GetValue<string>()??"");
                    Set("upgrade_stat_"+slot,item["statText"]?["zh_cn"]?.GetValue<string>()??"等级 "+TextNumber(choice!,"nextLevel"));
                    SceneServices.SetAttribute(mDocument, "upgrade_icon_image_" + slot, "src", Text(item, "icon"));
                }
            }
            for(int i=1;i<=3;i++)SceneServices.SetStyle(mDocument,"upgrade_"+i,"display",i<=index?"flex":"none");
        }
    }
    private JsonNode? Item(string id) => new[] { "characters", "weapons", "tomes", "trinkets", "evolutions", "power_ups", "challenges" }.SelectMany(k => mCatalog[k]!.AsArray()).FirstOrDefault(n => Text(n!, "id") == id);
    private void UpdateResult()
    {
        void Set(string id,string value)=>SceneServices.SetText(mDocument,id,value);
        var last=mSnapshot["profile"]!["lastRun"]!;var reward=last["reward"]!;
        Set("result_end_reason",Text(last,"endReason") switch{"victory"=>"结束原因：胜利","death"=>"结束原因：失败",_=>"结束原因：主动离开"});
        double elapsed=Number(mSnapshot,"elapsed");Set("final_time_value",$"{(int)elapsed/60:00}:{(int)elapsed%60:00}");
        foreach(var pair in new[]{("kills","kills"),("level","level"),("score","score")})Set("final_"+pair.Item1+"_value",TextNumber(mSnapshot,pair.Item2));
        Set("result_gold_total",TextNumber(reward,"earnedGold"));
        Set("result_gold_time","+"+TextNumber(reward,"timeGold"));Set("result_gold_kills","+"+TextNumber(reward,"killGold"));
        Set("result_gold_elite_boss","+"+(Number(reward,"eliteGold")+Number(reward,"bossGold")).ToString("0",CultureInfo.InvariantCulture));
        Set("result_gold_clear_difficulty","×"+Number(reward,"difficultyFactor").ToString("0.##",CultureInfo.InvariantCulture));
        Set("result_weapon_slot_limit",TextNumber(last,"weaponSlotLimit"));Set("result_weapon_slot_bonus","+"+TextNumber(reward,"weaponSlotBonusGold"));Set("result_gold_quests","+"+TextNumber(reward,"questGold"));
        Set("final_elites_value",(Number(reward,"eliteGold")/4).ToString("0",CultureInfo.InvariantCulture));Set("final_bosses_value",(Number(reward,"bossGold")/15).ToString("0",CultureInfo.InvariantCulture));
        var completed=mSnapshot["regions"]!.AsArray().Where(r=>Text(r!,"state")=="ACTIVATED").Select(r=>Text(r!,"id"));Set("result_region_order",string.Join(" → ",completed));
        var telemetry=mSnapshot["telemetry"]!;
        foreach(var pair in new[]{("damage_taken","damageTaken"),("damage_prevented","damagePrevented"),("healing","healing"),("distance_moved","distanceMoved")})Set("result_"+pair.Item1,Number(telemetry,pair.Item2).ToString("0.0",CultureInfo.InvariantCulture));
        Set("result_domain_summary",string.Join(" / ",mSnapshot["domains"]!.AsObject().Select(p=>p.Key.Replace("domain_",""))));
        foreach(string id in new[]{"result_region_attempts","result_region_exits","result_boss_ttk"})Set(id,"—");
        var equipped=mSnapshot["weapons"]!.AsObject().ToArray();
        for(int i=0;i<6;i++)
        {
            string row="result_weapon_slot_"+i;SceneServices.SetStyle(mDocument,row,"display",i<equipped.Length?"flex":"none");if(i>=equipped.Length)continue;
            Set(row+"_name",ItemName(equipped[i].Key));Set(row+"_level",equipped[i].Value!.ToString());
            var stats=telemetry["weapons"]?[equipped[i].Key];
            foreach(string metric in new[]{"damage","hits","crits","kills"})Set(row+"_"+metric,stats==null?"0":Number(stats,metric).ToString("0",CultureInfo.InvariantCulture));
            Set(row+"_dps",stats==null?"0":(Number(stats,"damage")/Math.Max(1,elapsed)).ToString("0.0",CultureInfo.InvariantCulture));
        }
    }
    private string ItemName(string id) => Item(id) is JsonNode item ? Local(item["name"]) : id;
    private static string TextNumber(JsonNode node, string key) => node[key]?.ToString() ?? "";
    private void UpdateMenu()
    {
        foreach (string page in new[]{"play","characters","armory","shop","quests","collection","settings"})
            SceneServices.SetStyle(mDocument,"hub_page_"+page,"display",mMenuPage==page?"flex":"none");
        SceneServices.SetText(mDocument,"play_seed_value",TextNumber(mSnapshot,"seed"));
        SceneServices.SetText(mDocument,"play_weapon_slots_summary","本局计划 "+TextNumber(mSnapshot["profile"]!,"selectedWeaponSlotLimit")+" 槽");
        SceneServices.SetAttribute(mDocument,"play_character_portrait","src",Text(mModels[mCharacter],"icon"));
        int ci=0;
        foreach (var c in mCatalog["challenges"]!.AsArray()) SceneServices.SetText(mDocument,"challenge_slot_"+(ci++)+"_name",ItemName(Text(c!,"id")));
        UpdateHubHeader();
        if (mMenuPage=="play" || mMenuPage=="settings") return;
        var profile=mSnapshot["profile"]!;
        if(mMenuPage=="characters")
        {
            SceneServices.SetText(mDocument,"character_roster_count",profile["owned"]!["characters"]!.AsArray().Count+" / "+mCatalog["characters"]!.AsArray().Count);
            foreach(var character in mCatalog["characters"]!.AsArray())
            {
                string id=Text(character!,"id"),prefix="character_"+id;
                bool owned=profile["owned"]!["characters"]!.AsArray().Any(n=>n!.GetValue<string>()==id);
                SceneServices.SetText(mDocument,prefix+"_name",ItemName(id));
                SceneServices.SetText(mDocument,prefix+"_passive",ItemName(Text(character!,"starterWeapon")));
                SceneServices.SetText(mDocument,prefix+"_unlock",owned?"已拥有":"完成解锁任务后购买");
                SceneServices.SetClass(mDocument,prefix,"locked_character",!owned);
                SceneServices.SetClass(mDocument,prefix,"selected_character",id==mPreviewCharacter);
            }
            bool previewOwned=profile["owned"]!["characters"]!.AsArray().Any(n=>n!.GetValue<string>()==mPreviewCharacter);
            SceneServices.SetText(mDocument,"character_detail_name",ItemName(mPreviewCharacter));
            SceneServices.SetText(mDocument,"character_detail_weapon",ItemName(Text(mModels[mPreviewCharacter],"starterWeapon")));
            SceneServices.SetText(mDocument,"character_detail_state",previewOwned?"已拥有":"完成解锁任务后可购买");
            SceneServices.SetText(mDocument,"character_detail_price",TextNumber(mModels[mPreviewCharacter],"price")+" 星币");
            SceneServices.SetStyle(mDocument,"character_purchase_button","display",previewOwned?"none":"flex");
            SceneServices.SetStyle(mDocument,"character_use_button","display",previewOwned?"flex":"none");
            int level=(int)Number(profile["characterTraining"]!,mPreviewCharacter);int[] costs=[100,200,350,550,800];
            SceneServices.SetText(mDocument,"character_training_level",level+" / 5");
            SceneServices.SetText(mDocument,"character_training_button_label",level<5?"训练 · "+costs[level]+" 星币":"训练已满级");
            SceneServices.SetText(mDocument,"character_training_toggle_button_label",profile["characterTrainingEnabled"]?[mPreviewCharacter]?.GetValue<bool>()==false?"训练已关闭":"训练已启用");
            return;
        }
        UpdateDesktopPages();
    }
    public override void Destroy()
    {
        ClearNativeEffects();
#if HE_ANDROID
        SceneServices.Call<bool>("input.touchControls", new { enabled = false });
#endif
        if(mMusic!=0)SceneServices.StopAudio(mMusic);
        if (mPreviousDisplay != null) SceneServices.Call<JsonObject>("settings.display", mPreviousDisplay);
        if (mSession != null) Engine.Api.WriteSave("survivor-csharp-v4", mSession.Save());
        SceneServices.ClearUi();
    }
    private ulong PlayAudio(string cue,bool loop=false) => mCatalog["audio"]?[cue] is JsonValue path ? SceneServices.PlayAudio(path.GetValue<string>(),loop,loop?.35f:.65f) : 0;
}
