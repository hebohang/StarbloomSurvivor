"""Data-bound Hub pages and isolated menu character preview."""

import math

import HEngine
import SurvivorEconomy
import SurvivorProfile
import SurvivorHubNavigation
import SurvivorMetaProgression
import SurvivorRules

from SurvivorCatalogCharacters import CHARACTERS, CHARACTER_BY_ID
from SurvivorCatalogItems import EVOLUTIONS, TOMES, TRINKETS, WEAPONS
from SurvivorCatalogMeta import POWER_UPS, PRODUCTS, QUESTS
from SurvivorCatalogWorld import BOSSES, CHALLENGES, DIFFICULTIES, ENEMIES
from SurvivorRuntimeAssets import asset_path


RmlUI = HEngine.RmlUI

HUB_PAGES = (
    "play", "characters", "armory", "shop", "quests", "collection", "settings",
)
ARMORY_DATA = {
    "weapons": WEAPONS,
    "tomes": TOMES,
    "trinkets": TRINKETS,
    "evolutions": EVOLUTIONS,
}
PRODUCT_BY_KEY = {
    (product["category"], product["contentId"]): product
    for product in PRODUCTS
}
DIFFICULTY_BY_ID = {entry["id"]: entry for entry in DIFFICULTIES}
CHALLENGE_BY_ID = {entry["id"]: entry for entry in CHALLENGES}
POWER_UP_BY_ID = {entry["id"]: entry for entry in POWER_UPS}
CONTENT_NAME_BY_ID = {
    entry["id"]: entry["name"]
    for entry in tuple(WEAPONS) + tuple(TOMES) + tuple(TRINKETS) + tuple(EVOLUTIONS)
}

HUB_TEXT = {
    "zh_cn": {
        "nav_play": "开始冒险", "nav_characters": "伙伴", "nav_armory": "军械库",
        "nav_shop": "星光成长", "nav_quests": "星愿任务",
        "nav_collection": "图鉴统计", "nav_settings": "设置",
        "wallet": "星币", "completion": "完成度", "difficulty": "难度",
        "state_hidden": "隐藏", "state_locked": "未达成资格",
        "state_eligible": "可购买", "state_owned": "已拥有", "state_selected": "使用中",
        "price": "价格 {value}", "free": "已开放", "use": "使用", "using": "正在使用",
        "purchase": "购买", "training": "训练 {level}/5 · {price}", "training_max": "训练已满",
        "training_toggle": "训练：{state}",
        "mastery": "熟练度 {level} 级 · {xp} 经验", "mastery_level": "等级 {level}",
        "dance": "打个招呼",
        "preview_hint": "A/D 或 ←/→ 旋转 · 按钮缩放 · 2.5 秒后恢复自动旋转",
        "armory_weapons": "武器", "armory_tomes": "绘本", "armory_trinkets": "奇物",
        "armory_evolutions": "进化", "state_sealed": "已封印",
        "pool_enabled": "从成长池封印", "pool_disabled": "解除封印",
        "pool_unavailable": "此内容不可封印",
        "pool_starter_protected": "当前伙伴的起始武器不可封印",
        "pool_minimum": "至少保留 {count} 项可用内容",
        "pool_hint": "封印只会让内容不再出现在下一局的随机成长中，不会失去已拥有内容。",
        "pool_locked_hint": "完成“二十颗星愿”任务后，可从下一局的随机成长池中封印内容。",
        "pool_unseal_all": "全部解除封印", "pool_sealed_count": "已封印 {count}",
        "page": "第 {page}/{pages} 页", "shop_buy": "购买下一级 · {price}",
        "shop_max": "已满级", "shop_enabled": "已启用", "shop_disabled": "已停用",
        "shop_generic_description": "永久强化，可在冒险前启用或停用。",
        "shop_refund": "全部强化 100% 退款", "quest_track": "追踪任务",
        "quest_untrack": "取消追踪", "quest_track_full": "追踪栏已满（最多 3 条）",
        "quest_completed": "已完成", "quest_progress": "{value}/{target}",
        "collection_summary": "伙伴 {characters}/10 · 武器 {weapons}/18 · 绘本 {tomes}/16 · 奇物 {trinkets}/12",
        "career_summary": "冒险 {runs} 次 · 胜利 {wins} 次 · 击杀 {kills} · 首领 {bosses}",
        "evolution_hint": "未发现配方：剪影会保留武器与绘本线索",
        "play_character": "当前伙伴：{name}", "play_reward": "金币倍率 ×{value}",
        "weapon_slots_summary": "已购上限 {purchased} 槽 · 本局计划 {selected} 槽",
        "weapon_slot_option": "{count} 槽 · 结算金币 +{bonus}%",
        "weapon_slot_locked": "{count} 槽 · 需要{difficulty}首通",
        "shop_requires_clear": "购买下一级需要先完成{difficulty}首通。",
        "shop_ready": "交易保存后才会更新余额。",
        "region_star": "星", "region_thunder": "雷", "region_water": "水", "region_wind": "风",
        "result_none": "—", "result_seconds": "{value} 秒",
        "difficulty_reward": "奖励 ×{value}",
        "difficulty_reward_locked": "未解锁 · 奖励 ×{value}",
        "difficulty_adventure": "冒险", "difficulty_fierce": "凶猛", "difficulty_nightmare": "噩梦",
        "challenge_none": "无挑战", "challenge_swarm": "虫潮", "challenge_chonk": "巨体",
        "challenge_fragile_star": "脆弱星", "challenge_hurry": "加速",
        "challenge_no_trinkets": "禁用奇物", "challenge_cursed_bloom": "诅咒花潮",
        "tracked_empty": "选择任务并追踪", "result_gold": "本局金币 {earned} · 钱包 {wallet}",
        "result_survival": "存活 {time} · Boss {bosses} · 最高等级 {level}",
        "settings_projectile": "玩家弹体透明度 {value}%", "settings_particle": "粒子密度 {value}",
        "settings_numbers": "伤害数字 {value}", "settings_shake": "屏幕震动 {value}",
        "settings_telegraph": "敌方预警配色 {value}", "settings_throttle": "自动视觉降档 {value}",
        "on": "开", "off": "关", "auto": "自动", "low": "低", "medium": "中", "high": "高",
        "reduced": "精简", "full": "完整", "default": "默认", "deuteranopia": "红绿色弱",
        "empty_content": "当前筛选没有内容。", "empty_quests": "当前筛选没有任务。",
        "unlock_character": "伙伴：{name}", "unlock_weapon": "武器：{name}",
        "unlock_tome": "绘本：{name}", "unlock_trinket": "奇物：{name}",
        "unlock_difficulty": "难度：{name}", "unlock_system": "系统功能：{name}",
    },
    "en": {
        "nav_play": "Play", "nav_characters": "Characters", "nav_armory": "Armory",
        "nav_shop": "Star Shop", "nav_quests": "Quests",
        "nav_collection": "Collection & Stats", "nav_settings": "Settings",
        "wallet": "Gold", "completion": "Completion", "difficulty": "Difficulty",
        "state_hidden": "Hidden", "state_locked": "Not Eligible",
        "state_eligible": "Eligible", "state_owned": "Owned", "state_selected": "Selected",
        "price": "Price {value}", "free": "Available", "use": "Use", "using": "In Use",
        "purchase": "Purchase", "training": "Training {level}/5 · {price}", "training_max": "Training Maxed",
        "training_toggle": "Training: {state}",
        "mastery": "Mastery Lv.{level} · {xp} XP", "mastery_level": "LV {level}",
        "dance": "Say Hello",
        "preview_hint": "A/D or ←/→ rotate · buttons zoom · auto rotate resumes after 2.5s",
        "armory_weapons": "Weapons", "armory_tomes": "Tomes", "armory_trinkets": "Trinkets",
        "armory_evolutions": "Evolutions", "state_sealed": "Sealed",
        "pool_enabled": "Seal from Upgrade Pool", "pool_disabled": "Unseal",
        "pool_unavailable": "This content cannot be sealed",
        "pool_starter_protected": "The current partner's starter weapon cannot be sealed",
        "pool_minimum": "Keep at least {count} available items",
        "pool_hint": "Sealing only removes content from random upgrades in the next run; owned content is never lost.",
        "pool_locked_hint": "Complete Twenty Wishes to seal content from the next run's random upgrade pool.",
        "pool_unseal_all": "Unseal All", "pool_sealed_count": "SEALED {count}",
        "page": "Page {page}/{pages}", "shop_buy": "Buy Next · {price}",
        "shop_max": "Max Level", "shop_enabled": "Enabled", "shop_disabled": "Disabled",
        "shop_generic_description": "A permanent upgrade that can be enabled or disabled before a run.",
        "shop_refund": "Refund All PowerUps 100%", "quest_track": "Track Quest",
        "quest_untrack": "Untrack", "quest_track_full": "Tracker full (maximum 3)",
        "quest_completed": "Completed", "quest_progress": "{value}/{target}",
        "collection_summary": "Characters {characters}/10 · Weapons {weapons}/18 · Tomes {tomes}/16 · Trinkets {trinkets}/12",
        "career_summary": "Runs {runs} · Wins {wins} · Kills {kills} · Bosses {bosses}",
        "evolution_hint": "Undiscovered recipes retain weapon and Tome clues as silhouettes.",
        "play_character": "Current Friend: {name}", "play_reward": "Gold Reward ×{value}",
        "weapon_slots_summary": "Purchased cap {purchased} · Planned for this run {selected}",
        "weapon_slot_option": "{count} slots · +{bonus}% result gold",
        "weapon_slot_locked": "{count} slots · Clear {difficulty} first",
        "shop_requires_clear": "Clear {difficulty} before purchasing the next level.",
        "shop_ready": "Your balance updates after the transaction is saved.",
        "region_star": "Star", "region_thunder": "Thunder", "region_water": "Water", "region_wind": "Wind",
        "result_none": "—", "result_seconds": "{value}s",
        "difficulty_reward": "Reward ×{value}",
        "difficulty_reward_locked": "Locked · Reward ×{value}",
        "difficulty_adventure": "Adventure", "difficulty_fierce": "Fierce", "difficulty_nightmare": "Nightmare",
        "challenge_none": "No Challenge", "challenge_swarm": "Swarm", "challenge_chonk": "Chonk",
        "challenge_fragile_star": "Fragile Star", "challenge_hurry": "Hurry",
        "challenge_no_trinkets": "No Trinkets", "challenge_cursed_bloom": "Cursed Bloom",
        "tracked_empty": "Select and track a quest", "result_gold": "Run Gold {earned} · Wallet {wallet}",
        "result_survival": "Survived {time} · Bosses {bosses} · Level {level}",
        "settings_projectile": "Player Projectile Opacity {value}%", "settings_particle": "Particle Density {value}",
        "settings_numbers": "Damage Numbers {value}", "settings_shake": "Screen Shake {value}",
        "settings_telegraph": "Enemy Telegraph Color {value}", "settings_throttle": "Auto Visual Throttle {value}",
        "on": "On", "off": "Off", "auto": "Auto", "low": "Low", "medium": "Medium", "high": "High",
        "reduced": "Reduced", "full": "Full", "default": "Default", "deuteranopia": "Deuteranopia",
        "empty_content": "No content matches this filter.", "empty_quests": "No quests match this filter.",
        "unlock_character": "Character: {name}", "unlock_weapon": "Weapon: {name}",
        "unlock_tome": "Tome: {name}", "unlock_trinket": "Trinket: {name}",
        "unlock_difficulty": "Difficulty: {name}", "unlock_system": "Feature: {name}",
    },
}

COLLECTION_ROLE_TEXT = {
    "zh_cn": {
        "chaser": "追击", "flanker": "侧袭", "armored": "重甲", "bruiser": "重击",
        "zone": "控场", "charger": "冲锋", "ranged": "远程", "lobber": "投掷",
        "ghost": "伏击", "shield": "盾卫", "suicide": "爆破", "summoner": "召唤",
        "boss_yeti": "冰霜首领", "boss_orc": "重击首领", "boss_demon": "符文首领",
        "boss_mushroom": "孢子首领", "boss_dragon": "星焰首领",
    },
    "en": {
        "chaser": "Chaser", "flanker": "Flanker", "armored": "Armored", "bruiser": "Bruiser",
        "zone": "Zoner", "charger": "Charger", "ranged": "Ranged", "lobber": "Lobber",
        "ghost": "Ambusher", "shield": "Guard", "suicide": "Bomber", "summoner": "Summoner",
        "boss_yeti": "Frost Boss", "boss_orc": "Bruiser Boss", "boss_demon": "Rune Boss",
        "boss_mushroom": "Spore Boss", "boss_dragon": "Starfire Boss",
    },
}

SYSTEM_UNLOCK_TEXT = {
    "zh_cn": {
        "reroll": "重抽次数", "skip": "跳过次数", "banish": "放逐次数",
        "pool_toggle": "成长池封印", "challenge_marks": "挑战印记",
    },
    "en": {
        "reroll": "Rerolls", "skip": "Skips", "banish": "Banishes",
        "pool_toggle": "Upgrade Pool Sealing", "challenge_marks": "Challenge Marks",
    },
}

