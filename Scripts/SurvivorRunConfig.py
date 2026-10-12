"""Immutable per-run configuration for Starbloom Survivor.

The runtime compiles this snapshot once before a run starts.  Gameplay systems
must consume the snapshot instead of re-reading mutable profile selection.
This module is pure Python and supports the project's Python 3.7 runtime.
"""

import math
from collections.abc import Mapping
from types import MappingProxyType

import SurvivorRules

from SurvivorRegionObjectives import objective_config_snapshot


DEFAULT_CHARACTER_ID = "starpaw"
DEFAULT_DIFFICULTY_ID = "adventure"
DEFAULT_RUN_SEED = 7319
RUN_CONFIG_SCHEMA_IDENTITY = "survivor-run-config-v1"


class FrozenMapping(Mapping):
    """A recursively immutable, hashable mapping."""

    __slots__ = ("_items", "_lookup", "_hash", "_locked")

    def __init__(self, values=None):
        items = tuple(
            (key, _freeze(value)) for key, value in dict(values or {}).items()
        )
        object.__setattr__(self, "_items", items)
        object.__setattr__(self, "_lookup", MappingProxyType(dict(items)))
        object.__setattr__(self, "_hash", None)
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name, value):
        if getattr(self, "_locked", False):
            raise AttributeError("FrozenMapping is immutable")
        object.__setattr__(self, name, value)

    def __getitem__(self, key):
        return self._lookup[key]

    def __iter__(self):
        return (key for key, _ in self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return "FrozenMapping({0!r})".format(dict(self._items))

    def __hash__(self):
        cached = self._hash
        if cached is None:
            cached = hash(self._items)
            object.__setattr__(self, "_hash", cached)
        return cached


def _freeze(value):
    if isinstance(value, FrozenMapping):
        return value
    if isinstance(value, Mapping):
        return FrozenMapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_thaw(item) for item in value)
    return value


def _challenge_catalog(challenges):
    if challenges is None:
        from SurvivorCatalogWorld import CHALLENGES
        challenges = CHALLENGES
    result = tuple(challenges)
    ids = [entry.get("id") for entry in result]
    if any(not isinstance(challenge_id, str) or not challenge_id for challenge_id in ids):
        raise ValueError("challenge catalog contains an invalid id")
    if len(ids) != len(set(ids)):
        raise ValueError("challenge catalog contains duplicate ids")
    return result


def _selected_challenges(profile, catalog, challenge_ids):
    valid_ids = tuple(entry["id"] for entry in catalog)
    source = challenge_ids
    if source is None:
        source = (
            profile.get("selectedChallenges")
            if "selectedChallenges" in profile else
            profile.get("selectedChallenge", "none")
        )
    return SurvivorRules.normalize_challenge_ids(source, valid_ids)


def _combined_reward(entries):
    # Keep the module usable in stripped pure-rule fixtures which do not place
    # the full economy module on sys.path.
    try:
        from SurvivorEconomy import combine_challenge_rewards
    except ImportError:
        value = 1.0
        for entry in entries:
            value = min(4.0, value * float(entry.get("gold", 1.0)))
        return value
    return combine_challenge_rewards(
        entry.get("gold", 1.0) for entry in entries
    )


def _slot_limit(profile, requested_limit=None):
    try:
        import SurvivorMetaProgression
    except ImportError:
        SurvivorMetaProgression = None

    if SurvivorMetaProgression is not None:
        purchased = int(
            SurvivorMetaProgression.purchased_weapon_slot_limit(profile)
        )
        selected = int(
            SurvivorMetaProgression.selected_weapon_slot_limit(profile)
        )
        minimum = int(getattr(SurvivorMetaProgression, "BASE_WEAPON_SLOTS", 3))
        maximum = int(getattr(SurvivorMetaProgression, "MAX_WEAPON_SLOTS", 6))
    else:
        minimum = 3
        maximum = 6
        power_ups = profile.get("powerUps", {})
        purchased_levels = power_ups.get("meta_weapon_slots", 0)
        if isinstance(purchased_levels, bool) or not isinstance(purchased_levels, int):
            purchased_levels = 0
        purchased = min(maximum, max(minimum, minimum + purchased_levels))
        selected = profile.get(
            "selectedWeaponSlotLimit",
            profile.get("weaponSlotLimit", purchased),
        )
        if isinstance(selected, bool) or not isinstance(selected, int):
            selected = purchased
        selected = min(purchased, max(minimum, selected))

    if requested_limit is not None:
        if isinstance(requested_limit, bool) or not isinstance(requested_limit, int):
            raise ValueError("weapon_slot_limit must be an integer")
        selected = requested_limit
    return min(maximum, purchased, max(minimum, selected))


