"""Pure economy and transaction rules for Starbloom Survivor.

This module deliberately has no HEngine dependency so the rules can be tested
without starting the game.  Callers own persistence; every mutating operation
returns a small receipt that is safe to feed to the UI.
"""

import math
import os

import SurvivorMetaProgression
import SurvivorRules


MAX_WALLET_GOLD = 2_000_000_000
MAX_RUN_COUNTER = 9_000_000_000
MAX_RUN_SECONDS = 86_400.0
MAX_REWARD_COMPONENT = 2_000_000_000
MAX_ECONOMY_FACTOR = 3.0
MAX_DIFFICULTY_FACTOR = 4.0
MAX_CHALLENGE_FACTOR = 4.0

CONTENT_CATEGORIES = {
    "character": "characters",
    "characters": "characters",
    "weapon": "weapons",
    "weapons": "weapons",
    "tome": "tomes",
    "tomes": "tomes",
    "trinket": "trinkets",
    "trinkets": "trinkets",
}

POWER_UP_DEFS = SurvivorMetaProgression.META_POWER_UP_BY_ID


class EconomyValidationError(ValueError):
    """Raised when a transaction receives malformed external input."""


class RunTransactionError(RuntimeError):
    """Raised when a run commit does not match the active run transaction."""


def _clamped_int(value, field_name, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise EconomyValidationError(field_name + " must be an integer")
    return min(maximum, max(0, value))


def _strict_nonnegative_int(value, field_name, maximum=MAX_WALLET_GOLD):
    if isinstance(value, bool) or not isinstance(value, int):
        raise EconomyValidationError(field_name + " must be an integer")
    if value < 0 or value > maximum:
        raise EconomyValidationError(field_name + " is outside the supported range")
    return value


def _clamped_number(value, field_name, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EconomyValidationError(field_name + " must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EconomyValidationError(field_name + " must be finite")
    return min(maximum, max(0.0, result))


def _wallet(profile):
    wallet = _clamped_int(profile.get("walletGold", 0), "walletGold", MAX_WALLET_GOLD)
    profile["walletGold"] = wallet
    return wallet


def _receipt(status, wallet_before, wallet_after, **values):
    result = {
        "status": status,
        "walletBefore": wallet_before,
        "walletAfter": wallet_after,
    }
    result.update(values)
    return result


def combine_challenge_rewards(challenge_rewards):
    """Multiply independent Challenge rewards with a hard economy cap."""

    if challenge_rewards is None:
        return 1.0
    if isinstance(challenge_rewards, (str, bytes)):
        raise EconomyValidationError("challengeRewards must be an array")
    try:
        rewards = tuple(challenge_rewards)
    except TypeError as error:
        raise EconomyValidationError("challengeRewards must be an array") from error
    result = 1.0
    for index, reward in enumerate(rewards):
        result *= _clamped_number(
            reward,
            "challengeRewards[" + str(index) + "]",
            MAX_CHALLENGE_FACTOR,
        )
        if result >= MAX_CHALLENGE_FACTOR:
            return MAX_CHALLENGE_FACTOR
    return min(MAX_CHALLENGE_FACTOR, result)


def compute_run_reward(
        survival_seconds,
        kills,
        elite_kills,
        boss_kills,
        level,
        victory=False,
        revives_used=0,
        quest_gold=0,
        bonus_gold=0,
        greed_tome_bonus=0.0,
        honeybun_bonus=0.0,
        global_greed_bonus=0.0,
        difficulty_reward=1.0,
        challenge_reward=1.0,
        end_reason="death",
        challenge_rewards=None,
        weapon_slot_limit=6):
    """Return the deterministic integer reward breakdown for one run.

    Abandon/restart/home exits receive half of the multiplied base reward.  An
    abandon before 60 seconds additionally suppresses time and kill gold.  Quest
    gold remains outside all economy and abandon multipliers.
    """

    survival_seconds = _clamped_number(
        survival_seconds, "survivalSeconds", MAX_RUN_SECONDS,
    )
    kills = _clamped_int(kills, "kills", MAX_RUN_COUNTER)
    elite_kills = _clamped_int(elite_kills, "eliteKills", MAX_RUN_COUNTER)
    boss_kills = _clamped_int(boss_kills, "bossKills", MAX_RUN_COUNTER)
    level = _clamped_int(level, "level", MAX_RUN_COUNTER)
    revives_used = _clamped_int(revives_used, "revivesUsed", MAX_RUN_COUNTER)
    quest_gold = _clamped_int(quest_gold, "questGold", MAX_REWARD_COMPONENT)
    bonus_gold = _clamped_int(bonus_gold, "bonusGold", MAX_REWARD_COMPONENT)
    if not isinstance(victory, bool):
        raise EconomyValidationError("victory must be a bool")
    if not isinstance(end_reason, str) or not end_reason:
        raise EconomyValidationError("endReason must be a non-empty string")
    try:
        weapon_slot_factor = SurvivorMetaProgression.weapon_slot_reward_factor(
            weapon_slot_limit,
        )
    except ValueError as error:
        raise EconomyValidationError(str(error)) from error

    b_abandon = end_reason in ("abandon", "restart", "return_hub")
    b_victory = victory and not b_abandon

    time_gold = min(60, int(math.floor(survival_seconds / 15.0)))
    kill_gold = min(75, kills // 40)
    if b_abandon and survival_seconds < 60.0:
        time_gold = 0
        kill_gold = 0
    elite_gold = min(MAX_REWARD_COMPONENT, elite_kills * 4)
    boss_gold = min(MAX_REWARD_COMPONENT, boss_kills * 15)
    level_gold = min(40, level)
    clear_gold = 80 if b_victory else 0
    no_revive_gold = 20 if b_victory and revives_used == 0 else 0

    sub_total = min(
        MAX_REWARD_COMPONENT,
        time_gold + kill_gold + elite_gold + boss_gold
        + level_gold + clear_gold + no_revive_gold,
    )
    bonuses = (
        _clamped_number(greed_tome_bonus, "greedTomeBonus", 1.0)
        + _clamped_number(honeybun_bonus, "honeybunBonus", 1.0)
        + _clamped_number(global_greed_bonus, "globalGreedBonus", 1.0)
    )
    economy_factor = min(MAX_ECONOMY_FACTOR, 1.0 + bonuses)
    challenge_factor = (
        combine_challenge_rewards(challenge_rewards)
        if challenge_rewards is not None else
        _clamped_number(
            challenge_reward, "challengeReward", MAX_CHALLENGE_FACTOR,
        )
    )
    difficulty_factor = min(
        MAX_DIFFICULTY_FACTOR,
        _clamped_number(difficulty_reward, "difficultyReward", 4.0)
        * challenge_factor,
    )
    abandon_factor = 0.5 if b_abandon else 1.0
    multiplied_gold_without_slot_bonus = min(
        MAX_REWARD_COMPONENT,
        int(math.floor(sub_total * economy_factor * difficulty_factor)),
    )
    multiplied_gold = min(
        MAX_REWARD_COMPONENT,
        int(math.floor(
            sub_total * economy_factor * difficulty_factor * weapon_slot_factor
        )),
    )
    settled_base_gold = int(math.floor(multiplied_gold * abandon_factor))
    settled_without_slot_bonus = int(math.floor(
        multiplied_gold_without_slot_bonus * abandon_factor
    ))
    settled_bonus_gold = min(
        MAX_REWARD_COMPONENT,
        int(math.floor(bonus_gold * weapon_slot_factor)),
    )
    settled_nonquest_gold = min(
        MAX_REWARD_COMPONENT,
        settled_base_gold + settled_bonus_gold,
    )
    settled_nonquest_without_slot_bonus = min(
        MAX_REWARD_COMPONENT,
        settled_without_slot_bonus + bonus_gold,
    )
    weapon_slot_bonus_gold = max(
        0,
        settled_nonquest_gold - settled_nonquest_without_slot_bonus,
    )
    earned_gold = min(
        MAX_REWARD_COMPONENT,
        settled_nonquest_gold + quest_gold,
    )

    return {
        "timeGold": int(time_gold),
        "killGold": int(kill_gold),
        "eliteGold": int(elite_gold),
        "bossGold": int(boss_gold),
        "levelGold": int(level_gold),
        "clearGold": int(clear_gold),
        "noReviveGold": int(no_revive_gold),
        "subTotal": int(sub_total),
        "economyFactor": economy_factor,
        "challengeFactor": challenge_factor,
        "difficultyFactor": difficulty_factor,
        "weaponSlotFactor": weapon_slot_factor,
        "weaponSlotBonusGold": int(weapon_slot_bonus_gold),
        "abandonFactor": abandon_factor,
        "questGold": int(quest_gold),
        "bonusGold": int(bonus_gold),
        "earnedGold": int(earned_gold),
    }


def new_run_id():
    return os.urandom(16).hex()


def begin_run(
        profile,
        run_id=None,
        character_id=None,
        difficulty_id=None,
        challenge_id=None,
        challenge_ids=None,
        weapon_slot_limit=None):
    """Open one run transaction without replacing an uncommitted run."""

    if run_id is None:
        run_id = new_run_id()
    if not isinstance(run_id, str) or not run_id or len(run_id) > 128:
        raise EconomyValidationError("runId must be a non-empty string up to 128 characters")

    previous = profile.get("lastRun")
    if isinstance(previous, dict) and not previous.get("rewardCommitted", False):
        if previous.get("runId") == run_id:
            return previous
        raise RunTransactionError("cannot replace an uncommitted run")

    if challenge_ids is not None:
        challenge_source = challenge_ids
    elif challenge_id is not None:
        challenge_source = challenge_id
    elif "selectedChallenges" in profile:
        challenge_source = profile.get("selectedChallenges")
    else:
        challenge_source = profile.get("selectedChallenge", "none")
    try:
        normalized_challenges = SurvivorRules.normalize_challenge_ids(
            challenge_source,
        )
    except ValueError as error:
        raise EconomyValidationError(str(error)) from error

    if weapon_slot_limit is None:
        weapon_slot_limit = SurvivorMetaProgression.selected_weapon_slot_limit(
            profile,
        )
    try:
        SurvivorMetaProgression.weapon_slot_reward_factor(weapon_slot_limit)
    except ValueError as error:
        raise EconomyValidationError(str(error)) from error

    record = {
        "runId": run_id,
        "rewardCommitted": False,
        "characterId": character_id or profile.get("selectedCharacter", "starpaw"),
        "difficultyId": difficulty_id or profile.get("selectedDifficulty", "adventure"),
        "challengeIds": list(normalized_challenges),
        "challengeId": (
            normalized_challenges[0] if normalized_challenges else "none"
        ),
        "weaponSlotLimit": weapon_slot_limit,
    }
    profile["lastRun"] = record
    return record


def commit_run_reward(profile, run_id, reward_breakdown, end_reason):
    """Credit an active run exactly once and persist its transaction receipt."""

    if not isinstance(run_id, str) or not run_id:
        raise EconomyValidationError("runId must be a non-empty string")
    active_run = profile.get("lastRun")
    if not isinstance(active_run, dict) or active_run.get("runId") != run_id:
        raise RunTransactionError("runId does not match the active run")
    if active_run.get("rewardCommitted", False):
        wallet = _wallet(profile)
        return _receipt(
            "already_committed",
            wallet,
            wallet,
            runId=run_id,
            creditedGold=0,
        )
    if not isinstance(reward_breakdown, dict):
        raise EconomyValidationError("rewardBreakdown must be an object")
    earned_gold = _strict_nonnegative_int(
        reward_breakdown.get("earnedGold"), "earnedGold", MAX_REWARD_COMPONENT,
    )
    if not isinstance(end_reason, str) or not end_reason:
        raise EconomyValidationError("endReason must be a non-empty string")

    wallet_before = _wallet(profile)
    wallet_after = min(MAX_WALLET_GOLD, wallet_before + earned_gold)
    credited_gold = wallet_after - wallet_before
    profile["walletGold"] = wallet_after

    career = profile.setdefault("career", {})
    career["runs"] = min(
        MAX_RUN_COUNTER,
        _clamped_int(career.get("runs", 0), "career.runs", MAX_RUN_COUNTER) + 1,
    )
    if end_reason == "victory":
        career["wins"] = min(
            MAX_RUN_COUNTER,
            _clamped_int(career.get("wins", 0), "career.wins", MAX_RUN_COUNTER) + 1,
        )
    career["totalGoldEarned"] = min(
        MAX_RUN_COUNTER,
        _clamped_int(
            career.get("totalGoldEarned", 0),
            "career.totalGoldEarned",
            MAX_RUN_COUNTER,
        ) + earned_gold,
    )

    active_run["endReason"] = end_reason
    active_run["reward"] = dict(reward_breakdown)
    active_run["rewardCommitted"] = True
    active_run["walletBefore"] = wallet_before
    active_run["walletAfter"] = wallet_after
    active_run["creditedGold"] = credited_gold
    return _receipt(
        "committed",
        wallet_before,
        wallet_after,
        runId=run_id,
        creditedGold=credited_gold,
    )


def purchase_content(profile, category, content_id, price):
    """Purchase one eligible catalog item; already-owned calls are idempotent."""

    category_key = CONTENT_CATEGORIES.get(category)
    if category_key is None:
        raise EconomyValidationError("unknown content category: " + str(category))
    if not isinstance(content_id, str) or not content_id:
        raise EconomyValidationError("contentId must be a non-empty string")
    price = _strict_nonnegative_int(price, "price")
    wallet_before = _wallet(profile)

    owned = profile.setdefault("owned", {}).setdefault(category_key, [])
    eligible = profile.setdefault("eligible", {}).setdefault(category_key, [])
    if content_id in owned:
        return _receipt(
            "already_owned", wallet_before, wallet_before,
            contentId=content_id, category=category_key, spentGold=0,
        )
    if content_id not in eligible:
        return _receipt(
            "not_eligible", wallet_before, wallet_before,
            contentId=content_id, category=category_key, spentGold=0,
        )
    if wallet_before < price:
        return _receipt(
            "insufficient_gold", wallet_before, wallet_before,
            contentId=content_id, category=category_key, spentGold=0,
        )

    profile["walletGold"] = wallet_before - price
    owned.append(content_id)
    eligible.remove(content_id)
    disabled = profile.setdefault("poolDisabled", {}).setdefault(category_key, [])
    if content_id in disabled:
        disabled.remove(content_id)
    return _receipt(
        "purchased", wallet_before, profile["walletGold"],
        contentId=content_id, category=category_key, spentGold=price,
    )


def content_state(profile, category, content_id):
    """Return owned, eligible, or locked for a catalog item."""

    category_key = CONTENT_CATEGORIES.get(category)
    if category_key is None:
        raise EconomyValidationError("unknown content category: " + str(category))
    if not isinstance(content_id, str) or not content_id:
        raise EconomyValidationError("contentId must be a non-empty string")
    owned = profile.setdefault("owned", {}).setdefault(category_key, [])
    if content_id in owned:
        return "owned"
    eligible = profile.setdefault("eligible", {}).setdefault(category_key, [])
    if content_id in eligible:
        return "eligible"
    return "locked"


def grant_content_eligibility(profile, category, content_id):
    """Move a locked item to eligible without granting ownership."""

    category_key = CONTENT_CATEGORIES.get(category)
    if category_key is None:
        raise EconomyValidationError("unknown content category: " + str(category))
    if not isinstance(content_id, str) or not content_id:
        raise EconomyValidationError("contentId must be a non-empty string")
    if content_state(profile, category_key, content_id) != "locked":
        return False
    profile["eligible"][category_key].append(content_id)
    return True


def _power_up_level(profile, power_up_id):
    definition = POWER_UP_DEFS.get(power_up_id)
    if definition is None:
        raise EconomyValidationError("unknown PowerUp: " + str(power_up_id))
    level = _clamped_int(
        profile.setdefault("powerUps", {}).get(power_up_id, 0),
        "powerUps." + power_up_id,
        len(definition["prices"]),
    )
    profile["powerUps"][power_up_id] = level
    return definition, level


def purchase_power_up(profile, power_up_id, expected_level):
    """Buy one PowerUp level using an optimistic level as the UI idempotency key."""

    definition, level = _power_up_level(profile, power_up_id)
    wallet_before = _wallet(profile)
    expected_level = _strict_nonnegative_int(
        expected_level, "expectedLevel", len(definition["prices"]),
    )
    if expected_level != level:
        return _receipt(
            "stale", wallet_before, wallet_before,
            powerUpId=power_up_id, level=level, spentGold=0,
        )
    if level >= len(definition["prices"]):
        return _receipt(
            "already_maxed", wallet_before, wallet_before,
            powerUpId=power_up_id, level=level, spentGold=0,
        )
    target_level = level + 1
    if not SurvivorMetaProgression.power_up_prerequisite_met(
            profile, power_up_id, target_level):
        prerequisite = SurvivorMetaProgression.power_up_level_prerequisite(
            power_up_id, target_level,
        )
        return _receipt(
            "locked", wallet_before, wallet_before,
            powerUpId=power_up_id, level=level, spentGold=0,
            prerequisiteDifficulty=prerequisite,
        )

    price = definition["prices"][level]
    if wallet_before < price:
        return _receipt(
            "insufficient_gold", wallet_before, wallet_before,
            powerUpId=power_up_id, level=level, spentGold=0,
        )
    profile["walletGold"] = wallet_before - price
    profile["powerUps"][power_up_id] = level + 1
    profile.setdefault("powerUpsEnabled", {})[power_up_id] = True
    return _receipt(
        "purchased", wallet_before, profile["walletGold"],
        powerUpId=power_up_id, level=level + 1, spentGold=price,
    )


def set_power_up_enabled(profile, power_up_id, b_enabled):
    definition, level = _power_up_level(profile, power_up_id)
    if not isinstance(b_enabled, bool):
        raise EconomyValidationError("enabled must be a bool")
    if not definition.get("toggleable", True):
        profile.setdefault("powerUpsEnabled", {})[power_up_id] = level > 0
        return level > 0
    profile.setdefault("powerUpsEnabled", {})[power_up_id] = b_enabled and level > 0
    return profile["powerUpsEnabled"][power_up_id]


def refund_power_up(profile, power_up_id, expected_level=None):
    """Refund every purchased level of one PowerUp at its exact paid prices."""

    definition, level = _power_up_level(profile, power_up_id)
    wallet_before = _wallet(profile)
    if expected_level is not None:
        expected_level = _strict_nonnegative_int(
            expected_level, "expectedLevel", len(definition["prices"]),
        )
        if expected_level != level:
            return _receipt(
                "stale", wallet_before, wallet_before,
                powerUpId=power_up_id, level=level, refundedGold=0,
            )
    if level == 0:
        return _receipt(
            "nothing_to_refund", wallet_before, wallet_before,
            powerUpId=power_up_id, level=0, refundedGold=0,
        )

    refund = sum(definition["prices"][:level])
    if wallet_before + refund > MAX_WALLET_GOLD:
        return _receipt(
            "wallet_cap", wallet_before, wallet_before,
            powerUpId=power_up_id, level=level, refundedGold=0,
        )
    profile["walletGold"] = wallet_before + refund
    profile["powerUps"][power_up_id] = 0
    profile.setdefault("powerUpsEnabled", {})[power_up_id] = False
    if power_up_id == SurvivorMetaProgression.WEAPON_SLOT_POWER_UP_ID:
        profile["selectedWeaponSlotLimit"] = (
            SurvivorMetaProgression.selected_weapon_slot_limit(profile)
        )
    return _receipt(
        "refunded", wallet_before, profile["walletGold"],
        powerUpId=power_up_id, level=0, refundedGold=refund,
    )


def refund_all_power_ups(profile):
    """Atomically refund all known PowerUps without touching owned content."""

    wallet_before = _wallet(profile)
    levels = {}
    refund = 0
    for power_up_id, definition in POWER_UP_DEFS.items():
        _, level = _power_up_level(profile, power_up_id)
        levels[power_up_id] = level
        refund += sum(definition["prices"][:level])
    if refund == 0:
        return _receipt(
            "nothing_to_refund", wallet_before, wallet_before, refundedGold=0,
        )
    if wallet_before + refund > MAX_WALLET_GOLD:
        return _receipt(
            "wallet_cap", wallet_before, wallet_before, refundedGold=0,
        )

    profile["walletGold"] = wallet_before + refund
    enabled = profile.setdefault("powerUpsEnabled", {})
    for power_up_id in levels:
        profile["powerUps"][power_up_id] = 0
        enabled[power_up_id] = False
    profile["selectedWeaponSlotLimit"] = (
        SurvivorMetaProgression.selected_weapon_slot_limit(profile)
    )
    return _receipt(
        "refunded", wallet_before, profile["walletGold"], refundedGold=refund,
    )
