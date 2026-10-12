"""Data shared by the Survivor weapons, Tomes, upgrades, and HUD."""

from SurvivorRuntimeAssets import asset_path


MAX_WEAPON_SLOTS = 6
MAX_TOME_SLOTS = 6

CHARACTER_ORDER = ("starpaw", "peachy", "mossling", "snowbean", "azura")

CHARACTER_DEFS = {
    "starpaw": {
        "name_key": "character_starpaw_name", "passive_key": "character_starpaw_passive",
        "unlock_key": "character_unlocked", "badge": "S",
        "mesh": asset_path("character/starpaw/mesh"),
        "controller": asset_path("character/starpaw/controller"),
        "scale": 0.0075, "weapon": "comet",
        "modifiers": {"crit_chance_add": 0.05, "move_speed_mul": 1.08},
        "hooks": ("on_level_starpaw_might",),
    },
    "peachy": {
        "name_key": "character_peachy_name", "passive_key": "character_peachy_passive",
        "unlock_key": "character_peachy_unlock", "badge": "P",
        "mesh": asset_path("character/peachy/mesh"),
        "controller": asset_path("character/peachy/controller"),
        "scale": 0.0095, "weapon": "bubble",
        "modifiers": {"max_health_add": 35.0, "magnet_range_mul": 1.25},
        "hooks": ("on_overheal_bubble_shield",),
    },
    "mossling": {
        "name_key": "character_mossling_name", "passive_key": "character_mossling_passive",
        "unlock_key": "character_mossling_unlock", "badge": "M",
        "mesh": asset_path("character/mossling/mesh"),
        "controller": asset_path("character/mossling/controller"),
        "scale": 0.0086, "weapon": "dagger",
        "modifiers": {"weapon_cooldown_mul": 0.88, "move_speed_mul": 1.12},
        "hooks": ("on_distance_cast_echo",),
    },
    "snowbean": {
        "name_key": "character_snowbean_name", "passive_key": "character_snowbean_passive",
        "unlock_key": "character_snowbean_unlock", "badge": "N",
        "mesh": asset_path("character/snowbean/mesh"),
        "controller": asset_path("character/snowbean/controller"),
        "scale": 0.0088, "weapon": "frostorb",
        "modifiers": {"weapon_reach_mul": 1.18, "weapon_damage_mul": 1.12},
        "hooks": ("on_damage_freeze_burst",),
    },
    "azura": {
        "name_key": "character_azura_name", "passive_key": "character_azura_passive",
        "unlock_key": "character_azura_unlock", "badge": "A",
        "mesh": asset_path("character/azura/mesh"),
        "controller": asset_path("character/azura/controller"),
        "scale": 0.0088, "weapon": "petalstorm",
        "modifiers": {"projectile_add": 1, "projectile_speed_mul": 1.20},
        "hooks": ("on_item_maxed_projectile_area",),
    },
}

WEAPON_ORDER = (
    "ring",
    "fireball",
    "moonblade",
    "bubble",
    "aura",
    "dagger",
    "starwheel",
    "petalstorm",
    "comet",
)

