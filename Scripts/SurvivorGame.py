import importlib
import math
import os
import time

import HEngine
import SurvivorDomainPowers
import SurvivorHub
import SurvivorObjectives
import SurvivorPresentation
import SurvivorProgression
import SurvivorCombatHooks
import SurvivorSession
import SurvivorWorld
import SurvivorWeapons
import SurvivorRunConfig

from SurvivorContent import (
    CHARACTER_DEFS,
    CHARACTER_ORDER,
    CONTENT_TEXT,
    MAX_TOME_SLOTS,
    MAX_WEAPON_SLOTS,
    TOME_DEFS,
    TOME_ORDER,
    WEAPON_DEFS,
    WEAPON_ORDER,
    validate_catalog,
)
from SurvivorAudio import SurvivorAudio
from SurvivorCatalog import (
    BOSSES as CATALOG_BOSSES,
    BOSS_EVENTS as CATALOG_BOSS_EVENTS,
    CHALLENGES as CATALOG_CHALLENGES,
    DIFFICULTIES as CATALOG_DIFFICULTIES,
    ENEMIES as CATALOG_ENEMIES,
    WAVES as CATALOG_WAVES,
)
from SurvivorRules import ProjectileBudget, compile_character_start_state, due_weapon_ids
from SurvivorQuests import SurvivorQuestTracker
from SurvivorTelemetry import SurvivorTelemetry
from SurvivorRuntimeAssets import asset_path
from HEngineUI.motion import UIAnimationDirector, UIScreenStack


if globals().get("_SURVIVOR_MIXINS_IMPORTED", False):
    SurvivorHub = importlib.reload(SurvivorHub)
    SurvivorDomainPowers = importlib.reload(SurvivorDomainPowers)
    SurvivorObjectives = importlib.reload(SurvivorObjectives)
    SurvivorPresentation = importlib.reload(SurvivorPresentation)
    SurvivorProgression = importlib.reload(SurvivorProgression)
    SurvivorCombatHooks = importlib.reload(SurvivorCombatHooks)
    SurvivorWorld = importlib.reload(SurvivorWorld)
    SurvivorWeapons = importlib.reload(SurvivorWeapons)
    SurvivorRunConfig = importlib.reload(SurvivorRunConfig)
_SURVIVOR_MIXINS_IMPORTED = True

SurvivorHubMixin = SurvivorHub.SurvivorHubMixin
SurvivorDomainPowersMixin = SurvivorDomainPowers.SurvivorDomainPowersMixin
SurvivorObjectivesMixin = SurvivorObjectives.SurvivorObjectivesMixin
SurvivorPresentationMixin = SurvivorPresentation.SurvivorPresentationMixin
SurvivorProgressionMixin = SurvivorProgression.SurvivorProgressionMixin
SurvivorCombatHooksMixin = SurvivorCombatHooks.SurvivorCombatHooksMixin
SurvivorWorldMixin = SurvivorWorld.SurvivorWorldMixin
SurvivorWeaponsMixin = SurvivorWeapons.SurvivorWeaponsMixin


RmlUI = HEngine.RmlUI
_SETTINGS_CONTROL_IDS = frozenset((
    "settings_back_button", "settings_defaults_button",
    "language_zh", "language_en",
    "volume_down", "volume_up",
    "vsync_on", "vsync_off",
    "display_fullscreen", "display_windowed",
    "ui_scale_small", "ui_scale_normal", "ui_scale_large",
    "motion_on", "motion_off", "flash_on", "flash_off",
    "projectile_opacity_down", "projectile_opacity_up",
    "particle_density_auto", "particle_density_low",
    "particle_density_medium", "particle_density_high",
    "damage_numbers_off", "damage_numbers_reduced", "damage_numbers_full",
    "screen_shake_on", "screen_shake_off",
    "telegraph_color_default", "telegraph_color_deuteranopia",
    "telegraph_color_tritanopia", "telegraph_color_high_contrast",
    "auto_throttle_on", "auto_throttle_off",
))
_PROFILE_GAMEPLAY_FRAME = getattr(HEngine, "_MarkSurvivorGameplayFrame", None)
_PROFILE_STAGE_CALL = getattr(HEngine, "_ProfileSurvivorStage", None)
_PROFILE_STAGE_ENUM = getattr(HEngine, "_SurvivorProfileStage", None)
_PROFILE_ENABLED = (
    _PROFILE_GAMEPLAY_FRAME is not None and
    _PROFILE_STAGE_CALL is not None and
    _PROFILE_STAGE_ENUM is not None
)
_STAGE_TIMING_ENABLED = os.environ.get("HE_SURVIVOR_STAGE_TIMINGS") == "1"
_STAGE_TIMING_SAMPLES = 0
_STAGE_TIMING_TOTALS = {}
_STAGE_TIMING_PEAKS = {}
_STAGE_FRAME_MS = {}