RESULT_TEXT = {
    "zh_cn": {
        "result_reason": "结束原因：{reason}",
        "reason_death": "失败", "reason_defeat": "失败", "reason_victory": "胜利",
        "reason_abandon": "主动结束", "reason_restart": "重新开始",
        "commit_saved": "奖励已保存", "commit_failed": "保存失败，可以重试",
        "result_commit_retry_button_label": "重试",
        "final_time_label": "存活时间", "final_elites_label": "精英",
        "final_bosses_label": "首领", "result_gold_section_label": "金币结算",
        "result_gold_time_label": "存活时间", "result_gold_kills_label": "击杀",
        "result_gold_elite_boss_label": "精英与首领",
        "result_gold_clear_difficulty_label": "通关与难度",
        "result_weapon_slot_limit_label": "普通武器槽",
        "result_weapon_slot_bonus_label": "低槽位奖励",
        "result_gold_quests_label": "任务奖励（不参与倍率）",
        "result_survival_section_label": "生存记录",
        "result_damage_taken_label": "承受伤害",
        "result_damage_prevented_label": "阻止伤害", "result_healing_label": "治疗",
        "result_distance_moved_label": "移动距离", "distance_unit": "米",
        "result_region_order_label": "区域激活顺序",
        "result_objective_section_label": "四域与终局",
        "result_region_attempts_label": "区域尝试次数",
        "result_region_exits_label": "离圈失败次数",
        "result_domain_summary_label": "区域权能贡献",
        "result_boss_ttk_label": "最终首领用时",
        "result_weapon_section_label": "武器表现",
        "result_weapon_columns_label": "伤害 / 每秒伤害 / 命中 / 暴击 / 击杀 / 等级",
        "result_weapon_name_label": "武器", "result_weapon_damage_label": "伤害",
        "result_weapon_dps_label": "每秒", "result_weapon_hits_label": "命中",
        "result_weapon_crits_label": "暴击", "result_weapon_kills_label": "击杀",
        "result_weapon_level_label": "等级 / 进化",
        "result_quests_section_label": "任务与新资格",
        "result_quest_progress": "本局没有新的任务进度",
        "result_first_completion": "首次通关：—", "result_new_eligible": "新购买资格：—",
        "result_adjust_build_button_label": "调整构筑",
    },
    "en": {
        "result_reason": "END REASON: {reason}",
        "reason_death": "DEFEAT", "reason_defeat": "DEFEAT", "reason_victory": "VICTORY",
        "reason_abandon": "ENDED EARLY", "reason_restart": "RESTARTED",
        "commit_saved": "REWARDS SAVED", "commit_failed": "SAVE FAILED — RETRY AVAILABLE",
        "result_commit_retry_button_label": "RETRY",
        "final_time_label": "SURVIVAL", "final_elites_label": "ELITES",
        "final_bosses_label": "BOSSES", "result_gold_section_label": "GOLD BREAKDOWN",
        "result_gold_time_label": "Survival", "result_gold_kills_label": "Kills",
        "result_gold_elite_boss_label": "Elites & Bosses",
        "result_gold_clear_difficulty_label": "Clear & Difficulty",
        "result_weapon_slot_limit_label": "Regular Weapon Slots",
        "result_weapon_slot_bonus_label": "Low-Slot Bonus",
        "result_gold_quests_label": "Quest Rewards (not multiplied)",
        "result_survival_section_label": "SURVIVAL RECORD",
        "result_damage_taken_label": "Damage Taken",
        "result_damage_prevented_label": "Damage Prevented", "result_healing_label": "Healing",
        "result_distance_moved_label": "Distance Moved", "distance_unit": "m",
        "result_region_order_label": "Region Activation Order",
        "result_objective_section_label": "REGIONS & FINALE",
        "result_region_attempts_label": "Region Attempts",
        "result_region_exits_label": "Ring Exit Failures",
        "result_domain_summary_label": "Domain Power Contribution",
        "result_boss_ttk_label": "Final Boss TTK",
        "result_weapon_section_label": "WEAPON PERFORMANCE",
        "result_weapon_columns_label": "DAMAGE / DPS / HIT / CRIT / KILL / LEVEL",
        "result_weapon_name_label": "Weapon", "result_weapon_damage_label": "Damage",
        "result_weapon_dps_label": "DPS", "result_weapon_hits_label": "Hits",
        "result_weapon_crits_label": "Crits", "result_weapon_kills_label": "Kills",
        "result_weapon_level_label": "Level / Evolution",
        "result_quests_section_label": "QUESTS & UNLOCKS",
        "result_quest_progress": "No new quest progress this run",
        "result_first_completion": "FIRST CLEAR: —", "result_new_eligible": "NEW ELIGIBLE: —",
        "result_adjust_build_button_label": "ADJUST BUILD",
    },
}

HUB_STATIC_TEXT = {
    "zh_cn": {
        "start_eyebrow": "软绵绵的星光冒险",
        "start_title": "小树保卫者",
        "hub_wallet_label": "星币", "hub_completion_label": "完成度",
        "hub_difficulty_label": "当前难度",
        "hub_nav_play_label": "开始冒险", "hub_nav_characters_label": "伙伴",
        "hub_nav_armory_label": "军械库", "hub_nav_shop_label": "星光成长",
        "hub_nav_quests_label": "星愿任务", "hub_nav_collection_label": "图鉴统计",
        "hub_nav_settings_label": "设置",
        "play_page_eyebrow": "开始冒险", "play_page_title": "今晚的星光旅程",
        "play_character_label": "当前伙伴", "play_change_character_label": "更换伙伴",
        "play_difficulty_label": "难度", "play_challenges_label": "挑战",
        "play_weapon_slots_label": "普通武器槽位",
        "difficulty_adventure_title": "冒险", "difficulty_fierce_title": "凶猛",
        "difficulty_nightmare_title": "噩梦",
        "difficulty_adventure_subtitle": "奖励 ×1.00",
        "difficulty_fierce_subtitle": "奖励 ×1.35",
        "difficulty_nightmare_subtitle": "未解锁 · 奖励 ×1.75",
        "play_seed_label": "本局种子", "play_seed_button_label": "重新生成",
        "start_button_label": "开始冒险",
        "start_subtitle": "净化四域 · 中央召唤 · 击败星外巨龙",
        "start_hint": "方向键或手柄切换选项，确认后开始冒险。",
        "characters_page_eyebrow": "伙伴", "character_select_title": "选择本次冒险伙伴",
        "character_preview_label": "预览伙伴", "character_weapon_label": "起始武器",
        "character_state_label": "状态", "character_price_label": "价格",
        "character_training_label": "训练", "character_mastery_label": "熟练度",
        "character_preview_idle_label": "待机", "character_preview_dance_label": "跳舞",
        "character_preview_loading": "正在载入伙伴预览",
        "character_preview_error": "伙伴预览暂时不可用",
        "training_stat_0": "力量", "training_stat_1": "生命", "training_stat_2": "急速",
        "training_stat_3": "速度", "training_stat_4": "幸运",
        "armory_page_eyebrow": "军械库", "armory_page_title": "整理本局成长池",
        "armory_filter_all_label": "全部", "armory_filter_owned_label": "已拥有",
        "armory_filter_eligible_label": "可购买", "armory_filter_locked_label": "未解锁",
        "armory_filter_disabled_label": "已封印", "armory_selected_label": "当前内容",
        "armory_state_label": "状态", "armory_price_label": "价格",
        "armory_evolution_label": "进化线索",
        "shop_page_eyebrow": "星光成长", "shop_page_title": "永久强化",
        "shop_refund_all_label": "全部退款", "shop_powerup_label": "强化详情",
        "shop_current_label": "当前", "shop_next_label": "下一级", "shop_price_label": "价格",
        "shop_refund_label": "退还此项", "shop_transaction_status": "交易保存后才会更新余额。",
        "quests_page_eyebrow": "星愿任务", "quests_page_title": "完成任务，开放新星光",
        "quest_filter_all_label": "全部", "quest_filter_character_label": "伙伴",
        "quest_filter_combat_label": "战斗", "quest_filter_mastery_label": "熟练",
        "quest_filter_untracked_label": "未追踪", "quest_detail_label": "任务详情",
        "quest_reward_label": "奖励", "quest_unlock_label": "解锁",
        "collection_page_eyebrow": "图鉴统计", "collection_page_title": "记录每一次相遇与成长",
        "collection_tab_enemies_label": "敌人", "collection_tab_bosses_label": "首领",
        "collection_tab_evolutions_label": "进化", "collection_tab_characters_label": "伙伴",
        "collection_tab_stats_label": "历史统计", "collection_runs_label": "冒险次数",
        "collection_best_time_label": "最佳时间", "collection_kills_label": "总击杀",
        "collection_top_weapon_label": "最佳武器",
        "settings_page_eyebrow": "设置", "settings_page_title": "舒适、清楚地看见每一道星光",
        "hub_language_label": "语言", "hub_language_desc": "选择菜单与冒险中的文字语言",
        "hub_language_zh_label": "中文", "hub_language_en_label": "英文",
        "hub_volume_label": "主音量", "hub_volume_desc": "控制所有游戏声音",
        "hub_vsync_label": "垂直同步", "hub_vsync_desc": "减少画面撕裂",
        "hub_display_label": "显示模式", "hub_display_desc": "选择全屏或窗口模式",
        "hub_ui_scale_label": "界面大小", "hub_ui_scale_desc": "调整所有界面与菜单",
        "hub_motion_label": "界面动效", "hub_motion_desc": "按钮与页面的柔和动画",
        "hub_flash_label": "受伤闪光", "hub_flash_desc": "受到伤害时显示提示",
        "hub_projectile_opacity_label": "玩家弹体透明度",
        "hub_projectile_opacity_desc": "保留核心弹体与敌方预警清晰度",
        "hub_particle_density_label": "粒子密度", "hub_particle_density_desc": "调节装饰粒子数量",
        "hub_damage_numbers_label": "伤害数字", "hub_damage_numbers_desc": "减少高压战斗的视觉噪声",
        "hub_screen_shake_label": "屏幕震动", "hub_screen_shake_desc": "关闭后仍保留危险方向提示",
        "hub_telegraph_color_label": "敌方预警颜色",
        "hub_telegraph_color_desc": "选择高对比或色觉辅助方案",
        "hub_auto_throttle_label": "自动视觉降档",
        "hub_auto_throttle_desc": "高负载时优先减少装饰效果",
        "hub_display_fullscreen_label": "全屏", "hub_display_windowed_label": "窗口化",
        "hub_ui_scale_small_label": "小", "hub_ui_scale_normal_label": "标准",
        "hub_ui_scale_large_label": "大", "hub_particle_density_auto_label": "自动",
        "hub_particle_density_low_label": "低", "hub_particle_density_medium_label": "中",
        "hub_particle_density_high_label": "高", "hub_damage_numbers_off_label": "关闭",
        "hub_damage_numbers_reduced_label": "精简", "hub_damage_numbers_full_label": "完整",
        "hub_telegraph_default_label": "默认", "hub_telegraph_deuteranopia_label": "红绿色弱",
        "hub_telegraph_tritanopia_label": "蓝黄色弱", "hub_telegraph_high_contrast_label": "高对比",
        "hub_vsync_on_label": "开启", "hub_vsync_off_label": "关闭",
        "hub_motion_on_label": "开启", "hub_motion_off_label": "关闭",
        "hub_flash_on_label": "开启", "hub_flash_off_label": "关闭",
        "hub_screen_shake_on_label": "开启", "hub_screen_shake_off_label": "关闭",
        "hub_auto_throttle_on_label": "开启", "hub_auto_throttle_off_label": "关闭",
        "hub_settings_defaults_label": "恢复默认设置",
        "hub_settings_saved_hint": "更改自动保存",
        "activity_tracked_label": "追踪任务", "recent_unlock_label": "最近解锁",
        "recent_unlock_name": "还没有新解锁", "recent_unlock_hint": "继续冒险，新的星光会在这里出现。",
        "hub_footer_hint": "方向键导航 · 回车确认 · 返回键返回 · 肩键换页",
        "hub_save_status": "存档已就绪",
    },
    "en": {
        "start_eyebrow": "A SOFT STARLIGHT ADVENTURE",
        "start_title": "小树保卫者",
        "hub_wallet_label": "GOLD", "hub_completion_label": "COMPLETION",
        "hub_difficulty_label": "DIFFICULTY",
        "hub_nav_play_label": "Play", "hub_nav_characters_label": "Characters",
        "hub_nav_armory_label": "Armory", "hub_nav_shop_label": "Star Shop",
        "hub_nav_quests_label": "Quests", "hub_nav_collection_label": "Collection",
        "hub_nav_settings_label": "Settings",
        "play_page_eyebrow": "PLAY", "play_page_title": "Tonight's Starlight Journey",
        "play_character_label": "CURRENT PARTNER", "play_change_character_label": "Change Partner",
        "play_difficulty_label": "DIFFICULTY", "play_challenges_label": "CHALLENGES",
        "play_weapon_slots_label": "REGULAR WEAPON SLOTS",
        "difficulty_adventure_title": "Adventure", "difficulty_fierce_title": "Fierce",
        "difficulty_nightmare_title": "Nightmare",
        "difficulty_adventure_subtitle": "Reward ×1.00",
        "difficulty_fierce_subtitle": "Reward ×1.35",
        "difficulty_nightmare_subtitle": "Locked · Reward ×1.75",
        "play_seed_label": "RUN SEED", "play_seed_button_label": "Generate",
        "start_button_label": "Start Adventure",
        "start_subtitle": "Purify four regions · Central summon · Defeat the Star Dragon",
        "start_hint": "Use arrows or a controller to choose, then confirm to begin.",
        "characters_page_eyebrow": "CHARACTERS", "character_select_title": "Choose Your Partner",
        "character_preview_label": "PREVIEW", "character_weapon_label": "Starter Weapon",
        "character_state_label": "State", "character_price_label": "Price",
        "character_training_label": "TRAINING", "character_mastery_label": "MASTERY",
        "character_preview_idle_label": "IDLE", "character_preview_dance_label": "DANCE",
        "character_preview_loading": "Loading partner preview",
        "character_preview_error": "Partner preview is temporarily unavailable",
        "training_stat_0": "MIGHT", "training_stat_1": "HEALTH", "training_stat_2": "HASTE",
        "training_stat_3": "SPEED", "training_stat_4": "LUCK",
        "armory_page_eyebrow": "ARMORY", "armory_page_title": "Curate Your Upgrade Pool",
        "armory_filter_all_label": "ALL", "armory_filter_owned_label": "OWNED",
        "armory_filter_eligible_label": "ELIGIBLE", "armory_filter_locked_label": "LOCKED",
        "armory_filter_disabled_label": "SEALED", "armory_selected_label": "SELECTED CONTENT",
        "armory_state_label": "State", "armory_price_label": "Price",
        "armory_evolution_label": "Evolution Hint",
        "shop_page_eyebrow": "STAR SHOP", "shop_page_title": "Permanent PowerUps",
        "shop_refund_all_label": "Refund All", "shop_powerup_label": "POWERUP DETAILS",
        "shop_current_label": "Current", "shop_next_label": "Next", "shop_price_label": "Price",
        "shop_refund_label": "Refund This", "shop_transaction_status": "Your balance updates after the transaction is saved.",
        "quests_page_eyebrow": "QUESTS", "quests_page_title": "Complete Quests, Unlock New Starlight",
        "quest_filter_all_label": "ALL", "quest_filter_character_label": "CHARACTER",
        "quest_filter_combat_label": "COMBAT", "quest_filter_mastery_label": "MASTERY",
        "quest_filter_untracked_label": "UNTRACKED", "quest_detail_label": "QUEST DETAILS",
        "quest_reward_label": "Reward", "quest_unlock_label": "Unlock",
        "collection_page_eyebrow": "COLLECTION", "collection_page_title": "Every Encounter and Milestone",
        "collection_tab_enemies_label": "Enemies", "collection_tab_bosses_label": "Bosses",
        "collection_tab_evolutions_label": "Evolutions", "collection_tab_characters_label": "Characters",
        "collection_tab_stats_label": "Stats", "collection_runs_label": "TOTAL RUNS",
        "collection_best_time_label": "BEST TIME", "collection_kills_label": "TOTAL KILLS",
        "collection_top_weapon_label": "TOP WEAPON",
        "settings_page_eyebrow": "SETTINGS", "settings_page_title": "Keep Every Spark Clear and Comfortable",
        "hub_language_label": "Language", "hub_language_desc": "Choose the language used by menus and gameplay",
        "hub_language_zh_label": "Chinese", "hub_language_en_label": "English",
        "hub_volume_label": "Master Volume", "hub_volume_desc": "Controls all game audio",
        "hub_vsync_label": "VSync", "hub_vsync_desc": "Reduces visible tearing",
        "hub_display_label": "Display Mode", "hub_display_desc": "Choose fullscreen or windowed mode",
        "hub_ui_scale_label": "UI Scale", "hub_ui_scale_desc": "Adjust the HUD and menu size",
        "hub_motion_label": "UI Motion", "hub_motion_desc": "Soft button and page animations",
        "hub_flash_label": "Damage Flash", "hub_flash_desc": "Shows a cue when taking damage",
        "hub_projectile_opacity_label": "Player Projectile Opacity",
        "hub_projectile_opacity_desc": "Keeps projectile cores and enemy telegraphs clear",
        "hub_particle_density_label": "Particle Density", "hub_particle_density_desc": "Adjust decorative particles",
        "hub_damage_numbers_label": "Damage Numbers", "hub_damage_numbers_desc": "Reduce visual noise under pressure",
        "hub_screen_shake_label": "Screen Shake", "hub_screen_shake_desc": "Danger direction cues remain when disabled",
        "hub_telegraph_color_label": "Enemy Telegraph Color",
        "hub_telegraph_color_desc": "Choose contrast and color-vision presets",
        "hub_auto_throttle_label": "Automatic Visual Throttle",
        "hub_auto_throttle_desc": "Reduces decoration first under heavy load",
        "hub_display_fullscreen_label": "Fullscreen", "hub_display_windowed_label": "Windowed",
        "hub_ui_scale_small_label": "Small", "hub_ui_scale_normal_label": "Normal",
        "hub_ui_scale_large_label": "Large", "hub_particle_density_auto_label": "Auto",
        "hub_particle_density_low_label": "Low", "hub_particle_density_medium_label": "Medium",
        "hub_particle_density_high_label": "High", "hub_damage_numbers_off_label": "Off",
        "hub_damage_numbers_reduced_label": "Reduced", "hub_damage_numbers_full_label": "Full",
        "hub_telegraph_default_label": "Default", "hub_telegraph_deuteranopia_label": "Deuteranopia",
        "hub_telegraph_tritanopia_label": "Tritanopia", "hub_telegraph_high_contrast_label": "High Contrast",
        "hub_vsync_on_label": "On", "hub_vsync_off_label": "Off",
        "hub_motion_on_label": "On", "hub_motion_off_label": "Off",
        "hub_flash_on_label": "On", "hub_flash_off_label": "Off",
        "hub_screen_shake_on_label": "On", "hub_screen_shake_off_label": "Off",
        "hub_auto_throttle_on_label": "On", "hub_auto_throttle_off_label": "Off",
        "hub_settings_defaults_label": "Restore Defaults",
        "hub_settings_saved_hint": "Changes save automatically",
        "activity_tracked_label": "TRACKED QUESTS", "recent_unlock_label": "RECENT UNLOCK",
        "recent_unlock_name": "No recent unlock", "recent_unlock_hint": "Keep adventuring and new starlight will appear here.",
        "hub_footer_hint": "Arrows navigate · Enter confirms · Esc returns · LB/RB changes page",
        "hub_save_status": "PROFILE READY",
    },
}