WEAPON_DEFS = {
    "ring": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "ring_label",
        "icon": asset_path("weapon/ring/icon"),
        "effect": asset_path("weapon/ring/body-vfx"),
        "unlock_name_key": "upgrade_ring_unlock_name",
        "unlock_desc_key": "upgrade_ring_unlock_desc",
        "unlock_stat_key": "upgrade_ring_unlock_stat",
        "upgrade_name_key": "upgrade_ring_name",
        "upgrade_desc_key": "upgrade_ring_desc",
        "upgrade_stat_key": "upgrade_ring_stat",
    },
    "fireball": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "fireball_label",
        "icon": asset_path("weapon/fireball/icon"),
        "effect": asset_path("weapon/fireball/body-vfx"),
        "unlock_name_key": "upgrade_fireball_unlock_name",
        "unlock_desc_key": "upgrade_fireball_unlock_desc",
        "unlock_stat_key": "upgrade_fireball_unlock_stat",
        "upgrade_name_key": "upgrade_fireball_name",
        "upgrade_desc_key": "upgrade_fireball_desc",
        "upgrade_stat_key": "upgrade_fireball_stat",
    },
    "moonblade": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "moonblade_label",
        "icon": asset_path("weapon/moonblade/icon"),
        "effect": asset_path("weapon/moonblade/body-vfx"),
        "unlock_name_key": "upgrade_moonblade_unlock_name",
        "unlock_desc_key": "upgrade_moonblade_unlock_desc",
        "unlock_stat_key": "upgrade_moonblade_unlock_stat",
        "upgrade_name_key": "upgrade_moonblade_name",
        "upgrade_desc_key": "upgrade_moonblade_desc",
        "upgrade_stat_key": "upgrade_moonblade_stat",
    },
    "bubble": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "bubble_label",
        "icon": asset_path("weapon/bubble/icon"),
        "effect": asset_path("weapon/bubble/body-vfx"),
        "unlock_name_key": "upgrade_bubble_unlock_name",
        "unlock_desc_key": "upgrade_bubble_unlock_desc",
        "unlock_stat_key": "upgrade_bubble_unlock_stat",
        "upgrade_name_key": "upgrade_bubble_name",
        "upgrade_desc_key": "upgrade_bubble_desc",
        "upgrade_stat_key": "upgrade_bubble_stat",
    },
    "aura": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "aura_label",
        "icon": asset_path("weapon/aura/icon"),
        "effect": asset_path("weapon/aura/body-vfx"),
        "unlock_name_key": "upgrade_aura_unlock_name",
        "unlock_desc_key": "upgrade_aura_unlock_desc",
        "unlock_stat_key": "upgrade_aura_unlock_stat",
        "upgrade_name_key": "upgrade_aura_name",
        "upgrade_desc_key": "upgrade_aura_desc",
        "upgrade_stat_key": "upgrade_aura_stat",
    },
    "dagger": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "dagger_label",
        "icon": asset_path("weapon/dagger/icon"),
        "effect": asset_path("weapon/dagger/body-vfx"),
        "unlock_name_key": "upgrade_dagger_unlock_name",
        "unlock_desc_key": "upgrade_dagger_unlock_desc",
        "unlock_stat_key": "upgrade_dagger_unlock_stat",
        "upgrade_name_key": "upgrade_dagger_name",
        "upgrade_desc_key": "upgrade_dagger_desc",
        "upgrade_stat_key": "upgrade_dagger_stat",
    },
    "starwheel": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "starwheel_label",
        "icon": asset_path("weapon/starwheel/icon"),
        "effect": asset_path("weapon/starwheel/body-vfx"),
        "unlock_name_key": "upgrade_starwheel_unlock_name",
        "unlock_desc_key": "upgrade_starwheel_unlock_desc",
        "unlock_stat_key": "upgrade_starwheel_unlock_stat",
        "upgrade_name_key": "upgrade_starwheel_name",
        "upgrade_desc_key": "upgrade_starwheel_desc",
        "upgrade_stat_key": "upgrade_starwheel_stat",
    },
    "petalstorm": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "petalstorm_label",
        "icon": asset_path("weapon/petalstorm/icon"),
        "effect": asset_path("weapon/petalstorm/body-vfx"),
        "unlock_name_key": "upgrade_petalstorm_unlock_name",
        "unlock_desc_key": "upgrade_petalstorm_unlock_desc",
        "unlock_stat_key": "upgrade_petalstorm_unlock_stat",
        "upgrade_name_key": "upgrade_petalstorm_name",
        "upgrade_desc_key": "upgrade_petalstorm_desc",
        "upgrade_stat_key": "upgrade_petalstorm_stat",
    },
    "comet": {
        "start_level": 0,
        "max_level": 10,
        "name_key": "comet_label",
        "icon": asset_path("weapon/comet/icon"),
        "effect": asset_path("weapon/comet/body-vfx"),
        "unlock_name_key": "upgrade_comet_unlock_name",
        "unlock_desc_key": "upgrade_comet_unlock_desc",
        "unlock_stat_key": "upgrade_comet_unlock_stat",
        "upgrade_name_key": "upgrade_comet_name",
        "upgrade_desc_key": "upgrade_comet_desc",
        "upgrade_stat_key": "upgrade_comet_stat",
    },
}

TOME_ORDER = (
    "magnet",
    "vitality",
    "guard",
    "might",
    "haste",
    "reach",
    "fortune",
    "growth",
    "quantity",
    "velocity",
    "duration",
)

