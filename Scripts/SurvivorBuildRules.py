"""Deterministic, HEngine-free build and run transaction rules."""

import SurvivorEconomy
import SurvivorProfile


class BuildRuleError(ValueError):
    pass


class DeterministicRng:
    __slots__ = ("state",)

    def __init__(self, seed):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise BuildRuleError("seed must be an integer")
        self.state = seed & 0xFFFFFFFF

    def next_u32(self):
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state

    def unit(self):
        return self.next_u32() / 4294967296.0

    def weighted_index(self, weights):
        total = sum(max(0.0, float(weight)) for weight in weights)
        if total <= 0.0:
            raise BuildRuleError("weighted selection requires a positive weight")
        roll = self.unit() * total
        cumulative = 0.0
        for index, weight in enumerate(weights):
            cumulative += max(0.0, float(weight))
            if roll < cumulative:
                return index
        return len(weights) - 1


def _id_set(values, field_name):
    result = set()
    for value in values or ():
        if not isinstance(value, str) or not value:
            raise BuildRuleError(field_name + " must contain non-empty ids")
        result.add(value)
    return result


def _level_map(values, field_name):
    result = {}
    for content_id, level in dict(values or {}).items():
        if not isinstance(content_id, str) or not content_id:
            raise BuildRuleError(field_name + " has an invalid id")
        if isinstance(level, bool) or not isinstance(level, int) or level < 0:
            raise BuildRuleError(field_name + " has an invalid level")
        result[content_id] = level
    return result