def _default_content_identity():
    try:
        from SurvivorCatalog import CATALOG_VERSION
        return "survivor-catalog-v{0}".format(CATALOG_VERSION)
    except (ImportError, AttributeError):
        return "survivor-catalog-unknown"


def _default_profile_schema_identity():
    try:
        from SurvivorProfile import PROFILE_VERSION
        return "survivor-profile-v{0}".format(PROFILE_VERSION)
    except (ImportError, AttributeError):
        return "survivor-profile-unknown"


class RunConfig(object):
    """Deeply immutable run snapshot with snake_case runtime fields."""

    __slots__ = (
        "selected_character",
        "selected_difficulty",
        "challenge_ids",
        "combined_challenge_tuning",
        "combined_challenge_rewards",
        "weapon_slot_limit",
        "objective_config",
        "run_seed",
        "content_identity",
        "schema_identity",
        "_challenge_tuning_by_world_minute",
        "_locked",
    )

    def __init__(
            self,
            selected_character,
            selected_difficulty,
            challenge_ids,
            combined_challenge_tuning,
            combined_challenge_rewards,
            weapon_slot_limit,
            objective_config,
            run_seed,
            content_identity,
            schema_identity,
            challenge_tuning_by_world_minute):
        object.__setattr__(self, "selected_character", str(selected_character))
        object.__setattr__(self, "selected_difficulty", str(selected_difficulty))
        object.__setattr__(self, "challenge_ids", tuple(challenge_ids))
        object.__setattr__(
            self, "combined_challenge_tuning", _freeze(combined_challenge_tuning),
        )
        object.__setattr__(
            self, "combined_challenge_rewards", float(combined_challenge_rewards),
        )
        object.__setattr__(self, "weapon_slot_limit", int(weapon_slot_limit))
        object.__setattr__(self, "objective_config", _freeze(objective_config))
        object.__setattr__(self, "run_seed", int(run_seed) & 0xFFFFFFFF)
        object.__setattr__(self, "content_identity", _freeze(content_identity))
        object.__setattr__(self, "schema_identity", _freeze(schema_identity))
        object.__setattr__(
            self,
            "_challenge_tuning_by_world_minute",
            tuple(_freeze(row) for row in challenge_tuning_by_world_minute),
        )
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name, value):
        if getattr(self, "_locked", False):
            raise AttributeError("RunConfig is immutable")
        object.__setattr__(self, name, value)

    @property
    def character(self):
        return self.selected_character

    @property
    def difficulty(self):
        return self.selected_difficulty

    @property
    def seed(self):
        return self.run_seed

    @property
    def world_clock_multiplier(self):
        return float(self.combined_challenge_tuning.get("clock", 1.0))

    @property
    def objective_clock_multiplier(self):
        # Hurry and every other world-clock modifier are excluded by contract.
        return 1.0

    def challenge_tuning_for_world_minute(self, minute):
        if isinstance(minute, bool) or not isinstance(minute, (int, float)):
            raise ValueError("minute must be numeric")
        value = float(minute)
        if not math.isfinite(value):
            raise ValueError("minute must be finite")
        index = max(0, min(15, int(value)))
        return self._challenge_tuning_by_world_minute[index]

    def world_delta(self, raw_gameplay_delta):
        raw = _validated_delta(raw_gameplay_delta)
        return raw * self.world_clock_multiplier

    def objective_delta(self, raw_gameplay_delta, gameplay_active=True):
        raw = _validated_delta(raw_gameplay_delta)
        return raw if gameplay_active else 0.0

    def as_dict(self):
        """Return a detached camelCase serialization payload."""

        return {
            "selectedCharacter": self.selected_character,
            "selectedDifficulty": self.selected_difficulty,
            "challengeIds": list(self.challenge_ids),
            "combinedChallengeTuning": _thaw(self.combined_challenge_tuning),
            "combinedChallengeRewards": self.combined_challenge_rewards,
            "challengeTuningByWorldMinute": [
                _thaw(row) for row in self._challenge_tuning_by_world_minute
            ],
            "weaponSlotLimit": self.weapon_slot_limit,
            "objectiveConfig": _thaw(self.objective_config),
            "runSeed": self.run_seed,
            "contentIdentity": _thaw(self.content_identity),
            "schemaIdentity": _thaw(self.schema_identity),
        }

    def __repr__(self):
        return (
            "RunConfig(character={0!r}, difficulty={1!r}, challenges={2!r}, "
            "weapon_slot_limit={3}, seed={4})"
        ).format(
            self.selected_character,
            self.selected_difficulty,
            self.challenge_ids,
            self.weapon_slot_limit,
            self.run_seed,
        )