TOME_DEFS = {
    "magnet": {
        "max_level": 5,
        "name_key": "upgrade_magnet_name",
        "icon": asset_path("tome/magnet/icon"),
        "description_key": "upgrade_magnet_desc",
        "stat_key": "upgrade_magnet_stat",
    },
    "vitality": {
        "max_level": 5,
        "name_key": "upgrade_vitality_name",
        "icon": asset_path("tome/vitality/icon"),
        "description_key": "upgrade_vitality_desc",
        "stat_key": "upgrade_vitality_stat",
    },
    "guard": {
        "max_level": 5,
        "name_key": "upgrade_guard_name",
        "icon": asset_path("tome/guard/icon"),
        "description_key": "upgrade_guard_desc",
        "stat_key": "upgrade_guard_stat",
    },
    "might": {
        "max_level": 5,
        "name_key": "upgrade_might_name",
        "icon": asset_path("tome/might/icon"),
        "description_key": "upgrade_might_desc",
        "stat_key": "upgrade_might_stat",
    },
    "haste": {
        "max_level": 5,
        "name_key": "upgrade_haste_name",
        "icon": asset_path("tome/haste/icon"),
        "description_key": "upgrade_haste_desc",
        "stat_key": "upgrade_haste_stat",
    },
    "reach": {
        "max_level": 5,
        "name_key": "upgrade_reach_name",
        "icon": asset_path("tome/reach/icon"),
        "description_key": "upgrade_reach_desc",
        "stat_key": "upgrade_reach_stat",
    },
    "fortune": {
        "max_level": 5,
        "name_key": "upgrade_fortune_name",
        "icon": asset_path("tome/fortune/icon"),
        "description_key": "upgrade_fortune_desc",
        "stat_key": "upgrade_fortune_stat",
    },
    "growth": {
        "max_level": 5,
        "name_key": "upgrade_growth_name",
        "icon": asset_path("tome/growth/icon"),
        "description_key": "upgrade_growth_desc",
        "stat_key": "upgrade_growth_stat",
    },
    "quantity": {
        "max_level": 5,
        "name_key": "upgrade_quantity_name",
        "icon": asset_path("tome/quantity/icon"),
        "description_key": "upgrade_quantity_desc",
        "stat_key": "upgrade_quantity_stat",
    },
    "velocity": {
        "max_level": 5,
        "name_key": "upgrade_velocity_name",
        "icon": asset_path("tome/velocity/icon"),
        "description_key": "upgrade_velocity_desc",
        "stat_key": "upgrade_velocity_stat",
    },
    "duration": {
        "max_level": 5,
        "name_key": "upgrade_duration_name",
        "icon": asset_path("tome/duration/icon"),
        "description_key": "upgrade_duration_desc",
        "stat_key": "upgrade_duration_stat",
    },
}


