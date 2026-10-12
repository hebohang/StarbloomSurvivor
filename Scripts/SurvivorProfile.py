"""Versioned, recoverable profile storage for Starbloom Survivor.

The module is intentionally independent from HEngine.  It accepts an optional
logger callback so the game can route recovery messages to its normal logger.
"""

import json
import math
import os

import SurvivorMetaProgression
import SurvivorRules

from SurvivorCatalogWorld import CHALLENGES
from SurvivorEconomy import (
    MAX_RUN_COUNTER,
    MAX_RUN_SECONDS,
    MAX_WALLET_GOLD,
    POWER_UP_DEFS,
)


PROFILE_VERSION = 4
_TEMP_FILE_SERIAL = 0
CHALLENGE_IDS = tuple(entry["id"] for entry in CHALLENGES)
RETIRED_NORMAL_WEAPONS = frozenset(("thunder", "starfall", "tornado"))
RETIRED_WEAPON_REFUNDS = {"thunder": 0, "tornado": 100, "starfall": 120}
RETIRED_WEAPON_QUESTS = frozenset(
    "quest_weapon_" + weapon_id for weapon_id in RETIRED_NORMAL_WEAPONS
)

LEGACY_CHARACTERS = ("starpaw", "peachy", "mossling", "snowbean", "azura")
LEGACY_WEAPONS = (
    "ring", "fireball", "moonblade", "bubble", "aura", "dagger",
    "starwheel", "petalstorm", "comet",
)
LEGACY_TOMES = (
    "magnet", "vitality", "guard", "might", "haste", "reach",
    "fortune", "growth", "quantity", "velocity", "duration",
)
STARTER_WEAPONS = ("comet", "ring", "fireball", "moonblade", "bubble")
STARTER_TOMES = (
    "magnet", "vitality", "guard", "might", "haste", "reach", "growth", "velocity",
)
STARTER_TRINKETS = (
    "prism_lens", "sticky_honey", "tiny_magnet", "marshmallow_shield",
)


class ProfileError(RuntimeError):
    """Base class for profile load, validation, and migration failures."""


class ProfileValidationError(ProfileError):
    """Raised when a profile does not satisfy the supported schema."""


class FutureProfileVersionError(ProfileError):
    """Raised without fallback or overwrite for an unknown future version."""


def _clone_json_value(value):
    if isinstance(value, dict):
        return {key: _clone_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_clone_json_value(item) for item in value]
    return value


def default_profile():
    return {
        "version": PROFILE_VERSION,
        "walletGold": 0,
        "selectedCharacter": "starpaw",
        "selectedDifficulty": "adventure",
        "selectedChallenges": [],
        "selectedChallenge": "none",
        "selectedWeaponSlotLimit": SurvivorMetaProgression.BASE_WEAPON_SLOTS,
        "career": {
            "runs": 0,
            "wins": 0,
            "totalKills": 0,
            "totalElites": 0,
            "totalBossKills": 0,
            "totalGoldEarned": 0,
            "bestSurvivalSeconds": 0.0,
            "bestLevel": 1,
            "highestDifficulty": "adventure",
        },
        "owned": {
            "characters": ["starpaw"],
            "weapons": list(STARTER_WEAPONS),
            "tomes": list(STARTER_TOMES),
            "trinkets": list(STARTER_TRINKETS),
        },
        "eligible": {
            "characters": [], "weapons": [], "tomes": [], "trinkets": [],
        },
        "powerUps": {},
        "powerUpsEnabled": {},
        "characterTraining": {},
        "characterTrainingEnabled": {},
        "characterMasteryXp": {},
        "completedQuests": [],
        "questProgress": {},
        "trackedQuests": [],
        "discoveredEvolutions": [],
        "discoveredDomains": [],
        "poolDisabled": {
            "weapons": [], "tomes": [], "trinkets": [],
        },
        "difficultyClears": {},
        "challengeClears": {},
        "lastRun": None,
    }


