"""Named Project-layer contracts invoked by the headless HEngineTests bridge."""

import json
import os
import re

import SurvivorBuildRules
import SurvivorBalance
import SurvivorCatalog
import SurvivorCatalogItems
import SurvivorCatalogMeta
import SurvivorCatalogWorld
import SurvivorContent
import SurvivorEconomy as SurvivorEconomyModule
import SurvivorHubNavigation
import SurvivorMetaProgression
import SurvivorProfile
import SurvivorRegionObjectives
import SurvivorRunConfig
import SurvivorRules
import SurvivorQuests
import SurvivorWorld
import SurvivorRuntimeAssets


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            message + "; actual=" + repr(actual) + ", expected=" + repr(expected)
        )


def _near(actual, expected, message, tolerance=1.0e-9):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(
            message + "; actual=" + repr(actual) + ", expected=" + repr(expected)
        )


def _raises(exception_type, callback, message):
    try:
        callback()
    except exception_type:
        return
    raise AssertionError(message)


def SurvivorContentCatalog():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    counts = SurvivorCatalog.validate_catalog(project_root, True)
    _equal(counts["characters"], 10, "character catalog count changed")
    _equal(counts["weapons"], 18, "base weapon catalog count changed")
    _equal(counts["evolutions"], 9, "evolution catalog count changed")
    _equal(counts["tomes"], 16, "Tome catalog count changed")
    _equal(counts["trinkets"], 12, "Trinket catalog count changed")
    _require(counts["enemies"] >= 12, "enemy catalog is below twelve")
    _require(counts["bosses"] >= 5, "boss catalog is below five")
    _require(counts["quests"] >= 36, "quest catalog is below thirty-six")
    _equal(counts["powerUps"], 13, "PowerUp catalog count changed")
    for character in SurvivorCatalog.CHARACTERS:
        _near(
            character["preview"]["yaw"], 0.0,
            character["id"] + " preview facing diverged from its model family",
        )
        _near(
            character["preview"]["upright"], 0.0,
            character["id"] + " applies a second up-axis conversion to engine-space animation",
        )
    power_up_icons = tuple(
        entry["icon"] for entry in SurvivorCatalogMeta.POWER_UPS
    )
    _equal(len(set(power_up_icons)), 13,
        "PowerUp Catalog icon paths are not unique")
    manifest_path = os.path.join(
        project_root, "Assets", "UI", "Icons", "Survivor", "manifest.json",
    )
    with open(manifest_path, "r", encoding="utf-8") as stream:
        icon_manifest = json.load(stream)
    _equal(icon_manifest["category_counts"].get("PowerUps"), 13,
        "PowerUp icon manifest count changed")
    manifest_power_ups = {
        entry["id"]: entry
        for entry in icon_manifest["files"]
        if entry["category"] == "PowerUps"
    }
    _equal(set(manifest_power_ups), {
        entry["id"] for entry in SurvivorCatalogMeta.POWER_UPS
    }, "PowerUp icon manifest IDs diverged from the Catalog")
    power_up_hashes = set()
    for power_up in SurvivorCatalogMeta.POWER_UPS:
        manifest_entry = manifest_power_ups[power_up["id"]]
        _equal(manifest_entry["path"], power_up["icon"],
            power_up["id"] + " manifest path diverged from the Catalog")
        _require(bool(manifest_entry.get("sha256")),
            power_up["id"] + " icon hash is missing from the manifest")
        power_up_hashes.add(manifest_entry["sha256"])
    _equal(len(power_up_hashes), 13,
        "PowerUp PNG payloads are not unique")
    _equal(tuple(SurvivorContent.WEAPON_ORDER), tuple(
        entry["id"] for entry in SurvivorCatalogItems.WEAPONS
    ), "runtime weapon order diverged from the validated catalog")
    _equal(len(set(SurvivorContent.WEAPON_ORDER)), 18,
        "runtime weapon order contains duplicates")
    retired_domain_duplicates = {"thunder", "starfall", "tornado"}
    _require(retired_domain_duplicates.isdisjoint(SurvivorContent.WEAPON_ORDER),
        "retired normal DomainPower duplicates remain in the weapon catalog")
    _require("storybooktempest" not in {
        entry["id"] for entry in SurvivorCatalogItems.EVOLUTIONS
    }, "retired Tornado evolution remains in the catalog")
    return counts