CONTENT_TEXT = {
    "zh_cn": {
        "tome_title": "奇妙绘本",
        "moonblade_label": "月光刃",
        "bubble_label": "泡泡连弹",
        "tornado_label": "口袋龙卷",
        "starfall_label": "星光坠击",
        "aura_label": "精灵齐射",
        "dagger_label": "星辉飞刀",
        "starwheel_label": "回旋星轮",
        "weapon_level_value": "{level}级",
        "tome_level_value": "{level}级",
        "upgrade_moonblade_unlock_name": "新伙伴：月光刃",
        "upgrade_moonblade_unlock_desc": "朝最近的敌群挥出一轮宽宽的月牙斩。",
        "upgrade_moonblade_unlock_stat": "新增自动武器 · 扇形穿透",
        "upgrade_moonblade_name": "月光刃",
        "upgrade_moonblade_desc": "月光刃升至 {level} 级：斩击更强，并能扫到更多敌人。",
        "upgrade_moonblade_stat": "斩击伤害 +10 · 命中数提升",
        "upgrade_bubble_unlock_name": "新伙伴：泡泡连弹",
        "upgrade_bubble_unlock_desc": "淘气泡泡会在附近怪物之间连续弹跳。",
        "upgrade_bubble_unlock_stat": "新增自动武器 · 连锁弹跳",
        "upgrade_bubble_name": "泡泡连弹",
        "upgrade_bubble_desc": "泡泡连弹升至 {level} 级：伤害更高，弹跳次数更多。",
        "upgrade_bubble_stat": "泡泡伤害 +7 · 连锁数量提升",
        "upgrade_tornado_unlock_name": "新伙伴：口袋龙卷",
        "upgrade_tornado_unlock_desc": "在怪物最密集的位置放下一阵软绵绵的龙卷风。",
        "upgrade_tornado_unlock_stat": "新增自动武器 · 持续领域",
        "upgrade_tornado_name": "口袋龙卷",
        "upgrade_tornado_desc": "口袋龙卷升至 {level} 级：持续更久，卷起的范围更大。",
        "upgrade_tornado_stat": "每跳伤害 +3 · 范围与持续提升",
        "upgrade_starfall_unlock_name": "新伙伴：星光坠击",
        "upgrade_starfall_unlock_desc": "锁定最强壮的怪物，预警后垂直落下一束星光。",
        "upgrade_starfall_unlock_stat": "新增自动武器 · 强敌优先范围伤害",
        "upgrade_starfall_name": "星光坠击",
        "upgrade_starfall_desc": "星光坠击升至 {level} 级：锁定更多强敌，爆闪范围更大。",
        "upgrade_starfall_stat": "星落伤害 +9 · 高等级增加落点",
        "upgrade_aura_unlock_name": "新伙伴：精灵齐射",
        "upgrade_aura_unlock_desc": "小精灵会从肩旁射出一群亮晶晶的追踪弹。",
        "upgrade_aura_unlock_stat": "新增自动武器 · 多目标追踪弹",
        "upgrade_aura_name": "精灵齐射",
        "upgrade_aura_desc": "精灵齐射升至 {level} 级：弹得更快，并会增加精灵弹数量。",
        "upgrade_aura_stat": "单弹伤害 +3 · 高等级增加弹数",
        "upgrade_dagger_unlock_name": "新伙伴：星辉飞刀",
        "upgrade_dagger_unlock_desc": "朝最近的怪群快速扇射多把清晰可见的星光飞刀。",
        "upgrade_dagger_unlock_stat": "新增自动武器 · 高频多发穿透",
        "upgrade_dagger_name": "星辉飞刀",
        "upgrade_dagger_desc": "星辉飞刀升至 {level} 级：飞刀更多、更强，并逐渐获得穿透。",
        "upgrade_dagger_stat": "飞刀伤害 +5 · 3/5/7级增加弹数",
        "upgrade_starwheel_unlock_name": "新伙伴：回旋星轮",
        "upgrade_starwheel_unlock_desc": "向怪群抛出会沿弧线飞回来的月白星轮，去回都能命中。",
        "upgrade_starwheel_unlock_stat": "新增自动武器 · 往返双程命中",
        "upgrade_starwheel_name": "回旋星轮",
        "upgrade_starwheel_desc": "回旋星轮升至 {level} 级：伤害更高，高等级会多抛一枚。",
        "upgrade_starwheel_stat": "星轮伤害 +8 · 4/7级增加数量",
        "upgrade_might_name": "力量糖果",
        "upgrade_might_desc": "所有武器的伤害都会变得更甜、更有劲。",
        "upgrade_might_stat": "全武器伤害 +10%",
        "upgrade_haste_name": "快快时钟",
        "upgrade_haste_desc": "把所有自动武器的休息时间向前拨一点。",
        "upgrade_haste_stat": "全武器冷却 -7%",
        "upgrade_reach_name": "放大贴纸",
        "upgrade_reach_desc": "扩大攻击范围、领域半径和特效尺寸。",
        "upgrade_reach_stat": "攻击尺寸与范围 +8%",
        "upgrade_fortune_name": "幸运四叶草",
        "upgrade_fortune_desc": "幸运一击更常出现，而且会更加闪亮。",
        "upgrade_fortune_stat": "暴击率 +4% · 暴击伤害 +10%",
        "upgrade_growth_name": "成长绘本",
        "upgrade_growth_desc": "每一颗星光碎片都会讲出更多经验故事。",
        "upgrade_growth_stat": "经验获取 +8%",
        "upgrade_snack_name": "星星点心",
        "upgrade_snack_desc": "装备都满级时，吃点点心恢复体力。",
        "upgrade_snack_stat": "恢复 35% 最大生命",
        "upgrade_bonus_name": "闪亮纪念章",
        "upgrade_bonus_desc": "把这次成长换成一枚值钱的冒险纪念章。",
        "upgrade_bonus_stat": "冒险得分 +750",
        "upgrade_spark_name": "微光祝福",
        "upgrade_spark_desc": "让下一段旅程多一点生命和好运。",
        "upgrade_spark_stat": "最大生命 +12 · 暴击率 +1%",
    },
    "en": {
        "tome_title": "WONDER TOMES",
        "moonblade_label": "MOON BLADE",
        "bubble_label": "BUBBLE BOUNCE",
        "tornado_label": "POCKET TWISTER",
        "starfall_label": "STARFALL",
        "aura_label": "WISP VOLLEY",
        "dagger_label": "STAR DAGGERS",
        "starwheel_label": "STAR WHEEL",
        "weapon_level_value": "LV {level}",
        "tome_level_value": "LV {level}",
        "upgrade_moonblade_unlock_name": "NEW FRIEND: MOON BLADE",
        "upgrade_moonblade_unlock_desc": "Sweep a wide crescent through the nearest group.",
        "upgrade_moonblade_unlock_stat": "NEW AUTO WEAPON · PIERCING SWEEP",
        "upgrade_moonblade_name": "MOON BLADE",
        "upgrade_moonblade_desc": "Moon Blade reaches LV {level}: stronger sweeps hit more monsters.",
        "upgrade_moonblade_stat": "SLASH DAMAGE +10 · MORE TARGETS",
        "upgrade_bubble_unlock_name": "NEW FRIEND: BUBBLE BOUNCE",
        "upgrade_bubble_unlock_desc": "Mischievous bubbles bounce between nearby monsters.",
        "upgrade_bubble_unlock_stat": "NEW AUTO WEAPON · CHAIN BOUNCE",
        "upgrade_bubble_name": "BUBBLE BOUNCE",
        "upgrade_bubble_desc": "Bubble Bounce reaches LV {level}: harder hits and more bounces.",
        "upgrade_bubble_stat": "BUBBLE DAMAGE +7 · MORE CHAINS",
        "upgrade_tornado_unlock_name": "NEW FRIEND: POCKET TWISTER",
        "upgrade_tornado_unlock_desc": "Plant a fluffy tornado where monsters are most crowded.",
        "upgrade_tornado_unlock_stat": "NEW AUTO WEAPON · LASTING ZONE",
        "upgrade_tornado_name": "POCKET TWISTER",
        "upgrade_tornado_desc": "Pocket Twister reaches LV {level}: wider and longer lasting.",
        "upgrade_tornado_stat": "TICK DAMAGE +3 · WIDER & LONGER",
        "upgrade_starfall_unlock_name": "NEW FRIEND: STARFALL",
        "upgrade_starfall_unlock_desc": "Mark the toughest monster, then drop a vertical starlight blast.",
        "upgrade_starfall_unlock_stat": "NEW AUTO WEAPON · TOUGHEST-TARGET AREA",
        "upgrade_starfall_name": "STARFALL",
        "upgrade_starfall_desc": "Starfall reaches LV {level}: mark more tough foes with wider blasts.",
        "upgrade_starfall_stat": "STAR DAMAGE +9 · MORE DROPS",
        "upgrade_aura_unlock_name": "NEW FRIEND: WISP VOLLEY",
        "upgrade_aura_unlock_desc": "Tiny wisps launch a sparkling volley at several nearby monsters.",
        "upgrade_aura_unlock_stat": "NEW AUTO WEAPON · MULTI-TARGET HOMING",
        "upgrade_aura_name": "WISP VOLLEY",
        "upgrade_aura_desc": "Wisp Volley reaches LV {level}: faster volleys gain more wisps.",
        "upgrade_aura_stat": "BOLT DAMAGE +3 · MORE BOLTS",
        "upgrade_dagger_unlock_name": "NEW FRIEND: STAR DAGGERS",
        "upgrade_dagger_unlock_desc": "Rapidly fan several bright star daggers through the nearest pack.",
        "upgrade_dagger_unlock_stat": "NEW AUTO WEAPON · RAPID MULTISHOT",
        "upgrade_dagger_name": "STAR DAGGERS",
        "upgrade_dagger_desc": "Star Daggers reaches LV {level}: more and stronger knives gain pierce.",
        "upgrade_dagger_stat": "DAGGER DAMAGE +5 · +SHOT AT LV 3/5/7",
        "upgrade_starwheel_unlock_name": "NEW FRIEND: STAR WHEEL",
        "upgrade_starwheel_unlock_desc": "Throw a moon-white wheel that damages monsters going out and back.",
        "upgrade_starwheel_unlock_stat": "NEW AUTO WEAPON · RETURNING DOUBLE HIT",
        "upgrade_starwheel_name": "STAR WHEEL",
        "upgrade_starwheel_desc": "Star Wheel reaches LV {level}: stronger throws gain extra wheels.",
        "upgrade_starwheel_stat": "WHEEL DAMAGE +8 · +WHEEL AT LV 4/7",
        "upgrade_might_name": "MIGHT CANDY",
        "upgrade_might_desc": "Every weapon becomes a little sweeter and much stronger.",
        "upgrade_might_stat": "ALL WEAPON DAMAGE +10%",
        "upgrade_haste_name": "HURRY CLOCK",
        "upgrade_haste_desc": "Nudge every automatic weapon's rest time forward.",
        "upgrade_haste_stat": "ALL WEAPON COOLDOWNS -7%",
        "upgrade_reach_name": "BIG STICKER",
        "upgrade_reach_desc": "Grow attack reach, zone radius, and effect size.",
        "upgrade_reach_stat": "ATTACK SIZE & RANGE +8%",
        "upgrade_fortune_name": "LUCKY CLOVER",
        "upgrade_fortune_desc": "Lucky hits happen more often and sparkle much harder.",
        "upgrade_fortune_stat": "CRIT +4% · CRIT DAMAGE +10%",
        "upgrade_growth_name": "GROWTH STORYBOOK",
        "upgrade_growth_desc": "Every star shard tells a little more experience story.",
        "upgrade_growth_stat": "EXPERIENCE GAIN +8%",
        "upgrade_snack_name": "STAR SNACK",
        "upgrade_snack_desc": "When the backpack is complete, enjoy a healing snack.",
        "upgrade_snack_stat": "RESTORE 35% MAX HEALTH",
        "upgrade_bonus_name": "SHINY MEDAL",
        "upgrade_bonus_desc": "Trade this growth gift for a valuable adventure keepsake.",
        "upgrade_bonus_stat": "ADVENTURE SCORE +750",
        "upgrade_spark_name": "WISP BLESSING",
        "upgrade_spark_desc": "Add a little vitality and luck to the road ahead.",
        "upgrade_spark_stat": "MAX HEALTH +12 · CRIT +1%",
    },
}

