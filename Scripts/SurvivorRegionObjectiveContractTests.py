"""Headless contracts for Survivor region objectives and immutable RunConfig."""

import io
import itertools
import unittest

import SurvivorRegionObjectives as Objectives
import SurvivorRunConfig


CHALLENGES = (
    {"id": "swarm", "enemyCount": 1.65, "enemySpeed": 1.15, "xp": 0.80, "gold": 1.45},
    {"id": "chonk", "enemyHealth": 2.0, "enemyDamage": 1.45, "gold": 1.55},
    {"id": "fragile_star", "playerMaxHealth": 1, "gold": 2.0},
    {"id": "hurry", "clock": 1.5, "xp": 1.25, "gold": 1.50},
    {"id": "no_trinkets", "disableTrinkets": True, "gold": 1.35},
    {
        "id": "cursed_bloom",
        "healthPerMinute": 0.08,
        "damagePerMinute": 0.05,
        "spawnPerMinute": 0.05,
        "gold": 2.0,
    },
)


def _center(region_id):
    position = Objectives.REGION_CONFIG[region_id]["authoredPosition"]
    return float(position[0]), float(position[2])


def _enter_assault(controller, region_id="star"):
    x, z = _center(region_id)
    events = controller.update(1.5, x, z)
    if controller.region_states[region_id].state != Objectives.REGION_ASSAULT:
        raise AssertionError("fixture did not enter ASSAULT: {0!r}".format(events))
    return x, z


class RegionConfigurationContracts(unittest.TestCase):
    def test_authoritative_region_mapping_and_hysteresis(self):
        expected = {
            "star": ("EventAnchor_NorthRift", 9.0),
            "thunder": ("EventAnchor_WestShrine", 7.5),
            "water": ("EventAnchor_SouthWetland", 9.0),
            "wind": ("EventAnchor_EastBasin", 11.0),
        }
        self.assertEqual(tuple(Objectives.REGION_CONFIG), Objectives.REGION_IDS)
        for region_id, (tag, radius) in expected.items():
            row = Objectives.REGION_CONFIG[region_id]
            self.assertEqual(row["anchorTag"], tag)
            self.assertEqual(row["clearRadius"], radius)
            self.assertEqual(row["enterRadius"], radius - 0.50)
            self.assertEqual(row["holdRadius"], radius - 0.25)
            self.assertLess(row["enterRadius"], row["holdRadius"])
        with self.assertRaises(TypeError):
            Objectives.REGION_CONFIG["star"]["clearRadius"] = 1.0

    def test_domain_power_contract_and_proc_boundary(self):
        self.assertEqual(
            Objectives.DOMAIN_IDS,
            ("domain_star", "domain_thunder", "domain_water", "domain_wind"),
        )
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_star"]["cooldown"], 14.0)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_star"]["warningSeconds"], 0.70)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_star"]["vulnerability"], 0.08)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_star"]["vulnerabilitySeconds"], 3.0)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_thunder"]["cooldown"], 11.0)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_thunder"]["chainTargetsMin"], 4)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_thunder"]["chainTargetsMax"], 6)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_thunder"]["interruptSeconds"], 0.35)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_water"]["cooldown"], 15.0)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_water"]["slowStrength"], 0.25)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_water"]["slowSeconds"], 2.5)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_wind"]["cooldown"], 17.0)
        self.assertEqual(Objectives.DOMAIN_POWER_CONFIG["domain_wind"]["duration"], 3.0)
        self.assertEqual(Objectives.DOMAIN_GLOBAL_VFX_SPACING, 1.10)
        for domain_id in Objectives.DOMAIN_IDS:
            row = Objectives.DOMAIN_POWER_CONFIG[domain_id]
            self.assertTrue(row["id"].startswith("domain_"))
            self.assertTrue(all(row["assetKeys"].values()))
            self.assertGreaterEqual(
                row["overcharge"]["ordinaryHealthFractionDamage"], 0.65,
            )
            self.assertEqual(row["overcharge"]["bossHealthFractionDamage"], 0.0)
        self.assertNotIn("synergy", Objectives.DOMAIN_POWER_CONFIG["domain_star"])
        self.assertNotIn("synergy", Objectives.DOMAIN_POWER_CONFIG["domain_thunder"])
        self.assertNotIn("synergy", Objectives.DOMAIN_POWER_CONFIG["domain_wind"])
        self.assertEqual(
            Objectives.DOMAIN_POWER_CONFIG["domain_water"]["synergy"]["telemetryOwner"],
            "domain_water",
        )
        policy = Objectives.DOMAIN_PROC_POLICY
        self.assertFalse(policy["entersWeaponSlots"])
        self.assertFalse(policy["entersUpgradePool"])
        self.assertFalse(policy["countsForWeaponQuests"])
        self.assertFalse(policy["allowsTrinketProcs"])
        self.assertFalse(policy["allowsRecursiveProcs"])


