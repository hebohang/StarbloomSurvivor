using System.Text.Json.Nodes;
using HEngine;

namespace GameScripts;

public sealed partial class SurvivorNativeGame
{
    private bool bSettingsOpen;
    private JsonObject mSettings = new();
    private JsonObject? mPreviousDisplay;
    private static JsonObject DefaultSettings() => new()
    {
        ["Language"] = "zh_cn", ["MasterVolume"] = .5, ["VSync"] = false,
        ["Fullscreen"] = false, ["UIScale"] = 1.0, ["MotionEnabled"] = true,
        ["DamageFlashEnabled"] = true, ["ProjectileOpacity"] = .85,
        ["ParticleDensity"] = "auto", ["DamageNumbers"] = "full",
        ["ScreenShake"] = true, ["TelegraphColor"] = "default",
        ["AutoVisualThrottle"] = true
    };
    private void InitializeSettings()
    {
        mPreviousDisplay = SceneServices.Call<JsonObject>("settings.display", new { });
        mSettings = DefaultSettings();
        var saved = SceneServices.Call<JsonObject>("settings.read", new { path = "Config/SurvivorGame.json" });
        foreach (var pair in saved)
            if (mSettings[pair.Key] is JsonValue expected && pair.Value is JsonValue actual &&
                (expected.GetValueKind() == actual.GetValueKind() || (expected.TryGetValue<bool>(out _) && actual.TryGetValue<bool>(out _))))
                mSettings[pair.Key] = actual.DeepClone();
        ApplySettings();
    }
    private bool HandleSettingsClick(string id, string mode)
    {
        if (id == "pause_settings_button" && mode == "paused")
        { bSettingsOpen = true; UpdateUi(); return true; }
        if (id == "settings_back_button" && bSettingsOpen)
        { bSettingsOpen = false; UpdateUi(); return true; }
        if (!bSettingsOpen && !(mode == "menu" && mMenuPage == "settings")) return false;
        string option = id.StartsWith("hub_", StringComparison.Ordinal) ? id[4..] : id;
        bool changed = true;
        switch (option)
        {
            case "settings_defaults_button": mSettings = DefaultSettings(); break;
            case "language_zh": mSettings["Language"] = "zh_cn"; break;
            case "language_en": mSettings["Language"] = "en"; break;
            case "volume_down": mSettings["MasterVolume"] = Math.Max(0, Number(mSettings,"MasterVolume") - .1); break;
            case "volume_up": mSettings["MasterVolume"] = Math.Min(1, Number(mSettings,"MasterVolume") + .1); break;
            case "projectile_opacity_down": mSettings["ProjectileOpacity"] = Math.Max(.25, Number(mSettings,"ProjectileOpacity") - .05); break;
            case "projectile_opacity_up": mSettings["ProjectileOpacity"] = Math.Min(1, Number(mSettings,"ProjectileOpacity") + .05); break;
            case "ui_scale_small": mSettings["UIScale"] = .85; break;
            case "ui_scale_normal": mSettings["UIScale"] = 1.0; break;
            case "ui_scale_large": mSettings["UIScale"] = 1.15; break;
            case "display_fullscreen": mSettings["Fullscreen"] = true; break;
            case "display_windowed": mSettings["Fullscreen"] = false; break;
            default:
                changed = false;
                foreach (var (prefix, key, values) in SettingGroups())
                    foreach (string value in values)
                        if (option == prefix + value)
                        {
                            mSettings[key] = values.Length == 2 ? JsonValue.Create(value == "on") : JsonValue.Create(value);
                            changed = true;
                        }
                break;
        }
        if (!changed) return false;
        ApplySettings();
        SceneServices.Call<bool>("settings.write", new { path = "Config/SurvivorGame.json", value = mSettings });
        return true;
    }
    private static IEnumerable<(string Prefix, string Key, string[] Values)> SettingGroups()
    {
        yield return ("vsync_", "VSync", ["on", "off"]);
        yield return ("motion_", "MotionEnabled", ["on", "off"]);
        yield return ("flash_", "DamageFlashEnabled", ["on", "off"]);
        yield return ("screen_shake_", "ScreenShake", ["on", "off"]);
        yield return ("auto_throttle_", "AutoVisualThrottle", ["on", "off"]);
        yield return ("particle_density_", "ParticleDensity", ["auto", "low", "medium", "high"]);
        yield return ("damage_numbers_", "DamageNumbers", ["off", "reduced", "full"]);
        yield return ("telegraph_color_", "TelegraphColor", ["default", "deuteranopia", "tritanopia", "high_contrast"]);
    }
    private void ApplySettings()
    {
        var applied = SceneServices.Call<JsonObject>("settings.display", mSettings);
        foreach (var pair in applied) mSettings[pair.Key] = pair.Value!.DeepClone();
        bool Enabled(string key) => mSettings[key]!.GetValue<bool>();
        void Class(string name, bool enabled) => SceneServices.SetClass(mDocument, "hud", name, enabled);
        Class("reduce_motion", !Enabled("MotionEnabled"));
        Class("reduce_flash", !Enabled("DamageFlashEnabled"));
        Class("screen_shake_off", !Enabled("ScreenShake"));
        Class("damage_numbers_off", Text(mSettings,"DamageNumbers") == "off");
        Class("damage_numbers_reduced", Text(mSettings,"DamageNumbers") == "reduced");
        Class("particle_density_low", Text(mSettings,"ParticleDensity") == "low");
        Class("low_particle", Text(mSettings,"ParticleDensity") == "low");
        Class("telegraph_deuteranopia", Text(mSettings,"TelegraphColor") == "deuteranopia");
        Class("auto_visual_throttle", Enabled("AutoVisualThrottle"));
        if (!Enabled("DamageFlashEnabled")) SceneServices.SetStyle(mDocument,"damage_flash","opacity","0");
        var labels = mCatalog["nativeUiText"]?[Text(mSettings,"Language")] as JsonObject;
        if (labels != null) foreach (var pair in labels) SceneServices.SetText(mDocument, pair.Key, pair.Value!.GetValue<string>());
#if !HE_ANDROID
        bool english = Text(mSettings,"Language") == "en";
        SceneServices.SetText(mDocument, "controls_camera_key", english ? "Mouse" : "鼠标");
        SceneServices.SetText(mDocument, "controls_camera", english ? "Look around" : "转动视角");
#endif
        void Select(string id, bool selected)
        {
            SceneServices.SetClass(mDocument, id, "selected_option", selected);
            SceneServices.SetClass(mDocument, "hub_" + id, "selected_option", selected);
        }
        foreach (var (prefix, key, values) in SettingGroups())
            foreach (string value in values)
                Select(prefix + value, key == "DamageNumbers" || values.Length > 2 ? Text(mSettings,key) == value : Enabled(key) == (value == "on"));
        Select("language_zh", Text(mSettings,"Language") == "zh_cn");
        Select("language_en", Text(mSettings,"Language") == "en");
        Select("display_fullscreen", Enabled("Fullscreen"));
        Select("display_windowed", !Enabled("Fullscreen"));
        Select("ui_scale_small", Number(mSettings,"UIScale") < .93);
        Select("ui_scale_normal", Number(mSettings,"UIScale") >= .93 && Number(mSettings,"UIScale") <= 1.07);
        Select("ui_scale_large", Number(mSettings,"UIScale") > 1.07);
        foreach (string id in new[] {"volume_value_label", "hub_volume_value"})
            SceneServices.SetText(mDocument, id, $"{Number(mSettings,"MasterVolume") * 100:0}%");
        foreach (string id in new[] {"projectile_opacity_value_label", "hub_projectile_opacity_value"})
            SceneServices.SetText(mDocument, id, $"{Number(mSettings,"ProjectileOpacity") * 100:0}%");
    }
}