class UpgradePoolController:
    """Weighted upgrade pool with deterministic, injectable random state."""

    FALLBACK_IDS = ("snack", "bonus", "spark")

    def __init__(
            self,
            weapons,
            tomes,
            owned,
            enabled=None,
            weapon_levels=None,
            tome_levels=None,
            weapon_slots=None,
            tome_slots=None,
            max_weapon_slots=6,
            max_tome_slots=6,
            seed=1,
            rerolls=0,
            skips=0,
            banishes=0,
            sealed=None,
            held_weight_multiplier=2.0,
            excluded_ids=None):
        self.catalog = {
            "weapons": tuple(weapons),
            "tomes": tuple(tomes),
        }
        self.owned = {
            category: _id_set(dict(owned or {}).get(category, ()), "owned." + category)
            for category in ("weapons", "tomes")
        }
        enabled = dict(enabled or {})
        self.enabled = {
            category: _id_set(
                enabled.get(category, self.owned[category]),
                "enabled." + category,
            ) & self.owned[category]
            for category in ("weapons", "tomes")
        }
        self.levels = {
            "weapons": _level_map(weapon_levels, "weaponLevels"),
            "tomes": _level_map(tome_levels, "tomeLevels"),
        }
        self.slots = {
            "weapons": list(weapon_slots or ()),
            "tomes": list(tome_slots or ()),
        }
        self.slot_limits = {
            "weapons": int(max_weapon_slots),
            "tomes": int(max_tome_slots),
        }
        if self.slot_limits["weapons"] < 0 or self.slot_limits["tomes"] < 0:
            raise BuildRuleError("slot limits must be non-negative")
        if float(held_weight_multiplier) < 1.0:
            raise BuildRuleError("held weight multiplier must be at least one")
        self.held_weight_multiplier = float(held_weight_multiplier)
        self.rng = DeterministicRng(seed)
        self.rerolls_remaining = max(0, int(rerolls))
        self.skips_remaining = max(0, int(skips))
        self.banishes_remaining = max(0, int(banishes))
        self.banished = set()
        self.sealed = _id_set(sealed, "sealed")
        self.excluded_ids = _id_set(excluded_ids, "excludedIds")
        self.current_choices = ()
        self.roll_serial = 0

        for category in ("weapons", "tomes"):
            ids = [entry.get("id") for entry in self.catalog[category]]
            if any(not isinstance(content_id, str) or not content_id for content_id in ids):
                raise BuildRuleError(category + " catalog has an invalid id")
            if len(ids) != len(set(ids)):
                raise BuildRuleError(category + " catalog contains duplicate ids")

    def _candidate_rows(self):
        rows = []
        for category in ("weapons", "tomes"):
            b_slots_full = len(self.slots[category]) >= self.slot_limits[category]
            for definition in self.catalog[category]:
                content_id = definition["id"]
                if content_id in self.excluded_ids:
                    continue
                if content_id not in self.owned[category]:
                    continue
                if content_id not in self.enabled[category]:
                    continue
                if content_id in self.sealed or content_id in self.banished:
                    continue
                current_level = self.levels[category].get(content_id, 0)
                max_level = int(definition.get("maxLevel", 1))
                if current_level >= max_level:
                    continue
                if current_level <= 0 and b_slots_full:
                    continue
                weight = max(0.0, float(definition.get("rarityWeight", 1.0)))
                if current_level > 0:
                    weight *= self.held_weight_multiplier
                if weight <= 0.0:
                    continue
                rows.append({
                    "id": content_id,
                    "kind": category[:-1],
                    "category": category,
                    "currentLevel": current_level,
                    "nextLevel": current_level + 1,
                    "unlock": current_level <= 0,
                    "weight": weight,
                })
        return rows

    def roll(self, choice_count=3):
        if isinstance(choice_count, bool) or not isinstance(choice_count, int):
            raise BuildRuleError("choice count must be an integer")
        if choice_count <= 0:
            raise BuildRuleError("choice count must be positive")
        available = self._candidate_rows()
        choices = []
        while available and len(choices) < choice_count:
            index = self.rng.weighted_index([row["weight"] for row in available])
            choices.append(available.pop(index))
        if not choices:
            choices = [
                {
                    "id": fallback_id,
                    "kind": "fallback",
                    "category": "fallbacks",
                    "currentLevel": 0,
                    "nextLevel": 0,
                    "unlock": False,
                    "weight": 1.0,
                }
                for fallback_id in self.FALLBACK_IDS[:choice_count]
            ]
        self.current_choices = tuple(choices)
        self.roll_serial += 1
        return self.current_choices

    def candidate_snapshot(self):
        return tuple(dict(row) for row in self._candidate_rows())

    def reroll(self, choice_count=3):
        if self.rerolls_remaining <= 0:
            return {"status": "unavailable", "choices": self.current_choices}
        self.rerolls_remaining -= 1
        return {"status": "rerolled", "choices": self.roll(choice_count)}

    def skip(self):
        if self.skips_remaining <= 0:
            return {"status": "unavailable", "choices": self.current_choices}
        self.skips_remaining -= 1
        self.current_choices = ()
        return {"status": "skipped", "choices": ()}

    def banish(self, content_id, choice_count=3):
        if self.banishes_remaining <= 0:
            return {"status": "unavailable", "choices": self.current_choices}
        if content_id not in {choice["id"] for choice in self.current_choices}:
            return {"status": "not_in_choices", "choices": self.current_choices}
        self.banishes_remaining -= 1
        self.banished.add(content_id)
        return {"status": "banished", "choices": self.roll(choice_count)}

    def seal(self, content_id):
        self.sealed.add(content_id)
        self.current_choices = tuple(
            choice for choice in self.current_choices if choice["id"] != content_id
        )

    def unseal(self, content_id):
        self.sealed.discard(content_id)

    def set_enabled(self, category, content_id, b_enabled):
        if category not in self.enabled:
            raise BuildRuleError("unknown upgrade category: " + str(category))
        if not isinstance(b_enabled, bool):
            raise BuildRuleError("enabled must be a bool")
        if content_id not in self.owned[category]:
            raise BuildRuleError("cannot enable unowned content")
        if b_enabled:
            self.enabled[category].add(content_id)
        else:
            self.enabled[category].discard(content_id)


