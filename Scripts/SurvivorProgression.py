import os

import HEngine

from SurvivorBuildRules import EvolutionResolver, UpgradePoolController
from SurvivorCatalogItems import (
    EVOLUTIONS as CATALOG_EVOLUTIONS,
    TOMES as CATALOG_TOMES,
    TRINKETS as CATALOG_TRINKETS,
    WEAPONS as CATALOG_WEAPONS,
)
from SurvivorContent import (
    CHARACTER_DEFS,
    MAX_TOME_SLOTS,
    MAX_WEAPON_SLOTS,
    TOME_DEFS,
    TOME_ORDER,
    WEAPON_DEFS,
    WEAPON_ORDER,
)
from SurvivorRegionObjectives import DOMAIN_POWER_IDS


RmlUI = HEngine.RmlUI


class SurvivorProgressionMixin:
    def _add_experience(self, amount):
        growth_multiplier = (
            1.0 + self._tome_level("growth") * 0.07
        ) * getattr(self, "character_xp_multiplier", 1.0)
        run_config = getattr(self, "run_config", None)
        challenge_xp = (
            run_config.challenge_tuning_for_world_minute(
                min(15, int(getattr(self, "elapsed", 0.0) // 60.0)),
            )["xp"]
            if run_config is not None else
            self._challenge_tuning()["xp"]
        )
        growth_multiplier *= challenge_xp * (
            1.0 + self._tome_level("curse") * 0.08
        )
        self.experience += amount * growth_multiplier
        self._try_level_up()

    @staticmethod
    def _experience_requirement(level):
        # Keep the Vampire Survivors-style slopes, but omit its level 20/40
        # spikes because this game has no temporary Growth compensation.
        if level <= 1:
            return 5
        if level <= 20:
            return level * 10 - 5
        if level <= 40:
            return 195 + (level - 20) * 13
        return 455 + (level - 40) * 16

    def _try_level_up(self):
        if self.bAwaitingUpgrade or self.experience < self.experience_to_level:
            return

        self.experience -= self.experience_to_level
        self.level += 1
        self.experience_to_level = self._experience_requirement(self.level)
        if self.quest_tracker is not None:
            self.quest_tracker.record("best_level", self.level, bSet=True)
        self._dispatch_combat_hook("level", {"level": self.level})
        self._begin_upgrade()

    def _begin_upgrade(self):
        # Build the complete choice payload before pausing the level. Content
        # mistakes must never strand the player in a paused state with no cards.
        upgrade_choices = self._roll_upgrade_choices()

        HEngine.SetRuntimePaused(True)
        self.audio.set_music_ducked(True)
        self.audio.post("level_up")
        self.bAwaitingUpgrade = True
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.15
        self.level_up_flash_timer = 1.0
        self._set_player_input_enabled(False)
        self.upgrade_choices = upgrade_choices
        self.upgrade_selected_index = -1
        if self.document_id:
            self._set_hud_class("upgrade_panel", "hover_enabled", False)
            self._refresh_upgrade_panel()
            if self.ui_screens:
                self.ui_screens.ShowModal("upgrade", "modal_enter")
            else:
                RmlUI.SetStyle(self.document_id, "upgrade_panel", "display", "flex")
            RmlUI.SetMouseCursorVisible(self.document_id, True)

        if (
                os.environ.get("HE_SURVIVOR_AUTOPLAY", "0") == "1"
                and self.upgrade_choices):
            self._select_upgrade(0)

    def _weapon_level(self, weapon_code):
        return getattr(self, weapon_code + "_level", 0)

    def _set_weapon_level(self, weapon_code, level):
        setattr(self, weapon_code + "_level", level)

    def _tome_level(self, tome_code):
        return self.tome_levels.get(tome_code, 0)

    def _roll_upgrade_choices(self):
        profile = getattr(self, "profile", {})
        owned = profile.get("owned", {})
        owned_weapons = set(owned.get("weapons", WEAPON_ORDER))
        owned_tomes = set(owned.get("tomes", TOME_ORDER))
        starter_weapon = CHARACTER_DEFS[self.selected_character]["weapon"]
        owned_weapons.add(starter_weapon)
        disabled = profile.get("poolDisabled", {})
        enabled = {
            "weapons": owned_weapons - set(disabled.get("weapons", ())),
            "tomes": owned_tomes - set(disabled.get("tomes", ())),
        }
        enabled["weapons"].add(starter_weapon)
        controller = UpgradePoolController(
            CATALOG_WEAPONS,
            CATALOG_TOMES,
            {"weapons": owned_weapons, "tomes": owned_tomes},
            enabled,
            {code: self._weapon_level(code) for code in WEAPON_ORDER},
            self.tome_levels,
            self.weapon_slots,
            self.tome_slots,
            getattr(self, "weapon_slot_limit", MAX_WEAPON_SLOTS),
            MAX_TOME_SLOTS,
            self.random_state,
            getattr(self, "rerolls_remaining", 0),
            getattr(self, "skips_remaining", 0),
            getattr(self, "banishes_remaining", 0),
            getattr(self, "run_banished", ()),
            excluded_ids=DOMAIN_POWER_IDS,
        )
        rows = controller.roll(3)
        self.random_state = controller.rng.state
        self._active_upgrade_pool = controller
        choices = []
        fallback_definitions = {
            "snack": ("vitality", "upgrade_snack_name", "upgrade_snack_desc", "upgrade_snack_stat", False),
            "bonus": ("fortune", "upgrade_bonus_name", "upgrade_bonus_desc", "upgrade_bonus_stat", True),
            "spark": ("growth", "upgrade_spark_name", "upgrade_spark_desc", "upgrade_spark_stat", True),
        }
        for row in rows:
            code = row["id"]
            if code in DOMAIN_POWER_IDS:
                raise RuntimeError(
                    "DomainPower entered the normal upgrade pool: " + code,
                )
            if row["kind"] == "fallback":
                icon_code, name_key, desc_key, stat_key, bRare = fallback_definitions[code]
                choices.append({
                    "code": code,
                    "icon": TOME_DEFS[icon_code]["icon"],
                    "name_key": name_key,
                    "description_key": desc_key,
                    "stat_key": stat_key,
                    "kind": "passive",
                    "rare": bRare,
                })
                continue
            bWeapon = row["kind"] == "weapon"
            definition = WEAPON_DEFS[code] if bWeapon else TOME_DEFS[code]
            bUnlock = row["unlock"]
            choice = {
                "code": code,
                "icon": definition["icon"],
                "name_key": (
                    definition["unlock_name_key" if bUnlock else "upgrade_name_key"]
                    if bWeapon else definition["name_key"]
                ),
                "description_key": (
                    definition["unlock_desc_key" if bUnlock else "upgrade_desc_key"]
                    if bWeapon else definition["description_key"]
                ),
                "stat_key": (
                    definition["unlock_stat_key" if bUnlock else "upgrade_stat_key"]
                    if bWeapon else definition["stat_key"]
                ),
                "kind": row["kind"],
                "current_level": row["currentLevel"],
                "next_level": row["nextLevel"],
                "unlock": bUnlock,
                "format_args": {"level": row["nextLevel"], "target_bonus": False},
                "rare": row["nextLevel"] in (5, 7, 10),
            }
            choices.append(choice)
        return choices

    def _set_upgrade_selection(self, index):
        if not self.bAwaitingUpgrade or not self.upgrade_choices:
            return

        self.upgrade_selected_index = (
            index if 0 <= index < len(self.upgrade_choices) else -1
        )
        for choice_index in range(3):
            self._set_hud_class(
                "upgrade_" + str(choice_index + 1),
                "selected",
                choice_index == self.upgrade_selected_index,
            )

    def _reroll_upgrade(self):
        if not self.bAwaitingUpgrade or self.rerolls_remaining <= 0:
            return False
        self.rerolls_remaining -= 1
        self.upgrade_choices = self._roll_upgrade_choices()
        self.upgrade_selected_index = -1
        self._refresh_upgrade_panel()
        return True

    def _skip_upgrade(self):
        if not self.bAwaitingUpgrade or self.skips_remaining <= 0:
            return False
        self.skips_remaining -= 1
        refund = max(1.0, self.experience_to_level * 0.25)
        self.experience += refund
        self._finish_upgrade("upgrade_skip_name")
        return True

    def _banish_upgrade(self, index):
        if (
                not self.bAwaitingUpgrade
                or self.banishes_remaining <= 0
                or index < 0
                or index >= len(self.upgrade_choices)):
            return False
        choice = self.upgrade_choices[index]
        if choice.get("current_level", 0) > 0 or choice["kind"] == "passive":
            return False
        self.banishes_remaining -= 1
        self.run_banished.add(choice["code"])
        self.upgrade_choices = self._roll_upgrade_choices()
        self.upgrade_selected_index = -1
        self._refresh_upgrade_panel()
        return True

    def _select_upgrade(self, index):
        if not self.bAwaitingUpgrade or index < 0 or index >= len(self.upgrade_choices):
            return

        choice = self.upgrade_choices[index]
        code = choice["code"]
        if choice["kind"] == "weapon":
            definition = WEAPON_DEFS[code]
            bNewWeapon = code not in self.weapon_slots
            self._set_weapon_level(
                code,
                min(definition["max_level"], self._weapon_level(code) + 1),
            )
            if bNewWeapon:
                self.weapon_slots.append(code)
                body_effect = definition["bodyVfx"]
                if body_effect and not HEngine.VFX.LoadEffect(body_effect):
                    HEngine.HE_CORE_WARN(
                        "[SurvivorVFX] failed to preload unlocked weapon "
                        + body_effect,
                    )
            timer_name = code + "_timer"
            setattr(self, timer_name, min(getattr(self, timer_name), 0.12))
            if self._weapon_level(code) == definition["max_level"]:
                self._dispatch_combat_hook(
                    "item_maxed", {"kind": "weapon", "id": code},
                )
        elif choice["kind"] == "tome":
            definition = TOME_DEFS[code]
            previous_level = self._tome_level(code)
            self.tome_levels[code] = min(
                definition["max_level"],
                self._tome_level(code) + 1,
            )
            if code not in self.tome_slots:
                self.tome_slots.append(code)
            self._recompute_tome_stats(
                bVitalityLevel=(code == "vitality" and previous_level < self.tome_levels[code]),
            )
            if self._tome_level(code) == definition["max_level"]:
                self._dispatch_combat_hook(
                    "item_maxed", {"kind": "tome", "id": code},
                )
        elif code == "snack":
            self.health = min(self.max_health, self.health + self.max_health * 0.35)
        elif code == "bonus":
            self.score += 750
        elif code == "spark":
            self.max_health += 12.0
            self.health = min(self.max_health, self.health + 12.0)
            self.crit_chance = min(0.50, self.crit_chance + 0.01)

        self._recompute_friendship_pin()
        self._finish_upgrade(choice["name_key"])

    def _recompute_tome_stats(self, bVitalityLevel=False):
        previous_max_health = self.max_health
        vitality_level = self._tome_level("vitality")
        self.max_health = self.base_character_max_health * (
            1.0 + vitality_level * 0.08
        )
        if bVitalityLevel:
            self.health = min(
                self.max_health,
                self.health + self.max_health * 0.08,
            )
        else:
            self.health = min(
                self.max_health,
                self.health * self.max_health / max(1.0, previous_max_health),
            )
        self.magnet_range = self.base_character_magnet_range * (
            1.0 + self._tome_level("magnet") * 0.18
        )
        self.damage_reduction = min(
            0.55,
            self.base_character_damage_reduction
            + self._tome_level("guard") * 0.06,
        )
        self.crit_chance = min(
            0.50,
            self.base_character_crit_chance
            + self._tome_level("fortune") * 0.03,
        )
        self.crit_multiplier = 2.0 + self._tome_level("fortune") * 0.08
        self.recovery_per_second = (
            self.base_character_recovery_per_second
            + self._tome_level("recovery") * 0.20
        )
        self.thorns = self.base_character_thorns + self._tome_level("thorns") * 6.0
        self.tome_gold_multiplier = 1.0 + self._tome_level("greed") * 0.08
        self.status_multiplier = 1.0 + self._tome_level("status") * 0.10
        self.curse_level = self._tome_level("curse")

    def _resolve_boss_chest(self, chest_tier):
        discovered = self.profile.get("discoveredEvolutions", [])
        base_slots = [
            next(
                (
                    base_id
                    for base_id, evolution_id in self.active_evolutions.items()
                    if evolution_id == slot_id
                ),
                slot_id,
            )
            for slot_id in self.weapon_slots
        ]
        resolver = EvolutionResolver(
            CATALOG_EVOLUTIONS,
            {code: self._weapon_level(code) for code in WEAPON_ORDER},
            self.tome_levels,
            base_slots,
            discovered,
        )
        evolution_result = resolver.resolve_chest(int(chest_tier))
        if evolution_result["evolutions"]:
            for evolution_id in evolution_result["evolutions"]:
                recipe = next(
                    entry for entry in CATALOG_EVOLUTIONS
                    if entry["id"] == evolution_id
                )
                base_id = recipe["weaponId"]
                self.active_evolutions[base_id] = evolution_id
                self.evolution_times[evolution_id] = self.elapsed
                setattr(self, base_id + "_timer", 0.0)
            self.profile["discoveredEvolutions"] = list(
                evolution_result["discovered"],
            )
            self._save_progression()
            if self.quest_tracker is not None:
                self.quest_tracker.record(
                    "evolutions_in_run",
                    len(self.active_evolutions),
                    bSet=True,
                )
                self.quest_tracker.record("evolutions", len(evolution_result["evolutions"]))
            self.audio.post("level_up")
            return {
                "kind": "evolution",
                "ids": evolution_result["evolutions"],
            }

        run_config = getattr(self, "run_config", None)
        bDisableTrinkets = (
            bool(run_config.challenge_tuning_for_world_minute(0)["disableTrinkets"])
            if run_config is not None else
            bool(self._challenge_tuning()["disableTrinkets"])
        )
        if not bDisableTrinkets and len(self.trinket_slots) < 4:
            owned = set(self.profile.get("owned", {}).get("trinkets", ()))
            disabled = set(
                self.profile.get("poolDisabled", {}).get("trinkets", ()),
            )
            available = [
                entry["id"] for entry in CATALOG_TRINKETS
                if entry["id"] in owned
                and entry["id"] not in disabled
                and entry["id"] not in self.trinket_slots
            ]
            if available:
                index = min(
                    len(available) - 1,
                    int(self._random_uniform(0.0, float(len(available)))),
                )
                trinket_id = available[index]
                self._equip_trinket(trinket_id)
                if self.quest_tracker is not None:
                    self.quest_tracker.record("chests_opened", 1)
                return {"kind": "trinket", "ids": (trinket_id,)}

        upgrade_candidates = []
        for weapon_id in base_slots:
            if weapon_id in WEAPON_DEFS:
                level = self._weapon_level(weapon_id)
                if level < WEAPON_DEFS[weapon_id]["max_level"]:
                    upgrade_candidates.append((level, "weapon", weapon_id))
        for tome_id in self.tome_slots:
            level = self._tome_level(tome_id)
            if level < TOME_DEFS[tome_id]["max_level"]:
                upgrade_candidates.append((level, "tome", tome_id))
        if upgrade_candidates:
            _, kind, content_id = min(upgrade_candidates)
            if kind == "weapon":
                self._set_weapon_level(content_id, self._weapon_level(content_id) + 1)
            else:
                self.tome_levels[content_id] += 1
                self._recompute_tome_stats()
            return {"kind": "upgrade", "ids": (content_id,)}

        gold = 12 + int(chest_tier) * 8
        if "boss_bell" in self.trinket_slots:
            gold = int(gold * 1.20)
        self.run_gold += gold
        return {"kind": "gold", "gold": gold, "ids": ()}

    def _finish_upgrade(self, banner_key):
        if not self.bAwaitingUpgrade:
            return

        # Deterministic Agent/autoplay sessions cannot wait on a UI-motion
        # callback while gameplay is paused.  Apply the already selected card
        # immediately so long-running capture and profiler recipes keep making
        # raw-gameplay progress.
        if os.environ.get("HE_SURVIVOR_AUTOPLAY", "0") == "1":
            self._finish_upgrade_now(banner_key)
            return

        if self.document_id and self.ui_motion and self.ui_screens:
            def on_motion(action, name, ticket):
                if action == "marker" and name == "switch":
                    self._finish_upgrade_now(banner_key)
            self.ui_screens.CloseModal("modal_confirm_exit", on_motion)
            return

        self._finish_upgrade_now(banner_key)

    def _finish_upgrade_now(self, banner_key):
        if not self.bAwaitingUpgrade:
            return

        self.bAwaitingUpgrade = False
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.0
        self.audio.post("ui_confirm")
        self.audio.set_music_ducked(False)
        HEngine.SetRuntimePaused(False)
        self._set_player_input_enabled(True)
        self.banner_timer = 2.2
        self.banner_key = banner_key
        self.upgrade_choices = []
        self.upgrade_selected_index = -1
        if self.document_id:
            self._set_hud_class("upgrade_panel", "hover_enabled", False)
            RmlUI.SetMouseCursorVisible(self.document_id, False)
            RmlUI.SetStyle(self.document_id, "upgrade_panel", "display", "none")
            self._set_hud_text("banner", self._text(self.banner_key))
        self._sync_hud()
        self._try_level_up()
