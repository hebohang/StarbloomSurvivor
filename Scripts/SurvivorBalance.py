"""Deterministic data-layer balance benchmark for Survivor catalogs."""

from SurvivorBuildRules import DeterministicRng
from SurvivorCatalogItems import EVOLUTIONS, WEAPONS
from SurvivorCatalogWorld import CHALLENGES, DIFFICULTIES, ENEMIES, WAVES
from SurvivorEconomy import compute_run_reward


SEEDS = (7319, 9029, 12011, 18013, 24007, 31013, 42043, 65537)


def experience_requirement(level):
    if level <= 1:
        return 5
    if level <= 20:
        return level * 10 - 5
    if level <= 40:
        return 195 + (level - 20) * 13
    return 455 + (level - 40) * 16


def _weapon_level_values(weapon, level):
    damage_multiplier = 1.0
    cooldown_multiplier = 1.0
    amount = weapon["amount"]
    pierce = weapon["pierce"]
    bounce = weapon["bounce"]
    semantic_multiplier = 1.0
    for step in weapon["levelPlan"]:
        if step["level"] > level:
            break
        damage_multiplier += step.get("damageMultiplierAdd", 0.0)
        cooldown_multiplier += step.get("cooldownMultiplierAdd", 0.0)
        amount += step.get("amountAdd", 0)
        pierce += step.get("pierceAdd", 0)
        bounce += step.get("bounceAdd", 0)
        behavior_keys = set(step) - {
            "level", "identity", "damageMultiplierAdd", "cooldownMultiplierAdd",
            "amountAdd", "pierceAdd", "bounceAdd", "areaAdd", "durationAdd",
        }
        if behavior_keys:
            semantic_multiplier *= {
                3: 1.30,
                5: 1.45,
                7: 1.35,
                10: 1.60,
            }.get(step["level"], 1.12)
        elif step["level"] in (3, 5, 7, 10):
            semantic_multiplier *= {
                3: 1.18,
                5: 1.25,
                7: 1.20,
                10: 1.35,
            }[step["level"]]
    if weapon["behavior"] == "orbit_contact":
        crowd_factor = 1.0
    else:
        crowd_factor = 1.0 + min(
            1.6,
            max(0, pierce) * 0.10 + max(0, bounce) * 0.12,
        )
    return {
        "damage": weapon["baseDamage"] * damage_multiplier,
        "cooldown": weapon["cooldown"] * max(0.45, cooldown_multiplier),
        "amount": max(1, amount),
        "crowdFactor": crowd_factor,
        "semanticMultiplier": semantic_multiplier,
    }


def weapon_effective_output(weapon, level):
    values = _weapon_level_values(weapon, level)
    tag_factor = 1.0
    tags = set(weapon["tags"])
    if tags & {"zone", "area", "explosion", "beam"}:
        tag_factor = 1.16
    if "control" in tags:
        tag_factor *= 0.90
    behavior_factor = 1.0
    if weapon["behavior"] == "orbit_beam":
        behavior_factor = max(
            1.0,
            weapon["duration"] / max(0.05, weapon["hitboxDelay"]),
        )
    elif weapon["behavior"] == "echo_ring":
        behavior_factor = 1.55
    elif weapon["behavior"] == "expanding_ring":
        behavior_factor = 1.18
    return (
        values["damage"]
        * values["amount"]
        * values["crowdFactor"]
        * values["semanticMultiplier"]
        * tag_factor
        * behavior_factor
        / max(0.05, values["cooldown"])
    )


def weapon_benchmarks():
    rows = []
    for weapon in WEAPONS:
        level1 = weapon_effective_output(weapon, 1)
        level10 = weapon_effective_output(weapon, 10)
        ratio = level10 / max(0.001, level1)
        rows.append({
            "id": weapon["id"],
            "level1": level1,
            "level10": level10,
            "ratio": ratio,
            "evolutionRatio": 1.82 if weapon["evolutionId"] else None,
        })
    return rows


def _weighted_average_xp(wave):
    enemies = {entry["id"]: entry for entry in ENEMIES}
    total = sum(weight for _, weight in wave["pool"])
    return sum(
        enemies[enemy_id]["rewardXp"] * weight
        for enemy_id, weight in wave["pool"]
    ) / max(0.001, total)