CONTENT_TEXT["zh_cn"].update({
    "character_select_title": "选择本次冒险伙伴",
    "character_unlocked": "已解锁",
    "character_locked": "尚未解锁",
    "character_starpaw_name": "星爪猫",
    "character_starpaw_passive": "幸运星：暴击率 +5%，移动速度 +8%",
    "character_peachy_name": "桃桃团",
    "character_peachy_passive": "软糖心：最大生命 +35，拾取范围 +25%",
    "character_peachy_unlock": "单局存活 2 分钟",
    "character_mossling_name": "苔苔球",
    "character_mossling_passive": "风之叶：攻击冷却 -12%，移动速度 +12%",
    "character_mossling_unlock": "累计击败 750 只怪物",
    "character_snowbean_name": "雪豆豆",
    "character_snowbean_passive": "雪球体质：武器尺寸 +18%，伤害 +12%",
    "character_snowbean_unlock": "击败任意 Boss",
    "character_azura_name": "小苍蓝",
    "character_azura_passive": "彗星之子：额外 +1 发射物，弹速 +20%",
    "character_azura_unlock": "单局达到 20 级",
    "character_unlock_banner": "新伙伴已经加入星光队伍！",
    "upgrade_thunder_unlock_name": "新伙伴：闪电糖果",
    "upgrade_thunder_unlock_desc": "召来一束会自动追踪附近怪物的亮晶晶雷霆。",
    "upgrade_thunder_unlock_stat": "新增自动武器 · 连锁落雷",
    "petalstorm_label": "花瓣星爆",
    "comet_label": "彗星合唱",
    "upgrade_petalstorm_unlock_name": "新伙伴：花瓣星爆",
    "upgrade_petalstorm_unlock_desc": "向四周同时绽放一整圈立体星瓣。",
    "upgrade_petalstorm_unlock_stat": "新增自动武器 · 环形弹幕",
    "upgrade_petalstorm_name": "花瓣星爆",
    "upgrade_petalstorm_desc": "花瓣星爆升至 {level} 级：星瓣更多、更强、更密。",
    "upgrade_petalstorm_stat": "伤害 +6 · 高等级增加一整圈星瓣",
    "upgrade_comet_unlock_name": "新伙伴：彗星合唱",
    "upgrade_comet_unlock_desc": "一群有立体星核的小彗星会分头追逐怪物。",
    "upgrade_comet_unlock_stat": "新增自动武器 · 多目标追踪",
    "upgrade_comet_name": "彗星合唱",
    "upgrade_comet_desc": "彗星合唱升至 {level} 级：齐射更多，飞行更快。",
    "upgrade_comet_stat": "伤害 +7 · 3/5/7/10 级增加彗星",
    "upgrade_quantity_name": "万花齐发书",
    "upgrade_quantity_desc": "每次施法都多送出一份礼物，让弹幕真正铺满夜空。",
    "upgrade_quantity_stat": "适用武器每次攻击 +1 发射物",
    "upgrade_velocity_name": "疾星飞行书",
    "upgrade_velocity_desc": "星弹飞得更快，轨迹更利落，也更快空出对象池。",
    "upgrade_velocity_stat": "发射物速度 +15%",
    "upgrade_duration_name": "长夜沙漏书",
    "upgrade_duration_desc": "延长龙卷、光环、回旋武器与领域特效的持续时间。",
    "upgrade_duration_stat": "持续时间 +15%",
})

