"""Pure, deterministic rules shared by Survivor runtime and exact tests.

This module deliberately has no ``HEngine`` dependency.  Keeping high-value
state transitions here lets the headless test runner validate the same rules
used by gameplay without constructing a window or scene.
"""

import math

PLAYER_HURT_IFRAME = 0.45
REGULAR_ATTACK_WINDUP = 0.35
BOSS_ATTACK_WINDUP = 0.85
MAX_DAMAGE_REDUCTION = 0.55
MAX_EVASION = 0.35

MAX_CHALLENGE_COUNT_MULTIPLIER = 3.0
MAX_CHALLENGE_HEALTH_MULTIPLIER = 4.0
MAX_CHALLENGE_DAMAGE_MULTIPLIER = 3.0
MAX_CHALLENGE_SPEED_MULTIPLIER = 2.0
MAX_CHALLENGE_SCALE_MULTIPLIER = 2.0
MAX_CHALLENGE_CLOCK_MULTIPLIER = 2.0
MAX_CHALLENGE_XP_MULTIPLIER = 3.0
MAX_CHALLENGE_GOLD_MULTIPLIER = 4.0

_CHARACTER_MODIFIER_KEYS = frozenset({
    "max_health_add",
    "crit_chance_add",
    "move_speed_mul",
    "magnet_range_mul",
    "weapon_damage_mul",
    "weapon_cooldown_mul",
    "weapon_reach_mul",
    "projectile_add",
    "projectile_speed_mul",
    "armor_add",
    "thorns_add",
    "evasion_add",
    "luck_add",
    "xp_gain_mul",
    "gold_gain_mul",
    "difficulty_mul",
})


def normalize_challenge_ids(value, valid_ids=None):
    """Return unique challenge ids in stable catalog order.

    A scalar is accepted for v2 profile compatibility.  ``"none"`` means an
    empty selection.  When ``valid_ids`` is omitted, input order is retained;
    this is useful for immutable run transaction snapshots that should not
    import the gameplay catalog.
    """

    if value is None or value == "none":
        items = ()
    elif isinstance(value, str):
        items = (value,)
    elif isinstance(value, (list, tuple)):
        items = tuple(value)
    else:
        raise ValueError("selected challenges must be a string or array")

    selected = set()
    ordered_input = []
    for challenge_id in items:
        if not isinstance(challenge_id, str) or not challenge_id:
            raise ValueError("selected challenge ids must be non-empty strings")
        if challenge_id == "none" or challenge_id in selected:
            continue
        selected.add(challenge_id)
        ordered_input.append(challenge_id)

    if valid_ids is None:
        return tuple(ordered_input)

    catalog_order = tuple(valid_ids)
    return tuple(
        challenge_id for challenge_id in catalog_order
        if challenge_id in selected
    )


def selected_challenge_ids(profile, valid_ids=None):
    """Read the authoritative list with a legacy scalar fallback."""

    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    if "selectedChallenges" in profile:
        source = profile.get("selectedChallenges")
    else:
        source = profile.get("selectedChallenge", "none")
    return normalize_challenge_ids(source, valid_ids)


def toggle_challenge_id(selected_ids, challenge_id, valid_ids):
    """Add or remove one challenge and return a canonical immutable list."""

    catalog_order = tuple(valid_ids)
    if challenge_id not in catalog_order:
        raise ValueError("unknown challenge id: " + str(challenge_id))
    selected = set(normalize_challenge_ids(selected_ids, catalog_order))
    if challenge_id in selected:
        selected.remove(challenge_id)
    else:
        selected.add(challenge_id)
    return tuple(item for item in catalog_order if item in selected)