def SurvivorRuntimeAssetAuthority():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(
        project_root, "Config", "SurvivorRuntimeAssets.json",
    )
    with open(manifest_path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)

    _equal(manifest["Schema"], "hengine.runtime-asset-set",
        "runtime asset manifest schema changed")
    _equal(manifest["SchemaVersion"], 1,
        "runtime asset manifest version changed")
    entries = manifest["Assets"]
    keys = tuple(entry["Key"] for entry in entries)
    _equal(len(keys), len(set(keys)),
        "runtime asset manifest contains duplicate keys")
    _equal(
        tuple((entry["Key"], entry["Path"]) for entry in entries),
        tuple(sorted(
            ((entry["Key"], entry["Path"]) for entry in entries),
            key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8")),
        )),
        "runtime asset manifest order is not stable by Key then Path",
    )

    key_pattern = re.compile(r"^[a-z0-9][a-z0-9/_-]*[a-z0-9]$")
    manifest_paths = set()
    for entry in entries:
        key = entry["Key"]
        path = entry["Path"]
        _require(bool(key_pattern.fullmatch(key)),
            "runtime asset key is not canonical ASCII: " + repr(key))
        _require("//" not in key,
            "runtime asset key contains an empty segment: " + repr(key))
        _equal(entry["Kind"], "HardRuntime",
            key + " is not a HardRuntime dependency")
        _require(isinstance(entry["Reason"], str) and bool(entry["Reason"].strip()),
            key + " has no reason")
        _require(path.startswith(("Assets/", "Config/", "Scripts/", "Shaders/")),
            key + " is not project-root-relative")
        _require("\\" not in path and ":" not in path,
            key + " contains a forbidden path form")
        _require(all(part not in ("", ".", "..") for part in path.split("/")),
            key + " contains a non-canonical path segment")
        _require(os.path.isfile(os.path.join(project_root, *path.split("/"))),
            key + " points to a missing runtime asset: " + path)
        manifest_paths.add(path)

    manifest_by_key = {
        entry["Key"]: entry["Path"] for entry in entries
    }
    _equal(manifest_by_key, {
        key: SurvivorRuntimeAssets.asset_path(key)
        for key in SurvivorRuntimeAssets.asset_keys()
    }, "Python runtime asset view diverged from the JSON manifest")
    _raises(
        SurvivorRuntimeAssets.RuntimeAssetManifestError,
        lambda: SurvivorRuntimeAssets.asset_path("missing/runtime-asset-key"),
        "missing runtime asset keys no longer fail closed",
    )

    icon_manifest_path = os.path.join(
        project_root, "Assets", "UI", "Icons", "Survivor", "manifest.json",
    )
    with open(icon_manifest_path, "r", encoding="utf-8") as stream:
        icon_manifest = json.load(stream)
    icon_prefixes = {
        "Characters": "character",
        "Enemies": "enemy",
        "Bosses": "boss",
        "Weapons": "weapon",
        "Evolutions": "evolution",
        "Tomes": "tome",
        "Trinkets": "trinket",
        "PowerUps": "powerup",
    }
    provenance_icons = {
        icon_prefixes[file_entry["category"]] + "/" +
        file_entry["id"] + "/icon": file_entry["path"]
        for file_entry in icon_manifest["files"]
    }
    authority_icons = {
        key: path for key, path in manifest_by_key.items()
        if key.endswith("/icon") and
        key.split("/", 1)[0] in icon_prefixes.values()
    }
    _equal(authority_icons, provenance_icons,
        "runtime Catalog icons diverged from generated icon provenance")

    expected_catalog_keys = set()

    def check_fields(prefix, records, fields):
        for record in records:
            for manifest_role, field in fields:
                key = prefix + "/" + record["id"] + "/" + manifest_role
                value = record[field]
                if not value:
                    _require(key not in manifest_by_key,
                        key + " exists despite an empty runtime field")
                    continue
                expected_catalog_keys.add(key)
                _equal(value, SurvivorRuntimeAssets.asset_path(key),
                    key + " diverged from its runtime asset manifest entry")

    check_fields("character", SurvivorCatalog.CHARACTERS, (
        ("mesh", "mesh"),
        ("controller", "controller"),
        ("idle", "idle"),
        ("dance", "dance"),
        ("icon", "icon"),
    ))
    check_fields("enemy", SurvivorCatalogWorld.ENEMIES, (
        ("prefab", "prefab"),
        ("mesh", "mesh"),
        ("controller", "controller"),
        ("icon", "icon"),
    ))
    check_fields("boss", SurvivorCatalogWorld.BOSSES, (
        ("prefab", "prefab"),
        ("mesh", "mesh"),
        ("controller", "controller"),
        ("icon", "icon"),
    ))
    check_fields("weapon", SurvivorCatalogItems.WEAPONS, (
        ("icon", "icon"),
        ("projectile-prefab", "projectilePrefab"),
        ("cast-vfx", "castVfx"),
        ("body-vfx", "bodyVfx"),
        ("impact-vfx", "impactVfx"),
    ))
    for prefix, records in (
            ("evolution", SurvivorCatalogItems.EVOLUTIONS),
            ("tome", SurvivorCatalogItems.TOMES),
            ("trinket", SurvivorCatalogItems.TRINKETS),
            ("powerup", SurvivorCatalogMeta.POWER_UPS)):
        check_fields(prefix, records, (("icon", "icon"),))

    _equal(
        SurvivorRuntimeAssets.asset_path("character/starpaw/dance"),
        "Assets/Models/Quaternius/UltimateMonsters/Cat/CharacterArmature_Dance.hanim",
        "Starpaw menu-preview dance is no longer locked into the runtime set",
    )

    scripts_root = os.path.join(project_root, "Scripts")
    literal_consumer_files = tuple(sorted(
        filename for filename in os.listdir(scripts_root)
        if filename.startswith("Survivor")
        and filename.endswith(".py")
        and not filename.endswith("ContractTests.py")
        and filename != "SurvivorRuntimeAssets.py"
    ))
    literal_key_pattern = re.compile(
        r'''asset_path\(\s*(["'])([a-z0-9/_-]+)\1\s*\)''',
    )
    literal_keys = set()
    for filename in literal_consumer_files:
        with open(os.path.join(scripts_root, filename),
                  "r", encoding="utf-8") as stream:
            literal_keys.update(
                match.group(2)
                for match in literal_key_pattern.finditer(stream.read())
            )

    static_ui_keys = {
        "ui/background/loading",
        "ui/background/menu-garden",
        "ui/motion/loading-lottie",
        "ui/motion/starburst-svg",
        "ui/window-icon",
    }
    domain_keys = {
        key
        for config in SurvivorRegionObjectives.DOMAIN_POWER_CONFIG.values()
        for key in config["assetKeys"].values()
    }
    expected_keys = (
        expected_catalog_keys | literal_keys | static_ui_keys | domain_keys
    )
    _equal(set(keys), expected_keys,
        "runtime asset manifest has missing or unconsumed keys")

    with open(os.path.join(project_root, "Config", "Game.json"),
              "r", encoding="utf-8") as stream:
        game_config = json.load(stream)
    _equal(game_config["Cook"].get("DynamicAssetSets"), [{
        "Name": "SurvivorRuntime",
        "Manifest": "Config/SurvivorRuntimeAssets.json",
    }], "Game.Cook.DynamicAssetSets no longer selects the Survivor authority")
    _equal(game_config["Game"]["Icon"],
        SurvivorRuntimeAssets.asset_path("ui/window-icon"),
        "window icon diverged from the runtime asset manifest")

    extension_rules = (
        (lambda key: key.endswith("/mesh"), (".hmesh",)),
        (lambda key: key.endswith("/controller"), (".hanimctrl",)),
        (lambda key: key.endswith(("/idle", "/dance")), (".hanim",)),
        (lambda key: key.endswith("/icon") or key.startswith("ui/background/") or
            key.startswith("ui/cursor/") or key == "ui/window-icon", (".png",)),
        (lambda key: key.endswith("/prefab") or key.endswith("-prefab") or
            key.startswith("common/prefab/"), (".hprefab",)),
        (lambda key: "-vfx" in key or key.startswith("vfx/"), (".efkpkg",)),
        (lambda key: key.startswith("audio/"), (".wav",)),
    )
    for entry in entries:
        for matches, extensions in extension_rules:
            if matches(entry["Key"]):
                _require(entry["Path"].lower().endswith(extensions),
                    entry["Key"] + " has an invalid extension: " + entry["Path"])
                break

    def visit_sprite_components(value, textures):
        if isinstance(value, list):
            for child in value:
                visit_sprite_components(child, textures)
            return
        if not isinstance(value, dict):
            return
        component = value.get("SpriteRendererComponent")
        if isinstance(component, dict):
            texture = component.get("Texture", "")
            if texture and texture != "None":
                textures.add(texture.replace("\\", "/"))
        for child in value.values():
            visit_sprite_components(child, textures)

    sprite_textures = set()
    for relative_root in (
            os.path.join("Assets", "Scenes"),
            os.path.join("Assets", "Prefabs")):
        for directory, _, filenames in os.walk(os.path.join(project_root, relative_root)):
            for filename in filenames:
                if not filename.lower().endswith((".he", ".hprefab")):
                    continue
                with open(os.path.join(directory, filename),
                          "r", encoding="utf-8") as stream:
                    visit_sprite_components(json.load(stream), sprite_textures)
    for texture in sprite_textures:
        _require(texture in manifest_paths,
            "SpriteRendererComponent.Texture is absent from the runtime asset set: " +
            texture)

    return {
        "assets": len(entries),
        "catalogKeys": len(expected_catalog_keys),
        "spriteTextures": len(sprite_textures),
    }


def SurvivorProgressionMigration():
    legacy = {
        "version": 1,
        "selected_character": "azura",
        "total_kills": 900,
        "best_survival": 130.5,
        "best_level": 22,
        "boss_kills": 3,
    }
    migrated = SurvivorProfile.migrate_profile(legacy)
    _equal(migrated["version"], 4, "v1 did not migrate to v4")
    _equal(migrated["career"]["totalKills"], 900,
        "v1 total kills were lost")
    _equal(migrated["career"]["bestSurvivalSeconds"], 130.5,
        "v1 best survival was lost")
    _equal(migrated["career"]["bestLevel"], 22,
        "v1 best level was lost")
    _equal(migrated["career"]["totalBossKills"], 3,
        "v1 boss kills were lost")
    _equal(set(migrated["owned"]["characters"]),
        set(SurvivorProfile.LEGACY_CHARACTERS),
        "eligible legacy characters were not preserved")
    _equal(set(migrated["owned"]["weapons"]),
        set(SurvivorProfile.LEGACY_WEAPONS),
        "legacy weapon ownership was not preserved")
    _equal(set(migrated["owned"]["tomes"]),
        set(SurvivorProfile.LEGACY_TOMES),
        "legacy Tome ownership was not preserved")
    _equal(SurvivorProfile.migrate_profile(migrated), migrated,
        "v4 migration is not idempotent")

    legacy_v2 = SurvivorProfile.default_profile()
    legacy_v2["version"] = 2
    legacy_v2["walletGold"] = 4321
    legacy_v2["characterTraining"]["starpaw"] = 4
    legacy_v2["questProgress"]["quest_character_mossling"] = 321
    legacy_v2.pop("selectedWeaponSlotLimit", None)
    legacy_v2.pop("discoveredDomains", None)
    migrated_v2 = SurvivorProfile.migrate_profile(legacy_v2)
    _equal(migrated_v2["version"], 4, "v2 did not migrate to v4")
    _equal(migrated_v2["walletGold"], 4321, "v2 wallet was lost")
    _equal(migrated_v2["characterTraining"]["starpaw"], 4,
        "v2 character training was lost")
    _equal(migrated_v2["questProgress"]["quest_character_mossling"], 321,
        "v2 quest history was lost")
    _equal(migrated_v2["selectedWeaponSlotLimit"], 3,
        "v2 profile did not receive the three-slot default")

    def migrate_future():
        SurvivorProfile.migrate_profile({"version": 5})

    def migrate_corrupt():
        SurvivorProfile.migrate_profile({"walletGold": 5})

    _raises(SurvivorProfile.FutureProfileVersionError, migrate_future,
        "a future profile version was accepted")
    _raises(SurvivorProfile.ProfileValidationError, migrate_corrupt,
        "a non-legacy versionless profile was accepted")
    return True