CONTENT_TEXT["en"].update({
    "character_select_title": "CHOOSE YOUR STAR FRIEND",
    "character_unlocked": "UNLOCKED",
    "character_locked": "LOCKED",
    "character_starpaw_name": "STARPAW",
    "character_starpaw_passive": "Lucky Star: +5% crit, +8% move speed",
    "character_peachy_name": "PEACHY",
    "character_peachy_passive": "Gummy Heart: +35 max HP, +25% pickup range",
    "character_peachy_unlock": "Survive 2 minutes in one run",
    "character_mossling_name": "MOSSLING",
    "character_mossling_passive": "Wind Leaf: -12% cooldown, +12% move speed",
    "character_mossling_unlock": "Defeat 750 monsters total",
    "character_snowbean_name": "SNOWBEAN",
    "character_snowbean_passive": "Snowball: +18% weapon size, +12% damage",
    "character_snowbean_unlock": "Defeat any boss",
    "character_azura_name": "AZURA",
    "character_azura_passive": "Comet Child: +1 projectile, +20% projectile speed",
    "character_azura_unlock": "Reach level 20 in one run",
    "character_unlock_banner": "A NEW STAR FRIEND JOINED!",
    "upgrade_thunder_unlock_name": "NEW FRIEND: THUNDER CANDY",
    "upgrade_thunder_unlock_desc": "Call down a sparkling bolt that seeks nearby monsters.",
    "upgrade_thunder_unlock_stat": "NEW AUTO WEAPON · CHAIN LIGHTNING",
    "petalstorm_label": "PETAL NOVA",
    "comet_label": "COMET CHOIR",
    "upgrade_petalstorm_unlock_name": "NEW FRIEND: PETAL NOVA",
    "upgrade_petalstorm_unlock_desc": "Bloom a full ring of chunky 3D star petals.",
    "upgrade_petalstorm_unlock_stat": "NEW AUTO WEAPON · RADIAL BARRAGE",
    "upgrade_petalstorm_name": "PETAL NOVA",
    "upgrade_petalstorm_desc": "Petal Nova reaches LV {level}: denser, stronger rings.",
    "upgrade_petalstorm_stat": "DAMAGE +6 · MORE PETALS AT HIGH LEVEL",
    "upgrade_comet_unlock_name": "NEW FRIEND: COMET CHOIR",
    "upgrade_comet_unlock_desc": "A choir of 3D-cored comets splits between nearby monsters.",
    "upgrade_comet_unlock_stat": "NEW AUTO WEAPON · MULTI-TARGET HOMING",
    "upgrade_comet_name": "COMET CHOIR",
    "upgrade_comet_desc": "Comet Choir reaches LV {level}: faster and larger volleys.",
    "upgrade_comet_stat": "DAMAGE +7 · +COMET AT LV 3/5/7/10",
    "upgrade_quantity_name": "BLOSSOM BARRAGE TOME",
    "upgrade_quantity_desc": "Every cast sends one more gift until the night fills with stars.",
    "upgrade_quantity_stat": "+1 PROJECTILE TO SUPPORTED WEAPONS",
    "upgrade_velocity_name": "SWIFT STAR TOME",
    "upgrade_velocity_desc": "Projectiles fly faster, read cleaner, and free pooled visuals sooner.",
    "upgrade_velocity_stat": "PROJECTILE SPEED +15%",
    "upgrade_duration_name": "LONG NIGHT TOME",
    "upgrade_duration_desc": "Tornadoes, auras, returning weapons, and zones linger longer.",
    "upgrade_duration_stat": "EFFECT DURATION +15%",
})


