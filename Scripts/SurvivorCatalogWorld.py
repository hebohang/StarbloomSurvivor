"""Enemy roles, wave timeline, difficulties, and challenges."""

from SurvivorRuntimeAssets import asset_path


def _enemy(
        enemy_id,
        zh_name,
        en_name,
        behavior,
        health,
        speed,
        damage,
        radius,
        reward,
        preferred_range=0.0,
        attacks=("melee",),
        resistances=None,
        scale=0.008,
        asset_kind="enemy"):
    asset_key = asset_kind + "/" + enemy_id + "/"
    return {
        "id": enemy_id,
        "name": {"zh_cn": zh_name, "en": en_name},
        "prefab": asset_path(asset_key + "prefab"),
        "mesh": asset_path(asset_key + "mesh"),
        "controller": asset_path(asset_key + "controller"),
        "scale": scale,
        "health": float(health),
        "speed": float(speed),
        "damage": float(damage),
        "radius": float(radius),
        "rewardXp": int(reward),
        "behaviorId": behavior,
        "moveMode": behavior,
        "preferredRange": float(preferred_range),
        "acceleration": 8.0,
        "attackSet": tuple(attacks),
        "telegraph": 0.35 if behavior in ("chaser", "flanker") else 0.65,
        "cooldown": 1.05,
        "projectile": "enemy_orange_orb" if "ranged" in attacks else "",
        "zone": "enemy_ground_zone" if "zone" in attacks else "",
        "resistances": dict(resistances or {}),
        "eliteAffixes": ("swift", "armored", "volatile", "commander"),
        "coinChance": 0.02,
        "animationState": behavior,
        "icon": asset_path(asset_key + "icon"),
    }


ENEMIES = (
    _enemy("green_blob", "绿团怪", "Green Blob", "chaser", 15, 1.55, 6, 0.72, 1, scale=0.0053),
    _enemy("pink_blob", "粉团侧袭者", "Pink Flanker", "flanker", 28, 2.05, 6, 0.70, 1, attacks=("dash",), scale=0.0065),
    _enemy("spiky_blob", "荆棘盾团", "Spiky Guard", "armored", 48, 1.35, 9, 0.82, 2, resistances={"frontDamage": 0.45}, scale=0.0048),
    _enemy("orc_bruiser", "兽人重锤", "Orc Bruiser", "bruiser", 78, 1.28, 13, 0.96, 3, attacks=("heavy_arc",), scale=0.0065),
    _enemy("yeti_zoner", "雪怪压区者", "Yeti Zoner", "zone", 138, 1.08, 15, 1.10, 5, 5.0, ("zone", "melee"), {"freeze": 0.45}, 0.0048),
    _enemy("alien_charger", "星外冲锋手", "Alien Charger", "charger", 58, 1.70, 12, 0.76, 3, attacks=("charge",), scale=0.0085),
    _enemy("bee_ranger", "蜂群射手", "Bee Ranger", "ranged", 34, 1.85, 7, 0.60, 2, 7.5, ("ranged",), scale=0.0080),
    _enemy("mushroom_lobber", "孢子投手", "Mushroom Lobber", "lobber", 55, 1.20, 10, 0.72, 3, 8.0, ("lobbed_zone",), scale=0.0088),
    _enemy("ghost_ambusher", "幽影伏击者", "Ghost Ambusher", "ghost", 42, 1.72, 11, 0.68, 3, attacks=("phase_dash",), resistances={"knockbackWhilePhased": 1.0}, scale=0.0087),
    _enemy("crab_guard", "横移蟹卫", "Crab Guard", "shield", 105, 1.15, 11, 0.92, 4, attacks=("shield_bash",), resistances={"frontDamage": 0.60}, scale=0.0086),
    _enemy("bomb_spore", "爆爆孢子", "Bomb Spore", "suicide", 26, 2.15, 22, 0.64, 2, attacks=("suicide",), scale=0.0065),
    _enemy("alien_commander", "星外指挥官", "Alien Commander", "summoner", 92, 1.05, 8, 0.82, 5, 7.0, ("summon", "haste_aura"), scale=0.0100),
)
ENEMY_BY_ID = {entry["id"]: entry for entry in ENEMIES}