def SurvivorEconomy():
    reward = SurvivorEconomyModule.compute_run_reward(
        300, 400, 2, 1, 20,
        victory=True,
        revives_used=0,
        quest_gold=7,
        end_reason="victory",
    )
    _equal(reward["subTotal"], 173, "fixed reward subtotal changed")
    _equal(reward["earnedGold"], 180, "fixed reward vector changed")
    abandon = SurvivorEconomyModule.compute_run_reward(
        120, 400, 0, 0, 10, end_reason="abandon",
    )
    _equal(abandon["earnedGold"], 14, "abandon factor changed")
    short_abandon = SurvivorEconomyModule.compute_run_reward(
        30, 400, 0, 0, 10, quest_gold=9, end_reason="abandon",
    )
    _equal(short_abandon["timeGold"], 0,
        "short abandon retained time gold")
    _equal(short_abandon["killGold"], 0,
        "short abandon retained kill gold")
    _equal(short_abandon["earnedGold"], 14,
        "quest gold did not remain outside abandon suppression")
    return reward


def SurvivorChallengeComposition():
    challenge_ids = tuple(
        entry["id"] for entry in SurvivorCatalogWorld.CHALLENGES
    )
    selection = SurvivorRules.toggle_challenge_id((), "swarm", challenge_ids)
    selection = SurvivorRules.toggle_challenge_id(
        selection, "chonk", challenge_ids,
    )
    _equal(selection, ("swarm", "chonk"),
        "two Challenges did not compose additively")
    selection = SurvivorRules.toggle_challenge_id(
        selection, "swarm", challenge_ids,
    )
    _equal(selection, ("chonk",),
        "removing one Challenge cleared another selection")
    selection = ()
    for challenge_id in challenge_ids:
        selection = SurvivorRules.toggle_challenge_id(
            selection, challenge_id, challenge_ids,
        )
    _equal(selection, challenge_ids,
        "selecting all Challenges lost catalog order or an entry")

    legacy = SurvivorProfile.default_profile()
    legacy.pop("selectedChallenges")
    legacy["selectedChallenge"] = "hurry"
    migrated = SurvivorProfile.validate_profile(legacy)
    _equal(migrated["selectedChallenges"], ["hurry"],
        "legacy scalar Challenge did not migrate to the list view")
    _equal(migrated["selectedChallenge"], "hurry",
        "legacy Challenge compatibility view changed")
    _equal(SurvivorProfile.validate_profile(migrated), migrated,
        "Challenge list normalization is not idempotent")

    unordered = SurvivorProfile.default_profile()
    unordered["selectedChallenges"] = [
        "chonk", "swarm", "chonk", "unknown_challenge",
    ]
    unordered["selectedChallenge"] = "hurry"
    normalized = SurvivorProfile.validate_profile(unordered)
    _equal(normalized["selectedChallenges"], ["swarm", "chonk"],
        "Challenge list was not deduplicated and catalog ordered")
    _equal(normalized["selectedChallenge"], "swarm",
        "scalar compatibility view did not mirror the first list entry")

    selected_definitions = tuple(SurvivorCatalogWorld.CHALLENGES)
    combined = SurvivorRules.combine_challenge_modifiers(
        selected_definitions, minute=14,
    )
    _near(combined["enemyCount"], 2.805,
        "Swarm and Cursed Bloom spawn pressure did not multiply")
    _near(combined["enemyHealth"], 4.0,
        "combined Challenge health pressure was not clamped")
    _near(combined["enemyDamage"], 2.465,
        "combined Challenge damage pressure changed")
    _near(combined["enemySpeed"], 0.9775,
        "Swarm and Chonk speed modifiers did not multiply")
    _near(combined["enemyScale"], 1.6,
        "Chonk scale was lost from the combined tuning")
    _near(combined["gold"], 4.0,
        "all-Challenge reward multiplier was not clamped")
    _equal(combined["playerMaxHealth"], 1.0,
        "Fragile Star did not survive composition")
    _require(combined["disableTrinkets"],
        "No Trinkets did not survive composition")

    pair_reward = SurvivorEconomyModule.combine_challenge_rewards((1.45, 1.55))
    _near(pair_reward, 2.2475,
        "Challenge gold rewards did not multiply")
    all_reward = SurvivorEconomyModule.combine_challenge_rewards(
        entry["gold"] for entry in SurvivorCatalogWorld.CHALLENGES
    )
    _near(all_reward, 4.0,
        "all-Challenge gold reward exceeded its cap")
    reward = SurvivorEconomyModule.compute_run_reward(
        300, 400, 2, 1, 20,
        victory=True,
        challenge_rewards=(1.45, 1.55),
        end_reason="victory",
    )
    _near(reward["challengeFactor"], 2.2475,
        "run reward did not retain the combined Challenge factor")

    class ContractWorld(SurvivorWorld.SurvivorWorldMixin):
        MAX_MONSTERS = 1000
        WAVE_PHASES = ({
            "start": 0,
            "end": 900,
            "count_start": 200,
            "count_end": 200,
            "health_multiplier": 1.0,
            "damage_multiplier": 1.0,
            "speed_multiplier": 1.0,
        },)
        DIFFICULTIES = tuple(SurvivorCatalogWorld.DIFFICULTIES)
        CHALLENGES = tuple(SurvivorCatalogWorld.CHALLENGES)

    world = ContractWorld()
    world.elapsed = 840.0
    world.profile = SurvivorProfile.default_profile()
    world.profile["selectedChallenges"] = list(challenge_ids)
    world.profile["selectedChallenge"] = challenge_ids[0]
    world.character_difficulty_multiplier = 1.0
    world.curse_level = 0
    _equal(world._phase_population_target(world.WAVE_PHASES[0]), 561,
        "World did not consume combined spawn pressure")
    health, damage, speed = world._difficulty_scales()
    _near(health, 4.0,
        "World health pressure did not use the combined clamp")
    _near(damage, 2.465,
        "World damage pressure did not use the combined tuning")
    _near(speed, 0.9775,
        "World speed pressure did not use the combined tuning")

    transaction_profile = SurvivorProfile.default_profile()
    transaction = SurvivorBuildRules.RunEndTransaction(
        transaction_profile,
        "multi-challenge-run",
        challenge_ids=challenge_ids,
    )
    _equal(transaction.profile["lastRun"]["challengeIds"], list(challenge_ids),
        "run transaction did not snapshot all selected Challenges")
    _equal(transaction.profile["lastRun"]["challengeId"], challenge_ids[0],
        "run transaction compatibility Challenge changed")
    return combined


def SurvivorUnlocksAndPurchases():
    profile = SurvivorProfile.default_profile()
    profile["walletGold"] = 1000
    profile["eligible"]["characters"].append("peachy")
    first = SurvivorEconomyModule.purchase_content(
        profile, "character", "peachy", 100,
    )
    duplicate = SurvivorEconomyModule.purchase_content(
        profile, "character", "peachy", 100,
    )
    _equal(first["status"], "purchased", "eligible purchase was rejected")
    _equal(duplicate["status"], "already_owned",
        "double-click purchase was not idempotent")
    _equal(profile["walletGold"], 900, "double click charged twice")
    _equal(profile["owned"]["characters"].count("peachy"), 1,
        "double click delivered duplicate content")

    power_one = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_might", expected_level=0,
    )
    stale = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_might", expected_level=0,
    )
    _equal(power_one["status"], "purchased", "PowerUp purchase failed")
    _equal(stale["status"], "stale", "stale PowerUp click was accepted")
    refunded = SurvivorEconomyModule.refund_power_up(
        profile, "meta_might", expected_level=1,
    )
    _equal(refunded["refundedGold"], 100, "PowerUp refund changed")
    _equal(profile["walletGold"], 900, "PowerUp refund did not restore balance")

    profile["walletGold"] = 0
    profile["eligible"]["weapons"].append("honeyneedle")
    insufficient = SurvivorEconomyModule.purchase_content(
        profile, "weapon", "honeyneedle", 250,
    )
    _equal(insufficient["status"], "insufficient_gold",
        "insufficient purchase mutated ownership")
    _require("honeyneedle" not in profile["owned"]["weapons"],
        "insufficient purchase delivered content")
    return True