# Catalog v2 is the authoritative content source.  The compatibility views
# below preserve the small field surface used by the existing HUD and weapon
# handlers while new systems consume the complete definitions directly.
from SurvivorCatalog import (
    CHARACTERS as _CATALOG_CHARACTERS,
    EVOLUTIONS,
    TOMES as _CATALOG_TOMES,
    TRINKETS,
    WEAPONS as _CATALOG_WEAPONS,
    validate_catalog,
)


CHARACTER_ORDER = tuple(entry["id"] for entry in _CATALOG_CHARACTERS)
CHARACTER_DEFS = {}
for _entry in _CATALOG_CHARACTERS:
    _id = _entry["id"]
    _name_key = "character_" + _id + "_name"
    _passive_key = "character_" + _id + "_passive"
    _unlock_key = "character_" + _id + "_unlock"
    CHARACTER_DEFS[_id] = {
        "name_key": _name_key,
        "passive_key": _passive_key,
        "unlock_key": _unlock_key,
        "badge": _entry["name"]["en"][0].upper(),
        "mesh": _entry["mesh"],
        "controller": _entry["controller"],
        "idle": _entry["idle"],
        "dance": _entry["dance"],
        "scale": _entry["scale"],
        "weapon": _entry["starterWeapon"],
        "modifiers": _entry["modifiers"],
        "hooks": _entry["hooks"],
        "price": _entry["price"],
        "unlock_id": _entry["unlockId"],
        "icon": _entry["icon"],
        "preview": _entry["preview"],
    }
    for _language in ("zh_cn", "en"):
        _localized_text = CONTENT_TEXT[_language]
        _localized_text.setdefault(_name_key, _entry["name"][_language])
        _localized_text.setdefault(_passive_key, _entry["description"][_language])
        _localized_text.setdefault(
            _unlock_key,
            "任务达成后可购买"
            if _language == "zh_cn" else
            "Complete its quest to purchase",
        )


