"""Quest, unlock-product, and PowerUp catalog."""

from SurvivorMetaProgression import META_POWER_UP_RULES
from SurvivorRuntimeAssets import asset_path


def _quest(
        quest_id,
        category,
        zh_title,
        en_title,
        metric,
        target,
        unlock_type="",
        unlock_id="",
        reward_gold=0,
        filters=None,
        prerequisites=(),
        hidden_until="",
        progress_mode="career",
        retroactive=True):
    return {
        "id": quest_id,
        "category": category,
        "title": {"zh_cn": zh_title, "en": en_title},
        "description": {
            "zh_cn": "完成目标以获得金币与新内容购买资格。",
            "en": "Complete the objective to earn gold and purchase eligibility.",
        },
        "metric": metric,
        "target": target,
        "filters": dict(filters or {}),
        "prerequisiteIds": tuple(prerequisites),
        "rewardGold": int(reward_gold),
        "unlockType": unlock_type,
        "unlockId": unlock_id,
        "hiddenUntil": hidden_until,
        "progressMode": progress_mode,
        "bRetroactive": bool(retroactive),
    }


QUESTS = [
    _quest("quest_start", "system", "第一束星光", "First Starlight", "profile_created", 1, reward_gold=0),
]

_CHARACTER_QUESTS = (
    ("peachy", "存活两分钟", "Survive Two Minutes", "survival_seconds", 120, {}),
    ("mossling", "怪潮初识", "Meet the Horde", "kills", 750, {}),
    ("snowbean", "初见强敌", "First Boss", "boss_kills", 1, {}),
    ("azura", "星光二十级", "Level Twenty", "best_level", 20, {}),
    ("honeybun", "蜂针如雨", "Needle Rain", "projectiles_spawned", 2500, {}),
    ("mushmellow", "孢子花园", "Spore Garden", "kills", 500, {"tags": ("poison", "zone")}),
    ("boolet", "无伤幽步", "Ghost Step", "no_damage_seconds_after", 90, {"afterSeconds": 300}),
    ("crabble", "坚不可摧", "Unbreakable", "damage_prevented", 1000, {}),
    ("cosmobob", "星门初开", "Open the Star Gate", "difficulty_clear", 1, {"difficulty": "adventure"}),
)
for row in _CHARACTER_QUESTS:
    QUESTS.append(_quest(
        "quest_character_" + row[0], "character", row[1], row[2], row[3], row[4],
        "character", row[0], 35, row[5],
        progress_mode="run" if row[0] == "boolet" else "career",
    ))

_NEW_WEAPON_QUESTS = (
    ("honeyneedle", "蜂针练习", "Needle Practice", "projectiles_spawned", 2500, {}),
    ("sporecap", "六分钟花园", "Six-Minute Garden", "survival_seconds", 360, {}),
    ("phantombell", "暴击铃声", "Critical Chimes", "critical_hits", 300, {}),
    ("coralanchor", "牵引潮汐", "Tidal Pull", "enemies_moved", 1000, {}),
    ("prismorbit", "折射通关", "Clear Refraction", "difficulty_clear", 1, {"difficulty": "adventure"}),
    ("acornmortar", "连环爆米花", "Acorn Multikills", "multikill_5", 100, {}),
    ("frostorb", "冰糖收藏", "Frost Collection", "status_applied", 500, {"status": ("slow", "freeze")}),
    ("gravityyoyo", "回程高手", "Return Expert", "damage", 50000, {"path": "return"}),
    ("rainbowrail", "强敌轨迹", "Elite Rail", "elite_boss_kills", 30, {}),
)
for row in _NEW_WEAPON_QUESTS:
    QUESTS.append(_quest(
        "quest_weapon_" + row[0], "weapon", row[1], row[2], row[3], row[4],
        "weapon", row[0], 30, row[5],
    ))

_CURRENT_UNLOCK_QUESTS = (
    ("weapon", "ring", "环绕教学", "Ring Lesson", "kills", 120, {"weapon": "ring"}, 80),
    ("weapon", "fireball", "火球教学", "Fireball Lesson", "hits", 300, {"weapon": "fireball"}, 80),
    ("weapon", "moonblade", "月刃教学", "Moon Lesson", "pierce_hits", 250, {}, 90),
    ("weapon", "bubble", "泡泡教学", "Bubble Lesson", "bounce_hits", 250, {}, 90),
    ("weapon", "aura", "灵光收集", "Wisp Collection", "xp_collected", 1000, {}, 100),
    ("weapon", "dagger", "十二级飞刀", "Level Twelve Daggers", "best_level", 12, {}, 100),
    ("weapon", "starwheel", "千怪星轮", "Thousand-Wheel", "kills", 1000, {}, 140),
    ("weapon", "petalstorm", "十八级花瓣", "Level Eighteen Petals", "best_level", 18, {}, 140),
    ("weapon", "comet", "彗星启程", "Comet Start", "runs", 1, {}, 0),
    ("tome", "fortune", "百次幸运", "Hundred Crits", "critical_hits", 100, {}, 90),
    ("tome", "quantity", "千枚星弹", "Thousand Projectiles", "projectiles_spawned", 1000, {}, 120),
    ("tome", "duration", "长效魔法", "Lasting Magic", "effect_seconds", 120, {"tags": ("zone", "orbit", "return")}, 100),
    ("tome", "recovery", "治愈之路", "Healing Path", "healing", 200, {}, 100),
    ("tome", "thorns", "荆棘反击", "Thorny Return", "thorns_prevented", 300, {}, 120),
    ("tome", "greed", "第一袋金币", "First Gold Bag", "gold_earned", 300, {}, 150),
    ("tome", "status", "异彩五百", "Five Hundred Status", "status_applied", 500, {}, 150),
    ("tome", "curse", "诅咒通关", "Cursed Clear", "difficulty_clear", 1, {"tome": "curse"}, 200),
)
for row in _CURRENT_UNLOCK_QUESTS:
    QUESTS.append(_quest(
        "quest_" + row[0] + "_" + row[1], row[0], row[2], row[3], row[4], row[5],
        row[0], row[1], 20, row[6],
    ))