class EvolutionResolver:
    """Resolve chest evolutions without adding weapon slots."""

    def __init__(
            self,
            recipes,
            weapon_levels,
            tome_levels,
            weapon_slots,
            discovered=None):
        self.recipes = tuple(recipes)
        self.weapon_levels = _level_map(weapon_levels, "weaponLevels")
        self.tome_levels = _level_map(tome_levels, "tomeLevels")
        self.weapon_slots = list(weapon_slots)
        self.discovered = list(dict.fromkeys(discovered or ()))
        self._discovered_set = set(self.discovered)
        self._resolved = {
            recipe["id"]
            for recipe in self.recipes
            if recipe["id"] in self.weapon_slots
            or self.weapon_levels.get(recipe["id"], 0) > 0
        }

    def _eligible(self, recipe, chest_tier):
        evolution_id = recipe["id"]
        weapon_id = recipe["weaponId"]
        tome_id = recipe["tomeId"]
        return (
            evolution_id not in self._resolved
            and weapon_id in self.weapon_slots
            and chest_tier >= int(recipe.get("chestTier", 1))
            and self.weapon_levels.get(weapon_id, 0)
            >= int(recipe.get("requiredWeaponLevel", 10))
            and self.tome_levels.get(tome_id, 0)
            >= int(recipe.get("requiredTomeLevel", 5))
        )

    def resolve_chest(self, chest_tier):
        if isinstance(chest_tier, bool) or not isinstance(chest_tier, int):
            raise BuildRuleError("chest tier must be an integer")
        if chest_tier < 0 or chest_tier > 3:
            raise BuildRuleError("chest tier must be between zero and three")
        limit = 2 if chest_tier == 3 else 1
        resolved = []
        newly_discovered = []
        for recipe in self.recipes:
            if len(resolved) >= limit:
                break
            if not self._eligible(recipe, chest_tier):
                continue
            weapon_id = recipe["weaponId"]
            evolution_id = recipe["id"]
            slot_index = self.weapon_slots.index(weapon_id)
            self.weapon_slots[slot_index] = evolution_id
            self.weapon_levels[weapon_id] = 0
            self.weapon_levels[evolution_id] = 1
            self._resolved.add(evolution_id)
            resolved.append(evolution_id)
            if evolution_id not in self._discovered_set:
                self._discovered_set.add(evolution_id)
                self.discovered.append(evolution_id)
                newly_discovered.append(evolution_id)
        return {
            "status": "evolved" if resolved else "no_evolution",
            "evolutions": tuple(resolved),
            "newlyDiscovered": tuple(newly_discovered),
            "weaponSlots": tuple(self.weapon_slots),
            "weaponLevels": dict(self.weapon_levels),
            "discovered": tuple(self.discovered),
        }


def _clone_value(value):
    if isinstance(value, dict):
        return {key: _clone_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_value(item) for item in value)
    if isinstance(value, set):
        return set(_clone_value(item) for item in value)
    return value


class RunEndTransaction:
    """Single-commit run settlement with persistence rollback and retry."""

    def __init__(
            self,
            profile,
            run_id,
            character_id=None,
            difficulty_id=None,
            challenge_id=None,
            persist=None,
            challenge_ids=None,
            weapon_slot_limit=None):
        if not isinstance(profile, dict):
            raise BuildRuleError("profile must be an object")
        self.profile = profile
        self.run_id = run_id
        self.persist = persist
        previous = profile.get("lastRun")
        if not (
                isinstance(previous, dict)
                and previous.get("runId") == run_id
                and previous.get("rewardCommitted", False)):
            SurvivorEconomy.begin_run(
                profile,
                run_id,
                character_id=character_id,
                difficulty_id=difficulty_id,
                challenge_id=challenge_id,
                challenge_ids=challenge_ids,
                weapon_slot_limit=weapon_slot_limit,
            )

    def settle(self, end_reason, reward_inputs=None, reward_breakdown=None):
        if not isinstance(end_reason, str) or not end_reason:
            raise BuildRuleError("end reason must be a non-empty string")
        if reward_breakdown is None:
            inputs = dict(reward_inputs or {})
            inputs["end_reason"] = end_reason
            inputs["victory"] = end_reason == "victory"
            inputs["weapon_slot_limit"] = self.profile[
                "lastRun"
            ]["weaponSlotLimit"]
            reward_breakdown = SurvivorEconomy.compute_run_reward(**inputs)
        snapshot = _clone_value(self.profile)
        try:
            receipt = SurvivorEconomy.commit_run_reward(
                self.profile,
                self.run_id,
                reward_breakdown,
                end_reason,
            )
            SurvivorProfile.validate_profile(self.profile)
            if receipt["status"] == "committed" and self.persist is not None:
                self.persist(self.profile)
            return {
                "status": receipt["status"],
                "receipt": receipt,
                "reward": dict(reward_breakdown),
            }
        except BaseException:
            self.profile.clear()
            self.profile.update(snapshot)
            raise