def _object(value, field_name):
    if not isinstance(value, dict):
        raise ProfileValidationError(field_name + " must be an object")
    return value


def _clamped_int(value, field_name, minimum=0, maximum=MAX_RUN_COUNTER):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileValidationError(field_name + " must be an integer")
    return min(maximum, max(minimum, value))


def _clamped_float(value, field_name, minimum=0.0, maximum=MAX_RUN_SECONDS):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileValidationError(field_name + " must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ProfileValidationError(field_name + " must be finite")
    return min(maximum, max(minimum, result))


def _string(value, field_name, default=None):
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ProfileValidationError(field_name + " must be a non-empty string")
    return value


def _string_list(value, field_name, maximum=4096):
    if not isinstance(value, list):
        raise ProfileValidationError(field_name + " must be an array")
    result = []
    seen = set()
    for item in value:
        item = _string(item, field_name + "[]")
        if item not in seen:
            result.append(item)
            seen.add(item)
        if len(result) >= maximum:
            break
    return result


def _string_int_map(value, field_name, maximum=MAX_RUN_COUNTER):
    value = _object(value, field_name)
    result = {}
    for key, item in value.items():
        key = _string(key, field_name + ".key")
        result[key] = _clamped_int(item, field_name + "." + key, 0, maximum)
    return result


def _string_number_map(value, field_name, maximum=MAX_RUN_COUNTER):
    value = _object(value, field_name)
    result = {}
    for key, item in value.items():
        key = _string(key, field_name + ".key")
        number = _clamped_float(item, field_name + "." + key, 0.0, maximum)
        result[key] = int(number) if number.is_integer() else number
    return result


def _completion_map(value, field_name):
    value = _object(value, field_name)
    result = {}
    for key, item in value.items():
        key = _string(key, field_name + ".key")
        if not isinstance(item, (bool, int)):
            raise ProfileValidationError(field_name + "." + key + " must be bool or int")
        result[key] = bool(item)
    return result


def _legacy_int(profile, key, default, minimum=0):
    value = profile.get(key, default)
    if isinstance(value, bool):
        raise ProfileValidationError(key + " must be numeric")
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ProfileValidationError(key + " must be an integer") from error
    return min(MAX_RUN_COUNTER, max(minimum, value))


def _legacy_float(profile, key, default):
    value = profile.get(key, default)
    if isinstance(value, bool):
        raise ProfileValidationError(key + " must be numeric")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ProfileValidationError(key + " must be numeric") from error
    if not math.isfinite(value):
        raise ProfileValidationError(key + " must be finite")
    return min(MAX_RUN_SECONDS, max(0.0, value))


def _migrate_v1(profile):
    total_kills = _legacy_int(profile, "total_kills", 0)
    best_survival = _legacy_float(profile, "best_survival", 0.0)
    best_level = _legacy_int(profile, "best_level", 1, 1)
    boss_kills = _legacy_int(profile, "boss_kills", 0)

    owned_characters = ["starpaw"]
    if best_survival >= 120.0:
        owned_characters.append("peachy")
    if total_kills >= 750:
        owned_characters.append("mossling")
    if boss_kills >= 1:
        owned_characters.append("snowbean")
    if best_level >= 20:
        owned_characters.append("azura")

    result = default_profile()
    result["career"]["totalKills"] = total_kills
    result["career"]["bestSurvivalSeconds"] = best_survival
    result["career"]["bestLevel"] = best_level
    result["career"]["totalBossKills"] = boss_kills
    result["owned"]["characters"] = owned_characters
    result["owned"]["weapons"] = list(LEGACY_WEAPONS)
    result["owned"]["tomes"] = list(LEGACY_TOMES)
    selected = profile.get("selected_character", "starpaw")
    if selected in owned_characters:
        result["selectedCharacter"] = selected
    return result


def _normalize_current_profile(profile, source_version=PROFILE_VERSION):
    base = default_profile()
    result = default_profile()
    result["walletGold"] = _clamped_int(
        profile.get("walletGold", base["walletGold"]),
        "walletGold", 0, MAX_WALLET_GOLD,
    )

    career = _object(profile.get("career", base["career"]), "career")
    result["career"] = {
        "runs": _clamped_int(career.get("runs", 0), "career.runs"),
        "wins": _clamped_int(career.get("wins", 0), "career.wins"),
        "totalKills": _clamped_int(career.get("totalKills", 0), "career.totalKills"),
        "totalElites": _clamped_int(career.get("totalElites", 0), "career.totalElites"),
        "totalBossKills": _clamped_int(
            career.get("totalBossKills", 0), "career.totalBossKills",
        ),
        "totalGoldEarned": _clamped_int(
            career.get("totalGoldEarned", 0), "career.totalGoldEarned",
        ),
        "bestSurvivalSeconds": _clamped_float(
            career.get("bestSurvivalSeconds", 0.0), "career.bestSurvivalSeconds",
        ),
        "bestLevel": _clamped_int(career.get("bestLevel", 1), "career.bestLevel", 1),
        "highestDifficulty": _string(
            career.get("highestDifficulty", "adventure"), "career.highestDifficulty",
        ),
    }

    owned = _object(profile.get("owned", base["owned"]), "owned")
    eligible = _object(profile.get("eligible", base["eligible"]), "eligible")
    for category in ("characters", "weapons", "tomes", "trinkets"):
        owned_items = _string_list(
            owned.get(category, base["owned"][category]), "owned." + category,
        )
        if category == "weapons":
            if source_version <= 3:
                refund = sum(
                    RETIRED_WEAPON_REFUNDS.get(weapon_id, 0)
                    for weapon_id in set(owned_items)
                )
                result["walletGold"] = min(
                    MAX_WALLET_GOLD, result["walletGold"] + refund,
                )
            owned_items = [
                item for item in owned_items
                if item not in RETIRED_NORMAL_WEAPONS
            ]
        result["owned"][category] = owned_items
        result["eligible"][category] = [
            item for item in _string_list(
                eligible.get(category, []), "eligible." + category,
            ) if item not in result["owned"][category]
            and not (
                category == "weapons" and item in RETIRED_NORMAL_WEAPONS
            )
        ]
    if "starpaw" not in result["owned"]["characters"]:
        result["owned"]["characters"].insert(0, "starpaw")

    selected_character = _string(
        profile.get("selectedCharacter", "starpaw"), "selectedCharacter",
    )
    result["selectedCharacter"] = (
        selected_character
        if selected_character in result["owned"]["characters"]
        else "starpaw"
    )
    result["selectedDifficulty"] = _string(
        profile.get("selectedDifficulty", "adventure"), "selectedDifficulty",
    )
    if "selectedChallenges" in profile:
        selected_challenge_source = _string_list(
            profile.get("selectedChallenges"),
            "selectedChallenges",
            len(CHALLENGE_IDS),
        )
    else:
        selected_challenge_source = _string(
            profile.get("selectedChallenge", "none"),
            "selectedChallenge",
        )
    selected_challenges = SurvivorRules.normalize_challenge_ids(
        selected_challenge_source,
        CHALLENGE_IDS,
    )
    result["selectedChallenges"] = list(selected_challenges)
    result["selectedChallenge"] = (
        selected_challenges[0] if selected_challenges else "none"
    )

    power_ups = _object(profile.get("powerUps", {}), "powerUps")
    enabled = _object(profile.get("powerUpsEnabled", {}), "powerUpsEnabled")
    for power_up_id, definition in POWER_UP_DEFS.items():
        level = _clamped_int(
            power_ups.get(power_up_id, 0),
            "powerUps." + power_up_id,
            0,
            len(definition["prices"]),
        )
        if level > 0:
            result["powerUps"][power_up_id] = level
            enabled_value = enabled.get(power_up_id, True)
            if not isinstance(enabled_value, bool):
                raise ProfileValidationError(
                    "powerUpsEnabled." + power_up_id + " must be a bool",
                )
            result["powerUpsEnabled"][power_up_id] = (
                enabled_value if definition.get("toggleable", True) else True
            )

    purchased_weapon_slots = SurvivorMetaProgression.purchased_weapon_slot_limit(
        result,
    )
    result["selectedWeaponSlotLimit"] = _clamped_int(
        profile.get(
            "selectedWeaponSlotLimit",
            SurvivorMetaProgression.BASE_WEAPON_SLOTS,
        ),
        "selectedWeaponSlotLimit",
        SurvivorMetaProgression.BASE_WEAPON_SLOTS,
        purchased_weapon_slots,
    )

    result["characterTraining"] = _string_int_map(
        profile.get("characterTraining", {}), "characterTraining", 5,
    )
    result["characterTrainingEnabled"] = _completion_map(
        profile.get("characterTrainingEnabled", {}),
        "characterTrainingEnabled",
    )
    result["characterMasteryXp"] = _string_int_map(
        profile.get("characterMasteryXp", {}), "characterMasteryXp",
    )
    result["completedQuests"] = _string_list(
        profile.get("completedQuests", []), "completedQuests",
    )
    result["questProgress"] = {
        quest_id: value
        for quest_id, value in _string_number_map(
            profile.get("questProgress", {}), "questProgress",
        ).items()
        if quest_id not in RETIRED_WEAPON_QUESTS
    }
    result["trackedQuests"] = [
        quest_id for quest_id in _string_list(
            profile.get("trackedQuests", []), "trackedQuests", 3,
        ) if quest_id not in RETIRED_WEAPON_QUESTS
    ]
    result["discoveredEvolutions"] = [
        evolution_id for evolution_id in _string_list(
            profile.get("discoveredEvolutions", []), "discoveredEvolutions",
        ) if evolution_id != "storybooktempest"
    ]
    result["discoveredDomains"] = _string_list(
        profile.get("discoveredDomains", []), "discoveredDomains",
    )

    disabled = _object(profile.get("poolDisabled", base["poolDisabled"]), "poolDisabled")
    for category in ("weapons", "tomes", "trinkets"):
        result["poolDisabled"][category] = [
            item for item in _string_list(
                disabled.get(category, []), "poolDisabled." + category,
            ) if item in result["owned"][category]
        ]
    result["difficultyClears"] = _completion_map(
        profile.get("difficultyClears", {}), "difficultyClears",
    )
    result["challengeClears"] = _completion_map(
        profile.get("challengeClears", {}), "challengeClears",
    )

    last_run = profile.get("lastRun")
    if last_run is not None:
        last_run = _clone_json_value(_object(last_run, "lastRun"))
        last_run["runId"] = _string(last_run.get("runId"), "lastRun.runId")
        committed = last_run.get("rewardCommitted", False)
        if not isinstance(committed, bool):
            raise ProfileValidationError("lastRun.rewardCommitted must be a bool")
        last_run["rewardCommitted"] = committed
        if "challengeIds" in last_run:
            last_run_source = _string_list(
                last_run.get("challengeIds"),
                "lastRun.challengeIds",
                len(CHALLENGE_IDS),
            )
        else:
            last_run_source = _string(
                last_run.get("challengeId", "none"),
                "lastRun.challengeId",
            )
        last_run_challenges = SurvivorRules.normalize_challenge_ids(
            last_run_source,
            CHALLENGE_IDS,
        )
        last_run["challengeIds"] = list(last_run_challenges)
        last_run["challengeId"] = (
            last_run_challenges[0] if last_run_challenges else "none"
        )
        legacy_weapon_slot_limit = (
            SurvivorMetaProgression.MAX_WEAPON_SLOTS
            if source_version <= 2 else
            result["selectedWeaponSlotLimit"]
        )
        last_run["weaponSlotLimit"] = _clamped_int(
            last_run.get("weaponSlotLimit", legacy_weapon_slot_limit),
            "lastRun.weaponSlotLimit",
            SurvivorMetaProgression.BASE_WEAPON_SLOTS,
            SurvivorMetaProgression.MAX_WEAPON_SLOTS,
        )
        result["lastRun"] = last_run
    return result


def migrate_profile(profile):
    """Migrate a supported object to the normalized current profile."""

    profile = _object(profile, "profile")
    version = profile.get("version")
    if version is None:
        legacy_keys = {
            "total_kills", "best_survival", "best_level",
            "boss_kills", "selected_character",
        }
        if not legacy_keys.intersection(profile):
            raise ProfileValidationError("profile version is missing")
        version = 1
    if isinstance(version, bool) or not isinstance(version, int):
        raise ProfileValidationError("profile version must be an integer")
    if version > PROFILE_VERSION:
        raise FutureProfileVersionError(
            "profile version " + str(version)
            + " is newer than supported version " + str(PROFILE_VERSION),
        )
    if version == 1:
        return _migrate_v1(profile)
    if version not in (2, 3, PROFILE_VERSION):
        raise ProfileValidationError("unsupported profile version: " + str(version))
    return _normalize_current_profile(profile, version)


def validate_profile(profile):
    return migrate_profile(profile)


def _reject_json_constant(value):
    raise ValueError("non-finite JSON value: " + value)


def _read_profile_file(path):
    with open(path, "r", encoding="utf-8") as profile_file:
        data = json.load(profile_file, parse_constant=_reject_json_constant)
    return migrate_profile(data)


def load_profile(path, logger=None, backup_path=None):
    """Load primary, then .bak on corruption, then a fresh default profile."""

    path = os.fspath(path)
    backup_path = os.fspath(backup_path) if backup_path else path + ".bak"
    logger = logger if logger is not None else (lambda _message: None)

    try:
        return _read_profile_file(path)
    except FutureProfileVersionError:
        raise
    except FileNotFoundError:
        logger("Survivor profile is missing; checking backup")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ProfileError) as error:
        logger("Survivor profile is invalid; checking backup: " + str(error))

    try:
        profile = _read_profile_file(backup_path)
        logger("Recovered Survivor profile from backup")
        return profile
    except FutureProfileVersionError:
        raise
    except FileNotFoundError:
        logger("Survivor profile backup is missing; creating a default profile")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ProfileError) as error:
        logger("Survivor profile backup is invalid; creating a default profile: " + str(error))
    return default_profile()


