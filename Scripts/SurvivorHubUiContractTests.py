"""Static and pure contracts for the data-bound Survivor Hub UI."""

import os
import re
import unittest
import xml.etree.ElementTree as ElementTree

import SurvivorHubNavigation


SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIRECTORY)
RML_PATH = os.path.join(PROJECT_ROOT, "Assets", "UI", "SurvivorHUD.rml")
RCSS_PATH = os.path.join(PROJECT_ROOT, "Assets", "UI", "SurvivorHUD.rcss")
HUB_PATH = os.path.join(SCRIPT_DIRECTORY, "SurvivorHub.py")
GAME_PATH = os.path.join(SCRIPT_DIRECTORY, "SurvivorGame.py")


class SurvivorHubUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ElementTree.parse(RML_PATH).getroot()
        with open(RCSS_PATH, "r", encoding="utf-8") as stream:
            cls.rcss = stream.read()
        with open(HUB_PATH, "r", encoding="utf-8") as stream:
            cls.hub = stream.read()
        with open(GAME_PATH, "r", encoding="utf-8") as stream:
            cls.game = stream.read()

    def _element(self, element_id):
        for element in self.root.iter():
            if element.attrib.get("id") == element_id:
                return element
        self.fail("missing RML element: " + element_id)

    def test_ids_are_unique(self):
        ids = [
            element.attrib["id"]
            for element in self.root.iter()
            if "id" in element.attrib
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_dynamic_selection_has_no_stale_first_item(self):
        self.assertNotIn(
            "selected_character",
            self._element("character_starpaw").attrib.get("class", ""),
        )
        self.assertNotIn(
            "selected_option",
            self._element("armory_slot_0").attrib.get("class", ""),
        )
        self.assertNotIn(
            "selected_option",
            self._element("quest_slot_0").attrib.get("class", ""),
        )
        self.assertIn('card_id, "preview_character"', self.hub)
        self.assertGreaterEqual(
            self.hub.count('slot_id, "selected_option"'), 2,
        )
        start_panel = self._element("start_panel")
        for element in start_panel.iter():
            self.assertNotIn(
                "selected_option", element.attrib.get("class", ""),
                msg="business selection must be initialized by profile state: "
                + element.attrib.get("id", element.tag),
            )

    def test_shop_purchase_double_click_is_debounced(self):
        gate = SurvivorHubNavigation.ActionDebouncer(0.35)
        self.assertTrue(gate.acquire("meta_weapon_slots"))
        self.assertFalse(gate.acquire("meta_weapon_slots"))
        self.assertTrue(gate.acquire("meta_might"))
        self.assertFalse(gate.acquire("meta_weapon_slots"))
        gate.update(0.35)
        self.assertTrue(gate.acquire("meta_weapon_slots"))

    def test_preview_is_centered_bright_and_responsive(self):
        self.assertIn("PREVIEW_POSITION = HEngine.vec3(0.0, 0.08, 0.0)", self.hub)
        scale_match = re.search(r"PREVIEW_MODEL_SCALE\s*=\s*([0-9.]+)", self.hub)
        self.assertIsNotNone(scale_match)
        self.assertGreater(float(scale_match.group(1)), 1.0)
        self.assertIn("PREVIEW_DEFAULT_YAW = 0.0", self.hub)
        self.assertRegex(
            self.hub,
            r"transform\.Rotation\s*=\s*HEngine\.vec3\(\s*float\(preview\.get\(\"upright\", 0\.0\)\) \+ self\.preview_pitch,\s*self\.preview_yaw,\s*0\.0",
        )
        self.assertIn("SetVisualSilhouette", self.hub)
        self.assertIn("_fit_menu_backdrop", self.hub)
        self.assertIn("StarbloomMenuGarden.png cover", self.rcss)
        self._element("title_backdrop_image")
        self.assertIn("character_preview_mode #title_backdrop_image", self.rcss)
        self.assertIn("character_preview_mode #title_backdrop", self.rcss)
        self.assertIn("#character_detail_panel", self.rcss)
        self.assertIn(".hub_detail_panel > *", self.rcss)

    def test_formerly_dead_controls_have_handlers(self):
        for element_id in (
                "play_seed_button",
                "armory_pool_toggle_all",
                "tracked_quest_slot_",
                "collection_tab_"):
            self.assertIn(element_id, self.hub)
        for index in range(5):
            self.assertEqual(self._element("training_stat_" + str(index)).tag, "span")

    def test_inline_settings_are_complete_and_live(self):
        setting_controls = (
            "hub_language_zh", "hub_language_en",
            "hub_volume_down", "hub_volume_up",
            "hub_vsync_on", "hub_vsync_off",
            "hub_display_fullscreen", "hub_display_windowed",
            "hub_ui_scale_small", "hub_ui_scale_normal", "hub_ui_scale_large",
            "hub_motion_on", "hub_motion_off", "hub_flash_on", "hub_flash_off",
            "hub_projectile_opacity_down", "hub_projectile_opacity_up",
            "hub_particle_density_auto", "hub_particle_density_low",
            "hub_particle_density_medium", "hub_particle_density_high",
            "hub_damage_numbers_off", "hub_damage_numbers_reduced",
            "hub_damage_numbers_full", "hub_screen_shake_on", "hub_screen_shake_off",
            "hub_telegraph_color_default", "hub_telegraph_color_deuteranopia",
            "hub_telegraph_color_tritanopia", "hub_telegraph_color_high_contrast",
            "hub_auto_throttle_on", "hub_auto_throttle_off",
            "hub_settings_defaults_button",
        )
        for element_id in setting_controls:
            self._element(element_id)
            self.assertIn(element_id, self.hub)
        self.assertNotIn("hub_projectile_opacity_summary", self.hub)
        self.assertIn('"settings": "hub_language_zh"', self.hub)
        self.assertIn('"hub_volume_value"', self.hub)
        self.assertIn('"hub_projectile_opacity_value"', self.hub)
        self.assertRegex(
            self.rcss,
            r"\.hub_segment_button,\s*\.hub_stepper_button\s*\{[^}]*pointer-events:\s*auto;",
        )
        self.assertRegex(
            self.rcss,
            r"\.hub_setting_row\s*\{[^}]*min-width:\s*760dp;",
        )

    def test_challenges_are_additive_but_exclusive_groups_are_not(self):
        self.assertIn("selectedChallenges", self.hub)
        self.assertIn('slot_id, "checked", bChecked', self.hub)
        self.assertIn("SurvivorRules.toggle_challenge_id", self.hub)
        self.assertIn(".toggle_card.checked", self.rcss)
        self.assertIn("def _set_exclusive_selection", self.hub)
        for prefix in (
                "difficulty_", "armory_tab_", "armory_filter_",
                "quest_filter_", "collection_tab_", "hub_language_"):
            self.assertIn(prefix, self.hub)

    def test_weapon_slot_selection_and_meta_upgrade_are_data_bound(self):
        for weapon_slot_limit in range(3, 7):
            self._element("weapon_limit_" + str(weapon_slot_limit))
            self._element("weapon_limit_" + str(weapon_slot_limit) + "_label")
        self._element("play_weapon_slots_summary")
        self._element("powerup_node_12")
        self._element("powerup_node_12_icon")
        self.assertIn("SurvivorMetaProgression.purchased_weapon_slot_limit", self.hub)
        self.assertIn("def _select_weapon_slot_limit", self.hub)
        self.assertIn('source_id.startswith("weapon_limit_")', self.hub)
        self.assertIn("len(POWER_UPS)", self.hub)

    def test_gameplay_objective_domain_and_result_ids_are_complete(self):
        for element_id in (
                "region_objective_panel", "region_completed_count",
                "region_current_name", "region_countdown", "region_progress_fill",
                "region_status_instruction", "objective_navigation", "domain_power_panel",
                "result_weapon_slot_limit", "result_weapon_slot_bonus",
                "result_region_order", "result_region_attempts", "result_region_exits",
                "result_domain_summary", "result_boss_ttk"):
            self._element(element_id)
        for region_id in ("star", "thunder", "water", "wind"):
            for suffix in ("", "_name", "_status", "_direction"):
                self._element("region_seal_" + region_id + suffix)
            self._element("domain_power_" + region_id)
            self._element("domain_power_" + region_id + "_icon")
            self._element("domain_power_" + region_id + "_cooldown")
        self.assertIn("#region_objective_panel", self.rcss)
        self.assertIn("#domain_power_panel", self.rcss)
        self.assertIn("particle_density_low #region_objective_panel", self.rcss)

    def test_play_and_result_layouts_use_stable_logical_widths(self):
        self.assertRegex(
            self.rcss,
            r"#hub_page_play \.hub_feature_card,[\s\S]*?width:\s*760dp;[\s\S]*?min-width:\s*760dp;",
        )
        self.assertRegex(
            self.rcss,
            r"\.result_column\s*>\s*\.result_section\s*\{[^}]*width:\s*360dp;",
        )
        self.assertRegex(
            self.rcss,
            r"\.weapon_result_column\s*>\s*\.result_section\s*\{[^}]*width:\s*760dp;",
        )
        self.assertNotIn("min-width: 100%;", self.rcss)
        self.assertNotRegex(
            self.rcss,
            r"\.weapon_limit_choices \.choice_card\s*\{[^}]*width:\s*24%;",
        )

    def test_play_scroll_layer_does_not_steal_button_hits(self):
        self.assertRegex(
            self.rcss,
            r"#play_scroll\s*\{[^}]*overflow:\s*hidden;[^}]*pointer-events:\s*none;",
        )
        self.assertRegex(
            self.rcss,
            r"#play_scroll button\s*\{[^}]*pointer-events:\s*auto;",
        )

    def test_result_actions_are_distinct_and_purchase_dead_end_is_removed(self):
        self.assertNotIn("result_purchase_button", self.hub)
        with self.assertRaises(AssertionError):
            self._element("result_purchase_button")
        self.assertIn("result_restart_button", self._element(
            "restart_button").attrib.get("class", ""))
        self.assertIn("result_build_button", self._element(
            "result_adjust_build_button").attrib.get("class", ""))
        self.assertIn("result_home_button", self._element(
            "game_over_home_button").attrib.get("class", ""))
        self.assertIn('source_id == "result_adjust_build_button"', self.hub)
        self.assertIn('self._show_hub_page("armory")', self.hub)

    def test_result_stats_have_fixed_readable_cells(self):
        self.assertRegex(
            self.rcss,
            r"#result_stats\s*\{[^}]*min-width:\s*1120dp;",
        )
        self.assertRegex(
            self.rcss,
            r"\.result_stat\s*\{[^}]*width:\s*181dp;[^}]*height:\s*68dp;",
        )
        self.assertRegex(
            self.rcss,
            r"#result_stats \.result_value\s*\{[^}]*font-size:\s*23dp;",
        )

    def test_game_settings_scroll_layer_does_not_steal_button_hits(self):
        self.assertRegex(
            self.rcss,
            r"#settings_body\s*\{[^}]*overflow:\s*hidden;[^}]*pointer-events:\s*none;",
        )
        self.assertRegex(
            self.rcss,
            r"#settings_body button\s*\{[^}]*pointer-events:\s*auto;",
        )
        self.assertRegex(
            self.rcss,
            r"#settings_body \.setting_row\s*\{[^}]*min-height:\s*43dp;",
        )
        self.assertIn("_SETTINGS_CONTROL_IDS", self.game)
        self.assertIn("not bSettingsControl", self.game)

    def test_weapon_slots_keep_locked_empty_and_equipped_states_distinct(self):
        for index in range(1, 7):
            self._element("weapon_slot_" + str(index))
        self.assertIn(".weapon_stat.empty { display: flex;", self.rcss)
        self.assertIn(".weapon_stat.equipped", self.rcss)
        self.assertIn(".weapon_stat.locked", self.rcss)
        self.assertNotIn(".weapon_stat.empty {\n  display: none;", self.rcss)

    def test_six_weapon_endgame_quests_are_hidden_until_slot_six(self):
        self.assertIn('hidden_until == "meta_weapon_slots:3"', self.hub)
        self.assertIn("def _quest_visible", self.hub)

    def test_catalog_cards_use_real_images(self):
        for element_id in (
            "play_character_portrait", "character_starpaw_icon",
                "armory_slot_0_icon", "powerup_node_0_icon", "powerup_node_12_icon",
                "collection_slot_0_icon"):
            self.assertEqual(self._element(element_id).tag, "img")

    def test_collection_tabs_and_slots_are_complete(self):
        for tab in ("enemies", "bosses", "evolutions", "characters", "stats"):
            self._element("collection_tab_" + tab)
        for index in range(12):
            self._element("collection_slot_" + str(index))

    def test_quest_and_action_controls_have_explicit_width_rules(self):
        self.assertRegex(
            self.rcss,
            r"\.quest_slot\s*\{[^}]*width:\s*560dp;[^}]*min-width:\s*560dp;",
        )
        self.assertRegex(
            self.rcss,
            r"\.hub_detail_panel\s*>\s*\*\s*\{[^}]*width:\s*100%;",
        )
        self.assertIn(".hub_action_button.disabled", self.rcss)
        self.assertIn(".quest_slot > span { pointer-events: none; }", self.rcss)
        self.assertRegex(
            self.rcss,
            r"\.segment_group\s*\{[^}]*min-width:\s*173dp;",
        )
        self.assertRegex(
            self.rcss,
            r"\.hub_tab\s*\{[^}]*flex:\s*1 1 0;",
        )
        self.assertIn(
            'event_type == "mousedown" and source_id.startswith("quest_filter_")',
            self.hub,
        )
        self.assertIn('slot_id, "selected_option", False', self.hub)
        self.assertNotIn(".quest_slot.completed {", self.rcss)

    def test_armory_sealing_is_explained_and_safe(self):
        self._element("armory_pool_hint")
        self._element("armory_empty_state")
        self._element("armory_empty_state_label")
        self.assertIn("quest_system_seal", self.hub)
        self.assertIn(
            'event_type == "mousedown" and source_id.startswith("armory_filter_")',
            self.hub,
        )
        self.assertIn('self.armory_filter = "all"', self.hub)
        self.assertNotIn('"精简池" if self.language', self.hub)


if __name__ == "__main__":
    unittest.main(verbosity=2)