def _upgrade_controller(seed=7319, **overrides):
    weapons = SurvivorCatalogItems.WEAPONS[:6]
    tomes = SurvivorCatalogItems.TOMES[:4]
    arguments = {
        "weapons": weapons,
        "tomes": tomes,
        "owned": {
            "weapons": [entry["id"] for entry in weapons],
            "tomes": [entry["id"] for entry in tomes],
        },
        "enabled": {
            "weapons": [entry["id"] for entry in weapons[:-1]],
            "tomes": [entry["id"] for entry in tomes],
        },
        "weapon_levels": {weapons[0]["id"]: 2},
        "tome_levels": {tomes[0]["id"]: 1},
        "weapon_slots": [weapons[0]["id"]],
        "tome_slots": [tomes[0]["id"]],
        "seed": seed,
        "rerolls": 1,
        "skips": 1,
        "banishes": 1,
    }
    arguments.update(overrides)
    return SurvivorBuildRules.UpgradePoolController(**arguments)


def SurvivorUpgradePoolControl():
    weapons = SurvivorCatalogItems.WEAPONS[:6]
    held_weapon_id = weapons[0]["id"]
    unselected_weapon_id = weapons[1]["id"]
    disabled_weapon_id = weapons[-1]["id"]
    first = _upgrade_controller()
    second = _upgrade_controller()
    first_choices = first.roll()
    second_choices = second.roll()
    _equal(first_choices, second_choices,
        "equal injected seeds produced different upgrade rolls")
    _equal(len(first_choices), len({choice["id"] for choice in first_choices}),
        "one upgrade screen contains duplicate choices")
    _require(disabled_weapon_id not in {choice["id"] for choice in first_choices},
        "disabled content entered the upgrade pool")
    snapshot = {row["id"]: row for row in first.candidate_snapshot()}
    _near(snapshot[held_weapon_id]["weight"], 2.0,
        "an in-run owned weapon did not receive its weight bonus")
    _near(snapshot[unselected_weapon_id]["weight"], 1.0,
        "an unselected weapon received the held-item weight")

    rerolled = first.reroll()
    _equal(rerolled["status"], "rerolled", "Reroll was not consumed")
    _equal(first.rerolls_remaining, 0, "Reroll count did not decrement")
    banished_id = rerolled["choices"][0]["id"]
    banished = first.banish(banished_id)
    _equal(banished["status"], "banished", "Banish was not consumed")
    _require(banished_id not in {choice["id"] for choice in banished["choices"]},
        "banished content reappeared in the run")
    first.seal(unselected_weapon_id)
    _require(unselected_weapon_id not in {
        row["id"] for row in first.candidate_snapshot()
    },
        "sealed content remained enabled")
    skipped = first.skip()
    _equal(skipped["status"], "skipped", "Skip was not consumed")
    _equal(first.current_choices, (), "Skip retained the current upgrade screen")

    full = _upgrade_controller(
        weapon_slots=[entry["id"] for entry in SurvivorCatalogItems.WEAPONS[:6]],
        max_weapon_slots=6,
    )
    full_weapon_ids = {
        row["id"] for row in full.candidate_snapshot()
        if row["category"] == "weapons"
    }
    _equal(full_weapon_ids, {SurvivorCatalogItems.WEAPONS[0]["id"]},
        "a full weapon inventory offered an unheld weapon")

    empty = SurvivorBuildRules.UpgradePoolController(
        (), (), {"weapons": (), "tomes": ()}, seed=5,
    )
    _equal(tuple(choice["id"] for choice in empty.roll()),
        SurvivorBuildRules.UpgradePoolController.FALLBACK_IDS,
        "an empty upgrade pool did not return its fallback choices")
    return True


def SurvivorEvolutionResolver():
    recipes = SurvivorCatalogItems.EVOLUTIONS[:3]
    weapon_levels = {recipe["weaponId"]: 10 for recipe in recipes}
    tome_levels = {recipe["tomeId"]: 5 for recipe in recipes}
    slots = [recipe["weaponId"] for recipe in recipes]

    tier_two = SurvivorBuildRules.EvolutionResolver(
        recipes[:1], weapon_levels, tome_levels, slots[:1],
        discovered=(recipes[0]["id"],),
    )
    blocked = tier_two.resolve_chest(1)
    _equal(blocked["status"], "no_evolution",
        "an under-tier chest evolved a weapon")
    receipt = tier_two.resolve_chest(2)
    _equal(receipt["evolutions"], (recipes[0]["id"],),
        "Tier 2 chest did not evolve one eligible weapon")
    _equal(len(receipt["weaponSlots"]), 1,
        "evolution added a weapon slot")
    _equal(receipt["weaponSlots"][0], recipes[0]["id"],
        "evolution did not replace its base slot")
    _equal(receipt["weaponLevels"][recipes[0]["weaponId"]], 0,
        "evolution retained the base weapon level")
    _equal(receipt["newlyDiscovered"], (),
        "an already discovered recipe was announced twice")
    _equal(tier_two.resolve_chest(3)["status"], "no_evolution",
        "one base weapon evolved more than once")

    tier_three = SurvivorBuildRules.EvolutionResolver(
        recipes, weapon_levels, tome_levels, slots,
    )
    multi = tier_three.resolve_chest(3)
    _equal(len(multi["evolutions"]), 2,
        "Tier 3 chest did not cap at two evolutions")
    _equal(len(multi["weaponSlots"]), len(slots),
        "Tier 3 evolution changed slot count")
    _equal(set(multi["newlyDiscovered"]), set(multi["evolutions"]),
        "new recipes were not discovered exactly once")
    return True


def SurvivorHubGamepadNavigation():
    rows = (
        ("nav",),
        ("a", "b", "c", "d", "e"),
        ("one", "two"),
        ("confirm",),
    )
    _equal(
        SurvivorHubNavigation.normalize_focus(rows, "missing", "confirm"),
        "confirm", "gamepad focus did not use its visible fallback",
    )
    _equal(SurvivorHubNavigation.move_focus(rows, "a", "left"), "e",
        "horizontal gamepad navigation did not wrap its row")
    _equal(SurvivorHubNavigation.move_focus(rows, "e", "down"), "two",
        "ragged gamepad grid lost normalized columns")
    _equal(SurvivorHubNavigation.move_focus(rows, "two", "down"), "confirm",
        "vertical gamepad navigation did not reach the confirmation row")

    repeater = SurvivorHubNavigation.DirectionalRepeater()
    _equal(repeater.update(0.75, 0.10, 0.0), "right",
        "left stick did not move immediately after crossing its threshold")
    _equal(repeater.update(0.75, 0.10, 0.10), None,
        "left stick repeated before its initial delay")
    _equal(repeater.update(0.75, 0.10, 0.10), None,
        "left stick repeated before the remaining initial delay")
    _equal(repeater.update(0.75, 0.10, 0.10), None,
        "left stick repeated before the final initial-delay slice")
    _equal(repeater.update(0.75, 0.10, 0.05), "right",
        "left stick did not repeat after its initial delay")
    _equal(repeater.update(0.20, 0.10, 0.10), None,
        "left stick hysteresis did not release at neutral")
    _equal(repeater.update(0.0, -0.80, 0.0), "down",
        "dominant vertical gamepad navigation changed direction")

    purchase_gate = SurvivorHubNavigation.ActionDebouncer(0.35)
    _require(purchase_gate.acquire("meta_weapon_slots"),
        "first shop purchase interaction was rejected")
    _require(not purchase_gate.acquire("meta_weapon_slots"),
        "same-frame shop double-click was accepted")
    _require(purchase_gate.acquire("meta_might"),
        "debouncer blocked a distinct shop item")
    _require(not purchase_gate.acquire("meta_weapon_slots"),
        "A-B-A shop clicks bypassed the per-item debounce")
    purchase_gate.update(0.35)
    _require(purchase_gate.acquire("meta_weapon_slots"),
        "shop purchase did not re-arm after the debounce interval")

    previous = {"accept": False, "back": True}
    current = {"accept": True, "back": True}
    _equal(SurvivorHubNavigation.pressed_edges(previous, current), {"accept"},
        "held gamepad buttons generated duplicate click edges")
    _equal(SurvivorHubNavigation.apply_deadzone(0.10), 0.0,
        "right-stick deadzone retained drift")
    _near(SurvivorHubNavigation.apply_deadzone(1.0), 1.0,
        "right-stick deadzone changed its full-scale value")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(project_root, "Assets", "UI", "SurvivorHUD.rml"),
              "r", encoding="utf-8") as stream:
        rml = stream.read()
    required_ids = set(SurvivorHubNavigation.focus_ids((
        ("hub_nav_play", "start_button", "character_starpaw"),
        ("armory_slot_0", "powerup_node_0", "quest_slot_0"),
        ("hub_nav_settings", "settings_back_button"),
    )))
    for element_id in required_ids:
        _require('id="' + element_id + '"' in rml,
            "gamepad focus target is missing from RML: " + element_id)
    return True