def _atomic_write(path, payload):
    global _TEMP_FILE_SERIAL
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor = None
    temp_path = ""
    for _attempt in range(64):
        _TEMP_FILE_SERIAL += 1
        temp_path = (
            path + ".tmp." + str(os.getpid()) + "." + str(_TEMP_FILE_SERIAL)
        )
        try:
            descriptor = os.open(
                temp_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            break
        except FileExistsError:
            continue
    if descriptor is None:
        raise OSError("could not allocate a unique profile temporary file")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _serialized(profile):
    try:
        return json.dumps(
            profile, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError) as error:
        raise ProfileValidationError("profile is not JSON serializable") from error


def save_profile(profile, path, backup_path=None):
    """Atomically save v3 while retaining the previous valid file as .bak."""

    normalized = migrate_profile(profile)
    path = os.fspath(path)
    backup_path = os.fspath(backup_path) if backup_path else path + ".bak"
    new_payload = _serialized(normalized)

    previous_payload = None
    try:
        _read_profile_file(path)
        with open(path, "r", encoding="utf-8") as previous_file:
            previous_payload = previous_file.read()
    except FutureProfileVersionError:
        raise
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError, ValueError, ProfileError):
        previous_payload = None

    if previous_payload is not None:
        _atomic_write(backup_path, previous_payload)
    else:
        try:
            _read_profile_file(backup_path)
        except FutureProfileVersionError:
            raise
        except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError, ValueError, ProfileError):
            _atomic_write(backup_path, new_payload)
    _atomic_write(path, new_payload)
    return normalized
