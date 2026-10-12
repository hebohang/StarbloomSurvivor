"""Cached character combat-hook registry for Starbloom Survivor."""

import HEngine


class SurvivorCombatHooksMixin:
    _HOOK_EVENTS = {
        "on_level_starpaw_might": "level",
        "on_level_honey_gold": "level",
        "on_level_cosmic_training": "level",
        "on_overheal_bubble_shield": "heal",
        "on_distance_cast_echo": "distance",
        "on_damage_freeze_burst": "damage",
        "on_item_maxed_projectile_area": "item_maxed",
        "on_hit_honey_mark": "hit",
        "on_poison_kill_spread": "kill",
        "on_evade_phantom_echo": "evade",
        "on_damage_prevented_tidal_wave": "damage_prevented",
    }

    def _compile_character_hooks(self):
        from SurvivorContent import WEAPON_DEFS

        registry = {
            "on_level_starpaw_might": self._hook_starpaw_level,
            "on_level_honey_gold": self._hook_honey_level,
            "on_level_cosmic_training": self._hook_cosmobob_level,
            "on_overheal_bubble_shield": self._hook_peachy_overheal,
            "on_distance_cast_echo": self._hook_mossling_distance,
            "on_damage_freeze_burst": self._hook_snowbean_damage,
            "on_item_maxed_projectile_area": self._hook_azura_item_maxed,
            "on_hit_honey_mark": self._hook_honey_hit,
            "on_poison_kill_spread": self._hook_mushmellow_kill,
            "on_evade_phantom_echo": self._hook_boolet_evade,
            "on_damage_prevented_tidal_wave": self._hook_crabble_prevented,
        }
        compiled = {}
        for hook_id in self.active_character_hooks:
            if hook_id not in registry or hook_id not in self._HOOK_EVENTS:
                raise ValueError("Unknown active character hook: " + hook_id)
            event = self._HOOK_EVENTS[hook_id]
            compiled.setdefault(event, []).append(registry[hook_id])
        self.combat_hooks = {
            event: tuple(callbacks)
            for event, callbacks in compiled.items()
        }
        self.character_hook_state = {
            "starpawMight": 0.0,
            "bubbleShield": 0.0,
            "distance": 0.0,
            "echoReady": False,
            "snowCooldown": 0.0,
            "azuraStacks": 0,
            "booletCooldown": 0.0,
            "prevented": 0.0,
            "cosmicBonuses": {
                "might": 0.0,
                "area": 0.0,
                "haste": 0.0,
                "speed": 0.0,
                "duration": 0.0,
            },
            "cosmicHistory": [],
        }
        self.trinket_state = {
            "castCounter": 0,
            "magnetStacks": 0,
            "magnetDecayTimer": 0.0,
            "marshmallowTimer": 0.0,
            "marshmallowReady": False,
            "luckyWindow": -1,
            "luckyAwards": 0,
            "friendshipWeapon": "",
        }
        self.weapon_tag_cache = {
            weapon_id: frozenset(definition.get("tags", ()))
            for weapon_id, definition in WEAPON_DEFS.items()
        }

    def _equip_trinket(self, trinket_id):
        if trinket_id in self.trinket_slots or len(self.trinket_slots) >= 4:
            return False
        self.trinket_slots.append(trinket_id)
        if trinket_id == "glass_star":
            health_fraction = self.health / max(1.0, self.max_health)
            self.base_character_max_health *= 0.80
            self.max_health = self.base_character_max_health * (
                1.0 + self._tome_level("vitality") * 0.08
            )
            self.health = min(self.max_health, self.max_health * health_fraction)
        elif trinket_id == "marshmallow_shield":
            self.trinket_state["marshmallowTimer"] = 0.0
            self.trinket_state["marshmallowReady"] = True
        self._recompute_friendship_pin()
        return True

    def _recompute_friendship_pin(self):
        if "friendship_pin" not in self.trinket_slots:
            self.trinket_state["friendshipWeapon"] = ""
            return
        base_slots = [
            next((
                base_id for base_id, evolution_id in self.active_evolutions.items()
                if evolution_id == slot_id
            ), slot_id)
            for slot_id in self.weapon_slots
        ]
        base_slots = [slot_id for slot_id in base_slots if hasattr(self, slot_id + "_level")]
        self.trinket_state["friendshipWeapon"] = min(
            base_slots,
            key=lambda slot_id: (self._weapon_level(slot_id), slot_id),
            default="",
        )

    def _update_trinkets(self, dt):
        state = self.trinket_state
        if "marshmallow_shield" in self.trinket_slots and not state["marshmallowReady"]:
            state["marshmallowTimer"] += dt
            if state["marshmallowTimer"] >= 45.0:
                state["marshmallowTimer"] = 0.0
                state["marshmallowReady"] = True
        if "tiny_magnet" in self.trinket_slots:
            state["magnetDecayTimer"] += dt
            if state["magnetDecayTimer"] >= 2.0 and state["magnetStacks"] > 0:
                decay_steps = int((state["magnetDecayTimer"] - 2.0) // 0.5) + 1
                state["magnetStacks"] = max(0, state["magnetStacks"] - decay_steps * 2)
                state["magnetDecayTimer"] = 2.0

    def _on_xp_pickup_trinkets(self):
        if "tiny_magnet" not in self.trinket_slots:
            return
        state = self.trinket_state
        state["magnetStacks"] = min(8, state["magnetStacks"] + 1)
        state["magnetDecayTimer"] = 0.0

    def _on_weapon_cast_trinkets(self, weapon_id):
        state = self.trinket_state
        state["castCounter"] += 1
        if (
                "echo_shell" in self.trinket_slots
                and not getattr(self, "bWeaponEchoCast", False)
                and state["castCounter"] % 7 == 0):
            self.pending_weapon_echoes.append({
                "timer": 0.22,
                "weapon_id": weapon_id,
                "proc": 0.45,
            })

    def _trinket_damage_multiplier(self, weapon_id, target):
        multiplier = 1.0
        tags = self.weapon_tag_cache.get(weapon_id, frozenset())
        if "popcorn_kernel" in self.trinket_slots and tags & {"explosion", "zone"}:
            multiplier *= 0.92
        if "glass_star" in self.trinket_slots and self.health >= self.max_health - 0.001:
            multiplier *= 1.40
        if "boss_bell" in self.trinket_slots:
            multiplier *= 1.28 if (target.get("boss") or target.get("elite")) else 0.95
        if "comet_tail" in self.trinket_slots and "projectile" in tags:
            velocity_bonus = self._tome_level("velocity") * 0.12
            multiplier *= 1.0 + min(0.24, int(velocity_bonus / 0.20) * 0.04)
        return multiplier

    def _trinket_area_multiplier(self, weapon_id):
        if "popcorn_kernel" not in self.trinket_slots:
            return 1.0
        tags = self.weapon_tag_cache.get(weapon_id, frozenset())
        return 1.30 if tags & {"explosion", "zone"} else 1.0

    def _on_weapon_hit_trinkets(self, source_id, target, damage, bCritical):
        base_source = source_id.split(":", 1)[0]
        if "sticky_honey" in self.trinket_slots:
            apply_status = getattr(HEngine, "ApplySurvivorAgentStatus", None)
            if apply_status is not None:
                accepted, applied_duration, _ = apply_status(
                    target["entity"], "slow", 0.12, 1.4,
                    target.get("activation_id", 0),
                )
                if accepted and applied_duration > 0.0 and self.quest_tracker is not None:
                    self.quest_tracker.record(
                        "status_applied", 1, {"status": "slow"},
                    )
        if (
                "prism_lens" in self.trinket_slots
                and ":split" not in source_id
                and self._random_uniform(0.0, 1.0) < 0.16):
            target_pos = target["transform"].Translation
            split_targets = [
                nearby for _, nearby in self._weapon_candidates(
                    target_pos.x, target_pos.y, target_pos.z, 2.8,
                )
                if nearby is not target
            ][:2]
            for nearby in split_targets:
                self._apply_weapon_damage(
                    nearby, damage * 0.35,
                    target_pos.x, target_pos.z,
                    0.10, False, base_source + ":split",
                )
        return bCritical

    def _on_critical_kill_trinkets(self):
        if "lucky_ribbon" not in self.trinket_slots:
            return
        second = int(self.elapsed)
        state = self.trinket_state
        if state["luckyWindow"] != second:
            state["luckyWindow"] = second
            state["luckyAwards"] = 0
        if state["luckyAwards"] >= 3:
            return
        if self._random_uniform(0.0, 1.0) < 0.08:
            state["luckyAwards"] += 1
            self.run_gold += 1

    def _dispatch_combat_hook(self, event, context=None):
        context = context or {}
        for callback in self.combat_hooks.get(event, ()):
            callback(context)

    def _update_character_hook_timers(self, dt):
        state = self.character_hook_state
        state["snowCooldown"] = max(0.0, state["snowCooldown"] - dt)
        state["booletCooldown"] = max(0.0, state["booletCooldown"] - dt)

    def _apply_healing(self, amount, bAllowOverheal=False):
        amount = max(0.0, float(amount))
        missing = max(0.0, self.max_health - self.health)
        healed = min(missing, amount)
        self.health += healed
        self.run_healed += healed
        if self.quest_tracker is not None and healed > 0.0:
            self.quest_tracker.record("healing", healed)
        overflow = max(0.0, amount - healed)
        if overflow > 0.0 and (bAllowOverheal or self.combat_hooks.get("heal")):
            self._dispatch_combat_hook("heal", {"overflow": overflow})
        return healed

    def _hook_starpaw_level(self, context):
        level = int(context.get("level", self.level))
        bonus = min(0.40, (level // 10) * 0.08)
        self.character_hook_state["starpawMight"] = bonus
        self.character_damage_multiplier = (
            self.base_character_weapon_damage_multiplier * (1.0 + bonus)
        )

    def _hook_honey_level(self, context):
        level = min(40, int(context.get("level", self.level)))
        self.character_gold_multiplier = 1.0 + level * 0.0075

    def _hook_cosmobob_level(self, context):
        level = int(context.get("level", self.level))
        if level <= 0 or level % 5 != 0:
            return
        keys = ("might", "area", "haste", "speed", "duration")
        index = min(
            len(keys) - 1,
            int(self._random_uniform(0.0, float(len(keys)))),
        )
        key = keys[index]
        bonuses = self.character_hook_state["cosmicBonuses"]
        bonuses[key] += 0.02
        self.character_hook_state["cosmicHistory"].append(key)
        if key == "might":
            self.character_damage_multiplier *= 1.02
        elif key == "area":
            self.character_reach_multiplier *= 1.02
        elif key == "haste":
            self.character_cooldown_multiplier *= 0.98
        elif key == "speed":
            movement = self.player.GetComponent("CharacterMovement")
            movement.MaxSpeed *= 1.02
        elif key == "duration":
            self.character_duration_multiplier *= 1.02

    def _hook_peachy_overheal(self, context):
        state = self.character_hook_state
        state["bubbleShield"] = min(
            self.max_health * 0.20,
            state["bubbleShield"] + max(0.0, context.get("overflow", 0.0)),
        )

    def _hook_mossling_distance(self, context):
        state = self.character_hook_state
        state["distance"] += max(0.0, context.get("distance", 0.0))
        if state["distance"] >= 18.0:
            state["distance"] %= 18.0
            state["echoReady"] = True

    def _consume_mossling_echo(self):
        state = self.character_hook_state
        if not state.get("echoReady", False):
            return False
        state["echoReady"] = False
        return True

    def _hook_snowbean_damage(self, context):
        state = self.character_hook_state
        if state["snowCooldown"] > 0.0:
            return
        state["snowCooldown"] = 12.0
        player_pos = self.player.GetComponent("Transform").Translation
        apply_status = getattr(HEngine, "ApplySurvivorAgentStatus", None)
        if apply_status is None:
            return
        for _, monster in self._weapon_candidates(
                player_pos.x, player_pos.y, player_pos.z, 3.2):
            accepted, applied_duration, _ = apply_status(
                monster["entity"],
                "freeze",
                0.55 if monster["boss"] else 1.0,
                1.1 * self.status_multiplier,
                monster.get("activation_id", 0),
            )
            if accepted and applied_duration > 0.0 and self.quest_tracker is not None:
                self.quest_tracker.record(
                    "status_applied", 1, {"status": "freeze"},
                )

    def _hook_azura_item_maxed(self, context):
        del context
        state = self.character_hook_state
        state["azuraStacks"] = min(6, state["azuraStacks"] + 1)

    def _hook_honey_hit(self, context):
        target = context.get("target")
        if target is None:
            return
        marks = target.get("honey_marks", 0) + 1
        if marks < 3:
            target["honey_marks"] = marks
            return
        target["honey_marks"] = 0
        target_pos = target["transform"].Translation
        for _, nearby in self._weapon_candidates(
                target_pos.x, target_pos.y, target_pos.z, 2.2):
            if nearby is target:
                continue
            self._apply_weapon_damage(
                nearby,
                max(1.0, context.get("damage", 0.0) * 0.25),
                target_pos.x,
                target_pos.z,
                0.25,
                False,
                "honeyneedle",
            )

    def _hook_mushmellow_kill(self, context):
        target = context.get("target")
        generation = int(context.get("generation", 0))
        remaining = max(0.0, context.get("poisonRemaining", 0.0))
        if target is None or generation > 0 or remaining <= 0.0:
            return
        target_pos = target["transform"].Translation
        candidates = self._weapon_candidates(
            target_pos.x, target_pos.y, target_pos.z, 2.2,
        )[:4]
        for _, nearby in candidates:
            if nearby is target:
                continue
            spread_total = remaining * 0.50
            nearby["poison_remaining_damage"] = spread_total
            nearby["poison_generation"] = 1
            nearby_pos = nearby["transform"].Translation
            tick_damage = spread_total / 6.0
            self._queue_custom_area(
                "sporecap",
                nearby_pos.x,
                nearby_pos.y,
                nearby_pos.z,
                0.0,
                0.48,
                tick_damage,
                tick_damage,
                3.0,
                0.5,
                0.0,
                target_limit=1,
            )

    def _hook_boolet_evade(self, context):
        del context
        state = self.character_hook_state
        if state["booletCooldown"] > 0.0:
            return
        state["booletCooldown"] = 1.2
        player_pos = self.player.GetComponent("Transform").Translation
        self._queue_custom_area(
            "phantombell",
            player_pos.x, player_pos.y, player_pos.z,
            0.0,
            self._weapon_reach(2.6),
            self._weapon_damage(24.0) * 0.40,
            duration=0.0,
            visual_kind="bell",
            visual_count=1,
        )

    def _hook_crabble_prevented(self, context):
        state = self.character_hook_state
        state["prevented"] += max(0.0, context.get("amount", 0.0))
        if state["prevented"] < 60.0:
            return
        state["prevented"] %= 60.0
        player_pos = self.player.GetComponent("Transform").Translation
        self._queue_custom_area(
            "coralanchor",
            player_pos.x, player_pos.y, player_pos.z,
            0.60,
            self._weapon_reach(3.0),
            self._weapon_damage(42.0),
            duration=0.0,
            force=1.2,
        )