def SurvivorCharacterStartState():
    _equal(len(SurvivorContent.CHARACTER_ORDER), 10,
        "character start contract does not cover ten characters")
    for character_id in SurvivorContent.CHARACTER_ORDER:
        definition = SurvivorContent.CHARACTER_DEFS[character_id]
        state = SurvivorRules.compile_character_start_state(
            character_id, definition, training_level=5,
        )
        _equal(state["character_id"], character_id,
            "compiled state retained a previous character id")
        _equal(state["starter_weapon"], definition["weapon"],
            "compiled state retained a previous starter weapon")
        _equal(state["hooks"], tuple(definition.get("hooks", ())),
            "compiled state lost character hooks")
        _require(state["max_health"] > 0.0,
            "compiled character has non-positive max health")
        base_damage = SurvivorRules.compile_character_start_state(
            character_id, definition, training_level=0,
        )["weapon_damage_multiplier"]
        _near(state["weapon_damage_multiplier"], base_damage * 1.10,
            "training did not apply to the confirmed character snapshot")
    return True


def SurvivorWeaponLevelZero():
    weapon_order = tuple(SurvivorContent.WEAPON_ORDER)
    _equal(len(weapon_order), 18,
        "level-zero dispatch contract does not cover 18 weapons")
    zero_levels = {weapon_id: 0 for weapon_id in weapon_order}
    due_timers = {weapon_id: 0.0 for weapon_id in weapon_order}
    _equal(SurvivorRules.due_weapon_ids(
        weapon_order, zero_levels, due_timers,
    ), (), "a level-zero weapon entered cast dispatch")
    for weapon_id in weapon_order:
        levels = dict(zero_levels)
        levels[weapon_id] = 1
        _equal(SurvivorRules.due_weapon_ids(
            weapon_order, levels, due_timers,
        ), (weapon_id,), "dispatch did not isolate the one owned weapon")
    return True


def SurvivorProjectileBudget():
    budget = SurvivorRules.ProjectileBudget(2, 1)
    _equal(budget.reserve(), "full", "first projectile did not get full visual")
    _equal(budget.reserve(), "core_fallback",
        "visual exhaustion hid gameplay instead of using a core fallback")
    _equal(budget.reserve(), "retry",
        "critical gameplay exhaustion did not request retry")
    _equal(budget.reserve(False), "reject",
        "non-critical exhaustion did not reject explicitly")
    _equal(budget.retry_count, 1, "retry telemetry changed")
    _equal(budget.visual_degrade_count, 1, "visual degrade telemetry changed")
    _equal(budget.rejected_count, 1, "reject telemetry changed")
    budget.release(False)
    _equal(budget.reserve(), "core_fallback",
        "released gameplay capacity was not reusable")
    generation = budget.generation
    budget.reset()
    _equal(budget.gameplay_active, 0, "reset retained gameplay projectiles")
    _equal(budget.visual_active, 0, "reset retained visual projectiles")
    _equal(budget.generation, generation + 1,
        "reset did not invalidate projectile generations")
    return True


def SurvivorWaveTimeline():
    expected_start = 0
    previous_health = 0.0
    previous_damage = 0.0
    previous_speed = 0.0
    for wave in SurvivorCatalogWorld.WAVES:
        _equal(wave["start"], expected_start,
            "wave timeline has a gap or overlap")
        _require(wave["end"] > wave["start"],
            "wave duration is not positive")
        _require(bool(wave["pool"]), "wave enemy pool is empty")
        _require(wave["healthMultiplier"] >= previous_health,
            "wave health pressure decreased")
        _require(wave["damageMultiplier"] >= previous_damage,
            "wave damage pressure decreased")
        _require(wave["speedMultiplier"] >= previous_speed,
            "wave speed pressure decreased")
        expected_start = wave["end"]
        previous_health = wave["healthMultiplier"]
        previous_damage = wave["damageMultiplier"]
        previous_speed = wave["speedMultiplier"]
    _equal(expected_start, 900, "Adventure timeline does not end at 15 minutes")
    _require(all(wave["chestTier"] == 0 for wave in SurvivorCatalogWorld.WAVES),
        "legacy timed wave chest rewards were not removed")
    _equal(len(SurvivorCatalogWorld.BOSS_EVENTS), 1,
        "objective mode must expose exactly one final Boss event")
    boss_event = SurvivorCatalogWorld.BOSS_EVENTS[0]
    _require("time" not in boss_event,
        "the objective Boss retained a fixed-time bypass")
    _require(
        boss_event.get("id") == "starbloom_final_objective"
        and boss_event.get("bossId") == "star_dragon"
        and boss_event.get("objectiveBoss")
        and boss_event.get("finalBoss")
        and boss_event.get("requiredRegions") == 4,
        "the final Boss is not bound to the four-Region objective",
    )
    consumed_events = {
        event_id: SurvivorRegionObjectives.resolve_wave_event(event_id, 10)
        for event_id in (
            "lane_rush", "four_side", "four_wall", "charge_lanes", "final_peak",
        )
    }
    _require(all(row["socketIndices"] for row in consumed_events.values()),
        "a Catalog special wave event has no runtime socket consumer")
    _equal(len(SurvivorCatalogWorld.DIFFICULTIES), 3,
        "difficulty count changed")
    _require(len(SurvivorCatalogWorld.CHALLENGES) >= 6,
        "challenge count dropped below six")
    return True


def SurvivorRunEndTransaction():
    profile = SurvivorProfile.default_profile()
    persisted_wallets = []

    def persist(current_profile):
        persisted_wallets.append(current_profile["walletGold"])

    transaction = SurvivorBuildRules.RunEndTransaction(
        profile, "contract-run", persist=persist,
    )
    reward_inputs = {
        "survival_seconds": 300,
        "kills": 400,
        "elite_kills": 2,
        "boss_kills": 1,
        "level": 20,
        "revives_used": 0,
        "quest_gold": 7,
        # Settlement must ignore a stale caller value and consume begin_run's
        # immutable slot snapshot.
        "weapon_slot_limit": 6,
    }
    first = transaction.settle("victory", reward_inputs=reward_inputs)
    second = transaction.settle("victory", reward_inputs=reward_inputs)
    _equal(first["status"], "committed", "first run settlement did not commit")
    _equal(second["status"], "already_committed",
        "run settlement committed twice")
    _equal(first["reward"]["weaponSlotFactor"], 1.20,
        "run settlement ignored its three-slot start snapshot")
    _equal(first["reward"]["weaponSlotBonusGold"], 34,
        "run settlement omitted the visible three-slot bonus")
    _equal(profile["walletGold"], 214, "run reward was credited more than once")
    _equal(profile["career"]["runs"], 1, "run count was committed twice")
    _equal(profile["career"]["wins"], 1, "win count was committed twice")
    _equal(persisted_wallets, [214], "committed profile was persisted more than once")

    retry_profile = SurvivorProfile.default_profile()

    def fail_persist(_):
        raise RuntimeError("expected persistence failure")

    retry = SurvivorBuildRules.RunEndTransaction(
        retry_profile, "retry-run", persist=fail_persist,
    )

    def settle_failure():
        retry.settle("victory", reward_inputs=reward_inputs)

    _raises(RuntimeError, settle_failure,
        "persistence failure was reported as a committed reward")
    _equal(retry_profile["walletGold"], 0,
        "failed persistence left credited gold in memory")
    _require(not retry_profile["lastRun"]["rewardCommitted"],
        "failed persistence left the run committed")
    retry.persist = persist
    _equal(retry.settle("victory", reward_inputs=reward_inputs)["status"],
        "committed", "failed run transaction could not be retried")
    return True


def SurvivorBalanceHarness():
    report = SurvivorBalance.validate_balance_report()
    _require(report["passed"], "balance report did not pass")
    _equal(report["catalogCounts"]["weapons"], 18, "balance weapon count drifted")
    _equal(len(report["seedResults"]), 8, "balance seed coverage drifted")
    _require(
        "not a human win-rate" in report["simulationInterpretation"],
        "balance report lost its simulation interpretation",
    )
    return True