class RegionStateMachineContracts(unittest.TestCase):
    def test_arming_requires_continuous_one_point_five_seconds(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _center("star")
        controller.update(0.75, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ARMING)
        controller.update(0.01, x + 20.0, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_DORMANT)
        controller.update(1.49, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ARMING)
        events = controller.update(0.01, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ASSAULT)
        self.assertIn("region_assault_started", [event["type"] for event in events])
        self.assertEqual(controller.region_states["star"].attempts, 1)

    def test_entry_and_hold_thresholds_form_hysteresis(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _center("star")
        controller.update(0.5, x + 8.6, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_DORMANT)
        controller.update(0.5, x, z)
        controller.update(0.5, x + 8.6, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ARMING)

    def test_assault_uses_exact_raw_gameplay_seconds(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _enter_assault(controller)
        controller.update(59.99, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ASSAULT)
        self.assertAlmostEqual(controller.region_states["star"].assault_elapsed, 59.99)
        events = controller.update(0.01, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ACTIVATED)
        self.assertEqual(events[0]["type"], "region_activated")

    def test_pause_upgrade_or_settings_gate_does_not_advance(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _enter_assault(controller)
        raw_before = controller.raw_elapsed
        controller.update(20.0, x, z, gameplay_active=False)
        state = controller.region_states["star"]
        self.assertEqual(state.assault_elapsed, 0.0)
        self.assertEqual(controller.raw_elapsed, raw_before)

    def test_outside_grace_pauses_and_preserves_progress_on_return(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _enter_assault(controller)
        controller.update(20.0, x, z)
        progress = controller.region_states["star"].assault_elapsed
        controller.update(0.1, x + 20.0, z)
        self.assertEqual(
            controller.region_states["star"].state,
            Objectives.REGION_OUTSIDE_GRACE,
        )
        controller.update(1.25, x + 20.0, z)
        self.assertEqual(
            controller.region_states["star"].state,
            Objectives.REGION_OUTSIDE_GRACE,
        )
        self.assertEqual(controller.region_states["star"].assault_elapsed, progress)
        controller.update(0.01, x, z)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_ASSAULT)
        self.assertEqual(controller.region_states["star"].assault_elapsed, progress)

    def test_grace_expiry_resets_and_runs_twelve_second_cooldown(self):
        controller = Objectives.RegionObjectiveController()
        x, z = _enter_assault(controller)
        controller.update(31.0, x, z)
        controller.update(0.01, x + 20.0, z)
        events = controller.update(1.251, x + 20.0, z)
        state = controller.region_states["star"]
        self.assertEqual(state.state, Objectives.REGION_COOLDOWN)
        self.assertEqual(state.assault_elapsed, 0.0)
        self.assertEqual(state.cooldown_remaining, 12.0)
        self.assertEqual(state.failure_count, 1)
        self.assertEqual(
            [event["type"] for event in events],
            ["stop_region_spawns", "region_failed", "region_cooldown_started"],
        )
        self.assertFalse(controller.is_region_spawn_enabled())
        controller.update(11.999, x, z)
        self.assertEqual(state.state, Objectives.REGION_COOLDOWN)
        controller.update(0.001, x, z)
        self.assertEqual(state.state, Objectives.REGION_DORMANT)
        self.assertIsNone(controller.active_region_id)

    def test_only_one_region_is_active(self):
        # Overlap two centers in the pure fixture so both are eligible during
        # the same update; stable REGION_IDS order must select exactly one.
        controller = Objectives.RegionObjectiveController(region_positions={
            "star": (0.0, 0.0),
            "thunder": (0.0, 0.0),
        })
        controller.update(0.5, 0.0, 0.0)
        self.assertEqual(controller.active_region_id, "star")
        self.assertEqual(controller.region_states["thunder"].state, Objectives.REGION_DORMANT)

    def test_completion_reward_order_and_idempotency(self):
        controller = Objectives.RegionObjectiveController()
        actions = controller.complete_region("water")
        self.assertEqual(
            [event["type"] for event in actions[:8]],
            [
                "region_activated",
                "stop_region_spawns",
                "grant_domain_power",
                "domain_overcharge",
                "vacuum_encounter_xp",
                "spawn_region_chest",
                "region_state_updated",
                "retire_excess_region_monsters",
            ],
        )
        self.assertEqual(actions[5]["tier"], 1)
        self.assertEqual(actions[5]["sourceKind"], "region_completion")
        self.assertEqual(actions[5]["zoneId"], "water")
        self.assertEqual(controller.complete_region("water"), ())
        self.assertEqual(controller.completed_regions, ["water"])

    def test_all_twenty_four_orders_reach_boss_ready(self):
        for order in itertools.permutations(Objectives.REGION_IDS):
            controller = Objectives.RegionObjectiveController()
            tiers = []
            for region_id in order:
                actions = controller.complete_region(region_id)
                chest = next(row for row in actions if row["type"] == "spawn_region_chest")
                tiers.append(chest["tier"])
            self.assertEqual(controller.completed_regions, list(order))
            self.assertEqual(tiers, [1, 2, 2, 3])
            self.assertEqual(controller.objective_state, Objectives.OBJECTIVE_BOSS_READY)

    def test_revive_preserves_complete_regions_and_fails_current_assault(self):
        controller = Objectives.RegionObjectiveController()
        controller.complete_region("wind")
        x, z = _enter_assault(controller, "star")
        controller.update(12.0, x, z)
        events = controller.on_revive()
        self.assertEqual(controller.region_states["wind"].state, Objectives.REGION_ACTIVATED)
        self.assertEqual(controller.region_states["star"].state, Objectives.REGION_COOLDOWN)
        self.assertEqual(controller.region_states["star"].assault_elapsed, 0.0)
        self.assertIn("region_failed", [event["type"] for event in events])

    def test_nine_hundred_seconds_neither_completes_regions_nor_spawns_boss(self):
        controller = Objectives.RegionObjectiveController()
        controller.update(900.0, 30.0, 30.0)
        self.assertEqual(controller.objective_state, Objectives.OBJECTIVE_EXPLORATION)
        self.assertEqual(controller.completed_regions, [])
        self.assertFalse(controller.boss_spawn_request_issued)


class BossObjectiveContracts(unittest.TestCase):
    def _boss_ready(self):
        controller = Objectives.RegionObjectiveController()
        for region_id in Objectives.REGION_IDS:
            controller.complete_region(region_id)
        return controller

    def test_zero_to_three_regions_cannot_arm_central_summon(self):
        for count in range(4):
            controller = Objectives.RegionObjectiveController()
            for region_id in Objectives.REGION_IDS[:count]:
                controller.complete_region(region_id)
            controller.update(20.0, 0.0, 0.0)
            self.assertNotIn(
                controller.objective_state,
                (Objectives.OBJECTIVE_BOSS_INTRO, Objectives.OBJECTIVE_BOSS_ACTIVE),
            )

    def test_central_hold_intro_and_one_explicit_spawn_request(self):
        controller = self._boss_ready()
        controller.update(1.0, 0.0, 0.0)
        controller.update(0.1, 10.0, 0.0)
        self.assertEqual(controller.central_hold_elapsed, 0.0)
        controller.update(2.0, 0.0, 0.0)
        self.assertEqual(controller.objective_state, Objectives.OBJECTIVE_BOSS_INTRO)
        events = controller.update(3.0, 0.0, 0.0)
        self.assertEqual(controller.objective_state, Objectives.OBJECTIVE_BOSS_ACTIVE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "boss_spawn_requested")
        self.assertEqual(events[0]["archetypeId"], "star_dragon")
        self.assertEqual(controller.update(3.0, 0.0, 0.0), ())

    def test_only_registered_objective_event_can_win(self):
        controller = self._boss_ready()
        controller.update(2.0, 0.0, 0.0)
        controller.update(3.0, 0.0, 0.0)
        event_id = Objectives.OBJECTIVE_CONFIG["objectiveBossEventId"]
        self.assertFalse(controller.mark_boss_spawned("fake_event", 10, 1))
        self.assertTrue(controller.mark_boss_spawned(event_id, 10, 7))
        self.assertFalse(controller.mark_boss_killed(event_id, False, 10, 7, final_boss=True))
        self.assertFalse(controller.mark_boss_killed("fake_event", True, 10, 7))
        self.assertFalse(controller.mark_boss_killed(event_id, True, 11, 7))
        self.assertTrue(controller.mark_boss_killed(event_id, True, 10, 7))
        self.assertEqual(controller.objective_state, Objectives.OBJECTIVE_VICTORY)
        self.assertFalse(controller.mark_boss_killed(event_id, True, 10, 7))


class EncounterDirectorContracts(unittest.TestCase):
    def test_local_targets_and_difficulty_challenge_cap(self):
        director = Objectives.EncounterDirector()
        self.assertEqual(director.local_target(1, 0.0), 50)
        self.assertEqual(director.local_target(1, 1.0), 85)
        self.assertEqual(director.local_target(2, 1.0), 120)
        self.assertEqual(director.local_target(3, 1.0), 160)
        self.assertEqual(director.local_target(4, 1.0), 210)
        self.assertEqual(director.local_target(1, 1.0, "fierce"), 98)
        self.assertEqual(director.local_target(4, 1.0, "nightmare", 1.65), 320)
        self.assertEqual(Objectives.ENCOUNTER_TIERS[0]["healthMultiplier"], 1.0)
        self.assertEqual(Objectives.ENCOUNTER_TIERS[3]["healthMultiplier"], 1.72)
        self.assertEqual(Objectives.ENCOUNTER_TIERS[3]["damageMultiplier"], 1.38)

    def test_kill_rate_ewma_is_deterministic_and_spawn_rate_bounded(self):
        first = Objectives.KillRateEWMA()
        second = Objectives.KillRateEWMA()
        samples = ((1.0, 5), (1.0, 10), (2.0, 4), (1.0, 0))
        for raw_dt, kills in samples:
            self.assertAlmostEqual(
                first.update(raw_dt, kills), second.update(raw_dt, kills), places=12,
            )
        director = Objectives.EncounterDirector()
        self.assertEqual(director.spawn_rate(1, recent_kills_per_second=0.0), 5.0)
        self.assertEqual(director.spawn_rate(1, recent_kills_per_second=100.0), 8.0)
        self.assertGreater(
            director.spawn_rate(1, "fierce", 1.65, 0.0), 5.0,
        )

    def test_local_alive_counts_only_radius_and_encounter(self):
        rows = [
            {"entityId": 1, "encounterId": "star:run", "x": 0.0, "z": 0.0},
            {"entityId": 2, "encounterId": "star:run", "x": 23.9, "z": 0.0},
            {"entityId": 3, "encounterId": "star:run", "x": 24.1, "z": 0.0},
            {"entityId": 4, "encounterId": "world", "x": 0.0, "z": 0.0},
            {"entityId": 5, "encounterId": "star:run", "x": 0.0, "z": 0.0, "dead": True},
        ]
        self.assertEqual(
            Objectives.EncounterDirector.count_local_alive(
                rows, 0.0, 0.0, "star:run",
            ),
            2,
        )

    def test_far_world_population_does_not_suppress_local_refill_below_cap(self):
        director = Objectives.EncounterDirector()
        director.begin_attempt("star", 1, 1, "star:run")
        plan = director.plan_spawn(
            1.0, 10.0, local_alive=0, total_alive=100,
        )
        self.assertGreater(plan["spawnCount"], 0)
        self.assertGreater(plan["burstCount"], 0)
        self.assertGreaterEqual(plan["localTarget"], 50)

    def test_global_cap_is_never_exceeded(self):
        director = Objectives.EncounterDirector()
        director.begin_attempt("wind", 1, 4, "wind:run")
        plan = director.plan_spawn(
            1.0, 50.0, local_alive=0, total_alive=319,
            difficulty="nightmare", challenge_tuning={"enemyCount": 3.0},
        )
        self.assertLessEqual(plan["spawnCount"], 1)
        self.assertLessEqual(319 + plan["spawnCount"], 320)
        plan = director.plan_spawn(
            1.0, 51.0, local_alive=0, total_alive=320,
            difficulty="nightmare", challenge_tuning={"enemyCount": 3.0},
        )
        self.assertEqual(plan["spawnCount"], 0)
        self.assertEqual(plan["reason"], "global_cap")
        self.assertGreater(director.spawn_failures["global_cap"], 0)

    def test_fixed_elites_are_scheduled_and_once_per_attempt(self):
        expected = (2, 3, 4, 5)
        for order, expected_count in enumerate(expected, 1):
            director = Objectives.EncounterDirector()
            director.begin_attempt("star", 1, order, "star:run")
            due = director.fixed_elites_due(0.0, 60.0, order)
            self.assertEqual(sum(row["count"] for row in due), expected_count)
            self.assertEqual(director.fixed_elites_due(0.0, 60.0, order), ())
            self.assertTrue(all(row["time"] in Objectives.FIXED_ELITE_TIMES for row in due))

    def test_special_wave_events_resolve_to_runtime_socket_directions(self):
        for event_id in (
                "lane_rush", "four_side", "four_wall", "charge_lanes", "final_peak"):
            result = Objectives.resolve_wave_event(event_id, 10, serial=3)
            self.assertEqual(result["eventId"], event_id)
            self.assertTrue(result["phase"])
            self.assertTrue(result["spawnStyle"])
            self.assertEqual(len(result["socketIndices"]), result["directionCount"])
            self.assertEqual(len(result["socketIndices"]), len(set(result["socketIndices"])))
            self.assertTrue(all(0 <= index < 10 for index in result["socketIndices"]))

        observed = set()
        for region_id in Objectives.REGION_IDS:
            director = Objectives.EncounterDirector()
            director.begin_attempt(region_id, 1, 1, region_id + ":run")
            observed.update(
                event["eventId"]
                for event in director.wave_events_due(0.0, 60.0, region_id, 10)
            )
        self.assertEqual(
            observed,
            {"lane_rush", "four_side", "four_wall", "charge_lanes", "final_peak"},
        )

    def test_rosters_keep_low_health_fodder_share(self):
        for region_id in Objectives.REGION_IDS:
            for elapsed in (0.0, 18.0, 34.0, 50.0):
                roster = Objectives.region_roster_weights(region_id, elapsed)
                fodder_share = sum(row["weight"] for row in roster if row["fodder"])
                self.assertGreaterEqual(fodder_share, 0.55)
                self.assertLessEqual(fodder_share, 0.70)
                self.assertAlmostEqual(sum(row["weight"] for row in roster), 1.0)

    def test_failed_retry_does_not_refresh_xp_or_gold_budget(self):
        director = Objectives.EncounterDirector()
        director.begin_attempt("water", 1, 1, "water:run")
        self.assertEqual(director.consume_xp("water", 100.0), 100.0)
        self.assertEqual(director.consume_gold("water", 3), 3)
        before = director.snapshot()["budgets"]["water"]
        director.end_attempt(False)
        director.begin_attempt("water", 2, 1, "water:run")
        after = director.snapshot()["budgets"]["water"]
        self.assertEqual(before, after)
        self.assertEqual(after["budgetTier"], 1)
        self.assertEqual(director.consume_xp("water", 1000.0), 220.0)
        self.assertEqual(director.consume_xp("water", 1.0), 0.0)
        self.assertEqual(director.consume_gold("water", 100), 5)
        self.assertEqual(director.consume_gold("water", 1), 0)
        self.assertEqual(director.scaled_region_xp(10), 5.0)

    def test_failure_cleanup_retains_everything_until_cooldown_and_is_bounded(self):
        rows = [
            {"key": "near", "regionId": "star", "encounterId": "star:run", "x": 2, "z": 0, "engaged": True},
            {"key": "far", "regionId": "star", "encounterId": "star:run", "x": 35, "z": 0, "engaged": True},
            {"key": "idle", "regionId": "star", "encounterId": "star:run", "x": 20, "z": 0, "engaged": False},
        ]
        pending = Objectives.classify_region_cleanup(
            rows, 0, 0, "star", "star:run", False,
        )
        self.assertEqual(pending["retire"], [])
        self.assertEqual(pending["convert"], [])
        cleaned = Objectives.classify_region_cleanup(
            rows, 0, 0, "star", "star:run", True, max_retire=1,
        )
        self.assertEqual(len(cleaned["retire"]), 1)
        self.assertIn("near", cleaned["convert"])
        self.assertNotIn("near", cleaned["retire"])

    def test_global_threat_bands_are_permanent_monotonic_tiers(self):
        targets = [Objectives.global_threat_target(count, 0.5) for count in range(5)]
        self.assertEqual(targets, [38, 52, 70, 92, 112])
        self.assertEqual(targets, sorted(targets))


class RunConfigContracts(unittest.TestCase):
    def _profile(self):
        return {
            "selectedCharacter": "snowbean",
            "selectedDifficulty": "fierce",
            "selectedChallenges": ["hurry", "swarm", "hurry"],
            "selectedChallenge": "hurry",
            "powerUps": {"meta_weapon_slots": 2},
            "selectedWeaponSlotLimit": 4,
        }

    def test_snapshot_is_deeply_immutable_and_detached(self):
        profile = self._profile()
        config = SurvivorRunConfig.compile_run_config(
            profile,
            CHALLENGES,
            run_seed=0x123456789,
            content_identity={"catalog": 7},
        )
        profile["selectedCharacter"] = "starpaw"
        profile["selectedChallenges"].append("chonk")
        self.assertEqual(config.selected_character, "snowbean")
        self.assertEqual(config.challenge_ids, ("swarm", "hurry"))
        self.assertEqual(config.run_seed, 0x23456789)
        with self.assertRaises(AttributeError):
            config.weapon_slot_limit = 6
        with self.assertRaises(TypeError):
            config.objective_config["objective"]["assaultSeconds"] = 1.0
        with self.assertRaises(TypeError):
            config.content_identity["catalog"] = 8
        payload = config.as_dict()
        payload["challengeIds"].append("chonk")
        payload["objectiveConfig"]["objective"]["assaultSeconds"] = 1.0
        self.assertEqual(config.challenge_ids, ("swarm", "hurry"))
        self.assertEqual(
            config.objective_config["objective"]["assaultSeconds"], 60.0,
        )

    def test_camel_case_payload_and_snake_case_fields(self):
        config = SurvivorRunConfig.compile_run_config(
            self._profile(), CHALLENGES, run_seed=42,
        )
        self.assertEqual(config.character, config.selected_character)
        self.assertEqual(config.difficulty, config.selected_difficulty)
        self.assertEqual(config.seed, config.run_seed)
        payload = config.as_dict()
        expected_keys = {
            "selectedCharacter",
            "selectedDifficulty",
            "challengeIds",
            "combinedChallengeTuning",
            "combinedChallengeRewards",
            "weaponSlotLimit",
            "objectiveConfig",
            "runSeed",
            "contentIdentity",
            "schemaIdentity",
        }
        self.assertTrue(expected_keys.issubset(payload))
        self.assertEqual(payload["weaponSlotLimit"], config.weapon_slot_limit)

    def test_challenges_follow_catalog_order_and_all_are_snapshotted(self):
        profile = self._profile()
        profile["selectedChallenges"] = [
            "cursed_bloom", "no_trinkets", "swarm", "unknown", "chonk",
        ]
        config = SurvivorRunConfig.compile_run_config(profile, CHALLENGES)
        self.assertEqual(
            config.challenge_ids,
            ("swarm", "chonk", "no_trinkets", "cursed_bloom"),
        )
        self.assertTrue(config.combined_challenge_tuning["disableTrinkets"])
        self.assertAlmostEqual(config.combined_challenge_tuning["enemyCount"], 1.65)
        minute_tuning = config.challenge_tuning_for_world_minute(14)
        self.assertGreater(minute_tuning["enemyCount"], 1.65)
        self.assertEqual(minute_tuning["ids"], config.challenge_ids)
        self.assertGreater(config.combined_challenge_rewards, 1.0)

    def test_hurry_scales_world_clock_but_never_objective_raw_clock(self):
        profile = self._profile()
        profile["selectedChallenges"] = ["hurry"]
        config = SurvivorRunConfig.compile_run_config(profile, CHALLENGES)
        self.assertEqual(config.world_clock_multiplier, 1.5)
        self.assertEqual(config.objective_clock_multiplier, 1.0)
        self.assertEqual(config.world_delta(40.0), 60.0)
        self.assertEqual(config.objective_delta(40.0), 40.0)
        self.assertEqual(config.objective_delta(40.0, gameplay_active=False), 0.0)

    def test_weapon_slot_limit_is_run_immutable_and_clamped_to_purchase(self):
        profile = self._profile()
        config = SurvivorRunConfig.compile_run_config(profile, CHALLENGES)
        self.assertEqual(config.weapon_slot_limit, 4)
        requested = SurvivorRunConfig.compile_run_config(
            profile, CHALLENGES, weapon_slot_limit=6,
        )
        self.assertEqual(requested.weapon_slot_limit, 5)
        profile["powerUps"]["meta_weapon_slots"] = 3
        profile["selectedWeaponSlotLimit"] = 6
        self.assertEqual(config.weapon_slot_limit, 4)


def run_contracts():
    """Run every pure contract and raise one actionable assertion on failure."""

    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError(output.getvalue())
    return {
        "testsRun": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": True,
    }


if __name__ == "__main__":
    unittest.main(verbosity=2)
