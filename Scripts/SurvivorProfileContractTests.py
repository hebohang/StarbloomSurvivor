"""Standalone contract tests for SurvivorProfile and SurvivorEconomy."""

import json
import os
import tempfile
import unittest

import SurvivorEconomy
import SurvivorMetaProgression
import SurvivorProfile


class SurvivorProfileContractTests(unittest.TestCase):
    def test_default_profile_has_complete_v4_schema(self):
        profile = SurvivorProfile.default_profile()
        self.assertEqual(profile["version"], 4)
        self.assertEqual(profile["selectedCharacter"], "starpaw")
        self.assertEqual(profile["selectedWeaponSlotLimit"], 3)
        self.assertEqual(profile["discoveredDomains"], [])
        self.assertIn("comet", profile["owned"]["weapons"])
        self.assertIn("magnet", profile["owned"]["tomes"])
        self.assertIn("prism_lens", profile["owned"]["trinkets"])
        self.assertIsNone(profile["lastRun"])

    def test_v1_migration_preserves_stats_unlocks_and_legacy_pool(self):
        v1 = {
            "version": 1,
            "selected_character": "azura",
            "total_kills": 900,
            "best_survival": 130.5,
            "best_level": 22,
            "boss_kills": 3,
        }
        migrated = SurvivorProfile.migrate_profile(v1)
        self.assertEqual(migrated["career"]["totalKills"], 900)
        self.assertEqual(migrated["career"]["bestSurvivalSeconds"], 130.5)
        self.assertEqual(migrated["career"]["bestLevel"], 22)
        self.assertEqual(migrated["career"]["totalBossKills"], 3)
        self.assertEqual(set(migrated["owned"]["characters"]), set(SurvivorProfile.LEGACY_CHARACTERS))
        self.assertEqual(set(migrated["owned"]["weapons"]), set(SurvivorProfile.LEGACY_WEAPONS))
        self.assertEqual(set(migrated["owned"]["tomes"]), set(SurvivorProfile.LEGACY_TOMES))
        self.assertEqual(migrated["selectedCharacter"], "azura")
        self.assertEqual(SurvivorProfile.migrate_profile(migrated), migrated)

    def test_v2_migration_preserves_all_progression_and_history(self):
        v2 = SurvivorProfile.default_profile()
        v2["version"] = 2
        v2.pop("selectedWeaponSlotLimit")
        v2.pop("discoveredDomains")
        v2["walletGold"] = 4321
        v2["selectedCharacter"] = "peachy"
        v2["selectedDifficulty"] = "fierce"
        v2["selectedChallenges"] = ["hurry", "swarm"]
        v2["owned"]["characters"].append("peachy")
        v2["eligible"]["weapons"].append("tornado")
        v2["powerUps"]["meta_might"] = 2
        v2["powerUpsEnabled"]["meta_might"] = False
        v2["characterTraining"]["peachy"] = 4
        v2["characterTrainingEnabled"]["peachy"] = False
        v2["characterMasteryXp"]["peachy"] = 987
        v2["completedQuests"] = ["quest_start"]
        v2["questProgress"]["quest_character_mossling"] = 321
        v2["trackedQuests"] = ["quest_character_mossling"]
        v2["discoveredEvolutions"] = ["supernovachoir"]
        v2["poolDisabled"]["weapons"] = ["thunder"]
        v2["difficultyClears"] = {"adventure": True}
        v2["challengeClears"] = {"hurry": True}
        v2["lastRun"] = {
            "runId": "legacy-history",
            "rewardCommitted": True,
            "challengeIds": ["hurry", "swarm"],
            "resultSummary": {"bossTtkSeconds": 91.5},
        }

        migrated = SurvivorProfile.migrate_profile(v2)
        self.assertEqual(migrated["version"], 4)
        self.assertEqual(migrated["walletGold"], 4321)
        self.assertEqual(migrated["owned"], v2["owned"])
        self.assertEqual(migrated["eligible"]["weapons"], [])
        self.assertEqual(migrated["powerUps"]["meta_might"], 2)
        self.assertFalse(migrated["powerUpsEnabled"]["meta_might"])
        self.assertEqual(migrated["characterTraining"], v2["characterTraining"])
        self.assertEqual(migrated["characterTrainingEnabled"], v2["characterTrainingEnabled"])
        self.assertEqual(migrated["characterMasteryXp"], v2["characterMasteryXp"])
        self.assertEqual(migrated["completedQuests"], v2["completedQuests"])
        self.assertEqual(migrated["questProgress"], v2["questProgress"])
        self.assertEqual(migrated["trackedQuests"], v2["trackedQuests"])
        self.assertEqual(migrated["discoveredEvolutions"], v2["discoveredEvolutions"])
        self.assertEqual(migrated["poolDisabled"]["weapons"], [])
        self.assertEqual(migrated["difficultyClears"], v2["difficultyClears"])
        self.assertEqual(migrated["challengeClears"], v2["challengeClears"])
        self.assertEqual(migrated["selectedWeaponSlotLimit"], 3)
        self.assertEqual(migrated["discoveredDomains"], [])
        self.assertEqual(migrated["lastRun"]["weaponSlotLimit"], 6)
        self.assertEqual(
            migrated["lastRun"]["resultSummary"],
            {"bossTtkSeconds": 91.5},
        )
        self.assertEqual(SurvivorProfile.migrate_profile(migrated), migrated)

    def test_v3_retires_normal_domain_duplicates_and_refunds_purchases(self):
        v3 = SurvivorProfile.default_profile()
        v3["version"] = 3
        v3["walletGold"] = 100
        v3["owned"]["weapons"].extend(("thunder", "tornado", "starfall"))
        v3["eligible"]["weapons"] = ["tornado", "starfall"]
        v3["poolDisabled"]["weapons"] = ["thunder", "tornado"]
        v3["questProgress"] = {
            "quest_weapon_tornado": 200,
            "quest_character_mossling": 5,
        }
        v3["trackedQuests"] = [
            "quest_weapon_starfall", "quest_character_mossling",
        ]
        v3["discoveredEvolutions"] = [
            "storybooktempest", "supernovachoir",
        ]

        migrated = SurvivorProfile.migrate_profile(v3)
        self.assertEqual(migrated["version"], 4)
        self.assertEqual(migrated["walletGold"], 320)
        self.assertFalse(
            SurvivorProfile.RETIRED_NORMAL_WEAPONS.intersection(
                migrated["owned"]["weapons"],
            ),
        )
        self.assertFalse(
            SurvivorProfile.RETIRED_NORMAL_WEAPONS.intersection(
                migrated["eligible"]["weapons"],
            ),
        )
        self.assertEqual(migrated["poolDisabled"]["weapons"], [])
        self.assertEqual(
            migrated["questProgress"], {"quest_character_mossling": 5},
        )
        self.assertEqual(
            migrated["trackedQuests"], ["quest_character_mossling"],
        )
        self.assertEqual(
            migrated["discoveredEvolutions"], ["supernovachoir"],
        )
        self.assertEqual(SurvivorProfile.migrate_profile(migrated), migrated)

    def test_future_version_is_refused_without_backup_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "SurvivorProgression.json")
            with open(path, "w", encoding="utf-8") as profile_file:
                json.dump({"version": 5}, profile_file)
            SurvivorProfile.save_profile(SurvivorProfile.default_profile(), path + ".bak")
            with self.assertRaises(SurvivorProfile.FutureProfileVersionError):
                SurvivorProfile.load_profile(path)
            with self.assertRaises(SurvivorProfile.FutureProfileVersionError):
                SurvivorProfile.save_profile(SurvivorProfile.default_profile(), path)
            with open(path, "r", encoding="utf-8") as profile_file:
                self.assertEqual(json.load(profile_file)["version"], 5)

    def test_atomic_save_keeps_previous_good_backup_and_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "SurvivorProgression.json")
            first = SurvivorProfile.default_profile()
            SurvivorProfile.save_profile(first, path)
            second = SurvivorProfile.default_profile()
            second["walletGold"] = 77
            SurvivorProfile.save_profile(second, path)
            with open(path, "w", encoding="utf-8") as profile_file:
                profile_file.write("{broken")
            logs = []
            recovered = SurvivorProfile.load_profile(path, logs.append)
            self.assertEqual(recovered["walletGold"], 0)
            self.assertTrue(any("backup" in message.lower() for message in logs))
            self.assertFalse(any(".tmp." in name for name in os.listdir(directory)))

    def test_loaded_integer_fields_are_clamped(self):
        profile = SurvivorProfile.default_profile()
        profile["walletGold"] = -50
        profile["career"]["totalKills"] = SurvivorEconomy.MAX_RUN_COUNTER + 50
        normalized = SurvivorProfile.migrate_profile(profile)
        self.assertEqual(normalized["walletGold"], 0)
        self.assertEqual(
            normalized["career"]["totalKills"], SurvivorEconomy.MAX_RUN_COUNTER,
        )

    def test_reward_formula_and_abandon_rules(self):
        reward = SurvivorEconomy.compute_run_reward(
            300, 400, 2, 1, 20,
            victory=True, revives_used=0, quest_gold=7, end_reason="victory",
        )
        self.assertEqual(reward["subTotal"], 173)
        self.assertEqual(reward["earnedGold"], 180)

        abandon = SurvivorEconomy.compute_run_reward(
            120, 400, 0, 0, 10, end_reason="abandon",
        )
        self.assertEqual(abandon["earnedGold"], 14)
        short_abandon = SurvivorEconomy.compute_run_reward(
            30, 400, 0, 0, 10, quest_gold=9, end_reason="abandon",
        )
        self.assertEqual(short_abandon["timeGold"], 0)
        self.assertEqual(short_abandon["killGold"], 0)
        self.assertEqual(short_abandon["earnedGold"], 14)

    def test_weapon_slot_reward_factors_are_explicit_and_leave_quest_gold_outside(self):
        expected_factors = {3: 1.20, 4: 1.10, 5: 1.05, 6: 1.00}
        baseline = SurvivorEconomy.compute_run_reward(
            300, 400, 2, 1, 20,
            victory=True, revives_used=0, quest_gold=7, bonus_gold=10,
            end_reason="victory", weapon_slot_limit=6,
        )
        for weapon_slot_limit, factor in expected_factors.items():
            reward = SurvivorEconomy.compute_run_reward(
                300, 400, 2, 1, 20,
                victory=True, revives_used=0, quest_gold=7, bonus_gold=10,
                end_reason="victory", weapon_slot_limit=weapon_slot_limit,
            )
            self.assertEqual(reward["weaponSlotFactor"], factor)
            self.assertEqual(
                reward["weaponSlotBonusGold"],
                reward["earnedGold"] - baseline["earnedGold"],
            )
            self.assertEqual(reward["questGold"], 7)

    def test_weapon_slot_power_up_prices_prerequisites_idempotency_and_refund(self):
        profile = SurvivorProfile.default_profile()
        profile["walletGold"] = 10_000
        power_up_id = SurvivorMetaProgression.WEAPON_SLOT_POWER_UP_ID

        locked = SurvivorEconomy.purchase_power_up(profile, power_up_id, 0)
        self.assertEqual(locked["status"], "locked")
        self.assertEqual(locked["prerequisiteDifficulty"], "adventure")
        self.assertEqual(profile["walletGold"], 10_000)

        paid = []
        for expected_level, difficulty_id, price in (
                (0, "adventure", 600),
                (1, "fierce", 1500),
                (2, "nightmare", 3200)):
            profile["difficultyClears"][difficulty_id] = True
            receipt = SurvivorEconomy.purchase_power_up(
                profile, power_up_id, expected_level,
            )
            paid.append(receipt["spentGold"])
            duplicate = SurvivorEconomy.purchase_power_up(
                profile, power_up_id, expected_level,
            )
            self.assertEqual(duplicate["status"], "stale")
            if expected_level < 2:
                next_locked = SurvivorEconomy.purchase_power_up(
                    profile, power_up_id, expected_level + 1,
                )
                self.assertEqual(next_locked["status"], "locked")
                self.assertEqual(
                    next_locked["prerequisiteDifficulty"],
                    ("fierce", "nightmare")[expected_level],
                )
        self.assertEqual(paid, [600, 1500, 3200])
        self.assertEqual(
            SurvivorMetaProgression.purchased_weapon_slot_limit(profile), 6,
        )
        self.assertTrue(
            SurvivorEconomy.set_power_up_enabled(profile, power_up_id, False),
        )
        self.assertEqual(
            SurvivorMetaProgression.purchased_weapon_slot_limit(profile), 6,
        )

        profile["selectedWeaponSlotLimit"] = 6
        refund = SurvivorEconomy.refund_power_up(profile, power_up_id, 3)
        self.assertEqual(refund["refundedGold"], 5300)
        self.assertEqual(profile["selectedWeaponSlotLimit"], 3)
        normalized = SurvivorProfile.validate_profile(profile)
        self.assertEqual(normalized["selectedWeaponSlotLimit"], 3)
        self.assertEqual(
            SurvivorMetaProgression.purchased_weapon_slot_limit(normalized), 3,
        )

    def test_begin_run_snapshots_selected_weapon_slot_limit(self):
        profile = SurvivorProfile.default_profile()
        profile["powerUps"]["meta_weapon_slots"] = 2
        profile["selectedWeaponSlotLimit"] = 4
        run = SurvivorEconomy.begin_run(
            profile, "weapon-slot-snapshot", challenge_ids=("hurry", "swarm"),
        )
        profile["selectedWeaponSlotLimit"] = 5
        self.assertEqual(run["weaponSlotLimit"], 4)
        self.assertEqual(run["challengeIds"], ["hurry", "swarm"])

    def test_run_commit_is_idempotent(self):
        profile = SurvivorProfile.default_profile()
        SurvivorEconomy.begin_run(profile, "fixed-run")
        reward = SurvivorEconomy.compute_run_reward(
            300, 400, 2, 1, 20,
            victory=True, revives_used=0, quest_gold=7, end_reason="victory",
        )
        first = SurvivorEconomy.commit_run_reward(
            profile, "fixed-run", reward, "victory",
        )
        second = SurvivorEconomy.commit_run_reward(
            profile, "fixed-run", reward, "victory",
        )
        self.assertEqual(first["status"], "committed")
        self.assertEqual(second["status"], "already_committed")
        self.assertEqual(profile["walletGold"], 180)
        self.assertEqual(profile["career"]["runs"], 1)
        self.assertEqual(profile["career"]["wins"], 1)

    def test_content_purchase_double_click_only_charges_once(self):
        profile = SurvivorProfile.default_profile()
        profile["walletGold"] = 500
        self.assertEqual(
            SurvivorEconomy.content_state(profile, "character", "peachy"),
            "locked",
        )
        self.assertTrue(SurvivorEconomy.grant_content_eligibility(
            profile, "character", "peachy",
        ))
        self.assertFalse(SurvivorEconomy.grant_content_eligibility(
            profile, "character", "peachy",
        ))
        self.assertEqual(
            SurvivorEconomy.content_state(profile, "character", "peachy"),
            "eligible",
        )
        first = SurvivorEconomy.purchase_content(profile, "character", "peachy", 100)
        second = SurvivorEconomy.purchase_content(profile, "character", "peachy", 100)
        self.assertEqual(first["status"], "purchased")
        self.assertEqual(second["status"], "already_owned")
        self.assertEqual(profile["walletGold"], 400)
        self.assertEqual(profile["owned"]["characters"].count("peachy"), 1)
        self.assertEqual(
            SurvivorEconomy.content_state(profile, "character", "peachy"),
            "owned",
        )

    def test_run_transaction_survives_save_and_remains_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "SurvivorProgression.json")
            profile = SurvivorProfile.default_profile()
            SurvivorEconomy.begin_run(profile, "persisted-run")
            SurvivorProfile.save_profile(profile, path)

            loaded = SurvivorProfile.load_profile(path)
            self.assertFalse(loaded["lastRun"]["rewardCommitted"])
            reward = SurvivorEconomy.compute_run_reward(
                120, 400, 0, 0, 10, end_reason="abandon",
            )
            SurvivorEconomy.commit_run_reward(
                loaded, "persisted-run", reward, "abandon",
            )
            SurvivorProfile.save_profile(loaded, path)

            committed = SurvivorProfile.load_profile(path)
            wallet = committed["walletGold"]
            duplicate = SurvivorEconomy.commit_run_reward(
                committed, "persisted-run", reward, "abandon",
            )
            self.assertEqual(duplicate["status"], "already_committed")
            self.assertEqual(committed["walletGold"], wallet)
            self.assertEqual(committed["career"]["runs"], 1)

    def test_power_up_expected_level_and_full_refund(self):
        profile = SurvivorProfile.default_profile()
        profile["walletGold"] = 1000
        first = SurvivorEconomy.purchase_power_up(profile, "meta_might", expected_level=0)
        duplicate = SurvivorEconomy.purchase_power_up(profile, "meta_might", expected_level=0)
        second = SurvivorEconomy.purchase_power_up(profile, "meta_might", expected_level=1)
        self.assertEqual(first["status"], "purchased")
        self.assertEqual(duplicate["status"], "stale")
        self.assertEqual(second["status"], "purchased")
        self.assertEqual(profile["walletGold"], 720)
        refunded = SurvivorEconomy.refund_power_up(
            profile, "meta_might", expected_level=2,
        )
        duplicate_refund = SurvivorEconomy.refund_power_up(profile, "meta_might")
        self.assertEqual(refunded["refundedGold"], 280)
        self.assertEqual(duplicate_refund["status"], "nothing_to_refund")
        self.assertEqual(profile["walletGold"], 1000)
        self.assertEqual(profile["powerUps"]["meta_might"], 0)

    def test_staged_purchase_does_not_touch_canonical_profile_before_save(self):
        canonical = SurvivorProfile.default_profile()
        canonical["walletGold"] = 500
        SurvivorEconomy.grant_content_eligibility(
            canonical, "character", "peachy",
        )
        staged = SurvivorProfile.validate_profile(canonical)
        receipt = SurvivorEconomy.purchase_content(
            staged, "character", "peachy", 100,
        )
        self.assertEqual(receipt["status"], "purchased")
        self.assertEqual(staged["walletGold"], 400)
        self.assertEqual(canonical["walletGold"], 500)
        self.assertNotIn("peachy", canonical["owned"]["characters"])

    def test_power_up_boundaries_do_not_mutate_wallet(self):
        profile = SurvivorProfile.default_profile()
        profile["walletGold"] = 99
        receipt = SurvivorEconomy.purchase_power_up(profile, "meta_might", expected_level=0)
        self.assertEqual(receipt["status"], "insufficient_gold")
        self.assertEqual(profile["walletGold"], 99)
        with self.assertRaises(SurvivorEconomy.EconomyValidationError):
            SurvivorEconomy.purchase_content(profile, "weapon", "x", -1)

    def test_refund_all_power_ups_is_atomic_and_preserves_content(self):
        profile = SurvivorProfile.default_profile()
        original_weapons = list(profile["owned"]["weapons"])
        profile["walletGold"] = 1000
        SurvivorEconomy.purchase_power_up(profile, "meta_might", expected_level=0)
        SurvivorEconomy.purchase_power_up(profile, "meta_health", expected_level=0)
        receipt = SurvivorEconomy.refund_all_power_ups(profile)
        self.assertEqual(receipt["status"], "refunded")
        self.assertEqual(receipt["refundedGold"], 180)
        self.assertEqual(profile["walletGold"], 1000)
        self.assertEqual(profile["owned"]["weapons"], original_weapons)
        self.assertEqual(profile["powerUps"]["meta_might"], 0)
        self.assertEqual(profile["powerUps"]["meta_health"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