def SurvivorQuestsContract():
    profile = SurvivorProfile.default_profile()
    tracker = SurvivorQuests.SurvivorQuestTracker(profile)
    tracker.record("kills", 750)
    completed = tracker.flush()
    _require("quest_character_mossling" in completed,
        "career kill quest did not complete")
    _require("mossling" in profile["eligible"]["characters"],
        "quest reward did not create purchase eligibility")
    mossling_completion_count = profile["completedQuests"].count(
        "quest_character_mossling",
    )
    tracker.record("kills", 750)
    tracker.flush()
    _equal(
        profile["completedQuests"].count("quest_character_mossling"),
        mossling_completion_count,
        "completed quest was recorded twice",
    )
    tracker.reset_run()
    tracker.record("full_health_seconds", 120, bSet=True)
    tracker.record("full_health_seconds", 180, bSet=True)
    tracker.flush()
    _require("quest_trinket_glass" in profile["completedQuests"],
        "run-scoped full-health quest did not complete")
    tracker.reset_run()
    tracker.record("weapons_at_level", 6, {"level": 5}, bSet=True)
    tracker.record("different_damage_weapons_clear", 6, bSet=True)
    tracker.flush()
    _require("quest_trinket_friendship" not in profile["completedQuests"]
        and "quest_build_six_weapon_clear" not in profile["completedQuests"],
        "six-weapon endgame quests progressed before slot six was unlocked")
    profile.setdefault("powerUps", {})["meta_weapon_slots"] = 3
    tracker.record("weapons_at_level", 6, {"level": 5}, bSet=True)
    tracker.record("different_damage_weapons_clear", 6, bSet=True)
    tracker.flush()
    _require("quest_trinket_friendship" in profile["completedQuests"]
        and "quest_build_six_weapon_clear" in profile["completedQuests"],
        "six-weapon endgame quests did not unlock with slot six")
    return True


def SurvivorRegionObjectivesContract():
    controller = SurvivorRegionObjectives.RegionObjectiveController()
    star = SurvivorRegionObjectives.REGION_CONFIG["star"]["authoredPosition"]
    controller.update(1.49, star[0], star[2])
    _equal(controller.region_states["star"].state,
        SurvivorRegionObjectives.REGION_ARMING,
        "Region entered ASSAULT before 1.5 continuous raw seconds")
    controller.update(0.01, star[0], star[2])
    _equal(controller.region_states["star"].state,
        SurvivorRegionObjectives.REGION_ASSAULT,
        "Region did not enter ASSAULT at 1.5 seconds")
    controller.update(20.0, star[0], star[2])
    progress = controller.region_states["star"].assault_elapsed
    controller.update(30.0, star[0], star[2], gameplay_active=False)
    _near(controller.region_states["star"].assault_elapsed, progress,
        "paused gameplay advanced the objective clock")
    controller.update(0.01, star[0] + 20.0, star[2])
    _equal(controller.region_states["star"].state,
        SurvivorRegionObjectives.REGION_OUTSIDE_GRACE,
        "leaving the ring did not pause ASSAULT immediately")
    controller.update(1.0, star[0] + 20.0, star[2])
    controller.update(0.01, star[0], star[2])
    _near(controller.region_states["star"].assault_elapsed, progress,
        "return inside grace lost Region progress")
    controller.update(0.01, star[0] + 20.0, star[2])
    controller.update(1.26, star[0] + 20.0, star[2])
    _equal(controller.region_states["star"].state,
        SurvivorRegionObjectives.REGION_COOLDOWN,
        "expired grace did not enter cooldown")
    _near(controller.region_states["star"].assault_elapsed, 0.0,
        "expired grace did not fully reset progress")

    for order in __import__("itertools").permutations(
            SurvivorRegionObjectives.REGION_IDS):
        ordered = SurvivorRegionObjectives.RegionObjectiveController()
        for region_id in order:
            ordered.complete_region(region_id)
        _equal(tuple(ordered.completed_regions), order,
            "an arbitrary Region order was not preserved")
        _equal(ordered.objective_state,
            SurvivorRegionObjectives.OBJECTIVE_BOSS_READY,
            "four Regions did not produce BOSS_READY")

    scripts_root = os.path.dirname(__file__)
    game_source = open(
        os.path.join(scripts_root, "SurvivorGame.py"),
        "r", encoding="utf-8",
    ).read()
    objective_source = open(
        os.path.join(scripts_root, "SurvivorObjectives.py"),
        "r", encoding="utf-8",
    ).read()
    world_source = open(
        os.path.join(scripts_root, "SurvivorWorld.py"),
        "r", encoding="utf-8",
    ).read()
    fixed_source = game_source.split("    def FixedUpdate(self, ts):", 1)[1]
    fixed_source = fixed_source.split("    @_profile_stage(\"Bookkeeping\")", 1)[0]
    _require(re.search(
        r'_timed_stage_call\("Objectives",\s*'
        r'self\._update_region_objectives,\s*player_pos,\s*dt,\s*\)',
        fixed_source,
    ) is not None,
        "runtime Region clock does not consume the fixed gameplay tick")
    _require('monster["encounter_id"] = ""' not in objective_source
        and 'monster["zone_id"] = ""' not in objective_source,
        "converted Region wanderers lose anti-farm provenance")
    _require("region_fixed_elites_pending" in objective_source,
        "failed fixed-elite spawns are not retained for retry")
    _require("_apply_objective_capture_population" in objective_source
        and "prefill_count = min(self.MAX_MONSTERS - 12, target)" in objective_source,
        "deterministic Region peak fixtures do not prefill localAlive pressure")
    _require("region_reward_limited" in world_source
        and "reward_zone_id" in world_source,
        "converted Region kills bypass shared reward budgets")
    _require("source_values" in world_source
        and "source_values" in objective_source,
        "pickup-cap merging loses Region XP vacuum provenance")
    _require("pending_objective_retry_events" in objective_source,
        "failed Domain discovery persistence has no retry queue")
    repository_root = os.path.dirname(os.path.dirname(scripts_root))
    binding_source = open(
        os.path.join(
            repository_root,
            "Engine", "Source", "Plugins", "PythonScript", "Binding",
            "EcsBinding.hpp",
        ),
        "r", encoding="utf-8",
    ).read()
    _require('animator.HasParameter("Hit")' in binding_source
        and 'animator.HasParameter("Speed")' in binding_source,
        "animation budget path does not distinguish combat and locomotion controllers")
    _require(":state\"" in objective_source
        and ":activated\"" in objective_source,
        "runtime Region completion side effects lack idempotent receipts")
    return {"orders": 24, "rawAssaultSeconds": 60.0}


