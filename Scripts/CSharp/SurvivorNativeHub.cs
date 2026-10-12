using System.Globalization;
using System.Text.Json.Nodes;
using HEngine;

namespace GameScripts;

// Bind the original desktop document; never replace its authored layout with HTML.
public sealed partial class SurvivorNativeGame
{
    private string mArmoryTab = "weapons", mArmoryFilter = "all", mArmoryFocus = "";
    private string mQuestFilter = "all", mQuestFocus = "", mShopFocus = "", mCollectionTab = "enemies";
    private int mArmoryPage, mQuestPage;
    private readonly Dictionary<string, string> mHubSlots = new();
    private JsonNode Profile => mSnapshot["profile"]!;
    private static bool Has(JsonNode? values, string id) => values is JsonArray array && array.Any(n => n?.GetValue<string>() == id);
    private string Local(JsonNode? value) => value is JsonObject ? value[Text(mSettings,"Language")]?.GetValue<string>() ?? value["zh_cn"]?.GetValue<string>() ?? "" : value?.ToString() ?? "";
    private string HubText(string key, params (string Key, object Value)[] values)
    {
        string text = mCatalog["nativeHubText"]?[Text(mSettings,"Language")]?[key]?.GetValue<string>() ?? key;
        foreach (var pair in values) text = text.Replace("{" + pair.Key + "}", Convert.ToString(pair.Value, CultureInfo.InvariantCulture));
        return text;
    }
    private void UiText(string id, string text) => SceneServices.SetText(mDocument,id,text);
    private void UiShow(string id, bool show, string display = "flex") => SceneServices.SetStyle(mDocument,id,"display",show?display:"none");
    private void UiClass(string id, string name, bool enabled) => SceneServices.SetClass(mDocument,id,name,enabled);
    private void UiImage(string id, string path) { SceneServices.SetAttribute(mDocument,id,"src",path); UiShow(id,path.Length>0,"block"); }
    private string ContentState(string group, string id) => Has(Profile["owned"]?[group],id) ? "owned" : Has(Profile["eligible"]?[group],id) ? "eligible" : "locked";
    private bool SealingUnlocked => Has(Profile["completedQuests"],"quest_system_seal") || new[]{"weapons","tomes","trinkets"}.Any(g=>Profile["poolDisabled"]?[g]?.AsArray().Count>0);
    private void SelectGroup(string prefix, IEnumerable<string> options, string selected)
    { foreach (string option in options) UiClass(prefix+option,"selected_option",option==selected); }
    private void UpdateHubHeader()
    {
        UiText("hub_wallet_value",TextNumber(Profile,"walletGold"));
        string[] groups = ["characters","weapons","tomes","trinkets","evolutions"];
        double count=groups.Sum(g=>g=="evolutions"?Profile["discoveredEvolutions"]!.AsArray().Count:Profile["owned"]![g]!.AsArray().Count);
        UiText("hub_completion_value",$"{100*count/Math.Max(1,groups.Sum(g=>mCatalog[g]!.AsArray().Count)):0}%");
        UiText("hub_difficulty_value",HubText("difficulty_"+Text(Profile,"selectedDifficulty")));
        SelectGroup("hub_nav_",["play","characters","armory","shop","quests","collection","settings"],mMenuPage);
        var tracked=Profile["trackedQuests"]!.AsArray().Select(n=>n!.GetValue<string>()).ToArray();
        UiText("activity_tracked_count",tracked.Length+"/3");
        for(int i=0;i<3;i++)
        {
            var quest=i<tracked.Length?mCatalog["quests"]!.AsArray().FirstOrDefault(q=>Text(q!,"id")==tracked[i]):null;
            string slot="tracked_quest_slot_"+i;
            UiText(slot+"_name",quest==null?HubText("tracked_empty"):Local(quest["title"]));
            UiText(slot+"_progress",quest==null?"—":$"{QuestProgress(quest):0} / {Number(quest,"target"):0}");
            UiClass(slot,"empty",quest==null);
            if(quest!=null)mHubSlots[slot]=Text(quest,"id");else mHubSlots.Remove(slot);
        }
    }
    private bool HandleHubClick(string id)
    {
        if(id.StartsWith("armory_tab_")){mArmoryTab=id[11..];mArmoryPage=0;return true;}
        if(id.StartsWith("armory_filter_")){mArmoryFilter=id[14..];mArmoryPage=0;return true;}
        if(id.StartsWith("quest_filter_")){mQuestFilter=id[13..];mQuestPage=0;return true;}
        if(id.StartsWith("collection_tab_")){mCollectionTab=id[15..];return true;}
        if(mHubSlots.TryGetValue(id,out string? selected))
        {
            if(id.StartsWith("armory_slot_")) mArmoryFocus=selected;
            else if(id.StartsWith("powerup_node_")) mShopFocus=selected;
            else if(id.StartsWith("tracked_quest_slot_")){mMenuPage="quests";mQuestFilter="all";mQuestPage=mCatalog["quests"]!.AsArray().Select(q=>Text(q!,"id")).ToList().IndexOf(selected)/10;mQuestFocus=selected;}
            else if(id.StartsWith("quest_slot_")) mQuestFocus=selected;
            return true;
        }
        switch(id)
        {
            case "armory_page_previous":mArmoryPage=Math.Max(0,mArmoryPage-1);break;
            case "armory_page_next":++mArmoryPage;break;
            case "quest_page_previous":mQuestPage=Math.Max(0,mQuestPage-1);break;
            case "quest_page_next":++mQuestPage;break;
            case "armory_purchase_button":Command("buy",mArmoryFocus);break;
            case "armory_toggle_button":Command("togglePool",mArmoryFocus);break;
            case "armory_pool_toggle_all":Command("unsealPool",mArmoryTab);mArmoryFilter="all";break;
            case "shop_purchase_button":Command("power",mShopFocus);break;
            case "shop_enable_button":Command("togglePower",mShopFocus);break;
            case "shop_refund_button":Command("refundPower",mShopFocus);break;
            case "shop_refund_all_button":Command("refundAllPower");break;
            case "quest_track_button":Command("trackQuest",mQuestFocus);break;
            default:return false;
        }
        return true;
    }
    private void UpdateDesktopPages()
    {
        switch(mMenuPage)
        {
            case "armory":UpdateArmory();break;
            case "shop":UpdateShop();break;
            case "quests":UpdateQuests();break;
            case "collection":UpdateCollection();break;
        }
    }
    private void UpdateArmory()
    {
        bool evolution=mArmoryTab=="evolutions", sealing=SealingUnlocked;
        if(mArmoryFilter=="disabled"&&!sealing)mArmoryFilter="all";
        var disabled=Profile["poolDisabled"]?[mArmoryTab];
        var all=mCatalog[mArmoryTab]!.AsArray();
        var entries=all.Where(e=>evolution||mArmoryFilter=="all"||(mArmoryFilter=="disabled"?Has(disabled,Text(e!,"id")):ContentState(mArmoryTab,Text(e!,"id"))==mArmoryFilter&&(mArmoryFilter!="owned"||!Has(disabled,Text(e!,"id"))))).ToArray();
        int pages=Math.Max(1,(entries.Length+9)/10);mArmoryPage=Math.Clamp(mArmoryPage,0,pages-1);
        var visible=entries.Skip(mArmoryPage*10).Take(10).ToArray();
        if(!visible.Any(e=>Text(e!,"id")==mArmoryFocus))mArmoryFocus=visible.Length>0?Text(visible[0]!,"id"):"";
        UiShow("armory_empty_state",visible.Length==0);UiText("armory_empty_state_label",HubText("empty_content"));
        for(int i=0;i<10;i++)
        {
            string slot="armory_slot_"+i;mHubSlots.Remove(slot);UiShow(slot,i<visible.Length);if(i>=visible.Length)continue;
            var item=visible[i]!;string id=Text(item,"id");mHubSlots[slot]=id;
            string state=evolution?(Has(Profile["discoveredEvolutions"],id)?"owned":"hidden"):ContentState(mArmoryTab,id);
            if(Has(disabled,id))state="sealed";
            UiImage(slot+"_icon",state=="hidden"?"":Text(item,"icon"));UiText(slot+"_name",state=="hidden"?"???":Local(item["name"]));
            SceneServices.SetStyle(mDocument,slot+"_name","width","100%");
            SceneServices.SetStyle(mDocument,slot+"_name","flex","none");
            SceneServices.SetStyle(mDocument,slot+"_name","text-align","center");
            UiText(slot+"_state",HubText("state_"+state));
            foreach(string s in new[]{"hidden","locked","eligible","owned","sealed"})UiClass(slot,"state_"+s,state==s);
            UiClass(slot,"focused",id==mArmoryFocus);UiClass(slot,"selected_option",id==mArmoryFocus);
        }
        SelectGroup("armory_tab_",["weapons","tomes","trinkets","evolutions"],mArmoryTab);
        SelectGroup("armory_filter_",["all","owned","eligible","locked","disabled"],mArmoryFilter);
        foreach(string filter in new[]{"all","owned","eligible","locked","disabled"})UiShow("armory_filter_"+filter,!evolution&&(filter!="disabled"||sealing));
        UiText("armory_page_value",HubText("page",("page",mArmoryPage+1),("pages",pages)));
        UiText("armory_pool_summary",(evolution?Profile["discoveredEvolutions"]!.AsArray().Count:Profile["owned"]![mArmoryTab]!.AsArray().Count)+" / "+all.Count);
        UiText("armory_filter_disabled_label",HubText("pool_sealed_count",("count",disabled?.AsArray().Count??0)));
        UiShow("armory_pool_toggle_all",!evolution&&sealing&&disabled?.AsArray().Count>0);
        UiShow("armory_pool_hint",!evolution,"block");UiText("armory_pool_hint",HubText(sealing?"pool_hint":"pool_locked_hint"));
        var focus=visible.FirstOrDefault(e=>Text(e!,"id")==mArmoryFocus);
        UiShow("armory_purchase_button",focus!=null&&!evolution&&ContentState(mArmoryTab,mArmoryFocus)=="eligible");
        bool owned=!evolution&&ContentState(mArmoryTab,mArmoryFocus)=="owned", isSealed=Has(disabled,mArmoryFocus);
        UiShow("armory_toggle_button",owned&&sealing);
        if(focus==null){foreach(string field in new[]{"name","description","state","price","evolution"})UiText("armory_detail_"+field,"—");return;}
        bool discovered=!evolution||Has(Profile["discoveredEvolutions"],mArmoryFocus);
        UiText("armory_detail_name",discovered?Local(focus["name"]):"???");
        string formula=discovered?ItemName(Text(focus,"weaponId"))+" + "+ItemName(Text(focus,"tomeId")):"???";
        UiText("armory_detail_description",evolution?formula:Local(focus["description"]));
        UiText("armory_detail_state",HubText("state_"+(evolution?(discovered?"owned":"hidden"):isSealed?"sealed":ContentState(mArmoryTab,mArmoryFocus))));
        var product=mCatalog["products"]!.AsArray().FirstOrDefault(p=>Text(p!,"category")==mArmoryTab&&Text(p!,"contentId")==mArmoryFocus);
        UiText("armory_detail_price",product==null?"—":TextNumber(product,"price"));
        UiText("armory_detail_evolution",evolution?formula:Text(focus,"evolutionId").Length>0?ItemName(Text(focus,"evolutionId")):"—");
        int minimum=mArmoryTab=="trinkets"?4:6, enabled=evolution?0:Profile["owned"]![mArmoryTab]!.AsArray().Count-(disabled?.AsArray().Count??0);
        bool starter=mArmoryTab=="weapons"&&mArmoryFocus==Text(mModels[mCharacter],"starterWeapon");
        UiClass("armory_toggle_button","disabled",!isSealed&&(starter||enabled<=minimum));
        UiText("armory_toggle_button_label",HubText(isSealed?"pool_disabled":starter?"pool_starter_protected":enabled<=minimum?"pool_minimum":"pool_enabled",("count",minimum)));
    }
    private void UpdateShop()
    {
        var all=mCatalog["power_ups"]!.AsArray();if(!all.Any(e=>Text(e!,"id")==mShopFocus))mShopFocus=Text(all[0]!,"id");
        for(int i=0;i<all.Count;i++)
        {
            var item=all[i]!;string id=Text(item,"id"),slot="powerup_node_"+i;mHubSlots[slot]=id;
            int level=(int)Number(Profile["powerUps"]!,id);UiImage(slot+"_icon",Text(item,"icon"));UiText(slot+"_name",Local(item["name"]));
            UiText(slot+"_rank",level+"/"+TextNumber(item,"maxLevel"));UiClass(slot,"focused",id==mShopFocus);UiClass(slot,"selected_option",id==mShopFocus);
            UiClass(slot,"maxed",level>=Number(item,"maxLevel"));UiClass(slot,"locked",PowerLocked(id,level));
        }
        var selected=all.First(e=>Text(e!,"id")==mShopFocus)!;var rule=mCatalog["metaPowerUps"]!.AsArray().First(e=>Text(e!,"id")==mShopFocus)!;
        int rank=(int)Number(Profile["powerUps"]!,mShopFocus),max=(int)Number(selected,"maxLevel");bool locked=PowerLocked(mShopFocus,rank);
        UiText("shop_detail_name",Local(selected["name"]));UiText("shop_detail_description",Local(selected["description"]));
        UiText("shop_current_value",mShopFocus=="meta_weapon_slots"?$"{3+rank} / 6":rank.ToString());
        UiText("shop_next_value",mShopFocus=="meta_weapon_slots"?$"{3+Math.Min(max,rank+1)} / 6":Math.Min(max,rank+1).ToString());
        UiText("shop_next_price",rank<max?rule["prices"]![rank]!.ToString():"—");
        UiText("shop_purchase_button_label",rank<max?HubText("shop_buy",("price",rule["prices"]![rank]!.ToString())):HubText("shop_max"));
        UiText("shop_transaction_status",locked?HubText("shop_requires_clear",("difficulty",HubText("difficulty_"+rule["levelPrerequisites"]![rank]!.GetValue<string>()))):Text(mSnapshot,"message").Length>0?Text(mSnapshot,"message"):HubText("shop_ready"));
        UiShow("shop_purchase_button",rank<max);UiClass("shop_purchase_button","disabled",locked);
        UiShow("shop_enable_button",rank>0&&rule["toggleable"]?.GetValue<bool>()!=false);
        UiText("shop_enable_button_label",HubText(Profile["powerUpsEnabled"]?[mShopFocus]?.GetValue<bool>()==true?"shop_enabled":"shop_disabled"));
        UiShow("shop_refund_button",rank>0);
    }
    private bool PowerLocked(string id,int rank)
    {
        var rule=mCatalog["metaPowerUps"]!.AsArray().First(e=>Text(e!,"id")==id)!;var required=rule["levelPrerequisites"]!.AsArray();
        return rank<required.Count&&Profile["difficultyClears"]?[required[rank]!.GetValue<string>()]?.GetValue<bool>()!=true;
    }
    private double QuestProgress(JsonNode quest)
    {
        string metric=Text(quest,"metric");string key=metric switch {"kills"=>"totalKills","boss_kills"=>"totalBossKills","best_level"=>"bestLevel","survival_seconds"=>"bestSurvivalSeconds","gold_earned"=>"totalGoldEarned",_=>metric};
        double value=metric=="quests_completed"?Profile["completedQuests"]!.AsArray().Count:Number(Profile["career"]!,key);
        return Math.Min(Number(quest,"target"),Math.Max(value,Number(Profile["questProgress"]!,Text(quest,"id"))));
    }
    private void UpdateQuests()
    {
        var entries=mCatalog["quests"]!.AsArray().Where(q=>Text(q!,"hiddenUntil")!="meta_weapon_slots:3"||Number(Profile["powerUps"]!,"meta_weapon_slots")>=3)
            .Where(q=>mQuestFilter switch {"character"=>Text(q!,"category")=="character","combat"=>Text(q!,"category") is "weapon" or "trinket","mastery"=>Text(q!,"category") is "build" or "difficulty","untracked"=>!Has(Profile["trackedQuests"],Text(q!,"id")),_=>true}).ToArray();
        int pages=Math.Max(1,(entries.Length+9)/10);mQuestPage=Math.Clamp(mQuestPage,0,pages-1);var visible=entries.Skip(mQuestPage*10).Take(10).ToArray();
        if(!visible.Any(q=>Text(q!,"id")==mQuestFocus))mQuestFocus=visible.Length>0?Text(visible[0]!,"id"):"";
        for(int i=0;i<10;i++)
        {
            string slot="quest_slot_"+i;mHubSlots.Remove(slot);UiShow(slot,i<visible.Length);if(i>=visible.Length)continue;
            var q=visible[i]!;string id=Text(q,"id");mHubSlots[slot]=id;bool completed=Has(Profile["completedQuests"],id);
            UiText(slot+"_name",Local(q["title"]));UiText(slot+"_progress",$"{QuestProgress(q):0} / {Number(q,"target"):0}");
            UiText(slot+"_reward",completed?HubText("quest_completed"):"+"+TextNumber(q,"rewardGold"));UiClass(slot,"completed",completed);
            UiClass(slot,"tracked",Has(Profile["trackedQuests"],id));UiClass(slot,"focused",id==mQuestFocus);
        }
        SelectGroup("quest_filter_",["all","character","combat","mastery","untracked"],mQuestFilter);
        UiText("quest_page_value",HubText("page",("page",mQuestPage+1),("pages",pages)));
        UiText("quest_completion_summary",Profile["completedQuests"]!.AsArray().Count+" / "+mCatalog["quests"]!.AsArray().Count);
        var focus=visible.FirstOrDefault(q=>Text(q!,"id")==mQuestFocus);UiShow("quest_track_button",focus!=null);
        if(focus==null){UiText("quest_detail_name","—");UiText("quest_detail_description",HubText("empty_quests"));return;}
        UiText("quest_detail_name",Local(focus["title"]));UiText("quest_detail_description",Local(focus["description"]));
        UiText("quest_detail_progress_text",$"{QuestProgress(focus):0} / {Number(focus,"target"):0}");
        SceneServices.SetStyle(mDocument,"quest_detail_progress_fill","width",(100*QuestProgress(focus)/Math.Max(1,Number(focus,"target"))).ToString("0",CultureInfo.InvariantCulture)+"%");
        UiText("quest_detail_reward","+"+TextNumber(focus,"rewardGold"));UiText("quest_detail_unlock",ItemName(Text(focus,"unlockId")));
        UiText("quest_track_button_label",HubText(Has(Profile["trackedQuests"],mQuestFocus)?"quest_untrack":Profile["trackedQuests"]!.AsArray().Count>=3?"quest_track_full":"quest_track"));
    }
    private void UpdateCollection()
    {
        UiText("collection_completion_summary",HubText("collection_summary",new[]{"characters","weapons","tomes","trinkets"}.Select(g=>(g,(object)Profile["owned"]![g]!.AsArray().Count)).ToArray()));
        UiText("collection_total_runs",TextNumber(Profile["career"]!,"runs"));UiText("collection_total_kills",TextNumber(Profile["career"]!,"totalKills"));
        UiText("collection_best_time",TimeSpan.FromSeconds(Number(Profile["career"]!,"bestSurvivalSeconds")).ToString(@"mm\:ss",CultureInfo.InvariantCulture));UiText("collection_top_weapon","—");
        SelectGroup("collection_tab_",["enemies","bosses","evolutions","characters","stats"],mCollectionTab);
        bool stats=mCollectionTab=="stats";UiShow("collection_catalog_grid",!stats);UiShow("collection_stats_summary",stats);
        var entries=mCatalog[stats?"enemies":mCollectionTab]!.AsArray();
        for(int i=0;i<12;i++)
        {
            string slot="collection_slot_"+i;UiShow(slot,!stats&&i<entries.Count);if(stats||i>=entries.Count)continue;
            var item=entries[i]!;string id=Text(item,"id");bool known=mCollectionTab=="evolutions"?Has(Profile["discoveredEvolutions"],id):mCollectionTab!="characters"||ContentState("characters",id)!="locked";
            string title=mCollectionTab=="evolutions"&&!known?"???":Local(item["name"]);
            string role=Text(item,"behaviorId");if(role.Length==0)role=Text(item,"behavior");
            string hint=mCollectionTab=="characters"?HubText("state_"+ContentState("characters",id)):mCollectionTab=="evolutions"?(known?ItemName(Text(item,"weaponId"))+" + "+ItemName(Text(item,"tomeId")):"???"):mCatalog["nativeCollectionRoles"]?[Text(mSettings,"Language")]?[role]?.GetValue<string>()??role;
            string icon=known?Text(item,"icon"):"";UiImage(slot+"_icon",icon);UiShow(slot+"_symbol",icon.Length==0,"block");UiText(slot+"_symbol",known?"◆":"?");
            UiText(slot+"_title",title);UiText(slot+"_hint",hint);UiClass(slot,"discovered",known);UiClass(slot,"silhouette",!known);
        }
    }
}
