"""Pure, authoritative meta-progression rules for Starbloom Survivor."""


BASE_WEAPON_SLOTS = 3
MAX_WEAPON_SLOTS = 6
WEAPON_SLOT_POWER_UP_ID = "meta_weapon_slots"
WEAPON_SLOT_REWARD_FACTORS = {
    3: 1.20,
    4: 1.10,
    5: 1.05,
    6: 1.00,
}


def _power_up(
        power_up_id,
        prices,
        per_level,
        level_prerequisites=(),
        unlock_id="",
        toggleable=True):
    prices = tuple(int(price) for price in prices)
    prerequisites = tuple(str(value) for value in level_prerequisites)
    if prerequisites and len(prerequisites) != len(prices):
        raise ValueError(power_up_id + " must define one prerequisite per level")
    return {
        "id": power_up_id,
        "maxLevel": len(prices),
        "perLevel": per_level,
        "prices": prices,
        "levelPrerequisites": prerequisites,
        "unlockId": unlock_id,
        "toggleable": bool(toggleable),
    }


META_POWER_UP_RULES = (
    _power_up("meta_might", (100, 180, 300, 460, 650), 0.03),
    _power_up("meta_health", (80, 140, 230, 360, 520), 0.05),
    _power_up("meta_recovery", (90, 160, 260, 400, 580), 0.05),
    _power_up("meta_move", (120, 260, 480), 0.03),
    _power_up("meta_magnet", (80, 160, 280, 440), 0.125),
    _power_up("meta_growth", (120, 220, 350, 520, 720), 0.03),
    _power_up("meta_luck", (120, 230, 380, 570, 800), 0.02),
    _power_up("meta_greed", (100, 180, 280, 410, 570, 760, 980), 0.05),
    _power_up("meta_reroll", (250, 550, 900), 1),
    _power_up("meta_skip", (300, 700), 1),
    _power_up("meta_banish", (400, 800, 1300), 1),
    _power_up(
        "meta_revive",
        (2500,),
        1,
        ("adventure",),
        unlock_id="quest_clear_adventure",
    ),
    _power_up(
        WEAPON_SLOT_POWER_UP_ID,
        (600, 1500, 3200),
        1,
        ("adventure", "fierce", "nightmare"),
        toggleable=False,
    ),
)

META_POWER_UP_BY_ID = {
    definition["id"]: definition
    for definition in META_POWER_UP_RULES
}


def _bounded_power_up_level(profile, power_up_id):
    definition = META_POWER_UP_BY_ID[power_up_id]
    value = profile.get("powerUps", {}).get(power_up_id, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return min(definition["maxLevel"], max(0, value))


def purchased_weapon_slot_limit(profile):
    """Return the permanent weapon-slot capability, clamped to 3..6."""

    return min(
        MAX_WEAPON_SLOTS,
        BASE_WEAPON_SLOTS + _bounded_power_up_level(
            profile,
            WEAPON_SLOT_POWER_UP_ID,
        ),
    )


def selected_weapon_slot_limit(profile):
    """Return the planned next-run limit without mutating the profile."""

    purchased_limit = purchased_weapon_slot_limit(profile)
    value = profile.get("selectedWeaponSlotLimit", BASE_WEAPON_SLOTS)
    if isinstance(value, bool) or not isinstance(value, int):
        value = BASE_WEAPON_SLOTS
    return min(purchased_limit, max(BASE_WEAPON_SLOTS, value))


def weapon_slot_reward_factor(weapon_slot_limit):
    if isinstance(weapon_slot_limit, bool) or not isinstance(weapon_slot_limit, int):
        raise ValueError("weaponSlotLimit must be an integer")
    try:
        return WEAPON_SLOT_REWARD_FACTORS[weapon_slot_limit]
    except KeyError as error:
        raise ValueError("weaponSlotLimit must be between 3 and 6") from error


def power_up_level_prerequisite(power_up_id, target_level):
    """Return the difficulty clear required for a one-based target level."""

    definition = META_POWER_UP_BY_ID.get(power_up_id)
    if definition is None:
        raise ValueError("unknown PowerUp: " + str(power_up_id))
    if isinstance(target_level, bool) or not isinstance(target_level, int):
        raise ValueError("targetLevel must be an integer")
    if target_level < 1 or target_level > definition["maxLevel"]:
        raise ValueError("targetLevel is outside the PowerUp range")
    prerequisites = definition["levelPrerequisites"]
    return prerequisites[target_level - 1] if prerequisites else ""


def power_up_prerequisite_met(profile, power_up_id, target_level):
    prerequisite = power_up_level_prerequisite(power_up_id, target_level)
    return (
        not prerequisite
        or bool(profile.get("difficultyClears", {}).get(prerequisite, False))
    )