class SurvivorHubMixin:
    MENU_PREVIEW_PREFAB = asset_path("ui/menu-preview-prefab")
    TRAINING_PRICES = (100, 200, 350, 550, 800)
    RUN_SEEDS = (7319, 9029, 12011, 18013, 24007, 31013, 42043, 65537)
    PREVIEW_POSITION = HEngine.vec3(0.0, 0.08, 0.0)
    PREVIEW_MODEL_SCALE = 1.75
    PREVIEW_DEFAULT_YAW = 0.0
    MENU_BACKDROP_BASE_SCALE = 0.105
    MENU_BACKDROP_ASPECT = 1672.0 / 941.0

    def _hub_text(self, key, **values):
        table = HUB_TEXT.get(self.language, HUB_TEXT["zh_cn"])
        return table.get(key, HUB_TEXT["en"].get(key, key)).format(**values)

    def _localized_catalog_text(self, value):
        if isinstance(value, dict):
            return value.get(self.language, value.get("en", value.get("zh_cn", "")))
        return str(value)

    def _localized_content_name(self, content_id):
        if content_id in CHARACTER_BY_ID:
            return self._localized_catalog_text(CHARACTER_BY_ID[content_id]["name"])
        if content_id in CONTENT_NAME_BY_ID:
            return self._localized_catalog_text(CONTENT_NAME_BY_ID[content_id])
        if content_id in DIFFICULTY_BY_ID:
            return self._hub_text("difficulty_" + content_id)
        return str(content_id).replace("_", " ").title()

    def _localized_formula(self, weapon_id, tome_id, bRevealTome=True):
        weapon_name = self._localized_content_name(weapon_id)
        tome_name = self._localized_content_name(tome_id) if bRevealTome else "???"
        return weapon_name + " + " + tome_name

    def _localized_unlock(self, unlock_type, unlock_id):
        if not unlock_type or not unlock_id:
            return "—"
        if unlock_type == "system":
            table = SYSTEM_UNLOCK_TEXT.get(self.language, SYSTEM_UNLOCK_TEXT["en"])
            name = table.get(unlock_id, str(unlock_id).replace("_", " ").title())
        else:
            name = self._localized_content_name(unlock_id)
        key = "unlock_" + unlock_type
        return self._hub_text(key, name=name)

    def _set_exclusive_selection(self, element_ids, selected_id):
        for element_id in element_ids:
            self._set_hud_class(
                element_id, "selected_option", element_id == selected_id,
            )

    def _initialize_hub_state(self):
        self.hub_page = "play"
        self.character_slot_map = {}
        self.armory_slot_map = {}
        self.shop_slot_map = {}
        self.quest_slot_map = {}
        self.armory_tab = "weapons"
        self.armory_filter = "all"
        self.armory_page = 0
        self.armory_focus_id = WEAPONS[0]["id"]
        self.shop_page = 0
        self.shop_focus_id = POWER_UPS[0]["id"]
        self.shop_purchase_debouncer = SurvivorHubNavigation.ActionDebouncer()
        self.quest_filter = "all"
        self.quest_page = 0
        self.quest_focus_id = QUESTS[0]["id"]
        self.collection_tab = "enemies"
        self.tracked_quest_slot_map = {}
        self.selected_run_seed = self.RUN_SEEDS[0]
        self.preview_character_id = self.selected_character
        self.menu_preview_entity = None
        self.menu_backdrop_entity = None
        self.menu_backdrop_viewport_aspect = -1.0
        self.preview_yaw = self.PREVIEW_DEFAULT_YAW
        self.preview_pitch = -0.08
        self.preview_zoom = 1.0
        self.preview_animation_mode = "idle"
        self.bPreviewDragging = False
        self.preview_pointer_x = 0.0
        self.preview_pointer_y = 0.0
        self.preview_manual_timer = 2.5
        self.preview_dance_timer = 0.0
        self.bMenuPreviewVisible = False
        self.hub_focus_by_page = {}
        self.hub_focus_id = ""
        self.hub_gamepad_index = -1
        self.hub_gamepad_connected = False
        self.hub_gamepad_buttons = {}
        self.hub_gamepad_repeater = SurvivorHubNavigation.DirectionalRepeater()

    def _ensure_menu_preview(self):
        if self.menu_preview_entity is not None:
            return True
        try:
            self.menu_preview_entity = HEngine.Instantiate(
                self.MENU_PREVIEW_PREFAB, self.PREVIEW_POSITION,
            )
        except Exception as error:
            self.menu_preview_entity = None
            self._set_hud_style("character_preview_loading", "display", "none")
            self._set_hud_style("character_preview_error", "display", "block")
            HEngine.HE_CORE_ERROR("[SurvivorHub] Preview prefab failed: " + str(error))
            return False
        self._set_hud_style("character_preview_loading", "display", "none")
        self._set_hud_style("character_preview_error", "display", "none")
        self._set_preview_character(self.preview_character_id, True)
        return True

    def _destroy_menu_preview(self):
        if getattr(self, "menu_preview_entity", None) is None:
            return
        try:
            HEngine.Destroy(self.menu_preview_entity)
        except Exception:
            pass
        self.menu_preview_entity = None

    def _set_player_menu_visible(self, bVisible):
        if self.player is None or not self.player.HasComponent("Transform"):
            return
        if bVisible:
            self._apply_selected_character_visual()
        else:
            self.player.GetComponent("Transform").Scale = HEngine.vec3(0.0, 0.0, 0.0)

    def _fit_menu_backdrop(self):
        if not getattr(self, "bMenuScene", False):
            return
        try:
            viewport_width, viewport_height = HEngine.UI.GetViewportSize()
        except Exception:
            return
        if viewport_width <= 0.0 or viewport_height <= 0.0:
            return
        viewport_aspect = float(viewport_width) / float(viewport_height)
        if abs(viewport_aspect - self.menu_backdrop_viewport_aspect) < 0.0001:
            return
        if self.menu_backdrop_entity is None:
            backdrop = HEngine.FindEntityByTag("Menu Backdrop")
            if backdrop is None or not backdrop.HasComponent("Transform"):
                return
            self.menu_backdrop_entity = backdrop
        cover_scale = self.MENU_BACKDROP_BASE_SCALE * max(
            1.0, viewport_aspect / self.MENU_BACKDROP_ASPECT,
        )
        self.menu_backdrop_entity.GetComponent("Transform").Scale = HEngine.vec3(
            cover_scale, cover_scale, cover_scale,
        )
        self.menu_backdrop_viewport_aspect = viewport_aspect

    def _set_menu_preview_visible(self, bVisible):
        self.bMenuPreviewVisible = bVisible
        if bVisible and not self._ensure_menu_preview():
            return
        if self.menu_preview_entity is None:
            return
        if bVisible:
            self._set_preview_character(self.preview_character_id, True)
        else:
            self.menu_preview_entity.GetComponent("Transform").Scale = HEngine.vec3(0.0, 0.0, 0.0)

    def _apply_preview_transform(self):
        if self.menu_preview_entity is None:
            return
        entry = CHARACTER_BY_ID[self.preview_character_id]
        preview = entry.get("preview", {})
        transform = self.menu_preview_entity.GetComponent("Transform")
        transform.Translation = self.PREVIEW_POSITION
        transform.Rotation = HEngine.vec3(
            float(preview.get("upright", 0.0)) + self.preview_pitch,
            self.preview_yaw,
            0.0,
        )
        scale = entry["scale"] * self.PREVIEW_MODEL_SCALE * self.preview_zoom
        transform.Scale = HEngine.vec3(scale, scale, scale)

    def _apply_preview_silhouette(self):
        if self.menu_preview_entity is None:
            return
        set_silhouette = getattr(self.menu_preview_entity, "SetVisualSilhouette", None)
        if set_silhouette is None:
            return
        state = self._character_state(self.preview_character_id)
        set_silhouette(state not in ("owned", "selected"))

    def _reset_preview_transform(self, character_id):
        preview = CHARACTER_BY_ID[character_id].get("preview", {})
        self.preview_yaw = self.PREVIEW_DEFAULT_YAW + float(preview.get("yaw", 0.0))
        self.preview_pitch = float(preview.get("pitch", -0.08))
        self.preview_zoom = float(preview.get("zoom", 1.0))
        self.preview_manual_timer = 2.5

    def _set_preview_animation_mode(self, mode):
        self.preview_animation_mode = mode if mode in ("idle", "dance") else "idle"
        self._set_hud_class(
            "character_preview_idle", "selected_option",
            self.preview_animation_mode == "idle",
        )
        self._set_hud_class(
            "character_preview_dance", "selected_option",
            self.preview_animation_mode == "dance",
        )

    def _set_preview_character(self, character_id, bForce=False):
        if character_id not in CHARACTER_BY_ID:
            return
        if not bForce and character_id == self.preview_character_id:
            return
        self.preview_character_id = character_id
        self._reset_preview_transform(character_id)
        self.preview_dance_timer = 0.0
        self._set_preview_animation_mode("idle")
        if not self._ensure_menu_preview():
            return
        entry = CHARACTER_BY_ID[character_id]
        self.menu_preview_entity.SetVisual(
            entry["mesh"], entry["controller"],
            entry["scale"] * self.PREVIEW_MODEL_SCALE * self.preview_zoom,
        )
        self._apply_preview_silhouette()
        if self.menu_preview_entity.HasComponent("Animator"):
            animator = self.menu_preview_entity.GetComponent("Animator")
            animator.SetSpeed(1.0)
            animator.Play()
        self._apply_preview_transform()
        self._refresh_character_page()

    def _play_preview_dance(self):
        if not self._ensure_menu_preview():
            return
        entry = CHARACTER_BY_ID[self.preview_character_id]
        if not self.menu_preview_entity.HasComponent("Animator"):
            return
        animator = self.menu_preview_entity.GetComponent("Animator")
        animator.SetControllerPath("None")
        animator.animResPath = entry["dance"]
        animator.bLoop = True
        animator.SetSpeed(1.0)
        animator.Play()
        self.preview_dance_timer = 2.4
        self._set_preview_animation_mode("dance")

    def _restore_preview_idle(self):
        if self.menu_preview_entity is None:
            return
        entry = CHARACTER_BY_ID[self.preview_character_id]
        self.menu_preview_entity.SetVisual(
            entry["mesh"], entry["controller"],
            entry["scale"] * self.PREVIEW_MODEL_SCALE * self.preview_zoom,
        )
        if self.menu_preview_entity.HasComponent("Animator"):
            animator = self.menu_preview_entity.GetComponent("Animator")
            animator.animResPath = entry["idle"]
            animator.SetSpeed(1.0)
            animator.Play()
        self._apply_preview_transform()
        self._set_preview_animation_mode("idle")

    def _rotate_preview(self, delta):
        self.preview_yaw += delta
        self.preview_manual_timer = 2.5
        self._apply_preview_transform()

    def _zoom_preview(self, delta):
        self.preview_zoom = max(0.72, min(1.32, self.preview_zoom + delta))
        self.preview_manual_timer = 2.5
        self._apply_preview_transform()

    def _handle_hub_extended_event(self, target_id, event_type, payload):
        if self.hub_page != "characters" or not self.bMenuPreviewVisible:
            self.bPreviewDragging = False
            return False
        target = payload.get("targetElementId", target_id)
        current = payload.get("currentElementId", "")
        bPreviewTarget = (
            target == "character_preview_hit_area"
            or current == "character_preview_hit_area"
        )
        if event_type == "mousedown" and bPreviewTarget:
            if "mouseX" not in payload or "mouseY" not in payload:
                return False
            self.bPreviewDragging = True
            self.preview_pointer_x = float(payload["mouseX"])
            self.preview_pointer_y = float(payload["mouseY"])
            self.preview_manual_timer = 2.5
            return True
        if event_type == "mouseup":
            bHandled = self.bPreviewDragging
            self.bPreviewDragging = False
            return bHandled
        if event_type == "mousemove" and self.bPreviewDragging:
            if "mouseX" not in payload or "mouseY" not in payload:
                return False
            pointer_x = float(payload["mouseX"])
            pointer_y = float(payload["mouseY"])
            delta_x = pointer_x - self.preview_pointer_x
            delta_y = pointer_y - self.preview_pointer_y
            self.preview_pointer_x = pointer_x
            self.preview_pointer_y = pointer_y
            self.preview_yaw += delta_x * 0.012
            self.preview_pitch = max(
                -0.24,
                min(0.16, self.preview_pitch + delta_y * 0.006),
            )
            self.preview_manual_timer = 2.5
            self._apply_preview_transform()
            return True
        if event_type == "mousescroll" and bPreviewTarget:
            if "wheelDelta" not in payload:
                return False
            self._zoom_preview(-float(payload["wheelDelta"]) * 0.06)
            return True
        return False

    def _hub_focus_context(self):
        return "settings_overlay" if self.bSettingsOpen else self.hub_page

    def _hub_focus_rows(self):
        context = self._hub_focus_context()
        if context == "settings_overlay":
            return (
                ("settings_back_button",),
                ("language_zh", "language_en"),
                ("volume_down", "volume_up"),
                ("vsync_on", "vsync_off"),
                ("display_fullscreen", "display_windowed"),
                ("ui_scale_small", "ui_scale_normal", "ui_scale_large"),
                ("motion_on", "motion_off"),
                ("flash_on", "flash_off"),
                ("projectile_opacity_down", "projectile_opacity_up"),
                ("particle_density_auto", "particle_density_low",
                 "particle_density_medium", "particle_density_high"),
                ("damage_numbers_off", "damage_numbers_reduced", "damage_numbers_full"),
                ("screen_shake_on", "screen_shake_off"),
                ("telegraph_color_default", "telegraph_color_deuteranopia",
                 "telegraph_color_tritanopia", "telegraph_color_high_contrast"),
                ("auto_throttle_on", "auto_throttle_off"),
                ("settings_defaults_button",),
            )

        rows = [("hub_nav_" + context,)]
        if context == "play":
            rows.extend((
                ("play_change_character_button",),
                ("difficulty_adventure", "difficulty_fierce", "difficulty_nightmare"),
                ("weapon_limit_3", "weapon_limit_4", "weapon_limit_5", "weapon_limit_6"),
                ("challenge_slot_0", "challenge_slot_1", "challenge_slot_2"),
                ("challenge_slot_3", "challenge_slot_4", "challenge_slot_5"),
                ("play_seed_button",),
                ("start_button",),
            ))
        elif context == "characters":
            cards = tuple("character_" + entry["id"] for entry in CHARACTERS)
            rows.extend((cards[:5], cards[5:]))
            rows.append((
                "character_rotate_left", "character_zoom_out",
                "character_preview_idle", "character_preview_dance",
                "character_preview_reset", "character_zoom_in",
                "character_rotate_right",
            ))
            state = self._character_state(self.preview_character_id)
            training = self.profile.get(
                "characterTraining", {},
            ).get(self.preview_character_id, 0)
            actions = []
            if state == "eligible":
                actions.append("character_purchase_button")
            if state in ("owned", "selected"):
                actions.append("character_use_button")
                if training < len(self.TRAINING_PRICES):
                    actions.append("character_training_button")
                if training > 0:
                    actions.append("character_training_toggle_button")
            if actions:
                rows.append(tuple(actions))
        elif context == "armory":
            rows.extend((
                tuple("armory_tab_" + tab for tab in ARMORY_DATA),
                tuple("armory_filter_" + item for item in (
                    "all", "owned", "eligible", "locked", "disabled",
                )) + ("armory_pool_toggle_all",),
            ))
            slots = tuple(self.armory_slot_map)
            rows.extend(tuple(slots[index:index + 3]) for index in range(0, len(slots), 3))
            actions = []
            state = (
                "hidden" if self.armory_tab == "evolutions"
                else self._content_state(self.armory_tab, self.armory_focus_id)
            )
            if state == "eligible":
                actions.append("armory_purchase_button")
            if state == "owned" and self.armory_tab != "evolutions":
                actions.append("armory_toggle_button")
            if actions:
                rows.append(tuple(actions))
            rows.append(("armory_page_previous", "armory_page_next"))
        elif context == "shop":
            nodes = tuple(self.shop_slot_map)
            rows.extend(tuple(nodes[index:index + 4]) for index in range(0, len(nodes), 4))
            entry = POWER_UP_BY_ID.get(self.shop_focus_id)
            level = self.profile.get("powerUps", {}).get(self.shop_focus_id, 0)
            actions = []
            bPurchaseReady = bool(
                entry
                and level < entry["maxLevel"]
                and SurvivorMetaProgression.power_up_prerequisite_met(
                    self.profile, entry["id"], level + 1,
                )
            )
            if bPurchaseReady:
                actions.append("shop_purchase_button")
            if level > 0:
                if entry and entry.get("toggleable", True):
                    actions.append("shop_enable_button")
                actions.append("shop_refund_button")
            if actions:
                rows.append(tuple(actions))
            rows.append(("shop_refund_all_button",))
        elif context == "quests":
            rows.append(tuple("quest_filter_" + item for item in (
                "all", "character", "combat", "mastery", "untracked",
            )))
            slots = tuple(self.quest_slot_map)
            rows.extend((slot,) for slot in slots)
            if slots:
                rows.append(("quest_track_button",))
            rows.append(("quest_page_previous", "quest_page_next"))
        elif context == "collection":
            rows.append(tuple("collection_tab_" + tab for tab in (
                "enemies", "bosses", "evolutions", "characters", "stats",
            )))
        elif context == "settings":
            rows.extend((
                ("hub_language_zh", "hub_language_en"),
                ("hub_volume_down", "hub_volume_up"),
                ("hub_vsync_on", "hub_vsync_off"),
                ("hub_display_fullscreen", "hub_display_windowed"),
                ("hub_ui_scale_small", "hub_ui_scale_normal", "hub_ui_scale_large"),
                ("hub_motion_on", "hub_motion_off"),
                ("hub_flash_on", "hub_flash_off"),
                ("hub_projectile_opacity_down", "hub_projectile_opacity_up"),
                ("hub_particle_density_auto", "hub_particle_density_low",
                 "hub_particle_density_medium", "hub_particle_density_high"),
                ("hub_damage_numbers_off", "hub_damage_numbers_reduced",
                 "hub_damage_numbers_full"),
                ("hub_screen_shake_on", "hub_screen_shake_off"),
                ("hub_telegraph_color_default", "hub_telegraph_color_deuteranopia",
                 "hub_telegraph_color_tritanopia", "hub_telegraph_color_high_contrast"),
                ("hub_auto_throttle_on", "hub_auto_throttle_off"),
                ("hub_settings_defaults_button",),
            ))
        return tuple(row for row in rows if row)

    def _hub_focus_default(self):
        context = self._hub_focus_context()
        defaults = {
            "play": "start_button",
            "characters": "character_" + self.preview_character_id,
            "armory": next(iter(self.armory_slot_map), "hub_nav_armory"),
            "shop": next(iter(self.shop_slot_map), "hub_nav_shop"),
            "quests": next(iter(self.quest_slot_map), "hub_nav_quests"),
            "collection": "hub_nav_collection",
            "settings": "hub_language_zh" if self.language == "zh_cn" else "hub_language_en",
            "settings_overlay": "settings_back_button",
        }
        return defaults.get(context, "")

    def _set_hub_focus(self, element_id, bApply=True):
        context = self._hub_focus_context()
        available = SurvivorHubNavigation.focus_ids(self._hub_focus_rows())
        if element_id not in available:
            return False
        self.hub_focus_id = element_id
        self.hub_focus_by_page[context] = element_id
        if bApply and self.document_id:
            return bool(RmlUI.FocusElement(self.document_id, element_id))
        return True

    def _normalize_hub_focus(self, bApply=False):
        context = self._hub_focus_context()
        focus_id = SurvivorHubNavigation.normalize_focus(
            self._hub_focus_rows(),
            self.hub_focus_by_page.get(context, self.hub_focus_id),
            self._hub_focus_default(),
        )
        if focus_id:
            self._set_hub_focus(focus_id, bApply)
        return focus_id

    def _move_hub_focus(self, direction):
        focus_id = SurvivorHubNavigation.move_focus(
            self._hub_focus_rows(), self.hub_focus_id, direction,
        )
        if focus_id:
            self._set_hub_focus(focus_id, True)

    def _cycle_hub_page(self, offset):
        index = HUB_PAGES.index(self.hub_page)
        self._show_hub_page(HUB_PAGES[(index + offset) % len(HUB_PAGES)])

    def _update_hub_gamepad(self, dt):
        gamepad_index = HEngine.Input.FindFirstConnectedGamepad()
        if gamepad_index < 0:
            self.hub_gamepad_index = -1
            self.hub_gamepad_connected = False
            self.hub_gamepad_buttons = {}
            self.hub_gamepad_repeater.reset()
            return

        pad = HEngine.Input.GetGamepadState(gamepad_index)
        if not pad.Connected:
            return
        buttons = {
            "accept": pad.IsButtonPressed(HEngine.GamepadButton.A),
            "back": pad.IsButtonPressed(HEngine.GamepadButton.B),
            "page_left": pad.IsButtonPressed(HEngine.GamepadButton.LeftBumper),
            "page_right": pad.IsButtonPressed(HEngine.GamepadButton.RightBumper),
        }
        left_x = pad.GetAxis(HEngine.GamepadAxis.LeftX)
        left_y = -pad.GetAxis(HEngine.GamepadAxis.LeftY)
        if pad.IsButtonPressed(HEngine.GamepadButton.DPadLeft):
            left_x = -1.0
        elif pad.IsButtonPressed(HEngine.GamepadButton.DPadRight):
            left_x = 1.0
        if pad.IsButtonPressed(HEngine.GamepadButton.DPadUp):
            left_y = 1.0
        elif pad.IsButtonPressed(HEngine.GamepadButton.DPadDown):
            left_y = -1.0

        bNewConnection = (
            not self.hub_gamepad_connected
            or gamepad_index != self.hub_gamepad_index
        )
        self.hub_gamepad_connected = True
        self.hub_gamepad_index = gamepad_index
        if bNewConnection:
            self.hub_gamepad_buttons = buttons
            self.hub_gamepad_repeater.reset()
            self.hub_gamepad_repeater.update(left_x, left_y, 0.0)
            self._normalize_hub_focus(True)
            return

        edges = SurvivorHubNavigation.pressed_edges(
            self.hub_gamepad_buttons, buttons,
        )
        self.hub_gamepad_buttons = buttons
        if "back" in edges:
            if self.bSettingsOpen:
                self._close_settings()
                self._normalize_hub_focus(True)
            elif self.hub_page != "play":
                self._show_hub_page("play")
            return
        if not self.bSettingsOpen:
            if "page_left" in edges:
                self._cycle_hub_page(-1)
            elif "page_right" in edges:
                self._cycle_hub_page(1)
        if "accept" in edges:
            self._normalize_hub_focus(True)
            if self.hub_focus_id and not RmlUI.ClickElement(
                    self.document_id, self.hub_focus_id):
                self.OnUIEvent(self.document_id, self.hub_focus_id, "click")

        direction = self.hub_gamepad_repeater.update(left_x, left_y, dt)
        if direction:
            self._move_hub_focus(direction)

        if self.hub_page == "characters" and self.bMenuPreviewVisible:
            right_x = SurvivorHubNavigation.apply_deadzone(
                pad.GetAxis(HEngine.GamepadAxis.RightX),
            )
            right_y = SurvivorHubNavigation.apply_deadzone(
                pad.GetAxis(HEngine.GamepadAxis.RightY),
            )
            if right_x != 0.0 or right_y != 0.0:
                self.preview_yaw += right_x * 1.8 * dt
                self.preview_pitch = max(
                    -0.24,
                    min(0.16, self.preview_pitch + right_y * 0.9 * dt),
                )
                self.preview_manual_timer = 2.5
                self._apply_preview_transform()
            zoom_axis = (
                pad.GetAxis(HEngine.GamepadAxis.RightTrigger)
                - pad.GetAxis(HEngine.GamepadAxis.LeftTrigger)
            )
            if abs(zoom_axis) > 0.08:
                self._zoom_preview(zoom_axis * 0.38 * dt)

    def _update_hub(self, dt):
        if not self.bInMainMenu:
            return
        self.shop_purchase_debouncer.update(dt)
        self._fit_menu_backdrop()
        self._update_hub_gamepad(dt)
        if self.hub_page == "characters" and self.bMenuPreviewVisible:
            rotate = 0.0
            if HEngine.Input.IsKeyPressed(HEngine.KeyCode.A):
                rotate -= 1.35 * dt
            if HEngine.Input.IsKeyPressed(HEngine.KeyCode.D):
                rotate += 1.35 * dt
            if rotate != 0.0:
                self._rotate_preview(rotate)
            else:
                self.preview_manual_timer = max(0.0, self.preview_manual_timer - dt)
                if self.bMotionEnabled and self.preview_manual_timer <= 0.0:
                    self.preview_yaw += math.radians(10.0) * dt
                    self._apply_preview_transform()
            if self.preview_dance_timer > 0.0:
                self.preview_dance_timer = max(0.0, self.preview_dance_timer - dt)
                if self.preview_dance_timer <= 0.0:
                    self._restore_preview_idle()

    def _show_hub_page(self, page):
        if page not in HUB_PAGES:
            return
        self.hub_page = page
        for page_id in HUB_PAGES:
            self._set_hud_style(
                "hub_page_" + page_id,
                "display",
                "flex" if page_id == page else "none",
            )
            self._set_hud_class("hub_page_" + page_id, "selected_hub_page", page_id == page)
            self._set_hud_class("hub_nav_" + page_id, "active", page_id == page)
            self._set_hud_class("hub_nav_" + page_id, "selected_option", page_id == page)
        self._set_hud_class("hud", "character_preview_mode", page == "characters")
        self._set_menu_preview_visible(page == "characters")
        self._refresh_hub()
        self._normalize_hub_focus(self.hub_gamepad_connected)

    def _refresh_hub(self):
        if not self.document_id:
            return
        self._refresh_hub_static_text()
        self._refresh_hub_header()
        self._refresh_play_page()
        self._refresh_character_page()
        self._refresh_armory_page()
        self._refresh_shop_page()
        self._refresh_quest_page()
        self._refresh_collection_page()
        self._refresh_hub_settings()
        if self.hub_focus_id:
            self._normalize_hub_focus(self.hub_gamepad_connected)

    def _refresh_hub_static_text(self):
        table = HUB_STATIC_TEXT.get(self.language, HUB_STATIC_TEXT["zh_cn"])
        for element_id, text in table.items():
            self._set_hud_text(element_id, text)
        for element_id, key in {
            "armory_tab_weapons_label": "armory_weapons",
            "armory_tab_tomes_label": "armory_tomes",
            "armory_tab_trinkets_label": "armory_trinkets",
            "armory_tab_evolutions_label": "armory_evolutions",
        }.items():
            self._set_hud_text(element_id, self._hub_text(key))

    def _completion_percent(self):
        owned = self.profile["owned"]
        discovered = self.profile.get("discoveredEvolutions", [])
        completed = (
            len(owned["characters"]) + len(owned["weapons"])
            + len(owned["tomes"]) + len(owned["trinkets"]) + len(discovered)
        )
        total = len(CHARACTERS) + len(WEAPONS) + len(TOMES) + len(TRINKETS) + len(EVOLUTIONS)
        return int(round(100.0 * completed / max(1, total)))

    def _refresh_hub_header(self):
        difficulty_id = self.profile.get("selectedDifficulty", "adventure")
        self._set_hud_text("hub_wallet_value", str(self.profile["walletGold"]))
        self._set_hud_text("hub_completion_value", str(self._completion_percent()) + "%")
        self._set_hud_text(
            "hub_difficulty_value", self._hub_text("difficulty_" + difficulty_id),
        )
        quest_by_id = {quest["id"]: quest for quest in QUESTS}
        tracked = [
            quest_id
            for quest_id in self.profile.get("trackedQuests", [])
            if self._quest_visible(quest_by_id.get(quest_id))
        ][:3]
        self._set_hud_text("activity_tracked_count", str(len(tracked)) + "/3")
        self.tracked_quest_slot_map = {}
        for index in range(3):
            name_text = self._hub_text("tracked_empty")
            progress_text = "—"
            if index < len(tracked) and tracked[index] in quest_by_id:
                quest = quest_by_id[tracked[index]]
                self.tracked_quest_slot_map[
                    "tracked_quest_slot_" + str(index)
                ] = quest["id"]
                progress = self._quest_progress(quest)
                name_text = self._localized_catalog_text(quest["title"])
                progress_text = self._hub_text(
                    "quest_progress", value=progress, target=quest["target"],
                )
            self._set_hud_text("tracked_quest_slot_" + str(index) + "_name", name_text)
            self._set_hud_text("tracked_quest_slot_" + str(index) + "_progress", progress_text)
            self._set_hud_class(
                "tracked_quest_slot_" + str(index), "empty",
                "tracked_quest_slot_" + str(index) not in self.tracked_quest_slot_map,
            )

    def _refresh_play_page(self):
        selected = CHARACTER_BY_ID[self.selected_character]
        self._set_hud_text(
            "play_character_name", self._localized_catalog_text(selected["name"]),
        )
        self._set_hud_text("play_character_passive", self._localized_catalog_text(selected["description"]))
        self._set_hud_attribute("play_character_portrait", "src", selected["icon"])
        difficulty_id = self.profile.get("selectedDifficulty", "adventure")
        valid_challenge_ids = tuple(entry["id"] for entry in CHALLENGES)
        challenge_ids = SurvivorRules.selected_challenge_ids(
            self.profile, valid_challenge_ids,
        )
        difficulty_reward = DIFFICULTY_BY_ID.get(difficulty_id, {"gold": 1.0})["gold"]
        challenge_reward = SurvivorEconomy.combine_challenge_rewards(
            CHALLENGE_BY_ID[challenge_id]["gold"]
            for challenge_id in challenge_ids
        )
        purchased_weapon_slots = SurvivorMetaProgression.purchased_weapon_slot_limit(
            self.profile,
        )
        selected_weapon_slots = SurvivorMetaProgression.selected_weapon_slot_limit(
            self.profile,
        )
        weapon_slot_factor = SurvivorMetaProgression.weapon_slot_reward_factor(
            selected_weapon_slots,
        )
        difficulty_challenge_factor = min(
            SurvivorEconomy.MAX_DIFFICULTY_FACTOR,
            difficulty_reward * challenge_reward,
        )
        self._set_hud_text(
            "play_reward_multiplier",
            self._hub_text(
                "play_reward",
                value=f"{difficulty_challenge_factor * weapon_slot_factor:.2f}",
            ),
        )
        self._set_hud_text(
            "play_weapon_slots_summary",
            self._hub_text(
                "weapon_slots_summary",
                purchased=purchased_weapon_slots,
                selected=selected_weapon_slots,
            ),
        )
        for weapon_slot_limit in range(
                SurvivorMetaProgression.BASE_WEAPON_SLOTS,
                SurvivorMetaProgression.MAX_WEAPON_SLOTS + 1):
            button_id = "weapon_limit_" + str(weapon_slot_limit)
            bLocked = weapon_slot_limit > purchased_weapon_slots
            if bLocked:
                prerequisite = SurvivorMetaProgression.power_up_level_prerequisite(
                    SurvivorMetaProgression.WEAPON_SLOT_POWER_UP_ID,
                    weapon_slot_limit - SurvivorMetaProgression.BASE_WEAPON_SLOTS,
                )
                label = self._hub_text(
                    "weapon_slot_locked",
                    count=weapon_slot_limit,
                    difficulty=self._hub_text("difficulty_" + prerequisite),
                )
            else:
                bonus_percent = int(round(
                    (SurvivorMetaProgression.weapon_slot_reward_factor(
                        weapon_slot_limit,
                    ) - 1.0) * 100.0
                ))
                label = self._hub_text(
                    "weapon_slot_option",
                    count=weapon_slot_limit,
                    bonus=bonus_percent,
                )
            self._set_hud_text(button_id + "_label", label)
            self._set_hud_class(button_id, "locked", bLocked)
            self._set_hud_class(button_id, "locked_content", bLocked)
        self._set_exclusive_selection(
            tuple(
                "weapon_limit_" + str(limit)
                for limit in range(
                    SurvivorMetaProgression.BASE_WEAPON_SLOTS,
                    SurvivorMetaProgression.MAX_WEAPON_SLOTS + 1,
                )
            ),
            "weapon_limit_" + str(selected_weapon_slots),
        )
        self._set_hud_text("play_seed_value", str(self.selected_run_seed))
        clears = self.profile.get("difficultyClears", {})
        for entry in DIFFICULTIES:
            difficulty = entry["id"]
            bLocked = (
                difficulty == "fierce" and not clears.get("adventure", False)
            ) or (
                difficulty == "nightmare" and not clears.get("fierce", False)
            )
            self._set_hud_class("difficulty_" + difficulty, "selected_option", difficulty == difficulty_id)
            self._set_hud_class("difficulty_" + difficulty, "locked", bLocked)
            self._set_hud_class("difficulty_" + difficulty, "locked_content", bLocked)
            reward_text = self._hub_text(
                "difficulty_reward_locked" if bLocked else "difficulty_reward",
                value=f"{entry['gold']:.2f}",
            )
            self._set_hud_text("difficulty_" + difficulty + "_subtitle", reward_text)
        self._set_exclusive_selection(
            tuple("difficulty_" + entry["id"] for entry in DIFFICULTIES),
            "difficulty_" + difficulty_id,
        )
        self.challenge_slot_map = {}
        for index, entry in enumerate(CHALLENGES):
            slot_id = "challenge_slot_" + str(index)
            challenge = entry["id"]
            self.challenge_slot_map[slot_id] = challenge
            self._set_hud_text(slot_id + "_name", self._hub_text("challenge_" + challenge))
            bChecked = challenge in challenge_ids
            self._set_hud_class(slot_id, "checked", bChecked)
            self._set_hud_class(slot_id, "selected_option", False)
            self._set_hud_text(slot_id + "_mark", "✓" if bChecked else "+")
        self._set_hud_text(
            "play_challenge_count", str(len(challenge_ids)) + " / " + str(len(CHALLENGES)),
        )

    def _character_state(self, character_id):
        state = self._content_state("characters", character_id)
        if state == "owned" and character_id == self.selected_character:
            return "selected"
        return state

    def _refresh_character_page(self):
        if not self.document_id:
            return
        self.character_slot_map = {}
        for index, entry in enumerate(CHARACTERS):
            slot_id = "character_slot_" + str(index)
            character_id = entry["id"]
            self.character_slot_map[slot_id] = character_id
            state = self._character_state(character_id)
            product = PRODUCT_BY_KEY.get(("characters", character_id), {"price": 0})
            card_id = "character_" + character_id
            self.character_slot_map[card_id] = character_id
            self._set_hud_attribute(card_id + "_icon", "src", entry["icon"])
            self._set_hud_text(card_id + "_name", self._localized_catalog_text(entry["name"]))
            self._set_hud_text(card_id + "_passive", self._localized_catalog_text(entry["description"]))
            state_text = self._hub_text("state_" + state)
            if state == "eligible" and product["price"] > 0:
                state_text += " · " + str(product["price"])
            self._set_hud_text(card_id + "_unlock", state_text)
            for state_name in ("hidden", "locked", "eligible", "owned", "selected"):
                self._set_hud_class(slot_id, "state_" + state_name, state == state_name)
                self._set_hud_class(card_id, "state_" + state_name, state == state_name)
            self._set_hud_class(card_id, "locked_character", state in ("hidden", "locked"))
            self._set_hud_class(card_id, "selected_character", state == "selected")
            self._set_hud_class(
                card_id, "preview_character",
                character_id == self.preview_character_id,
            )

        entry = CHARACTER_BY_ID[self.preview_character_id]
        state = self._character_state(self.preview_character_id)
        self._apply_preview_silhouette()
        mastery_xp = self.profile.get("characterMasteryXp", {}).get(self.preview_character_id, 0)
        mastery_level = min(10, 1 + mastery_xp // 500)
        training = self.profile.get("characterTraining", {}).get(self.preview_character_id, 0)
        training_enabled = self.profile.get(
            "characterTrainingEnabled", {},
        ).get(self.preview_character_id, True)
        self._set_hud_text("character_detail_name", self._localized_catalog_text(entry["name"]))
        self._set_hud_text("character_detail_passive", self._localized_catalog_text(entry["description"]))
        self._set_hud_text("character_detail_state", self._hub_text("state_" + state))
        weapon_name = CONTENT_NAME_BY_ID.get(entry["starterWeapon"], entry["starterWeapon"])
        self._set_hud_text(
            "character_detail_weapon", self._localized_catalog_text(weapon_name),
        )
        self._set_hud_text(
            "character_mastery_text",
            self._hub_text("mastery", level=mastery_level, xp=mastery_xp),
        )
        self._set_hud_text(
            "character_mastery_level",
            self._hub_text("mastery_level", level=mastery_level),
        )
        self._set_hud_style("character_mastery_fill", "width", str(min(100, (mastery_xp % 500) // 5)) + "%")
        product = PRODUCT_BY_KEY.get(("characters", self.preview_character_id), {"price": 0})
        self._set_hud_text(
            "character_detail_price",
            str(product["price"]) if state == "eligible" else "—",
        )
        self._set_hud_text(
            "character_use_button_label",
            self._hub_text("using" if state == "selected" else "use"),
        )
        self._set_hud_text(
            "character_purchase_button_label",
            self._hub_text("purchase") + " · " + str(product["price"]),
        )
        if training >= len(self.TRAINING_PRICES):
            training_text = self._hub_text("training_max")
        else:
            training_text = self._hub_text(
                "training", level=training, price=self.TRAINING_PRICES[training],
            )
        self._set_hud_text("character_training_level", str(training) + "/5")
        self._set_hud_text("character_training_button_label", training_text)
        self._set_hud_text(
            "character_training_toggle_button_label",
            self._hub_text(
                "training_toggle",
                state=self._hub_text("on" if training_enabled else "off"),
            ),
        )
        self._set_hud_text("character_roster_count", str(len(self.profile["owned"]["characters"])) + " / 10")
        self._set_hud_class("character_use_button", "disabled", state != "owned")
        self._set_hud_class("character_purchase_button", "disabled", state != "eligible")
        self._set_hud_class(
            "character_training_button", "disabled",
            state not in ("owned", "selected") or training >= 5,
        )
        self._set_hud_class(
            "character_training_toggle_button", "disabled",
            state not in ("owned", "selected") or training <= 0,
        )
        self._set_hud_style(
            "character_purchase_button", "display",
            "flex" if state == "eligible" else "none",
        )
        self._set_hud_style(
            "character_use_button", "display",
            "flex" if state in ("owned", "selected") else "none",
        )
        self._set_hud_style(
            "character_training_button", "display",
            "flex" if state in ("owned", "selected") and training < 5 else "none",
        )
        self._set_hud_style(
            "character_training_toggle_button", "display",
            "flex" if state in ("owned", "selected") and training > 0 else "none",
        )

    def _purchase_preview_character(self):
        receipt = self._purchase_content("characters", self.preview_character_id)
        self._refresh_hub()
        return receipt

    def _use_preview_character(self):
        if self._content_state("characters", self.preview_character_id) != "owned":
            return False
        self._select_character(self.preview_character_id)
        self._refresh_hub()
        return self.selected_character == self.preview_character_id

    def _train_preview_character(self):
        character_id = self.preview_character_id
        if self._content_state("characters", character_id) not in ("owned", "selected"):
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        level = staged["characterTraining"].get(character_id, 0)
        if level >= len(self.TRAINING_PRICES):
            return False
        price = self.TRAINING_PRICES[level]
        if staged["walletGold"] < price:
            return False
        staged["walletGold"] -= price
        staged["characterTraining"][character_id] = level + 1
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _toggle_preview_training(self):
        character_id = self.preview_character_id
        if self._content_state("characters", character_id) not in ("owned", "selected"):
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        if staged["characterTraining"].get(character_id, 0) <= 0:
            return False
        enabled = staged["characterTrainingEnabled"].get(character_id, True)
        staged["characterTrainingEnabled"][character_id] = not enabled
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _armory_sealing_unlocked(self):
        if "quest_system_seal" in self.profile.get("completedQuests", []):
            return True
        return any(
            self.profile.get("poolDisabled", {}).get(category, [])
            for category in ("weapons", "tomes", "trinkets")
        )

    def _refresh_armory_page(self):
        bSealingUnlocked = self._armory_sealing_unlocked()
        if self.armory_filter == "disabled" and not bSealingUnlocked:
            self.armory_filter = "all"
        entries = self._filtered_armory_entries()
        pages = max(1, (len(entries) + 9) // 10)
        self.armory_page = min(self.armory_page, pages - 1)
        start = self.armory_page * 10
        visible = entries[start:start + 10]
        bEmpty = not visible
        visible_ids = tuple(entry["id"] for entry in visible)
        if self.armory_focus_id not in visible_ids:
            self.armory_focus_id = visible_ids[0] if visible_ids else ""
        self.armory_slot_map = {}
        discovered = set(self.profile.get("discoveredEvolutions", []))
        disabled = set(self.profile.get("poolDisabled", {}).get(self.armory_tab, []))
        self._set_hud_text("armory_empty_state_label", self._hub_text("empty_content"))
        self._set_hud_style(
            "armory_empty_state", "display", "flex" if bEmpty else "none",
        )
        self._set_hud_style("armory_layout", "display", "flex")
        self._set_hud_style("armory_slot_grid", "display", "flex")
        self._set_hud_style("armory_detail", "display", "flex")
        for index in range(10):
            slot_id = "armory_slot_" + str(index)
            if index >= len(visible):
                self._set_hud_style(slot_id, "display", "none")
                self._set_hud_attribute(slot_id + "_icon", "src", "")
                continue
            self._set_hud_style(slot_id, "display", "flex")
            entry = visible[index]
            content_id = entry["id"]
            self.armory_slot_map[slot_id] = content_id
            if self.armory_tab == "evolutions":
                bDiscovered = content_id in discovered
                state = "owned" if bDiscovered else "hidden"
                name = self._localized_catalog_text(entry["name"]) if bDiscovered else "???"
                description = self._localized_formula(
                    entry["weaponId"], entry["tomeId"], bDiscovered,
                )
            else:
                state = self._content_state(self.armory_tab, content_id)
                name = self._localized_catalog_text(entry["name"])
                description = self._localized_catalog_text(entry["description"])
            display_state = "sealed" if content_id in disabled else state
            icon_path = entry["icon"] if state != "hidden" else ""
            self._set_hud_attribute(slot_id + "_icon", "src", icon_path)
            self._set_hud_style(
                slot_id + "_icon", "display", "block" if icon_path else "none",
            )
            self._set_hud_text(slot_id + "_name", name)
            self._set_hud_text(
                slot_id + "_state", self._hub_text("state_" + display_state),
            )
            for state_name in ("hidden", "locked", "eligible", "owned", "sealed"):
                self._set_hud_class(
                    slot_id, "state_" + state_name, display_state == state_name,
                )
            self._set_hud_class(slot_id, "focused", content_id == self.armory_focus_id)
            self._set_hud_class(
                slot_id, "selected_option",
                content_id == self.armory_focus_id,
            )
        self._set_hud_text("armory_page_value", self._hub_text("page", page=self.armory_page + 1, pages=pages))
        self._set_exclusive_selection(
            tuple("armory_tab_" + tab for tab in ARMORY_DATA),
            "armory_tab_" + self.armory_tab,
        )
        self._set_exclusive_selection(
            tuple("armory_filter_" + filter_id for filter_id in (
                "all", "owned", "eligible", "locked", "disabled",
            )),
            "armory_filter_" + self.armory_filter,
        )
        owned_count = len(self.profile["owned"].get(self.armory_tab, [])) if self.armory_tab != "evolutions" else len(self.profile.get("discoveredEvolutions", []))
        self._set_hud_text("armory_pool_summary", str(owned_count) + " / " + str(len(ARMORY_DATA[self.armory_tab])))
        disabled_count = len(self.profile.get("poolDisabled", {}).get(self.armory_tab, []))
        self._set_hud_text(
            "armory_pool_toggle_all_label",
            self._hub_text("pool_unseal_all"),
        )
        self._set_hud_text(
            "armory_filter_disabled_label",
            self._hub_text("pool_sealed_count", count=disabled_count),
        )
        self._set_hud_text(
            "armory_pool_hint",
            self._hub_text("pool_hint" if bSealingUnlocked else "pool_locked_hint"),
        )
        bEvolutionTab = self.armory_tab == "evolutions"
        for filter_id in ("all", "owned", "eligible", "locked", "disabled"):
            self._set_hud_style(
                "armory_filter_" + filter_id,
                "display", "none" if (
                    bEvolutionTab or (filter_id == "disabled" and not bSealingUnlocked)
                ) else "flex",
            )
        self._set_hud_style(
            "armory_pool_toggle_all",
            "display", "flex" if (
                not bEvolutionTab and bSealingUnlocked and disabled_count > 0
            ) else "none",
        )
        self._set_hud_style(
            "armory_pool_hint", "display", "none" if bEvolutionTab else "block",
        )
        self._refresh_armory_focus()

    def _filtered_armory_entries(self):
        entries = ARMORY_DATA[self.armory_tab]
        if self.armory_filter == "all" or self.armory_tab == "evolutions":
            return entries
        disabled = set(self.profile.get("poolDisabled", {}).get(self.armory_tab, []))
        result = []
        for entry in entries:
            state = self._content_state(self.armory_tab, entry["id"])
            if self.armory_filter == "disabled" and entry["id"] in disabled:
                result.append(entry)
            elif self.armory_filter == "owned" and state == "owned" and entry["id"] not in disabled:
                result.append(entry)
            elif self.armory_filter not in ("disabled", "owned") and state == self.armory_filter:
                result.append(entry)
        return tuple(result)

    def _refresh_armory_focus(self):
        entries = {entry["id"]: entry for entry in ARMORY_DATA[self.armory_tab]}
        entry = entries.get(self.armory_focus_id)
        if entry is None:
            self._set_hud_text("armory_detail_name", "—")
            self._set_hud_text("armory_detail_description", self._hub_text("empty_content"))
            self._set_hud_text("armory_detail_state", "—")
            self._set_hud_text("armory_detail_price", "—")
            self._set_hud_text("armory_detail_evolution", "—")
            self._set_hud_style("armory_purchase_button", "display", "none")
            self._set_hud_style("armory_toggle_button", "display", "none")
            return
        if self.armory_tab == "evolutions":
            bDiscovered = entry["id"] in self.profile.get("discoveredEvolutions", [])
            self._set_hud_text(
                "armory_detail_name",
                self._localized_catalog_text(entry["name"]) if bDiscovered else "???",
            )
            description = self._localized_formula(
                entry["weaponId"], entry["tomeId"], bDiscovered,
            )
            state = "owned" if entry["id"] in self.profile.get("discoveredEvolutions", []) else "hidden"
            price = "—"
            evolution = description if bDiscovered else "???"
        else:
            self._set_hud_text("armory_detail_name", self._localized_catalog_text(entry["name"]))
            description = self._localized_catalog_text(entry["description"])
            state = self._content_state(self.armory_tab, entry["id"])
            product = PRODUCT_BY_KEY.get((self.armory_tab, entry["id"]), {"price": 0})
            price = str(product["price"])
            evolution_id = entry.get("evolutionId", "")
            evolution = self._localized_catalog_text(
                CONTENT_NAME_BY_ID.get(evolution_id, evolution_id or "—"),
            )
        self._set_hud_text("armory_detail_description", description)
        disabled = self.profile.get("poolDisabled", {}).get(self.armory_tab, [])
        bSealed = self.armory_focus_id in disabled
        self._set_hud_text(
            "armory_detail_state",
            self._hub_text("state_sealed" if bSealed else "state_" + state),
        )
        self._set_hud_text("armory_detail_price", price)
        self._set_hud_text("armory_detail_evolution", evolution)
        bOwned = (
            self.armory_tab != "evolutions"
            and self._content_state(self.armory_tab, self.armory_focus_id) == "owned"
        )
        minimum = {"weapons": 6, "tomes": 6, "trinkets": 4}.get(self.armory_tab, 0)
        enabled_count = len(self.profile["owned"].get(self.armory_tab, [])) - len(disabled)
        bStarterProtected = (
            self.armory_tab == "weapons"
            and self.armory_focus_id == CHARACTER_BY_ID[self.selected_character]["starterWeapon"]
        )
        bCanToggle = (
            bOwned and self._armory_sealing_unlocked()
            and (bSealed or (not bStarterProtected and enabled_count > minimum))
        )
        if not bOwned:
            toggle_text = self._hub_text("pool_unavailable")
        elif bSealed:
            toggle_text = self._hub_text("pool_disabled")
        elif bStarterProtected:
            toggle_text = self._hub_text("pool_starter_protected")
        elif enabled_count <= minimum:
            toggle_text = self._hub_text("pool_minimum", count=minimum)
        else:
            toggle_text = self._hub_text("pool_enabled")
        self._set_hud_text("armory_toggle_button_label", toggle_text)
        self._set_hud_text("armory_purchase_button_label", self._hub_text("purchase"))
        self._set_hud_class("armory_toggle_button", "disabled", not bCanToggle)
        self._set_hud_class(
            "armory_purchase_button", "disabled",
            self.armory_tab == "evolutions" or state != "eligible",
        )
        self._set_hud_style(
            "armory_purchase_button", "display",
            "flex" if self.armory_tab != "evolutions" and state == "eligible" else "none",
        )
        self._set_hud_style(
            "armory_toggle_button", "display",
            "flex" if bOwned and self._armory_sealing_unlocked() else "none",
        )

    def _purchase_armory_focus(self):
        if self.armory_tab == "evolutions":
            return None
        receipt = self._purchase_content(self.armory_tab, self.armory_focus_id)
        self._refresh_hub()
        return receipt

    def _toggle_armory_pool(self):
        category = self.armory_tab
        content_id = self.armory_focus_id
        if (
                not self._armory_sealing_unlocked()
                or category == "evolutions"
                or self._content_state(category, content_id) != "owned"):
            return False
        if category == "weapons" and content_id == CHARACTER_BY_ID[self.selected_character]["starterWeapon"]:
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        disabled = staged["poolDisabled"][category]
        if content_id in disabled:
            disabled.remove(content_id)
        else:
            owned = staged["owned"][category]
            minimum = {"weapons": 6, "tomes": 6, "trinkets": 4}[category]
            if len(owned) - len(disabled) <= minimum:
                return False
            disabled.append(content_id)
        if not self._save_progression(staged):
            return False
        self._refresh_armory_page()
        return True

    def _toggle_all_armory_pool(self):
        category = self.armory_tab
        if not self._armory_sealing_unlocked() or category == "evolutions":
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        disabled = staged["poolDisabled"][category]
        if not disabled:
            return False
        disabled.clear()
        if not self._save_progression(staged):
            return False
        self.armory_filter = "all"
        self._refresh_armory_page()
        return True

    def _refresh_shop_page(self):
        self.shop_slot_map = {}
        for index, entry in enumerate(POWER_UPS):
            slot_id = "powerup_node_" + str(index)
            power_up_id = entry["id"]
            self.shop_slot_map[slot_id] = power_up_id
            self._set_hud_attribute(slot_id + "_icon", "src", entry["icon"])
            level = self.profile.get("powerUps", {}).get(power_up_id, 0)
            self._set_hud_text(slot_id + "_name", self._localized_catalog_text(entry["name"]))
            self._set_hud_text(slot_id + "_rank", str(level) + "/" + str(entry["maxLevel"]))
            self._set_hud_class(slot_id, "focused", power_up_id == self.shop_focus_id)
            self._set_hud_class(slot_id, "selected_option", power_up_id == self.shop_focus_id)
            self._set_hud_class(slot_id, "maxed", level >= entry["maxLevel"])
            bLocked = (
                level < entry["maxLevel"]
                and not SurvivorMetaProgression.power_up_prerequisite_met(
                    self.profile, power_up_id, level + 1,
                )
            )
            self._set_hud_class(slot_id, "locked", bLocked)
        self._set_exclusive_selection(
            tuple("powerup_node_" + str(index) for index in range(len(POWER_UPS))),
            next((
                slot_id for slot_id, power_up_id in self.shop_slot_map.items()
                if power_up_id == self.shop_focus_id
            ), ""),
        )
        self._refresh_shop_focus()

    def _refresh_shop_focus(self):
        entry = POWER_UP_BY_ID.get(self.shop_focus_id)
        if entry is None:
            return
        level = self.profile.get("powerUps", {}).get(self.shop_focus_id, 0)
        enabled = self.profile.get("powerUpsEnabled", {}).get(self.shop_focus_id, level > 0)
        self._set_hud_text("shop_detail_name", self._localized_catalog_text(entry["name"]))
        self._set_hud_text(
            "shop_detail_description",
            self._localized_catalog_text(
                entry.get("description", self._hub_text("shop_generic_description")),
            ),
        )
        if self.shop_focus_id == SurvivorMetaProgression.WEAPON_SLOT_POWER_UP_ID:
            self._set_hud_text(
                "shop_current_value",
                str(SurvivorMetaProgression.BASE_WEAPON_SLOTS + level) + " / 6",
            )
            self._set_hud_text(
                "shop_next_value",
                str(
                    SurvivorMetaProgression.BASE_WEAPON_SLOTS
                    + min(entry["maxLevel"], level + 1)
                ) + " / 6",
            )
        else:
            self._set_hud_text("shop_current_value", str(level))
            self._set_hud_text(
                "shop_next_value", str(min(entry["maxLevel"], level + 1)),
            )
        bPurchaseLocked = (
            level < entry["maxLevel"]
            and not SurvivorMetaProgression.power_up_prerequisite_met(
                self.profile, self.shop_focus_id, level + 1,
            )
        )
        if level >= entry["maxLevel"]:
            buy_text = self._hub_text("shop_max")
            next_price = "—"
        else:
            buy_text = self._hub_text("shop_buy", price=entry["prices"][level])
            next_price = str(entry["prices"][level])
        self._set_hud_text("shop_next_price", next_price)
        self._set_hud_text("shop_purchase_button_label", buy_text)
        if bPurchaseLocked:
            prerequisite = SurvivorMetaProgression.power_up_level_prerequisite(
                self.shop_focus_id, level + 1,
            )
            transaction_status = self._hub_text(
                "shop_requires_clear",
                difficulty=self._hub_text("difficulty_" + prerequisite),
            )
        else:
            transaction_status = self._hub_text("shop_ready")
        self._set_hud_text("shop_transaction_status", transaction_status)
        self._set_hud_text(
            "shop_enable_button_label",
            self._hub_text("shop_enabled" if enabled else "shop_disabled"),
        )
        self._set_hud_class(
            "shop_purchase_button", "disabled",
            level >= entry["maxLevel"] or bPurchaseLocked,
        )
        self._set_hud_class("shop_enable_button", "disabled", level <= 0)
        self._set_hud_style(
            "shop_purchase_button", "display",
            "flex" if level < entry["maxLevel"] else "none",
        )
        self._set_hud_style(
            "shop_enable_button", "display",
            "flex" if level > 0 and entry.get("toggleable", True) else "none",
        )
        self._set_hud_style(
            "shop_refund_button", "display",
            "flex" if level > 0 else "none",
        )

    def _buy_focused_power_up(self):
        if not self.shop_purchase_debouncer.acquire(self.shop_focus_id):
            return {
                "status": "debounced",
                "powerUpId": self.shop_focus_id,
                "spentGold": 0,
            }
        level = self.profile.get("powerUps", {}).get(self.shop_focus_id, 0)
        receipt = self._purchase_power_up(self.shop_focus_id, level)
        self._refresh_hub()
        return receipt

    def _toggle_focused_power_up(self):
        entry = POWER_UP_BY_ID.get(self.shop_focus_id)
        if entry is None or not entry.get("toggleable", True):
            return False
        level = self.profile.get("powerUps", {}).get(self.shop_focus_id, 0)
        if level <= 0:
            return False
        enabled = self.profile.get("powerUpsEnabled", {}).get(self.shop_focus_id, True)
        receipt = self._set_power_up_enabled(self.shop_focus_id, not enabled)
        self._refresh_hub()
        return receipt["status"] == "updated"

    def _refund_focused_power_up(self):
        level = self.profile.get("powerUps", {}).get(self.shop_focus_id, 0)
        receipt = self._refund_power_up(self.shop_focus_id, level)
        self._refresh_hub()
        return receipt

    def _quest_visible(self, quest):
        if not isinstance(quest, dict):
            return False
        hidden_until = quest.get("hiddenUntil", "")
        if hidden_until == "meta_weapon_slots:3":
            return self.profile.get("powerUps", {}).get(
                SurvivorMetaProgression.WEAPON_SLOT_POWER_UP_ID,
                0,
            ) >= 3
        return True

    def _filtered_quests(self):
        visible_quests = tuple(
            quest for quest in QUESTS
            if self._quest_visible(quest)
        )
        if self.quest_filter == "all":
            return visible_quests
        if self.quest_filter == "character":
            return tuple(
                quest for quest in visible_quests
                if quest["category"] == "character"
            )
        if self.quest_filter == "combat":
            return tuple(
                quest for quest in visible_quests
                if quest["category"] in ("weapon", "trinket")
            )
        if self.quest_filter == "mastery":
            return tuple(
                quest for quest in visible_quests
                if quest["category"] in ("build", "difficulty")
            )
        if self.quest_filter == "untracked":
            tracked = set(self.profile.get("trackedQuests", []))
            return tuple(
                quest for quest in visible_quests
                if quest["id"] not in tracked
            )
        return visible_quests

    def _quest_progress(self, quest):
        career = self.profile["career"]
        metric = quest["metric"]
        career_values = {
            "runs": career["runs"], "kills": career["totalKills"],
            "boss_kills": career["totalBossKills"], "best_level": career["bestLevel"],
            "survival_seconds": int(career["bestSurvivalSeconds"]),
            "gold_earned": career["totalGoldEarned"],
            "quests_completed": len(self.profile.get("completedQuests", [])),
        }
        return min(
            quest["target"],
            max(career_values.get(metric, 0), self.profile.get("questProgress", {}).get(quest["id"], 0)),
        )

    def _refresh_quest_page(self):
        quests = self._filtered_quests()
        pages = max(1, (len(quests) + 9) // 10)
        self.quest_page = min(self.quest_page, pages - 1)
        visible = quests[self.quest_page * 10:self.quest_page * 10 + 10]
        visible_ids = tuple(quest["id"] for quest in visible)
        if self.quest_focus_id not in visible_ids:
            self.quest_focus_id = visible_ids[0] if visible_ids else ""
        self.quest_slot_map = {}
        completed = set(self.profile.get("completedQuests", []))
        tracked = set(self.profile.get("trackedQuests", []))
        for index in range(10):
            slot_id = "quest_slot_" + str(index)
            if index >= len(visible):
                self._set_hud_style(slot_id, "display", "none")
                continue
            self._set_hud_style(slot_id, "display", "flex")
            quest = visible[index]
            quest_id = quest["id"]
            self.quest_slot_map[slot_id] = quest_id
            progress = self._quest_progress(quest)
            self._set_hud_text(slot_id + "_name", self._localized_catalog_text(quest["title"]))
            self._set_hud_text(
                slot_id + "_progress",
                self._hub_text("quest_progress", value=progress, target=quest["target"]),
            )
            self._set_hud_text(
                slot_id + "_reward",
                self._hub_text("quest_completed")
                if quest_id in completed else "+" + str(quest["rewardGold"]),
            )
            self._set_hud_class(slot_id, "completed", quest_id in completed)
            self._set_hud_class(slot_id, "tracked", quest_id in tracked)
            self._set_hud_class(slot_id, "focused", quest_id == self.quest_focus_id)
            self._set_hud_class(slot_id, "selected_option", False)
        self._set_hud_text("quest_page_value", self._hub_text("page", page=self.quest_page + 1, pages=pages))
        self._set_exclusive_selection(
            tuple("quest_filter_" + category for category in (
                "all", "character", "combat", "mastery", "untracked",
            )),
            "quest_filter_" + self.quest_filter,
        )
        self._set_hud_text(
            "quest_completion_summary",
            str(len(completed)) + " / " + str(len(QUESTS)),
        )
        self._refresh_quest_focus()

    def _refresh_quest_focus(self):
        quest_by_id = {quest["id"]: quest for quest in QUESTS}
        quest = quest_by_id.get(self.quest_focus_id)
        if quest is None:
            self._set_hud_text("quest_detail_name", "—")
            self._set_hud_text("quest_detail_description", self._hub_text("empty_quests"))
            self._set_hud_style("quest_track_button", "display", "none")
            return
        self._set_hud_style("quest_track_button", "display", "flex")
        tracked = self.profile.get("trackedQuests", [])
        self._set_hud_text("quest_detail_name", self._localized_catalog_text(quest["title"]))
        self._set_hud_text("quest_detail_description", self._localized_catalog_text(quest["description"]))
        progress = self._quest_progress(quest)
        self._set_hud_text(
            "quest_detail_progress_text",
            self._hub_text("quest_progress", value=progress, target=quest["target"]),
        )
        self._set_hud_style(
            "quest_detail_progress_fill", "width",
            str(int(100 * progress / max(1, quest["target"]))) + "%",
        )
        self._set_hud_text("quest_detail_reward", "+" + str(quest["rewardGold"]))
        self._set_hud_text(
            "quest_detail_unlock",
            self._localized_unlock(
                quest.get("unlockType", ""), quest.get("unlockId", ""),
            ),
        )
        if self.quest_focus_id in tracked:
            label = self._hub_text("quest_untrack")
        elif len(tracked) >= 3:
            label = self._hub_text("quest_track_full")
        else:
            label = self._hub_text("quest_track")
        self._set_hud_text("quest_track_button_label", label)

    def _toggle_focused_quest_tracking(self):
        staged = SurvivorProfile.validate_profile(self.profile)
        tracked = staged["trackedQuests"]
        if self.quest_focus_id in tracked:
            tracked.remove(self.quest_focus_id)
        elif len(tracked) < 3:
            tracked.append(self.quest_focus_id)
        else:
            return False
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _refresh_collection_page(self):
        owned = self.profile["owned"]
        career = self.profile["career"]
        self._set_hud_text(
            "collection_completion_summary",
            self._hub_text(
                "collection_summary",
                characters=len(owned["characters"]), weapons=len(owned["weapons"]),
                tomes=len(owned["tomes"]), trinkets=len(owned["trinkets"]),
            ),
        )
        self._set_hud_text("collection_total_runs", str(career["runs"]))
        best_seconds = int(career["bestSurvivalSeconds"])
        self._set_hud_text("collection_best_time", f"{best_seconds // 60:02d}:{best_seconds % 60:02d}")
        self._set_hud_text("collection_total_kills", str(career["totalKills"]))
        self._set_hud_text("collection_top_weapon", "—")
        self._set_exclusive_selection(
            tuple("collection_tab_" + tab for tab in (
                "enemies", "bosses", "evolutions", "characters", "stats",
            )),
            "collection_tab_" + self.collection_tab,
        )
        self._set_hud_style(
            "collection_catalog_grid", "display",
            "none" if self.collection_tab == "stats" else "flex",
        )
        self._set_hud_style(
            "collection_stats_summary", "display",
            "flex" if self.collection_tab == "stats" else "none",
        )
        if self.collection_tab == "enemies":
            entries = ENEMIES
        elif self.collection_tab == "bosses":
            entries = BOSSES
        elif self.collection_tab == "characters":
            entries = CHARACTERS
        else:
            entries = EVOLUTIONS
        discovered = set(self.profile.get("discoveredEvolutions", []))
        for index in range(12):
            slot_id = "collection_slot_" + str(index)
            if index >= len(entries) or self.collection_tab == "stats":
                self._set_hud_style(slot_id, "display", "none")
                continue
            self._set_hud_style(slot_id, "display", "flex")
            entry = entries[index]
            bDiscovered = True
            symbol = "◆"
            if self.collection_tab == "evolutions":
                bDiscovered = entry["id"] in discovered
                title = self._localized_catalog_text(entry["name"]) if bDiscovered else "???"
                hint = self._localized_formula(
                    entry["weaponId"], entry["tomeId"], bDiscovered,
                )
                symbol = "◆" if bDiscovered else "?"
            elif self.collection_tab == "characters":
                state = self._character_state(entry["id"])
                title = self._localized_catalog_text(entry["name"])
                hint = self._hub_text("state_" + state)
                bDiscovered = state not in ("hidden", "locked")
                symbol = title[:1]
            else:
                title = self._localized_catalog_text(entry["name"])
                role = entry.get("behaviorId", entry.get("behavior", ""))
                hint = COLLECTION_ROLE_TEXT.get(
                    self.language, COLLECTION_ROLE_TEXT["en"],
                ).get(role, str(role).replace("_", " ").title())
                symbol = "B" if self.collection_tab == "bosses" else "M"
            icon_path = entry.get("icon", "") if bDiscovered else ""
            self._set_hud_attribute(slot_id + "_icon", "src", icon_path)
            self._set_hud_style(
                slot_id + "_icon", "display",
                "block" if icon_path else "none",
            )
            self._set_hud_text(slot_id + "_symbol", symbol)
            self._set_hud_style(
                slot_id + "_symbol", "display",
                "none" if icon_path else "block",
            )
            self._set_hud_text(slot_id + "_title", title)
            self._set_hud_text(slot_id + "_hint", hint)
            self._set_hud_class(slot_id, "discovered", bDiscovered)
            self._set_hud_class(slot_id, "silhouette", not bDiscovered)

    def _refresh_hub_settings(self):
        if not self.document_id:
            return
        self._set_hud_text(
            "hub_volume_value",
            str(int(round(self.master_volume * 100.0))) + "%",
        )
        opacity = str(int(round(self.player_projectile_opacity * 100))) + "%"
        self._set_hud_text("hub_projectile_opacity_value", opacity)
        self._set_hud_text("projectile_opacity_value_label", opacity)

        groups = (
            (("hub_language_zh", "hub_language_en"),
             "hub_language_zh" if self.language == "zh_cn" else "hub_language_en"),
            (("hub_vsync_on", "hub_vsync_off"),
             "hub_vsync_on" if self.bVSyncEnabled else "hub_vsync_off"),
            (("hub_display_fullscreen", "hub_display_windowed"),
             "hub_display_fullscreen" if self.bFullscreen else "hub_display_windowed"),
            (("hub_ui_scale_small", "hub_ui_scale_normal", "hub_ui_scale_large"),
             "hub_ui_scale_small" if self.ui_scale < 0.93 else
             "hub_ui_scale_large" if self.ui_scale > 1.07 else "hub_ui_scale_normal"),
            (("hub_motion_on", "hub_motion_off"),
             "hub_motion_on" if self.bMotionEnabled else "hub_motion_off"),
            (("hub_flash_on", "hub_flash_off"),
             "hub_flash_on" if self.bDamageFlashEnabled else "hub_flash_off"),
            (("hub_particle_density_auto", "hub_particle_density_low",
              "hub_particle_density_medium", "hub_particle_density_high"),
             "hub_particle_density_" + self.particle_density),
            (("hub_damage_numbers_off", "hub_damage_numbers_reduced",
              "hub_damage_numbers_full"),
             "hub_damage_numbers_" + self.damage_numbers_mode),
            (("hub_screen_shake_on", "hub_screen_shake_off"),
             "hub_screen_shake_on" if self.bScreenShakeEnabled else "hub_screen_shake_off"),
            (("hub_telegraph_color_default", "hub_telegraph_color_deuteranopia",
              "hub_telegraph_color_tritanopia", "hub_telegraph_color_high_contrast"),
             "hub_telegraph_color_" + self.enemy_telegraph_color),
            (("hub_auto_throttle_on", "hub_auto_throttle_off"),
             "hub_auto_throttle_on" if self.bAutoVisualThrottle else "hub_auto_throttle_off"),
        )
        for element_ids, selected_id in groups:
            self._set_exclusive_selection(element_ids, selected_id)

    def _apply_and_save_hub_setting(self):
        self._apply_settings()
        self._save_settings()

    def _select_difficulty(self, difficulty_id):
        if difficulty_id not in DIFFICULTY_BY_ID:
            return False
        clears = self.profile.get("difficultyClears", {})
        if difficulty_id == "fierce" and not clears.get("adventure", False):
            return False
        if difficulty_id == "nightmare" and not clears.get("fierce", False):
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        staged["selectedDifficulty"] = difficulty_id
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _select_weapon_slot_limit(self, weapon_slot_limit):
        if (
                isinstance(weapon_slot_limit, bool)
                or not isinstance(weapon_slot_limit, int)
                or weapon_slot_limit < SurvivorMetaProgression.BASE_WEAPON_SLOTS
                or weapon_slot_limit > SurvivorMetaProgression.purchased_weapon_slot_limit(
                    self.profile,
                )):
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        staged["selectedWeaponSlotLimit"] = weapon_slot_limit
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _select_challenge(self, challenge_id):
        if challenge_id not in CHALLENGE_BY_ID:
            return False
        staged = SurvivorProfile.validate_profile(self.profile)
        valid_ids = tuple(entry["id"] for entry in CHALLENGES)
        selected = SurvivorRules.toggle_challenge_id(
            staged.get("selectedChallenges", ()), challenge_id, valid_ids,
        )
        staged["selectedChallenges"] = list(selected)
        staged["selectedChallenge"] = selected[0] if selected else "none"
        if not self._save_progression(staged):
            return False
        self._refresh_hub()
        return True

    def _cycle_setting(self, name, values):
        current = getattr(self, name)
        index = values.index(current) if current in values else 0
        setattr(self, name, values[(index + 1) % len(values)])
        self._save_settings()
        self._apply_settings()
        self._refresh_hub_settings()

    def _refresh_result_details(self):
        last_run = self.profile.get("lastRun") or {}
        reward = last_run.get("reward", {})
        result_summary = last_run.get("resultSummary", {})
        if not isinstance(result_summary, dict):
            result_summary = {}
        earned = reward.get("earnedGold", 0)
        result_text = RESULT_TEXT.get(self.language, RESULT_TEXT["zh_cn"])
        for element_id, text in result_text.items():
            if element_id.startswith("reason_") or element_id in (
                    "result_reason", "commit_saved", "commit_failed", "distance_unit"):
                continue
            self._set_hud_text(element_id, text)
        minutes = int(self.elapsed // 60)
        seconds = int(self.elapsed % 60)
        self._set_hud_text("final_time_value", f"{minutes:02d}:{seconds:02d}")
        self._set_hud_text("final_elites_value", str(getattr(self, "run_elite_kills", 0)))
        self._set_hud_text("final_bosses_value", str(self.run_boss_kills))
        end_reason = str(last_run.get("endReason", "death"))
        reason_text = result_text.get(
            "reason_" + end_reason,
            end_reason.replace("_", " ").title(),
        )
        self._set_hud_text(
            "result_end_reason", result_text["result_reason"].format(reason=reason_text),
        )
        self._set_hud_text("result_gold_total", str(earned))
        self._set_hud_text("result_gold_time", "+" + str(reward.get("timeGold", 0)))
        self._set_hud_text("result_gold_kills", "+" + str(reward.get("killGold", 0)))
        self._set_hud_text(
            "result_gold_elite_boss",
            "+" + str(reward.get("eliteGold", 0) + reward.get("bossGold", 0)),
        )
        self._set_hud_text(
            "result_gold_clear_difficulty",
            "+" + str(reward.get("clearGold", 0)) + " · ×" + f"{reward.get('difficultyFactor', 1.0):.2f}",
        )
        self._set_hud_text("result_gold_quests", "+" + str(reward.get("questGold", 0)))
        weapon_slot_limit = last_run.get(
            "weaponSlotLimit",
            SurvivorMetaProgression.selected_weapon_slot_limit(self.profile),
        )
        self._set_hud_text("result_weapon_slot_limit", str(weapon_slot_limit))
        self._set_hud_text(
            "result_weapon_slot_bonus",
            "+" + str(reward.get("weaponSlotBonusGold", 0))
            + " · ×" + f"{reward.get('weaponSlotFactor', 1.0):.2f}",
        )
        self._set_hud_text("result_damage_taken", str(int(getattr(self, "run_damage_taken", 0.0))))
        self._set_hud_text(
            "result_damage_prevented",
            str(int(getattr(self, "run_damage_prevented", 0.0))),
        )
        self._set_hud_text("result_healing", str(int(getattr(self, "run_healed", 0.0))))
        self._set_hud_text(
            "result_distance_moved",
            str(int(getattr(self, "run_distance_moved", 0.0)))
            + " " + result_text["distance_unit"],
        )
        region_aliases = {
            "north_rift": "star", "EventAnchor_NorthRift": "star",
            "west_shrine": "thunder", "EventAnchor_WestShrine": "thunder",
            "south_wetland": "water", "EventAnchor_SouthWetland": "water",
            "east_basin": "wind", "EventAnchor_EastBasin": "wind",
            "domain_star": "star", "domain_thunder": "thunder",
            "domain_water": "water", "domain_wind": "wind",
        }

        def region_name(region_id):
            canonical_id = region_aliases.get(str(region_id), str(region_id))
            return self._hub_text("region_" + canonical_id)

        activation_order = result_summary.get("regionActivationOrder", ())
        if not isinstance(activation_order, (list, tuple)):
            activation_order = ()
        self._set_hud_text(
            "result_region_order",
            " → ".join(region_name(region_id) for region_id in activation_order)
            or self._hub_text("result_none"),
        )

        def region_counter_text(value):
            def count_text(count):
                try:
                    return str(max(0, int(count)))
                except (TypeError, ValueError, OverflowError):
                    return "0"

            if not isinstance(value, dict):
                return (
                    count_text(value)
                    if isinstance(value, (int, float)) else
                    self._hub_text("result_none")
                )
            return " · ".join(
                region_name(region_id) + " " + count_text(count)
                for region_id, count in value.items()
            ) or self._hub_text("result_none")

        self._set_hud_text(
            "result_region_attempts",
            region_counter_text(result_summary.get("regionAttempts", {})),
        )
        self._set_hud_text(
            "result_region_exits",
            region_counter_text(result_summary.get("regionExitFailures", {})),
        )
        domain_stats = result_summary.get("domainStats", {})
        if isinstance(domain_stats, dict):
            domain_rows = []
            for domain_id, values in domain_stats.items():
                values = values if isinstance(values, dict) else {}
                try:
                    damage = max(0.0, float(values.get("damage", 0.0)))
                    control_time = max(0.0, float(values.get("controlTime", 0.0)))
                except (TypeError, ValueError, OverflowError):
                    damage = 0.0
                    control_time = 0.0
                domain_rows.append(
                    region_name(domain_id)
                    + " " + str(int(damage))
                    + " / " + f"{control_time:.1f}s"
                )
            domain_summary = " · ".join(domain_rows)
        else:
            domain_summary = str(domain_stats) if domain_stats else ""
        self._set_hud_text(
            "result_domain_summary",
            domain_summary or self._hub_text("result_none"),
        )
        boss_ttk = result_summary.get("bossTtkSeconds")
        self._set_hud_text(
            "result_boss_ttk",
            self._hub_text("result_seconds", value=f"{float(boss_ttk):.1f}")
            if isinstance(boss_ttk, (int, float)) else
            self._hub_text("result_none"),
        )
        committed = bool(last_run.get("rewardCommitted", False))
        self._set_hud_text(
            "result_commit_status_label",
            result_text["commit_saved"] if committed else result_text["commit_failed"],
        )
        self._set_hud_class("result_commit_status", "result_commit_pending", not committed)
        self._set_hud_class("result_commit_status", "result_commit_saved", committed)
        ranked = sorted(
            self.weapon_telemetry.items(), key=lambda item: item[1].get("damage", 0.0), reverse=True,
        )
        for index in range(6):
            weapon_id = ""
            values = {}
            if index < len(ranked) and ranked[index][1].get("damage", 0.0) > 0.0:
                weapon_id, values = ranked[index]
            prefix = "result_weapon_slot_" + str(index)
            self._set_hud_text(
                prefix + "_name",
                self._localized_content_name(weapon_id) if weapon_id else "—",
            )
            self._set_hud_text(prefix + "_damage", str(int(values.get("damage", 0.0))))
            self._set_hud_text(prefix + "_dps", f"{values.get('damage', 0.0) / max(1.0, self.elapsed):.1f}")
            self._set_hud_text(prefix + "_hits", str(values.get("hits", 0)))
            self._set_hud_text(prefix + "_crits", str(values.get("criticalHits", 0)))
            self._set_hud_text(prefix + "_kills", str(values.get("kills", 0)))
            self._set_hud_text(prefix + "_level", str(self._weapon_level(weapon_id)) if weapon_id else "—")

    @staticmethod
    def _slot_index(source_id, prefix, count):
        if not source_id.startswith(prefix):
            return None
        suffix = source_id[len(prefix):].split("_")[0]
        try:
            index = int(suffix)
        except ValueError:
            return None
        return index if 0 <= index < count else None

    def _handle_hub_ui_event(self, source_id, event_type):
        if event_type == "mousedown" and source_id.startswith("armory_filter_"):
            armory_filter = source_id[len("armory_filter_"):]
            if armory_filter in ("all", "owned", "eligible", "locked", "disabled"):
                self.armory_filter = armory_filter
                self.armory_page = 0
                self._refresh_armory_page()
            return True
        if event_type == "mousedown" and source_id.startswith("quest_filter_"):
            quest_filter = source_id[len("quest_filter_"):]
            if quest_filter in ("all", "character", "combat", "mastery", "untracked"):
                self.quest_filter = quest_filter
                self.quest_page = 0
                self._refresh_quest_page()
            return True
        if event_type != "click":
            return False
        if source_id in SurvivorHubNavigation.focus_ids(self._hub_focus_rows()):
            self._set_hub_focus(source_id, False)
        nav = {
            "hub_nav_play": "play", "hub_nav_characters": "characters",
            "hub_nav_armory": "armory", "hub_nav_shop": "shop",
            "hub_nav_quests": "quests", "hub_nav_collection": "collection",
            "hub_nav_settings": "settings",
        }
        if source_id in nav:
            self._show_hub_page(nav[source_id])
            return True
        if source_id in ("hub_language_zh", "hub_language_en"):
            self._set_language("zh_cn" if source_id.endswith("_zh") else "en")
            return True
        if source_id in ("hub_volume_down", "hub_volume_up"):
            delta = -0.1 if source_id.endswith("_down") else 0.1
            self._set_master_volume(self.master_volume + delta)
            self._refresh_hub_settings()
            return True
        if source_id in ("hub_vsync_on", "hub_vsync_off"):
            self._set_vsync(source_id.endswith("_on"))
            self._refresh_hub_settings()
            return True
        if source_id in ("hub_display_fullscreen", "hub_display_windowed"):
            self._set_fullscreen(source_id.endswith("_fullscreen"))
            self._refresh_hub_settings()
            return True
        if source_id.startswith("hub_ui_scale_"):
            scales = {"small": 0.85, "normal": 1.0, "large": 1.15}
            scale_id = source_id[len("hub_ui_scale_"):]
            if scale_id in scales:
                self._set_ui_scale(scales[scale_id])
                self._refresh_hub_settings()
            return True
        if source_id in ("hub_motion_on", "hub_motion_off"):
            self._set_motion_enabled(source_id.endswith("_on"))
            self._refresh_hub_settings()
            return True
        if source_id in ("hub_flash_on", "hub_flash_off"):
            self._set_damage_flash_enabled(source_id.endswith("_on"))
            self._refresh_hub_settings()
            return True
        if source_id in ("hub_projectile_opacity_down", "hub_projectile_opacity_up"):
            delta = -0.05 if source_id.endswith("_down") else 0.05
            self.player_projectile_opacity = max(
                0.25, min(1.0, self.player_projectile_opacity + delta),
            )
            self._apply_and_save_hub_setting()
            return True
        if source_id.startswith("hub_particle_density_"):
            density = source_id[len("hub_particle_density_"):]
            if density in ("auto", "low", "medium", "high"):
                self.particle_density = density
                self._apply_and_save_hub_setting()
            return True
        if source_id.startswith("hub_damage_numbers_"):
            mode = source_id[len("hub_damage_numbers_"):]
            if mode in ("off", "reduced", "full"):
                self.damage_numbers_mode = mode
                self._apply_and_save_hub_setting()
            return True
        if source_id in ("hub_screen_shake_on", "hub_screen_shake_off"):
            self.bScreenShakeEnabled = source_id.endswith("_on")
            self._apply_and_save_hub_setting()
            return True
        if source_id.startswith("hub_telegraph_color_"):
            color_mode = source_id[len("hub_telegraph_color_"):]
            if color_mode in ("default", "deuteranopia", "tritanopia", "high_contrast"):
                self.enemy_telegraph_color = color_mode
                self._apply_and_save_hub_setting()
            return True
        if source_id in ("hub_auto_throttle_on", "hub_auto_throttle_off"):
            self.bAutoVisualThrottle = source_id.endswith("_on")
            self._apply_and_save_hub_setting()
            return True
        if source_id == "hub_settings_defaults_button":
            self._restore_settings_defaults()
            return True
        if source_id == "play_change_character_button":
            self._show_hub_page("characters"); return True
        if source_id == "play_seed_button":
            self.selected_run_seed = (
                1664525 * int(self.selected_run_seed) + 1013904223
            ) & 0xFFFFFFFF
            self._refresh_play_page(); return True
        if source_id.startswith("weapon_limit_"):
            try:
                weapon_slot_limit = int(source_id[len("weapon_limit_"):])
            except ValueError:
                return True
            self._select_weapon_slot_limit(weapon_slot_limit)
            return True
        character_index = self._slot_index(source_id, "character_slot_", 10)
        if character_index is not None:
            content_id = self.character_slot_map.get("character_slot_" + str(character_index))
            if content_id:
                self._set_preview_character(content_id)
            return True
        if source_id.startswith("character_"):
            character_id = source_id[len("character_"):]
            if character_id in CHARACTER_BY_ID and self.hub_page == "characters":
                self._set_preview_character(character_id); return True
        if source_id == "character_purchase_button":
            self._purchase_preview_character(); return True
        if source_id == "character_use_button":
            self._use_preview_character(); return True
        if source_id == "character_training_button":
            self._train_preview_character(); return True
        if source_id == "character_training_toggle_button":
            self._toggle_preview_training(); return True
        if source_id == "character_preview_dance":
            self._play_preview_dance(); return True
        if source_id == "character_preview_idle":
            self._restore_preview_idle(); return True
        if source_id == "character_rotate_left":
            self._rotate_preview(-0.35); return True
        if source_id == "character_rotate_right":
            self._rotate_preview(0.35); return True
        if source_id == "character_zoom_in":
            self._zoom_preview(0.08); return True
        if source_id == "character_zoom_out":
            self._zoom_preview(-0.08); return True
        if source_id == "character_preview_reset":
            self._reset_preview_transform(self.preview_character_id)
            self._restore_preview_idle(); return True
        if source_id.startswith("armory_tab_"):
            tab = source_id[len("armory_tab_"):]
            if tab in ARMORY_DATA:
                self.armory_tab = tab; self.armory_page = 0
                if tab == "evolutions":
                    self.armory_filter = "all"
                self.armory_focus_id = ARMORY_DATA[tab][0]["id"]
                self._refresh_armory_page()
            return True
        if source_id.startswith("armory_filter_"):
            armory_filter = source_id[len("armory_filter_"):]
            if armory_filter in ("all", "owned", "eligible", "locked", "disabled"):
                self.armory_filter = armory_filter; self.armory_page = 0
                self._refresh_armory_page()
            return True
        armory_index = self._slot_index(source_id, "armory_slot_", 10)
        if armory_index is not None:
            content_id = self.armory_slot_map.get("armory_slot_" + str(armory_index))
            if content_id:
                self.armory_focus_id = content_id; self._refresh_armory_page()
            return True
        if source_id == "armory_page_previous":
            self.armory_page = max(0, self.armory_page - 1); self._refresh_armory_page(); return True
        if source_id == "armory_page_next":
            self.armory_page += 1; self._refresh_armory_page(); return True
        if source_id == "armory_toggle_button":
            self._toggle_armory_pool(); return True
        if source_id == "armory_pool_toggle_all":
            self._toggle_all_armory_pool(); return True
        if source_id == "armory_purchase_button":
            self._purchase_armory_focus(); return True
        shop_index = self._slot_index(
            source_id, "powerup_node_", len(POWER_UPS),
        )
        if shop_index is not None:
            power_up_id = self.shop_slot_map.get("powerup_node_" + str(shop_index))
            if power_up_id:
                self.shop_focus_id = power_up_id; self._refresh_shop_page()
            return True
        if source_id == "shop_purchase_button":
            self._buy_focused_power_up(); return True
        if source_id == "shop_enable_button":
            self._toggle_focused_power_up(); return True
        if source_id == "shop_refund_button":
            self._refund_focused_power_up(); return True
        if source_id == "shop_refund_all_button":
            self._refund_all_power_ups(); self._refresh_hub(); return True
        if source_id.startswith("quest_filter_"):
            self.quest_filter = source_id[len("quest_filter_"):]
            self.quest_page = 0; self._refresh_quest_page(); return True
        quest_index = self._slot_index(source_id, "quest_slot_", 10)
        if quest_index is not None:
            quest_id = self.quest_slot_map.get("quest_slot_" + str(quest_index))
            if quest_id:
                self.quest_focus_id = quest_id; self._refresh_quest_page()
            return True
        if source_id == "quest_page_previous":
            self.quest_page = max(0, self.quest_page - 1); self._refresh_quest_page(); return True
        if source_id == "quest_page_next":
            self.quest_page += 1; self._refresh_quest_page(); return True
        if source_id == "quest_track_button":
            self._toggle_focused_quest_tracking(); return True
        tracked_index = self._slot_index(source_id, "tracked_quest_slot_", 3)
        if tracked_index is not None:
            quest_id = self.tracked_quest_slot_map.get(
                "tracked_quest_slot_" + str(tracked_index),
            )
            if quest_id:
                self.quest_filter = "all"
                self.quest_focus_id = quest_id
                quest_ids = [quest["id"] for quest in QUESTS]
                self.quest_page = quest_ids.index(quest_id) // 10
                self._show_hub_page("quests")
            return True
        if source_id.startswith("collection_tab_"):
            tab = source_id[len("collection_tab_"):]
            if tab in ("enemies", "bosses", "evolutions", "characters", "stats"):
                self.collection_tab = tab
                self._refresh_collection_page()
            return True
        if source_id.startswith("difficulty_"):
            self._select_difficulty(source_id[len("difficulty_"):]); return True
        challenge_index = self._slot_index(source_id, "challenge_slot_", 6)
        if challenge_index is not None:
            challenge_id = self.challenge_slot_map.get("challenge_slot_" + str(challenge_index))
            if challenge_id:
                self._select_challenge(challenge_id)
            return True
        if source_id == "projectile_opacity_down":
            self.player_projectile_opacity = max(0.25, self.player_projectile_opacity - 0.05)
            self._save_settings(); self._apply_settings(); self._refresh_hub_settings(); return True
        if source_id == "projectile_opacity_up":
            self.player_projectile_opacity = min(1.0, self.player_projectile_opacity + 0.05)
            self._save_settings(); self._apply_settings(); self._refresh_hub_settings(); return True
        if source_id.startswith("particle_density_"):
            self.particle_density = source_id[len("particle_density_"):]
            self._save_settings(); self._apply_settings(); return True
        if source_id.startswith("damage_numbers_"):
            self.damage_numbers_mode = source_id[len("damage_numbers_"):]
            self._save_settings(); self._apply_settings(); return True
        if source_id in ("screen_shake_on", "screen_shake_off"):
            self.bScreenShakeEnabled = source_id.endswith("_on")
            self._save_settings(); self._apply_settings(); return True
        if source_id.startswith("telegraph_color_"):
            self.enemy_telegraph_color = source_id[len("telegraph_color_"):]
            self._save_settings(); self._apply_settings(); return True
        if source_id in ("auto_throttle_on", "auto_throttle_off"):
            self.bAutoVisualThrottle = source_id.endswith("_on")
            self._save_settings(); self._apply_settings(); return True
        if source_id == "result_commit_retry_button":
            reason = getattr(self, "run_end_reason", "death")
            self._finish_run(reason); self._sync_game_over_text(); return True
        if source_id == "result_adjust_build_button":
            if self._return_to_start_menu():
                self._show_hub_page("armory")
            return True
        return False