_TRINKET_QUESTS = (
    ("popcorn", "popcorn_kernel", "爆米花连杀", "Popcorn Multikill", "multikill_5", 25, {}),
    ("echo", "echo_shell", "千次回声", "Thousand Casts", "casts", 1000, {}),
    ("ribbon", "lucky_ribbon", "幸运绝唱", "Lucky Finale", "critical_kills", 150, {}),
    ("glass", "glass_star", "满血三分钟", "Three Minutes Full", "full_health_seconds", 180, {}),
    ("boss", "boss_bell", "十位强敌", "Ten Bosses", "boss_kills", 10, {}),
    ("battery", "bloom_battery", "花火电量", "Bloom Charge", "damage", 100000, {"tags": ("zone", "tick")}),
    ("tail", "comet_tail", "五千命中", "Five Thousand Hits", "projectile_hits", 5000, {}),
    ("friendship", "friendship_pin", "终局·六星同辉", "Endgame: Six Stars Together", "weapons_at_level", 6, {"level": 5}),
)
for row in _TRINKET_QUESTS:
    QUESTS.append(_quest(
        "quest_trinket_" + row[0], "trinket", row[2], row[3], row[4], row[5],
        "trinket", row[1], 25, row[6],
        progress_mode="run" if row[0] in ("glass", "friendship") else "career",
    ))

QUESTS.extend((
    _quest("quest_system_reroll", "system", "三颗星愿", "Three Wishes", "quests_completed", 3, "system", "reroll", 50),
    _quest("quest_system_skip", "system", "八颗星愿", "Eight Wishes", "quests_completed", 8, "system", "skip", 75, prerequisites=("quest_system_reroll",)),
    _quest("quest_system_banish", "system", "十二颗星愿", "Twelve Wishes", "quests_completed", 12, "system", "banish", 100, prerequisites=("quest_system_skip",)),
    _quest("quest_system_seal", "system", "二十颗星愿", "Twenty Wishes", "quests_completed", 20, "system", "pool_toggle", 150, prerequisites=("quest_system_banish",)),
    _quest("quest_clear_adventure", "difficulty", "冒险首通", "Adventure Clear", "difficulty_clear", 1, "difficulty", "fierce", 100, {"difficulty": "adventure"}),
    _quest("quest_clear_fierce", "difficulty", "勇猛首通", "Fierce Clear", "difficulty_clear", 1, "difficulty", "nightmare", 150, {"difficulty": "fierce"}, ("quest_clear_adventure",)),
    _quest("quest_clear_challenge", "difficulty", "挑战印记", "Challenge Mark", "challenge_clear", 1, "system", "challenge_marks", 120),
    _quest("quest_build_first_evolution", "build", "首次进化", "First Evolution", "evolutions", 1, reward_gold=80),
    _quest("quest_build_double_evolution", "build", "双重进化", "Double Evolution", "evolutions_in_run", 2, reward_gold=120, prerequisites=("quest_build_first_evolution",), progress_mode="run", retroactive=False),
    _quest("quest_build_six_weapon_clear", "build", "终局·六武器通关", "Endgame: Six-Weapon Clear", "different_damage_weapons_clear", 6, reward_gold=160),
))

for _quest_entry in QUESTS:
    if _quest_entry["id"] in (
            "quest_trinket_friendship", "quest_build_six_weapon_clear"):
        _quest_entry["hiddenUntil"] = "meta_weapon_slots:3"
        _quest_entry["description"] = {
            "zh_cn": "购买第六个普通武器槽后，在同一局中完成这个终局构筑目标。",
            "en": "Purchase the sixth regular weapon slot, then complete this endgame build objective in one run.",
        }

QUESTS = tuple(QUESTS)
QUEST_BY_ID = {entry["id"]: entry for entry in QUESTS}


