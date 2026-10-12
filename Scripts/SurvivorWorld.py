import os
import time

import HEngine

from SurvivorRules import (
    combine_challenge_modifiers,
    resolve_defense,
    selected_challenge_ids,
)
from SurvivorRuntimeAssets import asset_path

_BATCH_TIMING_ENABLED = os.environ.get("HE_SURVIVOR_STAGE_TIMINGS") == "1"
_ACTIVATION_TIMING_ENABLED = os.environ.get("HE_SURVIVOR_OBJECTIVE_TIMINGS") == "1"


class SurvivorWorldMixin:
    def _animation_budget(self):
        override = os.environ.get("HE_SURVIVOR_ANIMATION_BUDGET", "").strip()
        if override:
            try:
                value = int(override)
            except ValueError:
                raise ValueError("HE_SURVIVOR_ANIMATION_BUDGET must be 12, 16, or 20")
            if value not in (12, 16, 20):
                raise ValueError("HE_SURVIVOR_ANIMATION_BUDGET must be 12, 16, or 20")
            return value
        density = getattr(self, "particle_density", "auto")
        if density == "low":
            return 12
        if density == "high":
            return 20
        return 16

    def _selected_challenge_entries(self):
        run_config = getattr(self, "run_config", None)
        if run_config is not None:
            selected = set(run_config.challenge_ids)
            return tuple(
                entry for entry in self.CHALLENGES
                if entry["id"] in selected
            )
        profile = getattr(self, "profile", {})
        challenge_ids = selected_challenge_ids(
            profile,
            (entry["id"] for entry in self.CHALLENGES),
        )
        selected = set(challenge_ids)
        return tuple(
            entry for entry in self.CHALLENGES
            if entry["id"] in selected
        )

    def _challenge_tuning(self):
        minute = min(15, int(self.elapsed // 60.0))
        run_config = getattr(self, "run_config", None)
        if run_config is not None:
            return run_config.challenge_tuning_for_world_minute(minute)
        return combine_challenge_modifiers(
            self._selected_challenge_entries(),
            minute,
        )

    def _current_wave_phase(self):
        for phase in self.WAVE_PHASES:
            if self.elapsed < phase["end"]:
                return phase
        return self.WAVE_PHASES[-1]

    def _phase_population_target(self, phase):
        objective_target = getattr(self, "_global_population_target", None)
        if objective_target is not None:
            target = float(objective_target())
        else:
            duration = max(0.001, phase["end"] - phase["start"])
            progress = max(
                0.0,
                min(1.0, (self.elapsed - phase["start"]) / duration),
            )
            target = phase["count_start"] + (
                phase["count_end"] - phase["count_start"]
            ) * progress
        difficulty = self._difficulty_entry()
        challenge = self._challenge_tuning()
        count_multiplier = (
            difficulty["spawn"]
            * challenge["enemyCount"]
            * getattr(self, "character_difficulty_multiplier", 1.0)
            * (1.0 + getattr(self, "curse_level", 0) * 0.08)
        )
        # A Region assault owns the remaining global capacity.  The hard 320
        # limit is still enforced again at activation time.
        reserve = int(getattr(self, "_region_capacity_reserve", lambda: 0)())
        return min(
            max(0, self.MAX_MONSTERS - reserve),
            int(round(target * count_multiplier)),
        )

    def _select_regular_archetype(self, phase):
        total_weight = sum(weight for _, weight in phase["pool"])
        roll = self._random_uniform(0.0, total_weight)
        selected_id = phase["pool"][-1][0]
        cumulative_weight = 0.0
        for archetype_id, weight in phase["pool"]:
            cumulative_weight += weight
            if roll <= cumulative_weight:
                selected_id = archetype_id
                break

        for archetype in self.MONSTER_ARCHETYPES:
            if archetype["id"] == selected_id:
                return archetype
        return self.MONSTER_ARCHETYPES[0]

    def _difficulty_entry(self):
        run_config = getattr(self, "run_config", None)
        difficulty_id = (
            run_config.selected_difficulty
            if run_config is not None else
            getattr(self, "profile", {}).get("selectedDifficulty", "adventure")
        )
        return next(
            (entry for entry in self.DIFFICULTIES if entry["id"] == difficulty_id),
            self.DIFFICULTIES[0],
        )

    def _difficulty_scales(self):
        phase = self._current_wave_phase()
        difficulty = self._difficulty_entry()
        challenge = self._challenge_tuning()
        return (
            phase["health_multiplier"] * difficulty["health"]
            * challenge["enemyHealth"]
            * getattr(self, "character_difficulty_multiplier", 1.0)
            * (1.0 + getattr(self, "curse_level", 0) * 0.08),
            phase["damage_multiplier"] * difficulty["damage"]
            * challenge["enemyDamage"]
            * getattr(self, "character_difficulty_multiplier", 1.0)
            * (1.0 + getattr(self, "curse_level", 0) * 0.06),
            phase["speed_multiplier"] * difficulty["speed"]
            * challenge["enemySpeed"],
        )

    def _find_spawn_position(self, player_pos):
        for _ in range(self.SPAWN_GROUND_ATTEMPTS):
            offset_x = self._random_uniform(-1.0, 1.0)
            offset_z = self._random_uniform(-1.0, 1.0)
            offset_length = max(0.001, (offset_x * offset_x + offset_z * offset_z) ** 0.5)
            distance = self._random_uniform(9.0, 14.0)
            spawn_x = player_pos.x + offset_x / offset_length * distance
            spawn_z = player_pos.z + offset_z / offset_length * distance
            if (abs(spawn_x) > self.PLAYABLE_HALF_EXTENT or
                    abs(spawn_z) > self.PLAYABLE_HALF_EXTENT):
                continue
            spawn_probe = HEngine.vec3(spawn_x, player_pos.y, spawn_z)
            spawn_y = self._try_grounded_y(
                spawn_probe,
                self.MONSTER_GROUND_OFFSET,
            )
            if spawn_y is not None:
                return HEngine.vec3(spawn_x, spawn_y, spawn_z)
        return None

    def _activate_monster(
            self,
            spawn,
            boss=False,
            phase=None,
            archetype_id=None,
            boss_event_id="",
            objective_boss=False,
            final_boss=False,
            encounter_id="",
            zone_id="",
            attempt_id=0,
            health_multiplier=1.0,
            damage_multiplier=1.0,
            speed_multiplier=1.0,
            reward_scale=1.0,
            force_elite=False,
            fixed_elite=False,
            chest_tier=0,
            max_health_override=None,
            no_distance_retire=False):
        """Activate one explicit monster generation.

        Objective bosses and Region encounters must pass their identity instead
        of relying on the old timed ``boss_spawn_index`` side channel.  Keeping
        all provenance on the generation also makes pooled entities safe across
        retries and lets reward budgets remain idempotent.
        """

        activation_start_ns = time.perf_counter_ns() if _ACTIVATION_TIMING_ENABLED else 0
        instantiate_ms = 0.0
        phase = phase or self._current_wave_phase()
        if sum(1 for monster in self.monsters if not monster.get("dead", False)) >= self.MAX_MONSTERS:
            record_failure = getattr(self, "_record_spawn_failure", None)
            if record_failure is not None:
                record_failure("global_cap")
            return False
        catalog = self.BOSS_ARCHETYPES if boss else self.MONSTER_ARCHETYPES
        archetype = None
        if archetype_id:
            archetype = next(
                (entry for entry in catalog if entry["id"] == archetype_id),
                None,
            )
            if archetype is None:
                raise ValueError("unknown Survivor archetype: " + str(archetype_id))
        elif boss:
            raise ValueError("Boss activation requires an explicit archetype_id")
        else:
            archetype = self._select_regular_archetype(phase)

        animated = boss
        pool = self.monster_pools.setdefault(archetype["id"], [])
        from_pool = bool(pool)
        if from_pool:
            monster = pool.pop()
            entity = monster["entity"]
            transform = monster["transform"]
        else:
            instantiate_start_ns = time.perf_counter_ns() if _ACTIVATION_TIMING_ENABLED else 0
            entity = HEngine.Instantiate(archetype["prefab"], spawn)
            if not entity.HasComponent("Transform"):
                return False
            transform = entity.GetComponent("Transform")
            monster = {"entity": entity, "transform": transform}
            if _ACTIVATION_TIMING_ENABLED:
                instantiate_ms = (time.perf_counter_ns() - instantiate_start_ns) / 1_000_000.0

        bElite = bool(force_elite) or (
            not boss
            and self._random_uniform(0.0, 1.0) < phase.get("elite_rate", 0.0)
        )
        elite_affixes = ("swift", "armored", "volatile", "commander")
        elite_affix = ""
        if bElite:
            elite_affix = elite_affixes[min(
                len(elite_affixes) - 1,
                int(self._random_uniform(0.0, float(len(elite_affixes)))),
            )]

        scale = archetype["scale"]
        if not boss:
            scale *= self._random_uniform(0.92, 1.08)
        if bElite:
            scale *= 1.08
        scale *= self._challenge_tuning()["enemyScale"]
        transform.Translation = spawn
        transform.Rotation = HEngine.vec3(0.0, self._random_uniform(-3.14, 3.14), 0.0)
        transform.Scale = HEngine.vec3(scale, scale, scale)

        if entity.HasComponent("Animator"):
            animator = entity.GetComponent("Animator")
            if animated:
                animator.SetControllerPath(archetype["controller"])
                animator.SetSpeed(self._random_uniform(0.95, 1.25))
                animator.Play()
                if animator.HasParameter("Speed"):
                    animator.SetFloat("Speed", 1.0)
            else:
                animator.SetControllerPath("None")
                animator.Stop()

        if encounter_id or objective_boss:
            difficulty = self._difficulty_entry()
            challenge = self._challenge_tuning()
            health_scale = (
                difficulty["health"] * challenge["enemyHealth"]
                * getattr(self, "character_difficulty_multiplier", 1.0)
                * (1.0 + getattr(self, "curse_level", 0) * 0.08)
            )
            damage_scale = (
                difficulty["damage"] * challenge["enemyDamage"]
                * getattr(self, "character_difficulty_multiplier", 1.0)
                * (1.0 + getattr(self, "curse_level", 0) * 0.06)
            )
            speed_scale = difficulty["speed"] * challenge["enemySpeed"]
        else:
            health_scale, damage_scale, speed_scale = self._difficulty_scales()
        health_scale *= max(0.0, float(health_multiplier))
        damage_scale *= max(0.0, float(damage_multiplier))
        speed_scale *= max(0.0, float(speed_multiplier))
        if not boss:
            speed_scale *= self._random_uniform(0.94, 1.06)

        if bElite:
            health_scale *= 1.8
            damage_scale *= 1.25
            if elite_affix == "swift":
                speed_scale *= 1.22
            elif elite_affix == "armored":
                health_scale *= 1.18
            elif elite_affix == "volatile":
                damage_scale *= 1.16
        max_health = (
            max(1.0, float(max_health_override))
            if max_health_override is not None else
            archetype["health"] * health_scale
        )
        if (
                objective_boss
                and os.environ.get(
                    "HE_SURVIVOR_CAPTURE_FINAL_BOSS_HP", "0",
                ) == "1"):
            max_health = 1.0
        self.monster_activation_serial += 1
        monster.update({
            "activation_id": self.monster_activation_serial,
            "health": max_health,
            "max_health": max_health,
            "speed": archetype["speed"] * speed_scale,
            "damage": archetype["damage"] * damage_scale,
            "radius": archetype["radius"],
            "base_scale": scale,
            "touch_timer": 0.0,
            "attack_windup": 0.0,
            "attack_cooldown": self._random_uniform(0.0, 0.3),
            "attacking": False,
            "boss": boss,
            "boss_event_id": str(boss_event_id),
            "objective_boss": bool(objective_boss),
            "final_boss": bool(final_boss),
            "boss_behavior": "star_dragon" if archetype["id"] == "star_dragon" else "generic",
            "no_distance_retire": bool(objective_boss or no_distance_retire),
            "boss_enrage_seconds": 120.0 if objective_boss else 0.0,
            "elite": bElite,
            "elite_affix": elite_affix,
            "fixed_elite": bool(fixed_elite),
            "animated": animated,
            "animation_warmup": 0.16 if animated else 0.0,
            "dead": False,
            "death_timer": 0.0,
            "death_anim_sent": False,
            "hit_flash": 0.0,
            "knock_x": 0.0,
            "knock_z": 0.0,
            "phase": self._random_uniform(0.0, 6.28318),
            "ground_offset": self.MONSTER_GROUND_OFFSET,
            "archetype_id": archetype["id"],
            "encounter_id": str(encounter_id),
            "zone_id": str(zone_id),
            "attempt_id": max(0, int(attempt_id)),
            "region_spawned": bool(encounter_id),
            "region_reward_limited": bool(encounter_id and zone_id),
            "reward_encounter_id": str(encounter_id),
            "reward_zone_id": str(zone_id),
            "encounter_health_multiplier": max(0.0, float(health_multiplier)),
            "encounter_damage_multiplier": max(0.0, float(damage_multiplier)),
            "encounter_speed_multiplier": max(0.0, float(speed_multiplier)),
            "encounter_reward_scale": max(0.0, float(reward_scale)),
            "animation_controller": archetype["controller"],
            "behavior": archetype.get("behavior", "chaser"),
            "attack": dict(archetype.get("attack", {})),
            "resistances": dict(archetype.get("resistances", {})),
            "boss_phase": archetype.get("boss_phase", 0),
            "display_names": {
                "zh_cn": archetype["name_zh"], "en": archetype["name_en"],
            },
            "display_name": archetype["name_zh"] if self.language == "zh_cn" else archetype["name_en"],
            "reward": max(
                0.0,
                archetype["reward"] * (4 if bElite else 1)
                * max(0.0, float(reward_scale)),
            ),
            "run_gold_reward": 4 if bElite else 0,
            "chest_tier": max(0, int(chest_tier)),
        })
        register_start_ns = time.perf_counter_ns() if _ACTIVATION_TIMING_ENABLED else 0
        entity_id = HEngine.RegisterSurvivorAgent(entity, monster)
        register_ms = (
            (time.perf_counter_ns() - register_start_ns) / 1_000_000.0
            if _ACTIVATION_TIMING_ENABLED else 0.0
        )
        monster["entity_id"] = entity_id
        self.monsters_by_id[entity_id] = monster
        self.monsters.append(monster)
        if boss:
            HEngine.VFX.PlayEffectAdvanced(
                self.BOSS_SPAWN_WARNING_EFFECT,
                spawn.x, spawn.y + 0.05, spawn.z,
                0.0, 0.0, -1.0,
                0.75, 1.6, 0,  # GameplayCritical budget category.
            )
            self.audio.post("boss_alert")
        if _ACTIVATION_TIMING_ENABLED and encounter_id:
            total_ms = (time.perf_counter_ns() - activation_start_ns) / 1_000_000.0
            if total_ms > 0.4:
                HEngine.HE_CORE_INFO(
                    "[RegionActivationTiming] elapsed={:.3f} archetype={} pooled={} totalMs={:.3f} instantiateMs={:.3f} registerMs={:.3f}".format(
                        self.elapsed, archetype["id"], from_pool, total_ms,
                        instantiate_ms, register_ms,
                    )
                )
        return True

    def _runtime_warmup_progress(self):
        if self.bRuntimeReady or self.warmup_stage == "ready":
            return 1.0, "loading_ready"

        if self.pending_effects:
            total = max(1, self.warmup_total_effects)
            completed = total - len(self.pending_effects)
            return 0.20 * completed / total, "loading_effects"

        monster_base = 0.20
        monster_weight = 0.55
        if self.warmup_stage in ("effects", "monster", "monster_release"):
            total = max(1, self.warmup_total_monsters)
            completed = total - len(self.pending_monster_warmups)
            if self.warmup_stage == "monster":
                completed -= 2.0 / 3.0
            elif self.warmup_stage == "monster_release":
                completed -= 1.0 / 3.0
            ratio = max(0.0, min(1.0, completed / total))
            return monster_base + monster_weight * ratio, "loading_monsters"

        if self.warmup_stage == "pickup":
            return 0.78, "loading_pickup"

        if self.warmup_stage == "visuals":
            return 0.81, "loading_projectiles"

        resource_progresses = [
            HEngine.RuntimeResourceWarmup.GetTriggerProgress(trigger)
            for trigger in ("AdventureCore", "Wave00", "RegionFoundations")
        ]
        ready_progresses = [
            progress for progress in resource_progresses
            if progress is not None
        ]
        resource_ratio = (
            0.0 if not ready_progresses else
            sum(progress.Ratio for progress in ready_progresses)
            / len(ready_progresses)
        )
        return 0.83 + 0.17 * resource_ratio, "loading_resources"

    def _advance_runtime_warmup(self):
        if self.bRuntimeReady:
            return

        if self.pending_effects:
            effect = self.pending_effects.pop(0)
            if not HEngine.VFX.LoadEffect(effect):
                HEngine.HE_CORE_WARN("[SurvivorGame] failed to preload " + effect)
            return

        if self.warmup_stage == "effects":
            if not self.pending_monster_warmups:
                self.warmup_stage = "pickup"
                return

            archetype = self.pending_monster_warmups.pop(0)
            warmup_position = HEngine.vec3(0.0, -100.0, 0.0)
            entity = HEngine.Instantiate(archetype["prefab"], warmup_position)
            if entity.HasComponent("Transform"):
                transform = entity.GetComponent("Transform")
                transform.Translation = warmup_position
                scale = archetype["scale"]
                transform.Scale = HEngine.vec3(scale, scale, scale)
                self.warmup_monster = {
                    "entity": entity,
                    "transform": transform,
                    "archetype_id": archetype["id"],
                }
            else:
                HEngine.Destroy(entity)
            self.warmup_stage = "monster"
            return

        if self.warmup_stage == "monster":
            if self.warmup_monster is not None:
                entity = self.warmup_monster["entity"]
                if entity.HasComponent("Animator"):
                    animator = entity.GetComponent("Animator")
                    animator.SetControllerPath("None")
                    animator.Stop()
            self.warmup_stage = "monster_release"
            return

        if self.warmup_stage == "monster_release":
            if self.warmup_monster is not None:
                transform = self.warmup_monster["transform"]
                transform.Scale = self.HIDDEN_SCALE
                transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
                pool = self.monster_pools.setdefault(
                    self.warmup_monster["archetype_id"],
                    [],
                )
                pool.append(self.warmup_monster)
                self.warmup_monster = None
            self.warmup_stage = (
                "effects" if self.pending_monster_warmups else "pickup"
            )
            return

        if self.warmup_stage == "pickup":
            warmup_position = HEngine.vec3(0.0, -100.0, 0.0)
            entity = HEngine.Instantiate(self.EXPERIENCE_PREFAB, warmup_position)
            if entity.HasComponent("Transform"):
                transform = entity.GetComponent("Transform")
                transform.Translation = warmup_position
                transform.Scale = self.HIDDEN_SCALE
                self.pickup_pool.append({"entity": entity, "transform": transform})
            else:
                HEngine.Destroy(entity)
            self.warmup_stage = "visuals"
            return

        if self.warmup_stage == "visuals":
            if self.pending_visual_warmups:
                visual_kind = self.pending_visual_warmups.pop(0)
                entity = self._acquire_projectile_visual(visual_kind)
                if entity is not None:
                    transform = entity.GetComponent("Transform")
                    transform.Scale = self.HIDDEN_SCALE
                    self.projectile_visual_pool[visual_kind].append(entity)
                return
            self.warmup_stage = "resources"
            return

        for trigger in ("AdventureCore", "Wave00", "RegionFoundations"):
            progress = HEngine.RuntimeResourceWarmup.GetTriggerProgress(trigger)
            if progress is None:
                raise RuntimeError(trigger + " resource warm-up trigger is not configured")
            if progress.FailedGroups > 0:
                HEngine.RuntimeResourceWarmup.RethrowFailure(trigger)
            if progress.ReadyGroups != progress.TotalGroups:
                return

        self.warmup_stage = "ready"
        self.bRuntimeReady = True
        self.spawn_timer = 0.0
        HEngine.HE_CORE_INFO("[SurvivorGame] runtime warm-up ready")

    def _update_monsters(self, player_pos, dt):
        previous_health = self.health
        batch_start_ns = time.perf_counter_ns() if _BATCH_TIMING_ENABLED else 0
        (
            retired,
            self.damage_cooldown,
            self.health,
            damage_flash_timer,
            banner_timer,
            game_over,
            self.random_state,
            raw_damage_events,
            projectile_events,
            zone_events,
            summon_events,
            telegraph_events,
            enemy_telemetry,
        ) = HEngine.UpdateSurvivorAgents(
            player_pos,
            dt,
            self.elapsed,
            self.damage_cooldown,
            self.health,
            self.damage_reduction,
            self.random_state,
            min(self.MAX_ANIMATED_MONSTERS, self._animation_budget()),
            self.ANIMATION_LOD_DISTANCE,
            self.ANIMATION_LOD_RELEASE_DISTANCE,
            self.MONSTER_DESPAWN_DISTANCE_SQ,
            self.MONSTER_ANIM_CONTROLLER,
        )
        batch_end_ns = time.perf_counter_ns() if _BATCH_TIMING_ENABLED else 0
        self._process_enemy_batch_events(
            player_pos,
            projectile_events,
            zone_events,
            summon_events,
            telegraph_events,
            enemy_telemetry,
        )
        if _BATCH_TIMING_ENABLED:
            event_end_ns = time.perf_counter_ns()
            batch_ms = (batch_end_ns - batch_start_ns) / 1_000_000.0
            event_ms = (event_end_ns - batch_end_ns) / 1_000_000.0
            if batch_ms > 3.0 or event_ms > 3.0:
                HEngine.HE_CORE_INFO(
                    "[SurvivorBatchTiming] elapsed={:.3f} batchMs={:.3f} eventsMs={:.3f}".format(
                        self.elapsed, batch_ms, event_ms,
                    )
                )
        update_objective_boss = getattr(
            self, "_update_objective_boss_runtime", None,
        )
        if update_objective_boss is not None:
            update_objective_boss(player_pos, dt)

        damage_flash_timer = 0.0
        banner_timer = 0.0
        game_over = False
        for source_entity_id, activation_id, raw_damage, kind_id in raw_damage_events:
            source = self.monsters_by_id.get(source_entity_id)
            if (
                    source is None
                    or source.get("activation_id", -1) != activation_id
                    or source["dead"]):
                continue
            bMarshmallowBlock = self.trinket_state.get("marshmallowReady", False)
            bubble_shield = self.character_hook_state.get("bubbleShield", 0.0)
            shield = bubble_shield
            bRoyalBubbleBlock = (
                kind_id == "projectile"
                and self.character_hook_state.get(
                    "royalBubbleProjectileShield", 0,
                ) > 0
            )
            if bRoyalBubbleBlock:
                shield += max(1.0, raw_damage)
            tidal_fortress = self.character_hook_state.get("tidalFortress", 0.0)
            shield += tidal_fortress
            if bMarshmallowBlock:
                shield += max(1.0, raw_damage)
            result = resolve_defense(
                raw_damage,
                self._random_uniform(0.0, 1.0),
                self.evasion,
                self.armor,
                self.damage_reduction,
                shield,
            )
            remaining_absorption = result.shield_absorbed
            if bRoyalBubbleBlock:
                self.character_hook_state["royalBubbleProjectileShield"] = 0
                remaining_absorption = max(
                    0.0,
                    remaining_absorption - max(1.0, raw_damage),
                )
            if bMarshmallowBlock:
                remaining_absorption = max(
                    0.0,
                    remaining_absorption - max(1.0, raw_damage),
                )
            if tidal_fortress > 0.0:
                tidal_absorbed = min(tidal_fortress, remaining_absorption)
                self.character_hook_state["tidalFortress"] = max(
                    0.0,
                    tidal_fortress - tidal_absorbed,
                )
                remaining_absorption -= tidal_absorbed
            self.character_hook_state["bubbleShield"] = max(
                0.0,
                bubble_shield - remaining_absorption,
            )
            if bMarshmallowBlock:
                self.trinket_state["marshmallowReady"] = False
                self.trinket_state["marshmallowTimer"] = 0.0
            prevented = (
                result.armor_prevented
                + result.reduction_prevented
                + result.shield_absorbed
            )
            if result.evaded:
                self.run_evaded_hits += 1
                self._dispatch_combat_hook(
                    "evade", {"source": source, "kind": kind_id},
                )
            if prevented > 0.0:
                self.run_damage_prevented += prevented
                self._dispatch_combat_hook(
                    "damage_prevented", {"amount": prevented, "source": source},
                )
                if self.quest_tracker is not None:
                    self.quest_tracker.record("damage_prevented", prevented)
            if result.damage <= 0.0:
                continue
            self.telemetry.record_attack_damage(kind_id, result.damage)
            self.health = max(0.0, self.health - result.damage)
            self.last_damage_elapsed = self.elapsed
            self.run_damage_taken += result.damage
            damage_flash_timer = 0.2
            banner_timer = 0.28
            self._dispatch_combat_hook(
                "damage", {"amount": result.damage, "source": source, "kind": kind_id},
            )
            if kind_id in ("melee", "charge", "suicide") and self.thorns > 0.0:
                source["health"] = HEngine.ApplySurvivorAgentHit(
                    source["entity"],
                    self.thorns,
                    0.0,
                    0.0,
                )
                if source["health"] <= 0.0:
                    self._kill_monster(source)
                if self.quest_tracker is not None:
                    self.quest_tracker.record("thorns_prevented", self.thorns)
            if self.health <= 0.0:
                if getattr(self, "run_revives_remaining", 0) > 0:
                    self.run_revives_remaining -= 1
                    self.run_revives_used += 1
                    self.health = self.max_health * 0.50
                    self.damage_cooldown = max(self.damage_cooldown, 1.0)
                    on_revive = getattr(self, "_on_objective_revive", None)
                    if on_revive is not None:
                        on_revive()
                    player_pos_now = self.player.GetComponent("Transform").Translation
                    HEngine.VFX.PlayEffectAdvanced(
                        asset_path("vfx/common/heal-level-up"),
                        player_pos_now.x,
                        player_pos_now.y + 0.10,
                        player_pos_now.z,
                        0.0, 0.0, -1.0,
                        0.48, 1.0,
                    )
                else:
                    game_over = True
                break

        if self.health < previous_health:
            self.audio.post("player_hit")

        if damage_flash_timer > 0.0:
            self.damage_flash_timer = damage_flash_timer
        if banner_timer > 0.0:
            self.banner_timer = banner_timer
        if game_over:
            self._game_over()
            return

        for entity_id in retired:
            monster = self.monsters_by_id.get(entity_id)
            if monster is not None:
                self._retire_monster(monster)

    def _process_enemy_batch_events(
            self,
            player_pos,
            projectile_events,
            zone_events,
            summon_events,
            telegraph_events,
            enemy_telemetry):
        for key, value in enemy_telemetry.items():
            if key == "activeAgents":
                self.enemy_batch_telemetry[key] = value
            else:
                self.enemy_batch_telemetry[key] = (
                    self.enemy_batch_telemetry.get(key, 0) + value
                )

        for slot, generation, _, _, event_id, x, y, z in projectile_events:
            key = (slot, generation)
            if event_id == "spawned":
                previous = self.enemy_projectile_effects.pop(key, None)
                if previous is not None:
                    HEngine.VFX.StopEffect(previous)
                direction_x = player_pos.x - x
                direction_z = player_pos.z - z
                self.enemy_projectile_effects[key] = HEngine.VFX.PlayEffectAdvanced(
                    self.ENEMY_PROJECTILE_EFFECT,
                    x, y + 0.34, z,
                    direction_x, 0.0, direction_z,
                    0.42, 1.0,
                    0,
                )
            elif event_id in ("hit", "expired"):
                handle = self.enemy_projectile_effects.pop(key, None)
                if handle is not None:
                    HEngine.VFX.StopEffect(handle)

        for slot, generation, _, _, event_id, x, y, z, radius in zone_events:
            key = (slot, generation)
            if event_id == "spawned":
                previous = self.enemy_zone_effects.pop(key, None)
                if previous is not None:
                    HEngine.VFX.StopEffect(previous)
                self.enemy_zone_effects[key] = HEngine.VFX.PlayEffectAdvanced(
                    self.ENEMY_ZONE_TELEGRAPH_EFFECT,
                    x, y + 0.03, z,
                    0.0, 0.0, -1.0,
                    max(0.18, radius * 0.16), 1.0,
                    0,
                )
            elif event_id == "expired":
                handle = self.enemy_zone_effects.pop(key, None)
                if handle is not None:
                    HEngine.VFX.StopEffect(handle)

        for (
                entity_id,
                activation_id,
                phase_id,
                behavior_id,
                x,
                y,
                z,
                attack_range,
                _,
                bBoss,
        ) in telegraph_events:
            key = (entity_id, activation_id)
            if phase_id == "start":
                previous = self.enemy_telegraph_effects.pop(key, None)
                if previous is not None:
                    HEngine.VFX.StopEffect(previous)
                effect = (
                    self.BOSS_AREA_TELEGRAPH_EFFECT
                    if bBoss else
                    self.ENEMY_ZONE_TELEGRAPH_EFFECT
                )
                direction_x = player_pos.x - x
                direction_z = player_pos.z - z
                self.enemy_telegraph_effects[key] = HEngine.VFX.PlayEffectAdvanced(
                    effect,
                    x, y + 0.03, z,
                    direction_x, 0.0, direction_z,
                    max(0.16, attack_range * (0.18 if bBoss else 0.13)),
                    1.0,
                    0,
                )
            elif phase_id in ("active", "end"):
                handle = self.enemy_telegraph_effects.pop(key, None)
                if handle is not None:
                    HEngine.VFX.StopEffect(handle)

        summon_budget = 8
        phase = self._current_wave_phase()
        for source_id, activation_id, _, x, y, z, count in summon_events:
            source = self.monsters_by_id.get(source_id)
            if (
                    source is None
                    or source.get("activation_id", -1) != activation_id
                    or source["dead"]):
                continue
            spawn_count = min(int(count), summon_budget)
            for index in range(spawn_count):
                angle = source.get("phase", 0.0) + index * 2.39996
                spawn = HEngine.vec3(
                    x + self._sin_approx(angle) * 1.4,
                    y,
                    z + self._sin_approx(angle + 1.5708) * 1.4,
                )
                self._activate_monster(
                    spawn,
                    False,
                    phase,
                    archetype_id="green_blob",
                    encounter_id=source.get("encounter_id", ""),
                    zone_id=source.get("zone_id", ""),
                    attempt_id=source.get("attempt_id", 0),
                    health_multiplier=source.get(
                        "encounter_health_multiplier", 1.0,
                    ),
                    damage_multiplier=source.get(
                        "encounter_damage_multiplier", 1.0,
                    ),
                    speed_multiplier=source.get(
                        "encounter_speed_multiplier", 1.0,
                    ),
                    reward_scale=source.get("encounter_reward_scale", 1.0),
                    no_distance_retire=source.get("region_spawned", False),
                )
            summon_budget -= spawn_count
            if summon_budget <= 0:
                break

    def _update_monsters_python_reference(self, player_pos, dt):
        retired = []
        animated_count = sum(
            1 for monster in self.monsters
            if monster["animated"] and not monster["dead"]
        )

        for monster in self.monsters:
            transform = monster["transform"]
            pos = transform.Translation

            if monster["dead"]:
                monster["animation_warmup"] = max(0.0, monster["animation_warmup"] - dt)
                if (monster["animated"]
                        and not monster["death_anim_sent"]
                        and monster["animation_warmup"] <= 0.0):
                    animator = monster["entity"].GetComponent("Animator")
                    if animator.HasParameter("Attacking"):
                        animator.SetBool("Attacking", False)
                    if animator.HasParameter("Dead"):
                        animator.SetBool("Dead", True)
                    elif animator.HasParameter("Speed"):
                        animator.SetFloat("Speed", 0.0)
                    monster["death_anim_sent"] = True

                monster["death_timer"] -= dt
                if monster["death_timer"] < 0.24:
                    fraction = max(0.0, monster["death_timer"] / 0.24)
                    scale = monster["base_scale"] * fraction
                    transform.Scale = HEngine.vec3(scale, scale, scale)
                if monster["death_timer"] <= 0.0:
                    retired.append(monster)
                continue

            dx = player_pos.x - pos.x
            dz = player_pos.z - pos.z
            distance_sq = dx * dx + dz * dz
            if distance_sq > self.MONSTER_DESPAWN_DISTANCE_SQ:
                retired.append(monster)
                continue

            distance = max(0.001, distance_sq ** 0.5)
            attack_distance = monster["radius"] + 0.42
            in_attack_range = distance <= attack_distance
            should_animate = (
                monster["boss"]
                or (monster["animated"] and distance <= self.ANIMATION_LOD_RELEASE_DISTANCE)
                or ((in_attack_range or distance <= self.ANIMATION_LOD_DISTANCE)
                    and animated_count < self.MAX_ANIMATED_MONSTERS)
            )

            if should_animate and not monster["animated"]:
                animator = monster["entity"].GetComponent("Animator")
                animator.SetControllerPath(monster["animation_controller"])
                animator.SetSpeed(self._random_uniform(0.95, 1.22))
                animator.Play()
                if animator.HasParameter("Speed"):
                    animator.SetFloat("Speed", 1.0)
                monster["animated"] = True
                monster["animation_warmup"] = 0.14
                animated_count += 1
            elif (monster["animated"]
                    and not monster["boss"]
                    and not in_attack_range
                    and distance > self.ANIMATION_LOD_RELEASE_DISTANCE):
                animator = monster["entity"].GetComponent("Animator")
                animator.SetControllerPath("None")
                animator.Stop()
                monster["animated"] = False
                monster["attacking"] = False
                monster["animation_warmup"] = 0.0
                animated_count = max(0, animated_count - 1)

            if monster["knock_x"] != 0.0 or monster["knock_z"] != 0.0:
                pos.x += monster["knock_x"] * dt
                pos.z += monster["knock_z"] * dt
                damping = max(0.0, 1.0 - 9.0 * dt)
                monster["knock_x"] *= damping
                monster["knock_z"] *= damping

            if distance > attack_distance:
                inv_distance = 1.0 / distance
                tangent_x = -dz * inv_distance
                tangent_z = dx * inv_distance
                weave = self._sin_approx(self.elapsed * 1.7 + monster["phase"]) * 0.12
                move_x = dx * inv_distance + tangent_x * weave
                move_z = dz * inv_distance + tangent_z * weave
                move_distance = min(monster["speed"] * dt, distance - attack_distance)
                pos.x += move_x * move_distance
                pos.z += move_z * move_distance
                transform.Translation = pos
                transform.Rotation = HEngine.vec3(0.0, self._atan2(dx, dz), 0.0)

            monster["hit_flash"] = max(0.0, monster["hit_flash"] - dt)
            pulse = 1.13 if monster["hit_flash"] > 0.0 else 1.0
            if not monster["animated"]:
                pulse *= 1.0 + self._sin_approx(self.elapsed * 4.0 + monster["phase"]) * 0.025
            scale = monster["base_scale"] * pulse
            transform.Scale = HEngine.vec3(scale, scale, scale)

            monster["touch_timer"] = max(0.0, monster["touch_timer"] - dt)
            monster["attack_cooldown"] = max(0.0, monster["attack_cooldown"] - dt)
            monster["animation_warmup"] = max(0.0, monster["animation_warmup"] - dt)

            wants_attack = in_attack_range and monster["attack_cooldown"] <= 0.0
            if (monster["animated"]
                    and monster["animation_warmup"] <= 0.0
                    and monster["attacking"] != wants_attack):
                animator = monster["entity"].GetComponent("Animator")
                if animator.HasParameter("Dead"):
                    animator.SetBool("Dead", False)
                if animator.HasParameter("Attacking"):
                    animator.SetBool("Attacking", wants_attack)
                elif animator.HasParameter("Speed"):
                    animator.SetFloat("Speed", 0.0 if wants_attack else 1.0)
                monster["attacking"] = wants_attack
                if wants_attack:
                    monster["attack_windup"] = 0.85 if monster["boss"] else 0.35

            if wants_attack:
                monster["attack_windup"] = max(0.0, monster["attack_windup"] - dt)
            elif not in_attack_range:
                monster["attack_windup"] = 0.0

            if (wants_attack
                    and monster["attack_windup"] <= 0.0
                    and monster["touch_timer"] <= 0.0
                    and self.damage_cooldown <= 0.0):
                monster["touch_timer"] = 0.65
                monster["attack_cooldown"] = 0.82 if monster["boss"] else 1.05
                monster["attack_windup"] = 0.0
                self.damage_cooldown = 0.45
                damage = monster["damage"] * (1.0 - self.damage_reduction)
                self.health = max(0.0, self.health - damage)
                self.damage_flash_timer = 0.2
                self.banner_timer = 0.28
                if self.health <= 0.0:
                    self._game_over()
                    return

        for monster in retired:
            self._retire_monster(monster)

    def _retire_monster(self, monster):
        if monster in self.monsters:
            self.monsters.remove(monster)
        entity_id = monster.get("entity_id")
        if self.monsters_by_id.get(entity_id) is monster:
            self.monsters_by_id.pop(entity_id, None)
        HEngine.DeactivateSurvivorAgent(monster["entity"])
        transform = monster["transform"]
        transform.Scale = self.HIDDEN_SCALE
        transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
        if monster["entity"].HasComponent("Animator"):
            animator = monster["entity"].GetComponent("Animator")
            animator.SetControllerPath("None")
            animator.Stop()
        pool = self.monster_pools.setdefault(monster["archetype_id"], [])
        pool.append(monster)

    def _kill_monster(self, monster):
        if monster["dead"]:
            return

        monster["dead"] = True
        monster["attacking"] = False
        monster["death_timer"] = HEngine.KillSurvivorAgent(monster["entity"])

        reward = monster.get("reward", 8 if monster["boss"] else 2)
        bRegionRewardLimited = bool(monster.get(
            "region_reward_limited", monster.get("region_spawned", False),
        ))
        reward_zone_id = monster.get(
            "reward_zone_id", monster.get("zone_id", ""),
        )
        reward_encounter_id = monster.get(
            "reward_encounter_id", monster.get("encounter_id", ""),
        )
        if bRegionRewardLimited:
            consume_xp = getattr(self, "_consume_region_xp_reward", None)
            if consume_xp is not None:
                reward = consume_xp(reward_zone_id, reward)
        death_position = monster["transform"].Translation
        self.audio.post("monster_death", death_position)
        if reward > 0:
            self.pending_pickup_spawns.append((
                death_position.x,
                death_position.y,
                death_position.z,
                reward,
                "region" if bRegionRewardLimited else "world",
                reward_encounter_id,
            ))
        self.kills += 1
        if self.quest_tracker is not None:
            self.quest_tracker.record(
                "kills",
                1,
                {
                    "tags": monster.pop("last_damage_tags", ()),
                    "weapon": monster.pop("last_damage_weapon", ""),
                },
            )
            if self.elapsed - self.multikill_window_start > 1.0:
                self.multikill_window_start = self.elapsed
                self.multikill_count = 0
            self.multikill_count += 1
            if self.multikill_count == 5:
                self.quest_tracker.record("multikill_5", 1)
        if monster.get("elite", False):
            self.run_elite_kills += 1
            requested_elite_gold = monster.get("run_gold_reward", 4)
            elite_gold = requested_elite_gold
            if bRegionRewardLimited:
                consume_gold = getattr(self, "_consume_region_gold_reward", None)
                if consume_gold is not None:
                    elite_gold = consume_gold(
                        reward_zone_id,
                        elite_gold,
                        monster.get("fixed_elite", False),
                    )
            self.run_gold += elite_gold
            if not bRegionRewardLimited or elite_gold >= requested_elite_gold:
                self.run_reward_elite_kills += 1
                self.run_elite_bonus_gold += elite_gold
            if self.quest_tracker is not None and (
                    not bRegionRewardLimited or elite_gold > 0):
                self.quest_tracker.record("elite_boss_kills", 1)
        if monster["boss"]:
            self.run_total_boss_kills += 1
            if self.quest_tracker is not None:
                self.quest_tracker.record("boss_kills", 1)
                self.quest_tracker.record("elite_boss_kills", 1)
            if monster.get("objective_boss", False):
                on_objective_killed = getattr(
                    self, "_on_objective_boss_killed", None,
                )
                if on_objective_killed is not None and on_objective_killed(monster):
                    self.run_boss_kills += 1
                    self._finish_run("victory")
            else:
                self.run_elite_kills += 1
                self.run_reward_elite_kills += 1
                if monster.get("chest_tier", 0) > 0:
                    self.pending_chest_rewards.append({
                        "sourceKind": "boss",
                        "sourceId": monster.get("boss_event_id", ""),
                        "zoneId": "",
                        "tier": monster["chest_tier"],
                        "position": (
                            death_position.x,
                            death_position.y,
                            death_position.z,
                        ),
                    })
        self.score += 300 if monster["boss"] else 35

    def _spawn_experience(
            self,
            position,
            value,
            source_kind="world",
            encounter_id=""):
        source_key = str(encounter_id)
        if len(self.pickups) >= self.MAX_PICKUPS:
            nearest = next((
                pickup for pickup in self.pickups
                if source_key in pickup.get("source_values", {})
            ), self.pickups[0])
            source_values = nearest.setdefault(
                "source_values",
                {str(nearest.get("encounter_id", "")): nearest["value"]},
            )
            source_values[source_key] = source_values.get(source_key, 0.0) + value
            nearest["value"] += value
            if len(source_values) == 1:
                nearest["encounter_id"] = source_key
                nearest["source_kind"] = str(source_kind)
            else:
                nearest["encounter_id"] = ""
                nearest["source_kind"] = "mixed"
            nearest["scale_bonus"] = min(0.16, nearest["scale_bonus"] + 0.012)
            HEngine.SetSurvivorPickupScaleBonus(
                nearest["entity"],
                nearest["activation_id"],
                nearest["scale_bonus"],
            )
            return

        scatter_x = self._random_uniform(-0.32, 0.32)
        scatter_z = self._random_uniform(-0.32, 0.32)
        pickup_x = position.x + scatter_x
        pickup_z = position.z + scatter_z
        pickup_probe = HEngine.vec3(pickup_x, position.y, pickup_z)
        base_y = self._grounded_y(
            pickup_probe,
            self.PICKUP_GROUND_OFFSET,
            position.y,
        )

        if self.pickup_pool:
            pickup = self.pickup_pool.pop()
            entity = pickup["entity"]
            transform = pickup["transform"]
        else:
            spawn_pos = HEngine.vec3(pickup_x, base_y, pickup_z)
            entity = HEngine.Instantiate(self.EXPERIENCE_PREFAB, spawn_pos)
            if not entity.HasComponent("Transform"):
                return
            transform = entity.GetComponent("Transform")
            pickup = {"entity": entity, "transform": transform}

        transform.Translation = HEngine.vec3(pickup_x, base_y, pickup_z)
        transform.Scale = self.GEM_SCALE
        phase = self._random_uniform(0.0, 6.28318)
        rotation = self._random_uniform(0.0, 6.28318)
        self.pickup_activation_serial += 1
        pickup.update({
            "activation_id": self.pickup_activation_serial,
            "value": value,
            "scale_bonus": 0.0,
            "source_kind": str(source_kind),
            "encounter_id": str(encounter_id),
            "source_values": {str(encounter_id): value},
        })
        entity_id = HEngine.RegisterSurvivorPickup(
            entity,
            pickup["activation_id"],
            base_y,
            phase,
            rotation,
            0.0,
        )
        pickup["entity_id"] = entity_id
        self.pickups_by_id[entity_id] = pickup
        self.pickups.append(pickup)

    def _drain_pending_chest_spawns(self):
        if not self.pending_chest_rewards:
            return
        reward = self.pending_chest_rewards.pop(0)
        x, y, z = reward["position"]
        if self.chest_pool:
            chest = self.chest_pool.pop()
            entity = chest["entity"]
            transform = chest["transform"]
        else:
            entity = HEngine.Instantiate(
                self.BOSS_CHEST_PREFAB,
                HEngine.vec3(x, y, z),
            )
            if not entity.HasComponent("Transform"):
                raise RuntimeError("Boss chest prefab requires Transform")
            transform = entity.GetComponent("Transform")
            chest = {"entity": entity, "transform": transform}
        transform.Translation = HEngine.vec3(x, y + 0.18, z)
        transform.Scale = HEngine.vec3(0.72, 0.72, 0.72)
        chest.update({
            "tier": reward["tier"],
            "sourceKind": reward.get("sourceKind", "boss"),
            "sourceId": reward.get("sourceId", ""),
            "zoneId": reward.get("zoneId", ""),
            "baseY": y + 0.18,
            "age": 0.0,
        })
        self.active_chests.append(chest)
        HEngine.VFX.PlayEffectAdvanced(
            self.BOSS_CHEST_EFFECT,
            x, y + 0.10, z,
            0.0, 0.0, -1.0,
            0.52, 1.0,
        )

    def _update_chests(self, player_pos, dt):
        for chest in tuple(self.active_chests):
            chest["age"] += dt
            transform = chest["transform"]
            position = transform.Translation
            position.y = chest["baseY"] + self._sin_approx(
                chest["age"] * 2.4,
            ) * 0.08
            transform.Translation = position
            transform.Rotation = HEngine.vec3(
                0.0,
                chest["age"] * 0.8,
                0.0,
            )
            dx = player_pos.x - position.x
            dz = player_pos.z - position.z
            if dx * dx + dz * dz > 1.45 * 1.45:
                continue
            result = self._resolve_boss_chest(chest["tier"])
            self.active_chests.remove(chest)
            transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
            transform.Scale = self.HIDDEN_SCALE
            self.chest_pool.append(chest)
            self.banner_timer = 2.4
            self.banner_key = "chest_" + result["kind"] + "_banner"
            if self.document_id:
                self._set_hud_text("banner", self._text(self.banner_key))

    def _update_pickups(self, player_pos, dt):
        for entity_id, activation_id in HEngine.UpdateSurvivorPickups(
                player_pos,
                dt,
                self.magnet_range * (
                    1.0 + self.trinket_state.get("magnetStacks", 0) * 0.05
                ),
                self.pickup_range,
                self.GEM_SCALE,
        ):
            pickup = self.pickups_by_id.get(entity_id)
            if (pickup is None or
                    pickup.get("activation_id", -1) != activation_id):
                continue
            self._collect_pickup(pickup)

    def _collect_pickup(self, pickup):
        if pickup not in self.pickups:
            return

        self.pickups.remove(pickup)
        entity_id = pickup.get("entity_id")
        if self.pickups_by_id.get(entity_id) is pickup:
            self.pickups_by_id.pop(entity_id, None)
        value = pickup["value"]
        transform = pickup["transform"]
        transform.Scale = self.HIDDEN_SCALE
        transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
        self.pickup_pool.append(pickup)
        self.collected_shards += value
        self.score += int(round(value * 5))
        self.audio.post("xp_pickup")
        self._on_xp_pickup_trinkets()
        if self.quest_tracker is not None:
            self.quest_tracker.record("xp_collected", value)
        self._add_experience(value)

    @staticmethod
    def _try_grounded_y(probe_position, ground_offset):
        floor_height = HEngine.RaycastFloorHeight(probe_position, 12.0, 32.0)
        if floor_height is None:
            return None
        return float(floor_height) + ground_offset

    @classmethod
    def _grounded_y(cls, probe_position, ground_offset, fallback_y):
        grounded_y = cls._try_grounded_y(probe_position, ground_offset)
        return fallback_y if grounded_y is None else grounded_y

    def _update_player_ground_safety(self, player_transform):
        position = player_transform.Translation
        floor_height = HEngine.RaycastFloorHeight(position, 4.0, 12.0)
        inside_bounds = (
            abs(position.x) <= self.PLAYABLE_HALF_EXTENT and
            abs(position.z) <= self.PLAYABLE_HALF_EXTENT
        )
        if floor_height is not None and inside_bounds:
            grounded_y = float(floor_height) + self.PLAYER_GROUND_OFFSET
            if abs(position.y - grounded_y) <= self.PLAYER_SAFE_GROUND_DISTANCE:
                self.last_safe_player_position = HEngine.vec3(
                    position.x,
                    grounded_y,
                    position.z,
                )

        if (floor_height is not None and inside_bounds and
                position.y >= self.FALL_RECOVERY_Y):
            return

        recovery = HEngine.vec3(
            self.last_safe_player_position.x,
            self.last_safe_player_position.y,
            self.last_safe_player_position.z,
        )
        player_transform.Translation = recovery
        self.player.Teleport(recovery)
        HEngine.HE_CORE_WARN("[SurvivorGame] Player recovered from outside the arena")

    def _set_player_input_enabled(self, enabled):
        if self.player is not None and self.player.HasComponent("CharacterMovement"):
            self.player.SetMovementInputEnabled(enabled)

    def _random_uniform(self, minimum, maximum):
        self.random_state = (1664525 * self.random_state + 1013904223) & 0xFFFFFFFF
        fraction = self.random_state / 4294967295.0
        return minimum + (maximum - minimum) * fraction

    @staticmethod
    def _sin_approx(value):
        pi = 3.141592653589793
        value = (value + pi) % (2.0 * pi) - pi
        value2 = value * value
        return value * (1.0 - value2 / 6.0 + value2 * value2 / 120.0)

    @staticmethod
    def _atan2(y, x):
        pi = 3.141592653589793
        abs_y = abs(y) + 0.0000001
        if x >= 0.0:
            ratio = (x - abs_y) / (x + abs_y)
            angle = pi * 0.25 - pi * 0.25 * ratio
        else:
            ratio = (x + abs_y) / (abs_y - x)
            angle = pi * 0.75 - pi * 0.25 * ratio
        return -angle if y < 0.0 else angle