def _profile_stage(name):
    if not _PROFILE_ENABLED or _STAGE_TIMING_ENABLED:
        if not _STAGE_TIMING_ENABLED:
            return lambda function: function

        def decorate(function):
            def profiled(*args, **kwargs):
                global _STAGE_TIMING_SAMPLES
                if name == "Update":
                    _STAGE_FRAME_MS.clear()
                start_ns = time.perf_counter_ns()
                try:
                    return function(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
                    _STAGE_TIMING_TOTALS[name] = _STAGE_TIMING_TOTALS.get(name, 0.0) + elapsed_ms
                    _STAGE_TIMING_PEAKS[name] = max(
                        _STAGE_TIMING_PEAKS.get(name, 0.0), elapsed_ms,
                    )
                    _STAGE_FRAME_MS[name] = _STAGE_FRAME_MS.get(name, 0.0) + elapsed_ms
                    if name == "Update":
                        if elapsed_ms > 8.0:
                            details = " ".join(
                                "{}={:.3f}".format(stage, duration)
                                for stage, duration in sorted(_STAGE_FRAME_MS.items())
                            )
                            HEngine.HE_CORE_INFO(
                                "[SurvivorStageSpike] elapsed={:.3f} {}".format(
                                    getattr(args[0], "elapsed", 0.0), details,
                                )
                            )
                        _STAGE_TIMING_SAMPLES += 1
                        if _STAGE_TIMING_SAMPLES == 60:
                            details = " ".join(
                                "{}={:.3f}/{:.3f}".format(
                                    stage,
                                    total / _STAGE_TIMING_SAMPLES,
                                    _STAGE_TIMING_PEAKS[stage],
                                )
                                for stage, total in sorted(_STAGE_TIMING_TOTALS.items())
                            )
                            HEngine.HE_CORE_INFO(
                                "[SurvivorStageTiming] mean/max ms over 60 frames: " + details
                            )
                            _STAGE_TIMING_SAMPLES = 0
                            _STAGE_TIMING_TOTALS.clear()
                            _STAGE_TIMING_PEAKS.clear()
            profiled.__name__ = function.__name__
            profiled.__qualname__ = function.__qualname__
            return profiled
        return decorate

    stage = getattr(_PROFILE_STAGE_ENUM, name)

    def decorate(function):
        if name == "Hud":
            def profiled(*args, **kwargs):
                result = _PROFILE_STAGE_CALL(stage, function, *args, **kwargs)
                _PROFILE_GAMEPLAY_FRAME()
                return result
        else:
            def profiled(*args, **kwargs):
                return _PROFILE_STAGE_CALL(stage, function, *args, **kwargs)
        profiled.__name__ = function.__name__
        profiled.__qualname__ = function.__qualname__
        return profiled

    return decorate


def _timed_stage_call(name, function, *args):
    if not _STAGE_TIMING_ENABLED:
        return function(*args)
    start_ns = time.perf_counter_ns()
    try:
        return function(*args)
    finally:
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        _STAGE_TIMING_TOTALS[name] = _STAGE_TIMING_TOTALS.get(name, 0.0) + elapsed_ms
        _STAGE_TIMING_PEAKS[name] = max(
            _STAGE_TIMING_PEAKS.get(name, 0.0), elapsed_ms,
        )
        _STAGE_FRAME_MS[name] = _STAGE_FRAME_MS.get(name, 0.0) + elapsed_ms


def _catalog_archetype_view(entry, bBoss=False):
    attack_set = entry["attackSet"]
    resistance_source = entry["resistances"]
    return {
        "id": entry["id"],
        "name_zh": entry["name"]["zh_cn"],
        "name_en": entry["name"]["en"],
        "prefab": entry["prefab"],
        "controller": entry["controller"],
        "scale": entry["scale"],
        "health": entry["health"],
        "speed": entry["speed"],
        "damage": entry["damage"],
        "radius": entry["radius"],
        "reward": entry["rewardXp"],
        "behavior": "boss" if bBoss else entry["behaviorId"],
        "attack": {
            "range": entry["radius"] + 0.42,
            "preferred_range": entry["preferredRange"],
            "cooldown": entry["cooldown"],
            "source_cooldown": 0.65,
            "telegraph": max(0.85 if bBoss else 0.35, entry["telegraph"]),
            "active": 0.12,
            "recovery": 0.36 if bBoss else 0.22,
            "charge_speed": 9.0,
            "projectile_speed": 7.5,
            "projectile_lifetime": 2.4,
            "projectile_radius": 0.28,
            "projectile_damage_scale": 1.0,
            "zone_radius": 2.4 if bBoss else 1.6,
            "zone_duration": 2.4 if bBoss else 2.0,
            "zone_tick": 0.5,
            "zone_damage_scale": 0.75,
            "suicide_damage_scale": 1.5,
            "shield": 60.0 if entry["behaviorId"] in ("shield", "boss_orc") else 0.0,
            "shield_duration": 2.0,
            "summon_count": 4 if "summon" in " ".join(attack_set) else 0,
        },
        "resistances": {
            "damage": float(resistance_source.get("damage", 0.0)),
            "slow": float(resistance_source.get("slow", 0.0)),
            "freeze": float(resistance_source.get("freeze", 0.0)),
            "poison": float(resistance_source.get("poison", 0.0)),
            "knockback": float(resistance_source.get("knockback", 0.0)),
        },
        "boss_phase": 1 if bBoss else 0,
    }


SURVIVOR_TEXT = {
    "zh_cn": {
        "survive_banner": "星光冒险开始！",
        "region_objective_title": "四域净化",
        "domain_power_title": "区域权能",
        "region_arming_banner": "区域正在回应……",
        "region_assault_banner": "净化开始：守住光圈 60 秒！",
        "region_grace_banner": "已离开光圈，计时暂停！",
        "region_resumed_banner": "已返回光圈，继续净化！",
        "region_failed_banner": "净化失败，区域冷却 12 秒",
        "region_complete_banner": "区域净化完成，权能觉醒！",
        "boss_ready_banner": "四域合流：返回中央星台！",
        "boss_intro_banner": "星台正在召唤星外巨龙……",
        "region_completed": "已净化 {count} / 4",
        "region_star_name": "星之区域",
        "region_thunder_name": "雷之区域",
        "region_water_name": "水之区域",
        "region_wind_name": "风之区域",
        "region_state_dormant": "沉寂",
        "region_state_arming": "响应中",
        "region_state_assault": "守卫中",
        "region_state_outside_grace": "离圈宽限",
        "region_state_cooldown": "冷却中",
        "region_state_activated": "已净化",
        "direction_north": "北",
        "direction_west": "西",
        "direction_south": "南",
        "direction_east": "东",
        "region_direction": "{direction} · {distance}m",
        "region_explore_hint": "寻找未净化区域",
        "region_explore_instruction": "追随区域光柱，进入光圈启动净化",
        "region_arming_instruction": "保持停留，正在展开净化穹顶",
        "region_hold_instruction": "留在穹顶范围内 · 击退来袭怪物",
        "region_grace_instruction": "立即返回穹顶！净化计时已暂停",
        "region_grace_countdown": "返回 {seconds}s",
        "region_cooldown_instruction": "净化中断 · 等待区域重新响应",
        "region_complete_instruction": "区域已净化 · 权能持续生效",
        "region_current_none": "寻找未净化区域",
        "region_navigation": "{direction} · {distance}m",
        "domain_star_name": "星落权能",
        "domain_thunder_name": "雷霆权能",
        "domain_water_name": "潮汐权能",
        "domain_wind_name": "风暴权能",
        "weapon_slot_locked": "未解锁槽位",
        "weapon_slot_empty": "空槽位",
        "boss_ready_objective": "返回中央星台并停留 2 秒",
        "objective_find_regions": "前往任意未净化区域",
        "objective_hold_region": "{region} · 穹顶内防守",
        "objective_return_region": "{region} · 立即返回穹顶",
        "objective_return_center": "返回中央星台 · {distance}m",
        "objective_defeat_boss": "击败目标：星外巨龙",
        "elite_banner": "小心，厉害的家伙来啦！",
        "critical_banner": "漂亮一击！",
        "chest_evolution_banner": "武器进化！星光形态觉醒！",
        "chest_trinket_banner": "获得一件闪亮奇物！",
        "chest_upgrade_banner": "星匣强化了一件装备！",
        "chest_gold_banner": "星匣里装满了金币！",
        "upgrade_skip_name": "跳过本次成长",
        "level": "等级 {level}",
        "kills": "击杀 {count}",
        "enemy_count": "附近怪物 {count}",
        "experience": "经验 {current} / {required}  ·  {percent}%",
        "experience_ready": "升级啦！  等级 {level}",
        "shards": "星光碎片 {count}",
        "score_label": "冒险得分",
        "timer_caption": "本轮时间",
        "controls_move": "移动",
        "controls_jump_key": "空格",
        "controls_jump": "跳跃",
        "controls_camera_key": "右键",
        "controls_camera": "环绕视角",
        "controls_auto": "自动攻击",
        "boss_name": "大块头来啦",
        "health_label": "生命",
        "weapon_title": "魔法小背包",
        "thunder_label": "雷霆",
        "ring_label": "波纹环",
        "fireball_label": "火球",
        "weapon_value": "{level}级 · {damage}伤害",
        "weapon_evolved_value": "已进化",
        "locked": "未解锁",
        "start_eyebrow": "软绵绵的星光冒险",
        "start_title": "小树保卫者",
        "start_subtitle": "带上会自己施法的小背包，在怪物浪潮里收集闪闪发亮的成长礼物。",
        "start_feature_magic": "自动魔法",
        "start_feature_cozy": "可爱怪潮",
        "start_feature_growth": "每局新成长",
        "start_button": "开始冒险",
        "start_settings_button": "设置",
        "start_hint": "进入冒险后，按 ESC 可以随时休息。",
        "loading_eyebrow": "星光正在集结",
        "loading_title": "准备软绵绵的冒险",
        "loading_subtitle": "魔法背包正在把可爱伙伴和闪亮礼物装进今晚的旅程。",
        "loading_effects": "正在唤醒魔法特效",
        "loading_monsters": "正在邀请怪物伙伴",
        "loading_pickup": "正在打包星光礼物",
        "loading_resources": "正在铺好冒险道路",
        "loading_ready": "星光就位，出发！",
        "loading_hint": "星光铺好道路后，冒险会自动开始。",
        "level_up": "升级啦！",
        "upgrade_title": "等级 {level}",
        "upgrade_subtitle": "挑一个喜欢的能力吧",
        "upgrade_flavor": "每次成长，都会让冒险轻松一点点。",
        "upgrade_level_caption": "当前等级",
        "choice_prompt": "三选一 · 选择一份成长礼物",
        "upgrade_hint_mouse": "移动鼠标选择，点击卡片确认",
        "upgrade_reroll": "重抽",
        "upgrade_skip": "跳过",
        "upgrade_banish": "放逐所选",
        "upgrade_banish_confirm": "确认放逐",
        "upgrade_kind_passive": "绘本 · 被动",
        "upgrade_kind_weapon": "自动武器",
        "upgrade_rank_permanent": "永久强化",
        "upgrade_rank_unlock": "首次解锁",
        "upgrade_rank_level": "{current}级 → {next}级",
        "rarity_common": "常规",
        "rarity_rare": "闪亮",
        "rarity_new": "新能力",
        "pause_title": "休息一下",
        "pause_subtitle": "冒险已经暂停，准备好再继续吧。",
        "resume_button": "继续冒险",
        "pause_settings_button": "设置",
        "pause_restart_button": "重新开始",
        "pause_home_button": "返回开始界面",
        "pause_hint_text": "返回游戏",
        "settings_eyebrow": "舒适小屋",
        "settings_title": "设置",
        "settings_back_button": "返回",
        "settings_language_label": "语言",
        "settings_language_desc": "选择冒险中的文字语言",
        "settings_volume_label": "主音量",
        "settings_volume_desc": "控制所有游戏声音",
        "settings_vsync_label": "垂直同步",
        "settings_vsync_desc": "减少画面撕裂",
        "settings_display_mode_label": "显示模式",
        "settings_display_mode_desc": "选择全屏游玩或使用窗口（Alt + Enter）",
        "settings_ui_scale_label": "界面大小",
        "settings_ui_scale_desc": "调整所有界面和菜单",
        "settings_motion_label": "界面动效",
        "settings_motion_desc": "按钮与星星的柔和动画",
        "settings_flash_label": "受伤闪光",
        "settings_flash_desc": "受到伤害时显示珊瑚色提示",
        "option_on": "开启",
        "option_off": "关闭",
        "display_fullscreen": "全屏",
        "display_windowed": "窗口化",
        "ui_scale_small": "小",
        "ui_scale_normal": "标准",
        "ui_scale_large": "大",
        "language_zh": "中文",
        "language_en": "英文",
        "character_rotate_left_aria": "向左旋转伙伴",
        "character_rotate_right_aria": "向右旋转伙伴",
        "character_zoom_out_aria": "缩小伙伴预览",
        "character_zoom_in_aria": "放大伙伴预览",
        "settings_projectile_opacity_label": "玩家弹体透明度",
        "settings_projectile_opacity_desc": "只调节玩家弹体装饰；核心弹体与敌方预警保持清楚",
        "settings_particle_density_label": "粒子密度",
        "settings_particle_density_desc": "关键命中、弹体核心与预警不会被隐藏",
        "particle_density_auto": "自动", "particle_density_low": "低",
        "particle_density_medium": "中", "particle_density_high": "高",
        "settings_damage_numbers_label": "伤害数字",
        "settings_damage_numbers_desc": "减少高压战斗中的非关键视觉噪声",
        "damage_numbers_off": "关闭", "damage_numbers_reduced": "精简",
        "damage_numbers_full": "完整",
        "settings_screen_shake_label": "屏幕震动",
        "settings_screen_shake_desc": "关闭后保留伤害方向与危险边界提示",
        "settings_telegraph_color_label": "敌方预警颜色",
        "settings_telegraph_color_desc": "选择高对比或色觉辅助预设",
        "telegraph_color_default": "默认", "telegraph_color_deuteranopia": "红绿色弱",
        "telegraph_color_tritanopia": "蓝黄色弱", "telegraph_color_high_contrast": "高对比",
        "settings_auto_throttle_label": "自动视觉降档",
        "settings_auto_throttle_desc": "高负载时优先降低尾迹与装饰，不隐藏玩法关键视觉",
        "settings_defaults_button": "恢复默认",
        "settings_saved_hint": "更改会自动保存",
        "game_over_title": "这次冒险结束啦",
        "game_over_subtitle": "已经做得很棒了，下次一定能走得更远！",
        "restart_button": "再来一次",
        "game_over_home_button": "返回开始界面",
        "restart_hint_text": "快速重开",
        "final_score_label": "得分",
        "final_kills_label": "击杀",
        "final_level_label": "等级",
        "upgrade_magnet_name": "吸吸星光",
        "upgrade_magnet_desc": "更远的星光碎片也会主动飞过来。",
        "upgrade_magnet_stat": "拾取范围  +2.2 米",
        "upgrade_vitality_name": "活力泡泡",
        "upgrade_vitality_desc": "最大生命 +28，并恢复 40 生命",
        "upgrade_vitality_stat": "最大生命  +28  ·  立即恢复 40",
        "upgrade_guard_name": "软绵护甲",
        "upgrade_guard_desc": "柔软但可靠，受到的伤害降低 10%。",
        "upgrade_guard_stat": "伤害减免  +10%",
        "upgrade_thunder_name": "闪电糖果",
        "upgrade_thunder_desc": "雷霆升至 {level} 级：伤害更高、落雷更快{target_bonus}",
        "upgrade_thunder_stat": "雷击伤害  +10  ·  间隔缩短",
        "upgrade_target_bonus": "，并多攻击 1 个目标",
        "upgrade_ring_unlock_name": "新伙伴：波纹环",
        "upgrade_ring_unlock_desc": "一圈圈魔法波纹会自动穿过身边的怪物。",
        "upgrade_ring_unlock_stat": "新增自动武器  ·  范围伤害",
        "upgrade_ring_name": "波纹环",
        "upgrade_ring_desc": "波纹环升至 {level} 级：范围更大、扩散更快。",
        "upgrade_ring_stat": "波纹伤害  +8  ·  范围与速度提升",
        "upgrade_fireball_unlock_name": "新伙伴：火球",
        "upgrade_fireball_unlock_desc": "从头顶升起一颗火球，再追向最近的怪物。",
        "upgrade_fireball_unlock_stat": "新增自动武器  ·  追踪攻击",
        "upgrade_fireball_name": "火球",
        "upgrade_fireball_desc": "火球升至 {level} 级：完整飞行更快，高等级还会增加火球。",
        "upgrade_fireball_stat": "火球伤害  +14  ·  4/7级增加数量",
    },
    "en": {
        "survive_banner": "STARLIGHT ADVENTURE!",
        "region_objective_title": "FOUR-REGION PURIFICATION",
        "domain_power_title": "DOMAIN POWERS",
        "region_arming_banner": "THE REGION IS ANSWERING...",
        "region_assault_banner": "PURIFICATION STARTED: HOLD FOR 60 SECONDS!",
        "region_grace_banner": "OUTSIDE THE RING — TIMER PAUSED!",
        "region_resumed_banner": "BACK IN THE RING — PURIFICATION RESUMED!",
        "region_failed_banner": "PURIFICATION FAILED — 12 SECOND COOLDOWN",
        "region_complete_banner": "REGION PURIFIED — DOMAIN POWER AWAKENED!",
        "boss_ready_banner": "FOUR REGIONS CONVERGE — RETURN TO THE PLINTH!",
        "boss_intro_banner": "THE PLINTH IS SUMMONING THE STAR DRAGON...",
        "region_completed": "Purified {count} / 4",
        "region_star_name": "Star Region",
        "region_thunder_name": "Thunder Region",
        "region_water_name": "Water Region",
        "region_wind_name": "Wind Region",
        "region_state_dormant": "Dormant",
        "region_state_arming": "Arming",
        "region_state_assault": "Defending",
        "region_state_outside_grace": "Outside Grace",
        "region_state_cooldown": "Cooldown",
        "region_state_activated": "Purified",
        "direction_north": "North",
        "direction_west": "West",
        "direction_south": "South",
        "direction_east": "East",
        "region_direction": "{direction} · {distance}m",
        "region_explore_hint": "Find an unpurified region",
        "region_explore_instruction": "Follow a region beacon and enter its ring",
        "region_arming_instruction": "Hold position while the purification dome forms",
        "region_hold_instruction": "STAY INSIDE THE DOME · REPEL THE WAVE",
        "region_grace_instruction": "RETURN TO THE DOME! PURIFICATION IS PAUSED",
        "region_grace_countdown": "RETURN {seconds}s",
        "region_cooldown_instruction": "PURIFICATION INTERRUPTED · REGION RECOVERING",
        "region_complete_instruction": "REGION PURIFIED · DOMAIN POWER ACTIVE",
        "region_current_none": "Find an unpurified region",
        "region_navigation": "{direction} · {distance}m",
        "domain_star_name": "Starfall Domain",
        "domain_thunder_name": "Thunder Domain",
        "domain_water_name": "Tidal Domain",
        "domain_wind_name": "Tempest Domain",
        "weapon_slot_locked": "Locked slot",
        "weapon_slot_empty": "Empty slot",
        "boss_ready_objective": "Return to the central plinth and hold for 2 seconds",
        "objective_find_regions": "Travel to any unpurified region",
        "objective_hold_region": "{region} · DEFEND INSIDE THE DOME",
        "objective_return_region": "{region} · RETURN TO THE DOME",
        "objective_return_center": "Return to the central plinth · {distance}m",
        "objective_defeat_boss": "Defeat the objective: Star Dragon",
        "elite_banner": "A TOUGH ONE IS HERE!",
        "critical_banner": "NICE HIT!",
        "chest_evolution_banner": "EVOLUTION! A STAR FORM AWAKENS!",
        "chest_trinket_banner": "A SHINY TRINKET JOINS THE BUILD!",
        "chest_upgrade_banner": "THE CHEST UPGRADED YOUR GEAR!",
        "chest_gold_banner": "THE CHEST WAS FULL OF GOLD!",
        "upgrade_skip_name": "SKIPPED THIS GROWTH",
        "level": "LV {level}",
        "kills": "KILLS  {count}",
        "enemy_count": "MONSTERS NEARBY  {count}",
        "experience": "EXPERIENCE {current} / {required}  ·  {percent}%",
        "experience_ready": "LEVEL UP!  LV {level}",
        "shards": "STAR SHARDS  {count}",
        "score_label": "ADVENTURE SCORE",
        "timer_caption": "RUN TIME",
        "controls_move": "MOVE",
        "controls_jump_key": "SPACE",
        "controls_jump": "JUMP",
        "controls_camera_key": "RMB",
        "controls_camera": "ORBIT",
        "controls_auto": "AUTO ATTACK",
        "boss_name": "BIG TROUBLE",
        "health_label": "VITALITY",
        "weapon_title": "MAGIC BACKPACK",
        "thunder_label": "THUNDER",
        "ring_label": "RIPPLE RING",
        "fireball_label": "FIREBALL",
        "weapon_value": "LV {level} · {damage} DMG",
        "weapon_evolved_value": "EVOLVED",
        "locked": "LOCKED",
        "start_eyebrow": "A COZY STARLIGHT ADVENTURE",
        "start_title": "小树保卫者",
        "start_subtitle": "Bring a self-casting magic backpack and collect sparkling gifts among waves of cute monsters.",
        "start_feature_magic": "AUTO MAGIC",
        "start_feature_cozy": "CUTE WAVES",
        "start_feature_growth": "NEW GROWTH",
        "start_button": "START ADVENTURE",
        "start_settings_button": "SETTINGS",
        "start_hint": "Press ESC during an adventure whenever you need a breather.",
        "loading_eyebrow": "STARLIGHT ASSEMBLING",
        "loading_title": "PACKING A COZY ADVENTURE",
        "loading_subtitle": "Your magic backpack is gathering cute companions and sparkling gifts for tonight's journey.",
        "loading_effects": "Waking up magical effects",
        "loading_monsters": "Inviting monster friends",
        "loading_pickup": "Packing starlight gifts",
        "loading_resources": "Opening the adventure trail",
        "loading_ready": "Starlight ready — let's go!",
        "loading_hint": "The adventure begins automatically when the starlight trail is ready.",
        "level_up": "LEVEL UP!",
        "upgrade_title": "LEVEL {level}",
        "upgrade_subtitle": "PICK YOUR FAVORITE POWER",
        "upgrade_flavor": "Every little boost makes the adventure friendlier.",
        "upgrade_level_caption": "CURRENT LEVEL",
        "choice_prompt": "PICK ONE · A LITTLE GROWTH GIFT",
        "upgrade_hint_mouse": "MOVE THE CURSOR, THEN CLICK A CARD",
        "upgrade_reroll": "REROLL",
        "upgrade_skip": "SKIP",
        "upgrade_banish": "BANISH SELECTED",
        "upgrade_banish_confirm": "CONFIRM BANISH",
        "upgrade_kind_passive": "TOME · PASSIVE",
        "upgrade_kind_weapon": "AUTO WEAPON",
        "upgrade_rank_permanent": "PERMANENT",
        "upgrade_rank_unlock": "NEW UNLOCK",
        "upgrade_rank_level": "LV {current} → LV {next}",
        "rarity_common": "COZY",
        "rarity_rare": "SHINY",
        "rarity_new": "NEW",
        "pause_title": "TAKE A BREATHER",
        "pause_subtitle": "The adventure is paused. Continue whenever you are ready.",
        "resume_button": "KEEP GOING",
        "pause_settings_button": "SETTINGS",
        "pause_restart_button": "START OVER",
        "pause_home_button": "BACK TO TITLE",
        "pause_hint_text": "BACK TO GAME",
        "settings_eyebrow": "COZY CORNER",
        "settings_title": "SETTINGS",
        "settings_back_button": "BACK",
        "settings_language_label": "LANGUAGE",
        "settings_language_desc": "Choose the language used in the adventure",
        "settings_volume_label": "MASTER VOLUME",
        "settings_volume_desc": "Controls all game audio",
        "settings_vsync_label": "VERTICAL SYNC",
        "settings_vsync_desc": "Helps prevent screen tearing",
        "settings_display_mode_label": "DISPLAY MODE",
        "settings_display_mode_desc": "Play fullscreen or in a window (Alt + Enter)",
        "settings_ui_scale_label": "UI SIZE",
        "settings_ui_scale_desc": "Resize every HUD and menu",
        "settings_motion_label": "UI MOTION",
        "settings_motion_desc": "Gentle button and sparkle animations",
        "settings_flash_label": "DAMAGE FLASH",
        "settings_flash_desc": "Show a coral cue when taking damage",
        "option_on": "ON",
        "option_off": "OFF",
        "display_fullscreen": "FULLSCREEN",
        "display_windowed": "WINDOWED",
        "ui_scale_small": "SMALL",
        "ui_scale_normal": "NORMAL",
        "ui_scale_large": "LARGE",
        "language_zh": "CHINESE",
        "language_en": "ENGLISH",
        "character_rotate_left_aria": "Rotate character left",
        "character_rotate_right_aria": "Rotate character right",
        "character_zoom_out_aria": "Zoom character preview out",
        "character_zoom_in_aria": "Zoom character preview in",
        "settings_projectile_opacity_label": "PLAYER PROJECTILE OPACITY",
        "settings_projectile_opacity_desc": "Adjust player projectile decoration while keeping cores and enemy warnings clear",
        "settings_particle_density_label": "PARTICLE DENSITY",
        "settings_particle_density_desc": "Critical hits, projectile cores, and warnings always remain visible",
        "particle_density_auto": "AUTO", "particle_density_low": "LOW",
        "particle_density_medium": "MEDIUM", "particle_density_high": "HIGH",
        "settings_damage_numbers_label": "DAMAGE NUMBERS",
        "settings_damage_numbers_desc": "Reduce nonessential visual noise in crowded fights",
        "damage_numbers_off": "OFF", "damage_numbers_reduced": "REDUCED",
        "damage_numbers_full": "FULL",
        "settings_screen_shake_label": "SCREEN SHAKE",
        "settings_screen_shake_desc": "Damage direction and danger boundaries remain visible when disabled",
        "settings_telegraph_color_label": "ENEMY TELEGRAPH COLOR",
        "settings_telegraph_color_desc": "Choose a high-contrast or color-vision preset",
        "telegraph_color_default": "DEFAULT", "telegraph_color_deuteranopia": "DEUTERANOPIA",
        "telegraph_color_tritanopia": "TRITANOPIA", "telegraph_color_high_contrast": "HIGH CONTRAST",
        "settings_auto_throttle_label": "AUTOMATIC VISUAL THROTTLE",
        "settings_auto_throttle_desc": "Reduce trails and decoration first without hiding gameplay-critical visuals",
        "settings_defaults_button": "RESET DEFAULTS",
        "settings_saved_hint": "CHANGES SAVE AUTOMATICALLY",
        "game_over_title": "ADVENTURE COMPLETE",
        "game_over_subtitle": "Great job! Next time you will go even farther.",
        "restart_button": "TRY AGAIN",
        "game_over_home_button": "BACK TO TITLE",
        "restart_hint_text": "QUICK RESTART",
        "final_score_label": "SCORE",
        "final_kills_label": "KILLS",
        "final_level_label": "LEVEL",
        "upgrade_magnet_name": "STAR SIPHON",
        "upgrade_magnet_desc": "Faraway star shards happily fly toward you.",
        "upgrade_magnet_stat": "PICKUP RANGE  +2.2 M",
        "upgrade_vitality_name": "VITALITY BUBBLE",
        "upgrade_vitality_desc": "+28 max health and instantly heal 40.",
        "upgrade_vitality_stat": "MAX HEALTH  +28  ·  HEAL 40",
        "upgrade_guard_name": "FLUFFY ARMOR",
        "upgrade_guard_desc": "Soft but sturdy. Take 10% less damage.",
        "upgrade_guard_stat": "DAMAGE REDUCTION  +10%",
        "upgrade_thunder_name": "THUNDER CANDY",
        "upgrade_thunder_desc": "Thunder reaches LV {level}: stronger, faster strikes{target_bonus}.",
        "upgrade_thunder_stat": "THUNDER DAMAGE  +10  ·  FASTER",
        "upgrade_target_bonus": " and +1 target",
        "upgrade_ring_unlock_name": "NEW FRIEND: RIPPLE RING",
        "upgrade_ring_unlock_desc": "Magic ripples automatically sweep through nearby monsters.",
        "upgrade_ring_unlock_stat": "NEW AUTO WEAPON  ·  AREA DAMAGE",
        "upgrade_ring_name": "RIPPLE RING",
        "upgrade_ring_desc": "Ripple Ring reaches LV {level}: wider and faster waves.",
        "upgrade_ring_stat": "RING DAMAGE  +8  ·  WIDER & FASTER",
        "upgrade_fireball_unlock_name": "NEW FRIEND: FIREBALL",
        "upgrade_fireball_unlock_desc": "Raise a fireball overhead, then send it after the nearest monster.",
        "upgrade_fireball_unlock_stat": "NEW AUTO WEAPON  ·  HOMING HIT",
        "upgrade_fireball_name": "FIREBALL",
        "upgrade_fireball_desc": "Fireball reaches LV {level}: faster full flights gain extra fireballs.",
        "upgrade_fireball_stat": "FIREBALL DAMAGE +14 · +BALL AT LV 4/7",
    },
}

for content_language, content_text in CONTENT_TEXT.items():
    language_text = SURVIVOR_TEXT.setdefault(content_language, {})
    for content_key, localized_text in content_text.items():
        language_text.setdefault(content_key, localized_text)


class SurvivorGame(
        SurvivorHubMixin,
        SurvivorPresentationMixin,
        SurvivorProgressionMixin,
        SurvivorCombatHooksMixin,
        SurvivorObjectivesMixin,
        SurvivorDomainPowersMixin,
        SurvivorWorldMixin,
        SurvivorWeaponsMixin):
    """Wave director for the MainGame survivor arena."""

    MENU_DIRECTOR_UUID = "b81e7bcf-f246-470b-93d2-14a69488ea52"
    GAMEPLAY_DIRECTOR_UUID = "a900eabb-cccf-599c-b4b1-11f42739cefd"

    SETTINGS_CONFIG = "Config/SurvivorGame.json"
    DEFAULT_LANGUAGE = "zh_cn"
    DEFAULT_MASTER_VOLUME = 0.5
    DEFAULT_VSYNC = False
    DEFAULT_FULLSCREEN = False
    DEFAULT_UI_SCALE = 1.0
    DEFAULT_MOTION_ENABLED = True
    DEFAULT_DAMAGE_FLASH_ENABLED = True
    DEFAULT_PROJECTILE_OPACITY = 0.85
    DEFAULT_PARTICLE_DENSITY = "auto"
    DEFAULT_DAMAGE_NUMBERS = "full"
    DEFAULT_SCREEN_SHAKE = True
    DEFAULT_TELEGRAPH_COLOR = "default"
    DEFAULT_AUTO_VISUAL_THROTTLE = True
    CURSOR_ASSET = asset_path("ui/cursor/starbloom")
    HUD_DOCUMENT = asset_path("ui/hud/document")
    HUD_MOTION = asset_path("ui/hud/motion")
    EXPERIENCE_PREFAB = asset_path("common/prefab/experience-gem")
    BOSS_CHEST_PREFAB = asset_path("common/prefab/boss-chest")
    BOSS_CHEST_EFFECT = asset_path("vfx/common/boss-chest")
    ENEMY_PROJECTILE_EFFECT = asset_path("vfx/common/enemy-projectile-orange")
    ENEMY_ZONE_TELEGRAPH_EFFECT = asset_path("vfx/common/enemy-zone-telegraph")
    BOSS_AREA_TELEGRAPH_EFFECT = asset_path("vfx/common/boss-area-telegraph")
    MONSTER_ANIM_CONTROLLER = asset_path("enemy/green_blob/controller")
    THUNDER_EFFECT = asset_path("domain/thunder/impact-vfx")
    RING_EFFECT = WEAPON_DEFS["ring"]["effect"]
    FIREBALL_EFFECT = WEAPON_DEFS["fireball"]["effect"]
    MOONBLADE_EFFECT = WEAPON_DEFS["moonblade"]["effect"]
    BUBBLE_EFFECT = WEAPON_DEFS["bubble"]["effect"]
    TORNADO_EFFECT = asset_path("domain/wind/impact-vfx")
    STARFALL_EFFECT = asset_path("domain/star/impact-vfx")
    AURA_EFFECT = WEAPON_DEFS["aura"]["effect"]
    DAGGER_EFFECT = WEAPON_DEFS["dagger"]["effect"]
    STARWHEEL_EFFECT = WEAPON_DEFS["starwheel"]["effect"]
    PETALSTORM_EFFECT = WEAPON_DEFS["petalstorm"]["effect"]
    COMET_EFFECT = WEAPON_DEFS["comet"]["effect"]
    BOSS_SPAWN_WARNING_EFFECT = asset_path("vfx/common/boss-area-telegraph")

    # Each phase introduces at most one new regular enemy. Strong-enemy and boss
    # phases deliberately lower the population target before ramping up again.
    WAVE_PHASES = (
        {"start": 0.0, "end": 60.0, "count_start": 12, "count_end": 24, "interval": 0.60, "batch": 2, "pool": (("green_blob", 1.0),)},
        {"start": 60.0, "end": 120.0, "count_start": 24, "count_end": 36, "interval": 0.52, "batch": 2, "pool": (("green_blob", 0.70), ("pink_blob", 0.30))},
        {"start": 120.0, "end": 180.0, "count_start": 36, "count_end": 50, "interval": 0.58, "batch": 2, "pool": (("green_blob", 0.40), ("pink_blob", 0.40), ("spiky_blob", 0.20))},
        {"start": 180.0, "end": 300.0, "count_start": 50, "count_end": 72, "interval": 0.48, "batch": 2, "pool": (("green_blob", 0.20), ("pink_blob", 0.30), ("spiky_blob", 0.35), ("orc", 0.15))},
        {"start": 300.0, "end": 360.0, "count_start": 55, "count_end": 65, "interval": 0.62, "batch": 2, "pool": (("pink_blob", 0.10), ("spiky_blob", 0.35), ("orc", 0.35), ("yeti", 0.20))},
        {"start": 360.0, "end": 420.0, "count_start": 65, "count_end": 90, "interval": 0.45, "batch": 3, "pool": (("pink_blob", 0.10), ("spiky_blob", 0.30), ("orc", 0.40), ("yeti", 0.20))},
        {"start": 420.0, "end": 600.0, "count_start": 90, "count_end": 150, "interval": 0.34, "batch": 3, "pool": (("green_blob", 0.10), ("pink_blob", 0.15), ("spiky_blob", 0.30), ("orc", 0.30), ("yeti", 0.15))},
        {"start": 600.0, "end": 900.0, "count_start": 120, "count_end": 210, "interval": 0.30, "batch": 4, "pool": (("pink_blob", 0.05), ("spiky_blob", 0.25), ("orc", 0.40), ("yeti", 0.30))},
        {"start": 900.0, "end": 1800.0, "count_start": 210, "count_end": 320, "interval": 0.24, "batch": 5, "pool": (("spiky_blob", 0.15), ("orc", 0.40), ("yeti", 0.45))},
    )

    @staticmethod
    def _catalog_archetype(entry, bBoss=False):
        attack_set = entry["attackSet"]
        attack = {
            "range": entry["radius"] + 0.42,
            "preferred_range": entry["preferredRange"],
            "cooldown": entry["cooldown"],
            "source_cooldown": 0.65,
            "telegraph": max(0.85 if bBoss else 0.35, entry["telegraph"]),
            "active": 0.12,
            "recovery": 0.36 if bBoss else 0.22,
            "charge_speed": 9.0,
            "projectile_speed": 7.5,
            "projectile_lifetime": 2.4,
            "projectile_radius": 0.28,
            "projectile_damage_scale": 1.0,
            "zone_radius": 2.4 if bBoss else 1.6,
            "zone_duration": 2.4 if bBoss else 2.0,
            "zone_tick": 0.5,
            "zone_damage_scale": 0.75,
            "suicide_damage_scale": 1.5,
            "shield": 60.0 if entry["behaviorId"] in ("shield", "boss_orc") else 0.0,
            "shield_duration": 2.0,
            "summon_count": 4 if "summon" in " ".join(attack_set) else 0,
        }
        resistance_source = entry["resistances"]
        resistances = {
            "damage": float(resistance_source.get("damage", 0.0)),
            "slow": float(resistance_source.get("slow", 0.0)),
            "freeze": float(resistance_source.get("freeze", 0.0)),
            "poison": float(resistance_source.get("poison", 0.0)),
            "knockback": float(resistance_source.get("knockback", 0.0)),
        }
        return {
            "id": entry["id"],
            "name_zh": entry["name"]["zh_cn"],
            "name_en": entry["name"]["en"],
            "prefab": entry["prefab"],
            "controller": entry["controller"],
            "scale": entry["scale"],
            "health": entry["health"],
            "speed": entry["speed"],
            "damage": entry["damage"],
            "radius": entry["radius"],
            "reward": entry["rewardXp"],
            "behavior": "boss" if bBoss else entry["behaviorId"],
            "attack": attack,
            "resistances": resistances,
            "boss_phase": 1 if bBoss else 0,
        }

    MONSTER_ARCHETYPES = tuple(
        _catalog_archetype_view(entry)
        for entry in CATALOG_ENEMIES
    )
    BOSS_ARCHETYPES = tuple(
        _catalog_archetype_view(entry, True)
        for entry in CATALOG_BOSSES
    )
    WAVE_PHASES = tuple({
        "start": wave["start"],
        "end": wave["end"],
        "count_start": wave["countStart"],
        "count_end": wave["countEnd"],
        "interval": wave["spawnInterval"],
        "batch": wave["batch"],
        "pool": wave["pool"],
        "health_multiplier": wave["healthMultiplier"],
        "damage_multiplier": wave["damageMultiplier"],
        "speed_multiplier": wave["speedMultiplier"],
        "elite_rate": wave["eliteRate"],
        "event": wave["event"],
        "chest_tier": wave["chestTier"],
    } for wave in CATALOG_WAVES)
    BOSS_EVENTS = tuple(CATALOG_BOSS_EVENTS)
    DIFFICULTIES = tuple(CATALOG_DIFFICULTIES)
    CHALLENGES = tuple(CATALOG_CHALLENGES)
    DIFFICULTY_GROWTH_START = 300.0
    DIFFICULTY_GROWTH_DURATION = 1500.0
    HEALTH_GROWTH_PER_SECOND = 0.0008
    DAMAGE_GROWTH_PER_SECOND = 0.00025
    SPEED_GROWTH_PER_SECOND = 0.00005

    MAX_MONSTERS = 320
    MAX_PICKUPS = 220
    # Runtime selects 12/16/20 from the visual-density setting.  Twenty remains
    # the absolute animation budget; the rest use inexpensive crowd motion.
    MAX_ANIMATED_MONSTERS = 20
    ANIMATION_LOD_DISTANCE = 7.0
    ANIMATION_LOD_RELEASE_DISTANCE = 8.5
    MONSTER_UPDATE_INTERVAL = 1.0 / 30.0
    PICKUP_UPDATE_INTERVAL = 1.0 / 30.0
    MAX_SIMULATION_STEPS_PER_FRAME = 2
    PICKUP_SPAWN_BUDGET_PER_FRAME = 4
    SCREEN_ATTACK_RANGE = 10.5
    RING_EDGE_WIDTH = 0.42
    RING_EFFECT_SPEED = 1.6
    RING_EXPANSION_TIME = 70.0 / (60.0 * RING_EFFECT_SPEED)
    FIREBALL_EFFECT_SCALE = 0.56
    FIREBALL_RETRY_INTERVAL = 0.08
    FIREBALL_MIN_TRAVEL_TIME = 0.36
    FIREBALL_MAX_TRAVEL_TIME = 0.78
    FIREBALL_TRAVEL_SPEED = 12.0
    FIREBALL_ROOT_ARC_HEIGHT = 0.72
    FIREBALL_IMPACT_PADDING = 0.90
    BUBBLE_CHAIN_DELAY = 0.18
    STARFALL_IMPACT_DELAY = 0.45
    MAX_ACTIVE_PROJECTILES = 160
    MAX_PROJECTILE_VISUALS = 96
    PROJECTILE_RESTART_INTERVAL = 0.16
    MOONWAVE_PROJECTILE_SCALE = 0.69
    BUBBLE_PROJECTILE_SCALE = 0.82
    WISP_PROJECTILE_SCALE = 0.50
    DAGGER_PROJECTILE_SCALE = 0.68
    STARWHEEL_PROJECTILE_SCALE = 0.78
    STAR_BOLT_PREFAB = asset_path("weapon/moonblade/projectile-prefab")
    STAR_WHEEL_PREFAB = asset_path("weapon/starwheel/projectile-prefab")
    COMET_CORE_PREFAB = asset_path("weapon/comet/projectile-prefab")
    BUBBLE_CORE_PREFAB = asset_path("weapon/bubble/projectile-prefab")
    FIREBALL_CORE_PREFAB = asset_path("weapon/fireball/projectile-prefab")
    PETAL_CORE_PREFAB = asset_path("weapon/petalstorm/projectile-prefab")
    HONEY_NEEDLE_CORE_PREFAB = asset_path("weapon/honeyneedle/projectile-prefab")
    SPORECAP_CORE_PREFAB = asset_path("weapon/sporecap/projectile-prefab")
    PHANTOM_BELL_CORE_PREFAB = asset_path("weapon/phantombell/projectile-prefab")
    CORAL_ANCHOR_CORE_PREFAB = asset_path("weapon/coralanchor/projectile-prefab")
    PRISM_CORE_PREFAB = asset_path("weapon/prismorbit/projectile-prefab")
    ACORN_CORE_PREFAB = asset_path("weapon/acornmortar/projectile-prefab")
    FROST_ORB_CORE_PREFAB = asset_path("weapon/frostorb/projectile-prefab")
    GRAVITY_YOYO_CORE_PREFAB = asset_path("weapon/gravityyoyo/projectile-prefab")
    MONSTER_DESPAWN_DISTANCE_SQ = 48.0 * 48.0
    PLAYER_GROUND_OFFSET = 0.08
    MONSTER_GROUND_OFFSET = 0.08
    PICKUP_GROUND_OFFSET = 0.04
    WEAPON_VERTICAL_RANGE = 2.25
    PLAYER_GROUND_CHECK_INTERVAL = 0.10
    PLAYER_SAFE_GROUND_DISTANCE = 1.75
    # Must remain inside GenerateVerdantRift.py's physical boundary walls.
    PLAYABLE_HALF_EXTENT = 84.0
    FALL_RECOVERY_Y = -4.0
    SPAWN_GROUND_ATTEMPTS = 10
    GEM_SCALE = HEngine.vec3(0.62, 0.72, 0.62)
    HIDDEN_SCALE = HEngine.vec3(0.0, 0.0, 0.0)

    def __init__(self):
        self.audio = SurvivorAudio()
        self.entity = None
        self.player = None
        self.document_id = ""
        self.ui_motion = None
        self.ui_screens = None
        self.monsters = []
        self.monsters_by_id = {}
        self.monster_pools = {}
        self.pickups = []
        self.pickups_by_id = {}
        self.pickup_pool = []
        self.pending_pickup_spawns = []
        self.pending_chest_rewards = []
        self.enemy_projectile_effects = {}
        self.enemy_zone_effects = {}
        self.enemy_telegraph_effects = {}
        self.enemy_batch_telemetry = {}
        self.active_chests = []
        self.chest_pool = []
        self.trinket_slots = []
        self.active_evolutions = {}
        self.evolution_times = {}
        self.upgrade_choices = []
        self.random_state = 7319
        self.monster_activation_serial = 0
        self.pickup_activation_serial = 0
        self.language = "zh_cn"
        self.banner_key = "survive_banner"
        self.run_config = None
        self.weapon_slot_limit = 3
        self.telemetry = SurvivorTelemetry(False)
        self.quest_tracker = None
        self.bMenuScene = False
        self.bSceneTransitionRequested = False

        self.elapsed = 0.0
        self.spawn_timer = 0.0
        self.thunder_timer = 0.0
        self.ring_timer = 0.0
        self.fireball_timer = 0.0
        self.moonblade_timer = 0.0
        self.bubble_timer = 0.0
        self.tornado_timer = 0.0
        self.starfall_timer = 0.0
        self.aura_timer = 0.0
        self.dagger_timer = 0.0
        self.starwheel_timer = 0.0
        self.petalstorm_timer = 0.0
        self.comet_timer = 0.0
        for weapon_code in WEAPON_ORDER:
            timer_name = weapon_code + "_timer"
            if not hasattr(self, timer_name):
                setattr(self, timer_name, 0.0)
        self.active_ring_waves = []
        self.active_fireballs = []
        self.active_bubble_chains = []
        self.active_tornado_zones = []
        self.active_starfall_impacts = []
        self.active_custom_areas = []
        self.active_custom_beams = []
        self.pending_weapon_echoes = []
        self.domain_power_effects = []
        self.domain_activation_overcharges = set()
        self.active_projectiles = []
        self.pending_projectile_spawns = []
        self.projectile_budget = ProjectileBudget(
            self.MAX_ACTIVE_PROJECTILES,
            self.MAX_PROJECTILE_VISUALS,
        )
        self.projectile_visual_pool = {
            "bolt": [], "wheel": [], "comet": [],
            "bubble": [], "fireball": [], "petal": [],
            "needle": [], "spore": [], "bell": [], "anchor": [],
            "prism": [], "acorn": [], "frost": [], "yoyo": [],
        }
        self.projectile_visual_entities = []
        self.hud_timer = 0.0
        self.monster_update_accumulator = 0.0
        self.pickup_update_accumulator = 0.0
        self.banner_timer = 0.0
        self.damage_flash_timer = 0.0
        self.level_up_flash_timer = 0.0
        self.damage_cooldown = 0.0
        self.player_ground_check_timer = 0.0
        self.last_safe_player_position = HEngine.vec3(0.0, self.PLAYER_GROUND_OFFSET, 0.0)
        self.last_restart_pressed = False
        self.last_pause_pressed = False
        self.last_fullscreen_shortcut_pressed = False
        self.upgrade_selected_index = -1
        self.pending_effects = []
        self.warmup_stage = "ready"
        self.warmup_monster = None
        self.pending_monster_warmups = []
        self.pending_visual_warmups = []
        self.warmup_total_effects = 0
        self.warmup_total_monsters = 0
        self.warmup_display_progress = 0.0
        self.bRuntimeReady = False
        self.bLoadingAdventure = False
        self.hud_cache = {}

        self.health = 100.0
        self.max_health = 100.0
        self.level = 1
        self.experience = 0.0
        self.experience_to_level = 5
        self.kills = 0
        self.score = 0
        self.collected_shards = 0
        self.last_player_hook_position = None
        self.weapon_telemetry = {
            weapon_code: {
                "damage": 0.0,
                "hits": 0,
                "criticalHits": 0,
                "kills": 0,
                "casts": 0,
                "projectiles": 0,
                "visualDegrades": 0,
                "spawnRetries": 0,
            }
            for weapon_code in WEAPON_ORDER
        }

        for weapon_code in WEAPON_ORDER:
            setattr(
                self,
                weapon_code + "_level",
                WEAPON_DEFS[weapon_code].get("start_level", 0),
            )
        self.weapon_slots = [
            weapon_code
            for weapon_code in WEAPON_ORDER
            if self._weapon_level(weapon_code) > 0
        ][:MAX_WEAPON_SLOTS]
        for weapon_code in WEAPON_ORDER:
            if weapon_code not in self.weapon_slots:
                self._set_weapon_level(weapon_code, 0)
        self._apply_vfx_showcase_override()
        self.tome_levels = {tome_code: 0 for tome_code in TOME_ORDER}
        self.tome_slots = []
        profile = getattr(self, "profile", {})
        self.selected_difficulty = profile.get("selectedDifficulty", "adventure")
        self.selected_challenge = profile.get("selectedChallenge", "none")
        power_ups = profile.get("powerUps", {})
        completed_quests = set(profile.get("completedQuests", ()))
        self.rerolls_remaining = power_ups.get("meta_reroll", 0) + (
            1 if "quest_system_reroll" in completed_quests else 0
        )
        self.skips_remaining = power_ups.get("meta_skip", 0) + (
            1 if "quest_system_skip" in completed_quests else 0
        )
        self.banishes_remaining = power_ups.get("meta_banish", 0) + (
            1 if "quest_system_banish" in completed_quests else 0
        )
        self.run_banished = set()
        self._active_upgrade_pool = None
        self.crit_chance = 0.08
        self.crit_multiplier = 2.0
        self.knockback = 0.42
        self.magnet_range = 4.2
        self.pickup_range = 0.85
        self.damage_reduction = 0.0
        self.bAwaitingUpgrade = False
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.0
        self.pending_banish_index = -1
        self.banish_confirm_timer = 0.0
        self.bPaused = False
        self.bGameOver = False
        self.bInMainMenu = False
        self.bSettingsOpen = False
        self.settings_return_screen = "start"
        self.menu_animation_timer = 0.0
        self.menu_animation_phase = False

        self.master_volume = self.DEFAULT_MASTER_VOLUME
        self.bVSyncEnabled = self.DEFAULT_VSYNC
        self.previous_vsync = None
        self.previous_fullscreen = None
        self.bFullscreen = self.DEFAULT_FULLSCREEN
        self.ui_scale = self.DEFAULT_UI_SCALE
        self.bMotionEnabled = self.DEFAULT_MOTION_ENABLED
        self.bDamageFlashEnabled = self.DEFAULT_DAMAGE_FLASH_ENABLED
        self.player_projectile_opacity = self.DEFAULT_PROJECTILE_OPACITY
        self.particle_density = self.DEFAULT_PARTICLE_DENSITY
        self.damage_numbers_mode = self.DEFAULT_DAMAGE_NUMBERS
        self.bScreenShakeEnabled = self.DEFAULT_SCREEN_SHAKE
        self.enemy_telegraph_color = self.DEFAULT_TELEGRAPH_COLOR
        self.bAutoVisualThrottle = self.DEFAULT_AUTO_VISUAL_THROTTLE

    def Start(self, entity):
        catalog_project_root = os.path.dirname(
            os.path.dirname(HEngine.GetFullPath("Config/BaseEngine.json")),
        )
        bLooseProject = os.path.isfile(
            os.path.join(catalog_project_root, "Project.heproject"),
        )
        catalog_counts = validate_catalog(
            catalog_project_root if bLooseProject else None,
            bLooseProject,
        )
        HEngine.HE_CORE_INFO(
            "[SurvivorCatalog] validated "
            + ", ".join(
                key + "=" + str(value)
                for key, value in catalog_counts.items()
            )
        )
        self.entity = entity
        self.telemetry = SurvivorTelemetry(
            os.environ.get("HE_SURVIVOR_TELEMETRY", "0") == "1",
            HEngine.GetSavedPath("Telemetry/SurvivorRun.json"),
        )
        director_uuid = entity.GetUUID()
        if director_uuid == self.MENU_DIRECTOR_UUID:
            self.bMenuScene = True
        elif director_uuid == self.GAMEPLAY_DIRECTOR_UUID:
            self.bMenuScene = False
        else:
            menu_marker = HEngine.FindEntityByTag("MenuSceneMarker")
            self.bMenuScene = menu_marker.HasComponent("Transform")
        self.player = None if self.bMenuScene else HEngine.FindEntityByTag("Player")
        if (
                not self.bMenuScene and
                (self.player is None or not self.player.HasComponent("Transform"))):
            HEngine.HE_CORE_ERROR("[SurvivorGame] Player entity is missing")
            return

        self.previous_vsync = HEngine.Settings.GetVSync()
        self.previous_fullscreen = HEngine.Settings.GetFullscreen()
        self._load_settings()
        self.quest_tracker = SurvivorQuestTracker(self.profile)
        self.quest_tracker.record("profile_created", 1, bSet=True)
        self.quest_tracker.flush()
        self.quest_completion_audio_count = len(self.profile["completedQuests"])
        if self.bMenuScene:
            # The dedicated menu camera looks along +Y with world +Z as screen up.
            self.PREVIEW_DEFAULT_YAW = 0.0
        self._initialize_hub_state()
        self.document_id = RmlUI.Load(self.HUD_DOCUMENT)
        if self.document_id:
            RmlUI.Show(self.document_id)
            RmlUI.SetActive(self.document_id)
            RmlUI.SetCustomMouseCursor(
                self.document_id,
                self.CURSOR_ASSET,
                3,
                2,
            )
            try:
                motion_asset = RmlUI.LoadMotionAsset(self.HUD_MOTION)
                self.ui_motion = UIAnimationDirector(self.document_id, motion_asset, RmlUI)
                self.ui_motion.register_screen("start", "start_panel", visible=True)
                self.ui_motion.register_screen("loading", "loading_panel")
                self.ui_motion.register_screen("gameplay", "gameplay_hud")
                self.ui_motion.register_screen("upgrade", "upgrade_panel", modal=True)
                self.ui_motion.register_screen("pause", "pause_panel", modal=True)
                self.ui_motion.register_screen("settings", "settings_panel", modal=True)
                self.ui_motion.register_screen("game_over", "game_over_panel", modal=True)
                self.ui_screens = UIScreenStack(self.ui_motion)
            except Exception as error:
                self.ui_motion = None
                self.ui_screens = None
                HEngine.HE_CORE_ERROR("[UiMotion] " + str(error))

        self._apply_settings()
        self._apply_language()
        if self.bMenuScene:
            SurvivorSession.clear_launch()
            self._show_start_menu()
            HEngine.HE_CORE_INFO("[SurvivorGame] dedicated menu scene started")
            return

        launch = SurvivorSession.consume_launch()
        if launch is not None:
            character_id = launch.get("character_id", self.selected_character)
            if character_id in CHARACTER_DEFS:
                self.selected_character = character_id
            self.selected_run_seed = int(
                launch.get("run_seed", self.selected_run_seed),
            ) & 0xFFFFFFFF
        self._start_game_now()
        HEngine.HE_CORE_INFO("[SurvivorGame] Nightfall arena loading")

    @_profile_stage("Update")
    def Update(self, ts):
        if (
                not self.bMenuScene and
                (self.player is None or not self.player.HasComponent("Transform"))):
            return

        if self.ui_motion:
            _timed_stage_call("UiMotion", self.ui_motion.Update)
        self.last_frame_delta_seconds = max(0.0, float(ts.GetSeconds()))
        dt = min(self.last_frame_delta_seconds, 0.05)
        _timed_stage_call("Audio", self.audio.update, dt)
        _timed_stage_call("Hub", self._update_hub, dt)
        self.level_up_flash_timer = max(0.0, self.level_up_flash_timer - dt)
        restart_pressed = HEngine.Input.IsKeyPressed(HEngine.KeyCode.R)
        restart_triggered = restart_pressed and not self.last_restart_pressed
        self.last_restart_pressed = restart_pressed
        pause_pressed = HEngine.Input.IsKeyPressed(HEngine.KeyCode.Escape)
        pause_triggered = pause_pressed and not self.last_pause_pressed
        self.last_pause_pressed = pause_pressed
        self._update_fullscreen_shortcut()

        self._update_menu_animation(dt)

        if self.bLoadingAdventure:
            if self.bSceneTransitionRequested or self.bMenuScene:
                return
            self._advance_runtime_warmup()
            self._sync_loading_ui()
            if self.bRuntimeReady:
                self._complete_adventure_start()
            return

        if self.bSettingsOpen:
            self._set_player_input_enabled(False)
            if pause_triggered:
                self._close_settings()
            return

        if self.bInMainMenu:
            self._set_player_input_enabled(False)
            return

        if self.bGameOver:
            self._set_player_input_enabled(False)
            if restart_triggered:
                self._start_game()
            self._sync_hud()
            return

        if self.bAwaitingUpgrade:
            self._set_player_input_enabled(False)
            self._sync_hud()
            return

        if pause_triggered:
            self._set_paused(not self.bPaused)

        if self.bPaused:
            self._set_player_input_enabled(False)
            self._sync_hud()
            return

        if not self.bRuntimeReady:
            self._advance_runtime_warmup()
            self._sync_hud()
            if not self.bRuntimeReady:
                return

        self._update_hud_phase()

    def FixedUpdate(self, ts):
        if (
                self.bMenuScene or self.bSceneTransitionRequested or
                self.bLoadingAdventure or self.bSettingsOpen or
                self.bInMainMenu or not self.bRuntimeReady or self.bGameOver or
                self.bAwaitingUpgrade or self.bPaused or
                self.player is None or
                not self.player.HasComponent("Transform")):
            return
        # Update handles the pause key once per displayed frame, after the
        # fixed ticks. Skip gameplay on the edge that will pause this frame.
        if (HEngine.Input.IsKeyPressed(HEngine.KeyCode.Escape) and
                not self.last_pause_pressed):
            return

        dt = float(ts.GetSeconds())
        player_transform = self.player.GetComponent("Transform")
        self.player_ground_check_timer = max(0.0, self.player_ground_check_timer - dt)
        if (self.player_ground_check_timer <= 0.0 or
                player_transform.Translation.y < self.FALL_RECOVERY_Y):
            self._update_player_ground_safety(player_transform)
            self.player_ground_check_timer = self.PLAYER_GROUND_CHECK_INTERVAL

        player_pos = self._update_gameplay_bookkeeping(dt)
        if self.bGameOver:
            return
        # The objective follows simulated time, including bounded catch-up
        # and deliberate time drops after a long presentation stall.
        _timed_stage_call("Objectives", self._update_region_objectives,
            player_pos, dt,
        )
        if self.bGameOver:
            return
        self._drain_pending_pickup_spawns()
        self._drain_pending_chest_spawns()
        self._spawn_wave(player_pos)
        if not self._update_monster_phase(player_pos):
            return
        self._update_pickup_phase(player_pos)
        self._update_weapons(player_pos, dt)
        _timed_stage_call("DomainPowers", self._update_domain_powers, player_pos, dt)

    @_profile_stage("Bookkeeping")
    def _update_gameplay_bookkeeping(self, dt):
        if _PROFILE_ENABLED:
            # A profiler capture measures a fixed combat workload; it must not
            # terminate early because the unattended player dies.
            self.health = self.max_health
        previous_elapsed = self.elapsed
        run_config = getattr(self, "run_config", None)
        challenge = (
            run_config.challenge_tuning_for_world_minute(
                min(15, int(self.elapsed // 60.0)),
            )
            if run_config is not None else
            self._challenge_tuning()
        )
        self.elapsed += dt * challenge.get("clock", 1.0)
        if (
                os.environ.get("HE_SURVIVOR_CAPTURE_FORCE_DEATH", "0") == "1"
                and self.elapsed
                >= getattr(self, "capture_override_start_time", self.elapsed) + 1.0
                and not self.bGameOver):
            self.health = 0.0
            self._finish_run("death")
        warmup_schedule = {
            60: "Wave02",
            90: "Wave04",
            120: "Wave05",
            150: "Wave07",
            180: "Wave08",
        }
        for threshold, trigger in warmup_schedule.items():
            if previous_elapsed < threshold <= self.elapsed:
                HEngine.RuntimeResourceWarmup.QueueTrigger(trigger)
        self.spawn_timer -= dt
        self.thunder_timer = max(0.0, self.thunder_timer - dt)
        self.ring_timer = max(0.0, self.ring_timer - dt)
        self.fireball_timer = max(0.0, self.fireball_timer - dt)
        self.moonblade_timer = max(0.0, self.moonblade_timer - dt)
        self.bubble_timer = max(0.0, self.bubble_timer - dt)
        self.tornado_timer = max(0.0, self.tornado_timer - dt)
        self.starfall_timer = max(0.0, self.starfall_timer - dt)
        self.aura_timer = max(0.0, self.aura_timer - dt)
        self.dagger_timer = max(0.0, self.dagger_timer - dt)
        self.starwheel_timer = max(0.0, self.starwheel_timer - dt)
        self.petalstorm_timer = max(0.0, self.petalstorm_timer - dt)
        self.comet_timer = max(0.0, self.comet_timer - dt)
        for weapon_code in WEAPON_ORDER[12:]:
            timer_name = weapon_code + "_timer"
            setattr(self, timer_name, max(0.0, getattr(self, timer_name) - dt))
        self.hud_timer -= dt
        self.monster_update_accumulator += dt
        self.pickup_update_accumulator += dt
        self.banner_timer = max(0.0, self.banner_timer - dt)
        self.damage_flash_timer = max(0.0, self.damage_flash_timer - dt)
        self.damage_cooldown = max(0.0, self.damage_cooldown - dt)
        previous_banish_timer = self.banish_confirm_timer
        self.banish_confirm_timer = max(0.0, self.banish_confirm_timer - dt)
        if previous_banish_timer > 0.0 and self.banish_confirm_timer <= 0.0:
            self.pending_banish_index = -1
            if self.bAwaitingUpgrade:
                self._refresh_upgrade_panel()
        player_position = self.player.GetComponent("Transform").Translation
        if self.last_player_hook_position is not None:
            dx = player_position.x - self.last_player_hook_position[0]
            dz = player_position.z - self.last_player_hook_position[1]
            distance_moved = (dx * dx + dz * dz) ** 0.5
            self.run_distance_moved += distance_moved
            self._dispatch_combat_hook(
                "distance", {"distance": distance_moved},
            )
        self.last_player_hook_position = (player_position.x, player_position.z)
        self._update_character_hook_timers(dt)
        self._update_trinkets(dt)
        if self.recovery_per_second > 0.0:
            self._apply_healing(self.recovery_per_second * dt)
        if self.quest_tracker is not None:
            if self.health >= self.max_health - 0.001:
                self.full_health_streak += dt
            else:
                self.full_health_streak = 0.0
            self.quest_tracker.record(
                "full_health_seconds",
                self.full_health_streak,
                bSet=True,
            )
            if self.elapsed >= 300.0:
                self.quest_tracker.record(
                    "no_damage_seconds_after",
                    max(0.0, self.elapsed - max(300.0, self.last_damage_elapsed)),
                    {"afterSeconds": 300},
                    bSet=True,
                )
            if self.active_tornado_zones or self.active_custom_areas:
                self.quest_tracker.record(
                    "effect_seconds",
                    dt,
                    {"tags": ("zone", "orbit", "return")},
                )
            self.quest_tracker.record(
                "weapons_at_level",
                sum(
                    1 for weapon_id in WEAPON_ORDER
                    if self._weapon_level(weapon_id) >= 5
                ),
                {"level": 5},
                bSet=True,
            )
        self.telemetry.sample(self, dt)
        if self.quest_tracker is not None:
            self.quest_tracker.flush()
            completed_count = len(self.profile["completedQuests"])
            if completed_count > self.quest_completion_audio_count:
                self.audio.post("quest_complete")
                self.quest_completion_audio_count = completed_count
        return player_position

    @_profile_stage("Monsters")
    def _update_monster_phase(self, player_pos):
        monster_steps = min(
            int(self.monster_update_accumulator / self.MONSTER_UPDATE_INTERVAL),
            self.MAX_SIMULATION_STEPS_PER_FRAME,
        )
        if monster_steps > 0:
            monster_dt = monster_steps * self.MONSTER_UPDATE_INTERVAL
            self.monster_update_accumulator = max(
                0.0,
                self.monster_update_accumulator - monster_dt,
            )
            self._update_monsters(player_pos, monster_dt)
            if self.bGameOver:
                self._sync_hud()
                return False
        return True

    @_profile_stage("Pickups")
    def _update_pickup_phase(self, player_pos):
        pickup_steps = min(
            int(self.pickup_update_accumulator / self.PICKUP_UPDATE_INTERVAL),
            self.MAX_SIMULATION_STEPS_PER_FRAME,
        )
        if pickup_steps > 0:
            pickup_dt = pickup_steps * self.PICKUP_UPDATE_INTERVAL
            self.pickup_update_accumulator = max(
                0.0,
                self.pickup_update_accumulator - pickup_dt,
            )
            self._update_pickups(player_pos, pickup_dt)
            self._update_chests(player_pos, pickup_dt)

    @_profile_stage("Hud")
    def _update_hud_phase(self):
        if self.hud_timer <= 0.0:
            self.hud_timer = 0.1
            self._sync_hud()

    def UpdatePaused(self, ts):
        if (
                not self.bMenuScene and
                (self.player is None or not self.player.HasComponent("Transform"))):
            return

        if self.ui_motion:
            self.ui_motion.Update()
        self.last_frame_delta_seconds = max(0.0, float(ts.GetSeconds()))
        dt = min(self.last_frame_delta_seconds, 0.05)
        self.audio.update(dt)
        self._update_hub(dt)
        self._update_fullscreen_shortcut()
        self.upgrade_hover_guard_timer = max(
            0.0,
            self.upgrade_hover_guard_timer - dt,
        )
        restart_pressed = HEngine.Input.IsKeyPressed(HEngine.KeyCode.R)
        restart_triggered = restart_pressed and not self.last_restart_pressed
        self.last_restart_pressed = restart_pressed
        pause_pressed = HEngine.Input.IsKeyPressed(HEngine.KeyCode.Escape)
        pause_triggered = pause_pressed and not self.last_pause_pressed
        self.last_pause_pressed = pause_pressed

        self._update_menu_animation(dt)
        if self.bLoadingAdventure:
            if self.bSceneTransitionRequested or self.bMenuScene:
                return
            self._advance_runtime_warmup()
            self._sync_loading_ui()
            if self.bRuntimeReady:
                self._complete_adventure_start()
            return
        if self.bSettingsOpen:
            self._set_player_input_enabled(False)
            if pause_triggered:
                self._close_settings()
            return
        if self.bInMainMenu:
            self._set_player_input_enabled(False)
            return
        if self.bGameOver:
            self._set_player_input_enabled(False)
            if restart_triggered:
                self._start_game()
            self._sync_hud()
            return
        if self.bAwaitingUpgrade:
            self._set_player_input_enabled(False)
            self._sync_hud()
            return
        if self.bPaused:
            self._set_player_input_enabled(False)
            if pause_triggered:
                self._set_paused(False)

    def OnUIEvent(self, document_id, source_id, event_type):
        if os.environ.get("HE_SURVIVOR_UI_TRACE", "0") == "1":
            HEngine.HE_CORE_INFO(
                "[SurvivorUI] event=" + event_type
                + " source=" + source_id
                + " settings=" + str(self.bSettingsOpen)
                + " locked=" + str(
                    bool(self.ui_motion and self.ui_motion.is_input_locked())
                ),
            )
        bSettingsControl = (
            self.bSettingsOpen and source_id in _SETTINGS_CONTROL_IDS
        )
        if (self.ui_motion and self.ui_motion.is_input_locked() and
                event_type in ("mousedown", "click", "submit") and
                not bSettingsControl):
            return
        if event_type == "mousemove" and self.bAwaitingUpgrade:
            if (
                not self.bUpgradeHoverArmed
                and self.upgrade_hover_guard_timer <= 0.0
            ):
                self.bUpgradeHoverArmed = True
                self._set_hud_class("upgrade_panel", "hover_enabled", True)
            return

        if event_type == "click":
            self.audio.post("ui_click")

        if self._handle_hub_ui_event(source_id, event_type):
            return

        if source_id == "language_zh" and event_type == "click":
            if self.language != "zh_cn":
                self._set_language("zh_cn")
            return
        if source_id == "language_en" and event_type == "click":
            if self.language != "en":
                self._set_language("en")
            return

        if source_id.startswith("character_") and event_type == "click":
            self._select_character(source_id[len("character_"):])
            return

        upgrade_index = self._upgrade_source_index(source_id)
        if upgrade_index is not None:
            if event_type == "mousedown":
                self._set_upgrade_selection(upgrade_index)
            elif event_type == "click":
                self._set_upgrade_selection(upgrade_index)
                self._select_upgrade(upgrade_index)
            return

        if event_type != "click":
            return

        if source_id == "upgrade_reroll_button":
            if self._reroll_upgrade():
                self.telemetry.rerolls += 1
                self.audio.post("ui_confirm")
            return
        elif source_id == "upgrade_skip_button":
            if self._skip_upgrade():
                self.telemetry.skips += 1
            return
        elif source_id == "upgrade_banish_button":
            selected_index = self.upgrade_selected_index
            if selected_index < 0:
                selected_index = 0
            if (
                    self.pending_banish_index != selected_index
                    or self.banish_confirm_timer <= 0.0):
                self.pending_banish_index = selected_index
                self.banish_confirm_timer = 2.0
                self._set_hud_text(
                    "upgrade_banish_label",
                    self._text("upgrade_banish_confirm"),
                )
                return
            if self._banish_upgrade(selected_index):
                self.telemetry.banishes += 1
                self.audio.post("ui_confirm")
            self.pending_banish_index = -1
            self.banish_confirm_timer = 0.0
            return
        elif source_id == "start_button":
            self._start_game()
        elif source_id == "start_settings_button":
            self._open_settings("start")
        elif source_id == "resume_button":
            self._set_paused(False)
        elif source_id == "pause_settings_button":
            self._open_settings("pause")
        elif source_id == "pause_restart_button":
            self._start_game()
        elif source_id == "pause_home_button":
            self._return_to_start_menu()
        elif source_id == "restart_button":
            self._start_game()
        elif source_id == "game_over_home_button":
            self._return_to_start_menu()
        elif source_id == "settings_back_button":
            self._close_settings()
        elif source_id == "settings_defaults_button":
            self._restore_settings_defaults()
        elif source_id == "volume_down":
            self._set_master_volume(self.master_volume - 0.1)
        elif source_id == "volume_up":
            self._set_master_volume(self.master_volume + 0.1)
        elif source_id == "vsync_on":
            self._set_vsync(True)
        elif source_id == "vsync_off":
            self._set_vsync(False)
        elif source_id == "display_fullscreen":
            self._set_fullscreen(True)
        elif source_id == "display_windowed":
            self._set_fullscreen(False)
        elif source_id == "ui_scale_small":
            self._set_ui_scale(0.85)
        elif source_id == "ui_scale_normal":
            self._set_ui_scale(1.0)
        elif source_id == "ui_scale_large":
            self._set_ui_scale(1.15)
        elif source_id == "motion_on":
            self._set_motion_enabled(True)
        elif source_id == "motion_off":
            self._set_motion_enabled(False)
        elif source_id == "flash_on":
            self._set_damage_flash_enabled(True)
        elif source_id == "flash_off":
            self._set_damage_flash_enabled(False)

    def OnUIEventEx(self, document_id, target_id, event_type, payload):
        if self._handle_hub_extended_event(target_id, event_type, payload):
            return
        # Extended animation events intentionally use the exact event target.
        # UiMotion v1 is time-driven, while this hook is available to authored
        # pages which want an explicit RCSS completion acknowledgement.
        if event_type not in ("animationend", "transitionend"):
            return

    @staticmethod
    def _upgrade_source_index(source_id):
        if not source_id.startswith("upgrade_"):
            return None

        for index in range(3):
            suffix = "_" + str(index + 1)
            if source_id == "upgrade" + suffix or source_id.endswith(suffix):
                return index
        return None

    def Stop(self):
        if getattr(self, "profile", None) and self._has_uncommitted_run():
            self._finish_run("return_hub")
        self.telemetry.write(self, "stop")
        self.audio.stop()
        self._set_player_input_enabled(True)
        self._destroy_menu_preview()
        self._clear_runtime_entities()
        HEngine.VFX.StopAll()
        if self.previous_vsync is not None:
            HEngine.Settings.SetVSync(self.previous_vsync)
            self.previous_vsync = None
        if self.previous_fullscreen is not None:
            HEngine.Settings.SetFullscreen(self.previous_fullscreen)
            self.previous_fullscreen = None
        if self.ui_motion:
            self.ui_motion.Shutdown()
            self.ui_motion = None
            self.ui_screens = None
        if self.document_id:
            RmlUI.SetMouseCursorVisible(self.document_id, False)
            RmlUI.Unload(self.document_id)
            self.document_id = ""

    def _text(self, key, **values):
        language_table = SURVIVOR_TEXT.get(self.language, SURVIVOR_TEXT["zh_cn"])
        template = language_table.get(key, SURVIVOR_TEXT["en"].get(key, key))
        return template.format(**values)

    @staticmethod
    def _config_value(config_text, key):
        marker = '"' + key + '"'
        marker_index = config_text.find(marker)
        if marker_index < 0:
            return None

        value_index = config_text.find(":", marker_index + len(marker))
        if value_index < 0:
            return None
        value_index += 1
        while value_index < len(config_text) and config_text[value_index].isspace():
            value_index += 1
        if value_index >= len(config_text):
            return None

        if config_text[value_index] == '"':
            end_index = config_text.find('"', value_index + 1)
            if end_index < 0:
                return None
            return config_text[value_index + 1:end_index]

        end_index = len(config_text)
        for delimiter in (",", "\n", "}"):
            delimiter_index = config_text.find(delimiter, value_index)
            if delimiter_index >= 0:
                end_index = min(end_index, delimiter_index)
        return config_text[value_index:end_index].strip()

    @staticmethod
    def _config_bool(config_text, key, fallback):
        value = SurvivorGame._config_value(config_text, key)
        if value is None:
            return fallback
        normalized_value = value.lower()
        if normalized_value == "true":
            return True
        if normalized_value == "false":
            return False
        return fallback

    def _apply_settings_config(self, config_text):
        configured_language = self._config_value(config_text, "Language")
        if configured_language in SURVIVOR_TEXT:
            self.language = configured_language

        configured_volume = self._config_value(config_text, "MasterVolume")
        if configured_volume is not None:
            try:
                parsed_volume = float(configured_volume)
                if parsed_volume != parsed_volume:
                    raise ValueError("MasterVolume is NaN")
                self.master_volume = max(0.0, min(1.0, parsed_volume))
            except (ValueError, OverflowError):
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] Ignoring invalid MasterVolume",
                )

        configured_scale = self._config_value(config_text, "UIScale")
        if configured_scale is not None:
            try:
                parsed_scale = float(configured_scale)
                if parsed_scale != parsed_scale:
                    raise ValueError("UIScale is NaN")
                self.ui_scale = max(0.85, min(1.15, parsed_scale))
            except (ValueError, OverflowError):
                HEngine.HE_CORE_WARN(
                    "[SurvivorGame] Ignoring invalid UIScale",
                )

        self.bVSyncEnabled = self._config_bool(
            config_text,
            "VSync",
            self.bVSyncEnabled,
        )
        self.bFullscreen = self._config_bool(
            config_text,
            "Fullscreen",
            self.bFullscreen,
        )
        self.bMotionEnabled = self._config_bool(
            config_text,
            "MotionEnabled",
            self.bMotionEnabled,
        )
        self.bDamageFlashEnabled = self._config_bool(
            config_text,
            "DamageFlashEnabled",
            self.bDamageFlashEnabled,
        )
        configured_opacity = self._config_value(config_text, "ProjectileOpacity")
        if configured_opacity is not None:
            try:
                self.player_projectile_opacity = max(
                    0.25, min(1.0, float(configured_opacity)),
                )
            except (ValueError, OverflowError):
                HEngine.HE_CORE_WARN("[SurvivorGame] Ignoring invalid ProjectileOpacity")
        configured_density = self._config_value(config_text, "ParticleDensity")
        if configured_density in ("auto", "low", "medium", "high"):
            self.particle_density = configured_density
        configured_numbers = self._config_value(config_text, "DamageNumbers")
        if configured_numbers in ("off", "reduced", "full"):
            self.damage_numbers_mode = configured_numbers
        self.bScreenShakeEnabled = self._config_bool(
            config_text, "ScreenShake", self.bScreenShakeEnabled,
        )
        configured_telegraph = self._config_value(config_text, "TelegraphColor")
        if configured_telegraph in (
                "default", "deuteranopia", "tritanopia", "high_contrast"):
            self.enemy_telegraph_color = configured_telegraph
        self.bAutoVisualThrottle = self._config_bool(
            config_text, "AutoVisualThrottle", self.bAutoVisualThrottle,
        )


    def _set_language(self, language):
        if language not in SURVIVOR_TEXT:
            return

        language_changed = self.language != language
        self.language = language
        if language_changed:
            self._save_settings()
        self.hud_cache.clear()
        self._apply_language()
        if self.bAwaitingUpgrade:
            self._refresh_upgrade_panel()
        if self.bGameOver:
            self._sync_game_over_text()
        if self.banner_key:
            self._set_hud_text("banner", self._text(self.banner_key))
        self._sync_settings_ui()
        self._sync_hud()


    def _apply_vfx_showcase_override(self):
        showcase_weapon = os.environ.get("HE_SURVIVOR_VFX_WEAPON", "").strip().lower()
        if showcase_weapon not in WEAPON_DEFS:
            return
        try:
            showcase_level = int(os.environ.get("HE_SURVIVOR_VFX_LEVEL", "4"))
        except ValueError:
            showcase_level = 4
        showcase_level = max(1, min(10, showcase_level))
        for weapon_code in WEAPON_ORDER:
            self._set_weapon_level(
                weapon_code,
                showcase_level if weapon_code == showcase_weapon else 0,
            )
        self.weapon_slots = [showcase_weapon]
        self.experience_to_level = 1_000_000_000
        setattr(self, showcase_weapon + "_timer", 1.5)
        HEngine.HE_CORE_INFO(
            "[SurvivorVFX] Showcase weapon="
            + showcase_weapon
            + " level="
            + str(showcase_level)
        )

    def _apply_capture_scenario_override(self):
        text = os.environ.get("HE_SURVIVOR_CAPTURE_TIME", "").strip()
        scenario = os.environ.get(
            "HE_SURVIVOR_CAPTURE_SCENARIO", "",
        ).strip().lower()
        if not text and not scenario:
            return
        if text:
            try:
                start_time = max(0.0, min(899.0, float(text)))
            except ValueError:
                raise ValueError("HE_SURVIVOR_CAPTURE_TIME must be numeric")
        else:
            start_time = 0.0
        mature_weapons = (
            "comet", "ring", "fireball", "moonblade", "bubble", "aura",
        )[:getattr(self, "weapon_slot_limit", 3)]
        capture_weapon_level = (
            2
            if scenario.startswith("region_") or scenario == "low_particle" else
            10
        )
        for weapon_id in WEAPON_ORDER:
            self._set_weapon_level(
                weapon_id,
                capture_weapon_level if weapon_id in mature_weapons else 0,
            )
        self.weapon_slots = list(mature_weapons)
        if scenario == "three_slot_adventure":
            for weapon_id in mature_weapons:
                self._set_weapon_level(weapon_id, 7)
        elif scenario == "six_slot_nightmare":
            for weapon_id in mature_weapons:
                self._set_weapon_level(weapon_id, 10)
        for tome_id in TOME_ORDER:
            self.tome_levels[tome_id] = (
                5 if tome_id in (
                    "might", "haste", "reach", "quantity", "velocity", "duration",
                ) else 0
            )
        self.tome_slots = [
            "might", "haste", "reach", "quantity", "velocity", "duration",
        ]
        self.elapsed = start_time
        self.capture_override_start_time = start_time
        self.level = min(45, max(1, 1 + int(start_time / 22.0)))
        self.experience = 0.0
        self.experience_to_level = self._experience_requirement(self.level)
        self._recompute_tome_stats()
        self._dispatch_combat_hook("level", {"level": self.level})
        if os.environ.get("HE_SURVIVOR_CAPTURE_PLAYER_HP", "0") == "1":
            self.health = 1.0
        if self.document_id:
            self._set_hud_class("hud", "low_particle", scenario == "low_particle")
            self._set_hud_class(
                "hud", "particle_density_low", scenario == "low_particle",
            )
        HEngine.HE_CORE_INFO(
            "[SurvivorCapture] deterministic scenario time=" + str(start_time),
        )

    def _reset_run(self):
        self._clear_runtime_entities()
        self.random_state = int(getattr(self, "selected_run_seed", 7319)) & 0xFFFFFFFF
        self.telemetry.reset()
        if hasattr(self, "capture_player_position_override"):
            del self.capture_player_position_override
        self._reset_domain_powers()
        self._reset_region_objectives()
        if self.quest_tracker is not None:
            self.quest_tracker.reset_run()
        HEngine.VFX.StopAll()
        self.elapsed = 0.0
        self.spawn_timer = 0.15
        self.thunder_timer = 0.2
        self.ring_timer = 0.45
        self.fireball_timer = 0.75
        self.moonblade_timer = 0.35
        self.bubble_timer = 0.55
        self.tornado_timer = 0.80
        self.starfall_timer = 0.65
        self.aura_timer = 0.25
        self.dagger_timer = 0.40
        self.starwheel_timer = 0.70
        self.petalstorm_timer = 0.36
        self.comet_timer = 0.48
        for weapon_code in WEAPON_ORDER[12:]:
            setattr(self, weapon_code + "_timer", 0.55)
        self.active_ring_waves = []
        self.active_fireballs = []
        self.active_bubble_chains = []
        self.active_tornado_zones = []
        self.active_starfall_impacts = []
        self.active_custom_areas = []
        self.active_custom_beams = []
        self.pending_weapon_echoes = []
        self.domain_power_effects = []
        self.domain_activation_overcharges = set()
        self.active_projectiles = []
        self.pending_projectile_spawns = []
        self.projectile_budget.reset()
        self.hud_timer = 0.0
        self.monster_update_accumulator = 0.0
        self.pickup_update_accumulator = self.PICKUP_UPDATE_INTERVAL * 0.5
        self.health = 100.0
        self.max_health = 100.0
        self.level = 1
        self.experience = 0.0
        self.experience_to_level = 5
        self.kills = 0
        self.score = 0
        self.collected_shards = 0
        self.last_player_hook_position = None
        self.weapon_telemetry = {
            weapon_code: {
                "damage": 0.0,
                "hits": 0,
                "criticalHits": 0,
                "kills": 0,
                "casts": 0,
                "projectiles": 0,
                "visualDegrades": 0,
                "spawnRetries": 0,
            }
            for weapon_code in WEAPON_ORDER
        }
        self.run_boss_kills = 0
        self.run_total_boss_kills = 0
        self.run_elite_kills = 0
        self.run_reward_elite_kills = 0
        self.run_gold = 0
        self.run_elite_bonus_gold = 0
        self.pending_chest_rewards = []
        self.enemy_projectile_effects = {}
        self.enemy_zone_effects = {}
        self.enemy_telegraph_effects = {}
        self.enemy_batch_telemetry = {}
        self.active_chests = []
        self.chest_pool = []
        self.trinket_slots = []
        self.active_evolutions = {}
        self.evolution_times = {}
        self.run_damage_taken = 0.0
        self.run_damage_prevented = 0.0
        self.run_evaded_hits = 0
        self.run_healed = 0.0
        self.run_distance_moved = 0.0
        self.last_damage_elapsed = 0.0
        self.multikill_window_start = 0.0
        self.multikill_count = 0
        self.full_health_streak = 0.0
        self.character_damage_multiplier = 1.0
        self.character_cooldown_multiplier = 1.0
        self.character_reach_multiplier = 1.0
        self.character_projectile_bonus = 0
        self.character_projectile_speed_multiplier = 1.0
        self.monster_activation_serial = 0
        self.pickup_activation_serial = 0
        training_level = getattr(self, "profile", {}).get(
            "characterTraining", {},
        ).get(self.selected_character, 0)
        if not getattr(self, "profile", {}).get(
                "characterTrainingEnabled", {}).get(
                    self.selected_character, True):
            training_level = 0
        character_state = compile_character_start_state(
            self.selected_character,
            CHARACTER_DEFS[self.selected_character],
            training_level,
        )
        self.weapon_slot_limit = int(
            getattr(getattr(self, "run_config", None), "weapon_slot_limit", 3)
        )
        starter_weapon = character_state["starter_weapon"]
        for weapon_code in WEAPON_ORDER:
            setattr(self, weapon_code + "_level", 1 if weapon_code == starter_weapon else 0)
        self.weapon_slots = [
            weapon_code
            for weapon_code in WEAPON_ORDER
            if self._weapon_level(weapon_code) > 0
        ][:self.weapon_slot_limit]
        for weapon_code in WEAPON_ORDER:
            if weapon_code not in self.weapon_slots:
                self._set_weapon_level(weapon_code, 0)
        self._apply_vfx_showcase_override()
        self.tome_levels = {tome_code: 0 for tome_code in TOME_ORDER}
        self.tome_slots = []
        profile = getattr(self, "profile", {})
        run_config = getattr(self, "run_config", None)
        self.selected_difficulty = (
            run_config.selected_difficulty
            if run_config is not None else
            profile.get("selectedDifficulty", "adventure")
        )
        self.selected_challenge = (
            run_config.challenge_ids[0]
            if run_config is not None and run_config.challenge_ids else
            "none"
        )
        power_ups = profile.get("powerUps", {})
        power_up_enabled = profile.get("powerUpsEnabled", {})
        def enabled_power_up(power_up_id):
            return (
                power_ups.get(power_up_id, 0) > 0
                and power_up_enabled.get(power_up_id, True)
            )
        completed_quests = set(profile.get("completedQuests", ()))
        self.rerolls_remaining = (
            power_ups.get("meta_reroll", 0)
            if enabled_power_up("meta_reroll") else 0
        ) + (
            1 if "quest_system_reroll" in completed_quests else 0
        )
        self.skips_remaining = (
            power_ups.get("meta_skip", 0)
            if enabled_power_up("meta_skip") else 0
        ) + (
            1 if "quest_system_skip" in completed_quests else 0
        )
        self.banishes_remaining = (
            power_ups.get("meta_banish", 0)
            if enabled_power_up("meta_banish") else 0
        ) + (
            1 if "quest_system_banish" in completed_quests else 0
        )
        self.run_banished = set()
        self._active_upgrade_pool = None
        self.crit_chance = character_state["crit_chance"] + (
            power_ups.get("meta_luck", 0) * 0.02
            if enabled_power_up("meta_luck") else 0.0
        )
        self.crit_multiplier = 2.0
        self.knockback = 0.42
        meta_magnet = (
            power_ups.get("meta_magnet", 0) * 0.125
            if enabled_power_up("meta_magnet") else 0.0
        )
        self.magnet_range = character_state["magnet_range"] * (1.0 + meta_magnet)
        self.pickup_range = 0.85
        self.damage_reduction = 0.0
        self.armor = character_state["armor"]
        self.thorns = character_state["thorns"]
        self.evasion = character_state["evasion"]
        self.luck = character_state["luck"] + (
            power_ups.get("meta_luck", 0) * 0.02
            if enabled_power_up("meta_luck") else 0.0
        )
        self.character_xp_multiplier = character_state["xp_gain_multiplier"] * (
            1.0 + (
                power_ups.get("meta_growth", 0) * 0.03
                if enabled_power_up("meta_growth") else 0.0
            )
        )
        self.character_gold_multiplier = character_state["gold_gain_multiplier"]
        self.character_difficulty_multiplier = character_state["difficulty_multiplier"]
        self.active_character_hooks = character_state["hooks"]
        self.base_character_max_health = character_state["max_health"] * (
            1.0 + (
                power_ups.get("meta_health", 0) * 0.05
                if enabled_power_up("meta_health") else 0.0
            )
        )
        self.base_character_magnet_range = self.magnet_range
        self.base_character_damage_reduction = 0.0
        self.base_character_crit_chance = self.crit_chance
        self.base_character_thorns = character_state["thorns"]
        self.recovery_per_second = (
            power_ups.get("meta_recovery", 0) * 0.05
            if enabled_power_up("meta_recovery") else 0.0
        )
        self.base_character_recovery_per_second = self.recovery_per_second
        self.tome_gold_multiplier = 1.0
        self.status_multiplier = 1.0
        self.curse_level = 0
        movement = self.player.GetComponent("CharacterMovement")
        movement.MaxSpeed = character_state["move_speed"] * (
            1.0 + (
                power_ups.get("meta_move", 0) * 0.03
                if enabled_power_up("meta_move") else 0.0
            )
        )
        self.max_health = self.base_character_max_health
        challenge_tuning = (
            run_config.challenge_tuning_for_world_minute(0)
            if run_config is not None else
            self._challenge_tuning()
        )
        if challenge_tuning.get("playerMaxHealth") is not None:
            self.max_health = min(
                self.max_health,
                float(challenge_tuning["playerMaxHealth"]),
            )
        self.health = self.max_health
        self.character_cooldown_multiplier = character_state[
            "weapon_cooldown_multiplier"
        ]
        self.character_reach_multiplier = character_state[
            "weapon_reach_multiplier"
        ]
        self.character_damage_multiplier = character_state[
            "weapon_damage_multiplier"
        ] * (
            1.0 + (
                power_ups.get("meta_might", 0) * 0.03
                if enabled_power_up("meta_might") else 0.0
            )
        )
        mastery_level = min(
            10,
            profile.get("characterMasteryXp", {}).get(
                self.selected_character, 0,
            ) // 500,
        )
        self.character_damage_multiplier *= 1.0 + mastery_level * 0.003
        self.base_character_weapon_damage_multiplier = self.character_damage_multiplier
        self.character_duration_multiplier = 1.0
        self.character_projectile_bonus = character_state["projectile_bonus"]
        self.character_projectile_speed_multiplier = character_state[
            "projectile_speed_multiplier"
        ]
        self._compile_character_hooks()
        self.run_revives_remaining = (
            1
            if enabled_power_up("meta_revive")
            and power_ups.get("meta_revive", 0) > 0
            else 0
        )
        self.run_revives_used = 0
        self.bAwaitingUpgrade = False
        self.bUpgradeHoverArmed = False
        self.upgrade_hover_guard_timer = 0.0
        self.pending_banish_index = -1
        self.banish_confirm_timer = 0.0
        self.bPaused = False
        self.bGameOver = False
        self.bInMainMenu = False
        self.bSettingsOpen = False
        self.banner_timer = 3.0
        self.damage_flash_timer = 0.0
        self.level_up_flash_timer = 0.0
        self.damage_cooldown = 0.0
        self.player_ground_check_timer = 0.0
        warmup_weapon_ids = tuple(self.weapon_slots)
        region_foundation_effects = [
            asset_path(config["assetKeys"]["castVfx"])
            for config in SurvivorDomainPowers.DOMAIN_POWER_CONFIG.values()
        ]
        self.pending_effects = list(dict.fromkeys([
            WEAPON_DEFS[weapon_code]["bodyVfx"]
            for weapon_code in warmup_weapon_ids
            if WEAPON_DEFS[weapon_code]["bodyVfx"]
        ] + [
            self.BOSS_SPAWN_WARNING_EFFECT,
            self.ENEMY_PROJECTILE_EFFECT,
            self.ENEMY_ZONE_TELEGRAPH_EFFECT,
        ] + region_foundation_effects))
        self.pending_pickup_spawns.clear()
        self.warmup_stage = "effects"
        self.warmup_monster = None
        early_enemy_ids = {
            enemy_id
            for phase in self.WAVE_PHASES[:2]
            for enemy_id, _ in phase["pool"]
        }
        self.pending_monster_warmups = [
            archetype for archetype in self.MONSTER_ARCHETYPES
            if archetype["id"] in early_enemy_ids
        ] + [self.BOSS_ARCHETYPES[0]]
        visual_by_weapon = {
            "comet": "comet", "dagger": "bolt", "starwheel": "wheel",
            "bubble": "bubble", "fireball": "fireball", "petalstorm": "petal",
            "honeyneedle": "needle", "sporecap": "spore", "phantombell": "bell",
            "coralanchor": "anchor", "prismorbit": "prism",
            "acornmortar": "acorn", "frostorb": "frost", "gravityyoyo": "yoyo",
        }
        self.pending_visual_warmups = list(dict.fromkeys(
            visual_by_weapon[weapon_code]
            for weapon_code in warmup_weapon_ids
            if weapon_code in visual_by_weapon
        ))
        self.warmup_total_effects = len(self.pending_effects)
        self.warmup_total_monsters = len(self.pending_monster_warmups)
        self.warmup_display_progress = 0.0
        self.bRuntimeReady = False
        self.bLoadingAdventure = False
        self._apply_capture_scenario_override()
        self._apply_objective_capture_population()
        self.upgrade_choices = []
        self.upgrade_selected_index = -1
        self.banner_key = "survive_banner"
        self.hud_cache.clear()

        player_transform = self.player.GetComponent("Transform")
        reset_probe = HEngine.vec3(0.0, 8.0, 0.0)
        reset_y = self._grounded_y(
            reset_probe,
            self.PLAYER_GROUND_OFFSET,
            0.08,
        )
        reset_position = getattr(
            self,
            "capture_player_position_override",
            HEngine.vec3(0.0, reset_y, 0.0),
        )
        player_transform.Translation = reset_position
        self.last_safe_player_position = HEngine.vec3(0.0, reset_y, 0.0)
        self.player.Teleport(reset_position)
        self._set_player_input_enabled(True)

        if self.document_id:
            self._set_hud_class("upgrade_panel", "hover_enabled", False)
            RmlUI.SetMouseCursorVisible(self.document_id, False)
            RmlUI.SetStyle(self.document_id, "title_backdrop", "display", "none")
            RmlUI.SetStyle(self.document_id, "upgrade_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "pause_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "settings_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "game_over_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "start_panel", "display", "none")
            RmlUI.SetStyle(self.document_id, "gameplay_hud", "display", "block")
            RmlUI.SetStyle(self.document_id, "boss_panel", "display", "none")
            self._apply_language()
            self._set_hud_text("banner", self._text("survive_banner"))
        self._sync_hud()

    def _clear_runtime_entities(self):
        HEngine.ResetSurvivorAgents()
        HEngine.ResetSurvivorPickups()
        all_entities = []
        if self.warmup_monster is not None:
            all_entities.append(self.warmup_monster["entity"])
        for monster in self.monsters:
            all_entities.append(monster["entity"])
        for pool in self.monster_pools.values():
            for monster in pool:
                all_entities.append(monster["entity"])
        for pickup in self.pickups:
            all_entities.append(pickup["entity"])
        for pickup in self.pickup_pool:
            all_entities.append(pickup["entity"])
        for chest in self.active_chests:
            all_entities.append(chest["entity"])
        for chest in self.chest_pool:
            all_entities.append(chest["entity"])

        for runtime_entity in all_entities:
            try:
                HEngine.Destroy(runtime_entity)
            except Exception:
                pass

        self.monsters = []
        self.monsters_by_id = {}
        self.monster_pools = {}
        self.pickups = []
        self.pickups_by_id = {}
        self.pickup_pool = []
        self.active_chests = []
        self.chest_pool = []
        self.pending_chest_rewards = []
        self.enemy_projectile_effects = {}
        self.enemy_zone_effects = {}
        self.enemy_telegraph_effects = {}
        self.enemy_batch_telemetry = {}
        self.pending_pickup_spawns.clear()
        self.warmup_monster = None
        self.pending_monster_warmups = []
        self.pending_visual_warmups = []
        self.active_ring_waves = []
        self.active_fireballs = []
        self.active_bubble_chains = []
        self.active_tornado_zones = []
        self.active_starfall_impacts = []
        self.active_custom_areas = []
        self.active_custom_beams = []
        self.pending_weapon_echoes = []
        self.active_projectiles = []
        self.pending_projectile_spawns = []
        self.projectile_budget.reset()
        for visual_entity in self.projectile_visual_entities:
            try:
                HEngine.Destroy(visual_entity)
            except Exception:
                pass
        self.projectile_visual_pool = {
            "bolt": [], "wheel": [], "comet": [],
            "bubble": [], "fireball": [], "petal": [],
            "needle": [], "spore": [], "bell": [], "anchor": [],
            "prism": [], "acorn": [], "frost": [], "yoyo": [],
        }
        self.projectile_visual_entities = []

    @_profile_stage("WaveSpawn")
    def _spawn_wave(self, player_pos):
        if self.spawn_timer > 0.0 or not self.bRuntimeReady:
            return

        phase = self._current_wave_phase()
        if getattr(self, "_global_spawning_suppressed", lambda: False)():
            self.spawn_timer = 0.10
            return
        total_alive = sum(1 for monster in self.monsters if not monster["dead"])
        alive_count = sum(
            1 for monster in self.monsters
            if not monster["dead"]
            and not monster.get("region_spawned", False)
            and not monster.get("boss", False)
        )
        desired_count = self._phase_population_target(phase)
        missing = desired_count - alive_count
        batch = min(
            phase["batch"],
            max(0, missing),
            max(0, self.MAX_MONSTERS - total_alive),
        )

        spawned_count = 0
        for _ in range(batch):
            spawn = getattr(
                self,
                "_find_global_spawn_position",
                lambda position, _event: self._find_spawn_position(position),
            )(player_pos, phase.get("event", ""))
            if spawn is None:
                record_failure = getattr(self, "_record_spawn_failure", None)
                if record_failure is not None:
                    record_failure("world_ground_probe_failed")
                continue
            if self._activate_monster(spawn, False, phase):
                spawned_count += 1

        difficulty = self._difficulty_entry()
        challenge = self._challenge_tuning()
        frequency_multiplier = (
            difficulty["spawn"]
            * challenge["enemyCount"]
            * getattr(self, "character_difficulty_multiplier", 1.0)
            * (1.0 + getattr(self, "curse_level", 0) * 0.08)
        )
        self.spawn_timer = phase["interval"] / max(1.0, frequency_multiplier)


    @_profile_stage("PendingPickupSpawns")
    def _drain_pending_pickup_spawns(self):
        spawn_count = min(
            self.PICKUP_SPAWN_BUDGET_PER_FRAME,
            len(self.pending_pickup_spawns),
        )
        for _ in range(spawn_count):
            pending = self.pending_pickup_spawns.pop(0)
            x, y, z, value = pending[:4]
            source_kind = pending[4] if len(pending) > 4 else "world"
            encounter_id = pending[5] if len(pending) > 5 else ""
            self._spawn_experience(
                HEngine.vec3(x, y, z),
                value,
                source_kind,
                encounter_id,
            )


    @_profile_stage("Weapons")
    def _update_weapons(self, player_pos, dt):
        self._update_projectile_retries(dt)
        pending_echoes = []
        for echo in self.pending_weapon_echoes:
            echo["timer"] -= dt
            if echo["timer"] > 0.0:
                pending_echoes.append(echo)
                continue
            weapon_code = echo["weapon_id"]
            previous_timer = getattr(self, weapon_code + "_timer")
            self.weapon_proc_multiplier = echo.get("proc", 0.45)
            self.bWeaponEchoCast = True
            getattr(self, "_fire_" + weapon_code)(player_pos)
            self.bWeaponEchoCast = False
            self.weapon_proc_multiplier = 1.0
            setattr(self, weapon_code + "_timer", previous_timer)
        self.pending_weapon_echoes = pending_echoes

        self._update_projectiles(player_pos, dt)
        self._update_ring_waves(dt)
        self._update_fireballs(dt)
        self._update_bubble_chains(dt)
        self._update_tornado_zones(dt)
        self._update_starfall_impacts(dt)
        self._update_custom_areas(dt)
        self._update_custom_beams(dt)

        levels = {
            weapon_code: self._weapon_level(weapon_code)
            for weapon_code in WEAPON_ORDER
        }
        timers = {
            weapon_code: getattr(self, weapon_code + "_timer")
            for weapon_code in WEAPON_ORDER
        }
        for weapon_code in due_weapon_ids(WEAPON_ORDER, levels, timers):
            previous_casts = self.weapon_telemetry[weapon_code]["casts"]
            if _STAGE_TIMING_ENABLED:
                cast_start_ns = time.perf_counter_ns()
            getattr(self, "_fire_" + weapon_code)(player_pos)
            if _STAGE_TIMING_ENABLED:
                cast_ms = (time.perf_counter_ns() - cast_start_ns) / 1_000_000.0
                if cast_ms > 3.0:
                    HEngine.HE_CORE_INFO(
                        "[SurvivorWeaponSpike] weapon={} elapsed={:.3f} cast={:.3f}ms".format(
                            weapon_code, self.elapsed, cast_ms,
                        )
                    )
            if (
                    self.weapon_telemetry[weapon_code]["casts"] == previous_casts
                    and getattr(self, weapon_code + "_timer") > 0.15):
                self.weapon_telemetry[weapon_code]["casts"] += 1
                if self.quest_tracker is not None:
                    self.quest_tracker.record(
                        "casts", 1, {"weapon": weapon_code},
                    )
            bCasted = self.weapon_telemetry[weapon_code]["casts"] > previous_casts
            if bCasted:
                self._on_weapon_cast_trinkets(weapon_code)
            if (
                    bCasted
                    and
                    not getattr(self, "bWeaponEchoCast", False)
                    and self._consume_mossling_echo()):
                self.pending_weapon_echoes.append({
                    "timer": 0.18,
                    "weapon_id": weapon_code,
                    "proc": 0.45,
                })