def _boss(
        boss_id,
        zh_name,
        en_name,
        behavior,
        health,
        damage,
        attacks,
        scale):
    result = _enemy(
        boss_id, zh_name, en_name, behavior, health, 1.18,
        damage, 1.70, 25, 6.0, attacks,
        {"knockback": 0.78, "freeze": 0.75, "instantKill": 1.0}, scale,
        asset_kind="boss",
    )
    result["boss"] = True
    result["eliteAffixes"] = ()
    result["coinChance"] = 1.0
    result["phaseThresholds"] = (0.65, 0.32)
    return result


BOSSES = (
    _boss("yeti_colossus", "雪原巨兽", "Yeti Colossus", "boss_yeti", 900, 18, ("ice_zone", "triple_slam"), 0.0085),
    _boss("orc_warlord", "兽人酋长", "Orc Warlord", "boss_orc", 1900, 23, ("heavy_arc", "charge", "summon_orc"), 0.0105),
    _boss("azure_demon", "苍蓝魔王", "Azure Demon", "boss_demon", 3000, 27, ("fan_projectile", "rune_zone", "phase_two"), 0.0045),
    _boss("mushroom_monarch", "菌星君王", "Mushroom Monarch", "boss_mushroom", 4200, 30, ("spore_rain", "moving_safe_zone", "summon"), 0.0160),
    _boss("star_dragon", "星外巨龙", "Star Dragon", "boss_dragon", 50000, 34, ("ring_projectile", "sweep_breath", "final_charge", "region_pressure", "summon"), 0.0190),
)
BOSS_BY_ID = {entry["id"]: entry for entry in BOSSES}


_WAVE_ROWS = (
    (0, 60, 16, 24, 0.65, 2, (("green_blob", 1.0),), 0.00, "", 0),
    (60, 120, 24, 34, 0.55, 2, (("green_blob", 0.72), ("pink_blob", 0.28)), 0.00, "", 0),
    (120, 180, 34, 48, 0.48, 2, (("green_blob", 0.48), ("pink_blob", 0.32), ("spiky_blob", 0.20)), 0.001, "lane_rush", 0),
    (180, 240, 42, 58, 0.46, 2, (("green_blob", 0.55), ("pink_blob", 0.25), ("spiky_blob", 0.20)), 0.001, "", 0),
    (240, 300, 58, 78, 0.38, 3, (("green_blob", 0.35), ("pink_blob", 0.25), ("bee_ranger", 0.40)), 0.0015, "four_side", 0),
    (300, 360, 76, 98, 0.32, 3, (("pink_blob", 0.20), ("spiky_blob", 0.25), ("orc_bruiser", 0.30), ("alien_charger", 0.25)), 0.002, "elite_twins", 0),
    (360, 420, 82, 110, 0.30, 3, (("spiky_blob", 0.25), ("orc_bruiser", 0.35), ("alien_charger", 0.25), ("bee_ranger", 0.15)), 0.002, "", 0),
    (420, 480, 110, 135, 0.25, 4, (("mushroom_lobber", 0.30), ("ghost_ambusher", 0.30), ("orc_bruiser", 0.20), ("bee_ranger", 0.20)), 0.003, "", 0),
    (480, 540, 130, 160, 0.22, 4, (("pink_blob", 0.20), ("ghost_ambusher", 0.20), ("crab_guard", 0.20), ("bomb_spore", 0.25), ("alien_commander", 0.15)), 0.0035, "rush_commander", 0),
    (540, 600, 150, 180, 0.20, 4, (("crab_guard", 0.25), ("bee_ranger", 0.25), ("bomb_spore", 0.25), ("mushroom_lobber", 0.25)), 0.004, "", 0),
    (600, 660, 150, 190, 0.19, 4, (("spiky_blob", 0.20), ("crab_guard", 0.25), ("bee_ranger", 0.25), ("alien_commander", 0.30)), 0.004, "", 0),
    (660, 720, 185, 215, 0.17, 5, (("alien_charger", 0.25), ("ghost_ambusher", 0.20), ("bomb_spore", 0.20), ("alien_commander", 0.15), ("crab_guard", 0.20)), 0.005, "four_wall", 0),
    (720, 780, 205, 240, 0.15, 5, (("alien_charger", 0.30), ("mushroom_lobber", 0.25), ("bee_ranger", 0.20), ("crab_guard", 0.25)), 0.006, "charge_lanes", 0),
    (780, 840, 210, 250, 0.15, 5, (("mushroom_lobber", 0.25), ("ghost_ambusher", 0.20), ("bomb_spore", 0.20), ("alien_commander", 0.15), ("crab_guard", 0.20)), 0.007, "", 0),
    (840, 900, 245, 300, 0.12, 6, (("spiky_blob", 0.12), ("orc_bruiser", 0.12), ("alien_charger", 0.16), ("bee_ranger", 0.14), ("mushroom_lobber", 0.14), ("ghost_ambusher", 0.12), ("crab_guard", 0.10), ("bomb_spore", 0.10)), 0.008, "final_peak", 0),
)