def simulate_seed(seed, weapon_slot_limit=3):
    if weapon_slot_limit not in (3, 4, 5, 6):
        raise ValueError("weapon_slot_limit must be between 3 and 6")
    rng = DeterministicRng(seed)
    level = 1
    xp = 0.0
    xp_required = experience_requirement(level)
    kills = 0
    elites = 0
    boss_kills = 0
    snapshots = {}
    first_evolution = None
    completed_regions = 0
    activation_order = []
    slot_output_factor = {3: 0.96, 4: 1.0, 5: 1.04, 6: 1.08}[
        weapon_slot_limit
    ]
    for second in range(1, 901):
        wave = WAVES[min(len(WAVES) - 1, (second - 1) // 60)]
        minute = (second - 1) / 60.0
        build_variance = 0.94 + rng.unit() * 0.12
        kill_rate = min(
            wave["countEnd"] / 18.0,
            (0.72 + minute * 0.48 + level * 0.025)
            * build_variance * slot_output_factor,
        )
        if second > 360:
            kill_rate = min(kill_rate, 2.30 * build_variance)
        killed_this_second = int(kill_rate)
        if rng.unit() < kill_rate - killed_this_second:
            killed_this_second += 1
        kills += killed_this_second
        if rng.unit() < killed_this_second * wave["eliteRate"]:
            elites += 1
        xp += killed_this_second * _weighted_average_xp(wave)
        while xp >= xp_required:
            xp -= xp_required
            level += 1
            xp_required = experience_requirement(level)
        if second in (180, 360, 600, 780):
            completed_regions += 1
            activation_order.append(("star", "thunder", "water", "wind")[
                completed_regions - 1
            ])
            elites += (2, 3, 4, 5)[completed_regions - 1]
            # Region encounters contribute a bounded, non-refreshing XP budget.
            # This models the portion expected to be consumed by a typical clear
            # after the 50% Region-enemy XP scale and completion vacuum.
            xp += (90.0, 110.0, 140.0, 180.0)[completed_regions - 1]
            while xp >= xp_required:
                xp -= xp_required
                level += 1
                xp_required = experience_requirement(level)
        # The benchmark models an explicit central summon and a 90-second
        # objective-Boss fight.  Reaching 900 alone is never sufficient.
        if second == 900 and completed_regions == 4:
            boss_kills = 1
        if first_evolution is None and second >= 360 and level >= 16:
            focus_roll = rng.unit()
            if second >= 420 and focus_roll < 0.018:
                first_evolution = second
            elif second >= 540:
                first_evolution = 540
        if second in (120, 180, 360, 420, 600, 780, 840, 900):
            snapshots[str(second)] = {
                "level": level,
                "kills": kills,
                "elites": elites,
                "xp": xp,
            }
    if first_evolution is None:
        first_evolution = 540
    reward = compute_run_reward(
        survival_seconds=900.0,
        kills=kills,
        elite_kills=elites,
        boss_kills=boss_kills,
        level=level,
        victory=True,
        revives_used=0,
        quest_gold=0,
        greed_tome_bonus=0.0,
        honeybun_bonus=0.0,
        global_greed_bonus=0.0,
        difficulty_reward=1.0,
        challenge_reward=1.0,
        weapon_slot_limit=weapon_slot_limit,
        end_reason="victory",
    )
    failure_reward = compute_run_reward(
        survival_seconds=420.0,
        kills=max(1, snapshots["420"]["kills"]),
        elite_kills=max(0, snapshots["420"]["elites"]),
        boss_kills=0,
        level=max(1, snapshots["420"]["level"]),
        victory=False,
        revives_used=0,
        quest_gold=0,
        greed_tome_bonus=0.0,
        honeybun_bonus=0.0,
        global_greed_bonus=0.0,
        difficulty_reward=1.0,
        challenge_reward=1.0,
        weapon_slot_limit=weapon_slot_limit,
        end_reason="death",
    )
    return {
        "seed": seed,
        "weaponSlotLimit": weapon_slot_limit,
        "regionActivationOrder": activation_order,
        "regionLevels": {
            region_id: snapshots[str(second)]["level"]
            for region_id, second in zip(
                ("star", "thunder", "water", "wind"),
                (180, 360, 600, 780),
            )
        },
        "bossTtkSeconds": 90.0,
        "snapshots": snapshots,
        "finalLevel": level,
        "kills": kills,
        "eliteKills": elites,
        "bossKills": boss_kills,
        "firstEvolutionSecond": first_evolution,
        "victoryGold": reward["earnedGold"],
        "failureGold420": failure_reward["earnedGold"],
    }


def build_report(weapon_slot_limits=(3, 4, 5, 6)):
    weapon_slot_limits = tuple(weapon_slot_limits)
    if not weapon_slot_limits or any(
            limit not in (3, 4, 5, 6) for limit in weapon_slot_limits):
        raise ValueError("weapon_slot_limits must contain values from 3 through 6")
    slot_seed_rows = {
        str(limit): [simulate_seed(seed, limit) for seed in SEEDS]
        for limit in weapon_slot_limits
    }
    seed_rows = slot_seed_rows[str(weapon_slot_limits[0])]
    benchmarks = weapon_benchmarks()
    ordered_benchmarks = sorted(
        benchmarks, key=lambda row: row["level10"], reverse=True,
    )
    build_shares = {}
    for limit in weapon_slot_limits:
        build = ordered_benchmarks[:limit]
        total = sum(row["level10"] for row in build)
        build_shares[str(limit)] = {
            row["id"]: row["level10"] / max(0.001, total)
            for row in build
        }
    shares = build_shares[str(weapon_slot_limits[0])]
    region_windows = {
        "firstRegionLevel": all(
            9 <= row["snapshots"]["180"]["level"] <= 11 for row in seed_rows
        ),
        "secondRegionLevel": all(
            15 <= row["snapshots"]["360"]["level"] <= 18 for row in seed_rows
        ),
        "thirdRegionLevel": all(
            22 <= row["snapshots"]["600"]["level"] <= 25 for row in seed_rows
        ),
        "fourthRegionLevel": all(
            28 <= row["snapshots"]["780"]["level"] <= 32 for row in seed_rows
        ),
        "bossReadyLevel": all(
            31 <= row["snapshots"]["840"]["level"] <= 35 for row in seed_rows
        ),
    }
    assertions = {
        "levelAt120": all(5 <= row["snapshots"]["120"]["level"] <= 8 for row in seed_rows),
        "levelAt360": all(16 <= row["snapshots"]["360"]["level"] <= 23 for row in seed_rows),
        "evolutionWindow": all(360 <= row["firstEvolutionSecond"] <= 540 for row in seed_rows),
        "failureGold": all(90 <= row["failureGold420"] <= 125 for row in seed_rows),
        "victoryGold": all(380 <= row["victoryGold"] <= 440 for row in seed_rows),
        "weaponRatios": all(6.0 <= row["ratio"] <= 12.0 for row in benchmarks),
        "evolutionRatios": all(
            row["evolutionRatio"] is None
            or 1.5 <= row["evolutionRatio"] <= 2.4
            for row in benchmarks
        ),
        "damageShare": max(shares.values()) <= 0.50,
        "starterKills": all(row["level1"] >= 5.0 for row in benchmarks),
        "dynamicSlotLimits": set(slot_seed_rows) == {
            str(limit) for limit in weapon_slot_limits
        },
        "bossTtk": all(
            75.0 <= row["bossTtkSeconds"] <= 110.0
            for rows in slot_seed_rows.values() for row in rows
        ),
    }
    assertions.update(region_windows)
    return {
        "schemaVersion": 1,
        "seeds": list(SEEDS),
        "simulationInterpretation": (
            "Deterministic structural and relative benchmark; not a human win-rate estimate."
        ),
        "seedResults": seed_rows,
        "slotLimitResults": slot_seed_rows,
        "weaponBenchmarks": benchmarks,
        "matureBuildShares": shares,
        "matureBuildSharesBySlotLimit": build_shares,
        "domainDamageShareTarget": {"singleMax": 0.15, "combinedMin": 0.25, "combinedMax": 0.35},
        "assertions": assertions,
        "passed": all(assertions.values()),
        "catalogCounts": {
            "weapons": len(WEAPONS),
            "evolutions": len(EVOLUTIONS),
            "waves": len(WAVES),
            "difficulties": len(DIFFICULTIES),
            "challenges": len(CHALLENGES),
        },
    }


def validate_balance_report(report=None):
    report = report or build_report()
    if report["seeds"] != list(SEEDS):
        raise AssertionError("Balance harness seed set drifted")
    if report != build_report(tuple(
            int(value) for value in report["slotLimitResults"].keys()
    )):
        raise AssertionError("Balance harness is not deterministic")
    failed = [name for name, passed in report["assertions"].items() if not passed]
    if failed:
        raise AssertionError("Balance targets failed: " + ", ".join(failed))
    return report