def SurvivorWeaponSlotsContract():
    default_profile = SurvivorProfile.default_profile()
    _equal(default_profile["selectedWeaponSlotLimit"], 3,
        "new profiles do not start with three weapon slots")
    _equal(SurvivorMetaProgression.purchased_weapon_slot_limit(default_profile), 3,
        "new profile purchased slot capability changed")

    profile = SurvivorProfile.default_profile()
    profile["walletGold"] = 10_000
    locked = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_weapon_slots", expected_level=0,
    )
    _equal(locked["status"], "locked",
        "slot four was purchasable before Adventure clear")
    profile["difficultyClears"]["adventure"] = True
    fourth = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_weapon_slots", expected_level=0,
    )
    duplicate = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_weapon_slots", expected_level=0,
    )
    _equal((fourth["status"], fourth["spentGold"]), ("purchased", 600),
        "slot four price changed")
    _equal(duplicate["status"], "stale",
        "double-click slot purchase charged twice")
    _equal(profile["walletGold"], 9400,
        "double-click slot purchase mutated the wallet twice")
    _equal(
        SurvivorEconomyModule.purchase_power_up(
            profile, "meta_weapon_slots", expected_level=1,
        )["status"],
        "locked",
        "slot five was purchasable before Fierce clear",
    )
    profile["difficultyClears"]["fierce"] = True
    fifth = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_weapon_slots", expected_level=1,
    )
    profile["difficultyClears"]["nightmare"] = True
    sixth = SurvivorEconomyModule.purchase_power_up(
        profile, "meta_weapon_slots", expected_level=2,
    )
    _equal((fifth["spentGold"], sixth["spentGold"]), (1500, 3200),
        "slot five/six prices changed")
    profile["selectedWeaponSlotLimit"] = 3
    normalized = SurvivorProfile.validate_profile(profile)
    _equal(normalized["selectedWeaponSlotLimit"], 3,
        "voluntary lower slot selection was not persisted")

    reward_factors = {}
    for limit in (3, 4, 5, 6):
        reward = SurvivorEconomyModule.compute_run_reward(
            300, 400, 2, 1, 20,
            victory=True,
            end_reason="victory",
            weapon_slot_limit=limit,
        )
        reward_factors[limit] = reward["weaponSlotFactor"]
        _require("weaponSlotBonusGold" in reward,
            "slot reward is missing from the visible breakdown")
    _equal(reward_factors, {3: 1.20, 4: 1.10, 5: 1.05, 6: 1.00},
        "weapon slot reward factors changed")

    snapshot_profile = SurvivorProfile.validate_profile(profile)
    snapshot_profile["selectedWeaponSlotLimit"] = 3
    run_config = SurvivorRunConfig.compile_run_config(snapshot_profile)
    snapshot_profile["powerUps"]["meta_weapon_slots"] = 3
    snapshot_profile["selectedWeaponSlotLimit"] = 6
    _equal(run_config.weapon_slot_limit, 3,
        "an in-progress RunConfig changed with meta progression")

    weapons = SurvivorCatalogItems.WEAPONS[:4]
    controller = SurvivorBuildRules.UpgradePoolController(
        weapons,
        (),
        {"weapons": [row["id"] for row in weapons], "tomes": []},
        weapon_levels={row["id"]: 1 for row in weapons[:3]},
        weapon_slots=[row["id"] for row in weapons[:3]],
        max_weapon_slots=3,
        max_tome_slots=0,
        seed=7319,
    )
    candidate_ids = {row["id"] for row in controller.candidate_snapshot()}
    _require(weapons[3]["id"] not in candidate_ids,
        "a new weapon entered a full three-slot upgrade pool")

    balance = SurvivorBalance.validate_balance_report()
    _equal(set(balance["slotLimitResults"]), {"3", "4", "5", "6"},
        "balance harness does not cover Top 3/4/5/6 builds")
    return reward_factors


def SurvivorDomainPowersContract():
    policy = SurvivorRegionObjectives.DOMAIN_PROC_POLICY
    _require(not policy["entersWeaponSlots"] and not policy["entersUpgradePool"],
        "DomainPower entered the normal weapon build")
    _require(not policy["countsForWeaponQuests"],
        "DomainPower is attributed to weapon quests")
    _require(not policy["allowsTrinketProcs"] and not policy["allowsRecursiveProcs"],
        "DomainPower can recursively proc Trinkets")
    _equal(tuple(SurvivorRegionObjectives.DOMAIN_POWER_CONFIG),
        ("domain_star", "domain_thunder", "domain_water", "domain_wind"),
        "DomainPower order changed")
    _near(SurvivorRegionObjectives.DOMAIN_GLOBAL_VFX_SPACING, 1.10,
        "Domain VFX spacing changed")
    _require(not set(SurvivorRegionObjectives.DOMAIN_POWER_IDS).intersection(
        SurvivorContent.WEAPON_ORDER),
        "a DomainPower id aliases a normal weapon id")
    contaminated_weapon = dict(SurvivorCatalogItems.WEAPONS[0])
    contaminated_weapon["id"] = "domain_star"
    contaminated_pool = SurvivorBuildRules.UpgradePoolController(
        (contaminated_weapon,),
        (),
        {"weapons": ("domain_star",), "tomes": ()},
        weapon_levels={"domain_star": 0},
        tome_levels={},
        max_weapon_slots=3,
        max_tome_slots=0,
        excluded_ids=SurvivorRegionObjectives.DOMAIN_POWER_IDS,
    )
    _require(not contaminated_pool.candidate_snapshot(),
        "a contaminated catalog/profile can offer DomainPower as an upgrade")
    domains = SurvivorRegionObjectives.DOMAIN_POWER_CONFIG
    _near(domains["domain_star"]["vulnerability"], 0.08,
        "Star vulnerability changed")
    _require(not domains["domain_thunder"]["bossHardControl"],
        "Thunder hard-stuns the Boss")
    _require(not domains["domain_water"]["bossDisplacement"]
        and not domains["domain_wind"]["bossDisplacement"],
        "Water/Wind can displace the Boss")
    domain_source = open(
        os.path.join(os.path.dirname(__file__), "SurvivorDomainPowers.py"),
        "r", encoding="utf-8",
    ).read()
    _require("_apply_weapon_damage(" not in domain_source,
        "DomainPower re-entered normal weapon damage/proc attribution")
    _require("ApplySurvivorAgentStatus" in domain_source
        and '"interrupt"' in domain_source,
        "Domain Thunder does not consume the native interrupt contract")
    return True


def SurvivorObjectiveBossContract():
    event = SurvivorCatalogWorld.BOSS_EVENTS[0]
    _require("time" not in event and event["requiredRegions"] == 4,
        "waiting can still bypass the four-Region objective")
    _equal(SurvivorCatalogWorld.BOSS_BY_ID["star_dragon"]["health"], 50000.0,
        "Adventure Star Dragon base health changed")
    game_source = open(
        os.path.join(os.path.dirname(__file__), "SurvivorGame.py"),
        "r", encoding="utf-8",
    ).read()
    world_source = open(
        os.path.join(os.path.dirname(__file__), "SurvivorWorld.py"),
        "r", encoding="utf-8",
    ).read()
    _require("next_boss_time" not in game_source
        and "boss_spawn_index" not in game_source,
        "gameplay still infers the final Boss from the timed index")
    objective_source = open(
        os.path.join(os.path.dirname(__file__), "SurvivorObjectives.py"),
        "r", encoding="utf-8",
    ).read()
    _require('archetype_id=event["archetypeId"]' in objective_source,
        "objective Boss is not spawned with an explicit archetype")
    _require('monster.get("objective_boss", False)' in world_source,
        "victory is not gated by explicit objective Boss identity")
    activation_source = world_source.split(
        "    def _activate_monster(", 1,
    )[1].split("    def _runtime_warmup_progress(", 1)[0]
    _require("_kill_monster" not in activation_source,
        "capture mode can kill the objective Boss before identity registration")
    _require("_make_objective_boss_capacity" in objective_source
        and "Keep the explicit request pending" in objective_source,
        "objective Boss spawn cannot recover from the global population cap")
    return True


def SurvivorRegionSceneResourcesContract():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scene_path = os.path.join(project_root, "Assets", "Scenes", "MainGame.he")
    with open(scene_path, "r", encoding="utf-8") as stream:
        scene = json.load(stream)
    entities = scene.get("Entities", scene)
    if isinstance(entities, dict):
        component_rows = entities.values()
    else:
        component_rows = entities
    by_tag = {}
    for row in component_rows:
        components = row.get("Components", row) if isinstance(row, dict) else {}
        tag = components.get("TagComponent", {}).get("Tag")
        if tag:
            by_tag[tag] = components
    for region_id, config in SurvivorRegionObjectives.REGION_CONFIG.items():
        anchor = by_tag.get(config["anchorTag"])
        marker = by_tag.get(config["markerTag"])
        barrier = by_tag.get(config["anchorTag"] + " Barrier Dome")
        _require(anchor is not None and marker is not None and barrier is not None,
            region_id + " anchor, marker, or barrier dome is missing")
        _require("MeshComponent" not in anchor and "Rigidbody3DComponent" not in anchor,
            region_id + " anchor is not transform-only")
        _require("Rigidbody3DComponent" not in marker,
            region_id + " marker is no longer visual-only")
        _require("MeshComponent" in barrier and "Rigidbody3DComponent" not in barrier,
            region_id + " barrier dome must be visual-only mesh geometry")
        sockets = [
            tag for tag in by_tag
            if tag.startswith(config["spawnTagPrefix"])
        ]
        _equal(len(sockets), 10,
            region_id + " does not have ten deterministic sockets")

    with open(os.path.join(project_root, "Config", "Game.json"),
              "r", encoding="utf-8") as stream:
        game_config = json.load(stream)
    with open(os.path.join(project_root, "Config", "BaseEngine.json"),
              "r", encoding="utf-8") as stream:
        render_config = json.load(stream)
    _equal(
        render_config["Rendering"]["AntiAliasing"]["Mode"],
        "FXAA",
        "Starbloom gameplay no longer enables project-level FXAA",
    )
    warmups = {
        row["Name"]: row
        for row in game_config["Game"]["ResourceWarmup"]["Groups"]
    }
    for group in ("RegionFoundations", "RegionRewards", "FinalBoss"):
        _require(group in warmups, group + " warmup group is missing")
    _require("Wave15" not in warmups,
        "final Boss still depends on the fixed Wave15 warmup")
    roots = set(game_config["Cook"]["RootFiles"])
    for script in (
            "Scripts/SurvivorRegionObjectives.py",
            "Scripts/SurvivorRunConfig.py",
            "Scripts/SurvivorDomainPowers.py",
            "Scripts/SurvivorObjectives.py"):
        _require(script in roots, script + " is absent from Cook roots")
    _equal(
        SurvivorRuntimeAssets.asset_path("domain/water/impact-vfx"),
        "Assets/Effects/Survivor/ToonWater.efkpkg",
        "ToonWater is not the authoritative Water Domain runtime asset",
    )
    markup = open(
        os.path.join(project_root, "Assets", "UI", "SurvivorHUD.rml"),
        "r", encoding="utf-8",
    ).read()
    for element_id in (
            "region_objective_panel", "region_seal_star", "region_seal_thunder",
            "region_seal_water", "region_seal_wind", "domain_power_panel",
            "region_status_instruction", "objective_navigation",
            "result_region_order", "result_boss_ttk"):
        _require('id="' + element_id + '"' in markup,
            "HUD is missing " + element_id)
    return {"sceneTags": len(by_tag), "warmups": tuple(sorted(warmups))}


