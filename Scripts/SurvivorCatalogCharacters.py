"""Playable-character catalog for Starbloom Survivor."""

from SurvivorRuntimeAssets import asset_path


def _character(
        character_id,
        zh_name,
        en_name,
        model_name,
        starter_weapon,
        price,
        quest_id,
        modifiers,
        hooks,
        scale=0.0088,
        model_family="CuteAnimatedCharacters"):
    asset_key = "character/" + character_id + "/"
    return {
        "id": character_id,
        "name": {"zh_cn": zh_name, "en": en_name},
        "description": {
            "zh_cn": "以独特被动与起始武器展开星光冒险。",
            "en": "Begins each starlight adventure with a unique passive and weapon.",
        },
        "model": model_name,
        "mesh": asset_path(asset_key + "mesh"),
        "controller": asset_path(asset_key + "controller"),
        "idle": asset_path(asset_key + "idle"),
        "dance": asset_path(asset_key + "dance"),
        "scale": scale,
        "starterWeapon": starter_weapon,
        "price": price,
        "unlockId": quest_id,
        "modifiers": dict(modifiers),
        "hooks": tuple(hooks),
        "preview": {
            # Exported meshes and animation palettes already use engine Y-up.
            # Applying the original source-family correction again tips the
            # character forward in native, Web and mini-game presentation.
            "upright": 0.0,
            "yaw": 0.0,
            "pitch": -0.08,
            "zoom": 1.0,
        },
        "icon": asset_path(asset_key + "icon"),
    }


CHARACTERS = (
    _character(
        "starpaw", "星爪猫", "Starpaw", "Cat", "comet", 0, "quest_start",
        {"crit_chance_add": 0.05, "move_speed_mul": 1.08},
        ("on_level_starpaw_might",),
        0.0075,
        "UltimateMonsters",
    ),
    _character(
        "peachy", "桃桃团", "Peachy", "Pig", "bubble", 100,
        "quest_character_peachy",
        {"max_health_add": 35.0, "magnet_range_mul": 1.25},
        ("on_overheal_bubble_shield",),
        0.0095,
    ),
    _character(
        "mossling", "苔苔球", "Mossling", "Cactus", "dagger", 150,
        "quest_character_mossling",
        {"weapon_cooldown_mul": 0.88, "move_speed_mul": 1.12},
        ("on_distance_cast_echo",),
        0.0086,
    ),
    _character(
        "snowbean", "雪豆豆", "Snowbean", "Panda", "frostorb", 200,
        "quest_character_snowbean",
        {"weapon_reach_mul": 1.18, "weapon_damage_mul": 1.12},
        ("on_damage_freeze_burst",),
    ),
    _character(
        "azura", "小苍蓝", "Azura", "Penguin", "petalstorm", 250,
        "quest_character_azura",
        {"projectile_add": 1, "projectile_speed_mul": 1.20},
        ("on_item_maxed_projectile_area",),
    ),
    _character(
        "honeybun", "蜜糖蜂", "Honeybun", "Bee", "honeyneedle", 300,
        "quest_character_honeybun",
        {"gold_gain_mul": 1.0},
        ("on_hit_honey_mark", "on_level_honey_gold"),
    ),
    _character(
        "mushmellow", "绵菇菇", "Mushmellow", "Mushroom", "sporecap", 350,
        "quest_character_mushmellow",
        {},
        ("on_poison_kill_spread",),
    ),
    _character(
        "boolet", "幽幽团", "Boolet", "Ghost", "phantombell", 400,
        "quest_character_boolet",
        {"max_health_add": -20.0, "evasion_add": 0.12, "luck_add": 0.18},
        ("on_evade_phantom_echo",),
    ),
    _character(
        "crabble", "珊瑚钳", "Crabble", "Crab", "coralanchor", 450,
        "quest_character_crabble",
        {"armor_add": 2.0, "thorns_add": 20.0},
        ("on_damage_prevented_tidal_wave",),
    ),
    _character(
        "cosmobob", "星外豆", "Cosmobob", "Alien", "prismorbit", 600,
        "quest_character_cosmobob",
        {"difficulty_mul": 1.20, "xp_gain_mul": 1.15, "gold_gain_mul": 1.15},
        ("on_level_cosmic_training",),
    ),
)

CHARACTER_BY_ID = {entry["id"]: entry for entry in CHARACTERS}
