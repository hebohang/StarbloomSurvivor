"""Runtime-only DomainPower controller for the four Region rewards.

Domain powers intentionally bypass the normal weapon pool, weapon slots,
weapon quests, critical hits, Trinket callbacks, and weapon echo/proc paths.
The deterministic configuration and state-machine rules live in
``SurvivorRegionObjectives`` so their contracts can run without HEngine.
"""

import math

import HEngine

from SurvivorRegionObjectives import DOMAIN_IDS, DOMAIN_POWER_CONFIG
from SurvivorRuntimeAssets import asset_path


def _structured_domain_id(domain_id):
    if domain_id in DOMAIN_POWER_CONFIG:
        return domain_id
    candidate = "domain_" + str(domain_id)
    if candidate in DOMAIN_POWER_CONFIG:
        return candidate
    raise ValueError("unknown DomainPower: " + str(domain_id))


def _domain_kind(domain_id):
    structured = _structured_domain_id(domain_id)
    return structured[len("domain_"):]


class SurvivorDomainPowersMixin:
    DOMAIN_GLOBAL_VFX_SPACING = 1.10

    def _reset_domain_powers(self):
        self.domain_power_states = {
            domain_id: {
                "acquired": False,
                "cooldown": 0.0,
                "casts": 0,
            }
            for domain_id in DOMAIN_IDS
        }
        self.domain_power_order = []
        self.domain_power_effects = []
        self.domain_global_vfx_spacing = 0.0
        self.domain_activation_overcharges = set()
        self.domain_telemetry = {
            domain_id: {
                "casts": 0,
                "hits": 0,
                "damage": 0.0,
                "kills": 0,
                "controlTime": 0.0,
                "visualDegrades": 0,
            }
            for domain_id in DOMAIN_IDS
        }

    def _grant_domain_power(self, domain_id):
        domain_id = _structured_domain_id(domain_id)
        state = self.domain_power_states[domain_id]
        if state["acquired"]:
            return False
        state["acquired"] = True
        # Newly earned powers are deliberately staggered.  This also guarantees
        # that earning several powers through a deterministic capture fixture
        # cannot produce four opaque VFX on the same frame.
        state["cooldown"] = 1.25 + len(self.domain_power_order) * 1.10
        self.domain_power_order.append(domain_id)
        return True

    def _has_equipped_weapon_tag(self, tag):
        tag_cache = getattr(self, "weapon_tag_cache", {})
        return any(
            self._weapon_level(weapon_id) > 0
            and tag in tag_cache.get(weapon_id, ())
            for weapon_id in getattr(self, "weapon_slots", ())
        )

    def _domain_damage_scale(self):
        completed = len(getattr(self, "domain_power_order", ()))
        level = max(1, int(getattr(self, "level", 1)))
        return (1.0 + (level - 1) * 0.035) * (1.0 + completed * 0.08)

    def _domain_candidates(self, x, y, z, radius):
        return [
            monster
            for _, monster in self._weapon_candidates(x, y, z, radius)
            if not monster.get("dead", False)
        ]

    def _densest_domain_point(self, player_pos, search_radius, cluster_radius):
        rows = HEngine.SelectDensestSurvivorAgents(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            search_radius,
            self.WEAPON_VERTICAL_RANGE,
            cluster_radius,
            1,
        )
        for _, entity_id, activation_id, x, y, z, _, _ in rows:
            target = self._resolve_survivor_target(entity_id, activation_id)
            if target is not None and not target.get("dead", False):
                return (float(x), float(y), float(z), target)
        candidates = self._domain_candidates(
            player_pos.x, player_pos.y, player_pos.z, search_radius,
        )
        if not candidates:
            return None
        target = candidates[0]
        position = target["transform"].Translation
        return (position.x, position.y, position.z, target)

    def _play_domain_effect(self, domain_id, key_suffix, x, y, z, scale, speed=1.0):
        domain_id = _structured_domain_id(domain_id)
        role_by_suffix = {
            "telegraph-vfx": "castVfx",
            "vfx": "impactVfx",
            "overcharge-vfx": "overchargeVfx",
        }
        role = role_by_suffix.get(key_suffix, key_suffix)
        key = DOMAIN_POWER_CONFIG[domain_id]["assetKeys"][role]
        if getattr(self, "particle_density", "auto") == "low":
            # Telegraphs remain present; only their decorative footprint is
            # reduced.  This counter is included in the independent domain
            # telemetry and never in weapon visual-degrade statistics.
            scale *= 0.82
            self.domain_telemetry[domain_id]["visualDegrades"] += 1
        return HEngine.VFX.PlayEffectAdvanced(
            asset_path(key),
            x, y, z,
            0.0, 0.0, -1.0,
            scale, speed,
            0,  # GameplayCritical: never hidden by decorative throttling.
        )

    def _apply_domain_status(self, target, status_id, magnitude, duration):
        apply_status = getattr(HEngine, "ApplySurvivorAgentStatus", None)
        if apply_status is None or target.get("dead", False):
            return 0.0
        accepted, applied_duration, _ = apply_status(
            target["entity"],
            status_id,
            max(0.0, float(magnitude)),
            max(0.0, float(duration)),
            target.get("activation_id", 0),
        )
        return float(applied_duration) if accepted else 0.0

    def _apply_domain_damage(
            self,
            domain_id,
            target,
            damage,
            origin_x,
            origin_z,
            force=0.0):
        """Apply structured domain damage without entering weapon proc paths."""

        domain_id = _structured_domain_id(domain_id)
        if target.get("dead", False):
            return 0.0
        if target.get("domain_vulnerability_remaining", 0.0) > 0.0:
            damage *= 1.0 + target.get("domain_vulnerability", 0.08)
        damage = max(0.0, float(damage))
        applied = min(damage, max(0.0, float(target.get("health", 0.0))))
        position = target["transform"].Translation
        direction_x = position.x - origin_x
        direction_z = position.z - origin_z
        length = max(0.001, math.sqrt(direction_x * direction_x + direction_z * direction_z))
        if target.get("boss", False):
            force = 0.0
        target["health"] = HEngine.ApplySurvivorAgentHit(
            target["entity"],
            damage,
            direction_x / length * force,
            direction_z / length * force,
        )
        telemetry = self.domain_telemetry[domain_id]
        telemetry["hits"] += 1
        telemetry["damage"] += applied
        target["last_damage_domain"] = domain_id
        target.pop("last_damage_weapon", None)
        target["last_damage_tags"] = ("domain", domain_id)
        if target["health"] <= 0.0:
            telemetry["kills"] += 1
            self._kill_monster(target)
        else:
            self.audio.post("monster_hit", position)
        return applied

    def _cast_star_domain(self, player_pos, bOvercharge=False, zone_id=""):
        config = DOMAIN_POWER_CONFIG["domain_star"]
        candidates = self._domain_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            config.get("searchRadius", 14.0),
        )
        if bOvercharge and zone_id:
            candidates = [
                monster for monster in self.monsters
                if not monster.get("dead", False)
                and monster.get("zone_id") == zone_id
            ]
        if not candidates:
            return False
        target = max(
            candidates,
            key=lambda monster: (
                bool(monster.get("objective_boss", False)),
                bool(monster.get("boss", False)),
                bool(monster.get("elite", False)),
                float(monster.get("health", 0.0)),
                -int(monster.get("entity_id", 0)),
            ),
        )
        position = target["transform"].Translation
        radius = config.get("radius", 3.6)
        delay = 0.0 if bOvercharge else config.get("warningSeconds", 0.70)
        self._play_domain_effect(
            "star", "telegraph-vfx", position.x, position.y + 0.04,
            position.z, radius * 0.16, 1.0,
        )
        self.domain_power_effects.append({
            "kind": "star",
            "domain_id": "star",
            "timer": delay,
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "radius": radius,
            "damage": (
                config.get("baseDamage", 26.0)
                + max(0, int(getattr(self, "level", 1)) - 1)
                * config.get("damagePerPlayerLevel", 1.8)
            )
            * self._domain_damage_scale()
            * (2.2 if bOvercharge else 1.0),
            "vulnerability": config.get("vulnerability", 0.08),
            "vulnerabilityDuration": config.get("vulnerabilitySeconds", 3.0),
            "aftershock": False,
        })
        return True

    def _cast_thunder_domain(self, player_pos, bOvercharge=False, zone_id=""):
        config = DOMAIN_POWER_CONFIG["domain_thunder"]
        candidates = self._domain_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            config.get("searchRadius", 13.0),
        )
        if bOvercharge and zone_id:
            candidates = [
                monster for monster in self.monsters
                if not monster.get("dead", False)
                and monster.get("zone_id") == zone_id
            ]
        if not candidates:
            return False
        chain_count = config.get("chainTargetsMin", 4) + min(
            config.get("chainTargetsMax", 6) - config.get("chainTargetsMin", 4),
            len(self.domain_power_order) // 2,
        )
        chain_count = min(chain_count, len(candidates))
        ordered = sorted(
            candidates,
            key=lambda monster: (
                not monster.get("boss", False),
                -float(monster.get("health", 0.0)),
                int(monster.get("entity_id", 0)),
            ),
        )[:chain_count]
        damage = (
            config.get("baseDamage", 18.0)
            + max(0, int(getattr(self, "level", 1)) - 1)
            * config.get("damagePerPlayerLevel", 1.25)
        ) * self._domain_damage_scale()
        if bOvercharge:
            damage *= 2.0
        for target in ordered:
            position = target["transform"].Translation
            self._play_domain_effect(
                "thunder", "vfx", position.x, position.y + 0.35,
                position.z, 0.14, 1.75,
            )
            self._apply_domain_damage(
                "thunder", target, damage,
                player_pos.x, player_pos.z, 0.0,
            )
            controlled = self._apply_domain_status(
                target,
                "interrupt",
                1.0,
                config.get("interruptSeconds", 0.35),
            )
            self.domain_telemetry["domain_thunder"]["controlTime"] += controlled
        return True

    def _cast_water_domain(self, player_pos, bOvercharge=False, zone_id=""):
        config = DOMAIN_POWER_CONFIG["domain_water"]
        point = self._densest_domain_point(
            player_pos,
            config.get("searchRadius", 14.0),
            config.get("radius", 4.2),
        )
        if point is None:
            return False
        x, y, z, _ = point
        radius = config.get("radius", 4.2)
        duration = config.get("slowSeconds", 2.5)
        if self._has_equipped_weapon_tag("water"):
            radius *= 1.15
            duration *= 1.20
        self._play_domain_effect("water", "vfx", x, y + 0.04, z, radius * 0.17, 1.0)
        damage = (
            config.get("baseDamage", 20.0)
            + max(0, int(getattr(self, "level", 1)) - 1)
            * config.get("damagePerPlayerLevel", 1.35)
        ) * self._domain_damage_scale()
        if bOvercharge:
            damage *= 2.2
        candidates = self._domain_candidates(x, y, z, radius)
        if bOvercharge and zone_id:
            candidates = [
                monster for monster in self.monsters
                if not monster.get("dead", False)
                and monster.get("zone_id") == zone_id
            ]
        for target in candidates:
            self._apply_domain_damage(
                "water", target, damage, x, z,
                config.get("pushStrength", 0.70)
                if not target.get("boss", False) else 0.0,
            )
            controlled = self._apply_domain_status(
                target, "slow", config.get("slowStrength", 0.25), duration,
            )
            self.domain_telemetry["domain_water"]["controlTime"] += controlled
        return True

    def _cast_wind_domain(self, player_pos, bOvercharge=False, zone_id=""):
        config = DOMAIN_POWER_CONFIG["domain_wind"]
        point = self._densest_domain_point(
            player_pos,
            config.get("searchRadius", 15.0),
            config.get("radius", 4.5),
        )
        if point is None:
            return False
        x, y, z, _ = point
        duration = config.get("duration", 3.0)
        radius = config.get("radius", 4.5)
        self._play_domain_effect("wind", "vfx", x, y + 0.05, z, radius * 0.16, 1.55)
        self.domain_power_effects.append({
            "kind": "wind",
            "domain_id": "wind",
            "age": 0.0,
            "duration": 0.8 if bOvercharge else duration,
            "tick": 0.0,
            "tick_interval": config.get("tickInterval", 0.50),
            "x": x,
            "y": y,
            "z": z,
            "radius": radius,
            "damage": (
                config.get("baseTickDamage", 8.0)
                + max(0, int(getattr(self, "level", 1)) - 1)
                * config.get("tickDamagePerPlayerLevel", 0.55)
            ) * self._domain_damage_scale() * (2.0 if bOvercharge else 1.0),
            "pull_strength": config.get("pullStrength", 1.15),
            "boss_slow": config.get("bossSlowStrength", 0.18),
            "zone_id": zone_id if bOvercharge else "",
        })
        return True

    def _cast_domain_power(self, domain_id, player_pos, bOvercharge=False, zone_id=""):
        domain_id = _structured_domain_id(domain_id)
        caster = getattr(self, "_cast_" + _domain_kind(domain_id) + "_domain")
        if not caster(player_pos, bOvercharge=bOvercharge, zone_id=zone_id):
            return False
        telemetry = self.domain_telemetry[domain_id]
        telemetry["casts"] += 1
        self.domain_power_states[domain_id]["casts"] += 1
        if not bOvercharge:
            self.domain_power_states[domain_id]["cooldown"] = float(
                DOMAIN_POWER_CONFIG[domain_id]["cooldown"]
            )
            self.domain_global_vfx_spacing = self.DOMAIN_GLOBAL_VFX_SPACING
        return True

    def _trigger_domain_overcharge(self, domain_id, zone_id, player_pos):
        domain_id = _structured_domain_id(domain_id)
        key = (domain_id, zone_id)
        if key in self.domain_activation_overcharges:
            return False
        targets = [
            monster for monster in self.monsters
            if not monster.get("dead", False)
            and monster.get("zone_id") == zone_id
        ]
        config = DOMAIN_POWER_CONFIG[domain_id]
        overcharge = config.get("overcharge", {})
        center_x, center_y, center_z = player_pos.x, player_pos.y, player_pos.z
        anchor = getattr(self, "region_anchors", {}).get(zone_id)
        if anchor is not None:
            center = anchor[1].Translation
            center_x, center_y, center_z = center.x, center.y, center.z
        self._play_domain_effect(
            domain_id,
            "overcharge-vfx",
            center_x,
            center_y + 0.05,
            center_z,
            config.get("radius", 4.0) * overcharge.get("radiusMultiplier", 2.0)
            * 0.15,
            1.0,
        )
        for target in targets:
            if target.get("boss", False):
                fraction = overcharge.get("bossHealthFractionDamage", 0.0)
            elif target.get("elite", False):
                fraction = overcharge.get("eliteHealthFractionDamage", 0.36)
            else:
                fraction = overcharge.get("ordinaryHealthFractionDamage", 0.72)
            if fraction <= 0.0:
                continue
            self._apply_domain_damage(
                domain_id,
                target,
                target.get("max_health", target.get("health", 0.0)) * fraction,
                center_x,
                center_z,
                0.0,
            )
        self.domain_telemetry[domain_id]["casts"] += 1
        self.domain_power_states[domain_id]["casts"] += 1
        self.domain_activation_overcharges.add(key)
        return True

    def _update_domain_effects(self, raw_dt):
        active = []
        for effect in self.domain_power_effects:
            if effect["kind"] == "star":
                effect["timer"] -= raw_dt
                if effect["timer"] > 0.0:
                    active.append(effect)
                    continue
                self._play_domain_effect(
                    "star", "vfx", effect["x"], effect["y"] + 0.08,
                    effect["z"], effect["radius"] * 0.15, 1.65,
                )
                targets = self._domain_candidates(
                    effect["x"], effect["y"], effect["z"], effect["radius"],
                )
                for target in targets:
                    self._apply_domain_damage(
                        "star", target, effect["damage"],
                        effect["x"], effect["z"], 0.0,
                    )
                    if not target.get("dead", False):
                        target["domain_vulnerability"] = effect["vulnerability"]
                        target["domain_vulnerability_remaining"] = max(
                            target.get("domain_vulnerability_remaining", 0.0),
                            effect["vulnerabilityDuration"],
                        )
                if effect.get("aftershock", False):
                    aftershock = dict(effect)
                    aftershock["timer"] = 0.42
                    aftershock["damage"] *= 0.35
                    aftershock["radius"] *= 0.72
                    aftershock["aftershock"] = False
                    active.append(aftershock)
                continue

            effect["age"] += raw_dt
            effect["tick"] -= raw_dt
            if effect["tick"] <= 0.0:
                effect["tick"] += effect.get("tick_interval", 0.50)
                candidates = self._domain_candidates(
                    effect["x"], effect["y"], effect["z"], effect["radius"],
                )
                if effect.get("zone_id"):
                    candidates = [
                        target for target in candidates
                        if target.get("zone_id") == effect["zone_id"]
                    ]
                for target in candidates:
                    self._apply_domain_damage(
                        "wind", target, effect["damage"],
                        effect["x"], effect["z"],
                        -effect.get("pull_strength", 1.15)
                        if not target.get("boss", False) else 0.0,
                    )
                    if target.get("boss", False):
                        controlled = self._apply_domain_status(
                            target,
                            "slow",
                            effect.get("boss_slow", 0.18),
                            effect.get("tick_interval", 0.50) + 0.10,
                        )
                        self.domain_telemetry["domain_wind"]["controlTime"] += controlled
                    else:
                        self.domain_telemetry["domain_wind"]["controlTime"] += effect.get(
                            "tick_interval", 0.50,
                        )
            if effect["age"] < effect["duration"]:
                active.append(effect)
        self.domain_power_effects = active

    def _update_domain_powers(self, player_pos, raw_dt):
        raw_dt = max(0.0, float(raw_dt))
        self.domain_global_vfx_spacing = max(
            0.0, self.domain_global_vfx_spacing - raw_dt,
        )
        for monster in self.monsters:
            if monster.get("domain_vulnerability_remaining", 0.0) > 0.0:
                monster["domain_vulnerability_remaining"] = max(
                    0.0,
                    monster["domain_vulnerability_remaining"] - raw_dt,
                )
        self._update_domain_effects(raw_dt)
        for domain_id in DOMAIN_IDS:
            state = self.domain_power_states[domain_id]
            if state["acquired"]:
                state["cooldown"] = max(0.0, state["cooldown"] - raw_dt)
        if self.domain_global_vfx_spacing > 0.0:
            return
        for domain_id in self.domain_power_order:
            state = self.domain_power_states[domain_id]
            if state["acquired"] and state["cooldown"] <= 0.0:
                if self._cast_domain_power(domain_id, player_pos):
                    break
                # A targetless retry stays cheap and deterministic.
                state["cooldown"] = 0.20

    def _domain_cooldown_snapshot(self):
        return {
            domain_id: {
                "acquired": bool(state["acquired"]),
                "remaining": max(0.0, float(state["cooldown"])),
                "cooldown": float(DOMAIN_POWER_CONFIG[domain_id]["cooldown"]),
            }
            for domain_id, state in self.domain_power_states.items()
        }
