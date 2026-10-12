import os

import HEngine
import SurvivorEconomy
import SurvivorProfile
import SurvivorRunConfig
import SurvivorSession

from SurvivorCatalogMeta import PRODUCTS
from SurvivorCatalogItems import EVOLUTION_BY_ID
from SurvivorCatalogWorld import CHALLENGES, DIFFICULTIES
from SurvivorContent import (
    CHARACTER_DEFS,
    CHARACTER_ORDER,
    MAX_TOME_SLOTS,
    MAX_WEAPON_SLOTS,
    TOME_DEFS,
    TOME_ORDER,
    WEAPON_DEFS,
    WEAPON_ORDER,
)


RmlUI = HEngine.RmlUI
_PRODUCT_BY_KEY = {
    (product["category"], product["contentId"]): product
    for product in PRODUCTS
}
_DIFFICULTY_GOLD = {entry["id"]: entry["gold"] for entry in DIFFICULTIES}
_CHALLENGE_GOLD = {entry["id"]: entry["gold"] for entry in CHALLENGES}


class SurvivorPresentationMixin:
    def _load_settings(self):
        self.language = self.DEFAULT_LANGUAGE
        self.master_volume = self.DEFAULT_MASTER_VOLUME
        self.bVSyncEnabled = self.DEFAULT_VSYNC
        self.bFullscreen = self.DEFAULT_FULLSCREEN
        self.ui_scale = self.DEFAULT_UI_SCALE
        self.bMotionEnabled = self.DEFAULT_MOTION_ENABLED
        self.bDamageFlashEnabled = self.DEFAULT_DAMAGE_FLASH_ENABLED
        self.player_projectile_opacity = self.DEFAULT_PROJECTILE_OPACITY
        self.particle_density = self.DEFAULT_PARTICLE_DENSITY
        self.damage_numbers_mode = self.DEFAULT_DAMAGE_NUMBERS
        self.bScreenShakeEnabled = self.DEFAULT_SCREEN_SHAKE
        self.enemy_telegraph_color = self.DEFAULT_TELEGRAPH_COLOR
        self.bAutoVisualThrottle = self.DEFAULT_AUTO_VISUAL_THROTTLE
        self.selected_character = "starpaw"
        self.profile = SurvivorProfile.default_profile()
        self.bProfileWritable = True

        config_sources = (
            (HEngine.GetFullPath(self.SETTINGS_CONFIG), False, "packaged defaults"),
            (HEngine.GetSavedPath(self.SETTINGS_CONFIG), True, "saved settings"),
        )
        for config_path, bMissingAllowed, config_label in config_sources:
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    self._apply_settings_config(config_file.read())
            except FileNotFoundError:
                if not bMissingAllowed:
                    HEngine.HE_CORE_WARN(
                        "[SurvivorGame] Packaged settings defaults unavailable",
                    )
            except (OSError, UnicodeError, ValueError):
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] Could not read " + config_label + "; ignoring it",
                )
        self._load_progression()

    def _progression_path(self):
        return HEngine.GetSavedPath("Config/SurvivorProgression.json")

    def _load_progression(self):
        def log_recovery(message):
            HEngine.HE_CORE_WARN("[SurvivorProfile] " + message)

        try:
            profile = SurvivorProfile.load_profile(
                self._progression_path(), logger=log_recovery,
            )
        except SurvivorProfile.FutureProfileVersionError as error:
            self.bProfileWritable = False
            profile = SurvivorProfile.default_profile()
            HEngine.HE_CORE_ERROR(
                "[SurvivorProfile] Refusing newer profile without overwriting it: "
                + str(error),
            )
        interrupted_run = profile.get("lastRun")
        if (
                isinstance(interrupted_run, dict)
                and not interrupted_run.get("rewardCommitted", False)):
            zero_reward = SurvivorEconomy.compute_run_reward(
                0.0, 0, 0, 0, 1, end_reason="abandon",
            )
            SurvivorEconomy.commit_run_reward(
                profile,
                interrupted_run["runId"],
                zero_reward,
                "abandon",
            )
            try:
                profile = SurvivorProfile.save_profile(
                    profile,
                    self._progression_path(),
                )
            except (OSError, ValueError, RuntimeError) as error:
                HEngine.HE_CORE_WARN(
                    "[SurvivorProfile] Interrupted run recovery could not persist: "
                    + str(error),
                )
        self._refresh_profile_eligibility(profile)
        self._adopt_profile(profile)

    def _adopt_profile(self, profile):
        self.profile = profile
        quest_tracker = getattr(self, "quest_tracker", None)
        if quest_tracker is not None:
            quest_tracker.profile = profile
        owned_characters = profile["owned"]["characters"]
        selected = profile.get("selectedCharacter", "starpaw")
        if selected not in CHARACTER_DEFS or selected not in owned_characters:
            selected = "starpaw"
            profile["selectedCharacter"] = selected
        self.selected_character = selected

    def _save_progression(self, profile=None):
        if not getattr(self, "bProfileWritable", True):
            HEngine.HE_CORE_WARN("[SurvivorProfile] Save refused for newer profile version")
            return False
        profile = self.profile if profile is None else profile
        try:
            saved_profile = SurvivorProfile.save_profile(
                profile, self._progression_path(),
            )
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            HEngine.HE_CORE_WARN(
                "[SurvivorProfile] Could not persist progression: " + str(error),
            )
            return False
        self._adopt_profile(saved_profile)
        return True

    def _refresh_profile_eligibility(self, profile):
        completed = set(profile.get("completedQuests", []))
        cleared = profile.get("difficultyClears", {})
        newly_eligible_characters = []
        for product in PRODUCTS:
            unlock_id = product["unlockId"]
            bEligible = (
                unlock_id == "quest_start"
                or unlock_id in completed
                or (unlock_id == "quest_clear_adventure" and cleared.get("adventure"))
                or (unlock_id == "quest_clear_fierce" and cleared.get("fierce"))
            )
            if bEligible and SurvivorEconomy.grant_content_eligibility(
                    profile, product["category"], product["contentId"]):
                if product["category"] == "characters":
                    newly_eligible_characters.append(product["contentId"])

        career = profile["career"]
        legacy_eligibility = {
            "peachy": career["bestSurvivalSeconds"] >= 120.0,
            "mossling": career["totalKills"] >= 750,
            "snowbean": career["totalBossKills"] >= 1,
            "azura": career["bestLevel"] >= 20,
        }
        for character_id, bEligible in legacy_eligibility.items():
            if bEligible and SurvivorEconomy.grant_content_eligibility(
                    profile, "characters", character_id):
                newly_eligible_characters.append(character_id)
        return tuple(newly_eligible_characters)

    def _character_unlocked(self, character_code):
        return character_code in self.profile["owned"]["characters"]

    def _content_state(self, category, content_id):
        return SurvivorEconomy.content_state(self.profile, category, content_id)

    def _grant_content_eligibility(self, category, content_id):
        staged = SurvivorProfile.validate_profile(self.profile)
        if not SurvivorEconomy.grant_content_eligibility(
                staged, category, content_id):
            return True
        return self._save_progression(staged)

    def _persist_economy_receipt(self, staged, receipt, success_status):
        if receipt["status"] != success_status:
            receipt["persisted"] = False
            self.audio.post(
                "insufficient_gold"
                if receipt["status"] == "insufficient_gold" else
                "ui_error",
            )
            return receipt
        if self._save_progression(staged):
            receipt["persisted"] = True
            self._refresh_character_roster()
            self.audio.post("purchase" if success_status == "purchased" else "ui_confirm")
            return receipt
        failed = dict(receipt)
        failed["status"] = "save_failed"
        failed["persisted"] = False
        failed["walletAfter"] = self.profile["walletGold"]
        return failed

    def _purchase_content(self, category, content_id):
        category_key = SurvivorEconomy.CONTENT_CATEGORIES.get(category)
        product = _PRODUCT_BY_KEY.get((category_key, content_id))
        if product is None:
            wallet = self.profile["walletGold"]
            return {
                "status": "unknown_product",
                "walletBefore": wallet,
                "walletAfter": wallet,
                "persisted": False,
            }
        staged = SurvivorProfile.validate_profile(self.profile)
        receipt = SurvivorEconomy.purchase_content(
            staged, category_key, content_id, product["price"],
        )
        return self._persist_economy_receipt(staged, receipt, "purchased")

    def _purchase_power_up(self, power_up_id, expected_level):
        staged = SurvivorProfile.validate_profile(self.profile)
        receipt = SurvivorEconomy.purchase_power_up(
            staged, power_up_id, expected_level,
        )
        return self._persist_economy_receipt(staged, receipt, "purchased")

    def _refund_power_up(self, power_up_id, expected_level=None):
        staged = SurvivorProfile.validate_profile(self.profile)
        receipt = SurvivorEconomy.refund_power_up(
            staged, power_up_id, expected_level,
        )
        return self._persist_economy_receipt(staged, receipt, "refunded")

    def _refund_all_power_ups(self):
        staged = SurvivorProfile.validate_profile(self.profile)
        receipt = SurvivorEconomy.refund_all_power_ups(staged)
        return self._persist_economy_receipt(staged, receipt, "refunded")

    def _set_power_up_enabled(self, power_up_id, bEnabled):
        staged = SurvivorProfile.validate_profile(self.profile)
        bApplied = SurvivorEconomy.set_power_up_enabled(
            staged, power_up_id, bEnabled,
        )
        if self._save_progression(staged):
            return {"status": "updated", "enabled": bApplied, "persisted": True}
        return {"status": "save_failed", "enabled": False, "persisted": False}

    def _has_uncommitted_run(self):
        active_run = self.profile.get("lastRun")
        return (
            isinstance(active_run, dict)
            and not active_run.get("rewardCommitted", False)
        )

    def _begin_run_transaction(self):
        staged = SurvivorProfile.validate_profile(self.profile)
        config_profile = staged
        capture_scenario = os.environ.get(
            "HE_SURVIVOR_CAPTURE_SCENARIO", "",
        ).strip().lower()
        capture_difficulty = staged["selectedDifficulty"]
        capture_slot_limit = staged["selectedWeaponSlotLimit"]
        if capture_scenario == "three_slot_adventure":
            capture_difficulty = "adventure"
            capture_slot_limit = 3
        elif capture_scenario == "six_slot_nightmare":
            config_profile = SurvivorProfile.validate_profile(staged)
            config_profile.setdefault("powerUps", {})["meta_weapon_slots"] = 3
            config_profile["selectedWeaponSlotLimit"] = 6
            capture_difficulty = "nightmare"
            capture_slot_limit = 6
        run_config = SurvivorRunConfig.compile_run_config(
            config_profile,
            challenges=CHALLENGES,
            character_id=staged["selectedCharacter"],
            difficulty_id=capture_difficulty,
            challenge_ids=staged["selectedChallenges"],
            weapon_slot_limit=capture_slot_limit,
            run_seed=int(getattr(self, "selected_run_seed", 7319)),
        )
        try:
            run_record = SurvivorEconomy.begin_run(
                staged,
                character_id=run_config.selected_character,
                difficulty_id=run_config.selected_difficulty,
                challenge_ids=run_config.challenge_ids,
                weapon_slot_limit=run_config.weapon_slot_limit,
            )
            run_record["runConfig"] = run_config.as_dict()
        except (ValueError, RuntimeError) as error:
            HEngine.HE_CORE_WARN(
                "[SurvivorProfile] Could not begin run transaction: " + str(error),
            )
            return False
        if not self._save_progression(staged):
            return False
        self.run_config = run_config
        self.current_run_id = run_record["runId"]
        self.run_end_reason = ""
        return True

    def _run_reward_breakdown(self, end_reason):
        tome_levels = getattr(self, "tome_levels", {})
        greed_tome_bonus = (
            tome_levels.get("greed", 0) * 0.08
            + tome_levels.get("curse", 0) * 0.10
        )
        power_ups = self.profile.get("powerUps", {})
        power_up_enabled = self.profile.get("powerUpsEnabled", {})
        global_greed_bonus = 0.0
        if power_up_enabled.get("meta_greed", False):
            global_greed_bonus = power_ups.get("meta_greed", 0) * 0.05

        character_gold_bonus = max(
            0.0, getattr(self, "character_gold_multiplier", 1.0) - 1.0,
        )
        run_config = getattr(self, "run_config", None)
        difficulty_id = (
            run_config.selected_difficulty
            if run_config is not None else
            self.profile.get("selectedDifficulty", "adventure")
        )
        challenge_reward = (
            run_config.combined_challenge_rewards
            if run_config is not None else
            1.0
        )
        return SurvivorEconomy.compute_run_reward(
            self.elapsed,
            self.kills,
            getattr(
                self, "run_reward_elite_kills",
                getattr(self, "run_elite_kills", 0),
            ),
            self.run_boss_kills,
            self.level,
            victory=end_reason == "victory",
            revives_used=getattr(self, "run_revives_used", 0),
            quest_gold=(
                self.quest_tracker.run_quest_gold
                if self.quest_tracker is not None else
                0
            ),
            bonus_gold=max(
                0,
                int(getattr(self, "run_gold", 0))
                - int(getattr(self, "run_elite_bonus_gold", 0)),
            ),
            greed_tome_bonus=greed_tome_bonus,
            honeybun_bonus=character_gold_bonus,
            global_greed_bonus=global_greed_bonus,
            difficulty_reward=_DIFFICULTY_GOLD.get(difficulty_id, 1.0),
            challenge_reward=challenge_reward,
            weapon_slot_limit=getattr(self, "weapon_slot_limit", 3),
            end_reason=end_reason,
        )

    def _record_run_progress(self, end_reason="death"):
        active_run = self.profile.get("lastRun")
        wallet = self.profile["walletGold"]
        if not isinstance(active_run, dict):
            return {
                "status": "no_active_run",
                "walletBefore": wallet,
                "walletAfter": wallet,
                "persisted": False,
                "newCharacterEligible": False,
            }
        if active_run.get("rewardCommitted", False):
            return {
                "status": "already_committed",
                "walletBefore": wallet,
                "walletAfter": wallet,
                "persisted": True,
                "newCharacterEligible": False,
            }

        if self.quest_tracker is not None:
            self.quest_tracker.record("runs", 1)
            if end_reason == "victory":
                self.quest_tracker.record(
                    "different_damage_weapons_clear",
                    sum(
                        1 for values in self.weapon_telemetry.values()
                        if values["damage"] > 0.0
                    ),
                    bSet=True,
                )
            self.quest_tracker.flush()
            completed_count = len(self.profile["completedQuests"])
            if completed_count > getattr(self, "quest_completion_audio_count", 0):
                self.audio.post("quest_complete")
                self.quest_completion_audio_count = completed_count
        reward = self._run_reward_breakdown(end_reason)
        if self.quest_tracker is not None:
            self.quest_tracker.record("gold_earned", reward["earnedGold"])
            self.quest_tracker.flush()
            reward = self._run_reward_breakdown(end_reason)

        staged = SurvivorProfile.validate_profile(self.profile)
        career = staged["career"]
        career["totalKills"] = min(
            SurvivorEconomy.MAX_RUN_COUNTER,
            career["totalKills"] + max(0, int(self.kills)),
        )
        career["totalElites"] = min(
            SurvivorEconomy.MAX_RUN_COUNTER,
            career["totalElites"] + max(0, int(getattr(self, "run_elite_kills", 0))),
        )
        career["totalBossKills"] = min(
            SurvivorEconomy.MAX_RUN_COUNTER,
            career["totalBossKills"] + max(
                0,
                int(getattr(self, "run_total_boss_kills", self.run_boss_kills)),
            ),
        )
        career["bestSurvivalSeconds"] = max(
            career["bestSurvivalSeconds"], max(0.0, float(self.elapsed)),
        )
        career["bestLevel"] = max(career["bestLevel"], max(1, int(self.level)))

        character_id = staged["selectedCharacter"]
        mastery_xp = int(max(0.0, float(self.elapsed)))
        mastery_xp += max(0, int(self.kills)) // 5
        mastery_xp += max(0, int(self.run_boss_kills)) * 100
        if end_reason == "victory":
            mastery_xp += 300
        staged["characterMasteryXp"][character_id] = min(
            SurvivorEconomy.MAX_RUN_COUNTER,
            staged["characterMasteryXp"].get(character_id, 0) + mastery_xp,
        )

        run_config = getattr(self, "run_config", None)
        difficulty_id = (
            run_config.selected_difficulty
            if run_config is not None else
            staged["selectedDifficulty"]
        )
        challenge_ids = (
            run_config.challenge_ids
            if run_config is not None else
            tuple(staged.get("selectedChallenges", ()))
        )
        if end_reason == "victory":
            staged["difficultyClears"][difficulty_id] = True
            for challenge_id in challenge_ids:
                staged["challengeClears"][challenge_id] = True
            difficulty_rank = {"adventure": 0, "fierce": 1, "nightmare": 2}
            if difficulty_rank.get(difficulty_id, 0) > difficulty_rank.get(
                    career["highestDifficulty"], 0):
                career["highestDifficulty"] = difficulty_id

        objective_controller = getattr(self, "objective_controller", None)
        objective_snapshot = (
            objective_controller.snapshot()
            if objective_controller is not None else
            {"completedRegions": [], "regions": {}}
        )
        region_rows = objective_snapshot.get("regions", {})
        staged["lastRun"]["resultSummary"] = {
            "regionActivationOrder": list(
                objective_snapshot.get("completedRegions", ())
            ),
            "regionAttempts": {
                region_id: int(row.get("attempts", 0))
                for region_id, row in region_rows.items()
            },
            "regionExitFailures": {
                region_id: int(row.get("failureCount", 0))
                for region_id, row in region_rows.items()
            },
            "weaponSlotLimit": int(getattr(self, "weapon_slot_limit", 3)),
            "domainStats": {
                domain_id: dict(values)
                for domain_id, values in getattr(
                    self, "domain_telemetry", {},
                ).items()
            },
            "bossTtkSeconds": (
                float(getattr(self, "objective_boss_ttk", 0.0))
                if getattr(self, "objective_boss_spawn_raw_time", None) is not None
                else None
            ),
        }

        receipt = SurvivorEconomy.commit_run_reward(
            staged, active_run["runId"], reward, end_reason,
        )
        newly_eligible = self._refresh_profile_eligibility(staged)
        if self._save_progression(staged):
            receipt["persisted"] = True
            receipt["newCharacterEligible"] = bool(newly_eligible)
            self._refresh_character_roster()
            return receipt

        failed = dict(receipt)
        failed["status"] = "save_failed"
        failed["persisted"] = False
        failed["walletAfter"] = self.profile["walletGold"]
        failed["newCharacterEligible"] = False
        return failed

    def _select_character(self, character_code):
        if character_code not in CHARACTER_DEFS or not self._character_unlocked(character_code):
            return
        staged = SurvivorProfile.validate_profile(self.profile)
        staged["selectedCharacter"] = character_code
        if self._save_progression(staged):
            if not self.bInMainMenu:
                self._apply_selected_character_visual()
            self._refresh_character_roster()

    def _apply_selected_character_visual(self):
        if self.player is None:
            return
        # Scripts can be reloaded while an older Editor process still owns the
        # embedded HEngine module. Keep PIE usable until that process is rebuilt
        # and restarted with the newer Entity.SetVisual binding.
        set_visual = getattr(self.player, "SetVisual", None)
        if set_visual is None:
            return
        definition = CHARACTER_DEFS[self.selected_character]
        set_visual(
            definition["mesh"],
            definition["controller"],
            definition["scale"],
        )

    def _refresh_character_roster(self):
        if not self.document_id:
            return
        for code in CHARACTER_ORDER:
            definition = CHARACTER_DEFS[code]
            bUnlocked = self._character_unlocked(code)
            self._set_hud_text(
                "character_" + code + "_name",
                self._text(definition["name_key"]),
            )
            self._set_hud_text(
                "character_" + code + "_passive",
                self._text(definition["passive_key"]),
            )
            self._set_hud_text(
                "character_" + code + "_unlock",
                self._text("character_unlocked" if bUnlocked else definition["unlock_key"]),
            )
            self._set_hud_class("character_" + code, "locked_character", not bUnlocked)
            self._set_hud_class(
                "character_" + code,
                "selected_character",
                bUnlocked and code == self.selected_character,
            )

    def _save_settings(self):
        temp_path = ""
        try:
            settings_path = HEngine.GetSavedPath(self.SETTINGS_CONFIG)
            settings_directory = os.path.dirname(settings_path)
            os.makedirs(settings_directory, exist_ok=True)
            temp_path = settings_path + ".tmp." + str(os.getpid())
            with open(temp_path, "w", encoding="utf-8", newline="\n") as config_file:
                config_file.write(
                    "{\n"
                    + '  "Language": "' + self.language + '",\n'
                    + '  "MasterVolume": ' + f"{self.master_volume:.1f}" + ",\n"
                    + '  "VSync": ' + ("true" if self.bVSyncEnabled else "false") + ",\n"
                    + '  "Fullscreen": ' + ("true" if self.bFullscreen else "false") + ",\n"
                    + '  "UIScale": ' + f"{self.ui_scale:.2f}" + ",\n"
                    + '  "MotionEnabled": ' + ("true" if self.bMotionEnabled else "false") + ",\n"
                    + '  "DamageFlashEnabled": ' + ("true" if self.bDamageFlashEnabled else "false") + ",\n"
                    + '  "ProjectileOpacity": ' + f"{self.player_projectile_opacity:.2f}" + ",\n"
                    + '  "ParticleDensity": "' + self.particle_density + '",\n'
                    + '  "DamageNumbers": "' + self.damage_numbers_mode + '",\n'
                    + '  "ScreenShake": ' + ("true" if self.bScreenShakeEnabled else "false") + ",\n"
                    + '  "TelegraphColor": "' + self.enemy_telegraph_color + '",\n'
                    + '  "AutoVisualThrottle": ' + ("true" if self.bAutoVisualThrottle else "false") + "\n"
                    + "}\n",
                )
                config_file.flush()
                os.fsync(config_file.fileno())
            os.replace(temp_path, settings_path)
        except (OSError, UnicodeError, ValueError, RuntimeError):
            HEngine.HE_CORE_WARN(
                "[SurvivorGame] Could not persist settings",
            )
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _apply_settings(self):
        HEngine.Settings.SetMasterVolume(self.master_volume)
        HEngine.Settings.SetVSync(self.bVSyncEnabled)
        self.bFullscreen = HEngine.Settings.SetFullscreen(self.bFullscreen)
        HEngine.Settings.SetUIScale(self.ui_scale)
        if self.document_id:
            self._set_hud_class("hud", "reduce_motion", not self.bMotionEnabled)
            self._set_hud_class("hud", "reduce_flash", not self.bDamageFlashEnabled)
            self._set_hud_class("hud", "screen_shake_off", not self.bScreenShakeEnabled)
            self._set_hud_class("hud", "damage_numbers_off", self.damage_numbers_mode == "off")
            self._set_hud_class("hud", "damage_numbers_reduced", self.damage_numbers_mode == "reduced")
            self._set_hud_class("hud", "particle_density_low", self.particle_density == "low")
            self._set_hud_class("hud", "low_particle", self.particle_density == "low")
            self._set_hud_class("hud", "telegraph_deuteranopia", self.enemy_telegraph_color == "deuteranopia")
            self._set_hud_class("hud", "auto_visual_throttle", self.bAutoVisualThrottle)
            if not self.bDamageFlashEnabled:
                self._set_hud_style("damage_flash", "opacity", "0")
            self._sync_settings_ui()
            self._refresh_hub_settings()

    def _sync_settings_ui(self):
        if not self.document_id:
            return

        self._set_hud_text("volume_value_label", str(int(round(self.master_volume * 100.0))) + "%")
        selected_options = {
            "language_zh": self.language == "zh_cn",
            "language_en": self.language == "en",
            "vsync_on": self.bVSyncEnabled,
            "vsync_off": not self.bVSyncEnabled,
            "display_fullscreen": self.bFullscreen,
            "display_windowed": not self.bFullscreen,
            "ui_scale_small": self.ui_scale < 0.93,
            "ui_scale_normal": 0.93 <= self.ui_scale <= 1.07,
            "ui_scale_large": self.ui_scale > 1.07,
            "motion_on": self.bMotionEnabled,
            "motion_off": not self.bMotionEnabled,
            "flash_on": self.bDamageFlashEnabled,
            "flash_off": not self.bDamageFlashEnabled,
            "particle_density_auto": self.particle_density == "auto",
            "particle_density_low": self.particle_density == "low",
            "particle_density_medium": self.particle_density == "medium",
            "particle_density_high": self.particle_density == "high",
            "damage_numbers_off": self.damage_numbers_mode == "off",
            "damage_numbers_reduced": self.damage_numbers_mode == "reduced",
            "damage_numbers_full": self.damage_numbers_mode == "full",
            "screen_shake_on": self.bScreenShakeEnabled,
            "screen_shake_off": not self.bScreenShakeEnabled,
            "telegraph_color_default": self.enemy_telegraph_color == "default",
            "telegraph_color_deuteranopia": self.enemy_telegraph_color == "deuteranopia",
            "telegraph_color_tritanopia": self.enemy_telegraph_color == "tritanopia",
            "telegraph_color_high_contrast": self.enemy_telegraph_color == "high_contrast",
            "auto_throttle_on": self.bAutoVisualThrottle,
            "auto_throttle_off": not self.bAutoVisualThrottle,
        }
        for element_id, bSelected in selected_options.items():
            self._set_hud_class(
                element_id,
                "selected_option",
                bSelected,
            )
        self._set_hud_text(
            "projectile_opacity_value_label",
            str(int(round(self.player_projectile_opacity * 100.0))) + "%",
        )

    def _set_master_volume(self, volume):
        self.master_volume = round(max(0.0, min(1.0, volume)) * 10.0) / 10.0
        HEngine.Settings.SetMasterVolume(self.master_volume)
        self._save_settings()
        self._sync_settings_ui()

    def _set_vsync(self, bEnabled):
        self.bVSyncEnabled = bEnabled
        HEngine.Settings.SetVSync(bEnabled)
        self._save_settings()
        self._sync_settings_ui()

    def _set_fullscreen(self, bEnabled):
        self.bFullscreen = HEngine.Settings.SetFullscreen(bEnabled)
        self._save_settings()
        self._sync_settings_ui()

    def _update_fullscreen_shortcut(self):
        alt_pressed = (
            HEngine.Input.IsKeyPressed(HEngine.KeyCode.LeftAlt)
            or HEngine.Input.IsKeyPressed(HEngine.KeyCode.RightAlt)
        )
        fullscreen_shortcut_pressed = (
            alt_pressed
            and HEngine.Input.IsKeyPressed(HEngine.KeyCode.Enter)
        )
        fullscreen_shortcut_triggered = (
            fullscreen_shortcut_pressed
            and not self.last_fullscreen_shortcut_pressed
        )
        self.last_fullscreen_shortcut_pressed = fullscreen_shortcut_pressed
        if fullscreen_shortcut_triggered:
            self._set_fullscreen(not self.bFullscreen)

    def _set_ui_scale(self, scale):
        self.ui_scale = max(0.85, min(1.15, scale))
        HEngine.Settings.SetUIScale(self.ui_scale)
        self._save_settings()
        self._sync_settings_ui()

    def _set_motion_enabled(self, bEnabled):
        self.bMotionEnabled = bEnabled
        self._set_hud_class("hud", "reduce_motion", not bEnabled)
        if not bEnabled:
            self.menu_animation_phase = False
            self._set_menu_sparkles(False)
        self._save_settings()
        self._sync_settings_ui()

    def _set_damage_flash_enabled(self, bEnabled):
        self.bDamageFlashEnabled = bEnabled
        if not bEnabled:
            self.damage_flash_timer = 0.0
            self._set_hud_style("damage_flash", "opacity", "0")
        self._save_settings()
        self._sync_settings_ui()

    def _restore_settings_defaults(self):
        self.language = self.DEFAULT_LANGUAGE
        self.master_volume = self.DEFAULT_MASTER_VOLUME
        self.bVSyncEnabled = self.DEFAULT_VSYNC
        self.bFullscreen = self.DEFAULT_FULLSCREEN
        self.ui_scale = self.DEFAULT_UI_SCALE
        self.bMotionEnabled = self.DEFAULT_MOTION_ENABLED
        self.bDamageFlashEnabled = self.DEFAULT_DAMAGE_FLASH_ENABLED
        self.player_projectile_opacity = self.DEFAULT_PROJECTILE_OPACITY
        self.particle_density = self.DEFAULT_PARTICLE_DENSITY
        self.damage_numbers_mode = self.DEFAULT_DAMAGE_NUMBERS
        self.bScreenShakeEnabled = self.DEFAULT_SCREEN_SHAKE
        self.enemy_telegraph_color = self.DEFAULT_TELEGRAPH_COLOR
        self.bAutoVisualThrottle = self.DEFAULT_AUTO_VISUAL_THROTTLE
        self._apply_settings()
        self._set_hud_class("hud", "reduce_motion", False)
        self._set_hud_class("hud", "reduce_flash", False)
        self.hud_cache.clear()
        self._apply_language()
        if self.bAwaitingUpgrade:
            self._refresh_upgrade_panel()
        if self.bGameOver:
            self._sync_game_over_text()
        if self.banner_key:
            self._set_hud_text("banner", self._text(self.banner_key))
        self._sync_hud()
        self._save_settings()

    def _apply_language(self):
        if not self.document_id:
            return

        static_text = {
            "score_label": "score_label",
            "timer_caption": "timer_caption",
            "region_objective_title": "region_objective_title",
            "domain_power_title": "domain_power_title",
            "controls_move": "controls_move",
            "controls_jump_key": "controls_jump_key",
            "controls_jump": "controls_jump",
            "controls_camera_key": "controls_camera_key",
            "controls_camera": "controls_camera",
            "controls_auto": "controls_auto",
            "boss_name": "boss_name",
            "hp_label": "health_label",
            "weapon_title": "weapon_title",
            "tome_title": "tome_title",
            "start_eyebrow": "start_eyebrow",
            "start_title": "start_title",
            "start_subtitle": "start_subtitle",
            "character_select_title": "character_select_title",
            "start_feature_magic_label": "start_feature_magic",
            "start_feature_cozy_label": "start_feature_cozy",
            "start_feature_growth_label": "start_feature_growth",
            "start_button_label": "start_button",
            "start_settings_button_label": "start_settings_button",
            "start_hint": "start_hint",
            "loading_eyebrow": "loading_eyebrow",
            "loading_title": "loading_title",
            "loading_subtitle": "loading_subtitle",
            "loading_hint": "loading_hint",
            "level_up_callout": "level_up",
            "upgrade_subtitle": "upgrade_subtitle",
            "upgrade_flavor": "upgrade_flavor",
            "upgrade_level_caption": "upgrade_level_caption",
            "choice_prompt_text": "choice_prompt",
            "upgrade_hint_mouse": "upgrade_hint_mouse",
            "pause_title": "pause_title",
            "pause_subtitle": "pause_subtitle",
            "resume_button_label": "resume_button",
            "pause_settings_button_label": "pause_settings_button",
            "pause_restart_button_label": "pause_restart_button",
            "pause_home_button_label": "pause_home_button",
            "pause_hint_text": "pause_hint_text",
            "settings_eyebrow": "settings_eyebrow",
            "settings_title": "settings_title",
            "settings_back_button_label": "settings_back_button",
            "settings_language_label": "settings_language_label",
            "settings_language_desc": "settings_language_desc",
            "settings_volume_label": "settings_volume_label",
            "settings_volume_desc": "settings_volume_desc",
            "settings_vsync_label": "settings_vsync_label",
            "settings_vsync_desc": "settings_vsync_desc",
            "settings_display_mode_label": "settings_display_mode_label",
            "settings_display_mode_desc": "settings_display_mode_desc",
            "settings_ui_scale_label": "settings_ui_scale_label",
            "settings_ui_scale_desc": "settings_ui_scale_desc",
            "settings_motion_label": "settings_motion_label",
            "settings_motion_desc": "settings_motion_desc",
            "settings_flash_label": "settings_flash_label",
            "settings_flash_desc": "settings_flash_desc",
            "language_zh_label": "language_zh",
            "language_en_label": "language_en",
            "vsync_on_label": "option_on",
            "vsync_off_label": "option_off",
            "display_fullscreen_label": "display_fullscreen",
            "display_windowed_label": "display_windowed",
            "ui_scale_small_label": "ui_scale_small",
            "ui_scale_normal_label": "ui_scale_normal",
            "ui_scale_large_label": "ui_scale_large",
            "motion_on_label": "option_on",
            "motion_off_label": "option_off",
            "flash_on_label": "option_on",
            "flash_off_label": "option_off",
            "settings_projectile_opacity_label": "settings_projectile_opacity_label",
            "settings_projectile_opacity_desc": "settings_projectile_opacity_desc",
            "settings_particle_density_label": "settings_particle_density_label",
            "settings_particle_density_desc": "settings_particle_density_desc",
            "particle_density_auto_label": "particle_density_auto",
            "particle_density_low_label": "particle_density_low",
            "particle_density_medium_label": "particle_density_medium",
            "particle_density_high_label": "particle_density_high",
            "settings_damage_numbers_label": "settings_damage_numbers_label",
            "settings_damage_numbers_desc": "settings_damage_numbers_desc",
            "damage_numbers_off_label": "damage_numbers_off",
            "damage_numbers_reduced_label": "damage_numbers_reduced",
            "damage_numbers_full_label": "damage_numbers_full",
            "settings_screen_shake_label": "settings_screen_shake_label",
            "settings_screen_shake_desc": "settings_screen_shake_desc",
            "screen_shake_on_label": "option_on",
            "screen_shake_off_label": "option_off",
            "settings_telegraph_color_label": "settings_telegraph_color_label",
            "settings_telegraph_color_desc": "settings_telegraph_color_desc",
            "telegraph_color_default_label": "telegraph_color_default",
            "telegraph_color_deuteranopia_label": "telegraph_color_deuteranopia",
            "telegraph_color_tritanopia_label": "telegraph_color_tritanopia",
            "telegraph_color_high_contrast_label": "telegraph_color_high_contrast",
            "settings_auto_throttle_label": "settings_auto_throttle_label",
            "settings_auto_throttle_desc": "settings_auto_throttle_desc",
            "auto_throttle_on_label": "option_on",
            "auto_throttle_off_label": "option_off",
            "settings_defaults_button_label": "settings_defaults_button",
            "settings_saved_hint": "settings_saved_hint",
            "game_over_title": "game_over_title",
            "game_over_subtitle": "game_over_subtitle",
            "restart_button_label": "restart_button",
            "game_over_home_button_label": "game_over_home_button",
            "restart_hint_text": "restart_hint_text",
            "final_score_label": "final_score_label",
            "final_kills_label": "final_kills_label",
            "final_level_label": "final_level_label",
        }
        for element_id, text_key in static_text.items():
            self._set_hud_text(element_id, self._text(text_key))
        for element_id, text_key in {
            "character_rotate_left": "character_rotate_left_aria",
            "character_rotate_right": "character_rotate_right_aria",
            "character_zoom_out": "character_zoom_out_aria",
            "character_zoom_in": "character_zoom_in_aria",
        }.items():
            self._set_hud_attribute(
                element_id, "aria-label", self._text(text_key),
            )
        self._refresh_character_roster()
        self._sync_settings_ui()
        self._refresh_hub()

    def _upgrade_text(self, choice):
        format_args = dict(choice.get("format_args", {}))
        if "target_bonus" in format_args:
            format_args["target_bonus"] = (
                self._text("upgrade_target_bonus")
                if format_args["target_bonus"] else ""
            )
        name = self._text(choice["name_key"])
        description = self._text(choice["description_key"], **format_args)
        return name, description

    def _refresh_upgrade_panel(self):
        if not self.document_id or not self.upgrade_choices:
            return

        self._set_hud_text(
            "upgrade_title",
            self._text("upgrade_title", level=self.level),
        )
        self._set_hud_text("upgrade_level_value", f"{self.level:02d}")
        for index, choice in enumerate(self.upgrade_choices):
            name, description = self._upgrade_text(choice)
            element_suffix = str(index + 1)
            bUnlock = choice.get("unlock", False)
            kind_key = (
                "upgrade_kind_weapon"
                if choice.get("kind") == "weapon" else
                "upgrade_kind_passive"
            )
            if bUnlock:
                rank_text = self._text("upgrade_rank_unlock")
            elif choice.get("kind") in ("weapon", "tome"):
                rank_text = self._text(
                    "upgrade_rank_level",
                    current=choice.get("current_level", 0),
                    next=choice.get("next_level", 1),
                )
            else:
                rank_text = self._text("upgrade_rank_permanent")
            rarity_key = (
                "rarity_new" if bUnlock else
                "rarity_rare" if choice["rare"] else
                "rarity_common"
            )

            self._set_hud_attribute(
                "upgrade_icon_image_" + element_suffix,
                "src",
                choice["icon"],
            )
            self._set_hud_text("upgrade_kind_" + element_suffix, self._text(kind_key))
            self._set_hud_text("upgrade_rank_" + element_suffix, rank_text)
            self._set_hud_text("upgrade_rarity_" + element_suffix, self._text(rarity_key))
            self._set_hud_text("upgrade_name_" + element_suffix, name)
            self._set_hud_text("upgrade_desc_" + element_suffix, description)
            self._set_hud_text(
                "upgrade_stat_" + element_suffix,
                self._text(choice["stat_key"]),
            )

            button_id = "upgrade_" + element_suffix
            self._set_hud_class(button_id, "rare", choice["rare"])
            self._set_hud_class(button_id, "unlock", bUnlock)
            icon_codes = WEAPON_ORDER + TOME_ORDER + ("snack", "bonus", "spark")
            for code in icon_codes:
                self._set_hud_class(
                    button_id,
                    "upgrade-" + code,
                    choice["code"] == code,
                )

        banish_key = (
            "upgrade_banish_confirm"
            if self.pending_banish_index == self.upgrade_selected_index
            and self.banish_confirm_timer > 0.0 else
            "upgrade_banish"
        )
        control_values = (
            ("upgrade_reroll", self._text("upgrade_reroll"), self.rerolls_remaining),
            ("upgrade_skip", self._text("upgrade_skip"), self.skips_remaining),
            ("upgrade_banish", self._text(banish_key), self.banishes_remaining),
        )
        for control_id, label, remaining in control_values:
            self._set_hud_text(control_id + "_label", label + " · " + str(remaining))
            self._set_hud_class(
                control_id + "_button", "disabled", remaining <= 0,
            )
        self._set_upgrade_selection(self.upgrade_selected_index)

    def _sync_game_over_text(self):
        self._set_hud_text("final_score_value", str(self.score))
        self._set_hud_text("final_kills_value", str(self.kills))
        self._set_hud_text("final_level_value", str(self.level))
        self._refresh_result_details()

    def _set_menu_sparkles(self, bBright):
        for element_id in ("start_sparkle_a", "start_sparkle_b", "start_sparkle_c"):
            self._set_hud_class(element_id, "twinkle", bBright)

    def _update_menu_animation(self, dt):
        if not self.bMotionEnabled or not self.bInMainMenu or self.bSettingsOpen:
            return

        self.menu_animation_timer -= dt
        if self.menu_animation_timer > 0.0:
            return
        self.menu_animation_timer = 0.75
        self.menu_animation_phase = not self.menu_animation_phase
        self._set_menu_sparkles(self.menu_animation_phase)

    def _show_start_menu(self):
        HEngine.SetRuntimePaused(True)
        HEngine.RuntimeResourceWarmup.QueueTrigger("MenuRoster")
        self.audio.reset_gameplay()
        self.audio.set_music_ducked(False)
        self.audio.play_music("menu")
        self.bInMainMenu = True
        self.bLoadingAdventure = False
        self.bSettingsOpen = False
        self.bPaused = False
        self.bGameOver = False
        self.bAwaitingUpgrade = False
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.0
        self.settings_return_screen = "start"
        self.menu_animation_timer = 0.05
        self.menu_animation_phase = False
        self._set_player_input_enabled(False)
        self.preview_character_id = self.selected_character
        self._set_player_menu_visible(False)
        if self.document_id:
            RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "block")
            RmlUI.SetStyle(self.document_id, "loading_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "loading_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "none")
            RmlUI.SetStyle(self.document_id, "upgrade_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "pause_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "game_over_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "start_panel", "display", "flex")
            RmlUI.SetMouseCursorVisible(self.document_id, True)
            if self.ui_motion:
                self.ui_motion.ResetToScreen("start")
                self.ui_motion.set_accessibility(
                    not self.bMotionEnabled,
                    not self.bDamageFlashEnabled,
                )
            self._show_hub_page("play")

    def _start_game(self):
        if (self.bInMainMenu and self.ui_motion and
                not self.ui_motion.IsTransitioning()):
            def on_motion(action, name, ticket):
                if action == "marker" and name == "switch":
                    self._start_game_now()
            self.ui_motion.PlayTransition(
                "start_to_loading",
                source="start",
                target="loading",
                operation="replace",
                callback=on_motion,
            )
            return
        self._start_game_now()

    def _start_game_now(self):
        if self.bLoadingAdventure:
            return
        if self.bMenuScene:
            challenge_selection = self.profile.get(
                "selectedChallenges",
                self.profile.get("selectedChallenge", "none"),
            )
            if not SurvivorSession.stage_launch(
                    self.selected_character,
                    self.profile.get("selectedDifficulty", "adventure"),
                    challenge_selection,
                    self.selected_run_seed):
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] A menu launch handoff is already pending",
                )
                return
            if not HEngine.RequestRuntimeScene(SurvivorSession.GAMEPLAY_SCENE):
                SurvivorSession.clear_launch()
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] Runtime scene request slot is busy",
                )
                return

            self.bSceneTransitionRequested = True
            self.bInMainMenu = False
            self.bLoadingAdventure = True
            self.bSettingsOpen = False
            self.settings_return_screen = "pause"
            self.warmup_display_progress = 0.05
            self._set_menu_preview_visible(False)
            self.audio.set_music_ducked(True)
            HEngine.SetRuntimePaused(True)
            if self.document_id:
                RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
                RmlUI.SetStyle(self.document_id, "loading_backdrop", "display", "block")
                RmlUI.SetStyle(self.document_id, "loading_panel", "display", "flex")
                RmlUI.SetStyle(self.document_id, "start_panel", "display", "none")
                RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
                RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "none")
                RmlUI.SetMouseCursorVisible(self.document_id, False)
                self._set_hud_style("loading_progress_fill", "width", "5%")
                self._set_hud_text("loading_status", self._text("loading_resources"))
                self._set_hud_text("loading_percent", "5%")
            HEngine.HE_CORE_INFO(
                "[SurvivorGame] menu requested gameplay scene",
            )
            return
        if self._has_uncommitted_run():
            if self.bGameOver and getattr(self, "run_end_reason", ""):
                end_reason = self.run_end_reason
            elif self.bInMainMenu:
                end_reason = "abandon"
            else:
                end_reason = "restart"
            receipt = self._finish_run(end_reason)
            if receipt["status"] not in ("committed", "already_committed"):
                if self.bInMainMenu:
                    self._show_start_menu()
                return
        if not self._begin_run_transaction():
            if self.bInMainMenu:
                self._show_start_menu()
            return
        # Always build the run from the currently confirmed character. The
        # title screen may have changed the preview after the previous reset;
        # skipping this reset mixed the new model with the old starter weapon
        # and passive on the first adventure.
        self._reset_run()
        self.bSceneTransitionRequested = False
        self._set_menu_preview_visible(False)
        self._set_player_menu_visible(True)
        HEngine.RuntimeResourceWarmup.QueueTrigger("AdventureCore")
        HEngine.RuntimeResourceWarmup.QueueTrigger("Wave00")
        HEngine.RuntimeResourceWarmup.QueueTrigger("Wave01")
        HEngine.RuntimeResourceWarmup.QueueTrigger("RegionFoundations")
        HEngine.RuntimeResourceWarmup.QueueTrigger("WeaponPool")
        self.warmup_display_progress = 0.02
        self.audio.reset_gameplay()
        HEngine.SetRuntimePaused(True)
        self.audio.set_music_ducked(True)
        self.bInMainMenu = False
        self.bLoadingAdventure = True
        self.bSettingsOpen = False
        self.settings_return_screen = "pause"
        self._set_player_input_enabled(False)
        if self.document_id:
            RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "loading_backdrop", "display", "block")
            RmlUI.SetStyle(self.document_id, "loading_panel", "display", "flex")
            RmlUI.SetStyle(self.document_id, "start_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "none")
            RmlUI.SetMouseCursorVisible(self.document_id, False)
        self._sync_loading_ui()

    def _complete_adventure_start(self):
        if not self.bLoadingAdventure or not self.bRuntimeReady:
            return
        self.bLoadingAdventure = False
        self.audio.reset_gameplay()
        self.audio.set_music_ducked(False)
        self.audio.play_music("gameplay")
        self._set_player_input_enabled(True)
        if self.document_id:
            RmlUI.SetStyle(self.document_id, "loading_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "loading_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "block")
            RmlUI.SetMouseCursorVisible(self.document_id, False)
            if self.ui_motion:
                self.ui_motion.ResetToScreen("gameplay")
        HEngine.SetRuntimePaused(False)
        HEngine.HE_CORE_INFO("[SurvivorGame] adventure started after warm-up")

    def _sync_loading_ui(self):
        if not self.document_id:
            return
        progress, status_key = self._runtime_warmup_progress()
        self.warmup_display_progress = max(
            self.warmup_display_progress,
            min(1.0, progress),
        )
        if status_key == "loading_ready" and self.warmup_display_progress < 0.94:
            status_key = "loading_resources"
        percent = int(round(self.warmup_display_progress * 100.0))
        self._set_hud_style(
            "loading_progress_fill",
            "width",
            str(percent) + "%",
        )
        self._set_hud_text("loading_status", self._text(status_key))
        self._set_hud_text("loading_percent", str(percent) + "%")

    def _return_to_start_menu(self, end_reason="return_hub"):
        if self._has_uncommitted_run():
            if self.bGameOver and getattr(self, "run_end_reason", ""):
                end_reason = self.run_end_reason
            receipt = self._finish_run(end_reason)
            if receipt["status"] not in ("committed", "already_committed"):
                return False
        if not self.bMenuScene:
            if self.bSceneTransitionRequested:
                return True
            SurvivorSession.clear_launch()
            if not HEngine.RequestRuntimeScene(SurvivorSession.MAIN_MENU_SCENE):
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] Runtime scene request slot is busy",
                )
                return False
            self.bSceneTransitionRequested = True
            self.bLoadingAdventure = True
            self.bPaused = False
            self.bSettingsOpen = False
            self._set_player_input_enabled(False)
            HEngine.SetRuntimePaused(True)
            if self.document_id:
                RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
                RmlUI.SetStyle(self.document_id, "loading_backdrop", "display", "block")
                RmlUI.SetStyle(self.document_id, "loading_panel", "display", "flex")
                RmlUI.SetStyle(self.document_id, "start_panel", "display", "none")
                RmlUI.SetStyle(self.document_id, "pause_panel", "display", "none")
                RmlUI.SetStyle(self.document_id, "game_over_panel", "display", "none")
                RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "none")
                RmlUI.SetMouseCursorVisible(self.document_id, False)
                self._set_hud_style("loading_progress_fill", "width", "5%")
                self._set_hud_text("loading_status", self._text("loading_resources"))
                self._set_hud_text("loading_percent", "5%")
            HEngine.HE_CORE_INFO(
                "[SurvivorGame] gameplay requested menu scene",
            )
            return True
        self._reset_run()
        self._show_start_menu()
        return True

    def _abandon_run(self):
        return self._return_to_start_menu("abandon")

    def _open_settings(self, return_screen):
        if self.bSettingsOpen:
            return
        self.bSettingsOpen = True
        self.settings_return_screen = return_screen
        if return_screen == "pause":
            self.bPaused = True
        else:
            self.bInMainMenu = True
        self._set_player_input_enabled(False)
        if self.document_id:
            if self.ui_screens:
                self.ui_screens.ShowModal("settings", "modal_enter")
                RmlUI.SetMouseCursorVisible(self.document_id, True)
                self._sync_settings_ui()
                return
            RmlUI.SetStyle(
                self.document_id,
                "title_backdrop",
                "display",
                "block" if return_screen == "start" else "none",
            )
            RmlUI.SetStyle(self.document_id, "start_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "pause_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "flex")
            RmlUI.SetMouseCursorVisible(self.document_id, True)
            self._sync_settings_ui()

    def _close_settings(self):
        if not self.bSettingsOpen:
            return
        if self.document_id:
            if self.ui_screens:
                def on_motion(action, name, ticket):
                    if action == "marker" and name == "switch":
                        self.bSettingsOpen = False
                self.ui_screens.CloseModal("modal_exit", on_motion)
                return
            self.bSettingsOpen = False
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            if self.settings_return_screen == "pause":
                RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
                RmlUI.SetStyle(self.document_id, "pause_panel", "display", "flex")
            else:
                RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "block")
                RmlUI.SetStyle(self.document_id, "start_panel", "display", "flex")
            RmlUI.SetMouseCursorVisible(self.document_id, True)

    def _set_paused(self, bPaused):
        if bPaused and (self.bAwaitingUpgrade or self.bGameOver or self.bInMainMenu):
            return

        if (not bPaused and self.bPaused and self.document_id and
                self.ui_motion and self.ui_screens):
            def on_motion(action, name, ticket):
                if action == "marker" and name == "switch":
                    self._set_paused_now(False)
            self.ui_motion.PlayTransition(
                "modal_exit",
                source="pause",
                target="gameplay",
                operation="pop",
                callback=on_motion,
            )
            return
        self._set_paused_now(bPaused)

    def _set_paused_now(self, bPaused):
        self.bPaused = bPaused
        HEngine.SetRuntimePaused(bPaused)
        self.audio.set_music_ducked(bPaused)
        if not bPaused:
            self.bSettingsOpen = False
        self._set_player_input_enabled(not bPaused)
        if self.document_id:
            if bPaused and self.ui_screens:
                self.ui_screens.ShowModal("pause", "modal_enter")
                RmlUI.SetMouseCursorVisible(self.document_id, True)
                return
            RmlUI.SetMouseCursorVisible(self.document_id, bPaused)
            RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            RmlUI.SetStyle(
                self.document_id,
                "pause_panel",
                "display",
                "flex" if bPaused else "none",
            )

    def _finish_run(self, end_reason):
        if end_reason not in (
                "death", "victory", "abandon", "restart", "return_hub"):
            raise ValueError("unknown Survivor run end reason: " + str(end_reason))
        if self.quest_tracker is not None:
            self.quest_tracker.record(
                "survival_seconds", self.elapsed, bSet=True,
            )
            if end_reason == "victory":
                run_config = getattr(self, "run_config", None)
                difficulty_id = (
                    run_config.selected_difficulty
                    if run_config is not None else
                    self.profile.get("selectedDifficulty", "adventure")
                )
                self.quest_tracker.record(
                    "difficulty_clear",
                    1,
                    {
                        "difficulty": difficulty_id,
                        "tome": "curse" if self._tome_level("curse") > 0 else "",
                    },
                )
                challenge_ids = (
                    run_config.challenge_ids
                    if run_config is not None else
                    tuple(self.profile.get("selectedChallenges", ()))
                )
                for challenge_id in challenge_ids:
                    self.quest_tracker.record(
                        "challenge_clear", 1, {"challenge": challenge_id},
                    )
            self.quest_tracker.flush()
        self.telemetry.write(self, end_reason)
        bShowResult = end_reason in ("death", "victory")
        if self.bGameOver:
            if self._has_uncommitted_run():
                return self._record_run_progress(
                    getattr(self, "run_end_reason", end_reason),
                )
            return self._record_run_progress(end_reason)
        if not bShowResult:
            receipt = self._record_run_progress(end_reason)
            HEngine.HE_CORE_INFO(
                "[SurvivorGame] run ended reason=" + end_reason
                + " score=" + str(self.score)
                + " profile=" + receipt["status"],
            )
            return receipt

        HEngine.SetRuntimePaused(True)
        self.audio.set_music_ducked(True)
        self.audio.post("game_over")
        self.bGameOver = True
        self.bAwaitingUpgrade = False
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.0
        self.bPaused = False
        self.bSettingsOpen = False
        self.run_end_reason = end_reason
        self._set_player_input_enabled(False)
        receipt = self._record_run_progress(end_reason)
        if receipt.get("status") == "committed":
            self.audio.post("gold_settlement")
        bUnlockedCharacter = receipt.get("newCharacterEligible", False)
        if self.document_id:
            self._set_hud_class("upgrade_panel", "hover_enabled", False)
            RmlUI.SetMouseCursorVisible(self.document_id, True)
            RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "upgrade_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "pause_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            if self.ui_screens:
                self.ui_screens.ShowModal("game_over", "modal_enter")
            else:
                RmlUI.SetStyle(self.document_id, "game_over_panel", "display", "flex")
            self._sync_game_over_text()
            if bUnlockedCharacter:
                self.banner_key = "character_unlock_banner"
                self.audio.post("new_unlock")
        HEngine.HE_CORE_INFO(
            "[SurvivorGame] run ended reason=" + end_reason
            + " score=" + str(self.score)
            + " profile=" + receipt["status"],
        )
        return receipt

    def _game_over(self, end_reason="death"):
        return self._finish_run(end_reason)

    def _victory(self):
        return self._finish_run("victory")

    def _sync_hud(self):
        if not self.document_id:
            return

        minutes = int(self.elapsed // 60)
        seconds = int(self.elapsed % 60)
        hp_fraction = max(0.0, min(1.0, self.health / self.max_health))
        xp_fraction = max(0.0, min(1.0, self.experience / float(self.experience_to_level)))
        if self.bAwaitingUpgrade:
            xp_fraction = 1.0
        alive_count = sum(1 for monster in self.monsters if not monster["dead"])

        self._set_hud_text("timer", f"{minutes:02d}:{seconds:02d}")
        self._set_hud_text("level", self._text("level", level=self.level))
        self._set_hud_text("kills", self._text("kills", count=self.kills))
        self._set_hud_text("score", f"{self.score:06d}")
        self._set_hud_text("hp_text", f"{int(self.health)} / {int(self.max_health)}")
        self._set_hud_text("enemy_count", self._text("enemy_count", count=alive_count))
        self._set_hud_text(
            "xp_label",
            (
                self._text("experience_ready", level=self.level)
                if self.bAwaitingUpgrade else
                self._text(
                    "experience",
                    current=int(self.experience),
                    required=self.experience_to_level,
                    percent=int(round(xp_fraction * 100.0)),
                )
            ),
        )
        self._set_hud_text(
            "shard_count",
            self._text("shards", count=int(self.collected_shards)),
        )
        self._sync_loadout_hud()
        self._sync_objective_hud(self.player.GetComponent("Transform").Translation)
        self._set_hud_style("hp_fill", "width", f"{hp_fraction * 100.0:.2f}%")
        self._set_hud_style("xp_fill", "width", f"{xp_fraction * 100.0:.2f}%")
        self._set_hud_class("bottom_hud", "low_health", hp_fraction <= 0.30)
        self._set_hud_style(
            "xp_flash",
            "opacity",
            "1" if self.bAwaitingUpgrade or self.level_up_flash_timer > 0.0 else "0",
        )
        self._set_hud_style("banner", "opacity", "1" if self.banner_timer > 0.0 else "0")
        self._set_hud_style(
            "damage_flash",
            "opacity",
            "1" if self.bDamageFlashEnabled and self.damage_flash_timer > 0.0 else "0",
        )

        boss = None
        for monster in self.monsters:
            if monster["boss"] and not monster["dead"]:
                boss = monster
                break
        if boss is None:
            self._set_hud_style("boss_panel", "display", "none")
        else:
            boss_fraction = max(0.0, min(1.0, boss["health"] / boss["max_health"]))
            self._set_hud_style("boss_panel", "display", "block")
            self._set_hud_text(
                "boss_name",
                boss.get("display_names", {}).get(
                    self.language, boss["display_name"],
                ),
            )
            self._set_hud_style("boss_fill", "width", f"{boss_fraction * 100.0:.2f}%")
            self._set_hud_text("boss_hp", str(int(max(0.0, boss["health"]))))

    def _sync_loadout_hud(self):
        slot_limit = max(3, min(
            MAX_WEAPON_SLOTS,
            int(getattr(self, "weapon_slot_limit", 3)),
        ))
        for slot_index in range(MAX_WEAPON_SLOTS):
            suffix = str(slot_index + 1)
            bLocked = slot_index >= slot_limit
            bEmpty = not bLocked and slot_index >= len(self.weapon_slots)
            bEquipped = not bLocked and not bEmpty
            self._set_hud_class("weapon_slot_" + suffix, "locked", bLocked)
            self._set_hud_class("weapon_slot_" + suffix, "empty", bEmpty)
            self._set_hud_class("weapon_slot_" + suffix, "equipped", bEquipped)
            if bLocked:
                self._set_hud_text("weapon_name_" + suffix, self._text("locked"))
                self._set_hud_text("weapon_value_" + suffix, "")
                continue
            if bEmpty:
                self._set_hud_text("weapon_name_" + suffix, "")
                self._set_hud_text("weapon_value_" + suffix, "")
                continue

            weapon_code = self.weapon_slots[slot_index]
            definition = WEAPON_DEFS[weapon_code]
            evolution_id = self.active_evolutions.get(weapon_code)
            evolution = EVOLUTION_BY_ID.get(evolution_id)
            self._set_hud_attribute(
                "weapon_icon_" + suffix,
                "src",
                evolution["icon"] if evolution else definition["icon"],
            )
            self._set_hud_text(
                "weapon_name_" + suffix,
                (
                    self._localized_catalog_text(evolution["name"])
                    if evolution else
                    self._text(definition["name_key"])
                ),
            )
            self._set_hud_text(
                "weapon_value_" + suffix,
                (
                    self._text("weapon_evolved_value") if evolution else
                    self._text(
                        "weapon_level_value",
                        level=self._weapon_level(weapon_code),
                    )
                ),
            )

        for slot_index in range(MAX_TOME_SLOTS):
            suffix = str(slot_index + 1)
            bEmpty = slot_index >= len(self.tome_slots)
            self._set_hud_class("tome_slot_" + suffix, "empty", bEmpty)
            if bEmpty:
                self._set_hud_text("tome_value_" + suffix, "")
                continue

            tome_code = self.tome_slots[slot_index]
            definition = TOME_DEFS[tome_code]
            self._set_hud_attribute(
                "tome_icon_" + suffix,
                "src",
                definition["icon"],
            )
            self._set_hud_text(
                "tome_value_" + suffix,
                self._text(
                    "tome_level_value",
                    level=self._tome_level(tome_code),
                ),
            )

    def _set_hud_text(self, element_id, value):
        cache_key = ("text", element_id)
        if self.hud_cache.get(cache_key) == value:
            return
        RmlUI.SetText(self.document_id, element_id, value)
        self.hud_cache[cache_key] = value

    def _set_hud_attribute(self, element_id, attribute_name, value):
        cache_key = ("attribute", element_id, attribute_name)
        if self.hud_cache.get(cache_key) == value:
            return
        RmlUI.SetAttribute(self.document_id, element_id, attribute_name, value)
        self.hud_cache[cache_key] = value

    def _set_hud_style(self, element_id, property_name, value):
        cache_key = ("style", element_id, property_name)
        if self.hud_cache.get(cache_key) == value:
            return
        RmlUI.SetStyle(self.document_id, element_id, property_name, value)
        self.hud_cache[cache_key] = value

    def _set_hud_class(self, element_id, class_name, bEnabled):
        cache_key = ("class", element_id, class_name)
        if self.hud_cache.get(cache_key) == bEnabled:
            return
        RmlUI.SetClass(self.document_id, element_id, class_name, bEnabled)
        self.hud_cache[cache_key] = bEnabled