def _validated_delta(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("raw_gameplay_delta must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError("raw_gameplay_delta must be finite and non-negative")
    return result


def compile_run_config(
        profile,
        challenges=None,
        character_id=None,
        difficulty_id=None,
        challenge_ids=None,
        weapon_slot_limit=None,
        run_seed=None,
        objective_config=None,
        content_identity=None,
        schema_identity=None):
    """Compile one deeply immutable snapshot from mutable launch/profile data."""

    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    catalog = _challenge_catalog(challenges)
    selected_ids = _selected_challenges(profile, catalog, challenge_ids)
    selected_set = set(selected_ids)
    selected_entries = tuple(
        entry for entry in catalog if entry["id"] in selected_set
    )
    tuning_by_minute = tuple(
        SurvivorRules.combine_challenge_modifiers(selected_entries, minute)
        for minute in range(16)
    )
    baseline_tuning = dict(tuning_by_minute[0])
    baseline_tuning["worldMinuteTableLength"] = len(tuning_by_minute)

    selected_character = character_id or profile.get(
        "selectedCharacter", DEFAULT_CHARACTER_ID,
    )
    selected_difficulty = difficulty_id or profile.get(
        "selectedDifficulty", DEFAULT_DIFFICULTY_ID,
    )
    if not isinstance(selected_character, str) or not selected_character:
        raise ValueError("selected character must be a non-empty string")
    if not isinstance(selected_difficulty, str) or not selected_difficulty:
        raise ValueError("selected difficulty must be a non-empty string")

    if run_seed is None:
        run_seed = profile.get("runSeed", profile.get("selectedRunSeed", DEFAULT_RUN_SEED))
    if isinstance(run_seed, bool) or not isinstance(run_seed, int):
        raise ValueError("run_seed must be an integer")

    if objective_config is None:
        objective_config = objective_config_snapshot()
    if content_identity is None:
        content_identity = _default_content_identity()
    if schema_identity is None:
        schema_identity = {
            "runConfig": RUN_CONFIG_SCHEMA_IDENTITY,
            "profile": _default_profile_schema_identity(),
        }

    return RunConfig(
        selected_character=selected_character,
        selected_difficulty=selected_difficulty,
        challenge_ids=selected_ids,
        combined_challenge_tuning=baseline_tuning,
        combined_challenge_rewards=_combined_reward(selected_entries),
        weapon_slot_limit=_slot_limit(profile, weapon_slot_limit),
        objective_config=objective_config,
        run_seed=run_seed,
        content_identity=content_identity,
        schema_identity=schema_identity,
        challenge_tuning_by_world_minute=tuning_by_minute,
    )


# Short alias for runtime call sites.
build_run_config = compile_run_config