WEAPON_ORDER = tuple(entry["id"] for entry in _CATALOG_WEAPONS)
WEAPON_DEFS = {}
for _entry in _CATALOG_WEAPONS:
    _id = _entry["id"]
    _name_key = _id + "_label"
    _unlock_name_key = "upgrade_" + _id + "_unlock_name"
    _unlock_desc_key = "upgrade_" + _id + "_unlock_desc"
    _unlock_stat_key = "upgrade_" + _id + "_unlock_stat"
    _upgrade_name_key = "upgrade_" + _id + "_name"
    _upgrade_desc_key = "upgrade_" + _id + "_desc"
    _upgrade_stat_key = "upgrade_" + _id + "_stat"
    WEAPON_DEFS[_id] = dict(_entry)
    WEAPON_DEFS[_id].update({
        "start_level": 0,
        "max_level": _entry["maxLevel"],
        "name_key": _name_key,
        "effect": _entry["bodyVfx"],
        "unlock_name_key": _unlock_name_key,
        "unlock_desc_key": _unlock_desc_key,
        "unlock_stat_key": _unlock_stat_key,
        "upgrade_name_key": _upgrade_name_key,
        "upgrade_desc_key": _upgrade_desc_key,
        "upgrade_stat_key": _upgrade_stat_key,
    })
    for _language in ("zh_cn", "en"):
        _name = _entry["name"][_language]
        _description = _entry["description"][_language]
        _localized_text = CONTENT_TEXT[_language]
        _localized_text.setdefault(_name_key, _name)
        _localized_text.setdefault(
            _unlock_name_key,
            ("新伙伴：" if _language == "zh_cn" else "NEW FRIEND: ") + _name,
        )
        _localized_text.setdefault(_unlock_desc_key, _description)
        _localized_text.setdefault(
            _unlock_stat_key,
            "新自动武器 · 1 级"
            if _language == "zh_cn" else
            "NEW AUTO WEAPON · LV 1",
        )
        _localized_text.setdefault(_upgrade_name_key, _name)
        _localized_text.setdefault(
            _upgrade_desc_key,
            _description + (
                "  {level} 级" if _language == "zh_cn" else "  LV {level}"
            ),
        )
        _localized_text.setdefault(
            _upgrade_stat_key,
            "成长节点强化" if _language == "zh_cn" else "MILESTONE UPGRADE",
        )


TOME_ORDER = tuple(entry["id"] for entry in _CATALOG_TOMES)
TOME_DEFS = {}
for _entry in _CATALOG_TOMES:
    _id = _entry["id"]
    _name_key = "upgrade_" + _id + "_name"
    _description_key = "upgrade_" + _id + "_desc"
    _stat_key = "upgrade_" + _id + "_stat"
    TOME_DEFS[_id] = dict(_entry)
    TOME_DEFS[_id].update({
        "max_level": _entry["maxLevel"],
        "name_key": _name_key,
        "description_key": _description_key,
        "stat_key": _stat_key,
    })
    for _language in ("zh_cn", "en"):
        _localized_text = CONTENT_TEXT[_language]
        _localized_text.setdefault(_name_key, _entry["name"][_language])
        _localized_text.setdefault(
            _description_key, _entry["description"][_language],
        )
        _localized_text.setdefault(_stat_key, _entry["statText"][_language])


TRINKET_ORDER = tuple(entry["id"] for entry in TRINKETS)
EVOLUTION_ORDER = tuple(entry["id"] for entry in EVOLUTIONS)