def SurvivorFixedUpdateContract():
    from types import SimpleNamespace
    import SurvivorGame as game_module

    calls = []
    pressed = [False]
    position = SimpleNamespace(x=0.0, y=0.0, z=0.0)

    class Player:
        def HasComponent(self, name):
            return name == "Transform"

        def GetComponent(self, name):
            _equal(name, "Transform", "fixed update requested another component")
            return SimpleNamespace(Translation=position)

    game = SimpleNamespace(
        bMenuScene=False, bSceneTransitionRequested=False,
        bLoadingAdventure=False, bSettingsOpen=False,
        bInMainMenu=False, bGameOver=False,
        bAwaitingUpgrade=False, bPaused=False,
        bRuntimeReady=True, player=Player(), last_pause_pressed=False,
        player_ground_check_timer=1.0, FALL_RECOVERY_Y=-100.0,
    )
    game._update_gameplay_bookkeeping = lambda dt: (
        calls.append(("bookkeeping", dt)) or position
    )
    game._update_region_objectives = lambda _pos, dt: calls.append(("objective", dt))
    game._drain_pending_pickup_spawns = lambda: None
    game._drain_pending_chest_spawns = lambda: None
    game._spawn_wave = lambda _pos: None
    game._update_monster_phase = lambda _pos: True
    game._update_pickup_phase = lambda _pos: None
    game._update_weapons = lambda _pos, dt: calls.append(("weapon", dt))
    game._update_domain_powers = lambda _pos, dt: calls.append(("domain", dt))

    original_engine = game_module.HEngine
    game_module.HEngine = SimpleNamespace(
        Input=SimpleNamespace(IsKeyPressed=lambda _key: pressed[0]),
        KeyCode=SimpleNamespace(Escape=1),
    )
    try:
        for dt in (1.0 / 60.0, 1.0 / 60.0, 1.0 / 30.0):
            game_module.SurvivorGame.FixedUpdate(
                game, SimpleNamespace(GetSeconds=lambda dt=dt: dt),
            )
        for stage in ("bookkeeping", "objective", "weapon", "domain"):
            values = [dt for name, dt in calls if name == stage]
            _equal(values, [1.0 / 60.0, 1.0 / 60.0, 1.0 / 30.0],
                stage + " did not consume exactly one fixed dt per tick")
        count = len(calls)
        game.bPaused = True
        game_module.SurvivorGame.FixedUpdate(
            game, SimpleNamespace(GetSeconds=lambda: 1.0 / 60.0),
        )
        _equal(len(calls), count, "paused gameplay advanced a fixed tick")
        game.bPaused = False
        game.bRuntimeReady = False
        game_module.SurvivorGame.FixedUpdate(
            game, SimpleNamespace(GetSeconds=lambda: 1.0 / 60.0),
        )
        _equal(len(calls), count, "warm-up advanced fixed gameplay")
        game.bRuntimeReady = True
        pressed[0] = True
        game_module.SurvivorGame.FixedUpdate(
            game, SimpleNamespace(GetSeconds=lambda: 1.0 / 60.0),
        )
        _equal(len(calls), count, "pause key edge advanced gameplay")
    finally:
        game_module.HEngine = original_engine


def SurvivorProjectileVisualWarmup():
    from types import SimpleNamespace

    scale = object()
    created = []

    class Visual:
        def __init__(self):
            self.transform = SimpleNamespace(Scale=None)

        def GetComponent(self, name):
            _equal(name, "Transform", "visual warm-up requested another component")
            return self.transform

    def acquire(kind):
        visual = Visual()
        created.append((kind, visual))
        return visual

    world = SimpleNamespace(
        bRuntimeReady=False,
        warmup_stage="visuals",
        pending_effects=[],
        pending_visual_warmups=["comet", "wheel"],
        projectile_visual_pool={"comet": [], "wheel": []},
        HIDDEN_SCALE=scale,
        _acquire_projectile_visual=acquire,
    )
    SurvivorWorld.SurvivorWorldMixin._advance_runtime_warmup(world)
    _equal(world.warmup_stage, "visuals", "visual warm-up skipped the next frame")
    _equal(len(world.projectile_visual_pool["comet"]), 1,
           "first visual was not pooled")
    SurvivorWorld.SurvivorWorldMixin._advance_runtime_warmup(world)
    _equal([kind for kind, _ in created], ["comet", "wheel"],
           "visual warm-up order changed")
    _require(all(visual.transform.Scale is scale for _, visual in created),
             "prewarmed visual was left visible")
    SurvivorWorld.SurvivorWorldMixin._advance_runtime_warmup(world)
    _equal(world.warmup_stage, "resources", "visual warm-up did not finish")
    return True


CONTRACTS = {
    "SurvivorContentCatalog": SurvivorContentCatalog,
    "SurvivorRuntimeAssetAuthority": SurvivorRuntimeAssetAuthority,
    "SurvivorProgressionMigration": SurvivorProgressionMigration,
    "SurvivorEconomy": SurvivorEconomy,
    "SurvivorChallengeComposition": SurvivorChallengeComposition,
    "SurvivorUnlocksAndPurchases": SurvivorUnlocksAndPurchases,
    "SurvivorUpgradePoolControl": SurvivorUpgradePoolControl,
    "SurvivorEvolutionResolver": SurvivorEvolutionResolver,
    "SurvivorHubGamepadNavigation": SurvivorHubGamepadNavigation,
    "SurvivorCharacterStartState": SurvivorCharacterStartState,
    "SurvivorWeaponLevelZero": SurvivorWeaponLevelZero,
    "SurvivorProjectileBudget": SurvivorProjectileBudget,
    "SurvivorWaveTimeline": SurvivorWaveTimeline,
    "SurvivorRunEndTransaction": SurvivorRunEndTransaction,
    "SurvivorBalanceHarness": SurvivorBalanceHarness,
    "SurvivorQuests": SurvivorQuestsContract,
    "SurvivorRegionObjectives": SurvivorRegionObjectivesContract,
    "SurvivorWeaponSlots": SurvivorWeaponSlotsContract,
    "SurvivorDomainPowers": SurvivorDomainPowersContract,
    "SurvivorObjectiveBoss": SurvivorObjectiveBossContract,
    "SurvivorRegionSceneResources": SurvivorRegionSceneResourcesContract,
    "SurvivorFixedUpdate": SurvivorFixedUpdateContract,
    "SurvivorProjectileVisualWarmup": SurvivorProjectileVisualWarmup,
}


def contract_names():
    return tuple(CONTRACTS)


def run_contract(name):
    if name not in CONTRACTS:
        raise KeyError("Unknown Survivor Project contract: " + str(name))
    return CONTRACTS[name]()