def _finite_multiplier(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(field_name + " must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(field_name + " must be finite and non-negative")
    return result


def combine_challenge_modifiers(challenges, minute=0):
    """Fold independent challenge definitions into bounded runtime tuning."""

    minute = max(0, min(15, int(minute)))
    count = 1.0
    health = 1.0
    damage = 1.0
    speed = 1.0
    scale = 1.0
    clock = 1.0
    xp = 1.0
    gold = 1.0
    player_max_health = None
    disable_trinkets = False
    selected_ids = []

    for challenge in challenges:
        if not isinstance(challenge, dict):
            raise ValueError("challenge definitions must be objects")
        challenge_id = challenge.get("id", "")
        if challenge_id:
            selected_ids.append(str(challenge_id))
        count *= _finite_multiplier(
            challenge.get("enemyCount", 1.0), "challenge.enemyCount",
        )
        count *= 1.0 + _finite_multiplier(
            challenge.get("spawnPerMinute", 0.0),
            "challenge.spawnPerMinute",
        ) * minute
        health *= _finite_multiplier(
            challenge.get("enemyHealth", 1.0), "challenge.enemyHealth",
        )
        health *= 1.0 + _finite_multiplier(
            challenge.get("healthPerMinute", 0.0),
            "challenge.healthPerMinute",
        ) * minute
        damage *= _finite_multiplier(
            challenge.get("enemyDamage", 1.0), "challenge.enemyDamage",
        )
        damage *= 1.0 + _finite_multiplier(
            challenge.get("damagePerMinute", 0.0),
            "challenge.damagePerMinute",
        ) * minute
        speed *= _finite_multiplier(
            challenge.get("enemySpeed", 1.0), "challenge.enemySpeed",
        )
        scale *= _finite_multiplier(
            challenge.get("enemyScale", 1.0), "challenge.enemyScale",
        )
        clock *= _finite_multiplier(
            challenge.get("clock", 1.0), "challenge.clock",
        )
        xp *= _finite_multiplier(challenge.get("xp", 1.0), "challenge.xp")
        gold *= _finite_multiplier(
            challenge.get("gold", 1.0), "challenge.gold",
        )
        if "playerMaxHealth" in challenge:
            candidate = _finite_multiplier(
                challenge["playerMaxHealth"], "challenge.playerMaxHealth",
            )
            player_max_health = (
                candidate if player_max_health is None
                else min(player_max_health, candidate)
            )
        disable_trinkets = disable_trinkets or bool(
            challenge.get("disableTrinkets", False)
        )

    return {
        "ids": tuple(selected_ids),
        "enemyCount": min(MAX_CHALLENGE_COUNT_MULTIPLIER, count),
        "enemyHealth": min(MAX_CHALLENGE_HEALTH_MULTIPLIER, health),
        "enemyDamage": min(MAX_CHALLENGE_DAMAGE_MULTIPLIER, damage),
        "enemySpeed": min(MAX_CHALLENGE_SPEED_MULTIPLIER, speed),
        "enemyScale": min(MAX_CHALLENGE_SCALE_MULTIPLIER, scale),
        "clock": min(MAX_CHALLENGE_CLOCK_MULTIPLIER, clock),
        "xp": min(MAX_CHALLENGE_XP_MULTIPLIER, xp),
        "gold": min(MAX_CHALLENGE_GOLD_MULTIPLIER, gold),
        "playerMaxHealth": player_max_health,
        "disableTrinkets": disable_trinkets,
    }


def due_weapon_ids(weapon_order, levels, timers):
    """Return only owned weapons whose cooldown has elapsed.

    ``levels`` and ``timers`` are mappings so tests can cover every catalog
    entry without a gameplay object.  Missing entries are treated as locked and
    therefore can never cast.
    """

    return tuple(
        weapon_id
        for weapon_id in weapon_order
        if int(levels.get(weapon_id, 0)) > 0
        and float(timers.get(weapon_id, 0.0)) <= 0.0
    )


def compile_character_start_state(character_id, definition, training_level=0):
    """Compile one confirmed character into a stable new-run snapshot."""

    modifiers = dict(definition.get("modifiers", {}))
    unknown = set(modifiers) - _CHARACTER_MODIFIER_KEYS
    if unknown:
        raise ValueError(
            "Unknown character modifier(s) for "
            + character_id
            + ": "
            + ", ".join(sorted(unknown))
        )
    if not 0 <= int(training_level) <= 5:
        raise ValueError("Character training level must be between 0 and 5")

    max_health = 100.0 + float(modifiers.get("max_health_add", 0.0))
    training_multiplier = 1.0 + int(training_level) * 0.02
    return {
        "character_id": character_id,
        "starter_weapon": definition["weapon"],
        "max_health": max_health,
        "crit_chance": 0.08 + float(modifiers.get("crit_chance_add", 0.0)),
        "move_speed": 4.25 * float(modifiers.get("move_speed_mul", 1.0)),
        "magnet_range": 4.2 * float(modifiers.get("magnet_range_mul", 1.0)),
        "weapon_damage_multiplier": (
            float(modifiers.get("weapon_damage_mul", 1.0))
            * training_multiplier
        ),
        "weapon_cooldown_multiplier": float(
            modifiers.get("weapon_cooldown_mul", 1.0)
        ),
        "weapon_reach_multiplier": float(
            modifiers.get("weapon_reach_mul", 1.0)
        ),
        "projectile_bonus": int(modifiers.get("projectile_add", 0)),
        "projectile_speed_multiplier": float(
            modifiers.get("projectile_speed_mul", 1.0)
        ),
        "armor": float(modifiers.get("armor_add", 0.0)),
        "thorns": float(modifiers.get("thorns_add", 0.0)),
        "evasion": min(MAX_EVASION, float(modifiers.get("evasion_add", 0.0))),
        "luck": float(modifiers.get("luck_add", 0.0)),
        "xp_gain_multiplier": float(modifiers.get("xp_gain_mul", 1.0)),
        "gold_gain_multiplier": float(modifiers.get("gold_gain_mul", 1.0)),
        "difficulty_multiplier": float(modifiers.get("difficulty_mul", 1.0)),
        "hooks": tuple(definition.get("hooks", ())),
    }


class DefenseResult:
    __slots__ = (
        "damage",
        "evaded",
        "armor_prevented",
        "reduction_prevented",
        "shield_absorbed",
        "shield_remaining",
    )

    def __init__(
            self,
            damage,
            evaded,
            armor_prevented,
            reduction_prevented,
            shield_absorbed,
            shield_remaining):
        self.damage = damage
        self.evaded = evaded
        self.armor_prevented = armor_prevented
        self.reduction_prevented = reduction_prevented
        self.shield_absorbed = shield_absorbed
        self.shield_remaining = shield_remaining


def resolve_defense(raw_damage, evasion_roll, evasion, armor, reduction, shield):
    """Resolve one legal hit in the documented, telemetry-friendly order."""

    raw_damage = max(0.0, float(raw_damage))
    evasion = min(MAX_EVASION, max(0.0, float(evasion)))
    if raw_damage <= 0.0 or float(evasion_roll) < evasion:
        return DefenseResult(0.0, raw_damage > 0.0, 0.0, 0.0, 0.0, max(0.0, shield))

    after_armor = max(1.0, raw_damage - max(0.0, float(armor)))
    armor_prevented = max(0.0, raw_damage - after_armor)
    reduction = min(MAX_DAMAGE_REDUCTION, max(0.0, float(reduction)))
    after_reduction = after_armor * (1.0 - reduction)
    reduction_prevented = after_armor - after_reduction
    shield = max(0.0, float(shield))
    shield_absorbed = min(shield, after_reduction)
    return DefenseResult(
        after_reduction - shield_absorbed,
        False,
        armor_prevented,
        reduction_prevented,
        shield_absorbed,
        shield - shield_absorbed,
    )


class ProjectileBudget:
    """Observable gameplay/visual capacity with bounded retry accounting."""

    def __init__(self, gameplay_limit, visual_limit):
        if int(gameplay_limit) <= 0 or int(visual_limit) < 0:
            raise ValueError("Projectile limits must be non-negative and gameplay > 0")
        self.gameplay_limit = int(gameplay_limit)
        self.visual_limit = int(visual_limit)
        self.gameplay_active = 0
        self.visual_active = 0
        self.retry_count = 0
        self.visual_degrade_count = 0
        self.rejected_count = 0
        self.generation = 1

    def reserve(self, bCritical=True):
        if self.gameplay_active >= self.gameplay_limit:
            if bCritical:
                self.retry_count += 1
                return "retry"
            self.rejected_count += 1
            return "reject"
        self.gameplay_active += 1
        if self.visual_active < self.visual_limit:
            self.visual_active += 1
            return "full"
        self.visual_degrade_count += 1
        return "core_fallback"

    def release(self, bHadVisual=True):
        self.gameplay_active = max(0, self.gameplay_active - 1)
        if bHadVisual:
            self.visual_active = max(0, self.visual_active - 1)

    def reset(self):
        self.gameplay_active = 0
        self.visual_active = 0
        self.retry_count = 0
        self.visual_degrade_count = 0
        self.rejected_count = 0
        self.generation += 1
