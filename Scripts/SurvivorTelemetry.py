"""Bounded, local-only Survivor telemetry aggregation."""

import json
import os


def _percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))
    return ordered[index]


class SurvivorTelemetry:
    def __init__(self, bEnabled=False, output_path=""):
        self.bEnabled = bool(bEnabled)
        self.output_path = output_path
        self.reset()

    def reset(self):
        self.frames = []
        self.minutes = []
        self.last_minute = -1
        self.peak_monsters = 0
        self.peak_projectiles = 0
        self.peak_visuals = 0
        self.attack_damage = {}
        self.chests = 0
        self.evolutions = 0
        self.trinkets = 0
        self.rerolls = 0
        self.skips = 0
        self.banishes = 0
        self.bWritten = False

    def record_attack_damage(self, kind_id, damage):
        if not self.bEnabled:
            return
        row = self.attack_damage.setdefault(kind_id, {"hits": 0, "damage": 0.0})
        row["hits"] += 1
        row["damage"] += max(0.0, float(damage))

    def sample(self, game, dt):
        if not self.bEnabled:
            return
        frame_dt = float(getattr(game, "last_frame_delta_seconds", dt))
        self.frames.append(frame_dt * 1000.0)
        if len(self.frames) > 3600:
            del self.frames[:len(self.frames) - 3600]
        alive = sum(1 for monster in game.monsters if not monster["dead"])
        projectiles = len(game.active_projectiles)
        visuals = (
            len(game.projectile_visual_entities)
            + len(getattr(game, "domain_power_effects", ()))
            + len(getattr(game, "enemy_projectile_effects", {}))
            + len(getattr(game, "enemy_zone_effects", {}))
            + len(getattr(game, "enemy_telegraph_effects", {}))
        )
        self.peak_monsters = max(self.peak_monsters, alive)
        self.peak_projectiles = max(self.peak_projectiles, projectiles)
        self.peak_visuals = max(self.peak_visuals, visuals)
        minute = min(15, int(game.elapsed // 60.0))
        if minute == self.last_minute:
            return
        self.last_minute = minute
        self.minutes.append({
            "minute": minute,
            "elapsed": game.elapsed,
            "alive": alive,
            "kills": game.kills,
            "eliteKills": game.run_elite_kills,
            "bossKills": game.run_boss_kills,
            "level": game.level,
            "experience": game.experience,
            "damageTaken": game.run_damage_taken,
            "damagePrevented": game.run_damage_prevented,
            "healed": game.run_healed,
            "runGold": game.run_gold,
            "projectiles": projectiles,
            "visuals": visuals,
            "trinkets": list(game.trinket_slots),
            "evolutions": dict(game.active_evolutions),
        })

    def report(self, game, end_reason):
        run_config = getattr(game, "run_config", None)
        objective_controller = getattr(game, "objective_controller", None)
        objective = (
            objective_controller.snapshot()
            if objective_controller is not None else
            {"objectiveState": "", "completedRegions": [], "regions": {}}
        )
        encounter_director = getattr(game, "encounter_director", None)
        encounter = (
            encounter_director.snapshot()
            if encounter_director is not None else
            {"spawnFailures": {}, "budgets": {}, "recentKillsPerSecond": 0.0}
        )
        weapon_damage_total = sum(
            max(0.0, float(values.get("damage", 0.0)))
            for values in game.weapon_telemetry.values()
        )
        domain_damage_total = sum(
            max(0.0, float(values.get("damage", 0.0)))
            for values in getattr(game, "domain_telemetry", {}).values()
        )
        attributed_damage_total = max(
            0.001, weapon_damage_total + domain_damage_total,
        )
        return {
            "schemaVersion": 2,
            "detailed": self.bEnabled,
            "endReason": end_reason,
            "runSeed": (
                run_config.run_seed
                if run_config is not None else
                int(getattr(game, "random_state", 0))
            ),
            "difficulty": (
                run_config.selected_difficulty
                if run_config is not None else
                getattr(game, "selected_difficulty", "adventure")
            ),
            "challengeIds": (
                list(run_config.challenge_ids)
                if run_config is not None else
                []
            ),
            "weaponSlotLimit": int(getattr(game, "weapon_slot_limit", 3)),
            "runConfig": run_config.as_dict() if run_config is not None else None,
            "elapsed": game.elapsed,
            "level": game.level,
            "kills": game.kills,
            "eliteKills": game.run_elite_kills,
            "bossKills": game.run_boss_kills,
            "frameMs": {
                "p50": _percentile(self.frames, 0.50),
                "p95": _percentile(self.frames, 0.95),
                "p99": _percentile(self.frames, 0.99),
            },
            "peaks": {
                "monsters": self.peak_monsters,
                "gameplayProjectiles": self.peak_projectiles,
                "projectileVisuals": self.peak_visuals,
                "vfx": self.peak_visuals,
            },
            "attackDamage": dict(self.attack_damage),
            "weapons": {
                weapon_id: dict(
                    values,
                    damageShare=max(0.0, float(values.get("damage", 0.0)))
                    / attributed_damage_total,
                )
                for weapon_id, values in game.weapon_telemetry.items()
                if values["casts"] or values["damage"]
            },
            "objective": {
                "state": objective.get("objectiveState", ""),
                "activationOrder": list(objective.get("completedRegions", ())),
                "regions": objective.get("regions", {}),
                "localAliveSamples": {
                    region_id: list(samples)
                    for region_id, samples in getattr(
                        game, "region_local_alive_samples", {},
                    ).items()
                },
                "spawnFailures": dict(encounter.get("spawnFailures", {})),
                "encounterBudgets": dict(encounter.get("budgets", {})),
                "recentKillsPerSecond": float(
                    encounter.get("recentKillsPerSecond", 0.0)
                ),
                "healthLost": dict(getattr(game, "region_health_lost", {})),
                "fixedElites": dict(getattr(
                    game, "region_fixed_elites_spawned", {},
                )),
                "randomElites": dict(getattr(
                    game, "region_random_elites_spawned", {},
                )),
            },
            "domains": {
                domain_id: dict(
                    values,
                    damageShare=max(0.0, float(values.get("damage", 0.0)))
                    / attributed_damage_total,
                )
                for domain_id, values in getattr(
                    game, "domain_telemetry", {},
                ).items()
            },
            "boss": {
                "ttkSeconds": float(getattr(game, "objective_boss_ttk", 0.0)),
                "phaseDurations": dict(getattr(
                    game, "objective_boss_phase_durations", {},
                )),
                "enraged": bool(getattr(game, "objective_boss_enraged", False)),
            },
            "projectileBudget": {
                "retry": game.projectile_budget.retry_count,
                "visualDegrade": game.projectile_budget.visual_degrade_count,
                "rejected": game.projectile_budget.rejected_count,
                "generation": game.projectile_budget.generation,
            },
            "poolControls": {
                "rerolls": self.rerolls,
                "skips": self.skips,
                "banishes": self.banishes,
            },
            "chests": self.chests,
            "evolutions": self.evolutions,
            "trinkets": self.trinkets,
            "minutes": list(self.minutes),
        }

    def write(self, game, end_reason):
        if not self.bEnabled or not self.output_path or self.bWritten:
            return ""
        report = self.report(game, end_reason)
        directory = os.path.dirname(os.path.abspath(self.output_path))
        os.makedirs(directory, exist_ok=True)
        temporary = self.output_path + ".tmp." + str(os.getpid())
        with open(temporary, "w", encoding="utf-8", newline="\n") as output:
            json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.output_path)
        self.bWritten = True
        return self.output_path
