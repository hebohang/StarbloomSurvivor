import ast
import string
import sys
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from SurvivorCatalog import (  # noqa: E402
    POWER_UPS,
    TOMES,
    TRINKETS,
    WEAPONS,
    validate_catalog,
)
from SurvivorContent import CONTENT_TEXT, TOME_DEFS, WEAPON_DEFS  # noqa: E402
from SurvivorMetaProgression import META_POWER_UP_RULES  # noqa: E402


def _literal_assignment(relative_path, assignment_name):
    source_path = PROJECT_ROOT / relative_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
                isinstance(target, ast.Name)
                and target.id == assignment_name
                for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Missing assignment " + assignment_name)


def _format_fields(template):
    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(template)
        if field_name
    }


class SurvivorLocalizationContractTests(unittest.TestCase):
    def test_language_tables_have_matching_keys_and_placeholders(self):
        tables = (
            _literal_assignment("Scripts/SurvivorGame.py", "SURVIVOR_TEXT"),
            _literal_assignment("Scripts/SurvivorHub.py", "HUB_TEXT"),
            _literal_assignment("Scripts/SurvivorHub.py", "RESULT_TEXT"),
            _literal_assignment("Scripts/SurvivorHub.py", "HUB_STATIC_TEXT"),
            CONTENT_TEXT,
        )
        for table in tables:
            self.assertEqual(set(table["zh_cn"]), set(table["en"]))
            for key in table["zh_cn"]:
                self.assertTrue(table["zh_cn"][key].strip(), key)
                self.assertTrue(table["en"][key].strip(), key)
                self.assertEqual(
                    _format_fields(table["zh_cn"][key]),
                    _format_fields(table["en"][key]),
                    key,
                )

    def test_catalog_display_fields_are_localized(self):
        validate_catalog()
        self.assertEqual(len(POWER_UPS), 13)
        for catalog_entry, rule in zip(POWER_UPS, META_POWER_UP_RULES):
            for field_name in (
                    "id", "maxLevel", "perLevel", "prices",
                    "levelPrerequisites", "toggleable"):
                self.assertEqual(
                    catalog_entry[field_name], rule[field_name],
                    catalog_entry["id"] + ":" + field_name,
                )
        for entry in TOMES + TRINKETS + POWER_UPS:
            description = entry["description"]
            self.assertTrue(description["zh_cn"].strip(), entry["id"])
            self.assertTrue(description["en"].strip(), entry["id"])
            self.assertNotEqual(
                description["zh_cn"], description["en"], entry["id"],
            )
        for entry in TOMES:
            self.assertTrue(entry["statText"]["zh_cn"].strip(), entry["id"])
            self.assertTrue(entry["statText"]["en"].strip(), entry["id"])

    def test_upgrade_choices_do_not_expose_internal_behavior_ids(self):
        behavior_ids = {entry["behavior"] for entry in WEAPONS}
        for item_id, definition in WEAPON_DEFS.items():
            for field_name in (
                    "unlock_name_key", "unlock_desc_key", "unlock_stat_key",
                    "upgrade_name_key", "upgrade_desc_key", "upgrade_stat_key"):
                key = definition[field_name]
                zh_text = CONTENT_TEXT["zh_cn"][key]
                en_text = CONTENT_TEXT["en"][key]
                self.assertNotEqual(zh_text, en_text, item_id + ":" + field_name)
                for behavior_id in behavior_ids:
                    self.assertNotIn(behavior_id, zh_text, key)

        for item_id, definition in TOME_DEFS.items():
            for field_name in ("description_key", "stat_key"):
                key = definition[field_name]
                self.assertNotEqual(
                    CONTENT_TEXT["zh_cn"][key],
                    CONTENT_TEXT["en"][key],
                    item_id + ":" + field_name,
                )
        weapon_slots = next(
            entry for entry in POWER_UPS
            if entry["id"] == "meta_weapon_slots"
        )
        self.assertEqual(weapon_slots["prices"], (600, 1500, 3200))
        self.assertNotEqual(
            weapon_slots["name"]["zh_cn"], weapon_slots["name"]["en"],
        )

    def test_runtime_applies_saved_language_before_showing_the_menu(self):
        source = (PROJECT_ROOT / "Scripts/SurvivorGame.py").read_text(encoding="utf-8")
        apply_settings = source.index("        self._apply_settings()")
        apply_language = source.index("        self._apply_language()", apply_settings)
        show_menu = source.index("            self._show_start_menu()", apply_language)
        self.assertLess(apply_settings, apply_language)
        self.assertLess(apply_language, show_menu)

    def test_active_ui_exposes_localizable_keycaps(self):
        markup = (PROJECT_ROOT / "Assets/UI/SurvivorHUD.rml").read_text(
            encoding="utf-8",
        )
        self.assertIn('id="controls_jump_key"', markup)
        self.assertIn('id="controls_camera_key"', markup)
        game_text = _literal_assignment("Scripts/SurvivorGame.py", "SURVIVOR_TEXT")
        for key in (
                "controls_jump_key", "controls_camera_key",
                "upgrade_reroll", "upgrade_skip", "upgrade_banish",
                "upgrade_banish_confirm", "weapon_evolved_value"):
            self.assertIn(key, game_text["zh_cn"])
            self.assertIn(key, game_text["en"])

    def test_region_domain_slot_and_result_ui_contract_is_localizable(self):
        markup = (PROJECT_ROOT / "Assets/UI/SurvivorHUD.rml").read_text(
            encoding="utf-8",
        )
        required_ids = (
            "region_objective_panel", "region_completed_count",
            "region_current_name", "region_countdown", "region_progress_fill",
            "region_status_instruction", "objective_navigation", "domain_power_panel",
            "result_weapon_slot_limit", "result_weapon_slot_bonus",
            "result_region_order", "result_region_attempts", "result_region_exits",
            "result_domain_summary", "result_boss_ttk",
        )
        for element_id in required_ids:
            self.assertIn('id="' + element_id + '"', markup)
        for region_id in ("star", "thunder", "water", "wind"):
            self.assertIn('id="region_seal_' + region_id + '"', markup)
            self.assertIn('id="region_seal_' + region_id + '_name"', markup)
            self.assertIn('id="region_seal_' + region_id + '_status"', markup)
            self.assertIn('id="region_seal_' + region_id + '_direction"', markup)
            self.assertIn('id="domain_power_' + region_id + '"', markup)
            self.assertIn('id="domain_power_' + region_id + '_icon"', markup)
            self.assertIn('id="domain_power_' + region_id + '_cooldown"', markup)

        game_text = _literal_assignment("Scripts/SurvivorGame.py", "SURVIVOR_TEXT")
        for key in (
                "region_objective_title", "region_completed", "region_current_none",
                "region_star_name", "region_thunder_name", "region_water_name",
                "region_wind_name", "region_state_dormant", "region_state_arming",
                "region_state_assault", "region_state_outside_grace",
                "region_state_cooldown", "region_state_activated",
                "region_explore_instruction", "region_arming_instruction",
                "region_hold_instruction", "region_grace_instruction",
                "region_grace_countdown", "region_cooldown_instruction",
                "region_complete_instruction",
                "objective_hold_region", "objective_return_region",
                "region_navigation", "domain_power_title", "domain_star_name",
                "domain_thunder_name", "domain_water_name", "domain_wind_name",
                "weapon_slot_locked", "weapon_slot_empty", "boss_ready_objective"):
            self.assertIn(key, game_text["zh_cn"])
            self.assertIn(key, game_text["en"])


if __name__ == "__main__":
    unittest.main()
