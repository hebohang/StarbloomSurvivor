"""Validated aggregate catalog for Starbloom Survivor.

The category modules contain parameters only.  Behavior values are selected
from finite registries here and never evaluated as arbitrary code.
"""

import json
import os

from SurvivorCatalogCharacters import CHARACTERS, CHARACTER_BY_ID
from SurvivorCatalogItems import (
    EVOLUTIONS,
    EVOLUTION_BY_ID,
    TOMES,
    TOME_BY_ID,
    TRINKETS,
    TRINKET_BY_ID,
    WEAPONS,
    WEAPON_BY_ID,
)
from SurvivorCatalogMeta import POWER_UPS, PRODUCTS, QUESTS, QUEST_BY_ID
from SurvivorCatalogWorld import (
    BOSSES,
    BOSS_BY_ID,
    BOSS_EVENTS,
    CHALLENGES,
    DIFFICULTIES,
    ENEMIES,
    ENEMY_BY_ID,
    WAVES,
)


CATALOG_VERSION = 4
LANGUAGES = ("zh_cn", "en")
WEAPON_BEHAVIORS = frozenset({
    "chain", "expanding_ring", "lob_homing", "fan_pierce", "bounce",
    "zone", "delayed_smite", "homing_volley", "fan_projectile",
    "returning", "radial_projectile", "lob_zone", "echo_ring",
    "returning_lob", "orbit_beam", "lob_split", "orbit_contact",
    "telegraphed_beam",
})
ENEMY_BEHAVIORS = frozenset({
    "chaser", "flanker", "armored", "bruiser", "zone", "charger",
    "ranged", "lobber", "ghost", "shield", "suicide", "summoner",
    "boss_yeti", "boss_orc", "boss_demon", "boss_mushroom", "boss_dragon",
})


class CatalogValidationError(ValueError):
    pass


def _valid_id(value):
    if not isinstance(value, str) or not value:
        return False
    if value[0] < "a" or value[0] > "z":
        return False
    return all(
        ("a" <= character <= "z")
        or ("0" <= character <= "9")
        or character == "_"
        for character in value
    )


def _require(condition, message, errors):
    if not condition:
        errors.append(message)


def _validate_localized_field(entry_id, field_name, localized, errors):
    for language in LANGUAGES:
        _require(
            isinstance(localized, dict)
            and isinstance(localized.get(language), str)
            and bool(localized.get(language).strip()),
            str(entry_id) + " is missing localized " + field_name + " " + language,
            errors,
        )


def _validate_collection(name, entries, errors):
    ids = []
    for entry in entries:
        entry_id = entry.get("id")
        _require(_valid_id(entry_id), name + " has invalid id: " + str(entry_id), errors)
        ids.append(entry_id)
        localized = entry.get("name", entry.get("title", {}))
        _validate_localized_field(entry_id, "name", localized, errors)
        for field_name in ("description", "statText"):
            if field_name in entry:
                _validate_localized_field(
                    entry_id, field_name, entry[field_name], errors,
                )
    _require(len(ids) == len(set(ids)), name + " contains duplicate ids", errors)


def _validate_quest_graph(errors):
    visiting = set()
    visited = set()

    def visit(quest_id):
        if quest_id in visited:
            return
        if quest_id in visiting:
            errors.append("Quest prerequisite cycle includes " + quest_id)
            return
        visiting.add(quest_id)
        for prerequisite in QUEST_BY_ID[quest_id]["prerequisiteIds"]:
            if prerequisite not in QUEST_BY_ID:
                errors.append(quest_id + " references missing quest " + prerequisite)
            else:
                visit(prerequisite)
        visiting.remove(quest_id)
        visited.add(quest_id)

    for quest_id in QUEST_BY_ID:
        visit(quest_id)


def _asset_path(project_root, path):
    return os.path.join(project_root, *path.split("/"))


