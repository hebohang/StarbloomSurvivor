"""Indexed, frame-aggregated quest progression for Survivor Profile v3."""

from SurvivorCatalogMeta import QUESTS


_CONTENT_CATEGORY = {
    "character": "characters",
    "weapon": "weapons",
    "tome": "tomes",
    "trinket": "trinkets",
}


class SurvivorQuestTracker:
    def __init__(self, profile):
        self.profile = profile
        self.by_metric = {}
        for quest in QUESTS:
            self.by_metric.setdefault(quest["metric"], []).append(quest)
        self.buffer = []
        self.run_values = {}
        self.run_quest_gold = 0
        self.completed_this_run = []

    def reset_run(self):
        self.buffer = []
        self.run_values = {}
        self.run_quest_gold = 0
        self.completed_this_run = []

    def record(self, metric, amount=1, context=None, bSet=False):
        if metric in self.by_metric:
            self.buffer.append((metric, amount, dict(context or {}), bool(bSet)))

    @staticmethod
    def _matches(filters, context):
        for key, expected in filters.items():
            actual = context.get(key)
            if key == "tags":
                if not set(expected).intersection(set(actual or ())):
                    return False
            elif isinstance(expected, (tuple, list, set)):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def _eligible_quest(self, quest):
        completed = set(self.profile.get("completedQuests", ()))
        if not all(
            prerequisite in completed
            for prerequisite in quest["prerequisiteIds"]
        ):
            return False
        hidden_until = quest.get("hiddenUntil", "")
        if hidden_until.startswith("meta_weapon_slots:"):
            try:
                required_level = int(hidden_until.rsplit(":", 1)[1])
            except (TypeError, ValueError):
                return False
            return self.profile.get("powerUps", {}).get(
                "meta_weapon_slots", 0,
            ) >= required_level
        return True

    def _complete(self, quest):
        quest_id = quest["id"]
        completed = self.profile["completedQuests"]
        if quest_id in completed:
            return False
        completed.append(quest_id)
        self.completed_this_run.append(quest_id)
        self.run_quest_gold += quest["rewardGold"]
        category = _CONTENT_CATEGORY.get(quest["unlockType"])
        unlock_id = quest["unlockId"]
        if category and unlock_id:
            eligible = self.profile["eligible"][category]
            owned = self.profile["owned"][category]
            if unlock_id not in eligible and unlock_id not in owned:
                eligible.append(unlock_id)
        self.record(
            "quests_completed",
            len(completed),
            {"questId": quest_id},
            True,
        )
        return True

    def flush(self):
        while self.buffer:
            metric, amount, context, bSet = self.buffer.pop(0)
            for quest in self.by_metric.get(metric, ()):
                quest_id = quest["id"]
                if quest_id in self.profile["completedQuests"]:
                    continue
                if not self._eligible_quest(quest):
                    continue
                if not self._matches(quest["filters"], context):
                    continue
                target = float(quest["target"])
                if quest["progressMode"] == "run":
                    previous = float(self.run_values.get(quest_id, 0.0))
                    value = max(previous, float(amount)) if bSet else previous + float(amount)
                    self.run_values[quest_id] = value
                else:
                    progress = self.profile["questProgress"]
                    previous = float(progress.get(quest_id, 0.0))
                    value = max(previous, float(amount)) if bSet else previous + float(amount)
                    progress[quest_id] = value
                if value >= target:
                    self._complete(quest)
        return tuple(self.completed_this_run)