_HP = (1.0, 1.08, 1.16, 1.25, 1.38, 1.52, 1.65, 1.82, 2.02, 2.25, 2.48, 2.68, 2.90, 3.12, 3.60)
_DAMAGE = (1.0, 1.03, 1.06, 1.10, 1.16, 1.22, 1.28, 1.36, 1.45, 1.55, 1.66, 1.76, 1.85, 1.96, 2.15)
_SPEED = (1.0, 1.01, 1.02, 1.03, 1.05, 1.06, 1.07, 1.09, 1.10, 1.12, 1.14, 1.16, 1.18, 1.20, 1.24)
WAVES = tuple({
    "minute": index,
    "start": row[0],
    "end": row[1],
    "countStart": row[2],
    "countEnd": row[3],
    "spawnInterval": row[4],
    "batch": row[5],
    "pool": row[6],
    "healthMultiplier": _HP[index],
    "damageMultiplier": _DAMAGE[index],
    "speedMultiplier": _SPEED[index],
    "eliteRate": row[7],
    "event": row[8],
    "chestTier": row[9],
} for index, row in enumerate(_WAVE_ROWS))

BOSS_EVENTS = (
    {
        "id": "starbloom_final_objective",
        "bossId": "star_dragon",
        "objectiveBoss": True,
        "finalBoss": True,
        "requiredRegions": 4,
        "centralHoldSeconds": 2.0,
        "introSeconds": 3.0,
        "softEnrageSeconds": 120.0,
    },
)

DIFFICULTIES = (
    {"id": "adventure", "health": 1.0, "damage": 1.0, "speed": 1.0, "spawn": 1.0, "gold": 1.0, "unlockId": "quest_start"},
    {"id": "fierce", "health": 1.30, "damage": 1.22, "speed": 1.10, "spawn": 1.20, "gold": 1.35, "unlockId": "quest_clear_adventure"},
    {"id": "nightmare", "health": 1.75, "damage": 1.50, "speed": 1.18, "spawn": 1.45, "gold": 1.80, "unlockId": "quest_clear_fierce"},
)

CHALLENGES = (
    {"id": "swarm", "enemyCount": 1.65, "enemySpeed": 1.15, "xp": 0.80, "gold": 1.45},
    {"id": "chonk", "enemyHealth": 2.0, "enemyDamage": 1.45, "enemyScale": 1.6, "enemySpeed": 0.85, "gold": 1.55},
    {"id": "fragile_star", "playerMaxHealth": 1, "gold": 2.0},
    {"id": "hurry", "clock": 1.5, "xp": 1.25, "gold": 1.50},
    {"id": "no_trinkets", "disableTrinkets": True, "gold": 1.35},
    {"id": "cursed_bloom", "healthPerMinute": 0.08, "damagePerMinute": 0.05, "spawnPerMinute": 0.05, "gold": 2.0},
)