def validate_catalog(project_root=None, bCheckResources=False):
    errors = []
    for name, entries in (
            ("characters", CHARACTERS),
            ("weapons", WEAPONS),
            ("evolutions", EVOLUTIONS),
            ("tomes", TOMES),
            ("trinkets", TRINKETS),
            ("enemies", ENEMIES),
            ("bosses", BOSSES),
            ("quests", QUESTS),
            ("powerUps", POWER_UPS)):
        _validate_collection(name, entries, errors)

    _require(len(CHARACTERS) == 10, "Catalog must contain 10 characters", errors)
    _require(len(WEAPONS) == 18, "Catalog must contain 18 base weapons", errors)
    _require(len(EVOLUTIONS) == 9, "Catalog must contain 9 evolutions", errors)
    _require(len(TOMES) == 16, "Catalog must contain 16 Tomes", errors)
    _require(len(TRINKETS) == 12, "Catalog must contain 12 Trinkets", errors)
    _require(len(ENEMIES) >= 12, "Catalog must contain at least 12 enemies", errors)
    _require(len(BOSSES) >= 5, "Catalog must contain at least 5 bosses", errors)
    _require(len(QUESTS) >= 36, "Catalog must contain at least 36 quests", errors)
    _require(len(POWER_UPS) == 13, "Catalog must contain 13 PowerUps", errors)
    _require(len(DIFFICULTIES) == 3, "Catalog must contain 3 difficulties", errors)
    _require(len(CHALLENGES) >= 6, "Catalog must contain at least 6 challenges", errors)

    for character in CHARACTERS:
        _require(
            character["starterWeapon"] in WEAPON_BY_ID,
            character["id"] + " has missing starter weapon",
            errors,
        )
        _require(character["unlockId"] in QUEST_BY_ID, character["id"] + " has missing unlock", errors)

    required_weapon_fields = (
        "id", "icon", "starterEligible", "maxLevel", "rarityWeight", "behavior",
        "tags", "baseDamage", "cooldown", "area", "speed", "duration", "amount",
        "pierce", "bounce", "knockback", "hitboxDelay", "poolLimit",
        "visualPoolLimit", "projectilePrefab", "castVfx", "bodyVfx", "impactVfx",
        "audioEvent", "levelPlan", "supportedStats", "unlockId", "evolutionId",
    )
    for weapon in WEAPONS:
        missing = [field for field in required_weapon_fields if field not in weapon]
        _require(not missing, weapon["id"] + " missing fields " + str(missing), errors)
        _require(weapon["behavior"] in WEAPON_BEHAVIORS, weapon["id"] + " has unknown behavior", errors)
        _require(weapon["maxLevel"] == 10, weapon["id"] + " must have 10 levels", errors)
        levels = [level.get("level") for level in weapon["levelPlan"]]
        _require(levels == list(range(1, 11)), weapon["id"] + " has invalid level plan", errors)
        _require(weapon["poolLimit"] > 0, weapon["id"] + " has invalid pool limit", errors)
        _require(weapon["visualPoolLimit"] >= 0, weapon["id"] + " has invalid visual pool", errors)
        _require(weapon["hitboxDelay"] >= 0.0, weapon["id"] + " has invalid hit delay", errors)
        _require(weapon["unlockId"] in QUEST_BY_ID, weapon["id"] + " has missing unlock", errors)
        evolution_id = weapon["evolutionId"]
        _require(not evolution_id or evolution_id in EVOLUTION_BY_ID, weapon["id"] + " has missing evolution", errors)

    for evolution in EVOLUTIONS:
        _require(evolution["weaponId"] in WEAPON_BY_ID, evolution["id"] + " has missing weapon", errors)
        _require(evolution["tomeId"] in TOME_BY_ID, evolution["id"] + " has missing Tome", errors)
        _require(
            WEAPON_BY_ID[evolution["weaponId"]]["evolutionId"] == evolution["id"],
            evolution["id"] + " is not reachable from its weapon",
            errors,
        )

    for item in TOMES + TRINKETS:
        _require(item["unlockId"] in QUEST_BY_ID, item["id"] + " has missing unlock", errors)

    power_up_icons = []
    for power_up in POWER_UPS:
        icon = power_up.get("icon")
        _require(
            isinstance(icon, str) and bool(icon),
            power_up["id"] + " is missing its PowerUp icon",
            errors,
        )
        if isinstance(icon, str):
            power_up_icons.append(icon)
    _require(
        len(power_up_icons) == len(set(power_up_icons)),
        "PowerUp icon paths must be unique",
        errors,
    )

    for enemy in ENEMIES + BOSSES:
        _require(enemy["behaviorId"] in ENEMY_BEHAVIORS, enemy["id"] + " has unknown behavior", errors)
        _require(enemy["telegraph"] >= 0.35, enemy["id"] + " telegraph is too short", errors)

    _validate_quest_graph(errors)
    content_ids = {
        "characters": set(CHARACTER_BY_ID),
        "weapons": set(WEAPON_BY_ID),
        "tomes": set(TOME_BY_ID),
        "trinkets": set(TRINKET_BY_ID),
    }
    product_keys = set()
    for product in PRODUCTS:
        key = (product["category"], product["contentId"])
        _require(key not in product_keys, "Duplicate product " + str(key), errors)
        product_keys.add(key)
        _require(product["category"] in content_ids, "Unknown product category", errors)
        if product["category"] in content_ids:
            _require(product["contentId"] in content_ids[product["category"]], "Product has missing content", errors)
        _require(product["unlockId"] in QUEST_BY_ID, "Product has missing unlock", errors)
        _require(isinstance(product["price"], int) and product["price"] >= 0, "Product has invalid price", errors)
    for category, ids in content_ids.items():
        for content_id in ids:
            _require((category, content_id) in product_keys, "Missing product " + category + ":" + content_id, errors)

    expected_start = 0.0
    for wave in WAVES:
        _require(wave["start"] == expected_start, "Wave timeline has a gap or overlap", errors)
        _require(wave["end"] > wave["start"], "Wave has non-positive duration", errors)
        _require(bool(wave["pool"]), "Wave has an empty pool", errors)
        _require(all(enemy_id in ENEMY_BY_ID for enemy_id, _ in wave["pool"]), "Wave references missing enemy", errors)
        expected_start = wave["end"]
    _require(expected_start == 900, "Wave timeline must end at 900 seconds", errors)
    _require(len(BOSS_EVENTS) == 1, "Objective mode must define exactly one final Boss event", errors)
    if BOSS_EVENTS:
        objective_boss = BOSS_EVENTS[0]
        _require("time" not in objective_boss,
            "Objective Boss must not retain a fixed timeline trigger", errors)
        _require(
            objective_boss.get("id") == "starbloom_final_objective"
            and objective_boss.get("bossId") == "star_dragon"
            and objective_boss.get("objectiveBoss")
            and objective_boss.get("finalBoss")
            and objective_boss.get("requiredRegions") == 4,
            "Final Boss event must require the explicit four-Region objective",
            errors,
        )
    _require(all(event["bossId"] in BOSS_BY_ID for event in BOSS_EVENTS), "Boss event has missing boss", errors)

    for index in range(1, len(DIFFICULTIES)):
        previous = DIFFICULTIES[index - 1]
        current = DIFFICULTIES[index]
        for field in ("health", "damage", "speed", "spawn", "gold"):
            _require(current[field] >= previous[field], "Difficulty is not monotonic for " + field, errors)

    if bCheckResources:
        _require(project_root is not None, "Resource validation requires project root", errors)
        if project_root is not None:
            resource_paths = []
            for character in CHARACTERS:
                resource_paths.extend((character["mesh"], character["controller"], character["idle"], character["dance"], character["icon"]))
            for weapon in WEAPONS:
                resource_paths.append(weapon["icon"])
                for field in ("projectilePrefab", "castVfx", "bodyVfx", "impactVfx"):
                    if weapon[field]:
                        resource_paths.append(weapon[field])
            for item in TOMES + TRINKETS + EVOLUTIONS:
                resource_paths.append(item["icon"])
            for power_up in POWER_UPS:
                resource_paths.append(power_up["icon"])
            for enemy in ENEMIES + BOSSES:
                resource_paths.extend((enemy["prefab"], enemy["mesh"], enemy["controller"], enemy["icon"]))
            for path in sorted(set(resource_paths)):
                _require(os.path.isfile(_asset_path(project_root, path)), "Missing catalog resource " + path, errors)
            provenance_path = os.path.join(
                project_root,
                "SourceAssets",
                "EffekseerInbox",
                "survivor-expansion-vfx",
                "asset.json",
            )
            if os.path.isfile(provenance_path):
                try:
                    with open(provenance_path, "r", encoding="utf-8") as source:
                        provenance = json.load(source)
                except (OSError, ValueError) as error:
                    errors.append("Expansion VFX provenance is unreadable: " + str(error))
                else:
                    _require(
                        provenance.get("intake_status") == "IMPORTED",
                        "Expansion VFX intake is not finalized",
                        errors,
                    )
                    _require(
                        "DX12" in provenance.get("supported_renderer_apis", ()),
                        "Expansion VFX lacks DX12 runtime evidence",
                        errors,
                    )
                    _require(
                        provenance.get("has_cpu_fallback") is True,
                        "Expansion VFX lacks a CPU fallback",
                        errors,
                    )
                    baseline = provenance.get("profiler_baseline", {})
                    _require(
                        baseline.get("runtime_regression", {}).get("status") == "PASS",
                        "Expansion VFX package regression is not PASS",
                        errors,
                    )
                    _require(
                        len(baseline.get("showcase_samples", ())) >= 4
                        and all(
                            sample.get("status") == "PASS"
                            for sample in baseline.get("showcase_samples", ())
                        ),
                        "Expansion VFX visual showcase is incomplete",
                        errors,
                    )
            else:
                _require(
                    not os.path.isdir(os.path.join(project_root, "SourceAssets")),
                    "Expansion VFX provenance manifest is missing",
                    errors,
                )

    if errors:
        raise CatalogValidationError("\n".join(errors))
    return {
        "characters": len(CHARACTERS),
        "weapons": len(WEAPONS),
        "evolutions": len(EVOLUTIONS),
        "tomes": len(TOMES),
        "trinkets": len(TRINKETS),
        "enemies": len(ENEMIES),
        "bosses": len(BOSSES),
        "quests": len(QUESTS),
        "powerUps": len(POWER_UPS),
        "difficulties": len(DIFFICULTIES),
        "challenges": len(CHALLENGES),
    }


SURVIVOR_CATALOG = {
    "version": CATALOG_VERSION,
    "characters": CHARACTERS,
    "weapons": WEAPONS,
    "evolutions": EVOLUTIONS,
    "tomes": TOMES,
    "trinkets": TRINKETS,
    "enemies": ENEMIES,
    "bosses": BOSSES,
    "waves": WAVES,
    "bossEvents": BOSS_EVENTS,
    "difficulties": DIFFICULTIES,
    "challenges": CHALLENGES,
    "quests": QUESTS,
    "products": PRODUCTS,
    "powerUps": POWER_UPS,
}