_PRICES = {
    "characters": {"starpaw": 0, "peachy": 100, "mossling": 150, "snowbean": 200, "azura": 250, "honeybun": 300, "mushmellow": 350, "boolet": 400, "crabble": 450, "cosmobob": 600},
    "weapons": {"comet": 0, "ring": 0, "fireball": 0, "moonblade": 0, "bubble": 0, "aura": 100, "dagger": 100, "starwheel": 140, "petalstorm": 140, "honeyneedle": 120, "sporecap": 140, "phantombell": 160, "coralanchor": 180, "prismorbit": 240, "acornmortar": 170, "frostorb": 190, "gravityyoyo": 210, "rainbowrail": 300},
    "tomes": {"magnet": 0, "vitality": 0, "guard": 0, "might": 0, "haste": 0, "reach": 0, "growth": 0, "velocity": 0, "fortune": 90, "quantity": 120, "duration": 100, "recovery": 100, "thorns": 120, "greed": 150, "status": 150, "curse": 200},
    "trinkets": {"prism_lens": 0, "sticky_honey": 0, "tiny_magnet": 0, "marshmallow_shield": 0, "popcorn_kernel": 80, "echo_shell": 100, "lucky_ribbon": 120, "glass_star": 140, "boss_bell": 180, "bloom_battery": 160, "comet_tail": 180, "friendship_pin": 220},
}


def _unlock_id(category, content_id):
    if category == "characters":
        return "quest_start" if content_id == "starpaw" else "quest_character_" + content_id
    if category == "weapons":
        return "quest_weapon_" + content_id
    if category == "tomes":
        if content_id == "curse":
            return "quest_clear_adventure"
        if content_id in ("magnet", "vitality", "guard", "might", "haste", "reach", "growth", "velocity"):
            return "quest_start"
        return "quest_tome_" + content_id
    initial = ("prism_lens", "sticky_honey", "tiny_magnet", "marshmallow_shield")
    if content_id in initial:
        return "quest_start"
    suffix = {
        "popcorn_kernel": "popcorn", "echo_shell": "echo",
        "lucky_ribbon": "ribbon", "glass_star": "glass",
        "boss_bell": "boss", "bloom_battery": "battery",
        "comet_tail": "tail", "friendship_pin": "friendship",
    }[content_id]
    return "quest_trinket_" + suffix


PRODUCTS = tuple(
    {
        "id": category + ":" + content_id,
        "category": category,
        "contentId": content_id,
        "price": price,
        "unlockId": _unlock_id(category, content_id),
    }
    for category, prices in _PRICES.items()
    for content_id, price in prices.items()
)


POWER_UPS = tuple(
    dict(
        definition,
        icon=asset_path("powerup/" + definition["id"] + "/icon"),
    )
    for definition in META_POWER_UP_RULES
)

_POWER_UP_NAMES = {
    "meta_might": ("星光力量", "Starlight Might"),
    "meta_health": ("活力上限", "Vitality"),
    "meta_recovery": ("温柔复苏", "Recovery"),
    "meta_move": ("轻盈脚步", "Fleet Feet"),
    "meta_magnet": ("星光吸引", "Magnet"),
    "meta_growth": ("成长祝福", "Growth"),
    "meta_luck": ("幸运丝线", "Luck"),
    "meta_greed": ("丰收星愿", "Greed"),
    "meta_reroll": ("重抽次数", "Rerolls"),
    "meta_skip": ("跳过次数", "Skips"),
    "meta_banish": ("放逐次数", "Banishes"),
    "meta_revive": ("再燃星光", "Revive"),
    "meta_weapon_slots": ("武器槽位", "Weapon Slots"),
}
_POWER_UP_DESCRIPTIONS = {
    "meta_might": ("武器伤害每级 +3%。", "Weapon damage +3% per level."),
    "meta_health": ("最大生命每级 +5%。", "Maximum health +5% per level."),
    "meta_recovery": ("生命恢复每级 +0.05/秒。", "Recovery +0.05 HP/s per level."),
    "meta_move": ("移动速度每级 +3%。", "Movement speed +3% per level."),
    "meta_magnet": ("星光吸引范围每级 +12.5%。", "Starlight magnet range +12.5% per level."),
    "meta_growth": ("经验获取每级 +3%。", "XP gain +3% per level."),
    "meta_luck": ("暴击率与幸运每级 +2%。", "Critical chance and luck +2% per level."),
    "meta_greed": ("本局与结算金币每级 +5%。", "Run and result gold +5% per level."),
    "meta_reroll": ("每局增加 1 次重抽。", "Gain one additional reroll per run."),
    "meta_skip": ("每局增加 1 次跳过。", "Gain one additional skip per run."),
    "meta_banish": ("每局增加 1 次放逐。", "Gain one additional banish per run."),
    "meta_revive": ("每局可复活 1 次。", "Revive once per run."),
    "meta_weapon_slots": (
        "将普通武器上限从 3 槽逐步扩展至 6 槽；每一级需要对应难度首通。",
        "Expand the regular weapon limit from 3 to 6; each level requires its matching difficulty clear.",
    ),
}
for _power_up in POWER_UPS:
    _names = _POWER_UP_NAMES[_power_up["id"]]
    _descriptions = _POWER_UP_DESCRIPTIONS[_power_up["id"]]
    _power_up["name"] = {"zh_cn": _names[0], "en": _names[1]}
    _power_up["description"] = {
        "zh_cn": _descriptions[0], "en": _descriptions[1],
    }
